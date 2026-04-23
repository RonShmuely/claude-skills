# META block contract

Every muscle must end its final text with this exact block. The orchestrator parses it to decide escalation.

## The block

```
---META---
confidence: 0.XX
method: "how you gathered the data"
not_checked: ["thing 1", "thing 2"]
sample_size: N or "exhaustive"
---END META---
```

## Field rules

### `confidence` (required, 0.0–1.0)

How confident are you that this report is accurate? Not how confident you are in the data — how confident you are that **you correctly characterized what's there**.

- `0.95` — exhaustive scan, cross-verified, no ambiguity
- `0.85` — solid work, minor gaps acknowledged in `not_checked`
- `0.75` — sampled rather than exhaustive, best-effort inference
- `0.60` — significant uncertainty, flagged in `not_checked`
- `< 0.50` — should have been escalated before reporting; flag as unverified

**Orchestrator behavior:** if `confidence < 0.7`, re-dispatch this same task on Sonnet. Silent — user sees the escalation arrow in the dashboard, not in chat.

### `method` (required)

One-line description of how you gathered data. Be specific about tools and scope. Examples:

- `"PowerShell EnumerateFiles recursive, no exclusions"`
- `"Glob top-level, sampled 20 subdirs, Read each README.md"`
- `"Grep TODO|FIXME across *.py *.ts *.md, counted matches only"`
- `"Inferred from filenames, no content inspection"` ← **lower confidence**

If your method involves inference or sampling, **say so explicitly**. It's fine; hidden methods are not.

### `not_checked` (required, list of strings)

Things you intentionally or unintentionally didn't verify. Examples:

- `"semantic similarity between images"`
- `"content hashes for dedup (used filenames only)"`
- `"whether the component is actually rendered at runtime"`
- `"Hebrew OCR of scanned PDFs"`
- `"node_modules exclusion may have missed transitive dependencies"`

Empty list `[]` is fine if you genuinely checked everything in scope. Never fake-empty this.

### `sample_size` (required)

How many items did you actually inspect?

- `"exhaustive"` — you touched every item in scope
- `"N of M"` — e.g., `"20 of 3000"` if you sampled
- `N` — e.g., `150` for count of items inspected

If you sampled, **your confidence should be lower** and the method should mention sampling.

## Why this contract matters

Without META, the orchestrator has no way to tell "Haiku exhaustively scanned everything and is 95% sure" from "Haiku looked at 3 files and is guessing." The prose reads the same. The output shape reads the same. Only the explicit confidence + method + sample_size lets the orchestrator catch confident-shallow work.

This is the Hermes Agent pattern: **typed result objects that the orchestrator can validate, transform, and route, preventing the telephone-game degradation.**

## Anti-patterns to reject

If you find yourself writing any of these, go back and fix the muscle prompt:

- `confidence: 1.0` — unreachable, something is always unchecked
- `method: "thorough analysis"` — not a method, that's marketing copy
- `not_checked: []` on every output — almost always a lie; name ≥1 thing
- `sample_size: "many"` — concrete number or `"exhaustive"`, nothing else

The orchestrator should reject these and re-dispatch asking for actual metadata.

## For orchestrators reading this

Parse the META block with this regex pattern (matches across single- or multi-line):

```python
CONFIDENCE_RE = re.compile(r"confidence\s*[:=]\s*([0-9]*\.?[0-9]+)", re.I)
METHOD_RE     = re.compile(r"method\s*[:=]\s*[\"']?([^\"'\n]+)", re.I)
SAMPLE_RE     = re.compile(r"sample_size\s*[:=]\s*[\"']?([^\"'\n]+)", re.I)
NOT_CHECKED_RE = re.compile(r"not_checked\s*[:=]\s*\[([^\]]*)\]", re.I)
```

Normalize confidence: if value > 1, assume 0–10 scale and divide by 10.

See `dashboard/app.py` for the reference parser.
