# Template — Spot-Check Artifact

The spot-check artifact is **mandatory** for `[M]` and `[H]` swarms when `discipline.spot_check_enforce: true` (the default). It must appear before final synthesis. If you decided not to run any verifications, the artifact must STILL appear with `Picked: 0` and an explicit reason — so the user can see the orchestrator considered the step.

## When to emit

- `[M]` and `[H]` safety-tagged swarms — always
- `[L]` swarms — skip
- Any setting `discipline.spot_check_enforce: false` — skip

## Artifact format

```markdown
## Spot-check report

Picked: 3 claims across reports {A, C, F}

- **Claim 1** (from Agent A, Lightning):
  > "Agent Lightning v0.3.0 released Dec 2024"
  Verified via WebFetch of GitHub releases page.
  Result: ✓ verified

- **Claim 2** (from Agent C, CLI compare):
  > "Gemini CLI cold start 20–50s on Windows"
  Verified via WebFetch of GitHub Issue #21853.
  Result: ✓ verified

- **Claim 3** (from Agent F, latency):
  > "NotebookLM p99 query latency 15–30s"
  Source: vague community report; could not independently confirm.
  Result: ⚠ flagged — synthesis will mark this as "estimate, not benchmarked"

Outcome: 2/3 verified, 1 flagged. No re-dispatch triggered.
```

## How to pick the 3 claims

Pick claims that:

1. **Drive a recommendation in the synthesis.** A claim that affects the user's next action is worth verifying.
2. **Span multiple agents.** Don't pick all 3 from one report — distribute the check across the swarm.
3. **Are checkable in <60 seconds.** A version number is checkable. "The vibe of the codebase" is not.
4. **Have a specific factual shape.** Numbers, dates, version strings, file paths, claim of presence/absence.

Avoid:
- Claims already verified with citations in the agent's report
- Claims marked in the agent's `not_checked` list (they're already flagged)
- Subjective claims ("this is the best library")
- Claims that would require running the swarm task again (you're not redoing the work)

## Tools to use

- **`WebFetch`** for URLs cited
- **`Read`** for file paths cited
- **`Grep`** for "X exists in codebase Y" claims
- **`Bash`** (sparingly) for fact-checks against external CLIs

## When all confidences are high

If every agent returned `confidence >= 0.85`, you may legitimately skip verification and emit:

```markdown
## Spot-check report

Picked: 0 (all reports above spot-check threshold of 0.85)
Confidences observed: A=0.92, B=0.88, C=0.91, D=0.89

Outcome: skipped per high-confidence threshold. Orchestrator considered this step but found no claims requiring verification.
```

This is acceptable. The artifact MUST appear so the user knows the orchestrator made the decision deliberately.

## When a spot-check fails

If a verification fails:

1. **Mark the agent's claim as unverified in the synthesis.** Use a footnote or inline caveat: "(spot-check failed — see report)".
2. **Drop the agent's confidence in your synthesis.** Even if the agent claimed 0.9, treat as ≤0.6 for purposes of "what to highlight".
3. **Trigger the dynamic reviewer (Patch 5)** if anomaly thresholds are configured to do so.

## Where it lives

The artifact is written to `memory/operations/<session-id>/spot-check.md` so it persists for retrieval and audit. It also appears inline above the final synthesis when `output.cost_report: "full"` (or always, if you want it visible).

## Cost

Per spot-check verification: 1–3 tool calls, ~5–30 seconds, ~$0.02 in API equivalent. For 3 checks: ~$0.06 + ~30–90 seconds. Trivial vs the cost of acting on a confident-wrong claim.
