---
name: autosave
description: Periodically save conversation context to memory during active sessions. Use this skill every few meaningful exchanges (roughly every 10 minutes of active conversation) to persist important decisions, feedback, project context, and discoveries to memory files and CLAUDE.md. Trigger this yourself as a background habit during any substantive work session — don't wait for the user to ask. Also trigger when the conversation is winding down or the user is about to leave.
---

# Autosave — Conversation Context Persistence

You are acting as an autosave system during active conversations. The goal is to ensure important context survives session boundaries without relying on cron jobs or timers.

## When to Autosave

Save after every 3-5 meaningful exchanges during active work. "Meaningful" means exchanges where decisions were made, feedback was given, bugs were found, architecture was discussed, or project context was shared. Don't save after simple Q&A or small talk.

Also save when:
- The user says something like "brb", "gotta go", "that's it for now"
- A major task or feature is completed
- The user gives feedback about your behavior or approach
- You learn something new about the project, user, or their preferences

## What to Save

Check the memory system (`MEMORY.md` index + individual memory files) and `CLAUDE.md` for what already exists, then save only **new or changed** information:

| Type | Where | Examples |
|------|-------|----------|
| User preferences & feedback | Memory files (`feedback_*.md`) | "Don't do X", "I prefer Y", corrections to your approach |
| Project context | Memory files (`project_*.md`) | Ongoing work, deadlines, who's doing what, blockers |
| User profile updates | Memory files (`user_*.md`) | Role changes, new responsibilities, knowledge areas |
| External references | Memory files (`reference_*.md`) | URLs, tool locations, dashboard links |
| Architecture/pattern changes | `CLAUDE.md` | New modules, changed patterns, new known issues |

## What NOT to Save

- Information already in memory or CLAUDE.md (no duplicates)
- Ephemeral task details (use TodoWrite for in-session tracking)
- Things derivable from code or git history
- Debugging steps or fix recipes (the fix is in the code)

## How to Save

1. Quickly review what's happened since your last save (or session start)
2. Check existing memory files and CLAUDE.md for overlap
3. Write new memory files or update existing ones as needed
4. Update `MEMORY.md` index if you added new files
5. Update `CLAUDE.md` only if project-level info changed (architecture, patterns, known issues)

Keep saves lightweight — a few sentences per memory file. Don't interrupt the user's flow; do this quietly between responses when natural.

## Important

This is a background habit, not a ceremony. Don't announce "autosaving now" unless you changed something the user should know about. The user should barely notice this happening — it's like an IDE autosaving files in the background.
