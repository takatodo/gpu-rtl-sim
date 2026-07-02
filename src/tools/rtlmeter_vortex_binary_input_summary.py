"""Summarize Vortex RTLMeter binary inputs for the first mini:hello gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any


DEFAULT_TEST_DIR = Path("third_party/rtlmeter/designs/Vortex/tests/hello")


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_memory_segments(path: Path) -> dict[str, Any]:
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
        segments.append(
            {
                "addr": addr,
                "addr_hex": f"0x{addr:x}",
                "size_bytes": size,
                "end_addr_exclusive": addr + size,
                "end_addr_exclusive_hex": f"0x{addr + size:x}",
            }
        )
        offset = end
    total_payload = sum(int(segment["size_bytes"]) for segment in segments)
    min_addr = min((int(segment["addr"]) for segment in segments), default=None)
    max_addr = max((int(segment["end_addr_exclusive"]) for segment in segments), default=None)
    return {
        "segment_count": len(segments),
        "total_payload_bytes": total_payload,
        "address_min": min_addr,
        "address_min_hex": f"0x{min_addr:x}" if min_addr is not None else None,
        "address_max_exclusive": max_addr,
        "address_max_exclusive_hex": f"0x{max_addr:x}" if max_addr is not None else None,
        "segments": segments,
    }


def _parse_dcr_pairs(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) % 8 != 0:
        raise ValueError(f"{path}: DCR file size must be a multiple of 8 bytes")
    writes = []
    for index, offset in enumerate(range(0, len(data), 8)):
        addr, value = struct.unpack_from(">II", data, offset)
        writes.append(
            {
                "index": index,
                "addr": addr,
                "addr_hex": f"0x{addr:x}",
                "value": value,
                "value_hex": f"0x{value:x}",
            }
        )
    return {
        "write_count": len(writes),
        "encoding": "big_endian_32bit_addr_value_pairs_for_sv_fread",
        "writes": writes,
    }


def _file_summary(path: Path, *, repo_root: Path) -> dict[str, Any]:
    return {
        "path": _display_path(path, repo_root=repo_root),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": _sha256(path) if path.is_file() else None,
    }


def build_summary(repo_root: Path, *, test_dir: Path = DEFAULT_TEST_DIR) -> dict[str, Any]:
    test_root = test_dir if test_dir.is_absolute() else repo_root / test_dir
    init_path = test_root / "init.bin"
    post_path = test_root / "post.bin"
    dcrs_path = test_root / "dcrs.bin"
    files = {
        "init": _file_summary(init_path, repo_root=repo_root),
        "post": _file_summary(post_path, repo_root=repo_root),
        "dcrs": _file_summary(dcrs_path, repo_root=repo_root),
    }
    missing = [name for name, item in files.items() if item["exists"] is not True]
    init = _parse_memory_segments(init_path) if init_path.is_file() else None
    post = _parse_memory_segments(post_path) if post_path.is_file() else None
    dcrs = _parse_dcr_pairs(dcrs_path) if dcrs_path.is_file() else None
    gpu_input_model = {
        "memory_segment_format": "little_endian_u64_addr_u64_size_payload",
        "dcr_format": "big_endian_32bit_addr_value_pairs_for_sv_fread",
        "block_size_bytes": 64,
        "required_device_memory_regions": [
            "sparse_or_segmented_RAM_initialized_from_init_bin",
            "post_bin_expected_segments_for_compare",
            "DCR_write_schedule_from_dcrs_bin",
        ],
        "host_phase_still_required": [
            "load_or_upload_init_segments",
            "apply_DCR_writes_in_tb_order",
            "export_or_compare_post_segments",
        ],
    }
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_binary_input_summary",
        "status": "parsed" if not missing else "missing_inputs",
        "case": "Vortex:mini:hello",
        "test_dir": _display_path(test_root, repo_root=repo_root),
        "files": files,
        "init_memory": init,
        "post_memory": post,
        "dcr_writes": dcrs,
        "gpu_input_model": gpu_input_model,
        "missing_prerequisites": missing,
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "input_parsing_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--test-dir", default=DEFAULT_TEST_DIR.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_summary(Path(args.repo_root), test_dir=Path(args.test_dir))
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
