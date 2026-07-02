"""Summarize NVDLA hot-SS repeat-median plan progress."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_PLAN = Path("reports/rtlmeter_nvdla_hot_ss_measurement_plan.json")


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


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


def _measurement_result(repo_root: Path, planned: Mapping[str, Any]) -> dict[str, Any]:
    report_rel = planned.get("report_out")
    if not isinstance(report_rel, str):
        raise ValueError("planned measurement missing report_out")
    report_path = repo_root / report_rel
    base = {
        "order": planned.get("order"),
        "id": planned.get("id"),
        "shape": planned.get("shape"),
        "report": _display_path(report_path, repo_root=repo_root),
    }
    if not report_path.exists():
        return {
            **base,
            "status": "not_measured",
            "coverage_output_equivalence_all_passed": None,
            "median": None,
        }
    report = _load_json(report_path)
    return {
        **base,
        "status": report.get("status"),
        "repeat_count": report.get("repeat_count"),
        "coverage_output_equivalence_all_passed": report.get("coverage_output_equivalence_all_passed"),
        "median": report.get("median"),
        "all_sample_coverage_mismatch_counts": [
            _mapping(_mapping(sample).get("coverage_output")).get("coverage_output_mismatch_count")
            for sample in report.get("samples", [])
            if isinstance(sample, Mapping)
        ],
    }


def build_summary(repo_root: Path, *, plan_path: Path = DEFAULT_PLAN) -> dict[str, Any]:
    resolved_plan = repo_root / plan_path
    plan = _load_json(resolved_plan)
    planned = plan.get("planned_measurements")
    if not isinstance(planned, list):
        raise ValueError("plan missing planned_measurements")
    results = [_measurement_result(repo_root, item) for item in planned if isinstance(item, Mapping)]
    measured = [item for item in results if item.get("status") == "measured"]
    passed = [item for item in measured if item.get("coverage_output_equivalence_all_passed") is True]
    favorable = [
        item
        for item in passed
        if (_number(_mapping(item.get("median")).get("cpu_to_hybrid_wall_speedup")) or 0) > 1.0
    ]
    best = max(
        favorable,
        key=lambda item: _number(_mapping(item.get("median")).get("cpu_to_hybrid_wall_speedup")) or 0.0,
        default=None,
    )
    return {
        "schema_version": 1,
        "surface": "rtlmeter_nvdla_hot_ss_repeat_summary",
        "status": "analyzed",
        "source_plan": _display_path(resolved_plan, repo_root=repo_root),
        "target": plan.get("target"),
        "planned_measurement_count": len(results),
        "measured_count": len(measured),
        "coverage_passed_count": len(passed),
        "gpu_favorable_count": len(favorable),
        "best_measured": best,
        "results": results,
        "non_claims": [
            "scoped_nvdla_hot_ss_repeat_summary_only",
            "not_full_nvdla_execution",
            "not_automatic_hybrid_partition",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--plan", default=DEFAULT_PLAN.as_posix(), help="NVDLA hot-SS measurement plan JSON")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)
    try:
        summary = build_summary(Path(args.repo_root), plan_path=Path(args.plan))
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
