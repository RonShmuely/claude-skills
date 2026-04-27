# `/swarm-addons` — Command Handler Recipes

These are step-by-step recipes the orchestrator (you) follow when the user types `/swarm-addons <subcommand>` in any session. Each subcommand maps to a small sequence of Bash + file ops + reload. No separate command file is needed in v1 — the orchestrator parses the input directly.

All commands are non-destructive by default. Removal archives, never deletes. Install does NOT auto-run package managers (`npm install` / `pip install`) — the user reviews the addon's contents and runs any install commands themselves.

---

## `/swarm-addons list`

**Goal:** show the user every discovered addon with status, version, source tier, priority, contribution counts.

```bash
cd <skill-dir> && python lib/addons.py list
```

The output is JSON-lines. Parse and present as a table in the user's language. Sample format:

| Name | Version | Source | Status | Priority | Skills | Recipes | Workflows | Hooks |
|---|---|---|---|---|---|---|---|---|
| auto-adapter | 1.0.0 | built-in | enabled | 80 | 0 | 1 | 0 | 0 |
| domain-bundle | 0.1.0 | user | disabled | 50 | 5 | 2 | 3 | 0 |
| (etc.) |

If `load_errors` is non-empty, list them under the table with a "⚠️ Load issues" header.

End with the available actions:
> *To enable: `/swarm-addons enable <name>` · To inspect: `/swarm-addons info <name>` · To learn from a repo: `/swarm-addons learn <path>`*

---

## `/swarm-addons info <name>`

**Goal:** show the manifest summary plus the full file list of one addon.

Steps:

1. Read `<addon-dir>/addon.yaml` (search all configured paths; first match wins per priority).
2. Print: name, version, description, author, source tier, status, priority, requires, tags.
3. Walk the addon dir and list every file under `skills/`, `recipes/`, `templates/`, `workflows/`, `hooks/`, `docs/`.
4. If a `README.md` exists at the addon root, append its first paragraph to the output.

If the user passed a name that isn't installed:
> *"Addon `<name>` not found. Run `/swarm-addons list` to see installed addons."*

---

## `/swarm-addons enable <name>`

**Goal:** flip an addon to `status: enabled` via user-level settings, then reload.

Steps:

1. Read `~/.claude/swarm-orchestrator/settings.json` (create with `{"addons": {"disabled": []}}` if missing).
2. Remove `<name>` from `addons.disabled` if present.
3. Atomic write: temp file + rename.
4. Re-run `python lib/addons.py list` to confirm the addon now shows `status: enabled`.
5. Tell the user:
   > *"`<name>` enabled. Skills/recipes/workflows it provides are now visible to the orchestrator on the next user message. Restart your conversation slot if the addon contributes triggers you want active immediately."*

If the addon's manifest has `status: disabled` (hardcoded by the author), enabling it requires editing the manifest. Surface that explicitly:
> *"Note: this addon's manifest declares `status: disabled` (likely a `auto-adapter` draft awaiting review). To enable, edit `<path>/addon.yaml` and change to `status: enabled`."*

---

## `/swarm-addons disable <name>`

**Goal:** add the addon's name to `addons.disabled` in user settings.

Steps:

1. Read `~/.claude/swarm-orchestrator/settings.json` (create if missing).
2. Append `<name>` to `addons.disabled` if not already present.
3. Atomic write.
4. Confirm with `python lib/addons.py list`.
5. Tell the user:
   > *"`<name>` disabled. Its skills/recipes/workflows are no longer visible to the orchestrator. Re-enable with `/swarm-addons enable <name>`."*

---

## `/swarm-addons doctor`

**Goal:** run the addon validator and report.

```bash
cd <skill-dir> && python lib/addons.py doctor
```

Parse output (lines like `OK <name> ...` or `FAIL <name>: <issues>`). Present:

| Status | Addon | Issues |
|---|---|---|
| ✅ OK | auto-adapter | — |
| ❌ FAIL | domain-bundle | requires 'wix-base' which is not installed |

Below the table, summarize:
> *"`<N>` OK / `<M>` FAIL. `<K>` load errors."*

If any FAIL: suggest the fix per error type:
- `requires '<x>' which is not installed` → *"Install `<x>` first via `/swarm-addons install <source>`."*
- `addon contributes nothing` → *"Edit `<addon>/addon.yaml` and add at least one path under `provides:`."*

---

## `/swarm-addons learn <repo-path>`

**Goal:** invoke the built-in `auto-adapter` addon's `learn-repo` recipe on the target repo.

Steps:

1. Resolve `<repo-path>` (handle `~` and relative paths). If it doesn't exist, abort: *"Repo not found at `<path>`. If it's a remote repo, clone it first."*
2. Look up the recipe:
   ```python
   match = registry.find_recipe("learn-repo")
   assert match is not None, "auto-adapter addon missing — reinstall the skill"
   addon, recipe_path = match
   ```
3. Compute the output dir: `~/.claude/swarm-orchestrator/addons/<repo-basename>-bundle/`. If it exists and is non-empty, abort with: *"`<output-dir>` already exists. Run `/swarm-addons remove <name>` first or pass `--out=<alternate-dir>`."*
4. Confirm with the user (Hebrew or English):
   > *"אדפיש 5 סוכנים על `<repo-path>`: 3 סקירה + 1 סינתזה (Opus) + 1 ביקורת (Opus). יווצר addon ב-`<output-dir>` עם `status: disabled` (גייט אישור). אישור?"*
5. After `כן` / `yes`, dispatch the recipe per the standard Lifecycle (Steps 1–8 of SKILL.md), substituting the recipe-defined agent list.
6. The synthesis muscle writes the addon files. The doctor muscle validates.
7. Present the final summary using the template in `addons/_core/auto-adapter/recipes/learn-repo.yaml` `synthesis.format`. End with the `/swarm-addons enable <name>` invocation.

---

## `/swarm-addons install <source>`

**Goal:** copy or `git clone` an external addon into the user-installed addons dir, then doctor.

`<source>` is one of:
- Absolute or relative local path → `cp -r <source> ~/.claude/swarm-orchestrator/addons/<name>/`
- `git+https://github.com/USER/REPO` or plain `https://github.com/USER/REPO` → `git clone <url> ~/.claude/swarm-orchestrator/addons/<name>/`
- `git+ssh://...` → same as above with SSH
- A `.tar.gz` URL → download to a temp file, `tar -xzf` into the addons dir
- Plain GitHub `USER/REPO` shorthand → expand to `https://github.com/USER/REPO`

Steps:

1. Determine `<name>` — prefer the source's basename (e.g., `wix-helper` from `https://github.com/x/wix-helper`). If it conflicts with an installed addon, abort: *"`<name>` already installed at `<path>`. Use `--name=<other>` or run `/swarm-addons remove <name>` first."*
2. Create the target dir: `mkdir -p ~/.claude/swarm-orchestrator/addons/<name>/`.
3. Run the appropriate copy/clone/extract command. Capture stderr.
4. Confirm `addon.yaml` exists at the destination root. If not: *"`<source>` doesn't look like a valid swarm-orchestrator addon (no `addon.yaml`). Aborted; cleaned up partial install at `<path>`."*
5. Run `python lib/addons.py doctor` and report any findings about the new addon.
6. **Do NOT auto-run** `npm install`, `pip install`, `pre-commit install`, or any other package manager. If the addon's `README.md` documents post-install steps, surface them verbatim:
   > *"This addon's README mentions post-install steps:*
   > > *<quoted README excerpt>*
   > *Run them yourself if you want."*
7. Final message:
   > *"`<name>` installed at `<path>`. Status: `<from-manifest>`. To enable: `/swarm-addons enable <name>`."*

---

## `/swarm-addons remove <name>`

**Goal:** archive the addon (never delete).

Steps:

1. Resolve the addon's path via the loader. If not found: *"`<name>` not installed."*
2. Refuse to remove built-in addons (those under `<skill-dir>/addons/_core/`):
   > *"`<name>` is a built-in addon. To stop using it, run `/swarm-addons disable <name>` instead."*
3. Compute archive path: `~/.claude/swarm-orchestrator/addons/_archive/<YYYY-MM-DD>_<name>/`. If a same-day archive already exists, append `_2`, `_3`, etc.
4. `mv <addon-path> <archive-path>` (Windows: `Move-Item`).
5. Edit `~/.claude/swarm-orchestrator/settings.json` to remove `<name>` from `addons.disabled` if present (cleanup).
6. Reload: `python lib/addons.py list` — addon should be gone.
7. Tell the user:
   > *"`<name>` archived to `<archive-path>`. To restore, move the folder back. Settings cleaned up."*

---

## Error handling rules

- **Never delete user data.** Removal = archive. If archive fails, abort and tell the user manually.
- **Never silently overwrite.** Install / `auto-adapter` synthesis must error if the destination is non-empty.
- **Confirmation gates** for any operation that creates files (`install`, `learn`) or moves files (`remove`). No confirmation needed for read-only ops (`list`, `info`, `doctor`).
- **Parse the loader's `load_errors` list** after every operation that reloads the registry. Surface anything unexpected to the user.
- **Quote stderr verbatim** when reporting failures — don't paraphrase shell errors.

---

## Future commands (not in v1)

- `/swarm-addons update <name>` — `git pull` on a git-installed addon, run doctor on the new version.
- `/swarm-addons publish <name>` — package the addon as a tarball + push to the user's GitHub.
- `/swarm-addons compose <name1> <name2> ...` — compose two addons into a meta-addon (cross-pollinate their rules).
