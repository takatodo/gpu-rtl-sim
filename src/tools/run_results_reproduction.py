#!/usr/bin/env python3
from __future__ import annotations

import sys

from results_reproduction_cli import build_parser, dispatch


def main(argv: list[str] | None = None) -> int:
    try:
        dispatch(build_parser().parse_args(argv))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
