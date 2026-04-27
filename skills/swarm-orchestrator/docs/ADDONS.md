# Addons & Extensions

Addons let you graft new skills, recipes, templates, workflows, model-tier overrides, hooks, and docs onto the swarm-orchestrator without forking the skill. The core skill stays small and stable; everything domain-specific (Hebrew CMS workflows, Telegram dispatch, domain-specific reviewers, …) lives in addons.

## Why addons

The core skill teaches: **decompose, dispatch, verify, synthesize, persist.** That's universal. But every real workflow brings domain-specific knowledge — Hebrew confirmation gates, Wix MCP capabilities, machine-fault diagnostic recipes, Telegram-bot input adapters. Baking those into the core skill bloats it. Addons keep them modular and toggleable.

The user-facing rule: **a skill should ship the discipline; addons ship the domain.**

## What an addon can contribute

| Slot | Purpose | File location inside addon |
|---|---|---|
| Skills | Loadable capability modules with frontmatter triggers (per the personality-vs-skills split) | `skills/*.md` |
| Recipes | Named swarm patterns with tool-use floors and dispatch templates | `recipes/*.yaml` |
| Templates | Prompt shapes (inventory, audit, reviewer, custom) | `templates/*.md` |
| Workflows | User-facing `/shortcuts` (e.g., `/update-event` Hebrew flow) | `workflows/*.md` |
| Model-tier overrides | Per-capability model lists, useful for runtime-specific routing | `model-tiers-overrides.yaml` |
| Hooks | Scripts that run on lifecycle events (`dispatch_start`, `synthesis_done`, etc.) | `hooks/*.py` or `hooks/*.sh` |
| Docs | Markdown documentation surfaced in the skill's docs index | `docs/*.md` |

An addon does not have to use every slot. A "single recipe" addon is valid — just a manifest plus one `recipes/x.yaml`.

## Where addons live (search order)

The loader scans these paths, in order. **Later paths override earlier ones** for same-named contributions.

1. `<skill-dir>/addons/` — built-in / shipped with the skill (e.g., `_core`).
2. `~/.claude/swarm-orchestrator/addons/` — user-installed, machine-local.
3. `<workspace>/.swarm/addons/` — project-scoped overrides (only loaded when working inside that workspace).

Conflict rule: project-scoped > user-local > built-in. A built-in `recipe.yaml` named `wix-update` will be transparently overridden if a project-scoped addon defines another `wix-update`.

## Manifest schema (`addon.yaml`)

Every addon folder contains exactly one `addon.yaml`. Without it, the folder is ignored.

```yaml
# REQUIRED
name: hive-bundle                       # unique within the load order; kebab-case
version: 1.0.0                          # semver
description: 7-skill bundle for a Hebrew-first user-tier workflow + voice-dispatch.
swarm_orchestrator_min: ">=2.0.0"       # min skill version this addon supports

# OPTIONAL
author: <your name>
status: enabled                         # enabled (default) | disabled
tags: [hebrew, wix, voice-dispatch]
requires: []                            # other addon names that must also be enabled
priority: 50                            # 0–100; higher wins on conflict (default 50)

# CONTRIBUTIONS — every key under `provides` is optional
provides:
  skills:
    - skills/wix-updater.md
    - skills/content-writer.md
  recipes:
    - recipes/hebrew-wix-update.yaml
    - recipes/voice-dispatch.yaml
  templates:
    - templates/hebrew-confirm.md
  workflows:
    - workflows/update-event.md
  model_tiers_overrides: model-tiers-overrides.yaml
  hooks:
    - on: dispatch_start
      run: hooks/log-hebrew-trigger.py
    - on: synthesis_done
      run: hooks/notify-slack.sh
  docs:
    - docs/HIVE-BUNDLE.md
```

### Required keys
- `name` — unique identifier in the load order.
- `version` — semver, used in conflict messages.
- `description` — one line shown in `/swarm-addons list`.
- `swarm_orchestrator_min` — guards against loading on an incompatible skill version.

### Optional keys
- `status` — flip to `disabled` to skip the addon without removing it. User can override per addon via settings.
- `requires` — list of other addon names. If any required addon is disabled or missing, this one stays inert (logged once).
- `priority` — tie-breaker on conflicts. Higher wins. Same priority → alphabetical.
- `provides.*` — the actual contributions; see slot table above.

## Folder layout of a typical addon

```
addons/hive-bundle/
├── addon.yaml                      # manifest (required)
├── README.md                       # human-readable intro (optional)
├── skills/
│   ├── wix-updater.md
│   └── content-writer.md
├── recipes/
│   ├── hebrew-wix-update.yaml
│   └── voice-dispatch.yaml
├── templates/
│   └── hebrew-confirm.md
├── workflows/
│   └── update-event.md
├── model-tiers-overrides.yaml
├── hooks/
│   ├── log-hebrew-trigger.py
│   └── notify-slack.sh
└── docs/
    └── HIVE-BUNDLE.md
```

## Hook events

Hooks fire on lifecycle events with a JSON context piped to stdin. They run in a subprocess; they cannot mutate the swarm's in-memory state.

| Event | Stdin context | When |
|---|---|---|
| `dispatch_start` | `{ session_id, agent_id, model, safety, prompt_summary }` | Just before each muscle dispatch |
| `agent_returned` | `{ session_id, agent_id, model, confidence, tools_used, anomaly }` | When a muscle returns |
| `synthesis_done` | `{ session_id, total_tokens, wall_clock_s, agents_count, recipe }` | After Step 6 of the lifecycle |
| `gate_failed` | `{ session_id, failures: [...] }` | Synthesis quality gate hard-block |
| `cost_report` | `{ session_id, total_cost_usd, per_agent: [...] }` | After Step 7 |

Hook scripts must exit 0 to be considered successful. A non-zero exit logs a warning but does not fail the swarm.

## Loader API (`lib/addons.py`)

The loader is small, ~200 lines. Public surface:

```python
from lib.addons import load_addons, AddonRegistry

registry: AddonRegistry = load_addons(settings)

# Query
registry.list()                              # → [Addon, ...] in load order
registry.get("hive-bundle")                  # → Addon | None
registry.find_skill_by_trigger("תעדכני")     # → Skill | None
registry.find_recipe("hebrew-wix-update")    # → Recipe | None
registry.apply_model_tier_overrides(base)    # → merged tier map

# Lifecycle
registry.run_hooks("dispatch_start", ctx)    # fires all matching hooks, parallel-safe
```

The orchestrator calls `load_addons()` once at session start and then queries the registry as it dispatches. Hooks are fire-and-forget; the swarm doesn't wait on them.

## Settings (`defaults.json` → `addons`)

```json
"addons": {
  "auto_discovery": true,
  "search_paths": [
    "<skill-dir>/addons",
    "~/.claude/swarm-orchestrator/addons",
    "<workspace>/.swarm/addons"
  ],
  "disabled": [],
  "priority_overrides": {}
}
```

- `auto_discovery` — when false, only addons listed in `priority_overrides` keys load. Default true.
- `search_paths` — ordered; later paths override earlier ones. Tokens (`<skill-dir>`, `<workspace>`) are resolved at load time.
- `disabled` — addon names to skip even if `status: enabled` in their manifest.
- `priority_overrides` — `{ "addon-name": 80 }` to bump or demote priorities without editing the manifest.

User-level overrides live at `~/.claude/swarm-orchestrator/settings.json`.

## `/swarm-addons` slash commands

Run inside any session where the swarm-orchestrator skill is active. The orchestrator parses these directly (no separate command file needed in v1).

| Command | Effect |
|---|---|
| `/swarm-addons list` | Show all discovered addons with status, version, priority, contribution counts |
| `/swarm-addons info <name>` | Manifest summary + file list |
| `/swarm-addons enable <name>` | Set `disabled` settings entry false; reload registry |
| `/swarm-addons disable <name>` | Add to `disabled`; reload registry |
| `/swarm-addons doctor` | Validate every manifest, report missing files, version mismatches, hook syntax errors |
| `/swarm-addons install <source>` | `<source>` = local path, git URL, or `git+ssh://…`. Clones into `~/.claude/swarm-orchestrator/addons/<name>/`, runs doctor, reports. **No code execution beyond `git clone`** — no `npm install` or `pip install` runs automatically. |
| `/swarm-addons remove <name>` | Move addon dir to `~/.claude/swarm-orchestrator/addons/_archive/<ts>_<name>/`. Never `rm -rf`. |

## Compatibility rules

- A built-in skill recipe named `audit` and an addon recipe named `audit` are merged: addon wins by priority. The orchestrator logs the override at info level.
- Addons cannot replace `defaults.json`; they can only contribute additive overrides through `model_tiers_overrides`.
- Addons cannot mutate the core protocol (the 9 mitigations, the META block, the synthesis gate). They can add hooks around them.
- An addon that requires a missing addon stays inert; it is not partially loaded.

## Versioning addons

Each addon has its own semver. Bump `version` on every published change. The `swarm_orchestrator_min` field declares the lowest skill version compatible. Mismatch is a doctor warning, not a hard block — you can force-load with `/swarm-addons enable <name> --force` (records a `force_loaded: true` metadata field, surfaces in UI).

## Authoring a new addon (5 steps)

1. `mkdir ~/.claude/swarm-orchestrator/addons/my-addon/` (or wherever your search path puts user addons).
2. Write `addon.yaml` per the schema above. Start with one `provides` slot.
3. Add the contribution files (a recipe, a template, etc.).
4. Run `/swarm-addons doctor` — fix any errors it reports.
5. Run `/swarm-addons list` — verify it loaded with the right priority and contributions.

## Distribution

Addons are plain folders. Distribute via:
- **GitHub** — `git clone` into the addons dir. Recommended for community addons.
- **Tarball** — `tar -xzf my-addon.tar.gz -C ~/.claude/swarm-orchestrator/addons/`. Useful for private bundles.
- **Symlink/junction** — point one source-of-truth folder into multiple skill installs (a multi-machine sync pattern).

There is no central addon registry yet. The skill's main repo maintains a curated list in `docs/ADDONS-REGISTRY.md` (planned, not built).

## What addons cannot do (intentional limits)

- Cannot disable core skill rules.
- Cannot bypass the synthesis quality gate.
- Cannot register tools the core skill rejects (e.g., a hook can call `curl` but cannot teach the orchestrator to issue an `eval()` of arbitrary user input).
- Cannot read other addons' private data (each addon's `data/` subfolder is its own).
- Cannot modify the dashboard's Flask app — they can only emit JSON events to a watched hook directory.

These constraints keep addons safe to install from third parties while still being expressive.

## See also

- `addons/README.md` — quick start.
- `addons/hive-bundle/` — reference addon (skills + recipes + workflows + hooks).
- `lib/addons.py` — the loader implementation.
- `docs/MEMORY-TIERS.md` — addons can write to `memory/knowledge/` to persist learnings, scoped by addon name.
