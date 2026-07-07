"""Validate the Vortex mini:hello DPI memory-model semantics in Python."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys
from typing import Any


DEFAULT_TEST_DIR = Path("third_party/rtlmeter/designs/Vortex/tests/hello")
MEM_BLOCK_SIZE = 64
IO_COUT_ADDR = 0x40
IO_COUT_SIZE = 64
PAGE_BITS = 12
PAGE_SIZE = 1 << PAGE_BITS
PAGE_MASK = PAGE_SIZE - 1


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _default_byte(offset: int) -> int:
    return (0xBAADF00D >> ((offset & 0x3) * 8)) & 0xFF


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


class VortexMemoryReference:
    def __init__(self) -> None:
        self.pages: dict[int, bytearray] = {}
        self.stdout_buffers: list[bytearray] = [bytearray() for _ in range(IO_COUT_SIZE)]
        self.stdout_lines: list[str] = []

    def clear(self) -> None:
        self.pages.clear()
        self.stdout_buffers = [bytearray() for _ in range(IO_COUT_SIZE)]
        self.stdout_lines = []

    def _page(self, address: int) -> bytearray:
        page_index = address >> PAGE_BITS
        page = self.pages.get(page_index)
        if page is None:
            base_addr = page_index << PAGE_BITS
            page = bytearray(_default_byte(base_addr + i) for i in range(PAGE_SIZE))
            self.pages[page_index] = page
        return page

    def read(self, address: int, size: int) -> bytes:
        out = bytearray()
        for offset in range(size):
            addr = address + offset
            out.append(self._page(addr)[addr & PAGE_MASK])
        return bytes(out)

    def write(self, address: int, payload: bytes) -> None:
        for offset, value in enumerate(payload):
            addr = address + offset
            self._page(addr)[addr & PAGE_MASK] = value

    def load_segments(self, segments: list[dict[str, Any]]) -> None:
        self.clear()
        for segment in segments:
            self.write(int(segment["addr"]), bytes(segment["payload"]))

    def compare_segments(self, segments: list[dict[str, Any]]) -> dict[str, Any]:
        mismatches = []
        compared_bytes = 0
        for segment in segments:
            addr = int(segment["addr"])
            expected = bytes(segment["payload"])
            actual = self.read(addr, len(expected))
            compared_bytes += len(expected)
            for offset, (expected_byte, actual_byte) in enumerate(zip(expected, actual, strict=True)):
                if expected_byte != actual_byte:
                    mismatches.append(
                        {
                            "addr": addr + offset,
                            "addr_hex": f"0x{addr + offset:x}",
                            "expected": expected_byte,
                            "actual": actual_byte,
                        }
                    )
        return {
            "match": not mismatches,
            "compared_bytes": compared_bytes,
            "mismatch_count": len(mismatches),
            "first_mismatches": mismatches[:8],
        }

    def mem_access(self, *, req_rw: bool, byteen: int, block_addr: int, wdata: bytes | None = None) -> bytes:
        addr = block_addr * MEM_BLOCK_SIZE
        if not req_rw:
            return self.read(addr, MEM_BLOCK_SIZE)
        if wdata is None:
            raise ValueError("write access requires wdata")
        if len(wdata) < MEM_BLOCK_SIZE:
            raise ValueError("wdata must contain at least one 64B block")
        if IO_COUT_ADDR <= addr < IO_COUT_ADDR + IO_COUT_SIZE:
            for lane in range(IO_COUT_SIZE):
                if (byteen >> lane) & 1:
                    char = wdata[lane]
                    buffer = self.stdout_buffers[lane]
                    buffer.append(char)
                    if char == 0x0A:
                        self.stdout_lines.append(f"#{lane:02d}: {buffer.decode(errors='replace')}")
                        buffer.clear()
        else:
            for lane in range(MEM_BLOCK_SIZE):
                if (byteen >> lane) & 1:
                    self.write(addr + lane, bytes([wdata[lane]]))
        return bytes(MEM_BLOCK_SIZE)


def _post_replay_self_check(post_segments: list[dict[str, Any]]) -> dict[str, Any]:
    ram = VortexMemoryReference()
    for segment in post_segments:
        addr = int(segment["addr"])
        payload = bytes(segment["payload"])
        offset = 0
        while offset < len(payload):
            absolute = addr + offset
            block_base = (absolute // MEM_BLOCK_SIZE) * MEM_BLOCK_SIZE
            block_offset = absolute - block_base
            take = min(len(payload) - offset, MEM_BLOCK_SIZE - block_offset)
            wdata = bytearray(MEM_BLOCK_SIZE)
            byteen = 0
            for lane in range(take):
                wdata[block_offset + lane] = payload[offset + lane]
                byteen |= 1 << (block_offset + lane)
            ram.mem_access(req_rw=True, byteen=byteen, block_addr=block_base // MEM_BLOCK_SIZE, wdata=bytes(wdata))
            offset += take
    compare = ram.compare_segments(post_segments)
    return {
        "status": "passed" if compare["match"] else "failed",
        "match": compare["match"],
        "compared_bytes": compare["compared_bytes"],
        "mismatch_count": compare["mismatch_count"],
    }


def _io_cout_self_check() -> dict[str, Any]:
    ram = VortexMemoryReference()
    first = bytearray(MEM_BLOCK_SIZE)
    second = bytearray(MEM_BLOCK_SIZE)
    first[0] = ord("O")
    second[0] = 0x0A
    ram.mem_access(req_rw=True, byteen=1, block_addr=IO_COUT_ADDR // MEM_BLOCK_SIZE, wdata=bytes(first))
    before = ram.read(IO_COUT_ADDR, 1)
    ram.mem_access(req_rw=True, byteen=1, block_addr=IO_COUT_ADDR // MEM_BLOCK_SIZE, wdata=bytes(second))
    after = ram.read(IO_COUT_ADDR, 1)
    return {
        "status": "passed" if before == after and ram.stdout_lines == ["#00: O\n"] else "failed",
        "ram_unchanged": before == after,
        "stdout_lines": ram.stdout_lines,
    }


def build_reference(repo_root: Path, *, test_dir: Path = DEFAULT_TEST_DIR) -> dict[str, Any]:
    test_root = test_dir if test_dir.is_absolute() else repo_root / test_dir
    init_path = test_root / "init.bin"
    post_path = test_root / "post.bin"
    dcrs_path = test_root / "dcrs.bin"
    init_segments = _parse_memory_file(init_path)
    post_segments = _parse_memory_file(post_path)
    dcr_writes = _parse_dcr_file(dcrs_path)

    ram = VortexMemoryReference()
    ram.load_segments(init_segments)
    initial_compare = ram.compare_segments(post_segments)
    first_init_block = None
    if init_segments:
        first_addr = int(init_segments[0]["addr"])
        first_init_block = {
            "addr": first_addr,
            "addr_hex": f"0x{first_addr:x}",
            "block_addr": first_addr // MEM_BLOCK_SIZE,
            "first_16_bytes_hex": ram.mem_access(req_rw=False, byteen=0, block_addr=first_addr // MEM_BLOCK_SIZE)[:16].hex(),
        }
    post_replay = _post_replay_self_check(post_segments)
    io_cout = _io_cout_self_check()
    status = "reference_validated" if not initial_compare["match"] and post_replay["match"] and io_cout["status"] == "passed" else "reference_failed"

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_memory_model_reference",
        "status": status,
        "case": "Vortex:mini:hello",
        "test_dir": _display_path(test_root, repo_root=repo_root),
        "memory_model": {
            "block_size_bytes": MEM_BLOCK_SIZE,
            "page_size_bytes": PAGE_SIZE,
            "uninitialized_pattern": "0d f0 ad ba repeating",
            "io_cout_addr": IO_COUT_ADDR,
            "io_cout_size": IO_COUT_SIZE,
            "byte_enable_write_granularity": "byte",
        },
        "inputs": {
            "init_segments": len(init_segments),
            "post_segments": len(post_segments),
            "dcr_writes": len(dcr_writes),
            "init_payload_bytes": sum(len(segment["payload"]) for segment in init_segments),
            "post_payload_bytes": sum(len(segment["payload"]) for segment in post_segments),
        },
        "initial_post_compare": initial_compare,
        "post_replay_self_check": post_replay,
        "io_cout_self_check": io_cout,
        "first_init_block_read": first_init_block,
        "dcr_schedule": {
            "encoding": "big_endian_32bit_addr_value_pairs_for_sv_fread",
            "write_count": len(dcr_writes),
            "first_writes": [
                {
                    "index": item["index"],
                    "addr": item["addr"],
                    "addr_hex": f"0x{item['addr']:x}",
                    "value": item["value"],
                    "value_hex": f"0x{item['value']:x}",
                }
                for item in dcr_writes[:8]
            ],
        },
        "gpu_bridge_implication": {
            "reference_semantics_ready": status == "reference_validated",
            "still_missing_for_gpu_launch": [
                "lowered_tb_mem_access_device_helper",
                "device_resident_sparse_or_segment_memory",
                "device_or_host_DCR_replay_in_tb_order",
                "post_compare_result_export",
            ],
        },
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "python_reference_semantics_only",
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
        summary = build_reference(Path(args.repo_root), test_dir=Path(args.test_dir))
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
