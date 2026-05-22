"""Timing metric parsing helpers for TL-UL FIFO sync scaling validation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


GPU_KERNEL_TIME_RE = re.compile(
    r"^gpu_kernel_time_ms:\s+total=(?P<total>[0-9.]+)\s+per_launch=(?P<per_launch>[0-9.]+)"
)
GPU_KERNEL_PER_STATE_RE = re.compile(r"^gpu_kernel_time:\s+per_state=(?P<per_state>[0-9.]+)\s+us")
GPU_KERNEL_REPEAT_RE = re.compile(
    r"^gpu_kernel_time_repeat_ms:\s+count=(?P<count>[0-9]+)\s+"
    r"min=(?P<min>[0-9.]+)\s+median=(?P<median>[0-9.]+)\s+"
    r"max=(?P<max>[0-9.]+)\s+samples=(?P<samples>[0-9.,]+)"
)
WALL_TIME_RE = re.compile(r"^wall_time_ms:\s+(?P<wall>[0-9.]+)")


def parse_timing_metrics(stdout: str) -> dict[str, object]:
    metrics: dict[str, object] = {
        "gpu_kernel_time_ms_total": None,
        "gpu_kernel_time_ms_per_launch": None,
        "gpu_kernel_time_us_per_state": None,
        "host_wall_time_ms": None,
        "gpu_kernel_time_repeat_count": None,
        "gpu_kernel_time_ms_total_min": None,
        "gpu_kernel_time_ms_total_median": None,
        "gpu_kernel_time_ms_total_max": None,
        "gpu_kernel_time_ms_total_samples": [],
    }
    for line in stdout.splitlines():
        kernel_match = GPU_KERNEL_TIME_RE.match(line)
        if kernel_match:
            metrics["gpu_kernel_time_ms_total"] = float(kernel_match.group("total"))
            metrics["gpu_kernel_time_ms_per_launch"] = float(kernel_match.group("per_launch"))
            continue
        per_state_match = GPU_KERNEL_PER_STATE_RE.match(line)
        if per_state_match:
            metrics["gpu_kernel_time_us_per_state"] = float(per_state_match.group("per_state"))
            continue
        repeat_match = GPU_KERNEL_REPEAT_RE.match(line)
        if repeat_match:
            metrics["gpu_kernel_time_repeat_count"] = int(repeat_match.group("count"))
            metrics["gpu_kernel_time_ms_total_min"] = float(repeat_match.group("min"))
            metrics["gpu_kernel_time_ms_total_median"] = float(repeat_match.group("median"))
            metrics["gpu_kernel_time_ms_total_max"] = float(repeat_match.group("max"))
            metrics["gpu_kernel_time_ms_total_samples"] = [
                float(part) for part in repeat_match.group("samples").split(",") if part
            ]
            continue
        wall_match = WALL_TIME_RE.match(line)
        if wall_match:
            metrics["host_wall_time_ms"] = float(wall_match.group("wall"))
    return metrics


def format_gpu_event_timing(metrics: dict[str, object]) -> dict[str, object]:
    available = (
        metrics["gpu_kernel_time_ms_total"] is not None
        and metrics["gpu_kernel_time_ms_per_launch"] is not None
        and metrics["gpu_kernel_time_us_per_state"] is not None
    )
    return {
        "available": available,
        "source": "run_vl_hybrid stdout",
        "total_ms": metrics["gpu_kernel_time_ms_total"],
        "per_launch_ms": metrics["gpu_kernel_time_ms_per_launch"],
        "per_state_us": metrics["gpu_kernel_time_us_per_state"],
        "reported_wall_time_ms": metrics["host_wall_time_ms"],
    }


def format_gpu_event_timing_repeat(metrics: dict[str, object]) -> dict[str, object]:
    count = metrics["gpu_kernel_time_repeat_count"]
    samples = metrics["gpu_kernel_time_ms_total_samples"]
    available = isinstance(count, int) and count > 1 and isinstance(samples, list)
    return {
        "available": available,
        "source": "run_vl_hybrid stdout",
        "count": count,
        "total_ms_samples": samples,
        "total_ms_min": metrics["gpu_kernel_time_ms_total_min"],
        "total_ms_median": metrics["gpu_kernel_time_ms_total_median"],
        "total_ms_max": metrics["gpu_kernel_time_ms_total_max"],
    }


def case_result_payload(
    *,
    repo_root: Path,
    run: dict[str, object],
    build_name: object,
    build_result: dict[str, object] | None,
    nstates: int,
    requested_steps: int,
    effective_steps: int,
    resident_steps: bool,
    timing_repeats: int,
    block_size: int,
    patch_script_lines: object,
    lowering: dict[str, object],
    completed: subprocess.CompletedProcess[str],
    elapsed_ms: float,
    dump_state: Path,
    dump_bytes: int,
    expected_dump_bytes: int,
    passed: bool,
    timing_metrics: dict[str, object],
) -> dict[str, object]:
    return {
        "name": str(run["name"]),
        "capture_round": run.get("capture_round"),
        "round_index": run.get("round_index"),
        "role": run.get("role"),
        "comparison_pair": run.get("comparison_pair"),
        "variant": run.get("variant"),
        "nstates": nstates,
        "steps": effective_steps,
        "requested_steps": requested_steps,
        "resident_steps": resident_steps,
        "timing_repeats": timing_repeats,
        "block_size": block_size,
        "build": build_name,
        "ptxas_opt_level": build_result.get("ptxas_opt_level") if build_result else None,
        "cubin": build_result.get("cubin") if build_result else None,
        "patch_script_line_count": len(patch_script_lines) if isinstance(patch_script_lines, list) else 0,
        "patch_script_lowering": lowering,
        "returncode": completed.returncode,
        "elapsed_ms": elapsed_ms,
        "states_per_second": (nstates * effective_steps) / (elapsed_ms / 1000.0) if elapsed_ms > 0 else None,
        "timing_metrics": timing_metrics,
        "gpu_event_timing": format_gpu_event_timing(timing_metrics),
        "gpu_event_timing_repeat": format_gpu_event_timing_repeat(timing_metrics),
        "gpu_kernel_time_ms_total": timing_metrics["gpu_kernel_time_ms_total"],
        "gpu_kernel_time_ms_per_launch": timing_metrics["gpu_kernel_time_ms_per_launch"],
        "gpu_kernel_time_us_per_state": timing_metrics["gpu_kernel_time_us_per_state"],
        "gpu_kernel_time_repeat_count": timing_metrics["gpu_kernel_time_repeat_count"],
        "gpu_kernel_time_ms_total_min": timing_metrics["gpu_kernel_time_ms_total_min"],
        "gpu_kernel_time_ms_total_median": timing_metrics["gpu_kernel_time_ms_total_median"],
        "gpu_kernel_time_ms_total_max": timing_metrics["gpu_kernel_time_ms_total_max"],
        "gpu_kernel_time_ms_total_samples": timing_metrics["gpu_kernel_time_ms_total_samples"],
        "host_wall_time_ms": timing_metrics["host_wall_time_ms"],
        "dump_state": str(dump_state.relative_to(repo_root)),
        "dump_bytes": dump_bytes,
        "expected_dump_bytes": expected_dump_bytes,
        "passed": passed,
        "stdout_tail": completed.stdout.splitlines()[-20:],
        "stderr_tail": completed.stderr.splitlines()[-20:],
    }
