# Muscle prompt — workflow extraction

[M] Identify the recurring workflow pipeline of the repo at `{{target_repo}}`.

You are READ-ONLY. The previous muscle (repo-inventory) gave you the lay of the land. Now answer: **what does this repo USUALLY do?**

A "workflow" is a pipeline you can describe in 3–7 numbered steps that an outsider could follow. For a guides repo it might be: edit JSON payload → run builder script → review HTML → approve → archive old versions. For a webapp repo: pull → install → run dev server → make changes → run tests → push.

## What to gather

1. **The primary creation pipeline.** What artifact is the repo's main output? (HTML guides, deployed webapp, JSON specs, podcast episodes, etc.) Trace the steps from "empty input" to "shippable artifact."
2. **The validation pipeline.** Is there a review/approval step before something is considered done? Who reviews? What flips a draft to approved?
3. **The archive / cleanup pipeline.** When something is deprecated, where does it go? Is there a never-delete-only-archive convention?
4. **Side workflows.** Things the repo does occasionally — backfills, schema migrations, retro-fixes, postmortems.
5. **Hot signals.** Recurring strings in scripts/docs that indicate a workflow trigger (e.g., `build_generic_guide.py --machine X`, `approve_diagnosis.py`, `vercel deploy --prod`, `npm run audit`).
6. **What gets WRITTEN by hand vs by tooling.** Critical for a swarm addon — if a tool generates HTML, the addon's skills must NEVER hand-author HTML (memory note `feedback_machineguides_builder_only.md` is exactly this rule for MachineGuides).
7. **Confirmation gates.** Are there places where the workflow REQUIRES human confirmation before proceeding? (e.g., a `--yes` flag, a "review the diff first" step.)

## Deliverable (under 700 words, exact shape)

## The primary pipeline
1. ...
2. ...
3. ...
(numbered, 3–7 steps)

## Validation pipeline
- Trigger: ...
- Steps: ...
- Approver: ...

## Archive / cleanup pipeline
- Trigger: ...
- Destination: ...
- Convention: never delete / hard delete / something else

## Side workflows
- Backfill: ...
- Migration: ...
- Postmortem: ...

## Hot signals (commands / scripts that trigger workflows)
- `<command>` — does X
- `<command>` — does Y

## Hand-authored vs tooling-generated
- Generated: <list of artifact types> (the addon's skills MUST use the tool for these)
- Hand-authored: <list>

## Confirmation gates
- ...

## Locked rules from existing AI files
Quote any rule from AGENTS.md/CLAUDE.md/.cursor/rules that the addon's skills must respect (e.g., "no fabricated data", "Hebrew UI everywhere", "never hand-author HTML").

## Notes
- Anything ambiguous; flag for the synthesis agent to ask the user about.

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
tools_used: {"Read": N, "Grep": N, "Glob": N}
---END META---
