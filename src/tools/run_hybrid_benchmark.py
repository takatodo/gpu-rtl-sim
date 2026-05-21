#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hybrid_benchmark import (
    print_efficiency_estimate,
    print_operator_plan,
    print_preflight,
    print_target_list,
    run_benchmark,
    write_summary,
)
from verilator_sidecar_options import resolve_sidecar_shape, validate_sim_accel_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one supported hybrid RTL benchmark with a Verilator-like target/shape interface."
    )
    parser.add_argument("target", nargs="?", help="Benchmark target, e.g. pulp_ita_mha, paged_attention_kv_score, mobile_vit.")
    parser.add_argument("--shape", help="Shape for RTL slice-template targets, e.g. 64x1 or 1x64.")
    parser.add_argument(
        "--sim-accel",
        choices=("sidecar-gpu",),
        help="Verilator-compatible accelerator spelling. Currently supports sidecar-gpu.",
    )
    parser.add_argument(
        "--sim-accel-states",
        help="Verilator-compatible independent state count. Use with --sim-accel-steps.",
    )
    parser.add_argument(
        "--sim-accel-steps",
        help="Verilator-compatible eval steps per state. Use with --sim-accel-states.",
    )
    parser.add_argument(
        "--sim-accel-shape",
        help="Compact compatibility spelling for --sim-accel-states N --sim-accel-steps S, e.g. 64x1.",
    )
    parser.add_argument(
        "--sim-accel-estimate-efficiency",
        action="store_true",
        help="Verilator-compatible alias for --estimate-efficiency.",
    )
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
    parser.add_argument(
        "--estimate-efficiency",
        action="store_true",
        help="Print a short human-readable efficiency estimate after planning or execution.",
    )
    parser.add_argument(
        "--estimate-efficiency-json",
        action="store_true",
        help="Print the efficiency estimate as JSON after planning or execution.",
    )
    parser.add_argument(
        "--sidecar-gpu",
        action="store_true",
        help=(
            "Use the existing hybrid sidecar GPU benchmark flow and print the "
            "human-readable efficiency estimate."
        ),
    )
    parser.add_argument(
        "--print-operator-plan",
        action="store_true",
        help="Print the synthesized Verilator sidecar command and efficiency estimate without executing commands.",
    )
    parser.add_argument("--list-targets", action="store_true", help="Print supported benchmark targets and exit.")
    return parser


def display_path(path: Path) -> Path | str:
    return path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path


def write_summary_for_args(args: argparse.Namespace, execution_mode: str) -> Path:
    summary_path = None if args.summary_out in (None, "auto") else Path(args.summary_out)
    return write_summary(
        path=summary_path,
        target=args.target,
        shape=args.shape,
        limit=args.limit,
        mode=args.mode,
        phases=args.phases,
        execution_mode=execution_mode,
    )


def run_with_args(args: argparse.Namespace) -> None:
    if args.list_targets:
        print_target_list()
        return
    if args.target is None:
        raise ValueError("target is required unless --list-targets is used")
    validate_sim_accel_mode(args.sim_accel)
    explicit_sidecar_gpu = args.sidecar_gpu
    sim_accel_sidecar_gpu = args.sim_accel == "sidecar-gpu"
    args.shape = resolve_sidecar_shape(
        shape=args.shape,
        sim_accel_shape=args.sim_accel_shape,
        sim_accel_states=args.sim_accel_states,
        sim_accel_steps=args.sim_accel_steps,
    )
    if sim_accel_sidecar_gpu and not args.preflight:
        args.sidecar_gpu = True
    if args.sim_accel_estimate_efficiency:
        args.estimate_efficiency = True
    if args.sidecar_gpu and not args.estimate_efficiency_json:
        args.estimate_efficiency = True
    if args.print_operator_plan:
        if args.preflight or args.dry_run or args.summary_from_existing or args.summary_out is not None:
            raise ValueError("--print-operator-plan cannot be combined with execution, preflight, or summary options")
        print_operator_plan(target=args.target, shape=args.shape, limit=args.limit, mode=args.mode, phases=args.phases)
        return
    if args.preflight:
        if args.summary_from_existing:
            raise ValueError("--summary-from-existing cannot be combined with --preflight")
        if explicit_sidecar_gpu or args.estimate_efficiency or args.estimate_efficiency_json:
            raise ValueError("--estimate-efficiency cannot be combined with --preflight")
        print_preflight(target=args.target, shape=args.shape, limit=args.limit, mode=args.mode, phases=args.phases)
        return
    if args.summary_from_existing:
        if args.dry_run:
            raise ValueError("--summary-from-existing cannot be combined with --dry-run")
        written = write_summary_for_args(args, execution_mode="existing_evidence")
        print(f"+ write {display_path(written)}")
        if args.estimate_efficiency or args.estimate_efficiency_json:
            print_efficiency_estimate(
                target=args.target,
                shape=args.shape,
                limit=args.limit,
                mode=args.mode,
                phases=args.phases,
                as_json=args.estimate_efficiency_json,
            )
        return

    run_benchmark(
        target=args.target,
        shape=args.shape,
        limit=args.limit,
        mode=args.mode,
        phases=args.phases,
        dry_run=args.dry_run,
    )
    if args.summary_out is not None:
        written = write_summary_for_args(args, execution_mode="dry_run" if args.dry_run else "executed")
        print(f"+ write {display_path(written)}")
    if args.estimate_efficiency or args.estimate_efficiency_json:
        print_efficiency_estimate(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            as_json=args.estimate_efficiency_json,
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
