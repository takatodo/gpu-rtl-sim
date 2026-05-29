"""Dry-run policies for scoped filelist GPU allocation."""

from __future__ import annotations

import json
from collections.abc import Iterable

import results_reproduction_gpu_allocation_policy_data as policy_data


def _target_names(targets: Iterable[dict[str, object]]) -> list[object]:
    return [target["target"] for target in targets]


def _evidence(target: dict[str, object]) -> dict[str, object]:
    return {
        "state_parallel_wall_ratio_median": target["state_parallel_wall_ratio_median"],
        "state_parallel_kernel_ratio_median": target["state_parallel_kernel_ratio_median"],
        "single_state_repeated_wall_ratio_median": target["single_state_repeated_wall_ratio_median"],
        "single_state_repeated_kernel_ratio_median": target["single_state_repeated_kernel_ratio_median"],
        "coverage_output_mismatch_count": 0,
    }


def _refusals(*, broader: bool) -> list[dict[str, object]]:
    return [
        {
            "case": case,
            "confidence": confidence,
            "fallback": broader_fallback if broader else scoped_fallback,
        }
        for case, confidence, scoped_fallback, broader_fallback in policy_data.REFUSALS_OR_LOW_CONFIDENCE
    ]


def _recommendation(
    target: dict[str, object],
    *,
    shape: str,
    nstates: int,
    reason: str,
    fallback: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "target": target["target"],
        "template": target["template"],
        "recommended_nstates": nstates,
        "recommended_steps": 1,
        "recommended_shape": shape,
        "confidence": "high",
        "source_closure_status": "complete",
        "timing_evidence": "repeat_median_present",
        "repeat_count": 3,
        "evidence": _evidence(target),
        "reason": reason,
        "fallback": fallback,
    }
    if extra:
        payload.update(extra)
    return payload


def build_filelist_shape_breadth_gpu_allocation_policy_payload() -> dict[str, object]:
    reason = (
        "Reviewed repeat-count-3 evidence strongly favors 32x1 state-parallel sidecar use "
        "over 1x32 repeated-step launches for this exact tracked filelist target."
    )
    recommendations = [
        _recommendation(
            target,
            shape="32x1",
            nstates=32,
            reason=reason,
            fallback="Use explicit --sim-accel-shape 32x1 or --shape 32x1 for this tracked template.",
            extra={
                "source_evidence_gate": policy_data.SOURCE_MEASUREMENT_GATE,
                "source_review_gate": policy_data.SOURCE_REVIEW_GATE,
                "summary_report": policy_data.SOURCE_SUMMARY_REPORT,
            },
        )
        for target in policy_data.REVIEWED_TARGETS
    ]
    return {
        "schema_version": 1,
        "status": "passed_filelist_shape_breadth_gpu_allocation_policy_dry_run",
        "tool": "src/tools/run_results_reproduction.py",
        "mode": "filelist_shape_breadth_gpu_allocation_policy_dry_run",
        "dry_run": True,
        "dry_run_only": True,
        "writes_files": False,
        "source_policy_gate": "config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_gate.json",
        "source_evidence": {
            "measurement_gate": policy_data.SOURCE_MEASUREMENT_GATE,
            "review_gate": policy_data.SOURCE_REVIEW_GATE,
            "summary_report": policy_data.SOURCE_SUMMARY_REPORT,
            "repeat_count": 3,
            "targets": _target_names(policy_data.REVIEWED_TARGETS),
            "reviewed_shapes": ["32x1", "1x32"],
            "coverage_output_mismatch_count": 0,
        },
        "recommendations": recommendations,
        "refusals_or_low_confidence": _refusals(broader=False),
        "validation_cases": [
            "reviewed_targets_high_confidence",
            "unreviewed_target_refused",
            "incomplete_source_closure_refused",
            "missing_repeat_median_evidence_low",
            "1xN_repeated_step_low_or_resident_mitigation",
        ],
        "non_claims": policy_data.NON_CLAIMS,
    }


def build_filelist_broader_shape_gpu_allocation_policy_payload() -> dict[str, object]:
    reason = (
        "Reviewed repeat-count-3 broader-shape evidence strongly favors 64x1 "
        "state-parallel sidecar use over 1x64 repeated-step launches for this exact "
        "tracked filelist target."
    )
    recommendations = [
        _recommendation(
            target,
            shape="64x1",
            nstates=64,
            reason=reason,
            fallback="Use explicit --sim-accel-shape 32x1 or --shape 32x1 when 64 states are too wide.",
            extra={
                "confidence_basis": "reviewed_repeat_median_64x1_over_1x64",
                "source_evidence_gates": [
                    policy_data.SOURCE_MEASUREMENT_GATE,
                    policy_data.SOURCE_REVIEW_GATE,
                    policy_data.BROADER_SOURCE_MEASUREMENT_GATE,
                    policy_data.BROADER_SOURCE_REVIEW_GATE,
                ],
            },
        )
        for target in policy_data.BROADER_REVIEWED_TARGETS
    ]
    return {
        "schema_version": 1,
        "status": "passed_filelist_broader_shape_gpu_allocation_policy_dry_run",
        "tool": "src/tools/run_results_reproduction.py",
        "mode": "filelist_broader_shape_gpu_allocation_policy_dry_run",
        "dry_run": True,
        "dry_run_only": True,
        "writes_files": False,
        "source_policy_gate": policy_data.BROADER_SOURCE_POLICY_GATE,
        "source_evidence": {
            "prior": {
                "measurement_gate": policy_data.SOURCE_MEASUREMENT_GATE,
                "review_gate": policy_data.SOURCE_REVIEW_GATE,
                "summary_report": policy_data.SOURCE_SUMMARY_REPORT,
                "reviewed_shapes": ["32x1", "1x32"],
                "fallback_shape": "32x1",
            },
            "broader": {
                "measurement_gate": policy_data.BROADER_SOURCE_MEASUREMENT_GATE,
                "review_gate": policy_data.BROADER_SOURCE_REVIEW_GATE,
                "summary_report": policy_data.BROADER_SOURCE_SUMMARY_REPORT,
                "reviewed_shapes": ["64x1", "1x64"],
                "recommended_shape": "64x1",
            },
            "repeat_count": 3,
            "targets": _target_names(policy_data.BROADER_REVIEWED_TARGETS),
            "target_shape_pair_count": 8,
            "coverage_output_mismatch_count": 0,
        },
        "recommendations": recommendations,
        "fallback_recommendations": [
            {
                "target": target["target"],
                "template": target["template"],
                "recommended_nstates": 32,
                "recommended_steps": 1,
                "recommended_shape": "32x1",
                "confidence": "medium",
                "reason": "The earlier reviewed 32x1 policy remains the fallback when 64-state batching is not acceptable.",
            }
            for target in policy_data.BROADER_REVIEWED_TARGETS
        ],
        "refusals_or_low_confidence": _refusals(broader=True),
        "validation_cases": [
            "reviewed_targets_64x1_high_confidence",
            "reviewed_targets_32x1_medium_fallback",
            "unreviewed_target_refused",
            "incomplete_source_closure_refused",
            "missing_repeat_median_evidence_low",
            "1xN_repeated_step_low_or_resident_mitigation",
        ],
        "non_claims": policy_data.NON_CLAIMS,
    }


def _run_policy_dry_run(payload: dict[str, object], *, dry_run: bool, label: str) -> dict[str, object]:
    if not dry_run:
        raise ValueError(f"{label} GPU allocation policy planning is dry-run only")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def run_filelist_shape_breadth_gpu_allocation_policy_dry_run(*, dry_run: bool) -> dict[str, object]:
    return _run_policy_dry_run(
        build_filelist_shape_breadth_gpu_allocation_policy_payload(),
        dry_run=dry_run,
        label="filelist shape-breadth",
    )


def run_filelist_broader_shape_gpu_allocation_policy_dry_run(*, dry_run: bool) -> dict[str, object]:
    return _run_policy_dry_run(
        build_filelist_broader_shape_gpu_allocation_policy_payload(),
        dry_run=dry_run,
        label="filelist broader-shape",
    )
