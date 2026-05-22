from __future__ import annotations

import argparse
import json
from pathlib import Path

from compare_vl_hybrid_phase_debug_entries import collect_phase_debug_entry
from compare_vl_hybrid_phase_localization import initial_phase_localization
from compare_vl_hybrid_phase_runner import run_hybrid


def collect_phase_debug(
    *,
    tmpdir: Path,
    single_dump: Path,
    split_path: Path,
    storage_size: int,
    layout: list[dict[str, object]],
    launch_sequence: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    phase_debug = []
    prev_dump = None
    phase_localization = initial_phase_localization()
    for idx in range(len(launch_sequence)):
        prefix_index = idx + 1
        kernels = launch_sequence[:prefix_index]
        entry, prev_dump = collect_phase_debug_entry(
            tmpdir=tmpdir,
            single_dump=single_dump,
            split_path=split_path,
            storage_size=storage_size,
            layout=layout,
            phase_localization=phase_localization,
            prefix_index=prefix_index,
            kernels=kernels,
            prev_dump=prev_dump,
            args=args,
        )
        phase_debug.append(entry)
    return phase_debug, phase_localization


def load_launch_sequence_from_meta(mdir: Path) -> list[str]:
    split_meta = json.loads((mdir / "vl_batch_gpu.meta.json").read_text(encoding="utf-8"))
    return list(split_meta.get("launch_sequence") or [])


def add_phase_debug_if_available(
    *,
    summary: dict[str, object],
    tmpdir: Path,
    mdir: Path,
    single_dump: Path,
    split_path: Path,
    storage_size: int,
    layout: list[dict[str, object]],
    args: argparse.Namespace,
) -> list[str]:
    launch_sequence = load_launch_sequence_from_meta(mdir)
    if launch_sequence:
        phase_debug, phase_localization = collect_phase_debug(
            tmpdir=tmpdir,
            single_dump=single_dump,
            split_path=split_path,
            storage_size=storage_size,
            layout=layout,
            launch_sequence=launch_sequence,
            args=args,
        )
        summary["phase_debug"] = phase_debug
        summary["phase_localization"] = phase_localization
    return launch_sequence
