# Hebrew + RTL handling guide

> Required reading for runtime adapter authors and skill authors whose work touches Hebrew or any RTL content.

The swarm-orchestrator framework was designed Hebrew-first. Every surface that renders user or agent text — dashboard cards, generated HTML artifacts, confirmation prompts, error messages — must handle bidirectional text correctly. Latin-only assumptions break the moment a Hebrew character appears.

This document is the canonical reference for how to do that across the framework.

## When these rules apply (read carefully — this is the load-bearing point)

**Rules fire on OUTPUT content, not INPUT language.** A user can:

- Type English, ask for English output → rules don't apply (no Hebrew anywhere).
- Type Hebrew, ask for Hebrew output → rules apply (obvious).
- **Type English, ask for Hebrew output** → rules STILL apply (Hebrew shows up in the artifact).
- Type Hebrew, ask for mixed output → rules apply (any Hebrew at all).

A Hebrew-native user must be able to use the framework — via Antigravity, Claude Code, Cursor, or any other adapter — to **generate** Hebrew artifacts without ever instructing the agent in BiDi/RTL mechanics. The framework applies these rules silently the moment Hebrew content is being produced.

This means **every dispatch preamble** (English and Hebrew alike) embeds the same Hebrew-output rules. The trigger is "your artifact contains Hebrew chars," not "the human spoke Hebrew." See `templates/dispatch-preamble-en.md` and `templates/dispatch-preamble-he.md` — both contain the identical Hebrew-output checklist.

---

## Three rules that cover 90% of cases

1. **Use `dir="auto"` on every element that displays user or agent content.** Never hardcode `dir="rtl"` unless the element is *guaranteed* Hebrew-only forever.
2. **Use a font fallback chain that includes a Hebrew-capable font.** Mono fonts (JetBrains Mono, Geist Mono, IBM Plex Mono) have no Hebrew glyphs — Hebrew chars rendered in those fall back to whatever the OS picks, often poorly. Add Heebo, Noto Sans Hebrew, or similar to the chain.
3. **Latin-only content (slugs, callsigns, file paths, model names) gets `dir="ltr"` explicitly.** Hebrew prose doesn't make `j_b4abd21d` a Hebrew identifier; force LTR so it renders deterministically.

If you follow only those three rules everywhere, the framework's Hebrew rendering works.

---

## When to use which `dir` value

| Value | When | Example |
|---|---|---|
| `dir="auto"` | Element content is dynamic and could be any language | Agent description, prompt body, error message, search input, textarea |
| `dir="rtl"` | Element content is *always* Hebrew/Arabic forever | A Hebrew-only branding label, a hardcoded Hebrew button caption in a Hebrew-only UI |
| `dir="ltr"` | Element content is identifier/code that must render LTR even inside RTL parent | Job IDs, callsigns, file paths, model names, command snippets shown inline |
| (omitted) | Element is structural (containers, layout flex) and contains no text | `<div class="card">`, `<section>` — direction inherited from `<html>` |

The orchestrator's default is `<html lang="en" dir="ltr">`. Per-element `dir="auto"` is what flips individual content nodes when their content is Hebrew. Don't switch the whole page to RTL — the chrome stays LTR.

---

## CSS — the canonical preamble

Every dashboard template, every generated HTML artifact, every adapter-rendered surface should declare this once in its CSS:

```css
:root {
  --font-bidi: 'JetBrains Mono', 'Geist Mono', 'Heebo', 'Segoe UI', system-ui, sans-serif;
}
[dir="auto"], [dir="rtl"] {
  font-family: var(--font-bidi);
}
[dir="auto"] {
  unicode-bidi: plaintext;   /* let the browser detect direction from content */
}
```

Plus the Heebo font import in `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700&display=swap" rel="stylesheet">
```

Heebo was chosen because it pairs well with mono fonts (similar x-height, neutral letterforms). Substitute Noto Sans Hebrew / Frank Ruhl Libre / Rubik if your design system requires.

---

## Layout gotchas

When an inline element flips from LTR to RTL via `dir="auto"`, watch for:

| Issue | Fix |
|---|---|
| Punctuation drifting to the wrong side | `unicode-bidi: plaintext` (in the canonical CSS above) handles this |
| Latin names inside Hebrew prose breaking direction | Wrap the Latin run in `<span dir="ltr">…</span>` |
| Numbers in tables looking inconsistent | Force the cell `dir="ltr"` if the column is purely numeric |
| Flex/grid items ordering surprisingly | Use `margin-inline-start` / `margin-inline-end` instead of `margin-left` / `margin-right` if you want symmetric layout. Otherwise leave `dir="ltr"` on the container and only flip the text nodes inside. |
| Tooltips with Hebrew strings | The `title` attribute uses OS bidi. `dir="auto"` on the element handles its content; tooltip rendering is the OS's responsibility. |

The dashboard uses the **second** approach — the chrome stays LTR, only individual text-content nodes get `dir="auto"`. This preserves the dashboard's visual identity and avoids re-laying-out the entire UI per agent run.

---

## Per-tier user expectations

| Tier | Expectation | What the adapter must do |
|---|---|---|
| Easy | Native Hebrew throughout. Every confirmation, every error, every label in Hebrew. UI feels Hebrew-first even if implemented LTR-default with per-element flip. | Adapter renders Hebrew confirmations + uses `dir="auto"` everywhere user content appears. Easy-tier UI may eventually warrant a fully RTL chrome — Phase 2+. |
| Advanced | English chrome, Hebrew/English content interchangeable. Hebrew code comments, Hebrew commit messages, Hebrew search queries all render correctly. | The current Phase A v3.3 baseline — already meets this. |
| Developer | Code-first. Hebrew rare in chrome but possible in test fixtures or content samples. | `dir="auto"` on dynamic-content nodes is sufficient. |

---

## Generated HTML artifacts (auto-adapter, future skill outputs)

When a synthesis muscle writes HTML for a Hebrew workspace:

- `<html lang="he" dir="rtl">` if the artifact is Hebrew-only.
- `<html lang="en" dir="ltr">` + per-element `dir="auto"` if the artifact mixes languages.
- The artifact manifest entry must include `"lang_hint": "he" | "en" | "mixed"` so downstream consumers can pick the right rendering surface. See `addons/_core/auto-adapter/templates/addon-synthesis.md` for the contract.

When generating a Hebrew artifact, the agent must also emit the canonical CSS preamble (above) inline in `<style>` so the file is self-contained.

---

## Dashboard-specific pattern (reference implementation)

The reference implementation lives in `packages/swarm-dashboard/templates/`. Patches summary:

- `<html lang="en" dir="ltr">` on every template (cockpit / dispatch / index / theater)
- Heebo Google-Fonts import in `<head>`
- Canonical CSS preamble (3 lines) at top of `<style>`
- `dir="auto"` on every node that renders `${esc(a.description)}`, `${esc(a.final_text)}`, `${esc(a.last_text)}`, `${esc(a.last_tool_input)}`, plus search and prompt textareas
- `dir="ltr"` on callsigns and identifier-only spans

The dashboard's chrome (mode buttons, model badges, status pills, layout containers) stays LTR. Only the individual text-content nodes flip. Visual identity preserved.

---

## What this guide does NOT cover

- Right-to-left **layout** for Easy-tier purpose-built UI (Phase 2+). When that ships, the rules expand to include `margin-inline-*` everywhere, mirrored icons, RTL-aware modal positioning, etc. Until then, the current LTR-chrome / per-element-auto pattern is correct.
- Hebrew **typography** beyond font selection (advanced ligatures, niqqud handling, justified Hebrew text). Punt to a typography review when a real Hebrew design system lands.
- **Voice** input/output Hebrew handling — Gemini 3.1 Pro's native bilingual transcription is the source of truth; framework just relays text.

---

## See also

- `docs/RUNTIME-ADAPTERS.md` — adapter authoring guide (cross-references this doc)
- `templates/dispatch-preamble-he.md` — Hebrew dispatch preamble
- `addons/_core/auto-adapter/templates/addon-synthesis.md` — artifact manifest contract including `lang_hint`
- `packages/swarm-dashboard/templates/*.html` — reference BiDi implementation
