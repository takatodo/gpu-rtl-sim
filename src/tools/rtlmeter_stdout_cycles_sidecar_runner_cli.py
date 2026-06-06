"""Thin CLI executor for the RTLMeter stdout/cycles sidecar runner."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_stdout_cycles_execution_observation import (
        STATUS_EXECUTION_FAILED,
        STATUS_VSIM_PROXY_ENV_MISSING,
        build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation,
        rtlmeter_stdout_cycles_observable_paths,
    )
    from .rtlmeter_stdout_cycles_plan import (
        DEFAULT_COMPILE_ARGS,
        SELECTED_SEED,
        build_rtlmeter_stdout_cycles_execution_plan,
    )
    from .rtlmeter_stdout_cycles_sidecar_runner import (
        _plan_missing_context,
        _rejected_command_inputs,
        _strip_separator,
        materialize_rtlmeter_stdout_cycles_sidecar_runner_command,
    )
    from .rtlmeter_vsim_main_proxy_patch import PROXY_ENV as VSIM_SIDECAR_PROXY_ENV
    from .rtlmeter_verilator_wrapper_phase import (
        PHASE_ENV,
        PHASE_RTL_METER_RUN,
        REPO_ROOT_ENV,
        STATUS_PHASE_CLEAR,
        STATUS_PHASE_ENTER_RTL_METER_RUN,
        env_with_rtlmeter_run_phase,
        wrapper_phase_guard_report,
    )
except ImportError:  # pragma: no cover - exercised when invoked as a script.
    from rtlmeter_stdout_cycles_execution_observation import (
        STATUS_EXECUTION_FAILED,
        STATUS_VSIM_PROXY_ENV_MISSING,
        build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation,
        rtlmeter_stdout_cycles_observable_paths,
    )
    from rtlmeter_stdout_cycles_plan import (
        DEFAULT_COMPILE_ARGS,
        SELECTED_SEED,
        build_rtlmeter_stdout_cycles_execution_plan,
    )
    from rtlmeter_stdout_cycles_sidecar_runner import (
        _plan_missing_context,
        _rejected_command_inputs,
        _strip_separator,
        materialize_rtlmeter_stdout_cycles_sidecar_runner_command,
    )
    from rtlmeter_vsim_main_proxy_patch import PROXY_ENV as VSIM_SIDECAR_PROXY_ENV
    from rtlmeter_verilator_wrapper_phase import (
        PHASE_ENV,
        PHASE_RTL_METER_RUN,
        REPO_ROOT_ENV,
        STATUS_PHASE_CLEAR,
        STATUS_PHASE_ENTER_RTL_METER_RUN,
        env_with_rtlmeter_run_phase,
        wrapper_phase_guard_report,
    )


STATUS_BLOCKED_WRAPPER_PHASE = "rtlmeter_stdout_cycles_sidecar_runner_blocked_wrapper_phase_guard"


def _repo_display_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>"


def _option_value(command: list[str], option: str) -> str | None:
    for index, item in enumerate(command):
        if item == option and index + 1 < len(command):
            return command[index + 1]
        if item.startswith(f"{option}="):
            return item.split("=", 1)[1]
    return None


def _plan_from_command(command: list[str], observable_execute_dir: str) -> dict[str, object]:
    plan = build_rtlmeter_stdout_cycles_execution_plan(
        seed=_option_value(command, "--cases") or SELECTED_SEED,
        compile_args=_option_value(command, "--compileArgs") or DEFAULT_COMPILE_ARGS,
    )
    gpu_candidate = dict(plan["gpu_candidate"])
    gpu_candidate["command"] = command
    gpu_candidate["observable_execute_dir"] = observable_execute_dir
    gpu_candidate["compile_args"] = _option_value(command, "--compileArgs") or DEFAULT_COMPILE_ARGS
    plan["gpu_candidate"] = gpu_candidate
    return plan


def _run_command(command: list[str], *, repo_root: Path, env: Mapping[str, str], runner) -> dict[str, object]:
    completed = runner(command, cwd=repo_root, env=dict(env), text=True, capture_output=True)
    return {"command": command, "returncode": int(completed.returncode), "stdout": completed.stdout, "stderr": completed.stderr}


def _runner_command_result(plan: Mapping[str, object], raw_result: Mapping[str, object]) -> dict[str, object]:
    result = dict(raw_result)
    result["inner_command"] = raw_result.get("command")
    result["command"] = materialize_rtlmeter_stdout_cycles_sidecar_runner_command(plan)
    return result


def _remove_existing_observable_files(*, observable_execute_dir: str, repo_root: Path) -> None:
    for path in rtlmeter_stdout_cycles_observable_paths(observable_execute_dir, repo_root):
        if path is not None and path.is_file():
            path.unlink()


def _resolve_vsim_sidecar_proxy_target(
    *,
    repo_root: Path,
    env: Mapping[str, str],
) -> tuple[str | None, dict[str, object] | None]:
    if env.get(VSIM_SIDECAR_PROXY_ENV):
        proxy_path = Path(env[VSIM_SIDECAR_PROXY_ENV])
        if not proxy_path.is_absolute():
            proxy_path = repo_root / proxy_path
        return proxy_path.as_posix(), {
            "schema_version": 1,
            "surface": "rtlmeter_reviewed_vsim_sidecar_proxy_target",
            "status": "rtlmeter_vsim_sidecar_proxy_target_from_environment",
            "env": VSIM_SIDECAR_PROXY_ENV,
            "path": _repo_display_path(repo_root, proxy_path),
            "source": VSIM_SIDECAR_PROXY_ENV,
            "executable": proxy_path.is_file() and os.access(proxy_path, os.X_OK),
            "cpu_as_gpu_fallback": False,
            "gpu_execution_claimed": False,
            "timing_measured": False,
            "speedup_claimed": False,
        }
    return None, None


def run_rtlmeter_stdout_cycles_sidecar_runner(
    *,
    observable_execute_dir: str,
    command_argv: list[str],
    repo_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
    runner=subprocess.run,
) -> dict[str, object]:
    command = _strip_separator(command_argv)
    root = (repo_root or Path.cwd()).resolve()
    plan = _plan_from_command(command, observable_execute_dir) if command is not None else None
    command_result = None
    vsim_sidecar_proxy_target = None
    env_source = os.environ if environ is None else environ
    phase_guard = wrapper_phase_guard_report(env_source)
    if command is not None and plan is not None and not _plan_missing_context(plan) and not _rejected_command_inputs(command):
        if phase_guard["status"] == STATUS_PHASE_CLEAR:
            child_env = env_with_rtlmeter_run_phase(env_source)
            child_env[REPO_ROOT_ENV] = root.as_posix()
            proxy_path, vsim_sidecar_proxy_target = _resolve_vsim_sidecar_proxy_target(repo_root=root, env=child_env)
            if proxy_path is not None:
                child_env[VSIM_SIDECAR_PROXY_ENV] = proxy_path
                _remove_existing_observable_files(observable_execute_dir=observable_execute_dir, repo_root=root)
                raw_result = _run_command(command, repo_root=root, env=child_env, runner=runner)
                command_result = _runner_command_result(plan, raw_result)
                phase_guard = {
                    **phase_guard,
                    "status": STATUS_PHASE_ENTER_RTL_METER_RUN,
                    "child_phase": PHASE_RTL_METER_RUN,
                    "child_phase_env": PHASE_ENV,
                    "repo_root_env": REPO_ROOT_ENV,
                    "repo_root_env_present": True,
                    "vsim_sidecar_proxy_env": VSIM_SIDECAR_PROXY_ENV,
                    "vsim_sidecar_proxy_env_present": True,
                    "diagnostic": "RTLMeter runner subprocess entered the rtlmeter_run wrapper phase",
                }
    report = build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation(
        stdout_cycles_plan=plan,
        command_result=command_result,
        repo_root=root,
    )
    report["runner_source_cli_implemented"] = True
    report["vsim_sidecar_proxy_env"] = VSIM_SIDECAR_PROXY_ENV
    report["vsim_sidecar_proxy_env_present"] = bool(env_source.get(VSIM_SIDECAR_PROXY_ENV))
    report["vsim_sidecar_proxy_target"] = vsim_sidecar_proxy_target
    report["wrapper_phase_guard"] = phase_guard
    if (
        command_result is None
        and command is not None
        and plan is not None
        and not _plan_missing_context(plan)
        and not _rejected_command_inputs(command)
        and phase_guard["status"] == STATUS_PHASE_CLEAR
        and not env_source.get(VSIM_SIDECAR_PROXY_ENV)
    ):
        report["status"] = STATUS_VSIM_PROXY_ENV_MISSING
        report["missing_observables"] = []
        report["observables_ready"] = False
        report["normalized_stdout_sha256"] = None
        report["cycle_count"] = None
        report["observable_stdout_has_missing_proxy_env"] = False
        report["observable_read_skipped"] = "missing_vsim_sidecar_proxy_env_pre_execution"
    if (
        command_result is not None
        and report["status"] == STATUS_EXECUTION_FAILED
        and not env_source.get(VSIM_SIDECAR_PROXY_ENV)
        and "missing RTLMETER_VSIM_SIDECAR_PROXY" in str(command_result.get("stderr", ""))
    ):
        report["status"] = STATUS_VSIM_PROXY_ENV_MISSING
    if (
        command_result is None
        and command is not None
        and plan is not None
        and not _plan_missing_context(plan)
        and not _rejected_command_inputs(command)
        and phase_guard["status"] != STATUS_PHASE_CLEAR
    ):
        report["status"] = STATUS_BLOCKED_WRAPPER_PHASE
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observable-execute-dir", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_rtlmeter_stdout_cycles_sidecar_runner(
        observable_execute_dir=args.observable_execute_dir,
        command_argv=args.command,
    )
    print(json.dumps(report, indent=2))
    if report["status"] == "rtlmeter_stdout_cycles_sidecar_runner_observables_ready":
        return 0
    if report["status"] in {
        "rtlmeter_stdout_cycles_sidecar_runner_execution_failed",
        "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_env_missing",
    }:
        result = report.get("command_result")
        return int(result.get("returncode", 1)) if isinstance(result, Mapping) else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
