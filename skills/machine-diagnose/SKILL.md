---
name: machine-diagnose
description: >
  Diagnose vehicle and heavy machine faults using NotebookLM technical notebooks.
  Automatically identifies the right machine notebook, queries it with the symptom,
  and delivers a structured diagnosis in Hebrew. Use this skill whenever the user
  describes a machine problem, fault, symptom, error code, or malfunction on any
  of their vehicles or equipment — including Wirtgen milling machines (W50Ri, W200i),
  Bobcat/Gehl skid loaders, Bomag rollers, Volvo trucks, or any machine they have
  a NotebookLM notebook for. Also triggers when the user mentions a fault code,
  blown fuse, hydraulic issue, sensor failure, or says things like "the machine
  does X when I press Y", "diagnose", "what's wrong with", "won't start",
  "error on display", or any Hebrew equivalent like "תקלה", "אבחון", "לא עובד",
  "פיוז", "חיישן". Even if the user just names a machine and a symptom with no
  other context, use this skill.
---

# Machine Diagnose

Diagnose faults on the user's vehicles and heavy equipment by querying their
NotebookLM technical notebooks. The user describes a symptom; you find the right
notebook, run the diagnosis, and deliver actionable repair steps — all in Hebrew.

## How It Works

The user's fleet documentation lives in NotebookLM notebooks. Each notebook
contains service manuals, fault code tables, wiring diagrams, fuse maps, and
field notes for a specific machine or machine family. Your job is to be the
bridge between the user's plain-language symptom description and the deep
technical data inside those notebooks.

## Core Operating Rules

These rules apply to every machine-diagnose session:

### Rule 1 — NotebookLM: MCP first, CLI only when asked

Always use the NotebookLM **MCP tools** (`notebook_list`, `notebook_query`,
`source_list`, etc.) for interacting with notebooks. Do NOT shell out to the
`notebooklm` CLI via Bash unless the user explicitly asks for CLI
(e.g., "use the CLI", "run notebooklm in bash", "run it from the command line").
The MCP tools are faster, return structured data, and don't pollute the
conversation with shell output.

### Rule 2 — Build diagnostic guides with real images from local PDFs

The user keeps original service PDFs locally at:
`C:\Users\ronsh\Desktop\MachineGuides\<MACHINE>\` (e.g. `W50RI`, `W200IF`, `W50DC`).
These folders contain the authoritative manuals, parts catalogs, electric
schematics, and hand-annotated fuse diagrams — including Hebrew-translated
sensor reference pages. **Always prefer these over web searches or NotebookLM
generation for imagery.**

Workflow when a diagnosis warrants visual aids (or when asked for an HTML guide):

1. **Check local PDFs first** — list `C:\Users\ronsh\Desktop\MachineGuides\<MACHINE>\`
   for relevant files (sensor references, schematics, parts catalog, fuse maps).
2. **Extract with the existing tooling** —
   `C:\Users\ronsh\Desktop\MachineGuides\extract_pdf.py` extracts embedded images
   and renders pages. Output goes to `MachineGuides/extracted/<name>/` with
   `images/` and `pages/` subfolders.
3. **Crop to the specific component** — when a page contains a table of multiple
   sensors/parts, crop just the relevant row. `crop_sensors.py` is the reference
   implementation for the W50Ri Hebrew sensor reference. For a new PDF, write a
   similar crop script that saves to `MachineGuides/images/<MACHINE>/<category>/`
   with descriptive names including the SPN/fault code where applicable
   (e.g. `sensor_7_fuel_low_pressure_SPN94.png`).
4. **Embed in the HTML guide** — use relative paths from the guide's location to
   the image library. If the guide sits on the Desktop and images live in
   `MachineGuides/images/...`, reference them as
   `MachineGuides/images/<MACHINE>/sensors/<file>.png`.
5. **Wrap images in a `<figure>` with a caption** — include the source
   ("מתוך ספר האימון של Wirtgen" / "מתוך קטלוג חלקים") and what the image shows.
   Use the `.img-figure` and `.img-side-by-side` CSS patterns already established
   in existing guides on the Desktop for consistency.

If no suitable local image exists, fall back to: (a) NotebookLM deep research
in a dedicated `ImgLibrary` notebook, then (b) web search. Never embed images
you haven't actually verified you can display.

### Rule 3 — Show full reasoning when asked

If the user asks to see your thinking, reasoning, or "how you got there"
(Hebrew: "תראה לי איך חשבת", "מה עבר לך בראש", "הסבר את תהליך החשיבה"), expose
the full reasoning trace before presenting the answer: the candidate hypotheses
you considered, which notebook passages you weighted highest, which FMI
branches you eliminated and why, what ambiguity you had to resolve, and any
assumptions you made. Default behavior (when NOT asked) stays the same: short,
practical answer — no meta-commentary.

## Step 1 — Identify the Machine

Parse the user's message for machine identifiers. Look for:

- Explicit model names: W50Ri, W200i, Bobcat, Bomag, Volvo FH, Gehl, Mustang
- Hebrew names: מקרצפת קטנה (W50Ri), מקרצפת גדולה (W200i), בובקט, בומג, וולוו
- Contextual clues: "the small milling machine", "the roller", "the truck", "the skid loader"
- If ambiguous, ask the user which machine they mean — don't guess

## Step 2 — Find the Notebook

Call `notebook_list` to get all notebooks. Match the machine to the right notebook
using title keywords. The user's notebooks follow a naming pattern that includes
the machine name, so match on that.

Known notebook patterns (these may change — always verify against the live list):
- W50Ri / מקרצפת קטנה → look for "W50Ri" in title
- W200i / מקרצפת גדולה → look for "W200i" in title
- Bobcat / Gehl / בובקט → look for "Bobcat" or "Gehl" in title
- Bomag / בומג → look for "Bomag" in title
- Volvo / וולוו → look for "Volvo" in title

Also check for supplementary notebooks (e.g., "Metals & Parts" variants) that
may contain additional technical data. If multiple notebooks match (e.g., a main
diagnostic notebook + a parts notebook), query the main one first — it usually
has the fault codes, wiring, and procedures.

If no notebook matches, tell the user you couldn't find a notebook for that
machine and ask if they want to create one or point you to the right one.

## Step 3 — Query for Diagnosis

Send a comprehensive diagnostic query to `notebook_query`. The query should
extract maximum useful information in a single call. Structure your query like:

```
The [machine description] has this problem: [user's symptom].
Diagnose this issue. Include:
1. All possible causes, ranked by likelihood
2. Relevant fault codes and their meanings
3. Which fuses, sensors, solenoid valves, or components are involved
4. Step-by-step diagnosis procedure
5. Cable routing — which cables to inspect and where they run
6. Emergency overrides or workarounds to keep working
7. Safety interlocks that might block the function
8. Any relevant wiring or fuse map information
```

If the first query doesn't return enough detail on a specific aspect (e.g., you
got the fault codes but not the fuse map), send follow-up queries to fill in
the gaps. It's better to make 2-3 targeted queries than to give the user an
incomplete diagnosis.

If you have an active `conversation_id` from a previous query to the same
notebook (within the same session), pass it to maintain context for follow-ups.

## Step 4 — Deliver the Diagnosis (Chat)

Present the diagnosis directly in the conversation. Structure it clearly:

1. **תיאור הבעיה** — Restate the problem and root cause
2. **גורמים אפשריים** — Ranked list of possible causes with fault codes
3. **שלבי אבחון** — Step-by-step what to check and in what order
4. **כבלים לבדיקה** — Which cables to trace, where they run, what to look for
5. **פתרונות חירום** — Emergency overrides to keep working
6. **נעילות בטיחות** — Safety interlocks that might block the function

Use Hebrew throughout. Keep it practical — this person is standing next to the
machine with tools in hand.

## Step 5 — HTML Guide (On Request)

If the user asks for a file, document, guide, or says something like "תכין לי
קובץ" / "תעשה לי מדריך" / "save this" / "make a file", create a comprehensive
HTML diagnostic guide.

The HTML file should be:
- **RTL Hebrew** (`dir="rtl"` on the html element)
- **Dark theme** — easy to read on a phone in sunlight or a dusty cab
- **Mobile-responsive** — the user is probably on their phone next to the machine
- **Self-contained** — all CSS inline, no external dependencies
- **Comprehensive** — include everything from the diagnosis:
  - Problem summary
  - Fuse map (visual cards showing the relevant fuses)
  - Full sensor/component table with fault codes
  - Step-by-step diagnosis procedure
  - Cable routing priorities
  - Emergency overrides
  - Safety interlocks
  - Tools needed
  - Quick-reference flowchart

Save the file to the user's workspace folder with a descriptive name like
`W50Ri_F31_Diagnosis.html` or `Bobcat_Hydraulic_Issue.html`.

## Important Notes

- Always respond in Hebrew unless the user writes in English
- Fault codes are critical — always include the code number AND what it means
- The user is a hands-on technician, not a desk engineer. Write for someone
  who's about to open a panel and start testing, not someone reading a report
- When listing things to check, put them in priority order (most likely first)
- If the notebook doesn't have enough info to fully diagnose, say so clearly
  and suggest what other information might help
- Cable routing and physical inspection guidance is extremely valuable — the
  user can't query NotebookLM from the field, so the diagnosis needs to be
  complete enough to work standalone
