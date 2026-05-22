"""Fresh single-vs-split build/run helpers for compare_vl_hybrid_modes."""

from __future__ import annotations

import argparse
from pathlib import Path

from build_vl_gpu import build_vl_gpu
from compare_vl_hybrid_layout import probe_root_layout
from compare_vl_hybrid_phase_debug import run_hybrid
from compare_vl_hybrid_types import FreshRunArtifacts


def build_and_run_single_mode(
    *,
    mdir: Path,
    single_cubin: Path,
    single_dump: Path,
    layout_args: argparse.Namespace,
) -> tuple[Path, int]:
    single_path, storage_size = build_vl_gpu(
        mdir,
        sm=layout_args.sm,
        out_cubin=single_cubin,
        force=layout_args.force_build,
        clang_opt=layout_args.clang_opt,
        kernel_split_phases=False,
    )
    run_hybrid(
        mdir=None,
        cubin=single_path,
        storage_size=storage_size,
        nstates=layout_args.nstates,
        steps=layout_args.steps,
        block_size=layout_args.block_size,
        dump_state=single_dump,
        patches=layout_args.patch,
    )
    return single_path, storage_size


def build_and_run_split_mode(
    *,
    mdir: Path,
    split_cubin: Path,
    split_dump: Path,
    expected_storage_size: int,
    layout_args: argparse.Namespace,
) -> Path:
    split_path, split_storage_size = build_vl_gpu(
        mdir,
        sm=layout_args.sm,
        out_cubin=split_cubin,
        force=layout_args.force_build,
        clang_opt=layout_args.clang_opt,
        kernel_split_phases=True,
    )
    if split_storage_size != expected_storage_size:
        raise RuntimeError(
            "storage_size mismatch between single "
            f"({expected_storage_size}) and split ({split_storage_size})"
        )
    run_hybrid(
        mdir=mdir,
        cubin=None,
        storage_size=expected_storage_size,
        nstates=layout_args.nstates,
        steps=layout_args.steps,
        block_size=layout_args.block_size,
        dump_state=split_dump,
        patches=layout_args.patch,
    )
    return split_path


def fresh_dump_paths(tmpdir: Path) -> tuple[Path, Path]:
    tmpdir.mkdir(parents=True, exist_ok=True)
    return tmpdir / "single_state.bin", tmpdir / "split_state.bin"


def build_fresh_run_artifacts(
    args: argparse.Namespace,
    *,
    mdir: Path,
    tmpdir: Path,
) -> FreshRunArtifacts:
    single_cubin = mdir / "vl_batch_gpu_single.cubin"
    split_cubin = mdir / "vl_batch_gpu_split.cubin"
    single_dump, split_dump = fresh_dump_paths(tmpdir)
    layout = probe_root_layout(mdir)

    single_path, storage_size = build_and_run_single_mode(
        mdir=mdir,
        single_cubin=single_cubin,
        single_dump=single_dump,
        layout_args=args,
    )
    split_path = build_and_run_split_mode(
        mdir=mdir,
        split_cubin=split_cubin,
        split_dump=split_dump,
        expected_storage_size=storage_size,
        layout_args=args,
    )
    return FreshRunArtifacts(
        single_path=single_path,
        split_path=split_path,
        single_dump=single_dump,
        split_dump=split_dump,
        storage_size=storage_size,
        layout=layout,
    )
