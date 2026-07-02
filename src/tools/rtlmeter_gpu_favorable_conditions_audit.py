"""Audit whether the RTLMeter GPU-favorable-condition search has succeeded."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_NVDLA_SUMMARY = Path("reports/rtlmeter_nvdla_hot_ss_repeat_summary.json")
DEFAULT_VORTEX_READINESS = Path("reports/rtlmeter_vortex_first_gate_readiness.json")


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


def build_audit(
    repo_root: Path,
    *,
    nvdla_summary_path: Path = DEFAULT_NVDLA_SUMMARY,
    vortex_readiness_path: Path = DEFAULT_VORTEX_READINESS,
) -> dict[str, Any]:
    nvdla_path = repo_root / nvdla_summary_path
    vortex_path = repo_root / vortex_readiness_path
    nvdla = _load_json(nvdla_path)
    vortex = _load_json(vortex_path)
    best = _mapping(nvdla.get("best_measured"))
    best_median = _mapping(best.get("median"))
    favorable_count = int(nvdla.get("gpu_favorable_count") or 0)
    coverage_count = int(nvdla.get("coverage_passed_count") or 0)
    measured_count = int(nvdla.get("measured_count") or 0)
    planned_count = int(nvdla.get("planned_measurement_count") or 0)
    best_speedup = _number(best_median.get("cpu_to_hybrid_wall_speedup"))
    nvdla_positive = (
        planned_count > 0
        and measured_count == planned_count
        and coverage_count == planned_count
        and favorable_count == planned_count
        and best_speedup is not None
        and best_speedup > 1.0
    )
    vortex_missing = vortex.get("missing_prerequisites")
    if not isinstance(vortex_missing, list):
        vortex_missing = []
    return {
        "schema_version": 1,
        "surface": "rtlmeter_gpu_favorable_conditions_audit",
        "status": "goal_satisfied_by_nvdla_hot_ss" if nvdla_positive else "not_satisfied",
        "objective": "find_gpu_favorable_rtlmeter_conditions_beyond_veer_portability",
        "completion_decision": {
            "achieved": nvdla_positive,
            "primary_evidence": "NVDLA.nvdla_cmac_a2cacc hot-SS repeat-median plan",
            "reason": (
                "all planned NVDLA a2cacc hot-SS repeat-median shapes are measured, "
                "coverage-output-equivalent, and GPU-favorable by wall time"
                if nvdla_positive
                else "NVDLA hot-SS evidence is incomplete or not favorable"
            ),
        },
        "nvdla": {
            "summary": _display_path(nvdla_path, repo_root=repo_root),
            "planned_measurement_count": planned_count,
            "measured_count": measured_count,
            "coverage_passed_count": coverage_count,
            "gpu_favorable_count": favorable_count,
            "best_shape": best.get("shape"),
            "best_cpu_to_hybrid_wall_speedup": best_speedup,
            "claim_scope": "scoped_hot_ss_coverage_output_equivalence_only",
        },
        "vortex": {
            "readiness": _display_path(vortex_path, repo_root=repo_root),
            "status": vortex.get("status"),
            "cpu_vs_hybrid_timing_present": "cpu_vs_hybrid_timing_report.vortex" not in vortex_missing,
            "remaining_generalization_role": "architecture_diverse_followup_not_required_for_current_positive_evidence",
            "missing_prerequisites": vortex_missing,
        },
        "veer": {
            "role": "portability_evidence_not_gpu_favorable_condition_basis",
        },
        "non_claims": [
            "not_full_nvdla_execution",
            "not_vortex_speedup",
            "not_arbitrary_rtlmeter_speedup",
            "not_automatic_hybrid_partition",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--nvdla-summary", default=DEFAULT_NVDLA_SUMMARY.as_posix())
    parser.add_argument("--vortex-readiness", default=DEFAULT_VORTEX_READINESS.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out")
    args = parser.parse_args(argv)
    try:
        audit = build_audit(
            Path(args.repo_root),
            nvdla_summary_path=Path(args.nvdla_summary),
            vortex_readiness_path=Path(args.vortex_readiness),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["completion_decision"]["achieved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
