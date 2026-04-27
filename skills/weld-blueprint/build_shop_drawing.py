"""
build_shop_drawing.py — Phase 1 MVP welding blueprint generator.

Renders a JSON payload into a single-file HTML shop drawing matching
templates/shop_drawing_master.html. Mirrors the patterns from
MachineGuides/build_generic_guide.py:
  - Hebrew punctuation normalization (gershayim, geresh, en-dash, ellipsis)
  - <bdi> auto-wrap for fault-code-family / dimension / part-number tokens
    so Latin/numeric content renders LTR inside RTL Hebrew prose
  - Escaped vs trusted HTML field discipline

Usage:
    python build_shop_drawing.py --payload examples/fillet_corner_bracket.json
    python build_shop_drawing.py --payload my_job.json --out custom/path.html

Required payload fields: job_id, title_he, parts[], welds[].
All others optional and degrade gracefully.
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).parent
TEMPLATE = SKILL_ROOT / "templates" / "shop_drawing_master.html"
DEFAULT_OUT_DIR = Path.home() / "Desktop" / "WeldingRef" / "blueprints"

# -----------------------------------------------------------------------------
# Hebrew punctuation + bidi helpers (verbatim from build_generic_guide.py)
# -----------------------------------------------------------------------------

_RE_GERSHAYIM = re.compile(r'(?<=[֐-׿])"(?=[֐-׿])')
_RE_GERESH    = re.compile(r'(?<=[֐-׿])\'')
_EN_DASH      = '–'
_ELLIPSIS     = '…'


def normalize_hebrew_punct(text: str) -> str:
    if not text:
        return text
    text = _RE_GERSHAYIM.sub('״', text)
    text = _RE_GERESH.sub('׳', text)
    text = text.replace('--', _EN_DASH)
    text = text.replace('...', _ELLIPSIS)
    return text


# Tokens that must render LTR in RTL prose: AWS codes, dimensions, part nums,
# weld IDs (W1, W2), revisions (Rev B), bolt specs (M10×30), etc.
_BIDI_TOKEN_RE = re.compile(
    r"""(
        \bSPN\s?\d{2,5}(?:\s+FMI\s?\d{1,3})?       # SPN 94 / SPN 975 FMI 5
      | \bFMI\s?\d{1,3}                            # FMI 5
      | \bAWS\s+[A-Z]\d+\.\d+                      # AWS A2.4 / AWS D1.1
      | \b(?:GMAW|SMAW|GTAW|FCAW|SAW|PAW|OFW)\b    # process codes
      | \b[Mm]\d{1,3}(?:\s*[×x]\s*\d{1,4})?        # M10×30 / M16
      | \bER\d{2,3}[A-Z]-\d{1,2}\b                 # ER70S-6
      | \bRHS\s*\d+(?:[×x]\d+){1,2}                # RHS 50×50×4
      | \bPL\s*\d+(?:[×x]\d+){1,2}                 # PL 200×150×8
      | (?<![A-Za-z])-?[A-Z]{1,3}\d{1,4}\b         # -HA3, X444, F19
      | \b[Ww]\d{1,3}\b                            # W1, W2, W23 (weld IDs)
      | \b\d+\s*[/:]\s*\d+\b                       # 1:5 (scale), 1/2
      | \b\d+(?:\.\d+)?\s*(?:mm|cm|m|kg|N|MPa|°)   # dimensions w/ units
    )""",
    re.VERBOSE,
)

_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
_BDI_OPEN_RE  = re.compile(r"<bdi\b[^>]*>", re.I)
_BDI_CLOSE_RE = re.compile(r"</bdi\s*>", re.I)


def _wrap_bidi(text: str) -> str:
    return _BIDI_TOKEN_RE.sub(lambda m: f"<bdi>{m.group(0)}</bdi>", text)


def _wrap_bidi_html(html: str) -> str:
    """Wrap LTR tokens with <bdi>, but skip text already inside an existing
    <bdi>...</bdi> in the input — prevents nested <bdi><bdi>X</bdi></bdi>."""
    parts = _TAG_SPLIT_RE.split(html)
    bdi_depth = 0
    for i, part in enumerate(parts):
        if i % 2 == 1:  # tag
            if _BDI_OPEN_RE.fullmatch(part):
                bdi_depth += 1
            elif _BDI_CLOSE_RE.fullmatch(part):
                bdi_depth = max(0, bdi_depth - 1)
        else:  # text
            if bdi_depth == 0:
                parts[i] = _wrap_bidi(part)
    return "".join(parts)


def esc(s) -> str:
    """HTML-escape plain text. Safe for body and attribute values."""
    if s is None or s == "":
        return ""
    return html_mod.escape(normalize_hebrew_punct(str(s)), quote=True)


def esc_bidi(s) -> str:
    """Escape + auto-wrap LTR tokens with <bdi>. Body content only."""
    if s is None or s == "":
        return ""
    return _wrap_bidi(html_mod.escape(normalize_hebrew_punct(str(s)), quote=True))


def rich(s) -> str:
    """Trusted HTML pass-through + auto-wrap LTR tokens. Body content only."""
    if s is None or s == "":
        return ""
    return _wrap_bidi_html(normalize_hebrew_punct(str(s)))


# -----------------------------------------------------------------------------
# Section builders
# -----------------------------------------------------------------------------

def fmt_date(date_iso: str) -> str:
    """YYYY-MM-DD → DD/MM/YYYY (Israeli norm). Pass through anything else."""
    if not date_iso:
        return ""
    try:
        d = datetime.strptime(date_iso, "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return date_iso


def build_view(views: list, payload: dict) -> tuple[str, str, str]:
    """Phase 1: render the FIRST view only as embedded image or placeholder.
    Returns (label, body_html, scale_note).
    """
    if not views:
        return (
            esc("מבט"),
            '<span class="empty">אין מבט מצורף בתשלובת הנתונים</span>',
            "",
        )
    v = views[0]
    label_he = v.get("label_he", "")
    label_en = v.get("label_en", "")
    label = esc(label_he) if label_he else esc(label_en) or esc("מבט")
    if label_he and label_en:
        label = f'{esc(label_he)} <span style="color:var(--ink-faint);font-weight:400">· {esc(label_en)}</span>'

    src = (v.get("src") or "").strip()
    if not src:
        body = '<span class="empty">אין תמונה מצורפת</span>'
    elif src.startswith("data:") or src.startswith("http"):
        body = f'<img src="{esc(src)}" alt="{label_he or "view"}">'
    else:
        # treat as filesystem path; convert to data URL inline
        body = _embed_local_image(src)

    scale = v.get("scale_note") or payload.get("scale", "")
    return label, body, esc(scale)


def _embed_local_image(path_str: str) -> str:
    """Best-effort base64 inline of a local image file."""
    import base64
    import mimetypes

    p = Path(path_str)
    if not p.is_absolute():
        p = (SKILL_ROOT / path_str).resolve()
    if not p.exists():
        return f'<span class="empty">קובץ תמונה חסר: <code>{esc(path_str)}</code></span>'
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f'<img src="data:{mime};base64,{b64}" alt="">'


def build_bom_rows(parts: list) -> str:
    if not parts:
        return (
            '<tr><td colspan="5" style="text-align:center;color:var(--ink-faint);'
            'padding:3mm;font-style:italic">אין פריטים בתשלובת</td></tr>'
        )
    rows = []
    for p in parts:
        item = p.get("item", "")
        qty = p.get("qty", "")
        desc = p.get("desc_he", "")
        spec = p.get("spec", "")
        length = p.get("len_mm")
        length_disp = f'<bdi>{esc(length)}</bdi>' if length not in (None, "") else "—"
        rows.append(
            "<tr>"
            f'<td class="num"><bdi>{esc(item)}</bdi></td>'
            f'<td>{esc(desc)}</td>'
            f'<td>{esc_bidi(spec)}</td>'
            f'<td>{length_disp}</td>'
            f'<td class="num"><bdi>{esc(qty)}</bdi></td>'
            "</tr>"
        )
    return "\n".join(rows)


_WELD_TYPE_HE = {
    "fillet":         "פינתי",
    "groove_v":       "חריץ V",
    "groove_u":       "חריץ U",
    "groove_j":       "חריץ J",
    "groove_bevel":   "חריץ בבל",
    "plug":           "תקע",
    "slot":           "חריץ ממוקם",
    "spot":           "נקודה",
    "seam":           "תפר",
    "surfacing":      "ציפוי",
}

_SIDE_HE = {"arrow": "חץ", "other": "נגדי", "both": "שני הצדדים"}


def build_weld_rows(welds: list) -> str:
    if not welds:
        return (
            '<tr><td colspan="8" style="text-align:center;color:var(--ink-faint);'
            'padding:3mm;font-style:italic">אין ריתוכים מוגדרים</td></tr>'
        )
    rows = []
    for w in welds:
        wid = w.get("id", "")
        wtype = w.get("type", "")
        type_he = _WELD_TYPE_HE.get(wtype, wtype)
        side_he = _SIDE_HE.get(w.get("side", "arrow"), w.get("side", ""))
        size = w.get("size_mm")
        length = w.get("length_mm")
        pitch = w.get("pitch_mm")
        process = w.get("process_tail", "")
        ref_items = w.get("ref_part_items", []) or []
        note = w.get("note_he", "")
        all_around = w.get("all_around", False)
        field_weld = w.get("field_weld", False)

        size_disp = f'<bdi>{esc(size)}</bdi>' if size not in (None, "") else "—"
        if length and pitch:
            length_disp = f'<bdi>{esc(length)}-{esc(pitch)}</bdi>'
        elif length:
            length_disp = f'<bdi>{esc(length)}</bdi>'
        else:
            length_disp = esc("רציף")  # continuous

        flags = []
        if all_around:
            flags.append('<span title="כל היקף">⌖</span>')
        if field_weld:
            flags.append('<span class="field-flag" title="ריתוך שדה">▶</span>')
        flag_str = " ".join(flags)

        items_disp = (
            ", ".join(f'<bdi>{esc(i)}</bdi>' for i in ref_items)
            if ref_items else "—"
        )

        rows.append(
            "<tr>"
            f'<td class="num"><bdi>{esc(wid)}</bdi> {flag_str}</td>'
            f'<td>{esc(type_he)}</td>'
            f'<td>{esc(side_he)}</td>'
            f'<td>{size_disp}</td>'
            f'<td>{length_disp}</td>'
            f'<td><bdi>{esc(process)}</bdi></td>'
            f'<td>{items_disp}</td>'
            f'<td>{rich(note)}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def build_notes(notes: list) -> str:
    if not notes:
        return '<div class="empty">אין הערות</div>'
    items = "\n".join(f"<li>{rich(n)}</li>" for n in notes)
    return f"<ol>\n{items}\n</ol>"


def build_revisions(revisions: list) -> str:
    if not revisions:
        return '<div class="empty">אין היסטוריית גרסאות</div>'
    head = (
        "<table>\n"
        "<thead><tr>"
        '<th class="rev-id">גרסה</th>'
        "<th>תאריך</th>"
        "<th>שינוי</th>"
        "</tr></thead>\n<tbody>"
    )
    rows = []
    for r in revisions:
        rev_id = r.get("rev", "")
        date = fmt_date(r.get("date", ""))
        note = r.get("note_he", "")
        rows.append(
            "<tr>"
            f'<td class="rev-id"><bdi>{esc(rev_id)}</bdi></td>'
            f'<td><bdi>{esc(date)}</bdi></td>'
            f'<td>{rich(note)}</td>'
            "</tr>"
        )
    return head + "\n".join(rows) + "\n</tbody></table>"


# -----------------------------------------------------------------------------
# Postprocess (light — collapse blank lines only)
# -----------------------------------------------------------------------------

_BLANK_LINE_RE = re.compile(r'(?:\r?\n[ \t]*){3,}')


def postprocess(html: str) -> str:
    return _BLANK_LINE_RE.sub("\n\n", html)


# -----------------------------------------------------------------------------
# Main render
# -----------------------------------------------------------------------------

def render(payload: dict) -> str:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE}")
    template = TEMPLATE.read_text(encoding="utf-8")

    parts = payload.get("parts", []) or []
    welds = payload.get("welds", []) or []
    views = payload.get("views", []) or []
    sheet = payload.get("sheet") or {}
    field_welds_count = sum(1 for w in welds if w.get("field_weld"))

    view_label, view_body, view_scale = build_view(views, payload)

    title_he = payload.get("title_he", "")
    job_id = payload.get("job_id", "")
    title_text_plain = f"{job_id} — {title_he}" if title_he else job_id

    replacements = {
        "{{TITLE_TEXT}}":       esc(title_text_plain),
        "{{JOB_ID}}":           esc(job_id),
        "{{TITLE_HE}}":         esc(title_he),
        "{{TITLE_EN}}":         esc(payload.get("title_en", "")),
        "{{DRAWN_BY}}":         esc(payload.get("drawn_by", "—")),
        "{{DATE_DISPLAY}}":     esc(fmt_date(payload.get("date_iso", ""))),
        "{{SCALE}}":            esc(payload.get("scale", "—")),
        "{{SHEET_N}}":          esc(sheet.get("n", 1)),
        "{{SHEET_OF}}":         esc(sheet.get("of", 1)),
        "{{REVISION}}":         esc(payload.get("revision", "—")),
        "{{MATERIAL_SPEC}}":    esc_bidi(payload.get("material_spec", "—")),
        "{{PROCESS}}":          esc_bidi(payload.get("process", "—")),
        "{{STANDARD}}":         esc_bidi(payload.get("standard", "—")),
        "{{PARTS_COUNT}}":      esc(len(parts)),
        "{{WELDS_COUNT}}":      esc(len(welds)),
        "{{FIELD_WELDS_COUNT}}": esc(field_welds_count),
        "{{VIEW_LABEL}}":       view_label,
        "{{VIEW_BODY}}":        view_body,
        "{{VIEW_SCALE}}":       view_scale,
        "{{NOTES_BODY}}":       build_notes(payload.get("notes_he", []) or []),
        "{{BOM_ROWS}}":         build_bom_rows(parts),
        "{{WELD_ROWS}}":        build_weld_rows(welds),
        "{{REVISIONS_BODY}}":   build_revisions(payload.get("revisions", []) or []),
    }

    html = template
    for key, val in replacements.items():
        html = html.replace(key, val)

    # Sanity check — no unfilled placeholders remain
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", html)
    if leftover:
        print(f"WARN: unfilled placeholders: {leftover}", file=sys.stderr)

    return postprocess(html)


def slugify(s: str) -> str:
    """Filesystem-safe slug. Drops Hebrew, keeps Latin/digits."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", str(s)).strip("_")
    return s or "untitled"


def default_out_path(payload: dict) -> Path:
    job_id = slugify(payload.get("job_id", "drawing"))
    rev = slugify(payload.get("revision", "A"))
    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_OUT_DIR / f"{job_id}_rev{rev}.html"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--payload", required=True, help="Path to JSON payload")
    ap.add_argument("--out", help="Output HTML path (default: ~/Desktop/WeldingRef/blueprints/)")
    args = ap.parse_args()

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"ERROR: payload not found: {payload_path}", file=sys.stderr)
        sys.exit(2)

    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    # Hard requireds
    for required in ("job_id", "title_he"):
        if not payload.get(required):
            print(f"ERROR: payload missing required field: {required}", file=sys.stderr)
            sys.exit(2)

    out_path = Path(args.out) if args.out else default_out_path(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = render(payload)
    out_path.write_text(html, encoding="utf-8")

    print(f"OK: {out_path}")
    print(f"   bytes: {out_path.stat().st_size:,}")


if __name__ == "__main__":
    main()
