---
name: web-cowork
description: Launch Chromium via Playwright MCP and co-work with the user on a local web page — Claude drives the browser (navigate, click, evaluate JS, screenshot, read console/network) while the user watches/interacts live. Includes a Mark Mode overlay (mark-mode.js) the user can inject to visually annotate elements/regions for Claude to act on. Trigger on explicit "/web-cowork", or phrases like "launch chromium and co-work on X", "open X in browser for cowork", "let's cowork on this page", "drive the browser for me on X", "turn on mark mode", "mark this for edits". Handles local files by starting a background HTTP server in the folder. Stages outside files into a sandbox subfolder. Does NOT auto-cleanup — server + browser stay open until user explicitly says "stop cowork" / "close browser" / "done coworking".
---

# Web Co-work

Live collaboration loop where Claude drives a Chromium window via Playwright MCP while the user watches and interacts with the same page. Use when the user wants to inspect / iterate on a local web artifact (HTML file, static site, served app) together with Claude.

## Trigger discipline

Fire on:
- `/web-cowork`
- "launch chromium and co-work on <X>"
- "open <X> in browser for cowork"
- "let's cowork on this page"
- "drive the browser with me on <X>"

Do NOT fire on casual "open this in a browser" (that's just a launch, not a co-work session) unless the user clearly wants Claude to keep driving afterward. When unsure, ask: *"Run this as a cowork session (I drive Chromium + you interact live), or just open the page?"*

## Phase 1 — Setup

### 1a. Resolve the target
Parse from the user's request. Target can be:
- A local file path (`.html`, `.md`, etc.)
- A local folder (serve its root)
- A `http://` / `https://` URL (skip server, go straight to Chromium)

For local paths, pick a **served root**:
- If user gave a file → served root = its parent folder.
- If user gave a folder → served root = that folder.

### 1b. Load Playwright MCP tools
The Playwright MCP tools are deferred. Load them at invocation with:

```
ToolSearch query: "select:mcp__plugin_playwright_playwright__browser_navigate,mcp__plugin_playwright_playwright__browser_snapshot,mcp__plugin_playwright_playwright__browser_take_screenshot,mcp__plugin_playwright_playwright__browser_resize,mcp__plugin_playwright_playwright__browser_click,mcp__plugin_playwright_playwright__browser_evaluate,mcp__plugin_playwright_playwright__browser_close"
```

Also consider loading (lazily, only when needed): `browser_fill_form`, `browser_console_messages`, `browser_network_requests`, `browser_press_key`, `browser_wait_for`, `browser_tabs`.

### 1c. Start the local HTTP server (local targets only)
Skip this step for `http://` / `https://` targets.

1. Try port `8765` first. If busy, increment (8766, 8767, …) until a free one is found (cap at 10 tries).
2. Launch with `python -m http.server <port>` in the served root, using **Bash `run_in_background: true`**. Remember the background task ID — it's needed for stop.
3. Record for the rest of the session:
   - `served_root` (absolute path)
   - `port`
   - `server_task_id` (from Bash)
   - `staged_files` (list — starts empty)

Port-busy check: attempt navigation to `http://localhost:<port>/` before starting; if it responds, try the next port.

### 1d. Launch Chromium
1. `browser_resize` to `1400 × 900` (good default for side-by-side with a terminal).
2. `browser_navigate` to `http://localhost:<port>/<file-relative-path>` (for files) or the bare port URL (for folders) or the user's URL (for http/https).
3. `browser_take_screenshot` to confirm the page loaded and share a visual with the user.
4. If the page errored (check console via `browser_console_messages`), report it briefly before starting the loop.

## Phase 2 — Co-work loop

In this phase, Claude and the user trade off driving the page. Claude has a rich browser toolkit — use the right tool for the job:

| Intent | Tool |
|---|---|
| See the page | `browser_take_screenshot` (viewport) or `browser_snapshot` (accessibility tree, better for clicking) |
| Click / type | `browser_click`, `browser_fill_form`, `browser_press_key` (need a snapshot first to get refs) |
| Run JS / inspect state | `browser_evaluate` |
| Check console | `browser_console_messages` |
| Check network | `browser_network_requests` |
| Navigate | `browser_navigate` |
| Reload after user edits source | `browser_navigate` to the same URL, or `browser_evaluate(() => location.reload())` |

### When the user edits the served file
If the user (via Claude's Edit/Write tool) changes a file that's being viewed, the browser won't auto-reload. After the edit lands, reload via `browser_evaluate(() => location.reload())` unless the user said not to.

### Staging outside files
If the user references a file outside the served root (e.g. `~/Downloads/foo.md` while serving `~/Desktop/project/`), auto-stage it:

1. Ensure `<served_root>/.cowork-temp/` exists (create if not).
2. Copy the outside file into `.cowork-temp/` preserving its name (or append `-N` if a name collision).
3. Append the staged path to `staged_files`.
4. Reference it in the browser as `http://localhost:<port>/.cowork-temp/<name>`.

Tell the user briefly when you stage: *"Staged `foo.md` into `.cowork-temp/` (auto-removed on stop)."*

If a file with the same name already exists at the served root (not in `.cowork-temp/`), prefer it — don't stage, don't overwrite.

### Mark Mode — visual annotation overlay

This skill ships with `mark-mode.js` (sibling file in the skill folder) — an injectable overlay that lets the user point at parts of the page for Claude to act on.

**Trigger phrases:** "turn on mark mode", "let me mark this", "inject mark mode", "mark for edits".

**To inject:**
1. Copy `<skill-folder>/mark-mode.js` → `<served_root>/.cowork-temp/mark-mode.js` (stage it like any other asset).
2. Run:
   ```js
   const s = document.createElement('script');
   s.src = '/.cowork-temp/mark-mode.js?t=' + Date.now();
   document.head.appendChild(s);
   ```
   via `browser_evaluate`. (Cache-bust with the timestamp so re-injections pick up updates.)

**User-facing UI:** floating widget top-right, three modes:
- **Element** — hover outlines, click to mark (snaps to DOM element)
- **Rect** — drag to draw a rectangle for region marks (for layout/gap issues that aren't one element)
- **Off** — no interactions; default

Each mark gets a pink numbered badge + outline, plus a note prompt (Ctrl+Enter saves, Esc skips). Keyboard: `E` element, `R` rect, `X` off, `Esc` cancels active mode.

**Reading marks:** `browser_evaluate(() => window.__markMode.getMarks())` returns an array of:
```
{ id, type: 'element'|'rect', tag?, selector?, text?, rect: {x,y,w,h}, note, createdAt }
```

When the user says "check marks" / "apply the marks" / "act on the marks", read them, then act on each:
- For `element` marks with a `selector`, resolve back to the source file if possible (e.g. match `text` back to the markdown). Edit the source accordingly.
- For `rect` marks, use the rect + a `browser_take_screenshot` to understand visually what's inside that region, then decide what to change.
- Clear marks (`window.__markMode.clearAll()`) after applying, or leave them so the user sees what was addressed.

**Cleanup:** mark-mode overlay is removed via its Close button or `window.__markMode.destroy()`. The `mark-mode.js` file in `.cowork-temp/` is cleaned up by the normal Phase 3 cleanup.

### Driving input events for JS-only targets
Some pages (like the md-viewer) only accept input via drag-drop or File API — you can't just navigate a file URL. Use `browser_evaluate` to synthesize a `DragEvent` with a `DataTransfer` holding a `File` built from `fetch()`'d bytes. Example shape:

```js
const res = await fetch('/path/to/file.md');
const file = new File([await res.text()], 'file.md', { type: 'text/markdown' });
const dt = new DataTransfer(); dt.items.add(file);
window.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
```

## Phase 3 — Cleanup (EXPLICIT ONLY)

**Do not run cleanup on end-of-turn, context compression, or ambiguous signals.** Cleanup runs only when the user says: "stop cowork", "close browser", "done coworking", "end cowork", "/stop-cowork", or during `/wrapup` if they confirm the cowork session is over.

When it fires:

1. **Browser:** `browser_close`.
2. **Server:** kill the background task (store/use the task ID from setup — use `BashOutput`/`KillShell` tools to terminate it). If the task ID is lost, fall back to finding the `python -m http.server <port>` process and killing it (on Windows: `taskkill /F /PID <pid>`, use `netstat -ano | findstr :<port>` to find it).
3. **Staged files:** delete `<served_root>/.cowork-temp/` entirely (one `rm -rf` — since nothing else should live there). If the directory has unexpected contents, list them and ask before deleting.
4. Report what was cleaned up in one line: *"Closed Chromium, stopped server on :8765, removed .cowork-temp/ (3 files)."*

If the user says "stop cowork but keep the server" or similar partial stops, honor the specific scope — just close Chromium, leave the server and staged files.

## PowerToys Workspaces (optional one-time setup)

PowerToys Workspaces (installed on this machine) lets the user capture a window layout (terminal + Chromium) and relaunch it with one click. **This skill does NOT auto-create Workspaces** — creation is a one-time manual step by the user. The skill just takes advantage of them when present.

Offer this setup the first time a user runs `/web-cowork` in a session (only if they seem interested — don't push):

> *"Tip: since PowerToys is installed, you can position this terminal + the Chromium window how you like, then open PowerToys → Workspaces → Create Workspace, and save as e.g. `Web Cowork`. Next time, launching that Workspace pre-arranges both windows before we start."*

If a PowerToys Workspace named `Web Cowork` (or similar) is already active when the skill fires, just proceed — no need to re-arrange. Don't attempt to read or write the Workspaces JSON directly; it's not a supported integration point.

## Safety / edge cases

- **Serve scope:** never serve from `~` or `C:\` or any parent of multiple projects — too much exposure. If the requested served root is above a sensible project scope, ask the user to confirm.
- **Port conflicts:** if `8765` is in use by something that isn't ours (i.e. an earlier cowork session the skill doesn't know about), pick the next port and note it.
- **Git repo pollution:** `.cowork-temp/` lives inside the served folder. If that folder is a git repo, suggest adding `.cowork-temp/` to `.gitignore` on first stage (once per session).
- **Missing Python:** if `python` isn't found, try `python3`, then `py`. If none work, tell the user and stop.
- **File not found:** if the target path doesn't exist, stop setup and say so — don't start a server in the wrong place.
- **Browser already open from a prior session:** Playwright MCP reuses its session. If `browser_navigate` works, assume a live context and proceed; no need to "launch" fresh.
- **Cross-platform:** this skill is Windows-focused (uses `taskkill`, references PowerToys). On other OSes, adapt the kill step (`kill <pid>` on Unix).

## Minimal happy path (for reference)

User: *"cowork on md-viewer.html"* (cwd = `C:\Users\ronsh\Desktop\MachineGuides`)

1. ToolSearch → load Playwright browser tools.
2. Bash `cd MachineGuides && python -m http.server 8765` in background.
3. `browser_resize 1400 900` → `browser_navigate http://localhost:8765/md-viewer.html` → `browser_take_screenshot`.
4. Report: *"Chromium is up on md-viewer.html. What do you want to do?"*
5. Loop: respond to user instructions using browser_* tools.
6. On "stop cowork": `browser_close` → kill background bash task → `rm -rf .cowork-temp` (if exists) → report.
