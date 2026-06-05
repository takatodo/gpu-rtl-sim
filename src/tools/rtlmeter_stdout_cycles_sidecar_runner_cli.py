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
    env_source = os.environ if environ is None else environ
    phase_guard = wrapper_phase_guard_report(env_source)
    if command is not None and plan is not None and not _plan_missing_context(plan) and not _rejected_command_inputs(command):
        if phase_guard["status"] == STATUS_PHASE_CLEAR:
            child_env = env_with_rtlmeter_run_phase(env_source)
            child_env[REPO_ROOT_ENV] = root.as_posix()
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
                "vsim_sidecar_proxy_env_present": bool(child_env.get(VSIM_SIDECAR_PROXY_ENV)),
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
    report["wrapper_phase_guard"] = phase_guard
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
    if report["status"] == "rtlmeter_stdout_cycles_sidecar_runner_execution_failed":
        result = report.get("command_result")
        return int(result.get("returncode", 1)) if isinstance(result, Mapping) else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
