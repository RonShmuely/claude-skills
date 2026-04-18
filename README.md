# Claude Code Skills

Custom skills for [Claude Code](https://claude.ai/code) — drop-in slash commands that extend Claude with specialized workflows.

---

## Skills

### 🔧 machine-diagnose
Diagnose faults on vehicles and heavy equipment by querying NotebookLM technical notebooks.

- Automatically identifies the right machine notebook from your description
- Queries it with the symptom and returns a structured diagnosis
- Works in Hebrew and English
- Triggers on fault codes, error displays, hydraulic issues, sensor failures, "won't start", etc.
- Supports: Wirtgen milling machines (W50Ri, W200i), Bobcat/Gehl skid loaders, Bomag rollers, Volvo trucks, and any machine with a NotebookLM notebook

**Trigger:** `/machine-diagnose` or just describe a machine problem naturally

**Requires:** `notebooklm` CLI installed and authenticated

---

### 🗂️ wrap-up
End-of-session wrap-up that saves conversation highlights to NotebookLM as long-term memory.

- Summarizes key decisions, insights, and action items from the session
- Uploads to a "Ron's Brain" notebook in NotebookLM
- Future sessions can query it instead of re-reading files or burning context tokens
- Deduplicates — won't upload the same session twice

**Trigger:** `/wrap-up`, "wrap up", "save this session", "store this in my brain"

**Requires:** `notebooklm` CLI installed and authenticated

---

## Installation

1. Find your Claude Code skills folder:
   - **Windows:** `%APPDATA%\Claude\...\skills\`
   - **Mac/Linux:** `~/.claude/skills/`

2. Copy the skill folder into it:
```bash
cp -r machine-diagnose ~/.claude/skills/
cp -r wrap-up ~/.claude/skills/
```

3. Restart Claude Code — the skill appears automatically.

---

## Requirements

Both skills use the [notebooklm-py](https://github.com/teng-lin/notebooklm-py) CLI:

```bash
pip install notebooklm-py
notebooklm login
notebooklm status  # should show your email
```

---

## Author

[RonShmuely](https://github.com/RonShmuely)
