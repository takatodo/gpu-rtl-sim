#!/usr/bin/env python3
"""Run a real CUDA Driver API runtime-sequence preflight for Vortex buffers."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rtlmeter_vortex_cuda_memory_transport_preflight import (
    DEFAULT_MATERIALIZATION_REPORT,
    REQUIRED_BUFFER_ORDER,
    _collect_buffers,
    _display_path,
    _load_json,
    _mapping,
    _resolve,
)


DEFAULT_ARTIFACT_DIR = Path("artifacts/rtlmeter_vortex_cuda_runtime_sequence_preflight")


def _artifact_literal(path: Path, *, repo_root: Path) -> str:
    return json.dumps(_display_path(path, repo_root=repo_root))


def _generated_source(*, repo_root: Path, buffers: list[dict[str, Any]]) -> str:
    buffer_defs = []
    expected_h2d_bytes = sum(
        int(row["bytes"]) for row in buffers if row["direction"] == "VORTEX_BUFFER_HOST_TO_DEVICE"
    )
    expected_d2h_initial_bytes = sum(
        int(row["bytes"]) for row in buffers if row["direction"] == "VORTEX_BUFFER_DEVICE_TO_HOST"
    )
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
    dcr_index = REQUIRED_BUFFER_ORDER.index("vortex_dcr_write_table")
    return (
        "#include <cuda.h>\n"
        "#include <stdint.h>\n"
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        '#include "src/hybrid/vortex_lowered_tb_runtime_sequence.h"\n\n'
        "static void *load_file(const char *path, size_t expected_bytes) {\n"
        "  FILE *fp = fopen(path, \"rb\");\n"
        "  if (!fp) return 0;\n"
        "  unsigned char *data = (unsigned char *)malloc(expected_bytes == 0 ? 1 : expected_bytes);\n"
        "  if (!data) { fclose(fp); return 0; }\n"
        "  size_t read_bytes = fread(data, 1, expected_bytes, fp);\n"
        "  int extra = fgetc(fp);\n"
        "  fclose(fp);\n"
        "  if (read_bytes != expected_bytes || extra != EOF) { free(data); return 0; }\n"
        "  return data;\n"
        "}\n\n"
        "static VortexCuResult real_alloc(VortexCuDeviceptr *out, size_t bytes) {\n"
        "  CUdeviceptr ptr = 0;\n"
        "  CUresult r = cuMemAlloc(&ptr, bytes);\n"
        "  if (r == CUDA_SUCCESS) *out = (VortexCuDeviceptr)ptr;\n"
        "  return (VortexCuResult)r;\n"
        "}\n"
        "static VortexCuResult real_h2d(VortexCuDeviceptr dst, const void *src, size_t bytes) {\n"
        "  return (VortexCuResult)cuMemcpyHtoD((CUdeviceptr)dst, src, bytes);\n"
        "}\n"
        "static VortexCuResult real_d2h(void *dst, VortexCuDeviceptr src, size_t bytes) {\n"
        "  return (VortexCuResult)cuMemcpyDtoH(dst, (CUdeviceptr)src, bytes);\n"
        "}\n"
        "static VortexCuResult real_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {\n"
        "  return (VortexCuResult)cuMemsetD8((CUdeviceptr)dst, value, bytes);\n"
        "}\n"
        "static VortexCuResult real_free(VortexCuDeviceptr ptr) {\n"
        "  return (VortexCuResult)cuMemFree((CUdeviceptr)ptr);\n"
        "}\n\n"
        "typedef struct { unsigned dcr_calls; unsigned kernel_calls; } ProbeUser;\n"
        "static VortexCuResult apply_dcr_probe(void *user, uint32_t addr, uint32_t value, int reset_asserted) {\n"
        "  ProbeUser *probe = (ProbeUser *)user;\n"
        "  if (!probe || !reset_asserted) return 1;\n"
        "  (void)addr;\n"
        "  (void)value;\n"
        "  ++probe->dcr_calls;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n"
        "static VortexCuResult launch_noop_probe(void *user, VortexRuntimeBuffer *buffers, unsigned buffer_count) {\n"
        "  ProbeUser *probe = (ProbeUser *)user;\n"
        "  if (!probe || !buffers || buffer_count != 7) return 1;\n"
        "  ++probe->kernel_calls;\n"
        "  return VORTEX_CUDA_SUCCESS;\n"
        "}\n\n"
        "int main(void) {\n"
        "  CUresult r = cuInit(0);\n"
        "  if (r != CUDA_SUCCESS) { printf(\"cuInit=%d\\n\", (int)r); return 10; }\n"
        "  CUdevice dev;\n"
        "  r = cuDeviceGet(&dev, 0);\n"
        "  if (r != CUDA_SUCCESS) { printf(\"cuDeviceGet=%d\\n\", (int)r); return 11; }\n"
        "  CUcontext ctx;\n"
        "  r = cuCtxCreate(&ctx, 0, dev);\n"
        "  if (r != CUDA_SUCCESS) { printf(\"cuCtxCreate=%d\\n\", (int)r); return 12; }\n"
        "  VortexRuntimeBuffer buffers[7];\n"
        + "\n".join(buffer_defs)
        + "\n"
        "  for (unsigned i = 0; i < 5; ++i) { if (buffers[i].host_data == 0) return 20; }\n"
        f"  VortexDcrWrite *dcr_writes = (VortexDcrWrite *)buffers[{dcr_index}].host_data;\n"
        f"  unsigned dcr_write_count = (unsigned)(buffers[{dcr_index}].bytes / sizeof(VortexDcrWrite));\n"
        "  VortexCudaUploadDriver upload_driver = {real_alloc, real_h2d, real_memset, real_free};\n"
        "  VortexObservableExportDriver export_driver = {real_d2h};\n"
        "  ProbeUser probe = {0, 0};\n"
        "  VortexRuntimeSequenceArgs args;\n"
        "  args.upload_driver = &upload_driver;\n"
        "  args.buffers = buffers;\n"
        "  args.buffer_count = 7;\n"
        "  args.dcr_writes = dcr_writes;\n"
        "  args.dcr_write_count = dcr_write_count;\n"
        "  args.apply_dcr = apply_dcr_probe;\n"
        "  args.dcr_user = &probe;\n"
        "  args.launch_kernel = launch_noop_probe;\n"
        "  args.kernel_user = &probe;\n"
        "  args.export_driver = &export_driver;\n"
        "  VortexRuntimeSequenceSummary sequence_summary;\n"
        "  VortexLoweredTbRuntimeSummary tb_summary;\n"
        "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
        "  for (unsigned i = 0; i < 5; ++i) { free((void *)buffers[i].host_data); buffers[i].host_data = 0; }\n"
        "  cuCtxDestroy(ctx);\n"
        "  printf(\"result=%d\\n\", result);\n"
        "  printf(\"runtime_sequence_called=%d\\n\", tb_summary.runtime_sequence_called);\n"
        "  printf(\"runtime_sequence_passed=%d\\n\", tb_summary.runtime_sequence_passed);\n"
        "  printf(\"authority_report_ready=%d\\n\", tb_summary.authority_report_ready);\n"
        "  printf(\"authority_passed=%d\\n\", tb_summary.authority_passed);\n"
        "  printf(\"authority_source=%s\\n\", tb_summary.authority_source ? tb_summary.authority_source : \"\");\n"
        "  printf(\"allocated_count=%u\\n\", sequence_summary.upload.allocated_count);\n"
        "  printf(\"h2d_bytes=%zu\\n\", sequence_summary.upload.h2d_bytes);\n"
        "  printf(\"d2h_initial_bytes=%zu\\n\", sequence_summary.upload.d2h_initial_bytes);\n"
        "  printf(\"dcr_applied_count=%u\\n\", sequence_summary.dcr_applied_count);\n"
        "  printf(\"kernel_launch_invoked=%d\\n\", sequence_summary.kernel_launch_invoked);\n"
        "  printf(\"observable_export_invoked=%d\\n\", sequence_summary.observable_export_invoked);\n"
        "  printf(\"buffers_released=%d\\n\", sequence_summary.buffers_released);\n"
        "  printf(\"probe_dcr_calls=%u\\n\", probe.dcr_calls);\n"
        "  printf(\"probe_kernel_calls=%u\\n\", probe.kernel_calls);\n"
        "  if (result != VORTEX_CUDA_SUCCESS) return 21;\n"
        "  if (!tb_summary.runtime_sequence_called || !tb_summary.runtime_sequence_passed) return 22;\n"
        "  if (!tb_summary.authority_report_ready || !tb_summary.authority_passed) return 23;\n"
        "  if (sequence_summary.upload.allocated_count != 7) return 24;\n"
        f"  if (sequence_summary.upload.h2d_bytes != {expected_h2d_bytes}u) return 25;\n"
        f"  if (sequence_summary.upload.d2h_initial_bytes != {expected_d2h_initial_bytes}u) return 26;\n"
        "  if (sequence_summary.dcr_applied_count != 9 || probe.dcr_calls != 9) return 27;\n"
        "  if (!sequence_summary.kernel_launch_invoked || probe.kernel_calls != 1) return 28;\n"
        "  if (!sequence_summary.observable_export_invoked || !sequence_summary.buffers_released) return 29;\n"
        "  return 0;\n"
        "}\n"
    )


def _cuda_env() -> dict[str, str]:
    env = os.environ.copy()
    wsl_libcuda = Path("/usr/lib/wsl/lib")
    if wsl_libcuda.is_dir():
        prior = env.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = (
            wsl_libcuda.as_posix() if not prior else wsl_libcuda.as_posix() + os.pathsep + prior
        )
    return env


def _stdout_value(stdout: str, key: str) -> str | None:
    prefix = key + "="
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def build_and_run_preflight(
    repo_root: Path,
    *,
    materialization_report: Path = DEFAULT_MATERIALIZATION_REPORT,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    cc: str = "cc",
) -> dict[str, Any]:
    root = repo_root.resolve()
    materialization_path = _resolve(materialization_report, repo_root=root)
    materialization = _load_json(materialization_path)
    buffers = _collect_buffers(materialization, repo_root=root)
    totals = _mapping(materialization.get("totals"))

    out_dir = _resolve(artifact_dir, repo_root=root)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / "vortex_cuda_runtime_sequence_preflight.c"
    binary = out_dir / "vortex_cuda_runtime_sequence_preflight"
    source.write_text(_generated_source(repo_root=root, buffers=buffers), encoding="utf-8")
    compile_argv = [
        cc,
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I.",
        source.as_posix(),
        "-lcuda",
        "-o",
        binary.as_posix(),
    ]
    compile_run = subprocess.run(compile_argv, cwd=root, text=True, capture_output=True)
    run = None
    if compile_run.returncode == 0:
        run = subprocess.run([binary.as_posix()], cwd=root, text=True, capture_output=True, env=_cuda_env(), timeout=60)
    passed = compile_run.returncode == 0 and run is not None and run.returncode == 0
    blocked_cuda = compile_run.returncode == 0 and run is not None and run.returncode in {10, 11, 12}
    stdout = run.stdout if run is not None else ""
    status = "passed" if passed else "blocked_cuda_unavailable" if blocked_cuda else "failed"
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_cuda_runtime_sequence_preflight",
        "status": status,
        "case": "Vortex:mini:hello",
        "materialization_report": _display_path(materialization_path, repo_root=root),
        "artifact_dir": _display_path(out_dir, repo_root=root),
        "generated_source": _display_path(source, repo_root=root),
        "generated_binary": _display_path(binary, repo_root=root),
        "compile": {
            "argv": [
                _display_path(Path(arg), repo_root=root) if arg.startswith(root.as_posix()) else arg
                for arg in compile_argv
            ],
            "returncode": compile_run.returncode,
            "stderr_tail": compile_run.stderr[-2000:],
        },
        "run": {
            "returncode": run.returncode if run is not None else None,
            "stdout": stdout,
            "stderr_tail": run.stderr[-2000:] if run is not None else "",
        },
        "real_cuda_driver_api_invoked": compile_run.returncode == 0 and run is not None,
        "real_cuda_runtime_sequence_preflight_passed": passed,
        "runtime_sequence_called": "runtime_sequence_called=1" in stdout,
        "runtime_sequence_passed": "runtime_sequence_passed=1" in stdout,
        "dcr_applied_count": 9 if "dcr_applied_count=9" in stdout else None,
        "kernel_callback_invoked": "kernel_launch_invoked=1" in stdout and "probe_kernel_calls=1" in stdout,
        "observable_export_invoked": "observable_export_invoked=1" in stdout,
        "preflight_authority_report_ready": "authority_report_ready=1" in stdout,
        "preflight_authority_passed": "authority_passed=1" in stdout,
        "preflight_authority_source": _stdout_value(stdout, "authority_source"),
        "host_to_device_bytes": totals.get("host_to_device_bytes"),
        "device_to_host_initial_bytes": totals.get("device_to_host_initial_bytes"),
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "runtime_sequence_preflight_only",
            "noop_kernel_callback_not_vortex_kernel_execution",
            "preflight_authority_is_not_vortex_observable_authority",
            "not_real_verilator_generated_lowered_tb_integration",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--materialization-report", default=DEFAULT_MATERIALIZATION_REPORT.as_posix())
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR.as_posix())
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_cuda_runtime_sequence_preflight.json")
    args = parser.parse_args(argv)

    try:
        report = build_and_run_preflight(
            Path(args.repo_root),
            materialization_report=Path(args.materialization_report),
            artifact_dir=Path(args.artifact_dir),
            cc=args.cc,
        )
    except Exception as exc:
        report = {
            "schema_version": 1,
            "surface": "rtlmeter_vortex_cuda_runtime_sequence_preflight",
            "status": "failed",
            "case": "Vortex:mini:hello",
            "error": str(exc),
            "runtime_authority": False,
            "timing_measured": False,
            "speedup_claimed": False,
        }
    if args.write_report:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {"passed", "blocked_cuda_unavailable"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
