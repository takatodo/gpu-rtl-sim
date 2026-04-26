#!/usr/bin/env python3
"""Run the tlul_fifo_sync CPU baseline timing gate."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_GATE = REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_baseline.json"
DEFAULT_MULTISTATE_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_multistate_baseline.json"
)
DEFAULT_EXACT_LOOP_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_exact_loop_baseline.json"
)
DEFAULT_MDIR = REPO_ROOT / "artifacts" / "tlul_fifo_sync_obj_dir"
DEFAULT_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_cpu_baseline.json"
DEFAULT_MULTISTATE_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_cpu_multistate_baseline.json"
DEFAULT_EXACT_LOOP_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_cpu_exact_loop_baseline.json"
DEFAULT_GPU_SCALING_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_scaling_validation.json"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(path: Path, message: str) -> None:
    if not path.is_file():
        raise SystemExit(f"error: {message}: {path}")


def _parse_probe_json(stdout: str) -> dict[str, object] | None:
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


def _run_probe_once(*, probe: Path, reset_cycles: int, post_reset_cycles: int) -> dict[str, object]:
    cmd = [
        str(probe),
        "--reset-cycles",
        str(reset_cycles),
        "--post-reset-cycles",
        str(post_reset_cycles),
    ]
    started = time.perf_counter()
    completed = subprocess.run(cmd, text=True, capture_output=True)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    parsed = _parse_probe_json(completed.stdout)
    constructor_ok = bool(parsed and parsed.get("constructor_ok") is True)
    root_size = int(parsed.get("root_size", 0)) if parsed else 0
    return {
        "returncode": completed.returncode,
        "elapsed_ms": elapsed_ms,
        "constructor_ok": constructor_ok,
        "root_size": root_size,
        "stdout_tail": completed.stdout.splitlines()[-20:],
        "stderr_tail": completed.stderr.splitlines()[-20:],
    }


def _run_multistate_case(
    *,
    probe: Path,
    run_cfg: dict[str, object],
    storage_size: int,
) -> dict[str, object]:
    nstates = int(run_cfg["nstates"])
    steps = int(run_cfg["steps"])
    reset_cycles = int(run_cfg["reset_cycles"])
    post_reset_cycles = int(run_cfg["post_reset_cycles"])
    started = time.perf_counter()
    states = [
        _run_probe_once(
            probe=probe,
            reset_cycles=reset_cycles,
            post_reset_cycles=post_reset_cycles,
        )
        for _ in range(nstates)
    ]
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    passed = all(
        int(state["returncode"]) == 0
        and bool(state["constructor_ok"])
        and int(state["root_size"]) == storage_size
        for state in states
    )
    states_per_second = (nstates * steps) / (elapsed_ms / 1000.0) if elapsed_ms > 0 else None
    return {
        "name": str(run_cfg["name"]),
        "nstates": nstates,
        "steps": steps,
        "reset_cycles": reset_cycles,
        "post_reset_cycles": post_reset_cycles,
        "elapsed_ms": elapsed_ms,
        "states_per_second": states_per_second,
        "state_count": len(states),
        "passed": passed,
        "state_summaries": states,
    }


def _run_exact_loop_case(
    *,
    probe: Path,
    run_cfg: dict[str, object],
    storage_size: int,
) -> dict[str, object]:
    nstates = int(run_cfg["nstates"])
    steps = int(run_cfg["steps"])
    reset_cycles = int(run_cfg["reset_cycles"])
    post_reset_cycles = int(run_cfg["post_reset_cycles"])
    cmd = [
        str(probe),
        "--reset-cycles",
        str(reset_cycles),
        "--post-reset-cycles",
        str(post_reset_cycles),
        "--repeat-states",
        str(nstates),
        "--repeat-eval-steps",
        str(steps),
    ]
    completed = subprocess.run(cmd, text=True, capture_output=True)
    parsed = _parse_probe_json(completed.stdout)
    elapsed_ms = float(parsed.get("elapsed_ms", 0.0)) if parsed else 0.0
    states_per_second = (
        float(parsed.get("state_steps_per_second", parsed.get("states_per_second", 0.0)))
        if parsed
        else None
    )
    constructor_ok = bool(parsed and parsed.get("constructor_ok") is True)
    root_size = int(parsed.get("root_size", 0)) if parsed else 0
    passed = completed.returncode == 0 and constructor_ok and root_size == storage_size
    return {
        "name": str(run_cfg["name"]),
        "nstates": nstates,
        "steps": steps,
        "reset_cycles": reset_cycles,
        "post_reset_cycles": post_reset_cycles,
        "returncode": completed.returncode,
        "elapsed_ms": elapsed_ms,
        "states_per_second": states_per_second,
        "constructor_ok": constructor_ok,
        "root_size": root_size,
        "throughput_unit": "state_steps_per_second",
        "passed": passed,
        "stdout_tail": completed.stdout.splitlines()[-20:],
        "stderr_tail": completed.stderr.splitlines()[-20:],
    }


def _gpu_runs_by_shape(path: Path) -> dict[tuple[int, int], dict[str, object]]:
    if not path.is_file():
        return {}
    report = _load_json(path)
    runs = report.get("runs", [])
    if not isinstance(runs, list):
        return {}
    out: dict[tuple[int, int], dict[str, object]] = {}
    for run in runs:
        if isinstance(run, dict):
            out[(int(run["nstates"]), int(run["steps"]))] = run
    return out


def _attach_gpu_comparison(
    *,
    cpu_results: list[dict[str, object]],
    gpu_scaling_report: Path,
) -> list[dict[str, object]]:
    gpu_by_shape = _gpu_runs_by_shape(gpu_scaling_report)
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


def _run_single_state_gate(*, gate: dict[str, object], probe: Path, storage_size: int) -> dict[str, object]:
    run_cfg = gate["runs"][0]
    reset_cycles = int(run_cfg["reset_cycles"])
    post_reset_cycles = int(run_cfg["post_reset_cycles"])
    reps = int(run_cfg["reps"])
    reps_out = [
        _run_probe_once(
            probe=probe,
            reset_cycles=reset_cycles,
            post_reset_cycles=post_reset_cycles,
        )
        for _ in range(reps)
    ]
    elapsed = [float(rep["elapsed_ms"]) for rep in reps_out]
    all_passed = all(
        int(rep["returncode"]) == 0
        and bool(rep["constructor_ok"])
        and int(rep["root_size"]) == storage_size
        for rep in reps_out
    )
    return {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if all_passed else "fail",
        "storage_size": storage_size,
        "reset_cycles": reset_cycles,
        "post_reset_cycles": post_reset_cycles,
        "reps": reps_out,
        "timing": {
            "rep_count": reps,
            "median_elapsed_ms": statistics.median(elapsed),
            "min_elapsed_ms": min(elapsed),
            "max_elapsed_ms": max(elapsed),
        },
        "acceptance": {
            "all_reps_passed": all_passed,
            "policy": gate["acceptance"],
        },
        "comparison_policy": gate["comparison_policy"],
    }


def _run_multistate_gate(
    *,
    gate: dict[str, object],
    probe: Path,
    storage_size: int,
    gpu_scaling_report: Path,
) -> dict[str, object]:
    results = [
        _run_multistate_case(probe=probe, run_cfg=run, storage_size=storage_size)
        for run in gate["runs"]
    ]
    results = _attach_gpu_comparison(cpu_results=results, gpu_scaling_report=gpu_scaling_report)
    passed = all(bool(result["passed"]) for result in results)
    return {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if passed else "fail",
        "storage_size": storage_size,
        "runs": results,
        "acceptance": {
            "all_required_runs_passed": passed,
            "policy": gate["acceptance"],
        },
        "comparison_policy": gate["comparison_policy"],
        "source_gpu_scaling_report": (
            str(gpu_scaling_report.relative_to(REPO_ROOT)) if gpu_scaling_report.is_file() else None
        ),
}


def _run_exact_loop_gate(
    *,
    gate: dict[str, object],
    probe: Path,
    storage_size: int,
    gpu_scaling_report: Path,
) -> dict[str, object]:
    results = [
        _run_exact_loop_case(probe=probe, run_cfg=run, storage_size=storage_size)
        for run in gate["runs"]
    ]
    results = _attach_gpu_comparison(cpu_results=results, gpu_scaling_report=gpu_scaling_report)
    passed = all(bool(result["passed"]) for result in results)
    return {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if passed else "fail",
        "storage_size": storage_size,
        "runs": results,
        "acceptance": {
            "all_required_runs_passed": passed,
            "policy": gate["acceptance"],
        },
        "comparison_policy": gate["comparison_policy"],
        "source_gpu_scaling_report": (
            str(gpu_scaling_report.relative_to(REPO_ROOT)) if gpu_scaling_report.is_file() else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--mdir", type=Path, default=DEFAULT_MDIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--multi-state", action="store_true")
    parser.add_argument("--exact-loop", action="store_true")
    parser.add_argument("--gpu-scaling-report", type=Path, default=DEFAULT_GPU_SCALING_REPORT)
    parser.add_argument(
        "--probe",
        type=Path,
        help="Host probe binary; defaults to <mdir>/tlul_slice_host_probe for existing TL-UL flows",
    )
    args = parser.parse_args()

    if args.multi_state and args.exact_loop:
        raise SystemExit("error: choose only one of --multi-state or --exact-loop")
    if args.exact_loop and args.gate == DEFAULT_GATE:
        gate_path = DEFAULT_EXACT_LOOP_GATE.resolve()
    elif args.multi_state and args.gate == DEFAULT_GATE:
        gate_path = DEFAULT_MULTISTATE_GATE.resolve()
    else:
        gate_path = args.gate.resolve()
    mdir = args.mdir.resolve()
    if args.exact_loop and args.json_out == DEFAULT_REPORT:
        json_out = DEFAULT_EXACT_LOOP_REPORT.resolve()
    elif args.multi_state and args.json_out == DEFAULT_REPORT:
        json_out = DEFAULT_MULTISTATE_REPORT.resolve()
    else:
        json_out = args.json_out.resolve()
    gpu_scaling_report = args.gpu_scaling_report.resolve()
    _require_file(gate_path, "CPU baseline gate config not found")
    probe = args.probe.resolve() if args.probe else mdir / "tlul_slice_host_probe"
    meta_path = mdir / "vl_batch_gpu.meta.json"
    _require_file(probe, "host probe not found; run the matching README host build first")
    _require_file(meta_path, "GPU meta not found; run README GPU build first")

    gate = _load_json(gate_path)
    meta = _load_json(meta_path)
    storage_size = int(meta["storage_size"])
    json_out.parent.mkdir(parents=True, exist_ok=True)

    if args.exact_loop:
        report = _run_exact_loop_gate(
            gate=gate,
            probe=probe,
            storage_size=storage_size,
            gpu_scaling_report=gpu_scaling_report,
        )
    elif args.multi_state:
        report = _run_multistate_gate(
            gate=gate,
            probe=probe,
            storage_size=storage_size,
            gpu_scaling_report=gpu_scaling_report,
        )
    else:
        report = _run_single_state_gate(gate=gate, probe=probe, storage_size=storage_size)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {json_out.relative_to(REPO_ROOT)}")
    print(json.dumps({"status": report["status"], "gate": report["gate"]}, indent=2))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
