# Agent categories

The swarm-orchestrator framework involves agents in three distinct categories. Each has a constrained job; they are NOT interchangeable. Confusing them is how confident-shallow output happens.

## The three categories at a glance

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│   USER                                                                │
│    │                                                                  │
│    ▼                                                                  │
│   ┌────────────────────────────────────────────────────────────┐     │
│   │  ORCHESTRATOR  (the brain)                                  │     │
│   │  - The running Claude Code session itself                   │     │
│   │  - Tier: Opus (decisions about decomposition + synthesis)   │     │
│   │  - Decides what to dispatch + parses META back + synthesizes│     │
│   │  - NEVER reads raw files; only the typed META blocks        │     │
│   └────────────────────────────────────────────────────────────┘     │
│       │                    │                    │                     │
│       │ dispatches         │ summons when       │ summons on          │
│       │ work               │ no obvious seams   │ [H] safety          │
│       ▼                    ▼                    ▼                     │
│   ┌──────────┐      ┌─────────────────┐   ┌──────────────────┐       │
│   │ MUSCLES  │      │  SPECIALISTS    │   │  SPECIALISTS     │       │
│   │ (workers)│      │  (pre-dispatch) │   │  (post-dispatch) │       │
│   ├──────────┤      ├─────────────────┤   ├──────────────────┤       │
│   │ Haiku    │      │ Decomposer      │   │ Reviewer         │       │
│   │ Sonnet   │      │ (always Opus)   │   │ (Sonnet, [H] only)│       │
│   │ Opus     │      │ Decides cuts    │   │ Critiques what   │       │
│   │ each in  │      │ before any      │   │ muscles produced │       │
│   │ isolated │      │ muscle fires    │   │ + spot-checks    │       │
│   │ context  │      └─────────────────┘   └──────────────────┘       │
│   │          │                                                        │
│   │ One per  │      ┌────────────────────┐  ┌────────────────────┐   │
│   │ scope    │      │ Cluster summarizer │  │ Cross-cluster pass │   │
│   │          │      │ (Sonnet, N≥9)      │  │ (Sonnet, parallel  │   │
│   │ Returns  │      │ Compresses 5-7     │  │  with summarizers) │   │
│   │ typed    │      │ muscles into one   │  │ Surfaces           │   │
│   │ META     │      │ summary so final   │  │ contradictions +   │   │
│   │ block    │      │ synthesis isn't    │  │ integrations       │   │
│   │          │      │ overloaded         │  │ across clusters    │   │
│   └────┬─────┘      └────────┬───────────┘  └────────┬───────────┘   │
│        │                     │                       │                │
│        │                     │                       │                │
│        └──────────┬──────────┴───────────┬───────────┘                │
│                   │                      │                            │
│                   │ all results return   │                            │
│                   │ to the orchestrator  │                            │
│                   ▼                      ▼                            │
│              ┌──────────────────────────────────────┐                 │
│              │  ORCHESTRATOR — synthesis            │                 │
│              │  Composes final answer from typed    │                 │
│              │  outputs of muscles + specialists    │                 │
│              └──────────────────┬───────────────────┘                 │
│                                 │                                     │
│                                 ▼                                     │
│                              USER                                     │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Category 1 — The orchestrator (the brain)

**Who:** the running Claude Code session — *you*, when you have the swarm-orchestrator skill loaded. Not a dispatched agent. The parent process.

**Job:** decide what to dispatch, who runs each piece, parse the META blocks back, synthesize the final answer. Conductor, not player.

**Tier:** whatever the user's session runs on, ideally Opus — because decisions about decomposition and synthesis need real reasoning.

**Reads:** the user's request, the META blocks from muscles and specialists. Does NOT read the raw files muscles read — that's the entire point of context isolation.

**Failure mode if abused:** if the orchestrator tries to BE a muscle (reads files itself instead of dispatching), it loses context isolation and its own context fills with content it could have summarized via META.

## Category 2 — Muscles (the workers)

**Who:** dispatched `Agent()` calls (or `claude -p` subprocess calls in some runtimes). Each muscle is its own isolated Claude session with its own context window.

**Job:** do one narrow scope of work and return a typed META block summarizing what they found. Muscles do the actual reading, grepping, web-fetching, file edits — the real work.

**Tier:** picked per scope by the decomposer or by direct orchestrator routing.
- **Haiku** — narrow-and-structured (inventory a folder, run a regex, count occurrences)
- **Sonnet** — ambiguity / reasoning (audit for security issues, evaluate tradeoffs)
- **Opus** — judgment with consequence (architectural decisions, irreversible recommendations)

**Reads:** the files in their assigned scope only, with hard exclusions for what other muscles own. Muscles do NOT see what other muscles are doing — they only talk through the orchestrator via META blocks.

**Failure mode if abused:** Haiku on an ambiguous task returns "confident-shallow" output (the dominant failure mode named in `PROTOCOL.md`). Mitigation: tier escalation when confidence < threshold, plus the reviewer pass on `[H]` swarms.

## Category 3 — Specialists (the named single-purpose agents)

These exist for specific framework jobs, not for arbitrary user work. Each fires only when its specific condition is met.

### 3a. Decomposer (always Opus)

**Fires when:** the task has no obvious seams (greenfield design, fuzzy scope, no module boundaries). Triggered by seam-score below threshold.

**Job:** propose 2-3 candidate decompositions, score each on disjoint / exhaustive / same-shape / granularity, recommend one. Does NOT do the user's task — only decides how to cut it.

**Returns:** a typed artifact (recommended cuts, exclusions, rationale, per-scope tier hints). Never executes anything.

**Tier reasoning:** always Opus because decomposition IS the reasoning step. Tier discipline says default up when stakes are high; the cuts shape every downstream choice, so they get the most capable model.

### 3b. Reviewer (Sonnet, fires on `[H]` safety only)

**Fires when:** the swarm has been tagged `[H]` (high-stakes) by the orchestrator or user.

**Job:** adversarial critique of what the muscles produced. Re-checks high-stakes claims, spot-checks for fabrication, looks for cross-cutting issues the muscles missed, evaluates whether the cuts themselves were the right cuts.

**Returns:** a critique artifact with flagged claims, missing findings, suggested remediation. Does NOT rewrite the synthesis — that stays the orchestrator's job.

**Tier reasoning:** Sonnet is enough for most adversarial work. Escalates to Opus on its own low confidence.

### 3c. Cluster summarizer (always Sonnet, fires on swarms ≥9 muscles)

**Fires when:** synthesis input would exceed cognitive ceiling (composite trigger: token budget, findings count, seam-type diversity, or agent count). One cluster summarizer per cluster of ~5-7 muscles.

**Job:** compress N muscles' META blocks + bodies into one structured summary the final synthesizer can use without reading the originals. Surfaces conflicts within the cluster, flags fidelity loss, can refuse with `RECLUSTER_REQUEST` if cohesion is fake.

**Returns:** a META-bearing summary artifact with confidence + fidelity-loss grade + cross-cluster hooks for the cross-cluster pass.

**Tier reasoning:** never Haiku (same confident-shallow failure mode at the cluster level). Opus is overkill for ~6 META blocks of input.

### 3d. Cross-cluster pass (Sonnet, parallel with cluster summarizers)

**Fires when:** two-stage synthesis is happening AND there are 2+ clusters.

**Job:** sees ALL muscle META blocks but does ONE thing only — surface contradictions and integrations that span clusters. Does NOT summarize anything; does NOT recommend anything to the user. Pure cross-cutting pattern detection.

**Returns:** a list of contradictions, integrations, and distributed evidence. Allowed to return "no patterns found" with an honest explanation when clusters are genuinely disjoint.

**Tier reasoning:** Sonnet because pattern-finding across diverse inputs needs reasoning, but the scope is narrow enough not to need Opus. Runs in parallel with the cluster summarizers — adds ~1 minute wall time, no stacked latency.

## The one-line summary

**Orchestrator decides. Muscles do the work. Specialists handle decomposition, review, and synthesis-quality — each summoned only when needed.**

## Future — live version

This is the static rendering. A future dashboard will render the same shape live, with each box bound to the real-time state of the agents currently dispatched in a swarm. See `future-features/ideas.md` → "Live agent-category flowchart in dashboard" for the design sketch and dependencies.

Until then: this file is the canonical reference for which category an agent belongs to. When in doubt about which agent type a new framework feature should add (or why an existing agent is doing what it's doing), come back here.
