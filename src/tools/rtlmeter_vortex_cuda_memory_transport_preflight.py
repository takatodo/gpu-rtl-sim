#!/usr/bin/env python3
"""Run a real CUDA Driver API upload/free preflight for Vortex materialized buffers."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DEFAULT_MATERIALIZATION_REPORT = Path("reports/rtlmeter_vortex_device_buffer_materialize.json")
DEFAULT_ARTIFACT_DIR = Path("artifacts/rtlmeter_vortex_cuda_memory_transport_preflight")
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
    return (
        "#include <cuda.h>\n"
        "#include <stdint.h>\n"
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        '#include "src/hybrid/vortex_runtime_upload.h"\n\n'
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
        "static VortexCuResult real_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) {\n"
        "  return (VortexCuResult)cuMemsetD8((CUdeviceptr)dst, value, bytes);\n"
        "}\n"
        "static VortexCuResult real_free(VortexCuDeviceptr ptr) {\n"
        "  return (VortexCuResult)cuMemFree((CUdeviceptr)ptr);\n"
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
        "  VortexCudaUploadDriver driver = {real_alloc, real_h2d, real_memset, real_free};\n"
        "  VortexRuntimeUploadSummary summary;\n"
        "  VortexCuResult result = vortex_upload_runtime_buffers(&driver, buffers, 7, &summary);\n"
        "  for (unsigned i = 0; i < 5; ++i) { free((void *)buffers[i].host_data); buffers[i].host_data = 0; }\n"
        "  if (result != VORTEX_CUDA_SUCCESS) {\n"
        "    printf(\"upload_result=%d failed_index=%d failed_op=%s\\n\", result, summary.failed_index, summary.failed_op ? summary.failed_op : \"\");\n"
        "    vortex_release_runtime_buffers(&driver, buffers, 7);\n"
        "    cuCtxDestroy(ctx);\n"
        "    return 21;\n"
        "  }\n"
        "  printf(\"allocated_count=%u\\n\", summary.allocated_count);\n"
        "  printf(\"h2d_copy_count=%u\\n\", summary.h2d_copy_count);\n"
        "  printf(\"d2h_init_count=%u\\n\", summary.d2h_init_count);\n"
        "  printf(\"h2d_bytes=%zu\\n\", summary.h2d_bytes);\n"
        "  printf(\"d2h_initial_bytes=%zu\\n\", summary.d2h_initial_bytes);\n"
        "  if (summary.allocated_count != 7 || summary.h2d_copy_count != 5 || summary.d2h_init_count != 2) return 22;\n"
        f"  if (summary.h2d_bytes != {expected_h2d_bytes}u || "
        f"summary.d2h_initial_bytes != {expected_d2h_initial_bytes}u) return 23;\n"
        "  vortex_release_runtime_buffers(&driver, buffers, 7);\n"
        "  cuCtxDestroy(ctx);\n"
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
    source = out_dir / "vortex_cuda_memory_transport_preflight.c"
    binary = out_dir / "vortex_cuda_memory_transport_preflight"
    source.write_text(_generated_source(repo_root=root, buffers=buffers), encoding="utf-8")
    compile_argv = [cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I.", source.as_posix(), "-lcuda", "-o", binary.as_posix()]
    compile_run = subprocess.run(compile_argv, cwd=root, text=True, capture_output=True)
    run = None
    if compile_run.returncode == 0:
        run = subprocess.run([binary.as_posix()], cwd=root, text=True, capture_output=True, env=_cuda_env(), timeout=60)
    passed = compile_run.returncode == 0 and run is not None and run.returncode == 0
    blocked_cuda = compile_run.returncode == 0 and run is not None and run.returncode in {10, 11, 12}
    status = "passed" if passed else "blocked_cuda_unavailable" if blocked_cuda else "failed"
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_cuda_memory_transport_preflight",
        "status": status,
        "case": "Vortex:mini:hello",
        "materialization_report": _display_path(materialization_path, repo_root=root),
        "artifact_dir": _display_path(out_dir, repo_root=root),
        "generated_source": _display_path(source, repo_root=root),
        "generated_binary": _display_path(binary, repo_root=root),
        "compile": {
            "argv": [
                _display_path(Path(arg), repo_root=root)
                if arg.startswith(root.as_posix())
                else arg
                for arg in compile_argv
            ],
            "returncode": compile_run.returncode,
            "stderr_tail": compile_run.stderr[-2000:],
        },
        "run": {
            "returncode": run.returncode if run is not None else None,
            "stdout": run.stdout if run is not None else "",
            "stderr_tail": run.stderr[-2000:] if run is not None else "",
        },
        "real_cuda_driver_api_invoked": compile_run.returncode == 0 and run is not None,
        "real_cuda_memory_transport_passed": passed,
        "buffer_count": len(buffers),
        "host_to_device_bytes": totals.get("host_to_device_bytes"),
        "device_to_host_initial_bytes": totals.get("device_to_host_initial_bytes"),
        "runtime_authority": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "cuda_memory_transport_preflight_only",
            "not_vortex_kernel_execution",
            "not_vortex_observable_authority",
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
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_cuda_memory_transport_preflight.json")
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
            "surface": "rtlmeter_vortex_cuda_memory_transport_preflight",
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
