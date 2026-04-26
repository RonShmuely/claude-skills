# `/swarm-help` — Master command + mode reference

The orchestrator renders this file when the user types `/swarm-help` (or `/swarm-help <topic>` for a focused view). Keep it skim-friendly. One source of truth — every other command doc links here.

---

## Quick reference

```
/swarm-help                 ← this card
/swarm-help <topic>         ← deep-dive on one topic (e.g. /swarm-help audit)

/swarm-addons <subcmd>      ← addon registry: list / info / enable / disable / doctor / learn / install / remove
/swarm-audit <subcmd>       ← improvement lab: feedback / replay / promote / weekly / status
/swarm-feedback "<text>"    ← shortcut: append a feedback entry tied to the current session
```

---

## Modes

The orchestrator runs in one of these modes per session. Mode is set by the user explicitly (`mode: <name>` in skill settings, or implicit by command).

| Mode | When | What changes |
|---|---|---|
| **default** (operator) | You're using the swarm to do work. | Standard lifecycle. Real dispatch. Real artifacts. |
| **audit** | You're improving the swarm itself. | All mutations land in `lab/`, never the live skill. Eval harness runs on every proposed change. Promotion gated by your explicit "ship it". See `/swarm-help audit`. |
| **theater** | You want to watch the swarm think. | Dashboard at `:5173` opens to `/theater` view. No orchestrator behavior change — view-only. |
| **cockpit** | Active ops session, multi-agent dispatch. | Dashboard opens to `/cockpit` (status + dispatch composer). |
| **dry-run** | You want a dispatch plan without firing. | Orchestrator decomposes + writes the planned dispatch to `lab/dry-runs/<ts>.json`. Nothing runs. |

---

## Commands by area

### Lifecycle (built-in, not addon-gated)

| Command | What it does |
|---|---|
| `/swarm-help [topic]` | This reference. Topics: `addons`, `audit`, `modes`, `tiers`, `dispatch`, `memory`. |
| `/swarm-status` | Show: current mode, active addons, recipes-cache hit rate (last 7d), Mitigation #9 verifications passed/failed. |
| `/swarm-feedback "<text>"` | Append a feedback line to `lab/feedback.jsonl` with current session ID + last dispatch context auto-attached. Works in any mode. |

### Addons (`/swarm-help addons`)

See [ADDONS-COMMANDS.md](ADDONS-COMMANDS.md). Summary: `list` · `info <n>` · `enable <n>` · `disable <n>` · `doctor` · `learn <repo>` · `install <src>` · `remove <n>`.

### Audit / improvement lab (`/swarm-help audit`)

See [AUDIT-COMMANDS.md](AUDIT-COMMANDS.md). Summary:
- `feedback "<text>"` — same as `/swarm-feedback`, scoped to lab.
- `replay <session-id> [--with=<lab-skill-path>]` — re-run a past session under a proposed skill change.
- `eval` — run the regression suite against `lab/proposed/SKILL.md`. Returns aggregate quality delta vs live.
- `promote` — diff `lab/proposed/` against live, ask for confirmation, copy + commit.
- `weekly` — fire the weekly self-review: orchestrator picks the worst N sessions of the past 7 days, presents them to you for rating, harvests preference pairs.
- `status` — show: open feedback count, pending replays, last eval delta, last promotion timestamp.

---

## Model tiers (`/swarm-help tiers`)

| Tier | Use for | Don't use for |
|---|---|---|
| **Opus orchestrator** | Coordination, decomposition, synthesis. Always 1 per session. | Anything else. |
| **Opus heavy muscle** | Decisions with real consequence. 1-3/day. | Greps, counts, inventories. |
| **Sonnet specialist** | Code, browser, reasoning, bounded tasks. ~60% of muscle work. | Open-ended exploration; ambiguous tasks. |
| **Haiku swarm** | Counts, greps, classifications, file lists. 5-10 in parallel. | Anything ambiguous. Anything requiring judgment. |

Default rule: **when in doubt, go up one tier.** See `MODEL-TIERS.md` for the full matrix.

---

## Dispatch paths (`/swarm-help dispatch`)

`DIRECT` (default) · `DIRECT-PARALLEL` · `DIRECT-BACKGROUND` · `DASHBOARD`. File-write tasks force `DIRECT`. See `RUNTIME-ADAPTERS.md` for cross-runtime details (Antigravity, headless `claude -p`).

---

## Memory tiers (`/swarm-help memory`)

1. **Skill** — `SKILL.md`, `PROJECT.md`, preambles. Constant identity.
2. **Recipes registry** — `provisional` → `validated` → `stale`.
3. **Operational log** — `cuts-log.jsonl`, `audit-deltas.jsonl`, per-session events.
4. **Promoted Knowledge** — librarian-curated cross-session patterns.

See `MEMORY-TIERS.md`.

---

## Don't see what you need?

- All non-trivial behaviors live in `docs/` next to this file. `ls ~/.claude/skills/swarm-orchestrator/docs/` lists every reference doc.
- For a one-line "what is this project" answer, see [PROJECT.md](../PROJECT.md).
- For changes, see [CHANGELOG.md](../CHANGELOG.md).
- For where it's heading, see `ROADMAP.md`.
