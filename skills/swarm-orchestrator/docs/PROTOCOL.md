# Protocol — The 9 Mitigations

The framework's failure mode is **confident-shallow output**: a muscle at the wrong tier returns a plausible-looking report that the orchestrator merges into a polished-looking synthesis which hides the thinness. Nine mitigations, layered by stakes, close that gap.

The original 5 mitigations remain. Mitigations #6 (tool-use anomaly), #7 (cross-pollination), and #8 (synthesis quality gate) were added in the v2 upgrade after a real swarm run revealed gaps that the original 5 could not catch. Mitigation #9 (artifact verification) was added 2026-04-25 after Phase A testing revealed a fabricated-success failure mode that #5, #6, and #8 could not catch.

## Mitigation summary

| # | Name | Cost added | Time added | Blocks parallel? | When |
|---|---|---|---|---|---|
| 1 | Reviewer loop | +$0.15–0.50 | +1–2 min tail | no | `[H]` always; `[M]` on dynamic trigger |
| 2 | Escalation protocol | +0 baseline, +$0.05–0.15 on trigger | +30–60s when fires | no | `[M]` and `[H]` |
| 3 | Spot-check verification | +$0.02/agent | +20–40s | no | `[M]` and `[H]` (mandatory artifact) |
| 4 | Model-match discipline | 0 | 0 | no | **always** |
| 5 | Typed outputs + confidence | ~0 | 0 | no | **always** |
| 6 | Tool-use anomaly detection | ~0 | 0 (pure parsing) | no | **always** |
| 7 | Cross-pollination pass | +$0.05–0.15 | +30–60s | no | swarms with N ≥ 4 |
| 8 | Synthesis quality gate | ~0 | 0 (orchestrator self-check) | no | **always** (capstone) |
| 9 | Artifact verification | ~0 | 0 (disk stat per declared artifact) | no | **always** when recipe declares artifacts |

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

## #6 — Tool-use anomaly detection (always on)

After parsing each muscle's META block, check `tools_used` against the recipe's expected floor (defined in `defaults.json` `recipe_floors` and surfaced in `docs/RECIPES.md`).

```
floor = recipe_floors[recipe_name]  # e.g. {"WebSearch": 4, "WebFetch": 2}
actual = muscle.meta.tools_used    # e.g. {"WebSearch": 0, "WebFetch": 0, ...}

for tool, min_count in floor.items():
    if actual.get(tool, 0) < min_count:
        anomaly_detected(muscle, tool, actual.get(tool, 0), min_count)
        break
```

When an anomaly is detected, behavior depends on `discipline.anomaly_detection`:

- `"off"` — silently ignore. Use only when you really trust the agents.
- `"warn"` (default) — flag the muscle in the synthesis caveat block: "Agent E reported 0 web searches on a research task — its claims are unverified despite self-reported confidence."
- `"block"` — auto re-dispatch on the next-higher tier (Haiku → Sonnet → Opus) as if the muscle's confidence were < 0.5, regardless of what it claimed.

**Why this matters:** in the v2 swarm run that motivated this upgrade, an agent dispatched on a research task returned with 0 tool uses and self-reported confidence 0.88. The orchestrator missed it entirely. The synthesis cited the agent's claims as if they were verified. Tool-use anomaly detection catches exactly this case — the agent's self-grade lies, but the tool-call trace doesn't.

**Cost:** zero. Pure parsing. Re-escalation when fired adds the cost of one extra muscle dispatch (~$0.05–0.30 depending on tier).

## #7 — Cross-pollination pass (on for swarms with N ≥ 4)

Before synthesis, the orchestrator does a "key facts extract" across all muscle reports:

1. From each muscle's report, extract the top 3 headline claims (bold/lead/conclusion-stated).
2. For each fact, check if it would change another muscle's recommendation.
3. If yes, emit a `## Cross-link findings` block listing the contradiction or integration.

**Example from the swarm run that motivated this:**
> Muscle C found: "Gemini CLI cold start = 20–50s on Windows."
> Muscle D recommended: "dual-CLI architecture with Claude + Gemini subprocess."
> Cross-link finding: Muscle D's recommendation is broken on Windows because of fact from Muscle C. Synthesis should add a caveat: "Use direct Gemini API SDK, not CLI subprocess."

Without this pass, each muscle's report stays in its own scope. The synthesis can describe both findings but won't notice the contradiction. The orchestrator (one model holding all reports) can spot what individual muscles cannot.

**Settings gate:** `discipline.cross_link_enabled` (default `true`). Skipped automatically when N < `discipline.cross_link_min_agents` (default 4) — overhead not worth it for tiny swarms.

**Cost:** ~5 min orchestrator time on a 6-agent swarm. ~$0.05–0.15 in API equivalent.

## #8 — Synthesis quality gate (always on, capstone)

Before publishing the final synthesis, the orchestrator runs an 8-item self-check that integrates all prior mitigations into one enforcement point. See `templates/synthesis-gate.md` for the full checklist:

1. All META blocks parsed and confidences extracted?
2. All low-confidence claims labeled "unverified" in synthesis?
3. Tool-use anomalies flagged in caveat block?
4. Cross-link conflicts surfaced?
5. Spot-check artifact present (for `[M]`/`[H]`)?
6. Reviewer triggered if conditions met?
7. Cost report emitted per settings?
8. Artifact verification: all declared artifacts exist on disk and are non-empty?

Each check returns `pass | fail (remediated) | skipped`. Hard blocks (missing META, missing artifact, failed artifact verification in `block` mode) prevent publish until resolved. Soft remediations (label unverified, inject caveat) are silently fixed by the orchestrator.

**Why this is the capstone:** without it, an orchestrator can technically have implemented Mitigations 1–7 but still publish a synthesis that fails them. The gate is the integration test.

**Cost:** ~0. Pure orchestrator self-check.

## #1 — Reviewer loop (on for `[H]` always; `[M]` on dynamic trigger)

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

## #9 — Artifact verification (always on when recipe declares artifacts)

After each agent returns and before cross-pollination (Mitigation #7) and the synthesis gate (Mitigation #8), the orchestrator verifies that every artifact the agent declared actually exists on disk and is non-empty. This prevents fabricated-success output — where an agent's tool call silently fails (e.g., a Write denied due to permissions) but the agent emits a success-shaped stdout (`path\n398`) that the orchestrator relays as "DONE" without checking.

**Discovery context (2026-04-25):** Phase A retest of the Antigravity adapter revealed this failure mode in practice. An Opus muscle dispatched to write `index.html` was permission-denied on the Write call, then printed `path\n398` as fabricated stdout. The slot relayed "DONE" without checking. Mitigation #5 (META block) did not catch it — the agent produced no real META block when faking. Mitigation #8 (synthesis gate) did not catch it — the gate operates on agent reports, not on disk reality. Mitigation #9 is the structural fix.

### Configuration (`discipline.artifact_verification` in `defaults.json`)

| Key | Type | Default | Meaning |
|---|---|---|---|
| `mode` | `"off" \| "warn" \| "block"` | `"block"` | How verification failures are handled |
| `expected_artifacts_field` | string | `"artifacts"` | META-block field where agents list files they wrote |
| `min_size_bytes` | integer | `1` | Files smaller than this are treated as empty / failed |

### Mode behavior

**`"block"` mode (default):** verification failure means the agent's report is treated as failed. The orchestrator does NOT relay any "DONE:" claim from that agent's output. Re-dispatches once on a higher tier with a tightened prompt explicitly naming the permission barrier. If the re-dispatch also fails verification, surfaces the verification failure to the user verbatim with `VERIFICATION FAILED:` prefix. No fabricated results merge into synthesis.

**`"warn"` mode:** verification failure is logged and flagged in the synthesis caveat block. The report is still relayed, but prefixed with `VERIFICATION FAILED:` so downstream readers know. Synthesis gate check #8 records this as a soft failure, remediated by the caveat.

**`"off"` mode:** no disk checks performed. Use only in environments where agents write to remote storage that the orchestrator cannot stat directly.

### When it fires

After each agent returns (between Step 2 "Per-muscle return processing" and Step 3 "Spot-check" in SKILL.md), for any agent whose dispatch recipe or META block declares an `artifacts` field. If the field is absent or empty, the check is skipped for that agent.

```python
# Step 2.5 — Artifact verification (mitigation #9)
if settings.discipline.artifact_verification.mode != 'off':
    for path in agent.meta.get('artifacts', []):
        if not os.path.exists(path) or os.path.getsize(path) < settings.discipline.artifact_verification.min_size_bytes:
            if settings.discipline.artifact_verification.mode == 'block':
                flag_agent_as_failed(agent, reason=f"VERIFICATION FAILED: {path} does not exist or is empty")
                redispatch_on_higher_tier(agent, tightened_prompt=True)
            elif settings.discipline.artifact_verification.mode == 'warn':
                flag_for_synthesis_caveat(agent, f"VERIFICATION FAILED: {path}")
```

### Synthesis gate impact

Synthesis gate check #8 is the integration enforcement point for this mitigation:

- In `"block"` mode: any failed verification is a **hard block** — synthesis cannot publish until the re-dispatch resolves or the failure is surfaced to the user.
- In `"warn"` mode: failed verifications are a **soft remediation** — the caveat block is injected before synthesis publishes.

**Cross-references:** configuration lives in `defaults.json` under `discipline.artifact_verification`. The gate check is in `templates/synthesis-gate.md` (check #8).

### Cost

~0 per artifact. A filesystem `stat` or `os.path.getsize` call. Re-dispatch when fired adds the cost of one extra muscle dispatch (~$0.05–0.30 depending on tier).

## Safety tag → mitigation layering

| Safety tag | #4 Match | #5 Typed | #2 Esc. | #3 Spot-check | #6 Anomaly | #7 Cross-link | #1 Reviewer | #8 Gate | #9 Artifact |
|---|---|---|---|---|---|---|---|---|---|
| `[L]` low-stakes | ✅ | ✅ | ⬜ | ⬜ | ✅ | ✅ (if N≥4) | ⬜ | ✅ | ✅ (if artifacts declared) |
| `[M]` medium-stakes | ✅ | ✅ | ✅ | ✅ (mandatory artifact) | ✅ | ✅ (if N≥4) | ⬜ static; ✅ on dynamic trigger | ✅ | ✅ (if artifacts declared) |
| `[H]` high-stakes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (if N≥4) | ✅ | ✅ | ✅ (if artifacts declared) |

The tag goes in the description prefix: `[M] Audit docs/diagnoses/`.

The dashboard parses the prefix and renders a colored safety pill.

Mitigations #6 (anomaly) and #8 (gate) run on every safety tag — they're cheap pure-parse checks that catch failures the other mitigations don't.

Mitigation #7 (cross-link) skips when N < 4 regardless of tag, since orchestrator overhead isn't worth it for tiny swarms.

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

**Pre-dispatch:**
- [ ] Settings loaded (`lib/memory.py:load_settings()`)
- [ ] Knowledge tier searched for similar past runs (Step 0.5 in SKILL.md)
- [ ] Dispatch template ends with full META contract (incl. `tools_used`)
- [ ] Description prefixed with `[L]` / `[M]` / `[H]`
- [ ] Explicit exclusion list in prompt so muscles don't trample each other

**Per-muscle parsing:**
- [ ] Parse confidence — escalate any `< reescalation_threshold` (default 0.7)
- [ ] Parse `tools_used` — check against recipe floor (mitigation #6); fire anomaly action per settings
- [ ] Parse `artifacts` — stat each declared file; apply `artifact_verification.mode` action (mitigation #9)
- [ ] Write per-agent JSON to `memory/operations/<session>/agents/<name>.json`

**Post-swarm (orchestrator):**
- [ ] For `[M]` and `[H]` with `spot_check_enforce: true`: emit spot-check artifact (mandatory; even "Picked: 0" if all confidences high)
- [ ] For N ≥ `cross_link_min_agents` with `cross_link_enabled: true`: run cross-pollination pass (mitigation #7), emit cross-link.md if conflicts found
- [ ] Check dynamic reviewer triggers (mitigation #5 conditions): if any fires, dispatch reviewer with adversarial mandate
- [ ] Run synthesis quality gate (mitigation #8) — apply hard blocks and soft remediations
- [ ] Compute cost report per `output.cost_report` setting; write to operations dir always; emit to chat per setting

**Post-synthesis:**
- [ ] Promote operations session to Knowledge tier (`knowledge.promote(session)`)
- [ ] Touch cleanup.lock so daily TTL job can eventually delete the operations dir
