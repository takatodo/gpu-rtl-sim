"""Final output and metadata helpers for build_vl_gpu orchestration."""

from __future__ import annotations

from pathlib import Path

from build_vl_gpu_hierarchy import (
    detect_hierarchy_state_metadata,
    syms_image_hierarchy_metadata,
)
from build_vl_gpu_metadata import write_build_metadata
from build_vl_gpu_stages import assemble_output_module
from build_vl_gpu_types import BuildArtifacts, BuildContext, BuildRequest


def detect_output_hierarchy_state(
    *,
    mdir: Path,
    storage_size: int,
    syms_state_image: bool,
    root_storage_size: int | None,
    state_root_offset: int | None,
) -> dict:
    if syms_state_image:
        return syms_image_hierarchy_metadata(
            mdir,
            root_storage_size=root_storage_size,
            syms_storage_size=storage_size,
            state_root_offset=state_root_offset,
        )
    return detect_hierarchy_state_metadata(mdir, storage_size)


def finalize_build_output(
    *,
    context: BuildContext,
    artifacts: BuildArtifacts,
    request: BuildRequest,
) -> tuple[Path, int]:
    out_module = assemble_output_module(
        mdir=context.mdir,
        gpu_ptx=artifacts.gpu_ptx,
        sm=request.sm,
        out_cubin=request.out_cubin,
        emit_ptx_module=request.emit_ptx_module,
        ptxas_opt_level=request.ptxas_opt_level,
    )
    storage_size = artifacts.storage_size
    hierarchy_state = detect_output_hierarchy_state(
        mdir=context.mdir,
        storage_size=storage_size,
        syms_state_image=request.syms_state_image,
        root_storage_size=artifacts.root_storage_size,
        state_root_offset=request.state_root_offset,
    )
    write_build_metadata(
        mdir=context.mdir,
        out_module=out_module,
        storage_size=storage_size,
        sm=request.sm,
        classifier_report=artifacts.classifier_report,
        clang_opt=request.clang_opt,
        gpu_opt_level=request.gpu_opt_level,
        emit_ptx_module=request.emit_ptx_module,
        incremental_mode=context.incremental_mode,
        existing_meta=context.existing_meta,
        ptxas_opt_level=request.ptxas_opt_level,
        launch_sequence=artifacts.launch_sequence,
        gpu_ir_workarounds=artifacts.gpu_ir_workarounds,
        hierarchy_state=hierarchy_state,
        opt_marker=context.opt_marker,
        kernel_split_phases=request.kernel_split_phases,
    )
    print(f'\nDone: {out_module}  ({out_module.stat().st_size} bytes)  storage_size={storage_size}')
    return out_module, storage_size
