# `lab/` — Audit-mode improvement workspace

This is where the swarm-orchestrator improves itself. **Nothing in here affects the live skill** until `/swarm-audit promote` runs and you confirm.

See [`docs/AUDIT-MODE.md`](../docs/AUDIT-MODE.md) for the full design and [`docs/AUDIT-COMMANDS.md`](../docs/AUDIT-COMMANDS.md) for the command recipes.

---

## Layout

```
lab/
├── README.md                 ← you are here
├── proposed/                 ← mutation target — copy of live skill, mutable
├── feedback.jsonl            ← all feedback entries, append-only
├── replays/                  ← per-replay reports
├── eval/
│   ├── tasks/                ← canonical eval tasks (one .md per task)
│   └── runs/                 ← per-run scoreboards
├── dry-runs/                 ← dispatch plans that didn't fire
├── training/
│   ├── dispatch-pairs.jsonl  ← (task, dispatch_decision, outcome) — fine-tune corpus
│   └── preferences.jsonl     ← (chosen, rejected) pairs — preference data
└── _archive/                 ← rejected proposals (never deleted)
```

---

## Safety rules (enforced by every audit command)

1. **No writes outside `lab/`** until `/swarm-audit promote` runs with explicit confirmation.
2. **No deletes.** Rejected work → `_archive/<YYYY-MM-DD>_<reason>/`.
3. **No fabricated data.** Eval scores from real reviewer runs only.
4. **No secrets.** Don't paste API keys or customer data into feedback entries.

---

## Quickstart

- Log feedback while working: `/swarm-feedback "haiku fabricated success on the file write"`
- Replay a past session under a proposed change: `/swarm-audit replay <session-id>`
- Run the eval suite: `/swarm-audit eval`
- Promote (after confirmation): `/swarm-audit promote`
- Weekly self-review: `/swarm-audit weekly`
- Snapshot: `/swarm-audit status`

For everything else: `/swarm-help audit`.
