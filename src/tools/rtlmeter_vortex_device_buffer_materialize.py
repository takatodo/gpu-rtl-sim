"""Materialize Vortex mini:hello device-buffer payloads from binary inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any


DEFAULT_TEST_DIR = Path("third_party/rtlmeter/designs/Vortex/tests/hello")
VORTEX_POST_COMPARE_RESULT_ABI_BYTES = 24


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_memory_file(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    offset = 0
    segments = []
    while offset < len(data):
        if len(data) - offset < 16:
            raise ValueError(f"{path}: truncated segment header at byte {offset}")
        addr, size = struct.unpack_from("<QQ", data, offset)
        offset += 16
        end = offset + size
        if end > len(data):
            raise ValueError(f"{path}: segment at 0x{addr:x} exceeds file size")
        payload = data[offset:end]
        segments.append({"addr": addr, "size": size, "payload": payload})
        offset = end
    return segments


def _parse_dcr_file(path: Path) -> list[dict[str, int]]:
    data = path.read_bytes()
    if len(data) % 8 != 0:
        raise ValueError(f"{path}: DCR file size must be a multiple of 8 bytes")
    writes = []
    for index, offset in enumerate(range(0, len(data), 8)):
        addr, value = struct.unpack_from(">II", data, offset)
        writes.append({"index": index, "addr": addr, "value": value})
    return writes


def _segment_table_and_payload(segments: list[dict[str, Any]]) -> tuple[bytes, bytes, list[dict[str, Any]]]:
    table = bytearray()
    payload = bytearray()
    records = []
    for index, segment in enumerate(segments):
        payload_offset = len(payload)
        segment_payload = bytes(segment["payload"])
        table.extend(struct.pack("<QQQ", int(segment["addr"]), payload_offset, int(segment["size"])))
        payload.extend(segment_payload)
        records.append(
            {
                "index": index,
                "addr": int(segment["addr"]),
                "addr_hex": f"0x{int(segment['addr']):x}",
                "payload_offset": payload_offset,
                "size_bytes": int(segment["size"]),
            }
        )
    return bytes(table), bytes(payload), records


def _dcr_table(writes: list[dict[str, int]]) -> bytes:
    out = bytearray()
    for write in writes:
        out.extend(struct.pack("<II", int(write["addr"]), int(write["value"])))
    return bytes(out)


def _buffer_summary(name: str, data: bytes, *, artifact_path: Path | None, repo_root: Path) -> dict[str, Any]:
    return {
        "name": name,
        "bytes": len(data),
        "sha256": _sha256_bytes(data),
        "artifact": _display_path(artifact_path, repo_root=repo_root) if artifact_path is not None else None,
    }


def build_materialization(
    repo_root: Path,
    *,
    test_dir: Path = DEFAULT_TEST_DIR,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    test_root = test_dir if test_dir.is_absolute() else repo_root / test_dir
    init_segments = _parse_memory_file(test_root / "init.bin")
    post_segments = _parse_memory_file(test_root / "post.bin")
    dcr_writes = _parse_dcr_file(test_root / "dcrs.bin")

    init_table, init_payload, init_records = _segment_table_and_payload(init_segments)
    post_table, post_payload, post_records = _segment_table_and_payload(post_segments)
    dcr_table = _dcr_table(dcr_writes)
    stdout_ring = bytes(64)
    post_compare_result = bytes(VORTEX_POST_COMPARE_RESULT_ABI_BYTES)
    buffers = {
        "vortex_init_segment_table": init_table,
        "vortex_init_payload": init_payload,
        "vortex_post_segment_table": post_table,
        "vortex_post_expected_payload": post_payload,
        "vortex_dcr_write_table": dcr_table,
        "vortex_stdout_ring_initial": stdout_ring,
        "vortex_post_compare_result_initial": post_compare_result,
    }

    artifact_paths: dict[str, Path | None] = {name: None for name in buffers}
    if artifact_dir is not None:
        out_dir = artifact_dir if artifact_dir.is_absolute() else repo_root / artifact_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, data in buffers.items():
            path = out_dir / f"{name}.bin"
            path.write_bytes(data)
            artifact_paths[name] = path

    summaries = [
        _buffer_summary(name, data, artifact_path=artifact_paths[name], repo_root=repo_root)
        for name, data in buffers.items()
    ]
    total_h2d = len(init_table) + len(init_payload) + len(post_table) + len(post_payload) + len(dcr_table)
    total_d2h_initial = len(stdout_ring) + len(post_compare_result)

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_device_buffer_materialize",
        "status": "device_buffers_materialized",
        "case": "Vortex:mini:hello",
        "test_dir": _display_path(test_root, repo_root=repo_root),
        "artifact_dir": _display_path((artifact_dir if artifact_dir.is_absolute() else repo_root / artifact_dir), repo_root=repo_root)
        if artifact_dir is not None
        else None,
        "abi": {
            "segment_record_type": "little_endian_u64_addr_u64_payload_offset_u64_size_bytes",
            "segment_record_bytes": 24,
            "dcr_record_type": "little_endian_u32_addr_u32_value_device_table",
            "dcr_record_bytes": 8,
            "stdout_ring_bytes": 64,
            "post_compare_result_bytes": VORTEX_POST_COMPARE_RESULT_ABI_BYTES,
        },
        "inputs": {
            "init_segments": len(init_segments),
            "post_segments": len(post_segments),
            "dcr_writes": len(dcr_writes),
            "init_payload_bytes": len(init_payload),
            "post_payload_bytes": len(post_payload),
        },
        "segment_records": {
            "init": init_records,
            "post": post_records,
        },
        "device_buffers": summaries,
        "totals": {
            "host_to_device_bytes": total_h2d,
            "device_to_host_initial_bytes": total_d2h_initial,
            "all_buffer_bytes": total_h2d + total_d2h_initial,
        },
        "readiness_delta": {
            "device_buffers_materialized": True,
            "still_missing_for_runtime": [
                "device_memory_buffers_uploaded_to_runtime",
                "lowered_tb_mem_access_device_helper_integration",
                "gpu_post_compare_result_export",
                "gpu_stdout_or_post_compare_observable_export",
                "dcrs_bin_gpu_schedule_or_host_phase_bridge",
            ],
        },
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_device_upload",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "host_buffer_materialization_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--test-dir", default=DEFAULT_TEST_DIR.as_posix())
    parser.add_argument("--artifact-dir", help="Optional generated artifact directory for buffer blobs")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_materialization(
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
