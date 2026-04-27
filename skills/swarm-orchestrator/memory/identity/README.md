# Identity tier — how to seed it

Identity is the **stable** memory tier — facts about you that don't change per swarm run. The orchestrator reads these files at session start to tailor its behavior (which model tiers to default to, which language to respond in, what kinds of tasks you typically dispatch, what to never assume).

## What goes here

Markdown files, one fact per file. The filename (without `.md`) is the lookup key. Examples:

- `user.md` — who you are, your role, what you do
- `preferences.md` — output format preferences, language, tone
- `costs.md` — your monthly Claude budget posture (relaxed / strict / unmetered)
- `domain.md` — the domain(s) you work in (welding, road milling, machine diagnosis, web dev, etc.)
- `forbidden.md` — things the orchestrator should NEVER do without explicit confirmation

## What does NOT go here

- Per-run artifacts → `memory/operations/`
- Past run history → `memory/knowledge/runs.sqlite` (auto-populated)
- Secrets / credentials / API keys → never; identity is committed-friendly content

## How the orchestrator reads it

```python
from memory import identity

persona = identity.get("user")           # → str (file contents) or None
prefs   = identity.get("preferences")    # → str or None
keys    = identity.list()                # → list[str] of all filenames
```

The orchestrator uses what it finds; missing files do not error. Start with one file (`user.md`) and grow as you notice the orchestrator making assumptions you'd rather it didn't.

## Example `user.md` skeleton

```markdown
# User

- Name (or alias): <your name>
- Role: <what you do>
- Primary languages: <e.g., English, Hebrew>
- Typical swarm tasks: <e.g., audit large repos, classify support tickets, diagnose machine faults>
- Cost posture: <e.g., default to Sonnet, escalate to Opus only on `[H]` tasks>
- Hard rules:
  - Never push to `main` without confirmation.
  - Never delete files; archive instead.
  - <add your own>
```

## Why this is empty by default

Identity is **never auto-written** by the orchestrator — you write it. The skill ships with no identity assumptions so a new user starts neutral. If you copy the skill from another machine and want the same persona, copy `memory/identity/*.md` along with the skill.

## Privacy

These files live alongside the skill in your local install. They are **not** synced anywhere by default. If you put the skill folder in git, decide per-file whether to commit identity (most users don't — the `.gitignore` at the skill root does not exclude `memory/identity/`, but you can add `memory/identity/*.md` to your personal `.gitignore` if you want).
