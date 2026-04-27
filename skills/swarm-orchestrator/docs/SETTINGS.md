# Settings — How They Work

Swarm-orchestrator is configurable. Every behavior knob has a default in `defaults.json` (committed to repo), and every user can override via their personal `~/.claude/swarm-orchestrator/settings.json`.

## Resolution order (highest priority wins)

1. **`~/.claude/swarm-orchestrator/settings.json`** — user-level override. NOT in repo. Per-user, per-machine.
2. **`<skill-dir>/settings.local.json`** — skill-local override. Also gitignored. Useful for testing without affecting `defaults.json`.
3. **`<skill-dir>/defaults.json`** — repo defaults. Everyone starts here.

The orchestrator merges these JSON objects deep — keys present in higher-priority files win, missing keys fall through.

## Editing settings via `/swarm-config`

> **How `/swarm-config` actually works:** it is **not** a registered Claude Code slash command (there is no `commands/swarm-config.md` shim). It is an **intent trigger** the skill recognizes. When the swarm-orchestrator skill is loaded into the session and you type `/swarm-config` (or natural-language equivalents like "open swarm config", "edit swarm settings"), the orchestrator follows the recipe below from `SKILL.md`. If the skill is not active in the session, `/swarm-config` will be treated as unknown input — load the skill first (it auto-loads on swarm-related triggers, or you can ask Claude to "use swarm-orchestrator").
>
> Direct alternative: edit `~/.claude/swarm-orchestrator/settings.json` with any text editor. The orchestrator reads it on every dispatch.

The recommended interactive flow (when triggered):

1. Reads the current effective settings (merges all 3 layers)
2. Renders them as a markdown view annotated with which layer each value came from
3. Calls `EnterPlanMode` so you can edit in the same plan-mode UI you use for code changes
4. On approve → parses your edits back to JSON → writes to `~/.claude/swarm-orchestrator/settings.json`
5. On reject → no change

## Knob reference

### Output

| Knob | Type | Default | Effect |
|---|---|---|---|
| `output.cost_report` | `off` \| `summary` \| `full` | `off` | Whether to emit a cost block at end of run. `full` includes per-agent breakdown + latency timeline |
| `output.output_format` | `chat` \| `html` \| `both` | `chat` | Where final synthesis goes |
| `output.verbose_meta` | bool | `false` | Show raw META blocks to user (debugging) |
| `output.synthesis_style` | `punchy` \| `thorough` | `punchy` | Brevity preference for the merged report |

### Discipline

| Knob | Type | Default | Effect |
|---|---|---|---|
| `discipline.spot_check_enforce` | bool | `true` | Force the spot-check artifact for `[M]`/`[H]` swarms even if all confidences are high |
| `discipline.spot_check_sample_size` | int | `3` | How many claims to verify post-swarm |
| `discipline.cross_link_enabled` | bool | `true` | Enable cross-pollination pass for swarms with N >= `cross_link_min_agents` |
| `discipline.cross_link_min_agents` | int | `4` | Minimum agent count to trigger cross-link review |
| `discipline.anomaly_detection` | `off` \| `warn` \| `block` | `warn` | What to do when an agent's `tools_used` violates the recipe floor. `block` auto-reescalates |
| `discipline.reescalation_threshold` | float (0–1) | `0.7` | Confidence below which an agent is silently re-dispatched on a higher tier |
| `discipline.low_confidence_flag_threshold` | float (0–1) | `0.5` | Confidence below which findings are flagged unverified in synthesis |
| `discipline.reviewer_dynamic_triggers.*` | bool | all `true` | Toggles for the 4 dynamic reviewer triggers (Patch 5) |
| `discipline.confidence_variance_threshold` | float | `0.15` | Confidence spread across muscles above which reviewer fires |

### Models

| Knob | Type | Default | Effect |
|---|---|---|---|
| `models.default_research_tier` | `haiku` \| `sonnet` \| `opus` | `sonnet` | Default tier for research-shaped tasks |
| `models.default_audit_tier` | `haiku` \| `sonnet` \| `opus` | `haiku` | Default tier for audit-shaped tasks |
| `models.force_opus_for` | list of strings | `[]` | Task type names that always get Opus regardless of tier defaults |
| `models.temperature.haiku/sonnet/opus` | float | `0.0` | Temperature hint passed to dispatch prompt (advisory — see caveat below) |

#### Temperature caveat

The Agent dispatch tool does not accept `temperature` directly. Settings here become **advisory** — the orchestrator includes them in dispatch prompts as natural-language hints (e.g., "be exploratory" for higher temps). True API-level temperature control requires direct API SDK calls instead of subagent dispatch. v2 may add a settings-aware dispatch wrapper.

### Quota / safety

| Knob | Type | Default | Effect |
|---|---|---|---|
| `quota.warnings_enabled` | bool | `true` | Warn the user if a swarm would consume >25% of remaining 5h quota |
| `quota.max_parallel_agents` | int | `8` | Cap on simultaneous in-flight agents |

### Memory

| Knob | Type | Default | Effect |
|---|---|---|---|
| `memory.enabled` | bool | `true` | Master switch for the 3-tier memory system |
| `memory.search_on_dispatch` | bool | `true` | Step 0.5: query Knowledge for similar past runs before dispatch |
| `memory.similarity_threshold` | float (0–1) | `0.85` | Above this, surface past run as "we've done this before" |
| `memory.operations.ttl_days` | int | `7` | Auto-cleanup window for Operations dirs |
| `memory.knowledge.enable_vectors` | bool | `false` | Use sqlite-vec extension for semantic search (FTS5 alone is plenty for most uses) |
| `memory.knowledge.embedding_model` | string | `all-MiniLM-L6-v2` | sentence-transformers model name (CPU-friendly, ~80MB) |
| `memory.knowledge.fts_weight` | float | `0.4` | Weight on full-text BM25 score in hybrid ranking |
| `memory.knowledge.vector_weight` | float | `0.6` | Weight on vector cosine score in hybrid ranking |

### Recipe floors

`recipe_floors` is a per-recipe object specifying minimum expected tool counts. Used by anomaly detection (Patch 2). Override per-recipe in your settings file:

```json
"recipe_floors": {
  "research-brief": { "WebSearch": 6, "WebFetch": 3 }
}
```

If an agent dispatched under recipe `research-brief` returns with `tools_used.WebSearch < 6`, anomaly detection fires per the `anomaly_detection` setting.

## Override semantics — partial vs full

Your override file does NOT need to contain every key. Only specify what you want different from defaults. Example minimal override:

```json
{
  "output": { "cost_report": "full" },
  "discipline": { "anomaly_detection": "block" }
}
```

Everything else falls through to `defaults.json`.

## Validating your settings

`/swarm-config` validates on save. Invalid types (e.g., `cost_report: 5`) or unknown keys are rejected with a specific error message and the file is not written.

## Tips

- **Want fewer interruptions?** Set `quota.warnings_enabled: false`.
- **Debugging an agent?** Set `output.verbose_meta: true` and see the raw META blocks.
- **Working on a privacy-sensitive task?** Set `memory.enabled: false` for the run (or comment out via `/swarm-config`).
- **Sharing your config with a teammate?** Hand them the JSON; they paste into their own `~/.claude/swarm-orchestrator/settings.json`.
