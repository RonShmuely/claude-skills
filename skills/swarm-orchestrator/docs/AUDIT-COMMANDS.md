# `/swarm-audit` — Command Handler Recipes

Step-by-step recipes the orchestrator follows when the user types `/swarm-audit <subcommand>` in any session. Mirrors the pattern of [ADDONS-COMMANDS.md](ADDONS-COMMANDS.md). All mutations land in `lab/` — never in the live skill — until `/swarm-audit promote` runs with explicit confirmation.

See [AUDIT-MODE.md](AUDIT-MODE.md) for the design rationale.

---

## `/swarm-audit feedback "<text>" [--tier=<t>] [--tags=<a,b>] [--rating=👍|👎]`

**Goal:** append one entry to `lab/feedback.jsonl` with current-session context auto-attached.

Steps:

1. Resolve `lab/` path: `~/.claude/skills/swarm-orchestrator/lab/`. Create if missing (with the structure documented in AUDIT-MODE.md §1).
2. Build the entry per the schema in AUDIT-MODE.md §2:
   - `ts` — current ISO-8601 UTC.
   - `session_id` — from `$CLAUDE_SESSION_ID` or current Claude Code session metadata.
   - `source` — `"slash"`.
   - `tier` / `tags` / `rating` — from CLI flags if provided, else null.
   - `free_text` — the quoted argument.
   - `context.last_dispatch_meta` — pull the most recent META block from the conversation if present; else null.
3. Atomic append: write to a temp file then `cat` onto `lab/feedback.jsonl` (single-line append; preserve JSONL invariant).
4. Confirm:
   > *"Logged. `lab/feedback.jsonl` now has `<N>` entries. Run `/swarm-audit status` for a summary."*

**Shortcut:** `/swarm-feedback "<text>"` is an alias — same recipe, defaults to no flags.

---

## `/swarm-audit replay <session-id> [--with=<path-to-skill.md>]`

**Goal:** re-run a past session's task under a proposed skill change, side-by-side with live, score blind.

Steps:

1. Resolve `<session-id>` from the operational log (`~/.claude/projects/.../sessions/<id>.jsonl`). If not found: *"Session `<id>` not found. List recent sessions with `/swarm-audit status --sessions`."*
2. Extract the original task prompt + dispatch META.
3. Resolve the proposed skill: `--with=` flag if given, else default `lab/proposed/SKILL.md`. If neither exists: *"No proposed skill to compare against. Make a change in `lab/proposed/SKILL.md` first or pass `--with=<path>`."*
4. Dispatch the task **twice in parallel** (DIRECT-PARALLEL path):
   - Agent A: live `SKILL.md`.
   - Agent B: proposed skill.
   - Both with identical preamble + cwd + tools.
5. After both complete, dispatch a **Sonnet reviewer** with both outputs labeled `option_1` and `option_2` (random assignment — reviewer doesn't know which is live). Reviewer scores: quality (1-5), correctness (pass/fail), notes.
6. Write report to `lab/replays/<session-id>_<ts>.json`:
   ```json
   {"session_id":"...","task":"...","live":{...},"proposed":{...},"reviewer":{...},"winner":"live|proposed|tie"}
   ```
7. Append to `lab/training/preferences.jsonl` if winner is decisive (not tie):
   ```jsonl
   {"task":"...","chosen":{...},"rejected":{...},"source":"replay","reviewer":"sonnet"}
   ```
8. Present a side-by-side summary table to user:

   | Metric | Live | Proposed |
   |---|---|---|
   | Cost (tokens) | ... | ... |
   | Time (s) | ... | ... |
   | BLOCKED? | ... | ... |
   | Reviewer score | x/5 | y/5 |
   | Winner | ... | ... |

   End with: *"Full report at `lab/replays/<file>`. Promote with `/swarm-audit promote`."*

---

## `/swarm-audit eval`

**Goal:** run the lab eval suite against `lab/proposed/SKILL.md`, report aggregate quality delta vs live.

Steps:

1. List canonical tasks: `lab/eval/tasks/*.md`. If empty: *"No eval tasks defined. Add canonical tasks to `lab/eval/tasks/` first. Each task is a small .md with `## Task`, `## Expected outcome shape` sections."*
2. For each task, dispatch under live skill AND under proposed skill (parallel, like replay).
3. Sonnet reviewer scores each output blind.
4. Write `lab/eval/runs/<ts>.json` with per-task + aggregate scores.
5. Compute deltas vs the last live-only run (cached).
6. Present:

   | Task | Live score | Proposed score | Δ |
   |---|---|---|---|
   | task-1.md | 4.2 | 4.5 | +0.3 |
   | ... | ... | ... | ... |
   | **Aggregate** | **4.0** | **4.3** | **+0.3** |

7. If aggregate Δ is negative or zero: *"Proposed skill is not an improvement. Review individual task scores before promoting."*
8. If positive: *"Proposed skill scores +`<Δ>` over live. Promote with `/swarm-audit promote`."*

---

## `/swarm-audit promote`

**Goal:** copy `lab/proposed/*` → live skill paths, commit, after explicit user confirmation.

Steps:

1. Compute diff: every file in `lab/proposed/` vs the same path in the live skill. Use `git diff --no-index` for clean output.
2. Require a recent eval pass:
   - Look for `lab/eval/runs/*.json` with timestamp within last 24h.
   - If none: *"No eval run within 24h. Run `/swarm-audit eval` first."*
   - If most recent eval shows negative aggregate Δ: *"Last eval shows proposed is worse. Refusing to promote. Override with `--force` (not recommended)."*
3. Count supporting feedback: every entry in `lab/feedback.jsonl` with `ts > <last-promotion-ts>`.
4. Show user:
   - The diff (paginated if long).
   - Last eval delta.
   - Supporting feedback count.
   - **Ask:** *"Promote `<N>` files? (y/N)"*
5. On `y`:
   - Copy each proposed file to its live path.
   - Stage + commit to `~/Desktop/claude-skills/` with message:
     ```
     skill: promote audit-mode proposal

     Eval delta: +<x>
     Supporting feedback entries: <N>
     Replay wins: <M>

     Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
     ```
   - Do NOT push (user pushes manually).
   - Confirm: *"Promoted. Live skill updated. `git push origin master` from `~/Desktop/claude-skills/` when ready."*
6. On `n`:
   - Move `lab/proposed/` → `lab/_archive/<YYYY-MM-DD>_rejected/`.
   - Write `lab/_archive/<...>/WHY.md` — ask user one line for the rejection reason.
   - Append `(chosen=live, rejected=proposed)` to `lab/training/preferences.jsonl` with `source: "promote_reject"`.
   - Confirm: *"Archived. Live skill unchanged."*

---

## `/swarm-audit weekly`

**Goal:** trigger the weekly self-review. Orchestrator picks the worst N sessions of the past 7 days, presents them for rating, harvests preference pairs.

Steps:

1. Query operational log for sessions where `ts > now-7d`.
2. Score each by signal stack:
   - `+2` per BLOCKED agent
   - `+3` per Mitigation #9 fail (artifact verification)
   - `+1` per escalation
   - `+5` per in-the-moment 👎 from feedback.jsonl
   - `+1` per cost spike vs session-cost median
3. Pick top N (default N=5, configurable via `--n=<k>`).
4. Present each one at a time:

   ```
   === Session 3 of 5 ===
   ID: <session-id>          Date: 2026-04-23
   Issues: 2 BLOCKED, 1 Mitigation #9 fail
   Task: <one-line summary>
   Dispatch: <tier> × <count>
   Outcome: <brief>

   What happened here? (free text, blank to skip)
   >
   ```

5. For each rated session, append one entry to `lab/feedback.jsonl` with `source: "weekly_review"`.
6. After all N reviewed, summarize:
   - Common failure patterns across the week (cluster by tags).
   - Suggested skill changes (write to `lab/proposed/SUGGESTIONS.md` — NOT to `lab/proposed/SKILL.md` directly; user reviews suggestions before mutating the proposed skill).
   - *"Weekly review complete. `<N>` entries logged. Suggestions at `lab/proposed/SUGGESTIONS.md`. Run `/swarm-audit eval` after applying any suggestion."*

**Auto-schedule:** if user wants weekly auto-trigger, suggest:
> *"Schedule with: `/schedule weekly /swarm-audit weekly` — fires every Monday morning."*

---

## `/swarm-audit status [--sessions]`

**Goal:** snapshot of audit-mode state.

Steps:

1. Read `lab/feedback.jsonl` — count total entries, count by source (slash/dashboard/weekly), count by rating (👍 vs 👎), top 5 tags.
2. Read `lab/replays/*.json` — count total replays, % won by proposed.
3. Read `lab/eval/runs/*.json` — most recent run timestamp + aggregate Δ.
4. Compute time since last `promote`.
5. Present:

   ```
   Audit-mode status
   ─────────────────
   Feedback entries:    142 (88 slash, 41 dashboard, 13 weekly)
   Ratings:             52 👍 / 31 👎 / 59 unrated
   Top tags:            wrong_tier (18), fabricated_artifact (12), good_dispatch (9), ...
   Replays:             7 total, proposed won 4 (57%)
   Last eval:           2026-04-25, Δ=+0.4 vs live
   Last promotion:      6 days ago (skill commit abc123)
   Pending in lab/proposed/: SKILL.md (modified), SUGGESTIONS.md (new)
   ```

6. If `--sessions` flag: append a list of the 10 most recent session IDs with one-line summaries (useful before `/swarm-audit replay <id>`).

---

## `/swarm-audit exit`

**Goal:** flip mode back to default.

Steps:

1. Read `~/.claude/swarm-orchestrator/settings.json`.
2. Set `mode: default` (or remove the key).
3. Atomic write.
4. Confirm: *"Audit mode off. Back to default lifecycle."*

---

## Error handling rules

- **Never write to live skill files** outside `/swarm-audit promote`. If a recipe tries to, abort and surface the bug.
- **Never delete.** Rejected proposals → `lab/_archive/`. Per the skill-wide "never delete only archive" principle.
- **Confirmation gates** for `promote` and `exit` (when there are unpromoted changes in `lab/proposed/`). No confirmation needed for `feedback`, `status`, `replay`, `eval`.
- **Quote stderr verbatim** when reporting failures.
- **Atomic writes** for `feedback.jsonl` and all settings — temp file + rename.
