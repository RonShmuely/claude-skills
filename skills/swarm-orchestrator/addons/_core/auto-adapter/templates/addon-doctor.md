# Muscle prompt — addon doctor

[H] Doctor pass on the freshly generated addon at `{{addon_output_dir}}`.

You are READ-ONLY. Do not modify any file. Your job is to validate the addon-synthesis muscle's output and report findings.

## Validate

1. **Manifest parses.** `addon.yaml` is valid YAML. Required keys present (name, version, description, swarm_orchestrator_min, provides).
2. **All `provides` paths exist.** Every file referenced in the manifest's `provides` block must exist on disk.
3. **No file references outside the addon dir.** Every relative path resolves under `{{addon_output_dir}}`.
4. **Skill frontmatter validates.** Every `skills/*.md` has parseable YAML frontmatter, required keys (name, version, description, triggers, preferred_capability, fallback_capability).
5. **Trigger uniqueness.** No two skills declare the same exact trigger keyword. Collisions = warning.
6. **Capability names valid.** Every `preferred_capability` and `fallback_capability` is one of the canonical capability keys: `hebrew_prose`, `tool_execution`, `architectural_high_blast`, `code_generation_english`, `critic_verification`, `image_understanding`.
7. **Locked-rule citations.** Skills that reference source-repo rules quote them, not paraphrase. Spot-check 3 quoted rules against the workflow-extraction output if available.
8. **No `rm -rf` / `Remove-Item` in skill bodies or hooks.** Per never-delete-only-archive convention. Warn if found.
9. **No fabricated data.** Look for percentages, accuracy numbers, or confidence scores in skill bodies that look invented (no source).
10. **Status is `disabled`.** Per the safety gate; if `enabled`, that's a finding (the synthesis agent disobeyed).
11. **Conflicts with existing addons.** List the addons currently loaded; flag if this addon's skill names or recipe names collide.

## Deliverable (under 500 words, exact shape)

## Doctor verdict: PASS / WARN / FAIL

## Manifest validation
- [✓ / ✗] Required keys present
- [✓ / ✗] swarm_orchestrator_min satisfied
- [✓ / ✗] All provides paths resolve

## Skill validation
- N skills checked
- ✓ All have valid frontmatter
- WARN: <skill-name> shares trigger "X" with <other-skill-name>
- ...

## Capability validation
- All capability names valid? Y/N
- Issues: ...

## Locked-rule citation check
- Skills citing source-repo rules: N
- Spot-check passed: K of N quotes match source verbatim
- Discrepancies: ...

## Hard-rule violations
- [✓ / ✗] No `rm -rf` / `Remove-Item`
- [✓ / ✗] No fabricated data
- [✓ / ✗] status: disabled

## Conflicts with currently loaded addons
- Existing addons checked: <list>
- Collisions: <list or "none">

## Recommendations
- Top 3 things the user should review before running /swarm-addons enable.

---META---
confidence: 0.XX
method: "Read manifest + skill files; cross-reference with currently loaded addons via lib/addons.py."
not_checked: [...]
sample_size: N or "exhaustive"
tools_used: {"Read": N, "Glob": N}
---END META---
