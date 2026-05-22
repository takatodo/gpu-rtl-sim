from __future__ import annotations

import argparse
from pathlib import Path

from compare_vl_hybrid_phase_localization import (
    build_phase_delta_summary,
    record_prefix_delta_localization,
    record_prefix_vs_single_localization,
)
from compare_vl_hybrid_phase_runner import run_phase_prefix
from compare_vl_hybrid_state_compare import compare_state_dumps


def add_previous_prefix_delta(
    *,
    entry: dict[str, object],
    phase_localization: dict[str, object],
    prefix_index: int,
    kernels: list[str],
    prev_dump: Path | None,
    prefix_dump: Path,
    storage_size: int,
    layout: list[dict[str, object]],
) -> None:
    if prev_dump is None:
        phase_localization["per_prefix_delta_counts"].append(None)
        return
    prev_summary = compare_state_dumps(prev_dump, prefix_dump, storage_size, layout=layout)
    entry["vs_previous_prefix"] = prev_summary
    entry["delta_from_previous_prefix"] = build_phase_delta_summary(prev_summary)
    record_prefix_delta_localization(
        phase_localization=phase_localization,
        prefix_index=prefix_index,
        kernels=kernels,
        prev_summary=prev_summary,
    )


def build_phase_prefix_entry(
    *,
    single_dump: Path,
    prefix_dump: Path,
    storage_size: int,
    layout: list[dict[str, object]],
    phase_localization: dict[str, object],
    prefix_index: int,
    kernels: list[str],
) -> dict[str, object]:
    prefix_summary = compare_state_dumps(
        single_dump,
        prefix_dump,
        storage_size,
        layout=layout,
    )
    record_prefix_vs_single_localization(
        phase_localization=phase_localization,
        prefix_index=prefix_index,
        kernels=kernels,
        prefix_summary=prefix_summary,
    )
    return {
        "prefix_index": prefix_index,
        "kernels": kernels,
        "vs_single_final": prefix_summary,
        "dump": str(prefix_dump),
    }


def collect_phase_debug_entry(
    *,
    tmpdir: Path,
    single_dump: Path,
    split_path: Path,
    storage_size: int,
    layout: list[dict[str, object]],
    phase_localization: dict[str, object],
    prefix_index: int,
    kernels: list[str],
    prev_dump: Path | None,
    args: argparse.Namespace,
) -> tuple[dict[str, object], Path]:
    prefix_dump = run_phase_prefix(
        tmpdir=tmpdir,
        split_path=split_path,
        storage_size=storage_size,
        prefix_index=prefix_index,
        kernels=kernels,
        args=args,
    )
    entry = build_phase_prefix_entry(
        single_dump=single_dump,
        prefix_dump=prefix_dump,
        storage_size=storage_size,
        layout=layout,
        phase_localization=phase_localization,
        prefix_index=prefix_index,
        kernels=kernels,
    )
    add_previous_prefix_delta(
        entry=entry,
        phase_localization=phase_localization,
        prefix_index=prefix_index,
        kernels=kernels,
        prev_dump=prev_dump,
        prefix_dump=prefix_dump,
        storage_size=storage_size,
        layout=layout,
    )
    return entry, prefix_dump
