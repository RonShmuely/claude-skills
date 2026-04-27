# Wow Demo — Showcase Swarm

A curated showcase swarm that exercises the full framework in under 5 minutes. Run this when you want to demo the stack to someone, smoke-test after changes, or get a real prioritized action list out of an existing workspace.

## What it does

Fires 5 muscle agents in parallel (mixed Haiku + Sonnet, safety tags `[L]` and `[M]`), then runs a Sonnet `[H]` reviewer sequentially on top. Produces a synthesized report with adversarial critique of the muscle findings.

## The swarm shape

| # | Model | Safety | Generic task |
|---|---|---|---|
| 1 | Haiku | `[L]` | Inventory loose files at the top of a project tree |
| 2 | Haiku | `[L]` | Count file types in a documentation directory |
| 3 | Sonnet | `[M]` | Audit pipeline status in a content-generation directory |
| 4 | Sonnet | `[M]` | Cross-check naming consistency across N similar artifacts |
| 5 | Sonnet | `[H]` | Synthesize freshness/scope/risk findings into one report |
| R | Opus  | adversarial | Re-read all child outputs + sample raw files |

Total: ~$0.80, ~4–5 min wall time, 6 agents visible on dashboard.

## Why these five

Each muscle covers one **dimension of workspace state**:

1. **What's loose** — top-level files reveal what's in flight or un-filed
2. **What's accumulating** — file-type counts in docs reveal drift in shape
3. **What's in the pipeline** — content-pipeline status shows incomplete or stale work
4. **What's inconsistent** — naming sweep across similar artifacts catches integrity issues
5. **What's the net read** — synthesis muscle compresses the other four into one risk picture

The reviewer synthesizes across dimensions to find the cross-cutting pattern no single muscle sees. This is the hierarchical decomposition pattern in miniature.

## What makes it "wow"

- **Visible parallelism** — 5 cards light up on the dashboard at once, color-coded by model
- **Live tool traces** — you watch each muscle scan its scope in real time
- **Safety tags + confidence pills** — protocol metadata visible on every card
- **Sequential reviewer** — after the parallel swarm, the `[H]` reviewer card appears and runs adversarial synthesis
- **Genuinely useful output** — not a contrived demo; produces a real prioritized action list against your own workspace

## How to fire it

### Option A — Tell Claude in chat

> "fire the wow demo" — or — "run the showcase swarm"

Claude picks up the trigger, dispatches the 5 muscles in one message (parallel), waits for all to complete, spot-checks one claim, then fires the reviewer. Synthesis delivered inline.

### Option B — From the dashboard

Click **Launch Wow Demo** from the dashboard's recipe menu (when added). Dashboard POSTs to Flask → Flask spawns the swarm via subprocess. Not yet implemented in the default dashboard but sketched in the README under "Extending".

### Option C — From the launcher

`dashboard/wow-demo.bat` opens the dashboard in your browser and prints the trigger phrase, then opens your Claude Code CLI so you can paste it and go. Useful for pitch demos where you want the dashboard pre-loaded.

## How to adapt this to your own setup

The swarm is templated — point each agent at your own paths and it works:

- **Muscle 1 (loose-file inventory):** point at `<your project>` root. Looks for files that appear un-filed (top-level scratch, screenshots, half-named docs). Returns a categorized list.
- **Muscle 2 (doc-folder type counts):** point at `<your docs folder>`. Returns extension/category counts and flags any sudden new file types as drift signals.
- **Muscle 3 (content-pipeline audit):** point at `<your content pipeline>` (e.g. a `guides/`, `posts/`, `reports/` directory). Returns per-stage counts: drafted, reviewed, published, stale.
- **Muscle 4 (naming-consistency cross-check):** point at a directory of N similar artifacts (specs, configs, templates). Returns mismatched-naming pairs and any artifacts whose content looks duplicated despite being named differently.
- **Muscle 5 (synthesis):** consumes the META blocks of muscles 1–4 and outputs a freshness/scope/risk read. No new tool calls — pure reasoning over the children.

The muscle prompts themselves are generic — only the paths and the reviewer's context sentence (what kind of operator you are, what you care about) need to change.

## When NOT to use this recipe

- You don't want an adversarial review. Some weeks you just want facts, not a critique. Skip the reviewer, run the 5 muscles only.
- You want deeper analysis on one dimension. Better to run a focused Sonnet deep-dive than a shallow multi-dimension swarm.
- The workspace is too quiet. The recipe will find little and look anticlimactic if no real work has happened recently.

## Expected output shape

Each muscle emits a META block that the orchestrator parses:

```
---META---
agent_id: muscle-3
model: sonnet
safety: M
confidence: 0.82
findings:
  - id: f1
    summary: "<short claim>"
    evidence: "<paths or counts>"
not_checked:
  - "<scope explicitly skipped>"
---END META---
```

The reviewer then produces:

```
# Showcase Swarm — Reviewer Synthesis

## Claims I doubt
[adversarial notes on muscle findings, with evidence sampled directly]

## What the swarm missed
[cross-section patterns only visible from combining reports]

## Top actions (prioritized)
1. [most urgent] — why, time estimate
2. ...

## Net state assessment
[one-paragraph honest read on workspace state]
```

The prioritized action list is the deliverable. Everything else is evidence.

## Running cost over time

Expected cost per run if used as a regular weekly triage:

- $0.80 per run × 52 weeks = **~$42/year** for a disciplined weekly pass
- Compare: the same quality review from a human consultant starts at $200/hr

The cost only goes up if you:
- Upgrade muscles 3 and 5 to Opus (rarely needed)
- Upgrade the reviewer to Opus (warranted if the triage drives ≥$5K decisions)
- Add more muscles to cover more dimensions

## Implementation notes

### Dispatch template

Each muscle follows the standard dispatch template from `templates/audit.md`, with three project-specific hooks:

1. Safety tag prefix: `[L]` for informational scopes, `[M]` for decision-driving
2. Deliverable shape: matches the per-muscle bullets in the table above
3. META block contract: every muscle MUST emit the footer

The reviewer follows `templates/reviewer.md` with all 5 muscle reports inlined and an explicit "be adversarial" mandate.

### Orchestrator behavior after swarm

1. Parse all 5 META blocks
2. Escalate any muscle with `confidence < 0.7` (silent re-dispatch to Sonnet)
3. Spot-check 1 critical claim with a direct tool call (typically the highest-safety-tag finding)
4. Dispatch reviewer with muscle outputs inlined
5. Present reviewer's synthesis to user — do NOT re-synthesize on top, it's already the deliverable
