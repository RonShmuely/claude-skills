# obsidian-emit

Built-in addon. On every `synthesis_done` event, writes one markdown file per
swarm run into the user's Obsidian vault so swarm history becomes searchable,
link-able, and graph-visible alongside memory and plans.

**Read-only projection.** Source artifacts in `memory/operations/<session-id>/`
are not modified. The vault file is a derivative — safe to delete or edit; the
next run won't overwrite it (filenames are timestamped).

## Output

```
<vault>/Skills/swarm-orchestrator/runs/<YYYY-MM-DDTHHMM>-<recipe-slug>.md
```

Frontmatter (Dataview-compatible):

```yaml
---
recipe: <recipe>
session_id: <session-id>
date: <ISO-8601 UTC>
duration_min: <float>
n_agents: <int>
total_tokens: <int>
gate_result: pass | fail | n/a
agents:
  - { index: 1, model: <model>, description: "...", confidence: 0.91, tokens: 8400 }
  - ...
tags: [swarm-run, <recipe-slug>]
---
```

Body sections (each present only if the corresponding artifact exists):
- `# <task summary>`
- `## Synthesis` — verbatim `synthesis.md`
- `## Cost` — verbatim `cost-report.md`
- `## Per-agent outputs` — bullet list per agent
- `## Spot check` — verbatim `spot-check.md` (if mitigation #4 fired)
- `## Cross-link findings` — verbatim `cross-link.md` (if mitigation #5 fired)
- `## Raw artifacts` — pointer to the operations dir for raw JSON

## Configuration

Vault path resolution order (first hit wins):

1. **User settings** at `~/.claude/swarm-orchestrator/settings.json`:
   ```json
   {
     "addons": {
       "obsidian-emit": {
         "vault_path": "C:/Users/ronsh/Desktop/Obsidian/Ron's Brain"
       }
     }
   }
   ```

2. **Env var** `SWARM_OBSIDIAN_VAULT`.

3. **Auto-detect** — any `~/Desktop/Obsidian/<vault-name>/.obsidian/` directory.
   If multiple, picks the most-recently-modified.

If no vault resolves, the hook logs `obsidian-emit: vault not configured,
skipping` and exits 0 (silent no-op). The orchestrator continues normally —
the addon is fail-safe by design.

## Disabling

Add to your settings to disable globally:

```json
{ "addons": { "disabled": ["obsidian-emit"] } }
```

Or set `status: disabled` in the addon's `addon.yaml`.

## Verification

To verify the addon works without running a real swarm, manually invoke the
hook with a sample payload (see the addon's tests/manual-fire.md if present,
or pipe a JSON payload into `python hooks/synthesis_done.py`).
