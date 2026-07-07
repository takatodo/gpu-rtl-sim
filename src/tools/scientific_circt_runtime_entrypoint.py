#!/usr/bin/env python3
"""Measure scientific CIRCT adapter runtime entrypoints."""

from __future__ import annotations

import argparse
import ctypes
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from scientific_circt_hybrid_protocol import _load

REPORT = Path("reports/scientific_circt_runtime_entrypoint.json")
ADAPTER_REPORT = Path("reports/scientific_circt_runtime_handoff_adapter.json")


def _sanitize(text: str) -> str:
    repo = Path.cwd().as_posix()
    text = text.replace(repo, "<repo>")
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", text)


def _display_path(path: Path) -> str:
    return _sanitize(path.as_posix())


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, int | float) else None


def _ceil_positive(value: float) -> int:
    whole = int(value)
    return whole if float(whole) == value else whole + 1


def _run(argv: list[str]) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    wall_ms = (time.perf_counter() - start) * 1000.0
    return {
        "argv": [_sanitize(arg) for arg in argv],
        "returncode": proc.returncode,
        "stdout": _sanitize(proc.stdout.strip()),
        "stderr": _sanitize(proc.stderr.strip()),
        "process_wall_ms": wall_ms,
    }


def _require_adapter_binary(adapter: dict[str, Any]) -> Path:
    if adapter.get("status") != "adapter_correctness_passed":
        raise ValueError("runtime handoff adapter is not ready")
    if adapter.get("candidate") != "microgpt_attention_head" or adapter.get("shape") != "1024x1":
        raise ValueError("runtime entrypoint currently supports microgpt_attention_head 1024x1")
    binary = adapter.get("adapter_binary")
    if not isinstance(binary, str) or not binary:
        raise ValueError("adapter report missing adapter_binary")
    return Path(binary)


def _require_adapter_library(adapter: dict[str, Any]) -> Path:
    if adapter.get("status") != "adapter_correctness_passed":
        raise ValueError("runtime handoff adapter is not ready")
    if adapter.get("candidate") != "microgpt_attention_head" or adapter.get("shape") != "1024x1":
        raise ValueError("runtime entrypoint currently supports microgpt_attention_head 1024x1")
    library = adapter.get("adapter_library")
    if not isinstance(library, str) or not library:
        raise ValueError("adapter report missing adapter_library")
    return Path(library)


def _adapter_dimensions(adapter: dict[str, Any]) -> tuple[int, int, int, int]:
    nstates = int(adapter.get("nstates", 0))
    repeat = int(adapter.get("repeat", 0))
    inner_repeat = int(adapter.get("inner_repeat", 0))
    integration_batches = int(adapter.get("integration_batches", 0))
    if nstates <= 0 or repeat <= 0 or inner_repeat <= 0 or integration_batches <= 0:
        raise ValueError("adapter report missing positive nstates/repeat/inner_repeat/integration_batches")
    average = adapter.get("average")
    if not isinstance(average, dict):
        raise ValueError("adapter report missing average timing object")
    return nstates, repeat, inner_repeat, integration_batches


def _call_in_process_library(
    library: Path,
    nstates: int,
    repeat: int,
    inner_repeat: int,
    integration_batches: int,
    symbol: str = "microgpt_attention_head_handoff_adapter_run_json",
) -> dict[str, Any]:
    lib = ctypes.CDLL(library.as_posix())
    fn = getattr(lib, symbol)
    fn.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    fn.restype = ctypes.c_int
    out = ctypes.create_string_buffer(8192)
    start = time.perf_counter()
    rc = fn(nstates, repeat, inner_repeat, integration_batches, out, ctypes.sizeof(out))
    wall_ms = (time.perf_counter() - start) * 1000.0
    return {
        "library": _display_path(library),
        "symbol": symbol,
        "returncode": int(rc),
        "stdout": _sanitize(out.value.decode("utf-8")),
        "in_process_wall_ms": wall_ms,
    }


def measure_entrypoint(adapter: dict[str, Any]) -> dict[str, Any]:
    binary = _require_adapter_binary(adapter)
    nstates, repeat, inner_repeat, integration_batches = _adapter_dimensions(adapter)

    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_runtime_entrypoint",
        "status": "entrypoint_ready" if binary.exists() else "failed_missing_adapter_binary",
        "candidate": adapter.get("candidate"),
        "shape": adapter.get("shape"),
        "source_adapter_report": _display_path(ADAPTER_REPORT),
        "adapter_binary": _display_path(binary),
        "entrypoint_kind": "process_mediated_adapter_binary",
        "nstates": nstates,
        "repeat": repeat,
        "inner_repeat": inner_repeat,
        "integration_batches": integration_batches,
        "commands": [],
        "non_claims": [
            "not_direct_verilator_entrypoint",
            "not_pcie_framing_evidence",
            "not_full_microgpt_execution",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
            "not_production_runtime_entrypoint",
        ],
    }
    if not binary.exists():
        return report

    result = _run([binary.as_posix(), str(nstates), str(repeat), str(inner_repeat), str(integration_batches)])
    report["commands"].append({"stage": "process_mediated_adapter_run", **result})
    if result["returncode"] != 0:
        report["status"] = "failed_process_mediated_adapter_run"
        return report

    observed = json.loads(result["stdout"])
    total_batches = repeat * integration_batches
    process_wall_per_batch = result["process_wall_ms"] / float(total_batches)
    cpu_ms = _number(observed.get("cpu_ms"))
    gpu_end_to_end_ms = _number(observed.get("gpu_end_to_end_ms"))
    gpu_kernel_ms = _number(observed.get("gpu_kernel_ms"))
    measured_work_ms = (
        cpu_ms + gpu_end_to_end_ms
        if cpu_ms is not None and gpu_end_to_end_ms is not None
        else None
    )
    process_extra_ms = (
        max(0.0, process_wall_per_batch - measured_work_ms)
        if measured_work_ms is not None
        else None
    )
    resident_reuse_break_even_batches = None
    resident_reuse_target_batches = None
    if (
        process_extra_ms is not None
        and cpu_ms is not None
        and gpu_end_to_end_ms is not None
        and cpu_ms > gpu_end_to_end_ms
    ):
        resident_reuse_break_even_batches = _ceil_positive(process_extra_ms / (cpu_ms - gpu_end_to_end_ms))
        resident_reuse_target_batches = resident_reuse_break_even_batches + 1
    report.update(
        {
            "observed": observed,
            "cpu_vs_gpu_output_equal": observed.get("mismatch_count") == 0,
            "cpu_vs_gpu_control_checksum_equal": observed.get("cpu_control_checksum")
            == observed.get("gpu_control_checksum"),
            "process_wall_ms": result["process_wall_ms"],
            "process_wall_ms_per_integration_batch": process_wall_per_batch,
            "adapter_average": {
                "cpu_ms": cpu_ms,
                "gpu_end_to_end_ms": gpu_end_to_end_ms,
                "gpu_kernel_ms": gpu_kernel_ms,
                "cpu_to_gpu_end_to_end_speedup": _number(observed.get("cpu_to_gpu_end_to_end_speedup")),
                "cpu_to_gpu_kernel_speedup": _number(observed.get("cpu_to_gpu_kernel_speedup")),
            },
            "cpu_to_process_wall_speedup": (
                cpu_ms / process_wall_per_batch if cpu_ms is not None and process_wall_per_batch > 0.0 else None
            ),
            "process_extra_ms_per_integration_batch": process_extra_ms,
            "process_extra_to_adapter_gpu_end_to_end_ratio": (
                process_extra_ms / gpu_end_to_end_ms
                if process_extra_ms is not None and gpu_end_to_end_ms is not None and gpu_end_to_end_ms > 0.0
                else None
            ),
            "resident_reuse_break_even_integration_batches": resident_reuse_break_even_batches,
            "resident_reuse_target_integration_batches": resident_reuse_target_batches,
            "resident_target_interpretation": (
                "keep the adapter resident or in-process long enough that one-time process/CUDA-context "
                "overhead is amortized below the CPU-vs-GPU adapter gap"
            ),
            "next_required_evidence": (
                "resident_or_in_process_entrypoint_with_at_least_target_integration_batches_and_cpu_vs_gpu_equality"
            ),
        }
    )
    report["status"] = (
        "entrypoint_timing_measured"
        if observed.get("status") == "adapter_correctness_passed"
        and report["cpu_vs_gpu_output_equal"]
        and report["cpu_vs_gpu_control_checksum_equal"]
        else "entrypoint_correctness_failed"
    )
    return report


def measure_in_process_entrypoint(adapter: dict[str, Any]) -> dict[str, Any]:
    library = _require_adapter_library(adapter)
    nstates, repeat, inner_repeat, integration_batches = _adapter_dimensions(adapter)
    report: dict[str, Any] = {
        "schema_version": 1,
        "surface": "scientific_circt_runtime_entrypoint",
        "status": "entrypoint_ready" if library.exists() else "failed_missing_adapter_library",
        "candidate": adapter.get("candidate"),
        "shape": adapter.get("shape"),
        "source_adapter_report": _display_path(ADAPTER_REPORT),
        "adapter_library": _display_path(library),
        "entrypoint_kind": "in_process_adapter_library",
        "subprocess_used": False,
        "warmup_run_excluded_from_timing": True,
        "nstates": nstates,
        "repeat": repeat,
        "inner_repeat": inner_repeat,
        "integration_batches": integration_batches,
        "calls": [],
        "non_claims": [
            "not_direct_verilator_entrypoint",
            "not_pcie_framing_evidence",
            "not_full_microgpt_execution",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
            "not_production_runtime_entrypoint",
        ],
    }
    if not library.exists():
        return report

    warmup = _call_in_process_library(
        library,
        nstates,
        repeat,
        inner_repeat,
        integration_batches,
        "microgpt_attention_head_handoff_adapter_run_json",
    )
    report["calls"].append({"stage": "in_process_warmup_adapter_library_run", **warmup})
    if warmup["returncode"] != 0:
        report["status"] = "failed_in_process_warmup_adapter_library_run"
        return report

    correctness_observed = json.loads(warmup["stdout"])
    result = _call_in_process_library(
        library,
        nstates,
        repeat,
        inner_repeat,
        integration_batches,
        "microgpt_attention_head_handoff_adapter_run_hybrid_json",
    )
    report["calls"].append({"stage": "in_process_timed_hybrid_library_run", **result})
    if result["returncode"] != 0:
        report["status"] = "failed_in_process_timed_hybrid_library_run"
        return report

    observed = json.loads(result["stdout"])
    total_batches = repeat * integration_batches
    in_process_wall_per_batch = result["in_process_wall_ms"] / float(total_batches)
    cpu_ms = _number(correctness_observed.get("cpu_ms"))
    gpu_end_to_end_ms = _number(observed.get("gpu_end_to_end_ms"))
    gpu_kernel_ms = _number(observed.get("gpu_kernel_ms"))
    checksum_equal = correctness_observed.get("cpu_control_checksum") == correctness_observed.get(
        "gpu_control_checksum"
    )
    timed_checksum_matches_correctness = observed.get("gpu_control_checksum") == correctness_observed.get(
        "gpu_control_checksum"
    )
    report.update(
        {
            "correctness_observed": correctness_observed,
            "observed": observed,
            "cpu_vs_gpu_output_equal": correctness_observed.get("mismatch_count") == 0,
            "cpu_vs_gpu_control_checksum_equal": checksum_equal,
            "timed_gpu_checksum_matches_correctness": timed_checksum_matches_correctness,
            "in_process_wall_ms": result["in_process_wall_ms"],
            "in_process_wall_ms_per_integration_batch": in_process_wall_per_batch,
            "in_process_hybrid_ms_per_integration_batch": gpu_end_to_end_ms,
            "adapter_average": {
                "cpu_ms": cpu_ms,
                "gpu_end_to_end_ms": gpu_end_to_end_ms,
                "gpu_kernel_ms": gpu_kernel_ms,
                "cpu_to_gpu_end_to_end_speedup": (
                    cpu_ms / gpu_end_to_end_ms
                    if cpu_ms is not None and gpu_end_to_end_ms is not None and gpu_end_to_end_ms > 0.0
                    else None
                ),
                "cpu_to_gpu_kernel_speedup": (
                    cpu_ms / gpu_kernel_ms
                    if cpu_ms is not None and gpu_kernel_ms is not None and gpu_kernel_ms > 0.0
                    else None
                ),
            },
            "cpu_to_in_process_wall_speedup": (
                cpu_ms / in_process_wall_per_batch
                if cpu_ms is not None and in_process_wall_per_batch > 0.0
                else None
            ),
            "next_required_evidence": (
                "direct_verilator_or_broader_hybrid_runtime_entrypoint_after_in_process_adapter_library_timing"
            ),
        }
    )
    report["status"] = (
        "in_process_entrypoint_timing_measured"
        if correctness_observed.get("status") == "adapter_correctness_passed"
        and observed.get("status") == "hybrid_entrypoint_passed"
        and report["cpu_vs_gpu_output_equal"]
        and report["cpu_vs_gpu_control_checksum_equal"]
        and report["timed_gpu_checksum_matches_correctness"]
        else "in_process_entrypoint_correctness_failed"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-report", type=Path, default=ADAPTER_REPORT)
    parser.add_argument("--mode", choices=("process", "in-process"), default="process")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        adapter = _load(args.adapter_report)
        report = (
            measure_in_process_entrypoint(adapter)
            if args.mode == "in-process"
            else measure_entrypoint(adapter)
        )
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {
        "entrypoint_timing_measured",
        "in_process_entrypoint_timing_measured",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
