---
name: skill-forge
description: After completing a complex task (5+ tool calls on a novel pattern), generate a reusable SKILL.md capturing the procedure, pitfalls, and verification steps. The Hermes self-improving loop: solve → document → retrieve → improve → repeat. Also invoked by wrapup as a pre-step to scan the full session for forge candidates.
---

# Skill Forge

After solving something worth remembering, write it down as a reusable skill. Future sessions load the skill instead of reasoning from scratch — Hermes benchmarks show 40% faster completion once 20+ self-created skills exist.

## When to Forge

Forge when ALL three are true:
1. The task involved **5 or more tool calls** (reads, edits, bash, web searches, agent dispatches)
2. The pattern is **novel** — not already covered by an existing skill
3. It's **reusable** — this could come up again in a different session or project

Also forge when:
- You hit errors/dead ends and found the working path (the path itself is the skill)
- The user corrected your approach — that correction is worth preserving
- A multi-step workflow was discovered that isn't obvious from docs alone

**Do NOT forge for:**
- One-off project-specific tasks (renaming a variable in a single file, etc.)
- Simple Q&A or explanation tasks
- Patterns already covered by an existing skill — update that skill instead
- Tasks that would produce fewer than 5 meaningful procedure steps

## Pre-Forge: Duplicate Check

Before creating, scan the available-skills list in the system-reminder:
- Similar skill exists → **patch it** (add edge cases, improved steps) rather than creating a new file
- Existing skill covers 80%+ of the workflow → skip, or note the gap to update later

## Procedure

### 1. Name the skill

Short kebab-case slug, `verb-noun` or `noun-verb` format. Max 3 words, lowercase, hyphens only.
Describes WHAT it does, not HOW. Examples: `deploy-vercel`, `notebooklm-research`, `debug-python-hook`, `build-swarm-task`.

### 2. Check for duplicates

```bash
ls /c/Users/ronsh/Desktop/claude-skills/skills/
```

If a directory with the same or very similar slug exists, read its SKILL.md and decide: update it, or proceed with a distinct new name.

### 3. Write the SKILL.md

Target: `/c/Users/ronsh/Desktop/claude-skills/skills/<slug>/SKILL.md`

Use this template exactly:

```markdown
---
name: <slug>
description: <One sentence: what + when. This is Level 0 — Claude sees only this before deciding to load the skill. Make it specific enough to avoid false triggers.>
---

# <Title Case Name>

## When to Use
- <Specific condition 1>
- <Specific condition 2>

## Quick Reference
| Step | Action | Tool |
|------|--------|------|
| 1 | ... | Bash / Read / Edit / Agent |
| 2 | ... | ... |

## Procedure

### 1. <Step name>
<What and why — include the non-obvious reasoning>

### 2. <Step name>
<What and why>

## Pitfalls
- **<Problem>:** <How to avoid or recover — include error messages if recognizable>

## Verification
- [ ] <How to confirm a key step worked>
- [ ] <How to confirm overall success>
```

### 4. Confirm the forge

Tell the user in one line:
> "Forged skill `<slug>` → `skills/<slug>/SKILL.md`. Available next session."

## Forge Rules

- **Max 1 forge per session** unless the user asks for more
- **Max 2 forges during a wrapup** pass
- Forge only after a task completes — never mid-task
- Don't announce "thinking about forging" — just do it quietly when done
- Skills belong to the user: always check for sensitive info before writing (credentials, internal paths, private API keys) — sanitize or generalize before saving

## When Called from wrapup

Scan the entire session for forge candidates:
1. Look for multi-tool-call sequences (5+) that solved something novel
2. Rank by: novelty × reusability × session value
3. Pick the top 1–2 candidates only
4. Forge each one before wrapup proceeds to the Brain upload

## Pitfalls

- **Over-forging:** Too many narrow skills bloat the index. One well-named general skill beats three hyper-specific ones.
- **Duplicate name collision:** Always check the existing skills dir before writing. A slug conflict silently overwrites the old skill if you use Write instead of checking first.
- **Sensitive data in paths:** If the procedure includes absolute paths like `C:\Users\ronsh\Desktop\...`, generalize to `~/Desktop/...` or `<project-dir>/...` so the skill works across machines.
- **Vague descriptions:** A description like "do the thing" won't trigger at Level 0. Write it as if explaining to someone who doesn't know the context.
