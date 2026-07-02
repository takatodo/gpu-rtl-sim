"""Run dry-run checks for the NVDLA hot-SS measurement plan.

This verifies the planned template commands without running the repeat-median
measurements. It is an execution-preflight report only and does not claim new
timing or speedup evidence.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


DEFAULT_PLAN = Path("reports/rtlmeter_nvdla_hot_ss_measurement_plan.json")
Runner = Callable[[Sequence[str], Mapping[str, str], Path], subprocess.CompletedProcess[str]]


def _load_json(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_command(command: object) -> tuple[dict[str, str], list[str]]:
    if not isinstance(command, list) or not command:
        raise ValueError("dry_run command must be a non-empty list")
    env: dict[str, str] = {}
    argv: list[str] = []
    for index, part in enumerate(command):
        if not isinstance(part, str):
            raise ValueError("dry_run command entries must be strings")
        if index == 0 and "=" in part and not part.startswith("-"):
            name, value = part.split("=", 1)
            env[name] = value
        else:
            argv.append(part)
    if not argv:
        raise ValueError("dry_run command did not include an executable argv")
    return env, argv


def _default_runner(argv: Sequence[str], env_update: Mapping[str, str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_update)
    return subprocess.run(
        list(argv),
        cwd=repo_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_dry_run_plan(repo_root: Path, *, plan_path: Path = DEFAULT_PLAN, runner: Runner | None = None) -> dict[str, Any]:
    resolved_plan = repo_root / plan_path
    plan = _load_json(resolved_plan)
    measurements = plan.get("planned_measurements")
    if not isinstance(measurements, list):
        raise ValueError("plan does not contain planned_measurements")
    run = runner or _default_runner
    results: list[dict[str, Any]] = []
    for measurement in measurements:
        if not isinstance(measurement, Mapping):
            raise ValueError("planned_measurements entries must be objects")
        commands = measurement.get("commands")
        dry_run = commands.get("dry_run") if isinstance(commands, Mapping) else None
        env_update, argv = _normalize_command(dry_run)
        completed = run(argv, env_update, repo_root)
        results.append(
            {
                "order": measurement.get("order"),
                "id": measurement.get("id"),
                "shape": measurement.get("shape"),
                "argv": list(argv),
                "env": env_update,
                "exit_code": completed.returncode,
                "passed": completed.returncode == 0,
                "stdout_tail": completed.stdout[-2000:],
                "stderr_tail": completed.stderr[-2000:],
            }
        )
    all_passed = all(result["passed"] for result in results) and bool(results)
    return {
        "schema_version": 1,
        "surface": "rtlmeter_nvdla_hot_ss_plan_dry_run",
        "status": "passed" if all_passed else "failed",
        "source_plan": _display_path(resolved_plan, repo_root=repo_root),
        "target": plan.get("target"),
        "dry_run_count": len(results),
        "passed_count": sum(1 for result in results if result["passed"]),
        "all_dry_runs_passed": all_passed,
        "results": results,
        "non_claims": [
            "dry_run_preflight_only",
            "no_repeat_median_measurement",
            "no_new_speedup_claim",
            "not_full_nvdla_execution",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--plan", default=DEFAULT_PLAN.as_posix(), help="NVDLA hot-SS measurement plan JSON")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to --report-out")
    parser.add_argument("--report-out", help="Report output path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        report = run_dry_run_plan(Path(args.repo_root), plan_path=Path(args.plan))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
