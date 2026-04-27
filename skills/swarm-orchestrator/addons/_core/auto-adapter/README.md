# auto-adapter

> Read a target repo, learn its workflow, generate a swarm-orchestrator addon that captures it.

This is the built-in "tell the swarm to adapt to a new domain" capability. It is itself an addon (eats its own dogfood) and ships in `addons/_core/`.

## What it does

You point the swarm at a repo. The swarm:

1. **Inventories** the repo (Sonnet, low-stakes) — structure, conventions, file types, build commands, existing AI rules.
2. **Extracts the workflow** (Sonnet, medium-stakes) — the recurring pipeline that produces the repo's main artifact.
3. **Synthesizes the skill set** (Sonnet, medium-stakes) — proposes modular skills with frontmatter triggers in the user's language.
4. **Synthesizes the addon** (Opus, high-stakes, only writer in the recipe) — writes manifest + skills + recipes + workflows + README to a draft addon folder.
5. **Doctors the result** (Opus, high-stakes, read-only) — validates manifest, checks file references, flags conflicts.

You then review the draft and run `/swarm-addons enable <name>` to adopt it. Generated addons ship `status: disabled` by default — the user explicitly opts in after review.

## Triggers

The orchestrator invokes this addon's `learn-repo` recipe on these triggers:

**English:**
- *"adapt to ~/Desktop/MachineGuides"*
- *"learn this repo: <path>"*
- *"build me an addon for <path>"*
- *"onboard <path> into the swarm"*
- `/swarm-addons learn <path>`

**Hebrew:**
- *"תלמדי את ~/Desktop/MachineGuides"*
- *"תתאימי ל-MachineGuides"*
- *"תבני אדאון ל-MachineGuides"*
- *"תאמצי את MachineGuides"*

The trigger captures the path with a regex named-group `<repo>`. Quote it with quotes if it contains spaces.

## Example: adapting to MachineGuides

```
You: תלמדי את ~/Desktop/MachineGuides

Swarm:
  Confirm: I will dispatch 4 muscles + 1 reviewer to read MachineGuides and
  generate an addon at ~/.claude/swarm-orchestrator/addons/machineguides-bundle/.
  Estimated: ~2 min wall-clock, ~5K tokens. אישור?

You: כן

Swarm: [dispatches the 5-agent learn-repo recipe via the dashboard]

  ## הסוכן למד את MachineGuides ✓

  Generated addon at: ~/.claude/swarm-orchestrator/addons/machineguides-bundle/

  Skills added: 5
    - diagnose-fault — fault diagnosis via NotebookLM
    - build-guide — render JSON payload via build_generic_guide.py (NEVER hand-author HTML)
    - approve-diagnosis — flip v1 → v3_approved after field validation
    - archive-old-version — move deprecated guides to _archive/<date>/
    - search-mkat — look up part numbers in the מק"ט database

  Recipes added: 2
    - render-fault-guide (haiku→sonnet→opus chain)
    - field-validation-loop

  Workflows added: 3
    - /diagnose <machine> <symptom>
    - /approve <fault-slug>
    - /archive <fault-slug>

  Locked rules imported (verbatim from source repo):
  - "Real guides go through build_generic_guide.py; mockups allowed in
     guides/_mockups/ with banner"
  - "No invented percentages/confidence/statistics; derive from documented weights only"
  - "Cleanup moves to _archive/<date>_<reason>/; never rm/Remove-Item on guides or diagnoses"
  - "All labels/chips/section titles in Hebrew; Latin only for technical identifiers"

  TODOs left for review:
  - [ ] Confirm `Wirtgen W200i מקרצפת גדולה` notebook ID is the right default for milling diagnoses
  - [ ] Decide whether `field-validation-loop` should auto-promote on Bobcat (inventory found 2 fault histories on the same SPN)

  Doctor verdict: PASS (1 warning: `archive-old-version` skill shares trigger "ארכיון" with no other skill currently — clean).

  Status: status: disabled (per safety gate). To enable: /swarm-addons enable machineguides-bundle
```

After enabling, the orchestrator natively dispatches MachineGuides work: any user message matching the new triggers loads the right skill, applies the locked rules, and routes through the right model tier per the recipe — without you ever editing the swarm core.

## Why this addon ships in `_core/`

It is the "addons of addons" — the bootstrap. Without it, every new domain integration would mean hand-authoring an addon. With it, the user says one sentence and the swarm produces a draft.

It is intentionally `priority: 80` so its triggers fire before any user-installed addon that might also claim "learn" / "adapt" keywords.

## Contents

| File | Purpose |
|---|---|
| `addon.yaml` | Manifest + triggers |
| `recipes/learn-repo.yaml` | The 5-agent recipe (3 inventory/extraction + 1 synthesis + 1 doctor) |
| `templates/repo-inventory.md` | Agent 1 prompt — read repo top-down |
| `templates/workflow-extraction.md` | Agent 2 prompt — identify the recurring pipeline |
| `templates/domain-skills-synthesis.md` | Agent 3 prompt — propose the skill set |
| `templates/addon-synthesis.md` | Agent 4 prompt (Opus, sole writer) — emit files |
| `templates/addon-doctor.md` | Agent 5 prompt — validate the result |
| `README.md` | This file |

## Limits

- One repo per invocation. Multi-repo or monorepo onboarding is a planned recipe (`learn-monorepo`), not v1.
- Generated addons are starting points, not finished products. The doctor catches structural issues; semantic correctness is the user's review.
- Doesn't auto-pull `git`. If the target repo isn't on disk, the user clones it first.
- Won't overwrite an existing `<repo-name>-bundle` addon. The synthesis muscle errors if the output dir is non-empty. Run `/swarm-addons remove <name>` first or pass an alternate output dir.

## Future extensions

- `learn-monorepo` — handle workspaces with multiple distinct sub-projects.
- `update-addon` — re-run inventory + workflow extraction against an already-adopted repo and emit a diff for the user to merge.
- `cross-link-addons` — find shared rules across N adopted repos and propose a base addon they could all extend (DRY for personal swarm policies).
