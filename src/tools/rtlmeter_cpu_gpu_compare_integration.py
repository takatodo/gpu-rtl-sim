#!/usr/bin/env python3
"""Fail-closed CPU/GPU compare integration for the first RTLMeter seed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from rtlmeter_cpu_gpu_compare_policy import rtlmeter_cpu_gpu_compare_policy
from rtlmeter_seed_selection import SELECTED_SEED
from rtlmeter_sidecar_contract_mapping import map_rtlmeter_case_to_sidecar_contract
from rtlmeter_verilator_command_capture import RtlmeterCommandCaptureError
from rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper


SURFACE = "rtlmeter_cpu_gpu_compare_integration"
OPT_IN_ENV = "RTLMETER_CPU_GPU_COMPARE_EXECUTE"
WRAPPER_ENV = "RTLMETER_SIDECAR_VERILATOR_WRAPPER"
DEFAULT_ARTIFACT_ROOT = Path("artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare")
TIMESTAMP_PREFIX_RE = re.compile(r"^\s*[0-9]+(?:\.[0-9]+)?\s+\|\s?")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sanitize(text: str) -> str:
    return re.sub(r"(?<!\S)/(?:home|tmp|Users|var|mnt|workspace|root)/\S+", "<local-absolute-path>", text)


def _split_seed(seed: str) -> tuple[str, str, str]:
    parts = seed.split(":")
    if len(parts) != 3:
        raise ValueError("RTLMeter execution seed must be formatted as <design>:<config>:<test>")
    return parts[0], parts[1], parts[2]


def _execute_dir(work_root: Path, seed: str) -> Path:
    design, config, test = _split_seed(seed)
    return work_root / design / config / "execute-0" / test


def _rtlmeter_command(seed: str, work_root: Path, compile_args: str = "") -> list[str]:
    command = [
        "third_party/rtlmeter/rtlmeter",
        "run",
        "--cases",
        seed,
        "--workRoot",
        work_root.as_posix(),
    ]
    if compile_args:
        command.append(f"--compileArgs={compile_args}")
    return command


def normalized_rtlmeter_stdout(text: str) -> str:
    lines = [TIMESTAMP_PREFIX_RE.sub("", line).rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def compare_rtlmeter_observables(cpu_execute_dir: Path, gpu_execute_dir: Path) -> dict[str, object]:
    cpu_stdout = normalized_rtlmeter_stdout((cpu_execute_dir / "_execute" / "stdout.log").read_text(encoding="utf-8"))
    gpu_stdout = normalized_rtlmeter_stdout((gpu_execute_dir / "_execute" / "stdout.log").read_text(encoding="utf-8"))
    cpu_cycles = int((cpu_execute_dir / "_rtlmeter_cycles.txt").read_text(encoding="utf-8").strip())
    gpu_cycles = int((gpu_execute_dir / "_rtlmeter_cycles.txt").read_text(encoding="utf-8").strip())
    stdout_match = cpu_stdout == gpu_stdout
    cycles_match = cpu_cycles == gpu_cycles
    return {
        "status": "passed" if stdout_match and cycles_match else "failed",
        "normalized_stdout_match": stdout_match,
        "cycle_count_match": cycles_match,
        "cpu_cycles": cpu_cycles,
        "gpu_cycles": gpu_cycles,
        "cpu_stdout_sha256": hashlib.sha256(cpu_stdout.encode("utf-8")).hexdigest(),
        "gpu_stdout_sha256": hashlib.sha256(gpu_stdout.encode("utf-8")).hexdigest(),
    }


def _preflight(*, repo_root: Path, sidecar_wrapper: str | None, path_env: str | None) -> list[str]:
    missing: list[str] = []
    if not (repo_root / "third_party/rtlmeter/rtlmeter").is_file():
        missing.append("third_party/rtlmeter/rtlmeter")
    if not (repo_root / "third_party/rtlmeter/venv/bin/python3").is_file():
        missing.append("third_party/rtlmeter/venv/bin/python3")
    if shutil.which("verilator", path=path_env) is None:
        missing.append("verilator in PATH")
    if not sidecar_wrapper:
        missing.append(f"{WRAPPER_ENV} executable named verilator")
    else:
        wrapper_path = Path(sidecar_wrapper)
        if wrapper_path.name != "verilator":
            missing.append(f"{WRAPPER_ENV} must point to an executable named verilator")
        if not wrapper_path.is_file():
            missing.append(f"{WRAPPER_ENV} file")
        elif not os.access(wrapper_path, os.X_OK):
            missing.append(f"{WRAPPER_ENV} executable bit")
    return missing


def _rtlmeter_execution_env(repo_root: Path, env_source: Mapping[str, str]) -> dict[str, str]:
    env = dict(env_source)
    rtlmeter_root = (repo_root / "third_party/rtlmeter").as_posix()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        rtlmeter_root if not existing_pythonpath else f"{rtlmeter_root}{os.pathsep}{existing_pythonpath}"
    )
    return env


def _run(command: list[str], *, repo_root: Path, env: Mapping[str, str], runner) -> dict[str, object]:
    completed = runner(command, cwd=repo_root, env=dict(env), text=True, capture_output=True)
    return {
        "command": command,
        "returncode": int(completed.returncode),
        "stdout": _sanitize(completed.stdout),
        "stderr": _sanitize(completed.stderr),
    }


def run_rtlmeter_cpu_gpu_compare_integration(
    *,
    seed: str = SELECTED_SEED,
    compile_args: str = "--use-gpu",
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
        "sidecar_contract": None,
        "missing_prerequisites": [],
        "ran_commands": False,
        "comparison": None,
        "sidecar_wrapper_source": None,
        "non_claims": [
            "no speedup or timing claim is made",
            "reports are generated evidence only and not source of truth",
            "CPU execution is never reported as GPU execution",
        ],
    }

    if not execute_enabled:
        return _maybe_write_report(report, root, write_report, report_rel)

    try:
        report["sidecar_contract"] = map_rtlmeter_case_to_sidecar_contract(seed, compile_args=(compile_args,))
    except RtlmeterCommandCaptureError as exc:
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

    missing = _preflight(repo_root=root, sidecar_wrapper=sidecar_wrapper, path_env=env_source.get("PATH"))
    if missing:
        report["status"] = "cannot_execute"
        report["missing_prerequisites"] = missing
        return _maybe_write_report(report, root, write_report, report_rel)

    base_env = _rtlmeter_execution_env(root, env_source)
    cpu_result = _run(cpu_command, repo_root=root, env=base_env, runner=runner)
    if cpu_result["returncode"] != 0:
        report["status"] = "cpu_execution_failed"
        report["command_results"] = {"cpu": cpu_result}
        return _maybe_write_report(report, root, write_report, report_rel)

    gpu_env = dict(base_env)
    assert sidecar_wrapper is not None
    gpu_env["PATH"] = f"{Path(sidecar_wrapper).parent}{os.pathsep}{gpu_env.get('PATH', '')}"
    gpu_result = _run(gpu_command, repo_root=root, env=gpu_env, runner=runner)
    report["ran_commands"] = True
    report["command_results"] = {"cpu": cpu_result, "gpu": gpu_result}
    if gpu_result["returncode"] != 0:
        report["status"] = "gpu_execution_failed"
        return _maybe_write_report(report, root, write_report, report_rel)

    comparison = compare_rtlmeter_observables(
        root / _execute_dir(cpu_work_root, seed),
        root / _execute_dir(gpu_work_root, seed),
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
    parser.add_argument("--seed", default=SELECTED_SEED)
    parser.add_argument("--compile-args", default="--use-gpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_rtlmeter_cpu_gpu_compare_integration(
        seed=args.seed,
        compile_args=args.compile_args,
        execute=args.execute,
        write_report=args.write_report,
        report_path=args.report_out,
    )
    print(json.dumps(report, indent=2))
    if report["status"] in {"failed", "cpu_execution_failed", "gpu_execution_failed"}:
        return 1
    if args.execute and report["status"] == "cannot_execute":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
