---
name: plan-to-ics
description: Convert a user's plans, schedule, or to-do list into a standards-compliant .ics calendar file that can be imported into Apple Calendar, Google Calendar, or Outlook. Use when the user asks to "把计划生成日历", "make an .ics", "generate a calendar file", "export my schedule to a calendar", "add these dates/events to my calendar", or simply lists future dates with things to do (e.g. "8月20号上午9点开会", "下周三下午3点看牙医", "9/1-9/5 去东京旅行"). Parses Chinese and English dates and times, resolves relative dates (今天/明天/后天/下周/周X), and writes the .ics via a bundled Python generator.
version: 0.1.0
---

# Plan to ICS

Turn natural-language plans into an importable `.ics` calendar file.

## Pipeline

1. **Parse** the user's plan into discrete events.
2. **Resolve** relative dates/times against today's date.
3. **Build** a JSON schedule.
4. **Generate** the `.ics` with the bundled script.
5. **Save** the file and tell the user how to import it.

## Step 1 — Parse events from the plan

Extract one event per activity. For each, capture:

- **summary** (what)
- **start** date/time (when)
- **end** date/time (until when) — optional
- **location** — optional
- **description** — optional

Split compound input (a bulleted list or a paragraph with several dates)
into separate events. A date range like "9/1 到 9/5" is ONE multi-day event,
not five.

## Step 2 — Resolve dates and times

Use today's date as the anchor. Resolve Chinese and English forms:

| Form | Meaning |
|---|---|
| 今天 / today | today |
| 明天 / tomorrow | +1 day |
| 后天 / 大后天 | +2 / +3 days |
| 下周X / next \<weekday\> | next occurrence of that weekday |
| 周X / 本周X / this \<weekday\> | this week's occurrence |
| X月X号 / X月X日 / X/X / X-X | that month and day |
| X月X号上午/下午/晚上X点(半) | that time of day |
| X天后 / in X days | +X days |
| 明年X月X日 / \<month\> \<day\> next year | next year |

Rules:

- If no year is given, use the current year; if the resolved date is already
  in the past, roll it forward one year (or to the next occurrence for
  weekdays).
- A time given without an end time → default duration **1 hour**.
- No time at all → **all-day** event (`VALUE=DATE`).
- "全天" / "一整天" / "整天" / "all day" → all-day event.

## Step 3 — Build the JSON

Build a JSON object with the schema below, write it to a temp file, and pass
that file's path to the generator. Do NOT inline the JSON as a shell heredoc
when it contains non-ASCII characters — a file avoids Windows stdin-encoding
issues.

```json
{
  "calendar_name": "My Plans",
  "timezone": "Asia/Shanghai",
  "events": [
    {
      "summary": "和团队开会",
      "start": "2026-08-20T09:00",
      "end": "2026-08-20T10:00",
      "location": "NTU N4-B2",
      "description": "讨论 Q3 路线图"
    }
  ]
}
```

**All-day `end` is EXCLUSIVE** (iCalendar semantics). A single all-day on
2026-08-20 is `start: "2026-08-20", end: "2026-08-21"`. A range covering
09-01 through 09-05 is `end: "2026-09-06"`.

## Step 4 — Generate the .ics

The generator is bundled at `${CLAUDE_SKILL_DIR}/scripts/generate_ics.py`
(`${CLAUDE_SKILL_DIR}` resolves to the directory containing this SKILL.md,
whether the skill is installed manually or as a plugin). Run it with the
Python launcher available on the machine — `python` on Windows, `python3` on
macOS/Linux:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/generate_ics.py" events.json output.ics
```

- `events.json` — the JSON from Step 3.
- `output.ics` — where to write the result.

If `python3` exits with a strange code (e.g. 49) on Windows, it is the
Microsoft Store stub — use `python` instead.

## Step 5 — Save and report

- Save the `.ics` to the current working directory (or a `calendar/`
  subfolder) with a sensible filename derived from `calendar_name` or the
  first event (e.g. `my-plans.ics`).
- Report the file path and give import instructions:
  - **macOS Apple Calendar**: double-click the `.ics`, or File → Import.
  - **iPhone/iPad**: AirDrop the file, or open it from Files/Mail and tap to
    add the events.
  - **Google Calendar**: Settings → Import & export → Import → select the
    file.

## Timezone

- By default emit **floating local time** (omit `timezone`): Apple Calendar
  then interprets times in the device's own timezone, which is what most
  people want for a personal plan and avoids a "times shifted by N hours"
  surprise.
- If the user explicitly names a timezone, set the top-level `timezone` to an
  IANA name (e.g. `Asia/Singapore`, `Asia/Shanghai`, `America/New_York`).

## Defaults and edge cases

- Ambiguous time ("晚上" with no hour) → default to a reasonable hour
  (上午=09:00, 下午=15:00, 晚上=19:00) and state the assumption.
- Missing end time → 1 hour.
- Overlapping events → keep them; do not silently merge.
- Past dates → warn the user rather than silently generating.

If the input is too vague to produce a meaningful event, ask a single
clarifying question; otherwise pick the most reasonable default, proceed, and
state the assumption.
