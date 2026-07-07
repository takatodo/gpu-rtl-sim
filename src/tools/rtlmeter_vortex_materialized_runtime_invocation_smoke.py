#!/usr/bin/env python3
"""Validate Vortex materialized runtime inputs before generated lowered-TB integration."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DEFAULT_MATERIALIZATION_REPORT = Path("reports/rtlmeter_vortex_device_buffer_materialize.json")
DEFAULT_DCR_SCHEDULE_REPORT = Path("reports/rtlmeter_vortex_dcr_schedule.json")
DEFAULT_LOWERED_TB_HEADER = Path("src/hybrid/vortex_lowered_tb_runtime_sequence.h")
REQUIRED_BUFFER_NAMES = [
    "vortex_init_segment_table",
    "vortex_init_payload",
    "vortex_post_segment_table",
    "vortex_post_expected_payload",
    "vortex_dcr_write_table",
    "vortex_stdout_ring_initial",
    "vortex_post_compare_result_initial",
]


def _load_json(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, Mapping) else None


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_report_path(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _buffer_rows(materialization: Mapping[str, Any], *, repo_root: Path) -> list[dict[str, Any]]:
    rows = []
    for item in materialization.get("device_buffers", []):
        if not isinstance(item, Mapping):
            continue
        artifact = item.get("artifact")
        artifact_path = repo_root / str(artifact) if isinstance(artifact, str) else None
        artifact_exists = artifact_path.is_file() if artifact_path is not None else False
        artifact_size = artifact_path.stat().st_size if artifact_exists else None
        rows.append(
            {
                "name": item.get("name"),
                "bytes": item.get("bytes"),
                "sha256": item.get("sha256"),
                "artifact": artifact,
                "artifact_exists": artifact_exists,
                "artifact_size": artifact_size,
                "artifact_size_matches": artifact_size == item.get("bytes") if artifact_size is not None else False,
            }
        )
    return rows


def build_smoke(
    repo_root: Path,
    *,
    materialization_report: Path = DEFAULT_MATERIALIZATION_REPORT,
    dcr_schedule_report: Path = DEFAULT_DCR_SCHEDULE_REPORT,
    lowered_tb_header: Path = DEFAULT_LOWERED_TB_HEADER,
) -> dict[str, Any]:
    root = repo_root.resolve()
    materialization_path = _resolve_report_path(materialization_report, repo_root=root)
    dcr_path = _resolve_report_path(dcr_schedule_report, repo_root=root)
    header_path = _resolve_report_path(lowered_tb_header, repo_root=root)
    materialization = _load_json(materialization_path)
    dcr = _load_json(dcr_path)
    header_text = header_path.read_text(encoding="utf-8") if header_path.is_file() else ""

    missing: list[str] = []
    if materialization is None:
        missing.append("device_buffer_materialization_report")
        materialization = {}
    if dcr is None:
        missing.append("dcr_schedule_report")
        dcr = {}
    if not header_path.is_file():
        missing.append("lowered_tb_runtime_sequence_header")

    buffer_rows = _buffer_rows(materialization, repo_root=root)
    buffers_by_name = {str(row.get("name")): row for row in buffer_rows}
    for name in REQUIRED_BUFFER_NAMES:
        row = buffers_by_name.get(name)
        if row is None:
            missing.append(f"buffer.{name}")
        elif row.get("artifact_exists") is not True or row.get("artifact_size_matches") is not True:
            missing.append(f"buffer_artifact.{name}")

    totals = _mapping(materialization.get("totals"))
    dcr_device = _mapping(dcr.get("device_schedule"))
    dcr_buffer = buffers_by_name.get("vortex_dcr_write_table")
    if dcr_buffer is not None and dcr_device:
        if dcr_buffer.get("bytes") != dcr_device.get("bytes"):
            missing.append("dcr_buffer_bytes_match_schedule")
        if dcr_buffer.get("sha256") != dcr_device.get("sha256"):
            missing.append("dcr_buffer_sha256_match_schedule")

    header_features = {
        "vortex_lowered_tb_invoke_runtime_sequence": "vortex_lowered_tb_invoke_runtime_sequence" in header_text,
        "vortex_run_runtime_sequence": "vortex_run_runtime_sequence" in header_text,
        "authority_report_ready": "authority_report_ready" in header_text,
        "authority_passed": "authority_passed" in header_text,
    }
    if not all(header_features.values()):
        missing.append("lowered_tb_runtime_sequence_header_features")

    ready = not missing
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_materialized_runtime_invocation_smoke",
        "status": "materialized_runtime_invocation_smoke_ready_not_integrated" if ready else "blocked_materialized_runtime_invocation_smoke",
        "case": "Vortex:mini:hello",
        "materialization_report": _display_path(materialization_path, repo_root=root),
        "dcr_schedule_report": _display_path(dcr_path, repo_root=root),
        "lowered_tb_header": _display_path(header_path, repo_root=root),
        "runtime_launchable": False,
        "smoke_ready": ready,
        "buffer_count": len(buffer_rows),
        "required_buffer_count": len(REQUIRED_BUFFER_NAMES),
        "host_to_device_bytes": totals.get("host_to_device_bytes"),
        "device_to_host_initial_bytes": totals.get("device_to_host_initial_bytes"),
        "dcr_write_count": dcr.get("write_count"),
        "dcr_schedule_bytes": dcr_device.get("bytes"),
        "buffers": buffer_rows,
        "header_features": header_features,
        "missing_prerequisites": missing,
        "still_missing_for_execution": [
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "real_cuda_kernel_launch_callback_from_lowered_tb",
            "runtime_sequence_reports_memory_post_or_stdout_TEST_PASSED_authority",
            "cpu_vs_hybrid_timing_report.vortex",
        ],
        "readiness_delta": {
            "materialized_runtime_args_ready": ready,
            "device_buffer_artifacts_present": ready,
            "dcr_table_matches_materialized_schedule": ready,
            "lowered_tb_sequence_call_boundary_present": ready,
        },
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_generated_lowered_tb_integration",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "materialized_runtime_invocation_smoke_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--materialization-report", default=DEFAULT_MATERIALIZATION_REPORT.as_posix())
    parser.add_argument("--dcr-schedule-report", default=DEFAULT_DCR_SCHEDULE_REPORT.as_posix())
    parser.add_argument("--lowered-tb-header", default=DEFAULT_LOWERED_TB_HEADER.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json")
    args = parser.parse_args(argv)

    report = build_smoke(
        Path(args.repo_root),
        materialization_report=Path(args.materialization_report),
        dcr_schedule_report=Path(args.dcr_schedule_report),
        lowered_tb_header=Path(args.lowered_tb_header),
    )
    if args.write_report:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
