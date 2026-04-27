# Muscle prompt — repo inventory

[L] Inventory the repo at `{{target_repo}}`.

You are READ-ONLY. Do not create, modify, or delete any file.

## What to gather

1. **Top-level structure.** `Glob` the top two levels. List directories, key files at the root (README, AGENTS.md, CLAUDE.md, package.json, pyproject.toml, requirements.txt, .gitignore, etc.).
2. **Primary file types and counts.** What is this repo built from? (e.g., `*.py: 47`, `*.tsx: 23`, `*.md: 18`, `*.json: 12`).
3. **Existing AI-rules files.** If `AGENTS.md`, `CLAUDE.md`, or `.cursor/rules/*.mdc` exist, read them. Quote any rules that look load-bearing.
4. **Build / run / test commands.** From `package.json` scripts, `Makefile`, `pyproject.toml`, or `README.md`. List 3–8 most-used commands with one-line descriptions.
5. **Naming conventions.** File-naming patterns (kebab-case, snake_case, dated prefixes), folder organization (`src/`, `lib/`, `guides/`, `diagnoses/`, etc.), version-suffix patterns (`*_v1.html`, `*_approved.json`).
6. **Archive / cleanup policy.** Does the repo have an `_archive/` convention? A `_postmortem/` folder? A "never delete, only archive" policy implied by the structure or docs?
7. **External integrations.** MCP servers (`.mcp.json` or `.antigravity/mcp.json`), config for Supabase / Vercel / NotebookLM / Wix / etc.
8. **Languages / locales.** Hebrew, English, German, etc. — both in code (`he-IL`, `lang="he"`) and in human-readable docs.

## Deliverable (under 600 words, exact shape)

## Repo at a glance
- **Name:** ...
- **Domain:** one-line guess at what this repo does
- **Primary languages:** ...
- **AI-rules present:** AGENTS.md / CLAUDE.md / .cursor/rules — list which exist

## Top-level structure
```
<paste glob output, top 2 levels>
```

## File-type distribution
- *.py: N
- *.tsx: N
- ...

## Existing AI-rules
- **AGENTS.md:** quote up to 3 load-bearing rules verbatim
- **CLAUDE.md:** ...
- (or "none present")

## Build / run / test
- `npm run dev` — ...
- `python build_generic_guide.py` — ...
- ...

## Conventions
- Naming: ...
- Versioning: ...
- Archive policy: ...

## External integrations
- ...

## Languages / locales
- ...

## Notes
- Anything you saw that the next agents (workflow-extraction, addon-synthesis) will need.

---META---
confidence: 0.XX
method: "..."
not_checked: [...]
sample_size: N or "exhaustive"
tools_used: {"Glob": N, "Read": N, "Grep": N}
---END META---
