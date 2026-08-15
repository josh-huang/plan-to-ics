#!/usr/bin/env python3
"""Generate a standards-compliant iCalendar (.ics) file from a JSON schedule.

This script handles the fiddly parts of RFC 5545 so the caller can focus on
the schedule itself, not the serialization:

  * CRLF line endings
  * 75-octet line folding (UTF-8 safe, never splits inside a character)
  * text escaping (backslash, semicolon, comma, newline)
  * unique UID per event
  * UTC DTSTAMP
  * all-day (VALUE=DATE) vs. timed (floating or TZID) events

Usage:
    python3 generate_ics.py events.json output.ics   # file -> file
    python3 generate_ics.py events.json              # file -> stdout
    python3 generate_ics.py                          # stdin -> stdout
    python3 generate_ics.py --selftest               # internal sanity check

Input schema (JSON)::

    {
      "calendar_name": "My Plans",        # optional -> X-WR-CALNAME
      "timezone": "Asia/Shanghai",        # optional default TZID for events
      "events": [
        {
          "summary": "Team standup",      # required
          "start": "2026-08-20T09:00",    # required; "2026-08-20" = all-day
          "end": "2026-08-20T09:30",      # required for timed events
          "location": "Room 302",         # optional
          "description": "Bring notes",   # optional
          "timezone": "Asia/Shanghai",    # optional per-event TZID override
          "uid": "team-standup-0820"      # optional stable UID (else uuid4)
        }
      ]
    }

For all-day events ``end`` is EXCLUSIVE, matching iCalendar DTEND semantics:
a single day on 2026-08-20 is ``start: "2026-08-20", end: "2026-08-21"``.

Exit codes: 0 ok, 1 usage/validation/serialization error.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

PRODID = "-//plan-to-ics//Calendar//EN"
CRLF = "\r\n"
MAX_OCTETS = 75


class IcsError(ValueError):
    """Raised for any input the generator cannot safely serialize."""


# --------------------------------------------------------------------------- #
# Low-level RFC 5545 helpers
# --------------------------------------------------------------------------- #

def escape_text(value: str) -> str:
    """Escape a text value per RFC 5545 section 3.3.11.

    Order matters: the backslash must be escaped first, otherwise the escapes
    inserted afterwards would themselves get double-escaped.
    """
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold_line(line: str) -> str:
    """Fold a content line to at most 75 octets per RFC 5545 section 3.1.

    Continuation lines begin with a single space (which the parser strips), so
    they may carry at most 74 further octets. Folding is done one character at
    a time so a multi-byte UTF-8 character is never split across lines.
    """
    if len(line.encode("utf-8")) <= MAX_OCTETS:
        return line

    chunks: list[str] = []
    current = ""
    budget = MAX_OCTETS  # octets left on the current physical line

    for ch in line:
        width = len(ch.encode("utf-8"))
        if width > budget:
            chunks.append(current)
            current = " " + ch          # continuation line leads with a space
            budget = (MAX_OCTETS - 1) - width
        else:
            current += ch
            budget -= width

    if current:
        chunks.append(current)
    return CRLF.join(chunks)


# --------------------------------------------------------------------------- #
# Date/time handling
# --------------------------------------------------------------------------- #

def parse_start(value: str) -> tuple[datetime, bool]:
    """Parse an event start into ``(datetime, is_all_day)``.

    ``YYYY-MM-DDTHH:MM`` (or ``...THH:MM:SS``) yields a timed event;
    ``YYYY-MM-DD`` yields an all-day event.
    """
    if "T" in value:
        try:
            dt = datetime.fromisoformat(value)
        except ValueError as exc:
            raise IcsError(
                f"invalid datetime {value!r}: expected YYYY-MM-DDTHH:MM"
            ) from exc
        if dt.tzinfo is not None:
            raise IcsError(
                f"{value!r} must be a naive local time (no offset or Z suffix)"
            )
        return dt, False

    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise IcsError(f"invalid date {value!r}: expected YYYY-MM-DD") from exc
    return dt, True


def format_start(dt: datetime, is_all_day: bool, tzid: str | None) -> str:
    if is_all_day:
        return f"DTSTART;VALUE=DATE:{dt.strftime('%Y%m%d')}"
    if tzid:
        return f"DTSTART;TZID={tzid}:{dt.strftime('%Y%m%dT%H%M%S')}"
    return f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}"


def format_end(dt: datetime, is_all_day: bool, tzid: str | None) -> str:
    if is_all_day:
        return f"DTEND;VALUE=DATE:{dt.strftime('%Y%m%d')}"
    if tzid:
        return f"DTEND;TZID={tzid}:{dt.strftime('%Y%m%dT%H%M%S')}"
    return f"DTEND:{dt.strftime('%Y%m%dT%H%M%S')}"


def normalize_uid(uid: str) -> str:
    """Make a caller-supplied UID safe: strip whitespace and control chars."""
    cleaned = "".join(ch for ch in uid if ch.isprintable() and not ch.isspace())
    if not cleaned:
        raise IcsError(f"invalid empty uid {uid!r}")
    return cleaned


# --------------------------------------------------------------------------- #
# Event building
# --------------------------------------------------------------------------- #

def build_event(evt: object, index: int, default_tz: str | None) -> list[str]:
    if not isinstance(evt, dict):
        raise IcsError(f"event #{index} must be a JSON object")

    summary = evt.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise IcsError(f"event #{index} is missing a non-empty 'summary'")

    start_raw = evt.get("start")
    if not isinstance(start_raw, str):
        raise IcsError(f"event #{index} ({summary}) is missing a 'start' date")

    start, is_all_day = parse_start(start_raw)
    tzid = evt.get("timezone", default_tz)
    if tzid is not None and not isinstance(tzid, str):
        raise IcsError(f"event #{index} ({summary}) has a non-string 'timezone'")

    uid_raw = evt.get("uid")
    uid = (
        normalize_uid(uid_raw)
        if uid_raw is not None
        else f"{uuid.uuid4()}@plan-to-ics"
    )

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.now(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        format_start(start, is_all_day, tzid),
    ]

    end_raw = evt.get("end")
    if is_all_day:
        if end_raw is None:
            end = start + timedelta(days=1)  # single-day all-day event
        else:
            end, is_end_all_day = parse_start(end_raw)
            if not is_end_all_day:
                raise IcsError(
                    f"event #{index} ({summary}): all-day 'end' must be a "
                    f"YYYY-MM-DD date, got {end_raw!r}"
                )
        if end <= start:
            raise IcsError(
                f"event #{index} ({summary}): all-day 'end' must be after "
                f"'start' (remember: end is exclusive)"
            )
        lines.append(format_end(end, True, None))
    else:
        if end_raw is None:
            raise IcsError(
                f"event #{index} ({summary}): timed event requires an 'end'"
            )
        end, _ = parse_start(end_raw)
        if end <= start:
            raise IcsError(
                f"event #{index} ({summary}): 'end' must be after 'start'"
            )
        lines.append(format_end(end, False, tzid))

    lines.append(f"SUMMARY:{escape_text(summary)}")

    location = evt.get("location")
    if location:
        lines.append(f"LOCATION:{escape_text(str(location))}")

    description = evt.get("description")
    if description:
        lines.append(f"DESCRIPTION:{escape_text(str(description))}")

    lines.append("END:VEVENT")
    return lines


def build_calendar(data: object) -> str:
    if not isinstance(data, dict):
        raise IcsError("input must be a JSON object with an 'events' array")

    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise IcsError("input must contain a non-empty 'events' array")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
    ]

    name = data.get("calendar_name")
    if name:
        lines.append(f"X-WR-CALNAME:{escape_text(str(name))}")

    default_tz = data.get("timezone")
    if default_tz:
        if not isinstance(default_tz, str):
            raise IcsError("'timezone' must be a string (IANA name, e.g. Asia/Shanghai)")
        lines.append(f"X-WR-TIMEZONE:{default_tz}")

    for index, evt in enumerate(events):
        lines.extend(build_event(evt, index, default_tz))

    lines.append("END:VCALENDAR")

    folded = [fold_line(line) for line in lines]
    return CRLF.join(folded) + CRLF


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #

def read_input(path: str | None) -> str:
    if path in (None, "-"):
        # Read raw bytes and decode UTF-8 explicitly: on Windows the default
        # stdin codec (cp1252/cp936) would mangle UTF-8 input into surrogates.
        return sys.stdin.buffer.read().decode("utf-8")
    return Path(path).read_text(encoding="utf-8")


def emit(text: str, path: str | None) -> None:
    data = text.encode("utf-8")
    if path:
        # write_bytes avoids Windows newline translation, preserving CRLF.
        Path(path).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

def selftest() -> int:
    sample = {
        "calendar_name": "Test Calendar",
        "timezone": "Asia/Shanghai",
        "events": [
            {
                "summary": "Team meeting",
                "start": "2026-08-20T09:00",
                "end": "2026-08-20T09:30",
                "location": "Room 302, Building A; floor 3",
                "description": "Discuss Q3 roadmap\nBring notes",
            },
            {
                "summary": "Day trip",
                "start": "2026-09-01",
                "end": "2026-09-03",  # exclusive: covers 09-01 and 09-02
                "uid": "day-trip-2026",
            },
            {
                "summary": "长标题" * 60,
                "start": "2026-10-01T14:00",
                "end": "2026-10-01T15:00",
            },
        ],
    }

    ics = build_calendar(sample)
    problems: list[str] = []

    if "\n" in ics.replace("\r\n", ""):
        problems.append("bare-LF line ending detected (must be CRLF only)")

    if not ics.endswith("\r\n"):
        problems.append("file does not end with CRLF")

    for line in ics.split("\r\n"):
        n = len(line.encode("utf-8"))
        if n > MAX_OCTETS:
            problems.append(f"line exceeds {MAX_OCTETS} octets ({n}): {line[:40]!r}")

    if "\\," not in ics or "\\;" not in ics:
        problems.append("comma/semicolon escaping missing")
    if "\\n" not in ics:
        problems.append("newline escaping missing")
    if "TZID=Asia/Shanghai" not in ics:
        problems.append("TZID parameter missing")
    if "VALUE=DATE" not in ics:
        problems.append("all-day VALUE=DATE missing")

    if problems:
        print("selftest FAILED", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(
        "selftest ok: 3 events, all lines <= 75 octets, CRLF intact, "
        "escaping + TZID + all-day correct"
    )
    return 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an .ics calendar file from a JSON schedule."
    )
    parser.add_argument("input", nargs="?", help="input JSON path, or '-' for stdin")
    parser.add_argument("output", nargs="?", help="output .ics path (default: stdout)")
    parser.add_argument("--selftest", action="store_true", help="run sanity checks and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.selftest:
        return selftest()

    try:
        raw = read_input(args.input)
        data = json.loads(raw)
        ics = build_calendar(data)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1
    except IcsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    emit(ics, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
