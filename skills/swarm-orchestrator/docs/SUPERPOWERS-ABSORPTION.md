# Superpowers absorption — what swarm-orchestrator should bake in

**Date:** 2026-04-27
**Status:** Plan, not yet applied
**Why:** Three `obra/superpowers` skills overlap with swarm-orchestrator's responsibilities. Either swarm absorbs them (so the discipline is enforced even when the skill isn't loaded) or swarm depends on them (fragile — skills can be uninstalled). Absorption wins for the load-bearing ones.

## Absorption plan

### 1. `superpowers:dispatching-parallel-agents` → swarm `Step 1.5: fan-out gate`

**What it adds:** explicit triggers for when fan-out is justified.

**Current state:** Swarm fans out whenever the user says "swarm" or the task list has ≥3 items. No principled gate.

**Absorbed rule** — add to `docs/PROTOCOL.md` after the Step 1 (decompose) section:

> **Step 1.5 — Fan-out gate.** Before launching ≥2 parallel dispatches, confirm ALL three:
> 1. Tasks are genuinely independent (no shared state, no sequential dependencies)
> 2. Each task has its own success criterion that can be checked without waiting for siblings
> 3. The total parallel cost ≤ 2× the sequential cost (otherwise fan-out's overhead eats the win)
>
> If any of the three fails, run sequentially. The fan-out *trigger* is parallelizability, not task count.

**Files to edit:**
- `docs/PROTOCOL.md` — add Step 1.5
- `SKILL.md` — add Step 1.5 to the lifecycle list
- `docs/RECIPES.md` — add `recipes/fan-out-gate-check.md` decision card

---

### 2. `superpowers:verification-before-completion` → strengthen Mitigation #9

**What it adds:** verification beyond file artifacts — test runs, build runs, typecheck runs.

**Current state:** Mitigation #9 only verifies file existence + non-empty size (`Test-Path` + `Length > 0`). Doesn't verify *correctness* of the artifact.

**Absorbed rule** — extend Mitigation #9 in `docs/PROTOCOL.md`:

> **Mitigation #9 — Artifact Verification (extended).**
>
> Tier 1 (existence): `Test-Path` + non-empty size — already in v3.3 baseline.
> **Tier 2 (validity, NEW):** if the artifact has an executable verification command (test run, build run, lint, typecheck, schema-validate), run it before relaying DONE. The agent MUST declare its verification command in the dispatch contract; the slot runs it.
>
> Examples:
> - `*.py` agent declares `python -m pytest tests/test_<name>.py` → slot runs it
> - `*.html` agent declares `npx html-validator --file=$f` → slot runs it
> - markdown agent declares `(none)` → Tier 1 only
>
> Failure mode: if the agent didn't declare a verification command but the task type usually has one, swarm logs `WARNING: agent skipped Tier-2 verification` and surfaces to user.

**Files to edit:**
- `docs/PROTOCOL.md` — extend Mitigation #9 spec
- `templates/synthesis-gate.md` — add Tier-2 check
- `templates/dispatch-preamble-en.md` + `dispatch-preamble-he.md` — add Rule 7: "declare your verification command in the form `VERIFY: <command>` before DONE; if no command applies, write `VERIFY: none`"
- `defaults.json` — `discipline.artifact_verification.tier_2_mode` (default `warn`, can escalate to `block`)

---

### 3. `superpowers:systematic-debugging` → swarm `recipes/systematic-debugging.md` (NEW)

**What it adds:** principled response to agent failures. Currently swarm retries with same model on failure, which usually fails the same way.

**Absorbed rule** — new recipe at `recipes/systematic-debugging.md`:

> **When invoked:** an agent returns `BLOCKED:` or `VERIFICATION FAILED` twice on the same task.
>
> **Process:**
> 1. **Reproduce** — slot runs the agent's last command itself (not via `claude -p`) to capture the actual error.
> 2. **Triage by error class:**
>    - Permission/sandbox → escalate to a different [[dispatch-paths|path]] (Path A → Path B if cwd issue)
>    - Tool missing → install via the recon scan from `Step 0.0`
>    - Logic error → escalate model tier (Haiku → Sonnet → Opus)
>    - Ambiguous prompt → restart with sharper [[dispatch-preamble]] and pre-decided ambiguities
> 3. **Re-dispatch ONCE** with the triage result encoded as a prompt prefix.
> 4. If still failing, surface to user with the triage report. Do not retry a third time.

**Files to edit:**
- `docs/RECIPES.md` — add the recipe
- `SKILL.md` — add a one-line trigger reference
- `defaults.json` — `discipline.systematic_debugging.max_retries: 2`

---

## Skip list (reasons documented)

- **`superpowers:brainstorming`** — your inspectors (`inspector-mvp-architect`, `inspector-validator`) cover this with finer per-turn control. Absorbing would make swarm prescriptive about creative work, which contradicts the "skills are loadable, not personalities" principle.
- **`superpowers:writing-plans` / `executing-plans`** — already absorbed implicitly via the swarm lifecycle (decompose → dispatch → synthesize). No additional benefit from formalizing.
- **`superpowers:test-driven-development`** — out of swarm's scope. Per-project decision, belongs in project `CLAUDE.md`.
- **`superpowers:using-git-worktrees`** — orthogonal. Swarm doesn't manage worktrees; the user does.
- **`superpowers:requesting-code-review` / `receiving-code-review` / `finishing-a-development-branch`** — workflow skills, not orchestration. No swarm overlap.

---

## Lint pattern absorption (from `anthropic-skills:consolidate-memory` — separate but related)

Karpathy's "lint" operation = `consolidate-memory` skill. This is **already a recipe candidate** for swarm:

**New recipe** — `recipes/wiki-lint.md`:

> **When invoked:** monthly `/schedule` job, OR explicit user "/swarm lint <wiki-path>".
> **Process:** 6-bucket lint (contradictions, orphans, stale, missing-xref, gaps, index-drift). Score REAL/GENERIC/WRONG. Output to `lint-reports/lint-YYYY-MM-DD.md`.
> **See:** `~/Desktop/Ron's Brain/Test/wiki/lint-2026-04-27.md` for the canonical output shape.
> **Reference implementation:** the live `trig_012Z8dPkcugzTV1Yj4C5bkC3` routine (created 2026-04-27) running this lint on `claude-brain` monthly.

**Files to add:**
- `recipes/wiki-lint.md` — the recipe
- `templates/lint-output-skeleton.md` — markdown template matching the Test/ wiki output

---

## Application order (when Ron picks this up)

1. **First** — Lint recipe (low risk, immediately useful, the routine already exists and proves it works)
2. **Second** — Mitigation #9 Tier 2 (highest leverage — catches real fabrication beyond file existence)
3. **Third** — Step 1.5 fan-out gate (cosmetic improvement; swarm currently over-fans-out only mildly)
4. **Fourth** — Systematic debugging recipe (lowest urgency — current "fail twice and surface" is already OK)

Each step is a self-contained PR against `claude-skills`.

## Test plan per absorption

Before merging any of these into the canonical swarm skill:

| Absorption | Test |
| --- | --- |
| Step 1.5 fan-out gate | Send a "fan out 5 trivial reads" task. Confirm gate fires and refuses to fan out (cost ratio fails). |
| Mitigation #9 Tier 2 | Dispatch a Python agent with intentionally-broken test. Confirm slot catches via `VERIFY:` even though file exists. |
| Systematic debugging | Dispatch agent with intentionally bad cwd. Confirm Path A → Path B escalation happens once, not infinitely. |
| Wiki-lint recipe | First monthly run of `trig_012Z8dPkcugzTV1Yj4C5bkC3` is the test. Read output, confirm ≥30% real-finding rate. |

---

## Anti-patterns (don't do these)

- **Don't absorb superpowers as a hard dependency.** If `obra/superpowers` is uninstalled, swarm should still work.
- **Don't import superpowers prompts verbatim.** Their phrasing is general-purpose; swarm's phrasing should be specific to dispatch + headless context.
- **Don't deprecate the original skills.** The absorbed rules are *swarm-internal*; users may still want the standalone skills for non-swarm contexts.
