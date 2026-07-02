"""Aggregate RTLMeter CPU/GPU advantage evidence.

The report produced here is a measurement index, not a new speedup claim. It
summarizes existing RTLMeter JSON outputs so the hybrid split can be discussed
with comparable CPU-parallel, GPU-sidecar, launch-feasibility, and bounded
progress numbers.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
import json
from pathlib import Path
import sys
from typing import Any


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _display_path(path: Path, *, repo_root: Path | None = None) -> str:
    try:
        if repo_root is not None:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        pass
    return path.as_posix()


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


def _summary(report: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(report.get("summary"))


def _cpu_parallel_summary(report: Mapping[str, Any]) -> Mapping[str, Any]:
    own_summary = _summary(report)
    if "parallel_wall_s" in own_summary or "parallel_speedup_vs_serial_sum" in own_summary:
        return own_summary
    return _mapping(report.get("cpu_parallel_baseline")).get("summary", {})  # type: ignore[return-value]


def _case_count(report: Mapping[str, Any]) -> int | None:
    summary = _summary(report)
    baseline_summary = _mapping(_mapping(report.get("cpu_parallel_baseline")).get("summary"))
    methodology = _mapping(report.get("methodology"))
    for source in (summary, baseline_summary, methodology):
        value = _int(source.get("case_count") or source.get("sidecar_nstates_override"))
        if value is not None:
            return value
    value = _int(report.get("sidecar_state_count"))
    if value is not None:
        return value
    return None


def _timing_metrics(report: Mapping[str, Any]) -> dict[str, Any] | None:
    summary = _summary(report)
    wall = _number(summary.get("sidecar_wall_s_median"))
    kernel_ms = _number(summary.get("gpu_kernel_ms_total_median"))
    ratio = _number(summary.get("sidecar_vs_cpu_parallel_ratio"))
    if wall is None and kernel_ms is None and ratio is None:
        return None
    nstates = _case_count(report)
    return {
        "sidecar_wall_s_median": wall,
        "gpu_kernel_ms_total_median": kernel_ms,
        "sidecar_vs_cpu_parallel_ratio": ratio,
        "nstates": nstates,
        "sidecar_wall_s_per_state": wall / nstates if wall is not None and nstates else None,
        "states_per_second": nstates / wall if wall and nstates else None,
    }


def _cpu_parallel_metrics(report: Mapping[str, Any]) -> dict[str, Any] | None:
    summary = _cpu_parallel_summary(report)
    wall = _number(summary.get("parallel_wall_s"))
    speedup = _number(summary.get("parallel_speedup_vs_serial_sum"))
    efficiency = _number(summary.get("parallel_efficiency"))
    case_count = _int(summary.get("case_count"))
    if wall is None and speedup is None and efficiency is None:
        return None
    return {
        "case_count": case_count,
        "parallel_wall_s": wall,
        "parallel_speedup_vs_serial_sum": speedup,
        "parallel_efficiency": efficiency,
        "all_runs_passed": summary.get("all_runs_passed"),
        "all_observables_match": summary.get("all_observables_match"),
    }


def _launch_feasibility(report: Mapping[str, Any]) -> dict[str, Any] | None:
    feasibility = _mapping(report.get("launch_count_feasibility"))
    if not feasibility:
        return None
    threshold = _int(feasibility.get("threshold"))
    if threshold is None:
        threshold = _int(feasibility.get("max_pair_cycle_fused_launches"))
    return {
        "status": feasibility.get("status"),
        "estimated_actual_timed_launches": _int(feasibility.get("estimated_actual_timed_launches")),
        "threshold": threshold,
    }


def _bounded_progress(report: Mapping[str, Any]) -> dict[str, Any] | None:
    if report.get("bounded_progress_evidence") is True:
        return {
            "report_count": _int(report.get("report_count")),
            "passed_report_count": _int(report.get("passed_report_count")),
            "timing_measured": report.get("timing_measured"),
            "speedup_claimed": report.get("speedup_claimed"),
        }
    if report.get("status") == "observables_emitted" and _mapping(report.get("observables")):
        validation = _mapping(report.get("parallel_state_validation"))
        timing = _mapping(report.get("run_vl_hybrid_timing"))
        return {
            "report_count": 1,
            "passed_report_count": 1 if validation.get("parallel_state_observables_match") is True else None,
            "timing_measured": False,
            "speedup_claimed": report.get("speedup_claimed"),
            "gpu_kernel_timed_launch_count": _int(timing.get("gpu_kernel_timed_launch_count")),
        }
    return None


def analyze_report(path: Path, report: Mapping[str, Any], *, repo_root: Path | None = None) -> dict[str, Any]:
    timing = _timing_metrics(report)
    cpu_parallel = _cpu_parallel_metrics(report)
    feasibility = _launch_feasibility(report)
    bounded = _bounded_progress(report)

    classifications: list[str] = []
    if cpu_parallel is not None and cpu_parallel.get("parallel_speedup_vs_serial_sum"):
        classifications.append("cpu_parallel_favorable")
    if timing is not None and timing.get("sidecar_vs_cpu_parallel_ratio") is not None:
        ratio = timing["sidecar_vs_cpu_parallel_ratio"]
        if ratio < 1.0:
            classifications.append("gpu_sidecar_favorable")
        elif ratio > 1.0:
            classifications.append("gpu_sidecar_unfavorable")
    if report.get("speedup_claimed") is False:
        classifications.append("no_gpu_speedup_claim")
    if feasibility is not None:
        classifications.append("launch_feasibility_blocked" if feasibility.get("status") else "launch_feasibility_recorded")
    if bounded is not None:
        classifications.append("gpu_bounded_progress")
    if not classifications:
        classifications.append("unclassified")

    return {
        "source": _display_path(path, repo_root=repo_root),
        "status": report.get("status"),
        "case": report.get("case"),
        "classifications": classifications,
        "cpu_parallel": cpu_parallel,
        "gpu_timing": timing,
        "launch_feasibility": feasibility,
        "bounded_progress": bounded,
        "speedup_claimed": report.get("speedup_claimed"),
        "cpu_as_gpu_fallback": report.get("cpu_as_gpu_fallback"),
    }


def _min_record(records: Iterable[dict[str, Any]], field_path: tuple[str, ...]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_value: float | None = None
    for record in records:
        value: object = record
        for field in field_path:
            value = _mapping(value).get(field)
        number = _number(value)
        if number is None:
            continue
        if best_value is None or number < best_value:
            best = record
            best_value = number
    return best


def _max_record(records: Iterable[dict[str, Any]], field_path: tuple[str, ...]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_value: float | None = None
    for record in records:
        value: object = record
        for field in field_path:
            value = _mapping(value).get(field)
        number = _number(value)
        if number is None:
            continue
        if best_value is None or number > best_value:
            best = record
            best_value = number
    return best


def aggregate_reports(report_paths: Iterable[Path], *, repo_root: Path | None = None) -> dict[str, Any]:
    reports = [analyze_report(path, _load_json(path), repo_root=repo_root) for path in report_paths]
    timing_reports = [report for report in reports if report.get("gpu_timing")]
    cpu_reports = [report for report in reports if report.get("cpu_parallel")]
    launch_blocked = [report for report in reports if "launch_feasibility_blocked" in report["classifications"]]
    bounded = [report for report in reports if "gpu_bounded_progress" in report["classifications"]]
    sidecar_slower = [
        report
        for report in timing_reports
        if _number(_mapping(report.get("gpu_timing")).get("sidecar_vs_cpu_parallel_ratio")) is not None
        and _number(_mapping(report.get("gpu_timing")).get("sidecar_vs_cpu_parallel_ratio")) > 1.0
    ]
    sidecar_faster = [
        report
        for report in timing_reports
        if _number(_mapping(report.get("gpu_timing")).get("sidecar_vs_cpu_parallel_ratio")) is not None
        and _number(_mapping(report.get("gpu_timing")).get("sidecar_vs_cpu_parallel_ratio")) < 1.0
    ]

    if sidecar_faster:
        recommendation = "prefer_gpu_sidecar_for_matching_measured_region"
        confidence = "medium"
    elif bounded or launch_blocked or sidecar_slower:
        recommendation = "prefer_cpu_parallel_control_with_gpu_bounded_batch_probes"
        confidence = "medium" if cpu_reports else "low"
    else:
        recommendation = "insufficient_evidence_define_measurement"
        confidence = "low"

    best_total = _min_record(timing_reports, ("gpu_timing", "sidecar_wall_s_median"))
    best_per_state = _min_record(timing_reports, ("gpu_timing", "sidecar_wall_s_per_state"))
    best_cpu_parallel = _max_record(cpu_reports, ("cpu_parallel", "parallel_speedup_vs_serial_sum"))
    worst_sidecar_ratio = _max_record(timing_reports, ("gpu_timing", "sidecar_vs_cpu_parallel_ratio"))
    best_sidecar_ratio = _min_record(timing_reports, ("gpu_timing", "sidecar_vs_cpu_parallel_ratio"))

    return {
        "schema_version": 1,
        "surface": "rtlmeter_hybrid_advantage",
        "status": "analyzed",
        "report_count": len(reports),
        "counts": {
            "cpu_parallel_favorable": sum("cpu_parallel_favorable" in report["classifications"] for report in reports),
            "gpu_sidecar_favorable": len(sidecar_faster),
            "gpu_sidecar_unfavorable": len(sidecar_slower),
            "launch_feasibility_blocked": len(launch_blocked),
            "gpu_bounded_progress": len(bounded),
            "no_gpu_speedup_claim": sum("no_gpu_speedup_claim" in report["classifications"] for report in reports),
        },
        "best_gpu_total_wall": best_total,
        "best_gpu_per_state_wall": best_per_state,
        "best_cpu_parallel_speedup": best_cpu_parallel,
        "best_sidecar_vs_cpu_parallel_ratio": best_sidecar_ratio,
        "worst_sidecar_vs_cpu_parallel_ratio": worst_sidecar_ratio,
        "hybrid_recommendation": {
            "recommended_action": recommendation,
            "confidence": confidence,
            "reason": (
                "current RTLMeter evidence favors CPU-parallel full-program control while keeping "
                "GPU sidecar for bounded batched probes or future region-specific kernels"
            ),
            "non_claims": [
                "no_new_speedup_claim",
                "no_runtime_abi_change",
                "no_automatic_optimal_allocation_claim",
            ],
        },
        "reports": reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, help="Input RTLMeter JSON report; repeatable")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    parser.add_argument("--repo-root", default=".", help="Path base used to display relative report paths")
    args = parser.parse_args(argv)

    try:
        repo_root = Path(args.repo_root)
        aggregate = aggregate_reports([Path(path) for path in args.report], repo_root=repo_root)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
