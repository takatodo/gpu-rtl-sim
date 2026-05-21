#!/usr/bin/env python3
"""JSON shim for the planned Verilator --sim-accel sidecar-gpu option."""

from __future__ import annotations

import argparse
import json
import sys

from hybrid_benchmark_efficiency import efficiency_estimate
from hybrid_benchmark_sidecar_plan import sidecar_stage_plan
from verilator_sidecar_options import resolve_sidecar_shape, validate_sim_accel_mode


TOOL = "src/tools/verilator_sidecar_shim.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emit the non-executing JSON plan a future Verilator --sim-accel "
            "sidecar-gpu implementation would need."
        )
    )
    parser.add_argument("--target", required=True, help="Supported benchmark target name.")
    parser.add_argument("--shape", help="Legacy NxS shape spelling.")
    parser.add_argument(
        "--sim-accel",
        default="sidecar-gpu",
        choices=("sidecar-gpu",),
        help="Planned Verilator accelerator option. Currently only sidecar-gpu is supported.",
    )
    parser.add_argument("--sim-accel-states", help="Independent state count.")
    parser.add_argument("--sim-accel-steps", help="Eval steps per state.")
    parser.add_argument("--sim-accel-shape", help="Compact NxS compatibility spelling.")
    parser.add_argument(
        "--mode",
        default="template",
        choices=("template", "resident-state-reuse", "persistent-resident-state-abi"),
        help="Benchmark mode to plan. Only template is ready for the option shim.",
    )
    parser.add_argument("--phases", type=int, default=4, help="Phase count for non-template modes.")
    parser.add_argument("--limit", type=int, help="Dataset limit for dataset-backed targets.")
    return parser


def shim_report(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    validate_sim_accel_mode(args.sim_accel)
    shape = resolve_sidecar_shape(
        shape=args.shape,
        sim_accel_shape=args.sim_accel_shape,
        sim_accel_states=args.sim_accel_states,
        sim_accel_steps=args.sim_accel_steps,
    )
    plan = sidecar_stage_plan(target=args.target, shape=shape, mode=args.mode)
    readiness = plan.get("verilator_option_readiness")
    ready = isinstance(readiness, dict) and readiness.get("status") == "ready_for_verilator_option_shim"
    status = "ready_for_verilator_option_shim" if ready else "not_ready_for_verilator_option_shim"
    report = {
        "schema_version": 1,
        "tool": TOOL,
        "status": status,
        "target": args.target,
        "shape": shape,
        "limit": args.limit,
        "mode": args.mode,
        "phases": args.phases,
        "sim_accel": args.sim_accel,
        "exit_code": 0 if ready else 2,
        "efficiency_estimate": efficiency_estimate(
            target=args.target,
            shape=shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
        ),
        "sidecar_stage_plan": plan,
        "non_claims": [
            "shim emits a non-executing plan only",
            "shim readiness does not mean Verilator itself implements --sim-accel",
            "coverage-output equivalence remains separate from performance estimates",
        ],
    }
    return (0 if ready else 2), report


def error_report(exc: Exception) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool": TOOL,
        "status": "error",
        "exit_code": 1,
        "error": str(exc),
        "non_claims": [
            "error output is not a sidecar execution result",
            "error output is not correctness or timing evidence",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code, report = shim_report(args)
    except Exception as exc:
        print(json.dumps(error_report(exc), indent=2), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
