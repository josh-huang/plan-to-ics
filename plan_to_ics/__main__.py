"""Allow ``python -m plan_to_ics`` to run the CLI."""

from .generate import main

if __name__ == "__main__":
    raise SystemExit(main())
