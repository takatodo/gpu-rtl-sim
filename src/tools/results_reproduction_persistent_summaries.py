"""Persistent resident summary payload builders."""

from __future__ import annotations

from results_reproduction_types import MedianWorkload


PERSISTENT_RESIDENT_STATE_ABI_SHAPE_PHASE_SWEEP_CASES = (
    {"case_id": "16x64_p2_r3", "nstates": 16, "steps": 64, "phases": 2, "repeat_count": 3},
    {"case_id": "16x64_p4_r3", "nstates": 16, "steps": 64, "phases": 4, "repeat_count": 3},
    {"case_id": "16x128_p4_r3", "nstates": 16, "steps": 128, "phases": 4, "repeat_count": 3},
    {"case_id": "32x64_p4_r3", "nstates": 32, "steps": 64, "phases": 4, "repeat_count": 3},
)


def persistent_resident_state_abi_probe_summary(
    *,
    workload: MedianWorkload,
    nstates: int,
    steps: int,
    phases: int,
    hybrid_report: str,
    phase_summaries: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "measured_persistent_resident_state_abi_probe",
        "target": workload.target_name,
        "shape": f"{nstates}x{steps}",
        "phases": phases,
        "acceptance_policy": "coverage_output_equivalence",
        "state_authority": "in_process_gpu_d_storage_after_phase_1",
        "all_coverage_output_passed": all(phase["coverage_output_passed"] for phase in phase_summaries),
        "max_coverage_output_mismatch_count": max(
            phase["coverage_output_mismatch_count"] for phase in phase_summaries
        ),
        "hybrid_report": hybrid_report,
        "phase_reports": phase_summaries,
    }


def persistent_resident_state_abi_repeat_summary(
    *,
    nstates: int,
    steps: int,
    phases: int,
    repeat_count: int,
    source_gate: str,
    samples: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "measured_persistent_resident_state_abi_repeat_median",
        "target": "pulp_ita_mha",
        "shape": f"{nstates}x{steps}",
        "phases": phases,
        "repeat_count": repeat_count,
        "acceptance_policy": "coverage_output_equivalence",
        "source_gate": source_gate,
        "state_authority": "in_process_gpu_d_storage_after_phase_1",
        "all_coverage_output_passed": all(sample["all_coverage_output_passed"] for sample in samples),
        "max_coverage_output_mismatch_count": max(
            int(sample["max_coverage_output_mismatch_count"]) for sample in samples
        ),
        "metrics": persistent_resident_state_abi_repeat_metrics(samples),
        "sample_reports": [sample["sample_report"] for sample in samples],
        "samples": samples,
        "non_claims": [
            "not a new workload",
            "not a runtime or ABI change",
            "not production LLM serving throughput",
            "not paper-grade statistical confidence beyond the selected repeat count",
            "not raw full-state equality",
        ],
    }


def persistent_resident_state_abi_repeat_metrics(samples: list[dict[str, object]]) -> dict[str, object]:
    from results_reproduction_summaries import summarize_numbers

    return {
        "gpu_kernel_total_ms": summarize_numbers([float(sample["gpu_kernel_total_ms"]) for sample in samples]),
        "hybrid_wall_ms": summarize_numbers([float(sample["hybrid_wall_ms"]) for sample in samples]),
        "wall_minus_kernel_residual_ms": summarize_numbers(
            [float(sample["wall_minus_kernel_residual_ms"]) for sample in samples]
        ),
        "gpu_kernel_total_ms_per_final_state_step": summarize_numbers(
            [float(sample["gpu_kernel_total_ms_per_final_state_step"]) for sample in samples]
        ),
        "hybrid_wall_ms_per_final_state_step": summarize_numbers(
            [float(sample["hybrid_wall_ms_per_final_state_step"]) for sample in samples]
        ),
        "wall_minus_kernel_residual_ms_per_final_state_step": summarize_numbers(
            [float(sample["wall_minus_kernel_residual_ms_per_final_state_step"]) for sample in samples]
        ),
    }


def persistent_resident_state_abi_shape_phase_aggregate(
    *,
    source_gate: str,
    case_summaries: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "measured_persistent_resident_state_abi_shape_phase_sweep",
        "target": "pulp_ita_mha",
        "source_gate": source_gate,
        "case_count": len(case_summaries),
        "acceptance_policy": "coverage_output_equivalence",
        "state_authority": "in_process_gpu_d_storage_after_phase_1",
        "all_coverage_output_passed": all(case["all_coverage_output_passed"] for case in case_summaries),
        "max_coverage_output_mismatch_count": max(
            int(case["max_coverage_output_mismatch_count"]) for case in case_summaries
        ),
        "required_metrics": [
            "median hybrid wall ms",
            "median GPU kernel total ms",
            "median wall-minus-kernel residual ms",
            "median hybrid wall ms per final state-step",
            "median GPU kernel total ms per final state-step",
            "coverage-output equivalence pass/fail",
            "maximum coverage-output mismatch count",
            "state authority and phase shape list",
        ],
        "cases": case_summaries,
        "non_claims": [
            "not a runtime or ABI change",
            "not a new workload import",
            "not production LLM serving throughput",
            "not raw full-state equality",
        ],
    }
