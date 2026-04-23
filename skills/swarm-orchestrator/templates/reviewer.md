# Template — Reviewer Loop (High-Stakes Only)

After an `[H]` swarm completes and spot-checks are done, dispatch an adversarial
reviewer. The reviewer's job is **not** to redo the work — it's to find what
the swarm missed, what looks shallow, and what nuance got lost in typed-output
compression.

## When to use

Only for `[H]` safety swarms — decisions with real money, customer, or safety
consequences. On `[M]` swarms, escalation + spot-check is enough. Reviewer
adds ~$0.20–0.50 and ~2 min.

## Model choice

- **Sonnet reviewer** for most `[H]` cases
- **Opus reviewer** when:
  - The decision costs > $1000 if wrong
  - The domain has high ambiguity (medical, legal, safety-critical engineering)
  - The swarm's synthesis will be quoted verbatim to a third party

## Dispatch prompt

```
[H] Review swarm output — {{SWARM_TOPIC}}

You are a reviewer. A swarm of {{N}} muscle agents just audited {{SCOPE}}.
Your job is NOT to redo their work — it's to find what they missed, what
looks shallow, and what nuance was lost in typed-output compression.

## The swarm's reports

{{INLINE_REPORT_A}}

---

{{INLINE_REPORT_B}}

---

{{INLINE_REPORT_C}}

---

[... all muscle reports inline ...]

## Sample these raw files the muscles didn't read deeply

{{RAW_FILE_1}}
{{RAW_FILE_2}}
{{RAW_FILE_3}}
{{RAW_FILE_4}}

(Read each with the Read tool. Compare against what the muscle reports claimed.)

## Produce

1. **Claims you doubt** — specific claim + your reasoning for doubt
2. **Things the muscles didn't notice but should have** — be concrete, cite files
3. **Cross-section patterns** only visible when seeing everything at once
4. **Your revised version of the top 3 findings** — replace the swarm's top 3
   with your own if you disagree; explain the delta

Be adversarial. A polite review is a useless review. Default to skepticism.
If a muscle's confidence is above 0.9, that's suspicious — challenge it.

## Output format

```
# Reviewer Critique — {{SWARM_TOPIC}}

## Claims I doubt
1. [specific claim] — [reasoning] — [severity: low/med/high]
...

## Gaps the swarm missed
1. [what was missed] — [file/evidence] — [why it matters]
...

## Cross-section patterns
1. [pattern] — [which sections surface it when combined]
...

## Revised top 3 findings
1. [original finding] → [revised version] — [why the swarm had it wrong]
...

## Net recommendation
[Should the user act on the swarm's output as-is, with caveats, or re-run parts?]
```

At the end, emit:

---META---
confidence: 0.XX   # how confident you are in your critique
method: "read N muscle reports, sampled M raw files, cross-referenced claims"
not_checked: [...]
sample_size: exhaustive over reports, N raw files
---END META---
```

## Fields to fill

- `{{SWARM_TOPIC}}` — what the swarm was about ("MachineGuides audit", "Code review of auth PR")
- `{{N}}` — number of muscle agents in the swarm
- `{{SCOPE}}` — what the swarm covered
- `{{INLINE_REPORT_A|B|C...}}` — the full final text of each muscle's report, pasted inline
- `{{RAW_FILE_1..4}}` — 3–5 paths the muscles read in their trace but that the orchestrator never saw in full. Pick the biggest / most central ones. Example:
  ```
  - C:\path\to\config.json (Section C Haiku read this, you should too)
  - C:\path\to\main.py (Section A grepped it, you should read it)
  ```

## What the reviewer should NOT do

- **Redo the inventory.** The muscles counted files; don't recount.
- **Validate every claim.** Pick the most consequential to challenge, not all of them.
- **Be polite.** If something looks shallow, say so. Ambiguous critiques are useless.
- **Invent claims to challenge.** If the swarm's work is solid, say "no significant gaps found" and list what you checked.

## Integration with synthesis

After the reviewer returns, the orchestrator:

1. Reads the reviewer's critique
2. Updates the synthesis — anything the reviewer flagged gets prefixed "Reviewer flagged:"
3. If the reviewer revised top findings, use the revised versions
4. If the reviewer says "re-run parts", the orchestrator dispatches follow-up muscles before presenting to user

## Cost and time

| Reviewer model | Added cost | Added time |
|---|---|---|
| Sonnet | ~$0.15–0.30 | ~1–2 min |
| Opus | ~$0.40–0.80 | ~2–3 min |

On a $1.80 baseline swarm, Sonnet reviewer takes you to ~$2.10 / 9 min. Opus
reviewer takes you to ~$2.50 / 10 min. For an `[H]` swarm, this premium is
trivial vs the cost of acting on confident-shallow output.

## Example trigger scenarios

- Merge gate for production code → Opus reviewer
- Choice between two expensive parts for a machine → Sonnet reviewer
- Architecture decision with 6-month+ commitment → Opus reviewer
- Customer-facing diagnosis → Opus reviewer
- Internal cleanup / refactor decisions → Sonnet reviewer (often skip to `[M]`)
