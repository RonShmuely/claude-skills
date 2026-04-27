# Muscle prompt — domain skills synthesis

[M] Propose the skill set the swarm should add for `{{target_repo}}`.

You have read the inventory and the workflow extraction. Now translate that knowledge into **swarm-orchestrator skills** — modular markdown files with YAML frontmatter that load on intent and unload on context shift.

## Core constraint (read this twice)

A swarm-orchestrator skill is NOT a personality. It is a loadable capability. Mom (or any user) might pivot from one skill to another in the same session. Each skill must be self-contained: triggers, tool list, preferred capability, unload signals, and a short body that tells the orchestrator how to behave when the skill is loaded.

If the repo's workflow has 5 distinct activities, you propose 5 skills. Not one mega-skill. Specialization is the point.

## What to deliver

For each skill you propose, provide:

```yaml
---
name: <kebab-case>
version: 0.1.0
description: One sentence — what this skill does for the orchestrator.

triggers:
  keywords: [<English>, <Hebrew>, <other-language-if-relevant>]
  patterns:
    - "<JS regex>"
  intents: [<canonical-intent-name-snake_case>]

preferred_capability: <one-of: hebrew_prose | tool_execution | architectural_high_blast | code_generation_english | critic_verification | image_understanding>
fallback_capability: <one-of the above>

tools: [<tool-name>, ...]      # e.g., specific MCP tool names, Bash, Read, Write
confirmation_required: <true | false | oob>
unload_signals:
  keywords: [<words that mean "user pivoted away">]
  on_intent_classified_as: [<other-intent-names>]
  ttl_messages: 6
priority: <0-100>
language_hints: [<he | en | ...>]
---
# Body (markdown) — instructions to the orchestrator when this skill is active.
# Reference any locked rules from the workflow extraction (e.g., "never hand-author HTML",
# "always use build_generic_guide.py for new guides").
```

## Constraints from the repo's locked rules

Apply every rule the workflow extraction surfaced. If the repo says "never hand-author HTML, always use the builder," every skill that produces HTML must call the builder, never write HTML directly. If the repo says "Hebrew UI everywhere," every skill must default to Hebrew triggers + Hebrew confirmations.

If the repo has a "never delete, only archive" rule, no skill in your output may use `rm -rf`, `Remove-Item`, or `unlink`. Skills that retire artifacts must move them to `_archive/<date>/`.

## Output shape (under 1500 words)

Open with a one-paragraph summary of the proposed skill set and how they cover the workflow.

Then dump each skill as a fenced YAML+markdown block as above.

End with a recipe-or-two recommendation: which workflows in the repo are worth promoting to swarm-recipes (multi-agent fan-out)?

```yaml
recipes:
  - name: <recipe-name>
    why: ...
    fan_out:
      - { tier: <haiku|sonnet|opus>, safety: <L|M|H>, scope: "..." }
      - { tier: ..., safety: ..., scope: "..." }
```

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
tools_used: {"Read": N, "Grep": N}
---END META---
