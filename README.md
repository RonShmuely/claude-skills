# Claude Brain — Synced Config for Claude Code

Personal Claude Code configuration + custom skills, synced between Ron-PC and Ron-ACER via Google Drive Mirror with git history on top.

---

## Contents

| Item | Purpose | Linked into |
|---|---|---|
| `CLAUDE.md` | Global Claude Code system prompt (preferences, workflows, inspector rules) | `~/.claude/CLAUDE.md` (hardlink) |
| `inspectors/` | Conversational role prompts loadable by name | `~/.claude/inspectors/` (junction) |
| `skills/` | Custom slash commands | `~/.claude/skills/` (junction) |
| `settings.json` | Hooks, statusline, enabled plugins, model choice | `~/.claude/settings.json` (hardlink) |
| `project-memory/<name>/` | Accumulated per-project memory (user/feedback/project/reference) | `~/.claude/projects/C--<path>/memory/` (junction, one per project) |

Not synced (intentional): `settings.local.json` (per-machine Bash permissions), `.credentials.json` (auth tokens), conversation logs (`.jsonl` session files), plugin caches, shell snapshots.

**Project memory folders currently synced:** `desktop`, `weldingref`, `garageinfo`, `voicelayerapp`. Add more by dropping a folder into `project-memory/` and junctioning it (see setup below).

---

## Skills

### 🔧 machine-diagnose
Diagnose vehicle / heavy equipment faults by querying NotebookLM technical notebooks. Supports Wirtgen milling machines (W50Ri, W200i), Bobcat/Gehl skid loaders, Bomag rollers, Volvo trucks, and any machine with a notebook. Works in Hebrew and English.

**Trigger:** `/machine-diagnose`, or describe a machine problem naturally.
**Requires:** notebooklm-mcp configured.

### 🗂️ wrap-up
End-of-session wrap-up that saves conversation highlights to NotebookLM "Ron's Brain" as long-term memory. Deduplicates.

**Trigger:** `/wrap-up`, "wrap up", "save this session", "store this in my brain".
**Requires:** notebooklm-mcp configured.

### 🌐 web-cowork
Live browser collaboration via Playwright MCP. Claude drives Chromium while you watch. Includes Mark Mode overlay for visual annotation.

**Trigger:** `/web-cowork`, "cowork on X", "turn on mark mode".
**Requires:** Playwright MCP plugin, Python 3 on PATH.

### 🎨 app-icon-generator
Generate app/folder icons (512px + 256px PNG) from a design philosophy.

**Trigger:** "icon for X", "app icon", "folder icon".

### 💾 autosave
Periodically saves important conversation context to memory files during active sessions.

**Trigger:** runs itself every ~10 minutes of active conversation, or at session wind-down.

### 📊 context-monitor
Warns at ~58% context window usage so sessions don't run out of room.

**Trigger:** runs itself every 8–10 exchanges.

### 💻 pcusage
Live PC system stats — CPU, GPU, RAM, disk, network, running processes.

**Trigger:** "pc usage", "system stats", "how's my PC doing", "PCUSAGE".

### 📺 youtube-transcript
Download YouTube video transcripts / captions.

**Trigger:** paste a YouTube URL or ask to fetch a transcript.

---

## Inspectors

Conversational role prompts that override Claude's default tone and output format for the duration of a task. Invoked by name ("use the validator", "mvp-architect this") or by implicit match on the user's query. Full rules are in `CLAUDE.md`.

Current inspectors:
- `inspector-validator` — diagnostics-first code/design reviewer
- `inspector-mvp-architect` — senior staff systems architect across ML / frontend / backend

Add more by dropping a new `inspector-<name>.md` into `inspectors/` and pushing.

---

## Installation

### Primary path: Google Drive Mirror (both machines)

1. Install [Google Drive for Desktop](https://www.google.com/drive/download/) in **Mirror files** mode (not Stream). Accept default location `C:\Users\<you>\My Drive\`.
2. Wait for `My Drive\claude-brain\claude-skills\` to appear (synced from the other machine).
3. Run the link commands below — they replace `~/.claude/*` with links into the Drive-synced repo.

**Windows (PowerShell, no admin needed):**
```powershell
$repo = "$HOME\My Drive\claude-brain\claude-skills"

# Backup existing files (non-destructive)
Move-Item $HOME\.claude\CLAUDE.md     $HOME\.claude\CLAUDE.md.bak -ErrorAction SilentlyContinue
Move-Item $HOME\.claude\inspectors    $HOME\.claude\inspectors.bak -ErrorAction SilentlyContinue
Move-Item $HOME\.claude\skills        $HOME\.claude\skills.bak -ErrorAction SilentlyContinue
Move-Item $HOME\.claude\settings.json $HOME\.claude\settings.json.bak -ErrorAction SilentlyContinue

# Hardlinks for files, junctions for directories
New-Item -ItemType HardLink -Path "$HOME\.claude\CLAUDE.md"     -Target "$repo\CLAUDE.md"
New-Item -ItemType HardLink -Path "$HOME\.claude\settings.json" -Target "$repo\settings.json"
New-Item -ItemType Junction -Path "$HOME\.claude\inspectors"    -Target "$repo\inspectors"
New-Item -ItemType Junction -Path "$HOME\.claude\skills"        -Target "$repo\skills"

# Optional: convenience junction so documented path ~/claude-skills works
New-Item -ItemType Junction -Path "$HOME\claude-skills" -Target "$repo"

# Machine identity for git commits (use Ron-PC or Ron-ACER)
git config --global user.name "RonShmuely (Ron-ACER)"

# Per-project memory junctions.
# The .claude/projects/ folder name is derived from the project's absolute path
# (Windows slashes → dashes). Adjust "ronsh" below if laptop username differs.
$user = "ronsh"
New-Item -ItemType Junction -Path "$HOME\.claude\projects\C--Users-$user-Desktop\memory"              -Target "$repo\project-memory\desktop"
New-Item -ItemType Junction -Path "$HOME\.claude\projects\C--Users-$user-Desktop-WeldingRef\memory"   -Target "$repo\project-memory\weldingref"
New-Item -ItemType Junction -Path "$HOME\.claude\projects\C--Users-$user-Desktop-GarageInfo\memory"   -Target "$repo\project-memory\garageinfo"
New-Item -ItemType Junction -Path "$HOME\.claude\projects\C--Users-$user-Desktop-VoiceLayerAPP\memory" -Target "$repo\project-memory\voicelayerapp"
# (each parent folder is auto-created by Claude Code on first project session; create it manually with New-Item -ItemType Directory if needed)
```

**macOS / Linux:**
```bash
repo="$HOME/Google Drive/My Drive/claude-brain/claude-skills"   # may differ on Mac

mv ~/.claude/CLAUDE.md      ~/.claude/CLAUDE.md.bak 2>/dev/null
mv ~/.claude/inspectors     ~/.claude/inspectors.bak 2>/dev/null
mv ~/.claude/skills         ~/.claude/skills.bak 2>/dev/null
mv ~/.claude/settings.json  ~/.claude/settings.json.bak 2>/dev/null

ln -s "$repo/CLAUDE.md"     ~/.claude/CLAUDE.md
ln -s "$repo/settings.json" ~/.claude/settings.json
ln -s "$repo/inspectors"    ~/.claude/inspectors
ln -s "$repo/skills"        ~/.claude/skills
```

Restart Claude Code — skills, inspectors, and preferences all load from the Drive-synced repo.

### Fallback path: git only (no cloud folder)
```bash
git clone https://github.com/RonShmuely/claude-skills.git ~/claude-skills
# then apply the same links as above, with $repo = ~/claude-skills
# manual: git pull after sitting down at a machine, git push after every edit
```

---

## Sync model

- **Drive** handles real-time bidirectional file sync between machines (seconds to a few minutes).
- **Git** runs on top for version history and rollback. Commit + push from either machine — the other machine's Drive catches up, and `git pull` there picks up the commit metadata.
- **Machine identity** is baked into git commits as `RonShmuely (Ron-PC)` or `RonShmuely (Ron-ACER)` so you can trace which machine made which change.
- **Conflicts** are rare in single-user two-machine setups. When they happen, Drive creates a `(conflicted copy)` file labeled with the source machine name.

---

## Requirements

- `machine-diagnose`, `wrap-up`, `notebooklm` skills use [`notebooklm-mcp`](https://github.com/teng-lin/notebooklm-py) via MCP server.
- `web-cowork` uses Playwright MCP + Python 3.
- `pcusage` uses PowerShell (Windows-only).

---

## Author

[RonShmuely](https://github.com/RonShmuely)
