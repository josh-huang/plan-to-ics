<p align="center">
  <h1 align="center">📅 plan-to-ics</h1>
  <p align="center">
    Turn your natural-language plans into an <code>.ics</code> calendar file —<br/>
    importable into <b>Apple Calendar</b>, <b>Google Calendar</b>, and <b>Outlook</b>.
  </p>
  <p align="center">
    <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg" />
    <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-blue.svg" />
    <img alt="Claude Code" src="https://img.shields.io/badge/claude%20code-skill-orange.svg" />
    <img alt="Version" src="https://img.shields.io/badge/version-0.2.0-blue" />
  </p>
</p>

---

Paste a whole schedule — a syllabus, a meeting list, a plan for the coming
months — and get one standards-compliant
[RFC 5545](https://datatracker.ietf.org/doc/html/rfc5545) `.ics` file that
imports into your calendar in a single tap.

> No accounts. No cloud. The generator is one Python file, standard library
> only. The `.ics` lives on your machine and goes straight into your calendar.

## ✨ Why this exists

The iCalendar format has a long tail of footguns that make hand-rolled `.ics`
files silently break on import:

- ❌ wrong line endings (must be `CRLF`, not `LF`)
- ❌ lines longer than 75 octets (must be folded, UTF-8-safely)
- ❌ unescaped commas / semicolons / newlines in event text
- ❌ all-day events missing `VALUE=DATE`
- ❌ recurring events with malformed `RRULE` or wrong `UNTIL`
- ❌ timezone mix-ups that shift every event by a few hours

This skill offloads all of that to a small, self-testing generator so the
result imports cleanly the first time.

## 🚀 Quick start

### Install

**Method 1 — Manual (works everywhere):**

```bash
# install the generator (one command)
pip install plan-to-ics

# install the skill
mkdir -p ~/.claude/skills
cp -r skills/plan-to-ics ~/.claude/skills/plan-to-ics
```

**Method 2 — As a plugin (two steps):**

```bash
# inside Claude Code
/plugin marketplace add josh-huang/plan-to-ics
/plugin install plan-to-ics@plan-to-ics
```

> The skill also auto-activates when you describe a plan in plain language —
> no explicit invocation needed.

### Use

Paste your whole plan at once, dates and times in any natural form:

```
> Team meeting Aug 20 9am in NTU N4-B2; dentist next Wednesday 3pm;
  Tokyo trip Sep 1–5; morning run every Mon/Wed/Fri starting Aug 24, 12 times;
  rent due the 1st of each month until December.
```

The skill parses it, generates one `my-plans.ics`, and hands you the path.
Import it (see [Importing into your calendar](#-importing-into-your-calendar))
and everything is in.

## 📖 Example

**Input** — paste this:

```
Aug 20, 9am — team meeting (NTU N4-B2, discuss the Q3 roadmap)
Aug 22 — moving day (all day)
Sep 1–5 — trip to Tokyo
Every Mon/Wed/Fri 7am — morning run, 12 times
Monthly on the 1st — rent due, until Dec
```

**Output** — the generated `.ics` (abridged):

```text
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//plan-to-ics//Calendar//EN
CALSCALE:GREGORIAN
X-WR-CALNAME:My Plans
X-WR-TIMEZONE:Asia/Shanghai
BEGIN:VEVENT
UID:ea62abb0-8689-4c80-acec-4bf80c1db586@plan-to-ics
DTSTAMP:20260815T064603Z
DTSTART;TZID=Asia/Shanghai:20260820T090000
DTEND;TZID=Asia/Shanghai:20260820T100000
SUMMARY:Team meeting
LOCATION:NTU\, N4-B2\, meeting room
DESCRIPTION:Discuss the Q3 roadmap
END:VEVENT
BEGIN:VEVENT
UID:4c64ea7b-7517-42cd-9518-8f2dfc767c20@plan-to-ics
DTSTAMP:20260815T064603Z
DTSTART;VALUE=DATE:20260822
DTEND;VALUE=DATE:20260823
SUMMARY:Moving day
END:VEVENT
BEGIN:VEVENT
UID:9f1c3a10-8d2e-4b7a-a1b5-7c9d3e2f4a10@plan-to-ics
DTSTAMP:20260815T064603Z
DTSTART;TZID=Asia/Shanghai:20260824T070000
DTEND;TZID=Asia/Shanghai:20260824T080000
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=12
SUMMARY:Morning run
END:VEVENT
END:VCALENDAR
```

Notice the details that matter: comma-escaping (`NTU\, N4-B2`), all-day events
as `VALUE=DATE` with exclusive `DTEND`, and a validated `RRULE` for the
recurring run.

## 🧠 What it understands

### Dates & times

| You say | It resolves to |
|---|---|
| today / tomorrow / the day after | today / +1 / +2 days |
| next Monday / this Friday | next / this occurrence of that weekday |
| Aug 20 / 8/20 / 20 Aug | that date |
| 9am / 3:30pm | 09:00 / 15:30 |
| all day / the whole day | an all-day event |
| Sep 1 to Sep 5 | one multi-day event, not five |

### Recurrence

| You say | recurrence |
|---|---|
| every day / every N days | `DAILY` (+ `interval`) |
| every Monday / every N weeks | `WEEKLY` (+ `byday`, `interval`) |
| the Nth of each month / every N months | `MONTHLY` (+ `bymonthday`, `interval`) |
| every year | `YEARLY` |
| 12 times / until the end of Dec | `count` / `until` |

Both **Chinese** (`今天`, `下周三`, `每月1号`, `每周一三五`) and **English**
forms are supported.

## 📲 Importing into your calendar

The `.ics` is generated on your machine; the last step is getting it onto the
device where your calendar lives.

| Device | Get the file there | Then |
|---|---|---|
| **Mac** | the file is already local | Double-click the `.ics`, or **File → Import** → select it |
| **iPhone / iPad** | **AirDrop** from your Mac, **email** it to yourself, or save to **iCloud Drive / Files** | Open the file in Files/Mail → tap **Add All** → pick a calendar |
| **Google Calendar** | open in a browser | **Settings → Import & export → Import** → select the `.ics` |

> On iPhone the preview lets you choose which calendar to import into and shows
> a per-event toggle before you commit — handy for a big batch.

## 🔧 Using the generator directly

The skill is a thin wrapper around a standalone, pip-installable CLI, so you
can use it without Claude Code at all:

```bash
pip install plan-to-ics

plan2ics examples/sample-events.json output.ics   # or:
python -m plan_to_ics examples/sample-events.json output.ics
```

Input is a JSON schedule:

```json
{
  "calendar_name": "My Plans",
  "timezone": "Asia/Shanghai",
  "events": [
    {
      "summary": "Team meeting",
      "start": "2026-08-20T09:00",
      "end": "2026-08-20T10:00",
      "location": "NTU, N4-B2, meeting room",
      "description": "Discuss the Q3 roadmap"
    },
    { "summary": "Moving day", "start": "2026-08-22" },
    {
      "summary": "Morning run",
      "start": "2026-08-24T07:00",
      "end": "2026-08-24T08:00",
      "recurrence": { "freq": "WEEKLY", "byday": ["MO", "WE", "FR"], "count": 12 }
    },
    {
      "summary": "Rent due",
      "start": "2026-09-01",
      "recurrence": { "freq": "MONTHLY", "bymonthday": 1, "until": "2026-12-01" }
    }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `summary` | ✅ | event title |
| `start` | ✅ | `YYYY-MM-DD` (all-day) or `YYYY-MM-DDTHH:MM` (timed) |
| `end` | timed events | for all-day, **exclusive** end day |
| `location`, `description` | — | optional |
| `timezone` | — | IANA name; per-event override |
| `uid` | — | stable UID (defaults to a UUID) |
| `recurrence` | — | `freq` + `interval` / `byday` / `bymonthday` / `count` / `until` |

**Recurrence rules:** `freq` is one of `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`.
`byday` (e.g. `["MO","WE"]`) is for `WEEKLY`; `bymonthday` (1–31) is for
`MONTHLY`. Use `count` **or** `until` (not both); `until` is an inclusive
last-occurrence date, and for a timed event it needs a `timezone` (its `UNTIL`
must be a UTC instant).

Run the built-in self-test to confirm the generator is healthy:

```bash
plan2ics --selftest
```

CLI options: `plan2ics <input> <output>` (stdin/stdout when omitted),
`--name`, `--timezone`, `--selftest`, `--version`.

## 🕐 Timezone behaviour

By default the generator emits **floating local time** (no `TZID`). Apple
Calendar then interprets the times in the device's own timezone — which is
almost always what you want for a personal plan, and it sidesteps the classic
"every event shifted by 8 hours" bug. If you *do* need a fixed timezone, set
the top-level `timezone` to any IANA name (`Asia/Singapore`, `America/New_York`,
…).

Timezone names are checked against the IANA database before export. Unknown,
empty, or malformed names produce a validation error instead of an invalid
calendar. Omit `timezone` (or set it to `null`) for floating local time; an
event-level `null` also overrides a calendar-wide timezone. Python uses the
system timezone database; if your system has none (commonly Windows), install
it with `pip install tzdata`.

## 📁 Repo layout

```text
plan-to-ics/
├── .claude-plugin/
│   ├── plugin.json               # plugin manifest for /plugin install
│   └── marketplace.json          # marketplace manifest (GitHub distribution)
├── plan_to_ics/                  # the pip-installable generator package
│   ├── __init__.py
│   ├── __main__.py               # enables python -m plan_to_ics
│   └── generate.py               # RFC 5545 + RRULE generator (stdlib only)
├── skills/
│   └── plan-to-ics/
│       ├── SKILL.md              # the skill definition
│       └── scripts/
│           └── generate_ics.py   # thin launcher for the package
├── examples/
│   └── sample-events.json        # a runnable example input
├── pyproject.toml                # pip packaging + plan2ics entry point
├── LICENSE
└── README.md
```

## 🧪 Correctness

The generator enforces the parts of RFC 5545 that most commonly break imports:

- **CRLF** line endings, no bare `LF`
- **75-octet line folding**, never splitting inside a multi-byte UTF-8 char
- **text escaping** for `\` `;` `,` and newlines
- **all-day events** as `VALUE=DATE` with exclusive `DTEND`
- **validated `RRULE`** — correct `FREQ`/`INTERVAL`/`BYDAY`/`BYMONTHDAY`, and
  `UNTIL` serialized as a DATE (all-day) or a UTC instant (timed, via `zoneinfo`)
- **unique `UID`** per event, UTC `DTSTAMP`
- optional **TZID** with `X-WR-TIMEZONE` for Apple Calendar

`--selftest` exercises every one of these and fails loudly on any regression.

## 🤝 Contributing

Bug reports and pull requests are welcome. Before changing the generator, run
`python -m plan_to_ics --selftest` and add a case for the bug you're fixing.
Run the regression suite with `python -m unittest discover -s tests -v`.

## 📄 License

[MIT](./LICENSE) © 2026 Josh Huang

