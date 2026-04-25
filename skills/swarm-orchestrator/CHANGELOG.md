# Changelog

All notable changes to the swarm-orchestrator skill.

## [2.0.0] — 2026-04-25

Major upgrade: 10 patches across ~13 files, ~1,547 net new lines. Driven by gaps observed in a real 6-agent swarm run that silently accepted an agent claiming `confidence: 0.88` while doing zero web searches.

### Added

- **Mitigation #6 — Tool-use anomaly detection.** Every muscle now reports `tools_used: {WebSearch: N, WebFetch: N, ...}` in its META block. Orchestrator parses, compares against the recipe's expected floor (declared in `defaults.json` `recipe_floors` and listed in `docs/RECIPES.md`), and acts per `discipline.anomaly_detection`: `off` / `warn` / `block` (auto re-dispatch on a higher tier).
- **Mitigation #7 — Cross-pollination pass.** When N ≥ `cross_link_min_agents` (default 4), orchestrator extracts top-3 facts from each muscle report and checks for contradictions before synthesis. Emits `cross-link.md` artifact when conflicts found.
- **Mitigation #8 — Synthesis quality gate.** Pre-publish 7-item self-check that integrates Mitigations #1–#7 into a single enforcement point. Hard blocks on missing META / spot-check artifact / un-run reviewer; soft remediations (label unverified, inject caveats) for the rest. Outcome stored in `gate-result.json`.
- **Settings infrastructure (Patch 9).** New `defaults.json` with 22 configurable knobs across Output / Discipline / Models / Quota / Memory / Recipe-floors. User overrides at `~/.claude/swarm-orchestrator/settings.json` (partial JSON — only knobs that differ from defaults). Skill-local override at `<skill-dir>/settings.local.json`. New `/swarm-config` slash command edits via AskUserQuestion popup wizard (4 paginated questions covering preset bundles); `/swarm-config --advanced` opens plan-mode markdown editor exposing every individual knob.
- **Three-tier memory architecture (Patch 10).** New `memory/` directory with enforced separation:
  - **Identity** (`memory/identity/*.md`) — stable user/agent facts, curated only, never auto-written
  - **Operations** (`memory/operations/<session>/`) — per-run artifacts (META blocks, spot-check, cross-link, cost-report, synthesis), auto-cleanup after `operations.ttl_days` (default 7)
  - **Knowledge** (`memory/knowledge/runs.sqlite`) — append-only indexed store of past runs with FTS5 (full-text) + optional sqlite-vec (semantic) hybrid retrieval; queried at Step 0.5 to surface "we've done this before" before fresh dispatch
- **`lib/memory.py`** (508 LOC) — settings loader (3-layer priority chain), Identity/Operations/Knowledge access classes, hybrid search, promotion logic. CLI helpers: `python memory.py settings | identity-list | operations-recent N | knowledge-search QUERY`.
- **Mandatory spot-check artifact (Patch 3).** `[M]` and `[H]` swarms now MUST emit `spot-check.md` even if 0 verifications happened (block contains `Picked: 0 (all reports above threshold)` so the user sees the orchestrator considered it).
- **Cost report with latency timeline (Patch 6).** Settings-gated end-of-run block: `off` / `summary` / `full`. Full mode includes per-agent breakdown sorted slowest-first plus a horizontal-bar latency timeline so bottlenecks pop visually. Always written to operations dir for the audit trail.
- **Dynamic reviewer triggers (Patch 5).** Reviewer now fires on any of: `[H]` tag (static), low confidence after re-escalation, confidence variance > threshold, tool-use anomaly, cross-link contradiction. Each dynamic trigger toggleable via `discipline.reviewer_dynamic_triggers.*`.
- **Recipe tool-use floors (Patch 8).** `docs/RECIPES.md` now declares expected minimum tool counts per recipe — used by Mitigation #6's anomaly detector to know what "0 tool uses" means in context.
- **`tools_used` field in META block (Patch 1).** Required for all new dispatches. Backward-compatible: missing field is treated as `{}` and falls back to `warn` mode regardless of user setting.
- **`docs/SETTINGS.md`** — every configurable knob documented with type, default, override mechanism.
- **`docs/MEMORY-TIERS.md`** — full memory architecture spec including SQLite schema, hybrid search formula, operations directory layout, promotion sequence.

### Changed

- **`docs/PROTOCOL.md`** — "5 Mitigations" → "8 Mitigations". Safety-tag layering matrix expanded. Implementation checklist rewritten as 4-phase (pre-dispatch / per-muscle / post-swarm / post-synthesis).
- **`SKILL.md`** — lifecycle expanded from 4 steps to 10 (Step 0 settings load, Step 0.5 knowledge recall, mandatory spot-check, cross-pollination, dynamic reviewer triggers, cost report, synthesis gate, knowledge promotion). Golden rules expanded from 7 to 12.
- **`templates/meta-block.md`** — added `tools_used` field spec, examples, regex-parser snippet.
- **`templates/reviewer.md`** — "When to use" section expanded with 4 dynamic trigger conditions.

### Notes

- Backward-compatible. Legacy muscle prompts that don't emit `tools_used` continue to work — anomaly detection silently falls through to `warn` for those agents.
- Memory tiers are opt-in via `memory.enabled` (default `true`). Set to `false` for privacy-sensitive runs to skip Knowledge indexing entirely.
- `sqlite-vec` extension is optional. `memory.knowledge.enable_vectors: false` (default) uses FTS5 alone — plenty for most retrieval needs without an extra dependency.
- Temperature settings are advisory — passed as natural-language hints in dispatch prompts, since the Agent dispatch tool doesn't accept temperature directly. True API-level temperature requires direct SDK calls (out of scope for v2).

### Migration

No action required — repo defaults match prior behavior for users who don't create a `~/.claude/swarm-orchestrator/settings.json`. To opt into v2 features:

```bash
# View current effective settings (merges defaults + any overrides)
python "<skill-dir>/lib/memory.py" settings

# Edit via popup wizard
/swarm-config

# Or edit every individual knob via plan-mode markdown
/swarm-config --advanced
```

### Verification

Smoke-tested 2026-04-25:
- Settings load: 3-layer priority chain works, user overrides correctly win, missing layers fall through cleanly
- Recipe floors loaded: 9/9 recipes
- Module imports: `lib/memory.py` loads without errors
- All 3 memory dirs exist and are writable
- `runs.sqlite` schema initializes cleanly on first import

---

## [1.0.0] — 2026-04 (initial release)

- 5-mitigation playbook (model-match, typed outputs, escalation, spot-check, reviewer loop)
- Four model tiers (Opus / Sonnet / Haiku, with optional Ollama tier 5 noted)
- Recipe library: `wow-demo`, `folder-audit`, `inventory`, `diagnose-machine-fault`, `research-brief`, `code-review-swarm`, `doc-audit`, `dedup-scan`, `bulk-classify`
- Templates: `inventory.md`, `audit.md`, `reviewer.md`, `meta-block.md`
- Optional Flask + Tailwind dashboard at `dashboard/` for live agent observation
- Cost benchmark: ~30–50× cheaper and ~2× faster than single Opus 1M on the reference 5-section audit workload
