"""Evidence summary helpers for hybrid benchmark reports."""

from __future__ import annotations

import json
from pathlib import Path

from hybrid_benchmark_catalog import (
    BENCHMARKS,
    KIND_MOBILE_VIT_IMAGENET,
    KIND_SLICE_TEMPLATE,
    MODE_TEMPLATE,
    BenchmarkSpec,
    display_path as _display_path,
    repo_path as _repo_path,
)
from hybrid_benchmark_expected_reports import expected_reports
from hybrid_template_runner import load_template_plan


def _coverage_from_compare(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    coverage = payload.get("coverage_output_policy") or {}
    return {
        "compare_report": _display_path(path),
        "acceptance_policy": coverage.get("acceptance_policy"),
        "coverage_output_passed": coverage.get("passed"),
        "coverage_output_mismatch_count": coverage.get("mismatch_count"),
        "compared_word_count": coverage.get("compared_word_count"),
        "compared_byte_count": coverage.get("compared_byte_count"),
    }


def _template_evidence_summary(spec: BenchmarkSpec, *, shape: str | None) -> dict[str, object]:
    assert spec.template is not None
    assert shape is not None
    plan = load_template_plan(Path(spec.template), shape=shape)
    if not plan.compare_report.exists():
        return {"status": "missing", "missing_report": _display_path(plan.compare_report)}
    evidence = _coverage_from_compare(plan.compare_report)
    evidence["status"] = "collected"
    return evidence


def _mobile_vit_evidence_summary(*, aggregate: str, payload: dict[str, object]) -> dict[str, object]:
    hybrid_control = payload.get("hybrid_control") or {}
    return {
        "status": "collected",
        "aggregate_summary": aggregate,
        "evaluated_count": payload.get("evaluated_count"),
        "top1_accuracy": payload.get("top1_accuracy"),
        "top5_accuracy": payload.get("top5_accuracy"),
        "coverage_output_passed": hybrid_control.get("coverage_output_equivalence_complete"),
        "hybrid_batch_count": hybrid_control.get("batch_count"),
    }


def _phase_aggregate_evidence_summary(
    *,
    aggregate: str,
    payload: dict[str, object],
    shape: str | None,
    phases: int,
) -> dict[str, object]:
    actual_shape = payload.get("shape")
    actual_phases = payload.get("phases")
    if actual_shape != shape or actual_phases != phases:
        return {
            "status": "mismatched_summary",
            "aggregate_summary": aggregate,
            "expected_shape": shape,
            "actual_shape": actual_shape,
            "expected_phases": phases,
            "actual_phases": actual_phases,
            "coverage_output_passed": payload.get("all_coverage_output_passed"),
            "coverage_output_mismatch_count": payload.get("max_coverage_output_mismatch_count"),
        }
    return {
        "status": "collected",
        "aggregate_summary": aggregate,
        "acceptance_policy": payload.get("acceptance_policy"),
        "coverage_output_passed": payload.get("all_coverage_output_passed"),
        "coverage_output_mismatch_count": payload.get("max_coverage_output_mismatch_count"),
        "phase_count": len(payload.get("phase_reports") or []),
    }


def evidence_summary(
    *,
    target: str,
    shape: str | None,
    limit: int | None,
    mode: str,
    phases: int,
    execution_mode: str,
) -> dict[str, object]:
    if execution_mode not in ("executed", "existing_evidence"):
        return {
            "status": "not_collected",
            "reason": f"{execution_mode} does not execute benchmark commands",
        }

    spec = BENCHMARKS[target]
    if spec.kind == KIND_SLICE_TEMPLATE and mode == MODE_TEMPLATE:
        return _template_evidence_summary(spec, shape=shape)

    reports = expected_reports(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    aggregate = reports.get("aggregate_summary")
    if not isinstance(aggregate, str):
        return {"status": "not_available"}
    aggregate_path = _repo_path(aggregate)
    if not aggregate_path.exists():
        return {"status": "missing", "missing_report": aggregate}
    payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
    if spec.kind == KIND_MOBILE_VIT_IMAGENET:
        return _mobile_vit_evidence_summary(aggregate=aggregate, payload=payload)
    return _phase_aggregate_evidence_summary(
        aggregate=aggregate,
        payload=payload,
        shape=shape,
        phases=phases,
    )
