"""obsidian-emit hook: project a finished swarm run into an Obsidian vault.

Triggered by the swarm-orchestrator on the `synthesis_done` event. Reads the
operations session dir and composes a single markdown file with rich
frontmatter (recipe, agents, models, costs, confidence, gate result) plus a
body containing the synthesis, cost report, and per-agent summaries.

Input (stdin, JSON):
    {
        "session_id": str,
        "total_tokens": int,
        "wall_clock_s": float,
        "agents_count": int,
        "recipe": str
    }

Output:
    Writes <vault>/Skills/swarm-orchestrator/runs/<YYYY-MM-DDTHHMM>-<recipe>.md

Exits 0 on success, 0 (silent skip) if vault not configured, 1 on bad input.
This hook is fire-and-forget per the addon contract — never raise.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Vault resolution
# ---------------------------------------------------------------------------


def resolve_vault_path() -> Path | None:
    """Resolve the Obsidian vault path. First hit wins."""
    # 1. user settings
    settings_path = Path.home() / ".claude" / "swarm-orchestrator" / "settings.json"
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            v = (
                settings.get("addons", {})
                .get("obsidian-emit", {})
                .get("vault_path")
            )
            if v:
                p = Path(os.path.expanduser(v))
                if p.is_dir():
                    return p
        except Exception:
            pass

    # 2. env var
    v = os.environ.get("SWARM_OBSIDIAN_VAULT")
    if v:
        p = Path(os.path.expanduser(v))
        if p.is_dir():
            return p

    # 3. auto-detect ~/Desktop/Obsidian/<vault>/.obsidian/
    desktop_obsidian = Path.home() / "Desktop" / "Obsidian"
    if desktop_obsidian.is_dir():
        candidates = [
            d for d in desktop_obsidian.iterdir()
            if d.is_dir() and (d / ".obsidian").is_dir()
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            return max(candidates, key=lambda p: (p / ".obsidian").stat().st_mtime)

    return None


# ---------------------------------------------------------------------------
# Artifact reading
# ---------------------------------------------------------------------------


def read_session_artifacts(operations_dir: Path, session_id: str) -> dict:
    """Read whatever exists in the session dir. Missing files are fine."""
    sess_dir = operations_dir / session_id
    out: dict = {
        "task": "",
        "synthesis": "",
        "cost_report": "",
        "spot_check": "",
        "cross_link": "",
        "gate_result": None,
        "agents": [],
        "session_dir": str(sess_dir),
    }
    if not sess_dir.is_dir():
        return out

    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    out["task"] = _read(sess_dir / "task.txt").strip()
    out["synthesis"] = _read(sess_dir / "synthesis.md")
    out["cost_report"] = _read(sess_dir / "cost-report.md")
    out["spot_check"] = _read(sess_dir / "spot-check.md")
    out["cross_link"] = _read(sess_dir / "cross-link.md")

    gate_path = sess_dir / "gate-result.json"
    if gate_path.is_file():
        try:
            out["gate_result"] = json.loads(gate_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    agents_dir = sess_dir / "agents"
    if agents_dir.is_dir():
        for j in sorted(agents_dir.glob("*.json")):
            try:
                out["agents"].append(json.loads(j.read_text(encoding="utf-8")))
            except Exception:
                continue

    return out


# ---------------------------------------------------------------------------
# Markdown composition
# ---------------------------------------------------------------------------


_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def slugify(text: str) -> str:
    s = _SLUG_RE.sub("-", text or "").strip("-").lower()
    return s or "unknown"


def _yaml_str(s: str) -> str:
    """Safely YAML-quote a string (single line). Trim and escape double quotes."""
    s = (s or "").replace("\n", " ").replace("\r", " ").strip()
    return '"' + s.replace('"', '\\"') + '"'


def _agent_summary(agent: dict, idx: int) -> tuple[str, str]:
    """Return (yaml_line, markdown_bullet) for one agent."""
    desc = (
        agent.get("description")
        or (agent.get("dispatch") or {}).get("description")
        or ""
    )[:120]
    model = (
        agent.get("model")
        or (agent.get("dispatch") or {}).get("model")
        or "?"
    )
    confidence = agent.get("confidence")
    if confidence is None:
        confidence = (agent.get("result") or {}).get("confidence")
    tokens = agent.get("tokens")
    if tokens is None:
        tokens = (agent.get("result") or {}).get("tokens", 0)

    conf_yaml = "null" if confidence is None else f"{float(confidence):.3f}"
    yaml_line = (
        f"  - {{ index: {idx}, model: {model}, "
        f"description: {_yaml_str(desc)}, "
        f"confidence: {conf_yaml}, tokens: {int(tokens or 0)} }}"
    )
    conf_str = ""
    if isinstance(confidence, (int, float)):
        conf_str = f" · {float(confidence):.2f}"
    md_bullet = f"- agent {idx} · model `{model}`{conf_str} · {desc}"
    return yaml_line, md_bullet


def compose_markdown(payload: dict, artifacts: dict) -> str:
    session_id = payload.get("session_id", "unknown")
    recipe = payload.get("recipe", "unknown")
    total_tokens = int(payload.get("total_tokens") or 0)
    wall_clock_s = float(payload.get("wall_clock_s") or 0)
    agents_count = int(payload.get("agents_count") or 0)

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    duration_min = round(wall_clock_s / 60.0, 2) if wall_clock_s else 0.0

    agent_yaml_lines: list[str] = []
    agent_md_lines: list[str] = []
    for i, ag in enumerate(artifacts["agents"], start=1):
        y, m = _agent_summary(ag, i)
        agent_yaml_lines.append(y)
        agent_md_lines.append(m)
    agents_yaml_block = "\n".join(agent_yaml_lines) if agent_yaml_lines else "  []"

    gate = artifacts.get("gate_result") or {}
    gate_pass = gate.get("pass") if isinstance(gate, dict) else None
    if gate_pass is True:
        gate_str = "pass"
    elif gate_pass is False:
        gate_str = "fail"
    else:
        gate_str = "n/a"

    task_text = artifacts["task"] or "(no task recorded)"
    task_summary = task_text.splitlines()[0][:140] if task_text else "(no task)"

    fm = (
        "---\n"
        f"recipe: {recipe}\n"
        f"session_id: {session_id}\n"
        f"date: {now_iso}\n"
        f"duration_min: {duration_min}\n"
        f"n_agents: {agents_count}\n"
        f"total_tokens: {total_tokens}\n"
        f"gate_result: {gate_str}\n"
        "agents:\n"
        f"{agents_yaml_block}\n"
        f"tags: [swarm-run, {slugify(recipe)}]\n"
        "---\n\n"
    )

    body_parts: list[str] = [f"# {task_summary}\n"]
    if artifacts["synthesis"]:
        body_parts.append("## Synthesis\n\n" + artifacts["synthesis"].strip() + "\n")
    if artifacts["cost_report"]:
        body_parts.append("## Cost\n\n" + artifacts["cost_report"].strip() + "\n")
    if agent_md_lines:
        body_parts.append("## Per-agent outputs\n\n" + "\n".join(agent_md_lines) + "\n")
    if artifacts["spot_check"]:
        body_parts.append("## Spot check\n\n" + artifacts["spot_check"].strip() + "\n")
    if artifacts["cross_link"]:
        body_parts.append("## Cross-link findings\n\n" + artifacts["cross_link"].strip() + "\n")
    body_parts.append(
        "## Raw artifacts\n\n"
        f"- Session dir: `{artifacts['session_dir']}` (transient — decays after TTL)\n"
    )
    return fm + "\n".join(body_parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        print("obsidian-emit: invalid JSON on stdin", file=sys.stderr)
        return 1

    session_id = payload.get("session_id")
    if not session_id:
        print("obsidian-emit: payload missing session_id, skipping", file=sys.stderr)
        return 0

    vault = resolve_vault_path()
    if vault is None:
        print("obsidian-emit: vault not configured, skipping", file=sys.stderr)
        return 0

    # Skill root: this file lives at <skill>/addons/_core/obsidian-emit/hooks/synthesis_done.py
    # parents[4] climbs hooks → obsidian-emit → _core → addons → skill root
    skill_dir = Path(__file__).resolve().parents[4]
    operations_dir = skill_dir / "memory" / "operations"
    artifacts = read_session_artifacts(operations_dir, session_id)

    md = compose_markdown(payload, artifacts)

    recipe_slug = slugify(payload.get("recipe", "unknown"))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    filename = f"{ts}-{recipe_slug}.md"

    out_dir = vault / "Skills" / "swarm-orchestrator" / "runs"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"obsidian-emit: cannot create output dir {out_dir}: {e}", file=sys.stderr)
        return 0

    out_path = out_dir / filename
    try:
        out_path.write_text(md, encoding="utf-8")
    except OSError as e:
        print(f"obsidian-emit: write failed {out_path}: {e}", file=sys.stderr)
        return 0

    print(f"obsidian-emit: wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
