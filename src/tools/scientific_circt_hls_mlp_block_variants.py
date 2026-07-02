#!/usr/bin/env python3
"""Measure HLS-friendly MLP/block source variants through Verilator callsites."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OUT_DIR = Path("artifacts/scientific_circt/hls_mlp_block_variants")
REPORT = Path("reports/scientific_circt_hls_mlp_block_variants.json")
REPO_FIRTOOL = Path("artifacts/toolchains/circt-firtool-1.149.0/firtool-1.149.0/bin/firtool")


@dataclass(frozen=True)
class Variant:
    name: str
    candidate: str
    kind: str
    module: str
    units: int
    inputs_per_unit: int
    outputs_per_unit: int
    baseline_report: Path
    strategy: str
    fill_a: int
    fill_b: int
    fill_c: int
    fill_mask: int
    non_claims: tuple[str, ...]


VARIANTS = {
    "mlp4_hls_friendly": Variant(
        name="mlp4_hls_friendly",
        candidate="microgpt_mlp_slice",
        kind="mlp",
        module="MicrogptMlpHls4",
        units=4,
        inputs_per_unit=4,
        outputs_per_unit=2,
        baseline_report=Path("reports/scientific_circt_microgpt_mlp_slice_1024x1.json"),
        strategy="four_independent_mlp_slices_per_state_to_increase_arithmetic_intensity",
        fill_a=31,
        fill_b=17,
        fill_c=3,
        fill_mask=0xFF,
        non_claims=("not_full_microgpt_execution", "not_full_mlp_width", "not_automatic_hls_rewrite"),
    ),
    "block2_hls_friendly": Variant(
        name="block2_hls_friendly",
        candidate="microgpt_block_slice",
        kind="block",
        module="MicrogptBlockHls2",
        units=2,
        inputs_per_unit=12,
        outputs_per_unit=2,
        baseline_report=Path("reports/scientific_circt_microgpt_block_slice_1024x1.json"),
        strategy="two_independent_block_slices_per_state_to_increase_arithmetic_intensity",
        fill_a=23,
        fill_b=17,
        fill_c=5,
        fill_mask=0x7F,
        non_claims=("not_full_microgpt_execution", "not_full_block_size_sequence", "not_automatic_hls_rewrite"),
    ),
    "inference2_hls_friendly": Variant(
        name="inference2_hls_friendly",
        candidate="microgpt_inference_slice",
        kind="inference",
        module="MicrogptInferenceHls2",
        units=2,
        inputs_per_unit=4,
        outputs_per_unit=3,
        baseline_report=Path("reports/scientific_circt_microgpt_inference_slice_1024x1.json"),
        strategy="two_independent_two_token_inference_slices_per_state_to_probe_whole_slice_reshaping",
        fill_a=17,
        fill_b=23,
        fill_c=7,
        fill_mask=0x3F,
        non_claims=("not_full_microgpt_execution", "not_full_block_size_sequence", "not_training_or_autograd", "not_automatic_hls_rewrite"),
    ),
}


def _sanitize(text: str) -> str:
    text = text.replace(Path.cwd().as_posix(), "<repo>")
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


def _tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if name == "firtool" and REPO_FIRTOOL.exists():
        return REPO_FIRTOOL.as_posix()
    return None


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


def _mlp_nodes(prefix: str) -> list[str]:
    return [
        f"    node {prefix}_h0sum_a = add(mul({prefix}_x0, UInt<4>(3)), mul({prefix}_x1, UInt<4>(5)))",
        f"    node {prefix}_h0sum_b = add(mul({prefix}_x2, UInt<4>(7)), mul({prefix}_x3, UInt<4>(11)))",
        f"    node {prefix}_h0sum = add({prefix}_h0sum_a, {prefix}_h0sum_b)",
        f"    node {prefix}_h0 = mux(gt({prefix}_h0sum, UInt<16>(900)), sub({prefix}_h0sum, UInt<16>(900)), UInt<16>(0))",
        f"    node {prefix}_h1sum_a = add(mul({prefix}_x0, UInt<4>(13)), mul({prefix}_x1, UInt<4>(2)))",
        f"    node {prefix}_h1sum_b = add(mul({prefix}_x2, UInt<4>(5)), mul({prefix}_x3, UInt<4>(3)))",
        f"    node {prefix}_h1sum = add({prefix}_h1sum_a, {prefix}_h1sum_b)",
        f"    node {prefix}_h1 = mux(gt({prefix}_h1sum, UInt<16>(1100)), sub({prefix}_h1sum, UInt<16>(1100)), UInt<16>(0))",
        f"    node {prefix}_h2sum_a = add(mul({prefix}_x0, UInt<4>(2)), mul({prefix}_x1, UInt<5>(17)))",
        f"    node {prefix}_h2sum_b = add(mul({prefix}_x2, UInt<4>(3)), mul({prefix}_x3, UInt<4>(5)))",
        f"    node {prefix}_h2sum = add({prefix}_h2sum_a, {prefix}_h2sum_b)",
        f"    node {prefix}_h2 = mux(gt({prefix}_h2sum, UInt<16>(1300)), sub({prefix}_h2sum, UInt<16>(1300)), UInt<16>(0))",
        f"    node {prefix}_h3sum_a = add(mul({prefix}_x0, UInt<4>(11)), mul({prefix}_x1, UInt<4>(7)))",
        f"    node {prefix}_h3sum_b = add(mul({prefix}_x2, UInt<4>(13)), mul({prefix}_x3, UInt<4>(2)))",
        f"    node {prefix}_h3sum = add({prefix}_h3sum_a, {prefix}_h3sum_b)",
        f"    node {prefix}_h3 = mux(gt({prefix}_h3sum, UInt<16>(1500)), sub({prefix}_h3sum, UInt<16>(1500)), UInt<16>(0))",
        f"    node {prefix}_y0a = add(mul({prefix}_h0, UInt<5>(19)), mul({prefix}_h1, UInt<5>(23)))",
        f"    node {prefix}_y0b = add(mul({prefix}_h2, UInt<5>(29)), mul({prefix}_h3, UInt<5>(31)))",
        f"    node {prefix}_y1a = add(mul({prefix}_h0, UInt<5>(7)), mul({prefix}_h1, UInt<5>(17)))",
        f"    node {prefix}_y1b = add(mul({prefix}_h2, UInt<5>(11)), mul({prefix}_h3, UInt<5>(13)))",
        f"    connect {prefix}_y0, add({prefix}_y0a, {prefix}_y0b)",
        f"    connect {prefix}_y1, add({prefix}_y1a, {prefix}_y1b)",
    ]


def _block_nodes(prefix: str) -> list[str]:
    names = ["x0", "x1", "x2", "x3", "k00", "k01", "k10", "k11", "v00", "v01", "v10", "v11"]
    p = {name: f"{prefix}_{name}" for name in names}
    return [
        f"    node {prefix}_score0 = add(mul({p['x0']}, {p['k00']}), mul({p['x1']}, {p['k01']}))",
        f"    node {prefix}_score1 = add(mul({p['x0']}, {p['k10']}), mul({p['x1']}, {p['k11']}))",
        f"    node {prefix}_w0s = add({prefix}_score0, UInt<18>(1))",
        f"    node {prefix}_w1s = add({prefix}_score1, UInt<18>(1))",
        f"    node {prefix}_w0 = mul({prefix}_w0s, {prefix}_w0s)",
        f"    node {prefix}_w1 = mul({prefix}_w1s, {prefix}_w1s)",
        f"    node {prefix}_att0 = add(mul({prefix}_w0, {p['v00']}), mul({prefix}_w1, {p['v10']}))",
        f"    node {prefix}_att1 = add(mul({prefix}_w0, {p['v01']}), mul({prefix}_w1, {p['v11']}))",
        f"    node {prefix}_r0 = add({prefix}_att0, {p['x0']})",
        f"    node {prefix}_r1 = add({prefix}_att1, {p['x1']})",
        f"    node {prefix}_r2 = add(mul({p['x2']}, UInt<6>(37)), UInt<14>(101))",
        f"    node {prefix}_r3 = add(mul({p['x3']}, UInt<6>(41)), UInt<14>(103))",
        f"    node {prefix}_h0sum = add(add(mul({prefix}_r0, UInt<5>(3)), mul({prefix}_r1, UInt<5>(5))), add(mul({prefix}_r2, UInt<5>(7)), mul({prefix}_r3, UInt<5>(11))))",
        f"    node {prefix}_h1sum = add(add(mul({prefix}_r0, UInt<5>(13)), mul({prefix}_r1, UInt<5>(17))), add(mul({prefix}_r2, UInt<5>(19)), mul({prefix}_r3, UInt<5>(23))))",
        f"    node {prefix}_h0 = mux(gt({prefix}_h0sum, UInt<64>(4096)), sub({prefix}_h0sum, UInt<64>(4096)), UInt<64>(0))",
        f"    node {prefix}_h1 = mux(gt({prefix}_h1sum, UInt<64>(8192)), sub({prefix}_h1sum, UInt<64>(8192)), UInt<64>(0))",
        f"    connect {prefix}_y0, add(mul({prefix}_h0, UInt<6>(29)), mul({prefix}_h1, UInt<6>(31)))",
        f"    connect {prefix}_y1, add(mul({prefix}_h0, UInt<6>(37)), mul({prefix}_h1, UInt<6>(43)))",
    ]


def _inference_nodes(prefix: str) -> list[str]:
    p = {name: f"{prefix}_{name}" for name in ["tok0", "pos0", "tok1", "pos1"]}
    return [
        f"    node {prefix}_x00 = add(add(mul({p['tok0']}, UInt<5>(3)), mul({p['pos0']}, UInt<5>(5))), UInt<8>(7))",
        f"    node {prefix}_x01 = add(add(mul({p['tok0']}, UInt<5>(11)), mul({p['pos0']}, UInt<5>(13))), UInt<8>(17))",
        f"    node {prefix}_x10 = add(add(mul({p['tok1']}, UInt<5>(19)), mul({p['pos1']}, UInt<5>(23))), UInt<8>(29))",
        f"    node {prefix}_x11 = add(add(mul({p['tok1']}, UInt<5>(31)), mul({p['pos1']}, UInt<6>(37))), UInt<8>(41))",
        f"    node {prefix}_k00 = add(mul({prefix}_x00, UInt<4>(3)), mul({prefix}_x01, UInt<4>(5)))",
        f"    node {prefix}_k01 = add(mul({prefix}_x00, UInt<4>(7)), mul({prefix}_x01, UInt<4>(11)))",
        f"    node {prefix}_v00 = add(mul({prefix}_x00, UInt<5>(13)), mul({prefix}_x01, UInt<5>(17)))",
        f"    node {prefix}_v01 = add(mul({prefix}_x00, UInt<5>(19)), mul({prefix}_x01, UInt<5>(23)))",
        f"    node {prefix}_k10 = add(mul({prefix}_x10, UInt<5>(29)), mul({prefix}_x11, UInt<5>(31)))",
        f"    node {prefix}_k11 = add(mul({prefix}_x10, UInt<6>(37)), mul({prefix}_x11, UInt<6>(41)))",
        f"    node {prefix}_v10 = add(mul({prefix}_x10, UInt<6>(43)), mul({prefix}_x11, UInt<6>(47)))",
        f"    node {prefix}_v11 = add(mul({prefix}_x10, UInt<6>(53)), mul({prefix}_x11, UInt<6>(59)))",
        f"    node {prefix}_q10 = add(mul({prefix}_x10, UInt<5>(17)), mul({prefix}_x11, UInt<5>(19)))",
        f"    node {prefix}_q11 = add(mul({prefix}_x10, UInt<5>(23)), mul({prefix}_x11, UInt<5>(29)))",
        f"    node {prefix}_score0 = add(mul({prefix}_q10, {prefix}_k00), mul({prefix}_q11, {prefix}_k01))",
        f"    node {prefix}_score1 = add(mul({prefix}_q10, {prefix}_k10), mul({prefix}_q11, {prefix}_k11))",
        f"    node {prefix}_w0s = add({prefix}_score0, UInt<28>(1))",
        f"    node {prefix}_w1s = add({prefix}_score1, UInt<28>(1))",
        f"    node {prefix}_w0 = mul({prefix}_w0s, {prefix}_w0s)",
        f"    node {prefix}_w1 = mul({prefix}_w1s, {prefix}_w1s)",
        f"    node {prefix}_att0 = add(mul({prefix}_w0, {prefix}_v00), mul({prefix}_w1, {prefix}_v10))",
        f"    node {prefix}_att1 = add(mul({prefix}_w0, {prefix}_v01), mul({prefix}_w1, {prefix}_v11))",
        f"    node {prefix}_r0 = add({prefix}_att0, {prefix}_x10)",
        f"    node {prefix}_r1 = add({prefix}_att1, {prefix}_x11)",
        f"    node {prefix}_h0sum = add(add(mul({prefix}_r0, UInt<4>(3)), mul({prefix}_r1, UInt<4>(5))), UInt<12>(409))",
        f"    node {prefix}_h1sum = add(add(mul({prefix}_r0, UInt<4>(7)), mul({prefix}_r1, UInt<4>(11))), UInt<12>(853))",
        f"    node {prefix}_h0 = mux(gt({prefix}_h0sum, UInt<64>(8192)), sub({prefix}_h0sum, UInt<64>(8192)), UInt<64>(0))",
        f"    node {prefix}_h1 = mux(gt({prefix}_h1sum, UInt<64>(16384)), sub({prefix}_h1sum, UInt<64>(16384)), UInt<64>(0))",
        f"    connect {prefix}_y0, add(mul({prefix}_h0, UInt<6>(31)), mul({prefix}_h1, UInt<6>(37)))",
        f"    connect {prefix}_y1, add(mul({prefix}_h0, UInt<6>(41)), mul({prefix}_h1, UInt<6>(43)))",
        f"    connect {prefix}_y2, add(add({prefix}_k00, {prefix}_k01), add(add({prefix}_v00, {prefix}_v01), add({prefix}_k10, {prefix}_v10)))",
    ]


def firrtl(variant: Variant) -> str:
    lines = ["FIRRTL version 4.0.0", f"circuit {variant.module} :", f"  public module {variant.module} :"]
    if variant.kind == "mlp":
        for unit in range(variant.units):
            for idx in range(4):
                lines.append(f"    input m{unit}_x{idx} : UInt<8>")
            lines.append(f"    output m{unit}_y0 : UInt<48>")
            lines.append(f"    output m{unit}_y1 : UInt<48>")
        for unit in range(variant.units):
            lines.append("")
            lines.extend(_mlp_nodes(f"m{unit}"))
    elif variant.kind == "block":
        names = ["x0", "x1", "x2", "x3", "k00", "k01", "k10", "k11", "v00", "v01", "v10", "v11"]
        for unit in range(variant.units):
            for name in names:
                lines.append(f"    input b{unit}_{name} : UInt<8>")
            lines.append(f"    output b{unit}_y0 : UInt<64>")
            lines.append(f"    output b{unit}_y1 : UInt<64>")
        for unit in range(variant.units):
            lines.append("")
            lines.extend(_block_nodes(f"b{unit}"))
    else:
        names = ["tok0", "pos0", "tok1", "pos1"]
        for unit in range(variant.units):
            for name in names:
                lines.append(f"    input i{unit}_{name} : UInt<8>")
            for out in range(3):
                lines.append(f"    output i{unit}_y{out} : UInt<64>")
        for unit in range(variant.units):
            lines.append("")
            lines.extend(_inference_nodes(f"i{unit}"))
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


def _eval_unit_cpp(variant: Variant) -> str:
    if variant.kind == "mlp":
        return r'''
__host__ __device__ static uint64_t relu_sub(uint64_t value, uint64_t bias) { return value > bias ? value - bias : 0; }
__host__ __device__ static void eval_unit(const uint8_t* x, uint64_t* y) {
  uint64_t h0 = relu_sub(uint64_t(x[0])*3 + uint64_t(x[1])*5 + uint64_t(x[2])*7 + uint64_t(x[3])*11, 900);
  uint64_t h1 = relu_sub(uint64_t(x[0])*13 + uint64_t(x[1])*2 + uint64_t(x[2])*5 + uint64_t(x[3])*3, 1100);
  uint64_t h2 = relu_sub(uint64_t(x[0])*2 + uint64_t(x[1])*17 + uint64_t(x[2])*3 + uint64_t(x[3])*5, 1300);
  uint64_t h3 = relu_sub(uint64_t(x[0])*11 + uint64_t(x[1])*7 + uint64_t(x[2])*13 + uint64_t(x[3])*2, 1500);
  y[0] = h0*19 + h1*23 + h2*29 + h3*31;
  y[1] = h0*7 + h1*17 + h2*11 + h3*13;
}
'''
    if variant.kind == "block":
        return r'''
__host__ __device__ static uint64_t relu_sub(uint64_t value, uint64_t bias) { return value > bias ? value - bias : 0; }
__host__ __device__ static void eval_unit(const uint8_t* x, uint64_t* y) {
  uint64_t score0 = uint64_t(x[0])*x[4] + uint64_t(x[1])*x[5];
  uint64_t score1 = uint64_t(x[0])*x[6] + uint64_t(x[1])*x[7];
  uint64_t w0 = (score0 + 1) * (score0 + 1);
  uint64_t w1 = (score1 + 1) * (score1 + 1);
  uint64_t r0 = w0 * x[8] + w1 * x[10] + x[0];
  uint64_t r1 = w0 * x[9] + w1 * x[11] + x[1];
  uint64_t r2 = uint64_t(x[2]) * 37 + 101;
  uint64_t r3 = uint64_t(x[3]) * 41 + 103;
  uint64_t h0 = relu_sub(r0*3 + r1*5 + r2*7 + r3*11, 4096);
  uint64_t h1 = relu_sub(r0*13 + r1*17 + r2*19 + r3*23, 8192);
  y[0] = h0*29 + h1*31;
  y[1] = h0*37 + h1*43;
}
'''
    return r'''
__host__ __device__ static uint64_t relu_sub(uint64_t value, uint64_t bias) { return value > bias ? value - bias : 0; }
__host__ __device__ static void eval_unit(const uint8_t* x, uint64_t* y) {
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
  y[0] = h0*31 + h1*37;
  y[1] = h0*41 + h1*43;
  y[2] = k00 + k01 + v00 + v01 + k10 + v10;
}
'''


def cuda_lib(variant: Variant) -> str:
    in_count = variant.units * variant.inputs_per_unit
    out_count = variant.units * variant.outputs_per_unit
    symbol = variant.name
    return f'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <vector>

struct In {{ uint8_t x[{in_count}]; }};
struct Out {{ uint64_t y[{out_count}]; }};

static void fill(std::vector<In>& input) {{
  for (size_t i = 0; i < input.size(); ++i)
    for (int j = 0; j < {in_count}; ++j) input[i].x[j] = uint8_t((i * {variant.fill_a}u + j * {variant.fill_b}u + {variant.fill_c}u) & {variant.fill_mask}u);
}}

{_eval_unit_cpp(variant)}

__host__ __device__ static Out compute_gpu(const In& in, int inner_repeat) {{
  Out base{{{{0}}}}, out{{{{0}}}};
  for (int u = 0; u < {variant.units}; ++u) eval_unit(&in.x[u * {variant.inputs_per_unit}], &base.y[u * {variant.outputs_per_unit}]);
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < {out_count}; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j * 3) & 255);
  return out;
}}

__global__ static void kernel(const In* input, Out* output, int nstates, int inner_repeat) {{
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < nstates) output[idx] = compute_gpu(input[idx], inner_repeat);
}}

static double ms_since(std::chrono::steady_clock::time_point s) {{
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s).count();
}}

extern "C" int {symbol}_run_gpu_outputs(int nstates, int inner_repeat, Out* out, size_t out_count) {{
  if (!out || nstates <= 0 || inner_repeat <= 0 || out_count < static_cast<size_t>(nstates)) return 2;
  std::vector<In> input(nstates); fill(input);
  In* d_input = nullptr; Out* d_output = nullptr; cudaError_t err = cudaFree(nullptr);
  if (err == cudaSuccess) err = cudaMalloc(&d_input, input.size() * sizeof(In));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, out_count * sizeof(Out));
  if (err == cudaSuccess) err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
  int threads = 256, blocks = (nstates + threads - 1) / threads;
  if (err == cudaSuccess) {{ kernel<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat); err = cudaDeviceSynchronize(); }}
  if (err == cudaSuccess) err = cudaMemcpy(out, d_output, out_count * sizeof(Out), cudaMemcpyDeviceToHost);
  if (d_input) cudaFree(d_input); if (d_output) cudaFree(d_output);
  return err == cudaSuccess ? 0 : 1;
}}

extern "C" int {symbol}_run_hybrid_json(int nstates, int repeat, int inner_repeat, int integration_batches, char* out_json, size_t out_json_size) {{
  if (!out_json || out_json_size == 0 || nstates <= 0 || repeat <= 0 || inner_repeat <= 0 || integration_batches <= 0) return 2;
  std::vector<In> input(nstates); std::vector<Out> gpu(nstates); fill(input);
  In* d_input = nullptr; Out* d_output = nullptr; cudaEvent_t ks, ke; cudaEventCreate(&ks); cudaEventCreate(&ke);
  cudaError_t err = cudaFree(nullptr);
  if (err == cudaSuccess) err = cudaMalloc(&d_input, input.size() * sizeof(In));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, gpu.size() * sizeof(Out));
  double gpu_ms = 0.0, kernel_ms = 0.0; uint64_t checksum = 0;
  int threads = 256, blocks = (nstates + threads - 1) / threads;
  for (int r = 0; r < repeat && err == cudaSuccess; ++r) {{
    auto gs = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches && err == cudaSuccess; ++b) {{
      err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
      if (err == cudaSuccess) {{ cudaEventRecord(ks); kernel<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat); cudaEventRecord(ke); err = cudaEventSynchronize(ke); }}
      if (err == cudaSuccess) {{ float km = 0.0f; cudaEventElapsedTime(&km, ks, ke); kernel_ms += km; err = cudaMemcpy(gpu.data(), d_output, gpu.size() * sizeof(Out), cudaMemcpyDeviceToHost); }}
      if (err == cudaSuccess) {{ err = cudaDeviceSynchronize(); checksum ^= gpu[(b + r) % nstates].y[(b + r) % {out_count}] + uint64_t(b + r); }}
    }}
    gpu_ms += ms_since(gs);
  }}
  double batches = double(repeat) * double(integration_batches); gpu_ms /= batches; kernel_ms /= batches;
  if (d_input) cudaFree(d_input); if (d_output) cudaFree(d_output); cudaEventDestroy(ks); cudaEventDestroy(ke);
  std::snprintf(out_json, out_json_size, "{{\\"status\\":\\"%s\\",\\"gpu_control_checksum\\":%llu,\\"gpu_end_to_end_ms\\":%.17g,\\"gpu_kernel_ms\\":%.17g}}",
      err == cudaSuccess ? "hybrid_entrypoint_passed" : "hybrid_entrypoint_failed", static_cast<unsigned long long>(checksum), gpu_ms, kernel_ms);
  return err == cudaSuccess ? 0 : 1;
}}
'''


def input_port_names(variant: Variant) -> tuple[str, ...]:
    """Return input port names in struct-field order (index k <-> in.x[k])."""
    if variant.kind == "mlp":
        return tuple(f"m{u}_x{i}" for u in range(variant.units) for i in range(4))
    if variant.kind == "block":
        names = ["x0", "x1", "x2", "x3", "k00", "k01", "k10", "k11", "v00", "v01", "v10", "v11"]
        return tuple(f"b{u}_{name}" for u in range(variant.units) for name in names)
    names = ["tok0", "pos0", "tok1", "pos1"]
    return tuple(f"i{u}_{name}" for u in range(variant.units) for name in names)


def output_port_names(variant: Variant) -> tuple[str, ...]:
    """Return output port names in struct-field order (index k <-> base.y[k])."""
    if variant.kind == "mlp":
        return tuple(f"m{u}_y{j}" for u in range(variant.units) for j in range(2))
    if variant.kind == "block":
        return tuple(f"b{u}_y{j}" for u in range(variant.units) for j in range(2))
    return tuple(f"i{u}_y{j}" for u in range(variant.units) for j in range(3))


def _bridge_assignments(variant: Variant) -> str:
    return "\n".join(f"  top.{port} = in.x[{k}];" for k, port in enumerate(input_port_names(variant)))


def _bridge_reads(variant: Variant) -> str:
    ports = output_port_names(variant)
    lines: list[str] = []
    for u in range(variant.units):
        start = u * variant.outputs_per_unit
        assignments = " ".join(
            f"base.y[{start + j}] = top.{ports[start + j]};" for j in range(variant.outputs_per_unit)
        )
        lines.append(f"  {assignments}")
    return "\n".join(lines)


def bridge_cpp(variant: Variant) -> str:
    in_count = variant.units * variant.inputs_per_unit
    out_count = variant.units * variant.outputs_per_unit
    symbol = variant.name
    return f'''#include "Vsim.h"
#include "verilated.h"
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <vector>

struct In {{ uint8_t x[{in_count}]; }};
struct Out {{ uint64_t y[{out_count}]; }};
typedef int (*run_outputs_fn)(int, int, Out*, size_t);
typedef int (*run_json_fn)(int, int, int, int, char*, size_t);

static double ms_since(struct timespec s) {{
  struct timespec n; clock_gettime(CLOCK_MONOTONIC, &n);
  return double(n.tv_sec - s.tv_sec) * 1000.0 + double(n.tv_nsec - s.tv_nsec) / 1000000.0;
}}
static const char* json_value_start(const char* json, const char* key) {{
  char pattern[96]; int n = snprintf(pattern, sizeof(pattern), "\\"%s\\":", key);
  const char* f = n > 0 ? strstr(json, pattern) : nullptr; return f ? f + n : nullptr;
}}
static int json_ull(const char* json, const char* key, unsigned long long* out) {{
  const char* v = json_value_start(json, key); char* e = nullptr; if (!v) return 0;
  *out = strtoull(v, &e, 10); return e != v;
}}
static int json_double(const char* json, const char* key, double* out) {{
  const char* v = json_value_start(json, key); char* e = nullptr; if (!v) return 0;
  *out = strtod(v, &e); return e != v;
}}
static void fill(std::vector<In>& input) {{
  for (size_t i = 0; i < input.size(); ++i)
    for (int j = 0; j < {in_count}; ++j) input[i].x[j] = uint8_t((i * {variant.fill_a}u + j * {variant.fill_b}u + {variant.fill_c}u) & {variant.fill_mask}u);
}}
static Out compute_cpu(Vsim& top, const In& in, int inner_repeat) {{
{_bridge_assignments(variant)}
  top.eval(); Out base{{{{0}}}}, out{{{{0}}}};
{_bridge_reads(variant)}
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < {out_count}; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j * 3) & 255);
  return out;
}}
int main(int argc, char** argv) {{
  if (argc != 6) {{ printf("{{\\"status\\":\\"failed_usage\\"}}\\n"); return 2; }}
  int nstates = atoi(argv[2]), repeat = atoi(argv[3]), inner_repeat = atoi(argv[4]), integration_batches = atoi(argv[5]);
  void* handle = dlopen(argv[1], RTLD_NOW);
  if (!handle) {{ printf("{{\\"status\\":\\"failed_dlopen\\"}}\\n"); return 1; }}
  auto run_outputs = (run_outputs_fn)dlsym(handle, "{symbol}_run_gpu_outputs");
  auto run_json = (run_json_fn)dlsym(handle, "{symbol}_run_hybrid_json");
  if (!run_outputs || !run_json) {{ printf("{{\\"status\\":\\"failed_dlsym\\"}}\\n"); return 1; }}
  std::vector<In> input(nstates); std::vector<Out> cpu(nstates), gpu(nstates); fill(input);
  VerilatedContext context; Vsim top(&context); double cpu_ms = 0.0; uint64_t cpu_checksum = 0;
  for (int r = 0; r < repeat; ++r) {{
    struct timespec cs; clock_gettime(CLOCK_MONOTONIC, &cs);
    for (int b = 0; b < integration_batches; ++b) {{
      for (int i = 0; i < nstates; ++i) cpu[i] = compute_cpu(top, input[i], inner_repeat);
      cpu_checksum ^= cpu[(b + r) % nstates].y[(b + r) % {out_count}] + uint64_t(b + r);
    }}
    cpu_ms += ms_since(cs);
  }}
  double batches = double(repeat) * double(integration_batches); cpu_ms /= batches;
  int out_rc = run_outputs(nstates, inner_repeat, gpu.data(), gpu.size());
  if (out_rc != 0) {{ printf("{{\\"status\\":\\"failed_gpu_outputs\\"}}\\n"); return 1; }}
  size_t mismatch_count = 0;
  for (int i = 0; i < nstates; ++i) for (int j = 0; j < {out_count}; ++j) if (cpu[i].y[j] != gpu[i].y[j]) ++mismatch_count;
  char hybrid_json[4096]; struct timespec hs; clock_gettime(CLOCK_MONOTONIC, &hs);
  int json_rc = run_json(nstates, repeat, inner_repeat, integration_batches, hybrid_json, sizeof(hybrid_json));
  double bridge_wall_ms = ms_since(hs); dlclose(handle); top.final();
  if (json_rc != 0) {{ printf("{{\\"status\\":\\"failed_hybrid_json\\"}}\\n"); return 1; }}
  unsigned long long gpu_checksum = 0; double gpu_ms = 0.0, kernel_ms = 0.0;
  int parsed = json_ull(hybrid_json, "gpu_control_checksum", &gpu_checksum) &&
      json_double(hybrid_json, "gpu_end_to_end_ms", &gpu_ms) && json_double(hybrid_json, "gpu_kernel_ms", &kernel_ms);
  if (!parsed) {{ printf("{{\\"status\\":\\"failed_parse_hybrid_json\\"}}\\n"); return 1; }}
  bool pass = mismatch_count == 0 && cpu_checksum == uint64_t(gpu_checksum);
  printf("{{\\"status\\":\\"%s\\",\\"variant\\":\\"{symbol}\\",\\"nstates\\":%d,\\"repeat\\":%d,\\"inner_repeat\\":%d,\\"integration_batches\\":%d,\\"unit_count\\":{variant.units},\\"input_bytes\\":%zu,\\"output_bytes\\":%zu,\\"mismatch_count\\":%zu,\\"cpu_control_checksum\\":%llu,\\"gpu_control_checksum\\":%llu,\\"cpu_vs_gpu_output_equal\\":%s,\\"cpu_vs_gpu_control_checksum_equal\\":%s,\\"cpu_ms\\":%.17g,\\"gpu_end_to_end_ms\\":%.17g,\\"gpu_kernel_ms\\":%.17g,\\"bridge_hybrid_wall_ms\\":%.17g,\\"bridge_hybrid_wall_ms_per_integration_batch\\":%.17g,\\"cpu_to_gpu_end_to_end_speedup\\":%.17g,\\"cpu_to_gpu_kernel_speedup\\":%.17g,\\"cpu_to_bridge_hybrid_wall_speedup\\":%.17g}}\\n",
    pass ? "hls_variant_measured" : "hls_variant_mismatch", nstates, repeat, inner_repeat, integration_batches,
    input.size() * sizeof(In), gpu.size() * sizeof(Out), mismatch_count, static_cast<unsigned long long>(cpu_checksum), gpu_checksum,
    mismatch_count == 0 ? "true" : "false", cpu_checksum == uint64_t(gpu_checksum) ? "true" : "false",
    cpu_ms, gpu_ms, kernel_ms, bridge_wall_ms, bridge_wall_ms / batches,
    gpu_ms > 0.0 ? cpu_ms / gpu_ms : 0.0, kernel_ms > 0.0 ? cpu_ms / kernel_ms : 0.0,
    (bridge_wall_ms / batches) > 0.0 ? cpu_ms / (bridge_wall_ms / batches) : 0.0);
  return pass ? 0 : 1;
}}
'''


def _load_baseline(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    median = payload.get("median") or {}
    return {
        "report": _display_path(path),
        "status": payload.get("status"),
        "candidate": payload.get("candidate"),
        "shape": payload.get("shape"),
        "cpu_to_gpu_end_to_end_speedup": median.get("cpu_to_gpu_end_to_end_speedup"),
        "cpu_to_gpu_kernel_speedup": median.get("cpu_to_gpu_kernel_speedup"),
        "cpu_ms": median.get("cpu_ms"),
        "gpu_end_to_end_ms": median.get("gpu_end_to_end_ms"),
        "gpu_kernel_ms": median.get("gpu_kernel_ms"),
    }


def measure_variant(
    variant: Variant,
    *,
    shape: str,
    repeat: int,
    inner_repeat: int,
    integration_batches: int,
    out_dir: Path,
) -> dict[str, Any]:
    nstates, steps = _shape(shape)
    if steps != 1:
        raise ValueError("HLS-friendly variants currently support Nx1 shapes")
    variant_dir = out_dir / variant.name
    variant_dir.mkdir(parents=True, exist_ok=True)
    fir = variant_dir / f"{variant.name}.fir"
    sv = variant_dir / f"{variant.name}.sv"
    probe = variant_dir / f"tb_{variant.name}.cpp"
    cu = variant_dir / f"{variant.name}_gpu.cu"
    bridge = variant_dir / f"{variant.name}_bridge.cpp"
    obj = variant_dir / "obj_dir"
    gpu_library = variant_dir / f"lib{variant.name}_gpu.so"
    binary = variant_dir / f"{variant.name}_direct"
    fir.write_text(firrtl(variant), encoding="utf-8")
    probe.write_text(PROBE, encoding="utf-8")
    cu.write_text(cuda_lib(variant), encoding="utf-8")
    bridge.write_text(bridge_cpp(variant), encoding="utf-8")
    verilator_root, root_command = _verilator_root_command()
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_hls_mlp_block_variant",
        "candidate": variant.candidate,
        "variant": variant.name,
        "source_variant_strategy": variant.strategy,
        "shape": shape,
        "unit_count": variant.units,
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
        "baseline": _load_baseline(variant.baseline_report),
        "commands": [],
        "toolchain": {
            "firtool": _tool("firtool") is not None,
            "verilator": _tool("verilator") is not None,
            "nvcc": _tool("nvcc") is not None,
        },
        "non_claims": [
            *variant.non_claims,
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
                variant.module,
                "-Mdir",
                obj.as_posix(),
                sv.as_posix(),
                probe.as_posix(),
                "--build",
            ],
        ),
        ("nvcc_gpu_library_build", [_tool("nvcc") or "nvcc", "-O3", "--std=c++17", "-shared", "-Xcompiler", "-fPIC", cu.as_posix(), "-o", gpu_library.as_posix()]),
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
        ("direct_callsite_run", [binary.as_posix(), gpu_library.as_posix(), str(nstates), str(repeat), str(inner_repeat), str(integration_batches)]),
    ]
    for stage, command in stages:
        result = _run(command)
        report["commands"].append({"stage": stage, **result})
        if result["returncode"] != 0:
            report["status"] = f"failed_{stage}"
            return report
    observed = json.loads(report["commands"][-1]["stdout"])
    baseline = report["baseline"] or {}
    baseline_speedup = baseline.get("cpu_to_gpu_end_to_end_speedup")
    variant_speedup = observed.get("cpu_to_bridge_hybrid_wall_speedup")
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
                "variant_gpu_end_to_end_speedup": observed.get("cpu_to_gpu_end_to_end_speedup"),
                "variant_gpu_kernel_speedup": observed.get("cpu_to_gpu_kernel_speedup"),
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


def summarize_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    rules = []
    for report in reports:
        comparison = report.get("comparison") or {}
        rules.append(
            {
                "variant": report.get("variant"),
                "candidate": report.get("candidate"),
                "unit_count": report.get("unit_count"),
                "baseline_speedup": comparison.get("baseline_speedup"),
                "variant_speedup": comparison.get("variant_speedup"),
                "speedup_improved": comparison.get("speedup_improved"),
                "rule_signal": "favor_explicit_independent_units_when_bridge_speedup_improves"
                if comparison.get("speedup_improved")
                else "do_not_promote_this_reshaping_without_more_batch_or_arithmetic_density",
            }
        )
    return {
        "schema_version": 1,
        "surface": "scientific_circt_hls_mlp_block_variants_summary",
        "status": "hls_variant_summary_ready" if all(r.get("status") in {"hls_variant_improved", "hls_variant_measured_no_speedup_improvement"} for r in reports) else "hls_variant_summary_incomplete",
        "variants": reports,
        "source_ir_transformation_rules": rules,
        "non_claims": [
            "not_full_microgpt_execution",
            "not_automatic_hls_rewrite",
            "not_pcie_framing_evidence",
            "not_rtlmeter_evidence",
        ],
    }


def materialize_and_measure(
    *,
    variants: list[str],
    shape: str = "1024x1",
    repeat: int = 5,
    inner_repeat: int = 1000,
    integration_batches: int = 15,
    out_dir: Path = OUT_DIR,
) -> dict[str, Any]:
    reports = [
        measure_variant(
            VARIANTS[name],
            shape=shape,
            repeat=repeat,
            inner_repeat=inner_repeat,
            integration_batches=integration_batches,
            out_dir=out_dir,
        )
        for name in variants
    ]
    return summarize_reports(reports)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=[*VARIANTS.keys(), "all"], default="all")
    parser.add_argument("--shape", default="1024x1")
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--inner-repeat", type=int, default=1000)
    parser.add_argument("--integration-batches", type=int, default=15)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    selected = list(VARIANTS) if args.variant == "all" else [args.variant]
    try:
        report = materialize_and_measure(
            variants=selected,
            shape=args.shape,
            repeat=args.repeat,
            inner_repeat=args.inner_repeat,
            integration_batches=args.integration_batches,
            out_dir=args.out_dir,
        )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "hls_variant_summary_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
