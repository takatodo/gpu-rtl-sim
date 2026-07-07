"""Quantify non-VeeR RTLMeter hybrid measurement readiness.

This report is an index over existing evidence. It does not run RTL, launch a
GPU kernel, or introduce a new speedup claim. Its job is to make the measured
NVDLA hot-SS evidence and the unmeasured Vortex first-gate blockers comparable
when deciding where hybrid measurement should go next.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any

from rtlmeter_non_veer_usefulness_candidates import build_summary as build_candidate_summary


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _shape_bucket(record: Mapping[str, Any]) -> str:
    nstates = _int(record.get("nstates")) or 0
    steps = _int(record.get("steps")) or 0
    if nstates > 1 and steps > 1:
        return "state_batch_and_repeated_step"
    if nstates > 1:
        return "state_batch"
    if steps > 1:
        return "repeated_step_single_state"
    return "single_state_single_step"


def _ratio_stats(records: list[Mapping[str, Any]], field: str) -> dict[str, Any]:
    values = [value for value in (_number(record.get(field)) for record in records) if value is not None]
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def _summarize_nvdla(candidate_summary: Mapping[str, Any]) -> dict[str, Any]:
    nvdla = _mapping(candidate_summary.get("nvdla"))
    evidence = _mapping(nvdla.get("evidence"))
    records = [record for record in evidence.get("records", []) if isinstance(record, Mapping)]
    favorable = [
        record
        for record in records
        if record.get("coverage_output_equivalence_passed") is True
        and (_number(record.get("cpu_to_hybrid_wall_speedup_ratio")) or 0.0) > 1.0
    ]
    buckets: dict[str, dict[str, Any]] = {}
    for record in records:
        bucket = _shape_bucket(record)
        entry = buckets.setdefault(
            bucket,
            {
                "measured_shape_count": 0,
                "gpu_favorable_shape_count": 0,
                "best_wall_speedup": None,
                "example_shapes": [],
            },
        )
        entry["measured_shape_count"] += 1
        ratio = _number(record.get("cpu_to_hybrid_wall_speedup_ratio"))
        if record.get("coverage_output_equivalence_passed") is True and ratio is not None and ratio > 1.0:
            entry["gpu_favorable_shape_count"] += 1
        best = entry["best_wall_speedup"]
        best_ratio = _number(_mapping(best).get("cpu_to_hybrid_wall_speedup_ratio"))
        if ratio is not None and (best_ratio is None or ratio > best_ratio):
            entry["best_wall_speedup"] = {
                "shape": record.get("shape"),
                "target": record.get("target"),
                "cpu_to_hybrid_wall_speedup_ratio": ratio,
            }
        if len(entry["example_shapes"]) < 3:
            entry["example_shapes"].append(record.get("shape"))

    descriptor = _mapping(nvdla.get("descriptor"))
    compile_has_cpp_dpi = (_int(descriptor.get("cpp_source_count")) or 0) > 0
    return {
        "classification": evidence.get("classification"),
        "hybrid_measurement_status": evidence.get("status"),
        "measured_shape_count": evidence.get("measured_shape_count"),
        "coverage_passed_shape_count": evidence.get("coverage_passed_shape_count"),
        "gpu_favorable_shape_count": evidence.get("gpu_favorable_shape_count"),
        "favorable_ratio": (
            len(favorable) / len(records)
            if records
            else None
        ),
        "wall_speedup_ratio_stats": _ratio_stats(records, "cpu_to_hybrid_wall_speedup_ratio"),
        "kernel_speedup_ratio_stats": _ratio_stats(records, "cpu_to_gpu_kernel_speedup_ratio"),
        "best_wall_speedup": evidence.get("best_wall_speedup"),
        "best_kernel_speedup": evidence.get("best_kernel_speedup"),
        "shape_buckets": buckets,
        "observed_favorable_features": [
            "scoped_hot_ss_boundary",
            "coverage_output_equivalence_passed",
            "independent_state_batching",
            "repeated_step_batching",
            "no_descriptor_cpp_dpi_bridge" if not compile_has_cpp_dpi else "descriptor_cpp_dpi_present",
        ],
        "hybrid_split_decision": {
            "decision_stage": "compile_time_candidate_selection_with_runtime_shape_confirmation",
            "recommended_action": "prefer_gpu_for_measured_nvdla_hot_ss_shapes",
            "reason": "all measured coverage-equivalent NVDLA hot-SS shapes in the current evidence are GPU-favorable by wall time",
        },
        "non_claims": [
            "not_full_nvdla_execution",
            "not_raw_full_state_equality",
            "not_unmeasured_shape_speedup",
        ],
    }


def _summarize_vortex(candidate_summary: Mapping[str, Any]) -> dict[str, Any]:
    vortex = _mapping(candidate_summary.get("vortex"))
    readiness = _mapping(vortex.get("first_gate_readiness"))
    bridge = _mapping(readiness.get("dpi_memory_bridge_review"))
    binary_input = _mapping(bridge.get("binary_input_summary"))
    materialized = _mapping(bridge.get("device_buffer_materialization"))
    dcr = _mapping(bridge.get("dcr_schedule"))
    missing = readiness.get("missing_prerequisites")
    if not isinstance(missing, list):
        missing = []
    return {
        "classification": vortex.get("classification"),
        "hybrid_measurement_status": vortex.get("status"),
        "first_gate": _mapping(readiness.get("first_measurement_candidate")).get("case"),
        "runtime_launchable": readiness.get("runtime_launchable"),
        "cpu_vs_hybrid_timing_present": "cpu_vs_hybrid_timing_report.vortex" not in missing,
        "missing_prerequisites": missing,
        "bridge_quantities": {
            "init_segment_count": binary_input.get("init_segment_count"),
            "init_total_payload_bytes": binary_input.get("init_total_payload_bytes"),
            "post_segment_count": binary_input.get("post_segment_count"),
            "post_total_payload_bytes": binary_input.get("post_total_payload_bytes"),
            "host_to_device_bytes": materialized.get("host_to_device_bytes"),
            "device_to_host_initial_bytes": materialized.get("device_to_host_initial_bytes"),
            "device_buffer_count": materialized.get("buffer_count"),
            "dcr_write_count": dcr.get("write_count"),
            "dcr_schedule_bytes": dcr.get("device_schedule_bytes"),
        },
        "observed_blocking_features": [
            "external_dpi_memory_authority",
            "stdout_TEST_PASSED_or_post_memory_authority",
            "ordered_dcr_schedule_required",
            "generated_lowered_tb_invocation_missing",
            "no_cpu_vs_hybrid_timing_yet",
        ],
        "hybrid_split_decision": {
            "decision_stage": "compile_time_fail_closed_until_first_gate_runtime_authority",
            "recommended_action": "do_not_claim_gpu_usefulness_until_vortex_mini_hello_timing_exists",
            "reason": "Vortex has useful parallel architecture shape, but the current evidence is bridge readiness, not measured hybrid execution",
        },
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_vortex_speedup",
            "not_mini_saxpy_or_sgemm_ready_before_mini_hello",
        ],
    }


def build_measurement_summary(repo_root: Path) -> dict[str, Any]:
    candidate_summary = build_candidate_summary(repo_root)
    nvdla = _summarize_nvdla(candidate_summary)
    vortex = _summarize_vortex(candidate_summary)
    measured_shape_count = _int(nvdla.get("measured_shape_count")) or 0
    gpu_favorable_shape_count = _int(nvdla.get("gpu_favorable_shape_count")) or 0
    vortex_timing_present = vortex.get("cpu_vs_hybrid_timing_present") is True

    if gpu_favorable_shape_count:
        recommended_next = "extend_nvdla_hot_ss_measurement_before_claiming_broader_rtlmeter_gpu_usefulness"
    elif not vortex_timing_present:
        recommended_next = "complete_vortex_mini_hello_first_cpu_vs_hybrid_gate"
    else:
        recommended_next = "compare_nvdla_and_vortex_measured_regions"

    return {
        "schema_version": 1,
        "surface": "rtlmeter_non_veer_hybrid_measurement_summary",
        "status": "analyzed",
        "scope": "non_veer_rtlmeter_hybrid_usefulness",
        "counts": {
            "measured_design_count": 1 if measured_shape_count else 0,
            "measured_shape_count": measured_shape_count,
            "gpu_favorable_shape_count": gpu_favorable_shape_count,
            "unmeasured_first_gate_candidate_count": 0 if vortex_timing_present else 1,
        },
        "nvdla": nvdla,
        "vortex": vortex,
        "hybrid_recommendation": {
            "recommended_next": recommended_next,
            "compile_time_policy": (
                "compile-time should select only reviewed hot-SS candidates; runtime shape/timing evidence "
                "must still confirm usefulness before a speedup claim"
            ),
            "reason": (
                "NVDLA is the only non-VeeR candidate with current CPU-vs-hybrid favorable timing; "
                "Vortex is useful as the next architecture-diverse gate but remains unmeasured"
            ),
            "non_claims": [
                "no_new_measurement_run",
                "no_new_speedup_claim",
                "no_automatic_hybrid_partition_claim",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_measurement_summary(Path(args.repo_root))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
