"""Summary payload builders for results reproduction workflows."""

from __future__ import annotations

import statistics

from results_reproduction_persistent_summaries import (
    PERSISTENT_RESIDENT_STATE_ABI_SHAPE_PHASE_SWEEP_CASES,
    persistent_resident_state_abi_probe_summary,
    persistent_resident_state_abi_repeat_metrics,
    persistent_resident_state_abi_repeat_summary,
    persistent_resident_state_abi_shape_phase_aggregate,
)
from results_reproduction_types import MedianWorkload


def summarize_numbers(values: list[float]) -> dict[str, object]:
    if not values:
        raise ValueError("cannot summarize an empty numeric sample set")
    return {
        "samples": values,
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def build_repeat_median_summary(
    *,
    workload: MedianWorkload,
    repeat_count: int,
    samples: list[dict[str, object]],
    resident_mode: bool | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "workload": workload.name,
        "target": workload.target_name,
        "shape": f"{workload.nstates}x{workload.steps}",
        "resident_mode": workload.resident if resident_mode is None else resident_mode,
        "source_gate": workload.source_gate,
        "repeat_count": repeat_count,
        "acceptance_policy": "coverage_output_equivalence",
        "all_coverage_output_passed": all(sample["coverage_output_passed"] for sample in samples),
        "max_coverage_output_mismatch_count": max(sample["coverage_output_mismatch_count"] for sample in samples),
        "metrics": {
            "cpu_elapsed_ms": summarize_numbers([float(sample["cpu_elapsed_ms"]) for sample in samples]),
            "gpu_kernel_total_ms": summarize_numbers([float(sample["gpu_kernel_total_ms"]) for sample in samples]),
            "hybrid_wall_ms": summarize_numbers([float(sample["hybrid_wall_ms"]) for sample in samples]),
            "gpu_kernel_total_ms_per_state_step": summarize_numbers(
                [float(sample["gpu_kernel_total_ms_per_state_step"]) for sample in samples]
            ),
            "hybrid_wall_ms_per_state_step": summarize_numbers(
                [float(sample["hybrid_wall_ms_per_state_step"]) for sample in samples]
            ),
        },
        "source_reports": {
            "cpu": [sample["reports"]["cpu_report"] for sample in samples],
            "hybrid": [sample["reports"]["hybrid_report"] for sample in samples],
            "compare": [sample["reports"]["compare_report"] for sample in samples],
            "compare_stdout": [sample["reports"]["compare_stdout_report"] for sample in samples],
        },
        "samples": samples,
    }
