"""plan-to-ics: generate RFC 5545 .ics calendar files from a JSON schedule."""

from .generate import IcsError, __version__, build_calendar, main

__all__ = ["IcsError", "__version__", "build_calendar", "main"]
