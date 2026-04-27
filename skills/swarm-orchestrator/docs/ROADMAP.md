# Roadmap — from here to there

The north-star plan for evolving the swarm framework into an always-on, multi-channel, self-improving local orchestrator.

Target stack: **antigravity + claudecode** dispatch surfaces, plus the swarm framework's discipline (model-tier selection, 9 mitigations, ship-don't-ask preamble). No visual canvas. Recipes stay as markdown + code (version-controlled, diff-able, syncable). No Ollama tier — Haiku rates are cheap enough that the $50–200/yr cost is trivial vs the engineering overhead of maintaining a local model integration. Four tiers: Opus orchestrator, Opus heavy muscle, Sonnet specialist, Haiku swarm.

---

## Current state

**Done:**
- Claude Code as execution engine, Agent tool dispatch
- swarm-orchestrator skill shipped to the public `claude-skills` repo
- 5 docs (ARCHITECTURE, MODEL-TIERS, PROTOCOL, COST-BENCHMARK, RECIPES)
- 4 prompt templates (meta-block, inventory, audit, reviewer)
- SWARM-PROTOCOL dispatch playbook with 5 mitigations
- Typed outputs + confidence + safety pills
- 3-mode dashboard (Dashboard / Theater / Compact) — built, not yet pushed
- Wow-demo / Week-Start-Triage flagship recipe
- Cost benchmark: ~$1.80 swarm vs ~$50–100 single-Opus 1M for same workload

**Missing:**
- Multi-channel adapter (Telegram bot → phone ingress)
- Persistent memory across sessions (beyond MEMORY.md)
- Scheduled triggers (cron-like autonomous runs)
- Self-improvement loop (pattern detection → recipe promotion)
- Natural-language shell ("just tell it what you want")

---

## Pre-sprint — close current loops (1–2 hrs)

Before any new building:

| Task | Time | Why |
|---|---|---|
| Push integrated 3-mode dashboard to claude-skills | 5 min | Close outstanding repo work |
| Junction-install skill into `~/.claude/skills/` | 2 min | Auto-activation on cold sessions |

---

## Sprint 1 — Foundation (4–6 hrs)

**Persistent cross-session memory.**

- Storage: SQLite at `~/.claude/swarm/history.db`
- Tables: `sessions`, `agents`, `swarms`, `findings`, `confidence_history`
- Orchestrator writes each swarm outcome + META data on completion
- Dashboard: new "Timeline" mode showing past 30 days of swarms grouped by day
- Retrieval helper function in skill: `recall_past_runs(path, days=30)` — skill prompts can query historical context

**Ships:** foundation for pattern detection. Can't do Sprint 3 (self-improvement) without this.

---

## Sprint 2 — Channel (8–12 hrs)

### Phase 3 — Scheduler (4–6 hrs)

- Long-running Python daemon with `schedule` library (or Windows Task Scheduler — pick one, stick with it)
- `triggers/` folder in skill: `.yml` specs per trigger
- Trigger types: **cron schedule**, **filesystem watcher** (via `watchdog`), **webhook** (local endpoint)
- Example spec: *"every Monday 7 AM → fire Week-Start Triage → Telegram the result"*
- Dashboard: "Scheduled" panel showing next-fire times for each trigger
- **Ships:** the system works when you don't

### Phase 4 — Telegram adapter (4–6 hrs) *(depends on Sprint 1)*

- BotFather token; hardcode your Telegram user ID as the only authorized sender (critical — reject all others)
- `python-telegram-bot` library → local Flask endpoint `/command`
- Flask spawns `claude -p "<prompt>"` headless subprocess; streams back via message edits to Telegram
- Voice-to-text via Telegram's native transcription (or Whisper local)
- Dashboard: "Channels" section showing active bots + recent ingress
- **Ships:** orchestrator reachable from anywhere with cell signal

---

## Sprint 3 — Intelligence (8–12 hrs) *(depends on Sprints 1 + 2)*

**Self-improvement librarian.**

- Sonnet librarian agent fires nightly via the scheduler
- Reads last 7 days of `history.db`
- Detects patterns:
  - *"you ran folder-audit on 4 folders this week → want a shortcut recipe?"*
  - *"these 3 memory rules could be consolidated"*
  - *"this muscle has returned `not_checked: ['hebrew OCR']` five times → add OCR step to its prompt"*
- Proposals land in Telegram as approve/reject inline buttons
- Approved proposals auto-commit to `claude-skills` repo with attribution
- **Ships:** the capstone — the system improves itself

Do not ship Sprint 3 until you've used Sprints 1+2 for ≥2 weeks. The librarian needs real pattern volume to find anything interesting; running it on synthetic data wastes money and gives bad suggestions.

---

## Sprint 4 — Polish (optional, 4–6 hrs)

**Natural-language shell.**

- Dashboard top bar: one-line text input — *"tell the orchestrator what you want"*
- Input → Claude Code classifier → selects skill/recipe → dispatches
- Learns over time which phrasings map to which skills (via `history.db` queries)
- Same input surface works from Telegram (already does after Sprint 2 — this polishes the UI version)
- **Ships:** the antigravity veneer — "just talk to it"

---

## Critical path + parallelism

```
Pre-sprint  →  Sprint 1  →  Sprint 2 Phase 3  →  Sprint 2 Phase 4  →  Sprint 3  →  Sprint 4
  1-2 hrs      4-6 hrs      4-6 hrs              4-6 hrs              8-12 hrs     4-6 hrs
```

Parallelism opportunities:

- Sprint 2 Phase 3 and Phase 4 can interleave (scheduler + Telegram are independent modules)
- Sprint 4 can ship at any point after Sprint 2 Phase 4

**Total estimate:** ~25–38 hrs of focused build time, +/- 30%.

---

## Tradeoffs to decide up front

Decide once, don't retrofit later:

| Decision | Options | My pick |
|---|---|---|
| Memory backend | SQLite (structured, queryable) vs JSONL append-log (dumb, durable, grep-able) | **SQLite** — pattern detection needs joins and aggregations |
| Scheduler | Windows Task Scheduler (native, annoying) vs Python daemon (portable, you manage it) | **Python daemon** — portable across machines via Drive Mirror sync |
| Voice input | Telegram native vs Whisper local vs skip | **Telegram native** for v1, Whisper if quality insufficient |
| Self-improvement trust | Auto-commit proposals vs require approval for every change | **Approval-required** until you trust the librarian, then opt-in auto-commit per proposal type |

---

## Where I'd start if the time were mine

1. **Pre-sprint today** (1–2 hrs) — dashboard push + skill junction. This is not optional.
2. **Sprint 1 tomorrow** (4–6 hrs) — memory store is the foundation for everything meaningful after.
3. **Sprint 2 Phase 4 before Phase 3** — get the "feels different" hit from Telegram first. The scheduler adds value but isn't viscerally different. Telegram is.
4. **Use the system for 2 weeks before Sprint 3** — don't build the librarian until you have real patterns for it to find.
5. **Sprint 4 is optional** — natural-language shell is nice but Telegram voice already gives you 80% of it.

---

## Explicit non-goals

- **No Ollama integration.** Haiku is cheap enough. The engineering cost of a local model integration exceeds the $50–200/yr API savings.
- **No visual canvas (n8n-style).** Recipes stay as markdown + code for version control and sync.
- **No multi-user support.** Single-operator system. Telegram bot hardcodes one authorized user ID.
- **No cloud hosting.** Everything runs local on your machine. The claude-skills repo is the only network dependency (and that's just for sync across your own machines).
- **No replacement of Claude Code as the execution engine.** Claude Code IS the orchestrator runtime. The adapters layer on top.

## When this roadmap is "done"

When:

- `Swarm Monitor.lnk` on your desktop opens a live dashboard showing agents fired by Telegram, CLI, scheduled triggers, and in-chat orchestration — all in one view.
- Monday morning, your phone buzzes with the week-start triage result before you open your laptop.
- You haven't manually run a folder-audit recipe in 3 weeks because the scheduler is doing it.
- The librarian has proposed 2–3 recipe promotions you actually accepted.
- You're spending ~$15/week on API calls, same as you were before this roadmap, because the swarm is cheaper per-task than single-Opus would have been.

That's the endgame. Nothing fancier required.
