# Changelog

All notable changes to the swarm-orchestrator skill.

## [2.2.0] — 2026-04-26

Mitigation #9 (Artifact verification), centralized dispatch preambles, runtime-adapter authoring guide, and BiDi/RTL handling across all rendering surfaces. Production-grade Hebrew support.

### Added

- **Mitigation #9 — Artifact verification.** New core mitigation. After each agent returns, the orchestrator verifies declared artifacts exist on disk and are non-empty before relaying any "DONE" claim. Discovered when Opus fabricated `path\n398` after a silent Write denial during Phase A retest. Three modes via `discipline.artifact_verification.mode`: `off` / `warn` / `block` (default `block`). Settings: `expected_artifacts_field` (default `"artifacts"`), `min_size_bytes` (default `1`).
  - `docs/PROTOCOL.md` — new section + safety-tag layering matrix updated; "8 Mitigations" → "9 Mitigations" throughout.
  - `templates/synthesis-gate.md` — 7-item check → 8-item; new check #8 hard-blocks in `block` mode, soft-caveats in `warn`.
  - `defaults.json` v1.2.0 — added `discipline.artifact_verification` block.
  - `SKILL.md` — Step 2.5 inserted between Step 2 and Step 3; Golden rule #9 added; "8-mitigation playbook" → "9-mitigation playbook".
  - `README.md` — "The 8 Mitigations" → "The 9 Mitigations" + numbered entry.
  - `addons/_core/auto-adapter/templates/addon-synthesis.md` — `ARTIFACTS` manifest contract + META `artifacts` field + "no fabricated artifacts" hard rule.

- **`docs/RUNTIME-ADAPTERS.md`** (new, 222 lines) — adapter authoring guide. 8-item per-runtime checklist (cwd handling, permission posture by tier, marker convention, ship-don't-ask preamble, confirmation gates, artifact verification, dashboard observer integration, BLOCKED protocol), 10-step dispatch protocol skeleton, anti-patterns, reference implementation (Antigravity AGENTS.md v3.3 = current Phase A baseline). Required reading for Mom-tier, Cursor, OpenCode adapter authors.

- **`templates/dispatch-preamble-en.md` and `dispatch-preamble-he.md`** (new) — canonical 6-rule ship-don't-ask preamble extracted from inline duplications in workspace AGENTS.md and `auto-adapter/templates/addon-synthesis.md`. Adapters concatenate at end of every dispatch prompt. Includes Rule 6 (no fabrication, EN+HE) hardened from real-world Opus fabrication incident.

- **`docs/HEBREW-AND-RTL.md`** (new) — required reading for adapter and skill authors whose work touches Hebrew/RTL. Covers: 3 core rules (`dir="auto"`, font fallback, explicit `dir="ltr"` for identifiers), `<html>`-level direction posture (LTR chrome + per-element `dir="auto"` flip), CSS canonical preamble, layout gotchas, per-tier user expectations, generated HTML artifact contract, dashboard reference implementation pointer.

- **Dashboard BiDi/RTL patches** (`packages/swarm-dashboard/templates/*.html`):
  - `<html lang="en" dir="ltr">` on every template (was `<html lang="en">`).
  - Heebo Google-Fonts import in every `<head>` (Hebrew-capable font; pairs with mono).
  - Canonical CSS preamble (`--font-bidi` chain, `[dir="auto"]` + `[dir="rtl"]` selectors, `unicode-bidi: plaintext`).
  - `dir="auto"` on every dynamic text node: agent description, final_text, last_text, last_tool_input across dashboard / cockpit / compact / theater modes; search input; dispatch composer textareas (`#dp-prompt`, `#dp-sys-prompt`, `#dp-chat-input`, plus the standalone `dispatch.html` `#prompt` and `#sys-prompt`).
  - `dir="ltr"` on identifier spans (callsigns) so Latin IDs render LTR even inside RTL parents.
  - Counts: index.html 15× `dir="auto"`, cockpit.html 4×, dispatch.html 4×, theater.html 3×.

- **`lang_hint` field in artifact manifest** (`addon-synthesis.md`). Values: `he` / `en` / `mixed` / `none`. Generated HTML artifacts with Hebrew content must report `mixed` or `he`, never `en`. Downstream consumers (dashboard, future Mom-tier UI) use this to pick the right rendering surface.

- **HTML output rules in BOTH dispatch preambles** (`dispatch-preamble-en.md` and `dispatch-preamble-he.md`) — when a dispatched agent generates Hebrew HTML, it must apply the canonical CSS preamble inline, set `<html lang="he" dir="rtl">` (or LTR with per-element `dir="auto"` for mixed), include the Heebo font import, and tag the manifest entry `lang_hint: "he"` or `"mixed"`. **Critical framing:** rules fire on **output content**, not input language. A user typing English can still ask for Hebrew output and the agent applies the rules silently. A Hebrew-native user should never have to instruct the agent in BiDi/RTL mechanics. Both preambles embed the identical Hebrew-output checklist; adapter picks preamble by primary user language, but either fully covers the Hebrew-output case. See `docs/HEBREW-AND-RTL.md` "When these rules apply" section.

### Changed

- **AGENTS.md v3.3** (workspace adapter, `~/Desktop/test-mom-wix/AGENTS.md`):
  - `--dangerously-skip-permissions` on every `claude -p` invocation (8 dispatch points across 4 paths). Documented as Ron-tier posture; Mom-tier adapter explicitly forbids this.
  - Rule 6 (no-fabrication, EN+HE) added to operating-mode preamble.
  - Step 7 — Verify artifacts on disk before reporting success — inserted between stdout capture and BLOCKED scan. PowerShell + Bash patterns provided. Trust nothing the agent says about artifacts; check on disk.

### Deprecation tracker

- `packages/swarm-dashboard/app.py` `/api/dispatch`, `/api/jobs`, `/api/jobs/<id>/stream`, `/api/jobs/<id>` DELETE — already marked deprecated in v2.1.1; **scheduled removal in v2.3** now that direct `claude -p` from runtime adapters is the canonical path.

## [2.1.1] — 2026-04-25

Layer split: framework / tool / adapter. Architectural cleanup that codifies what the framework is, what the dashboard is, and what runtime adapters are. No behavioral changes to the protocol, addons, or core dispatch — but the boundaries are now explicit and the dashboard is reframed as a passive observer.

### Added

- **Scope headers** in three locations:
  - `skills/swarm-orchestrator/README.md` — declares the framework as cross-runtime product, audiences (Mom / Ron / Brother / SaaS), runtimes (Antigravity / Claude Code / Cursor / OpenCode), and the rule "framework does not depend on dashboard."
  - `packages/swarm-dashboard/README.md` — declares the dashboard as a standalone observability tool, single-user, observer-only, and that `/api/dispatch` and friends are deprecated.
  - Workspace `AGENTS.md` template (Antigravity adapter) — declares it a runtime adapter, dispatches via direct `claude -p` from the workspace cwd, dashboard is passive.
- **Dashboard observer patches in `packages/swarm-dashboard/app.py`:**
  - `parse_parent_session_jsonl()` — walks Claude Code's native parent-session JSONLs at `~/.claude/projects/<slug>/<session-uuid>.jsonl`, extracts the same fields as `parse_jsonl()` plus a `swarm_marker` field if the first user message contains `[SWARM_DISPATCH:<task-slug>]`.
  - `collect_agents(source=...)` — accepts `all` / `subagent` / `parent-swarm` / `parent-other` filter. Pass 1 walks parent-session JSONLs, Pass 2 walks subagent JSONLs (existing logic). Each agent row gets a `source` field plus `swarm_marker` and `first_user_text` for parent rows.
  - `/api/agents?source=...&hours=...` — query param routed through.
  - `/stream?source=...` — SSE filter.
  - `/jobs` — new route, dedicated page for swarm-marked parent sessions.
  - **Deprecation banner** on the dispatch endpoint block (`/api/dispatch`, `/api/jobs`, `/api/jobs/<id>/stream`, `/api/jobs/<id>` DELETE) — keep in v2.1 for backward compatibility, removal planned in v2.2.
- **`SWARM_DISPATCH` marker convention.** Runtime adapters prefix every dispatch prompt with `[SWARM_DISPATCH:<task-slug>]` so the dashboard can filter swarm-dispatched parent sessions from ad-hoc Claude Code sessions the user runs elsewhere. The marker is a harmless string the model ignores; the dashboard's parent-session walker scans the first user message for it.
- **`cd` before dispatch** rule in workspace AGENTS.md. Slot pre-creates the target dir and `cd`s into it before `claude -p`, so the agent's filesystem sandbox boundary is the right scope. Fixes the `BLOCKED: path is outside the session's allowed working directories` failure mode that occurred when the dashboard's Flask cwd became the unintended sandbox.

### Changed

- **Default dispatch path is direct headless `claude -p`** (Path A in adapter), with optional dashboard upgrade for non-blocking + multi-agent runs when reachable. Reachability check: `curl -s --max-time 1 http://127.0.0.1:5173/api/jobs > /dev/null && echo UP || echo DOWN`. Never fail dispatch because the dashboard isn't running.
- **AGENTS.md routing rule** rewritten: file-write override (always Path A direct + `cd`) takes precedence over latency-based path selection. File-writing dispatches must not go through the dashboard.

### Architectural articulation (in case future-Ron forgets)

| Layer | Lives at | Role |
|---|---|---|
| Product (framework) | `skills/swarm-orchestrator/` | Cross-runtime swarm orchestration with addons. The thing you ship. |
| Tool (observer) | `packages/swarm-dashboard/` | Standalone single-user dashboard. Reads ~/.claude/projects/. Never dispatches. |
| Adapter (runtime binding) | Workspace `AGENTS.md`, `~/.claude/skills/`, `.cursor/rules/`, etc. | Translates framework concepts into one IDE's primitives. |

The framework is the source of truth. Adapters are thin wrappers. Dashboard is a bonus.

## [2.1.0] — 2026-04-25

Addons system. The skill ships the discipline; addons ship the domain. New users can graft new skills/recipes/templates/workflows/hooks onto the orchestrator without forking the core.

### Added

- **`docs/ADDONS.md`** — full design memo: manifest schema, search order (built-in `<` user `<` project), conflict resolution by priority, hook events (`dispatch_start`, `agent_returned`, `synthesis_done`, `gate_failed`, `cost_report`), `/swarm-addons` command surface, intentional limits.
- **`addons/` directory** with `addons/README.md` quick-start and load-order rules.
- **Built-in `addons/_core/auto-adapter/`** — the "tell the swarm to learn a repo" capability. Triggers on natural-language phrases (English + Hebrew) plus `/swarm-addons learn <path>`. Dispatches a 5-agent recipe (3× Sonnet inventory/extraction + 1× Opus synthesis + 1× Opus doctor) that produces a draft addon at `~/.claude/swarm-orchestrator/addons/<repo-name>-bundle/` with `status: disabled` for user review before enabling.
- **`lib/addons.py`** — addon loader (~430 LOC). Public API: `load_addons(settings, skill_dir, workspace_dir) → AddonRegistry`. Registry methods: `list()`, `get()`, `find_recipe()`, `find_skill_by_trigger()`, `find_addon_by_trigger()` (named-group capture), `apply_model_tier_overrides()`, `run_hooks(event, ctx)` (parallel daemon threads, fire-and-forget, 15s timeout per hook). CLI: `python lib/addons.py list | doctor`.
- **`addons` block in `defaults.json`** — `auto_discovery`, `search_paths` (with `<skill-dir>` / `<workspace>` tokens), `disabled` list, `priority_overrides` map. User-level override at `~/.claude/swarm-orchestrator/settings.json`.
- **`/swarm-addons <list | info | enable | disable | doctor | learn | install | remove>` command surface** documented in `SKILL.md`. Orchestrator handles directly in v1; no separate command file needed.

### Changed

- **`SKILL.md`** — added "Addons — extend the swarm without forking it" section before the reference docs index. Loader is called on session start; addons surface skills/recipes/templates/workflows transparently.
- **`defaults.json`** version bumped 1.0.0 → 1.1.0.

### Authoring rules (locked in this release)

- Generated addons (from `auto-adapter`) ship `status: disabled` by default. Trust gate: user reviews and explicitly enables.
- Addons cannot disable core protocol rules, bypass the synthesis quality gate, or modify the dashboard's Flask app.
- `/swarm-addons remove` archives, never deletes (consistent with the never-delete-only-archive memory rule).
- `/swarm-addons install` clones / copies but does NOT auto-run `npm install` or `pip install` — supply chain caution.

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
