"""Full GPU IR build path for build_vl_gpu."""

from __future__ import annotations

from pathlib import Path

from build_vl_gpu_veer_flat_mem import patch_veer_el2_flat_program_mem
from build_vl_gpu_stages import (
    analyze_phase_ir,
    compile_verilator_ir,
    optimize_gpu_ir_to_ptx,
    prepare_gpu_patched_ir,
    resolve_build_storage_size,
)
from build_vl_gpu_state import resolve_existing_classifier_report
from build_vl_gpu_types import BuildArtifacts, BuildRequest


def prepare_full_build_gpu_ir(
    *,
    mdir: Path,
    prefix: str,
    merged_ll: Path,
    existing_meta: dict | None,
    classifier_report: Path,
    request: BuildRequest,
) -> BuildArtifacts:
    storage_size, root_storage_size = resolve_build_storage_size(
        mdir=mdir,
        prefix=prefix,
        existing_meta=existing_meta,
        reuse_gpu_patched_ll=request.reuse_gpu_patched_ll,
        syms_state_image=request.syms_state_image,
        syms_storage_size=request.syms_storage_size,
        state_root_offset=request.state_root_offset,
    )
    if request.reuse_gpu_patched_ll:
        classifier_report = resolve_existing_classifier_report(mdir, existing_meta)

    return build_full_gpu_ir_artifacts(
        mdir=mdir,
        prefix=prefix,
        merged_ll=merged_ll,
        existing_meta=existing_meta,
        classifier_report=classifier_report,
        storage_size=storage_size,
        root_storage_size=root_storage_size,
        request=request,
    )


def build_full_gpu_ir_artifacts(
    *,
    mdir: Path,
    prefix: str,
    merged_ll: Path,
    existing_meta: dict | None,
    classifier_report: Path,
    storage_size: int,
    root_storage_size: int | None,
    request: BuildRequest,
) -> BuildArtifacts:
    gpu_patched, launch_sequence = prepare_gpu_patched_ir(
        mdir=mdir,
        merged_ll=merged_ll,
        storage_size=storage_size,
        classifier_report=classifier_report,
        existing_meta=existing_meta,
        reuse_gpu_patched_ll=request.reuse_gpu_patched_ll,
        syms_state_image=request.syms_state_image,
        state_root_offset=request.state_root_offset,
        kernel_split_phases=request.kernel_split_phases,
        kernel_probe_act_sequent_chunk_size=request.kernel_probe_act_sequent_chunk_size,
        disable_cfg_clone_diagnostics=request.disable_cfg_clone_diagnostics,
    )
    gpu_ptx, gpu_ir_workarounds = optimize_gpu_ir_to_ptx(
        mdir=mdir,
        prefix=prefix,
        gpu_patched=gpu_patched,
        gpu_opt_level=request.gpu_opt_level,
        sm=request.sm,
    )
    return BuildArtifacts(
        gpu_ptx=gpu_ptx,
        storage_size=storage_size,
        root_storage_size=root_storage_size,
        classifier_report=classifier_report,
        launch_sequence=launch_sequence,
        gpu_ir_workarounds=gpu_ir_workarounds,
    )


def run_full_build_path(
    *,
    mdir: Path,
    prefix: str,
    all_classes: list[str],
    existing_meta: dict | None,
    classifier_report: Path,
    clang_changed: bool,
    request: BuildRequest,
) -> BuildArtifacts:
    source_patch = patch_veer_el2_flat_program_mem(mdir, prefix)
    source_patch_changed = source_patch.get("changed") is True
    merged_ll = compile_verilator_ir(
        mdir=mdir,
        all_classes=all_classes,
        force=request.force,
        clang_changed=clang_changed or source_patch_changed,
        clang_opt=request.clang_opt,
        jobs=request.jobs,
    )
    if request.analyze_phases:
        analyze_phase_ir(mdir=mdir, merged_ll=merged_ll)

    return prepare_full_build_gpu_ir(
        mdir=mdir,
        prefix=prefix,
        merged_ll=merged_ll,
        existing_meta=existing_meta,
        classifier_report=classifier_report,
        request=request,
    )
