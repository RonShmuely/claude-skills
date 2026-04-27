---
name: swarm-orchestrator
description: >
  Multi-agent swarm framework with disciplined model-tier selection. Use when
  a task is parallelizable (audit N folders, search M files, classify K items),
  when dispatching multiple agents in parallel, or when the user asks to
  "swarm", "fan out", "orchestrate", "run N agents", "dispatch parallel haikus",
  "brain + muscles", "multi-agent", "hierarchical orchestration", or anything
  resembling the OpenClaw / Hermes sub-agent pattern. Also triggers when the
  user wants cost-efficient agent work ("cheap", "bulk", "in parallel"),
  when they mention the live dashboard / swarm monitor, or when they reference
  the "5 mitigations" / protocol for high-stakes swarms. Specifically triggers
  on "fire the wow demo", "run the week start triage", "wowdemo", "week-start
  triage" — these invoke the curated 5-muscle + 1-reviewer showcase swarm
  documented in docs/WOW-DEMO.md. Enforces the rule: Haiku for narrow-and-
  structured, Sonnet for reasoning/ambiguity, Opus for decisions with real
  consequence. Escalates on low confidence.
---

# Swarm Orchestrator

You are the **brain** of a multi-agent swarm. You dispatch specialist "muscle"
agents in parallel, each on a narrow slice of the task, then synthesize their
structured outputs into one merged answer. You do NOT do the muscle work yourself
when the task is parallelizable — that's the whole point.

The pattern mirrors **OpenClaw's sub-agent mode** and **Hermes Agent's
hierarchical decomposition**, but kept in-session (the user's current chat
session is the orchestrator, no separate Gateway).

## Core principle (non-negotiable)

> **The swarm's output quality equals the quality of your model-selection
> discipline.** Haiku on an ambiguous task fails silently with confident-shallow
> output. Default up a tier whenever in doubt.

This is not a suggestion. It is the skill's load-bearing rule. See
`docs/MODEL-TIERS.md` for the decision table.

## When to use this skill

**Use the swarm pattern when:**
- A task decomposes cleanly into N independent chunks (N folders, N files,
  N lookups, N items to classify)
- Each chunk can be narrowly specified with a structured output expectation
- Total work would take one Opus hours but N Haikus minutes in parallel
- The user explicitly asks for parallel / fan-out / swarm work

**Do NOT use the swarm pattern when:**
- The task needs one brain holding all context to spot cross-cutting patterns
- Every subtask requires deep judgment (all-Haiku swarm = shallow merged output)
- Total work is < 5 min and < 30K tokens (orchestration overhead not worth it)
- Task is linear / sequential research (read 5 papers, write position)

## The four tiers

| Tier | Model | Role | Volume |
|---|---|---|---|
| 1 | **Opus** (you, orchestrator) | BRAIN — decomposition, synthesis | 1 per session |
| 2 | **Opus** | HEAVY MUSCLE — decisions with real consequence | 1–3/day |
| 3 | **Sonnet** | SPECIALIST — reasoning, browser, code, reviews | ~60% of dispatches |
| 4 | **Haiku** | SWARM — inventories, greps, counts, patterns | ~35%, run 5–10 parallel |

Tier 5 (optional, not yet wired): **Ollama local** for bulk privacy-sensitive
or offline preprocessing. $0/token. See `docs/MODEL-TIERS.md`.

## Dispatch protocol

Every muscle you dispatch gets:

1. **A safety tag** in the description prefix: `[L]` / `[M]` / `[H]`
2. **A typed-output contract** requiring a META block at the end
3. **An explicit scope** with "do NOT touch X" exclusions when other muscles are
   working neighboring areas

See `docs/PROTOCOL.md` for the full 9-mitigation playbook and when to escalate.
See `templates/` for copy-paste prompt shapes.
See `docs/SETTINGS.md` for configurable behavior; run `/swarm-config` to edit (or edit `~/.claude/swarm-orchestrator/settings.json` directly — see the note in `SETTINGS.md` about how `/swarm-config` is implemented as an intent trigger, not a registered slash-command file).
See `docs/MEMORY-TIERS.md` for the Identity/Operations/Knowledge memory model.

### Default safety mapping

- **[L] Low-stakes** (inventory, count, grep): defaults only (model-match +
  typed output). Raw speed.
- **[M] Medium-stakes** (audit, recommendations): add escalation on
  `confidence < 0.7`, add spot-check verification of 3 claims post-swarm.
- **[H] High-stakes** (diagnosis decisions, architecture calls): add everything
  in [M] plus a Sonnet/Opus reviewer that reads all child outputs + samples raw
  files the muscles never read.

## The META block (always-on)

Every muscle's prompt must end with this contract:

```
At the end of your report, emit a metadata block:

---META---
confidence: 0.XX                            # your confidence this report is accurate (0.0–1.0)
method: "..."                               # how you gathered the data
not_checked: [...]                          # things you couldn't verify
sample_size: N or "exhaustive"
tools_used: {"WebSearch": 8, "WebFetch": 6, "Read": 0}   # actual tool counts by name
---END META---
```

Parse `confidence` from each muscle's final text. If `< 0.7`, re-dispatch the
same prompt on Sonnet. If `< 0.5`, flag the finding in the synthesis as
**unverified** regardless of what the muscle claimed.

Parse `tools_used` and check against the recipe's expected floor (`docs/RECIPES.md`).
If a research task returns with `WebSearch + WebFetch == 0`, that's an anomaly
even if the muscle claims high confidence. See PROTOCOL.md mitigation #6.

## Dispatch template

```
[SAFETY_TAG] <short description>

<scope — be specific about what IS and IS NOT in scope>

Read-only. Do NOT modify. Do NOT touch:
- <other agents' scopes to avoid overlap>

Deliverable (under N words, exact shape):

## <Section name>
- **Field 1:** ...
- **Field 2:** ...
- ...

Rules:
- If a claim requires inference, lower your confidence and say why in method
- If you couldn't check something, list it in not_checked
- Track every tool call you make so you can fill tools_used honestly

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
tools_used: {"WebSearch": N, "WebFetch": N, "Read": N, "Grep": N, ...}
---END META---
```

## Lifecycle of a swarm run

The orchestrator follows this sequence on every dispatch. Settings (Patch 9)
gate optional steps. Memory (Patch 10) persists artifacts to operations/ and
indexes to knowledge/.

### Step 0.0 — Local-first reconnaissance (mandatory, before anything else)

Before loading settings, before knowledge recall, before any decomposition or dispatch — **dispatch a cheap Haiku** for a focused local-filesystem scan. Cap: ~5–10s, ~5K tokens, read-only.

```python
# Skip only if: trivial conversational reply, user provided explicit path,
# or topic is obviously generic public knowledge with no on-disk footprint.
if not is_trivial(user_prompt) and not user_provided_path(user_prompt):
    scan = dispatch_haiku(
        prompt=LOCAL_SCAN_TEMPLATE.format(topic=extract_topic(user_prompt)),
        cap_tokens=5000,
        cap_seconds=10,
        read_only=True,
    )
    # scan returns: list of relevant paths + 1-line summary, OR "nothing relevant on disk"
    sess.write_artifact("local-scan.md", scan.report)
    grounded_context = scan.relevant_paths  # feed into Step 1 decomposition
```

The scan template globs `**/AGENTS.md`, `**/CLAUDE.md`, `**/SKILL.md`, `**/PROJECT.md`, `**/<topic>*`, `**/.<topic>*`; greps `~/.claude/projects/.../memory/` and `~/.claude/skills/`; runs `where <cmd>` for any tool name in the prompt; checks `AppData`, `~/.config`, `Program Files`.

**Why this is Step 0.0 and not Step 0.5:** knowledge recall searches *past swarm runs*. Local-first reconnaissance searches *the user's actual current setup* — different source, different (lower) cost, different (higher) authority. Both run; this one runs first.

**Order of escalation enforced by this step:**
1. Memory + loaded context (free, already in your head)
2. Step 0.0 — Haiku local scan (this step)
3. Targeted Read/Grep on paths the scan surfaced
4. Step 0+ — settings, knowledge recall, decomposition, dispatch
5. WebSearch/WebFetch only if Step 0.0 + targeted Read came back empty

**Anti-pattern blocked by this step:** dispatching parallel Sonnet/Haiku research muscles or WebSearch as the *opening* move on a question about Ron's tools / repos / setup. The cheap local probe nearly always grounds the question and shrinks the downstream swarm.

See: `~/.claude/CLAUDE.md` "Local-First Reconnaissance" section, and `~/.claude/projects/C--Users-ronsh-Desktop-Ron-s-Brain/memory/feedback_unknown_tool_haiku_scan_first.md`.

### Step 0 — Load settings

```python
from lib.memory import load_settings
settings = load_settings()  # resolves user > skill-local > defaults
session_id = new_session_id()
sess = operations.start(session_id, task_text=user_prompt)
```

### Step 0.1 — Load addons (always, before any dispatch)

```python
from lib.addons import load_addons
registry = load_addons(
    settings,
    skill_dir=Path(__file__).parent,
    workspace_dir=Path.cwd(),
)
# Apply addon model-tier overrides on top of base capability_map
capability_map = registry.apply_model_tier_overrides(settings.get("capability_map", {}))
```

The registry is now in scope for the whole session. Subsequent steps query it
to find skills (`registry.find_skill_by_trigger(user_prompt)`), recipes
(`registry.find_recipe(name)`), or addon-claimed triggers
(`registry.find_addon_by_trigger(user_prompt)`).

### Step 0.2 — Addon trigger match (before knowledge recall)

If an addon's `triggers:` block matches the user's input, route to that
addon's recipe immediately — these are the natural-language entry points
addons declared they can handle.

```python
match = registry.find_addon_by_trigger(user_prompt)
if match is not None:
    addon, captured = match            # captured = named regex groups
    # e.g. auto-adapter captures {"repo": "/path/to/MachineGuides"}
    confirm_with_user(addon, captured)
    if user_confirmed():
        recipe = first_recipe_in_addon(addon)
        run_recipe(recipe, captured)
        return  # short-circuit; don't fall through to generic decomposition
```

Confirmation phrasing (Hebrew or English depending on user language):
> *"אני רוצה להריץ את `learn-repo` של auto-adapter על `/path/to/MachineGuides`. ירוצו 5 סוכנים. אישור?"*

### Step 0.5 — Knowledge recall (configurable)

If `settings.memory.search_on_dispatch` is true:

```python
similar_runs = knowledge.search(user_prompt, limit=5)
top = similar_runs[0] if similar_runs else None
if top and top['fts_score'] indicates similarity > settings.memory.similarity_threshold:
    surface_to_user(f"We've done this before: {top['id']}")
    offer reuse / refine / fresh
```

When the user picks reuse, return the past synthesis as-is. Refine = use past
as starting point with focused agents on gaps. Fresh = full swarm, ignore past.

### Step 1 — Decompose + dispatch

Pick tier per `docs/MODEL-TIERS.md` (default up when ambiguous). Apply
`models.force_opus_for` settings. Dispatch all muscles in parallel.

```python
# Fire pre-dispatch hooks so addons can observe / log / audit
for agent in planned_agents:
    registry.run_hooks("dispatch_start", {
        "session_id": session_id,
        "agent_id": agent.id,
        "model": agent.model,
        "safety": agent.safety,
        "prompt_summary": agent.prompt[:200],
    })
```

### Step 2 — Per-muscle return processing

For each muscle as it returns:

```python
meta = parse_meta_block(muscle.return_text)
sess.write_agent(muscle.name, dispatch_dict, {**muscle.return_dict, "meta": meta})

# Mitigation #2 — escalation
if meta['confidence'] < settings.discipline.reescalation_threshold:
    redispatch_on_higher_tier(muscle)

# Mitigation #6 — anomaly detection
floor = settings.recipe_floors.get(recipe_name, {})
for tool, min_count in floor.items():
    if meta['tools_used'].get(tool, 0) < min_count:
        if settings.discipline.anomaly_detection == 'block':
            redispatch_on_higher_tier(muscle, reason='anomaly')
        elif settings.discipline.anomaly_detection == 'warn':
            flag_for_synthesis_caveat(muscle, tool, expected=min_count, actual=...)

# Fire return hooks so addons can observe per-muscle outcomes
registry.run_hooks("agent_returned", {
    "session_id": session_id,
    "agent_id": muscle.id,
    "model": muscle.model,
    "confidence": meta.get("confidence"),
    "tools_used": meta.get("tools_used"),
    "anomaly": locals().get("anomaly_flag"),
})
```

### Step 2.5 — Artifact verification (mitigation #9)

For each agent that declares an `artifacts` field in its META block, stat every listed path on disk before proceeding. Apply behavior per `discipline.artifact_verification.mode`:

```python
if settings.discipline.artifact_verification['mode'] != 'off':
    for path in agent.meta.get('artifacts', []):
        size = os.path.getsize(path) if os.path.exists(path) else -1
        if size < settings.discipline.artifact_verification['min_size_bytes']:
            mode = settings.discipline.artifact_verification['mode']
            if mode == 'block':
                flag_agent_as_failed(agent,
                    reason=f"VERIFICATION FAILED: {path} missing or empty")
                redispatch_on_higher_tier(agent, tightened_prompt=True)
            elif mode == 'warn':
                flag_for_synthesis_caveat(agent,
                    f"VERIFICATION FAILED: {path}")
```

Re-dispatch (block mode) uses a tightened prompt that explicitly names the permission barrier observed. If the re-dispatch also fails verification, surface the failure to the user verbatim — do not relay any "DONE:" claim from that agent. See `docs/PROTOCOL.md` mitigation #9 and `defaults.json` for configuration.

### Step 3 — Spot-check (mandatory artifact for [M]/[H])

If `safety_tag in (M, H)` and `settings.discipline.spot_check_enforce`:

```python
# Always emit the artifact, even if zero checks needed
artifact = run_spot_check(reports, sample_size=settings.discipline.spot_check_sample_size)
sess.write_artifact("spot-check.md", artifact)
```

See `templates/spot-check.md`. If all confidences ≥ 0.85, the artifact still
appears with `Picked: 0 (all reports above threshold)` so the user knows the
orchestrator considered it deliberately.

### Step 4 — Cross-pollination (mitigation #7)

If `N_agents >= settings.discipline.cross_link_min_agents` and
`settings.discipline.cross_link_enabled`:

```python
key_facts = extract_top_3_facts_per_report(reports)
contradictions = check_facts_against_each_recommendation(reports, key_facts)
if contradictions:
    sess.write_artifact("cross-link.md", render_contradictions(contradictions))
```

### Step 5 — Reviewer loop (dynamic triggers)

Dispatch the reviewer if **any** of:
- `safety_tag == [H]` (static trigger)
- Any muscle confidence < `reescalation_threshold` after re-escalation
- Confidence variance across muscles > `confidence_variance_threshold`
- Any muscle had a tools_used anomaly
- Cross-link found ≥1 contradiction

Each dynamic trigger is individually toggleable in
`settings.discipline.reviewer_dynamic_triggers.*`.

### Step 6 — Synthesize

Produce the merged report. Flag anything unverified. Apply soft remediations:
- Prefix low-confidence (<0.5) findings with "Unverified:"
- Inject anomaly caveat block if any agent was flagged
- Inject cross-link findings block before the synthesis when contradictions exist
- Quote the reviewer's flagged concerns with "Reviewer flagged:" prefix

```python
# Fire synthesis-done hook (addons can post to Slack, write to memory, etc.)
registry.run_hooks("synthesis_done", {
    "session_id": session_id,
    "total_tokens": total_tokens,
    "wall_clock_s": wall_clock_s,
    "agents_count": len(reports),
    "recipe": recipe_name,
})
```

### Step 7 — Cost report (settings-gated)

Compute the cost report (always written to operations dir for the record).
Emit to chat per `output.cost_report`:
- `off` — no chat output
- `summary` — one-line italic
- `full` — full block with per-agent breakdown + latency timeline

See `templates/cost-report.md`.

### Step 8 — Synthesis quality gate (capstone, mitigation #8)

Run the 8-item self-check. If any check fails, apply remediation; if any hard
block fails, do not publish. See `templates/synthesis-gate.md`.

```python
gate_result = synthesis_gate(swarm_state, settings)
sess.write_artifact("gate-result.json", json.dumps(gate_result))
if gate_result.has_blocking_failures():
    raise SynthesisBlocked(gate_result.failures)
```

### Step 9 — Promote to Knowledge tier

```python
knowledge.promote(sess, recipe=recipe_name, outcome="success", tags=tags,
                  total_tokens=..., wall_clock_min=..., ...)
sess.touch_lock()  # operations dir is now eligible for TTL cleanup
```

The current run is now searchable for future Step 0.5 recalls.

### Step 10 — Publish to user

Final synthesis + cost report (if enabled) appear in chat. Operations dir
persists for `operations.ttl_days` (default 7) after promotion lock.

## The dashboard (optional)

A live Flask + Tailwind dashboard companion that streams per-agent state from
`~/.claude/projects/<slug>/<session>/subagents/agent-*.jsonl`. Runs local on
`http://127.0.0.1:5173`. Shows model badges (color-coded by tier), safety
pills, confidence pills, tool traces, and a collapsible per-session history.

The dashboard is **not required** — this skill works entirely without it.
Install it only if you want to watch swarms live.

**Install:**
```bash
git clone https://github.com/RonShmuely/claude-skills
cd claude-skills/packages/swarm-dashboard
pip install -r requirements.txt
python app.py
```

See `packages/swarm-dashboard/README.md` for full setup and customization.

## The floating widget (optional, complements the dashboard)

A small frameless desktop popup that sits on top of any window stack,
showing live swarm activity in your peripheral vision while you work.
Built on PySide6 + QWebChannel; subscribes to the dashboard's `/stream`
endpoint via a Python proxy thread (CORS-bypassed, in-process IPC to JS).

**Lives at:** `~/Desktop/swarm-widget-popup.py` (launcher) +
`~/Desktop/Swarm Widget.lnk` (clickable Windows shortcut, generated by
`install-swarm-shortcut.ps1`).

**Three feed modes:**
- **Demo** — simulated agents on a loop with code-flavored recipes (build-react-feature,
  fix-failing-tests, refactor-auth-flow, scaffold-mcp-server, etc.). For visual testing.
- **Live · dashboard SSE** — Python proxy connects to `http://127.0.0.1:5173/stream`,
  filters to the top-10 currently-running non-parent agents, drops stale
  ones (>30s with 0 tools, >60s since last tool), pushes diff-based
  inject calls to the widget UI.
- **Live · Claude Code session tail** — directly tails
  `~/.claude/projects/.../subagents/agent-*.jsonl` files when the
  dashboard is offline. Same widget surface, different transport.

**Window controls:** frameless, draggable header, resizable edges,
overflow menu (`⋯`) for pin / blur / minimize / maximize / settings.
Settings panel: opacity slider, UI scale, snap-to-corner, follow-Claude
toggle (popup is on-top only when `Antigravity.exe` / `Claude.exe` /
`WindowsTerminal.exe` / `Code.exe` is foreground).

**Settings persist** to `~/.claude/swarm-widget/settings.json`.

**Why it complements the dashboard:** the dashboard is a full browser
panel (deep history, tool traces, callsigns); the widget is the
peripheral indicator that tells you "3 agents running, $0.04 spent,
oldest done in ~15s" without leaving the app you're working in. Run both.

## Worked example

User says: "audit MachineGuides for dead code / duplicates / orphans."

1. **Glob top-level.** See sections: `web/`, `DATAFOLDER/`, `extracted/`,
   `images/`, `text/`, `diagnoses/`, `guides/`, `cache/`, top-level scripts,
   top-level docs.
2. **Decompose into 5 non-overlapping scopes**: (A) web/, (B) data layer,
   (C) guide pipeline, (D) build scripts, (E) docs + archive.
3. **Pick tier.** These are narrow-and-structured scopes → Haiku. Safety
   tag `[M]` — the output will drive cleanup decisions.
4. **Dispatch 5 Haikus in parallel** with explicit exclusions so they don't
   trample each other. Each prompt ends with the META block contract.
5. **Wait for all 5.** Parse each confidence. One returns 0.5 on dedup
   detection → escalate to Sonnet with focus on that.
6. **Spot-check** 3 claims total (one random claim from 3 reports) via own
   tool calls.
7. **Synthesize** the merged audit with flagged unverified items.

Cost: ~$1.80 vs ~$50–100 for single Opus 1M doing it sequentially. Wall time:
~7 min vs ~15 min. See `docs/COST-BENCHMARK.md` for the math.

## Addons — extend the swarm without forking it

Addons let you graft new skills, recipes, templates, workflows, model-tier
overrides, and lifecycle hooks onto the swarm-orchestrator. Core skill ships
the discipline; addons ship the domain.

**Where addons live (load order, later overrides earlier):**

1. `<skill-dir>/addons/` — built-in (e.g., `_core/auto-adapter`)
2. `~/.claude/swarm-orchestrator/addons/` — user-installed
3. `<workspace>/.swarm/addons/` — project-scoped

See `docs/ADDONS.md` for the full design memo, manifest schema, and authoring guide.

### Auto-load at session start

When this skill activates, the orchestrator (you) calls
`load_addons()` from `lib/addons.py`. Every discovered manifest with
`status: enabled` is registered. Skills, recipes, templates, workflows, and
model-tier overrides become available transparently — same code paths as
built-in protocol assets, just contributed by an addon.

### `/swarm-addons` command surface

Concrete handler recipes (step-by-step Bash + file ops) for every subcommand
live in `docs/ADDONS-COMMANDS.md`. Read that file when invoking any of these.

When the user types one of these, you handle it directly (no separate command
file needed in v1):

| Command | Effect |
|---|---|
| `/swarm-addons list` | Show discovered addons with status / version / priority / contributions |
| `/swarm-addons info <name>` | Manifest summary + file list |
| `/swarm-addons enable <name>` | Set settings.disabled to remove this name; reload registry |
| `/swarm-addons disable <name>` | Add to settings.disabled; reload registry |
| `/swarm-addons doctor` | Validate every manifest, report missing files, version mismatches, hook errors |
| `/swarm-addons learn <repo-path>` | Invoke the built-in `auto-adapter` addon's `learn-repo` recipe |
| `/swarm-addons install <git-url-or-path>` | `git clone` (or copy) into `~/.claude/swarm-orchestrator/addons/<name>/`, run doctor, report. **No automatic `npm install` / `pip install`.** |
| `/swarm-addons remove <name>` | Move addon dir to `~/.claude/swarm-orchestrator/addons/_archive/<ts>_<name>/`. Never `rm -rf`. |

### Built-in: `auto-adapter` (the "learn this repo" capability)

The skill ships with one built-in addon at `addons/_core/auto-adapter/`. It
listens for triggers like:

- `"adapt to <path>"`, `"learn this repo: <path>"`, `"build addon for <path>"`,
  `"onboard <path> into the swarm"` (English)
- `"תלמדי את <path>"`, `"תתאימי ל-<path>"`, `"תבני אדאון ל-<path>"`,
  `"תאמצי את <path>"` (Hebrew)
- `/swarm-addons learn <path>`

When matched, you dispatch the `learn-repo` recipe — 3 inventory/extraction
muscles (sonnet) + 1 synthesis muscle (opus, sole writer) + 1 doctor (opus,
read-only). Output: a draft addon at
`~/.claude/swarm-orchestrator/addons/<repo-name>-bundle/` with
`status: disabled` (safety gate). User reviews, then runs `/swarm-addons enable`.

See `addons/_core/auto-adapter/README.md` for the full flow.

### Authoring rules

- An addon is a folder with `addon.yaml` + any of: `skills/`, `recipes/`,
  `templates/`, `workflows/`, `model-tiers-overrides.yaml`, `hooks/`, `docs/`.
- Generated addons (from `auto-adapter`) ship `status: disabled`. Never
  auto-enable a generated addon — the user reviews first.
- Addons cannot disable core protocol rules, bypass the synthesis gate, or
  modify the dashboard's Flask app. They extend; they do not subvert.

## Reference docs

- `docs/ARCHITECTURE.md` — the brain-and-muscles model in detail
- `docs/MODEL-TIERS.md` — when to use Haiku/Sonnet/Opus/Ollama, decision table
- `docs/PROTOCOL.md` — the 9 mitigations (reviewer, escalation, spot-check,
  model-match, typed outputs, anomaly detection, cross-pollination, synthesis gate, artifact verification)
- `docs/COST-BENCHMARK.md` — framework vs single-Opus 1M, real numbers
- `docs/RECIPES.md` — reusable swarm patterns + tool-use floors
- `docs/SETTINGS.md` — every configurable knob, defaults vs overrides, `/swarm-config`
- `docs/MEMORY-TIERS.md` — Identity/Operations/Knowledge architecture
- `docs/ADDONS.md` — addon system: manifest schema, search order, hooks, `/swarm-addons` commands

## Reference templates

- `templates/inventory.md` — folder inventory muscle
- `templates/audit.md` — audit / dead-code / duplicates muscle
- `templates/reviewer.md` — reviewer loop (static + dynamic triggers)
- `templates/meta-block.md` — the required META footer contract (incl. `tools_used`)
- `templates/spot-check.md` — mandatory artifact for [M]/[H]
- `templates/cost-report.md` — end-of-run cost block, latency timeline
- `templates/synthesis-gate.md` — pre-publish 8-item self-check

## Library

- `lib/memory.py` — Identity / Operations / Knowledge access, settings loader

## Settings

- `defaults.json` — packaged defaults
- `~/.claude/swarm-orchestrator/settings.json` — user-level overrides
- `/swarm-config` slash command — edit settings via plan-mode UI

## Golden rules

1. **Never dispatch Haiku for a task with real ambiguity.** Default up.
2. **Always require the META block** — including `tools_used`. No confidence and no tool count = no trust.
3. **Escalate on `confidence < reescalation_threshold`** (default 0.7). Automatic, silent.
4. **Anomaly check every muscle**: `tools_used` vs recipe floor. Anomaly handling per `discipline.anomaly_detection`.
5. **Spot-check artifact is mandatory** for [M]/[H] when `spot_check_enforce: true` — even if "Picked: 0".
6. **Cross-pollinate on N ≥ 4** to catch contradictions one muscle can't see.
7. **Reviewer triggers dynamically** on confidence-low, variance-high, anomaly, or cross-link contradiction — not just `[H]`.
8. **Synthesis quality gate is the capstone.** Run before publish; soft-remediate or hard-block.
9. **Verify artifacts on disk before trusting agent reports.** A permission denial returning success-shaped stdout is fabrication, not success.
10. **Flag unverified findings.** Confident-shallow is worse than missing.
11. **Keep scopes non-overlapping.** Muscles must not trample each other.
12. **Synthesize with honesty.** If the swarm returned thin results, say so.
13. **Always promote to Knowledge** after synthesis — your future self will thank you when Step 0.5 surfaces "we've done this before."
