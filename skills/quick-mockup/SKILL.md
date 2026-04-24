---
name: quick-mockup
description: Generate a quick visual HTML mockup in MachineGuides/guides/_mockups/ for rapid idea iteration — font comparisons, layout experiments, before/after typography demos, UI variants. Uses the canonical dark-industrial template. Trigger on explicit "/quick-mockup", "create a mockup for X", "mock up X", "show me X visually", "spin up a mockup of X". Do NOT trigger for real diagnostic guides — those go through `build_generic_guide.py` with a proper payload.
---

# Quick Mockup

Fast, disposable HTML mockups for generating and comparing ideas. Not real diagnostic guides — real guides always go through `build_generic_guide.py` with a `diagnoses/<slug>.json` payload.

## When to fire

Trigger ONLY for clearly-labeled experiments, comparisons, or idea iteration:

- "/quick-mockup dash comparison"
- "create a mockup for the hypothesis tracker layout"
- "mock up two header styles"
- "show me three color palette options visually"
- "spin up a mockup of how error states would look"

Do NOT trigger for:
- Actual diagnostic guides — use `build_generic_guide.py` + payload
- One-shot chat questions — answer inline
- Modifying an existing approved guide — that's an Edit, not a mockup

If unclear, ask: *"Is this a quick visual experiment (quick-mockup) or a real diagnostic guide (build_generic_guide.py)?"*

## Step 1 — Gather inputs

Before writing any file, get:

1. **Slug** (short, lowercase, underscores): e.g. `dash_comparison`, `hypothesis_hero`, `font_alternatives`. Ask if not given.
2. **Topic title** (Hebrew, short): what this mockup is about. Ask if not given.
3. **Subtitle** (English, technical): one-line description of what's being compared/shown.
4. **Content spec**: what blocks to include. Options:
   - **Single focus** — one main block showing the idea
   - **Side-by-side** — baseline vs. applied (2 columns)
   - **Gallery** — many variants stacked vertically for scan
   - **Interactive** — with a selector/toggle at top

If the user's request is concrete enough, skip the questions and infer. Only ask when genuinely ambiguous.

## Step 2 — Read the canonical template

```
C:\Users\ronsh\Desktop\MachineGuides\guides\_mockups\_template.html
```

The template has:
- Full CSS token set (matches MachineGuides dark-industrial theme)
- `MOCKUP` banner (keep it — it's what marks this as non-canonical)
- Placeholder comments marked `<!-- PLACEHOLDER:... -->` and `__TOKENS__` for easy replacement
- Commented-out examples of: side-by-side split, callouts, key/value rows, font selector

Tokens to replace:
- `__TOPIC__` → the slug, uppercase, for the banner and title
- `__TITLE_HEB__` → Hebrew title
- `__SUBTITLE_EN__` → English subtitle
- `__LABEL__`, `__BODY_TEXT__`, `__KEY__`, `__VALUE__`, `__CALLOUT_TEXT__`, `__BASELINE_TEXT__`, `__APPLIED_TEXT__` → filled from the content spec

Uncomment the example blocks that match the chosen layout; delete the ones that don't.

## Step 3 — Write the mockup

Write to:

```
C:\Users\ronsh\Desktop\MachineGuides\guides\_mockups\<slug>.html
```

Rules:
- Always use real sample content — never lorem ipsum. Pull from existing `diagnoses/*.json` payloads or use real Hebrew tech sentences the user cares about.
- Keep the `MOCKUP` banner. It's the signal that this is not a live artifact.
- Use straight quotes `"..."` in Hebrew (per project decision).
- Use `–` (`U+2013` en-dash) for em-dashes and `…` (`U+2026`) for ellipsis (matches builder output).
- Apply `<bdi>` wrapping only if the mockup is specifically about BiDi — otherwise trust `[dir="auto"]` in containers.

## Step 4 — Let the hook open it

Do not manually open the file. The `hook_open_md_viewer.py` fires on Write, auto-opens the HTML in the default browser, and reveals the folder (only the first time the path is seen).

Just tell the user: "[filename] is visible in the Launch preview panel — open in Chrome."

## Step 5 — Offer iteration paths

After the mockup is rendered, offer next steps:
- Tweak this one (change a variant, add a row, switch font)
- Spawn a sibling mockup (different angle on the same idea)
- Promote an idea to the real builder (e.g., "font B looked right — shall we apply to the canonical template?")

## Archive discipline

When a mockup is superseded or the experiment is done, **move it to `guides/_mockups/_archive/<date>_<reason>/`** — never delete. The rule from `feedback_never_delete_archive.md` applies here too.

## What this skill is NOT

- Not a replacement for `build_generic_guide.py`
- Not a way to create real diagnostic content — only visual experiments
- Not for non-HTML mockups — if the user needs a sketch/wireframe in another format, this skill doesn't apply
- Not for hand-authoring new canonical templates — those live outside `_mockups/`

## Quick-start example

User: `/quick-mockup font weights comparison`

Claude:
1. Reads `_template.html`
2. Sets slug `font_weights_comparison`, topic "השוואת משקלי פונטים"
3. Populates with a gallery of the same Hebrew sentence at 300/400/500/700/900 weights
4. Writes to `guides/_mockups/font_weights_comparison.html`
5. Reports: visible in preview panel, ready for review
