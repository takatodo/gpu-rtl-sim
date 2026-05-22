"""Operator-facing helpers for Verilator sidecar GPU plans."""

from __future__ import annotations

import shlex

from hybrid_benchmark_catalog import compatibility_entrypoint_for_shape
from hybrid_benchmark_efficiency import format_efficiency_estimate
from hybrid_benchmark_specs import CORRECTNESS_POLICY_COVERAGE_OUTPUT, SIDECAR_ACCEL


SIM_ACCEL_ESTIMATE_EFFICIENCY_FLAG = "--sim-accel-estimate-efficiency"


def select_sidecar_stage(plan: dict[str, object], stage_name: str | None) -> dict[str, object] | None:
    if stage_name is None:
        return None
    stages = plan.get("stages", [])
    if not isinstance(stages, list):
        raise ValueError(f"stage is not available for this plan: {stage_name}")
    for stage in stages:
        if isinstance(stage, dict) and stage.get("stage") == stage_name:
            return stage
    available = [str(stage.get("stage")) for stage in stages if isinstance(stage, dict)]
    suffix = f"; available stages: {', '.join(available)}" if available else ""
    raise ValueError(f"unknown sidecar stage: {stage_name}{suffix}")


def selected_stage_details(stage: dict[str, object] | None) -> dict[str, object]:
    details = stage.get("details", {}) if isinstance(stage, dict) else {}
    return details if isinstance(details, dict) else {}


def synthesized_verilator_command_argv(plan: dict[str, object]) -> list[str]:
    verilator_build = select_sidecar_stage(plan, "verilator_build")
    hybrid_run = select_sidecar_stage(plan, "hybrid_sidecar_run")
    build_details = selected_stage_details(verilator_build)
    run_details = selected_stage_details(hybrid_run)
    return [
        "verilator",
        "--cc",
        "--timing",
        "-Mdir",
        str(build_details["mdir"]),
        *[f"-D{define}" for define in build_details.get("verilator_defines", [])],
        *[str(arg) for arg in build_details.get("verilator_args", [])],
        *[str(path) for path in build_details.get("source_files", [])],
        "--top-module",
        str(build_details["top_module"]),
        "--sim-accel",
        SIDECAR_ACCEL,
        "--sim-accel-states",
        str(run_details["nstates"]),
        "--sim-accel-steps",
        str(run_details["steps"]),
    ]


def synthesized_verilator_estimate_command_argv(command_argv: list[str]) -> list[str]:
    return [*command_argv, SIM_ACCEL_ESTIMATE_EFFICIENCY_FLAG]


def sidecar_handoff_contract(plan: dict[str, object]) -> dict[str, object]:
    hybrid_run = select_sidecar_stage(plan, "hybrid_sidecar_run")
    compare = select_sidecar_stage(plan, "coverage_output_compare")
    run_details = selected_stage_details(hybrid_run)
    compare_details = selected_stage_details(compare)
    nstates = run_details["nstates"]
    steps = run_details["steps"]
    return {
        "schema_version": 1,
        "state_authority": "cpu_init_state_to_hybrid_candidate_dump",
        "shape": f"{nstates}x{steps}",
        "nstates": nstates,
        "steps": steps,
        "state_files": {
            "init_state": run_details["init_state"],
            "reference_dump": compare_details["reference_dump"],
            "candidate_dump": compare_details["candidate_dump"],
        },
        "compare": {
            "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
            "acceptance_policy": compare_details["acceptance_policy"],
            "reference_label": compare_details["reference_label"],
            "candidate_label": compare_details["candidate_label"],
            "coverage_output_target": compare_details["coverage_output_target"],
        },
        "generated_reports": {
            "compare_report": compare_details["json_out"],
        },
        "non_claims": [
            "handoff contract does not execute commands",
            "handoff contract is not correctness or timing evidence",
            "coverage-output equivalence remains separate from raw full-state equality",
        ],
    }


def sidecar_operator_plan(
    *,
    command_argv: list[str],
    command: str,
    efficiency_estimate: dict[str, object],
    handoff_contract: dict[str, object],
    discovery_hint: dict[str, object] | None = None,
) -> dict[str, object]:
    estimate_command_argv = synthesized_verilator_estimate_command_argv(command_argv)
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "planned",
        "command_argv": command_argv,
        "command": command,
        "estimate_command_argv": estimate_command_argv,
        "estimate_command": shlex.join(estimate_command_argv),
        "estimate_flag": SIM_ACCEL_ESTIMATE_EFFICIENCY_FLAG,
        "requested_compatibility_entrypoint": compatibility_entrypoint_for_shape(str(handoff_contract["shape"])),
        "efficiency_estimate": efficiency_estimate,
        "handoff_contract": handoff_contract,
        "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
        "non_claims": [
            "operator plan does not execute commands",
            "operator plan is not correctness or timing evidence",
            "coverage-output equivalence remains separate from performance estimates",
        ],
    }
    if discovery_hint is not None:
        report["discovery_hint"] = discovery_hint
    return report


def format_sidecar_operator_plan(operator_plan: dict[str, object]) -> str:
    lines = [
        "# verilator_sidecar_operator_plan",
        "command:",
        str(operator_plan["command"]),
        "estimate_command:",
        str(operator_plan["estimate_command"]),
        f"requested_compatibility_entrypoint: {operator_plan['requested_compatibility_entrypoint']}",
        f"estimate_flag: {operator_plan['estimate_flag']}",
        f"correctness_policy: {operator_plan['correctness_policy']}",
        "operator_plan_non_claims:",
    ]
    lines.extend(f"- {item}" for item in operator_plan["non_claims"])
    lines.append(format_efficiency_estimate(operator_plan["efficiency_estimate"]))
    return "\n".join(lines)
