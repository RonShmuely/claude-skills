---
name: wrapup
description: End-of-session wrap-up — triages stale open threads, saves key memories, writes a dated session summary, updates the open-threads ledger, uploads the summary to the user's AI Brain NotebookLM notebook, and periodically generates weekly/monthly roll-ups for layered memory. Trigger ONLY on explicit "/wrapup", "wrap up the session", "save this session", "end of session", or "session summary". Do NOT trigger on casual phrases like "wrap up this function" or "let's end here". Supports `/wrapup --rollup weekly` and `/wrapup --rollup monthly` for on-demand compression.
---

# Session Wrap-Up

Run this at the end of every session to capture what happened and commit it to long-term memory. The Brain is treated as a layered memory system (raw sessions → weekly roll-ups → monthly roll-ups), not a flat log.

## Trigger discipline

This skill writes memories, mutates a ledger, and uploads a source to NotebookLM — all leave persistent artifacts. Fire ONLY when the user clearly means "the whole session is ending". When unsure, ask: *"Do you want me to run a full session wrap-up (memories + ledger + Brain upload), or just summarize?"*

Roll-up modes (`--rollup weekly|monthly`) skip the per-session work and only produce the synthesized roll-up — see Step 7.

## Step 0: Locate the AI Brain notebook (strict, ID-first)

### 0a. Check for saved Brain notebook ID

Read the memory index (`MEMORY.md`) and look for an entry like `reference_brain_notebook.md`. If present, read the file and extract the notebook ID.

**If an ID is saved:** verify it still exists with `notebooklm list --json`. If it exists → use it. If it's gone → tell the user it was deleted and ask before creating a new one (don't silently recreate).

**If no ID is saved:** do NOT fuzzy-match on titles. Instead:
1. Run `notebooklm list --json` and show notebooks whose title exactly equals `"<Name>'s Brain"`, `"<Name>'s AI Brain"`, or `"AI Brain"`.
2. If there's exactly one exact match, ask: *"Use existing notebook '<title>' (<id>) as your Brain?"*
3. If multiple or zero exact matches, ask: *"No Brain notebook found. Create one now as '<Name>'s Brain'?"*
4. On confirmation, create with `notebooklm create "<title>" --json` and save the ID.

### 0b. Save the ID to memory (only when newly discovered/created)

Write `reference_brain_notebook.md`:
```markdown
---
name: Brain Notebook ID
description: NotebookLM notebook used by the wrapup skill to store session summaries and roll-ups
type: reference
---

Brain notebook: "<title>"
ID: <uuid>
Created/linked: <YYYY-MM-DD>
```

Then add to `MEMORY.md`:
```
- [Brain Notebook ID](reference_brain_notebook.md) — NotebookLM notebook where wrapup stores session summaries and roll-ups
```

## Step 1: Triage stale threads from the open-threads ledger

Before reviewing this session, surface anything that's been open too long so it gets decided, not silently carried forward.

### 1a. Read the ledger

Location: `$HOME/.claude/sessions/open-threads.md`. If it doesn't exist, create it with the schema below and skip to Step 2.

Schema:
```markdown
# Open Threads

## Active
- [YYYY-MM-DD] <thread text> (session: <session-file.md>)

## Done
- [YYYY-MM-DD opened → YYYY-MM-DD done] <thread text>

## Dropped
- [YYYY-MM-DD opened → YYYY-MM-DD dropped] <thread text> — reason
```

### 1b. Surface stale threads (>14 days old)

Compute age for every entry under `## Active`. If any are >14 days old relative to today, list them to the user:

> "Stale threads (opened > 14 days ago):
>  1) <text> — opened YYYY-MM-DD
>  2) <text> — opened YYYY-MM-DD
>
>  For each: keep / close (done) / drop (with reason)?"

Wait for the user's decision per thread. Apply moves (Active → Done or Active → Dropped) with today's date. If the user wants to defer all triage, that's fine — just note it and continue.

If no stale threads, skip silently.

## Step 2: Review the session

Look back through the entire conversation and identify:
- **Decisions made** — what was decided and why
- **Work completed** — what was built, fixed, configured, or shipped
- **Key learnings** — anything surprising or non-obvious that came up
- **New open threads** — anything left unfinished or to revisit next time
- **Closed threads** — anything that was open coming in and is now done
- **User preferences revealed** — new feedback about how the user likes to work

If there is nothing meaningful (e.g. a 2-turn Q&A), STOP and tell the user there's nothing worth a wrap-up. Don't force empty summaries or memories.

## Step 3: Save memories

Check the existing memory index and save or update memories as needed:
- **feedback** — corrections or confirmed approaches
- **project** — ongoing work, goals, deadlines, context future sessions need
- **user** — new info about the user's role, preferences, knowledge
- **reference** — external resources, tools, systems

Rules:
- Don't duplicate — update existing memories instead
- Don't save things derivable from code or git history
- Convert relative dates to absolute (e.g. "Thursday" → "2026-04-23")
- Include **Why:** and **How to apply:** for feedback and project memories

## Step 4: Write the session summary

Pick a stable, cross-platform sessions dir: `$HOME/.claude/sessions/` (works on Windows via Git Bash, macOS, Linux). Create it if missing.

### 4a. Pick a filename (robust per-day counter)

Today's date = `YYYY-MM-DD`. Glob `$HOME/.claude/sessions/session-YYYY-MM-DD*.md` and count:
- 0 matches → `session-YYYY-MM-DD.md`
- N matches → `session-YYYY-MM-DD-(N+1).md`

```bash
SESS_DIR="$HOME/.claude/sessions"
mkdir -p "$SESS_DIR"
DATE=$(date +%Y-%m-%d)
N=$(ls "$SESS_DIR"/session-"$DATE"*.md 2>/dev/null | wc -l)
if [ "$N" -eq 0 ]; then
  FILE="$SESS_DIR/session-$DATE.md"
else
  FILE="$SESS_DIR/session-$DATE-$((N+1)).md"
fi
```

### 4b. Write the summary

Format:
```markdown
# Session Summary — YYYY-MM-DD — <short topic>

## Topic
One sentence: what was this session about?

## What We Did
- Key work completed

## Decisions Made
- Key decisions and their reasoning

## Key Learnings
- Non-obvious insights

## New Open Threads
- Unfinished items (will be added to the ledger)

## Closed Threads
- Ledger items resolved this session

## Tools & Systems Touched
- Repos, services, CLIs, notebooks involved
```

Make the `# heading` include a short topic so future search/diff can distinguish sessions even when the filename collides. Save to the filename chosen in 4a — local summaries are the durable fallback if NotebookLM auth fails.

## Step 5: Update the open-threads ledger

Apply to `$HOME/.claude/sessions/open-threads.md`:

1. **New Open Threads** from the summary → append to `## Active` as `- [YYYY-MM-DD] <text> (session: <filename>)`
2. **Closed Threads** from the summary → move matching entries from `## Active` to `## Done` with `→ YYYY-MM-DD done` appended
3. **Triage outcomes from Step 1b** → apply if not already applied

The ledger is the single source of truth for "what's live". Individual session summaries record history; the ledger records state.

## Step 6: Dedup-check, then upload to the Brain

### 6a. Dedup by title

Before uploading, list existing sources:
```bash
notebooklm source list --notebook <BRAIN_ID> --json
```

By default the CLI uses the filename as the source title. If a source with the same title already exists, STOP and ask: *"A source named '<title>' already exists — upload as duplicate, skip, or rename?"*

Because Step 4b set a descriptive `# heading`, collisions on content are unlikely even with filename reuse, but dedup by title is still the hard gate.

### 6b. Upload

```bash
notebooklm source add "$FILE" --notebook <BRAIN_ID>
```

If `notebooklm` is not on PATH, fall back to `~/.notebooklm-venv/bin/notebooklm`.

## Step 7: Check roll-up triggers (progressive compression)

The Brain degrades as a memory when source count grows — retrieval has to span noise. Roll-ups add a synthesized layer so chat/search naturally favor denser entries. Raw sessions are KEPT, not replaced.

### 7a. Auto-detect trigger

After uploading the session, check:
- **Weekly:** is today Sunday (or the last day the user has been active this week) AND is there no Brain source titled `Weekly Roll-up — YYYY-Www` for the current ISO week? → ask: *"It's the end of the week — run a weekly roll-up now?"*
- **Monthly:** is today within the last 2 days of the month AND no `Monthly Roll-up — YYYY-MM` for the current month? → ask: *"End of month — run a monthly roll-up now?"*

Never auto-run. Always ask, because roll-up generation is rate-limited and takes 5–15 minutes.

### 7b. Explicit roll-up mode

If the skill was invoked with `--rollup weekly` or `--rollup monthly`, SKIP Steps 1–6 and go straight to 7c.

### 7c. Run the roll-up (subagent pattern — do NOT block the main conversation)

For a weekly roll-up:
1. List Brain sources and filter to session summaries whose date falls in the last 7 days (by title date prefix).
2. Collect their source IDs.
3. Spawn a background agent:
   ```
   Task(
     prompt="In Brain notebook <BRAIN_ID>, run:
       notebooklm generate report --format custom \
         -s <id1> -s <id2> ... \
         --append 'Synthesize these N session summaries into one weekly roll-up. Sections: Themes, Decisions, What Shipped, Open Threads Carried Forward. Cite session dates inline. Neutral tone, no fluff.' \
         --notebook <BRAIN_ID> --json
       Then: notebooklm artifact wait <artifact_id> --timeout 900 --notebook <BRAIN_ID>
       Then: notebooklm download report \"$HOME/.claude/sessions/rollup-weekly-YYYY-Www.md\" -a <artifact_id> --notebook <BRAIN_ID>
       Then: notebooklm source add \"$HOME/.claude/sessions/rollup-weekly-YYYY-Www.md\" --notebook <BRAIN_ID>
       Report the new source ID or any error.",
     subagent_type="general-purpose"
   )
   ```
4. Main conversation confirms the roll-up is running in the background and continues.

For a monthly roll-up, same pattern but:
- Filter to session summaries in the current calendar month
- Include that month's weekly roll-ups as sources too (so the monthly synthesizes the weeklies, not re-derives from raw)
- Filename `rollup-monthly-YYYY-MM.md`

### 7d. Roll-up failure handling

If generation fails (rate-limit, auth), the local file is absent but raw sessions are untouched. Tell the user and suggest retrying later with `/wrapup --rollup weekly`.

## Step 8: Confirm

Tell the user in 3–4 lines:
- Memories saved/updated (count + types)
- Summary file path + upload status (Brain source ID or skipped reason)
- Ledger delta (threads opened/closed/triaged)
- Roll-up status if applicable (running in background / skipped / not due)

Keep it brief. Don't read back the summary.

## Error handling

| Case | Action |
|------|--------|
| NotebookLM auth fails | Keep local summary + memories + ledger update. Tell user the summary is at `<path>` ready to upload later; re-run `notebooklm login`. |
| Brain ID in memory points to deleted notebook | Tell user, ask before creating. Update memory only after user confirms. |
| Duplicate title in Brain | Ask: upload / skip / rename. Never silently double-upload. |
| Nothing meaningful to save | Tell user, skip all writes. |
| `notebooklm` CLI not found | Try `~/.notebooklm-venv/bin/notebooklm`. If still missing: `pip install notebooklm-py`. |
| Ledger malformed | Back up to `open-threads.md.bak`, tell user, rebuild from today's summary. |
| Session dir unwritable | Fall back to OS temp dir and warn user the file won't persist. |
| Roll-up generation rate-limited | Log the failure, keep raw sessions intact, suggest retry with `--rollup` flag. |

## Prerequisites

Requires the NotebookLM CLI. See the NotebookLM skill for setup:
1. Install: `pip install "notebooklm-py[browser]"` then `playwright install chromium`
2. Authenticate: `notebooklm login` (or the headless login script on Claude Code)
3. First-run of this skill bootstraps the Brain notebook and ledger automatically.

## What this skill does NOT do

- Does not amend or delete prior session summaries or roll-ups
- Does not auto-run roll-ups without confirmation
- Does not share the Brain notebook
- Does not push to git or touch any project files
- Does not generate podcasts/videos/quizzes (those belong in explicit user requests)
