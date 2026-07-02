import json
from pathlib import Path

from build_vl_gpu_cache_markers import update_build_cache_markers
from gategpt_schedule_planner import (
    ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP,
    REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS,
    REQUIRED_PADDED_START_ENTRYPOINTS,
)

FC061_SUPPORTED = "supported_for_fc061_direct_kernel_launch_smoke"
FC061_UNSUPPORTED_TRIGGER_VECTOR = "unsupported_verilator_5_048_trigger_vector_artifact"
FC061_TRIGGERED_ACC_MARKER = "root_header___VactTriggeredAcc"
FC061_TRIGGER_VEC_MARKER = "gpu_ir_eval_triggers_vec__act"
PADDED_START_PAIR_CYCLE_LOOP_SHAPE = "padded_start_pair_cycle_loop"
ORDERING_AWARE_TOKEN_LOOP_SHAPE = ORDERING_AWARE_PHASE_RESIDENT_TOKEN_LOOP
SCHEDULE_LOWERING_IR_SOURCES = (
    "vl_batch_gpu_opt.ll",
    "vl_batch_gpu_patched.ll",
    "vl_batch_gpu.ll",
)


def reused_or_current_meta_value(
    *,
    existing_meta: dict | None,
    incremental_mode: str,
    key: str,
    current: str,
) -> str:
    if incremental_mode == 'reuse_ptx' and existing_meta:
        return existing_meta.get(key, current)
    return current


def _path_contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def detect_fc061_direct_shim_artifact_compatibility(
    *,
    mdir: Path,
    storage_size: int,
) -> dict:
    markers = []
    if any(_path_contains(path, "__VactTriggeredAcc") for path in mdir.glob("*___024root.h")):
        markers.append(FC061_TRIGGERED_ACC_MARKER)
    if any(
        _path_contains(path, "eval_triggers_vec__act")
        for pattern in ("vl_batch_gpu.ll", "vl_batch_gpu_patched.ll")
        for path in mdir.glob(pattern)
    ):
        markers.append(FC061_TRIGGER_VEC_MARKER)

    unsupported = bool(markers)
    return {
        "status": FC061_UNSUPPORTED_TRIGGER_VECTOR if unsupported else FC061_SUPPORTED,
        "supported": not unsupported,
        "trigger_vector_artifact_detected": unsupported,
        "trigger_vector_markers": markers,
        "observed_storage_size": storage_size,
        "known_good_storage_size_for_fc061": 6144,
        "observed_verilator_artifact_family": (
            "verilator_5_048_trigger_vector" if unsupported else "legacy_or_supported"
        ),
    }


def detect_schedule_lowering_capabilities(*, mdir: Path) -> dict:
    def entrypoint_sources_for(required: list[str]) -> dict[str, list[str]]:
        entrypoint_sources: dict[str, list[str]] = {}
        for entrypoint in required:
            sources = [
                source
                for source in SCHEDULE_LOWERING_IR_SOURCES
                if _path_contains(mdir / source, f"@{entrypoint}")
            ]
            if sources:
                entrypoint_sources[entrypoint] = sources
        return entrypoint_sources

    entrypoint_sources = entrypoint_sources_for(REQUIRED_PADDED_START_ENTRYPOINTS)
    token_loop_entrypoint_sources = entrypoint_sources_for(
        REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS
    )

    available = sorted(entrypoint_sources)
    missing = sorted(set(REQUIRED_PADDED_START_ENTRYPOINTS) - set(available))
    token_loop_available = sorted(token_loop_entrypoint_sources)
    token_loop_missing = sorted(
        set(REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS) - set(token_loop_available)
    )
    return {
        ORDERING_AWARE_TOKEN_LOOP_SHAPE: {
            "status": "available" if not token_loop_missing else "missing_required_entrypoints",
            "schedule_shape": ORDERING_AWARE_TOKEN_LOOP_SHAPE,
            "required_runtime_entrypoints": list(REQUIRED_ORDERING_AWARE_TOKEN_LOOP_ENTRYPOINTS),
            "available_runtime_entrypoints": token_loop_available,
            "missing_runtime_entrypoints": token_loop_missing,
            "entrypoint_sources": token_loop_entrypoint_sources,
            "metadata_boundary": "build_artifact_capability_only_not_execution_authority",
            "implementation_stage": (
                "prototype_entrypoint_phase_feedback_terminal_mask_body_available_runtime_owner_available_cpu_comparison_pending"
            ),
            "runtime_correctness_claimed": False,
            "requires_runtime_plan": True,
            "runtime_cli": "run_vl_hybrid.py --schedule-lowering-plan",
            "planner": (
                "gategpt_schedule_planner."
                "build_ordering_aware_phase_resident_token_loop_contract"
            ),
            "target_launch_shape": {
                "phase_set_launches": 0,
                "combined_feedback_launches": 0,
                "pair_cycle_loop_kernel_launches": 0,
                "ordering_aware_token_loop_kernel_launches": 1,
                "pair_cycle_loop_fallbacks": 0,
            },
            "non_claims": [
                "does_not_claim_entrypoint_implementation_when_missing",
                "prototype_entrypoint_body_consumes_phase_feedback_terminal_mask_with_runtime_owner_cpu_comparison_pending",
                "does_not_claim_semantic_equivalence",
                "does_not_claim_speedup",
                "does_not_claim_gateGPT_pass_fail_authority",
            ],
        },
        PADDED_START_PAIR_CYCLE_LOOP_SHAPE: {
            "status": "available" if not missing else "missing_required_entrypoints",
            "schedule_shape": PADDED_START_PAIR_CYCLE_LOOP_SHAPE,
            "required_runtime_entrypoints": list(REQUIRED_PADDED_START_ENTRYPOINTS),
            "available_runtime_entrypoints": available,
            "missing_runtime_entrypoints": missing,
            "entrypoint_sources": entrypoint_sources,
            "metadata_boundary": "build_artifact_capability_only_not_execution_authority",
            "requires_runtime_plan": True,
            "runtime_cli": "run_vl_hybrid.py --schedule-lowering-plan",
            "planner": "gategpt_schedule_planner.build_padded_start_pair_cycle_loop_lowering_plan",
            "non_claims": [
                "does_not_claim_semantic_equivalence",
                "does_not_claim_speedup",
                "does_not_select_gateGPT_scenarios",
            ],
        },
    }


def base_gpu_meta(
    *,
    out_module: Path,
    storage_size: int,
    sm: str,
    classifier_report: Path,
    clang_opt: str,
    gpu_opt_level: str,
    emit_ptx_module: bool,
    incremental_mode: str,
    existing_meta: dict | None,
    hierarchy_state: dict,
) -> dict:
    return {
        "schema_version": 1,
        "cubin": out_module.name,
        "storage_size": storage_size,
        "sm": sm,
        "kernel": "vl_eval_batch_gpu",
        "classifier_report": classifier_report.name,
        "clang_opt": reused_or_current_meta_value(
            existing_meta=existing_meta,
            incremental_mode=incremental_mode,
            key="clang_opt",
            current=clang_opt,
        ),
        "gpu_opt_level": reused_or_current_meta_value(
            existing_meta=existing_meta,
            incremental_mode=incremental_mode,
            key="gpu_opt_level",
            current=gpu_opt_level,
        ),
        "cuda_module_format": "ptx" if emit_ptx_module else "cubin",
        "incremental_mode": incremental_mode,
        "hierarchy_state": hierarchy_state,
        "fc061_direct_shim_compatibility": detect_fc061_direct_shim_artifact_compatibility(
            mdir=classifier_report.parent,
            storage_size=storage_size,
        ),
        "schedule_lowering_capabilities": detect_schedule_lowering_capabilities(
            mdir=classifier_report.parent,
        ),
    }


def build_gpu_meta(
    *,
    out_module: Path,
    storage_size: int,
    sm: str,
    classifier_report: Path,
    clang_opt: str,
    gpu_opt_level: str,
    emit_ptx_module: bool,
    incremental_mode: str,
    existing_meta: dict | None,
    ptxas_opt_level: int | None,
    launch_sequence: list[str] | None,
    gpu_ir_workarounds: list[str],
    hierarchy_state: dict,
) -> dict:
    meta = base_gpu_meta(
        out_module=out_module,
        storage_size=storage_size,
        sm=sm,
        classifier_report=classifier_report,
        clang_opt=clang_opt,
        gpu_opt_level=gpu_opt_level,
        emit_ptx_module=emit_ptx_module,
        incremental_mode=incremental_mode,
        existing_meta=existing_meta,
        hierarchy_state=hierarchy_state,
    )
    if ptxas_opt_level is not None:
        meta["ptxas_opt_level"] = ptxas_opt_level
    if launch_sequence is not None:
        meta["launch_sequence"] = launch_sequence
    if gpu_ir_workarounds:
        meta["gpu_ir_workarounds"] = gpu_ir_workarounds
    return meta


def write_build_metadata(
    *,
    mdir: Path,
    out_module: Path,
    storage_size: int,
    sm: str,
    classifier_report: Path,
    clang_opt: str,
    gpu_opt_level: str,
    emit_ptx_module: bool,
    incremental_mode: str,
    existing_meta: dict | None,
    ptxas_opt_level: int | None,
    launch_sequence: list[str] | None,
    gpu_ir_workarounds: list[str],
    hierarchy_state: dict,
    opt_marker: Path,
    kernel_split_phases: bool,
) -> None:
    meta_path = mdir / "vl_batch_gpu.meta.json"
    meta = build_gpu_meta(
        out_module=out_module,
        storage_size=storage_size,
        sm=sm,
        classifier_report=classifier_report,
        clang_opt=clang_opt,
        gpu_opt_level=gpu_opt_level,
        emit_ptx_module=emit_ptx_module,
        incremental_mode=incremental_mode,
        existing_meta=existing_meta,
        ptxas_opt_level=ptxas_opt_level,
        launch_sequence=launch_sequence,
        gpu_ir_workarounds=gpu_ir_workarounds,
        hierarchy_state=hierarchy_state,
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    update_build_cache_markers(
        mdir=mdir,
        opt_marker=opt_marker,
        clang_opt=clang_opt,
        incremental_mode=incremental_mode,
        kernel_split_phases=kernel_split_phases,
    )
    print(f"  [meta] -> {meta_path.name}")
