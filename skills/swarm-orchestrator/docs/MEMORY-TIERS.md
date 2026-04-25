# Memory Tiers — Identity / Operations / Knowledge

The orchestrator's memory architecture mirrors OpenClaw's three-tier model: each tier has its own storage, read API, write rules, and lifetime. The skill never accidentally treats Identity as ephemeral or Operations as permanent — separation is enforced by giving each tier a different access function in `lib/memory.py`.

## Why three tiers, not one flat MEMORY.md

A single flat memory file mixes:

- **Who you are** (Ron, runs Wirtgen+Bobcat fleet, prefers punchy synthesis) — should NEVER auto-overwrite
- **What you're doing right now** (current task, in-flight tool outputs, dispatch trace) — should evict in days
- **What you know from past runs** (cumulative diagnostic experience, indexed and searchable) — should grow forever, indexed for fast recall

When all three live in one file, the agent has to filter on every read, gets bloated context, and re-does past work because there's no fast retrieval over historical runs.

## The three tiers

### Identity

**What:** Stable facts about the user, agent persona, defaults that should rarely change.

**Storage:** `memory/identity/*.md`

Each file is a markdown document. Examples:
- `memory/identity/user.md` — who the user is, their role, their hardware
- `memory/identity/preferences.md` — output style, language preferences, escalation tolerance
- `memory/identity/personas.md` — agent personas the user has invoked

May symlink to existing `~/.claude/CLAUDE.md` and `~/.claude/projects/.../memory/MEMORY.md` so we don't break what works.

**Read API:** `identity.get(key)` returns the full markdown content.

**Write rules:** Curated only. The orchestrator NEVER auto-writes here. User edits via direct file edit, `/remember` slash command, or by approving an Identity-tier proposal in synthesis.

**Lifetime:** Forever, versioned by git.

### Operations

**What:** Ephemeral state of the current swarm run. Per-run dump of dispatch metadata, agent META blocks, intermediate artifacts.

**Storage:** `memory/operations/<session-id>/`

```
memory/operations/<session-id>/
  task.txt              # the user's original prompt
  agents/
    a-lightning.json    # full agent dispatch + return + META block
    b-gchat.json
    ...
  spot-check.md         # the artifact from Patch 3
  cross-link.md         # the artifact from Patch 4
  cost-report.md        # the artifact from Patch 6
  synthesis.md          # final orchestrator output
  cleanup.lock          # touched after promotion to Knowledge
```

**Read API:** 
- `operations.recent(n)` — list last N session dirs
- `operations.session(id).meta_blocks()` — all META blocks from that run
- `operations.session(id).artifact(name)` — read a named artifact (spot-check, cross-link, etc.)

**Write rules:** Auto-write during run. Each artifact (spot-check, cross-link, cost report, synthesis) gets dumped here at the moment it's produced.

**Lifetime:** `operations.ttl_days` (default 7). A daily cleanup script (cron / Windows Task Scheduler / Stop hook) deletes session dirs older than TTL **AND** that have a `cleanup.lock` (i.e., already promoted to Knowledge). Unlocked sessions stick around — they failed promotion and need investigation.

### Knowledge

**What:** Permanent indexed memory of completed swarm runs, searchable by full-text + vector + structured filters.

**Storage:** `memory/knowledge/runs.sqlite` (SQLite with FTS5 extension built-in; optional `sqlite-vec` extension for vectors)

**Schema:** see `lib/memory.py` for canonical version. Summary:

```sql
swarm_runs(
  id, date, recipe, task_summary, task_full,
  n_agents, total_tokens, total_cost_usd, wall_clock_min,
  anomalies_count, spot_checks_passed, cross_link_findings,
  reviewer_triggered, outcome, synthesis_summary, tags
)

swarm_runs_fts (FTS5 virtual table over task_full + synthesis_summary + tags)

swarm_runs_vec (vec0 virtual table, 384-dim embeddings of task_full)

swarm_agent_runs(
  run_id, agent_index, description, model, confidence,
  tokens, tool_uses, duration_sec, meta_block
)
```

**Read API:**
- `knowledge.search(query, limit=10, filters={})` — hybrid search returning ranked past runs
- `knowledge.recent(n)` — last N runs by date
- `knowledge.by_recipe(name)` — all runs of a given recipe
- `knowledge.run(id)` — full detail of one past run including per-agent rows

**Hybrid search formula:**
```
score = fts_weight * BM25(query, task_full + synthesis + tags)
      + vector_weight * cosine(query_embedding, run_embedding)
```
Lower is better. Weights are configurable in settings (defaults: 0.4 / 0.6).

**Write rules:** Append-only. Orchestrator promotes the current Operations dir to Knowledge at synthesis time:

```python
def promote(session_id):
    ops = operations.session(session_id)
    knowledge.insert({
        "id": session_id,
        "task_full": ops.task_text,
        ...all aggregated fields...
    })
    ops.touch_lock()  # marks as promoted; cleanup can now delete after TTL
```

**Lifetime:** Permanent. After 100 runs the SQLite is ~10 MB. After 1000 runs ~100 MB. Trivial.

## How the orchestrator uses the tiers

### Step 0.5 — Knowledge recall before dispatch

After settings load (Patch 9) but before agent dispatch:

```
1. Compute embedding of task description (skip if vectors disabled in settings)
2. knowledge.search(task) → top 5 similar past runs
3. If top result similarity > settings.memory.similarity_threshold (default 0.85):
     Surface to user: "We've run this before — see <session-id>, returned <synthesis_summary>"
     Offer 3 options:
       (a) Reuse — return past synthesis as-is, no swarm
       (b) Refine — use past as starting point, dispatch focused agents on gaps
       (c) Fresh — ignore past, full swarm from scratch
4. On user choice, proceed accordingly
```

### Step N — Promotion at synthesis time

After the synthesis gate (Patch 7) passes:

```
1. Write all artifacts to Operations dir (already done by individual patches)
2. knowledge.promote(current_session_id)
   - aggregates Operations/<id>/* into a single row
   - inserts into swarm_runs + computes embedding + populates FTS index
3. Touch cleanup.lock — Operations dir is now eligible for TTL cleanup
```

## Why this is safer than NotebookLM

NotebookLM is great for documents you've curated. It is NOT great for:
- Sub-second retrieval (queries take 2–8 seconds)
- Structured filters (you can't `WHERE recipe='research-brief' AND date > 2026-01-01`)
- Hybrid ranking (BM25 + vector + filters combined with custom weights)
- Local / offline use
- Versioning and diff

The Knowledge tier is local SQLite. It can be backed up by copying one file. It can be diffed by comparing two SQLite dumps. It is invisible to outside services.

## Settings that control memory

See `docs/SETTINGS.md` § Memory. Key knobs:
- `memory.enabled` — master switch
- `memory.search_on_dispatch` — disable Step 0.5 if you always want fresh
- `memory.knowledge.enable_vectors` — opt in to semantic search (requires sqlite-vec)
- `memory.operations.ttl_days` — how long to keep Operations dirs

## Privacy

Operations and Knowledge tiers are local files only. No network calls during read or write. The Knowledge index never leaves the machine unless the user explicitly copies the SQLite file. Settings can disable memory entirely (`memory.enabled: false`) for sensitive tasks.
