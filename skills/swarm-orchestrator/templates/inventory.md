# Template — Folder Inventory Muscle

Use this template to dispatch a Haiku inventory agent. Fill in the bracketed fields.

## Dispatch prompt

```
[L] Inventory {{FOLDER_NAME}}

Audit ONLY `{{FULL_PATH}}`. Read-only. Do NOT modify.

Exclude: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `env`
{{ADDITIONAL_EXCLUDES}}

Treat Hebrew filenames as normal (do not transliterate). Use `-LiteralPath` in
PowerShell so paths with non-ASCII work.

Deliverable (under 180 words, exact shape):

## {{SECTION_TITLE}}
- **Size:** X MB / N files (excluding listed)
- **Activity:** newest YYYY-MM-DD, oldest YYYY-MM-DD (by LastWriteTime)
- **Top 5 files by size:** bullet list with relative path + size
- **Type breakdown:** top 5 file extensions by count
- **What it is:** 2-sentence description based on README or top-level files
- **TODOs:** N found across `*.md`, `*.py`, `*.js/ts`. Examples (up to 3): file:line — snippet
- **Stale:** items LastWrite older than 6 months
- **1 surprise finding** — anything unexpected or broken-looking

Use PowerShell `[System.IO.Directory]::EnumerateFiles` for fast recursive size
sums. Use Glob + Grep for TODO extraction. Be precise on numbers — no estimates.

At the end of your report, emit a metadata block:

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
---END META---
```

## Fields to fill

- `{{FOLDER_NAME}}` — short friendly name (e.g., "YourProject")
- `{{FULL_PATH}}` — absolute path (e.g., `C:\Users\<you>\Desktop\YourProject` on Windows or `~/Desktop/YourProject` on macOS/Linux)
- `{{ADDITIONAL_EXCLUDES}}` — optional extra folder names to skip (one per line, e.g., `\n- .next\n- _archive`)
- `{{SECTION_TITLE}}` — report section heading (usually same as folder name)

## When to use

Safety `[L]` low-stakes inventory — descriptive output, not driving decisions. Uses Haiku, no escalation or spot-check needed.

## Parallelization

To inventory multiple folders at once, fill this template N times with different `{{FULL_PATH}}` values and dispatch all N in parallel. Make sure the scopes don't overlap — each agent owns its folder, no reads into siblings.

## Common variations

- **Big folder with known structure:** use `audit.md` template instead, it's more structured
- **Sensitive content:** add `"Do NOT read the contents of any file, only metadata"` if you just want sizes
- **Recently-added focus:** change `Activity` line to ask for "files added in last 30 days only"

## Example filled-in prompt

```
[L] Inventory <YourProject>

Audit ONLY `<absolute path to your folder>`. Read-only. Do NOT modify.

Exclude: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `env`

Treat Hebrew filenames as normal...

Deliverable (under 180 words, exact shape):

## ComfyUI
- **Size:** X MB / N files (excluding listed)
- **Activity:** ...
[etc.]

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
---END META---
```
