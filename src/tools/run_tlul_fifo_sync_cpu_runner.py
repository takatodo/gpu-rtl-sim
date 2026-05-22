"""Execution helpers for TL-UL FIFO sync CPU baseline gates."""

from __future__ import annotations

import statistics
import subprocess
import time
from pathlib import Path

from run_tlul_fifo_sync_cpu_exact_loop import run_exact_loop_case
from run_tlul_fifo_sync_cpu_reports import attach_gpu_comparison, gpu_runs_by_shape, parse_probe_json


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_probe_once(*, probe: Path, reset_cycles: int, post_reset_cycles: int) -> dict[str, object]:
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
    parsed = parse_probe_json(completed.stdout)
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


def run_multistate_case(
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
        run_probe_once(
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


def run_single_state_gate(*, gate: dict[str, object], probe: Path, storage_size: int) -> dict[str, object]:
    run_cfg = gate["runs"][0]
    reset_cycles = int(run_cfg["reset_cycles"])
    post_reset_cycles = int(run_cfg["post_reset_cycles"])
    reps = int(run_cfg["reps"])
    reps_out = [
        run_probe_once(
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


def run_multistate_gate(
    *,
    gate: dict[str, object],
    probe: Path,
    storage_size: int,
    gpu_scaling_report: Path,
    load_json,
) -> dict[str, object]:
    results = [
        run_multistate_case(probe=probe, run_cfg=run, storage_size=storage_size)
        for run in gate["runs"]
    ]
    results = attach_gpu_comparison(
        cpu_results=results,
        gpu_by_shape=gpu_runs_by_shape(gpu_scaling_report, load_json),
    )
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


def run_exact_loop_gate(
    *,
    gate: dict[str, object],
    mdir: Path,
    probe: Path,
    storage_size: int,
    gpu_scaling_report: Path,
    dump_dir: Path,
    load_json,
) -> dict[str, object]:
    results = [
        run_exact_loop_case(
            gate=gate,
            mdir=mdir,
            probe=probe,
            run_cfg=run,
            storage_size=storage_size,
            dump_dir=dump_dir,
            parse_probe_json=parse_probe_json,
        )
        for run in gate["runs"]
    ]
    results = attach_gpu_comparison(
        cpu_results=results,
        gpu_by_shape=gpu_runs_by_shape(gpu_scaling_report, load_json),
    )
    passed = all(bool(result["passed"]) for result in results)
    return {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if passed else "fail",
        "storage_size": storage_size,
        "cpu_final_state_dump_contract": {
            "status": "defined",
            "layout": "concat_root_storage_by_state",
            "dump_dir": str(dump_dir.relative_to(REPO_ROOT)),
            "expected_bytes_per_run": "storage_size * nstates",
        },
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


def run_selected_gate(
    *,
    exact_loop: bool,
    multi_state: bool,
    gate: dict[str, object],
    mdir: Path,
    probe: Path,
    storage_size: int,
    gpu_scaling_report: Path,
    load_json,
) -> dict[str, object]:
    if exact_loop:
        dump_dir = mdir / "cpu_exact_loop_final_states"
        dump_dir.mkdir(parents=True, exist_ok=True)
        return run_exact_loop_gate(
            gate=gate,
            mdir=mdir,
            probe=probe,
            storage_size=storage_size,
            gpu_scaling_report=gpu_scaling_report,
            dump_dir=dump_dir,
            load_json=load_json,
        )
    if multi_state:
        return run_multistate_gate(
            gate=gate,
            probe=probe,
            storage_size=storage_size,
            gpu_scaling_report=gpu_scaling_report,
            load_json=load_json,
        )
    return run_single_state_gate(gate=gate, probe=probe, storage_size=storage_size)
