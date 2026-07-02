"""Build the next non-VeeR RTLMeter hybrid measurement queue.

The queue consumes the non-VeeR measurement summary and turns it into ordered
next work. It is a planning/reporting surface only: it does not run Verilator,
launch GPU code, or promote speedup claims beyond the existing measured
evidence.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any

from rtlmeter_non_veer_hybrid_measurement_summary import build_measurement_summary


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _best_bucket(shape_buckets: Mapping[str, Any]) -> tuple[str | None, Mapping[str, Any]]:
    best_name: str | None = None
    best_bucket: Mapping[str, Any] = {}
    best_ratio: float | None = None
    for name, value in shape_buckets.items():
        bucket = _mapping(value)
        ratio = _number(_mapping(bucket.get("best_wall_speedup")).get("cpu_to_hybrid_wall_speedup_ratio"))
        if ratio is None:
            continue
        if best_ratio is None or ratio > best_ratio:
            best_name = str(name)
            best_bucket = bucket
            best_ratio = ratio
    return best_name, best_bucket


def _nvdla_queue_item(summary: Mapping[str, Any]) -> dict[str, Any] | None:
    nvdla = _mapping(summary.get("nvdla"))
    shape_buckets = _mapping(nvdla.get("shape_buckets"))
    favorable = _int(nvdla.get("gpu_favorable_shape_count")) or 0
    measured = _int(nvdla.get("measured_shape_count")) or 0
    if not measured:
        return None
    best_bucket_name, best_bucket = _best_bucket(shape_buckets)
    best_wall = _mapping(nvdla.get("best_wall_speedup"))
    return {
        "priority": 1 if favorable else 3,
        "id": "nvdla_hot_ss_measurement_extension",
        "target_family": "NVDLA",
        "status": "ready_to_extend_measured_hot_ss" if favorable else "needs_first_favorable_measurement",
        "measurement_kind": "coverage_output_equivalent_cpu_vs_hybrid_timing",
        "why": [
            "already_has_measured_non_veer_gpu_favorable_shapes" if favorable else "has_measurements_without_gpu_favorable_shape",
            "scoped_hot_ss_boundary",
            "no_vortex_first_gate_timing_required_for_this_extension",
        ],
        "current_evidence": {
            "measured_shape_count": measured,
            "gpu_favorable_shape_count": favorable,
            "favorable_ratio": nvdla.get("favorable_ratio"),
            "best_wall_speedup": best_wall,
            "best_shape_bucket": best_bucket_name,
            "best_bucket_wall_speedup": best_bucket.get("best_wall_speedup"),
        },
        "next_measurement": {
            "recommended_scope": "repeat_or_extend_best_observed_hot_ss_bucket",
            "preferred_bucket": best_bucket_name,
            "preferred_target": best_wall.get("target"),
            "preferred_shape": best_wall.get("shape"),
            "acceptance": [
                "coverage_output_equivalence_passed",
                "cpu_elapsed_ms_reported",
                "hybrid_wall_time_ms_reported",
                "repeat_median_or_explicit_single_sample_reason",
            ],
        },
        "claim_policy": {
            "speedup_claim_allowed": False,
            "allowed_claim": "measured_candidate_for_gpu_favorable_conditions_only",
            "blocked_claims": [
                "full_nvdla_execution",
                "unmeasured_shape_speedup",
                "automatic_hybrid_partition",
            ],
        },
    }


def _vortex_queue_item(summary: Mapping[str, Any]) -> dict[str, Any] | None:
    vortex = _mapping(summary.get("vortex"))
    if not vortex:
        return None
    missing = vortex.get("missing_prerequisites")
    if not isinstance(missing, list):
        missing = []
    bridge = _mapping(vortex.get("bridge_quantities"))
    required_before_timing = [item for item in missing if item != "cpu_vs_hybrid_timing_report.vortex"]
    first_missing = required_before_timing[0] if required_before_timing else (missing[0] if missing else None)
    return {
        "priority": 2,
        "id": "vortex_mini_hello_first_cpu_vs_hybrid_gate",
        "target_family": "Vortex",
        "status": (
            "ready_for_cpu_vs_hybrid_measurement"
            if vortex.get("cpu_vs_hybrid_timing_present") is True
            else "blocked_until_runtime_authority_and_observable_export"
        ),
        "measurement_kind": "first_gate_stdout_or_post_memory_authority_then_cpu_vs_hybrid_timing",
        "why": [
            "architecture_diverse_non_veer_candidate",
            "first_gate_inputs_and_bridge_quantities_are_materialized",
            "not_measured_yet",
        ],
        "current_evidence": {
            "first_gate": vortex.get("first_gate"),
            "hybrid_measurement_status": vortex.get("hybrid_measurement_status"),
            "cpu_vs_hybrid_timing_present": vortex.get("cpu_vs_hybrid_timing_present"),
            "bridge_quantities": bridge,
            "missing_prerequisites": missing,
        },
        "next_measurement": {
            "recommended_scope": "complete_vortex_mini_hello_first_gate_before_saxpy_or_sgemm",
            "first_blocker": first_missing,
            "required_before_timing": required_before_timing,
            "acceptance": [
                "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
                "runtime_execution_reports_vortex_observable_authority",
                "stdout_TEST_PASSED_or_memory_post_condition_gpu_observable",
                "cpu_vs_hybrid_timing_report.vortex",
            ],
        },
        "claim_policy": {
            "speedup_claim_allowed": False,
            "allowed_claim": "first_gate_candidate_only_until_timing_exists",
            "blocked_claims": [
                "vortex_gpu_execution",
                "vortex_speedup",
                "mini_saxpy_or_sgemm_before_mini_hello",
            ],
        },
    }


def build_queue(repo_root: Path, *, summary_path: Path | None = None) -> dict[str, Any]:
    summary = _load_json(summary_path) if summary_path is not None else build_measurement_summary(repo_root)
    items = [item for item in (_nvdla_queue_item(summary), _vortex_queue_item(summary)) if item is not None]
    items.sort(key=lambda item: int(item["priority"]))
    return {
        "schema_version": 1,
        "surface": "rtlmeter_non_veer_hybrid_next_queue",
        "status": "planned",
        "source_summary": _display_path(summary_path, repo_root=repo_root) if summary_path is not None else "generated_from_repo_root",
        "queue_count": len(items),
        "top_priority": items[0]["id"] if items else None,
        "top_priority_reason": (
            "NVDLA is the only current non-VeeR measured GPU-favorable region; Vortex remains next after first-gate authority"
            if items and items[0]["id"] == "nvdla_hot_ss_measurement_extension"
            else "no measured NVDLA GPU-favorable region is available"
        ),
        "queue": items,
        "non_claims": [
            "no_new_measurement_run",
            "no_new_speedup_claim",
            "not_a_scheduler_or_runtime_abi",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--summary", help="Optional precomputed non-VeeR hybrid measurement summary JSON")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        queue = build_queue(Path(args.repo_root), summary_path=Path(args.summary) if args.summary else None)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(queue, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
