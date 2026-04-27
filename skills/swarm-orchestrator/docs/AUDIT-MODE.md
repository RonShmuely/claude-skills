# Audit Mode — Improvement Lab

A meta-mode where the swarm turns inward. Its job stops being "do Ron's work" and becomes "improve itself." All mutations land in `lab/` and require explicit human promotion before touching the live skill.

> **Charter principle this serves:** *"The orchestrator becomes a self-improving system."* — see [PROJECT.md](../PROJECT.md) north-star.

---

## Activation

Three ways to enter audit mode:

1. **Slash:** any session, type `/swarm-audit <subcmd>`. Each subcommand auto-enters audit mode for the duration of that command.
2. **Settings flag:** `mode: audit` in `~/.claude/swarm-orchestrator/settings.json`. Sticks for the whole session.
3. **Weekly auto-trigger:** if `/swarm-audit weekly` is scheduled (via `/schedule`), it fires on its own and pings you with the worst-N sessions for review.

Audit mode never auto-deactivates mid-session — explicit `/swarm-audit exit` or the session ending.

---

## Components

### 1. Lab workspace — `~/.claude/skills/swarm-orchestrator/lab/`

```
lab/
├── README.md              ← orientation + safety rules
├── proposed/              ← mutation target — copy of the live skill, mutable
│   └── SKILL.md           ← (created on first proposed change)
├── feedback.jsonl         ← all feedback entries, append-only
├── replays/               ← per-replay reports
│   └── <session-id>_<ts>.json
├── eval/                  ← regression suite (canonical tasks)
│   ├── tasks/             ← one .md per canonical task
│   └── runs/              ← per-run scoreboards
├── dry-runs/              ← dispatch plans that didn't fire
├── training/              ← fine-tune-ready corpus (build now, use later)
│   ├── dispatch-pairs.jsonl     ← (task, dispatch_decision, outcome)
│   └── preferences.jsonl        ← (chosen, rejected) pairs from your promote/reject
└── _archive/              ← rejected proposals, archived not deleted
    └── <YYYY-MM-DD>_<reason>/
```

Safety rules (enforced by every audit command):
- **Never modify files outside `lab/`** until `promote` runs and you confirm.
- **Never delete.** Rejected proposals → `lab/_archive/`. Per the global "never delete only archive" principle.
- **Never write fabricated data.** Eval scores come from real reviewer runs, not estimates.

### 2. Feedback intake — three paths, one ledger

Every feedback entry, regardless of path, ends up as one JSONL line in `lab/feedback.jsonl`. Schema:

```jsonl
{
  "ts": "2026-04-26T18:23:00Z",
  "session_id": "abc-123",
  "source": "slash" | "dashboard" | "weekly_review",
  "tier": "haiku" | "sonnet" | "opus" | null,
  "tags": ["fabricated_artifact", "wrong_tier", "good_dispatch", ...],
  "rating": "👍" | "👎" | null,
  "free_text": "haiku fabricated success on the file write — should've gone DIRECT path",
  "context": {
    "last_dispatch_meta": { ... },           ← auto-attached if available
    "agent_card_id": "...",                  ← present for dashboard source
    "weekly_session_summary": "..."          ← present for weekly source
  }
}
```

**Path A — `/swarm-feedback "<text>"` slash command**
- Works in any session. Appends one entry, source=`slash`.
- Auto-attaches the most recent dispatch META to `context.last_dispatch_meta`.
- Zero friction. Use when you remember to flag something while working.

**Path B — Dashboard inline (`/cockpit` and `/theater`)**
- Every agent card gets a 👍/👎 + free-text box.
- Click writes one entry, source=`dashboard`, with `agent_card_id` and the agent's full output snapshot in `context`.
- Captures reactions in the moment, while you watch the swarm run.

**Path C — Weekly review (`/swarm-audit weekly`, optionally scheduled)**
- Orchestrator queries the operational log for the past 7d.
- Picks the **worst N** sessions by signal: BLOCKED rate, Mitigation #9 fail rate, escalation count, your in-the-moment 👎s, cost spikes.
- Presents one at a time: shows the dispatch + outcome + asks "what happened here?"
- Each rating becomes one entry, source=`weekly_review`. Multi-line free-text encouraged.

### 3. Replay harness — `lab/replays/`

`/swarm-audit replay <session-id> [--with=<lab-skill-path>]` does:

1. Read the past session's task + dispatch META from the operational log.
2. Re-dispatch the same task **twice** in parallel: once under live `SKILL.md`, once under `lab/proposed/SKILL.md`.
3. Score both with a Sonnet reviewer (blind — doesn't know which is which).
4. Write a side-by-side report to `lab/replays/<session-id>_<ts>.json`: cost, time, BLOCKED rate, reviewer score, diff of outputs.
5. Optionally append the (live, proposed) pair to `lab/training/preferences.jsonl` keyed by reviewer preference.

### 4. Eval harness — `lab/eval/`

Canonical tasks live in `lab/eval/tasks/*.md`. Each is a small, well-defined dispatch problem with a known-good outcome shape.

`/swarm-audit eval` runs every task under `lab/proposed/SKILL.md`, scores each with a Sonnet reviewer, writes a run scoreboard to `lab/eval/runs/<ts>.json`, and reports the aggregate quality delta vs the last live-skill run.

The regression suite grows over time — every time you reject a promotion because of a specific failure, that failure becomes a new canonical task.

### 5. Promotion gate — `/swarm-audit promote`

1. Compute diff: `lab/proposed/SKILL.md` vs live `SKILL.md`. Same for any other proposed file.
2. Require a recent eval pass (within 24h). If none, refuse and tell user to run `/swarm-audit eval` first.
3. Show: diff + last eval delta + count of supporting feedback entries.
4. Ask: *"Promote? (y/N)"*. No silent promotions.
5. On `y`: copy `lab/proposed/*` → live, commit to `claude-skills` repo with a generated message that cites the supporting feedback entries.
6. On `n`: move the proposed change to `lab/_archive/<date>_rejected/` with a `WHY.md` capturing the rejection reason. Add a `(chosen=live, rejected=proposed)` entry to `lab/training/preferences.jsonl`.

### 6. Training-data exporter (built now, used later)

Two files grow continuously, regardless of whether you're in audit mode:

- `lab/training/dispatch-pairs.jsonl` — every real dispatch + outcome. Format:
  ```jsonl
  {"task": "...", "dispatch": {"tier":"haiku","prompt":"..."}, "outcome": {"status":"DONE","artifact_verified":true,...}, "session_id":"..."}
  ```
- `lab/training/preferences.jsonl` — every promotion decision + every replay-pair scored by reviewer. Format:
  ```jsonl
  {"task":"...", "chosen": {...}, "rejected": {...}, "source": "promote|replay", "reviewer":"sonnet"|"human"}
  ```

These are useless today. They are exactly the format Anthropic-style fine-tuning (or any preference-tuning pipeline) wants. The day fine-tuning opens for Opus, you ship months of Ron-flavored preference data on day one.

---

## Future: Supabase backend (deferred)

You have one Supabase project: **MachineGuides** (`xuzalbnhcauulpvnxgnk`, ap-northeast-1). For audit-mode the **default is local-first** — JSONL files synced via the `claude-skills` GitHub repo. This matches the charter's "single-user, local-only" principle.

If/when audit-mode outgrows local files (cross-device live feedback, dashboard inline reactions from laptop while PC runs the swarm, real-time leaderboards across devices), the upgrade path is:

- **Option A:** Add an `audit` schema to the existing MachineGuides project. One project, two schemas. Cheap.
- **Option B:** New Supabase project `swarm-orchestrator-lab`. Cleaner boundary, but two projects to manage.

Tables would mirror the JSONL shapes one-to-one: `feedback`, `dispatch_pairs`, `preferences`, `replays`, `eval_runs`. RLS off (single-user). No auth (local network only).

**Decision deferred until JSONL volume or cross-device need forces it.** Don't pre-build.

---

## What audit-mode is NOT

- **Not real model training today.** It produces training-shaped data; it does not run gradient updates. The corpus is the long-term play.
- **Not autonomous improvement.** Every change requires your "ship it." The orchestrator suggests; you decide.
- **Not a replacement for the regression suite living in `regression-suite/`.** Audit mode complements it — `regression-suite/` is the hand-curated test bench; `lab/eval/` is the auto-grown one fed by failed promotions.
- **Not a place for production secrets.** Lab is single-user, local. Don't put real API keys or customer data in feedback entries.

---

## Versioning

Audit-mode lands in skill version `2.3.0`. CHANGELOG entry will be added on first commit of the lab scaffold.
