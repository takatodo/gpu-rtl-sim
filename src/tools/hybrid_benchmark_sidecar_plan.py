"""Stage-level plans for the planned Verilator sidecar GPU flow."""

from __future__ import annotations

from hybrid_benchmark_catalog import BENCHMARKS, KIND_SLICE_TEMPLATE, MODE_TEMPLATE
from hybrid_benchmark_paths import sanitize_local_absolute_paths
from hybrid_template_commands import command_plan
from hybrid_template_runner import load_template_plan


TEMPLATE_STAGE_NAMES = (
    "verilator_build",
    "host_probe_build",
    "cpu_init_state",
    "cpu_reference_output",
    "gpu_artifact_build",
    "hybrid_sidecar_run",
    "coverage_output_compare",
)


def _format_command(command: list[str]) -> str:
    return sanitize_local_absolute_paths(" ".join(command))


def sidecar_stage_plan(
    *,
    target: str,
    shape: str | None,
    mode: str,
) -> dict[str, object]:
    spec = BENCHMARKS[target]
    report: dict[str, object] = {
        "schema_version": 1,
        "target": target,
        "shape": shape,
        "mode": mode,
        "sim_accel": "sidecar-gpu",
        "correctness_policy": "coverage_output_equivalence",
        "non_claims": [
            "stage plan does not execute commands",
            "coverage-output equivalence is not raw full-state equality",
            "efficiency estimate remains separate from correctness",
        ],
    }
    if spec.kind != KIND_SLICE_TEMPLATE:
        report.update(
            {
                "status": "unsupported_for_stage_plan",
                "reason": "dataset-backed targets need host preprocessing separated before a Verilator-sidecar stage plan",
                "stages": [],
            }
        )
        return report
    if mode != MODE_TEMPLATE:
        report.update(
            {
                "status": "unsupported_for_stage_plan",
                "reason": "resident modes are higher-level benchmark workflows, not the template sidecar build/run/compare plan",
                "stages": [],
            }
        )
        return report
    if shape is None:
        raise ValueError(f"{target} requires --shape")
    assert spec.template is not None
    plan = load_template_plan(spec.template, shape=shape)
    stages = []
    for name, command in zip(TEMPLATE_STAGE_NAMES, command_plan(plan), strict=True):
        stages.append({"stage": name, "command": _format_command(command)})
    report.update(
        {
            "status": "planned",
            "template": spec.template,
            "stages": stages,
        }
    )
    return report
