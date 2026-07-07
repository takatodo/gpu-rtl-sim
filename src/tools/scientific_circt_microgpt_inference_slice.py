#!/usr/bin/env python3
"""Materialize and time a microGPT-derived two-token inference CIRCT slice."""

from __future__ import annotations

import argparse, json, re, shutil, subprocess
from pathlib import Path
from typing import Any

OUT_DIR = Path("artifacts/scientific_circt/microgpt_inference_slice")
REPORT = Path("reports/scientific_circt_microgpt_inference_slice.json")

FIRRTL = """FIRRTL version 4.0.0
circuit MicrogptInferenceSlice :
  public module MicrogptInferenceSlice :
    input tok0 : UInt<8>
    input pos0 : UInt<8>
    input tok1 : UInt<8>
    input pos1 : UInt<8>
    output logit0 : UInt<64>
    output logit1 : UInt<64>
    output cache_digest : UInt<64>

    node x00 = add(add(mul(tok0, UInt<5>(3)), mul(pos0, UInt<5>(5))), UInt<8>(7))
    node x01 = add(add(mul(tok0, UInt<5>(11)), mul(pos0, UInt<5>(13))), UInt<8>(17))
    node x10 = add(add(mul(tok1, UInt<5>(19)), mul(pos1, UInt<5>(23))), UInt<8>(29))
    node x11 = add(add(mul(tok1, UInt<5>(31)), mul(pos1, UInt<6>(37))), UInt<8>(41))

    node k00 = add(mul(x00, UInt<4>(3)), mul(x01, UInt<4>(5)))
    node k01 = add(mul(x00, UInt<4>(7)), mul(x01, UInt<4>(11)))
    node v00 = add(mul(x00, UInt<5>(13)), mul(x01, UInt<5>(17)))
    node v01 = add(mul(x00, UInt<5>(19)), mul(x01, UInt<5>(23)))

    node k10 = add(mul(x10, UInt<5>(29)), mul(x11, UInt<5>(31)))
    node k11 = add(mul(x10, UInt<6>(37)), mul(x11, UInt<6>(41)))
    node v10 = add(mul(x10, UInt<6>(43)), mul(x11, UInt<6>(47)))
    node v11 = add(mul(x10, UInt<6>(53)), mul(x11, UInt<6>(59)))

    node q10 = add(mul(x10, UInt<5>(17)), mul(x11, UInt<5>(19)))
    node q11 = add(mul(x10, UInt<5>(23)), mul(x11, UInt<5>(29)))
    node score0 = add(mul(q10, k00), mul(q11, k01))
    node score1 = add(mul(q10, k10), mul(q11, k11))
    node w0s = add(score0, UInt<28>(1))
    node w1s = add(score1, UInt<28>(1))
    node w0 = mul(w0s, w0s)
    node w1 = mul(w1s, w1s)

    node att0 = add(mul(w0, v00), mul(w1, v10))
    node att1 = add(mul(w0, v01), mul(w1, v11))
    node r0 = add(att0, x10)
    node r1 = add(att1, x11)
    node h0sum = add(add(mul(r0, UInt<4>(3)), mul(r1, UInt<4>(5))), UInt<12>(409))
    node h1sum = add(add(mul(r0, UInt<4>(7)), mul(r1, UInt<4>(11))), UInt<12>(853))
    node h0 = mux(gt(h0sum, UInt<64>(8192)), sub(h0sum, UInt<64>(8192)), UInt<64>(0))
    node h1 = mux(gt(h1sum, UInt<64>(16384)), sub(h1sum, UInt<64>(16384)), UInt<64>(0))

    connect logit0, add(mul(h0, UInt<6>(31)), mul(h1, UInt<6>(37)))
    connect logit1, add(mul(h0, UInt<6>(41)), mul(h1, UInt<6>(43)))
    connect cache_digest, add(add(k00, k01), add(add(v00, v01), add(k10, v10)))
"""

HARNESS = r'''#include "Vsim.h"
#include "verilated.h"
#include <array>
#include <cstdint>
#include <iostream>
struct Out { uint64_t logit0; uint64_t logit1; uint64_t cache_digest; };
static uint64_t relu_sub(uint64_t value, uint64_t bias) { return value > bias ? value - bias : 0; }
static Out ref(const std::array<uint8_t, 4>& x) {
  uint64_t tok0=x[0], pos0=x[1], tok1=x[2], pos1=x[3];
  uint64_t x00 = tok0*3 + pos0*5 + 7, x01 = tok0*11 + pos0*13 + 17;
  uint64_t x10 = tok1*19 + pos1*23 + 29, x11 = tok1*31 + pos1*37 + 41;
  uint64_t k00 = x00*3 + x01*5, k01 = x00*7 + x01*11, v00 = x00*13 + x01*17, v01 = x00*19 + x01*23;
  uint64_t k10 = x10*29 + x11*31, k11 = x10*37 + x11*41, v10 = x10*43 + x11*47, v11 = x10*53 + x11*59;
  uint64_t q10 = x10*17 + x11*19, q11 = x10*23 + x11*29;
  uint64_t score0 = q10*k00 + q11*k01, score1 = q10*k10 + q11*k11;
  uint64_t w0 = (score0 + 1) * (score0 + 1), w1 = (score1 + 1) * (score1 + 1);
  uint64_t r0 = w0*v00 + w1*v10 + x10, r1 = w0*v01 + w1*v11 + x11;
  uint64_t h0 = relu_sub(r0*3 + r1*5 + 409, 8192);
  uint64_t h1 = relu_sub(r0*7 + r1*11 + 853, 16384);
  return Out{h0*31 + h1*37, h0*41 + h1*43, k00 + k01 + v00 + v01 + k10 + v10};
}
int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Vsim top;
  const std::array<std::array<uint8_t, 4>, 4> cases = {{
      {1,0,2,1}, {17,3,19,4}, {31,7,29,8}, {63,15,61,15},
  }};
  for (const auto &c : cases) {
    top.tok0=c[0]; top.pos0=c[1]; top.tok1=c[2]; top.pos1=c[3]; top.eval();
    Out e = ref(c);
    if (top.logit0 != e.logit0 || top.logit1 != e.logit1 || top.cache_digest != e.cache_digest) {
      std::cerr << "microgpt_inference_slice mismatch\n"; return 1;
    }
  }
  top.final();
  std::cout << "TEST PASSED microgpt_inference_slice_cpu_reference cases=" << cases.size() << "\n";
  return 0;
}
'''

CUDA = r'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <vector>
struct In { uint8_t x[4]; };
struct Out { uint64_t logit0; uint64_t logit1; uint64_t cache_digest; };
static void fill(std::vector<In>& in) {
  for (size_t i = 0; i < in.size(); ++i) {
    in[i].x[0] = uint8_t((i * 17u + 1u) & 0x3fu);
    in[i].x[1] = uint8_t(i & 0x0fu);
    in[i].x[2] = uint8_t((i * 23u + 7u) & 0x3fu);
    in[i].x[3] = uint8_t((i + 1u) & 0x0fu);
  }
}
__host__ __device__ static uint64_t relu_sub(uint64_t value, uint64_t bias) { return value > bias ? value - bias : 0; }
__host__ __device__ static Out eval_once(const In& in) {
  uint64_t tok0=in.x[0], pos0=in.x[1], tok1=in.x[2], pos1=in.x[3];
  uint64_t x00 = tok0*3 + pos0*5 + 7, x01 = tok0*11 + pos0*13 + 17;
  uint64_t x10 = tok1*19 + pos1*23 + 29, x11 = tok1*31 + pos1*37 + 41;
  uint64_t k00 = x00*3 + x01*5, k01 = x00*7 + x01*11, v00 = x00*13 + x01*17, v01 = x00*19 + x01*23;
  uint64_t k10 = x10*29 + x11*31, k11 = x10*37 + x11*41, v10 = x10*43 + x11*47, v11 = x10*53 + x11*59;
  uint64_t q10 = x10*17 + x11*19, q11 = x10*23 + x11*29;
  uint64_t score0 = q10*k00 + q11*k01, score1 = q10*k10 + q11*k11;
  uint64_t w0 = (score0 + 1) * (score0 + 1), w1 = (score1 + 1) * (score1 + 1);
  uint64_t r0 = w0*v00 + w1*v10 + x10, r1 = w0*v01 + w1*v11 + x11;
  uint64_t h0 = relu_sub(r0*3 + r1*5 + 409, 8192);
  uint64_t h1 = relu_sub(r0*7 + r1*11 + 853, 16384);
  return Out{h0*31 + h1*37, h0*41 + h1*43, k00 + k01 + v00 + v01 + k10 + v10};
}
__host__ __device__ static Out compute(const In& in, int inner) {
  Out base = eval_once(in), out{0, 0, base.cache_digest};
  for (int r = 0; r < inner; ++r) {
    out.logit0 = (out.logit0 + base.logit0) ^ uint64_t((r * 13) & 255);
    out.logit1 = (out.logit1 + base.logit1) ^ uint64_t((r * 17) & 255);
    out.cache_digest ^= uint64_t((r + 1) * 19);
  }
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
  for (size_t i = 0; i < a.size(); ++i) if (a[i].logit0 != b[i].logit0 || a[i].logit1 != b[i].logit1 || a[i].cache_digest != b[i].cache_digest) return false;
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
        raise ValueError("microgpt_inference_slice currently supports Nx1 scenario batches")
    out_dir.mkdir(parents=True, exist_ok=True)
    fir = out_dir / "microgpt_inference_slice.fir"
    sv = out_dir / "microgpt_inference_slice.sv"
    harness = out_dir / "tb_microgpt_inference_slice.cpp"
    obj = out_dir / "obj_dir"
    cu = out_dir / "microgpt_inference_slice_gpu_timing.cu"
    bin_path = out_dir / "microgpt_inference_slice_gpu_timing"
    fir.write_text(FIRRTL, encoding="utf-8")
    harness.write_text(HARNESS, encoding="utf-8")
    cu.write_text(CUDA, encoding="utf-8")
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_testbench",
        "candidate": "microgpt_inference_slice",
        "shape": shape,
        "inner_repeat": inner_repeat,
        "commands": [],
        "toolchain": {"firtool": bool(shutil.which("firtool")), "verilator": bool(shutil.which("verilator")), "nvcc": bool(shutil.which("nvcc"))},
        "non_claims": [
            "not_full_microgpt_execution",
            "not_full_block_size_sequence",
            "not_training_or_autograd",
            "not_a_general_rtl_speedup_claim",
            "not_automatic_partitioning",
        ],
    }
    for name, cmd in [
        ("firtool", ["firtool", fir.as_posix(), "-o", sv.as_posix()]),
        ("verilator_build", ["verilator", "--cc", "--exe", "--timing", "-Wno-fatal", "--prefix", "Vsim", "--top-module", "MicrogptInferenceSlice", "-Mdir", obj.as_posix(), sv.as_posix(), harness.as_posix(), "--build"]),
        ("cpu_reference_run", [(obj / "Vsim").as_posix()]),
        ("nvcc_build", ["nvcc", "-O3", "--std=c++17", cu.as_posix(), "-o", bin_path.as_posix()]),
        ("cpu_gpu_timing_run", [bin_path.as_posix(), str(nstates), str(repeat), str(inner_repeat)]),
    ]:
        result = _run(cmd)
        report["commands"].append({"stage": name, **result})
        if result["returncode"] != 0:
            report["status"] = f"failed_{name}"
            return report
    sample = json.loads(report["commands"][-1]["stdout"])
    median = {k: sample[k] for k in ("cpu_ms", "gpu_end_to_end_ms", "gpu_kernel_ms", "cpu_to_gpu_end_to_end_speedup", "cpu_to_gpu_kernel_speedup")}
    report.update({"status": "measured" if sample.get("match") else "mismatch", "median": median, "samples": [sample], "repeat_count": 1})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", default="256x1")
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--inner-repeat", type=int, default=1000)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = materialize_and_measure(args.shape, args.repeat, args.inner_repeat, args.out_dir)
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
