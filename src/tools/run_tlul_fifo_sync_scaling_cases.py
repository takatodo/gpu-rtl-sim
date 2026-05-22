from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from pathlib import Path

from run_tlul_fifo_sync_scaling_case_runner import (
    _case_build_result,
    _run_case,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
RUN_VL_HYBRID = SCRIPT_DIR / "run_vl_hybrid.py"
DEFAULT_GATE = REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync.json"
DEFAULT_MDIR = REPO_ROOT / "artifacts" / "tlul_fifo_sync_obj_dir"
DEFAULT_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_scaling_validation.json"


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


def _run_builds(gate: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], bool]:
    build_results = [_run_build(build) for build in gate.get("builds", [])]
    builds_by_name = {str(build["name"]): build for build in build_results}
    builds_passed = all(bool(build["passed"]) for build in build_results)
    return build_results, builds_by_name, builds_passed


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


def _run_gate_cases(
    *,
    gate: dict[str, object],
    mdir: Path,
    storage_size: int,
    dump_dir: Path,
    builds_by_name: dict[str, dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], bool]:
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
    return gate_runs, results, runs_passed


def _scaling_report(
    *,
    gate: dict[str, object],
    storage_size: int,
    gate_runs: list[dict[str, object]],
    build_results: list[dict[str, object]],
    results: list[dict[str, object]],
    builds_passed: bool,
    runs_passed: bool,
) -> dict[str, object]:
    passed = builds_passed and runs_passed
    return {
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
