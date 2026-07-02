#!/usr/bin/env python3
"""Compile and run a Vortex lowered-TB memory-helper integration smoke."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DEFAULT_MATERIALIZATION_REPORT = Path("reports/rtlmeter_vortex_device_buffer_materialize.json")
DEFAULT_ARTIFACT_DIR = Path("artifacts/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke")
REQUIRED_BUFFER_NAMES = {
    "vortex_init_segment_table",
    "vortex_init_payload",
    "vortex_post_segment_table",
    "vortex_post_expected_payload",
}


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _artifact_literal(path: Path, *, repo_root: Path) -> str:
    return json.dumps(_display_path(path, repo_root=repo_root))


def _collect_required_buffers(materialization: Mapping[str, Any], *, repo_root: Path) -> dict[str, dict[str, Any]]:
    raw_buffers = materialization.get("device_buffers")
    if not isinstance(raw_buffers, list):
        raise ValueError("materialization report missing device_buffers list")
    buffers: dict[str, dict[str, Any]] = {}
    for item in raw_buffers:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        artifact = item.get("artifact")
        if not isinstance(name, str) or not isinstance(artifact, str):
            continue
        if name not in REQUIRED_BUFFER_NAMES:
            continue
        path = _resolve(Path(artifact), repo_root=repo_root)
        bytes_ = int(item.get("bytes"))
        if not path.is_file():
            raise ValueError(f"missing materialized buffer artifact: {_display_path(path, repo_root=repo_root)}")
        actual = path.stat().st_size
        if actual != bytes_:
            raise ValueError(f"buffer artifact size mismatch for {name}: report={bytes_} actual={actual}")
        buffers[name] = {"name": name, "artifact": path, "bytes": bytes_}
    missing = sorted(REQUIRED_BUFFER_NAMES - set(buffers))
    if missing:
        raise ValueError(f"materialization report missing required buffers: {', '.join(missing)}")
    return buffers


def _generated_source(*, repo_root: Path, buffers: Mapping[str, Mapping[str, Any]]) -> str:
    init_table = buffers["vortex_init_segment_table"]
    init_payload = buffers["vortex_init_payload"]
    post_table = buffers["vortex_post_segment_table"]
    post_payload = buffers["vortex_post_expected_payload"]
    return (
        "#include <assert.h>\n"
        "#include <stdint.h>\n"
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "#include <string.h>\n"
        '#include "src/hybrid/vortex_memory_model_device.h"\n\n'
        "static void *load_file(const char *path, size_t expected_bytes) {\n"
        "  FILE *fp = fopen(path, \"rb\");\n"
        "  assert(fp != 0);\n"
        "  unsigned char *data = (unsigned char *)malloc(expected_bytes == 0 ? 1 : expected_bytes);\n"
        "  assert(data != 0);\n"
        "  size_t read_bytes = fread(data, 1, expected_bytes, fp);\n"
        "  assert(read_bytes == expected_bytes);\n"
        "  assert(fgetc(fp) == EOF);\n"
        "  fclose(fp);\n"
        "  return data;\n"
        "}\n\n"
        "static void add_segment_blocks(VortexMemBlock *blocks,\n"
        "                               uint32_t *block_count,\n"
        "                               const VortexMemSegment *segments,\n"
        "                               uint32_t segment_count) {\n"
        "  for (uint32_t i = 0; i < segment_count; ++i) {\n"
        "    const uint64_t begin = segments[i].addr / VORTEX_MEM_BLOCK_SIZE;\n"
        "    const uint64_t end = (segments[i].addr + segments[i].size_bytes + VORTEX_MEM_BLOCK_SIZE - 1u) /\n"
        "                         VORTEX_MEM_BLOCK_SIZE;\n"
        "    for (uint64_t block_addr = begin; block_addr < end; ++block_addr) {\n"
        "      if (vortex_find_block(blocks, *block_count, block_addr) < 0) {\n"
        "        blocks[*block_count].block_addr = block_addr;\n"
        "        memset(blocks[*block_count].data, 0, VORTEX_MEM_BLOCK_SIZE);\n"
        "        ++*block_count;\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "static void replay_post_with_lowered_tb_mem_access(const VortexMemSegment *segments,\n"
        "                                                    uint32_t segment_count,\n"
        "                                                    const uint8_t *payload,\n"
        "                                                    VortexMemBlock *blocks,\n"
        "                                                    uint32_t block_count) {\n"
        "  for (uint32_t i = 0; i < segment_count; ++i) {\n"
        "    uint64_t offset = 0;\n"
        "    while (offset < segments[i].size_bytes) {\n"
        "      const uint64_t absolute = segments[i].addr + offset;\n"
        "      const uint64_t block_addr = absolute / VORTEX_MEM_BLOCK_SIZE;\n"
        "      const uint32_t block_offset = (uint32_t)(absolute % VORTEX_MEM_BLOCK_SIZE);\n"
        "      const uint64_t remaining = segments[i].size_bytes - offset;\n"
        "      const uint32_t take = (uint32_t)(remaining < (VORTEX_MEM_BLOCK_SIZE - block_offset)\n"
        "                                           ? remaining\n"
        "                                           : (VORTEX_MEM_BLOCK_SIZE - block_offset));\n"
        "      uint8_t wdata[VORTEX_MEM_BLOCK_SIZE];\n"
        "      uint8_t rdata[VORTEX_MEM_BLOCK_SIZE];\n"
        "      uint64_t byteen = 0;\n"
        "      memset(wdata, 0, sizeof(wdata));\n"
        "      memset(rdata, 0, sizeof(rdata));\n"
        "      for (uint32_t lane = 0; lane < take; ++lane) {\n"
        "        wdata[block_offset + lane] = payload[segments[i].payload_offset + offset + lane];\n"
        "        byteen |= 1ull << (block_offset + lane);\n"
        "      }\n"
        "      vortex_mem_access_device_helper(1, byteen, block_addr, wdata, rdata, blocks, block_count, 0);\n"
        "      offset += take;\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "static void write_stdout_with_lowered_tb_mem_access(VortexIoCoutCapture *io_cout) {\n"
        "  const char *message = \"TEST PASSED\\n\";\n"
        "  for (uint32_t i = 0; message[i] != 0; ++i) {\n"
        "    uint8_t wdata[VORTEX_MEM_BLOCK_SIZE];\n"
        "    uint8_t rdata[VORTEX_MEM_BLOCK_SIZE];\n"
        "    memset(wdata, 0, sizeof(wdata));\n"
        "    memset(rdata, 0, sizeof(rdata));\n"
        "    wdata[0] = (uint8_t)message[i];\n"
        "    vortex_mem_access_device_helper(1, 1ull, VORTEX_IO_COUT_ADDR / VORTEX_MEM_BLOCK_SIZE,\n"
        "                                    wdata, rdata, 0, 0, io_cout);\n"
        "  }\n"
        "}\n\n"
        "int main(void) {\n"
        f"  VortexMemSegment *init_segments = (VortexMemSegment *)load_file({_artifact_literal(init_table['artifact'], repo_root=repo_root)}, {int(init_table['bytes'])}u);\n"
        f"  uint8_t *init_payload = (uint8_t *)load_file({_artifact_literal(init_payload['artifact'], repo_root=repo_root)}, {int(init_payload['bytes'])}u);\n"
        f"  VortexMemSegment *post_segments = (VortexMemSegment *)load_file({_artifact_literal(post_table['artifact'], repo_root=repo_root)}, {int(post_table['bytes'])}u);\n"
        f"  uint8_t *post_payload = (uint8_t *)load_file({_artifact_literal(post_payload['artifact'], repo_root=repo_root)}, {int(post_payload['bytes'])}u);\n"
        f"  const uint32_t init_segment_count = {int(init_table['bytes']) // 24}u;\n"
        f"  const uint32_t post_segment_count = {int(post_table['bytes']) // 24}u;\n"
        "  VortexMemBlock blocks[640];\n"
        "  uint32_t block_count = 0;\n"
        "  memset(blocks, 0, sizeof(blocks));\n"
        "  add_segment_blocks(blocks, &block_count, init_segments, init_segment_count);\n"
        "  add_segment_blocks(blocks, &block_count, post_segments, post_segment_count);\n"
        "  assert(block_count > 0);\n"
        "  assert(block_count <= 640);\n"
        "  vortex_init_blocks_from_segments(blocks, block_count, init_segments, init_segment_count, init_payload);\n"
        "  VortexPostCompareResult before = vortex_post_compare_device_helper(\n"
        "      blocks, block_count, post_segments, post_segment_count, post_payload);\n"
        "  assert(before.mismatch_count > 0);\n"
        "  replay_post_with_lowered_tb_mem_access(post_segments, post_segment_count, post_payload, blocks, block_count);\n"
        "  VortexPostCompareResult after = vortex_post_compare_device_helper(\n"
        "      blocks, block_count, post_segments, post_segment_count, post_payload);\n"
        "  assert(after.mismatch_count == 0);\n"
        "  VortexIoCoutCapture io_cout;\n"
        "  memset(&io_cout, 0, sizeof(io_cout));\n"
        "  write_stdout_with_lowered_tb_mem_access(&io_cout);\n"
        "  assert(io_cout.count == 12);\n"
        "  assert(memcmp(io_cout.chars, \"TEST PASSED\\n\", 12) == 0);\n"
        "  printf(\"block_count=%u\\n\", block_count);\n"
        "  printf(\"initial_post_mismatches=%u\\n\", before.mismatch_count);\n"
        "  printf(\"post_replay_mismatches=%u\\n\", after.mismatch_count);\n"
        "  printf(\"stdout_chars=%u\\n\", io_cout.count);\n"
        "  return 0;\n"
        "}\n"
    )


def build_and_run_smoke(
    repo_root: Path,
    *,
    materialization_report: Path = DEFAULT_MATERIALIZATION_REPORT,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    cc: str = "cc",
) -> dict[str, Any]:
    root = repo_root.resolve()
    materialization_path = _resolve(materialization_report, repo_root=root)
    materialization = _load_json(materialization_path)
    buffers = _collect_required_buffers(materialization, repo_root=root)

    out_dir = _resolve(artifact_dir, repo_root=root)
    out_dir.mkdir(parents=True, exist_ok=True)
    source_path = out_dir / "vortex_lowered_tb_memory_helper_integration_smoke.c"
    binary_path = out_dir / "vortex_lowered_tb_memory_helper_integration_smoke"
    source_path.write_text(_generated_source(repo_root=root, buffers=buffers), encoding="utf-8")

    compile_cmd = [
        cc,
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I.",
        _display_path(source_path, repo_root=root),
        "-o",
        _display_path(binary_path, repo_root=root),
    ]
    compile_result = subprocess.run(compile_cmd, cwd=root, text=True, capture_output=True, check=False)
    if compile_result.returncode != 0:
        raise RuntimeError(compile_result.stderr or compile_result.stdout)
    run_result = subprocess.run([_display_path(binary_path, repo_root=root)], cwd=root, text=True, capture_output=True, check=False)
    if run_result.returncode != 0:
        raise RuntimeError(run_result.stderr or run_result.stdout)

    totals = materialization.get("totals") if isinstance(materialization.get("totals"), Mapping) else {}
    inputs = materialization.get("inputs") if isinstance(materialization.get("inputs"), Mapping) else {}
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke",
        "status": "lowered_tb_memory_helper_integration_smoke_passed",
        "case": "Vortex:mini:hello",
        "generated_source": _display_path(source_path, repo_root=root),
        "binary": _display_path(binary_path, repo_root=root),
        "materialization_report": _display_path(materialization_path, repo_root=root),
        "lowered_tb_memory_helper_integration_smoke_passed": True,
        "host_to_device_bytes": totals.get("host_to_device_bytes"),
        "device_to_host_initial_bytes": totals.get("device_to_host_initial_bytes"),
        "init_segment_count": inputs.get("init_segments"),
        "post_segment_count": inputs.get("post_segments"),
        "compile_command": compile_cmd,
        "run_stdout": run_result.stdout.splitlines(),
        "runtime_launchable": False,
        "readiness_delta": {
            "generated_c_harness_calls_vortex_mem_access_device_helper": True,
            "real_materialized_vortex_buffers_consumed": True,
            "post_condition_replay_passed_through_device_helper": True,
            "io_cout_stdout_capture_passed_through_device_helper": True,
            "still_missing_for_measurement": [
                "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
                "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
                "runtime_execution_reports_vortex_observable_authority",
                "cpu_vs_hybrid_timing_report",
            ],
        },
        "non_claims": [
            "not_real_verilator_generated_lowered_tb_integration",
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--materialization-report", default=DEFAULT_MATERIALIZATION_REPORT.as_posix())
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR.as_posix())
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_and_run_smoke(
            Path(args.repo_root),
            materialization_report=Path(args.materialization_report),
            artifact_dir=Path(args.artifact_dir),
            cc=args.cc,
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
