from __future__ import annotations


def validate_build_options(
    *,
    reuse_gpu_patched_ll: bool,
    reuse_ptx: bool,
    analyze_phases: bool,
    kernel_split_phases: bool,
    kernel_probe_act_sequent_chunk_size: int,
    syms_state_image: bool,
    syms_storage_size: int | None,
    state_root_offset: int | None,
    jobs: int,
) -> None:
    if reuse_gpu_patched_ll and reuse_ptx:
        raise ValueError("choose at most one reuse mode")
    if jobs <= 0:
        raise ValueError("jobs must be >= 1")
    if (reuse_gpu_patched_ll or reuse_ptx) and analyze_phases:
        raise ValueError("--analyze-phases requires a full rebuild from merged.ll")
    if (reuse_gpu_patched_ll or reuse_ptx) and kernel_split_phases:
        raise ValueError("--kernel-split-phases requires a full rebuild from merged.ll")
    if kernel_probe_act_sequent_chunk_size < 0:
        raise ValueError("--kernel-probe-act-sequent-chunk-size must be >= 0")
    if kernel_probe_act_sequent_chunk_size and not kernel_split_phases:
        raise ValueError("--kernel-probe-act-sequent-chunk-size requires --kernel-split-phases")
    if (reuse_gpu_patched_ll or reuse_ptx) and kernel_probe_act_sequent_chunk_size:
        raise ValueError("--kernel-probe-act-sequent-chunk-size requires a full rebuild from merged.ll")
    if syms_state_image and (reuse_gpu_patched_ll or reuse_ptx):
        raise ValueError("--syms-state-image requires a full rebuild from merged.ll")
    if syms_state_image:
        if syms_storage_size is None or syms_storage_size <= 0:
            raise ValueError("--syms-state-image requires --syms-storage-size > 0")
        if state_root_offset is None or state_root_offset < 0:
            raise ValueError("--syms-state-image requires --state-root-offset >= 0")
    elif syms_storage_size is not None or state_root_offset is not None:
        raise ValueError("--syms-storage-size/--state-root-offset require --syms-state-image")


def incremental_mode_name(*, reuse_gpu_patched_ll: bool, reuse_ptx: bool) -> str:
    if reuse_gpu_patched_ll:
        return "reuse_gpu_patched_ll"
    if reuse_ptx:
        return "reuse_ptx"
    return "full"
