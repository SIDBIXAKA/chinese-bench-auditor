"""Allow execution via `python -m bench_auditor`."""

from bench_auditor.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
