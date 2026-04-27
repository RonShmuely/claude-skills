# Template — Synthesis Quality Gate

The synthesis gate is the **capstone** patch. It runs as a silent self-check before the orchestrator publishes the final synthesis to the user. The OUTCOME of the check appears in the cost report; if any check fails, synthesis is blocked or flagged until the issue is addressed.

## When it runs

After all of the following are complete (or skipped per settings):

1. All agent META blocks parsed
2. Re-escalation pass complete
3. Spot-check artifact emitted (Patch 3)
4. Cross-link review pass complete (Patch 4)
5. Reviewer dispatched if triggered (Patch 5)
6. Cost report computed (Patch 6)
7. Memory promotion ready (Patch 10)

Then — and only then — the gate runs.

## The 8 checks

| # | Check | Pass criterion | Action on fail |
|---|---|---|---|
| 1 | **All META blocks parsed** | Every agent in the swarm has a parsed META object with confidence + tools_used | Re-dispatch any agent whose META is missing/malformed |
| 2 | **Low-confidence labeled** | Every agent with confidence < `low_confidence_flag_threshold` (default 0.5) has its findings explicitly marked "unverified" in the synthesis | Inject "Unverified:" prefixes into the synthesis |
| 3 | **Tool-use anomalies flagged** | Every agent flagged by Patch 2 anomaly detection is mentioned in the synthesis caveat block | Add caveat block with anomaly list |
| 4 | **Cross-link conflicts surfaced** | If Patch 4 found contradictions, they appear in the synthesis under "Inter-agent findings" | Inject the cross-link block before the synthesis |
| 5 | **Spot-check artifact present** | The spot-check artifact (Patch 3) exists in `memory/operations/<session>/spot-check.md` for `[M]`/`[H]` swarms | Block synthesis; orchestrator must emit the artifact first |
| 6 | **Reviewer triggered if conditions met** | If any dynamic trigger condition (Patch 5) was true, the reviewer was dispatched and its output integrated | Run the reviewer now |
| 7 | **Cost report emitted** | Per `output.cost_report` setting | Compute and emit the cost report |
| 8 | **Artifact verification** | Every artifact declared by every agent (via `artifacts` META field) exists on disk and is ≥ `min_size_bytes` (default 1 byte) | In `mode: block` — hard block; surface `VERIFICATION FAILED:` to user. In `mode: warn` — inject caveat block flagging each missing/empty artifact. |

## Outcome states

After the gate runs, every check is `pass | fail | skipped`:

- **pass** — check ran and succeeded
- **fail** — check ran and the orchestrator took remediation action (synthesis is now correct)
- **skipped** — check was disabled by settings (e.g., `spot_check_enforce: false` for an `[L]` swarm)

The cost report includes a 1-line summary: `Synthesis gate: 7 pass, 1 fail (remediated), 0 skipped`.

## Hard blocks vs soft remediations

Some failures are **hard blocks** — synthesis cannot publish until resolved:

- Check 1 (missing META) — re-dispatch the agent
- Check 5 (missing spot-check artifact for [M]/[H]) — emit the artifact
- Check 6 (reviewer not run when triggered) — run the reviewer
- Check 8 (artifact verification failure in `mode: block`) — surface `VERIFICATION FAILED:` to user; do not relay the agent's "DONE" claim

Others are **soft remediations** — the orchestrator silently fixes the synthesis text:

- Check 2 (label low-confidence) — add "Unverified:" prefixes
- Check 3 (flag anomalies) — add caveat block
- Check 4 (surface conflicts) — inject cross-link block
- Check 7 (cost report) — compute and append
- Check 8 (artifact verification failure in `mode: warn`) — inject "VERIFICATION FAILED:" caveat before the agent's report in synthesis

## Pseudo-code

```python
def synthesis_gate(swarm_state):
    results = {}
    
    # Hard blocks first
    for agent in swarm_state.agents:
        if agent.meta is None:
            redispatch(agent)
            results[1] = "fail (remediated by re-dispatch)"
        else:
            results[1] = "pass"
    
    if swarm_state.safety_tag in ("[M]", "[H]") and settings.discipline.spot_check_enforce:
        if not artifact_exists(swarm_state.session_id, "spot-check.md"):
            emit_spot_check_artifact(swarm_state)
            results[5] = "fail (remediated)"
        else:
            results[5] = "pass"
    else:
        results[5] = "skipped"
    
    if any_dynamic_trigger_met(swarm_state) and not swarm_state.reviewer_run:
        run_reviewer(swarm_state)
        results[6] = "fail (remediated)"
    elif any_dynamic_trigger_met(swarm_state):
        results[6] = "pass"
    else:
        results[6] = "skipped"
    
    # Soft remediations
    low_conf_agents = [a for a in swarm_state.agents 
                       if a.meta.confidence < settings.discipline.low_confidence_flag_threshold]
    if low_conf_agents and not all_labeled_unverified(swarm_state.synthesis, low_conf_agents):
        inject_unverified_prefixes(swarm_state.synthesis, low_conf_agents)
        results[2] = "fail (remediated)"
    else:
        results[2] = "pass" if low_conf_agents else "skipped"
    
    # ... checks 3, 4, 7 similar pattern ...
    
    return results
```

## Why this is the capstone

Each previous patch (1–6, 10) addresses one specific gap. The synthesis gate is the single enforcement point that ensures **no patch was silently skipped**. Without it, an orchestrator can technically have implemented Patches 1–6 but still publish a synthesis that fails them. The gate is the integration test.

## Settings interaction

The gate respects:
- `discipline.spot_check_enforce` — if false, skip check 5
- `discipline.cross_link_enabled` — if false, skip check 4
- `discipline.reviewer_dynamic_triggers.*` — toggles individual triggers in check 6
- `output.cost_report` — if `off`, check 7 still runs (writes the artifact for memory) but doesn't emit to chat
- `discipline.artifact_verification.mode` — if `"off"`, skip check 8; if `"warn"`, soft remediation; if `"block"`, hard block

## Where the gate result lives

Written to `memory/operations/<session-id>/gate-result.json`:

```json
{
  "session_id": "2026-04-24-1432-abc123",
  "checks": {
    "1": "pass",
    "2": "skipped",
    "3": "pass",
    "4": "fail (remediated)",
    "5": "pass",
    "6": "skipped",
    "7": "pass",
    "8": "pass"
  },
  "remediations_applied": ["cross_link_block_injected"],
  "blocks_failed_unrecoverably": []
}
```

This file is parsed by the cost report (Patch 6) for the 1-line summary.
