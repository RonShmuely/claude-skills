# swarm-orchestrator

> Multi-agent swarm skill for Claude Code. One brain, N muscles, configurable, with three-tier memory and a quality gate.

## Scope (read first)

This skill is the **cross-runtime swarm-orchestrator framework**. It is the product. It runs on top of any Claude-family runtime that can dispatch subagents — natively in Claude Code via the Agent tool, or via shell-out to `claude -p` from runtimes that lack native dispatch (Antigravity, Cursor). The framework is the single source of truth; per-runtime adapters (e.g., the workspace `AGENTS.md` template) are thin wrappers that translate framework concepts into one IDE's primitives.

The `swarm-dashboard` package (separate, at `packages/swarm-dashboard/`) is an **optional standalone observability tool** — a passive viewer of `~/.claude/projects/` and `~/.swarm/` that renders live + historical swarm runs. The dashboard is single-user and local-only. **The framework does not depend on the dashboard.** Dispatches happen via the runtime's native primitives (or `claude -p` shell-out); the dashboard, if running, watches and renders. If it's down, dispatches still work.

Audiences for the framework: **Easy tier** (non-technical user, Hebrew-first), **Advanced tier** (power user with multiple model subscriptions), **Developer tier** (unrestricted access for skill authoring + audits), and future SaaS tier users (open-core with closed federated learner). The dashboard is currently single-user / single-author scope.



## What this is

A Claude Code skill that turns any sufficiently-parallelizable task into a swarm: an Opus orchestrator decomposes, dispatches specialist muscles (Haiku for narrow work, Sonnet for reasoning, Opus for stakes), then synthesizes. Stays in-session — no separate Gateway process.

**Current version: v2.0** (2026-04-25). See [`CHANGELOG.md`](CHANGELOG.md) and [`RELEASE-v2.md`](RELEASE-v2.md) for the full upgrade notes.

## Why it exists

Running a single Opus on large parallelizable tasks is **30–50× more expensive** and **2–3× slower** than a disciplined swarm. But a naive swarm has a failure mode that hurts: Haiku used on ambiguous tasks returns confident-shallow output that merges into a polished-looking-but-thin synthesis. Hard to detect, worse than missing.

This skill codifies the discipline to do it right.

## The 9 Mitigations (v2)

1. **Reviewer loop** — adversarial agent re-reads children + samples raw files. Static trigger on `[H]` tag plus 4 dynamic triggers.
2. **Escalation protocol** — `confidence < reescalation_threshold` (default 0.7) silently re-dispatches on a higher tier.
3. **Spot-check verification** — mandatory artifact for `[M]`/`[H]` swarms; even "Picked: 0" must appear.
4. **Model-match discipline** — tier matches task shape; default up when ambiguous.
5. **Typed outputs + confidence** — every muscle emits a META block with `confidence`, `method`, `not_checked`, `sample_size`, `tools_used`.
6. **Tool-use anomaly detection** *(new in v2)* — `tools_used` checked against recipe floors. `block` mode auto re-dispatches violators.
7. **Cross-pollination pass** *(new in v2)* — for swarms with N≥4, finds contradictions between agent reports before synthesis.
8. **Synthesis quality gate** *(new in v2)* — 8-item pre-publish self-check; hard blocks on missing artifacts, soft remediations for the rest.
9. **Artifact verification** *(new in v2.1)* — after each agent returns, stats every declared artifact on disk before relaying any "DONE" claim; `block` mode prevents fabricated-success output from reaching synthesis.

## Three-tier memory (v2)

- **Identity** — stable user/agent facts; markdown files; never auto-written
- **Operations** — per-swarm artifacts (META blocks, spot-check, cross-link, cost report, synthesis); auto-cleanup after 7 days
- **Knowledge** — append-only SQLite index (FTS5 + optional sqlite-vec) of past runs; queried at Step 0.5 to surface "we've done this before"

See [`docs/MEMORY-TIERS.md`](docs/MEMORY-TIERS.md) for storage schema, hybrid search formula, and promotion rules.

## Configurable (v2)

22 knobs across Output / Discipline / Models / Quota / Memory / Recipe-floors. Three priority layers:

1. `~/.claude/swarm-orchestrator/settings.json` — your personal overrides (partial JSON)
2. `<skill-dir>/settings.local.json` — skill-local overrides (gitignored)
3. `<skill-dir>/defaults.json` — repo defaults

Edit via:

- **`/swarm-config`** — popup wizard with 4 paginated questions covering preset bundles. Fast path for common edits.
- **`/swarm-config --advanced`** — plan-mode markdown editor exposing every individual knob. For per-knob bulk edits.

Or edit `~/.claude/swarm-orchestrator/settings.json` directly with any text editor.

Full knob reference: [`docs/SETTINGS.md`](docs/SETTINGS.md).

## Layout

```
swarm-orchestrator/
├── SKILL.md            # the skill Claude Code loads (lifecycle, 12 golden rules)
├── README.md           # this file
├── CHANGELOG.md        # version history
├── RELEASE-v2.md       # detailed v2 diff report
├── defaults.json       # repo default settings (22 knobs + 9 recipe floors)
├── .gitignore
├── docs/
│   ├── ARCHITECTURE.md     # brain + muscles model
│   ├── MODEL-TIERS.md      # Haiku/Sonnet/Opus/Ollama decision table
│   ├── PROTOCOL.md         # the 9 mitigations in detail
│   ├── COST-BENCHMARK.md   # framework vs single-Opus 1M
│   ├── RECIPES.md          # 9 reusable swarm patterns + tool-use floors
│   ├── SETTINGS.md         # every knob, every default, override mechanism (v2)
│   ├── MEMORY-TIERS.md     # Identity/Operations/Knowledge architecture (v2)
│   ├── ROADMAP.md
│   └── WOW-DEMO.md
├── lib/
│   └── memory.py           # 3-tier access + settings loader + CLI helpers (v2)
├── templates/
│   ├── inventory.md        # folder inventory muscle
│   ├── audit.md            # audit / dead-code muscle
│   ├── reviewer.md         # reviewer loop with dynamic triggers
│   ├── meta-block.md       # required META footer (incl. tools_used)
│   ├── spot-check.md       # mandatory artifact for [M]/[H] (v2)
│   ├── cost-report.md      # end-of-run cost + latency timeline (v2)
│   └── synthesis-gate.md   # 8-item pre-publish checklist (v2)
├── memory/                 # v2
│   ├── identity/           # stable facts (gitkept; user adds *.md)
│   ├── operations/         # per-run artifacts (gitignored)
│   └── knowledge/          # runs.sqlite (gitignored)
└── dashboard/              # OPTIONAL live monitor
    ├── app.py              # Flask + SSE backend
    ├── templates/index.html# Tailwind UI
    └── ...
```

## Using it

The skill auto-activates when Claude sees triggers: *"swarm"*, *"parallel agents"*, *"dispatch N haikus"*, *"fan out"*, *"multi-agent"*, *"brain and muscles"*, *"orchestrate"*, anything resembling a swarm / fan-out / parallel-agent pattern. It also fires on cost-efficient-bulk asks.

Or invoke explicitly: "use the swarm-orchestrator skill to audit this folder."

Run `/swarm-config` to set your preferences. Settings load silently at the start of every swarm (Step 0).

## The dashboard (optional)

The `dashboard/` component is a standalone Flask app that watches `~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl` and streams per-agent state to a Tailwind UI:

- Cards per agent with model-badge coloring (purple=Opus, blue=Sonnet, green=Haiku)
- Safety pill showing `[L] / [M] / [H]`
- Confidence pill colored by threshold (green ≥85%, amber 70–85%, red <70%)
- Live tool trace, expandable details, session grouping, search, sort
- Updates via Server-Sent Events — no polling, no reload

To run:

```bash
cd dashboard
python app.py
# browse http://127.0.0.1:5173
```

Requires Flask. The dashboard is observational — the swarm pattern works without it.

> **v2 note:** the dashboard does NOT yet render the new `tools_used` anomaly indicator. That's planned as a follow-up patch — see `RELEASE-v2.md` § "What's next."

## Cost benchmark

On the reference workload *"audit a 29K-file project in 5 sections"*:

| Approach | Cost | Wall time | Main context |
|---|---|---|---|
| Single Opus 4.7 1M Extra High | ~$50–100 | 12–15 min | ~300K tokens |
| This swarm framework | **~$1.80** | **~7 min** | **~30K tokens** |
| **Delta** | **~30–50× cheaper** | **~2× faster** | **~10× cleaner** |

See [`docs/COST-BENCHMARK.md`](docs/COST-BENCHMARK.md) for the math.

## When NOT to use

- Task needs one brain holding all context to spot cross-cutting patterns
- Every subtask requires Opus-tier judgment anyway
- Work is < 5 min and < 30K tokens — orchestration overhead beats the win
- Pure linear research (read 5 papers, write a position)

When in doubt, stay with single-Opus. This skill exists for the cases where parallelism actually pays.

## License

Personal use. If you find it useful, fork it.
