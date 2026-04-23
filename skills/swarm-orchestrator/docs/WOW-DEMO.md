# Wow Demo — The Week Start Triage

A curated showcase swarm that exercises the full framework in under 5 minutes. Run this when you want to demo the stack to someone, smoke-test after changes, or legitimately need a prioritized week-start action list.

## What it does

Fires 5 muscle agents in parallel (mixed Haiku + Sonnet, safety tags `[L]` and `[M]`), then runs a Sonnet `[H]` reviewer sequentially on top. Produces a prioritized Top-5-actions-this-week list with adversarial critique of the muscle findings.

## The swarm shape

| # | Model | Safety | Scope |
|---|---|---|---|
| 1 | Haiku | `[L]` | Top-level loose files in `Ron's Brain/` |
| 2 | Haiku | `[L]` | Files added to `Downloads/` in the last 14 days |
| 3 | Sonnet | `[M]` | `MachineGuides/diagnoses/` + `guides/` pipeline status |
| 4 | Haiku | `[M]` | TODO/checkbox sweep across active projects |
| 5 | Sonnet | `[M]` | Git momentum across all active repos (last 7 days) |
| R | Sonnet | `[H]` | Adversarial reviewer — synthesis + Top 5 priorities |

Total: ~$0.80, ~4–5 min wall time, 6 agents visible on dashboard.

## Why these five

Each muscle covers one **dimension of weekly state**:

1. **What's actively being worked on** — recent loose files show what's in flight
2. **What's accumulating** — Downloads reveals what's being pulled in without triage
3. **What's in the pipeline** — diagnoses status shows incomplete/drift in the product
4. **What's open** — TODOs + checkboxes show commitments not yet closed
5. **What's shipping** — git momentum shows actual delivery vs planning

The reviewer synthesizes across dimensions to find the cross-cutting pattern no single muscle sees. This is the OpenClaw / Hermes hierarchical pattern in miniature.

## What makes it "wow"

- **Visible parallelism** — 5 cards light up on the dashboard at once, color-coded by model
- **Live tool traces** — you watch each muscle scan its scope in real time
- **Safety tags + confidence pills** — protocol metadata visible on every card
- **Sequential reviewer** — after the parallel swarm, the `[H]` reviewer card appears and runs adversarial synthesis
- **Genuinely useful output** — not a contrived demo; produces a real prioritized action list

## How to fire it

### Option A — Tell Claude in chat

> "fire the wow demo" — or — "run the week start triage"

Claude picks up the trigger, dispatches the 5 muscles in one message (parallel), waits for all to complete, spot-checks one claim, then fires the reviewer. Synthesis delivered inline.

### Option B — From the dashboard

Click **Launch Wow Demo** from the dashboard's recipe menu (when added). Dashboard POSTs to Flask → Flask spawns the swarm via subprocess. Not yet implemented in the default dashboard but sketched in the README under "Extending".

### Option C — From the launcher

`dashboard/wow-demo.bat` opens the dashboard in your browser and prints the trigger phrase, then opens your Claude Code CLI so you can paste it and go. Useful for pitch demos where you want the dashboard pre-loaded.

## Customizing the recipe

To adapt for other people's workloads, edit this doc and change:

- **Folder paths** in muscles 1, 2, 3, 4 to point at whoever's working directory
- **Active projects list** in muscle 5 to their repos
- **Reviewer context** — the persona sentence describing who the user is ("Ron is a welder/fabricator + co-CEO of a milling company") should be rewritten for the new user

The muscle prompts themselves are generic enough to transfer — the customization is purely paths + persona.

## When NOT to use this recipe

- You don't want an adversarial review. Some weeks you just want facts, not a critique. Skip the reviewer, run the 5 muscles only.
- You want deeper analysis on one dimension. Better to run a focused Sonnet deep-dive than a shallow multi-dimension swarm.
- You haven't done any work recently. The recipe will find little and look anticlimactic.

## Expected output shape

```
# Week Start Triage — Reviewer Synthesis

## Claims I doubt
[adversarial notes on muscle findings]

## What the swarm missed
[cross-section patterns only visible from combining reports]

## Top 5 actions for this week (prioritized)
1. [most urgent] — why, time estimate
2. ...

## Net state assessment
[one-paragraph honest read on Ron's working-environment state]
```

The Top 5 is the deliverable. Everything else is evidence.

## Running cost over time

Expected weekly cost if run every Monday morning:

- $0.80 per run × 52 weeks = **~$42/year** for a disciplined weekly triage
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
3. Spot-check 1 critical claim with a direct tool call (typically the security-tagged one, if any)
4. Dispatch reviewer with muscle outputs inlined
5. Present reviewer's synthesis to user — do NOT re-synthesize on top, it's already the deliverable

## History — the first wow demo run

The first run of this recipe (2026-04-23) found:

- Google OAuth credential exposed in Downloads (confirmed via orchestrator spot-check)
- Bobcat + Gehl SPN172 hypothesis trackers sharing identical content despite being physically different fleet machines (diagnostic integrity issue, not just data hygiene)
- MachineGuides + Ron's Brain both un-versioned (business risk for 18 JSON specs + hypothesis trackers)
- `rasar_*` files appearing suddenly in Ron's Brain with no scope declared — resource conflict with MachineGuides backfill work
- 122 open checkboxes across 5 active planning docs, low close-rate

Total cost of that run: ~$0.80. The OAuth finding alone paid for the next 50 runs.
