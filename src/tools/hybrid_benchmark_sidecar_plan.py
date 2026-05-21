"""Stage-level plans for the planned Verilator sidecar GPU flow."""

from __future__ import annotations

from pathlib import Path

from hybrid_benchmark_catalog import BENCHMARKS, KIND_SLICE_TEMPLATE, MODE_TEMPLATE
from hybrid_benchmark_paths import sanitize_local_absolute_paths
from hybrid_template_commands import command_plan
from hybrid_template_runner import load_template_plan
from hybrid_template_types import HybridTemplatePlan


REPO_ROOT = Path(__file__).resolve().parents[2]

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


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return sanitize_local_absolute_paths(str(path))


def _stage_details(plan: HybridTemplatePlan, stage: str) -> dict[str, object]:
    shape = f"{plan.nstates}x{plan.steps}"
    if stage == "verilator_build":
        return {
            "mdir": _display_path(plan.mdir),
            "top_module": plan.top_module,
            "source_files": [_display_path(path) for path in plan.source_files],
            "verilator_defines": list(plan.verilator_defines),
            "verilator_args": list(plan.verilator_args),
        }
    if stage == "host_probe_build":
        return {
            "host_probe_target": plan.host_probe_target,
            "template": _display_path(plan.template_path),
        }
    if stage == "cpu_init_state":
        return {
            "nstates": 1,
            "steps": 1,
            "output": _display_path(plan.cpu_init_state),
            "cfg": _cfg_details(plan),
        }
    if stage == "cpu_reference_output":
        return {
            "nstates": plan.nstates,
            "steps": plan.steps,
            "shape": shape,
            "output": _display_path(plan.cpu_reference_state),
            "cfg": _cfg_details(plan),
        }
    if stage == "gpu_artifact_build":
        return {
            "mdir": _display_path(plan.mdir),
            "builder": "src/tools/build_vl_gpu.py",
            "force": True,
        }
    if stage == "hybrid_sidecar_run":
        return {
            "runner": "src/tools/run_vl_hybrid.py",
            "mdir": _display_path(plan.mdir),
            "nstates": plan.nstates,
            "steps": plan.steps,
            "init_state": _display_path(plan.cpu_init_state),
            "dump_state": _display_path(plan.gpu_candidate_state),
            "sanitize_host_only_internals": True,
        }
    if stage == "coverage_output_compare":
        details: dict[str, object] = {
            "comparator": "src/tools/compare_vl_hybrid_modes.py",
            "mdir": _display_path(plan.mdir),
            "reference_dump": _display_path(plan.cpu_reference_state),
            "candidate_dump": _display_path(plan.gpu_candidate_state),
            "reference_label": f"cpu_repeat_{shape}",
            "candidate_label": f"hybrid_from_cpu_init_{shape}",
            "acceptance_policy": "coverage_output_equivalence",
            "json_out": _display_path(plan.compare_report),
            "coverage_output_target": plan.target_name,
        }
        if plan.source_gate is not None:
            details["coverage_output_gate"] = _display_path(plan.source_gate)
        return details
    return {}


def _cfg_details(plan: HybridTemplatePlan) -> dict[str, int]:
    return {
        "batch_length": plan.cfg_batch_length,
        "reset_cycles": plan.cfg_reset_cycles,
        "drain_cycles": plan.cfg_drain_cycles,
        "seed": plan.cfg_seed,
    }


def _verilator_option_readiness(stages: list[dict[str, object]]) -> dict[str, object]:
    by_stage = {str(stage["stage"]): stage for stage in stages}
    checks = {
        "verilator_build_has_mdir": _has_detail(by_stage, "verilator_build", "mdir"),
        "verilator_build_has_top_module": _has_detail(by_stage, "verilator_build", "top_module"),
        "verilator_build_has_source_files": bool(_details(by_stage, "verilator_build").get("source_files")),
        "gpu_artifact_build_has_mdir": _has_detail(by_stage, "gpu_artifact_build", "mdir"),
        "hybrid_run_has_shape": _has_detail(by_stage, "hybrid_sidecar_run", "nstates")
        and _has_detail(by_stage, "hybrid_sidecar_run", "steps"),
        "hybrid_run_has_state_io": _has_detail(by_stage, "hybrid_sidecar_run", "init_state")
        and _has_detail(by_stage, "hybrid_sidecar_run", "dump_state"),
        "compare_uses_coverage_output_equivalence": _details(by_stage, "coverage_output_compare").get("acceptance_policy")
        == "coverage_output_equivalence",
        "compare_has_reference_and_candidate": _has_detail(by_stage, "coverage_output_compare", "reference_dump")
        and _has_detail(by_stage, "coverage_output_compare", "candidate_dump"),
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {
        "status": "ready_for_verilator_option_shim" if not missing else "missing_required_inputs",
        "required_inputs": checks,
        "missing": missing,
        "non_claims": [
            "readiness means the wrapper plan has the minimum inputs for an option shim",
            "readiness does not mean Verilator itself implements --sim-accel",
            "readiness is not execution, correctness, or timing evidence",
        ],
    }


def _details(by_stage: dict[str, dict[str, object]], stage: str) -> dict[str, object]:
    details = by_stage.get(stage, {}).get("details", {})
    return details if isinstance(details, dict) else {}


def _has_detail(by_stage: dict[str, dict[str, object]], stage: str, key: str) -> bool:
    value = _details(by_stage, stage).get(key)
    if isinstance(value, str):
        return value != ""
    if isinstance(value, list):
        return len(value) > 0
    return value is not None


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
        "sidecar-gpu",
        "--sim-accel-states",
        str(run_details["nstates"]),
        "--sim-accel-steps",
        str(run_details["steps"]),
    ]


def sidecar_operator_plan(
    *,
    command_argv: list[str],
    command: str,
    efficiency_estimate: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "planned",
        "command_argv": command_argv,
        "command": command,
        "efficiency_estimate": efficiency_estimate,
        "correctness_policy": "coverage_output_equivalence",
        "non_claims": [
            "operator plan does not execute commands",
            "operator plan is not correctness or timing evidence",
            "coverage-output equivalence remains separate from performance estimates",
        ],
    }


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
        stages.append(
            {
                "stage": name,
                "command": _format_command(command),
                "details": _stage_details(plan, name),
            }
        )
    report.update(
        {
            "status": "planned",
            "template": spec.template,
            "stages": stages,
            "verilator_option_readiness": _verilator_option_readiness(stages),
        }
    )
    return report
