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
  the "5 mitigations" / protocol for high-stakes swarms. Enforces the rule:
  Haiku for narrow-and-structured, Sonnet for reasoning/ambiguity,
  Opus for decisions with real consequence. Escalates on low confidence.
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

See `docs/PROTOCOL.md` for the full 5-mitigation playbook and when to escalate.
See `templates/` for copy-paste prompt shapes.

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
confidence: 0.XX          # your confidence this report is accurate (0.0–1.0)
method: "..."             # how you gathered the data
not_checked: [...]        # things you couldn't verify
sample_size: N or "exhaustive"
---END META---
```

Parse `confidence` from each muscle's final text. If `< 0.7`, re-dispatch the
same prompt on Sonnet. If `< 0.5`, flag the finding in the synthesis as
**unverified** regardless of what the muscle claimed.

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

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
---END META---
```

## After the swarm returns

1. **Parse each muscle's META block.** Anything `confidence < 0.7` → escalate
   that one to Sonnet, re-run.
2. **Spot-check** (for [M] and [H]): pick 3 specific claims across the reports
   and verify with your own tool calls. If any spot-check fails, flag that
   finding.
3. **Reviewer loop** (for [H] only): dispatch a Sonnet (or Opus) that reads
   all child reports + samples raw files you haven't seen. Reviewer's job is
   adversarial — "what did the swarm miss, what nuance was lost, what
   cross-section patterns are only visible now?" See `templates/reviewer.md`.
4. **Synthesize.** Produce a merged report. Flag anything unverified. Never
   present shallow muscle output as authoritative — say so when it's thin.

## The dashboard (optional)

A live Flask + Tailwind dashboard at `dashboard/` streams per-agent state from
`~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl`. Runs local on
`http://127.0.0.1:5173`. Shows model badges (color-coded by tier), safety
pills, confidence pills, tool traces, and a collapsible per-session history.

The dashboard is **observational, not required**. The swarm pattern works
without it — the dashboard just makes it visible. See `dashboard/README.md`.

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
- `docs/PROTOCOL.md` — the 5 mitigations (reviewer, escalation, spot-check,
  model-match, typed outputs)
- `docs/COST-BENCHMARK.md` — framework vs single-Opus 1M, real numbers
- `docs/RECIPES.md` — reusable swarm patterns you can fire by name

## Reference templates

- `templates/inventory.md` — folder inventory muscle
- `templates/audit.md` — audit / dead-code / duplicates muscle
- `templates/reviewer.md` — reviewer loop for [H] swarms
- `templates/meta-block.md` — the required META footer contract

## Golden rules

1. **Never dispatch Haiku for a task with real ambiguity.** Default up.
2. **Always require the META block.** No confidence = no trust.
3. **Escalate on `confidence < 0.7`.** Automatic, silent.
4. **Spot-check claims** on [M] and [H] before presenting merged output.
5. **Flag unverified findings.** Confident-shallow is worse than missing.
6. **Keep scopes non-overlapping.** Muscles must not trample each other.
7. **Synthesize with honesty.** If the swarm returned thin results, say so.
