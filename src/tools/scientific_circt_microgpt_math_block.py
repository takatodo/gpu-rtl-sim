#!/usr/bin/env python3
"""Materialize and time a microGPT-style scientific CIRCT math block."""

from __future__ import annotations

import argparse, json, re, shutil, subprocess
from pathlib import Path
from typing import Any

OUT_DIR = Path("artifacts/scientific_circt/microgpt_math_block")
REPORT = Path("reports/scientific_circt_microgpt_math_block.json")

FIRRTL = """FIRRTL version 4.0.0
circuit MicrogptMathBlock :
  public module MicrogptMathBlock :
    input x0 : UInt<16>
    input x1 : UInt<16>
    input x2 : UInt<16>
    input x3 : UInt<16>
    input x4 : UInt<16>
    input x5 : UInt<16>
    input x6 : UInt<16>
    input x7 : UInt<16>
    output y : UInt<64>

    node p01 = mul(x0, x1)
    node p23 = mul(x2, x3)
    node p45 = mul(x4, x5)
    node p67 = mul(x6, x7)
    node dot0 = add(p01, p23)
    node dot1 = add(p45, p67)
    node score = add(dot0, dot1)
    node score_s = add(score, UInt<33>(1))
    node score_q = mul(score_s, score_s)
    node soft = add(mul(score_q, score_s), score_q)
    node red0 = add(x0, x1)
    node red1 = add(x2, x3)
    node red2 = add(x4, x5)
    node red3 = add(x6, x7)
    node red4 = add(add(red0, red1), add(red2, red3))
    connect y, add(soft, red4)
"""

HARNESS = r'''#include "Vsim.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
static uint64_t ref(const std::array<uint16_t, 8>& x) {
  uint64_t score = uint64_t(x[0])*x[1] + uint64_t(x[2])*x[3] + uint64_t(x[4])*x[5] + uint64_t(x[6])*x[7];
  uint64_t s = score + 1u, q = s * s, red = 0;
  for (uint16_t v : x) red += v;
  return q * s + q + red;
}
int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Vsim top;
  const std::array<std::array<uint16_t, 8>, 4> cases = {{
      {1,2,3,4,5,6,7,8}, {9,10,11,12,13,14,15,16},
      {255,17,19,23,29,31,37,41}, {63,64,65,66,67,68,69,70},
  }};
  for (const auto &c : cases) {
    top.x0=c[0]; top.x1=c[1]; top.x2=c[2]; top.x3=c[3]; top.x4=c[4]; top.x5=c[5]; top.x6=c[6]; top.x7=c[7]; top.eval();
    if (top.y != ref(c)) { std::cerr << "microgpt_math_block mismatch\n"; return 1; }
  }
  top.final();
  std::cout << "TEST PASSED microgpt_math_block_cpu_reference cases=" << cases.size() << "\n";
  return 0;
}
'''

CUDA = r'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <vector>
struct In { uint16_t x[8]; };
struct Out { uint64_t y; };
static void fill(std::vector<In>& in) {
  for (size_t i = 0; i < in.size(); ++i) for (int j = 0; j < 8; ++j) in[i].x[j] = uint16_t((i*17u+j*19u+1u)&0xffffu);
}
__host__ __device__ static uint64_t eval_once(const In& in) {
  uint64_t score = uint64_t(in.x[0])*in.x[1] + uint64_t(in.x[2])*in.x[3] + uint64_t(in.x[4])*in.x[5] + uint64_t(in.x[6])*in.x[7];
  uint64_t s = score + 1u, q = s * s, red = 0;
  for (int j = 0; j < 8; ++j) red += in.x[j];
  return q * s + q + red;
}
__host__ __device__ static Out compute(const In& in, int inner) {
  uint64_t y = 0, base = eval_once(in);
  for (int r = 0; r < inner; ++r) y = (y + base) ^ uint64_t((r * 13) & 255);
  return Out{y};
}
__global__ static void kernel(const In* in, Out* out, int n, int inner) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < n) out[idx] = compute(in[idx], inner);
}
static double ms_since(std::chrono::steady_clock::time_point s) {
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s).count();
}
static bool same(const std::vector<Out>& a, const std::vector<Out>& b) {
  for (size_t i = 0; i < a.size(); ++i) if (a[i].y != b[i].y) return false;
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
        raise ValueError("microgpt_math_block currently supports Nx1 shapes")
    out_dir.mkdir(parents=True, exist_ok=True)
    fir, sv, harness, obj = out_dir / "microgpt_math_block.fir", out_dir / "microgpt_math_block.sv", out_dir / "tb_microgpt_math_block.cpp", out_dir / "obj_dir"
    cu, bin_path = out_dir / "microgpt_math_block_gpu_timing.cu", out_dir / "microgpt_math_block_gpu_timing"
    fir.write_text(FIRRTL, encoding="utf-8"); harness.write_text(HARNESS, encoding="utf-8"); cu.write_text(CUDA, encoding="utf-8")
    report: dict[str, Any] = {"schema_version": 1, "surface": "scientific_circt_testbench", "candidate": "microgpt_math_block", "shape": shape, "inner_repeat": inner_repeat, "commands": [], "toolchain": {"firtool": bool(shutil.which("firtool")), "verilator": bool(shutil.which("verilator")), "nvcc": bool(shutil.which("nvcc"))}, "non_claims": ["not_microgpt_execution", "not_a_general_rtl_speedup_claim", "not_automatic_partitioning"]}
    for name, cmd in [
        ("firtool", ["firtool", fir.as_posix(), "-o", sv.as_posix()]),
        ("verilator_build", ["verilator", "--cc", "--exe", "--timing", "-Wno-fatal", "--prefix", "Vsim", "--top-module", "MicrogptMathBlock", "-Mdir", obj.as_posix(), sv.as_posix(), harness.as_posix(), "--build"]),
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
