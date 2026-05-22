from __future__ import annotations

from pathlib import Path


def update_build_cache_markers(
    *,
    mdir: Path,
    opt_marker: Path,
    clang_opt: str,
    incremental_mode: str,
    kernel_split_phases: bool,
) -> None:
    if incremental_mode != 'reuse_ptx':
        opt_marker.write_text(clang_opt + "\n", encoding='utf-8')
    if incremental_mode == 'full':
        (mdir / '.vl_gpu_kernel_split').write_text(
            'phases' if kernel_split_phases else '', encoding='utf-8'
        )
