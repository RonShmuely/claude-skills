---
name: weld-blueprint
description: Generate single-file HTML shop drawings (welding blueprints) for fabrication. Payload-driven, never hand-authored. Output prints clean to A3 landscape PDF — title block, BOM, weld table, notes, views. Hebrew RTL with <bdi> for AWS codes / part numbers / dimensions. Trigger on "shop drawing", "weld drawing", "blueprint for [part]", "תכנית ריתוך", "שרטוט סדנא", or any request to produce a drawing the welder works from. Do NOT trigger for client proposals, marketing pages, or process explainers — those are different document classes.
---

# weld-blueprint — Shop Drawing Generator

## What this skill does

Renders a JSON payload into a single-file HTML shop drawing that prints clean to A3 landscape PDF. The welder reads the printed output under a hood with dirty gloves and builds the part correctly. Aesthetics serve legibility, not the other way around.

**Non-negotiables (inherited from project rules):**
- Never hand-author HTML — payload + generator only
- Hebrew labels everywhere; Latin only for AWS codes, part numbers, units, dimensions
- `<bdi>`-wrap Latin/numeric tokens inside RTL prose so digits don't reshuffle
- No fabricated data — every visible value traces to the payload
- Output goes to `~/Desktop/WeldingRef/blueprints/{job_id}_rev{N}.html`

## How to use

```bash
python build_shop_drawing.py --payload examples/fillet_corner_bracket.json
# or
python build_shop_drawing.py --payload path/to/job.json --out custom/path.html
```

## Payload schema

See `examples/fillet_corner_bracket.json` for a complete worked example. Required fields: `job_id`, `title_he`, `parts[]`, `welds[]`. All others optional and degrade gracefully.

| Field             | Type    | Notes |
|-------------------|---------|-------|
| `job_id`          | string  | Drawing number, e.g. `JOB-2026-0142`. `<bdi>`-wrapped on render. |
| `title_he`        | string  | Hebrew title shown in title block. |
| `title_en`        | string? | Optional Latin caption under Hebrew title. |
| `drawn_by`        | string? | Drafter name (Hebrew). |
| `date_iso`        | string? | `YYYY-MM-DD`. Rendered as DD/MM/YYYY. |
| `scale`           | string? | e.g. `1:5`. `<bdi>`-wrapped. |
| `sheet`           | object? | `{ n: 1, of: 2 }`. Multi-sheet support arrives in Phase 3. |
| `revision`        | string? | e.g. `B`. |
| `material_spec`   | string? | e.g. `S235JR — 6mm`. |
| `process`         | string? | e.g. `GMAW — ER70S-6 / 80%Ar 20%CO₂`. |
| `standard`        | string? | e.g. `AWS D1.1`. |
| `parts[]`         | array   | BOM rows: `{ item, qty, desc_he, spec, len_mm }`. |
| `welds[]`         | array   | Weld table rows. See payload schema in `build_shop_drawing.py` docstring. |
| `views[]`         | array   | Each: `{ label_he, label_en, src, scale_note }`. `src` is base64 data URL or path. |
| `dimensions[]`    | array?  | Phase 3 (procedural overlays); for now just a reference table. |
| `notes_he[]`      | array?  | Trusted HTML strings. Supports `<strong>`, `<code>`, lists. |
| `hardware[]`      | array?  | Bolts/washers BOM (item, qty, desc_he, spec). |
| `revisions[]`     | array?  | Revision history rows. |

## Escape policy

Mirrors `build_generic_guide.py`:
- **Escaped (plain text):** `job_id`, `parts[].spec`, `welds[].id`, dimension values, AWS codes.
- **Trusted HTML:** `notes_he`, `welds[].note_he`, `revisions[].note_he`.
- **`<bdi>`-wrapped via `esc_bidi()`:** anything Latin/numeric appearing inside RTL prose.

## Phased delivery

- **Phase 1 (current MVP):** title block + BOM + weld table + notes + single embedded image view + A3 print CSS
- **Phase 2:** procedural AWS A2.4 weld symbols overlaid on views
- **Phase 3:** multi-sheet pagination + procedural dimension lines with tolerances
- **Phase 4 (optional):** `/draw` endpoint on `weldref_bridge.py`

## Out of scope

DXF/DWG export · 3D rendering · WPS docs · forking visual-explainer-extension.

## Anti-slop checklist (verify before delivering)

- [ ] No emoji headers
- [ ] No AI gradients, no indigo, no premium-typography flourishes
- [ ] Every dimension/tolerance/percentage traces to payload
- [ ] Hebrew uses gershayim (״) and geresh (׳), not straight quotes
- [ ] Latin tokens wrapped in `<bdi>` (visually verify in print preview — digits in correct order)
- [ ] Prints clean to B&W laser (no dark backgrounds bleeding)
