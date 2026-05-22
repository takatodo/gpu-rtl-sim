"""Reuse-path helpers for build_vl_gpu orchestration."""

from __future__ import annotations

from pathlib import Path

from build_vl_gpu_inputs import detect_storage_size
from build_vl_gpu_state import (
    resolve_existing_classifier_report,
    resolve_existing_storage_size,
    reuse_launch_sequence,
)
from build_vl_gpu_types import BuildArtifacts


def resolve_reused_ptx_build(*, mdir: Path, prefix: str, existing_meta: dict | None) -> BuildArtifacts:
    gpu_ptx = mdir / 'vl_batch_gpu.ptx'
    if not gpu_ptx.exists():
        raise FileNotFoundError(f'missing PTX for --reuse-ptx: {gpu_ptx}')
    storage_size = resolve_existing_storage_size(existing_meta)
    if storage_size is None:
        print('  [probe] existing meta missing storage_size; detecting...')
        storage_size = detect_storage_size(mdir, prefix)
    else:
        print(f'  [meta] reuse storage_size = {storage_size} bytes')
    classifier_report = resolve_existing_classifier_report(mdir, existing_meta)
    launch_sequence = reuse_launch_sequence(mdir, existing_meta)
    return BuildArtifacts(
        gpu_ptx=gpu_ptx,
        storage_size=storage_size,
        root_storage_size=None,
        classifier_report=classifier_report,
        launch_sequence=launch_sequence,
        gpu_ir_workarounds=[],
    )
