"""Materialize the Vortex mini:hello DCR write schedule semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any


DEFAULT_TEST_DIR = Path("third_party/rtlmeter/designs/Vortex/tests/hello")
DEFAULT_ARTIFACT_NAME = "vortex_dcr_schedule.bin"


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_dcr_file(path: Path) -> list[dict[str, int]]:
    data = path.read_bytes()
    if len(data) % 8 != 0:
        raise ValueError(f"{path}: DCR file size must be a multiple of 8 bytes")
    writes = []
    for index, offset in enumerate(range(0, len(data), 8)):
        addr, value = struct.unpack_from(">II", data, offset)
        writes.append({"index": index, "addr": addr, "value": value})
    return writes


def _device_schedule_blob(writes: list[dict[str, int]]) -> bytes:
    out = bytearray()
    for write in writes:
        out.extend(struct.pack("<II", int(write["addr"]), int(write["value"])))
    return bytes(out)


def _write_preview(writes: list[dict[str, int]], *, limit: int = 8) -> list[dict[str, Any]]:
    preview = []
    for write in writes[:limit]:
        preview.append(
            {
                "index": int(write["index"]),
                "addr": int(write["addr"]),
                "addr_hex": f"0x{int(write['addr']):08x}",
                "value": int(write["value"]),
                "value_hex": f"0x{int(write['value']):08x}",
                "reset_asserted": True,
                "dcr_wr_valid_high_time_units": 10,
            }
        )
    return preview


def build_schedule(
    repo_root: Path,
    *,
    test_dir: Path = DEFAULT_TEST_DIR,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    test_root = test_dir if test_dir.is_absolute() else repo_root / test_dir
    dcr_path = test_root / "dcrs.bin"
    writes = _parse_dcr_file(dcr_path)
    blob = _device_schedule_blob(writes)
    artifact_path = None
    if artifact_dir is not None:
        out_dir = artifact_dir if artifact_dir.is_absolute() else repo_root / artifact_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = out_dir / DEFAULT_ARTIFACT_NAME
        artifact_path.write_bytes(blob)

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_dcr_schedule",
        "status": "dcr_schedule_materialized",
        "case": "Vortex:mini:hello",
        "test_dir": _display_path(test_root, repo_root=repo_root),
        "input": {
            "path": _display_path(dcr_path, repo_root=repo_root),
            "encoding": "big_endian_u32_addr_u32_value_pairs_for_sv_fread",
            "size_bytes": dcr_path.stat().st_size,
            "sha256": _sha256_bytes(dcr_path.read_bytes()),
        },
        "write_count": len(writes),
        "schedule_semantics": {
            "source": "third_party/rtlmeter/designs/Vortex/src/tb.sv",
            "reset_asserted_before_dcr_writes_time_units": 100,
            "reset_asserted_during_all_dcr_writes": True,
            "per_write": {
                "dcr_wr_valid_high_time_units": 10,
                "dcr_wr_valid_low_between_writes": "delta_cycle_only",
                "addr_and_data_cast_to": ["VX_DCR_ADDR_WIDTH", "VX_DCR_DATA_WIDTH"],
                "file_order_preserved": True,
            },
            "after_final_write": {
                "dcr_wr_valid_low_time_units_before_reset_deassert": 10,
                "reset_deasserts_after_schedule": True,
            },
        },
        "device_schedule": {
            "record_type": "little_endian_u32_addr_u32_value",
            "record_bytes": 8,
            "bytes": len(blob),
            "sha256": _sha256_bytes(blob),
            "artifact": _display_path(artifact_path, repo_root=repo_root) if artifact_path is not None else None,
        },
        "first_writes": _write_preview(writes),
        "readiness_delta": {
            "dcr_schedule_materialized": True,
            "still_missing_for_runtime": [
                "runtime_execution_applies_vortex_dcr_schedule_while_reset_asserted",
                "lowered_tb_dcr_schedule_integration",
                "cpu_vs_hybrid_timing_report.vortex",
            ],
        },
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_runtime_dcr_application",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "schedule_materialization_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--test-dir", default=DEFAULT_TEST_DIR.as_posix())
    parser.add_argument("--artifact-dir", help="Optional generated artifact directory for the DCR schedule blob")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_schedule(
            Path(args.repo_root),
            test_dir=Path(args.test_dir),
            artifact_dir=Path(args.artifact_dir) if args.artifact_dir else None,
        )
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
