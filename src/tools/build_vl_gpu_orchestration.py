"""Build orchestration helpers for build_vl_gpu."""

from __future__ import annotations

from pathlib import Path

from build_vl_gpu_finalize import finalize_build_output
from build_vl_gpu_full_path import (
    build_full_gpu_ir_artifacts,
    prepare_full_build_gpu_ir,
    run_full_build_path,
)
from build_vl_gpu_inputs import (
    clang_opt_changed,
    find_classes_mk,
    find_prefix,
    incremental_mode_name,
    read_mk_list,
    validate_build_options,
)
from build_vl_gpu_reuse import resolve_reused_ptx_build
from build_vl_gpu_state import load_existing_meta
from build_vl_gpu_types import BuildArtifacts, BuildContext, BuildRequest


def prepare_build_context(
    *,
    mdir: Path,
    sm: str,
    clang_opt: str,
    gpu_opt_level: str,
    reuse_gpu_patched_ll: bool,
    reuse_ptx: bool,
) -> BuildContext:
    mdir = mdir.resolve()
    mk_text = find_classes_mk(mdir).read_text()
    prefix = find_prefix(mdir)
    incremental_mode = incremental_mode_name(
        reuse_gpu_patched_ll=reuse_gpu_patched_ll,
        reuse_ptx=reuse_ptx,
    )
    print(
        f'[build_vl_gpu] mdir={mdir}  prefix={prefix}  sm={sm}  '
        f'clang={clang_opt}  gpu_opt={gpu_opt_level}  mode={incremental_mode}'
    )

    fast_classes = read_mk_list(mk_text, 'VM_CLASSES_FAST')
    slow_classes = read_mk_list(mk_text, 'VM_CLASSES_SLOW')
    all_classes = fast_classes + slow_classes
    print(f'  Classes: {all_classes}')
    opt_marker, clang_changed = clang_opt_changed(mdir, clang_opt)
    return BuildContext(
        mdir=mdir,
        prefix=prefix,
        all_classes=all_classes,
        existing_meta=load_existing_meta(mdir),
        classifier_report=mdir / 'vl_classifier_report.json',
        incremental_mode=incremental_mode,
        opt_marker=opt_marker,
        clang_changed=clang_changed,
    )


def resolve_build_artifacts(
    *,
    context: BuildContext,
    request: BuildRequest,
) -> BuildArtifacts:
    if request.reuse_ptx:
        return resolve_reused_ptx_build(
            mdir=context.mdir,
            prefix=context.prefix,
            existing_meta=context.existing_meta,
        )
    return run_full_build_path(
        mdir=context.mdir,
        prefix=context.prefix,
        all_classes=context.all_classes,
        existing_meta=context.existing_meta,
        classifier_report=context.classifier_report,
        clang_changed=context.clang_changed,
        request=request,
    )


def validate_build_request(request: BuildRequest) -> None:
    validate_build_options(
        reuse_gpu_patched_ll=request.reuse_gpu_patched_ll,
        reuse_ptx=request.reuse_ptx,
        analyze_phases=request.analyze_phases,
        kernel_split_phases=request.kernel_split_phases,
        kernel_probe_act_sequent_chunk_size=request.kernel_probe_act_sequent_chunk_size,
        syms_state_image=request.syms_state_image,
        syms_storage_size=request.syms_storage_size,
        state_root_offset=request.state_root_offset,
        jobs=request.jobs,
    )


def prepare_build_request_context(mdir: Path, request: BuildRequest) -> BuildContext:
    return prepare_build_context(
        mdir=mdir,
        sm=request.sm,
        clang_opt=request.clang_opt,
        gpu_opt_level=request.gpu_opt_level,
        reuse_gpu_patched_ll=request.reuse_gpu_patched_ll,
        reuse_ptx=request.reuse_ptx,
    )


def run_build_request(mdir: Path, request: BuildRequest) -> tuple[Path, int]:
    validate_build_request(request)
    context = prepare_build_request_context(mdir, request)
    artifacts = resolve_build_artifacts(context=context, request=request)
    return finalize_build_output(
        context=context,
        artifacts=artifacts,
        request=request,
    )
