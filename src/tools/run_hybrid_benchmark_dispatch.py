from __future__ import annotations

import argparse
import json
from pathlib import Path

from hybrid_benchmark import (
    print_efficiency_estimate,
    print_preflight,
    print_target_list,
    print_verilator_option_preview,
    run_benchmark,
    write_summary,
)
from hybrid_benchmark_specs import BENCHMARKS, KIND_SLICE_TEMPLATE
from hybrid_benchmark_minimal_suite import minimal_bench_suite_report, run_minimal_bench_suite
from run_hybrid_benchmark_print_modes import run_print_only_mode
from verilator_sidecar_options import normalize_benchmark_sidecar_options, operator_entrypoint_metadata


def display_path(path: Path) -> Path | str:
    return path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path


def operator_entrypoint_for_args(args: argparse.Namespace) -> dict[str, object]:
    return operator_entrypoint_metadata(
        shape=args.shape,
        sim_accel=args.sim_accel,
        sim_accel_shape=args.sim_accel_shape,
        sim_accel_states=args.sim_accel_states,
        sim_accel_steps=args.sim_accel_steps,
        sidecar_gpu=args.sidecar_gpu,
    )


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


def normalize_args(args: argparse.Namespace) -> bool:
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
    return explicit_estimate_output


def run_preflight(args: argparse.Namespace, explicit_estimate_output: bool) -> bool:
    if not args.preflight:
        return False
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
    return True


def run_summary_from_existing(args: argparse.Namespace) -> bool:
    if not args.summary_from_existing:
        return False
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
    return True


def run_benchmark_mode(args: argparse.Namespace) -> None:
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


def run_with_args(args: argparse.Namespace) -> None:
    if args.minimal_bench_suite:
        print(json.dumps(minimal_bench_suite_report(), indent=2))
        return
    if args.run_minimal_bench_suite:
        report = run_minimal_bench_suite()
        print(json.dumps(report, indent=2))
        if report.get("status") != "passed":
            raise ValueError("minimal bench suite failed")
        return
    if args.list_targets:
        print_target_list(view=args.target)
        return
    if args.target is None:
        raise ValueError("target is required unless --list-targets is used")
    explicit_estimate_output = normalize_args(args)
    operator_entrypoint = operator_entrypoint_for_args(args)
    if run_print_only_mode(args, explicit_estimate_output, operator_entrypoint=operator_entrypoint):
        return
    if run_preflight(args, explicit_estimate_output):
        return
    if run_summary_from_existing(args):
        return
    run_benchmark_mode(args)
