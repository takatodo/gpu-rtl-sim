#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hybrid_host_probe_builder import load_host_probe_build_plan, run_host_probe_build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the generic tlul_slice_host_probe from slice_launch_template host-probe metadata."
    )
    parser.add_argument("template", type=Path, help="config/slice_launch_templates/<target>.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        run_host_probe_build(load_host_probe_build_plan(args.template), dry_run=args.dry_run)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
