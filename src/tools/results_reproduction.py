#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from results_reproduction_io import (
    display_path,
    format_command as _format_command,
    json_report,
    parse_hybrid_report,
    run_command,
    run_commands,
    sanitize_local_absolute_paths,
    write_json,
)
from results_reproduction_commands import (
    mha_obj as _mha_obj_impl,
    report as _report_impl,
)
from results_reproduction_basic import (
    reproduction_plan as _reproduction_plan_impl,
    run_public_pack_archive_plan as _run_public_pack_archive_plan_impl,
    run_reproduction_plan as _run_reproduction_plan_impl,
)
from results_reproduction_gpu_allocation_policy import (
    run_filelist_broader_shape_gpu_allocation_policy_dry_run as _run_filelist_broader_shape_gpu_allocation_policy_dry_run_impl,
    run_filelist_shape_breadth_gpu_allocation_policy_dry_run as _run_filelist_shape_breadth_gpu_allocation_policy_dry_run_impl,
)
from results_reproduction_mobile_vit import mobile_vit_imagenet_128_plan
from results_reproduction_manifest import PUBLIC_PACK_ARCHIVE_PATHS
from results_reproduction_median_dispatch import (
    run_filelist_broader_policy_repeat_median_impl,
    run_filelist_broader_shape_repeat_median_impl,
    run_filelist_shape_breadth_repeat_median_impl,
    run_median_measurements_impl,
    run_paged_attention_kv_cache_continuation_repeat_median_impl,
    run_paged_attention_kv_cache_next_shapes_repeat_median_impl,
    run_paged_attention_kv_cache_repeat_median_impl,
)
from results_reproduction_median_core import (
    init_state_paths as _init_state_paths,
    median_report_path as _median_report_path,
    run_init_state as _run_init_state,
    run_median_workload_set as _run_median_workload_set,
    run_workload_sample as _run_workload_sample,
    sample_paths as _sample_paths,
)
from results_reproduction_persistent_facade import (
    run_persistent_resident_state_abi_probe,
    run_persistent_resident_state_abi_repeat_median,
    run_persistent_resident_state_abi_shape_phase_sweep,
)
from results_reproduction_persistent_resident import (
    load_and_annotate_repeat_sample as _load_and_annotate_persistent_resident_state_abi_repeat_sample,
)
from results_reproduction_resident_batch import (
    parse_resident_batch_states,
    parse_shape,
)
from results_reproduction_resident_facade import run_resident_batch_sweep, run_resident_state_reuse_experiment
from results_reproduction_summaries import (
    build_repeat_median_summary as _build_repeat_median_summary,
    persistent_resident_state_abi_repeat_metrics as _persistent_resident_state_abi_repeat_metrics,
)
from results_reproduction_types import (
    MedianWorkload,
    ReproductionCommand,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_RESIDENT_SWEEP_STATES = (1, 8, 16, 32)

def _display_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def _sanitize_local_absolute_paths(text: str) -> str:
    return sanitize_local_absolute_paths(text)


def _mha_obj(path: str) -> Path:
    return _mha_obj_impl(REPO_ROOT, path)


def _report(path: str) -> Path:
    return _report_impl(REPO_ROOT, path)


def _json_report(path: Path) -> object:
    return json_report(path)


def _write_json(path: Path, payload: object) -> None:
    write_json(path, payload)


def reproduction_plan() -> list[ReproductionCommand]:
    return _reproduction_plan_impl(REPO_ROOT)


def format_command(command: ReproductionCommand) -> str:
    return _format_command(command, repo_root=REPO_ROOT)


def run_reproduction_plan(*, dry_run: bool) -> None:
    _run_reproduction_plan_impl(REPO_ROOT, dry_run=dry_run)


def run_public_pack_archive_plan(*, dry_run: bool) -> None:
    _run_public_pack_archive_plan_impl(dry_run=dry_run)


def run_mobile_vit_imagenet_128_reproduction(*, dry_run: bool) -> None:
    _run_commands(mobile_vit_imagenet_128_plan(), dry_run=dry_run)


def _run_command(command: ReproductionCommand, *, dry_run: bool) -> None:
    run_command(command, repo_root=REPO_ROOT, dry_run=dry_run)


def _run_commands(commands: list[ReproductionCommand], *, dry_run: bool) -> None:
    run_commands(commands, repo_root=REPO_ROOT, dry_run=dry_run)


def _parse_hybrid_report(path: Path) -> dict[str, float]:
    return parse_hybrid_report(path, repo_root=REPO_ROOT)


def run_median_measurements(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    return run_median_measurements_impl(
        repeat_count=repeat_count,
        dry_run=dry_run,
        run_median_workload_set=_run_median_workload_set,
    )


def run_paged_attention_kv_cache_repeat_median(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    return run_paged_attention_kv_cache_repeat_median_impl(
        repeat_count=repeat_count,
        dry_run=dry_run,
        run_median_workload_set=_run_median_workload_set,
    )


def run_paged_attention_kv_cache_continuation_repeat_median(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    return run_paged_attention_kv_cache_continuation_repeat_median_impl(
        repeat_count=repeat_count,
        dry_run=dry_run,
        run_median_workload_set=_run_median_workload_set,
    )


def run_paged_attention_kv_cache_next_shapes_repeat_median(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    return run_paged_attention_kv_cache_next_shapes_repeat_median_impl(
        repeat_count=repeat_count,
        dry_run=dry_run,
        run_median_workload_set=_run_median_workload_set,
    )


def run_filelist_shape_breadth_repeat_median(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    return run_filelist_shape_breadth_repeat_median_impl(
        repeat_count=repeat_count,
        dry_run=dry_run,
        run_median_workload_set=_run_median_workload_set,
    )


def run_filelist_broader_shape_repeat_median(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    return run_filelist_broader_shape_repeat_median_impl(
        repeat_count=repeat_count,
        dry_run=dry_run,
        run_median_workload_set=_run_median_workload_set,
    )


def run_filelist_broader_policy_repeat_median(*, repeat_count: int, dry_run: bool) -> list[dict[str, object]]:
    return run_filelist_broader_policy_repeat_median_impl(
        repeat_count=repeat_count,
        dry_run=dry_run,
        run_median_workload_set=_run_median_workload_set,
    )


def run_filelist_shape_breadth_gpu_allocation_policy_dry_run(*, dry_run: bool) -> dict[str, object]:
    return _run_filelist_shape_breadth_gpu_allocation_policy_dry_run_impl(dry_run=dry_run)


def run_filelist_broader_shape_gpu_allocation_policy_dry_run(*, dry_run: bool) -> dict[str, object]:
    return _run_filelist_broader_shape_gpu_allocation_policy_dry_run_impl(dry_run=dry_run)
