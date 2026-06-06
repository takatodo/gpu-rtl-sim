"""Diagnostics helpers for the RTLMeter CPU/GPU compare integration."""

from __future__ import annotations

import os
import re
import shlex
from collections.abc import Mapping
from pathlib import Path

from rtlmeter_stdout_cycles_execution_observation import STATUS_VSIM_PROXY_ENV_MISSING
from rtlmeter_stdout_cycles_plan import WRAPPER_ENV
from rtlmeter_verilator_wrapper_runtime import REAL_VERILATOR_ENV, resolve_real_verilator


BLOCKER_REAL_VERILATOR_NOT_SIDECAR_CAPABLE = "real_verilator_not_sidecar_capable_for_expanded_rtlmeter_argv"
BLOCKER_RTL_METER_VSIM_OBSERVABLES_MISSING = "rtlmeter_vsim_stdout_cycles_observables_missing"
BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_ENV_MISSING = "rtlmeter_vsim_sidecar_proxy_env_missing"
BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_TARGET_UNUSABLE = "rtlmeter_vsim_sidecar_proxy_target_unusable"
BLOCKER_RTL_METER_WRAPPER_PHASE_GUARD = "rtlmeter_vsim_sidecar_wrapper_phase_guard"
BLOCKER_GPU_RUNNER_EXECUTION_FAILED = "rtlmeter_sidecar_runner_execution_failed"
REAL_VERILATOR_PREFLIGHT_SURFACE = "rtlmeter_real_verilator_preflight"
REAL_VERILATOR_PREFLIGHT_MISSING = "real_verilator_missing"
REAL_VERILATOR_PREFLIGHT_SELECTED = "real_verilator_selected_capability_unproven"
REAL_VERILATOR_PREFLIGHT_BLOCKED = "real_verilator_preflight_blocked_by_missing_prerequisites"


def _sanitize(text: str) -> str:
    return re.sub(
        r"/(?:home|tmp|Users|var|mnt|workspace|root|usr/local)/[^\s'\",;)]+",
        "<local-absolute-path>",
        text,
    )


def _report_path(repo_root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve(strict=False)).as_posix()
    except ValueError:
        return "<local-absolute-path>" if path.is_absolute() else _sanitize(str(path))


def _path_with_wrapper_first(*, sidecar_wrapper: str, path_env: str | None) -> str:
    return f"{Path(sidecar_wrapper).parent}{os.pathsep}{path_env or ''}"


def _repo_relative_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _repo_relative_path_string(repo_root: Path, value: str) -> str:
    return _repo_relative_path(repo_root, value).resolve(strict=False).as_posix()


def _compile_arg_tokens(compile_args: str) -> tuple[str, ...]:
    return tuple(shlex.split(compile_args))


def _rtlmeter_execution_env(repo_root: Path, env_source: Mapping[str, str]) -> dict[str, str]:
    env = dict(env_source)
    if env.get(REAL_VERILATOR_ENV):
        env[REAL_VERILATOR_ENV] = _repo_relative_path_string(repo_root, env[REAL_VERILATOR_ENV])
    rtlmeter_root = (repo_root / "third_party/rtlmeter").as_posix()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        rtlmeter_root if not existing_pythonpath else f"{rtlmeter_root}{os.pathsep}{existing_pythonpath}"
    )
    return env


def _read_optional_log(path: Path) -> str | None:
    if not path.is_file():
        return None
    return _sanitize(path.read_text(encoding="utf-8"))


def build_real_verilator_preflight(
    *,
    repo_root: Path,
    sidecar_wrapper: str | None,
    environ: Mapping[str, str],
) -> dict[str, object]:
    """Return RTLMeter wrapper/real-Verilator selection diagnostics without executing Verilator."""

    missing: list[str] = []
    if not (repo_root / "third_party/rtlmeter/rtlmeter").is_file():
        missing.append("third_party/rtlmeter/rtlmeter")
    if not (repo_root / "third_party/rtlmeter/venv/bin/python3").is_file():
        missing.append("third_party/rtlmeter/venv/bin/python3")
    wrapper_path = None
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

    report: dict[str, object] = {
        "schema_version": 1,
        "surface": REAL_VERILATOR_PREFLIGHT_SURFACE,
        "status": REAL_VERILATOR_PREFLIGHT_BLOCKED,
        "sidecar_wrapper_env": WRAPPER_ENV,
        "real_verilator_env": REAL_VERILATOR_ENV,
        "wrapper_path": _report_path(repo_root, wrapper_path),
        "real_verilator_resolution": "not_attempted",
        "selected_real_verilator": None,
        "selected_real_verilator_source": None,
        "missing_prerequisites": missing,
        "capability_checked_by_invocation": False,
        "cpu_as_gpu_fallback": False,
        "sidecar_execution_invoked": False,
        "diagnostic": "preflight is blocked until wrapper and RTLMeter prerequisites are present",
    }
    if missing:
        return report

    assert wrapper_path is not None
    resolution_env = dict(environ)
    if environ.get(REAL_VERILATOR_ENV):
        resolution_env[REAL_VERILATOR_ENV] = _repo_relative_path_string(repo_root, environ[REAL_VERILATOR_ENV])
    resolution_env["PATH"] = _path_with_wrapper_first(sidecar_wrapper=sidecar_wrapper, path_env=environ.get("PATH"))
    real_verilator = resolve_real_verilator(environ=resolution_env, wrapper_path=wrapper_path)
    if real_verilator is None:
        report.update(
            {
                "status": REAL_VERILATOR_PREFLIGHT_MISSING,
                "real_verilator_resolution": "missing_after_excluding_wrapper",
                "missing_prerequisites": [
                    f"{REAL_VERILATOR_ENV} executable non-wrapper or real verilator after wrapper-filtered PATH"
                ],
                "diagnostic": "no executable non-wrapper real Verilator was found for RTLMeter sidecar handoff",
            }
        )
        return report

    report.update(
        {
            "status": REAL_VERILATOR_PREFLIGHT_SELECTED,
            "real_verilator_resolution": "selected_without_execution",
            "selected_real_verilator": _report_path(repo_root, real_verilator),
            "selected_real_verilator_source": (
                REAL_VERILATOR_ENV if environ.get(REAL_VERILATOR_ENV) else "wrapper_filtered_PATH"
            ),
            "missing_prerequisites": [],
            "diagnostic": (
                "a non-wrapper real Verilator was selected; sidecar capability is checked by the opt-in "
                "RTLMeter Verilate invocation"
            ),
        }
    )
    return report


def _preflight(*, repo_root: Path, sidecar_wrapper: str | None, path_env: str | None) -> list[str]:
    return list(
        build_real_verilator_preflight(
            repo_root=repo_root,
            sidecar_wrapper=sidecar_wrapper,
            environ={"PATH": path_env or ""},
        )["missing_prerequisites"]
    )


def classify_gpu_failure_blocker(*, diagnostic_log: str | None, runner_observation: Mapping[str, object] | None) -> str:
    """Return the narrowest known fail-closed RTLMeter GPU candidate blocker."""

    if diagnostic_log and "Invalid option: --sim-accel" in diagnostic_log:
        return BLOCKER_REAL_VERILATOR_NOT_SIDECAR_CAPABLE
    runner_report = runner_observation.get("runner_stdout_report") if isinstance(runner_observation, Mapping) else None
    runner_status = runner_observation.get("status") if isinstance(runner_observation, Mapping) else None
    nested_status = runner_report.get("status") if isinstance(runner_report, Mapping) else None
    if (
        isinstance(runner_observation, Mapping)
        and runner_observation.get("status") == "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing"
        and runner_observation.get("missing_observables")
    ) or (
        isinstance(runner_report, Mapping)
        and runner_report.get("status") == "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing"
        and runner_report.get("missing_observables")
    ):
        return BLOCKER_RTL_METER_VSIM_OBSERVABLES_MISSING
    if runner_status == "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_target_unusable" or nested_status == "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_target_unusable":
        return BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_TARGET_UNUSABLE
    if runner_status == "rtlmeter_stdout_cycles_sidecar_runner_blocked_wrapper_phase_guard" or nested_status == "rtlmeter_stdout_cycles_sidecar_runner_blocked_wrapper_phase_guard":
        return BLOCKER_RTL_METER_WRAPPER_PHASE_GUARD
    if isinstance(runner_observation, Mapping) and runner_observation.get("status") == STATUS_VSIM_PROXY_ENV_MISSING:
        return BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_ENV_MISSING
    return BLOCKER_GPU_RUNNER_EXECUTION_FAILED
