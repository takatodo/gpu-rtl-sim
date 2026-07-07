#!/usr/bin/env python3
"""PATH-selected wrapper for the first scoped Verilator --use-gpu path."""

from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    from .verilator_use_gpu_first_path import (
        DRY_READY,
        DRY_RUN_FLAG,
        EXECUTED,
        execute_verilator_use_gpu_first_path,
    )
except ImportError:  # pragma: no cover - exercised when invoked as a script.
    from verilator_use_gpu_first_path import (
        DRY_READY,
        DRY_RUN_FLAG,
        EXECUTED,
        execute_verilator_use_gpu_first_path,
    )


SURFACE = "verilator_use_gpu_wrapper_runtime"
REAL_VERILATOR_ENV = "VERILATOR_USE_GPU_REAL_VERILATOR"
WRAPPER_SELF_ENV = "VERILATOR_USE_GPU_WRAPPER_SELF"
STATUS_DELEGATED = "delegated_to_real_verilator"
STATUS_REAL_VERILATOR_MISSING = "real_verilator_missing"


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


def _has_use_gpu(argv: Sequence[str]) -> bool:
    return "--use-gpu" in argv or any(arg.startswith("--use-gpu=") for arg in argv)


def _real_verilator_missing_report() -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": STATUS_REAL_VERILATOR_MISSING,
        "execution_authority": False,
        "cpu_as_gpu_fallback": False,
        "delegated_to_real_verilator": False,
        "sidecar_execution_invoked": False,
        "diagnostic": "no executable real Verilator was found after excluding the wrapper itself",
    }


def run_verilator_use_gpu_wrapper(
    argv: Sequence[str],
    *,
    environ: Mapping[str, str] | None = None,
    executable: str | Path | None = None,
    runner=subprocess.run,
    launcher=None,
    stdout=None,
    stderr=None,
) -> int:
    env = dict(os.environ if environ is None else environ)
    args = [str(arg) for arg in argv]
    wrapper_path = Path(env.get(WRAPPER_SELF_ENV) or executable or sys.argv[0])

    if not _has_use_gpu(args):
        real_verilator = resolve_real_verilator(environ=env, wrapper_path=wrapper_path)
        if real_verilator is None:
            print(json.dumps(_real_verilator_missing_report(), indent=2), file=stderr or sys.stderr)
            return 127
        completed = runner([str(real_verilator), *args], env=env)
        return int(completed.returncode)

    dry_run = DRY_RUN_FLAG in args
    adapter_args = [arg for arg in args if arg != DRY_RUN_FLAG]
    report = execute_verilator_use_gpu_first_path(adapter_args, launcher=launcher, dry_run=dry_run)
    success = report["status"] in {DRY_READY, EXECUTED}
    print(json.dumps(report, indent=2), file=(stdout or sys.stdout) if success else (stderr or sys.stderr))
    return 0 if success else 2


def write_verilator_use_gpu_wrapper(path: str | Path, *, python_executable: str | None = None) -> Path:
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
    return run_verilator_use_gpu_wrapper(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
