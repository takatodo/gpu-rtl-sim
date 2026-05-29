#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hybrid_template_efficiency import format_template_efficiency_report, template_efficiency_report
from hybrid_template_runner import load_template_plan, run_plan, validate_source_closure_for_execution


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a slice_launch_template through Verilator --cc, host probe, "
            "GPU cubin build, hybrid launch, and coverage-output compare."
        )
    )
    parser.add_argument("template", type=Path, help="config/slice_launch_templates/<target>.json")
    parser.add_argument(
        "--shape",
        default="1x1",
        help="State/step shape formatted as NxS, for example 64x1 or 1x64.",
    )
    parser.add_argument("--cfg-batch-length", type=int, default=64)
    parser.add_argument("--cfg-reset-cycles", type=int, default=2)
    parser.add_argument("--cfg-drain-cycles", type=int, default=8)
    parser.add_argument("--cfg-seed", type=int, default=1)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated commands without executing them.",
    )
    parser.add_argument(
        "--estimate-efficiency",
        action="store_true",
        help="Print a short human-readable efficiency estimate after the command plan.",
    )
    parser.add_argument(
        "--estimate-efficiency-json",
        action="store_true",
        help="Print the efficiency estimate as JSON after the command plan.",
    )
    args = parser.parse_args(argv)

    try:
        plan = load_template_plan(
            args.template,
            shape=args.shape,
            cfg_batch_length=args.cfg_batch_length,
            cfg_reset_cycles=args.cfg_reset_cycles,
            cfg_drain_cycles=args.cfg_drain_cycles,
            cfg_seed=args.cfg_seed,
        )
        if not args.dry_run:
            validate_source_closure_for_execution(plan)
        run_plan(plan, dry_run=args.dry_run)
        if args.estimate_efficiency or args.estimate_efficiency_json:
            report = template_efficiency_report(plan)
            if args.estimate_efficiency_json:
                print("# efficiency_estimate_json")
                print(json.dumps(report, indent=2))
            else:
                print(format_template_efficiency_report(report))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
