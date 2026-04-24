---
name: diagnosis-html
description: Generate a standalone single-file HTML diagnosis document matching the MachineGuides design-reference. Use after machine-diagnose when the user confirms they want an HTML artifact of the diagnosis. Writes a JSON payload and invokes build_generic_guide.py — do NOT hand-author HTML.
---

# Diagnosis HTML Render

Turn a completed Hebrew machine diagnosis into a **single-file standalone HTML document** by writing a JSON payload and running the component-based builder. You do NOT write HTML by hand — the builder renders all 10 sections, hero, footer, glossary, wiring diagram, and tooltip JS from a JSON input.

## When to use

Invoked after `machine-diagnose` returns an answer and the user confirms (כן) to the HTML-creation prompt. Do NOT run this proactively without user consent.

## Cache-first rule (NEW — check this BEFORE anything else)

Before invoking NotebookLM, writing JSON, or running the builder, always check the approved-diagnosis cache. If there is a hit, serve the cached HTML immediately and skip the whole pipeline.

```bash
python lookup_cache.py --machine <machine> --fault-code "<code>"
# or
python lookup_cache.py --machine <machine> --schematic-mark=<mark>    # note the = (leading dash)
# or
python lookup_cache.py --machine <machine> --keywords "<hebrew or english keywords>"
```

- Exit 0 + JSON printed → cache hit. Report to user:
  > 📦 מהמטמון · אושר `{approved_at}` · `{html}`

  Done. Do NOT regenerate.
- Exit 1 → no match. Proceed with the normal pipeline below.

Run the cache lookup even if the user says "new diagnosis for X" — they often don't realize the exact fault was approved before.

## The pipeline (when cache misses)

```
diagnosis facts (from machine-diagnose + NotebookLM)
        ↓  you write
   diagnoses/<machine>_<fault>.json
        ↓  builder runs
   python build_generic_guide.py --machine X --fault-slug Y --payload-file ...
        ↓  writes
   guides/<machine>_<fault>_v1_standalone.html
        ↓  you ask in Hebrew
   "שמור למטמון? הפעם הבאה ייפתח מיד (כן/לא)"
        ↓  on yes
   python approve_diagnosis.py --machine X --fault-slug Y
        ↓  promotes to
   cache/approved/<machine>_<fault>.{json,html} + _index.json entry
```

## Files you work with

All paths are relative to `C:\Users\ronsh\Desktop\MachineGuides\`.

| Path | Purpose |
|---|---|
| `DATAFOLDER/` | **Source PDFs.** 8 top-level folders (`W50RI`, `W200IF`, `W50DC`, `בובקט`, `בומג`, `וולוו`, `מקרצפת גדולה`, `מקרצפת קטנה`). Hebrew+English folders for the same machine fold into one canonical ID — see `reference_machineguides_datafolder` memory. |
| `images/_index.json` | **Master image+text catalog**, built by `extract_all.py` from all PDFs in DATAFOLDER. Query this FIRST during image pre-flight. |
| `extract_all.py` / `extract_all.cmd` | **Bulk PDF extractor.** Renders every page to PNG, extracts embedded images, writes per-page text. Resume-safe. `--pdf <path>` extracts one PDF on-demand. `--rebuild-index` only remerges existing per-PDF state. |
| `query_images.py` / `query.cmd` | **Keyword lookup over the index.** Returns ranked matches with machine · pdf · page · text preview · image path. Use `--full-text` for thorough search through per-page text. |
| `images/<machine>/<category>/*.png` | Hand-curated crops (sensors, cooling_fan, starter, etc.). **Prefer these over `_auto/` renders** when they match — they're cropped to the exact component. |
| `images/<machine>/_auto/<pdf_stem>/pages/p{NNN}.png` | Auto-extracted full page renders from `extract_all.py`. Use as figures when no curated crop exists. |
| `lookup_cache.py` | **Cache checker.** Run FIRST, before anything else. Exit 0 = hit (serve cached HTML); exit 1 = miss (proceed to build). |
| `approve_diagnosis.py` | **Thumbs-up promoter.** Run after the user says `כן` / `👍` to "save to cache". Copies JSON + HTML into `cache/approved/` and updates the index. |
| `build_generic_guide.py` | **The builder.** Component-based — one `build_sec_*` function per section. Reads the design-reference HTML as a shell, surgically replaces body/title/localStorage/glossary-JS/SELECTORS. Never edit this unless adding schema fields. |
| `validate_payload.py` | **Pydantic schema validator.** Run between merge and build — catches typos, wrong types, missing required fields before the builder silently renders an empty section. |
| `merge_payload.py` | **Skeleton + overlay merger.** Combines `diagnoses/_base/<machine>.json` (common content) with the per-fault overlay. |
| `verify_claims.py` | **Verification re-query.** Extracts claims from the merged payload, re-queries NotebookLM (MCP), writes a verdict log. Run before the builder — never ship unverified claims. |
| `notebooklm_mcp.py` | **MCP client** to the NotebookLM server at `weldref.duckdns.org/nlm-mcp/mcp`. Use instead of the `notebooklm` CLI for parallel/structured calls. |
| `cache/approved/_index.json` | **Registry** of approved diagnoses. Keys = `<machine>_<fault_slug>`. |
| `cache/approved/<key>.{json,html}` | Cached artifacts served on a hit. |
| `diagnoses/_base/<machine>.json` | **Per-machine skeleton.** Common tools, safety boilerplate, base glossary. The per-fault overlay extends this (lists concatenate, scalars override). |
| `diagnoses/W50Ri_HM8_FanSolenoid.json` | **Reference fixture.** Full, real HM8 payload covering every schema field. Read this first when producing a new diagnosis — crib the shape. |
| `design-reference/W50Ri_HM8_FanSolenoid_Diagnosis_v2_standalone.html` | The visual template the builder uses as a shell. Don't edit for a single diagnosis. |
| `design-reference/FEATURES.md` | Feature spec the rendered output honors (theme toggle, glossary, lightbox, etc.). Not required reading per diagnosis. |
| `guides/<machine>_<fault>_v<N>_standalone.html` | Builder output. This is what you hand to the user. |

## Image pre-flight — use the index FIRST, fall back per-PDF if needed

Before writing the overlay JSON's `figures` field:

1. **Query the index by machine + component keywords:**
   ```bash
   python query_images.py --machine W50Ri --kw "SPN 94 fuel low pressure" --full-text --limit 10
   ```
   The ranked hits give you: machine · pdf · page · text preview · image path. Pick the most relevant 2–4 to embed as figures (e.g., one parts-catalog page, one schematic page, one sensor-reference page).

2. **If no hits** → check whether the relevant PDF is even in DATAFOLDER:
   ```bash
   python extract_all.py --dry-run --only W50Ri
   ```
   If the PDF is listed but not indexed (no `entries.json`), extract just it:
   ```bash
   python extract_all.py --pdf "DATAFOLDER\W50RI\<filename>.pdf"
   ```
   If the PDF isn't in DATAFOLDER at all, tell the user before building (per the `feedback_diagnosis_html_image_preflight` memory rule).

3. **Prefer hand-curated crops** at `images/<machine>/{sensors,cooling_fan,starter,...}/` whenever one matches the component — they're tighter than a full-page render.

4. **Report your figure plan to the user** before running the builder. Never silently ship figure-less docs.

## Workflow per diagnosis

0. **Check the cache first.** Run `lookup_cache.py` with whatever identifiers you have (machine + fault_code is ideal; machine + keywords works for fuzzy requests). If it exits 0, serve the cached HTML and stop — do NOT run steps 1–4.
1. **Read** `diagnoses/W50Ri_HM8_FanSolenoid.json` to see the shape. **Read** the docstring at the top of `build_generic_guide.py` for the canonical schema.
2. **Write** `diagnoses/<machine>_<fault>.json` with the diagnosis content. All fields optional except `machine` and `fault_code` — missing fields degrade gracefully to a Hebrew placeholder.
3. **Run** the builder:
   ```bash
   python build_generic_guide.py \
     --machine <machine> \
     --fault-slug <fault_slug> \
     --payload-file diagnoses/<machine>_<fault>.json
   ```
4. **Report** the output path (`guides/<machine>_<fault_slug>_v1_standalone.html`) back to the user.
5. **Ask to save** (thumbs-up prompt, Hebrew):
   > שמור למטמון? הפעם הבאה ייפתח מיד (כן/לא)
   
   On `כן` / `👍` / `save` / `thumbs up`:
   ```bash
   python approve_diagnosis.py \
     --machine <machine> \
     --fault-slug <fault_slug> \
     [--notes "short Hebrew note about why this was approved"]
   ```
   On `לא` / silence: skip — do not cache.

## Thumbs-down / invalidation

If the user says `👎` / `רענן` / `regenerate` / `cache is wrong`:

```bash
# Delete the stale entry + files
python -c "
import json, pathlib
idx = pathlib.Path('cache/approved/_index.json')
d = json.loads(idx.read_text(encoding='utf-8'))
key = '<machine>_<fault_slug>'
entry = d['entries'].pop(key, None)
if entry:
    for k in ('json','html'):
        p = pathlib.Path(entry[k])
        if p.exists(): p.unlink()
    idx.write_text(json.dumps(d, ensure_ascii=False, indent=2)+chr(10), encoding='utf-8')
    print('removed', key)
else:
    print('not cached:', key)
"
```

Then run the normal pipeline (steps 1–5) to produce a fresh doc.

## JSON schema (summary — full docstring in build_generic_guide.py)

```jsonc
{
  // — Identity (machine + fault_code required) —
  "machine":          "W50Ri",
  "engine":           "Deutz TCD 4.1",
  "ecu":              "Controller 1",
  "fault_code":       "SPN 975",
  "flash_code":       "228",
  "schematic_mark":   "-HM8",
  "supply_voltage":   "24V PWM",

  // — Hero strings —
  "fault_title_he":   "אבחון תקלת …",
  "component_he":     "סליל מגנטי — שסתום פרופורציונלי",
  "component_en":     "Fan drive solenoid coil",
  "subtitle_he":      "…",
  "badges":           [{"text": "COOLING SYSTEM", "variant": "gold"}],

  // — Section 01 content —
  "hebrew_answer":    "<intro paragraph rendered as תקציר האבחון>",
  "causes":           ["<li-1 rich HTML allowed>", "..."],
  "part_numbers":     [{"label": "…", "pn": "2094753", "note": "…"}],

  // — Section 02 —
  "location_he":      "<paragraph>",
  "location_bullets": ["<li>", "..."],

  // — Section 03 wiring —
  "wiring_pins": [
    {"box": "controller", "title": "…", "rows": [{"id": "…", "sig": "…"}],
     "fuse_note": "F20 · 10A"},
    {"box": "connector",  "title": "…", "wire_label": "PWM signal",
     "rows": [{"id": "פין 1", "sig": "…"}, {"id": "פין 2", "sig": "GND", "kind": "gnd"}]},
    {"box": "coil",       "title": "…", "wire_label": "-X60s → -X10p",
     "rows": [{"id": "מק״ט", "sig": "2094753", "kind": "pn"}]}
  ],

  // — Section 04 fault codes —
  "fmis": [
    {"code": "5", "meaning": "…", "direction": "חשמלי", "action": "…"}
  ],

  // — Section 05 diagnostic steps —
  "steps": [
    {"title": "…", "note": "<p HTML ok>", "bullets": ["<hint>", "..."]}
  ],

  // — Section 06 decision flow (tree) —
  "flow": [
    {"type": "q",   "text": "…?"},
    {"type": "arrow"},
    {"type": "branches", "branches": [
      [{"type": "bad", "text": "…"}, {"type": "arrow"}, {"type": "ok", "text": "…"}]
    ]}
  ],

  // — Section 07 emergency override —
  "override": {
    "danger":        "<plain danger callout>",
    "warn_title":    "…",
    "warn_bullets":  ["…", "..."]
  },

  // — Section 08 safety —
  "safety": {
    "info_title":    "…",
    "info_bullets":  ["…", "..."],
    "warn_title":    "…",
    "warn_bullets":  ["…", "..."]
  },

  // — Section 09 toolbox —
  "tools": [{"tool": "מולטימטר", "use": "VDC / Ω / Hz-Duty"}],

  // — Section 10 + inline tooltips —
  "glossary": [
    {"key": "spn", "term": "SPN", "heb": "Suspect Parameter Number",
     "short": "…", "context": "…בהקשר של האבחון הזה",
     "pattern": "\\bSPN\\b",
     "more": ["optional long-form paragraph", "..."]}
  ],

  // — Figures (base64-embedded into the HTML, lightbox-enabled) —
  "figures": [
    {"section": "01", "src": "images/W50Ri/cooling_fan/parts_p0246.png",
     "caption": "<strong>Spare Parts Catalogue · עמ׳ 246</strong> — …"},
    {"section": "02", "src": "images/W50Ri/cooling_fan/hose_p0027.png",
     "caption": "<strong>Hose Diagram · עמ׳ 27</strong> — …"},
    {"section": "02", "layout": "side-by-side", "src": "…",    "caption": "…"},
    {"section": "02", "layout": "side-by-side", "src": "…",    "caption": "…"},
    {"section": "04", "src": "images/…/fault_p0053.png",       "caption": "…"}
  ],

  // — Footer —
  "source_note": "מקור: NotebookLM · …"
}
```

### Schema notes

- **Escaped vs Trusted fields — read this before authoring (prevents the #1 UI bug).**
  Markup like `<strong>`, `<code>`, `<span class="pn">` only renders in **trusted** fields. Putting markup in an **escaped** field renders the raw tag text on the page (e.g. `<strong>foo</strong>` literally appears with the angle brackets). Rule of thumb: identifier/label/title = escaped; sentence/paragraph/caption/bullet = trusted.

  | Tier | Fields | Markup? |
  |---|---|---|
  | **ESCAPED** (plain text only) | `machine`, `fault_code`, `fault_title_he`, `subtitle_he`, `engine`, `ecu`, `schematic_mark`, `supply_voltage`, `flash_code`, `source_note`, `component_he`, `component_en`, `badges[*].text`, `fmis[*].{code,meaning,direction}`, `part_numbers[*].{label,pn}`, `tools[*].tool`, `wiring_pins[*].{title,fuse_note,wire_label}`, `wiring_pins[*].rows[*].{id,sig}`, `flow[*].text`, `glossary[*].{term,heb}`, `figures[*].src`, `steps[*].title` | ❌ NO |
  | **TRUSTED** (rich HTML pass-through) | `hebrew_answer`, `location_he`, `location_bullets[*]`, `causes[*]`, `part_numbers[*].note`, `fmis[*].action`, `steps[*].{note,bullets[*]}`, `tools[*].use`, `override.{danger,warn_title,warn_bullets[*]}`, `safety.{info_title,info_bullets[*],warn_title,warn_bullets[*]}`, `glossary[*].{short,context,more[*]}`, `figures[*].caption` | ✅ YES |

  Canonical source of truth lives in the docstring at the top of `build_generic_guide.py` — if you add a field, update both places.
- **Part-number chips** — wrap part numbers that appear inside `note`/`bullets`/`use` in `<span class="pn">2094753</span>` for the gold-chip treatment. In `part_numbers` itself just pass `pn: "2094753"` — the builder wraps it.
- **Wiring `rows[].kind`** — optional: `"gnd"` dims the sig color for ground rows; `"pn"` renders the sig as a gold P/N chip.
- **Flow node types**: `"q"` (question box), `"box"` (neutral), `"ok"` (green), `"bad"` (red), `"arrow"` (connector). Use `"branches"` with a list of parallel column-arrays for forks.
- **Glossary `pattern`** — JavaScript regex string (you're writing JSON so escape backslashes: `"\\bSPN\\b"`). Omit to let the builder default to `\bTERM\b`.
- **Glossary coverage is broad, not minimal** — every acronym, protocol, component name, and technical term the reader meets must be glossary-wrapped (tooltip + bottom `<details>` card). Target 10+ terms. Use the HM8 fixture as the minimum bar.
- **Missing sections** — omit the field entirely; the builder renders the section header with "אין מידע זמין למסמך זה" rather than fabricating content.
- **`figures[]`** — each entry needs `section` (matches a sec_num like `"01"`/`"02"`/`"04"`), `src` (repo-relative path like `images/W50Ri/cooling_fan/parts_p0246.png`), and `caption` (rich HTML). Images are base64-inlined into the HTML at build time — the output is self-contained. Missing files render a visible "תמונה חסרה" placeholder rather than failing the build. Use `"layout": "side-by-side"` on **adjacent** entries in the same section to pair them in a 2-column grid. Figures trigger the lightbox (zoom, pan, rotate, keyboard nav) — high-resolution source images (≥1500px wide) make the zoom useful; tiny thumbnails look bad at 6×.

## Content sourcing rules

- Pull facts **only from the machine-diagnose answer + the NotebookLM source notebook**. Do not invent part numbers, pin-outs, or torque specs.
- Unverified part numbers — use the label "אמת בקטלוג" and point to the right catalog. Do NOT fabricate.
- Callouts (`.callout.tip` / `.callout.warn`) via `safety`/`override` should carry real hints and safety notes, not filler.

## What NOT to do

- **Do not write the HTML by hand.** That was the old flow and it's dead. Write JSON; run the builder.
- **Do not edit `build_generic_guide.py`** unless genuinely extending the schema. If you need a new field, extend the builder + update this SKILL + add to the fixture.
- **Do not edit the design-reference template** for a single diagnosis — the builder uses it as a shell for every build.
- **Do not simplify the glossary** — broad coverage is a hard requirement.
- **Do not use English UI labels** — all section titles/button tooltips are Hebrew.

## Output naming

```
guides/<machine>_<fault_slug>_v<N>_standalone.html
```

- `<machine>`: short ID (`W50Ri`, `W200i`, `Bobcat_S650`)
- `<fault_slug>`: short fault slug (`HM8_FanSolenoid`, `SPN94_FuelLowPressure`)
- `<N>`: version (start `v1`; bump if regenerating)

Builder defaults to `v1`; pass `--out-file` for anything else.

## Quick verification after build

```bash
python -c "
import re
p = open('guides/<file>.html','r',encoding='utf-8').read()
print('sections :', len(re.findall(r'class=\"sec-num\">\d+</span>', p)))
print('glossary :', len(re.findall(r'<details class=\"gl-item\"', p)))
print('ls scope :', '<scope>.theme' in p)
"
```

Sections should be 10. Glossary count ≈ number of terms + 1 (template).
