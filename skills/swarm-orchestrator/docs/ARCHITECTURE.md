# Architecture — Brain and Muscles

## The mental model

```
         ┌──────────────────────────────┐
         │   YOU (human)                 │
         └───────────────┬──────────────┘
                         │
         ┌───────────────┴──────────────┐
         │   OPUS ORCHESTRATOR (brain)  │
         │                              │
         │   - Decomposes the task      │
         │   - Picks model tier per     │
         │     subtask                  │
         │   - Dispatches muscles in    │
         │     parallel                 │
         │   - Parses META blocks       │
         │   - Escalates low-confidence │
         │   - Spot-checks claims       │
         │   - Synthesizes outputs      │
         └──┬──────┬──────┬──────┬──────┘
            │      │      │      │
        ┌───┴──┐┌──┴──┐┌──┴──┐┌──┴──┐
        │HAIKU ││HAIKU││HAIKU││SONNET│   ← muscles (parallel)
        │scope ││scope││scope││scope │
        │  A   ││  B  ││  C  ││  D   │
        └───┬──┘└──┬──┘└──┬──┘└──┬──┘
            │      │      │      │
            └──────┴──┬───┴──────┘
                     │
                structured
                output
                (META block)
                     │
                     ▼
          ┌────────────────────┐
          │  SONNET reviewer   │   ← only on [H] safety
          │  (adversarial)     │
          └────────┬───────────┘
                   │
                   ▼
          ┌────────────────────┐
          │  Merged synthesis  │
          │  (back to user)    │
          └────────────────────┘
```

The orchestrator is **you** — the Claude Code session the user is chatting with. Muscles are `Agent()` dispatches via the Task tool. Each muscle has its own isolated context; they do not share memory directly. They communicate back to the orchestrator via typed META blocks.

This is the **hierarchical decomposition pattern** from Hermes Agent and the **sub-agent pattern** from OpenClaw. The key property: **muscles don't talk to each other, they talk through the orchestrator.** That prevents telephone-game degradation at the cost of losing cross-muscle nuance (mitigated by the reviewer loop on high-stakes swarms).

## Why this works

### Parallelism

N independent muscles finish in max(t_1, ..., t_N) wall time instead of sum(t_1, ..., t_N). For a 5-way split, that's typically 2–3× faster than a sequential single-agent approach.

### Cost asymmetry

Haiku is ~15× cheaper than Sonnet which is ~5× cheaper than Opus. If 35% of a task is narrow enough for Haiku and 60% for Sonnet, using a single Opus for everything pays 10–30× more than the mix. The orchestrator (Opus) only handles the expensive-per-token reasoning work; muscles do the bulk tool-call grind at cheaper tiers.

### Context isolation

The orchestrator's context stays lean — it never reads the raw files the muscles read. Instead it receives a concise structured summary per muscle (~2–5K tokens each). After 5 muscles complete, the orchestrator's context has grown by ~20–30K tokens, not by the 300K+ a single-agent pass would accumulate.

### Observability

Each muscle is a discrete unit of work with a discrete output. You can kill one muscle without affecting the others. You can re-dispatch one without re-running the swarm. You can inspect one agent's tool trace in isolation. The dashboard makes this visible live.

## Why it can fail

### Confident-shallow output

Haiku on an ambiguous task returns a plausible-looking but thin report. The orchestrator receives the report via typed passing, has no access to the raw files the muscle read, and merges it into a polished synthesis. The merged output looks authoritative because the orchestrator writes well — but the underlying signal was weak.

**This is the dominant failure mode.** See `PROTOCOL.md` for mitigations.

### Cross-cutting insights lost

Insights that only emerge when you see everything at once are structurally unavailable to the swarm. Each muscle sees only its scope. The reviewer loop (high-stakes only) partially fixes this by sampling across scopes, but it's an 80% fix, not 100%.

### Orchestration overhead

For small tasks (<5 min, <30K tokens), the overhead of writing dispatch prompts + parsing META blocks + synthesizing > the speedup from parallelism. Use single-agent for small tasks.

## Decision flow at dispatch time

```
┌─────────────────────────────────────┐
│ Task received from user             │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ Is it parallelizable into N         │
│ independent narrow chunks?          │
└──────────────┬──────────────────────┘
        no│            │yes
          ▼            ▼
  ┌──────────┐   ┌──────────────────────┐
  │ Single   │   │ Does each chunk      │
  │ Opus/    │   │ need real judgment?  │
  │ Sonnet   │   └──────────────────────┘
  └──────────┘     │yes          │no
                   ▼              ▼
          ┌──────────────┐  ┌──────────────┐
          │ Sonnet swarm │  │ Haiku swarm  │
          └──────────────┘  └──────────────┘
                   │              │
                   └──────┬───────┘
                          ▼
             ┌────────────────────────────┐
             │ Pick safety: [L] / [M] /   │
             │ [H] based on consequence   │
             │ of being wrong             │
             └────────────┬───────────────┘
                          ▼
             ┌────────────────────────────┐
             │ Dispatch N muscles with    │
             │ explicit exclusions,       │
             │ META contract              │
             └────────────────────────────┘
```

## Relationship to OpenClaw and Hermes

| Concept | OpenClaw | Hermes Agent | This skill |
|---|---|---|---|
| Orchestrator | Main agent / Gateway | Core AIAgent | You (current session) |
| Workers | Sub-agents | Specialist workers | Agent() dispatches |
| Communication | Structured events | Typed result objects | META block in final text |
| Multi-channel | WhatsApp, Slack, Telegram | Local only | Dashboard + in-session |
| Persistence | Platform database | File-based | Claude Code transcripts |
| Review | Agent teams (SWAT, Mission Control) | Self-improving loop | Reviewer prompt template |

The skill is a subset of both. It does NOT try to be a full Gateway with multi-channel support. It stays in-session, using Claude Code's native Agent tool as the dispatch mechanism. If you want multi-channel later, graduate to a Flask-based orchestrator (see `docs/RECIPES.md` for the graduation path).
