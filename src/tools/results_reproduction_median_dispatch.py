"""Dispatch helpers for repeat-median reproduction workflows."""

from __future__ import annotations

from collections.abc import Callable

from results_reproduction_types import MedianWorkload
from results_reproduction_workloads import (
    median_workloads,
    paged_attention_kv_cache_continuation_repeat_median_workloads,
    paged_attention_kv_cache_next_shapes_repeat_median_workloads,
    paged_attention_kv_cache_repeat_median_workloads,
)

RunMedianWorkloadSet = Callable[
    [...],
    list[dict[str, object]],
]


def _require_positive_repeat_count(value: int, option: str) -> None:
    if value <= 0:
        raise ValueError(f"{option} must be positive")


def run_median_measurements_impl(
    *,
    repeat_count: int,
    dry_run: bool,
    run_median_workload_set: RunMedianWorkloadSet,
) -> list[dict[str, object]]:
    _require_positive_repeat_count(repeat_count, "--repeat-median")
    return run_median_workload_set(
        repeat_count=repeat_count,
        dry_run=dry_run,
        workloads=median_workloads(),
        aggregate_status="measured_representative_repeat_median",
        aggregate_report="results_reproduction_median_summary.json",
    )


def run_paged_attention_kv_cache_repeat_median_impl(
    *,
    repeat_count: int,
    dry_run: bool,
    run_median_workload_set: RunMedianWorkloadSet,
) -> list[dict[str, object]]:
    _require_positive_repeat_count(repeat_count, "--paged-kv-repeat-median")
    return run_median_workload_set(
        repeat_count=repeat_count,
        dry_run=dry_run,
        workloads=paged_attention_kv_cache_repeat_median_workloads(),
        aggregate_status="measured_paged_attention_kv_cache_repeat_median",
        aggregate_report="paged_attention_kv_cache_repeat_median_summary.json",
    )


def run_paged_attention_kv_cache_continuation_repeat_median_impl(
    *,
    repeat_count: int,
    dry_run: bool,
    run_median_workload_set: RunMedianWorkloadSet,
) -> list[dict[str, object]]:
    _require_positive_repeat_count(repeat_count, "--paged-kv-continuation-repeat-median")
    return run_median_workload_set(
        repeat_count=repeat_count,
        dry_run=dry_run,
        workloads=paged_attention_kv_cache_continuation_repeat_median_workloads(),
        aggregate_status="measured_paged_attention_kv_cache_scale_up_continuation_repeat_median",
        aggregate_report="paged_attention_kv_cache_scale_up_continuation_repeat_median_summary.json",
    )


def run_paged_attention_kv_cache_next_shapes_repeat_median_impl(
    *,
    repeat_count: int,
    dry_run: bool,
    run_median_workload_set: RunMedianWorkloadSet,
) -> list[dict[str, object]]:
    _require_positive_repeat_count(repeat_count, "--paged-kv-next-shapes-repeat-median")
    return run_median_workload_set(
        repeat_count=repeat_count,
        dry_run=dry_run,
        workloads=paged_attention_kv_cache_next_shapes_repeat_median_workloads(),
        aggregate_status="measured_paged_attention_kv_cache_scale_up_next_shapes_repeat_median",
        aggregate_report="paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json",
    )
