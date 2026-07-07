#!/usr/bin/env python3
"""Execution boundary for a PATH-selected RTLMeter Verilator wrapper."""

from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

try:
    from .rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff
    from .rtlmeter_sidecar_proxy_marker import write_rtlmeter_sidecar_proxy_marker
    from .rtlmeter_stdout_cycles_runner_adapter import build_rtlmeter_stdout_cycles_wrapper_handoff_diagnostics
    from .rtlmeter_verilator_wrapper_reentry_guard import (
        build_rtlmeter_verilator_wrapper_reentry_guard_report,
        direct_sidecar_observable_execute_dir,
        direct_sidecar_proxy_readiness,
        direct_sidecar_verilate_ready,
    )
    from .rtlmeter_verilator_wrapper_phase import PHASE_ENV, REPO_ROOT_ENV, current_wrapper_phase, env_with_sidecar_verilate_phase
    from .rtlmeter_verilator_path_wrapper import (
        STATUS_DELEGATE_TO_REAL_VERILATOR,
        STATUS_GPU_INTENT_CAPTURED_NOT_READY,
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )
except ImportError:  # pragma: no cover - exercised when invoked as a script.
    from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff
    from rtlmeter_sidecar_proxy_marker import write_rtlmeter_sidecar_proxy_marker
    from rtlmeter_stdout_cycles_runner_adapter import build_rtlmeter_stdout_cycles_wrapper_handoff_diagnostics
    from rtlmeter_verilator_wrapper_reentry_guard import (
        build_rtlmeter_verilator_wrapper_reentry_guard_report,
        direct_sidecar_observable_execute_dir,
        direct_sidecar_proxy_readiness,
        direct_sidecar_verilate_ready,
    )
    from rtlmeter_verilator_wrapper_phase import PHASE_ENV, REPO_ROOT_ENV, current_wrapper_phase, env_with_sidecar_verilate_phase
    from rtlmeter_verilator_path_wrapper import (
        STATUS_DELEGATE_TO_REAL_VERILATOR,
        STATUS_GPU_INTENT_CAPTURED_NOT_READY,
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )


SURFACE = "rtlmeter_verilator_wrapper_runtime"
REAL_VERILATOR_ENV = "RTLMETER_REAL_VERILATOR"
SIDECAR_CONTEXT_JSON_ENV = "RTLMETER_SIDECAR_CONTEXT_JSON"
WRAPPER_SELF_ENV = "RTLMETER_VERILATOR_WRAPPER_SELF"
STATUS_DELEGATED = "delegated_to_real_verilator"
STATUS_REAL_VERILATOR_MISSING = "real_verilator_missing"
STATUS_USE_GPU_NEEDS_SCHEDULE = "use_gpu_requires_explicit_sidecar_schedule"
STATUS_UNSUPPORTED_GPU_REQUEST = "unsupported_gpu_request_fail_closed"
SIDECAR_ONLY_OPTIONS_WITH_VALUES = {
    "--sim-accel",
    "--sim-accel-states",
    "--sim-accel-steps",
    "--sim-accel-shape",
}
SIDECAR_ONLY_FLAGS = {
    "--sim-accel-estimate-efficiency",
}


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except OSError:
        return left.resolve(strict=False) == right.resolve(strict=False)


def _path_entries_without_wrapper(path_env: str, wrapper_path: Path) -> list[str]:
    entries: list[str] = []
    wrapper_resolved = wrapper_path.resolve(strict=False)
    for entry in path_env.split(os.pathsep):
        if not entry:
            continue
        candidate = (Path(entry) / "verilator").resolve(strict=False)
        if _same_path(candidate, wrapper_resolved):
            continue
        entries.append(entry)
    return entries


def strip_sidecar_only_verilator_options(argv: Sequence[str]) -> list[str]:
    """Remove wrapper-only sidecar schedule options before invoking real Verilator."""

    stripped: list[str] = []
    index = 0
    while index < len(argv):
        item = str(argv[index])
        if item in SIDECAR_ONLY_OPTIONS_WITH_VALUES:
            index += 2
            continue
        if any(item.startswith(f"{option}=") for option in SIDECAR_ONLY_OPTIONS_WITH_VALUES):
            index += 1
            continue
        if item in SIDECAR_ONLY_FLAGS:
            index += 1
            continue
        stripped.append(item)
        index += 1
    return stripped


def resolve_real_verilator(*, environ: Mapping[str, str], wrapper_path: Path) -> Path | None:
    explicit = environ.get(REAL_VERILATOR_ENV)
    if explicit:
        candidate = Path(explicit)
        if _is_executable(candidate) and not _same_path(candidate, wrapper_path):
            return candidate
        return None

    for entry in _path_entries_without_wrapper(environ.get("PATH", ""), wrapper_path):
        candidate = Path(entry) / "verilator"
        if _is_executable(candidate) and not _same_path(candidate, wrapper_path):
            return candidate
    return None


def _sidecar_context_from_env(environ: Mapping[str, str]) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    raw = environ.get(SIDECAR_CONTEXT_JSON_ENV)
    if not raw:
        return None, None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, {"env": SIDECAR_CONTEXT_JSON_ENV, "error": str(exc)}
    if not isinstance(parsed, dict):
        return None, {"env": SIDECAR_CONTEXT_JSON_ENV, "error": "value must be a JSON object"}
    return {str(key): value for key, value in parsed.items()}, None


def fail_closed_report(
    argv: Sequence[str],
    *,
    sidecar_context: Mapping[str, object] | None = None,
    sidecar_context_parse_error: Mapping[str, object] | None = None,
    wrapper_phase: str | None = None,
) -> dict[str, object]:
    inspection = inspect_rtlmeter_verilator_wrapper_argv(argv)
    status = str(inspection["status"])
    handoff_metadata = None
    launcher_invocation = None
    stdout_cycles_execution_plan = None
    stdout_cycles_runner_contract = None
    stdout_cycles_runner_implementation = None
    stdout_cycles_runner_adapter_implementation = None
    authority_registry = None
    authority_registry_load_error = None
    if status == STATUS_GPU_INTENT_CAPTURED_NOT_READY:
        runtime_status = STATUS_USE_GPU_NEEDS_SCHEDULE
        diagnostic = "--use-gpu reached the wrapper, but no explicit sidecar schedule was provided"
    elif status == STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING:
        handoff_metadata = build_rtlmeter_sidecar_handoff(argv, sidecar_context=sidecar_context)
        handoff_diagnostics = build_rtlmeter_stdout_cycles_wrapper_handoff_diagnostics(
            inspection=inspection,
            handoff_metadata=handoff_metadata,
        )
        runtime_status = str(handoff_diagnostics["status"])
        diagnostic = str(handoff_diagnostics["diagnostic"])
        launcher_invocation = handoff_diagnostics["launcher_invocation"]
        authority_registry = handoff_diagnostics["sidecar_authority_registry"]
        authority_registry_load_error = handoff_diagnostics["sidecar_authority_registry_load_error"]
        stdout_cycles_execution_plan = handoff_diagnostics["stdout_cycles_execution_plan"]
        stdout_cycles_runner_contract = handoff_diagnostics["stdout_cycles_runner_contract"]
        stdout_cycles_runner_implementation = handoff_diagnostics["stdout_cycles_runner_implementation"]
        stdout_cycles_runner_adapter_implementation = handoff_diagnostics[
            "stdout_cycles_runner_adapter_implementation"
        ]
    else:
        runtime_status = STATUS_UNSUPPORTED_GPU_REQUEST
        diagnostic = str(inspection["diagnostic"])
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": runtime_status,
        "json_flow_role": "runtime_diagnostic",
        "runtime_abi": False,
        "execution_authority": False,
        "cpu_as_gpu_fallback": False,
        "delegated_to_real_verilator": False,
        "sidecar_execution_invoked": False,
        "inspection_status": status,
        "wrapper_inspection": inspection,
        "missing_required_inputs": list(inspection.get("missing_required_inputs", [])),
        "handoff_metadata": handoff_metadata,
        "launcher_invocation": launcher_invocation,
        "sidecar_authority_registry": authority_registry,
        "sidecar_authority_registry_load_error": authority_registry_load_error,
        "stdout_cycles_execution_plan": stdout_cycles_execution_plan,
        "stdout_cycles_runner_contract": stdout_cycles_runner_contract,
        "stdout_cycles_runner_implementation": stdout_cycles_runner_implementation,
        "stdout_cycles_runner_adapter_implementation": stdout_cycles_runner_adapter_implementation,
        "reentry_guard": build_rtlmeter_verilator_wrapper_reentry_guard_report(
            stdout_cycles_runner_adapter_implementation,
            wrapper_phase=wrapper_phase,
        ),
        "sidecar_context_parse_error": (
            dict(sidecar_context_parse_error) if sidecar_context_parse_error is not None else None
        ),
        "diagnostic": diagnostic,
        "non_claims": [
            "GPU intent is never delegated to CPU Verilator as a fake GPU run",
            "runtime diagnostics are not the stable sidecar ABI",
            "RTLMeter runner commands are not executed from inside the Verilator wrapper without a phase guard",
            "no speedup or correctness claim is made from this fail-closed path",
        ],
    }


def _real_verilator_missing_report(
    *,
    wrapper_phase: str | None = None,
    direct_sidecar_verilate_attempted: bool = False,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": STATUS_REAL_VERILATOR_MISSING,
        "phase_env": PHASE_ENV,
        "wrapper_phase": wrapper_phase,
        "direct_sidecar_verilate_attempted": direct_sidecar_verilate_attempted,
        "execution_authority": False,
        "cpu_as_gpu_fallback": False,
        "delegated_to_real_verilator": False,
        "sidecar_execution_invoked": False,
        "diagnostic": "no executable real Verilator was found after excluding the wrapper itself",
    }


def run_rtlmeter_verilator_wrapper(
    argv: Sequence[str],
    *,
    environ: Mapping[str, str] | None = None,
    executable: str | Path | None = None,
    runner=subprocess.run,
    stderr=None,
) -> int:
    env = dict(os.environ if environ is None else environ)
    wrapper_path = Path(env.get(WRAPPER_SELF_ENV) or executable or sys.argv[0])
    inspection = inspect_rtlmeter_verilator_wrapper_argv(argv)

    if inspection["status"] == STATUS_DELEGATE_TO_REAL_VERILATOR:
        real_verilator = resolve_real_verilator(environ=env, wrapper_path=wrapper_path)
        if real_verilator is None:
            print(json.dumps(_real_verilator_missing_report(), indent=2), file=stderr or sys.stderr)
            return 127
        completed = runner([str(real_verilator), *map(str, argv)], env=env)
        return int(completed.returncode)

    sidecar_context, context_error = _sidecar_context_from_env(env)
    wrapper_phase = current_wrapper_phase(env)
    report = fail_closed_report(
        argv,
        sidecar_context=sidecar_context,
        sidecar_context_parse_error=context_error,
        wrapper_phase=wrapper_phase,
    )
    if direct_sidecar_verilate_ready(report):
        real_verilator = resolve_real_verilator(environ=env, wrapper_path=wrapper_path)
        if real_verilator is None:
            print(
                json.dumps(
                    _real_verilator_missing_report(
                        wrapper_phase=wrapper_phase,
                        direct_sidecar_verilate_attempted=True,
                    ),
                    indent=2,
                ),
                file=stderr or sys.stderr,
            )
            return 127
        completed = runner(
            [str(real_verilator), *strip_sidecar_only_verilator_options(argv)],
            env=env_with_sidecar_verilate_phase(env),
        )
        returncode = int(completed.returncode)
        if returncode != 0:
            return returncode
        repo_root = Path(env.get(REPO_ROOT_ENV) or env.get("PWD") or Path.cwd())
        proxy_readiness = direct_sidecar_proxy_readiness(report, repo_root=repo_root, environ=env)
        write_rtlmeter_sidecar_proxy_marker(
            observable_execute_dir=direct_sidecar_observable_execute_dir(report),
            repo_root=repo_root,
            proxy_readiness=proxy_readiness,
        )
        return returncode

    print(
        json.dumps(report, indent=2),
        file=stderr or sys.stderr,
    )
    return 2


def write_rtlmeter_verilator_wrapper(path: str | Path, *, python_executable: str | None = None) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    runtime_path = Path(__file__).resolve()
    python = python_executable or sys.executable or "python3"
    target.write_text(
        "#!/bin/sh\n"
        f"{WRAPPER_SELF_ENV}=\"$0\" exec {shlex.quote(python)} {shlex.quote(str(runtime_path))} \"$@\"\n",
        encoding="utf-8",
    )
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target


def main(argv: list[str] | None = None) -> int:
    return run_rtlmeter_verilator_wrapper(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
