"""Report parsing helpers for TL-UL FIFO sync CPU baseline flows."""

from __future__ import annotations

import json
from pathlib import Path


def parse_probe_json(stdout: str) -> dict[str, object] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def gpu_runs_by_shape(path: Path, load_json) -> dict[tuple[int, int], dict[str, object]]:
    if not path.is_file():
        return {}
    report = load_json(path)
    runs = report.get("runs", [])
    if not isinstance(runs, list):
        return {}
    out: dict[tuple[int, int], dict[str, object]] = {}
    for run in runs:
        if isinstance(run, dict):
            out[(int(run["nstates"]), int(run["steps"]))] = run
    return out


def attach_gpu_comparison(
    *,
    cpu_results: list[dict[str, object]],
    gpu_by_shape: dict[tuple[int, int], dict[str, object]],
) -> list[dict[str, object]]:
    compared: list[dict[str, object]] = []
    for result in cpu_results:
        shape = (int(result["nstates"]), int(result["steps"]))
        gpu = gpu_by_shape.get(shape)
        if gpu is None:
            result["gpu_comparison"] = None
            compared.append(result)
            continue
        cpu_sps = result.get("states_per_second")
        gpu_sps = gpu.get("states_per_second")
        throughput_ratio = (
            float(gpu_sps) / float(cpu_sps)
            if cpu_sps is not None and gpu_sps is not None and float(cpu_sps) > 0
            else None
        )
        result["gpu_comparison"] = {
            "gpu_elapsed_ms": gpu.get("elapsed_ms"),
            "gpu_states_per_second": gpu_sps,
            "cpu_states_per_second": cpu_sps,
            "gpu_over_cpu_throughput_ratio": throughput_ratio,
        }
        compared.append(result)
    return compared
