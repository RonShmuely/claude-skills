# Swarm Protocol

Orchestrator playbook for dispatching muscle agents. I (the brain) follow these rules on every swarm.

---

## Always-on defaults

These cost ~$0 extra and run on every dispatched agent.

### #4 — Model-match discipline

Before dispatching, I pick the tier by task shape, not by habit:

| Task shape | Tier |
|---|---|
| Narrow, structured output (count, grep, list, inventory) | **Haiku** |
| Reasoning, multi-step judgment, browser, code | **Sonnet** |
| Decision Ron would regret getting wrong | **Opus** |

If I catch myself dispatching Haiku for a task with real ambiguity, **I default up a tier**. Haiku's failure mode is confident-shallow — undetectable in the final synthesis. Sonnet is the safe escalation.

### #5 — Typed outputs + confidence

Every muscle prompt ends with this contract:

```
At the end of your report, emit a metadata block:

---META---
confidence: 0.XX          # your confidence this report is accurate (0.0–1.0)
method: "..."             # how you gathered the data
not_checked: [...]        # things you couldn't verify
sample_size: N            # if you sampled (not exhaustive)
---END META---
```

Dashboard parses this, shows a confidence pill on each card. Low confidence (< 0.7) triggers #2 (escalation).

---

## Opt-in by stakes

I tag each swarm dispatch with a safety level encoded in the description:

- `[L] ...` — Low — inventory, counts, simple greps
- `[M] ...` — Medium — audits, decision support, anything with recommendations
- `[H] ...` — High — diagnosis decisions, architecture calls, anything with real-world consequence

### [L] Low-stakes

Defaults only (#4 + #5). No reviewer, no spot-check, no escalation. Raw speed.

### [M] Medium-stakes

Add:

- **#2 Escalation protocol** — after each muscle returns, I check confidence. If < 0.7, I re-dispatch the same prompt to Sonnet. Dashboard shows an arrow from the Haiku card to the Sonnet card.
- **#3 Spot-check verification** — after the swarm completes, I pick 3 specific claims from the merged reports and verify them with my own tool calls (read a file, check a count, sanity-check a number). If a spot-check fails, I flag the finding as **unverified** in the synthesis.

### [H] High-stakes

Add everything in [M] plus:

- **#1 Reviewer loop** — I dispatch a final Sonnet (or Opus for [H] decisions) that reads all child reports + samples raw files I haven't seen and writes a critique. Reviewer's job is specifically "what did the swarm miss, what claims are suspicious, what nuance was lost in the typed-output pipe?"

---

## Dispatch template I use

```
[SAFETY_TAG] <description>

Audit <scope>. Read-only. Do NOT modify.

<specific deliverable>

Rules:
- Touch nothing outside your scope — other agents own neighboring areas
- If a claim requires inference, lower your confidence and say why
- If you couldn't check something, list it in `not_checked`

At the end of your report, emit:

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
---END META---
```

---

## Escalation trigger rules

When a muscle returns, I inspect:

1. **Confidence < 0.7** → escalate to Sonnet with same prompt
2. **`not_checked` lists something critical to the ask** → re-dispatch Sonnet with focus on that gap
3. **Numbers don't sanity-check** (unit errors, impossible counts) → spot-check with my own tool call, then escalate if still wrong
4. **"No findings" from a muscle when I expected findings** → escalate, Haiku may have missed them

Silent escalation: I don't bother Ron; dashboard shows the escalation arrow.

---

## Reviewer prompt template ([H] only)

```
You are a reviewer. The swarm below just audited <scope>. Your job is NOT to redo their work — it's to find what they missed, what looks shallow, and what nuance was lost in typed-output compression.

Read these N muscle reports:
<reports inline>

Then sample these raw files the muscles didn't fully read:
<3-5 file paths you pick>

Produce:
1. Claims you doubt (with your reasoning)
2. Things the muscles didn't notice but should have
3. Cross-section patterns only visible from seeing everything
4. Your revised version of the top 3 findings

Be adversarial. A polite review is a useless review.
```

Reviewer output goes into its own dashboard card, parented to the swarm.

---

## What this costs in practice

| Safety | Cost multiplier vs bare swarm | Time multiplier |
|---|---|---|
| [L] | 1.0× | 1.0× |
| [M] | ~1.15× | ~1.2× |
| [H] | ~1.4× | ~1.5× |

Ship [L] by default. Bump to [M] when the swarm's output will drive a decision. Bump to [H] when getting it wrong costs money or customer trust.

---

## #6 — Post-swarm learning (close the feedback loop)

The escalation count only helps if future-me reads it. Otherwise it's a metric
that shames you but doesn't change behavior. This rule closes the loop.

### After every swarm

Before declaring the swarm complete, append one line to
`~/.claude/swarm-log.md` in this exact shape:

```
- YYYY-MM-DD HH:MM · <task-pattern> · <tier-used> × <agent-count> · <escalations> esc · <cost> · <verdict>
```

Examples:
```
- 2026-04-23 20:07 · folder-audit (MG 5 sections) · haiku × 5 · 0 esc · $1.80 · right
- 2026-04-23 21:15 · hebrew-manual-research · haiku × 3 · 3 esc · $0.55 · UNDER-TIERED (use sonnet)
- 2026-04-23 22:40 · architecture-decision · opus × 1 · 0 esc · $1.20 · right
```

Verdict is exactly one of: `right` · `UNDER-TIERED` · `OVER-TIERED`.

- **`right`** — all muscles returned `confidence >= 0.7`, no spot-check failed,
  no reviewer flag. Tier was correct for the shape.
- **`UNDER-TIERED`** — any muscle fell below `0.7` and escalated, or reviewer
  flagged shallow work. Note which tier to use next time.
- **`OVER-TIERED`** — muscles returned 0.95+ with trivial structured output on
  a task a cheaper tier could handle. Downgrade recommendation next run.

### Before every swarm

First thing after decomposing the task, read `~/.claude/swarm-log.md` and
grep for similar patterns:

```bash
grep -iE "(folder-audit|hebrew|diagnosis|research)" ~/.claude/swarm-log.md | tail -10
```

If you see a recent `UNDER-TIERED` verdict on a related pattern, **default up
a tier** for the new swarm without re-arguing the case. The log is the
precedent. Trust past-you.

### Why this works

- **Zero infrastructure** — plain-text log file, readable by `grep`.
- **Stable across sessions** — lives in `~/.claude/`, loads from any project.
- **Self-compressing** — old entries fall to the bottom; `tail` grabs recent.
- **Honest** — writing `UNDER-TIERED` on yourself keeps the discipline real.

### Anti-patterns

- Writing `right` because the swarm *ran* — not because the tier was right.
  Tier is right only if you'd do the same thing again with today's knowledge.
- Skipping the log after a quick small swarm. The small ones are where
  tier-match errors sneak in; log every one.
- Never reading the log before dispatching. The log is worthless unless it
  shapes future decisions.

### What this is not

This rule is not about blaming Haiku for failing. Haiku failing a task it
shouldn't have been given is a **dispatch error** by the orchestrator. The
log holds the orchestrator accountable, not the muscle.
