#!/usr/bin/env python3
"""Compile and run a generated-lowered-TB Vortex runtime invocation smoke."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DEFAULT_MATERIALIZATION_REPORT = Path("reports/rtlmeter_vortex_device_buffer_materialize.json")
DEFAULT_DCR_SCHEDULE_REPORT = Path("reports/rtlmeter_vortex_dcr_schedule.json")
DEFAULT_ARTIFACT_DIR = Path("artifacts/rtlmeter_vortex_generated_lowered_tb_invocation_smoke")
REQUIRED_BUFFER_ORDER = [
    "vortex_init_segment_table",
    "vortex_init_payload",
    "vortex_post_segment_table",
    "vortex_post_expected_payload",
    "vortex_dcr_write_table",
    "vortex_stdout_ring_initial",
    "vortex_post_compare_result_initial",
]


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _artifact_literal(path: Path, *, repo_root: Path) -> str:
    return json.dumps(_display_path(path, repo_root=repo_root))


def _collect_buffers(materialization: Mapping[str, Any], *, repo_root: Path) -> list[dict[str, Any]]:
    raw_buffers = materialization.get("device_buffers")
    if not isinstance(raw_buffers, list):
        raise ValueError("materialization report missing device_buffers list")
    by_name = {}
    for item in raw_buffers:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        artifact = item.get("artifact")
        if not isinstance(name, str) or not isinstance(artifact, str):
            continue
        path = _resolve(Path(artifact), repo_root=repo_root)
        by_name[name] = {
            "name": name,
            "bytes": int(item.get("bytes")),
            "artifact": path,
            "direction": "VORTEX_BUFFER_DEVICE_TO_HOST"
            if name in {"vortex_stdout_ring_initial", "vortex_post_compare_result_initial"}
            else "VORTEX_BUFFER_HOST_TO_DEVICE",
        }
    missing = [name for name in REQUIRED_BUFFER_ORDER if name not in by_name]
    if missing:
        raise ValueError(f"materialization report missing required buffers: {', '.join(missing)}")
    rows = [by_name[name] for name in REQUIRED_BUFFER_ORDER]
    for row in rows:
        path = row["artifact"]
        if not path.is_file():
            raise ValueError(f"missing materialized buffer artifact: {_display_path(path, repo_root=repo_root)}")
        size = path.stat().st_size
        if size != row["bytes"]:
            raise ValueError(
                f"buffer artifact size mismatch for {row['name']}: report={row['bytes']} actual={size}"
            )
    return rows


def _generated_source(*, repo_root: Path, buffers: list[dict[str, Any]], dcr_write_count: int) -> str:
    buffer_defs = []
    for index, row in enumerate(buffers):
        buffer_defs.append(
            "  buffers[{index}].name = {name};\n"
            "  buffers[{index}].host_data = {host_data};\n"
            "  buffers[{index}].bytes = {bytes_}u;\n"
            "  buffers[{index}].direction = {direction};\n"
            "  buffers[{index}].initial_value = 0;\n"
            "  buffers[{index}].device_ptr = 0;".format(
                index=index,
                name=json.dumps(row["name"]),
                host_data=(
                    f"load_file({_artifact_literal(row['artifact'], repo_root=repo_root)}, {int(row['bytes'])}u)"
                    if row["direction"] == "VORTEX_BUFFER_HOST_TO_DEVICE"
                    else "0"
                ),
                bytes_=int(row["bytes"]),
                direction=row["direction"],
            )
        )
    return (
        "#include <assert.h>\n"
        "#include <stdint.h>\n"
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "#include <string.h>\n"
        '#include "src/hybrid/vortex_lowered_tb_runtime_sequence.h"\n\n'
        "typedef struct {\n"
        "  unsigned alloc_count;\n"
        "  unsigned h2d_count;\n"
        "  unsigned memset_count;\n"
        "  unsigned free_count;\n"
        "  unsigned dcr_count;\n"
        "  unsigned kernel_count;\n"
        "  unsigned dtoh_count;\n"
        "  VortexCuDeviceptr next_ptr;\n"
        "} FakeRuntime;\n\n"
        "static FakeRuntime g_fake;\n"
        "static VortexPostCompareResult g_post;\n"
        "static unsigned char g_stdout[64];\n\n"
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
        "static VortexCuResult fake_alloc(VortexCuDeviceptr *out, size_t bytes) {\n"
        "  assert(bytes > 0);\n"
        "  *out = g_fake.next_ptr++;\n"
        "  ++g_fake.alloc_count;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult fake_h2d(VortexCuDeviceptr dst, const void *src, size_t bytes) {\n"
        "  assert(dst != 0);\n"
        "  assert(src != 0);\n"
        "  assert(bytes > 0);\n"
        "  ++g_fake.h2d_count;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult fake_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {\n"
        "  assert(dst != 0);\n"
        "  assert(value == 0);\n"
        "  assert(bytes > 0);\n"
        "  ++g_fake.memset_count;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult fake_free(VortexCuDeviceptr ptr) {\n"
        "  assert(ptr != 0);\n"
        "  ++g_fake.free_count;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult fake_dcr(void *user, uint32_t addr, uint32_t value, int reset_asserted) {\n"
        "  (void)user;\n"
        "  (void)addr;\n"
        "  (void)value;\n"
        "  assert(reset_asserted == 1);\n"
        "  ++g_fake.dcr_count;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult fake_kernel(void *user, VortexRuntimeBuffer *buffers, unsigned buffer_count) {\n"
        "  (void)user;\n"
        "  assert(buffer_count == 7);\n"
        "  assert(buffers[0].device_ptr == 1000);\n"
        "  assert(buffers[6].device_ptr == 1006);\n"
        "  ++g_fake.kernel_count;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult fake_dtoh(void *dst, VortexCuDeviceptr src, size_t bytes) {\n"
        "  ++g_fake.dtoh_count;\n"
        "  if (src == 1006) {\n"
        "    assert(bytes == sizeof(VortexPostCompareResult));\n"
        "    memcpy(dst, &g_post, bytes);\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "  }\n"
        "  if (src == 1005) {\n"
        "    assert(bytes == 64);\n"
        "    memcpy(dst, g_stdout, bytes);\n"
        "    return VORTEX_CUDA_SUCCESS;\n"
        "  }\n"
        "  return 99;\n"
        "}\n\n"
        "int main(void) {\n"
        "  memset(&g_fake, 0, sizeof(g_fake));\n"
        "  memset(&g_post, 0, sizeof(g_post));\n"
        "  memset(g_stdout, 0, sizeof(g_stdout));\n"
        "  memcpy(g_stdout, \"TEST PASSED\\n\", 12);\n"
        "  g_fake.next_ptr = 1000;\n"
        "  VortexRuntimeBuffer buffers[7];\n"
        + "\n".join(buffer_defs)
        + "\n"
        f"  VortexDcrWrite *dcr_writes = (VortexDcrWrite *)buffers[4].host_data;\n"
        f"  const unsigned dcr_write_count = {dcr_write_count}u;\n"
        "  VortexCudaUploadDriver upload = {fake_alloc, fake_h2d, fake_memset, fake_free};\n"
        "  VortexObservableExportDriver export_driver = {fake_dtoh};\n"
        "  VortexRuntimeSequenceArgs args = {\n"
        "    &upload, buffers, 7, dcr_writes, dcr_write_count, fake_dcr, 0, fake_kernel, 0, &export_driver\n"
        "  };\n"
        "  VortexRuntimeSequenceSummary sequence_summary;\n"
        "  VortexLoweredTbRuntimeSummary tb_summary;\n"
        "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
        "  assert(result == VORTEX_CUDA_SUCCESS);\n"
        "  assert(tb_summary.runtime_sequence_called == 1);\n"
        "  assert(tb_summary.runtime_sequence_passed == 1);\n"
        "  assert(tb_summary.authority_report_ready == 1);\n"
        "  assert(tb_summary.authority_passed == 1);\n"
        "  assert(strcmp(tb_summary.authority_source, \"memory_post_condition_and_stdout_TEST_PASSED\") == 0);\n"
        "  assert(sequence_summary.dcr_applied_count == dcr_write_count);\n"
        "  assert(sequence_summary.kernel_launch_invoked == 1);\n"
        "  assert(sequence_summary.observable_export_invoked == 1);\n"
        "  assert(sequence_summary.buffers_released == 1);\n"
        "  printf(\"runtime_sequence_called=%d\\n\", tb_summary.runtime_sequence_called);\n"
        "  printf(\"authority_passed=%d\\n\", tb_summary.authority_passed);\n"
        "  printf(\"dcr_applied_count=%u\\n\", sequence_summary.dcr_applied_count);\n"
        "  printf(\"kernel_launch_invoked=%d\\n\", sequence_summary.kernel_launch_invoked);\n"
        "  return 0;\n"
        "}\n"
    )


def build_and_run_smoke(
    repo_root: Path,
    *,
    materialization_report: Path = DEFAULT_MATERIALIZATION_REPORT,
    dcr_schedule_report: Path = DEFAULT_DCR_SCHEDULE_REPORT,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    cc: str = "cc",
) -> dict[str, Any]:
    root = repo_root.resolve()
    materialization_path = _resolve(materialization_report, repo_root=root)
    dcr_path = _resolve(dcr_schedule_report, repo_root=root)
    materialization = _load_json(materialization_path)
    dcr = _load_json(dcr_path)
    buffers = _collect_buffers(materialization, repo_root=root)
    dcr_write_count = int(dcr.get("write_count", 0))
    if dcr_write_count <= 0:
        raise ValueError("DCR schedule report missing positive write_count")
    dcr_schedule = _mapping(dcr.get("device_schedule"))
    dcr_buffer = next(row for row in buffers if row["name"] == "vortex_dcr_write_table")
    if dcr_buffer["bytes"] != dcr_schedule.get("bytes"):
        raise ValueError("materialized DCR table bytes do not match DCR schedule report")

    out_dir = _resolve(artifact_dir, repo_root=root)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / "generated_vortex_lowered_tb_invocation_smoke.c"
    binary = out_dir / "generated_vortex_lowered_tb_invocation_smoke"
    source.write_text(_generated_source(repo_root=root, buffers=buffers, dcr_write_count=dcr_write_count), encoding="utf-8")
    compile_argv = [cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I.", source.as_posix(), "-o", binary.as_posix()]
    compile_run = subprocess.run(compile_argv, cwd=root, text=True, capture_output=True)
    run_argv = [binary.as_posix()]
    run = None
    if compile_run.returncode == 0:
        run = subprocess.run(run_argv, cwd=root, text=True, capture_output=True)
    passed = compile_run.returncode == 0 and run is not None and run.returncode == 0
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_generated_lowered_tb_invocation_smoke",
        "status": "generated_lowered_tb_invocation_smoke_passed" if passed else "blocked_generated_lowered_tb_invocation_smoke",
        "case": "Vortex:mini:hello",
        "runtime_launchable": False,
        "generated_lowered_tb_invocation_smoke_passed": passed,
        "materialization_report": _display_path(materialization_path, repo_root=root),
        "dcr_schedule_report": _display_path(dcr_path, repo_root=root),
        "artifact_dir": _display_path(out_dir, repo_root=root),
        "generated_source": _display_path(source, repo_root=root),
        "generated_binary": _display_path(binary, repo_root=root),
        "buffer_count": len(buffers),
        "host_to_device_bytes": _mapping(materialization.get("totals")).get("host_to_device_bytes"),
        "device_to_host_initial_bytes": _mapping(materialization.get("totals")).get("device_to_host_initial_bytes"),
        "dcr_write_count": dcr_write_count,
        "compile": {
            "argv": [_display_path(Path(arg), repo_root=root) if arg.startswith("/") else arg for arg in compile_argv],
            "returncode": compile_run.returncode,
            "stderr_tail": compile_run.stderr[-2000:],
        },
        "run": {
            "argv": [_display_path(Path(arg), repo_root=root) if arg.startswith("/") else arg for arg in run_argv],
            "returncode": run.returncode if run is not None else None,
            "stdout": run.stdout if run is not None else "",
            "stderr_tail": run.stderr[-2000:] if run is not None else "",
        },
        "readiness_delta": {
            "generated_c_harness_calls_vortex_lowered_tb_invoke_runtime_sequence": passed,
            "materialized_artifacts_consumed_by_generated_harness": passed,
            "fake_driver_runtime_sequence_authority_path_passed": passed,
        },
        "still_missing_for_execution": [
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "real_cuda_kernel_launch_callback_from_lowered_tb",
            "runtime_sequence_reports_real_memory_post_or_stdout_TEST_PASSED_authority",
            "cpu_vs_hybrid_timing_report.vortex",
        ],
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_real_verilator_generated_lowered_tb_integration",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "generated_c_smoke_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--materialization-report", default=DEFAULT_MATERIALIZATION_REPORT.as_posix())
    parser.add_argument("--dcr-schedule-report", default=DEFAULT_DCR_SCHEDULE_REPORT.as_posix())
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR.as_posix())
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json")
    args = parser.parse_args(argv)

    try:
        report = build_and_run_smoke(
            Path(args.repo_root),
            materialization_report=Path(args.materialization_report),
            dcr_schedule_report=Path(args.dcr_schedule_report),
            artifact_dir=Path(args.artifact_dir),
            cc=args.cc,
        )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["generated_lowered_tb_invocation_smoke_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
