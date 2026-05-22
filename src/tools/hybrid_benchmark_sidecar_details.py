"""Stage detail helpers for Verilator sidecar GPU planning."""

from __future__ import annotations

from pathlib import Path

from hybrid_benchmark_paths import sanitize_local_absolute_paths
from hybrid_benchmark_specs import (
    CORRECTNESS_POLICY_COVERAGE_OUTPUT,
    MODE_PERSISTENT_RESIDENT_STATE_ABI,
    MODE_RESIDENT_STATE_REUSE,
    STATUS_MISSING_REQUIRED_INPUTS,
    STATUS_READY_FOR_VERILATOR_OPTION_SHIM,
)
from hybrid_template_types import HybridTemplatePlan, parse_shape
from mobile_vit_hybrid_imagenet_defaults import DEFAULT_TEMPLATE as MOBILE_VIT_TEMPLATE
from results_reproduction_mobile_vit import (
    MOBILE_VIT_ACCURACY_REPORT_128,
    MOBILE_VIT_CPU_KICK_PREDICTIONS_128,
    MOBILE_VIT_HF_IMAGENET_128_DIR,
    MOBILE_VIT_MANIFEST_128,
    MOBILE_VIT_SUMMARY_REPORT_128,
)


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

MOBILE_VIT_STAGE_NAMES = (
    "host_preprocess",
    "rtl_sidecar_proxy_eval",
)


def format_command(command: list[str]) -> str:
    return sanitize_local_absolute_paths(" ".join(command))


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return sanitize_local_absolute_paths(str(path))


def stage_details(plan: HybridTemplatePlan, stage: str) -> dict[str, object]:
    shape = f"{plan.nstates}x{plan.steps}"
    if stage == "verilator_build":
        return {
            "mdir": display_path(plan.mdir),
            "top_module": plan.top_module,
            "source_files": [display_path(path) for path in plan.source_files],
            "verilator_defines": list(plan.verilator_defines),
            "verilator_args": list(plan.verilator_args),
        }
    if stage == "host_probe_build":
        return {
            "host_probe_target": plan.host_probe_target,
            "template": display_path(plan.template_path),
        }
    if stage == "cpu_init_state":
        return {
            "nstates": 1,
            "steps": 1,
            "output": display_path(plan.cpu_init_state),
            "cfg": cfg_details(plan),
        }
    if stage == "cpu_reference_output":
        return {
            "nstates": plan.nstates,
            "steps": plan.steps,
            "shape": shape,
            "output": display_path(plan.cpu_reference_state),
            "cfg": cfg_details(plan),
        }
    if stage == "gpu_artifact_build":
        return {
            "mdir": display_path(plan.mdir),
            "builder": "src/tools/build_vl_gpu.py",
            "force": True,
        }
    if stage == "hybrid_sidecar_run":
        return {
            "runner": "src/tools/run_vl_hybrid.py",
            "mdir": display_path(plan.mdir),
            "nstates": plan.nstates,
            "steps": plan.steps,
            "init_state": display_path(plan.cpu_init_state),
            "dump_state": display_path(plan.gpu_candidate_state),
            "sanitize_host_only_internals": True,
        }
    if stage == "coverage_output_compare":
        details: dict[str, object] = {
            "comparator": "src/tools/compare_vl_hybrid_modes.py",
            "mdir": display_path(plan.mdir),
            "reference_dump": display_path(plan.cpu_reference_state),
            "candidate_dump": display_path(plan.gpu_candidate_state),
            "reference_label": f"cpu_repeat_{shape}",
            "candidate_label": f"hybrid_from_cpu_init_{shape}",
            "acceptance_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
            "json_out": display_path(plan.compare_report),
            "coverage_output_target": plan.target_name,
        }
        if plan.source_gate is not None:
            details["coverage_output_gate"] = display_path(plan.source_gate)
        return details
    return {}


def cfg_details(plan: HybridTemplatePlan) -> dict[str, int]:
    return {
        "batch_length": plan.cfg_batch_length,
        "reset_cycles": plan.cfg_reset_cycles,
        "drain_cycles": plan.cfg_drain_cycles,
        "seed": plan.cfg_seed,
    }


def verilator_option_readiness(stages: list[dict[str, object]]) -> dict[str, object]:
    by_stage = {str(stage["stage"]): stage for stage in stages}
    checks = {
        "verilator_build_has_mdir": has_detail(by_stage, "verilator_build", "mdir"),
        "verilator_build_has_top_module": has_detail(by_stage, "verilator_build", "top_module"),
        "verilator_build_has_source_files": bool(details(by_stage, "verilator_build").get("source_files")),
        "gpu_artifact_build_has_mdir": has_detail(by_stage, "gpu_artifact_build", "mdir"),
        "hybrid_run_has_shape": has_detail(by_stage, "hybrid_sidecar_run", "nstates")
        and has_detail(by_stage, "hybrid_sidecar_run", "steps"),
        "hybrid_run_has_state_io": has_detail(by_stage, "hybrid_sidecar_run", "init_state")
        and has_detail(by_stage, "hybrid_sidecar_run", "dump_state"),
        "compare_uses_coverage_output_equivalence": details(by_stage, "coverage_output_compare").get(
            "acceptance_policy"
        )
        == CORRECTNESS_POLICY_COVERAGE_OUTPUT,
        "compare_has_reference_and_candidate": has_detail(by_stage, "coverage_output_compare", "reference_dump")
        and has_detail(by_stage, "coverage_output_compare", "candidate_dump"),
    }
    missing = [name for name, passed in checks.items() if not passed]
    return {
        "status": STATUS_READY_FOR_VERILATOR_OPTION_SHIM if not missing else STATUS_MISSING_REQUIRED_INPUTS,
        "required_inputs": checks,
        "missing": missing,
        "non_claims": [
            "readiness means the wrapper plan has the minimum inputs for an option shim",
            "readiness does not mean Verilator itself implements --sim-accel",
            "readiness is not execution, correctness, or timing evidence",
        ],
    }


def details(by_stage: dict[str, dict[str, object]], stage: str) -> dict[str, object]:
    stage_details_value = by_stage.get(stage, {}).get("details", {})
    return stage_details_value if isinstance(stage_details_value, dict) else {}


def has_detail(by_stage: dict[str, dict[str, object]], stage: str, key: str) -> bool:
    value = details(by_stage, stage).get(key)
    if isinstance(value, str):
        return value != ""
    if isinstance(value, list):
        return len(value) > 0
    return value is not None


def mobile_vit_stage_details(stage: str) -> dict[str, object]:
    if stage == "host_preprocess":
        return {
            "tool": "src/tools/mobile_vit_imagenet_manifest.py",
            "limit": 128,
            "manifest": MOBILE_VIT_MANIFEST_128,
            "hf_output_dir": MOBILE_VIT_HF_IMAGENET_128_DIR,
            "dataset_scope": "scoped_subset:imagenet_local_cache_128",
        }
    if stage == "rtl_sidecar_proxy_eval":
        return {
            "tool": "src/tools/mobile_vit_hybrid_imagenet_eval.py",
            "manifest": MOBILE_VIT_MANIFEST_128,
            "cpu_kick_predictions": MOBILE_VIT_CPU_KICK_PREDICTIONS_128,
            "accuracy_report": MOBILE_VIT_ACCURACY_REPORT_128,
            "summary": MOBILE_VIT_SUMMARY_REPORT_128,
            "hybrid_template": str(MOBILE_VIT_TEMPLATE),
            "rtl_proxy_target": "mobile_vit_cpu_kick_rtl_proxy",
            "cpu_kick_batch_size": 16,
            "hybrid_batch_size": 128,
            "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
            "coverage_output_equivalence_scope": "CPU-visible LOAD_MODEL/LOAD_IMAGE/KICK_INFER/POLL_DONE boundary",
        }
    return {}


def resident_stage_name(mode: str) -> str:
    if mode == MODE_RESIDENT_STATE_REUSE:
        return "resident_state_reuse_workflow"
    if mode == MODE_PERSISTENT_RESIDENT_STATE_ABI:
        return "persistent_resident_state_abi_workflow"
    raise ValueError(f"unsupported resident mode: {mode}")


def resident_workflow_command(*, mode: str, shape: str, phases: int) -> list[str]:
    if mode == MODE_RESIDENT_STATE_REUSE:
        return [
            "python3",
            "src/tools/run_results_reproduction.py",
            "--resident-state-reuse",
            shape,
            "--resident-state-reuse-phases",
            str(phases),
        ]
    if mode == MODE_PERSISTENT_RESIDENT_STATE_ABI:
        return [
            "python3",
            "src/tools/run_results_reproduction.py",
            "--persistent-resident-state-abi",
            shape,
            "--persistent-resident-state-abi-phases",
            str(phases),
        ]
    raise ValueError(f"unsupported resident mode: {mode}")


def resident_stage_details(*, mode: str, shape: str, phases: int) -> dict[str, object]:
    nstates, steps = parse_shape(shape)
    return {
        "workflow": mode,
        "shape": shape,
        "nstates": nstates,
        "steps": steps,
        "phases": phases,
        "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
        "fallback_command": format_command(resident_workflow_command(mode=mode, shape=shape, phases=phases)),
        "reason": "resident workflow reduces repeated host launch orchestration for low-efficiency single-state shapes",
    }
