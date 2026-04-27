"""
Addon loader for the swarm-orchestrator skill.

Discovers addon folders across multiple search paths, parses manifests, resolves
conflicts by priority, and exposes a query API used by the orchestrator at
session start and during dispatch.

Search order (later paths override earlier ones for same-named contributions):
  1. <skill-dir>/addons/        (built-in, e.g., _core/auto-adapter)
  2. ~/.claude/swarm-orchestrator/addons/   (user-installed, machine-local)
  3. <workspace>/.swarm/addons/  (project-scoped)

Conflict rule: project > user > built-in. Within a tier, higher `priority`
wins; ties broken alphabetically.

This module has zero runtime dependencies beyond the standard library + PyYAML.
PyYAML is already used by the dashboard and other skill components.

Usage:

    from lib.addons import load_addons

    registry = load_addons(settings={
        "addons": {
            "auto_discovery": True,
            "search_paths": [
                "<skill-dir>/addons",
                "~/.claude/swarm-orchestrator/addons",
                "<workspace>/.swarm/addons",
            ],
            "disabled": [],
            "priority_overrides": {},
        }
    }, skill_dir="C:/.../swarm-orchestrator", workspace_dir="C:/.../my-project")

    for addon in registry.list():
        print(addon.name, addon.version, addon.priority, addon.path)

    # Find the recipe for a "learn" trigger
    recipe = registry.find_recipe("learn-repo")
    skill = registry.find_skill_by_trigger("תעדכני את האתר")

    # Run hooks (fire-and-forget)
    registry.run_hooks("dispatch_start", {
        "session_id": "...",
        "agent_id": "...",
        "model": "sonnet",
    })
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


log = logging.getLogger("swarm.addons")
if not log.handlers:
    log.setLevel(logging.INFO)


CAPABILITY_KEYS = {
    "hebrew_prose",
    "tool_execution",
    "architectural_high_blast",
    "code_generation_english",
    "critic_verification",
    "image_understanding",
}

KNOWN_HOOK_EVENTS = {
    "dispatch_start",
    "agent_returned",
    "synthesis_done",
    "gate_failed",
    "cost_report",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Hook:
    event: str                       # one of KNOWN_HOOK_EVENTS
    script: Path                     # absolute path to .py / .sh / .bat


@dataclass
class TriggerMap:
    english: list[str] = field(default_factory=list)
    hebrew: list[str] = field(default_factory=list)
    other: dict[str, list[str]] = field(default_factory=dict)

    def all_patterns(self) -> list[str]:
        out = list(self.english) + list(self.hebrew)
        for v in self.other.values():
            out.extend(v)
        return out


@dataclass
class Addon:
    name: str
    version: str
    description: str
    path: Path                       # addon root dir
    swarm_orchestrator_min: str = ""
    author: str = ""
    status: str = "enabled"          # enabled | disabled
    priority: int = 50
    tags: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    triggers: TriggerMap = field(default_factory=TriggerMap)
    provides: dict[str, Any] = field(default_factory=dict)
    hooks: list[Hook] = field(default_factory=list)
    source_tier: str = "built-in"    # built-in | user | project

    # Resolved at registry time:
    skills: list[Path] = field(default_factory=list)
    recipes: list[Path] = field(default_factory=list)
    templates: list[Path] = field(default_factory=list)
    workflows: list[Path] = field(default_factory=list)
    docs: list[Path] = field(default_factory=list)
    model_tiers_overrides: Path | None = None

    @property
    def is_active(self) -> bool:
        return self.status == "enabled"

    def to_summary(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "source": self.source_tier,
            "path": str(self.path),
            "skills_count": len(self.skills),
            "recipes_count": len(self.recipes),
            "workflows_count": len(self.workflows),
            "hooks_count": len(self.hooks),
        }


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def _resolve_search_path(
    raw: str,
    skill_dir: Path,
    workspace_dir: Path | None,
) -> Path | None:
    """Expand `<skill-dir>` / `<workspace>` tokens and `~`."""
    s = raw
    s = s.replace("<skill-dir>", str(skill_dir))
    if workspace_dir is not None:
        s = s.replace("<workspace>", str(workspace_dir))
    elif "<workspace>" in s:
        return None  # no workspace, skip this path
    s = os.path.expanduser(s)
    p = Path(s).resolve()
    return p


# ---------------------------------------------------------------------------
# Manifest parsing
# ---------------------------------------------------------------------------


class ManifestError(ValueError):
    pass


def _parse_manifest(addon_dir: Path) -> dict:
    manifest_path = addon_dir / "addon.yaml"
    if not manifest_path.exists():
        manifest_path = addon_dir / "addon.yml"
    if not manifest_path.exists():
        raise ManifestError(f"no addon.yaml in {addon_dir}")
    if yaml is None:
        raise ManifestError("PyYAML not installed; cannot parse addon manifests")
    try:
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ManifestError(f"YAML parse error in {manifest_path}: {e}") from e
    if not isinstance(data, dict):
        raise ManifestError(f"manifest must be a YAML mapping: {manifest_path}")

    required = {"name", "version", "description"}
    missing = required - data.keys()
    if missing:
        raise ManifestError(f"manifest {manifest_path} missing required keys: {sorted(missing)}")
    return data


def _resolve_provides(
    addon_dir: Path,
    provides: dict,
) -> tuple[list[Path], list[Path], list[Path], list[Path], list[Path], Path | None]:
    """Resolve provides[*] paths. Missing files become warnings (logged), not errors."""
    def _resolve_list(key: str) -> list[Path]:
        items = provides.get(key) or []
        out: list[Path] = []
        if isinstance(items, str):
            items = [items]
        for rel in items:
            p = (addon_dir / rel).resolve()
            if p.exists():
                out.append(p)
            else:
                log.warning("addon %s declares missing %s file: %s", addon_dir.name, key, p)
        return out

    skills = _resolve_list("skills")
    recipes = _resolve_list("recipes")
    templates = _resolve_list("templates")
    workflows = _resolve_list("workflows")
    docs = _resolve_list("docs")

    mt_raw = provides.get("model_tiers_overrides")
    mt_path: Path | None = None
    if mt_raw:
        cand = (addon_dir / mt_raw).resolve()
        if cand.exists():
            mt_path = cand
        else:
            log.warning("addon %s declares missing model_tiers_overrides: %s", addon_dir.name, cand)

    return skills, recipes, templates, workflows, docs, mt_path


def _resolve_hooks(addon_dir: Path, hooks_decl: list[dict] | None) -> list[Hook]:
    if not hooks_decl:
        return []
    out: list[Hook] = []
    for entry in hooks_decl:
        if not isinstance(entry, dict):
            log.warning("addon %s: hook entry must be a mapping; got %r", addon_dir.name, entry)
            continue
        event = entry.get("on")
        rel = entry.get("run")
        if not event or not rel:
            log.warning("addon %s: hook missing on/run keys: %r", addon_dir.name, entry)
            continue
        if event not in KNOWN_HOOK_EVENTS:
            log.warning("addon %s: unknown hook event '%s'; skipping", addon_dir.name, event)
            continue
        script_path = (addon_dir / rel).resolve()
        if not script_path.exists():
            log.warning("addon %s: hook script not found: %s", addon_dir.name, script_path)
            continue
        out.append(Hook(event=event, script=script_path))
    return out


def _build_addon(addon_dir: Path, source_tier: str) -> Addon | None:
    try:
        m = _parse_manifest(addon_dir)
    except ManifestError as e:
        log.warning("addon manifest invalid: %s", e)
        return None

    triggers_raw = m.get("triggers") or {}
    triggers = TriggerMap()
    if isinstance(triggers_raw, dict):
        triggers.english = list(triggers_raw.get("english") or [])
        triggers.hebrew = list(triggers_raw.get("hebrew") or [])
        for k, v in triggers_raw.items():
            if k in ("english", "hebrew"):
                continue
            if isinstance(v, list):
                triggers.other[k] = list(v)

    provides = m.get("provides") or {}
    skills, recipes, templates, workflows, docs, mt = _resolve_provides(addon_dir, provides)

    hooks = _resolve_hooks(addon_dir, provides.get("hooks"))

    addon = Addon(
        name=str(m["name"]).strip(),
        version=str(m["version"]).strip(),
        description=str(m["description"]).strip(),
        path=addon_dir,
        swarm_orchestrator_min=str(m.get("swarm_orchestrator_min") or ""),
        author=str(m.get("author") or ""),
        status=str(m.get("status") or "enabled").strip(),
        priority=int(m.get("priority") if m.get("priority") is not None else 50),
        tags=list(m.get("tags") or []),
        requires=list(m.get("requires") or []),
        triggers=triggers,
        provides=provides,
        hooks=hooks,
        source_tier=source_tier,
        skills=skills,
        recipes=recipes,
        templates=templates,
        workflows=workflows,
        docs=docs,
        model_tiers_overrides=mt,
    )
    return addon


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass
class AddonRegistry:
    addons_by_name: dict[str, Addon] = field(default_factory=dict)
    load_errors: list[str] = field(default_factory=list)

    # ---- query ----

    def list(self) -> list[Addon]:
        return sorted(
            self.addons_by_name.values(),
            key=lambda a: (-a.priority, a.name),
        )

    def get(self, name: str) -> Addon | None:
        return self.addons_by_name.get(name)

    def find_recipe(self, recipe_name: str) -> tuple[Addon, Path] | None:
        for addon in self.list():
            if not addon.is_active:
                continue
            for rpath in addon.recipes:
                if rpath.stem == recipe_name:
                    return addon, rpath
        return None

    def find_skill_by_trigger(self, user_text: str) -> tuple[Addon, Path] | None:
        normalized = unicodedata.normalize("NFC", user_text or "").lower()
        for addon in self.list():
            if not addon.is_active:
                continue
            for spath in addon.skills:
                front = _read_skill_frontmatter(spath)
                if not front:
                    continue
                triggers = front.get("triggers") or {}
                keywords = triggers.get("keywords") or []
                for kw in keywords:
                    if not isinstance(kw, str):
                        continue
                    if unicodedata.normalize("NFC", kw).lower() in normalized:
                        return addon, spath
                patterns = triggers.get("patterns") or []
                for pat in patterns:
                    try:
                        if re.search(pat, user_text):
                            return addon, spath
                    except re.error:
                        continue
        return None

    def find_addon_by_trigger(self, user_text: str) -> tuple[Addon, dict[str, str]] | None:
        """Match the user input against any addon's `triggers:` block.

        Returns (addon, captured_named_groups). For example, the auto-adapter
        addon captures `{repo: "/path"}` from "adapt to /path".
        """
        for addon in self.list():
            if not addon.is_active:
                continue
            for pat in addon.triggers.all_patterns():
                try:
                    m = re.search(pat, user_text, flags=re.IGNORECASE)
                except re.error:
                    continue
                if m:
                    return addon, m.groupdict()
        return None

    def apply_model_tier_overrides(self, base: dict) -> dict:
        """Merge every addon's model_tiers_overrides.yaml into base in priority order."""
        merged = dict(base)
        for addon in self.list():
            if not addon.is_active or addon.model_tiers_overrides is None:
                continue
            try:
                if yaml is None:
                    continue
                doc = yaml.safe_load(addon.model_tiers_overrides.read_text(encoding="utf-8")) or {}
            except Exception as e:  # noqa: BLE001
                log.warning("addon %s: failed to load model_tiers_overrides: %s", addon.name, e)
                continue
            if not isinstance(doc, dict):
                continue
            cap_map = doc.get("capability_map") or doc
            if isinstance(cap_map, dict):
                merged_caps = dict(merged.get("capability_map") or {})
                for k, v in cap_map.items():
                    merged_caps[k] = v
                merged["capability_map"] = merged_caps
        return merged

    # ---- lifecycle ----

    def run_hooks(self, event: str, ctx: dict) -> None:
        """Fire all hooks for the event in parallel daemon threads. Fire-and-forget."""
        if event not in KNOWN_HOOK_EVENTS:
            log.warning("run_hooks: unknown event '%s'", event)
            return
        payload = json.dumps(ctx, ensure_ascii=False, default=str)
        for addon in self.list():
            if not addon.is_active:
                continue
            for hook in addon.hooks:
                if hook.event != event:
                    continue
                t = threading.Thread(
                    target=_run_one_hook, args=(addon.name, hook, payload), daemon=True
                )
                t.start()


def _run_one_hook(addon_name: str, hook: Hook, payload: str) -> None:
    try:
        suffix = hook.script.suffix.lower()
        if suffix == ".py":
            cmd = [sys.executable, str(hook.script)]
        elif suffix == ".sh":
            cmd = ["bash", str(hook.script)]
        elif suffix == ".bat":
            cmd = [str(hook.script)]
        else:
            cmd = [str(hook.script)]
        proc = subprocess.run(
            cmd,
            input=payload,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            log.warning(
                "hook %s/%s exit %d: %s",
                addon_name, hook.script.name, proc.returncode, proc.stderr.strip()[:400],
            )
    except subprocess.TimeoutExpired:
        log.warning("hook %s/%s timed out after 15s", addon_name, hook.script.name)
    except Exception as e:  # noqa: BLE001
        log.warning("hook %s/%s exception: %s", addon_name, hook.script.name, e)


def _read_skill_frontmatter(skill_path: Path) -> dict | None:
    """Parse YAML frontmatter at the top of a skill markdown file."""
    if yaml is None:
        return None
    try:
        text = skill_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def load_addons(
    settings: dict | None = None,
    skill_dir: str | Path | None = None,
    workspace_dir: str | Path | None = None,
) -> AddonRegistry:
    """Discover addons across the configured search paths and return a registry.

    settings keys:
      auto_discovery: bool       — if False, only addons listed in priority_overrides load
      search_paths:   list[str]  — ordered, later paths override earlier
      disabled:       list[str]  — addon names to skip
      priority_overrides: dict[str, int]  — name → forced priority
    """
    settings = (settings or {}).get("addons", settings or {}) or {}
    if "search_paths" not in settings:
        settings["search_paths"] = [
            "<skill-dir>/addons",
            "~/.claude/swarm-orchestrator/addons",
            "<workspace>/.swarm/addons",
        ]
    auto = settings.get("auto_discovery", True)
    disabled = set(settings.get("disabled") or [])
    priority_overrides = settings.get("priority_overrides") or {}

    skill_dir_p = Path(skill_dir).resolve() if skill_dir else Path(__file__).parent.parent
    workspace_dir_p = Path(workspace_dir).resolve() if workspace_dir else None

    registry = AddonRegistry()

    tier_for_path: dict[Path, str] = {}
    resolved_paths: list[Path] = []
    for raw in settings["search_paths"]:
        p = _resolve_search_path(raw, skill_dir_p, workspace_dir_p)
        if p is None:
            continue
        if "<skill-dir>" in raw:
            tier_for_path[p] = "built-in"
        elif "<workspace>" in raw:
            tier_for_path[p] = "project"
        else:
            tier_for_path[p] = "user"
        resolved_paths.append(p)

    seen_paths: set[Path] = set()
    for root in resolved_paths:
        if not root.exists():
            continue
        for entry in sorted(root.rglob("addon.yaml")) + sorted(root.rglob("addon.yml")):
            addon_dir = entry.parent
            if addon_dir in seen_paths:
                continue
            seen_paths.add(addon_dir)

            tier = tier_for_path.get(root, "user")
            addon = _build_addon(addon_dir, source_tier=tier)
            if addon is None:
                registry.load_errors.append(f"failed to build addon at {addon_dir}")
                continue

            # Apply settings overrides
            if addon.name in disabled:
                addon.status = "disabled"
            if addon.name in priority_overrides:
                try:
                    addon.priority = int(priority_overrides[addon.name])
                except (TypeError, ValueError):
                    pass

            # Auto-discovery off → only load addons that are explicitly priority-overridden
            if not auto and addon.name not in priority_overrides:
                addon.status = "disabled"

            # Conflict resolution: same name, later tier wins (project > user > built-in).
            existing = registry.addons_by_name.get(addon.name)
            if existing is None:
                registry.addons_by_name[addon.name] = addon
            else:
                tier_rank = {"built-in": 0, "user": 1, "project": 2}
                if tier_rank[addon.source_tier] > tier_rank[existing.source_tier]:
                    log.info(
                        "addon %s: %s overrides %s (priority %d > %d)",
                        addon.name, addon.source_tier, existing.source_tier,
                        addon.priority, existing.priority,
                    )
                    registry.addons_by_name[addon.name] = addon
                else:
                    log.info(
                        "addon %s: keeping %s instance (priority %d) over %s instance (priority %d)",
                        addon.name, existing.source_tier, existing.priority,
                        addon.source_tier, addon.priority,
                    )

    # Resolve `requires` — disable any addon whose requires aren't all enabled
    for addon in list(registry.addons_by_name.values()):
        for req in addon.requires:
            other = registry.addons_by_name.get(req)
            if other is None or not other.is_active:
                if addon.is_active:
                    log.info(
                        "addon %s requires %s which is missing/disabled; setting status=disabled",
                        addon.name, req,
                    )
                    addon.status = "disabled"
                break

    return registry


# ---------------------------------------------------------------------------
# CLI for `python lib/addons.py list / doctor`
# ---------------------------------------------------------------------------

def _cli() -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="addons", description="Swarm-orchestrator addon CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List discovered addons")
    sub.add_parser("doctor", help="Validate every discovered addon")
    args = parser.parse_args()

    registry = load_addons()
    if args.cmd == "list":
        for a in registry.list():
            print(json.dumps(a.to_summary(), ensure_ascii=False))
        if registry.load_errors:
            print(f"\n{len(registry.load_errors)} load errors:", file=sys.stderr)
            for err in registry.load_errors:
                print(f"  {err}", file=sys.stderr)
        return 0

    if args.cmd == "doctor":
        ok = True
        for a in registry.list():
            issues: list[str] = []
            if not a.skills and not a.recipes and not a.templates and not a.workflows:
                issues.append("addon contributes nothing (no skills/recipes/templates/workflows)")
            if a.requires:
                for r in a.requires:
                    if r not in registry.addons_by_name:
                        issues.append(f"requires '{r}' which is not installed")
            if issues:
                ok = False
                print(f"FAIL {a.name}: {'; '.join(issues)}")
            else:
                print(f"OK   {a.name} ({a.version}, {a.source_tier}, status={a.status})")
        if registry.load_errors:
            ok = False
            for err in registry.load_errors:
                print(f"FAIL load: {err}")
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
