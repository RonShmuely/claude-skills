# Runtime Adapters

## Scope

A runtime adapter is a thin per-IDE binding that translates the cross-runtime swarm-orchestrator framework into one IDE's native primitives. It is not a fork of the framework, not a parallel implementation, and not a standalone product. The framework (`skills/swarm-orchestrator/`) ships the discipline — model-tier selection, the 9 mitigations, the ship-don't-ask preamble, the dispatch protocol, the typed-output contract. The adapter binds those concepts to one specific execution surface: an Antigravity workspace `AGENTS.md`, a Claude Code `~/.claude/skills/` file, a Cursor `.cursor/rules/` entry, an OpenCode config block. Adapters are thin by design; any logic that can live in the framework should stay there, not be duplicated per-adapter.

---

## The Leech Principle

Adapters integrate by latching onto the host IDE's existing configuration files via `SWARM-MANAGED` block markers — they do not create parallel files alongside the IDE's own config. An Antigravity adapter lives inside `AGENTS.md`, not next to it. A Cursor adapter lives inside `.cursor/rules/swarm.mdc`, not in a separate `swarm-config.json`. This keeps the adapter visible to the IDE's own loader, avoids double-config confusion, and makes uninstall idempotent: strip the `<!-- SWARM-MANAGED START -->` … `<!-- SWARM-MANAGED END -->` block and the host file is back to its pre-adapter state, no residue.

**Example — Antigravity:**
```
# My Antigravity workspace config (hand-authored)
...existing content...

<!-- SWARM-MANAGED START: swarm-orchestrator v3.3 -->
## Scope
This AGENTS.md is a runtime adapter for Antigravity...
<!-- SWARM-MANAGED END -->
```
Idempotent uninstall means a user or script can remove the managed block and re-run the installer without creating duplicate sections. Never nest managed blocks. Never write outside the managed region.

---

## Per-Runtime Checklist

The eight items below are the load-bearing requirements for any adapter. Each item includes what it is, why it matters, and the failure mode it prevents.

### 1. cwd Handling

**What it is:** Before every dispatch, the slot pre-creates the target directory and `cd`s into it before invoking `claude -p`. The slot does not rely on the IDE process's existing cwd.

**Why it matters:** Claude Code's filesystem sandbox is anchored to the process cwd at launch. If the IDE process lives in `/dashboard/`, any write to `~/Desktop/project/` will be rejected with a sandbox boundary error.

**Failure mode prevented:** BLOCKED path errors on file-writing dispatches when the agent's process cwd does not match the intended write scope. The Antigravity reference implementation hard-wires this as the "file-write override" rule: any dispatch that writes files uses Path A (DIRECT headless) with `mkdir -p <target> && cd <target>` before `claude -p`.

```bash
TARGET_DIR="/absolute/path/to/target"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR" && claude -p --model=<MODEL> [flags] "<TASK with absolute paths>"
```

### 2. Permission Posture

**What it is:** The `--dangerously-skip-permissions` flag (or absence of it) is set per user tier, not per task.

**Why it matters:** Auto-granting write permissions for low-trust users bypasses the entire safety surface of the framework's user-tier model. Conversely, withholding it from trusted single-user dev environments creates constant friction with no safety benefit.

**Failure mode prevented:** Permission escalation for non-technical users (Easy-tier running a destructive agent without any grant awareness) and permission friction for power users (Advanced-tier blocked on every Write call in a scoped workspace). See the permission posture table below.

### 3. SWARM_DISPATCH Marker Convention

**What it is:** Every dispatch prompt is prefixed with `[SWARM_DISPATCH:<task-slug>]` where `task-slug` is a short kebab-case identifier of the task.

**Why it matters:** The swarm dashboard is a passive observer of `~/.claude/projects/<slug>/<session>.jsonl`. Without the prefix, the dashboard cannot distinguish swarm-dispatched Claude Code runs from ad-hoc interactive sessions the user has open elsewhere. The slug is also the traceability anchor when debugging a failed dispatch.

**Failure mode prevented:** Dashboard noise — ad-hoc Claude Code sessions showing up in the swarm viewer, making it impossible to isolate swarm run history.

```bash
TASK_SLUG="guide-build-motor-101"
claude -p --model=sonnet [flags] "[SWARM_DISPATCH:$TASK_SLUG] <full dispatch prompt>"
```

The model ignores the bracket prefix as context; the dashboard's log parser uses it as a filter key.

### 4. Ship-Don't-Ask Preamble

**What it is:** Every dispatch prompt ends with the canonical operating-mode preamble (English version at `templates/dispatch-preamble-en.md`, Hebrew version at `templates/dispatch-preamble-he.md`). Never hand-author this block inline.

**Why it matters:** Headless `claude -p` does not enforce non-interactive behavior on its own. Without the preamble, agents ask clarifying questions that will never be answered, produce multiple-choice menus that block the slot, or silently fabricate success when Write calls fail.

**Failure mode prevented:** Agent question-loops that freeze the dispatch; fake `DONE:` lines for artifacts that were never written. The preamble is the only mechanism that reliably forces headless agents into decide-and-ship mode.

**Hebrew/RTL note:** Both preamble variants include the same Hebrew-output rules (canonical CSS preamble, Heebo font import, `dir="auto"` requirements, `lang_hint` artifact tagging). The rules fire on **output content**, not input language — a user typing English can still ask for Hebrew output, and the agent applies the rules silently. A native Hebrew speaker should be able to use any adapter to produce correct Hebrew artifacts without ever instructing the agent in BiDi/RTL mechanics. Adapter authors: pick the preamble that matches the slot's expected primary user language, but trust that either preamble fully covers the Hebrew-output case. See `docs/HEBREW-AND-RTL.md` for the full spec.

```bash
claude -p --model=opus [flags] "$(cat <<'EOF'
[SWARM_DISPATCH:task-slug] <complete task spec>

$(cat ~/.claude/skills/swarm-orchestrator/templates/dispatch-preamble-en.md)
EOF
)"
```

### 5. Confirmation Gates

**What it is:** Before every dispatch, the slot must present the task summary, chosen model, and target path to the user in their language and wait for an explicit `yes` / `כן` / `ok`. Silent dispatch is never permitted.

**Why it matters:** The adapter decides ambiguities on the user's behalf (format, path, defaults) before dispatch. If the adapter's default choices are wrong, the confirmation step is the last chance to catch it before a headless agent ships the wrong output.

**Failure mode prevented:** Irreversible wrong-output dispatches — an agent that writes 300 lines of Hebrew copy to the wrong path when the user wanted English, or a destructive file-write the user didn't authorize.

Gate phrases: Hebrew *"אישור?"* / English *"Confirm?"*. Short. Wait for affirmative before shelling out. Skip the gate only for read-only status checks on already-dispatched jobs.

### 6. Artifact Verification (Mitigation #9)

**What it is:** After every dispatch that should produce files, the slot verifies each expected file exists on disk and is non-empty before reporting success to the user.

**Why it matters:** Agents have been observed emitting fabricated success-shaped output — paths, line counts, `DONE:` lines — when their Write calls were silently denied by the sandbox. The agent's stdout is not a trustworthy artifact report; the filesystem is.

**Failure mode prevented:** Relayed fake `DONE:` claims. User believes a guide was built; it was not. The next step in their workflow operates on a nonexistent file.

```bash
EXPECTED="$HOME/Desktop/output/guide.html"
[ -f "$EXPECTED" ] && [ -s "$EXPECTED" ] \
  && echo "VERIFIED: $EXPECTED ($(wc -c < "$EXPECTED") bytes)" \
  || echo "VERIFICATION FAILED: $EXPECTED missing or empty"
```

If verification fails, report the failure to the user truthfully. Offer re-dispatch with stricter prompt, model escalation, or manual troubleshooting. Do not relay the agent's fake `DONE:` line.

### 7. Dashboard Observer Integration

**What it is:** The adapter shells out to `claude -p` directly. It never POSTs to the dashboard's `/api/dispatch` endpoint.

**Why it matters:** `/api/dispatch` was removed in dashboard v2.2. More importantly, dispatching via the dashboard's Flask process inherits the dashboard's cwd as the agent sandbox — triggering the sandbox boundary failure described in item #1. The dashboard observes by reading `~/.claude/projects/` logs passively; it does not participate in the dispatch chain.

**Failure mode prevented:** cwd sandbox mismatch when dispatch is routed through the dashboard process; use of a deprecated endpoint that no longer exists.

Pre-session reachability check (run once, cache the answer):
```bash
curl -s --max-time 1 http://127.0.0.1:5173/api/jobs > /dev/null && echo UP || echo DOWN
```
If `DOWN`, dispatch via DIRECT paths. Never fail dispatch because the dashboard is not running.

### 8. BLOCKED Protocol

**What it is:** After the dispatch returns, scan stdout for lines starting with `BLOCKED:`. If found, surface the reason verbatim to the user. Do not auto-retry. Do not paraphrase.

**Why it matters:** `BLOCKED:` is a signal the agent emitted deliberately — it hit a hard stop (missing file, no write access, unauthorized destructive action, unreachable external service) and chose to halt rather than fabricate. Auto-retrying or paraphrasing the reason discards the agent's diagnosis.

**Failure mode prevented:** Silent retries that loop on the same hard stop; user-facing error messages that hide the actual cause and make debugging impossible.

If the agent returned a question instead of `BLOCKED:` (rare, indicates preamble failure), that is a prompt-construction failure on the adapter's end — tighten the prompt and re-dispatch with user awareness.

---

## Permission Posture by User Tier

| Tier | Profile | Default permission flags | Rationale |
|---|---|---|---|
| Easy | Non-technical user | none (restrictive defaults) | Never auto-grant; non-technical user; destructive writes must be explicitly scoped per-call |
| Advanced | Trusted power user | `--dangerously-skip-permissions` | Trusted single-user dev; agents work inside pre-created scoped target dirs |
| Developer | Contributor / maintainer | configurable per workspace | Audit and debug needs vary; adapter author sets flags in workspace config |

**Hard rule:** Easy-tier adapters must never include `--dangerously-skip-permissions`. This is not a default to override; it is a design constraint. The Easy-tier adapter (Phase 2, separate `AGENTS.md` template) will run with restrictive defaults and explicit per-call write allowlists.

---

## Rule Precedence — Project Rules Beat Global Rules

When a project-level `CLAUDE.md` and a global `~/.claude/CLAUDE.md` disagree (e.g., global says "answer from training, only research if guessing," project says "always WebFetch the latest published version"), the dispatched agent obeys the **project** rule. Validated in run #3 case 10: the agent did 2 WebFetches per the project override and answered correctly, in conscious deviation from the global default.

**What this means for adapters:** when an adapter ever implements rule enrichment (e.g., a future `_enrich_with_rules` layer that merges global + project + dispatch-specific instructions into the prompt), project rules MUST be applied AFTER global rules in the merged context so they shadow on conflict. Naive concatenation in the wrong order will let stale global rules override fresh project policy.

This is documentation of the intended merge order, not yet a code-level constraint — `_enrich_with_rules` does not currently exist. When implemented, it MUST honor this precedence.

---

## Dispatch Protocol Skeleton

Any adapter — regardless of IDE — implements these steps in order:

1. **Detect runtime and verify tooling.** Confirm `claude` is on PATH (or at known absolute path). Confirm auth is cached (`claude --version` or equivalent liveness check). If either fails, surface the error to the user before attempting any dispatch.

2. **Reachability check on dashboard.** Run the 1-second curl ping. Cache the result for the session. Re-check only if a `DASHBOARD` dispatch fails with connection-refused. Do not let dashboard state block dispatch.

3. **Classify intent and model.** Map the user's request to a task type and pick the model tier per `docs/MODEL-TIERS.md`. Default up when ambiguous. State the choice to the user so they can override.

4. **Confirm with user in their language.** Present task summary, model, target path. Wait for affirmative. Short phrase. No dispatch before confirmation.

5. **Pre-create target dir and cd into it.** If the dispatch writes files: `mkdir -p <target> && cd <target>`. If read-only: optional; stay in workspace dir.

6. **Build the dispatch prompt.** Pre-decide all ambiguities (format, path, style, language, length). Prefix with `[SWARM_DISPATCH:<task-slug>]`. Append the canonical ship-don't-ask preamble from `templates/dispatch-preamble-en.md` or `templates/dispatch-preamble-he.md`. Use absolute paths throughout.

7. **Run `claude -p`.** Include `--model=<X>` and `--dangerously-skip-permissions` per tier. Capture stdout.

8. **Scan stdout for `BLOCKED:` first.** If present, surface verbatim. Stop. Do not retry automatically.

9. **Verify artifacts on disk (Mitigation #9).** For file-writing dispatches: check existence and non-empty size. If verification fails, report failure truthfully. Do not relay agent-reported `DONE:` claims.

10. **Summarize to user in their language.** Only after step 9 passes. Quote the agent's verbatim `DONE:` line if clean. Do not fabricate content the agent didn't produce.

---

## Anti-Patterns (DO NOT)

1. **POST to `/api/dispatch`.** This endpoint was deprecated in dashboard v2.1 and removed in v2.2. Adapters that still call it will fail silently on current dashboard versions. Dispatch always happens via direct shell-out.

2. **Spawn `claude -p` from the dashboard's process.** The dashboard Flask app runs from its own directory. Subprocesses inherit that cwd. File writes outside `swarm-dashboard/` will hit sandbox boundary errors. Direct shell-out from the slot with explicit `cd` is the only safe pattern.

3. **Auto-grant permissions for Easy-tier users.** `--dangerously-skip-permissions` must never appear in Easy-tier adapter configs. Non-technical users do not have the context to anticipate what an agent will write; grant authority must remain with the adapter's per-call allowlist.

4. **Trust agent-reported success without disk verification.** Agents have been observed fabricating success-shaped output — file paths, line counts, `DONE:` lines — after Write calls were silently denied. The filesystem is the source of truth; agent stdout is not.

5. **Hand-author the ship-don't-ask preamble inline.** The canonical preamble lives in `templates/dispatch-preamble-en.md` and `templates/dispatch-preamble-he.md`. Inline copies drift. A drifted preamble is the most common cause of agent question-loops and fake-success output, and the hardest to diagnose because the symptom looks like agent behavior rather than adapter error.

---

## Reference Implementation

A private Antigravity adapter workspace (`AGENTS.md`, Phase A v3.3) — the canonical worked example, hardened through three iterations of real-world testing. The `AGENTS.md` itself is not redistributable (it lives in a private project workspace), but the patterns it demonstrates are documented in this file and in the skill's `SKILL.md` lifecycle. New adapters should follow the per-runtime checklist above; the source-of-truth for behavior is the canonical preamble in `templates/dispatch-preamble-en.md` / `-he.md`, not the Antigravity workspace.

**What it covers:**

- Scope header declaring the file as a runtime adapter, not a standalone config
- Permission posture declaration (Advanced-tier, single-user, explicit note that Easy-tier will differ)
- Dashboard role clarification (passive observer, never dispatch target)
- SWARM_DISPATCH marker convention explained
- Verification gate (Mitigation #9) as a non-negotiable
- In-slot vs dispatch routing table (trigger keywords, Hebrew and English)
- **4 dispatch paths:**
  - **Path A — DIRECT headless** (default; required for all file-writing dispatches)
  - **Path B — DIRECT-PARALLEL** (multiple agents, dashboard down; shell `&` backgrounding with `wait`)
  - **Path C — DIRECT-BACKGROUND** (single agent, user wants slot free, dashboard down; `nohup` + job ID)
  - **Path D — DASHBOARD** (when reachable and worth the overhead; opportunistic upgrade only)
- **Path A in 9 steps** (Steps 1–9 with Step 7 = artifact verification / Mitigation #9)
- Model resolution table (intent → `haiku` / `sonnet` / `opus` / in-slot)
- Confirmation gates (mandatory before every dispatch, optional for read-only status checks)
- Error handling (non-zero exit, timeout, `claude` not on PATH, unclear Hebrew transcription)

---

## What's Still TBD

The following are not yet specified by the framework for adapters and should not be hand-authored — wait for canonical definitions before implementing:

- **Per-tier credential pools.** Hive Layer 1 / 2 / 3 credential routing (per-tier credential pools across Easy / Advanced / Developer) has not been specified for adapter-level dispatch. Current adapters use a single ambient `claude` auth. Multi-tenant credential routing is deferred to the Hive SaaS architecture layer.

- **Federated learner integration.** The federated learner (open-core closed module, Hive plan) will eventually provide per-adapter learning signals. How adapters emit events to the learner and consume routing updates from it is TBD.

- **Mitigation #5 META-block handling for single-agent dispatches.** The META block contract is defined for swarm muscle agents (see `docs/PROTOCOL.md` Mitigation #5 and `templates/meta-block.md`). Whether single-agent adapter dispatches (Path A DIRECT headless, one agent, one task) should require or parse META blocks is not yet specified. Current reference implementation does not enforce it for single-agent dispatches.

---

> **Note on tier names:** the three tiers (Easy / Advanced / Developer) were originally designed against three real-world personas — a non-technical relative, a power user, and a developer contributor. The framework keeps the abstract labels for portability; the persona-flavored design history lives in the project's private notes.
