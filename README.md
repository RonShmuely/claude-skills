# claude-skills

Custom skills + inspectors for [Claude Code](https://docs.claude.com/claude-code), built and maintained by Ron Shmuely.

Drop-in additions to your `~/.claude/` setup. Every skill is self-contained — copy the folder you want and Claude Code picks it up.

> **Personal config (CLAUDE.md, settings.json, project memory) lives in a separate private repo.** This one is the shareable half: skills + inspectors, ready to use as-is.

---

## Skills

| Skill | What it does | Trigger |
|---|---|---|
| **machine-diagnose** | Diagnose vehicle / heavy-equipment faults by querying NotebookLM technical notebooks. Hebrew + English. | `/machine-diagnose`, or describe a machine fault naturally |
| **diagnosis-html** | Generate a standalone single-file HTML diagnosis matching the dark-industrial design reference. | After `machine-diagnose`, when user wants an HTML artifact |
| **swarm-orchestrator** | Multi-agent swarm framework with disciplined model-tier selection (Haiku narrow, Sonnet ambiguity, Opus consequence). 5-mitigation protocol, anomaly detection, memory tiers, live `/dashboard` with `/cockpit` + `/theater` modes. | `/swarm`, `swarm`, `multi-agent`, `wow demo` |
| **wrapup** | End-of-session: triage open threads, save memories, write a dated session summary, update the open-threads ledger, upload to NotebookLM. Supports `--rollup weekly\|monthly`. | `/wrapup`, "wrap up the session" |
| **autosave** | Periodic mid-session memory save (every ~10 min of active work). Background habit, no user prompt needed. | Self-triggers during active work |
| **web-cowork** | Launch Chromium via Playwright MCP and co-work on a local page. Includes Mark Mode overlay (`mark-mode.js`) for visual annotation. | `/web-cowork`, "let's cowork on X" |
| **app-icon-generator** | Produce a 512px + 256px PNG app/folder icon from a design philosophy. | "make me an icon for X" |
| **quick-mockup** | Generate a quick HTML mockup (font/layout iteration) using a canonical dark-industrial template. | `/quick-mockup`, "mock up X" |
| **stencil-studio** | Build offline AI-assisted image/stencil editor desktop apps (Flask + Fabric.js + Ollama / ComfyUI). | `/stencil-studio`, "build a stencil app" |
| **pcusage** | Live PC system stats (CPU, GPU, RAM, disk, network, processes). Windows / PowerShell. | "PCUSAGE", "system stats" |
| **notebooklm** | Full programmatic NotebookLM API — create notebooks, add sources, generate podcasts/videos/reports/quizzes/infographics, download artifacts. | `/notebooklm`, "create a podcast about X" |
| **youtube-transcript** | Download YouTube transcripts. | YouTube URL or "get transcript of X" |
| **skill-forge** | Self-authoring skill — write SKILL.md for a new skill from a captured pattern. | Invoked by `wrapup`'s forge pass |

Some skills (e.g. `swarm-orchestrator`) ship their own `docs/`, `templates/`, `lib/`, and `dashboard/` — see each skill's folder.

---

## Inspectors

Conversational role prompts that override Claude's default tone and output for the duration of a task.

| Inspector | Role |
|---|---|
| **inspector-validator** | Diagnostics-first code/design reviewer |
| **inspector-mvp-architect** | Senior staff systems architect across ML / FE / BE |

To invoke: "use the validator", "mvp-architect this", "run the X inspector". Inspector stays loaded across follow-ups until you switch or pivot.

---

## Install

Pick the skill(s) you want and drop the folder into your `~/.claude/skills/`:

```powershell
# Windows
git clone https://github.com/RonShmuely/claude-skills "$env:USERPROFILE\Desktop\claude-skills"
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\machine-diagnose" `
                            -Target "$env:USERPROFILE\Desktop\claude-skills\skills\machine-diagnose"
```

```bash
# macOS / Linux
git clone https://github.com/RonShmuely/claude-skills ~/Desktop/claude-skills
ln -s ~/Desktop/claude-skills/skills/machine-diagnose ~/.claude/skills/machine-diagnose
```

Or symlink/junction the entire `skills/` and `inspectors/` directories at once.

### Drift guard

If you sync this repo across machines, enable the pre-commit drift check so concurrent edits don't silently overwrite each other:

```
git config core.hooksPath .githooks
```

The hook refuses commits when the local branch is behind upstream and tells you to `git pull --ff-only` first.

---

## Requirements

- **Claude Code** 1.x or later
- **NotebookLM MCP** for `machine-diagnose`, `wrapup`, `notebooklm` — install via `pip install notebooklm-mcp` and configure in `~/.claude/mcp.json`
- **Playwright MCP** for `web-cowork`
- **Python 3.11+** for `swarm-orchestrator` dashboard, `notebooklm`, `pcusage` (Windows only for pcusage)

---

## License

MIT — see [LICENSE](LICENSE). Use, fork, modify, redistribute. If a skill saves you time, a star is appreciated.

## Contributing

PRs welcome. Each skill should be self-contained with its own `SKILL.md` (Anthropic skill format). For new inspectors, follow the existing `Role / Operating Principles / Behavior / Output Format / Hard Rules` layout.
