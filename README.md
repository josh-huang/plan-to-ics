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
  </p>
</p>

---

A [Claude Code](https://claude.com/code) skill that takes a schedule written the
way you'd actually say it — *"team meeting Aug 20 at 9am"*, *"dentist next
Wednesday at 3pm"*, *"Tokyo trip Sept 1–5"* — and produces a standards-compliant
[RFC 5545](https://datatracker.ietf.org/doc/html/rfc5545) `iCalendar` file you
can double-click to import.

> No accounts. No cloud. One Python file, standard library only. The generated
> `.ics` lives on your machine and goes straight into your calendar.

## ✨ Why this exists

The iCalendar format has a long tail of footguns that make hand-rolled `.ics`
files silently break on import:

- ❌ wrong line endings (must be `CRLF`, not `LF`)
- ❌ lines longer than 75 octets (must be folded, UTF-8-safely)
- ❌ unescaped commas / semicolons / newlines in event text
- ❌ all-day events missing `VALUE=DATE`
- ❌ timezone mix-ups that shift every event by a few hours

This skill offloads all of that to a small, self-testing generator so the
result imports cleanly the first time.

## 🚀 Quick start

### Install

**Method 1 — Manual (works everywhere):**

```bash
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

Just tell Claude your plan in plain language:

```
> Team meeting Aug 20 at 9am in NTU N4-B2; dentist next Wednesday at 3pm; Tokyo trip Sept 1–5
```

The skill parses it, generates `my-plans.ics`, and hands you the file path.
Double-click it (or File → Import in Apple Calendar) and you're done.

## 📖 Example

**Input** — what you say:

```
Aug 20, 9am — team meeting (NTU N4-B2, discuss the Q3 roadmap)
Aug 22 — moving day (all day)
Sep 1–5 — trip to Tokyo
```

**Output** — the generated `my-plans.ics`:

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
END:VCALENDAR
```

Notice the details that matter: comma-escaping (`NTU\, N4-B2`), all-day events
as `VALUE=DATE`, and `DTEND` being **exclusive** (the day *after* the event).

## 🧠 What it understands

| You say | It resolves to |
|---|---|
| today / tomorrow / the day after | today / +1 / +2 days |
| next Monday / this Friday | next / this occurrence of that weekday |
| Aug 20 / 8/20 / 20 Aug | that date |
| 9am / 3:30pm | 09:00 / 15:30 |
| all day / the whole day | an all-day event |
| Sep 1 to Sep 5 | one multi-day event, not five |

Both **Chinese** and **English** date forms are supported.

## 🔧 Using the generator directly

The skill is a thin wrapper around a standalone script, so you can use it
without Claude too:

```bash
python3 scripts/generate_ics.py examples/sample-events.json output.ics
```

Input is a simple JSON schedule:

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
    { "summary": "Trip to Tokyo", "start": "2026-09-01", "end": "2026-09-06" }
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

Run the built-in self-test to confirm the generator is healthy:

```bash
python3 scripts/generate_ics.py --selftest
```

## 🕐 Timezone behaviour

By default the generator emits **floating local time** (no `TZID`). Apple
Calendar then interprets the times in the device's own timezone — which is
almost always what you want for a personal plan, and it sidesteps the classic
"every event shifted by 8 hours" bug. If you *do* need a fixed timezone, set
the top-level `timezone` to any IANA name (`Asia/Singapore`, `America/New_York`,
…).

## 📁 Repo layout

```text
plan-to-ics/
├── .claude-plugin/
│   └── plugin.json               # plugin manifest for /plugin install
├── skills/
│   └── plan-to-ics/
│       ├── SKILL.md              # the skill definition (the prompt/instructions)
│       └── scripts/
│           └── generate_ics.py   # RFC 5545 generator (stdlib only, self-tests)
├── examples/
│   └── sample-events.json        # a runnable example input
├── LICENSE
└── README.md
```

## 🧪 Correctness

The generator enforces the parts of RFC 5545 that most commonly break imports:

- **CRLF** line endings, no bare `LF`
- **75-octet line folding**, never splitting inside a multi-byte UTF-8 char
- **text escaping** for `\` `;` `,` and newlines
- **all-day events** as `VALUE=DATE` with exclusive `DTEND`
- **unique `UID`** per event, UTC `DTSTAMP`
- optional **TZID** with `X-WR-TIMEZONE` for Apple Calendar

`--selftest` exercises every one of these and fails loudly on any regression.

## 🤝 Contributing

Bug reports and pull requests are welcome. Before changing the generator, run
`python3 scripts/generate_ics.py --selftest` and add a case for the bug you're
fixing.

## 📄 License

[MIT](./LICENSE) © 2026 Josh Huang
