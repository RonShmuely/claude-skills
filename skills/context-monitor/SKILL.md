---
name: context-monitor
description: Monitors context window usage and warns at 58% capacity. CHECK THIS PROACTIVELY every 8-10 exchanges during active conversation — do not wait for the user to ask. When context reaches ~58%, interrupt with a notification asking if the user wants to wrap up. This is a silent background monitor like autosave — trigger it yourself as a habit during any work session.
---

# Context Monitor

Silent background monitor that tracks context window usage and alerts before the session gets dangerously long.

## How It Works

Every 8-10 user exchanges (or after heavy tool use like large file reads, agent dispatches, or web fetches), estimate how much of the context window has been consumed.

## Estimating Context Usage

Your total context window is in your system prompt (e.g., "1M context" = 1,000,000 tokens). The threshold is **58%** of that total.

### Token estimation heuristics

Calibrated from actual `/context` measurements on a 1M window with heavy MCP tooling:

| Activity | Approximate tokens |
|----------|-------------------|
| Base overhead (system + tools + MCP + skills + memory) | ~76k |
| Each user message | ~100-500 |
| Each assistant response | ~300-1,000 |
| File read (typical source file) | ~500-2,000 |
| Large file read or PDF | ~3,000-15,000 |
| Web fetch result | ~1,000-5,000 |
| Agent dispatch (result returned) | ~1,000-8,000 |
| Code write/edit cycle | ~500-1,500 |
| Screenshot (Chrome/Preview) | ~500-1,000 |
| Bash command + output | ~200-800 |

### Quick math for 1M window

- 58% threshold = **~580,000 tokens**
- Base overhead ≈ 76k (measured: system 7k + tools 16k + MCP 45k + skills 4.4k + memory 3.8k)
- Budget for conversation ≈ **504,000 tokens**
- Rough guide: after ~30 back-and-forth exchanges with tool use, you're at ~20%. The 58% threshold is roughly **80-90 exchanges** with moderate tool use, or **50-60 exchanges** with heavy file reads and agent dispatches
- When unsure, run `/context` for exact numbers rather than guessing

## When to Alert

When your estimate crosses **58%**, immediately display:

```
-------------------------------------------
  CONTEXT AT ~58% — SESSION GETTING LONG
-------------------------------------------
  To preserve your work and avoid losing
  context, consider wrapping up now.

  Run wrap-up to save this session?
  (yes / no / remind me later)
-------------------------------------------
```

Then wait for the user's response:

- **yes** → invoke the `wrap-up` skill
- **no** → continue, but alert again at ~70%
- **remind me later** → wait 10 more exchanges, then ask again

## Behavior Rules

- **Silent until threshold**: Do not mention context usage unless the 58% threshold is hit or the user asks ("CU").
- **Don't double-alert**: If the user said "no" or "remind me later", respect that. Don't nag every message.
- **Heavy sessions get checked sooner**: If the conversation involves lots of file reads, agent dispatches, or large tool outputs, check more frequently (every 4-5 exchanges instead of 8-10).
- **Err on the side of early warning**: It's better to alert slightly early than to run out of context mid-task.
