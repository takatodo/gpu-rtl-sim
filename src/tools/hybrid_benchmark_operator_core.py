"""Operator-plan data helpers for hybrid benchmark sidecar previews."""

from __future__ import annotations

import shlex

from hybrid_benchmark_catalog import MODE_TEMPLATE, operator_discovery_hint
from hybrid_benchmark_efficiency import efficiency_estimate
from hybrid_benchmark_sidecar_plan import (
    sidecar_handoff_contract,
    sidecar_operator_plan,
    sidecar_stage_plan,
    synthesized_verilator_command_argv,
)
from hybrid_benchmark_specs import (
    CORRECTNESS_POLICY_COVERAGE_OUTPUT,
    SCHEMA_ROLE_TARGET_FIRST_OPERATOR_PLAN,
    STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_READY_FOR_VERILATOR_OPTION_SHIM,
)


def operator_plan_report(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> dict[str, object]:
    plan = sidecar_stage_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    readiness = plan.get("verilator_option_readiness")
    ready = isinstance(readiness, dict) and readiness.get("status") == STATUS_READY_FOR_VERILATOR_OPTION_SHIM
    if not ready:
        raise ValueError(f"{target} is not ready for the Verilator sidecar option shim")
    command_argv = synthesized_verilator_command_argv(plan)
    return sidecar_operator_plan(
        command_argv=command_argv,
        command=shlex.join(command_argv),
        efficiency_estimate=efficiency_estimate(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
        handoff_contract=sidecar_handoff_contract(plan),
    )


def operator_plan_json_report(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    operator_entrypoint: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    plan = sidecar_stage_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    readiness = plan.get("verilator_option_readiness")
    ready = isinstance(readiness, dict) and readiness.get("status") == STATUS_READY_FOR_VERILATOR_OPTION_SHIM
    if ready:
        report = operator_plan_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
        report["operator_entrypoint"] = operator_entrypoint
        report["schema_role"] = SCHEMA_ROLE_TARGET_FIRST_OPERATOR_PLAN
        report["tool"] = "src/tools/run_hybrid_benchmark.py"
        report["discovery_hint"] = operator_discovery_hint(target=target, requested_shape=shape)
        report["use_when"] = [
            "automation starts from run_hybrid_benchmark.py --list-targets",
            "automation needs the synthesized Verilator command and efficiency estimate",
            "full sidecar stage details are not required",
        ]
        report["shim_boundary"] = shim_boundary()
        report["exit_code"] = 0
        return 0, report

    report = {
        "schema_version": 1,
        "schema_role": SCHEMA_ROLE_TARGET_FIRST_OPERATOR_PLAN,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "status": STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
        "target": target,
        "shape": shape,
        "limit": limit,
        "mode": mode,
        "phases": phases,
        "operator_entrypoint": operator_entrypoint,
        "exit_code": 2,
        "efficiency_estimate": efficiency_estimate(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
        "sidecar_stage_plan": plan,
        "use_when": [
            "automation starts from run_hybrid_benchmark.py --list-targets",
            "automation needs a stable not-ready JSON result without parsing stderr",
        ],
        "shim_boundary": shim_boundary(),
        "non_claims": [
            "operator plan JSON does not execute commands",
            "not-ready status is not correctness or timing evidence",
            "coverage-output equivalence remains separate from performance estimates",
        ],
    }
    if isinstance(readiness, dict):
        report["missing"] = readiness.get("missing", [])
        if "fallback_command" in readiness:
            report["fallback_command"] = readiness["fallback_command"]
    return 2, report


def shim_boundary() -> dict[str, str]:
    return {
        "tool": "src/tools/verilator_sidecar_shim.py",
        "use_when": "need readiness/stage details, stage command emission, or stable shim handoff fields",
    }


def verilator_option_preview(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> dict[str, object]:
    exit_code, report = operator_plan_json_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    preview: dict[str, object] = {
        "schema_version": 1,
        "status": report["status"],
        "exit_code": exit_code,
        "command_emitted": exit_code == 0,
        "non_claims": [
            "preview does not execute commands",
            "preview does not mean Verilator itself implements --sim-accel",
            "coverage-output equivalence remains the correctness policy",
        ],
    }
    if exit_code == 0:
        preview.update(
            {
                "command_argv": report["command_argv"],
                "command": report["command"],
                "estimate_command_argv": report["estimate_command_argv"],
                "estimate_command": report["estimate_command"],
                "estimate_flag": report["estimate_flag"],
                "requested_compatibility_entrypoint": report["requested_compatibility_entrypoint"],
                "correctness_policy": report["correctness_policy"],
                "handoff_contract": report["handoff_contract"],
            }
        )
    else:
        plan = report.get("sidecar_stage_plan")
        readiness = plan.get("verilator_option_readiness") if isinstance(plan, dict) else None
        if isinstance(readiness, dict):
            preview["missing"] = readiness.get("missing", [])
    return preview


def format_verilator_option_preview(preview: dict[str, object]) -> str:
    lines = [
        "# verilator_option_preview",
        f"status: {preview['status']}",
        f"command_emitted: {str(preview['command_emitted']).lower()}",
    ]
    if "command" in preview:
        lines.extend(["command:", str(preview["command"])])
    if "estimate_command" in preview:
        lines.extend(["estimate_command:", str(preview["estimate_command"])])
    if "estimate_flag" in preview:
        lines.append(f"estimate_flag: {preview['estimate_flag']}")
    if "requested_compatibility_entrypoint" in preview:
        lines.append(f"requested_compatibility_entrypoint: {preview['requested_compatibility_entrypoint']}")
    if "correctness_policy" in preview:
        lines.append(f"correctness_policy: {preview['correctness_policy']}")
    if "missing" in preview:
        lines.append("missing:")
        lines.extend(f"- {item}" for item in preview["missing"])
    lines.append("non_claims:")
    lines.extend(f"- {item}" for item in preview["non_claims"])
    return "\n".join(lines)
