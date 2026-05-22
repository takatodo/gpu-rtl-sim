import json
from pathlib import Path

from build_vl_gpu_cache_markers import update_build_cache_markers


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
