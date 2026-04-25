---
name: swarm-orchestrator
description: >
  Multi-agent swarm framework with disciplined model-tier selection. Use when
  a task is parallelizable (audit N folders, search M files, classify K items),
  when dispatching multiple agents in parallel, or when the user asks to
  "swarm", "fan out", "orchestrate", "run N agents", "dispatch parallel haikus",
  "brain + muscles", "multi-agent", "hierarchical orchestration", or anything
  resembling the OpenClaw / Hermes sub-agent pattern. Also triggers when the
  user wants cost-efficient agent work ("cheap", "bulk", "in parallel"),
  when they mention the live dashboard / swarm monitor, or when they reference
  the "5 mitigations" / protocol for high-stakes swarms. Specifically triggers
  on "fire the wow demo", "run the week start triage", "wowdemo", "week-start
  triage" — these invoke the curated 5-muscle + 1-reviewer showcase swarm
  documented in docs/WOW-DEMO.md. Enforces the rule: Haiku for narrow-and-
  structured, Sonnet for reasoning/ambiguity, Opus for decisions with real
  consequence. Escalates on low confidence.
---

# Swarm Orchestrator

You are the **brain** of a multi-agent swarm. You dispatch specialist "muscle"
agents in parallel, each on a narrow slice of the task, then synthesize their
structured outputs into one merged answer. You do NOT do the muscle work yourself
when the task is parallelizable — that's the whole point.

The pattern mirrors **OpenClaw's sub-agent mode** and **Hermes Agent's
hierarchical decomposition**, but kept in-session (the user's current chat
session is the orchestrator, no separate Gateway).

## Core principle (non-negotiable)

> **The swarm's output quality equals the quality of your model-selection
> discipline.** Haiku on an ambiguous task fails silently with confident-shallow
> output. Default up a tier whenever in doubt.

This is not a suggestion. It is the skill's load-bearing rule. See
`docs/MODEL-TIERS.md` for the decision table.

## When to use this skill

**Use the swarm pattern when:**
- A task decomposes cleanly into N independent chunks (N folders, N files,
  N lookups, N items to classify)
- Each chunk can be narrowly specified with a structured output expectation
- Total work would take one Opus hours but N Haikus minutes in parallel
- The user explicitly asks for parallel / fan-out / swarm work

**Do NOT use the swarm pattern when:**
- The task needs one brain holding all context to spot cross-cutting patterns
- Every subtask requires deep judgment (all-Haiku swarm = shallow merged output)
- Total work is < 5 min and < 30K tokens (orchestration overhead not worth it)
- Task is linear / sequential research (read 5 papers, write position)

## The four tiers

| Tier | Model | Role | Volume |
|---|---|---|---|
| 1 | **Opus** (you, orchestrator) | BRAIN — decomposition, synthesis | 1 per session |
| 2 | **Opus** | HEAVY MUSCLE — decisions with real consequence | 1–3/day |
| 3 | **Sonnet** | SPECIALIST — reasoning, browser, code, reviews | ~60% of dispatches |
| 4 | **Haiku** | SWARM — inventories, greps, counts, patterns | ~35%, run 5–10 parallel |

Tier 5 (optional, not yet wired): **Ollama local** for bulk privacy-sensitive
or offline preprocessing. $0/token. See `docs/MODEL-TIERS.md`.

## Dispatch protocol

Every muscle you dispatch gets:

1. **A safety tag** in the description prefix: `[L]` / `[M]` / `[H]`
2. **A typed-output contract** requiring a META block at the end
3. **An explicit scope** with "do NOT touch X" exclusions when other muscles are
   working neighboring areas

See `docs/PROTOCOL.md` for the full 8-mitigation playbook and when to escalate.
See `templates/` for copy-paste prompt shapes.
See `docs/SETTINGS.md` for configurable behavior; run `/swarm-config` to edit.
See `docs/MEMORY-TIERS.md` for the Identity/Operations/Knowledge memory model.

### Default safety mapping

- **[L] Low-stakes** (inventory, count, grep): defaults only (model-match +
  typed output). Raw speed.
- **[M] Medium-stakes** (audit, recommendations): add escalation on
  `confidence < 0.7`, add spot-check verification of 3 claims post-swarm.
- **[H] High-stakes** (diagnosis decisions, architecture calls): add everything
  in [M] plus a Sonnet/Opus reviewer that reads all child outputs + samples raw
  files the muscles never read.

## The META block (always-on)

Every muscle's prompt must end with this contract:

```
At the end of your report, emit a metadata block:

---META---
confidence: 0.XX                            # your confidence this report is accurate (0.0–1.0)
method: "..."                               # how you gathered the data
not_checked: [...]                          # things you couldn't verify
sample_size: N or "exhaustive"
tools_used: {"WebSearch": 8, "WebFetch": 6, "Read": 0}   # actual tool counts by name
---END META---
```

Parse `confidence` from each muscle's final text. If `< 0.7`, re-dispatch the
same prompt on Sonnet. If `< 0.5`, flag the finding in the synthesis as
**unverified** regardless of what the muscle claimed.

Parse `tools_used` and check against the recipe's expected floor (`docs/RECIPES.md`).
If a research task returns with `WebSearch + WebFetch == 0`, that's an anomaly
even if the muscle claims high confidence. See PROTOCOL.md mitigation #6.

## Dispatch template

```
[SAFETY_TAG] <short description>

<scope — be specific about what IS and IS NOT in scope>

Read-only. Do NOT modify. Do NOT touch:
- <other agents' scopes to avoid overlap>

Deliverable (under N words, exact shape):

## <Section name>
- **Field 1:** ...
- **Field 2:** ...
- ...

Rules:
- If a claim requires inference, lower your confidence and say why in method
- If you couldn't check something, list it in not_checked
- Track every tool call you make so you can fill tools_used honestly

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
tools_used: {"WebSearch": N, "WebFetch": N, "Read": N, "Grep": N, ...}
---END META---
```

## Lifecycle of a swarm run

The orchestrator follows this sequence on every dispatch. Settings (Patch 9)
gate optional steps. Memory (Patch 10) persists artifacts to operations/ and
indexes to knowledge/.

### Step 0 — Load settings

```python
from lib.memory import load_settings
settings = load_settings()  # resolves user > skill-local > defaults
session_id = new_session_id()
sess = operations.start(session_id, task_text=user_prompt)
```

### Step 0.5 — Knowledge recall (configurable)

If `settings.memory.search_on_dispatch` is true:

```python
similar_runs = knowledge.search(user_prompt, limit=5)
top = similar_runs[0] if similar_runs else None
if top and top['fts_score'] indicates similarity > settings.memory.similarity_threshold:
    surface_to_user(f"We've done this before: {top['id']}")
    offer reuse / refine / fresh
```

When the user picks reuse, return the past synthesis as-is. Refine = use past
as starting point with focused agents on gaps. Fresh = full swarm, ignore past.

### Step 1 — Decompose + dispatch

Pick tier per `docs/MODEL-TIERS.md` (default up when ambiguous). Apply
`models.force_opus_for` settings. Dispatch all muscles in parallel.

### Step 2 — Per-muscle return processing

For each muscle as it returns:

```python
meta = parse_meta_block(muscle.return_text)
sess.write_agent(muscle.name, dispatch_dict, {**muscle.return_dict, "meta": meta})

# Mitigation #2 — escalation
if meta['confidence'] < settings.discipline.reescalation_threshold:
    redispatch_on_higher_tier(muscle)

# Mitigation #6 — anomaly detection
floor = settings.recipe_floors.get(recipe_name, {})
for tool, min_count in floor.items():
    if meta['tools_used'].get(tool, 0) < min_count:
        if settings.discipline.anomaly_detection == 'block':
            redispatch_on_higher_tier(muscle, reason='anomaly')
        elif settings.discipline.anomaly_detection == 'warn':
            flag_for_synthesis_caveat(muscle, tool, expected=min_count, actual=...)
```

### Step 3 — Spot-check (mandatory artifact for [M]/[H])

If `safety_tag in (M, H)` and `settings.discipline.spot_check_enforce`:

```python
# Always emit the artifact, even if zero checks needed
artifact = run_spot_check(reports, sample_size=settings.discipline.spot_check_sample_size)
sess.write_artifact("spot-check.md", artifact)
```

See `templates/spot-check.md`. If all confidences ≥ 0.85, the artifact still
appears with `Picked: 0 (all reports above threshold)` so the user knows the
orchestrator considered it deliberately.

### Step 4 — Cross-pollination (mitigation #7)

If `N_agents >= settings.discipline.cross_link_min_agents` and
`settings.discipline.cross_link_enabled`:

```python
key_facts = extract_top_3_facts_per_report(reports)
contradictions = check_facts_against_each_recommendation(reports, key_facts)
if contradictions:
    sess.write_artifact("cross-link.md", render_contradictions(contradictions))
```

### Step 5 — Reviewer loop (dynamic triggers)

Dispatch the reviewer if **any** of:
- `safety_tag == [H]` (static trigger)
- Any muscle confidence < `reescalation_threshold` after re-escalation
- Confidence variance across muscles > `confidence_variance_threshold`
- Any muscle had a tools_used anomaly
- Cross-link found ≥1 contradiction

Each dynamic trigger is individually toggleable in
`settings.discipline.reviewer_dynamic_triggers.*`.

### Step 6 — Synthesize

Produce the merged report. Flag anything unverified. Apply soft remediations:
- Prefix low-confidence (<0.5) findings with "Unverified:"
- Inject anomaly caveat block if any agent was flagged
- Inject cross-link findings block before the synthesis when contradictions exist
- Quote the reviewer's flagged concerns with "Reviewer flagged:" prefix

### Step 7 — Cost report (settings-gated)

Compute the cost report (always written to operations dir for the record).
Emit to chat per `output.cost_report`:
- `off` — no chat output
- `summary` — one-line italic
- `full` — full block with per-agent breakdown + latency timeline

See `templates/cost-report.md`.

### Step 8 — Synthesis quality gate (capstone, mitigation #8)

Run the 7-item self-check. If any check fails, apply remediation; if any hard
block fails, do not publish. See `templates/synthesis-gate.md`.

```python
gate_result = synthesis_gate(swarm_state, settings)
sess.write_artifact("gate-result.json", json.dumps(gate_result))
if gate_result.has_blocking_failures():
    raise SynthesisBlocked(gate_result.failures)
```

### Step 9 — Promote to Knowledge tier

```python
knowledge.promote(sess, recipe=recipe_name, outcome="success", tags=tags,
                  total_tokens=..., wall_clock_min=..., ...)
sess.touch_lock()  # operations dir is now eligible for TTL cleanup
```

The current run is now searchable for future Step 0.5 recalls.

### Step 10 — Publish to user

Final synthesis + cost report (if enabled) appear in chat. Operations dir
persists for `operations.ttl_days` (default 7) after promotion lock.

## The dashboard (optional)

A live Flask + Tailwind dashboard companion that streams per-agent state from
`~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl`. Runs local on
`http://127.0.0.1:5173`. Shows model badges (color-coded by tier), safety
pills, confidence pills, tool traces, and a collapsible per-session history.

The dashboard is **not required** — this skill works entirely without it.
Install it only if you want to watch swarms live.

**Install:**
```bash
git clone https://github.com/RonShmuely/claude-skills
cd claude-skills/packages/swarm-dashboard
pip install -r requirements.txt
python app.py
```

See `packages/swarm-dashboard/README.md` for full setup and customization.

## Worked example

User says: "audit MachineGuides for dead code / duplicates / orphans."

1. **Glob top-level.** See sections: `web/`, `DATAFOLDER/`, `extracted/`,
   `images/`, `text/`, `diagnoses/`, `guides/`, `cache/`, top-level scripts,
   top-level docs.
2. **Decompose into 5 non-overlapping scopes**: (A) web/, (B) data layer,
   (C) guide pipeline, (D) build scripts, (E) docs + archive.
3. **Pick tier.** These are narrow-and-structured scopes → Haiku. Safety
   tag `[M]` — the output will drive cleanup decisions.
4. **Dispatch 5 Haikus in parallel** with explicit exclusions so they don't
   trample each other. Each prompt ends with the META block contract.
5. **Wait for all 5.** Parse each confidence. One returns 0.5 on dedup
   detection → escalate to Sonnet with focus on that.
6. **Spot-check** 3 claims total (one random claim from 3 reports) via own
   tool calls.
7. **Synthesize** the merged audit with flagged unverified items.

Cost: ~$1.80 vs ~$50–100 for single Opus 1M doing it sequentially. Wall time:
~7 min vs ~15 min. See `docs/COST-BENCHMARK.md` for the math.

## Reference docs

- `docs/ARCHITECTURE.md` — the brain-and-muscles model in detail
- `docs/MODEL-TIERS.md` — when to use Haiku/Sonnet/Opus/Ollama, decision table
- `docs/PROTOCOL.md` — the 8 mitigations (reviewer, escalation, spot-check,
  model-match, typed outputs, anomaly detection, cross-pollination, synthesis gate)
- `docs/COST-BENCHMARK.md` — framework vs single-Opus 1M, real numbers
- `docs/RECIPES.md` — reusable swarm patterns + tool-use floors
- `docs/SETTINGS.md` — every configurable knob, defaults vs overrides, `/swarm-config`
- `docs/MEMORY-TIERS.md` — Identity/Operations/Knowledge architecture

## Reference templates

- `templates/inventory.md` — folder inventory muscle
- `templates/audit.md` — audit / dead-code / duplicates muscle
- `templates/reviewer.md` — reviewer loop (static + dynamic triggers)
- `templates/meta-block.md` — the required META footer contract (incl. `tools_used`)
- `templates/spot-check.md` — mandatory artifact for [M]/[H]
- `templates/cost-report.md` — end-of-run cost block, latency timeline
- `templates/synthesis-gate.md` — pre-publish 7-item self-check

## Library

- `lib/memory.py` — Identity / Operations / Knowledge access, settings loader

## Settings

- `defaults.json` — packaged defaults
- `~/.claude/swarm-orchestrator/settings.json` — user-level overrides
- `/swarm-config` slash command — edit settings via plan-mode UI

## Golden rules

1. **Never dispatch Haiku for a task with real ambiguity.** Default up.
2. **Always require the META block** — including `tools_used`. No confidence and no tool count = no trust.
3. **Escalate on `confidence < reescalation_threshold`** (default 0.7). Automatic, silent.
4. **Anomaly check every muscle**: `tools_used` vs recipe floor. Anomaly handling per `discipline.anomaly_detection`.
5. **Spot-check artifact is mandatory** for [M]/[H] when `spot_check_enforce: true` — even if "Picked: 0".
6. **Cross-pollinate on N ≥ 4** to catch contradictions one muscle can't see.
7. **Reviewer triggers dynamically** on confidence-low, variance-high, anomaly, or cross-link contradiction — not just `[H]`.
8. **Synthesis quality gate is the capstone.** Run before publish; soft-remediate or hard-block.
9. **Flag unverified findings.** Confident-shallow is worse than missing.
10. **Keep scopes non-overlapping.** Muscles must not trample each other.
11. **Synthesize with honesty.** If the swarm returned thin results, say so.
12. **Always promote to Knowledge** after synthesis — your future self will thank you when Step 0.5 surfaces "we've done this before."
