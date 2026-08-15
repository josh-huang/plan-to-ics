#!/usr/bin/env python3
"""Thin launcher for the plan_to_ics generator package.

The real implementation lives in the ``plan_to_ics`` package. This shim keeps
the skill's documented `python scripts/generate_ics.py <in> <out>` path working
whether the package is pip-installed or bundled at the plugin/repo root.
"""
import sys
from pathlib import Path


def _load_main():
    try:
        from plan_to_ics.generate import main
        return main
    except ModuleNotFoundError:
        # Plugin install: the package sits at the plugin (repo) root, three
        # levels up from scripts/ (scripts -> <skill> -> skills -> root).
        root = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(root))
        try:
            from plan_to_ics.generate import main
            return main
        except ModuleNotFoundError:
            sys.exit(
                "The plan_to_ics package is not installed.\n"
                "Install it first:\n"
                "    pip install plan-to-ics     # or:\n"
                "    pip install -e .            # from the repo root"
            )


if __name__ == "__main__":
    raise SystemExit(_load_main()())
