#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hybrid_benchmark import print_preflight, run_benchmark, write_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one supported hybrid RTL benchmark with a Verilator-like target/shape interface."
    )
    parser.add_argument("target", help="Benchmark target, e.g. pulp_ita_mha, paged_attention_kv_score, mobile_vit.")
    parser.add_argument("--shape", help="Shape for RTL slice-template targets, e.g. 64x1 or 1x64.")
    parser.add_argument("--limit", type=int, help="Input limit for dataset-backed targets, e.g. mobile_vit --limit 128.")
    parser.add_argument(
        "--mode",
        default="template",
        choices=("template", "resident-state-reuse", "persistent-resident-state-abi"),
        help="Benchmark execution mode for targets that support more than the template flow.",
    )
    parser.add_argument("--phases", type=int, default=4, help="Phase count for resident-state-reuse or persistent modes.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    parser.add_argument("--preflight", action="store_true", help="Print a JSON plan without executing commands.")
    parser.add_argument(
        "--summary-out",
        nargs="?",
        const="auto",
        help="Write a unified benchmark summary JSON. With no path, writes under reports/.",
    )
    parser.add_argument(
        "--summary-from-existing",
        action="store_true",
        help="Write a summary from existing generated reports without running benchmark commands.",
    )
    args = parser.parse_args(argv)

    try:
        if args.preflight:
            if args.summary_from_existing:
                raise ValueError("--summary-from-existing cannot be combined with --preflight")
            print_preflight(target=args.target, shape=args.shape, limit=args.limit, mode=args.mode, phases=args.phases)
        elif args.summary_from_existing:
            if args.dry_run:
                raise ValueError("--summary-from-existing cannot be combined with --dry-run")
            summary_path = None if args.summary_out in (None, "auto") else Path(args.summary_out)
            written = write_summary(
                path=summary_path,
                target=args.target,
                shape=args.shape,
                limit=args.limit,
                mode=args.mode,
                phases=args.phases,
                execution_mode="existing_evidence",
            )
            print(f"+ write {written.relative_to(Path.cwd()) if written.is_relative_to(Path.cwd()) else written}")
        else:
            run_benchmark(
                target=args.target,
                shape=args.shape,
                limit=args.limit,
                mode=args.mode,
                phases=args.phases,
                dry_run=args.dry_run,
            )
            if args.summary_out is not None:
                summary_path = None if args.summary_out == "auto" else Path(args.summary_out)
                written = write_summary(
                    path=summary_path,
                    target=args.target,
                    shape=args.shape,
                    limit=args.limit,
                    mode=args.mode,
                    phases=args.phases,
                    execution_mode="dry_run" if args.dry_run else "executed",
                )
                print(f"+ write {written.relative_to(Path.cwd()) if written.is_relative_to(Path.cwd()) else written}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
