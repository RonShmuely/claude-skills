# swarm-orchestrator

> Multi-agent swarm skill for Claude Code. One brain, N muscles, live dashboard.

## What this is

A Claude Code skill that turns any sufficiently-parallelizable task into a swarm: an Opus orchestrator decomposes, dispatches specialist muscles (Haiku for narrow work, Sonnet for reasoning, Opus for stakes), then synthesizes. Mirrors the **OpenClaw sub-agent mode** and **Hermes Agent hierarchical decomposition** patterns — but stays in-session, no separate Gateway process.

## Why it exists

Running a single Opus on large parallelizable tasks is **30–50× more expensive** and **2–3× slower** than a disciplined swarm. But a naive swarm has a failure mode that hurts: Haiku used on ambiguous tasks returns confident-shallow output that merges into a polished-looking-but-thin synthesis. Hard to detect, worse than missing.

This skill codifies the discipline to do it right:

1. **Tier-match the task** — Haiku for narrow-and-structured, Sonnet for reasoning, Opus for stakes
2. **Typed outputs with confidence** — every muscle emits a META block
3. **Escalate on low confidence** — `confidence < 0.7` triggers re-dispatch on Sonnet
4. **Spot-check claims** — orchestrator verifies a few specifics with its own tool calls
5. **Reviewer loop on high-stakes** — adversarial agent re-reads children + samples raw files

## Layout

```
swarm-orchestrator/
├── SKILL.md            # the skill Claude Code loads
├── README.md           # this file
├── docs/
│   ├── ARCHITECTURE.md     # brain + muscles model
│   ├── MODEL-TIERS.md      # Haiku/Sonnet/Opus/Ollama decision table
│   ├── PROTOCOL.md         # the 5 mitigations in detail
│   ├── COST-BENCHMARK.md   # framework vs single-Opus 1M
│   └── RECIPES.md          # reusable swarm patterns
├── templates/
│   ├── inventory.md        # folder inventory muscle
│   ├── audit.md            # audit / dead-code muscle
│   ├── reviewer.md         # reviewer loop muscle
│   └── meta-block.md       # the required META footer
└── dashboard/              # OPTIONAL live monitor
    ├── app.py              # Flask + SSE backend
    ├── templates/index.html# Tailwind UI
    ├── launch.bat
    ├── SWARM-PROTOCOL.md
    └── README.md
```

## Using it

The skill auto-activates when Claude sees triggers: *"swarm"*, *"parallel agents"*, *"dispatch N haikus"*, *"fan out"*, *"multi-agent"*, *"brain and muscles"*, *"orchestrate"*, anything resembling OpenClaw / Hermes patterns. It also fires on cost-efficient-bulk asks.

Or invoke explicitly: "use the swarm-orchestrator skill to audit this folder."

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
