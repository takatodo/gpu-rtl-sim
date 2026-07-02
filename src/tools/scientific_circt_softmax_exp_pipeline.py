#!/usr/bin/env python3
"""Materialize and time the scientific CIRCT softmax/exp-style candidate."""

from __future__ import annotations

import argparse, json, re, shutil, subprocess
from pathlib import Path
from typing import Any

OUT_DIR = Path("artifacts/scientific_circt/softmax_exp_pipeline")
REPORT = Path("reports/scientific_circt_softmax_exp_pipeline.json")

FIRRTL = """FIRRTL version 4.0.0
circuit SoftmaxExpPipeline :
  public module SoftmaxExpPipeline :
    input x0 : UInt<16>
    input x1 : UInt<16>
    input x2 : UInt<16>
    input x3 : UInt<16>
    output y0 : UInt<48>
    output y1 : UInt<48>
    output y2 : UInt<48>
    output y3 : UInt<48>

    node x0s = add(x0, UInt<16>(1))
    node x1s = add(x1, UInt<16>(1))
    node x2s = add(x2, UInt<16>(1))
    node x3s = add(x3, UInt<16>(1))
    node x0q = mul(x0s, x0s)
    node x1q = mul(x1s, x1s)
    node x2q = mul(x2s, x2s)
    node x3q = mul(x3s, x3s)
    connect y0, add(mul(x0q, x0s), x0q)
    connect y1, add(mul(x1q, x1s), x1q)
    connect y2, add(mul(x2q, x2s), x2q)
    connect y3, add(mul(x3q, x3s), x3q)
"""

HARNESS = r'''#include "Vsim.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
static uint64_t ref(uint16_t x) { uint64_t s = uint64_t(x) + 1u, q = s * s; return q * s + q; }
int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Vsim top;
  const std::array<std::array<uint16_t, 4>, 4> cases = {{{1,2,3,4},{9,10,11,12},{255,17,19,23},{63,64,65,66}}};
  for (const auto &x : cases) {
    top.x0=x[0]; top.x1=x[1]; top.x2=x[2]; top.x3=x[3]; top.eval();
    if (top.y0 != ref(x[0]) || top.y1 != ref(x[1]) || top.y2 != ref(x[2]) || top.y3 != ref(x[3])) {
      std::cerr << "softmax_exp_pipeline mismatch\n"; return 1;
    }
  }
  top.final();
  std::cout << "TEST PASSED softmax_exp_pipeline_cpu_reference cases=" << cases.size() << "\n";
  return 0;
}
'''

CUDA = r'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <vector>
struct In { uint16_t x[4]; };
struct Out { uint64_t y[4]; };
static void fill(std::vector<In>& in) {
  for (size_t i = 0; i < in.size(); ++i) for (int j = 0; j < 4; ++j) in[i].x[j] = uint16_t((i*17u+j*19u+1u)&0xffffu);
}
__host__ __device__ static uint64_t approx(uint16_t x) { uint64_t s = uint64_t(x) + 1u, q = s * s; return q * s + q; }
__host__ __device__ static Out compute(const In& in, int inner) {
  Out o{{0,0,0,0}};
  for (int r = 0; r < inner; ++r) for (int j = 0; j < 4; ++j) o.y[j] = (o.y[j] + approx(in.x[j])) ^ uint64_t((r + j) & 15);
  return o;
}
__global__ static void kernel(const In* in, Out* out, int n, int inner) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < n) out[idx] = compute(in[idx], inner);
}
static double ms_since(std::chrono::steady_clock::time_point s) {
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s).count();
}
static bool same(const std::vector<Out>& a, const std::vector<Out>& b) {
  for (size_t i = 0; i < a.size(); ++i) for (int j = 0; j < 4; ++j) if (a[i].y[j] != b[i].y[j]) return false;
  return true;
}
int main(int argc, char** argv) {
  if (argc != 4) return 2;
  int n = std::stoi(argv[1]), repeat = std::stoi(argv[2]), inner = std::stoi(argv[3]);
  if (n <= 0 || repeat <= 0 || inner <= 0) return 2;
  std::vector<In> input(n); std::vector<Out> cpu(n), gpu(n); fill(input);
  In* d_in = nullptr; Out* d_out = nullptr; cudaEvent_t ks, ke;
  cudaEventCreate(&ks); cudaEventCreate(&ke); cudaFree(nullptr);
  cudaMalloc(&d_in, input.size() * sizeof(In)); cudaMalloc(&d_out, gpu.size() * sizeof(Out));
  int threads = 256, blocks = (n + threads - 1) / threads;
  cudaMemcpy(d_in, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
  kernel<<<blocks, threads>>>(d_in, d_out, n, inner); cudaDeviceSynchronize();
  double cpu_ms = 0.0, gpu_ms = 0.0, kernel_ms = 0.0; bool match = true;
  for (int r = 0; r < repeat; ++r) {
    auto cs = std::chrono::steady_clock::now();
    for (int i = 0; i < n; ++i) cpu[i] = compute(input[i], inner);
    cpu_ms += ms_since(cs);
    auto gs = std::chrono::steady_clock::now();
    cudaMemcpy(d_in, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
    cudaEventRecord(ks); kernel<<<blocks, threads>>>(d_in, d_out, n, inner); cudaEventRecord(ke); cudaEventSynchronize(ke);
    float km = 0.0f; cudaEventElapsedTime(&km, ks, ke); kernel_ms += km;
    cudaMemcpy(gpu.data(), d_out, gpu.size() * sizeof(Out), cudaMemcpyDeviceToHost); cudaDeviceSynchronize();
    gpu_ms += ms_since(gs); match = match && same(cpu, gpu);
  }
  cudaFree(d_in); cudaFree(d_out); cudaEventDestroy(ks); cudaEventDestroy(ke);
  cpu_ms /= repeat; gpu_ms /= repeat; kernel_ms /= repeat;
  std::cout << "{\"status\":\"" << (match ? "measured" : "mismatch") << "\",\"nstates\":" << n
            << ",\"repeat\":" << repeat << ",\"inner_repeat\":" << inner << ",\"match\":" << (match ? "true" : "false")
            << ",\"cpu_ms\":" << cpu_ms << ",\"gpu_end_to_end_ms\":" << gpu_ms << ",\"gpu_kernel_ms\":" << kernel_ms
            << ",\"cpu_to_gpu_end_to_end_speedup\":" << (gpu_ms > 0.0 ? cpu_ms / gpu_ms : 0.0)
            << ",\"cpu_to_gpu_kernel_speedup\":" << (kernel_ms > 0.0 ? cpu_ms / kernel_ms : 0.0) << "}\n";
  return match ? 0 : 1;
}
'''


def _sanitize(text: str) -> str:
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", text.replace(Path.cwd().as_posix(), "<repo>"))


def _run(argv: list[str]) -> dict[str, Any]:
    p = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {"argv": [_sanitize(a) for a in argv], "returncode": p.returncode, "stdout": _sanitize(p.stdout.strip()), "stderr": _sanitize(p.stderr.strip())}


def _shape(shape: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d+)x(\d+)", shape)
    if not m:
        raise ValueError("shape must use NxS form")
    return int(m.group(1)), int(m.group(2))


def materialize_and_measure(shape: str, repeat: int, inner_repeat: int, out_dir: Path = OUT_DIR) -> dict[str, Any]:
    nstates, steps = _shape(shape)
    if steps != 1:
        raise ValueError("softmax_exp_pipeline currently supports Nx1 shapes")
    out_dir.mkdir(parents=True, exist_ok=True)
    fir, sv, harness, obj = out_dir / "softmax_exp_pipeline.fir", out_dir / "softmax_exp_pipeline.sv", out_dir / "tb_softmax_exp_pipeline.cpp", out_dir / "obj_dir"
    cu, bin_path = out_dir / "softmax_exp_pipeline_gpu_timing.cu", out_dir / "softmax_exp_pipeline_gpu_timing"
    fir.write_text(FIRRTL, encoding="utf-8"); harness.write_text(HARNESS, encoding="utf-8"); cu.write_text(CUDA, encoding="utf-8")
    report: dict[str, Any] = {"schema_version": 1, "surface": "scientific_circt_testbench", "candidate": "softmax_exp_pipeline", "shape": shape, "inner_repeat": inner_repeat, "commands": [], "toolchain": {"firtool": bool(shutil.which("firtool")), "verilator": bool(shutil.which("verilator")), "nvcc": bool(shutil.which("nvcc"))}, "non_claims": ["not_a_general_rtl_speedup_claim", "not_automatic_partitioning"]}
    for name, cmd in [
        ("firtool", ["firtool", fir.as_posix(), "-o", sv.as_posix()]),
        ("verilator_build", ["verilator", "--cc", "--exe", "--timing", "-Wno-fatal", "--prefix", "Vsim", "--top-module", "SoftmaxExpPipeline", "-Mdir", obj.as_posix(), sv.as_posix(), harness.as_posix(), "--build"]),
        ("cpu_reference_run", [(obj / "Vsim").as_posix()]),
        ("nvcc_build", ["nvcc", "-O3", "--std=c++17", cu.as_posix(), "-o", bin_path.as_posix()]),
        ("cpu_gpu_timing_run", [bin_path.as_posix(), str(nstates), str(repeat), str(inner_repeat)]),
    ]:
        result = _run(cmd); report["commands"].append({"stage": name, **result})
        if result["returncode"] != 0:
            report["status"] = f"failed_{name}"; return report
    sample = json.loads(report["commands"][-1]["stdout"])
    median = {k: sample[k] for k in ("cpu_ms", "gpu_end_to_end_ms", "gpu_kernel_ms", "cpu_to_gpu_end_to_end_speedup", "cpu_to_gpu_kernel_speedup")}
    report.update({"status": "measured" if sample.get("match") else "mismatch", "median": median, "samples": [sample], "repeat_count": 1})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", default="256x1"); parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--inner-repeat", type=int, default=1000); parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write-report", action="store_true"); parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = materialize_and_measure(args.shape, args.repeat, args.inner_repeat, args.out_dir)
    except Exception as exc:
        print(str(exc)); return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True); args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "measured" else 1


if __name__ == "__main__":
    raise SystemExit(main())
