"""Timezone validation must run before values reach iCalendar content lines."""

import json
import subprocess
import sys
import unittest

from plan_to_ics.generate import IcsError, build_calendar


class TimezoneTests(unittest.TestCase):
    def calendar(self, **overrides):
        event = {
            "summary": "Meeting",
            "start": "2026-11-13T09:00",
            "end": "2026-11-13T10:00",
        }
        event.update(overrides)
        return {"events": [event]}

    def test_rejects_invalid_calendar_and_event_timezones(self):
        for timezone in (
            "Asia/Singaproe",
            "Asia/Singapore\r\nBEGIN:VEVENT",
            "Asia/Singapore;VALUE=DATE",
            "",
            False,
            42,
        ):
            for scope in ("calendar", "event"):
                with self.subTest(timezone=timezone, scope=scope):
                    data = self.calendar()
                    target = data if scope == "calendar" else data["events"][0]
                    target["timezone"] = timezone
                    with self.assertRaises(IcsError):
                        build_calendar(data)

    def test_valid_timezone_and_event_override(self):
        data = self.calendar(timezone="UTC")
        data["timezone"] = "Asia/Singapore"
        ics = build_calendar(data)
        self.assertIn("X-WR-TIMEZONE:Asia/Singapore\r\n", ics)
        self.assertIn("DTSTART;TZID=UTC:20261113T090000\r\n", ics)
        self.assertIn("DTEND;TZID=UTC:20261113T100000\r\n", ics)

    def test_floating_time_and_null_override(self):
        for has_default in (False, True):
            data = self.calendar(timezone=None)
            if has_default:
                data["timezone"] = "Asia/Singapore"
            with self.subTest(has_default=has_default):
                ics = build_calendar(data)
                self.assertIn("DTSTART:20261113T090000\r\n", ics)
                self.assertNotIn("TZID=", ics)

    def test_timezone_does_not_change_all_day_dates(self):
        data = self.calendar(start="2026-11-13", end="2026-11-14")
        data["timezone"] = "Asia/Singapore"
        ics = build_calendar(data)
        self.assertIn("DTSTART;VALUE=DATE:20261113\r\n", ics)
        self.assertNotIn("TZID=", ics)

    def test_cli_reports_invalid_timezone_without_calendar_output(self):
        data = self.calendar(timezone="Asia/Singaproe")
        result = subprocess.run(
            [sys.executable, "-m", "plan_to_ics"],
            input=json.dumps(data),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("unknown timezone", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
