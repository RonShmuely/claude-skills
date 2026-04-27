# Swarm Monitor — Live Dashboard (optional, observer-only)

A local Flask + Tailwind dashboard that watches Claude Code's subagent transcripts and parent-session logs, then streams live state to the browser. Purely observational — the swarm pattern works without it.

## Scope (read first)

This is a **standalone observability tool**, not part of the swarm-orchestrator framework's dispatch path. It reads from `~/.claude/projects/` (Claude Code's native logs) and `~/.swarm/` (per-dispatch sidecars written by runtime adapters). It writes only to its own SQLite history at `~/.claude/swarm/history.db` and its in-memory job registry. It never spawns agents in the production architecture — direct `claude -p` from the runtime adapter (e.g., Antigravity AGENTS.md, Claude Code skill, Cursor rules) is the canonical dispatch path.

**Currently single-user and local-only.** The `/api/dispatch`, `/api/jobs`, and `/api/jobs/<id>/stream` endpoints (sections marked DEPRECATED in `app.py`) were a Phase A convenience to spawn `claude -p` from inside the dashboard process — useful for ad-hoc UI dispatches, but the wrong layer for production. They will be removed in v2.2; new code should not depend on them.

The framework dispatches; the dashboard observes. If it's down, dispatches still work.



## What you see

- **Cards per agent** — one card per muscle you dispatch
- **Model badges** — purple Opus, blue Sonnet, green Haiku
- **Safety pills** — `[L]` grey, `[M]` amber, `[H]` red
- **Confidence pills** — green ≥85%, amber 70–85%, red <70% (parsed from META block)
- **Live tool trace** — which tool the agent is currently using, which path
- **Session grouping** — current session expanded, older sessions collapsed
- **Search + sort + filter** — find anything across sessions
- **Expand inline** or open full modal for deep inspection
- **Auto-refresh via SSE** — no polling, no page reload

## How it works

Reads from `~/.claude/projects/<project-slug>/<session-id>/subagents/agent-*.jsonl` — Claude Code's native subagent transcripts. Parses each JSONL event (tool_use, tool_result, text) and a companion `*.meta.json` for model + description. Streams aggregated state to the browser every 1.5s via Server-Sent Events.

No API keys, no auth, no outside network. Pure local observability.

## Setup

Requires Python 3 + Flask:

```bash
pip install Flask
```

That's it. No other dependencies.

## Running

```bash
cd dashboard
python app.py
```

Open http://127.0.0.1:5173 in a browser.

Or on Windows, double-click `launch.bat` — it opens the URL in your default browser automatically.

## Icon / shortcut (optional)

If you want a desktop shortcut with a custom icon, the PowerShell to create one:

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$sc = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Swarm Monitor.lnk")
$sc.TargetPath       = "<path-to>\dashboard\launch.bat"
$sc.WorkingDirectory = "<path-to>\dashboard"
$sc.IconLocation     = "<path-to-your-icon>.ico,0"
$sc.Save()
```

## Architecture

```
~/.claude/projects/
  └── <project-slug>/
      └── <session-id>/
          └── subagents/
              ├── agent-abc123.jsonl          ← live event stream
              ├── agent-abc123.meta.json      ← model + description
              ├── agent-def456.jsonl
              └── agent-def456.meta.json
                   │
                   ▼
            Flask backend polls every 1.5s
            Parses JSONL → extracts:
              • tool_uses count
              • tool history (last 15)
              • last text snippet
              • final text + META block
              • confidence / method / sample_size
              • elapsed time
                   │
                   ▼
            SSE /stream → browser
                   │
                   ▼
            Tailwind UI renders cards
```

## JSONL event schema

Each line in `agent-*.jsonl` is one event:

```json
{
  "parentUuid": "...",
  "isSidechain": false,
  "agentId": "abc123...",
  "type": "assistant" | "user",
  "message": {
    "role": "assistant",
    "model": "claude-haiku-4-5-20251001",
    "content": [
      { "type": "text", "text": "..." },
      { "type": "tool_use", "name": "Read", "input": { "file_path": "..." } },
      { "type": "tool_result", "content": "..." }
    ]
  },
  "timestamp": "2026-04-23T20:07:15.432Z"
}
```

The parser extracts tool names + inputs, counts tool uses, tracks the last text block, and captures the final text for META parsing.

## META block parsing

The dashboard parses the required META footer from each muscle's final text:

```
---META---
confidence: 0.85
method: "PowerShell EnumerateFiles recursive"
not_checked: ["semantic dedup", "content hashing"]
sample_size: exhaustive
---END META---
```

Extracted fields populate the confidence pill, method line, sample size indicator, and `not_checked` tags in the expanded card view.

## Safety tag parsing

The dashboard looks for `[L]` / `[M]` / `[H]` prefix in the agent description:

```
"[M] Audit MachineGuides diagnoses/"
         ↓ strips prefix, sets safety
safety: "medium"
description: "Audit MachineGuides diagnoses/"
```

The pill color reflects the safety level. If no prefix, defaults to `[L]`.

## Customization

Want to change the polling interval, colors, or layout?

- **Poll frequency:** `POLL_SECONDS` in `app.py` (default 1.5s)
- **History window:** `hours` param on `/api/agents` (default 24h, frontend sends 168 for 7 days)
- **Model colors:** `MODEL_STYLES` object in `templates/index.html`
- **Safety colors:** `SAFETY_STYLES` object in `templates/index.html`
- **Port:** last line of `app.py` — change `port=5173`

## Known limitations

- **Polling**, not filesystem events. `watchdog` would be more efficient but adds a dependency. Fine for up to ~100 agents.
- **No kill button yet.** Planned feature; would need to write cancel signals that Claude Code honors.
- **No command composer yet.** Dashboard is observer-only. To issue commands from the browser, you'd need to spawn `claude -p` subprocesses from Flask — see the skill's `docs/RECIPES.md` for the graduation path.
- **Single machine only.** Watches your local `~/.claude`. No remote-agent support.

## Extending

Good first extensions:

1. **Cost tracker** — parse `usage` field from JSONL events, show $/agent/session
2. **Parent → child tree** — group sub-agents by their parent session agent
3. **Desktop notifications** — browser Notification API when a long-runner finishes
4. **Recipe buttons** — dropdown "Run Recipe" that POSTs to Flask → spawns swarm
5. **Kill button** — write cancel signal to the agent's state file

## The dashboard is NOT required

The skill works entirely in-session without it. The dashboard just makes swarms visible. If you're running one-off swarms from a chat, you don't need it. If you want to watch a live swarm happen while you do other things, run it.
