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
    from .rtlmeter_verilator_path_wrapper import (
        STATUS_DELEGATE_TO_REAL_VERILATOR,
        STATUS_GPU_INTENT_CAPTURED_NOT_READY,
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )
except ImportError:  # pragma: no cover - exercised when invoked as a script.
    from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff
    from rtlmeter_verilator_path_wrapper import (
        STATUS_DELEGATE_TO_REAL_VERILATOR,
        STATUS_GPU_INTENT_CAPTURED_NOT_READY,
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )


SURFACE = "rtlmeter_verilator_wrapper_runtime"
REAL_VERILATOR_ENV = "RTLMETER_REAL_VERILATOR"
SIDECAR_CONTEXT_JSON_ENV = "RTLMETER_SIDECAR_CONTEXT_JSON"
STATUS_DELEGATED = "delegated_to_real_verilator"
STATUS_REAL_VERILATOR_MISSING = "real_verilator_missing"
STATUS_USE_GPU_NEEDS_SCHEDULE = "use_gpu_requires_explicit_sidecar_schedule"
STATUS_SIDECAR_EXECUTION_NOT_IMPLEMENTED = "sidecar_schedule_captured_execution_not_implemented"
STATUS_UNSUPPORTED_GPU_REQUEST = "unsupported_gpu_request_fail_closed"


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
) -> dict[str, object]:
    inspection = inspect_rtlmeter_verilator_wrapper_argv(argv)
    status = str(inspection["status"])
    handoff_metadata = None
    if status == STATUS_GPU_INTENT_CAPTURED_NOT_READY:
        runtime_status = STATUS_USE_GPU_NEEDS_SCHEDULE
        diagnostic = "--use-gpu reached the wrapper, but no explicit sidecar schedule was provided"
    elif status == STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING:
        runtime_status = STATUS_SIDECAR_EXECUTION_NOT_IMPLEMENTED
        diagnostic = "expanded sidecar schedule was captured, but RTLMeter sidecar execution is not wired yet"
        handoff_metadata = build_rtlmeter_sidecar_handoff(argv, sidecar_context=sidecar_context)
    else:
        runtime_status = STATUS_UNSUPPORTED_GPU_REQUEST
        diagnostic = str(inspection["diagnostic"])
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": runtime_status,
        "json_flow_role": "runtime_diagnostic",
        "runtime_abi": False,
        "execution_authority": True,
        "cpu_as_gpu_fallback": False,
        "delegated_to_real_verilator": False,
        "sidecar_execution_invoked": False,
        "inspection_status": status,
        "handoff_metadata": handoff_metadata,
        "sidecar_context_parse_error": (
            dict(sidecar_context_parse_error) if sidecar_context_parse_error is not None else None
        ),
        "diagnostic": diagnostic,
        "non_claims": [
            "GPU intent is never delegated to CPU Verilator as a fake GPU run",
            "runtime diagnostics are not the stable sidecar ABI",
            "no speedup or correctness claim is made from this fail-closed path",
        ],
    }


def _real_verilator_missing_report() -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": STATUS_REAL_VERILATOR_MISSING,
        "execution_authority": True,
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
    wrapper_path = Path(executable or sys.argv[0])
    inspection = inspect_rtlmeter_verilator_wrapper_argv(argv)

    if inspection["status"] == STATUS_DELEGATE_TO_REAL_VERILATOR:
        real_verilator = resolve_real_verilator(environ=env, wrapper_path=wrapper_path)
        if real_verilator is None:
            print(json.dumps(_real_verilator_missing_report(), indent=2), file=stderr or sys.stderr)
            return 127
        completed = runner([str(real_verilator), *map(str, argv)], env=env)
        return int(completed.returncode)

    sidecar_context, context_error = _sidecar_context_from_env(env)
    print(
        json.dumps(
            fail_closed_report(
                argv,
                sidecar_context=sidecar_context,
                sidecar_context_parse_error=context_error,
            ),
            indent=2,
        ),
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
        f"exec {shlex.quote(python)} {shlex.quote(str(runtime_path))} \"$@\"\n",
        encoding="utf-8",
    )
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return target


def main(argv: list[str] | None = None) -> int:
    return run_rtlmeter_verilator_wrapper(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
