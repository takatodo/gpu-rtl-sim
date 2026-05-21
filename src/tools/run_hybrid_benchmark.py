#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hybrid_benchmark import (
    print_efficiency_estimate,
    print_operator_plan,
    print_operator_plan_json,
    print_preflight,
    print_target_list,
    print_verilator_efficiency_estimate,
    print_verilator_estimate_command,
    print_verilator_command,
    print_verilator_option_preview,
    run_benchmark,
    write_summary,
)
from hybrid_benchmark_specs import BENCHMARKS, KIND_SLICE_TEMPLATE
from verilator_sidecar_options import normalize_benchmark_sidecar_options, operator_entrypoint_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one supported hybrid RTL benchmark with a Verilator-like target/shape interface.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
epilog="""examples:
  python3 src/tools/run_hybrid_benchmark.py --list-targets
  python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --sidecar-gpu --dry-run
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --sidecar-gpu --preflight
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --sim-accel-estimate-efficiency --dry-run
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-command
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-estimate-command
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-efficiency-estimate
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
  python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json

notes:
  --print-verilator-command, --print-verilator-estimate-command, --print-efficiency-estimate, --print-operator-plan, and --operator-plan-json do not execute commands.
  --sim-accel-estimate-efficiency follows the normal execution or --dry-run path; use --print-efficiency-estimate for estimate-only preview.
  coverage_output_equivalence remains the correctness policy; efficiency output is separate.
""",
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
        help="Verilator-compatible alias for --estimate-efficiency after normal execution or --dry-run.",
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
        "--print-verilator-command",
        action="store_true",
        help="Print only the synthesized future Verilator sidecar command without executing commands.",
    )
    parser.add_argument(
        "--print-verilator-estimate-command",
        action="store_true",
        help=(
            "Print only the synthesized future Verilator sidecar command with "
            "--sim-accel-estimate-efficiency without executing commands."
        ),
    )
    parser.add_argument(
        "--print-efficiency-estimate",
        action="store_true",
        help="Print only the human-readable efficiency estimate without executing commands.",
    )
    parser.add_argument(
        "--print-operator-plan",
        action="store_true",
        help="Print the synthesized Verilator sidecar command and efficiency estimate without executing commands.",
    )
    parser.add_argument(
        "--operator-plan-json",
        action="store_true",
        help="Print the synthesized Verilator sidecar operator plan as JSON without executing commands.",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="Print supported benchmark targets and exit. Optional view: sidecar_gpu.",
    )
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
        operator_entrypoint=operator_entrypoint_for_args(args),
    )


def operator_entrypoint_for_args(args: argparse.Namespace) -> dict[str, object]:
    return operator_entrypoint_metadata(
        shape=args.shape,
        sim_accel=args.sim_accel,
        sim_accel_shape=args.sim_accel_shape,
        sim_accel_states=args.sim_accel_states,
        sim_accel_steps=args.sim_accel_steps,
        sidecar_gpu=args.sidecar_gpu,
    )


def validate_sidecar_shape_hint(args: argparse.Namespace) -> None:
    if args.shape is not None:
        return
    if not (args.sidecar_gpu or args.sim_accel == "sidecar-gpu"):
        return
    spec = BENCHMARKS.get(args.target)
    if spec is None or spec.kind != KIND_SLICE_TEMPLATE:
        return
    raise ValueError(
        f"{args.target} requires a shape for sidecar GPU planning; use "
        "--sim-accel-states N --sim-accel-steps S, --sim-accel-shape NxS, or --shape NxS"
    )


def run_with_args(args: argparse.Namespace) -> None:
    if args.list_targets:
        print_target_list(view=args.target)
        return
    if args.target is None:
        raise ValueError("target is required unless --list-targets is used")
    explicit_estimate_output = (
        args.estimate_efficiency or args.estimate_efficiency_json or args.sim_accel_estimate_efficiency
    )
    sidecar_options = normalize_benchmark_sidecar_options(
        shape=args.shape,
        sim_accel=args.sim_accel,
        sim_accel_shape=args.sim_accel_shape,
        sim_accel_states=args.sim_accel_states,
        sim_accel_steps=args.sim_accel_steps,
        sim_accel_estimate_efficiency=args.sim_accel_estimate_efficiency,
        sidecar_gpu=args.sidecar_gpu,
        estimate_efficiency=args.estimate_efficiency,
        estimate_efficiency_json=args.estimate_efficiency_json,
        preflight=args.preflight,
    )
    args.shape = sidecar_options.shape
    args.sidecar_gpu = sidecar_options.sidecar_gpu
    args.estimate_efficiency = sidecar_options.estimate_efficiency
    args.estimate_efficiency_json = sidecar_options.estimate_efficiency_json
    validate_sidecar_shape_hint(args)
    print_only_modes = [
        args.print_verilator_command,
        args.print_verilator_estimate_command,
        args.print_efficiency_estimate,
        args.print_operator_plan,
        args.operator_plan_json,
    ]
    if sum(1 for enabled in print_only_modes if enabled) > 1:
        raise ValueError(
            "--print-verilator-command, --print-verilator-estimate-command, "
            "--print-efficiency-estimate, --print-operator-plan, and --operator-plan-json are mutually exclusive"
        )
    if args.print_verilator_command:
        if args.preflight or args.dry_run or args.summary_from_existing or args.summary_out is not None:
            raise ValueError("--print-verilator-command cannot be combined with execution, preflight, or summary options")
        if explicit_estimate_output:
            raise ValueError(
                "--print-verilator-command cannot be combined with estimate output flags; "
                "use --print-verilator-estimate-command"
            )
        exit_code = print_verilator_command(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint_for_args(args),
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return
    if args.print_verilator_estimate_command:
        if args.preflight or args.dry_run or args.summary_from_existing or args.summary_out is not None:
            raise ValueError(
                "--print-verilator-estimate-command cannot be combined with execution, preflight, or summary options"
            )
        if explicit_estimate_output:
            raise ValueError("--print-verilator-estimate-command already includes --sim-accel-estimate-efficiency")
        exit_code = print_verilator_estimate_command(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint_for_args(args),
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return
    if args.print_efficiency_estimate:
        if args.preflight or args.dry_run or args.summary_from_existing or args.summary_out is not None:
            raise ValueError("--print-efficiency-estimate cannot be combined with execution, preflight, or summary options")
        if explicit_estimate_output:
            raise ValueError(
                "--print-efficiency-estimate cannot be combined with --estimate-efficiency, "
                "--estimate-efficiency-json, or --sim-accel-estimate-efficiency"
            )
        exit_code = print_verilator_efficiency_estimate(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return
    if args.operator_plan_json:
        if args.preflight or args.dry_run or args.summary_from_existing or args.summary_out is not None:
            raise ValueError("--operator-plan-json cannot be combined with execution, preflight, or summary options")
        exit_code = print_operator_plan_json(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint_for_args(args),
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return
    if args.print_operator_plan:
        if args.preflight or args.dry_run or args.summary_from_existing or args.summary_out is not None:
            raise ValueError("--print-operator-plan cannot be combined with execution, preflight, or summary options")
        exit_code = print_operator_plan(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint_for_args(args),
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return
    if args.preflight:
        if args.summary_from_existing:
            raise ValueError("--summary-from-existing cannot be combined with --preflight")
        if explicit_estimate_output:
            raise ValueError("--estimate-efficiency cannot be combined with --preflight")
        print_preflight(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint_for_args(args),
        )
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

    if args.dry_run and args.sidecar_gpu:
        print_verilator_option_preview(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
        )
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
