#!/usr/bin/env python3
"""Run the first scientific runtime handoff adapter correctness gate."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from scientific_circt_hybrid_protocol import _load

OUT_DIR = Path("artifacts/scientific_circt/runtime_handoff_adapter")
REPORT = Path("reports/scientific_circt_runtime_handoff_adapter.json")

CUDA_ADAPTER = r'''#include <cuda_runtime.h>
#include <chrono>
#include <cstdio>
#include <cstdint>
#include <iostream>
#include <vector>

struct MicrogptAttentionHeadIn { uint8_t x[20]; };
struct MicrogptAttentionHeadOut { uint64_t y[4]; };

static void fill(std::vector<MicrogptAttentionHeadIn>& input) {
  for (size_t i = 0; i < input.size(); ++i) {
    for (int j = 0; j < 20; ++j) input[i].x[j] = uint8_t((i * 17u + j * 11u + 1u) & 0x7fu);
  }
}

__host__ __device__ static MicrogptAttentionHeadOut adapter_eval(const MicrogptAttentionHeadIn& in) {
  uint64_t score0 = 0, score1 = 0;
  for (int j = 0; j < 4; ++j) {
    score0 += uint64_t(in.x[j]) * in.x[4 + j];
    score1 += uint64_t(in.x[j]) * in.x[8 + j];
  }
  uint64_t w0 = (score0 + 1) * (score0 + 1);
  uint64_t w1 = (score1 + 1) * (score1 + 1);
  MicrogptAttentionHeadOut out{{0, 0, 0, 0}};
  for (int j = 0; j < 4; ++j) out.y[j] = w0 * in.x[12 + j] + w1 * in.x[16 + j];
  return out;
}

__host__ __device__ static MicrogptAttentionHeadOut adapter_eval_fused(
    const MicrogptAttentionHeadIn& in,
    int inner_repeat) {
  MicrogptAttentionHeadOut base = adapter_eval(in);
  if (inner_repeat <= 1) return base;
  MicrogptAttentionHeadOut out{{0, 0, 0, 0}};
  for (int r = 0; r < inner_repeat; ++r) {
    for (int j = 0; j < 4; ++j) out.y[j] = (out.y[j] + base.y[j]) ^ uint64_t((r + j) & 31);
  }
  return out;
}

__global__ static void microgpt_attention_head_handoff_adapter(
    const MicrogptAttentionHeadIn* input,
    MicrogptAttentionHeadOut* output,
    int nstates,
    int inner_repeat) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < nstates) output[idx] = adapter_eval_fused(input[idx], inner_repeat);
}

static double ms_since(std::chrono::steady_clock::time_point start) {
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
}

extern "C" int microgpt_attention_head_handoff_adapter_run_json(
    int nstates,
    int repeat,
    int inner_repeat,
    int integration_batches,
    char* out_json,
    size_t out_json_size) {
  if (!out_json || out_json_size == 0) return 2;
  if (nstates <= 0 || repeat <= 0 || inner_repeat <= 0 || integration_batches <= 0) return 2;
  std::vector<MicrogptAttentionHeadIn> input(nstates);
  std::vector<MicrogptAttentionHeadOut> cpu(nstates), gpu(nstates);
  fill(input);

  MicrogptAttentionHeadIn* d_input = nullptr;
  MicrogptAttentionHeadOut* d_output = nullptr;
  cudaEvent_t kernel_start, kernel_stop;
  cudaEventCreate(&kernel_start);
  cudaEventCreate(&kernel_stop);
  cudaError_t err = cudaFree(nullptr);
  if (err != cudaSuccess) {
    std::snprintf(
        out_json,
        out_json_size,
        "{\"status\":\"cuda_unavailable\",\"cuda_error\":\"%s\"}",
        cudaGetErrorString(err));
    return 1;
  }
  err = cudaMalloc(&d_input, input.size() * sizeof(MicrogptAttentionHeadIn));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, gpu.size() * sizeof(MicrogptAttentionHeadOut));
  int threads = 256;
  int blocks = (nstates + threads - 1) / threads;

  double cpu_ms = 0.0, gpu_end_to_end_ms = 0.0, gpu_kernel_ms = 0.0;
  uint64_t cpu_control_checksum = 0, gpu_control_checksum = 0;
  size_t mismatch_count = 0;
  if (err == cudaSuccess) {
    err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(MicrogptAttentionHeadIn), cudaMemcpyHostToDevice);
  }
  if (err == cudaSuccess) {
    microgpt_attention_head_handoff_adapter<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
    err = cudaDeviceSynchronize();
  }
  for (int r = 0; r < repeat && err == cudaSuccess; ++r) {
    auto cpu_start = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches; ++b) {
      for (int i = 0; i < nstates; ++i) cpu[i] = adapter_eval_fused(input[i], inner_repeat);
      cpu_control_checksum ^= cpu[(b + r) % nstates].y[(b + r) & 3] + uint64_t(b + r);
    }
    cpu_ms += ms_since(cpu_start);

    auto gpu_start = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches && err == cudaSuccess; ++b) {
      err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(MicrogptAttentionHeadIn), cudaMemcpyHostToDevice);
      if (err == cudaSuccess) {
        cudaEventRecord(kernel_start);
        microgpt_attention_head_handoff_adapter<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
        cudaEventRecord(kernel_stop);
        err = cudaEventSynchronize(kernel_stop);
      }
      if (err == cudaSuccess) {
        float elapsed = 0.0f;
        cudaEventElapsedTime(&elapsed, kernel_start, kernel_stop);
        gpu_kernel_ms += elapsed;
        err = cudaMemcpy(gpu.data(), d_output, gpu.size() * sizeof(MicrogptAttentionHeadOut), cudaMemcpyDeviceToHost);
      }
      if (err == cudaSuccess) {
        err = cudaDeviceSynchronize();
        gpu_control_checksum ^= gpu[(b + r) % nstates].y[(b + r) & 3] + uint64_t(b + r);
      }
    }
    gpu_end_to_end_ms += ms_since(gpu_start);

    if (err == cudaSuccess) {
      for (int i = 0; i < nstates; ++i) {
        for (int j = 0; j < 4; ++j) {
          if (cpu[i].y[j] != gpu[i].y[j]) ++mismatch_count;
        }
      }
    }
  }
  double measured_batches = double(repeat) * double(integration_batches);
  cpu_ms /= measured_batches;
  gpu_end_to_end_ms /= measured_batches;
  gpu_kernel_ms /= measured_batches;
  if (d_input) cudaFree(d_input);
  if (d_output) cudaFree(d_output);
  cudaEventDestroy(kernel_start);
  cudaEventDestroy(kernel_stop);

  bool pass = err == cudaSuccess && mismatch_count == 0 && cpu_control_checksum == gpu_control_checksum;
  std::snprintf(
      out_json,
      out_json_size,
      "{\"status\":\"%s\",\"nstates\":%d,\"repeat\":%d,\"inner_repeat\":%d,"
      "\"integration_batches\":%d,\"input_bytes\":%zu,\"output_bytes\":%zu,"
      "\"mismatch_count\":%zu,\"cpu_control_checksum\":%llu,"
      "\"gpu_control_checksum\":%llu,\"cpu_ms\":%.17g,"
      "\"gpu_end_to_end_ms\":%.17g,\"gpu_kernel_ms\":%.17g,"
      "\"cpu_to_gpu_end_to_end_speedup\":%.17g,"
      "\"cpu_to_gpu_kernel_speedup\":%.17g,\"cuda_status\":\"%s\"}",
      pass ? "adapter_correctness_passed" : "adapter_correctness_failed",
      nstates,
      repeat,
      inner_repeat,
      integration_batches,
      input.size() * sizeof(MicrogptAttentionHeadIn),
      gpu.size() * sizeof(MicrogptAttentionHeadOut),
      mismatch_count,
      static_cast<unsigned long long>(cpu_control_checksum),
      static_cast<unsigned long long>(gpu_control_checksum),
      cpu_ms,
      gpu_end_to_end_ms,
      gpu_kernel_ms,
      gpu_end_to_end_ms > 0.0 ? cpu_ms / gpu_end_to_end_ms : 0.0,
      gpu_kernel_ms > 0.0 ? cpu_ms / gpu_kernel_ms : 0.0,
      err == cudaSuccess ? "success" : cudaGetErrorString(err));
  return pass ? 0 : 1;
}

extern "C" int microgpt_attention_head_handoff_adapter_run_hybrid_json(
    int nstates,
    int repeat,
    int inner_repeat,
    int integration_batches,
    char* out_json,
    size_t out_json_size) {
  if (!out_json || out_json_size == 0) return 2;
  if (nstates <= 0 || repeat <= 0 || inner_repeat <= 0 || integration_batches <= 0) return 2;
  std::vector<MicrogptAttentionHeadIn> input(nstates);
  std::vector<MicrogptAttentionHeadOut> gpu(nstates);
  fill(input);

  MicrogptAttentionHeadIn* d_input = nullptr;
  MicrogptAttentionHeadOut* d_output = nullptr;
  cudaEvent_t kernel_start, kernel_stop;
  cudaEventCreate(&kernel_start);
  cudaEventCreate(&kernel_stop);
  cudaError_t err = cudaFree(nullptr);
  if (err != cudaSuccess) {
    std::snprintf(
        out_json,
        out_json_size,
        "{\"status\":\"cuda_unavailable\",\"cuda_error\":\"%s\"}",
        cudaGetErrorString(err));
    return 1;
  }
  err = cudaMalloc(&d_input, input.size() * sizeof(MicrogptAttentionHeadIn));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, gpu.size() * sizeof(MicrogptAttentionHeadOut));
  int threads = 256;
  int blocks = (nstates + threads - 1) / threads;

  if (err == cudaSuccess) {
    err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(MicrogptAttentionHeadIn), cudaMemcpyHostToDevice);
  }
  if (err == cudaSuccess) {
    microgpt_attention_head_handoff_adapter<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
    err = cudaDeviceSynchronize();
  }

  double gpu_end_to_end_ms = 0.0, gpu_kernel_ms = 0.0;
  uint64_t gpu_control_checksum = 0;
  for (int r = 0; r < repeat && err == cudaSuccess; ++r) {
    auto gpu_start = std::chrono::steady_clock::now();
    for (int b = 0; b < integration_batches && err == cudaSuccess; ++b) {
      err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(MicrogptAttentionHeadIn), cudaMemcpyHostToDevice);
      if (err == cudaSuccess) {
        cudaEventRecord(kernel_start);
        microgpt_attention_head_handoff_adapter<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
        cudaEventRecord(kernel_stop);
        err = cudaEventSynchronize(kernel_stop);
      }
      if (err == cudaSuccess) {
        float elapsed = 0.0f;
        cudaEventElapsedTime(&elapsed, kernel_start, kernel_stop);
        gpu_kernel_ms += elapsed;
        err = cudaMemcpy(gpu.data(), d_output, gpu.size() * sizeof(MicrogptAttentionHeadOut), cudaMemcpyDeviceToHost);
      }
      if (err == cudaSuccess) {
        err = cudaDeviceSynchronize();
        gpu_control_checksum ^= gpu[(b + r) % nstates].y[(b + r) & 3] + uint64_t(b + r);
      }
    }
    gpu_end_to_end_ms += ms_since(gpu_start);
  }
  double measured_batches = double(repeat) * double(integration_batches);
  gpu_end_to_end_ms /= measured_batches;
  gpu_kernel_ms /= measured_batches;
  if (d_input) cudaFree(d_input);
  if (d_output) cudaFree(d_output);
  cudaEventDestroy(kernel_start);
  cudaEventDestroy(kernel_stop);

  bool pass = err == cudaSuccess;
  std::snprintf(
      out_json,
      out_json_size,
      "{\"status\":\"%s\",\"nstates\":%d,\"repeat\":%d,\"inner_repeat\":%d,"
      "\"integration_batches\":%d,\"input_bytes\":%zu,\"output_bytes\":%zu,"
      "\"gpu_control_checksum\":%llu,\"gpu_end_to_end_ms\":%.17g,"
      "\"gpu_kernel_ms\":%.17g,\"cuda_status\":\"%s\"}",
      pass ? "hybrid_entrypoint_passed" : "hybrid_entrypoint_failed",
      nstates,
      repeat,
      inner_repeat,
      integration_batches,
      input.size() * sizeof(MicrogptAttentionHeadIn),
      gpu.size() * sizeof(MicrogptAttentionHeadOut),
      static_cast<unsigned long long>(gpu_control_checksum),
      gpu_end_to_end_ms,
      gpu_kernel_ms,
      err == cudaSuccess ? "success" : cudaGetErrorString(err));
  return pass ? 0 : 1;
}

extern "C" int microgpt_attention_head_handoff_adapter_run_gpu_outputs(
    int nstates,
    int inner_repeat,
    MicrogptAttentionHeadOut* out,
    size_t out_count) {
  if (!out || nstates <= 0 || inner_repeat <= 0 || out_count < static_cast<size_t>(nstates)) return 2;
  std::vector<MicrogptAttentionHeadIn> input(nstates);
  fill(input);

  MicrogptAttentionHeadIn* d_input = nullptr;
  MicrogptAttentionHeadOut* d_output = nullptr;
  cudaError_t err = cudaFree(nullptr);
  if (err != cudaSuccess) return 1;
  err = cudaMalloc(&d_input, input.size() * sizeof(MicrogptAttentionHeadIn));
  if (err == cudaSuccess) err = cudaMalloc(&d_output, out_count * sizeof(MicrogptAttentionHeadOut));
  if (err == cudaSuccess) {
    err = cudaMemcpy(d_input, input.data(), input.size() * sizeof(MicrogptAttentionHeadIn), cudaMemcpyHostToDevice);
  }
  int threads = 256;
  int blocks = (nstates + threads - 1) / threads;
  if (err == cudaSuccess) {
    microgpt_attention_head_handoff_adapter<<<blocks, threads>>>(d_input, d_output, nstates, inner_repeat);
    err = cudaDeviceSynchronize();
  }
  if (err == cudaSuccess) {
    err = cudaMemcpy(out, d_output, out_count * sizeof(MicrogptAttentionHeadOut), cudaMemcpyDeviceToHost);
  }
  if (d_input) cudaFree(d_input);
  if (d_output) cudaFree(d_output);
  return err == cudaSuccess ? 0 : 1;
}

int main(int argc, char** argv) {
  if (argc != 5) return 2;
  int nstates = std::stoi(argv[1]);
  int repeat = std::stoi(argv[2]);
  int inner_repeat = std::stoi(argv[3]);
  int integration_batches = std::stoi(argv[4]);
  char out_json[4096] = {0};
  int rc = microgpt_attention_head_handoff_adapter_run_json(
      nstates, repeat, inner_repeat, integration_batches, out_json, sizeof(out_json));
  std::cout << out_json << "\n";
  return rc;
}
'''


def _sanitize(text: str) -> str:
    repo = Path.cwd().as_posix()
    text = text.replace(repo, "<repo>")
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", text)


def _display_path(path: Path) -> str:
    return _sanitize(path.as_posix())


def _run(argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    return {
        "argv": [_sanitize(arg) for arg in argv],
        "returncode": proc.returncode,
        "stdout": _sanitize(proc.stdout.strip()),
        "stderr": _sanitize(proc.stderr.strip()),
    }


def _require_abi(abi: dict[str, Any]) -> dict[str, Any]:
    if abi.get("status") != "handoff_abi_ready":
        raise ValueError("handoff ABI is not ready")
    if abi.get("candidate") != "microgpt_attention_head" or abi.get("shape") != "1024x1":
        raise ValueError("runtime adapter currently supports microgpt_attention_head 1024x1")
    handoff = abi.get("handoff_abi")
    if not isinstance(handoff, dict):
        raise ValueError("handoff ABI missing handoff_abi object")
    return handoff


def run_adapter(
    abi: dict[str, Any],
    out_dir: Path = OUT_DIR,
    repeat: int = 5,
    inner_repeat: int = 1,
    integration_batches: int = 1,
) -> dict[str, Any]:
    handoff = _require_abi(abi)
    if repeat <= 0:
        raise ValueError("repeat must be positive")
    if inner_repeat <= 0:
        raise ValueError("inner_repeat must be positive")
    if integration_batches <= 0:
        raise ValueError("integration_batches must be positive")
    nstates = int(abi.get("nstates", 0))
    if nstates <= 0:
        raise ValueError("handoff ABI missing positive nstates")
    input_bytes = int(handoff.get("logical_input_bytes", 0))
    output_bytes = int(handoff.get("logical_output_bytes", 0))
    if input_bytes != nstates * 20 or output_bytes != nstates * 32:
        raise ValueError("handoff ABI byte counts do not match microgpt_attention_head layout")

    out_dir.mkdir(parents=True, exist_ok=True)
    source = out_dir / "microgpt_attention_head_handoff_adapter.cu"
    binary = out_dir / "microgpt_attention_head_handoff_adapter"
    library = out_dir / "libmicrogpt_attention_head_handoff_adapter.so"
    source.write_text(CUDA_ADAPTER, encoding="utf-8")
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_runtime_handoff_adapter",
        "candidate": abi.get("candidate"),
        "shape": abi.get("shape"),
        "nstates": nstates,
        "source_abi_surface": abi.get("surface"),
        "handoff_abi_status": abi.get("status"),
        "adapter_source": _display_path(source),
        "adapter_binary": _display_path(binary),
        "adapter_library": _display_path(library),
        "expected_logical_input_bytes": input_bytes,
        "expected_logical_output_bytes": output_bytes,
        "repeat": repeat,
        "inner_repeat": inner_repeat,
        "integration_batches": integration_batches,
        "correctness_policy": handoff.get("correctness_policy"),
        "toolchain": {"nvcc": bool(shutil.which("nvcc"))},
        "commands": [],
        "timing_scope": "adapter_local_repeat_average_per_integration_batch",
        "fused_work_scope": "single_handoff_with_inner_repeated_attention_head_arithmetic",
        "non_claims": [
            "not_broad_runtime_speedup_claim",
            "not_pcie_framing_evidence",
            "not_full_microgpt_execution",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
            "not_broader_hybrid_runtime_entrypoint",
        ],
    }
    for stage, command in (
        ("nvcc_build", ["nvcc", "-O3", "--std=c++17", source.as_posix(), "-o", binary.as_posix()]),
        (
            "nvcc_shared_library_build",
            [
                "nvcc",
                "-O3",
                "--std=c++17",
                "-shared",
                "-Xcompiler",
                "-fPIC",
                source.as_posix(),
                "-o",
                library.as_posix(),
            ],
        ),
        (
            "adapter_correctness_run",
            [binary.as_posix(), str(nstates), str(repeat), str(inner_repeat), str(integration_batches)],
        ),
    ):
        result = _run(command)
        report["commands"].append({"stage": stage, **result})
        if result["returncode"] != 0:
            report["status"] = f"failed_{stage}"
            return report

    observed = json.loads(report["commands"][-1]["stdout"])
    observed_input = observed.get("input_bytes")
    observed_output = observed.get("output_bytes")
    report["observed"] = observed
    report["average"] = {
        "cpu_ms": observed.get("cpu_ms"),
        "gpu_end_to_end_ms": observed.get("gpu_end_to_end_ms"),
        "gpu_kernel_ms": observed.get("gpu_kernel_ms"),
        "cpu_to_gpu_end_to_end_speedup": observed.get("cpu_to_gpu_end_to_end_speedup"),
        "cpu_to_gpu_kernel_speedup": observed.get("cpu_to_gpu_kernel_speedup"),
    }
    report["input_bytes_match_abi"] = observed_input == input_bytes
    report["output_bytes_match_abi"] = observed_output == output_bytes
    report["cpu_vs_gpu_output_equal"] = observed.get("mismatch_count") == 0
    report["cpu_vs_gpu_control_checksum_equal"] = observed.get("cpu_control_checksum") == observed.get(
        "gpu_control_checksum"
    )
    report["status"] = (
        "adapter_correctness_passed"
        if observed.get("status") == "adapter_correctness_passed"
        and report["input_bytes_match_abi"]
        and report["output_bytes_match_abi"]
        and report["cpu_vs_gpu_output_equal"]
        and report["cpu_vs_gpu_control_checksum_equal"]
        else "adapter_correctness_failed"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--abi", type=Path, default=Path("reports/scientific_circt_runtime_handoff_abi.json"))
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--inner-repeat", type=int, default=1)
    parser.add_argument("--integration-batches", type=int, default=1)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = run_adapter(_load(args.abi), args.out_dir, args.repeat, args.inner_repeat, args.integration_batches)
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "adapter_correctness_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
