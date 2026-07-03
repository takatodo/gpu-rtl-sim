#!/usr/bin/env python3
"""Render FIRRTL/CUDA/bridge sources for source-variant search plans."""

from __future__ import annotations

from dataclasses import dataclass

import scientific_circt_hls_mlp_block_variants as mlp_blocks
from scientific_circt_source_variant_search import ATTENTION_DESCRIPTOR, BlockDescriptor, VariantPlan, plan_shape

@dataclass(frozen=True)
class GeneratedSources:
    firrtl: str
    cuda: str
    bridge: str

def descriptor_for_candidate(candidate: str) -> BlockDescriptor:
    if candidate == "microgpt_attention_head":
        return ATTENTION_DESCRIPTOR
    variant_name = {"microgpt_mlp_slice": "mlp4_hls_friendly", "microgpt_inference_slice": "inference2_hls_friendly"}.get(candidate)
    if variant_name is None:
        raise ValueError(f"unknown candidate: {candidate}")
    variant = mlp_blocks.VARIANTS[variant_name]
    return BlockDescriptor(
        variant.candidate, f"{variant.kind}_unit", variant.module.rstrip("0123456789"), variant.kind,
        mlp_blocks._eval_unit_cpp(variant).strip(), variant.fill_a, variant.fill_b, variant.fill_c,
        variant.fill_mask, mlp_blocks.MIX_J_MULT, mlp_blocks.MIX_MASK, variant.inputs_per_unit,
        variant.outputs_per_unit,
    )

def variant_name(descriptor: BlockDescriptor, plan: VariantPlan) -> str:
    units = plan_shape(plan).units
    if descriptor.kind == "attention":
        return f"attention_head{units}_hls_friendly"
    return f"{descriptor.kind}{units}_source_variant_search"

def symbol_stem(descriptor: BlockDescriptor, plan: VariantPlan) -> str:
    units = plan_shape(plan).units
    return f"attention_head{units}_hls" if descriptor.kind == "attention" else variant_name(descriptor, plan)

def module_name(descriptor: BlockDescriptor, plan: VariantPlan) -> str:
    return f"{descriptor.module_stem}{plan_shape(plan).units}"

def _attention_nodes(prefix: str) -> list[str]:
    lines = [
        f"    node {prefix}_s0a = add(mul({prefix}_x0, {prefix}_x4), mul({prefix}_x1, {prefix}_x5))",
        f"    node {prefix}_s0b = add(mul({prefix}_x2, {prefix}_x6), mul({prefix}_x3, {prefix}_x7))",
        f"    node {prefix}_score0 = add({prefix}_s0a, {prefix}_s0b)",
        f"    node {prefix}_s1a = add(mul({prefix}_x0, {prefix}_x8), mul({prefix}_x1, {prefix}_x9))",
        f"    node {prefix}_s1b = add(mul({prefix}_x2, {prefix}_x10), mul({prefix}_x3, {prefix}_x11))",
        f"    node {prefix}_score1 = add({prefix}_s1a, {prefix}_s1b)",
        f"    node {prefix}_w0s = add({prefix}_score0, UInt<19>(1))",
        f"    node {prefix}_w1s = add({prefix}_score1, UInt<19>(1))",
        f"    node {prefix}_w0 = mul({prefix}_w0s, {prefix}_w0s)",
        f"    node {prefix}_w1 = mul({prefix}_w1s, {prefix}_w1s)",
    ]
    lines.extend(f"    connect {prefix}_y{j}, add(mul({prefix}_w0, {prefix}_x{12 + j}), mul({prefix}_w1, {prefix}_x{16 + j}))" for j in range(4))
    return lines

def firrtl(descriptor: BlockDescriptor, plan: VariantPlan) -> str:
    shape = plan_shape(plan)
    if descriptor.kind != "attention":
        variant = mlp_blocks.Variant(
            variant_name(descriptor, plan), descriptor.candidate, descriptor.kind, module_name(descriptor, plan),
            shape.units, descriptor.unit_inputs, descriptor.unit_outputs,
            mlp_blocks.VARIANTS["mlp4_hls_friendly"].baseline_report, "source_variant_search",
            descriptor.fill_a, descriptor.fill_b, descriptor.fill_c, descriptor.fill_mask, (),
        )
        return mlp_blocks.firrtl(variant)
    module = module_name(descriptor, plan)
    lines = ["FIRRTL version 4.0.0", f"circuit {module} :", f"  public module {module} :"]
    for unit in range(shape.units):
        for idx in range(descriptor.unit_inputs):
            lines.append(f"    input h{unit}_x{idx} : UInt<8>")
        for out in range(descriptor.unit_outputs):
            lines.append(f"    output h{unit}_y{out} : UInt<{descriptor.output_width}>")
    lines.append("")
    for unit in range(shape.units):
        lines.extend(_attention_nodes(f"h{unit}"))
        lines.append("")
    return "\n".join(lines)

def _mix_expr(descriptor: BlockDescriptor) -> str:
    return "r + j" if descriptor.mix_j_mult == 1 else f"r + j * {descriptor.mix_j_mult}"

def _mask_literal(descriptor: BlockDescriptor) -> str:
    return f"0x{descriptor.fill_mask:x}" if descriptor.kind == "attention" else str(descriptor.fill_mask)

def _eval_name(descriptor: BlockDescriptor) -> str:
    return "eval_head" if descriptor.kind == "attention" else "eval_unit"

def cuda_lib(descriptor: BlockDescriptor, plan: VariantPlan) -> str:
    shape = plan_shape(plan)
    in_count, out_count = shape.units * descriptor.unit_inputs, shape.units * descriptor.unit_outputs
    eval_name = _eval_name(descriptor)
    return f'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <vector>

struct In {{ uint8_t x[{in_count}]; }};
struct Out {{ uint64_t y[{out_count}]; }};

static void fill(std::vector<In>& input) {{
  for (size_t i = 0; i < input.size(); ++i)
    for (int j = 0; j < {in_count}; ++j) input[i].x[j] = uint8_t((i * {descriptor.fill_a}u + j * {descriptor.fill_b}u + {descriptor.fill_c}u) & {_mask_literal(descriptor)}u);
}}

{descriptor.eval_unit_cpp}

__host__ __device__ static Out compute_gpu(const In& in, int inner_repeat) {{
  Out base{{{{0}}}}, out{{{{0}}}};
  for (int h = 0; h < {shape.units}; ++h) {eval_name}(&in.x[h * {descriptor.unit_inputs}], &base.y[h * {descriptor.unit_outputs}]);
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < {out_count}; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t(({_mix_expr(descriptor)}) & {descriptor.mix_mask});
  return out;
}}

__global__ static void kernel(const In* input, Out* output, int nstates, int inner_repeat) {{
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < nstates) output[idx] = compute_gpu(input[idx], inner_repeat);
}}

static double ms_since(std::chrono::steady_clock::time_point s) {{
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s).count();
}}

extern "C" int {symbol_stem(descriptor, plan)}_run_gpu_outputs(int nstates, int inner_repeat, Out* out, size_t out_count) {{
  if (!out || nstates <= 0 || inner_repeat <= 0 || out_count < static_cast<size_t>(nstates)) return 2;
  std::vector<In> input(nstates); fill(input);
  In* d_input = nullptr; Out* d_output = nullptr;
  cudaError_t err = cudaFree(nullptr);
  if (err == cudaSuccess) err = cudaMalloc(&d_input, input.size() * sizeof(In));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, out_count * sizeof(Out));
  if (err == cudaSuccess) err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
  int threads = 256, blocks = (nstates + threads - 1) / threads;
  if (err == cudaSuccess) {{ kernel<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat); err = cudaDeviceSynchronize(); }}
  if (err == cudaSuccess) err = cudaMemcpy(out, d_output, out_count * sizeof(Out), cudaMemcpyDeviceToHost);
  if (d_input) cudaFree(d_input);
  if (d_output) cudaFree(d_output);
  return err == cudaSuccess ? 0 : 1;
}}

extern "C" int {symbol_stem(descriptor, plan)}_run_hybrid_json(
    int nstates, int repeat, int inner_repeat, int integration_batches, char* out_json, size_t out_json_size) {{
  if (!out_json || out_json_size == 0 || nstates <= 0 || repeat <= 0 || inner_repeat <= 0 || integration_batches <= 0) return 2;
  std::vector<In> input(nstates); std::vector<Out> gpu(nstates); fill(input);
  In* d_input = nullptr; Out* d_output = nullptr; cudaEvent_t ks, ke;
  cudaEventCreate(&ks); cudaEventCreate(&ke);
  cudaError_t err = cudaFree(nullptr);
  if (err == cudaSuccess) err = cudaMalloc(&d_input, input.size() * sizeof(In));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, gpu.size() * sizeof(Out));
  double gpu_ms = 0.0, kernel_ms = 0.0; uint64_t checksum = 0;
  int threads = 256, blocks = (nstates + threads - 1) / threads;
  for (int r = 0; r < repeat && err == cudaSuccess; ++r) {{
    auto gs = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches && err == cudaSuccess; ++b) {{
      err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(In), cudaMemcpyHostToDevice);
      if (err == cudaSuccess) {{
        cudaEventRecord(ks); kernel<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
        cudaEventRecord(ke); err = cudaEventSynchronize(ke);
      }}
      if (err == cudaSuccess) {{
        float km = 0.0f; cudaEventElapsedTime(&km, ks, ke); kernel_ms += km;
        err = cudaMemcpy(gpu.data(), d_output, gpu.size() * sizeof(Out), cudaMemcpyDeviceToHost);
      }}
      if (err == cudaSuccess) {{ err = cudaDeviceSynchronize(); checksum ^= gpu[(b + r) % nstates].y[(b + r) & {out_count - 1}] + uint64_t(b + r); }}
    }}
    gpu_ms += ms_since(gs);
  }}
  double batches = double(repeat) * double(integration_batches);
  gpu_ms /= batches; kernel_ms /= batches;
  if (d_input) cudaFree(d_input);
  if (d_output) cudaFree(d_output);
  cudaEventDestroy(ks); cudaEventDestroy(ke);
  std::snprintf(out_json, out_json_size,
      "{{\\"status\\":\\"%s\\",\\"gpu_control_checksum\\":%llu,\\"gpu_end_to_end_ms\\":%.17g,\\"gpu_kernel_ms\\":%.17g}}",
      err == cudaSuccess ? "hybrid_entrypoint_passed" : "hybrid_entrypoint_failed",
      static_cast<unsigned long long>(checksum), gpu_ms, kernel_ms);
  return err == cudaSuccess ? 0 : 1;
}}
'''

def _apply_chain(units: int) -> str:
    items = [f"if (h == 0) {{ SET_HEAD(0); }}"]
    items.extend(f"else if (h == {unit}) {{ SET_HEAD({unit}); }}" for unit in range(1, units - 1))
    if units > 1:
        items.append(f"else {{ SET_HEAD({units - 1}); }}")
    return "  " + " ".join(items)

def _read_lines(units: int, per_unit: int) -> str:
    lines = []
    for unit in range(units):
        start = unit * per_unit
        assigns = " ".join(f"y[{start + out}]=top.h{unit}_y{out};" for out in range(per_unit))
        lines.append(f"  {assigns}")
    return "\n".join(lines)

def bridge_cpp(descriptor: BlockDescriptor, plan: VariantPlan) -> str:
    shape = plan_shape(plan)
    in_count, out_count, sym = shape.units * descriptor.unit_inputs, shape.units * descriptor.unit_outputs, symbol_stem(descriptor, plan)
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
    for (int j = 0; j < {in_count}; ++j) input[i].x[j] = uint8_t((i * {descriptor.fill_a}u + j * {descriptor.fill_b}u + {descriptor.fill_c}u) & {_mask_literal(descriptor)}u);
}}
static void apply_head(Vsim& top, const uint8_t* x, int h) {{
#define SET_HEAD(H) top.h##H##_x0=x[0]; top.h##H##_x1=x[1]; top.h##H##_x2=x[2]; top.h##H##_x3=x[3]; top.h##H##_x4=x[4]; top.h##H##_x5=x[5]; top.h##H##_x6=x[6]; top.h##H##_x7=x[7]; top.h##H##_x8=x[8]; top.h##H##_x9=x[9]; top.h##H##_x10=x[10]; top.h##H##_x11=x[11]; top.h##H##_x12=x[12]; top.h##H##_x13=x[13]; top.h##H##_x14=x[14]; top.h##H##_x15=x[15]; top.h##H##_x16=x[16]; top.h##H##_x17=x[17]; top.h##H##_x18=x[18]; top.h##H##_x19=x[19]
{_apply_chain(shape.units)}
#undef SET_HEAD
}}
static void read_base(const Vsim& top, uint64_t* y) {{
{_read_lines(shape.units, descriptor.unit_outputs)}
}}
static Out compute_cpu(Vsim& top, const In& in, int inner_repeat) {{
  for (int h = 0; h < {shape.units}; ++h) apply_head(top, &in.x[h * {descriptor.unit_inputs}], h);
  top.eval(); Out base{{{{0}}}}, out{{{{0}}}}; read_base(top, base.y);
  for (int r = 0; r < inner_repeat; ++r)
    for (int j = 0; j < {out_count}; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t(({_mix_expr(descriptor)}) & {descriptor.mix_mask});
  return out;
}}
int main(int argc, char** argv) {{
  if (argc != 6) {{ printf("{{\\"status\\":\\"failed_usage\\"}}\\n"); return 2; }}
  int nstates = atoi(argv[2]), repeat = atoi(argv[3]), inner_repeat = atoi(argv[4]), integration_batches = atoi(argv[5]);
  void* handle = dlopen(argv[1], RTLD_NOW);
  if (!handle) {{ printf("{{\\"status\\":\\"failed_dlopen\\"}}\\n"); return 1; }}
  auto run_outputs = (run_outputs_fn)dlsym(handle, "{sym}_run_gpu_outputs");
  auto run_json = (run_json_fn)dlsym(handle, "{sym}_run_hybrid_json");
  if (!run_outputs || !run_json) {{ printf("{{\\"status\\":\\"failed_dlsym\\"}}\\n"); return 1; }}
  std::vector<In> input(nstates); std::vector<Out> cpu(nstates), gpu(nstates); fill(input);
  VerilatedContext context; Vsim top(&context); double cpu_ms = 0.0; uint64_t cpu_checksum = 0;
  for (int r = 0; r < repeat; ++r) {{
    struct timespec cs; clock_gettime(CLOCK_MONOTONIC, &cs);
    for (int b = 0; b < integration_batches; ++b) {{
      for (int i = 0; i < nstates; ++i) cpu[i] = compute_cpu(top, input[i], inner_repeat);
      cpu_checksum ^= cpu[(b + r) % nstates].y[(b + r) & {out_count - 1}] + uint64_t(b + r);
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
  printf("{{\\"status\\":\\"%s\\",\\"variant\\":\\"{variant_name(descriptor, plan)}\\",\\"nstates\\":%d,\\"repeat\\":%d,\\"inner_repeat\\":%d,\\"integration_batches\\":%d,\\"head_count\\":{shape.units},\\"input_bytes\\":%zu,\\"output_bytes\\":%zu,\\"mismatch_count\\":%zu,\\"cpu_control_checksum\\":%llu,\\"gpu_control_checksum\\":%llu,\\"cpu_vs_gpu_output_equal\\":%s,\\"cpu_vs_gpu_control_checksum_equal\\":%s,\\"cpu_ms\\":%.17g,\\"gpu_end_to_end_ms\\":%.17g,\\"gpu_kernel_ms\\":%.17g,\\"bridge_hybrid_wall_ms\\":%.17g,\\"bridge_hybrid_wall_ms_per_integration_batch\\":%.17g,\\"cpu_to_gpu_end_to_end_speedup\\":%.17g,\\"cpu_to_gpu_kernel_speedup\\":%.17g,\\"cpu_to_bridge_hybrid_wall_speedup\\":%.17g}}\\n",
    pass ? "hls_variant_measured" : "hls_variant_mismatch", nstates, repeat, inner_repeat, integration_batches,
    input.size() * sizeof(In), gpu.size() * sizeof(Out), mismatch_count, static_cast<unsigned long long>(cpu_checksum), gpu_checksum,
    mismatch_count == 0 ? "true" : "false", cpu_checksum == uint64_t(gpu_checksum) ? "true" : "false",
    cpu_ms, gpu_ms, kernel_ms, bridge_wall_ms, bridge_wall_ms / batches,
    gpu_ms > 0.0 ? cpu_ms / gpu_ms : 0.0, kernel_ms > 0.0 ? cpu_ms / kernel_ms : 0.0,
    (bridge_wall_ms / batches) > 0.0 ? cpu_ms / (bridge_wall_ms / batches) : 0.0);
  return pass ? 0 : 1;
}}
'''

def render_sources(descriptor: BlockDescriptor, plan: VariantPlan) -> GeneratedSources:
    return GeneratedSources(firrtl=firrtl(descriptor, plan), cuda=cuda_lib(descriptor, plan), bridge=bridge_cpp(descriptor, plan))
