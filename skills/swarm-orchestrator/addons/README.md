# Addons

This directory holds **swarm-orchestrator addons** — modular extensions that contribute skills, recipes, templates, workflows, model-tier overrides, hooks, and docs to the core swarm-orchestrator skill without forking it.

## TL;DR

- **An addon is a folder.** Drop it in here (or under `~/.claude/swarm-orchestrator/addons/`, or your workspace `.swarm/addons/`) and it loads automatically.
- **Every addon has an `addon.yaml` manifest.** No manifest = ignored.
- **Every addon is independently versioned, enable-disable-able, and removable.**
- See `../docs/ADDONS.md` for the full design memo.

## Search order (later overrides earlier)

1. `<skill-dir>/addons/` ← you are here. Built-in addons live in `_core/`.
2. `~/.claude/swarm-orchestrator/addons/` — user-installed, machine-local.
3. `<workspace>/.swarm/addons/` — project-scoped overrides.

## Built-in addons (`_core/`)

| Addon | Purpose | Triggers (sample) |
|---|---|---|
| `auto-adapter` | Read a target repo, learn its workflow, generate a fresh addon that captures it. The "tell the swarm to adapt to a new domain" capability. | "adapt to X", "learn this repo", "build addon for X", "תלמדי את X", "תתאימי ל-X" |

More built-ins may land later. User-installed addons live outside this directory so they survive `git pull` of the skill repo.

## Quick-start: author your first addon

```
mkdir ~/.claude/swarm-orchestrator/addons/my-first-addon
cd ~/.claude/swarm-orchestrator/addons/my-first-addon

cat > addon.yaml <<'YAML'
name: my-first-addon
version: 0.1.0
description: My first swarm-orchestrator addon.
swarm_orchestrator_min: ">=2.0.0"
provides:
  recipes:
    - recipes/hello.yaml
YAML

mkdir recipes
cat > recipes/hello.yaml <<'YAML'
name: hello
description: A trivial greeting recipe to verify the addon loaded.
agents:
  - tier: haiku
    safety: L
    template: "Say hello in the user's language. Nothing else."
YAML
```

Then in any session running the swarm-orchestrator skill:

```
/swarm-addons doctor
/swarm-addons list
```

Your addon should appear with `status: enabled` and `provides.recipes: 1`.

## Auto-generating an addon from a target repo

The fastest path to a useful addon is to let the swarm read a repo and generate one for you:

```
/swarm-addons learn ~/Desktop/MachineGuides
```

or natural-language:

> *"adapt to ~/Desktop/MachineGuides"*
> *"תלמדי את MachineGuides ותבני addon"*
> *"build me an addon for the MachineGuides workflow"*

The orchestrator dispatches a 4-agent + 1-reviewer learning swarm (see `_core/auto-adapter/`), drafts the addon under `~/.claude/swarm-orchestrator/addons/<repo-name>-bundle/`, runs doctor, and reports. You then review the draft and toggle it to `status: enabled`.

## Distribution

Addons are plain folders. Distribute via:
- **GitHub** — `git clone <url> ~/.claude/swarm-orchestrator/addons/<name>/`.
- **Tarball** — `tar -xzf my-addon.tar.gz -C ~/.claude/swarm-orchestrator/addons/`.
- **Symlink/junction** — for cross-machine sync (Ron's pattern across PC + laptop via `claude-skills` repo).

## Intentional limits

Addons can extend, not subvert. They cannot disable core protocol rules, bypass the synthesis quality gate, or modify the dashboard's Flask app. See `../docs/ADDONS.md` § "What addons cannot do".
