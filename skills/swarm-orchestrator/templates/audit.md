# Template — Section Audit Muscle

Use this for an audit muscle in a multi-section swarm. Each muscle owns one
non-overlapping scope. Fill in the bracketed fields.

## Dispatch prompt

```
[{{SAFETY}}] {{SECTION_TITLE}}

Audit ONLY these paths inside `{{ROOT}}`:
{{INCLUDE_LIST}}

Read-only. Do NOT modify. Do NOT touch anything outside your scope — other
agents own neighboring areas:
{{EXCLUDE_LIST}}

Exclude from counts: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`
{{ADDITIONAL_EXCLUDES}}

Deliverable (under {{WORD_LIMIT}} words, exact shape):

## {{REPORT_HEADING}}
{{DELIVERABLE_FIELDS}}

Rules:
- If a claim requires inference, lower confidence and explain in method
- If you couldn't check something, list it in not_checked
- No estimates when a count is easy to measure — measure it
- No fabricated percentages — derive from documented weights only

Use PowerShell (`[System.IO.Directory]::EnumerateFiles` for size), Glob, Grep.
Read files when needed for semantic understanding.

At the end of your report, emit a metadata block:

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
---END META---
```

## Fields to fill

- `{{SAFETY}}` — `L`, `M`, or `H`. See `docs/PROTOCOL.md` for decision.
- `{{SECTION_TITLE}}` — short title (e.g., "Section A - web app")
- `{{ROOT}}` — absolute path (e.g., `C:\Users\<you>\Desktop\YourProject` on Windows or `~/Desktop/YourProject` on macOS/Linux)
- `{{INCLUDE_LIST}}` — bulleted list of paths IN scope. Example:
  ```
  - web/
  - web/src/
  ```
- `{{EXCLUDE_LIST}}` — bulleted list of sibling scopes to avoid. Example:
  ```
  - DATAFOLDER/, extracted/, images/, text/ (Section B owns these)
  - diagnoses/, guides/ (Section C owns these)
  ```
- `{{ADDITIONAL_EXCLUDES}}` — extra one-line exclusions if needed
- `{{WORD_LIMIT}}` — 180 for simple, 220 for complex
- `{{REPORT_HEADING}}` — heading text (same as SECTION_TITLE typically)
- `{{DELIVERABLE_FIELDS}}` — bulleted list of what to produce. Example:
  ```
  - **Size:** X MB / N files
  - **Stack:** framework + deps summary
  - **Entry points:** routes or main files
  - **TODOs/FIXMEs:** N found, 3 examples
  - **Suspect/dead files:** orphans, unreferenced
  - **Stale:** >6 months untouched
  - **1 surprise finding**
  ```

## Parallel dispatch

For a 5-section swarm:

1. Decompose `{{ROOT}}` into 5 non-overlapping scopes
2. Fill template 5 times, each with:
   - Its unique `{{INCLUDE_LIST}}`
   - An `{{EXCLUDE_LIST}}` naming the OTHER 4 scopes explicitly
   - Same `{{SAFETY}}` tag for the whole swarm
3. Dispatch all 5 in one message — they run in parallel

## Safety tag decision

- `[L]` — audit output is informational; no action will be taken without human review
- `[M]` — audit output will drive cleanup / refactor / dedup recommendations
- `[H]` — audit output drives production-critical decisions (merge gates, purchases, customer-facing)

See `docs/PROTOCOL.md` for what each tag triggers.

## After dispatch

For `[M]` and `[H]`:

1. Parse each muscle's META block
2. Re-dispatch on Sonnet any with `confidence < 0.7`
3. Pick 3 claims total across reports, spot-check with own tool calls
4. For `[H]`: dispatch reviewer (see `templates/reviewer.md`)
5. Synthesize, flag unverified findings explicitly

## Common variations

- **Language-specific audit:** add `Focus on *.py files only` to the include list
- **Security audit:** change deliverable to include `Security concerns`, `Secrets leak check`, `Suspicious patterns`
- **Dead-code audit:** deliverable focuses on `Orphan files`, `Unreferenced functions`, `Unused imports`
