#!/usr/bin/env python3
"""Debug JSON shim for the planned Verilator --sim-accel sidecar-gpu option."""

from __future__ import annotations

import argparse
import json
import shlex
import sys

from hybrid_benchmark_catalog import operator_discovery_hint
from hybrid_benchmark_efficiency import efficiency_estimate, format_efficiency_estimate
from hybrid_benchmark_sidecar_plan import (
    format_sidecar_operator_plan,
    select_sidecar_stage,
    sidecar_handoff_contract,
    sidecar_operator_plan,
    sidecar_stage_plan,
    synthesized_verilator_command_argv,
)
from hybrid_benchmark_specs import (
    JSON_FLOW_ROLE_DEBUG_INSPECTION,
    SIDECAR_ACCEL,
    STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_READY_FOR_VERILATOR_OPTION_SHIM,
)
from verilator_sidecar_options import normalize_shim_sidecar_options


TOOL = "src/tools/verilator_sidecar_shim.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emit debug JSON for the non-executing plan a future Verilator "
            "--sim-accel sidecar-gpu implementation would need."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-verilator-command
  python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-estimate-command
  python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel-shape 64x1 --emit-verilator-command
  python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel-shape 64x1 --sim-accel-estimate-efficiency
  python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-operator-plan
  python3 src/tools/verilator_sidecar_shim.py --target mobile_vit --limit 128 --stage host_preprocess --emit-command
  python3 src/tools/verilator_sidecar_shim.py --target pulp_ita_mha --sim-accel-states 1 --sim-accel-steps 64 --mode resident-state-reuse --stage resident_state_reuse_workflow --emit-command

notes:
  Ready template targets return exit code 0 for command previews.
  Not-ready stage examples still emit JSON stage commands and return exit code 2.
  JSON output is for debug/inspection, not the runtime ABI.
  No mode executes benchmark commands from this shim.
""",
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
        "--print-verilator-estimate-command",
        action="store_true",
        help=(
            "Print only the synthesized future Verilator command with "
            "--sim-accel-estimate-efficiency when ready. Does not execute it."
        ),
    )
    parser.add_argument(
        "--print-efficiency-estimate",
        action="store_true",
        help="Print only the human-readable efficiency estimate. Does not execute commands.",
    )
    parser.add_argument(
        "--sim-accel-estimate-efficiency",
        action="store_true",
        help="Verilator-compatible alias for --print-efficiency-estimate. Does not execute commands.",
    )
    parser.add_argument(
        "--print-operator-plan",
        action="store_true",
        help="Print the synthesized command plus efficiency estimate when ready. Does not execute commands.",
    )
    return parser


def shim_report(args: argparse.Namespace) -> tuple[int, dict[str, object]]:
    if args.emit_command and args.stage is None:
        raise ValueError("--emit-command requires --stage")
    sidecar_options = normalize_shim_sidecar_options(
        shape=args.shape,
        sim_accel=args.sim_accel,
        sim_accel_shape=args.sim_accel_shape,
        sim_accel_states=args.sim_accel_states,
        sim_accel_steps=args.sim_accel_steps,
        emit_verilator_command=args.emit_verilator_command,
        print_verilator_command=args.print_verilator_command,
        print_verilator_estimate_command=args.print_verilator_estimate_command,
        print_efficiency_estimate=args.print_efficiency_estimate,
        sim_accel_estimate_efficiency=args.sim_accel_estimate_efficiency,
        print_operator_plan=args.print_operator_plan,
    )
    shape = sidecar_options.shape
    plan = sidecar_stage_plan(target=args.target, shape=shape, limit=args.limit, mode=args.mode, phases=args.phases)
    readiness = plan.get("verilator_option_readiness")
    ready = isinstance(readiness, dict) and readiness.get("status") == STATUS_READY_FOR_VERILATOR_OPTION_SHIM
    status = STATUS_READY_FOR_VERILATOR_OPTION_SHIM if ready else STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM
    selected_stage = select_sidecar_stage(plan, args.stage) if args.stage is not None else None
    emit_verilator_command = sidecar_options.emit_verilator_command
    report = {
        "schema_version": 1,
        "schema_role": "verilator_sidecar_debug_plan",
        "json_flow_role": JSON_FLOW_ROLE_DEBUG_INSPECTION,
        "runtime_abi": False,
        "execution_authority": False,
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
            "shim JSON is debug/inspection output only",
            "shim JSON is not the runtime ABI",
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
        discovery_hint = operator_discovery_hint(target=args.target, requested_shape=shape)
        report["discovery_hint"] = discovery_hint
        report["operator_plan"] = sidecar_operator_plan(
            command_argv=command_argv,
            command=report["verilator_command"],
            efficiency_estimate=report["efficiency_estimate"],
            handoff_contract=sidecar_handoff_contract(plan),
            discovery_hint=discovery_hint,
        )
        report["verilator_estimate_command_argv"] = report["operator_plan"]["estimate_command_argv"]
        report["verilator_estimate_command"] = report["operator_plan"]["estimate_command"]
    return (0 if ready else 2), report


def error_report(exc: Exception) -> dict[str, object]:
    return {
        "schema_version": 1,
        "schema_role": "verilator_sidecar_debug_error",
        "json_flow_role": "debug_inspection",
        "runtime_abi": False,
        "execution_authority": False,
        "tool": TOOL,
        "status": "error",
        "exit_code": 1,
        "error": str(exc),
        "non_claims": [
            "error JSON is debug/inspection output only",
            "error JSON is not the runtime ABI",
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
    if args.print_verilator_estimate_command and exit_code == 0:
        print(report["verilator_estimate_command"])
        return 0
    if args.print_efficiency_estimate or args.sim_accel_estimate_efficiency:
        print(format_efficiency_estimate(report["efficiency_estimate"]))
        return exit_code
    if args.print_operator_plan and exit_code == 0:
        print(format_sidecar_operator_plan(report["operator_plan"]))
        return 0
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
