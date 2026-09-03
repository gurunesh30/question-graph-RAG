"""Thin entrypoint that delegates to ``kaqg.cli:main``."""
from kaqg.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
