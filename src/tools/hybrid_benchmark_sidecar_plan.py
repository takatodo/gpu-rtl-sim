"""Stage-level plans for the planned Verilator sidecar GPU flow."""

from __future__ import annotations

from hybrid_benchmark_catalog import (
    BENCHMARKS,
    KIND_MOBILE_VIT_IMAGENET,
    KIND_SLICE_TEMPLATE,
    MODE_PERSISTENT_RESIDENT_STATE_ABI,
    MODE_RESIDENT_STATE_REUSE,
    MODE_TEMPLATE,
)
from hybrid_benchmark_sidecar_details import (
    MOBILE_VIT_STAGE_NAMES,
    TEMPLATE_STAGE_NAMES,
    format_command,
    mobile_vit_stage_details,
    resident_stage_details,
    resident_stage_name,
    resident_workflow_command,
    stage_details,
    verilator_option_readiness,
)
from hybrid_benchmark_sidecar_operator import (
    SIM_ACCEL_ESTIMATE_EFFICIENCY_FLAG,
    format_sidecar_operator_plan,
    select_sidecar_stage,
    selected_stage_details,
    sidecar_handoff_contract,
    sidecar_operator_plan,
    synthesized_verilator_command_argv,
    synthesized_verilator_estimate_command_argv,
)
from hybrid_benchmark_specs import (
    CORRECTNESS_POLICY_COVERAGE_OUTPUT,
    SIDECAR_ACCEL,
    STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_UNSUPPORTED_FOR_STAGE_PLAN,
)
from hybrid_template_commands import command_plan
from hybrid_template_runner import load_template_plan
from results_reproduction_mobile_vit import mobile_vit_imagenet_128_plan


def sidecar_stage_plan(
    *,
    target: str,
    shape: str | None,
    limit: int | None = None,
    phases: int = 4,
    mode: str,
) -> dict[str, object]:
    spec = BENCHMARKS[target]
    report: dict[str, object] = {
        "schema_version": 1,
        "target": target,
        "shape": shape,
        "mode": mode,
        "sim_accel": SIDECAR_ACCEL,
        "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
        "non_claims": [
            "stage plan does not execute commands",
            "coverage-output equivalence is not raw full-state equality",
            "efficiency estimate remains separate from correctness",
        ],
    }
    if spec.kind == KIND_MOBILE_VIT_IMAGENET:
        return _mobile_vit_stage_plan(report=report, mode=mode, limit=limit)
    if spec.kind != KIND_SLICE_TEMPLATE:
        report.update(
            {
                "status": STATUS_UNSUPPORTED_FOR_STAGE_PLAN,
                "reason": "dataset-backed targets need host preprocessing separated before a Verilator-sidecar stage plan",
                "stages": [],
            }
        )
        return report
    if mode in (MODE_RESIDENT_STATE_REUSE, MODE_PERSISTENT_RESIDENT_STATE_ABI):
        if shape is None:
            raise ValueError(f"{target} requires --shape")
        return _resident_stage_plan(report=report, mode=mode, shape=shape, phases=phases)
    if mode != MODE_TEMPLATE:
        report.update(
            {
                "status": STATUS_UNSUPPORTED_FOR_STAGE_PLAN,
                "reason": "resident modes are higher-level benchmark workflows, not the template sidecar build/run/compare plan",
                "stages": [],
            }
        )
        return report
    if shape is None:
        raise ValueError(f"{target} requires --shape")
    assert spec.template is not None
    plan = load_template_plan(spec.template, shape=shape)
    stages = [
        {
            "stage": name,
            "command": format_command(command),
            "details": stage_details(plan, name),
        }
        for name, command in zip(TEMPLATE_STAGE_NAMES, command_plan(plan), strict=True)
    ]
    report.update(
        {
            "status": "planned",
            "template": spec.template,
            "stages": stages,
            "verilator_option_readiness": verilator_option_readiness(stages),
        }
    )
    return report


def _mobile_vit_stage_plan(*, report: dict[str, object], mode: str, limit: int | None) -> dict[str, object]:
    if mode != MODE_TEMPLATE:
        report.update(
            {
                "status": STATUS_UNSUPPORTED_FOR_STAGE_PLAN,
                "reason": "mobile_vit only exposes the template dataset-backed sidecar boundary",
                "stages": [],
            }
        )
        return report
    if limit != 128:
        report.update(
            {
                "status": STATUS_UNSUPPORTED_FOR_STAGE_PLAN,
                "reason": "mobile_vit sidecar stage plan currently requires --limit 128",
                "stages": [],
            }
        )
        return report
    commands = mobile_vit_imagenet_128_plan()
    stages = [
        {
            "stage": name,
            "command": format_command(command.argv),
            "details": mobile_vit_stage_details(name),
        }
        for name, command in zip(MOBILE_VIT_STAGE_NAMES, commands, strict=True)
    ]
    report.update(
        {
            "status": STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
            "reason": (
                "host preprocessing is separated, but this dataset-backed target still needs "
                "a direct RTL sidecar handoff before the Verilator option shim can be ready"
            ),
            "limit": limit,
            "stages": stages,
            "verilator_option_readiness": {
                "status": STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
                "missing": ["direct_verilator_rtl_sidecar_handoff"],
                "fallback_command": "python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run",
                "non_claims": [
                    "not-ready status is not correctness or timing evidence",
                    "dataset host preprocessing remains separate from RTL sidecar timing",
                ],
            },
        }
    )
    return report


def _resident_stage_plan(
    *,
    report: dict[str, object],
    mode: str,
    shape: str,
    phases: int,
) -> dict[str, object]:
    stage_name = resident_stage_name(mode)
    command = resident_workflow_command(mode=mode, shape=shape, phases=phases)
    report.update(
        {
            "status": STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
            "reason": (
                "resident modes are higher-level workflows; the supported fallback is exposed, "
                "but a direct Verilator resident sidecar handoff is not ready"
            ),
            "stages": [
                {
                    "stage": stage_name,
                    "command": format_command(command),
                    "details": resident_stage_details(mode=mode, shape=shape, phases=phases),
                }
            ],
            "verilator_option_readiness": {
                "status": STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
                "missing": ["direct_verilator_resident_sidecar_handoff"],
                "fallback_command": format_command(command),
                "non_claims": [
                    "not-ready status is not correctness or timing evidence",
                    "resident workflow fallback is not a direct Verilator option implementation",
                ],
            },
        }
    )
    return report
