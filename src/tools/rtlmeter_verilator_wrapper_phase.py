"""Shared phase guard constants for the RTLMeter Verilator wrapper path."""

from __future__ import annotations

from collections.abc import Mapping


PHASE_ENV = "RTLMETER_VERILATOR_WRAPPER_PHASE"
PHASE_RTL_METER_RUN = "rtlmeter_run"
PHASE_SIDECAR_VERILATE = "sidecar_verilate"

STATUS_PHASE_CLEAR = "rtlmeter_wrapper_phase_guard_clear"
STATUS_PHASE_ENTER_RTL_METER_RUN = "rtlmeter_wrapper_phase_guard_enter_rtlmeter_run"
STATUS_PHASE_BLOCKED_REENTRY = "rtlmeter_wrapper_phase_guard_blocked_reentry"
STATUS_PHASE_BLOCKED_UNKNOWN = "rtlmeter_wrapper_phase_guard_blocked_unknown_phase"


def current_wrapper_phase(environ: Mapping[str, str]) -> str | None:
    value = environ.get(PHASE_ENV)
    return value if value else None


def wrapper_phase_guard_report(environ: Mapping[str, str]) -> dict[str, object]:
    phase = current_wrapper_phase(environ)
    if phase is None:
        status = STATUS_PHASE_CLEAR
        diagnostic = "no RTLMeter wrapper phase is active"
    elif phase in {PHASE_RTL_METER_RUN, PHASE_SIDECAR_VERILATE}:
        status = STATUS_PHASE_BLOCKED_REENTRY
        diagnostic = "RTLMeter wrapper phase is already active"
    else:
        status = STATUS_PHASE_BLOCKED_UNKNOWN
        diagnostic = "unknown RTLMeter wrapper phase is active"

    return {
        "schema_version": 1,
        "surface": "rtlmeter_verilator_wrapper_phase_guard",
        "status": status,
        "phase_env": PHASE_ENV,
        "current_phase": phase,
        "can_enter_rtlmeter_run": phase is None,
        "execution_authority": False,
        "sidecar_execution_invoked": False,
        "cpu_as_gpu_fallback": False,
        "diagnostic": diagnostic,
    }


def env_with_rtlmeter_run_phase(environ: Mapping[str, str]) -> dict[str, str]:
    env = dict(environ)
    env[PHASE_ENV] = PHASE_RTL_METER_RUN
    return env


def env_with_sidecar_verilate_phase(environ: Mapping[str, str]) -> dict[str, str]:
    env = dict(environ)
    env[PHASE_ENV] = PHASE_SIDECAR_VERILATE
    return env
