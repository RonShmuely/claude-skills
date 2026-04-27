# Model Tiers — Decision Table

## The five tiers

| Tier | Model | Rough cost (in/out per M tokens) | Role |
|---|---|---|---|
| 1 | **Opus 4.7** (orchestrator) | $15 / $75 | Brain — decomposition, synthesis, user-facing judgment |
| 2 | **Opus 4.7** (heavy muscle) | $15 / $75 | High-stakes decisions, architecture, complex reviews |
| 3 | **Sonnet 4.6** | $3 / $15 | Specialist — reasoning, browser, code, multi-step work |
| 4 | **Haiku 4.5** | $1 / $5 | Swarm — inventories, greps, counts, pattern matching |
| 5 | **Ollama local** (optional) | $0 / $0 | Privacy-sensitive, offline, bulk preprocessing |

## Decision table

| Task shape | Tier | Example |
|---|---|---|
| Count files / sum sizes / list extensions | **Haiku** | Folder inventory |
| Grep patterns, find TODOs / dead code | **Haiku** | Static code audit |
| Schema validation, typed extraction | **Haiku** | Parse N JSON files, find drift |
| Pattern matching on structured data | **Haiku** | Find duplicates by filename |
| Summarize a single doc (<10K tokens) | **Haiku** | Quick manual lookup |
| Multi-step reasoning over noisy text | **Sonnet** | Reason over Hebrew service manuals |
| Browser automation | **Sonnet** | Google Photos verification, scraping |
| Code generation with real complexity | **Sonnet** | Build a component from spec |
| Review / critique of written content | **Sonnet** | PR review, doc review |
| Refactor with judgment calls | **Sonnet** | Modernize legacy code |
| Architecture / "should we do X" | **Opus** | Design decisions |
| Diagnosis with real uncertainty | **Opus** | Ambiguous fault, stakes |
| PR review for production-critical code | **Opus** | Final gate |
| Cross-cutting synthesis of 5+ sources | **Opus** | Research position paper |

## The golden decision rule

> **If the task fits in a paragraph and returns structured data → Haiku.  
> If it needs multi-step judgment or runs > 1 minute → Sonnet.  
> If it's a decision you'd regret getting wrong → Opus.**

## When to escalate (default up a tier)

Escalate the tier **before dispatching** if:

1. The task contains the word "decide", "recommend", "should", "best", or any question the human genuinely cares about the answer to
2. The output will drive a concrete action (cleanup, purchase, diagnosis)
3. The input is ambiguous — Hebrew + English mixed, handwritten notes, technical jargon outside the model's strength
4. The task requires synthesis across 3+ sources
5. You can't specify a structured output shape in 2 sentences

**When in doubt, go Sonnet.** The cost delta between Haiku ($0.03) and Sonnet ($0.20) is trivial compared to the cost of Haiku returning confident-shallow output.

## When to use Ollama (Tier 5, optional)

Ollama runs locally on the user's GPU. Benefits: $0/token, privacy-preserved, offline-capable, unlimited rate.

Use Ollama for:

- **Privacy-sensitive bulk work** — classify customer PDFs, tag internal photos, index proprietary manuals
- **Offline field use** — mobile technician without internet needs quick lookup
- **Preprocessing before Claude** — extract structured fields from 4 GB of Hebrew manuals, send only extracts up to Sonnet
- **Always-on watchers** — monitor Downloads folder, auto-tag new files 24/7
- **Embeddings for RAG** — embed corpus locally, serve retrieval

Do NOT use Ollama for:

- Multi-step tool-use agentic workflows (weaker than Haiku)
- Long-context work above ~128K tokens
- Structured JSON output reliability (Claude still wins)
- Anything requiring Claude-level reasoning quality

Integration: point dispatcher at `http://localhost:11434/api/generate` when task is tagged `local`, `private`, `offline`, `embed`, or `classify`. Not wired into this skill by default — see `docs/RECIPES.md` for the integration sketch.

## Cost examples (real)

Based on measured workloads from the reference project:

| Workload | Tier used | Cost | Wall time |
|---|---|---|---|
| 1 folder inventory (29K files) | Haiku | ~$0.03 | ~2 min |
| 5-section parallel audit | 5× Haiku + Opus sync | ~$1.80 | ~7 min |
| Browser verification (Google Photos) | Sonnet | ~$0.20 | ~10 min |
| Disk cleanup with judgment calls | Opus | ~$0.80 | ~6 min |
| Same 5-section audit on single Opus 1M Extra High | Opus (all of it) | ~$50–100 | ~15 min |

## Heterogeneous teams

For big tasks, you can mix tiers in sequence on the same subject:

```
 Haiku scout → Sonnet analyst → Opus judge
 (raw data)    (reasoning)      (final call)
```

Example: machine diagnosis.

1. **Haiku** reads the service PDF, extracts fault codes + FMI + candidate causes in structured form
2. **Sonnet** reasons over the scout's structured extract + user's symptom description, proposes top 3 hypotheses ranked
3. **Opus** reads both outputs + a sample of the raw PDF, makes the final call

Each tier sees only what it needs. Costs scale with decision weight. Output quality is Opus-tier because Opus actually made the call — but you paid Haiku + Sonnet + Opus instead of Opus × 3.

## The trap to avoid

**Never** use Haiku for a task that has one of:

- The word "should", "recommend", "best" in the ask
- A decision that affects real money / time / relationships
- Output that will be quoted directly to a human

Haiku will produce something. It will look fine. It may even be right. But the probability distribution of its output quality is wider than you want, and its failures are silent. Use Sonnet minimum for anything you'd act on.
