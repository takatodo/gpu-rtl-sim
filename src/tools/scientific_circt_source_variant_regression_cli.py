#!/usr/bin/env python3
"""Thin CLI: FC-076 regression harness over recorded source-variant rows.

`--run` repeat-samples each reference row's real run through
`scientific_circt_source_variant_bridge_emit.run_source_variant` (via
`scientific_circt_source_variant_regression.run_variant_samples`) and checks
promoted rows with `decide_promote_case` / the fallback row with
`decide_fallback_case`. `--self-check` needs no GPU: it feeds
`inject_corrupted_samples("oracle")` and `("speedup")` through the real
`decide_promote_case` and exits 0 only when both corruptions are detected
with their specific fail-closed reason.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import scientific_circt_source_variant_bridge_emit as bridge_emit
import scientific_circt_source_variant_metadata as metadata_module
import scientific_circt_source_variant_regression as regression

DEFAULT_RUN_REPORT_OUT = Path("reports/scientific_circt_source_variant_regression.json")
DEFAULT_SELF_CHECK_REPORT_OUT = Path("reports/scientific_circt_source_variant_regression_self_check.json")


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _select_cases(cases: list[regression.RegressionCase], wanted: list[str]) -> list[regression.RegressionCase] | None:
    if not wanted:
        return cases
    known = {case.source_variant for case in cases}
    unknown = sorted(set(wanted) - known)
    if unknown:
        return None
    return [case for case in cases if case.source_variant in wanted]


def self_check(cases: list[regression.RegressionCase]) -> dict[str, Any]:
    promote_cases = [case for case in cases if case.expected_policy == "promote_to_hls_gpu"]
    detections: dict[str, dict[str, Any]] = {}
    all_detected = True
    for kind, expected_reason in (("oracle", "oracle_mismatch"), ("speedup", "speedup_out_of_band")):
        samples = regression.inject_corrupted_samples(kind)
        per_variant: dict[str, Any] = {}
        kind_all_detected = True
        for case in promote_cases:
            passed, reason = regression.decide_promote_case(case, samples)
            detected = (not passed) and reason == expected_reason
            per_variant[case.source_variant] = {"detected": detected, "reason": reason}
            if not detected:
                kind_all_detected = False
        detections[kind] = {
            "expected_reason": expected_reason,
            "all_detected": kind_all_detected,
            "per_variant": per_variant,
        }
        if not kind_all_detected:
            all_detected = False
    return {
        "schema_version": 1,
        "surface": "scientific_circt_source_variant_regression_self_check",
        "status": "self_check_passed" if all_detected else "self_check_failed",
        "oracle_detected": detections["oracle"]["all_detected"],
        "speedup_detected": detections["speedup"]["all_detected"],
        "detections": detections,
        "non_claims": ["synthetic corrupted samples only", "no GPU dispatched"],
    }


def run_regression(
    cases: list[regression.RegressionCase],
    *,
    metadata_report: dict[str, Any],
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    repeat: int,
) -> dict[str, Any]:
    by_variant = metadata_module.metadata_rows_by_variant(metadata_report)
    results: dict[str, Any] = {}
    overall_passed = True
    for case in cases:
        row = by_variant.get(case.source_variant)
        if row is None:
            results[case.source_variant] = {
                "passed": False,
                "reason": "metadata_row_missing",
                "expected_policy": case.expected_policy,
            }
            overall_passed = False
            continue
        if case.expected_policy == "promote_to_hls_gpu":
            samples = regression.run_variant_samples(row, matrix, hls_summary, repeat)
            passed, reason = regression.decide_promote_case(case, samples)
            results[case.source_variant] = {
                "passed": passed,
                "reason": reason,
                "expected_policy": case.expected_policy,
                "repeat": repeat,
                "median_observed_speedup": regression.median_speedup(samples),
                "recorded_variant_speedup": case.recorded_variant_speedup,
            }
        else:
            run_report = regression.default_real_runner(row, matrix, hls_summary)
            passed, reason = regression.decide_fallback_case(case, run_report)
            results[case.source_variant] = {
                "passed": passed,
                "reason": reason,
                "expected_policy": case.expected_policy,
                "run_status": run_report.get("status"),
            }
        if not passed:
            overall_passed = False
    return {
        "schema_version": 1,
        "surface": "scientific_circt_source_variant_regression_cli",
        "status": "regression_passed" if overall_passed else "regression_failed",
        "results": results,
        "overall_passed": overall_passed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=regression.REFERENCE)
    parser.add_argument("--variant", action="append", default=[], help="Limit to one source_variant; repeatable. Default: all reference rows.")
    parser.add_argument("--repeat", type=int, default=3)

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true", help="Repeat-sample real runs and check against the reference.")
    mode.add_argument("--self-check", action="store_true", help="Fail-closed self-check of the decision functions; needs no GPU.")

    parser.add_argument("--metadata-report", type=Path, default=bridge_emit.METADATA_REPORT)
    parser.add_argument("--matrix", type=Path, default=bridge_emit.MATRIX_REPORT)
    parser.add_argument("--hls-variant-report", type=Path, default=bridge_emit.HLS_VARIANT_REPORT)
    parser.add_argument("--extra-hls-variant-report", type=Path, action="append", default=list(bridge_emit.EXTRA_HLS_VARIANT_REPORTS))
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        cases = regression.load_reference(args.reference)
    except Exception as exc:
        print(json.dumps({"status": "failed_reference_load", "reason": str(exc)}))
        return 2

    selected = _select_cases(cases, args.variant)
    if selected is None:
        unknown = sorted(set(args.variant) - {case.source_variant for case in cases})
        print(json.dumps({"status": "failed_unknown_variant", "unknown": unknown}))
        return 2

    if args.self_check:
        summary = self_check(selected)
    else:
        try:
            metadata_report = _load(args.metadata_report)
            matrix = _load(args.matrix)
            hls_summary = metadata_module.combined_hls_summary(
                _load(args.hls_variant_report),
                [_load(path) for path in args.extra_hls_variant_report],
            )
        except Exception as exc:
            print(json.dumps({"status": "failed_report_load", "reason": str(exc)}))
            return 2
        summary = run_regression(
            selected,
            metadata_report=metadata_report,
            matrix=matrix,
            hls_summary=hls_summary,
            repeat=args.repeat,
        )

    if args.write_report:
        report_out = args.report_out or (DEFAULT_SELF_CHECK_REPORT_OUT if args.self_check else DEFAULT_RUN_REPORT_OUT)
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    passed = summary["status"] in {"self_check_passed", "regression_passed"}
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
