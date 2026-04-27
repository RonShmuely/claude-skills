# swarm-orchestrator — Project Definition

> A skim-and-discuss doc. Three layers, timeless: TL;DR on top, charter in the middle, "how it works at a glance" reference card at the bottom. Status/WIP belongs in CHANGELOG.md and ROADMAP.md, not here.

---

## TL;DR

A **discipline-first multi-agent framework** for Claude Code. Decomposes one big task into many small ones, dispatches the right model tier for each, watches them in a live local dashboard, and synthesizes results — with safety rails so the cheap models can't quietly produce confident-shallow garbage and so cross-runtime dispatch (Antigravity, headless `claude -p`) inherits the same discipline.

- **What it is:** A loadable skill (`swarm-orchestrator`) + a local Flask dashboard + a layered memory system + a runtime-adapter pattern for non-Claude-Code platforms.
- **Who it's for:** A solo operator (Ron) who needs to do parallel work — audit N folders, classify K items, run M searches — without burning Opus on every step or trusting Haiku on ambiguous ones.
- **Why it matters:** Naive parallel dispatch fails silently. The framework's value is the *discipline* (model-tier selection, artifact verification, preamble injection, escalation, reviewer loop) — not the dispatch itself.

---

## Charter

### Problem

Multi-agent dispatch in Claude Code defaults to whatever model is in front of the orchestrator and whatever shape its natural prompt takes. The pathologies stack:

- Haiku silently fails on ambiguous tasks with confident-shallow output.
- Opus burns budget on greps and inventories that Haiku could do.
- Agents fabricate success-shaped output when blocked, and the orchestrator believes them.
- Cross-runtime dispatch (Antigravity, headless `claude -p`) loses preamble context — even Opus regresses to asking 3-way questions.
- The orchestrator can't see what its own swarm did, so failure post-mortems are guesswork.
- Hebrew/RTL output rules get dropped when the *input* happens to be English.

### Goal

Make a swarm produce work **at least as good as** the orchestrator would alone, at **meaningfully lower cost and time**, and make that property survive across:

- **Runtime** — Claude Code native, Antigravity, headless `claude -p` adapter.
- **Operator skill** — the discipline lives in the skill, not in the human's vigilance.
- **Agent failure modes** — verification + escalation + reviewer loop, not trust.

### In scope

- Model-tier selection rules + escalation triggers.
- Decomposition seam-detection + cuts cache (decomposer muscle, in flight).
- Dispatch preamble (en/he), permission posture, cwd handling per runtime.
- Artifact verification (Mitigation #9): on-disk presence + size before any DONE.
- Reviewer loop, cross-pollination, synthesis quality gate.
- Live local dashboard (Flask + SSE, observer-only) with Dashboard / Theater / Cockpit / Compact / Dispatch composer modes.
- Layered memory: skill → recipes registry → operational log → promoted Knowledge.
- Hebrew/RTL output rules baked into the preamble (regardless of input language).

### Out of scope

- Multi-user / SaaS / hosted dashboard (single-user, local-only, no auth, no egress).
- Network telemetry, outside calls from the dashboard or the skill.
- Fully-autonomous orchestrator running without a human at the wheel.
- Cross-account / cross-org agent dispatch.
- Replacing the Opus orchestrator with a smaller-model orchestrator. The brain stays Opus.
- Public release as a standalone product. Public surface goes through Hive SaaS, not this skill in isolation.

### Success criteria

1. **Quality parity** — A randomly-sampled swarm output, reviewed blind, scores ≥ a single-Opus run on the same task.
2. **Cost discipline** — Median session uses ≤ 35% Opus tokens and ≥ 35% Haiku tokens, with ≥ 60% of tasks correctly tier-routed on the first dispatch (no escalation needed).
3. **No silent failures** — Every BLOCKED agent surfaces as BLOCKED in the dashboard, never as fabricated success. Every artifact claim verified on disk before any report.
4. **Cross-runtime parity** — A swarm dispatched from Antigravity or a headless adapter produces the same Hebrew/RTL output, the same preamble discipline, the same reviewer loop as one dispatched in Claude Code.
5. **Decomposer pays for itself** — When fired, decomposer adds ≤ 1 Opus call of overhead, and cache hit rate exceeds 50% within a workspace's first month of use.

### Core principles (non-negotiable)

- **Quality = model-selection discipline.** Default up a tier when in doubt.
- **Skills are loadable capabilities, not personalities.** The orchestrator loads `swarm-orchestrator` on intent and unloads on context shift.
- **Handoffs to files, never inline.** Cumulative context cost makes inline ~4× more expensive than file-based.
- **No "luck" framing.** When the swarm catches or misses something, credit/blame the *mitigation*, never vigilance.
- **No vibes-based thresholds.** Soft labels + sample weighting + bootstrap calibration; never uncalibrated hard cutoffs.
- **Verify artifacts before trusting reports.** Agents fabricate success-shaped output when blocked.
- **Hebrew/RTL rules fire on output content, not input language.** Both en + he preambles carry identical Hebrew-output rules.
- **Never delete, only archive.** Cleanup moves to `_archive/<date>_<reason>/`.
- **No fabricated data.** No invented percentages / confidence / statistics — derive from documented weights only.

### Audience

- **Primary:** Ron, in two simultaneous roles — *operator* running real work (welding R&D, milling-fleet diagnosis, mom's Wix project, folder audits) and *tool-builder* iterating on the framework itself.
- **Secondary:** Future-Ron on a different machine. Cross-device sync via the `claude-skills` GitHub repo gives the same Claude personality, same skill, same dashboard on PC and laptop.
- **Not the audience (yet):** Other users. Any public surface is downstream of Hive SaaS, not this skill on its own.

### Dependencies

- **Claude Code** — primary runtime; native `Agent()` tool for in-session dispatch.
- **Anthropic API** — Opus / Sonnet / Haiku access via Claude Code.
- **Local Python + Flask** — dashboard on `http://127.0.0.1:5173` (no external bind, no auth, no telemetry).
- **`claude-skills` GitHub repo** — cross-device sync of skill, memory, plans, inspectors.
- **Optional adapters** — Antigravity workspace `AGENTS.md`, headless `claude -p` shell-out, with `--dangerously-skip-permissions` posture per tier.

### Known fragility (risks the design has to keep handling)

- Headless dispatch without the explicit ship-don't-ask preamble degrades even Opus into 3-way questions → preamble injection is mandatory, not optional.
- PowerShell stream-idle-timeout on long-running agents → locked workaround in the headless-quirks reference; cannot regress.
- Artifact verification depends on agents writing to predictable paths → file-write tasks force the DIRECT dispatch path.
- Decomposer cache poisoning → two-strikes-poisoned + fresh-decomposer-with-poison-context handles it, but the protocol is unproven at scale.
- Skill-trigger drift as Claude Code evolves → trigger description tested today, but no contract; needs periodic re-validation.
- Memory tier explosion → without librarian pruning, recipes registry will grow unbounded and dilute hit rate.

### North-star

The orchestrator becomes a **self-improving** system. Every session writes to the operational log → recipes get promoted `provisional → validated` based on downstream outcome → the librarian agent prunes stale entries → the next session's decomposer fires fewer times because cache hit rate climbs. The human's job shrinks to: *state intent, review synthesis, occasionally override the cache.*

---

## How It Works At A Glance (timeless reference card)

### Model tiers (4)

| Tier | Role | Frequency |
|---|---|---|
| **Opus orchestrator** | The brain. One per session. Always Opus. | 1 per session |
| **Opus heavy muscle** | Decisions with real consequence. | 1–3 per day |
| **Sonnet specialist** | Reasoning, browser, code. | ~60% of muscle work |
| **Haiku swarm** | Inventories, greps, counts, classifications. | ~35%, 5–10 in parallel |

### Lifecycle (10 + 1 steps)

```
Step 0     Load settings + addons
Step 0.5   Knowledge recall (recipes registry hit?)
Step 0.7   Seam detection (optionally fire decomposer muscle)
Step 1     Decompose + dispatch
Step 2     Parse META from each agent
Step 2.5   Artifact verification (Mitigation #9 — on-disk + size check)
Step 3     Escalation + spot-check
Step 4     Cross-pollination
Step 5     Reviewer loop
Step 6     Synthesize
Step 7     Cost report
Step 8     Synthesis quality gate
Step 9     Promote to Knowledge + publish
```

### Dispatch paths (4)

`DIRECT` (default) · `DIRECT-PARALLEL` · `DIRECT-BACKGROUND` · `DASHBOARD`. File-write tasks force `DIRECT`.

### Memory tiers (4)

1. **Skill** — constant identity (`SKILL.md`, preambles, principles).
2. **Recipes registry** — `provisional` → `validated` → `stale`.
3. **Operational log** — `cuts-log.jsonl`, `audit-deltas.jsonl`, per-session events.
4. **Promoted Knowledge** — synthesized cross-session learnings.

### The 9 mitigations

One-to-one mapped against historical failure modes. See `PROTOCOL.md` for the full list. Latest is **#9: artifact verification** (Test-Path + size check on disk before any DONE claim).

### Surfaces (where things live)

| Thing | Path |
|---|---|
| Skill | `~/.claude/skills/swarm-orchestrator/SKILL.md` |
| Dashboard | `dashboard/app.py` (Flask + SSE on `:5173`) + `dashboard/templates/` + `dashboard/static/` |
| Decomposer plan | `~/.claude/plans/lets-go-over-this-purring-peacock.md` (+ `*-agent-*.md`) |
| Cross-device sync | `claude-skills` GitHub repo (RonShmuely) |
| Runtime adapters reference | `docs/RUNTIME-ADAPTERS.md` |
| Cost benchmarks | `docs/COST-BENCHMARK.md` |
| Wow-demo script | `docs/WOW-DEMO.md` |
