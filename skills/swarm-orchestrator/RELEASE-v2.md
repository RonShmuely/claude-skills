# swarm-orchestrator v2.0 — Diff Report

Date: 2026-04-25  
Author: Ron Shmuely  
Trigger: Real 6-agent swarm run on 2026-04-25 silently accepted Agent E (VPS topic) self-reporting `confidence: 0.88` while doing **zero web searches**. The orchestrator merged its training-only output into the synthesis as if it were verified. v2 closes that gap and 5 others.

---

## At a glance

```
 SKILL.md         | 209 +++ ──── biggest rewrite (lifecycle: 4 steps → 10 steps)
 docs/PROTOCOL.md | 115 +++ ──── 5 mitigations → 8 mitigations
 docs/RECIPES.md  |  32 +++ ──── tool-use floors per recipe
 meta-block.md    |  32 +++ ──── tools_used field added
 reviewer.md      |  18 +++ ──── 4 dynamic triggers
 [+ 8 new files: 1,241 LOC]
```

| Metric | Value |
|---|---|
| Modified files | 5 |
| New files | 8 |
| Memory scaffold | 3 dirs + .gitkeeps + runs.sqlite (auto-created on first import) |
| Modified files diff | 356 lines added, 50 removed |
| New files line count | 1,241 LOC |
| **Total net new content** | **~1,547 LOC** |
| Wall-clock for execution | ~15 min (after plan approved) |
| Equivalent traditional dev effort | ~2-3 dev-days |
| Effective rate | ~100 LOC/min including design |

---

## What was broken before v2

| Gap | Symptom in the original run | v2 fix |
|---|---|---|
| **Anomaly silently accepted** | Agent E claimed 0.88 confidence with 0 tool uses; orchestrator merged its claims as verified | **Mitigation #6** — `tools_used` field + recipe floors + `block`/`warn`/`off` action |
| **Spot-check skipped quietly** | SKILL.md said "do spot-check on [M]/[H]" but nothing enforced it | **Patch 3** — mandatory artifact, even "Picked: 0" must appear |
| **Cross-agent contradictions buried** | Agent C found Gemini CLI broken on Windows; Agent D recommended dual-CLI architecture without that caveat | **Mitigation #7** — cross-pollination pass for N≥4 |
| **Reviewer only on `[H]` tag** | A medium-stakes swarm with 0.6 confidence had no reviewer recourse | **Patch 5** — 4 dynamic triggers (low conf / variance / anomaly / cross-link) |
| **No cost / latency visibility** | User couldn't see which agent was the bottleneck | **Patch 6** — settings-gated cost report with latency timeline |
| **No audit trail / reuse** | Every swarm started from scratch; identical research re-done | **Patch 10** — three-tier memory with FTS5 hybrid recall at Step 0.5 |
| **Hardcoded behavior** | No way to dial up/down strictness per use case | **Patch 9** — settings infrastructure with `/swarm-config` UX |
| **Implicit synthesis quality** | "Flag unverified findings" was an instruction, not enforcement | **Patch 7** — synthesis quality gate with 7 hard/soft checks |

---

## File-by-file diff

### Modified (5 files, 356 +/− 50)

#### `SKILL.md` — 209 line delta (biggest change)

- Lifecycle expanded from 4 steps to **10 steps**:
  - Step 0 — Load settings (3-layer priority chain)
  - Step 0.5 — Knowledge recall (skip if memory disabled or task is novel)
  - Step 1 — Decompose + dispatch (existing, polished)
  - Step 2 — Per-muscle return processing (NEW: `tools_used` parsing + anomaly check)
  - Step 3 — Mandatory spot-check artifact for `[M]`/`[H]`
  - Step 4 — Cross-pollination pass for N≥4
  - Step 5 — Reviewer loop with dynamic triggers (NEW)
  - Step 6 — Synthesize + apply soft remediations
  - Step 7 — Cost report (settings-gated)
  - Step 8 — Synthesis quality gate (capstone)
  - Step 9 — Promote operations to Knowledge
  - Step 10 — Publish to user
- Dispatch template: META block now includes `tools_used` field
- Reference docs section: 5 docs → 7 docs (added `SETTINGS.md`, `MEMORY-TIERS.md`)
- Reference templates: 4 → 7 (added `spot-check.md`, `cost-report.md`, `synthesis-gate.md`)
- Golden rules: 7 → 12

#### `docs/PROTOCOL.md` — 115 line delta

- "5 Mitigations" → "8 Mitigations"
- Mitigation summary table: 5 rows → 8 rows
- New sections: #6 (Tool-use anomaly detection), #7 (Cross-pollination pass), #8 (Synthesis quality gate)
- Updated #1 (Reviewer loop): static `[H]` trigger plus 4 new dynamic triggers
- Safety-tag layering matrix expanded: 5 columns → 8 columns
- Implementation checklist rewritten as 4-phase: pre-dispatch / per-muscle / post-swarm / post-synthesis

#### `docs/RECIPES.md` — 32 line delta

- New "About expected_tools_floor" intro section
- New "Tool-use floors per recipe" table at end (used by Mitigation #6)
- Recipe anatomy YAML schema gained `expected_tools_floor` field

#### `templates/meta-block.md` — 32 line delta

- Added `tools_used: {...}` field to the contract block
- New section explaining `tools_used` semantics, examples, and orchestrator behavior
- Backward-compat note (missing field treated as `{}`)
- Added `TOOLS_USED_RE` regex for orchestrator parsing

#### `templates/reviewer.md` — 18 line delta

- "When to use" section expanded:
  - Static trigger: `[H]` tag (unchanged)
  - 4 NEW dynamic triggers: low conf after re-escalation, variance > threshold, tool-use anomaly, cross-link contradiction
- Each dynamic trigger toggleable via `discipline.reviewer_dynamic_triggers.*`

### New files (8 files, 1,241 LOC)

| File | LOC | Purpose |
|---|---|---|
| `defaults.json` | 93 | Repo defaults for all 22 configurable knobs + 9 recipe floors |
| `.gitignore` | 24 | Excludes `settings.local.json`, transient operations dirs, runtime SQLite, `__pycache__` |
| `docs/MEMORY-TIERS.md` | 170 | Identity / Operations / Knowledge architecture spec (storage, read API, write rules, TTL, promotion) |
| `docs/SETTINGS.md` | 115 | Every knob documented with type, default, override mechanism |
| `lib/memory.py` | 508 | Settings loader + 3-tier access (`identity.get`, `operations.session`, `knowledge.search/promote`); CLI helpers |
| `templates/spot-check.md` | 87 | Mandatory artifact format for `[M]`/`[H]` swarms |
| `templates/cost-report.md` | 110 | End-of-run cost block: `off`/`summary`/`full` modes with latency timeline |
| `templates/synthesis-gate.md` | 134 | 7-item pre-publish checklist with hard blocks + soft remediations |

### External files (not in skill repo)

- `~/.claude/commands/swarm-config.md` — slash command (default popup wizard + `--advanced` plan-mode editor)
- `~/.claude/swarm-orchestrator/settings.json` — Ron's user-level overrides (partial JSON)

---

## Settings reference

22 knobs across 6 categories. Full spec in `docs/SETTINGS.md`.

| Category | Knobs |
|---|---|
| **Output** | `cost_report`, `output_format`, `verbose_meta`, `synthesis_style` |
| **Discipline** | `spot_check_enforce`, `spot_check_sample_size`, `cross_link_enabled`, `cross_link_min_agents`, `anomaly_detection`, `reescalation_threshold`, `low_confidence_flag_threshold`, `confidence_variance_threshold`, `reviewer_dynamic_triggers.*` (4) |
| **Models** | `default_research_tier`, `default_audit_tier`, `force_opus_for`, `temperature.{haiku,sonnet,opus}` |
| **Quota** | `warnings_enabled`, `max_parallel_agents` |
| **Memory** | `enabled`, `search_on_dispatch`, `similarity_threshold`, `operations.ttl_days`, `knowledge.enable_vectors`, `knowledge.embedding_model`, `knowledge.fts_weight`, `knowledge.vector_weight` |
| **Recipe floors** | Per-recipe object of expected minimum tool counts (9 recipes covered) |

---

## Verification — what passes today

```
✓ Module imports OK
✓ Settings layers: 3 of 3 dirs exist
✓ Cost report mode: full       (Ron's user override applied)
✓ Anomaly mode: block          (Ron's user override applied)
✓ Memory enabled: True
✓ Recipe floors loaded: 9 recipes
✓ Settings priority chain: user > skill-local > defaults
✓ User-override removal works (audit_tier dropped when set back to default)
```

---

## What's next (out-of-scope for v2)

- Wire `dashboard/` to consume new META `tools_used` field — render anomaly pill in agent cards
- Optional Patch 11: hooks integration (auto-cleanup Operations dirs on Stop event, replacing manual TTL cron)
- Per-recipe cost benchmarks regenerated for `COST-BENCHMARK.md`
- Settings-aware dispatch wrapper that does direct API calls when temperature is non-default (currently advisory)
- Ollama tier (Tier 5) wiring per existing ROADMAP.md item

---

## Provenance

- **Plan file:** `~/.claude/plans/cached-juggling-summit.md` (executed plan, retained for reference)
- **Session summary:** `~/.claude/sessions/session-2026-04-25-2.md` (uploaded to Ron's Brain notebook source `7c0618d4-cc4a-48a2-a8a5-e4c5057e5818`)
- **Memory entry:** `project_swarm-orchestrator-v2.md` in `project-memory/desktop/`
