#!/usr/bin/env python3
"""Fail-closed CPU/GPU compare integration for the first RTLMeter seed."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from rtlmeter_cpu_gpu_compare_diagnostics import (
    BLOCKER_GPU_RUNNER_EXECUTION_FAILED,
    BLOCKER_REAL_VERILATOR_NOT_SIDECAR_CAPABLE,
    BLOCKER_RTL_METER_VSIM_OBSERVABLES_MISSING,
    BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_ENV_MISSING,
    REAL_VERILATOR_PREFLIGHT_BLOCKED,
    REAL_VERILATOR_PREFLIGHT_MISSING,
    REAL_VERILATOR_PREFLIGHT_SELECTED,
    REAL_VERILATOR_PREFLIGHT_SURFACE,
    _compile_arg_tokens,
    _path_with_wrapper_first,
    _preflight,
    _read_optional_log,
    _rtlmeter_execution_env,
    _sanitize,
    build_real_verilator_preflight,
    classify_gpu_failure_blocker,
)
from rtlmeter_cpu_gpu_compare_policy import rtlmeter_cpu_gpu_compare_policy
from rtlmeter_seed_selection import SELECTED_SEED
from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_context_candidate
from rtlmeter_stdout_cycles_plan import (
    DEFAULT_ARTIFACT_ROOT,
    DEFAULT_AUTHORITY_REGISTRY,
    DEFAULT_COMPILE_ARGS,
    WRAPPER_ENV,
    build_rtlmeter_stdout_cycles_execution_plan,
    rtlmeter_command as _rtlmeter_command,
    rtlmeter_compile_dir as _compile_dir,
    rtlmeter_execute_dir as _execute_dir,
)
from rtlmeter_stdout_cycles_execution_observation import (
    STATUS_OUTPUTS_MISSING,
    STATUS_OBSERVABLES_READY,
    build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation,
)
from rtlmeter_stdout_cycles_observables import compare_rtlmeter_observables, required_observable_files_missing
from rtlmeter_stdout_cycles_sidecar_runner import materialize_rtlmeter_stdout_cycles_sidecar_runner_command
from rtlmeter_verilator_command_capture import RtlmeterCommandCaptureError
from rtlmeter_verilator_wrapper_runtime import (
    REAL_VERILATOR_ENV,
    SIDECAR_CONTEXT_JSON_ENV,
    write_rtlmeter_verilator_wrapper,
)


SURFACE = "rtlmeter_cpu_gpu_compare_integration"
OPT_IN_ENV = "RTLMETER_CPU_GPU_COMPARE_EXECUTE"
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(command: list[str], *, repo_root: Path, env: Mapping[str, str], runner) -> dict[str, object]:
    try:
        completed = runner(command, cwd=repo_root, env=dict(env), text=True, capture_output=True)
    except FileNotFoundError as exc:
        return {
            "command": command,
            "returncode": 127,
            "stdout": "",
            "stderr": _sanitize(str(exc)),
        }
    return {
        "command": command,
        "returncode": int(completed.returncode),
        "stdout": _sanitize(completed.stdout),
        "stderr": _sanitize(completed.stderr),
    }


def _clean_generated_work_roots(repo_root: Path, work_roots: list[Path]) -> list[str]:
    cleaned: list[str] = []
    for work_root in work_roots:
        target = repo_root / work_root
        if target.exists():
            shutil.rmtree(target)
            cleaned.append(work_root.as_posix())
    return cleaned

def run_rtlmeter_cpu_gpu_compare_integration(
    *,
    seed: str = SELECTED_SEED,
    compile_args: str = DEFAULT_COMPILE_ARGS,
    execute: bool = False,
    write_report: bool = False,
    report_path: str | Path | None = None,
    repo_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
    runner=subprocess.run,
) -> dict[str, object]:
    root = (repo_root or _repo_root()).resolve()
    env_source = os.environ if environ is None else environ
    execute_enabled = execute or env_source.get(OPT_IN_ENV) == "1"
    policy = rtlmeter_cpu_gpu_compare_policy(seed, compile_args=compile_args)
    report_rel = str(report_path or policy["generated_report_path_rule"])
    artifact_root = DEFAULT_ARTIFACT_ROOT
    cpu_work_root = artifact_root / "cpu"
    gpu_work_root = artifact_root / "gpu"
    cpu_command = _rtlmeter_command(seed, cpu_work_root)
    gpu_command = _rtlmeter_command(seed, gpu_work_root, compile_args)
    stdout_cycles_plan = build_rtlmeter_stdout_cycles_execution_plan(
        seed=seed,
        compile_args=compile_args,
        artifact_root=artifact_root,
    )
    report: dict[str, object] = {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "opt_in_required" if not execute_enabled else "preflight_pending",
        "seed": seed,
        "compile_args": compile_args,
        "canonical_project_state_changed": False,
        "generated_report_is_source_of_truth": False,
        "report_path": report_rel,
        "report_regeneration_command": f"{OPT_IN_ENV}=1 python3 src/tools/rtlmeter_cpu_gpu_compare_integration.py --execute --write-report",
        "cpu_as_gpu_fallback": False,
        "rtlmeter_metrics_preserved": True,
        "rtlmeter_timing_conflated_with_sidecar_timing": False,
        "commands": {"cpu": cpu_command, "gpu": gpu_command},
        "compare_policy": policy["compare_policy"],
        "stdout_cycles_execution_plan": stdout_cycles_plan,
        "sidecar_contract": None,
        "sidecar_context_candidate": None,
        "real_verilator_preflight": None,
        "stdout_cycles_sidecar_runner": None,
        "missing_prerequisites": [],
        "cleaned_generated_work_roots": [],
        "ran_commands": False,
        "comparison": None,
        "sidecar_wrapper_source": None,
        "non_claims": [
            "no speedup or timing claim is made",
            "passing stdout/cycles equivalence does not claim GPU runtime execution",
            "reports are generated evidence only and not source of truth",
            "CPU execution is never reported as GPU execution",
        ],
    }

    if not execute_enabled:
        return _maybe_write_report(report, root, write_report, report_rel)

    try:
        report["sidecar_contract"] = map_rtlmeter_case_to_sidecar_contract(
            seed,
            compile_args=_compile_arg_tokens(compile_args),
            rtlmeter_root=(root / "third_party/rtlmeter").as_posix(),
        )
        report["sidecar_context_candidate"] = build_rtlmeter_sidecar_context_candidate(
            report["sidecar_contract"],
            template_or_target_registry_entry=DEFAULT_AUTHORITY_REGISTRY,
            repo_root=root,
        )
    except (RtlmeterCommandCaptureError, ValueError) as exc:
        report["status"] = "cannot_execute"
        report["missing_prerequisites"] = [_sanitize(str(exc))]
        return _maybe_write_report(report, root, write_report, report_rel)

    sidecar_wrapper = env_source.get(WRAPPER_ENV)
    if sidecar_wrapper:
        report["sidecar_wrapper_source"] = WRAPPER_ENV
    else:
        sidecar_wrapper = (root / artifact_root / "wrapper" / "verilator").as_posix()
        write_rtlmeter_verilator_wrapper(sidecar_wrapper)
        report["sidecar_wrapper_source"] = "generated_artifact_default"

    report["real_verilator_preflight"] = build_real_verilator_preflight(
        repo_root=root,
        sidecar_wrapper=sidecar_wrapper,
        environ=env_source,
    )
    missing = list(report["real_verilator_preflight"]["missing_prerequisites"])
    if missing:
        report["status"] = "cannot_execute"
        report["missing_prerequisites"] = missing
        return _maybe_write_report(report, root, write_report, report_rel)

    report["cleaned_generated_work_roots"] = _clean_generated_work_roots(root, [cpu_work_root, gpu_work_root])
    base_env = _rtlmeter_execution_env(root, env_source)
    cpu_result = _run(cpu_command, repo_root=root, env=base_env, runner=runner)
    if cpu_result["returncode"] != 0:
        report["status"] = "cpu_execution_failed"
        report["command_results"] = {"cpu": cpu_result}
        return _maybe_write_report(report, root, write_report, report_rel)

    gpu_env = dict(base_env)
    assert sidecar_wrapper is not None
    gpu_env[WRAPPER_ENV] = sidecar_wrapper
    gpu_env["PATH"] = _path_with_wrapper_first(sidecar_wrapper=sidecar_wrapper, path_env=gpu_env.get("PATH"))
    if report["sidecar_context_candidate"] is not None:
        gpu_env[SIDECAR_CONTEXT_JSON_ENV] = json.dumps(report["sidecar_context_candidate"], sort_keys=True)
    gpu_runner_command = materialize_rtlmeter_stdout_cycles_sidecar_runner_command(stdout_cycles_plan)
    assert gpu_runner_command is not None
    report["commands"]["gpu_runner"] = gpu_runner_command
    gpu_result = _run(gpu_runner_command, repo_root=root, env=gpu_env, runner=runner)
    report["ran_commands"] = True
    report["command_results"] = {"cpu": cpu_result, "gpu": gpu_result}
    report["stdout_cycles_sidecar_runner"] = build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation(
        stdout_cycles_plan=stdout_cycles_plan,
        command_result=gpu_result,
        repo_root=root,
    )
    if (
        gpu_result["returncode"] == 0
        and isinstance(report.get("stdout_cycles_sidecar_runner"), Mapping)
        and report["stdout_cycles_sidecar_runner"].get("runner_stdout_report") is None
    ):
        report["status"] = "gpu_observables_not_ready"
        report["missing_runner_report"] = "rtlmeter_stdout_cycles_sidecar_runner_json_stdout"
        return _maybe_write_report(report, root, write_report, report_rel)
    if gpu_result["returncode"] != 0:
        report["status"] = "gpu_execution_failed"
        diagnostic_log = _read_optional_log(root / _compile_dir(gpu_work_root, seed) / "_verilate" / "stdout.log")
        report["gpu_failure_diagnostic_log"] = diagnostic_log
        report["gpu_failure_blocker"] = classify_gpu_failure_blocker(
            diagnostic_log=diagnostic_log,
            runner_observation=(
                report["stdout_cycles_sidecar_runner"]
                if isinstance(report.get("stdout_cycles_sidecar_runner"), Mapping)
                else None
            ),
        )
        return _maybe_write_report(report, root, write_report, report_rel)

    if report["stdout_cycles_sidecar_runner"]["status"] == STATUS_OUTPUTS_MISSING:
        report["status"] = "observables_missing"
        report["missing_observables"] = report["stdout_cycles_sidecar_runner"]["missing_observables"]
        return _maybe_write_report(report, root, write_report, report_rel)

    cpu_execute_dir = root / _execute_dir(cpu_work_root, seed)
    gpu_execute_dir = root / _execute_dir(gpu_work_root, seed)
    missing_observables = [
        *required_observable_files_missing(cpu_execute_dir, "cpu"),
        *required_observable_files_missing(gpu_execute_dir, "gpu"),
    ]
    if missing_observables:
        report["status"] = "observables_missing"
        report["missing_observables"] = missing_observables
        return _maybe_write_report(report, root, write_report, report_rel)
    if (
        report["stdout_cycles_sidecar_runner"]["status"] != STATUS_OBSERVABLES_READY
        or not report["stdout_cycles_sidecar_runner"]["execution_performed"]
    ):
        report["status"] = "gpu_observables_not_ready"
        return _maybe_write_report(report, root, write_report, report_rel)

    comparison = compare_rtlmeter_observables(
        cpu_execute_dir,
        gpu_execute_dir,
    )
    report["comparison"] = comparison
    report["status"] = "passed" if comparison["status"] == "passed" else "failed"
    return _maybe_write_report(report, root, write_report, report_rel)


def _maybe_write_report(report: dict[str, object], repo_root: Path, write_report: bool, report_rel: str) -> dict[str, object]:
    if write_report:
        path = repo_root / report_rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help=f"Run only when explicit; {OPT_IN_ENV}=1 is also accepted.")
    parser.add_argument("--write-report", action="store_true", help="Write the generated report under reports/.")
    parser.add_argument("--report-out", help="Override report output path.")
    parser.add_argument("--seed", default=SELECTED_SEED); parser.add_argument("--compile-args", default=DEFAULT_COMPILE_ARGS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_rtlmeter_cpu_gpu_compare_integration(
        seed=args.seed, compile_args=args.compile_args, execute=args.execute,
        write_report=args.write_report, report_path=args.report_out,
    )
    print(json.dumps(report, indent=2))
    if report["status"] in {"failed", "cpu_execution_failed", "gpu_execution_failed"}: return 1
    if args.execute and report["status"] == "cannot_execute": return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
