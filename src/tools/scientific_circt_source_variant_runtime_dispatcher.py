#!/usr/bin/env python3
"""Dispatch measured HLS source variants through metadata-described runtime boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scientific_circt_source_variant_metadata import (
    DEFAULT_SOURCE_VARIANTS,
    build_source_variant_metadata_report,
    combined_hls_summary,
    load_json,
    metadata_rows_by_variant,
)
from scientific_circt_source_variant_runtime_handoff import (
    SRC_HYBRID_BRIDGE,
    SRC_HYBRID_OUT_DIR,
    build_runtime_handoff_report,
)

REPORT = Path("reports/scientific_circt_source_variant_runtime_dispatcher.json")
MULTI_REPORT = Path("reports/scientific_circt_source_variant_runtime_dispatcher_multi.json")


def _selected_boundary(matrix: dict[str, Any]) -> dict[str, Any]:
    selected = matrix.get("selected_next_source_variant_runtime_boundary")
    if not isinstance(selected, dict):
        raise ValueError("dispatch matrix missing selected_next_source_variant_runtime_boundary")
    return selected


def _boundary_key(selected: dict[str, Any]) -> tuple[str, str, str]:
    candidate = selected.get("candidate")
    source_variant = selected.get("source_variant")
    shape = selected.get("shape")
    if not isinstance(candidate, str) or not isinstance(source_variant, str) or not isinstance(shape, str):
        raise ValueError("selected boundary missing candidate/source_variant/shape")
    return candidate, source_variant, shape


def _variant_report(summary: dict[str, Any], source_variant: str) -> dict[str, Any] | None:
    variants = summary.get("variants")
    rows = [variant for variant in variants if isinstance(variant, dict)] if isinstance(variants, list) else []
    if isinstance(summary.get("variant"), str):
        rows.append(summary)
    for variant in rows:
        if variant.get("variant") == source_variant:
            return variant
    return None


def _metadata_report(
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    if metadata is not None:
        return metadata
    return build_source_variant_metadata_report(matrix, hls_summary)


def _metadata_row(
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    metadata: dict[str, Any] | None,
    source_variant: str,
) -> dict[str, Any] | None:
    report = _metadata_report(matrix, hls_summary, metadata)
    return metadata_rows_by_variant(report).get(source_variant)


def _row_boundary(row: dict[str, Any]) -> dict[str, Any]:
    boundary = row.get("boundary") if isinstance(row.get("boundary"), dict) else {}
    return {
        "candidate": boundary.get("candidate") or row.get("candidate"),
        "source_variant": row.get("source_variant"),
        "shape": boundary.get("shape") or row.get("shape"),
        "rank": boundary.get("rank") or row.get("rank"),
        "selection_reason": row.get("selection_reason"),
        "baseline_speedup": boundary.get("baseline_speedup"),
        "variant_speedup": boundary.get("variant_speedup"),
        "speedup_delta": boundary.get("speedup_delta"),
        "steps": boundary.get("steps"),
        "cpu_owner": boundary.get("cpu_owner"),
        "gpu_subsystem": boundary.get("gpu_subsystem"),
    }


def _artifact_path(row: dict[str, Any], key: str, fallback: Path) -> Path:
    artifacts = row.get("artifacts") if isinstance(row.get("artifacts"), dict) else {}
    artifact = artifacts.get(key) if isinstance(artifacts.get(key), dict) else {}
    path = artifact.get("path")
    return Path(path) if isinstance(path, str) and path else fallback


def dispatch_source_variant_runtime(
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    *,
    source_variant: str | None = None,
    shape: str | None = None,
    steps: int | None = None,
    execute: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected = _selected_boundary(matrix)
    _, selected_variant, _ = _boundary_key(selected)
    requested_variant = source_variant or selected_variant
    metadata_report = _metadata_report(matrix, hls_summary, metadata)
    metadata_rows = metadata_rows_by_variant(metadata_report)
    row = metadata_rows.get(requested_variant)
    if row is None:
        row = metadata_rows.get(selected_variant)
    boundary = _row_boundary(row) if row is not None else selected
    candidate, boundary_variant, boundary_shape = _boundary_key(boundary)
    requested_shape = shape
    variant = _variant_report(hls_summary, requested_variant)
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_source_variant_runtime_dispatcher",
        "source_matrix_surface": matrix.get("surface"),
        "source_hls_summary_surface": hls_summary.get("surface"),
        "source_metadata_surface": metadata_report.get("surface"),
        "source_metadata_status": metadata_report.get("status"),
        "selected_boundary": {
            "candidate": selected.get("candidate"),
            "source_variant": selected_variant,
            "shape": selected.get("shape"),
            "rank": selected.get("rank"),
            "selection_reason": selected.get("selection_reason"),
        },
        "dispatch_boundary": {
            "candidate": candidate,
            "source_variant": boundary_variant,
            "shape": boundary_shape,
            "rank": boundary.get("rank"),
            "selection_reason": boundary.get("selection_reason"),
        },
        "requested_source_variant": requested_variant,
        "requested_shape": requested_shape,
        "requested_steps": steps,
        "supported_source_variants": sorted(metadata_rows),
        "execute": execute,
        "non_claims": [
            "not_full_microgpt_execution",
            "not_training_or_autograd",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
            "not_automatic_hls_rewrite",
            "not_production_runtime_dispatcher",
        ],
    }
    if requested_variant != boundary_variant:
        report["status"] = "dispatcher_rejected_unknown_source_variant"
        report["reason"] = "requested_source_variant_not_found_in_dispatch_matrix_or_hls_summary"
        return report
    if row is None:
        report["status"] = "dispatcher_missing_supported_boundary"
        report["reason"] = "source_variant_not_present_in_metadata"
        return report
    if row.get("candidate") != candidate or row.get("shape") != boundary_shape:
        report["status"] = "dispatcher_rejected_policy_mismatch"
        report["reason"] = "metadata_boundary_does_not_match_selection_matrix_candidate_or_shape"
        report["metadata_boundary"] = {
            "candidate": row.get("candidate"),
            "source_variant": requested_variant,
            "shape": row.get("shape"),
        }
        return report
    boundary_steps = boundary.get("steps")
    if requested_shape is not None and requested_shape != boundary_shape:
        report["status"] = "runtime_dispatch_cpu_fallback_unsupported_shape"
        report["reason"] = "requested_shape_not_in_measured_source_variant_boundary"
        report["cpu_fallback"] = True
        report["supported_shape"] = boundary_shape
        return report
    if steps is not None and boundary_steps is not None and steps != boundary_steps:
        report["status"] = "runtime_dispatch_cpu_fallback_unsupported_steps"
        report["reason"] = "requested_steps_not_in_measured_source_variant_boundary"
        report["cpu_fallback"] = True
        report["supported_steps"] = boundary_steps
        return report
    entrypoint = str(row.get("entrypoint_kind"))
    expected_boundary_kind = {
        "direct-binary": "direct_callsite_hls_source_variant_boundary",
        "src-hybrid-verilator": "src_hybrid_verilator_callsite_bridge",
        "fallback-baseline": "cpu_or_baseline_fallback",
    }.get(entrypoint)
    if row.get("metadata_complete") is not True:
        report["status"] = "dispatcher_rejected_incomplete_metadata"
        report["reason"] = "metadata_row_is_not_complete_for_runtime_dispatch"
        return report
    if expected_boundary_kind is None or row.get("runtime_boundary_kind") != expected_boundary_kind:
        report["status"] = "dispatcher_rejected_policy_mismatch"
        report["reason"] = "metadata_entrypoint_and_runtime_boundary_kind_do_not_match"
        report["metadata_boundary"] = {
            "entrypoint_kind": row.get("entrypoint_kind"),
            "runtime_boundary_kind": row.get("runtime_boundary_kind"),
        }
        return report
    if entrypoint == "fallback-baseline":
        report.update(
            {
                "status": "runtime_dispatch_fallback_baseline",
                "runtime_boundary_kind": row.get("runtime_boundary_kind"),
                "entrypoint": entrypoint,
                "policy": row.get("policy"),
                "reason": row.get("fallback_reason") or "source_variant_is_equality_checked_but_does_not_improve_baseline_speedup",
                "variant_status": variant.get("status") if variant else None,
                "comparison": variant.get("comparison") if variant else None,
                "metadata": {
                    "layout": row.get("layout"),
                    "gpu_symbols": row.get("gpu_symbols"),
                },
            }
        )
        return report

    handoff = build_runtime_handoff_report(
        matrix,
        hls_summary,
        execute=execute,
        entrypoint=entrypoint,
        src_hybrid_bridge=_artifact_path(row, "src_hybrid_bridge_source", SRC_HYBRID_BRIDGE),
        src_hybrid_out_dir=_artifact_path(row, "src_hybrid_out_dir", SRC_HYBRID_OUT_DIR),
        selected_boundary=boundary,
        metadata_row=row,
    )
    ok_statuses = {
        "runtime_handoff_boundary_measured",
        "src_hybrid_verilator_runtime_handoff_measured",
        "runtime_handoff_artifacts_ready",
    }
    report.update(
        {
            "status": "runtime_dispatch_measured" if handoff.get("status") in ok_statuses else "runtime_dispatch_failed",
            "runtime_boundary_kind": row.get("runtime_boundary_kind"),
            "entrypoint": entrypoint,
            "policy": row.get("policy"),
            "runtime_handoff_status": handoff.get("status"),
            "runtime_handoff": handoff,
            "metadata": {
                "layout": row.get("layout"),
                "gpu_symbols": row.get("gpu_symbols"),
            },
        }
    )
    return report


def dispatch_all_source_variant_runtimes(
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    *,
    shape: str | None = None,
    steps: int | None = None,
    execute: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata_report = _metadata_report(matrix, hls_summary, metadata)
    requested = list(metadata_report.get("requested_source_variants") or DEFAULT_SOURCE_VARIANTS)
    reports = [
        dispatch_source_variant_runtime(
            matrix,
            hls_summary,
            source_variant=str(variant),
            shape=shape,
            steps=steps,
            execute=execute,
            metadata=metadata_report,
        )
        for variant in requested
    ]
    status_counts: dict[str, int] = {}
    for report in reports:
        status = str(report.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1
    measured = [report for report in reports if report.get("status") == "runtime_dispatch_measured"]
    fallbacks = [report for report in reports if report.get("status") == "runtime_dispatch_fallback_baseline"]
    return {
        "schema_version": 1,
        "surface": "scientific_circt_source_variant_runtime_dispatcher_multi",
        "status": "multi_source_variant_dispatch_ready"
        if len(measured) == 3 and len(fallbacks) == 1
        else "multi_source_variant_dispatch_incomplete",
        "execute": execute,
        "source_metadata_surface": metadata_report.get("surface"),
        "source_metadata_status": metadata_report.get("status"),
        "requested_source_variants": requested,
        "status_counts": status_counts,
        "measured_count": len(measured),
        "fallback_count": len(fallbacks),
        "reports": reports,
        "non_claims": [
            "not_full_microgpt_execution",
            "not_training_or_autograd",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
            "not_automatic_hls_rewrite",
            "not_production_runtime_dispatcher",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=Path("reports/scientific_circt_hybrid_dispatch_matrix.json"))
    parser.add_argument(
        "--hls-variant-report",
        type=Path,
        default=Path("reports/scientific_circt_hls_mlp_block_variants.json"),
    )
    parser.add_argument("--source-variant", default=None)
    parser.add_argument("--shape", default=None)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--extra-hls-variant-report", type=Path, action="append", default=[])
    parser.add_argument("--metadata-report", type=Path, default=None)
    parser.add_argument("--all-known-source-variants", action="store_true")
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        summary = combined_hls_summary(load_json(args.hls_variant_report), [load_json(path) for path in args.extra_hls_variant_report])
        matrix = load_json(args.matrix)
        metadata = load_json(args.metadata_report) if args.metadata_report is not None else None
        if args.all_known_source_variants:
            report = dispatch_all_source_variant_runtimes(
                matrix,
                summary,
                shape=args.shape,
                steps=args.steps,
                execute=not args.no_execute,
                metadata=metadata,
            )
            if args.report_out == REPORT:
                args.report_out = MULTI_REPORT
        else:
            report = dispatch_source_variant_runtime(
                matrix,
                summary,
                source_variant=args.source_variant,
                shape=args.shape,
                steps=args.steps,
                execute=not args.no_execute,
                metadata=metadata,
            )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {
        "runtime_dispatch_measured",
        "runtime_dispatch_fallback_baseline",
        "runtime_dispatch_cpu_fallback_unsupported_shape",
        "runtime_dispatch_cpu_fallback_unsupported_steps",
        "multi_source_variant_dispatch_ready",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
