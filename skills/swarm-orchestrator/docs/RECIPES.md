# Recipes — Reusable Swarm Patterns

Pre-designed swarm shapes you can fire by name. Each recipe defines: the decomposition, muscle tier, safety tag, and synthesis shape.

## Recipe: `wow-demo` / `week-start-triage` ⭐ flagship

**Trigger phrases:** *"fire the wow demo"*, *"run the week start triage"*, *"wowdemo"*

**Goal:** Exercise the full framework in under 5 minutes — mixed-tier parallel muscles + sequential adversarial reviewer, producing a prioritized Top-5-actions-this-week list.

**Decomposition:** 5 muscles + 1 reviewer — covers what's in flight (loose files), what's accumulating (Downloads), what's in the pipeline (diagnoses status), what's open (TODOs + checkboxes), what's shipping (git momentum). Reviewer synthesizes across dimensions.

**Muscle tier:** 3× Haiku + 2× Sonnet + 1× Sonnet reviewer.

**Safety:** `[L]` for informational muscles, `[M]` for decision-driving, `[H]` reviewer.

**Cost / time:** ~$0.80 / ~4–5 min wall time.

**Use when:** demoing the framework, weekly Monday-morning triage, smoke-testing after framework changes.

**Full spec:** [`docs/WOW-DEMO.md`](WOW-DEMO.md).

---

## Recipe: `folder-audit`

**Goal:** Audit a large project folder for dead code, duplicates, orphans, stale files, reclaimable space, and TODOs. Produce merged findings.

**Decomposition:** 5 non-overlapping sections based on folder structure (glob top-level, bucket by kind).

**Muscle tier:** Haiku × 5 (narrow structured output per section).

**Safety:** `[M]` — findings drive cleanup actions.

**Dispatch shape:**

```
Section A: code/src folders
Section B: data/assets folders  
Section C: pipeline/build folders
Section D: top-level scripts
Section E: docs + config + archive
```

Each muscle audits only its scope with explicit exclusions. Uses `templates/audit.md` as base.

**Synthesis:** Unified table with (Section, Size, Files, Last Active, Health, Reclaimable). Flag anything `confidence < 0.7` as unverified.

**Reference:** `templates/audit.md`.

---

## Recipe: `inventory`

**Goal:** Quick inventory of a folder — size, file counts, top consumers, activity timeline.

**Decomposition:** 1 muscle for single folder, or N muscles for N folders in parallel.

**Muscle tier:** Haiku.

**Safety:** `[L]` — output is descriptive, not decision-driving.

**Reference:** `templates/inventory.md`.

---

## Recipe: `diagnose-machine-fault`

**Goal:** Given a machine fault description, produce a ranked diagnosis with actionable next steps.

**Decomposition (heterogeneous team):**

1. **Haiku scout** — search local PDFs + NotebookLM for fault code, parts, symptoms. Extract structured data.
2. **Sonnet analyst** — reason over scout's extract + user symptom description. Propose top 3 hypotheses with reasoning.
3. **Opus judge** — read both + sample raw manual pages the scout cited. Make the final call, write the diagnosis guide.

**Muscle tier:** mixed (see above).

**Safety:** `[H]` — diagnosis drives customer machine repair.

**Integration:** Fits the pattern in the user's `machine-diagnose` skill.

---

## Recipe: `research-brief`

**Goal:** Synthesize a position / brief from N sources (papers, docs, manuals).

**Decomposition:** N muscles, one per source, each extracting (claim, evidence, confidence).

**Muscle tier:** Sonnet (reasoning required to extract nuance).

**Safety:** `[M]` — output will be quoted / acted on.

**Synthesis:** Orchestrator reads all N extracts + reviewer critiques for missed cross-source patterns.

**Reviewer loop:** Yes — Opus reviewer reads all extracts + samples raw source text.

---

## Recipe: `code-review-swarm`

**Goal:** Review a large PR / diff for bugs, style, architecture concerns.

**Decomposition:** 4 muscles, each with a specialist lens:

1. **Haiku** — style & formatting (linters, patterns)
2. **Sonnet** — correctness & edge cases
3. **Sonnet** — architecture & abstraction
4. **Sonnet** — test coverage

**Safety:** `[M]` for normal PRs, `[H]` for merges to main/production.

**Reviewer loop:** Opus meta-reviewer reads all 4 critiques + the raw diff. Resolves conflicts.

---

## Recipe: `doc-audit`

**Goal:** Audit a markdown doc library for broken links, stale content, missing cross-refs.

**Decomposition:** Bucket docs by topic; 1 muscle per bucket.

**Muscle tier:** Haiku (narrow grep-heavy).

**Safety:** `[L]`.

---

## Recipe: `dedup-scan`

**Goal:** Find duplicate or near-duplicate files across a folder.

**Decomposition:** By file type or directory subtree.

**Muscle tier:** Haiku for exact-match (hash comparison), Sonnet for near-duplicate (semantic similarity).

**Safety:** `[M]` — recommendations drive deletion.

---

## Recipe: `bulk-classify`

**Goal:** Classify N items (documents, images, logs) into K categories.

**Decomposition:** Chunk items into batches of ~10, one muscle per batch.

**Muscle tier:** Haiku for structured classification, Sonnet if categories are fuzzy.

**Safety:** `[L]`.

**Future integration:** When Ollama is wired in, this recipe should use Ollama for bulk batches — it's $0 and the task is narrow-and-structured.

---

## Recipe anatomy

Every recipe has:

```yaml
name: folder-audit
goal: one sentence
decomposition: how the task splits, with count
muscle_tier: Haiku / Sonnet / Opus / mixed
safety: [L] / [M] / [H]
dispatch_template: path to templates/*.md to base from
synthesis_shape: what the merged output looks like
reviewer_loop: yes / no
```

## Adding a new recipe

1. Run the task manually one time — document what worked
2. Write the decomposition: how many muscles, what scope each
3. Pick the tier for each muscle honestly (default up when in doubt)
4. Pick the safety tag — be honest about stakes
5. Draft the dispatch template under `templates/`
6. Add the recipe spec to this file

## Graduating a recipe to a dashboard button

When a recipe gets fired 3+ times, it's worth turning into a UI affordance:

1. Dashboard gets a "Run Recipe" dropdown
2. Each recipe has a form: paths to target, any parameters
3. Click → Flask spawns the swarm by the recipe's spec
4. Dashboard shows the swarm grouped as a recipe-run

At that point the orchestrator isn't strictly needed in-session anymore — the dashboard becomes its own Gateway. That's the graduation path to the OpenClaw-style architecture (`docs/ARCHITECTURE.md` explains the tradeoff).
