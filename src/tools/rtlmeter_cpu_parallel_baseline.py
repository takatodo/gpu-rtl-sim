#!/usr/bin/env python3
"""Opt-in CPU-parallel RTLMeter baseline runner for design-CPU program cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

try:
    from .rtlmeter_stdout_cycles_observables import normalized_rtlmeter_stdout
except ImportError:  # pragma: no cover - exercised when run as a script.
    from rtlmeter_stdout_cycles_observables import normalized_rtlmeter_stdout


SURFACE = "rtlmeter_cpu_parallel_baseline"
OPT_IN_ENV = "RTLMETER_CPU_PARALLEL_BASELINE_EXECUTE"
DEFAULT_REPORT = "reports/rtlmeter_cpu_parallel_baseline.json"
DEFAULT_ARTIFACT_ROOT = "artifacts/rtlmeter_cpu_parallel_baseline"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _display_path(path: str | Path, repo_root: Path) -> str:
    p = Path(path)
    try:
        return p.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>"


def _report_arg_path(path: str | Path, repo_root: Path) -> str:
    p = Path(path)
    if p.is_absolute():
        return _display_path(p, repo_root)
    if ".." in p.parts:
        return "<local-relative-parent-path>"
    return p.as_posix()


def _command_for_report(command: Sequence[str], repo_root: Path) -> list[str]:
    sanitized = list(command)
    for option in ("--compileRoot", "--executeRoot", "--workRoot"):
        if option in sanitized:
            index = sanitized.index(option) + 1
            if index < len(sanitized):
                sanitized[index] = _report_arg_path(sanitized[index], repo_root)
    return sanitized


def _sanitize_text(text: str, repo_root: Path) -> str:
    root_text = repo_root.resolve().as_posix()
    return text.replace(root_text + "/", "").replace(root_text, ".")


def _validated_output_path(path: str | Path, *, required_root: str, default: str) -> tuple[str, list[str]]:
    raw = str(path)
    candidate = Path(raw)
    errors: list[str] = []
    if candidate.is_absolute():
        errors.append(f"{required_root}_path.absolute")
    if ".." in candidate.parts:
        errors.append(f"{required_root}_path.parent_reference")
    if not candidate.parts or candidate.parts[0] != required_root:
        errors.append(f"{required_root}_path.outside_{required_root}")
    return (default if errors else raw, errors)


def _case_slug(case: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in case).strip("_").lower()


def _case_run_specs(cases: Sequence[str]) -> list[dict[str, str]]:
    slugs = [_case_slug(case) for case in cases]
    total_by_slug = {slug: slugs.count(slug) for slug in set(slugs)}
    seen_by_slug: dict[str, int] = {}
    specs: list[dict[str, str]] = []
    for case, slug in zip(cases, slugs):
        seen_by_slug[slug] = seen_by_slug.get(slug, 0) + 1
        ordinal = seen_by_slug[slug]
        root_slug = slug if total_by_slug[slug] == 1 else f"{slug}_{ordinal}"
        specs.append(
            {
                "case": case,
                "case_instance": root_slug,
                "root_slug": root_slug,
            }
        )
    return specs


def _split_case(case: str) -> tuple[str, str, str]:
    parts = case.split(":")
    if len(parts) != 3 or not all(parts):
        raise ValueError("RTLMeter case must be formatted as <design>:<config>:<test>")
    return parts[0], parts[1], parts[2]


def execute_dir(execute_root: str | Path, case: str) -> Path:
    design, config, test = _split_case(case)
    return Path(execute_root) / design / config / "execute-0" / test


def rtlmeter_python_command(
    *,
    case: str,
    compile_root: str | Path,
    execute_root: str | Path,
    work_root: str | Path,
    timeout_minutes: int | None,
) -> list[str]:
    command = [
        "third_party/rtlmeter/venv/bin/python3",
        "-m",
        "rtlmeter.main",
        "run",
        "--cases",
        case,
        "--compileRoot",
        str(compile_root),
        "--executeRoot",
        str(execute_root),
        "--workRoot",
        str(work_root),
    ]
    if timeout_minutes is not None:
        command.extend(["--timeout", str(timeout_minutes)])
    return command


def rtlmeter_env(repo_root: Path, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if environ is None else environ
    env = dict(source)
    rtlmeter_root = repo_root / "third_party" / "rtlmeter"
    src = rtlmeter_root / "src"
    env["RTLMETER_ROOT"] = rtlmeter_root.as_posix()
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src.as_posix() if not current_pythonpath else f"{src.as_posix()}:{current_pythonpath}"
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def read_observables(execute_root: str | Path, case: str, *, repo_root: Path) -> dict[str, object]:
    directory = execute_dir(execute_root, case)
    if not directory.is_absolute():
        directory = repo_root / directory
    stdout_path = directory / "_execute" / "stdout.log"
    cycles_path = directory / "_rtlmeter_cycles.txt"
    missing = []
    if not stdout_path.is_file():
        missing.append(f"{_display_path(stdout_path, repo_root)}")
    if not cycles_path.is_file():
        missing.append(f"{_display_path(cycles_path, repo_root)}")
    if missing:
        return {
            "status": "missing_observables",
            "execute_dir": _display_path(directory, repo_root),
            "missing": missing,
        }
    normalized = normalized_rtlmeter_stdout(stdout_path.read_text(encoding="utf-8"))
    cycles = int(cycles_path.read_text(encoding="utf-8").strip())
    return {
        "status": "observables_ready",
        "execute_dir": _display_path(directory, repo_root),
        "normalized_stdout_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "rtlmeter_cycles": cycles,
    }


def _run_one(
    *,
    case: str,
    case_instance: str,
    compile_root: str,
    execute_root: str,
    work_root: str,
    timeout_minutes: int | None,
    repo_root: Path,
    env: Mapping[str, str],
    runner,
) -> dict[str, object]:
    command = rtlmeter_python_command(
        case=case,
        compile_root=compile_root,
        execute_root=execute_root,
        work_root=work_root,
        timeout_minutes=timeout_minutes,
    )
    start = time.monotonic()
    try:
        completed = runner(command, cwd=repo_root, env=dict(env), text=True, capture_output=True)
        returncode = int(completed.returncode)
    except FileNotFoundError as exc:
        returncode = 127
        completed = subprocess.CompletedProcess(command, returncode, stdout="", stderr=str(exc))
    wall_s = time.monotonic() - start
    observables = read_observables(execute_root, case, repo_root=repo_root) if returncode == 0 else None
    return {
        "case": case,
        "case_instance": case_instance,
        "command": _command_for_report(command, repo_root),
        "execute_root": execute_root,
        "work_root": work_root,
        "returncode": returncode,
        "wall_s": round(wall_s, 6),
        "passed": returncode == 0,
        "observables": observables,
    }


def _run_parallel(
    *,
    case_specs: Sequence[Mapping[str, str]],
    compile_root: str,
    execute_root: str,
    work_root: str,
    timeout_minutes: int | None,
    max_workers: int,
    repo_root: Path,
    env: Mapping[str, str],
    popen_factory=subprocess.Popen,
) -> tuple[list[dict[str, object]], float]:
    pending = list(case_specs)
    running: list[tuple[str, str, str, str, subprocess.Popen]] = []
    results: list[dict[str, object]] = []
    start = time.monotonic()

    while pending or running:
        while pending and len(running) < max_workers:
            spec = pending.pop(0)
            case = spec["case"]
            case_instance = spec["case_instance"]
            case_execute_root = str(Path(execute_root) / spec["root_slug"])
            case_work_root = str(Path(work_root) / "parallel" / spec["root_slug"])
            command = rtlmeter_python_command(
                case=case,
                compile_root=compile_root,
                execute_root=case_execute_root,
                work_root=case_work_root,
                timeout_minutes=timeout_minutes,
            )
            proc = popen_factory(
                command,
                cwd=repo_root,
                env=dict(env),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            running.append((case_instance, case, case_execute_root, case_work_root, proc))

        still_running: list[tuple[str, str, str, str, subprocess.Popen]] = []
        for case_instance, case, case_execute_root, case_work_root, proc in running:
            if proc.poll() is None:
                still_running.append((case_instance, case, case_execute_root, case_work_root, proc))
                continue
            stdout, stderr = proc.communicate()
            observables = (
                read_observables(case_execute_root, case, repo_root=repo_root)
                if int(proc.returncode) == 0
                else None
            )
            results.append(
                {
                    "case": case,
                    "case_instance": case_instance,
                    "execute_root": case_execute_root,
                    "work_root": case_work_root,
                    "returncode": int(proc.returncode),
                    "passed": int(proc.returncode) == 0,
                    "observables": observables,
                    "stdout_tail": _sanitize_text(stdout[-4000:], repo_root),
                    "stderr_tail": _sanitize_text(stderr[-4000:], repo_root),
                }
            )
        running = still_running
        if running:
            time.sleep(0.05)

    return results, time.monotonic() - start


def _compare_observables(
    serial_results: Sequence[Mapping[str, object]],
    parallel_results: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    serial_by_instance = {
        str(result.get("case_instance", result["case"])): result for result in serial_results
    }
    comparisons: list[dict[str, object]] = []
    for parallel in parallel_results:
        case = str(parallel["case"])
        case_instance = str(parallel.get("case_instance", case))
        serial = serial_by_instance.get(case_instance)
        serial_obs = serial.get("observables") if isinstance(serial, Mapping) else None
        parallel_obs = parallel.get("observables")
        match = (
            isinstance(serial_obs, Mapping)
            and isinstance(parallel_obs, Mapping)
            and serial_obs.get("status") == "observables_ready"
            and parallel_obs.get("status") == "observables_ready"
            and serial_obs.get("normalized_stdout_sha256") == parallel_obs.get("normalized_stdout_sha256")
            and serial_obs.get("rtlmeter_cycles") == parallel_obs.get("rtlmeter_cycles")
        )
        comparisons.append(
            {
                "case": case,
                "case_instance": case_instance,
                "serial_parallel_observables_match": match,
                "serial_cycles": serial_obs.get("rtlmeter_cycles") if isinstance(serial_obs, Mapping) else None,
                "parallel_cycles": parallel_obs.get("rtlmeter_cycles") if isinstance(parallel_obs, Mapping) else None,
                "serial_stdout_sha256": (
                    serial_obs.get("normalized_stdout_sha256") if isinstance(serial_obs, Mapping) else None
                ),
                "parallel_stdout_sha256": (
                    parallel_obs.get("normalized_stdout_sha256") if isinstance(parallel_obs, Mapping) else None
                ),
            }
        )
    return comparisons


def build_cpu_parallel_baseline_report(
    *,
    cases: Sequence[str],
    compile_root: str = "artifacts/design_cpu_state_parallel_probe/veer_el2_serial",
    artifact_root: str = DEFAULT_ARTIFACT_ROOT,
    max_workers: int = 2,
    timeout_minutes: int | None = 10,
    execute: bool = False,
    repo_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
    runner=subprocess.run,
    popen_factory=subprocess.Popen,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    case_list = [case for case in cases if case.strip()]
    case_specs = _case_run_specs(case_list)
    artifact_rel, artifact_errors = _validated_output_path(
        artifact_root,
        required_root="artifacts",
        default=DEFAULT_ARTIFACT_ROOT,
    )
    report: dict[str, object] = {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "opt_in_required" if not execute else "preflight_pending",
        "cases": case_list,
        "case_instances": [dict(spec) for spec in case_specs],
        "duplicate_cases_supported": True,
        "compile_root": _report_arg_path(compile_root, root),
        "artifact_root": artifact_rel,
        "max_workers": max_workers,
        "canonical_project_state_changed": False,
        "generated_report_is_source_of_truth": False,
        "gpu_execution_claimed": False,
        "speedup_claimed": False,
        "cpu_as_gpu_fallback": False,
        "commands": [],
        "serial_results": [],
        "parallel_results": [],
        "comparison": [],
        "summary": None,
        "missing_prerequisites": [],
        "non_claims": [
            "CPU-parallel baseline is not GPU execution evidence",
            "CPU-parallel throughput is a comparison floor for later GPU usefulness claims",
            "reports are generated evidence only and not source of truth",
        ],
    }

    if artifact_errors:
        report["status"] = "invalid_artifact_root"
        report["missing_prerequisites"] = artifact_errors
        return report
    if not case_list:
        report["status"] = "no_cases"
        report["missing_prerequisites"] = ["cases"]
        return report
    if max_workers < 1:
        report["status"] = "invalid_worker_count"
        report["missing_prerequisites"] = ["max_workers"]
        return report

    serial_roots = [str(Path(artifact_rel) / "serial" / spec["root_slug"]) for spec in case_specs]
    parallel_root = str(Path(artifact_rel) / "parallel")
    work_root = str(Path(artifact_rel) / "work")
    serial_work_roots = [str(Path(work_root) / "serial" / spec["root_slug"]) for spec in case_specs]
    for spec, serial_root, serial_work_root in zip(case_specs, serial_roots, serial_work_roots):
        case = spec["case"]
        report["commands"].append(
            {
                "mode": "serial",
                "case": case,
                "case_instance": spec["case_instance"],
                "command": _command_for_report(rtlmeter_python_command(
                    case=case,
                    compile_root=compile_root,
                    execute_root=serial_root,
                    work_root=serial_work_root,
                    timeout_minutes=timeout_minutes,
                ), root),
            }
        )
    for spec in case_specs:
        case = spec["case"]
        report["commands"].append(
            {
                "mode": "parallel",
                "case": case,
                "case_instance": spec["case_instance"],
                "command": _command_for_report(rtlmeter_python_command(
                    case=case,
                    compile_root=compile_root,
                    execute_root=str(Path(parallel_root) / spec["root_slug"]),
                    work_root=str(Path(work_root) / "parallel" / spec["root_slug"]),
                    timeout_minutes=timeout_minutes,
                ), root),
            }
        )

    if not execute:
        return report

    artifact_path = root / artifact_rel
    if artifact_path.exists():
        shutil.rmtree(artifact_path)

    env = rtlmeter_env(root, environ)
    serial_start = time.monotonic()
    serial_results = [
        _run_one(
            case=spec["case"],
            case_instance=spec["case_instance"],
            compile_root=compile_root,
            execute_root=serial_root,
            work_root=serial_work_root,
            timeout_minutes=timeout_minutes,
            repo_root=root,
            env=env,
            runner=runner,
        )
        for spec, serial_root, serial_work_root in zip(case_specs, serial_roots, serial_work_roots)
    ]
    serial_wall = time.monotonic() - serial_start
    parallel_results, parallel_wall = _run_parallel(
        case_specs=case_specs,
        compile_root=compile_root,
        execute_root=parallel_root,
        work_root=work_root,
        timeout_minutes=timeout_minutes,
        max_workers=max_workers,
        repo_root=root,
        env=env,
        popen_factory=popen_factory,
    )
    comparison = _compare_observables(serial_results, parallel_results)
    all_passed = all(result["passed"] for result in serial_results) and all(
        result["passed"] for result in parallel_results
    )
    all_observables_match = all(item["serial_parallel_observables_match"] for item in comparison)
    serial_sum = sum(float(result["wall_s"]) for result in serial_results)
    report.update(
        {
            "status": "passed" if all_passed and all_observables_match else "failed",
            "serial_results": serial_results,
            "parallel_results": parallel_results,
            "comparison": comparison,
            "summary": {
                "case_count": len(case_list),
                "max_workers": max_workers,
                "serial_driver_wall_s": round(serial_wall, 6),
                "serial_sum_case_wall_s": round(serial_sum, 6),
                "parallel_wall_s": round(parallel_wall, 6),
                "completed_cases_per_second_serial_sum": round(len(case_list) / serial_sum, 6)
                if serial_sum > 0
                else None,
                "completed_cases_per_second_parallel": round(len(case_list) / parallel_wall, 6)
                if parallel_wall > 0
                else None,
                "parallel_speedup_vs_serial_sum": round(serial_sum / parallel_wall, 6)
                if parallel_wall > 0
                else None,
                "parallel_efficiency": round((serial_sum / parallel_wall) / min(max_workers, len(case_list)), 6)
                if parallel_wall > 0
                else None,
                "all_runs_passed": all_passed,
                "all_observables_match": all_observables_match,
            },
        }
    )
    return report


def write_report(report: Mapping[str, object], report_path: str | Path, *, repo_root: Path) -> Path:
    path_text, errors = _validated_output_path(report_path, required_root="reports", default=DEFAULT_REPORT)
    if errors:
        raise ValueError(",".join(errors))
    path = repo_root / path_text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", required=True, help="RTLMeter cases to run, e.g. VeeR-EL2:default:cmark")
    parser.add_argument("--compile-root", default="artifacts/design_cpu_state_parallel_probe/veer_el2_serial")
    parser.add_argument("--artifact-root", default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=10, help="RTLMeter timeout in minutes")
    parser.add_argument("--execute", action="store_true", help="Run RTLMeter commands; also enabled by opt-in env")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = _repo_root()
    execute = args.execute or os.environ.get(OPT_IN_ENV) == "1"
    report = build_cpu_parallel_baseline_report(
        cases=args.cases,
        compile_root=args.compile_root,
        artifact_root=args.artifact_root,
        max_workers=args.max_workers,
        timeout_minutes=args.timeout,
        execute=execute,
        repo_root=root,
    )
    if args.write_report:
        write_report(report, args.report_out, repo_root=root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] in {"opt_in_required", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
