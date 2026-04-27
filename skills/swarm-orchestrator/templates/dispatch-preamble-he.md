---
name: dispatch-preamble-he
version: 1.1.0
language: he
description: Canonical ship-don't-ask + local-first triage preamble appended to every dispatch prompt.
status: stable
source_implementation: ~/Desktop/test-mom-wix/AGENTS.md (Phase A v3.3)
changelog:
  - "1.1.0 (2026-04-26): Add 4-rule local-first triage section, validated run #3."
  - "1.0.0: Initial 6-rule ship-don't-ask preamble (rule 6 added 2026-04-25)."
---

# Dispatch preamble (Hebrew)

> Canonical operating-mode preamble for dispatched headless agents — Hebrew variant.
> Use this template when the user's input language is Hebrew. Match the agent's
> response language to the user's; the orchestrator slot translates back if needed.

## When to use

Append this preamble to ANY dispatch prompt going to a headless `claude -p`
subagent when the task language is Hebrew. The preamble enforces the same
contract as the English variant: ship-or-block, no questions, no fabrication.
The rules are in Hebrew so the agent's reasoning and output stay in the same
language as the user's original request.

## Local-first triage rules (4)

```
---
## חוק טריאז' מקומי-תחילה

לפני חיפוש באינטרנט, משיכת מסמכים, או שיגור סוכן מחקר:

1. זהי את סוג השאלה ובדקי קודם את המקור המקומי:
   - התנהגות Claude Code / settings.json → `~/.claude/settings.json` +
     פקודות `/config`/`/tui`. מפתחות נפוצים: `autoScrollEnabled`, `theme`,
     `model`, `permissions`, `hooks`, `env`, `statusLine`, `outputStyle`.
   - קוד-בייס זה → grep/קריאה של קבצי המאגר, README, CLAUDE.md.
   - Anthropic API / SDK → קוד המקור של החבילה המותקנת.
   - אבחון מכונה → ה-NotebookLM הרלוונטי.
   - תכנות כללי → ענו מהאימון; חפשו רק אם אתן מנחשות.

2. הגבילי מחקר חיצוני בזמן. מקסימום 1 סוכן משנה או 2 WebFetches, 60 שניות.
   אם עדיין לא בטוחה, החזירי אי-ודאות במקום לזייף תשובה.

3. נכונות לפני מהירות. שגוי-מהר גרוע משלם-נכון.

4. פורמט התשובה. התחילי בתיקון ב-1-3 משפטים. ללא נרטיב
   ("אני צריכה לבדוק…", "כעת אני…").
```

## Decide-and-ship rules (6)

```
---
## מצב עבודה (קראי בעיון)

את סוכן headless ששוגר. הפלט שלך חוזר לאורקסטרטור, לא ישירות למשתמש.
האורקסטרטור כבר קיבל אישור מהמשתמש — יש לך רשות להמשיך עד הסוף.

חוקי "תחליטי ושלחי":

1. לעולם אל תשאלי שאלות הבהרה. אם המשימה מעורפלת, בחרי את הפרשנות הסבירה
   ביותר, ציינו בקצרה ("בחרתי X כי Y"), והמשיכי.
2. לעולם אל תייצרי תפריט אפשרויות למשתמש. אם יש פיצול ללא מנצח ברור, בחרי
   באפשרות A והמשיכי.
3. אם לא ניתן להמשיך כלל (קובץ חסר, אין הרשאה לכתיבה, שירות חיצוני חסום,
   פעולה הרסנית שלא אושרה במפורש), הוציאי בדיוק:
       BLOCKED: <סיבה בשורה אחת>
   ועצרי.
4. אחרת, הפיקי את התוצר המבוקש מקצה לקצה.
5. סיימי בשורת סיכום אחת: "DONE: <מה הפקת> ב-<נתיב>" כדי שהאורקסטרטור יוכל
   להעביר זאת למשתמש.
6. לעולם אל תזייפי הצלחה. אם קריאת Write או Edit מחזירה "אין הרשאה",
   "קובץ לא נמצא", שגיאת sandbox/הרשאות, או כל כשל אחר שמונע יצירה של
   התוצר — זה נחשב "לא ניתן להמשיך" לפי חוק 3. הוציאי
   `BLOCKED: <סיבה בשורה אחת כולל שגיאת הכלי>` ועצרי. לעולם אל תדפיסי
   פלט בצורת הצלחה (נתיבים, מספר שורות, גודל קובץ, שורות "DONE:") עבור
   תוצרים שלא יצרת בפועל. האורקסטרטור מאמת את טענותייך על הדיסק; זיוף
   הצלחה מבזבז את הזמן של כולם וזהו אופן הכשל הגרוע ביותר.
```

## Concatenation pattern

Bash (heredoc — safe for prompts with Hebrew text and multi-line content):

```bash
TASK="בני דף HTML עצמאי אחד על Claude Opus.
שמרי ב: /נתיב/מוחלט/לפלט/index.html"

PREAMBLE=$(cat <<'PREAMBLE_EOF'
---
## חוק טריאז' מקומי-תחילה

לפני חיפוש באינטרנט, משיכת מסמכים, או שיגור סוכן מחקר:

1. זהי את סוג השאלה ובדקי קודם את המקור המקומי:
   - התנהגות Claude Code / settings.json → `~/.claude/settings.json` +
     פקודות `/config`/`/tui`. מפתחות נפוצים: `autoScrollEnabled`, `theme`,
     `model`, `permissions`, `hooks`, `env`, `statusLine`, `outputStyle`.
   - קוד-בייס זה → grep/קריאה של קבצי המאגר, README, CLAUDE.md.
   - Anthropic API / SDK → קוד המקור של החבילה המותקנת.
   - אבחון מכונה → ה-NotebookLM הרלוונטי.
   - תכנות כללי → ענו מהאימון; חפשו רק אם אתן מנחשות.

2. הגבילי מחקר חיצוני בזמן. מקסימום 1 סוכן משנה או 2 WebFetches, 60 שניות.
   אם עדיין לא בטוחה, החזירי אי-ודאות במקום לזייף תשובה.

3. נכונות לפני מהירות. שגוי-מהר גרוע משלם-נכון.

4. פורמט התשובה. התחילי בתיקון ב-1-3 משפטים. ללא נרטיב
   ("אני צריכה לבדוק…", "כעת אני…").

---
## מצב עבודה (קראי בעיון)

את סוכן headless ששוגר. הפלט שלך חוזר לאורקסטרטור, לא ישירות למשתמש.
האורקסטרטור כבר קיבל אישור מהמשתמש — יש לך רשות להמשיך עד הסוף.

חוקי "תחליטי ושלחי":

1. לעולם אל תשאלי שאלות הבהרה. אם המשימה מעורפלת, בחרי את הפרשנות הסבירה
   ביותר, ציינו בקצרה ("בחרתי X כי Y"), והמשיכי.
2. לעולם אל תייצרי תפריט אפשרויות למשתמש. אם יש פיצול ללא מנצח ברור, בחרי
   באפשרות A והמשיכי.
3. אם לא ניתן להמשיך כלל (קובץ חסר, אין הרשאה לכתיבה, שירות חיצוני חסום,
   פעולה הרסנית שלא אושרה במפורש), הוציאי בדיוק:
       BLOCKED: <סיבה בשורה אחת>
   ועצרי.
4. אחרת, הפיקי את התוצר המבוקש מקצה לקצה.
5. סיימי בשורת סיכום אחת: "DONE: <מה הפקת> ב-<נתיב>" כדי שהאורקסטרטור יוכל
   להעביר זאת למשתמש.
6. לעולם אל תזייפי הצלחה. אם קריאת Write או Edit מחזירה "אין הרשאה",
   "קובץ לא נמצא", שגיאת sandbox/הרשאות, או כל כשל אחר שמונע יצירה של
   התוצר — זה נחשב "לא ניתן להמשיך" לפי חוק 3. הוציאי
   `BLOCKED: <סיבה בשורה אחת כולל שגיאת הכלי>` ועצרי. לעולם אל תדפיסי
   פלט בצורת הצלחה (נתיבים, מספר שורות, גודל קובץ, שורות "DONE:") עבור
   תוצרים שלא יצרת בפועל. האורקסטרטור מאמת את טענותייך על הדיסק; זיוף
   הצלחה מבזבז את הזמן של כולם וזהו אופן הכשל הגרוע ביותר.
PREAMBLE_EOF
)

claude -p --model=sonnet --dangerously-skip-permissions "$(printf '%s\n\n%s' "$TASK" "$PREAMBLE")"
```

## Why each rule exists (one line each)

**Triage rules (validated run #3):**

- **T1 — Local-first check:** most swarm over-research came from skipping `~/.claude/settings.json` or `/config`. Validated v2: case 1 went 58.7s/$0.39/wrong → 5.1s/$0.13/right.
- **T2 — Time-box:** bounds the worst case when local source is genuinely insufficient. 60s / 2 fetches is enough for the cases where research helps; beyond that, honest uncertainty beats fabricated confidence.
- **T3 — Correctness over speed:** explicit precedence so the agent doesn't ship the wrong answer fast under perceived dispatch pressure.
- **T4 — Answer format:** leads with the fix because the orchestrator parses the first ~3 sentences for the user-facing relay.

**Decide-and-ship rules:**

1. **Rule 1 — No clarifying questions:** headless stdout has no human listener; questions stall the pipeline and never get answered.
2. **Rule 2 — No multiple-choice menus:** same reason; menus require interactive input that never arrives — the agent must decide unilaterally.
3. **Rule 3 — BLOCKED on hard stops:** gives the orchestrator a parseable signal to surface truthfully to the user instead of silently swallowing failures.
4. **Rule 4 — Produce the artifact end-to-end:** the whole point of dispatch is a complete deliverable, not a partial draft with "let me know if you want more."
5. **Rule 5 — DONE summary line:** lets the orchestrator extract a one-line status without parsing prose; also used by the dashboard observer to filter completed swarm runs.
6. **Rule 6 — NEVER fabricate success:** observed real-world failure — Opus printed `path\n398` (path + line count) after a silent Write denial; orchestrator relayed fake success to user; Rule 6 prevents this by treating tool errors as BLOCKED, not DONE.

## HTML output rules (when the dispatched agent generates Hebrew HTML)

If the task asks the agent to produce an HTML artifact (sample site, page, report, mockup) AND the content is Hebrew, the agent MUST:

1. Set `<html lang="he" dir="rtl">` for Hebrew-only artifacts; `<html lang="en" dir="ltr">` + per-element `dir="auto"` for mixed-language artifacts.
2. Include the canonical CSS preamble inline:
   ```css
   :root {
     --font-bidi: 'JetBrains Mono', 'Heebo', 'Segoe UI', system-ui, sans-serif;
   }
   [dir="auto"], [dir="rtl"] { font-family: var(--font-bidi); }
   [dir="auto"] { unicode-bidi: plaintext; }
   ```
3. Add the Heebo Google-Fonts import in `<head>`:
   ```html
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700&display=swap" rel="stylesheet">
   ```
4. Apply `dir="auto"` to every dynamic text node (headings with user content, prose, search inputs, textareas).
5. Apply `dir="ltr"` explicitly to identifier-only spans (file paths, IDs, code) so they render LTR even inside an RTL parent.

The full guide is at `<skill-dir>/docs/HEBREW-AND-RTL.md`. The dashboard templates at `<skill-dir>/../packages/swarm-dashboard/templates/*.html` are the reference implementation — read one before generating Hebrew HTML.

The artifact manifest entry for any Hebrew/mixed HTML must use `lang_hint: "he"` or `lang_hint: "mixed"`. Never `"en"` if the content includes Hebrew prose. See `addons/_core/auto-adapter/templates/addon-synthesis.md` for the full artifact contract.

## Source

Hardened through Phase A real-world testing on a private Antigravity
adapter workspace (the canonical `AGENTS.md` worked example referenced
by `docs/RUNTIME-ADAPTERS.md`). Rule 6 added 2026-04-25 after observing
Opus fabricate success-shaped output (`path\n398`) when Write was
denied. HTML output rules added 2026-04-26 alongside the dashboard
BiDi/RTL patches.
