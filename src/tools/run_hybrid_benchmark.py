#!/usr/bin/env python3
from __future__ import annotations

import sys

from run_hybrid_benchmark_args import build_parser
from run_hybrid_benchmark_dispatch import (
    display_path,
    operator_entrypoint_for_args,
    run_with_args,
    validate_sidecar_shape_hint,
    write_summary_for_args,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run_with_args(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
