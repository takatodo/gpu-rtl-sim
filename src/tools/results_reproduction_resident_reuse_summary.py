"""Summary helpers for resident state-reuse experiments."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_io import json_report, parse_hybrid_report
from results_reproduction_persistent_resident import phase_report_paths
from results_reproduction_types import MedianWorkload


def resident_state_reuse_experiment_summary(
    *,
    workload: MedianWorkload,
    nstates: int,
    steps: int,
    phases: int,
    phase_summaries: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "measured_resident_state_reuse_experiment",
        "target": workload.target_name,
        "shape": f"{nstates}x{steps}",
        "phases": phases,
        "acceptance_policy": "coverage_output_equivalence",
        "all_coverage_output_passed": all(phase["coverage_output_passed"] for phase in phase_summaries),
        "max_coverage_output_mismatch_count": max(
            phase["coverage_output_mismatch_count"] for phase in phase_summaries
        ),
        "phase_reports": phase_summaries,
    }


def resident_state_reuse_phase_summary(
    *,
    phase: int,
    nstates: int,
    steps: int,
    cumulative_steps: int,
    paths: dict[str, Path],
) -> dict[str, object]:
    cpu = json_report(paths["cpu_report"])
    compare = json_report(paths["compare_report"])
    if not isinstance(cpu, dict) or not isinstance(compare, dict):
        raise ValueError(f"resident state reuse phase report is not a JSON object: phase {phase}")
    coverage = compare["coverage_output_policy"]
    hybrid = parse_hybrid_report(paths["hybrid_report"])
    state_step_count = nstates * cumulative_steps
    return {
        "phase": phase,
        "shape": f"{nstates}x{cumulative_steps}",
        "phase_step_count": steps,
        "cumulative_step_count": cumulative_steps,
        "state_step_count": state_step_count,
        "cpu_elapsed_ms": cpu["elapsed_ms"],
        **hybrid,
        "gpu_kernel_total_ms_per_state_step": hybrid["gpu_kernel_total_ms"] / state_step_count,
        "hybrid_wall_ms_per_state_step": hybrid["hybrid_wall_ms"] / state_step_count,
        "coverage_output_passed": coverage["passed"],
        "coverage_output_mismatch_count": coverage["mismatch_count"],
        "reports": phase_report_paths(paths),
    }
