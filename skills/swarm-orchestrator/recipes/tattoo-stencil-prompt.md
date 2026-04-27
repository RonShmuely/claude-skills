# Recipe — tattoo-stencil-prompt

Crafts production-quality tattoo stencil prompts for Antigravity's `generate_image` tool (Nano Banana Pro 2). The recipe runs a single Opus muscle (no fan-out) and returns structured JSON for an upstream orchestrator to consume — designed to be invoked from a Gemini-3.1 Antigravity slot via `run_command "claude -p"` shell-out.

## Metadata

```yaml
name: tattoo-stencil-prompt
version: 1.0
safety_tag: M                           # Drives paid image generation; bad prompts waste money + time
fan_out: 1                              # Single muscle, no parallelism — pure synthesis
muscle_tier: opus                       # Required — prompt quality is the load-bearing variable
muscle_count: 1
template: templates/tattoo-stencil-prompt.md
estimated_wall_clock_s: 45              # Opus crafting 3-6 detailed prompts in JSON
estimated_cost_usd: 0.30
output_format: json                     # Strict JSON to stdout, parseable by upstream
upstream_consumers:
  - antigravity-workflow:tattoo-stencil  # ~/.gemini/antigravity/workflows/tattoo-stencil.md
  - claude-code:direct                   # If invoked from Claude Code chat directly
```

## Inputs (passed by upstream into the template)

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `subject` | string | yes | — | What to tattoo (e.g. "wolf", "אריה", "mountain range") |
| `style` | enum | no | `fineline` | One of: fineline, traditional, neo-traditional, blackwork, dotwork, realism, geometric, ornamental, tribal, Japanese, linework |
| `placement` | enum | no | `forearm` | One of: forearm, calf, thigh, back, chest, shoulder, ribs, neck, hand, ankle, wrist |
| `count` | int | no | 3 | Number of variations (1-6) |
| `aspect_ratio` | enum | no | `1:1` | One of: 1:1, 3:4, 9:16, 4:3, 16:9 |
| `text_in_image` | string | no | `""` | Literal text to render in the image (name, date, etc.) |
| `text_script` | enum | no | `none` | One of: he, latin, mixed, none |
| `language` | enum | no | `en` | User's input language (he, en, mixed) — affects upstream messaging only |
| `slug` | string | yes | — | Kebab-case ID for downstream filename use |

## Output schema (strict JSON to stdout)

```json
{
  "subject": "<echo>",
  "style": "<echo>",
  "placement": "<echo>",
  "count": <echo>,
  "aspect_ratio": "<echo>",
  "text_in_image": "<echo>",
  "language": "<echo>",
  "prompts": [
    "<full prompt 1, English, 80-150 words, embeds all applicable rules>",
    "<full prompt 2>",
    "..."
  ],
  "negative_space_notes": "<one paragraph on skin curvature handling at the placement>",
  "post_processing_hints": {
    "mirror_for_thermal_transfer": true,
    "binarize_threshold": 128,
    "expected_output_format": "JPEG-with-.png-extension (Nano Banana Pro 2 quirk)"
  }
}
```

Followed by the standard META block with `confidence`, `method`, `not_checked`, `sample_size`, `tools_used`, `artifacts: []`.

## Tool-use floor (anomaly check per Mitigation #6)

This is **pure synthesis from in-context expertise**. The expected `tools_used` is all zeros:

```yaml
tools_used_floor:
  Read: 0
  Grep: 0
  Glob: 0
  WebSearch: 0
  WebFetch: 0
  Bash: 0
```

If the muscle returns with any tool count > 0, that's an anomaly — the muscle should not need to look anything up. Re-dispatch on Opus with the stricter "use only in-context expertise" preamble.

## Validation rules (orchestrator runs after muscle returns)

1. Parse stdout as JSON. Malformed → `BLOCKED: invalid JSON from tattoo-stencil-prompt muscle`
2. `prompts.length === count`. Mismatch → `BLOCKED: muscle returned N prompts, expected M`
3. Each prompt is 50–250 words. Outside range → flag for review (likely too sparse / too verbose)
4. Each prompt contains the literal phrase "black ink" or "black line" (universal stencil rule check). Missing → `BLOCKED: muscle dropped universal stencil rules`
5. If `style === "dotwork"`, prompts may mention dot density. Otherwise, no "shading" or "gradient" or "color" allowed in prompt text. Violation → flag for review.
6. META `confidence` ≥ 0.7 → proceed. < 0.7 → re-dispatch on Opus with stricter preamble. < 0.5 after re-dispatch → `BLOCKED: muscle returned low-confidence output`.

## Reviewer loop trigger (Mitigation #5)

Default `[M]` — no reviewer unless one of these dynamic triggers fires:
- Confidence < 0.7 after re-dispatch
- Tool-use anomaly (any tool count > 0)
- Validation rule 5 fails (style/content rule violation)

If reviewer fires: dispatch one Sonnet reviewer with the full muscle output + the recipe template, ask "do these N prompts comply with universal + style-specific rules? Flag any violations."

## How to invoke

**From Claude Code chat (direct):**
> "Run the tattoo-stencil-prompt recipe with subject=wolf, style=fineline, placement=forearm, count=3, slug=wolf-forearm"

**From Antigravity Gemini-3.1 slot (production):**
The Gemini workflow at `~/.gemini/antigravity/workflows/tattoo-stencil.md` invokes via `run_command "claude -p ..."` with the structured prompt that loads this recipe. See that file for the exact dispatch shell-out.

**Standalone (any other runtime):**
Any orchestrator that can shell out to `claude -p` and parse JSON from stdout can invoke this recipe. Pass the inputs as a structured spec in the prompt body; the headless Claude reads `templates/tattoo-stencil-prompt.md` and produces the output.
