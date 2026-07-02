#!/usr/bin/env python3
"""Measure CPU vs CUDA batched execution for the CIRCT dense matmul tile."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("artifacts/scientific_circt/dense_matmul_tile")
DEFAULT_REPORT = Path("reports/scientific_circt_dense_matmul_tile_gpu_timing.json")
CUDA_SOURCE = r'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <vector>

struct TileIn { uint16_t a00, a01, a10, a11, b00, b01, b10, b11; };
struct TileOut { uint64_t c00, c01, c10, c11; };

static void fill_inputs(std::vector<TileIn>& inputs) {
  for (size_t i = 0; i < inputs.size(); ++i) {
    inputs[i] = {static_cast<uint16_t>((i * 17u + 1u) & 0xffffu),
                 static_cast<uint16_t>((i * 19u + 2u) & 0xffffu),
                 static_cast<uint16_t>((i * 23u + 3u) & 0xffffu),
                 static_cast<uint16_t>((i * 29u + 4u) & 0xffffu),
                 static_cast<uint16_t>((i * 31u + 5u) & 0xffffu),
                 static_cast<uint16_t>((i * 37u + 6u) & 0xffffu),
                 static_cast<uint16_t>((i * 41u + 7u) & 0xffffu),
                 static_cast<uint16_t>((i * 43u + 8u) & 0xffffu)};
  }
}

__host__ __device__ static TileOut compute_tile(const TileIn& x, int inner_repeat) {
  uint64_t c00 = 0, c01 = 0, c10 = 0, c11 = 0;
  const uint64_t base00 = static_cast<uint64_t>(x.a00) * x.b00 + static_cast<uint64_t>(x.a01) * x.b10;
  const uint64_t base01 = static_cast<uint64_t>(x.a00) * x.b01 + static_cast<uint64_t>(x.a01) * x.b11;
  const uint64_t base10 = static_cast<uint64_t>(x.a10) * x.b00 + static_cast<uint64_t>(x.a11) * x.b10;
  const uint64_t base11 = static_cast<uint64_t>(x.a10) * x.b01 + static_cast<uint64_t>(x.a11) * x.b11;
  for (int r = 0; r < inner_repeat; ++r) {
    c00 = (c00 + base00) ^ static_cast<uint64_t>(r & 1);
    c01 = (c01 + base01) ^ static_cast<uint64_t>(r & 3);
    c10 = (c10 + base10) ^ static_cast<uint64_t>(r & 7);
    c11 = (c11 + base11) ^ static_cast<uint64_t>(r & 15);
  }
  return TileOut{c00, c01, c10, c11};
}

__global__ static void tile_kernel(const TileIn* inputs, TileOut* outputs, int nstates, int inner_repeat) {
  const int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= nstates) return;
  outputs[idx] = compute_tile(inputs[idx], inner_repeat);
}

static double millis_since(std::chrono::steady_clock::time_point start) {
  const auto end = std::chrono::steady_clock::now();
  return std::chrono::duration<double, std::milli>(end - start).count();
}

static bool same_outputs(const std::vector<TileOut>& l, const std::vector<TileOut>& r) {
  for (size_t i = 0; i < l.size(); ++i)
    if (l[i].c00 != r[i].c00 || l[i].c01 != r[i].c01 || l[i].c10 != r[i].c10 || l[i].c11 != r[i].c11) return false;
  return true;
}

int main(int argc, char** argv) {
  if (argc != 4) { std::cerr << "usage: " << argv[0] << " <nstates> <repeat> <inner_repeat>\n"; return 2; }
  const int nstates = std::stoi(argv[1]);
  const int repeat = std::stoi(argv[2]);
  const int inner_repeat = std::stoi(argv[3]);
  if (nstates <= 0 || repeat <= 0 || inner_repeat <= 0) return 2;

  std::vector<TileIn> inputs(nstates); std::vector<TileOut> cpu(nstates), gpu(nstates);
  fill_inputs(inputs);

  TileIn* d_inputs = nullptr;
  TileOut* d_outputs = nullptr;
  cudaEvent_t kernel_start, kernel_stop;
  cudaEventCreate(&kernel_start);
  cudaEventCreate(&kernel_stop);
  cudaFree(nullptr);
  cudaMalloc(&d_inputs, inputs.size() * sizeof(TileIn));
  cudaMalloc(&d_outputs, gpu.size() * sizeof(TileOut));

  double cpu_total_ms = 0.0, gpu_total_ms = 0.0, gpu_kernel_ms = 0.0;
  bool match = true;
  const int threads = 256;
  const int blocks = (nstates + threads - 1) / threads;
  cudaMemcpy(d_inputs, inputs.data(), inputs.size() * sizeof(TileIn), cudaMemcpyHostToDevice);
  tile_kernel<<<blocks, threads>>>(d_inputs, d_outputs, nstates, inner_repeat);
  cudaDeviceSynchronize();

  for (int r = 0; r < repeat; ++r) {
    auto cpu_start = std::chrono::steady_clock::now();
    for (int i = 0; i < nstates; ++i) cpu[i] = compute_tile(inputs[i], inner_repeat);
    cpu_total_ms += millis_since(cpu_start);

    auto gpu_start = std::chrono::steady_clock::now();
    cudaMemcpy(d_inputs, inputs.data(), inputs.size() * sizeof(TileIn), cudaMemcpyHostToDevice);
    cudaEventRecord(kernel_start);
    tile_kernel<<<blocks, threads>>>(d_inputs, d_outputs, nstates, inner_repeat);
    cudaEventRecord(kernel_stop);
    cudaEventSynchronize(kernel_stop);
    float sample_kernel_ms = 0.0f;
    cudaEventElapsedTime(&sample_kernel_ms, kernel_start, kernel_stop);
    gpu_kernel_ms += sample_kernel_ms;
    cudaMemcpy(gpu.data(), d_outputs, gpu.size() * sizeof(TileOut), cudaMemcpyDeviceToHost);
    cudaDeviceSynchronize();
    gpu_total_ms += millis_since(gpu_start);
    match = match && same_outputs(cpu, gpu);
  }

  cudaFree(d_inputs); cudaFree(d_outputs);
  cudaEventDestroy(kernel_start); cudaEventDestroy(kernel_stop);

  const double cpu_ms = cpu_total_ms / repeat, gpu_ms = gpu_total_ms / repeat, kernel_ms = gpu_kernel_ms / repeat;
  std::cout << "{\"status\":\"" << (match ? "measured" : "mismatch")
            << "\",\"nstates\":" << nstates << ",\"repeat\":" << repeat
            << ",\"inner_repeat\":" << inner_repeat << ",\"match\":" << (match ? "true" : "false")
            << ",\"cpu_ms\":" << cpu_ms << ",\"gpu_end_to_end_ms\":" << gpu_ms
            << ",\"gpu_kernel_ms\":" << kernel_ms
            << ",\"cpu_to_gpu_end_to_end_speedup\":" << (gpu_ms > 0.0 ? cpu_ms / gpu_ms : 0.0)
            << ",\"cpu_to_gpu_kernel_speedup\":" << (kernel_ms > 0.0 ? cpu_ms / kernel_ms : 0.0)
            << "}\n";
  return match ? 0 : 1;
}
'''


def _sanitize(text: str) -> str:
    text = text.replace(Path.cwd().as_posix(), "<repo>")
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", text)

def _display_path(path: Path, out_dir: Path) -> str:
    if out_dir.is_absolute():
        return f"<out_dir>/{path.relative_to(out_dir).as_posix()}"
    return path.as_posix()

def parse_shape(shape: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", shape.strip())
    if not match:
        raise ValueError(f"shape must use NxS form, got {shape!r}")
    return int(match.group(1)), int(match.group(2))


def _run(argv: list[str]) -> dict[str, Any]:
    result = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {
        "argv": [_sanitize(arg) for arg in argv],
        "returncode": result.returncode,
        "stdout": _sanitize(result.stdout.strip()),
        "stderr": _sanitize(result.stderr.strip()),
    }


def _median(samples: list[dict[str, Any]], key: str) -> float | None:
    values = sorted(float(sample[key]) for sample in samples if key in sample)
    if not values:
        return None
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2.0


def summarize_measurements(samples: list[dict[str, Any]]) -> dict[str, Any]:
    status = "measured" if samples and all(sample.get("match") for sample in samples) else "failed"
    keys = ("cpu_ms", "gpu_end_to_end_ms", "gpu_kernel_ms", "cpu_to_gpu_end_to_end_speedup", "cpu_to_gpu_kernel_speedup")
    return {
        "status": status,
        "repeat_count": len(samples),
        "median": {key: _median(samples, key) for key in keys},
        "samples": samples,
    }


def measure(
    *,
    shape: str,
    repeat: int,
    inner_repeat: int,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> dict[str, Any]:
    nstates, steps = parse_shape(shape)
    if steps != 1:
        raise ValueError("dense_matmul_tile CUDA timing currently supports Nx1 shapes")
    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / "dense_matmul_tile_gpu_timing.cu"
    binary = out_dir / "dense_matmul_tile_gpu_timing"
    source.write_text(CUDA_SOURCE, encoding="utf-8")
    report: dict[str, Any] = dict(
        schema_version=1,
        surface="scientific_circt_dense_matmul_tile_gpu_timing",
        candidate="dense_matmul_tile",
        shape=shape,
        inner_repeat=inner_repeat,
        artifacts={"cuda_source": _display_path(source, out_dir), "binary": _display_path(binary, out_dir)},
        toolchain={"nvcc": shutil.which("nvcc") is not None},
        commands=[],
        non_claims=[
            "single_candidate_scoped_measurement",
            "not_a_general_rtl_speedup_claim",
            "not_automatic_hybrid_partitioning",
        ],
    )
    if not report["toolchain"]["nvcc"]:
        report["status"] = "blocked_nvcc_missing"
        return report

    build = _run(["nvcc", "-O3", "--std=c++17", source.as_posix(), "-o", binary.as_posix()])
    report["commands"].append({"stage": "nvcc_build", **build})
    if build["returncode"] != 0:
        report["status"] = "failed_nvcc_build"
        return report
    run = _run([binary.as_posix(), str(nstates), str(repeat), str(inner_repeat)])
    report["commands"].append({"stage": "cpu_gpu_timing_run", **run})
    if run["returncode"] != 0:
        report["status"] = "failed_timing_run"
        return report
    report.update(summarize_measurements([json.loads(run["stdout"])]))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", default="64x1")
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--inner-repeat", type=int, default=1000)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    try:
        report = measure(shape=args.shape, repeat=args.repeat, inner_repeat=args.inner_repeat, out_dir=args.out_dir)
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "measured" else 1


if __name__ == "__main__":
    raise SystemExit(main())
