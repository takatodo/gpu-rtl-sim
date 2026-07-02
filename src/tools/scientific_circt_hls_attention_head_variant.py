#!/usr/bin/env python3
"""Measure an HLS-friendly multi-head attention source variant through Verilator."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

OUT_DIR = Path("artifacts/scientific_circt/hls_attention_head4")
REPORT = Path("reports/scientific_circt_hls_attention_head4.json")
BASELINE_REPORT = Path("reports/scientific_circt_verilator_callsite_entrypoint.json")
REPO_FIRTOOL = Path("artifacts/toolchains/circt-firtool-1.149.0/firtool-1.149.0/bin/firtool")


def _sanitize(text: str) -> str:
    repo = Path.cwd().as_posix()
    text = text.replace(repo, "<repo>")
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root|usr)/[^\s\"']+", "<local-path>", text)


def _display_path(path: Path) -> str:
    return _sanitize(path.as_posix())


def _run(argv: list[str]) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {
        "argv": [_sanitize(arg) for arg in argv],
        "returncode": proc.returncode,
        "stdout": _sanitize(proc.stdout.strip()),
        "stderr": _sanitize(proc.stderr.strip()),
        "process_wall_ms": (time.perf_counter() - start) * 1000.0,
    }


def _shape(shape: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", shape)
    if not match:
        raise ValueError("shape must use NxS form")
    return int(match.group(1)), int(match.group(2))


def _verilator_root_command() -> tuple[Path | None, dict[str, Any] | None]:
    env_root = os.environ.get("VERILATOR_ROOT")
    if env_root:
        return Path(env_root), None
    if shutil.which("verilator") is None:
        return None, {
            "argv": ["verilator", "--getenv", "VERILATOR_ROOT"],
            "returncode": 127,
            "stdout": "",
            "stderr": "missing verilator",
            "process_wall_ms": 0.0,
        }
    start = time.perf_counter()
    proc = subprocess.run(["verilator", "--getenv", "VERILATOR_ROOT"], text=True, capture_output=True, check=False)
    raw_stdout = proc.stdout.strip()
    result = {
        "argv": ["verilator", "--getenv", "VERILATOR_ROOT"],
        "returncode": proc.returncode,
        "stdout": _sanitize(raw_stdout),
        "stderr": _sanitize(proc.stderr.strip()),
        "process_wall_ms": (time.perf_counter() - start) * 1000.0,
    }
    return (Path(raw_stdout), result) if proc.returncode == 0 and raw_stdout else (None, result)


def _tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if name == "firtool" and REPO_FIRTOOL.exists():
        return REPO_FIRTOOL.as_posix()
    return None


# Must match the extern "C" function names and the fill() formula in the
# embedded GPU source template below.
GPU_SYMBOL_STEM = "attention_head4_hls"
FILL_A = 17
FILL_B = 11
FILL_C = 1
FILL_MASK = 0x7F
MIX_J_MULT = 1
MIX_MASK = 31


def input_port_names(heads: int = 4) -> tuple[str, ...]:
    """Return input port names in struct-field order (index k <-> in.x[k])."""
    return tuple(f"h{h}_x{i}" for h in range(heads) for i in range(20))


def output_port_names(heads: int = 4) -> tuple[str, ...]:
    """Return output port names in struct-field order (index k <-> base.y[k])."""
    return tuple(f"h{h}_y{j}" for h in range(heads) for j in range(4))


def _firrtl(heads: int = 4) -> str:
    lines = [
        "FIRRTL version 4.0.0",
        "circuit MicrogptAttentionHeadHls4 :",
        "  public module MicrogptAttentionHeadHls4 :",
    ]
    inputs, outputs = input_port_names(heads), output_port_names(heads)
    for h in range(heads):
        for port in inputs[h * 20 : (h + 1) * 20]:
            lines.append(f"    input {port} : UInt<8>")
        for port in outputs[h * 4 : (h + 1) * 4]:
            lines.append(f"    output {port} : UInt<56>")
    lines.append("")
    for h in range(heads):
        lines.extend(
            [
                f"    node h{h}_s0a = add(mul(h{h}_x0, h{h}_x4), mul(h{h}_x1, h{h}_x5))",
                f"    node h{h}_s0b = add(mul(h{h}_x2, h{h}_x6), mul(h{h}_x3, h{h}_x7))",
                f"    node h{h}_score0 = add(h{h}_s0a, h{h}_s0b)",
                f"    node h{h}_s1a = add(mul(h{h}_x0, h{h}_x8), mul(h{h}_x1, h{h}_x9))",
                f"    node h{h}_s1b = add(mul(h{h}_x2, h{h}_x10), mul(h{h}_x3, h{h}_x11))",
                f"    node h{h}_score1 = add(h{h}_s1a, h{h}_s1b)",
                f"    node h{h}_w0s = add(h{h}_score0, UInt<19>(1))",
                f"    node h{h}_w1s = add(h{h}_score1, UInt<19>(1))",
                f"    node h{h}_w0 = mul(h{h}_w0s, h{h}_w0s)",
                f"    node h{h}_w1 = mul(h{h}_w1s, h{h}_w1s)",
            ]
        )
        for j in range(4):
            lines.append(
                f"    connect h{h}_y{j}, add(mul(h{h}_w0, h{h}_x{12 + j}), mul(h{h}_w1, h{h}_x{16 + j}))"
            )
        lines.append("")
    return "\n".join(lines)


PROBE = r'''#include "Vsim.h"
#include "verilated.h"
int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Vsim top;
  top.eval();
  top.final();
  return 0;
}
'''


CUDA = r'''#include "Vsim.h"
#include "verilated.h"
#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <vector>

struct In { uint8_t x[80]; };
struct Out { uint64_t y[16]; };

static void fill(std::vector<In>& input) {
  for (size_t i = 0; i < input.size(); ++i)
    for (int j = 0; j < 80; ++j) input[i].x[j] = uint8_t((i * 17u + j * 11u + 1u) & 0x7fu);
}

__host__ __device__ static void eval_head(const uint8_t* x, uint64_t* y) {
  uint64_t score0 = 0, score1 = 0;
  for (int j = 0; j < 4; ++j) {
    score0 += uint64_t(x[j]) * x[4 + j];
    score1 += uint64_t(x[j]) * x[8 + j];
  }
  uint64_t w0 = (score0 + 1) * (score0 + 1);
  uint64_t w1 = (score1 + 1) * (score1 + 1);
  for (int j = 0; j < 4; ++j) y[j] = w0 * x[12 + j] + w1 * x[16 + j];
}

__host__ __device__ static Out compute_gpu(const In& in, int inner_repeat) {
  Out base{{0}}, out{{0}};
  for (int h = 0; h < 4; ++h) eval_head(&in.x[h * 20], &base.y[h * 4]);
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < 16; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j) & 31);
  return out;
}

__global__ static void kernel(const In* input, Out* output, int nstates, int inner_repeat) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < nstates) output[idx] = compute_gpu(input[idx], inner_repeat);
}

static void apply_head(Vsim& top, const uint8_t* x, int h) {
  switch (h) {
    case 0:
      top.h0_x0=x[0]; top.h0_x1=x[1]; top.h0_x2=x[2]; top.h0_x3=x[3]; top.h0_x4=x[4];
      top.h0_x5=x[5]; top.h0_x6=x[6]; top.h0_x7=x[7]; top.h0_x8=x[8]; top.h0_x9=x[9];
      top.h0_x10=x[10]; top.h0_x11=x[11]; top.h0_x12=x[12]; top.h0_x13=x[13]; top.h0_x14=x[14];
      top.h0_x15=x[15]; top.h0_x16=x[16]; top.h0_x17=x[17]; top.h0_x18=x[18]; top.h0_x19=x[19]; break;
    case 1:
      top.h1_x0=x[0]; top.h1_x1=x[1]; top.h1_x2=x[2]; top.h1_x3=x[3]; top.h1_x4=x[4];
      top.h1_x5=x[5]; top.h1_x6=x[6]; top.h1_x7=x[7]; top.h1_x8=x[8]; top.h1_x9=x[9];
      top.h1_x10=x[10]; top.h1_x11=x[11]; top.h1_x12=x[12]; top.h1_x13=x[13]; top.h1_x14=x[14];
      top.h1_x15=x[15]; top.h1_x16=x[16]; top.h1_x17=x[17]; top.h1_x18=x[18]; top.h1_x19=x[19]; break;
    case 2:
      top.h2_x0=x[0]; top.h2_x1=x[1]; top.h2_x2=x[2]; top.h2_x3=x[3]; top.h2_x4=x[4];
      top.h2_x5=x[5]; top.h2_x6=x[6]; top.h2_x7=x[7]; top.h2_x8=x[8]; top.h2_x9=x[9];
      top.h2_x10=x[10]; top.h2_x11=x[11]; top.h2_x12=x[12]; top.h2_x13=x[13]; top.h2_x14=x[14];
      top.h2_x15=x[15]; top.h2_x16=x[16]; top.h2_x17=x[17]; top.h2_x18=x[18]; top.h2_x19=x[19]; break;
    default:
      top.h3_x0=x[0]; top.h3_x1=x[1]; top.h3_x2=x[2]; top.h3_x3=x[3]; top.h3_x4=x[4];
      top.h3_x5=x[5]; top.h3_x6=x[6]; top.h3_x7=x[7]; top.h3_x8=x[8]; top.h3_x9=x[9];
      top.h3_x10=x[10]; top.h3_x11=x[11]; top.h3_x12=x[12]; top.h3_x13=x[13]; top.h3_x14=x[14];
      top.h3_x15=x[15]; top.h3_x16=x[16]; top.h3_x17=x[17]; top.h3_x18=x[18]; top.h3_x19=x[19]; break;
  }
}

static void read_base(const Vsim& top, uint64_t* y) {
  y[0]=top.h0_y0; y[1]=top.h0_y1; y[2]=top.h0_y2; y[3]=top.h0_y3;
  y[4]=top.h1_y0; y[5]=top.h1_y1; y[6]=top.h1_y2; y[7]=top.h1_y3;
  y[8]=top.h2_y0; y[9]=top.h2_y1; y[10]=top.h2_y2; y[11]=top.h2_y3;
  y[12]=top.h3_y0; y[13]=top.h3_y1; y[14]=top.h3_y2; y[15]=top.h3_y3;
}

static Out compute_cpu(Vsim& top, const In& in, int inner_repeat) {
  for (int h = 0; h < 4; ++h) apply_head(top, &in.x[h * 20], h);
  top.eval();
  Out base{{0}}, out{{0}};
  read_base(top, base.y);
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < 16; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j) & 31);
  return out;
}

static double ms_since(std::chrono::steady_clock::time_point s) {
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s).count();
}

int main(int argc, char** argv) {
  if (argc != 5) return 2;
  int nstates = std::stoi(argv[1]), repeat = std::stoi(argv[2]);
  int inner_repeat = std::stoi(argv[3]), integration_batches = std::stoi(argv[4]);
  std::vector<In> input(nstates); std::vector<Out> cpu(nstates), gpu(nstates);
  fill(input);
  VerilatedContext context; Vsim top(&context);
  double cpu_ms = 0.0, gpu_ms = 0.0, kernel_ms = 0.0;
  uint64_t cpu_checksum = 0, gpu_checksum = 0;
  size_t mismatch_count = 0;
  In* d_input = nullptr; Out* d_output = nullptr; cudaEvent_t ks, ke;
  cudaEventCreate(&ks); cudaEventCreate(&ke); cudaFree(nullptr);
  cudaMalloc(&d_input, input.size() * sizeof(In)); cudaMalloc(&d_output, gpu.size() * sizeof(Out));
  int threads = 256, blocks = (nstates + threads - 1) / threads;
  for (int r = 0; r < repeat; ++r) {
    auto cs = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches; ++b) {
      for (int i = 0; i < nstates; ++i) cpu[i] = compute_cpu(top, input[i], inner_repeat);
      cpu_checksum ^= cpu[(b + r) % nstates].y[(b + r) & 15] + uint64_t(b + r);
    }
    cpu_ms += ms_since(cs);
    auto gs = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches; ++b) {
      cudaMemcpy(d_input, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
      cudaEventRecord(ks); kernel<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
      cudaEventRecord(ke); cudaEventSynchronize(ke);
      float km = 0.0f; cudaEventElapsedTime(&km, ks, ke); kernel_ms += km;
      cudaMemcpy(gpu.data(), d_output, gpu.size() * sizeof(Out), cudaMemcpyDeviceToHost); cudaDeviceSynchronize();
      gpu_checksum ^= gpu[(b + r) % nstates].y[(b + r) & 15] + uint64_t(b + r);
    }
    gpu_ms += ms_since(gs);
  }
  for (int i = 0; i < nstates; ++i)
    for (int j = 0; j < 16; ++j) if (cpu[i].y[j] != gpu[i].y[j]) ++mismatch_count;
  cudaFree(d_input); cudaFree(d_output); cudaEventDestroy(ks); cudaEventDestroy(ke);
  top.final();
  double batches = double(repeat) * double(integration_batches);
  cpu_ms /= batches; gpu_ms /= batches; kernel_ms /= batches;
  bool pass = mismatch_count == 0 && cpu_checksum == gpu_checksum;
  std::cout << "{\"status\":\"" << (pass ? "hls_variant_measured" : "hls_variant_mismatch")
            << "\",\"variant\":\"attention_head4_hls_friendly\",\"nstates\":" << nstates
            << ",\"repeat\":" << repeat << ",\"inner_repeat\":" << inner_repeat
            << ",\"integration_batches\":" << integration_batches
            << ",\"head_count\":4,\"input_bytes\":" << (input.size() * sizeof(In))
            << ",\"output_bytes\":" << (gpu.size() * sizeof(Out))
            << ",\"mismatch_count\":" << mismatch_count
            << ",\"cpu_control_checksum\":" << cpu_checksum
            << ",\"gpu_control_checksum\":" << gpu_checksum
            << ",\"cpu_vs_gpu_output_equal\":" << (mismatch_count == 0 ? "true" : "false")
            << ",\"cpu_vs_gpu_control_checksum_equal\":" << (cpu_checksum == gpu_checksum ? "true" : "false")
            << ",\"cpu_ms\":" << cpu_ms << ",\"gpu_end_to_end_ms\":" << gpu_ms
            << ",\"gpu_kernel_ms\":" << kernel_ms
            << ",\"cpu_to_gpu_end_to_end_speedup\":" << (gpu_ms > 0.0 ? cpu_ms / gpu_ms : 0.0)
            << ",\"cpu_to_gpu_kernel_speedup\":" << (kernel_ms > 0.0 ? cpu_ms / kernel_ms : 0.0)
            << "}\n";
  return pass ? 0 : 1;
}
'''

CUDA_LIB = r'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <vector>

struct In { uint8_t x[80]; };
struct Out { uint64_t y[16]; };

static void fill(std::vector<In>& input) {
  for (size_t i = 0; i < input.size(); ++i)
    for (int j = 0; j < 80; ++j) input[i].x[j] = uint8_t((i * 17u + j * 11u + 1u) & 0x7fu);
}

__host__ __device__ static void eval_head(const uint8_t* x, uint64_t* y) {
  uint64_t score0 = 0, score1 = 0;
  for (int j = 0; j < 4; ++j) {
    score0 += uint64_t(x[j]) * x[4 + j];
    score1 += uint64_t(x[j]) * x[8 + j];
  }
  uint64_t w0 = (score0 + 1) * (score0 + 1);
  uint64_t w1 = (score1 + 1) * (score1 + 1);
  for (int j = 0; j < 4; ++j) y[j] = w0 * x[12 + j] + w1 * x[16 + j];
}

__host__ __device__ static Out compute_gpu(const In& in, int inner_repeat) {
  Out base{{0}}, out{{0}};
  for (int h = 0; h < 4; ++h) eval_head(&in.x[h * 20], &base.y[h * 4]);
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < 16; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j) & 31);
  return out;
}

__global__ static void kernel(const In* input, Out* output, int nstates, int inner_repeat) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < nstates) output[idx] = compute_gpu(input[idx], inner_repeat);
}

static double ms_since(std::chrono::steady_clock::time_point s) {
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s).count();
}

extern "C" int attention_head4_hls_run_gpu_outputs(int nstates, int inner_repeat, Out* out, size_t out_count) {
  if (!out || nstates <= 0 || inner_repeat <= 0 || out_count < static_cast<size_t>(nstates)) return 2;
  std::vector<In> input(nstates); fill(input);
  In* d_input = nullptr; Out* d_output = nullptr;
  cudaError_t err = cudaFree(nullptr);
  if (err == cudaSuccess) err = cudaMalloc(&d_input, input.size() * sizeof(In));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, out_count * sizeof(Out));
  if (err == cudaSuccess) err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
  int threads = 256, blocks = (nstates + threads - 1) / threads;
  if (err == cudaSuccess) { kernel<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat); err = cudaDeviceSynchronize(); }
  if (err == cudaSuccess) err = cudaMemcpy(out, d_output, out_count * sizeof(Out), cudaMemcpyDeviceToHost);
  if (d_input) cudaFree(d_input);
  if (d_output) cudaFree(d_output);
  return err == cudaSuccess ? 0 : 1;
}

extern "C" int attention_head4_hls_run_hybrid_json(
    int nstates, int repeat, int inner_repeat, int integration_batches, char* out_json, size_t out_json_size) {
  if (!out_json || out_json_size == 0 || nstates <= 0 || repeat <= 0 || inner_repeat <= 0 || integration_batches <= 0) return 2;
  std::vector<In> input(nstates); std::vector<Out> gpu(nstates); fill(input);
  In* d_input = nullptr; Out* d_output = nullptr; cudaEvent_t ks, ke;
  cudaEventCreate(&ks); cudaEventCreate(&ke);
  cudaError_t err = cudaFree(nullptr);
  if (err == cudaSuccess) err = cudaMalloc(&d_input, input.size() * sizeof(In));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, gpu.size() * sizeof(Out));
  double gpu_ms = 0.0, kernel_ms = 0.0; uint64_t checksum = 0;
  int threads = 256, blocks = (nstates + threads - 1) / threads;
  for (int r = 0; r < repeat && err == cudaSuccess; ++r) {
    auto gs = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches && err == cudaSuccess; ++b) {
      err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
      if (err == cudaSuccess) {
        cudaEventRecord(ks); kernel<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
        cudaEventRecord(ke); err = cudaEventSynchronize(ke);
      }
      if (err == cudaSuccess) {
        float km = 0.0f; cudaEventElapsedTime(&km, ks, ke); kernel_ms += km;
        err = cudaMemcpy(gpu.data(), d_output, gpu.size() * sizeof(Out), cudaMemcpyDeviceToHost);
      }
      if (err == cudaSuccess) { err = cudaDeviceSynchronize(); checksum ^= gpu[(b + r) % nstates].y[(b + r) & 15] + uint64_t(b + r); }
    }
    gpu_ms += ms_since(gs);
  }
  double batches = double(repeat) * double(integration_batches);
  gpu_ms /= batches; kernel_ms /= batches;
  if (d_input) cudaFree(d_input);
  if (d_output) cudaFree(d_output);
  cudaEventDestroy(ks); cudaEventDestroy(ke);
  std::snprintf(out_json, out_json_size,
      "{\"status\":\"%s\",\"gpu_control_checksum\":%llu,\"gpu_end_to_end_ms\":%.17g,\"gpu_kernel_ms\":%.17g}",
      err == cudaSuccess ? "hybrid_entrypoint_passed" : "hybrid_entrypoint_failed",
      static_cast<unsigned long long>(checksum), gpu_ms, kernel_ms);
  return err == cudaSuccess ? 0 : 1;
}
'''

BRIDGE_CPP = r'''#include "Vsim.h"
#include "verilated.h"
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <vector>

struct In { uint8_t x[80]; };
struct Out { uint64_t y[16]; };
typedef int (*run_outputs_fn)(int, int, Out*, size_t);
typedef int (*run_json_fn)(int, int, int, int, char*, size_t);

static double ms_since(struct timespec s) {
  struct timespec n; clock_gettime(CLOCK_MONOTONIC, &n);
  return double(n.tv_sec - s.tv_sec) * 1000.0 + double(n.tv_nsec - s.tv_nsec) / 1000000.0;
}
static const char* json_value_start(const char* json, const char* key) {
  char pattern[96]; int n = snprintf(pattern, sizeof(pattern), "\"%s\":", key);
  const char* f = n > 0 ? strstr(json, pattern) : nullptr; return f ? f + n : nullptr;
}
static int json_ull(const char* json, const char* key, unsigned long long* out) {
  const char* v = json_value_start(json, key); char* e = nullptr; if (!v) return 0;
  *out = strtoull(v, &e, 10); return e != v;
}
static int json_double(const char* json, const char* key, double* out) {
  const char* v = json_value_start(json, key); char* e = nullptr; if (!v) return 0;
  *out = strtod(v, &e); return e != v;
}
static void fill(std::vector<In>& input) {
  for (size_t i = 0; i < input.size(); ++i)
    for (int j = 0; j < 80; ++j) input[i].x[j] = uint8_t((i * 17u + j * 11u + 1u) & 0x7fu);
}
static void apply_head(Vsim& top, const uint8_t* x, int h) {
#define SET_HEAD(H) top.h##H##_x0=x[0]; top.h##H##_x1=x[1]; top.h##H##_x2=x[2]; top.h##H##_x3=x[3]; top.h##H##_x4=x[4]; top.h##H##_x5=x[5]; top.h##H##_x6=x[6]; top.h##H##_x7=x[7]; top.h##H##_x8=x[8]; top.h##H##_x9=x[9]; top.h##H##_x10=x[10]; top.h##H##_x11=x[11]; top.h##H##_x12=x[12]; top.h##H##_x13=x[13]; top.h##H##_x14=x[14]; top.h##H##_x15=x[15]; top.h##H##_x16=x[16]; top.h##H##_x17=x[17]; top.h##H##_x18=x[18]; top.h##H##_x19=x[19]
  if (h == 0) { SET_HEAD(0); } else if (h == 1) { SET_HEAD(1); } else if (h == 2) { SET_HEAD(2); } else { SET_HEAD(3); }
#undef SET_HEAD
}
static void read_base(const Vsim& top, uint64_t* y) {
  y[0]=top.h0_y0; y[1]=top.h0_y1; y[2]=top.h0_y2; y[3]=top.h0_y3;
  y[4]=top.h1_y0; y[5]=top.h1_y1; y[6]=top.h1_y2; y[7]=top.h1_y3;
  y[8]=top.h2_y0; y[9]=top.h2_y1; y[10]=top.h2_y2; y[11]=top.h2_y3;
  y[12]=top.h3_y0; y[13]=top.h3_y1; y[14]=top.h3_y2; y[15]=top.h3_y3;
}
static Out compute_cpu(Vsim& top, const In& in, int inner_repeat) {
  for (int h = 0; h < 4; ++h) apply_head(top, &in.x[h * 20], h);
  top.eval(); Out base{{0}}, out{{0}}; read_base(top, base.y);
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < 16; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j) & 31);
  return out;
}
int main(int argc, char** argv) {
  if (argc != 6) { printf("{\"status\":\"failed_usage\"}\n"); return 2; }
  int nstates = atoi(argv[2]), repeat = atoi(argv[3]), inner_repeat = atoi(argv[4]), integration_batches = atoi(argv[5]);
  void* handle = dlopen(argv[1], RTLD_NOW);
  if (!handle) { printf("{\"status\":\"failed_dlopen\"}\n"); return 1; }
  auto run_outputs = (run_outputs_fn)dlsym(handle, "attention_head4_hls_run_gpu_outputs");
  auto run_json = (run_json_fn)dlsym(handle, "attention_head4_hls_run_hybrid_json");
  if (!run_outputs || !run_json) { printf("{\"status\":\"failed_dlsym\"}\n"); return 1; }
  std::vector<In> input(nstates); std::vector<Out> cpu(nstates), gpu(nstates); fill(input);
  VerilatedContext context; Vsim top(&context); double cpu_ms = 0.0; uint64_t cpu_checksum = 0;
  for (int r = 0; r < repeat; ++r) {
    struct timespec cs; clock_gettime(CLOCK_MONOTONIC, &cs);
    for (int b = 0; b < integration_batches; ++b) {
      for (int i = 0; i < nstates; ++i) cpu[i] = compute_cpu(top, input[i], inner_repeat);
      cpu_checksum ^= cpu[(b + r) % nstates].y[(b + r) & 15] + uint64_t(b + r);
    }
    cpu_ms += ms_since(cs);
  }
  double batches = double(repeat) * double(integration_batches); cpu_ms /= batches;
  int out_rc = run_outputs(nstates, inner_repeat, gpu.data(), gpu.size());
  if (out_rc != 0) { printf("{\"status\":\"failed_gpu_outputs\"}\n"); return 1; }
  size_t mismatch_count = 0;
  for (int i = 0; i < nstates; ++i) for (int j = 0; j < 16; ++j) if (cpu[i].y[j] != gpu[i].y[j]) ++mismatch_count;
  char hybrid_json[4096]; struct timespec hs; clock_gettime(CLOCK_MONOTONIC, &hs);
  int json_rc = run_json(nstates, repeat, inner_repeat, integration_batches, hybrid_json, sizeof(hybrid_json));
  double bridge_wall_ms = ms_since(hs); dlclose(handle); top.final();
  if (json_rc != 0) { printf("{\"status\":\"failed_hybrid_json\"}\n"); return 1; }
  unsigned long long gpu_checksum = 0; double gpu_ms = 0.0, kernel_ms = 0.0;
  int parsed = json_ull(hybrid_json, "gpu_control_checksum", &gpu_checksum) &&
      json_double(hybrid_json, "gpu_end_to_end_ms", &gpu_ms) && json_double(hybrid_json, "gpu_kernel_ms", &kernel_ms);
  if (!parsed) { printf("{\"status\":\"failed_parse_hybrid_json\"}\n"); return 1; }
  bool pass = mismatch_count == 0 && cpu_checksum == uint64_t(gpu_checksum);
  printf("{\"status\":\"%s\",\"variant\":\"attention_head4_hls_friendly\",\"nstates\":%d,\"repeat\":%d,\"inner_repeat\":%d,\"integration_batches\":%d,\"head_count\":4,\"input_bytes\":%zu,\"output_bytes\":%zu,\"mismatch_count\":%zu,\"cpu_control_checksum\":%llu,\"gpu_control_checksum\":%llu,\"cpu_vs_gpu_output_equal\":%s,\"cpu_vs_gpu_control_checksum_equal\":%s,\"cpu_ms\":%.17g,\"gpu_end_to_end_ms\":%.17g,\"gpu_kernel_ms\":%.17g,\"bridge_hybrid_wall_ms\":%.17g,\"bridge_hybrid_wall_ms_per_integration_batch\":%.17g,\"cpu_to_gpu_end_to_end_speedup\":%.17g,\"cpu_to_gpu_kernel_speedup\":%.17g,\"cpu_to_bridge_hybrid_wall_speedup\":%.17g}\n",
    pass ? "hls_variant_measured" : "hls_variant_mismatch", nstates, repeat, inner_repeat, integration_batches,
    input.size() * sizeof(In), gpu.size() * sizeof(Out), mismatch_count, static_cast<unsigned long long>(cpu_checksum), gpu_checksum,
    mismatch_count == 0 ? "true" : "false", cpu_checksum == uint64_t(gpu_checksum) ? "true" : "false",
    cpu_ms, gpu_ms, kernel_ms, bridge_wall_ms, bridge_wall_ms / batches,
    gpu_ms > 0.0 ? cpu_ms / gpu_ms : 0.0, kernel_ms > 0.0 ? cpu_ms / kernel_ms : 0.0,
    (bridge_wall_ms / batches) > 0.0 ? cpu_ms / (bridge_wall_ms / batches) : 0.0);
  return pass ? 0 : 1;
}
'''


def _load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "report": _display_path(path),
        "status": payload.get("status"),
        "candidate": payload.get("candidate"),
        "shape": payload.get("shape"),
        "cpu_to_bridge_hybrid_wall_speedup": payload.get("cpu_to_bridge_hybrid_wall_speedup"),
        "cpu_ms": (payload.get("adapter_average") or {}).get("cpu_ms"),
        "gpu_end_to_end_ms": (payload.get("adapter_average") or {}).get("gpu_end_to_end_ms"),
        "gpu_kernel_ms": (payload.get("adapter_average") or {}).get("gpu_kernel_ms"),
    }


def materialize_and_measure(
    *,
    shape: str = "1024x1",
    repeat: int = 5,
    inner_repeat: int = 1000,
    integration_batches: int = 15,
    out_dir: Path = OUT_DIR,
    baseline_report: Path = BASELINE_REPORT,
) -> dict[str, Any]:
    nstates, steps = _shape(shape)
    if steps != 1:
        raise ValueError("attention_head4_hls_friendly currently supports Nx1 shapes")
    out_dir.mkdir(parents=True, exist_ok=True)
    fir = out_dir / "attention_head4_hls_friendly.fir"
    sv = out_dir / "attention_head4_hls_friendly.sv"
    probe = out_dir / "tb_attention_head4_hls_friendly.cpp"
    cu = out_dir / "attention_head4_hls_friendly_gpu.cu"
    bridge = out_dir / "attention_head4_hls_friendly_bridge.cpp"
    obj = out_dir / "obj_dir"
    gpu_library = out_dir / "libattention_head4_hls_friendly_gpu.so"
    binary = out_dir / "attention_head4_hls_friendly_direct"
    fir.write_text(_firrtl(), encoding="utf-8")
    probe.write_text(PROBE, encoding="utf-8")
    cu.write_text(CUDA_LIB, encoding="utf-8")
    bridge.write_text(BRIDGE_CPP, encoding="utf-8")
    verilator_root, root_command = _verilator_root_command()
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_hls_attention_head_variant",
        "candidate": "microgpt_attention_head",
        "variant": "attention_head4_hls_friendly",
        "source_variant_strategy": "explicit_four_independent_attention_heads_per_state_to_increase_arithmetic_intensity",
        "shape": shape,
        "head_count": 4,
        "repeat": repeat,
        "inner_repeat": inner_repeat,
        "integration_batches": integration_batches,
        "artifacts": {
            "firrtl": _display_path(fir),
            "systemverilog": _display_path(sv),
            "verilator_mdir": _display_path(obj),
            "gpu_library_source": _display_path(cu),
            "gpu_library": _display_path(gpu_library),
            "direct_callsite_bridge_source": _display_path(bridge),
            "direct_callsite_binary": _display_path(binary),
        },
        "baseline": _load_baseline(baseline_report),
        "commands": [],
        "toolchain": {
            "firtool": _tool("firtool") is not None,
            "verilator": _tool("verilator") is not None,
            "nvcc": _tool("nvcc") is not None,
        },
        "non_claims": [
            "not_full_microgpt_execution",
            "not_full_attention_implementation",
            "not_automatic_hls_rewrite",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
            "not_production_runtime_entrypoint",
        ],
    }
    if root_command is not None:
        report["commands"].append({"stage": "resolve_verilator_root", **root_command})
    if verilator_root is None:
        report["status"] = "failed_missing_verilator_root"
        return report
    stages = [
        ("firtool", [_tool("firtool") or "firtool", fir.as_posix(), "-o", sv.as_posix()]),
        (
            "verilator_build",
            [
                _tool("verilator") or "verilator",
                "--cc",
                "--exe",
                "--timing",
                "-Wno-fatal",
                "--prefix",
                "Vsim",
                "--top-module",
                "MicrogptAttentionHeadHls4",
                "-Mdir",
                obj.as_posix(),
                sv.as_posix(),
                probe.as_posix(),
                "--build",
            ],
        ),
        (
            "nvcc_gpu_library_build",
            [
                _tool("nvcc") or "nvcc",
                "-O3",
                "--std=c++17",
                "-shared",
                "-Xcompiler",
                "-fPIC",
                cu.as_posix(),
                "-o",
                gpu_library.as_posix(),
            ],
        ),
        (
            "cxx_direct_callsite_build",
            [
                os.environ.get("CXX", "g++"),
                "-O3",
                "-std=c++17",
                bridge.as_posix(),
                "-I",
                obj.as_posix(),
                "-I",
                (verilator_root / "include").as_posix(),
                "-I",
                (verilator_root / "include" / "vltstd").as_posix(),
                (obj / "Vsim__ALL.a").as_posix(),
                (obj / "verilated.o").as_posix(),
                (obj / "verilated_threads.o").as_posix(),
                "-ldl",
                "-pthread",
                "-o",
                binary.as_posix(),
            ],
        ),
        (
            "direct_callsite_run",
            [
                binary.as_posix(),
                gpu_library.as_posix(),
                str(nstates),
                str(repeat),
                str(inner_repeat),
                str(integration_batches),
            ],
        ),
    ]
    for stage, command in stages:
        result = _run(command)
        report["commands"].append({"stage": stage, **result})
        if result["returncode"] != 0:
            report["status"] = f"failed_{stage}"
            return report
    observed = json.loads(report["commands"][-1]["stdout"])
    baseline = report["baseline"] or {}
    baseline_speedup = baseline.get("cpu_to_bridge_hybrid_wall_speedup")
    variant_speedup = observed.get("cpu_to_bridge_hybrid_wall_speedup")
    variant_gpu_end_to_end_speedup = observed.get("cpu_to_gpu_end_to_end_speedup")
    speedup_delta = (
        variant_speedup - baseline_speedup
        if isinstance(variant_speedup, int | float) and isinstance(baseline_speedup, int | float)
        else None
    )
    report.update(
        {
            "status": "hls_variant_improved" if observed.get("status") == "hls_variant_measured" and speedup_delta is not None and speedup_delta > 0.0 else "hls_variant_measured_no_speedup_improvement",
            "observed": observed,
            "cpu_vs_gpu_output_equal": observed.get("cpu_vs_gpu_output_equal") is True,
            "cpu_vs_gpu_control_checksum_equal": observed.get("cpu_vs_gpu_control_checksum_equal") is True,
            "lowering_evidence": {
                "firrtl_to_systemverilog": True,
                "verilator_build": True,
                "gpu_library_build": True,
                "direct_callsite_bridge_build": True,
                "direct_callsite_run": True,
            },
            "comparison": {
                "baseline_speedup": baseline_speedup,
                "variant_speedup": variant_speedup,
                "variant_gpu_end_to_end_speedup": variant_gpu_end_to_end_speedup,
                "speedup_delta": speedup_delta,
                "speedup_improved": speedup_delta is not None and speedup_delta > 0.0,
                "baseline_cpu_ms": baseline.get("cpu_ms"),
                "variant_cpu_ms": observed.get("cpu_ms"),
                "baseline_gpu_end_to_end_ms": baseline.get("gpu_end_to_end_ms"),
                "variant_gpu_end_to_end_ms": observed.get("gpu_end_to_end_ms"),
            },
        }
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", default="1024x1")
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--inner-repeat", type=int, default=1000)
    parser.add_argument("--integration-batches", type=int, default=15)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--baseline-report", type=Path, default=BASELINE_REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = materialize_and_measure(
            shape=args.shape,
            repeat=args.repeat,
            inner_repeat=args.inner_repeat,
            integration_batches=args.integration_batches,
            out_dir=args.out_dir,
            baseline_report=args.baseline_report,
        )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {"hls_variant_improved", "hls_variant_measured_no_speedup_improvement"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
