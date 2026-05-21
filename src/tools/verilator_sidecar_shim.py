#!/usr/bin/env python3
"""JSON shim for the planned Verilator --sim-accel sidecar-gpu option."""

from __future__ import annotations

import argparse
import json
import shlex
import sys

from hybrid_benchmark_efficiency import efficiency_estimate
from hybrid_benchmark_sidecar_plan import select_sidecar_stage, sidecar_stage_plan
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
    parser.add_argument(
        "--stage",
        help=(
            "Select one sidecar stage by name, for example gpu_artifact_build "
            "or hybrid_sidecar_run. The shim still does not execute it."
        ),
    )
    parser.add_argument(
        "--emit-command",
        action="store_true",
        help="Include the selected stage command as a top-level field. Requires --stage.",
    )
    parser.add_argument(
        "--emit-verilator-command",
        action="store_true",
        help="Include the synthesized future Verilator --sim-accel command without executing it.",
    )
    parser.add_argument(
        "--print-verilator-command",
        action="store_true",
        help="Print only the synthesized future Verilator command when ready. Does not execute it.",
    )
    return parser


def _stage_details(stage: dict[str, object] | None) -> dict[str, object]:
    details = stage.get("details", {}) if isinstance(stage, dict) else {}
    return details if isinstance(details, dict) else {}


def _synthesized_verilator_command_argv(plan: dict[str, object]) -> list[str]:
    verilator_build = select_sidecar_stage(plan, "verilator_build")
    hybrid_run = select_sidecar_stage(plan, "hybrid_sidecar_run")
    build_details = _stage_details(verilator_build)
    run_details = _stage_details(hybrid_run)
    return [
        "verilator",
        "--cc",
        "--timing",
        "-Mdir",
        str(build_details["mdir"]),
        *[str(arg) for arg in build_details.get("verilator_args", [])],
        *[str(path) for path in build_details.get("source_files", [])],
        "--top-module",
        str(build_details["top_module"]),
        "--sim-accel",
        "sidecar-gpu",
        "--sim-accel-states",
        str(run_details["nstates"]),
        "--sim-accel-steps",
        str(run_details["steps"]),
    ]


def shim_report(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    validate_sim_accel_mode(args.sim_accel)
    if args.emit_command and args.stage is None:
        raise ValueError("--emit-command requires --stage")
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
    selected_stage = select_sidecar_stage(plan, args.stage) if ready else None
    emit_verilator_command = bool(args.emit_verilator_command or args.print_verilator_command)
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
        "selected_stage": selected_stage,
        "command_emitted": bool(args.emit_command),
        "verilator_command_requested": emit_verilator_command,
        "verilator_command_emitted": bool(emit_verilator_command and ready),
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
            "emitted stage commands are printed but not executed",
            "synthesized Verilator commands are printed but not executed",
        ],
    }
    if args.emit_command:
        assert selected_stage is not None
        report["emitted_command"] = selected_stage["command"]
        report["emitted_stage"] = selected_stage["stage"]
        report["selected_stage_command"] = selected_stage["command"]
    if emit_verilator_command and ready:
        command_argv = _synthesized_verilator_command_argv(plan)
        report["verilator_command_argv"] = command_argv
        report["verilator_command"] = shlex.join(command_argv)
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
    if args.print_verilator_command and exit_code == 0:
        print(report["verilator_command"])
        return 0
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
