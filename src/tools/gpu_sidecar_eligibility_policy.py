"""Conservative GPU sidecar eligibility policy.

This module consumes review/debug metadata such as the FC-063 LLVM RTL
suitability JSON and returns policy metadata. It does not execute RTL, authorize
runtime ABI, or claim speedup.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import re
import sys
from typing import Any


GOOD_VERDICT = "good_state_parallel"
POOR_VERDICT = "poor_requires_new_implementation"


def _parse_shape(shape: object) -> tuple[int | None, int | None]:
    if not isinstance(shape, str):
        return None, None
    match = re.fullmatch(r"(\d+)x(\d+)", shape.strip())
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _metric(report: Mapping[str, Any], name: str) -> Any:
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        return None
    return metrics.get(name)


def eligibility_from_suitability_report(
    suitability_report: Mapping[str, Any],
    *,
    observable_policy: str = "coverage_output_equivalence",
    source_closure_status: str = "unknown",
    measurement_region: str = "static_llvm_ir",
    state_bytes_estimate: int | None = None,
    output_words_estimate: int | None = None,
) -> dict[str, Any]:
    """Map a suitability report to a conservative FC-045 policy record."""

    shape = suitability_report.get("shape")
    independent_state_count, steps_per_state = _parse_shape(shape)
    verdict = suitability_report.get("verdict")
    recommended_path = suitability_report.get("recommended_path")
    target = suitability_report.get("target")
    metrics = suitability_report.get("metrics")
    valid_report = (
        suitability_report.get("surface") == "llvm_rtl_gpu_suitability"
        and suitability_report.get("status") == "analyzed"
        and isinstance(metrics, Mapping)
    )

    reasons: list[str] = []
    confidence = "low"
    recommended_action = "fail_closed_define_source_closure"

    if not valid_report:
        reasons.append("invalid_or_unsupported_suitability_report")
    elif source_closure_status not in {"reviewed", "complete"}:
        reasons.append("source_closure_not_reviewed")
    elif independent_state_count is None or steps_per_state is None:
        reasons.append("shape_missing_or_invalid")
        recommended_action = "fail_closed_define_measurement"
    elif steps_per_state > 1 and independent_state_count <= 1:
        reasons.append("single_state_repeated_step_shape")
        recommended_action = "prefer_resident_or_cpu_parallel_mitigation"
    elif verdict == POOR_VERDICT or recommended_path == "cpu_parallel_or_gem_like_mapping":
        reasons.append("suitability_recommends_cpu_or_new_mapping")
        recommended_action = "prefer_cpu_parallel_or_new_mapping"
    elif verdict == GOOD_VERDICT and recommended_path == "gpu_state_parallel":
        reasons.append("suitability_recommends_state_parallel_gpu")
        if independent_state_count >= 1024:
            recommended_action = "prefer_gpu_state_parallel_large_batch_with_caveats"
            confidence = "medium"
            reasons.append("large_independent_state_batch")
            reasons.append("kernel_only_or_region_scoped_evidence_required")
        else:
            recommended_action = "gpu_correctness_smoke_only_require_larger_batch_evidence"
            reasons.append("small_independent_state_batch")
            reasons.append("no_speedup_claim_for_64x1")
    else:
        reasons.append("suitability_uncertain_or_missing_favorable_path")
        recommended_action = "fail_closed_define_measurement"

    return {
        "schema_version": 1,
        "surface": "gpu_sidecar_eligibility_policy",
        "schema_role": "gpu_sidecar_eligibility_policy",
        "status": "analyzed" if valid_report else "unsupported",
        "target": target,
        "shape": shape,
        "independent_state_count": independent_state_count,
        "steps_per_state": steps_per_state,
        "observable_policy": observable_policy,
        "source_closure_status": source_closure_status,
        "state_bytes_estimate": state_bytes_estimate,
        "output_words_estimate": output_words_estimate,
        "measurement_region": measurement_region,
        "evidence_status": "debug_review_metadata_only",
        "suitability": {
            "surface": suitability_report.get("surface"),
            "verdict": verdict,
            "recommended_path": recommended_path,
            "branch_density": _metric(suitability_report, "branch_density"),
            "memory_regularity_score": _metric(suitability_report, "memory_regularity_score"),
            "state_independence_score": _metric(suitability_report, "state_independence_score"),
            "observable_pressure": _metric(suitability_report, "observable_pressure"),
        },
        "recommended_action": recommended_action,
        "confidence": confidence,
        "reasons": reasons,
        "non_claims": [
            "no_speedup_claim",
            "no_runtime_abi_change",
            "no_gpu_execution",
            "no_automatic_optimal_allocation_claim",
            "debug_json_not_runtime_abi",
        ],
    }


def _optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suitability-report", required=True, help="FC-063 suitability JSON input")
    parser.add_argument(
        "--source-closure-status",
        default="unknown",
        help="Source closure status, for example reviewed, complete, or unknown",
    )
    parser.add_argument("--observable-policy", default="coverage_output_equivalence")
    parser.add_argument("--measurement-region", default="static_llvm_ir")
    parser.add_argument("--state-bytes-estimate")
    parser.add_argument("--output-words-estimate")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        suitability_report = json.loads(Path(args.suitability_report).read_text(encoding="utf-8"))
        policy = eligibility_from_suitability_report(
            suitability_report,
            observable_policy=args.observable_policy,
            source_closure_status=args.source_closure_status,
            measurement_region=args.measurement_region,
            state_bytes_estimate=_optional_int(args.state_bytes_estimate),
            output_words_estimate=_optional_int(args.output_words_estimate),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(policy, indent=2, sort_keys=True))
    return 0
