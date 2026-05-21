#!/usr/bin/env python3
"""JSON shim for the planned Verilator --sim-accel sidecar-gpu option."""

from __future__ import annotations

import argparse
import json
import shlex
import sys

from hybrid_benchmark_efficiency import efficiency_estimate, format_efficiency_estimate
from hybrid_benchmark_sidecar_plan import (
    select_sidecar_stage,
    sidecar_operator_plan,
    sidecar_stage_plan,
    synthesized_verilator_command_argv,
)
from hybrid_benchmark_specs import (
    SIDECAR_ACCEL,
    STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_READY_FOR_VERILATOR_OPTION_SHIM,
)
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
    parser.add_argument(
        "--print-efficiency-estimate",
        action="store_true",
        help="Print only the human-readable efficiency estimate. Does not execute commands.",
    )
    parser.add_argument(
        "--print-operator-plan",
        action="store_true",
        help="Print the synthesized command plus efficiency estimate when ready. Does not execute commands.",
    )
    return parser


def shim_report(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    validate_sim_accel_mode(args.sim_accel)
    if args.emit_command and args.stage is None:
        raise ValueError("--emit-command requires --stage")
    print_only_modes = [args.print_verilator_command, args.print_efficiency_estimate, args.print_operator_plan]
    if sum(1 for enabled in print_only_modes if enabled) > 1:
        raise ValueError(
            "--print-verilator-command, --print-efficiency-estimate, and --print-operator-plan are mutually exclusive"
        )
    shape = resolve_sidecar_shape(
        shape=args.shape,
        sim_accel_shape=args.sim_accel_shape,
        sim_accel_states=args.sim_accel_states,
        sim_accel_steps=args.sim_accel_steps,
    )
    plan = sidecar_stage_plan(target=args.target, shape=shape, mode=args.mode)
    readiness = plan.get("verilator_option_readiness")
    ready = isinstance(readiness, dict) and readiness.get("status") == STATUS_READY_FOR_VERILATOR_OPTION_SHIM
    status = STATUS_READY_FOR_VERILATOR_OPTION_SHIM if ready else STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM
    selected_stage = select_sidecar_stage(plan, args.stage) if ready else None
    emit_verilator_command = bool(args.emit_verilator_command or args.print_verilator_command or args.print_operator_plan)
    report = {
        "schema_version": 1,
        "tool": TOOL,
        "status": status,
        "target": args.target,
        "shape": shape,
        "limit": args.limit,
        "mode": args.mode,
        "phases": args.phases,
        "sim_accel": args.sim_accel or SIDECAR_ACCEL,
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
        command_argv = synthesized_verilator_command_argv(plan)
        report["verilator_command_argv"] = command_argv
        report["verilator_command"] = shlex.join(command_argv)
        report["operator_plan"] = sidecar_operator_plan(
            command_argv=command_argv,
            command=report["verilator_command"],
            efficiency_estimate=report["efficiency_estimate"],
        )
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
    if args.print_efficiency_estimate:
        print(format_efficiency_estimate(report["efficiency_estimate"]))
        return exit_code
    if args.print_operator_plan and exit_code == 0:
        operator_plan = report["operator_plan"]
        print("# verilator_sidecar_operator_plan")
        print("command:")
        print(operator_plan["command"])
        print(f"correctness_policy: {operator_plan['correctness_policy']}")
        print("operator_plan_non_claims:")
        for item in operator_plan["non_claims"]:
            print(f"- {item}")
        print(format_efficiency_estimate(operator_plan["efficiency_estimate"]))
        return 0
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
