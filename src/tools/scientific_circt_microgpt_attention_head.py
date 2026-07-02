#!/usr/bin/env python3
"""Materialize and time a microGPT-derived attention-head CIRCT slice."""

from __future__ import annotations

import argparse, json, re, shutil, subprocess
from pathlib import Path
from typing import Any

OUT_DIR = Path("artifacts/scientific_circt/microgpt_attention_head")
REPORT = Path("reports/scientific_circt_microgpt_attention_head.json")

FIRRTL = """FIRRTL version 4.0.0
circuit MicrogptAttentionHead :
  public module MicrogptAttentionHead :
    input q0 : UInt<8>
    input q1 : UInt<8>
    input q2 : UInt<8>
    input q3 : UInt<8>
    input k00 : UInt<8>
    input k01 : UInt<8>
    input k02 : UInt<8>
    input k03 : UInt<8>
    input k10 : UInt<8>
    input k11 : UInt<8>
    input k12 : UInt<8>
    input k13 : UInt<8>
    input v00 : UInt<8>
    input v01 : UInt<8>
    input v02 : UInt<8>
    input v03 : UInt<8>
    input v10 : UInt<8>
    input v11 : UInt<8>
    input v12 : UInt<8>
    input v13 : UInt<8>
    output y0 : UInt<56>
    output y1 : UInt<56>
    output y2 : UInt<56>
    output y3 : UInt<56>

    node s0a = add(mul(q0, k00), mul(q1, k01))
    node s0b = add(mul(q2, k02), mul(q3, k03))
    node score0 = add(s0a, s0b)
    node s1a = add(mul(q0, k10), mul(q1, k11))
    node s1b = add(mul(q2, k12), mul(q3, k13))
    node score1 = add(s1a, s1b)
    node w0s = add(score0, UInt<19>(1))
    node w1s = add(score1, UInt<19>(1))
    node w0 = mul(w0s, w0s)
    node w1 = mul(w1s, w1s)
    connect y0, add(mul(w0, v00), mul(w1, v10))
    connect y1, add(mul(w0, v01), mul(w1, v11))
    connect y2, add(mul(w0, v02), mul(w1, v12))
    connect y3, add(mul(w0, v03), mul(w1, v13))
"""

HARNESS = r'''#include "Vsim.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
struct Out { uint64_t y[4]; };
static Out ref(const std::array<uint8_t, 20>& x) {
  uint64_t q[4] = {x[0], x[1], x[2], x[3]};
  uint64_t k0[4] = {x[4], x[5], x[6], x[7]}, k1[4] = {x[8], x[9], x[10], x[11]};
  uint64_t v0[4] = {x[12], x[13], x[14], x[15]}, v1[4] = {x[16], x[17], x[18], x[19]};
  uint64_t score0 = 0, score1 = 0;
  for (int j = 0; j < 4; ++j) { score0 += q[j] * k0[j]; score1 += q[j] * k1[j]; }
  uint64_t w0 = (score0 + 1) * (score0 + 1), w1 = (score1 + 1) * (score1 + 1);
  return Out{{w0*v0[0]+w1*v1[0], w0*v0[1]+w1*v1[1], w0*v0[2]+w1*v1[2], w0*v0[3]+w1*v1[3]}};
}
int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Vsim top;
  const std::array<std::array<uint8_t, 20>, 4> cases = {{
      {1,2,3,4, 5,6,7,8, 9,10,11,12, 1,3,5,7, 2,4,6,8},
      {9,8,7,6, 5,4,3,2, 1,2,3,4, 7,6,5,4, 3,2,1,9},
      {17,19,23,29, 31,37,41,43, 47,53,59,61, 2,3,5,7, 11,13,17,19},
      {63,64,65,66, 12,13,14,15, 16,17,18,19, 20,21,22,23, 24,25,26,27},
  }};
  for (const auto &c : cases) {
    top.q0=c[0]; top.q1=c[1]; top.q2=c[2]; top.q3=c[3];
    top.k00=c[4]; top.k01=c[5]; top.k02=c[6]; top.k03=c[7]; top.k10=c[8]; top.k11=c[9]; top.k12=c[10]; top.k13=c[11];
    top.v00=c[12]; top.v01=c[13]; top.v02=c[14]; top.v03=c[15]; top.v10=c[16]; top.v11=c[17]; top.v12=c[18]; top.v13=c[19];
    top.eval();
    Out e = ref(c);
    if (top.y0 != e.y[0] || top.y1 != e.y[1] || top.y2 != e.y[2] || top.y3 != e.y[3]) {
      std::cerr << "microgpt_attention_head mismatch\n"; return 1;
    }
  }
  top.final();
  std::cout << "TEST PASSED microgpt_attention_head_cpu_reference cases=" << cases.size() << "\n";
  return 0;
}
'''

CUDA = r'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <vector>
struct In { uint8_t x[20]; };
struct Out { uint64_t y[4]; };
static void fill(std::vector<In>& in) {
  for (size_t i = 0; i < in.size(); ++i) for (int j = 0; j < 20; ++j) in[i].x[j] = uint8_t((i*17u+j*11u+1u)&0x7fu);
}
__host__ __device__ static Out eval_once(const In& in) {
  uint64_t score0 = 0, score1 = 0;
  for (int j = 0; j < 4; ++j) { score0 += uint64_t(in.x[j]) * in.x[4+j]; score1 += uint64_t(in.x[j]) * in.x[8+j]; }
  uint64_t w0 = (score0 + 1) * (score0 + 1), w1 = (score1 + 1) * (score1 + 1);
  Out out{{0,0,0,0}};
  for (int j = 0; j < 4; ++j) out.y[j] = w0 * in.x[12+j] + w1 * in.x[16+j];
  return out;
}
__host__ __device__ static Out compute(const In& in, int inner) {
  Out base = eval_once(in), out{{0,0,0,0}};
  for (int r = 0; r < inner; ++r) for (int j = 0; j < 4; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j) & 31);
  return out;
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
        raise ValueError("microgpt_attention_head currently supports Nx1 shapes")
    out_dir.mkdir(parents=True, exist_ok=True)
    fir, sv, harness, obj = out_dir / "microgpt_attention_head.fir", out_dir / "microgpt_attention_head.sv", out_dir / "tb_microgpt_attention_head.cpp", out_dir / "obj_dir"
    cu, bin_path = out_dir / "microgpt_attention_head_gpu_timing.cu", out_dir / "microgpt_attention_head_gpu_timing"
    fir.write_text(FIRRTL, encoding="utf-8"); harness.write_text(HARNESS, encoding="utf-8"); cu.write_text(CUDA, encoding="utf-8")
    report: dict[str, Any] = {"schema_version": 1, "surface": "scientific_circt_testbench", "candidate": "microgpt_attention_head", "shape": shape, "inner_repeat": inner_repeat, "commands": [], "toolchain": {"firtool": bool(shutil.which("firtool")), "verilator": bool(shutil.which("verilator")), "nvcc": bool(shutil.which("nvcc"))}, "non_claims": ["not_full_microgpt_execution", "not_a_general_rtl_speedup_claim", "not_automatic_partitioning"]}
    for name, cmd in [
        ("firtool", ["firtool", fir.as_posix(), "-o", sv.as_posix()]),
        ("verilator_build", ["verilator", "--cc", "--exe", "--timing", "-Wno-fatal", "--prefix", "Vsim", "--top-module", "MicrogptAttentionHead", "-Mdir", obj.as_posix(), sv.as_posix(), harness.as_posix(), "--build"]),
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
