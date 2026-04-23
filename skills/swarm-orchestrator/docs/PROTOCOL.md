# Protocol — The 5 Mitigations

The framework's failure mode is **confident-shallow output**: a muscle at the wrong tier returns a plausible-looking report that the orchestrator merges into a polished-looking synthesis which hides the thinness. Five mitigations, layered by stakes, close that gap.

## Mitigation summary

| # | Name | Cost added | Time added | Blocks parallel? | When |
|---|---|---|---|---|---|
| 1 | Reviewer loop | +$0.15–0.50 | +1–2 min tail | no | `[H]` only |
| 2 | Escalation protocol | +0 baseline, +$0.05–0.15 on trigger | +30–60s when fires | no | `[M]` and `[H]` |
| 3 | Spot-check verification | +$0.02/agent | +20–40s | no | `[M]` and `[H]` |
| 4 | Model-match discipline | 0 | 0 | no | **always** |
| 5 | Typed outputs + confidence | ~0 | 0 | no | **always** |

## #4 — Model-match discipline (always on, the foundation)

Before dispatching, the orchestrator picks the tier based on task shape — never out of habit, never out of cost-consciousness alone. Rule: **if in doubt, default up a tier.**

See `MODEL-TIERS.md` for the decision table.

This mitigation is **$0** — it's pure discipline. But it's the single highest-leverage practice. The other four mitigations are bandages if you skip this one.

## #5 — Typed outputs + confidence (always on, enforceable)

Every muscle prompt ends with this exact contract:

```
At the end of your report, emit a metadata block:

---META---
confidence: 0.XX          # your confidence this report is accurate (0.0–1.0)
method: "..."             # how you gathered the data
not_checked: [...]        # things you couldn't verify
sample_size: N or "exhaustive"
---END META---
```

The orchestrator's post-swarm parser extracts these fields. The dashboard displays confidence as a colored pill. Low confidence triggers #2 (escalation).

**Why this is close to free:** the META block costs ~50 output tokens per muscle. The upside is massive — you now have structured metadata on every result, parseable, displayable, trigger-able.

## #2 — Escalation protocol (on for `[M]` and `[H]`)

After each muscle returns, the orchestrator parses its META block:

```
if muscle.confidence < 0.7:
    re-dispatch same prompt on Sonnet
    link the two cards in the dashboard (escalation arrow)

if muscle.confidence < 0.5:
    in addition to above, flag ALL findings as unverified in synthesis
```

The re-dispatch is silent (no user interruption). The dashboard shows the arrow from Haiku → Sonnet so you know it happened.

Also escalate if:

- `not_checked` contains something critical to the ask
- Numbers don't sanity-check (unit errors, impossible counts)
- Muscle returned "no findings" when the orchestrator expected findings

## #3 — Spot-check verification (on for `[M]` and `[H]`)

After the swarm completes and before synthesis, the orchestrator picks **3 specific claims** spread across the reports and verifies each with its own tool call:

- A claim like "76% of images are orphaned" → grep for 5 image filenames from the report, check if they actually appear in the referenced folder
- A claim like "file X is 150 MB" → `ls -lh` on file X, compare
- A claim like "schema has drifted between v3 and v5" → read both files, diff the top-level keys

If a spot-check fails: flag the finding as **unverified** in synthesis, note the spot-check in a caveat section. Do not silently accept or silently discard.

This costs ~3–9 extra orchestrator tool calls per swarm. Catches fabrication, unit errors, and confident-wrong claims. Costs ~$0.02 per agent.

## #1 — Reviewer loop (on for `[H]` only)

After the swarm and spot-checks, dispatch a **reviewer agent** — Sonnet for most [H] cases, Opus when the decision is really expensive. The reviewer gets:

1. All the muscle reports, inline
2. A list of 3–5 raw files the muscles read but the orchestrator never saw
3. An adversarial mandate: *"Your job is NOT to redo their work. Find what they missed. Find what looks shallow. Find what nuance was lost in typed-output compression."*

See `templates/reviewer.md` for the full prompt shape.

The reviewer produces:

- Claims it doubts, with reasoning
- Things the muscles didn't notice but should have
- Cross-section patterns only visible from seeing everything
- Its revised version of the top 3 findings

Reviewer output goes into its own dashboard card, visually linked to the swarm. The orchestrator incorporates reviewer findings into the final synthesis, prefixing any reviewer-flagged concerns with "Reviewer flagged:".

## Safety tag → mitigation layering

| Safety tag | #4 Model-match | #5 Typed outputs | #2 Escalation | #3 Spot-check | #1 Reviewer |
|---|---|---|---|---|---|
| `[L]` low-stakes | ✅ | ✅ | ⬜ | ⬜ | ⬜ |
| `[M]` medium-stakes | ✅ | ✅ | ✅ | ✅ | ⬜ |
| `[H]` high-stakes | ✅ | ✅ | ✅ | ✅ | ✅ |

The tag goes in the description prefix: `[M] Audit MachineGuides diagnoses/`.

The dashboard parses the prefix and renders a colored safety pill.

## Cost summary

For a 5-Haiku swarm baseline of ~$1.80 / 7 min:

| Safety | Added | New total | Reason |
|---|---|---|---|
| `[L]` | — | $1.80 / 7 min | Defaults only |
| `[M]` | +$0.20 / +2 min | $2.00 / 9 min | Escalation + spot-check |
| `[H]` | +$0.50 / +3 min | $2.30 / 10 min | + reviewer |

Trivial premium for catching confident-wrong output. Always worth it when the swarm drives a real decision.

## What this protocol does NOT fix

- **Latency on very small swarms.** For 2–3 muscle work, the reviewer + spot-check tail dominates. Use single-agent.
- **Tasks that genuinely need cross-muscle debate.** The reviewer partially fixes this but debate-like synthesis is better done by a single agent with full context.
- **Domain knowledge the muscles don't have.** If every muscle and the reviewer all lack context X, no protocol catches X. Give the orchestrator relevant memory/context before dispatching.
- **User-in-the-loop judgment.** When a decision really needs the user's domain input, don't auto-synthesize — pause and ask.

## Implementation checklist

- [ ] Dispatch template ends with META contract every time
- [ ] Description prefixed with `[L]` / `[M]` / `[H]`
- [ ] Explicit exclusion list in prompt so muscles don't trample each other
- [ ] After swarm: iterate muscles, parse META, escalate any `confidence < 0.7`
- [ ] For `[M]` and `[H]`: pick 3 claims total, spot-check
- [ ] For `[H]` only: dispatch reviewer with adversarial mandate
- [ ] Synthesize: flag unverified findings, never oversell
