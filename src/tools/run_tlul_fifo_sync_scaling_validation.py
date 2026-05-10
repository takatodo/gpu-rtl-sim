#!/usr/bin/env python3
"""Run the tlul_fifo_sync scaling validation gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from named_patch_lowering import resolve_patch_script_lines


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
RUN_VL_HYBRID = SCRIPT_DIR / "run_vl_hybrid.py"
DEFAULT_GATE = REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync.json"
DEFAULT_MDIR = REPO_ROOT / "artifacts" / "tlul_fifo_sync_obj_dir"
DEFAULT_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_scaling_validation.json"
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


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(path: Path, message: str) -> None:
    if not path.is_file():
        raise SystemExit(f"error: {message}: {path}")


def _resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _run_build(build: dict[str, object]) -> dict[str, object]:
    name = str(build["name"])
    command = str(build["command"])
    env = os.environ.copy()
    argv = shlex.split(command)
    while argv and "=" in argv[0] and not argv[0].startswith("-"):
        key, value = argv.pop(0).split("=", 1)
        env[key] = value
    if not argv:
        raise SystemExit(f"error: {name} build command is empty")
    started = time.perf_counter()
    completed = subprocess.run(argv, text=True, capture_output=True, cwd=REPO_ROOT, env=env)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    cubin = _resolve_repo_path(str(build["cubin"]))
    passed = completed.returncode == 0 and cubin.is_file()
    return {
        "name": name,
        "ptxas_opt_level": build.get("ptxas_opt_level"),
        "command": command,
        "cubin": str(cubin.relative_to(REPO_ROOT)),
        "returncode": completed.returncode,
        "elapsed_ms": elapsed_ms,
        "cubin_bytes": cubin.stat().st_size if cubin.is_file() else 0,
        "passed": passed,
        "stdout_tail": completed.stdout.splitlines()[-20:],
        "stderr_tail": completed.stderr.splitlines()[-20:],
    }


def _parse_timing_metrics(stdout: str) -> dict[str, object]:
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


def _format_gpu_event_timing(metrics: dict[str, object]) -> dict[str, object]:
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


def _format_gpu_event_timing_repeat(metrics: dict[str, object]) -> dict[str, object]:
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


def _patch_script_logical_steps(lines: list[str]) -> int:
    total = 0
    repeat_stack: list[tuple[int, int]] = []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if parts[0] == "@repeat-seq":
            if len(parts) != 2:
                raise SystemExit("error: @repeat-seq requires exactly one count")
            repeat_stack.append((int(parts[1], 0), 0))
        elif parts[0] == "@end-repeat-seq":
            if not repeat_stack:
                raise SystemExit("error: @end-repeat-seq without @repeat-seq")
            repeat_count, body_steps = repeat_stack.pop()
            expanded = repeat_count * body_steps
            if repeat_stack:
                parent_count, parent_steps = repeat_stack.pop()
                repeat_stack.append((parent_count, parent_steps + expanded))
            else:
                total += expanded
        else:
            if repeat_stack:
                repeat_count, body_steps = repeat_stack.pop()
                repeat_stack.append((repeat_count, body_steps + 1))
            else:
                total += 1
    if repeat_stack:
        raise SystemExit("error: unterminated @repeat-seq")
    return total


def _expand_gate_runs(gate: dict[str, object]) -> list[dict[str, object]]:
    if "runs" in gate:
        runs = gate["runs"]
        if not isinstance(runs, list):
            raise SystemExit("error: gate runs must be a list")
        return runs

    round_spec = gate.get("round_based_runs")
    if not isinstance(round_spec, dict):
        raise SystemExit("error: gate must define runs or round_based_runs")
    rounds = round_spec.get("rounds")
    base_runs = round_spec.get("base_runs")
    if not isinstance(rounds, list) or not all(isinstance(round_name, str) for round_name in rounds):
        raise SystemExit("error: round_based_runs.rounds must be a list of strings")
    if not isinstance(base_runs, list) or not all(isinstance(run, dict) for run in base_runs):
        raise SystemExit("error: round_based_runs.base_runs must be a list of objects")

    expanded: list[dict[str, object]] = []
    for round_index, round_name in enumerate(rounds, start=1):
        for base_run in base_runs:
            run = dict(base_run)
            run["name"] = f"{round_name}_{base_run['name']}"
            run["capture_round"] = round_name
            run["round_index"] = round_index
            expanded.append(run)
    return expanded


def _run_case(
    *,
    gate: dict[str, object],
    mdir: Path,
    run: dict[str, object],
    storage_size: int,
    dump_dir: Path,
    builds_by_name: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    name = str(run["name"])
    nstates = int(run["nstates"])
    steps = int(run["steps"])
    resident_steps = bool(run.get("resident_steps", False))
    patch_script_lines, lowering = resolve_patch_script_lines(gate=gate, run_cfg=run, mdir=mdir)
    dump_state = dump_dir / f"{name}_state.bin"
    cmd = [
        sys.executable,
        str(RUN_VL_HYBRID),
        "--mdir",
        str(mdir),
        "--nstates",
        str(nstates),
        "--steps",
        str(steps),
        "--dump-state",
        str(dump_state),
    ]
    build_name = run.get("build")
    build_result = None
    if build_name is not None:
        if builds_by_name is None or str(build_name) not in builds_by_name:
            raise SystemExit(f"error: {name} references unknown build: {build_name}")
        build_result = builds_by_name[str(build_name)]
        cmd.extend(["--cubins", str(_resolve_repo_path(str(build_result["cubin"])))])
    if resident_steps:
        cmd.append("--resident-steps")
    timing_repeats = int(run.get("timing_repeats", 1))
    if timing_repeats < 1:
        raise SystemExit(f"error: {name} timing_repeats must be >= 1")
    if timing_repeats > 1:
        cmd.extend(["--timing-repeats", str(timing_repeats)])
    block_size = int(run.get("block_size", 256))
    if block_size < 1:
        raise SystemExit(f"error: {name} block_size must be >= 1")
    if "block_size" in run:
        cmd.extend(["--block-size", str(block_size)])
    effective_steps = steps
    patch_script_tmp: Path | None = None
    if patch_script_lines is not None:
        if not isinstance(patch_script_lines, list) or not all(
            isinstance(line, str) for line in patch_script_lines
        ):
            raise SystemExit(f"error: {name} patch_script_lines must be a list of strings")
        effective_steps = _patch_script_logical_steps(patch_script_lines)
        fd, tmp_name = tempfile.mkstemp(prefix=f"{name}_", suffix=".patch_script")
        patch_script_tmp = Path(tmp_name)
        with open(fd, "w", encoding="utf-8") as fp:
            fp.write("\n".join(patch_script_lines))
            fp.write("\n")
        cmd.extend(["--patch-script", str(patch_script_tmp)])
    try:
        started = time.perf_counter()
        completed = subprocess.run(cmd, text=True, capture_output=True)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    finally:
        if patch_script_tmp is not None:
            patch_script_tmp.unlink(missing_ok=True)
    expected_dump_bytes = storage_size * nstates
    dump_bytes = dump_state.stat().st_size if dump_state.is_file() else 0
    passed = completed.returncode == 0 and dump_bytes == expected_dump_bytes
    states_per_second = (
        (nstates * effective_steps) / (elapsed_ms / 1000.0) if elapsed_ms > 0 else None
    )
    timing_metrics = _parse_timing_metrics(completed.stdout)
    gpu_event_timing = _format_gpu_event_timing(timing_metrics)
    gpu_event_timing_repeat = _format_gpu_event_timing_repeat(timing_metrics)
    return {
        "name": name,
        "capture_round": run.get("capture_round"),
        "round_index": run.get("round_index"),
        "role": run.get("role"),
        "comparison_pair": run.get("comparison_pair"),
        "variant": run.get("variant"),
        "nstates": nstates,
        "steps": effective_steps,
        "requested_steps": steps,
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
        "states_per_second": states_per_second,
        "timing_metrics": timing_metrics,
        "gpu_event_timing": gpu_event_timing,
        "gpu_event_timing_repeat": gpu_event_timing_repeat,
        "gpu_kernel_time_ms_total": timing_metrics["gpu_kernel_time_ms_total"],
        "gpu_kernel_time_ms_per_launch": timing_metrics["gpu_kernel_time_ms_per_launch"],
        "gpu_kernel_time_us_per_state": timing_metrics["gpu_kernel_time_us_per_state"],
        "gpu_kernel_time_repeat_count": timing_metrics["gpu_kernel_time_repeat_count"],
        "gpu_kernel_time_ms_total_min": timing_metrics["gpu_kernel_time_ms_total_min"],
        "gpu_kernel_time_ms_total_median": timing_metrics["gpu_kernel_time_ms_total_median"],
        "gpu_kernel_time_ms_total_max": timing_metrics["gpu_kernel_time_ms_total_max"],
        "gpu_kernel_time_ms_total_samples": timing_metrics["gpu_kernel_time_ms_total_samples"],
        "host_wall_time_ms": timing_metrics["host_wall_time_ms"],
        "dump_state": str(dump_state.relative_to(REPO_ROOT)),
        "dump_bytes": dump_bytes,
        "expected_dump_bytes": expected_dump_bytes,
        "passed": passed,
        "stdout_tail": completed.stdout.splitlines()[-20:],
        "stderr_tail": completed.stderr.splitlines()[-20:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--mdir", type=Path, default=DEFAULT_MDIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    gate_path = args.gate.resolve()
    mdir = args.mdir.resolve()
    json_out = args.json_out.resolve()
    _require_file(gate_path, "gate config not found")
    _require_file(RUN_VL_HYBRID, "run_vl_hybrid.py not found")
    meta_path = mdir / "vl_batch_gpu.meta.json"
    _require_file(meta_path, "GPU meta not found; run README build flow first")

    gate = _load_json(gate_path)
    meta = _load_json(meta_path)
    storage_size = int(meta["storage_size"])
    dump_dir = mdir / "scaling_validation"
    dump_dir.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)

    build_results = [_run_build(build) for build in gate.get("builds", [])]
    builds_by_name = {str(build["name"]): build for build in build_results}
    builds_passed = all(bool(build["passed"]) for build in build_results)
    gate_runs = _expand_gate_runs(gate)
    results = [
        _run_case(
            gate=gate,
            mdir=mdir,
            run=run,
            storage_size=storage_size,
            dump_dir=dump_dir,
            builds_by_name=builds_by_name,
        )
        for run in gate_runs
    ]
    runs_passed = all(bool(result["passed"]) for result in results)
    passed = builds_passed and runs_passed
    report = {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if passed else "fail",
        "storage_size": storage_size,
        "resident_steps": any(bool(run.get("resident_steps", False)) for run in gate_runs),
        "builds": build_results,
        "runs": results,
        "acceptance": {
            "all_required_builds_passed": builds_passed,
            "all_required_runs_passed": runs_passed,
            "correctness_policy": gate.get("correctness_policy"),
            "performance_policy": gate.get("performance_policy"),
        },
        "non_claims": gate.get("performance_policy", gate.get("correctness_policy", {})).get(
            "non_claims", []
        ),
    }
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {json_out.relative_to(REPO_ROOT)}")
    print(json.dumps({"status": report["status"], "runs": results}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
