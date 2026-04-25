# Template — Cost / Token Report

End-of-run summary. Settings-gated by `output.cost_report` (default `off` for repo users).

## Modes

| Mode | When | Format |
|---|---|---|
| `off` | repo default; quiet experience for new users | nothing emitted |
| `summary` | one-line collapsed | `_Swarm: 5.5min · 256K tok · $2.70 · 0 anomalies · 1 cross-link finding_` |
| `full` | personal/dev mode | full block including per-agent breakdown + latency timeline |

## Full report format

```markdown
## Swarm cost report

**Wall clock:** 5.5 min (parallel max — slowest agent dictates)
**Total tokens:** 256K (~206K children + ~50K orchestrator)
**Tool uses:** 95 across all agents
**Cost equivalent (API):** ~$2.70 (Sonnet ×6 + Opus orchestrator)
**Quota burn:** ~6 messages of Max plan budget

### Per-agent breakdown

| Agent | Tier | Model | Tokens | Tool uses | Confidence | Wall clock |
|---|---|---|---|---|---|---|
| A (Lightning) | 3 | Sonnet | 47K | 34 | 0.82 | 5.2 min |
| B (Google Chat) | 3 | Sonnet | 34K | 14 | 0.78 | 2.5 min |
| C (CLI compare) | 3 | Sonnet | 42K | 19 | 0.88 | 3.6 min |
| D (OpenClaw verdict) | 3 | Sonnet | 32K | 13 | 0.81 | 2.6 min |
| E (VPS) | 3 | Sonnet | 15K | 0 | 0.88 | 0.6 min ⚠ |
| F (Latency) | 3 | Sonnet | 36K | 15 | 0.72 | 2.5 min |

### Latency timeline

```
Dispatch → A returned   ████████████████████  5.2 min  ←slowest
Dispatch → B returned   █████████              2.5 min
Dispatch → C returned   ██████████████         3.6 min
Dispatch → D returned   ██████████             2.6 min
Dispatch → E returned   ██                     0.6 min  ← anomaly: 0 tool uses
Dispatch → F returned   █████████              2.5 min
Synthesis (orchestrator)                       1.2 min
```

### Quality gates

- **Anomalies flagged:** 1 (Agent E: 0 tool uses on a research task)
- **Spot-checks performed:** 3 of 3 verified
- **Cross-link conflicts found:** 1 (Agent D vs Agent C — Gemini CLI on Windows)
- **Reviewer triggered:** no (no condition met)
- **Synthesis gate:** all 7 checks passed ✓

### Memory tier I/O

- Knowledge search at dispatch: 5 candidates, top similarity 0.42 (below threshold 0.85 — fresh swarm)
- Operations dir: `memory/operations/2026-04-24-1432-abc123/`
- Promoted to Knowledge: ✓ after synthesis
```

## Summary mode format

```
_Swarm: 5.5min · 256K tok · ~$2.70 · 1 anomaly · 1 cross-link finding · 3/3 spot-checks ✓_
```

One line, italic, collapsed. User can run `/swarm-last-report` (future feature) to expand.

## Data sources

| Field | Source |
|---|---|
| Wall clock | Orchestrator records dispatch + return timestamps |
| Tokens | Sum of agent META `tokens` field (extension to META schema, optional) OR estimated from agent return length × 1.3 |
| Tool uses | Sum of agent META `tools_used` map values |
| Confidence | META block |
| Anomalies | Patch 2 detector output |
| Spot-checks | Patch 3 artifact parse |
| Cross-link | Patch 4 artifact parse |
| Reviewer triggered | Patch 5 dispatch flag |
| Knowledge I/O | `lib/memory.py` log |

## Cost estimation formula

For each agent:
```
cost_usd = (input_tokens × tier.input_rate + output_tokens × tier.output_rate) / 1_000_000
```

Tier rates (April 2026, USD per million tokens, approximate):
| Tier | Input | Output |
|---|---|---|
| Haiku | $0.80 | $4.00 |
| Sonnet | $3.00 | $15.00 |
| Opus | $15.00 | $75.00 |

Sum across all agents + orchestrator. Round to 2 decimals. Note in the report this is API equivalent — actual cost on Max/Pro plans is $0 within quota.

## Where it lives

Written to `memory/operations/<session-id>/cost-report.md` always. Emitted inline at end of synthesis only when `output.cost_report` is `summary` or `full`.

## When the report is wrong

If you suspect the cost report numbers are off:
1. Check `memory/operations/<session-id>/agents/*.json` for raw agent return data
2. Cross-reference token counts with the agent's reported `total_tokens` in the META block
3. Tool counts come from the agent's META `tools_used` field — if that's missing, the agent didn't emit it (legacy prompt or bug)
4. Wall clock is precise (orchestrator timestamps); tokens are ±20% if estimated rather than reported
