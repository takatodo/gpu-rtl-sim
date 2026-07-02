"""Plan the Vortex mini:hello GPU memory-model ABI from parsed binary inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


INPUT_SUMMARY_REPORT = Path("reports/rtlmeter_vortex_binary_input_summary.json")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _required_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"input summary missing {field}")
    return value


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def build_plan(repo_root: Path, *, input_summary_path: Path | None = None) -> dict[str, Any]:
    report_path = repo_root / (input_summary_path or INPUT_SUMMARY_REPORT)
    summary = _load_json(report_path)
    init = _required_mapping(summary.get("init_memory"), "init_memory")
    post = _required_mapping(summary.get("post_memory"), "post_memory")
    dcrs = _required_mapping(summary.get("dcr_writes"), "dcr_writes")
    files = _required_mapping(summary.get("files"), "files")
    init_payload = int(init.get("total_payload_bytes") or 0)
    post_payload = int(post.get("total_payload_bytes") or 0)
    dcr_count = int(dcrs.get("write_count") or 0)
    init_segment_count = int(init.get("segment_count") or 0)
    post_segment_count = int(post.get("segment_count") or 0)
    block_size = int(_required_mapping(summary.get("gpu_input_model"), "gpu_input_model").get("block_size_bytes") or 64)
    init_block_count = _ceil_div(init_payload, block_size) if block_size else None
    post_block_count = _ceil_div(post_payload, block_size) if block_size else None
    dcr_table_bytes = dcr_count * 8
    segment_record_bytes = 24
    segment_table_bytes = (init_segment_count + post_segment_count) * segment_record_bytes
    payload_bytes = init_payload + post_payload
    minimum_static_bytes = payload_bytes + dcr_table_bytes + segment_table_bytes

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_gpu_memory_model_plan",
        "status": "abi_plan_ready" if summary.get("status") == "parsed" else "blocked_unparsed_inputs",
        "case": summary.get("case", "Vortex:mini:hello"),
        "source_report": _display_path(report_path, repo_root=repo_root),
        "runtime_launchable": False,
        "memory_model_abi": {
            "block_size_bytes": block_size,
            "addressing": "block_addr_times_64_byte_address",
            "write_mask": "uint64_byteen_one_bit_per_byte",
            "read_write_granularity": "64B_block_with_byte_enable_writes",
            "layout": "segmented_sparse_memory_payload_plus_segment_tables",
            "init_segments": init_segment_count,
            "init_payload_bytes": init_payload,
            "init_block_count": init_block_count,
            "post_segments": post_segment_count,
            "post_payload_bytes": post_payload,
            "post_block_count": post_block_count,
            "dcr_write_count": dcr_count,
            "dcr_table_bytes": dcr_table_bytes,
            "segment_record_bytes": segment_record_bytes,
            "segment_table_bytes": segment_table_bytes,
            "minimum_static_input_bytes": minimum_static_bytes,
            "address_min_hex": init.get("address_min_hex"),
            "address_max_exclusive_hex": init.get("address_max_exclusive_hex"),
        },
        "device_buffers": [
            {
                "name": "vortex_init_segment_table",
                "direction": "host_to_device",
                "record_type": "u64_addr_u64_payload_offset_u64_size_bytes",
                "record_count": init_segment_count,
                "bytes": init_segment_count * segment_record_bytes,
                "source": files.get("init", {}).get("path") if isinstance(files.get("init"), dict) else None,
            },
            {
                "name": "vortex_init_payload",
                "direction": "host_to_device",
                "record_type": "u8_payload",
                "bytes": init_payload,
                "source": files.get("init", {}).get("path") if isinstance(files.get("init"), dict) else None,
            },
            {
                "name": "vortex_post_segment_table",
                "direction": "host_to_device",
                "record_type": "u64_addr_u64_payload_offset_u64_size_bytes",
                "record_count": post_segment_count,
                "bytes": post_segment_count * segment_record_bytes,
                "source": files.get("post", {}).get("path") if isinstance(files.get("post"), dict) else None,
            },
            {
                "name": "vortex_post_expected_payload",
                "direction": "host_to_device",
                "record_type": "u8_payload",
                "bytes": post_payload,
                "source": files.get("post", {}).get("path") if isinstance(files.get("post"), dict) else None,
            },
            {
                "name": "vortex_dcr_write_table",
                "direction": "host_to_device",
                "record_type": "u32_addr_u32_value",
                "record_count": dcr_count,
                "bytes": dcr_table_bytes,
                "source": files.get("dcrs", {}).get("path") if isinstance(files.get("dcrs"), dict) else None,
            },
            {
                "name": "vortex_stdout_ring",
                "direction": "device_to_host",
                "record_type": "u8_chars",
                "bytes": 64,
                "source": "IO_COUT_ADDR_0x40",
            },
            {
                "name": "vortex_post_compare_result",
                "direction": "device_to_host",
                "record_type": "u32_mismatch_count",
                "bytes": 4,
                "source": "post_bin_compare",
            },
        ],
        "kernel_entrypoints": [
            {
                "name": "vortex_mem_model_init_gpu",
                "role": "initialize_sparse_or_segmented_device_memory_from_init_segments",
            },
            {
                "name": "vortex_apply_dcr_writes_gpu_or_host_phase",
                "role": "preserve_tb_ordered_DCR_writes_before_deassert_reset",
            },
            {
                "name": "vortex_mem_access_device_helper",
                "role": "service_64B_reads_writes_and_IO_COUT_writes_from_lowered_tb",
            },
            {
                "name": "vortex_post_compare_gpu",
                "role": "compare_post_expected_segments_or_export_actual_bytes",
            },
        ],
        "implementation_blockers": [
            "lowered_tb_mem_access_must_call_device_helper_not_host_DPI",
            "DCR_writes_must_be_replayed_in_original_tb_order",
            "IO_COUT_stdout_capture_must_feed_TEST_PASSED_observable_or_post_compare_must_replace_stdout_authority",
            "post_compare_result_must_be_reported_before_timing_or_speedup_claim",
        ],
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "abi_plan_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--input-summary", default=INPUT_SUMMARY_REPORT.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_plan(Path(args.repo_root), input_summary_path=Path(args.input_summary))
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
