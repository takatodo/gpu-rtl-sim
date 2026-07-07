#!/usr/bin/env python3
"""Audit scientific CIRCT candidate evidence from config and generated reports."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPORT = Path("reports/scientific_circt_evidence_audit.json")
DISPATCH_MATRIX = Path("reports/scientific_circt_hybrid_dispatch_matrix.json")
REQUIRED_MEDIAN_KEYS = (
    "cpu_ms",
    "gpu_end_to_end_ms",
    "gpu_kernel_ms",
    "cpu_to_gpu_end_to_end_speedup",
    "cpu_to_gpu_kernel_speedup",
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path) -> str:
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", path.as_posix())


def _candidate_entries(selection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    root = selection.get("scientific_circt_gpu_candidate_search")
    if not isinstance(root, dict):
        raise ValueError("selection missing scientific_circt_gpu_candidate_search")
    entries = {}
    for name, value in root.items():
        if isinstance(value, dict) and isinstance(value.get("timing_reports"), dict):
            entries[name] = value
    return entries


def _audit_timing_report(candidate: str, shape: str, path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"shape": shape, "report": _display_path(path), "present": path.exists()}
    if not path.exists():
        record["status"] = "missing"
        return record
    payload = _load(path)
    median = payload.get("median")
    commands = payload.get("commands")
    command_stages = [cmd.get("stage") for cmd in commands if isinstance(cmd, dict)] if isinstance(commands, list) else []
    missing_median = [key for key in REQUIRED_MEDIAN_KEYS if not isinstance(median, dict) or key not in median]
    record.update(
        {
            "status": payload.get("status"),
            "candidate_matches": payload.get("candidate") == candidate,
            "shape_matches": payload.get("shape") == shape,
            "median_complete": not missing_median,
            "missing_median_keys": missing_median,
            "has_cpu_gpu_timing_run": "cpu_gpu_timing_run" in command_stages,
            "has_cpu_reference_run": "cpu_reference_run" in command_stages,
            "end_to_end_speedup": median.get("cpu_to_gpu_end_to_end_speedup") if isinstance(median, dict) else None,
            "kernel_speedup": median.get("cpu_to_gpu_kernel_speedup") if isinstance(median, dict) else None,
        }
    )
    record["ready"] = (
        record["status"] == "measured"
        and record["candidate_matches"]
        and record["shape_matches"]
        and record["median_complete"]
        and record["has_cpu_gpu_timing_run"]
    )
    return record


def _matrix_records(dispatch_matrix: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    records = dispatch_matrix.get("records")
    if not isinstance(records, list):
        raise ValueError("dispatch matrix missing records array")
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        candidate = record.get("candidate")
        shape = record.get("shape")
        if isinstance(candidate, str) and isinstance(shape, str):
            indexed[(candidate, shape)] = record
    return indexed


def _audit_matrix_rows(
    candidate: str,
    timing_reports: dict[str, Any],
    matrix_index: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for shape in sorted(timing_reports):
        matrix_row = matrix_index.get((candidate, shape))
        timing = matrix_row.get("timing_evidence") if isinstance(matrix_row, dict) else None
        timing_measured = isinstance(timing, dict) and timing.get("status") == "measured"
        rows.append(
            {
                "shape": shape,
                "present": isinstance(matrix_row, dict),
                "decision": matrix_row.get("decision") if isinstance(matrix_row, dict) else None,
                "reason": matrix_row.get("reason") if isinstance(matrix_row, dict) else None,
                "timing_evidence_measured": timing_measured,
                "end_to_end_speedup": (
                    timing.get("cpu_to_gpu_end_to_end_speedup") if isinstance(timing, dict) else None
                ),
                "kernel_speedup": timing.get("cpu_to_gpu_kernel_speedup") if isinstance(timing, dict) else None,
                "ready": isinstance(matrix_row, dict) and timing_measured,
            }
        )
    return rows


def audit(
    selection: dict[str, Any],
    summary: dict[str, Any],
    policy: dict[str, Any],
    dispatch_matrix: dict[str, Any],
) -> dict[str, Any]:
    entries = _candidate_entries(selection)
    matrix_index = _matrix_records(dispatch_matrix)
    candidates: dict[str, Any] = {}
    for candidate, cfg in sorted(entries.items()):
        timing_reports = cfg.get("timing_reports")
        reports = [
            _audit_timing_report(candidate, shape, Path(path))
            for shape, path in sorted(timing_reports.items())
        ] if isinstance(timing_reports, dict) else []
        policy_entry = policy.get("candidates", {}).get(candidate) if isinstance(policy.get("candidates"), dict) else None
        summary_entry = summary.get("by_candidate", {}).get(candidate) if isinstance(summary.get("by_candidate"), dict) else None
        matrix_rows = _audit_matrix_rows(
            candidate,
            timing_reports if isinstance(timing_reports, dict) else {},
            matrix_index,
        )
        systemverilog = Path(str(cfg.get("systemverilog"))) if cfg.get("systemverilog") else None
        candidates[candidate] = {
            "systemverilog": _display_path(systemverilog) if systemverilog else None,
            "systemverilog_present": systemverilog.exists() if systemverilog else False,
            "verilator_cpu_reference": cfg.get("verilator_cpu_reference"),
            "verilator_cpu_reference_pass": cfg.get("verilator_cpu_reference") == "cpu_reference_pass",
            "timing_report_count": len(reports),
            "timing_reports_ready": all(report.get("ready") for report in reports),
            "timing_reports": reports,
            "summary_present": isinstance(summary_entry, dict),
            "policy_present": isinstance(policy_entry, dict),
            "policy_action": policy_entry.get("recommended_action") if isinstance(policy_entry, dict) else None,
            "min_gpu_nstates": policy_entry.get("min_gpu_nstates") if isinstance(policy_entry, dict) else None,
            "first_gpu_end_to_end_favorable_shape": (
                summary_entry.get("first_gpu_end_to_end_favorable_shape") if isinstance(summary_entry, dict) else None
            ),
            "dispatch_matrix_row_count": len(matrix_rows),
            "dispatch_matrix_rows_ready": all(row["ready"] for row in matrix_rows),
            "dispatch_matrix_rows": matrix_rows,
        }
        candidates[candidate]["ready"] = (
            candidates[candidate]["systemverilog_present"]
            and candidates[candidate]["verilator_cpu_reference_pass"]
            and candidates[candidate]["timing_report_count"] >= 3
            and candidates[candidate]["timing_reports_ready"]
            and candidates[candidate]["summary_present"]
            and candidates[candidate]["policy_present"]
            and candidates[candidate]["dispatch_matrix_row_count"] >= candidates[candidate]["timing_report_count"]
            and candidates[candidate]["dispatch_matrix_rows_ready"]
        )
    ready_count = sum(1 for payload in candidates.values() if payload["ready"])
    return {
        "schema_version": 1,
        "surface": "scientific_circt_evidence_audit",
        "status": "evidence_ready" if ready_count == len(candidates) and candidates else "evidence_incomplete",
        "candidate_count": len(candidates),
        "ready_candidate_count": ready_count,
        "summary_counts": summary.get("counts"),
        "policy_status": policy.get("status"),
        "gpu_ready_candidate_count": policy.get("gpu_ready_candidate_count"),
        "dispatch_matrix_status": dispatch_matrix.get("status"),
        "dispatch_matrix_record_count": dispatch_matrix.get("record_count"),
        "dispatch_matrix_measured_speedup_records_attached": dispatch_matrix.get("measured_speedup_records_attached"),
        "candidates": candidates,
        "non_claims": [
            "not_a_general_rtl_speedup_claim",
            "not_microgpt_execution",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=Path("config/selection.json"))
    parser.add_argument("--summary", type=Path, default=Path("reports/scientific_circt_testbench_hybrid_advantage.json"))
    parser.add_argument("--policy", type=Path, default=Path("reports/scientific_circt_gpu_selection_policy.json"))
    parser.add_argument("--dispatch-matrix", type=Path, default=DISPATCH_MATRIX)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = audit(_load(args.selection), _load(args.summary), _load(args.policy), _load(args.dispatch_matrix))
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "evidence_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
