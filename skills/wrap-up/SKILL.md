---
name: wrap-up
description: End-of-session wrap-up that saves conversation highlights to NotebookLM as long-term memory. Use when the user says "wrap up", "save this session", "store this in my brain", or at the end of a productive session. Also triggers on /wrap-up.
---

# Session Wrap-Up to NotebookLM

Save the key takeaways from the current conversation into a persistent "Ron's Brain" notebook in NotebookLM. This acts as long-term memory across sessions — instead of re-reading files or burning tokens on context, future sessions can query NotebookLM with a single call to recall past decisions, insights, and action items.

## Prerequisites

Uses the NotebookLM MCP server (always running via proxy on weldrefapp). No CLI auth needed.

## Workflow

### Step 1: Find the Brain Notebook

Use the MCP tool to list notebooks:
```
mcp__notebooklm-mcp__notebook_list
```

Look for "Ron's Brain" (ID: `2a0bb671-3bde-414f-b1a9-b96da4ad219f`). If not found, create it:
```
mcp__notebooklm-mcp__notebook_create  title="Ron's Brain"
```

### Step 2: Summarize the Session

Review the entire conversation and produce a structured summary. Include:

- **Session date** — today's date
- **Topic** — what the session was about in one line
- **Key decisions** — any choices made with their rationale
- **Insights & learnings** — non-obvious things discovered
- **Action items** — anything the user needs to follow up on
- **Technical notes** — commands, configurations, or patterns worth remembering
- **Context** — any background that would help future sessions understand why these decisions were made

Keep it concise but complete. Prioritize information that would be expensive to rediscover.

### Step 3: Save to NotebookLM (both note AND source)

Save the summary as a **note** (unlimited, acts as backup):
```
mcp__notebooklm-mcp__note
  notebook_id="2a0bb671-3bde-414f-b1a9-b96da4ad219f"
  action="create"
  title="Session: <topic> — <date>"
  content="<summary>"
```

Also save as a **text source** (enables AI-powered `notebook_query` search):
```
mcp__notebooklm-mcp__source_add
  notebook_id="2a0bb671-3bde-414f-b1a9-b96da4ad219f"
  source_type="text"
  title="Session: <topic> — <date>"
  text="<summary>"
  wait=true
```

Both are required. Notes are the unlimited backup. Sources enable semantic search via `notebook_query`.

Confirm both were saved successfully.

### Step 4: Report Back

Tell the user:
- What was saved (brief overview)
- The notebook it was saved to ("Ron's Brain")
- How to recall it later: *"In any future session, ask Claude to query your NotebookLM brain notebook for context on [topic]."*

## Recall Pattern (for other skills/sessions)

To retrieve past session context in a future conversation, use BOTH methods:

**Method 1 — AI search (preferred for broad questions):**
```
mcp__notebooklm-mcp__notebook_query
  notebook_id="2a0bb671-3bde-414f-b1a9-b96da4ad219f"
  query="What do I know about <topic>?"
```
This returns grounded, cited answers from all stored session sources — semantic long-term memory.

**Method 2 — Direct note listing (preferred for "what happened last session"):**
```
mcp__notebooklm-mcp__note
  notebook_id="2a0bb671-3bde-414f-b1a9-b96da4ad219f"
  action="list"
```
This lists all session notes by title. Read the relevant one for full details.

## Tips

- Run wrap-up at the end of any session that involved decisions, research, or learning worth preserving
- The brain notebook grows over time — each session adds a new note
- NotebookLM's RAG system means you only retrieve what's relevant, not everything
- This saves tokens in future sessions by avoiding re-reading large context files
- Always use MCP tools (`mcp__notebooklm-mcp__*`), never the CLI
