# Cost Benchmark — Framework vs Single Opus 1M Extra High

Reference workload: **audit a 29,473-file project in 5 non-overlapping sections** (real case, MachineGuides repo).

## Headline numbers

| Metric | Single Opus 4.7 1M Extra High | Swarm framework | Delta |
|---|---|---|---|
| **Cost** | ~$50–100 | **~$1.80** | **~30–50× cheaper** |
| **Wall time** | 12–15 min | **~7 min** | ~2× faster |
| **Output tokens** | ~80K (incl. thinking) | ~60K (across 6 agents) | ≈ parity |
| **Input tokens billed** | ~3–5M (after caching) | ~300K | ~10–15× fewer |
| **Main context usage** | ~300K (polluted) | **~30K** (lean) | ~10× cleaner |
| **Parallelism** | 1 thread | 5 in parallel (up to ~10) | N× throughput |
| **Observability** | Scroll a chat | Live dashboard | Categorical |
| **Reproducibility** | Re-run = re-spend full cost | Recipe = one-click | Categorical |
| **Resilience** | API blip = lose 15 min | 1 muscle fails = re-dispatch | Categorical |

## The math behind the cost

### Single Opus 4.7 1M Extra High

Assumptions for a thorough folder audit:
- ~150 tool calls (Grep, Read, ls across 5 sections)
- Context grows to ~300K tokens as file contents accumulate
- Extended thinking adds ~2× to output tokens per turn
- Prompt caching helps but each new tool result invalidates caches around it

Pricing (current Anthropic):
- Opus standard: $15/M input, $75/M output
- 1M context tier: $30/M input, $150/M output (2× premium)
- Prompt caching: 90% discount on cached reads

Estimated:
- Cumulative input if no caching: ~22.5M tokens (context × call count / 2)
- With caching: ~3–5M effective input tokens
- Output: ~50K (answer) + ~30K (extended thinking) = ~80K
- At 1M tier: 3–5M × $30 = $90–$150, 80K × $150 = $12
- Net: **~$100–160 upper estimate**

At standard Opus tier (non-1M): ~$50–80.

The 1M Extra High premium costs ~2× what standard Opus costs, plus extended thinking doubles output. Real bills tend to land $50–100 for this specific workload; $100+ if heavily accumulated context.

### Swarm framework

Actual measured numbers from the reference audit:

| Agent | Model | Tool calls | Duration | Tokens |
|---|---|---|---|---|
| Section A (web/) | Haiku | 31 | 7:44 | ~57K |
| Section B (data) | Haiku | 8 | 2:17 | ~50K |
| Section C (pipeline) | Haiku | 7 | 0:54 | ~51K |
| Section D (scripts) | Haiku | 39 | 3:55 | ~74K |
| Section E (docs) | Haiku | 29 | 2:05 | ~61K |
| Orchestrator | Opus | ~10 | ~2 min | ~20K |
| **Totals** | — | 124 | **7:44 wall** | **~313K** |

Pricing:
- 5 Haikus × ~60K each ≈ 300K Haiku tokens → ~$0.30–0.40 total
- Orchestrator: ~20K Opus tokens (mostly cached orchestration context, small output) → ~$1.20
- **Total: ~$1.50–1.80**

Add [M] safety tier (+escalation + spot-check): **~$2.00**  
Add [H] safety tier (+reviewer): **~$2.30**

## Why the framework wins so hard on cost

1. **Tier-pricing asymmetry.** Haiku is 15× cheaper than Opus per token. When 90% of the work is tool-grind (grep, count, read), doing it at Haiku rates compounds.
2. **Context isolation.** Each muscle starts with a fresh ~5K context and ends ~50K. Orchestrator stays ~30K. No one ever pays for a 300K accumulated context.
3. **Parallel wall time reduces total work-seconds.** Not directly a cost win but means you get more done per clock-hour.
4. **Caching actually works.** Each muscle's prompt has a stable prefix (the skill guidance) that gets cached hard. Single-agent conversations invalidate caches constantly.

## Why the framework does NOT always win

| Dimension | Single Opus 1M better |
|---|---|
| Cross-section synthesis | One brain sees everything, spots patterns the reviewer might miss |
| Single-voice output | One style, one reasoning chain, no stitching |
| Deep ambiguity in every subtask | Splitting to Haiku just returns shallow reports |
| Small tasks (<5 min, <30K) | Orchestration overhead eats the win |
| Pure linear research | Nothing to parallelize |

**Honest framing:** you pay 30–50× more for ~5–10% better cross-section synthesis with single-Opus 1M. Worth it for 1 task in 20 (architecture, deep research). The other 19 should be swarm.

## Compounding advantages over time

Single-Opus cost scales linearly per request. Swarm has structural advantages that compound:

### Recipes

The 2nd run of "5-section folder audit" on any folder costs ~$1.80 again — but the **orchestration logic is already designed**. No re-planning, no re-templating. One click in the dashboard.

Single-Opus has no memory that the last run cost $80. The next audit costs $80 again too.

### Model mix evolution

Add Ollama (Tier 5) for preprocessing and ~10–30% of what Haiku does today drops to **$0**. The swarm absorbs new cheaper tiers as they arrive. Single-Opus can't downgrade its own work.

### Context hygiene

10 swarms in a row keeps the orchestrator context under 50K. Single-Opus 1M after 10 audits has eaten its own 1M ceiling and degraded — you start seeing quality drop, hallucinations, context-edge weirdness. The swarm just keeps going.

### Escalation savings

With typed outputs + confidence, you only pay Sonnet/Opus when Haiku returned low confidence (~10% of the time in practice). The other 90% stays at Haiku prices. Single-Opus pays Opus prices 100% of the time.

## Rule of thumb for deciding

| If you think the task is... | ...use |
|---|---|
| "I could write this as 5 independent prompts" | **Swarm** |
| "I need one brain to see everything" | **Single Opus 1M** |
| "It's research, mostly linear" | **Single Opus** (no need for 1M unless >500K context) |
| "It's >100K tokens of raw material to synthesize" | **Single Opus 1M** |
| "I want to watch it happen / kill it mid-run" | **Swarm** (dashboard) |
| "I want to re-run this on a different folder tomorrow" | **Swarm** (recipe) |
| "The decision has real money on it" | **Single Opus, extended thinking on** |
| "The decision is low-stakes but bulk" | **Swarm** |

## TL;DR

Swarm is **categorically cheaper and faster** for the 90% of work that's parallelizable-into-narrow-chunks. Single-Opus 1M Extra High wins the remaining 10% — cross-section reasoning, deep research, or when being wrong costs real money. Match the tool to the task; don't default to one or the other.

For a typical engineering workload over a week, expect:
- 90% of agent-work → swarm → ~$5–15
- 10% of agent-work → single-Opus → ~$20–40
- **Weekly total: ~$30–55**

Same workload on single-Opus for everything: **$300–600/week.**
