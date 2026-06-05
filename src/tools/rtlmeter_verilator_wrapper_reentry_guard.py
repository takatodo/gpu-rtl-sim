"""RTLMeter Verilator wrapper reentry guard diagnostics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

try:
    from .rtlmeter_stdout_cycles_runner_adapter import STATUS_HANDOFF_BLOCKED
    from .rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN, PHASE_SIDECAR_VERILATE
except ImportError:  # pragma: no cover - exercised when invoked as a script.
    from rtlmeter_stdout_cycles_runner_adapter import STATUS_HANDOFF_BLOCKED
    from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN, PHASE_SIDECAR_VERILATE


STATUS_REENTRY_GUARD_BLOCKED_RECURSIVE_RTL_METER = (
    "rtlmeter_wrapper_reentry_guard_blocked_recursive_rtlmeter_run"
)
STATUS_REENTRY_GUARD_RTL_METER_RUN_PHASE_READY = (
    "rtlmeter_wrapper_reentry_guard_rtlmeter_run_phase_ready_for_direct_sidecar_verilate"
)
STATUS_REENTRY_GUARD_BLOCKED_SIDECAR_VERILATE_REENTRY = (
    "rtlmeter_wrapper_reentry_guard_blocked_sidecar_verilate_reentry"
)
STATUS_REENTRY_GUARD_BLOCKED_UNKNOWN_PHASE = "rtlmeter_wrapper_reentry_guard_blocked_unknown_phase"
STATUS_REENTRY_GUARD_DIRECT_COMMAND_READY = "rtlmeter_wrapper_reentry_guard_direct_command_ready"
STATUS_REENTRY_GUARD_NO_RUNNER_COMMAND = "rtlmeter_wrapper_reentry_guard_no_runner_command"


def _runner_command_invokes_rtlmeter_run(command: object) -> bool:
    if isinstance(command, (str, bytes)) or not isinstance(command, Sequence):
        return False
    items = [str(item) for item in command]
    for index, item in enumerate(items):
        if Path(item).name == "rtlmeter" and "run" in items[index + 1 :]:
            return True
    return False


def build_rtlmeter_verilator_wrapper_reentry_guard_report(
    adapter_implementation: Mapping[str, object] | None,
    *,
    wrapper_phase: str | None = None,
) -> dict[str, object]:
    runner_command = None
    if isinstance(adapter_implementation, Mapping):
        runner_command = adapter_implementation.get("runner_command_argv")
    invokes_rtlmeter = _runner_command_invokes_rtlmeter_run(runner_command)

    direct_sidecar_verilate_phase_allowed = False
    if wrapper_phase == PHASE_RTL_METER_RUN:
        status = STATUS_REENTRY_GUARD_RTL_METER_RUN_PHASE_READY
        diagnostic = (
            "wrapper is inside the RTLMeter run phase; runner_command_argv remains metadata-only and "
            "direct sidecar Verilate is the next boundary"
        )
        direct_sidecar_verilate_phase_allowed = True
    elif wrapper_phase == PHASE_SIDECAR_VERILATE:
        status = STATUS_REENTRY_GUARD_BLOCKED_SIDECAR_VERILATE_REENTRY
        diagnostic = "wrapper is already inside the sidecar Verilate phase"
    elif wrapper_phase is not None:
        status = STATUS_REENTRY_GUARD_BLOCKED_UNKNOWN_PHASE
        diagnostic = "wrapper saw an unknown RTLMeter wrapper phase"
    elif invokes_rtlmeter:
        status = STATUS_REENTRY_GUARD_BLOCKED_RECURSIVE_RTL_METER
        diagnostic = "runner_command_argv would invoke RTLMeter run from inside the Verilator wrapper"
    elif runner_command:
        status = STATUS_REENTRY_GUARD_DIRECT_COMMAND_READY
        diagnostic = "runner_command_argv does not invoke RTLMeter run, but wrapper-side execution is still blocked"
    else:
        status = STATUS_REENTRY_GUARD_NO_RUNNER_COMMAND
        diagnostic = "no runner_command_argv is available for wrapper-side execution"

    return {
        "schema_version": 1,
        "surface": "rtlmeter_verilator_wrapper_reentry_guard",
        "status": status,
        "phase_env": PHASE_ENV,
        "wrapper_phase": wrapper_phase,
        "runner_command_present": bool(runner_command),
        "runner_command_invokes_rtlmeter_run": invokes_rtlmeter,
        "runner_command_safe_to_execute_from_wrapper": False,
        "direct_sidecar_verilate_phase_allowed": direct_sidecar_verilate_phase_allowed,
        "execution_authority": False,
        "sidecar_execution_invoked": False,
        "cpu_as_gpu_fallback": False,
        "diagnostic": diagnostic,
    }


def direct_sidecar_verilate_ready(report: Mapping[str, object]) -> bool:
    reentry_guard = report.get("reentry_guard")
    if not isinstance(reentry_guard, Mapping):
        return False
    return (
        report.get("status") == STATUS_HANDOFF_BLOCKED
        and reentry_guard.get("wrapper_phase") == PHASE_RTL_METER_RUN
        and reentry_guard.get("direct_sidecar_verilate_phase_allowed") is True
        and reentry_guard.get("runner_command_invokes_rtlmeter_run") is True
    )


def direct_sidecar_observable_execute_dir(report: Mapping[str, object]) -> object:
    plan = report.get("stdout_cycles_execution_plan")
    if not isinstance(plan, Mapping):
        return None
    gpu_candidate = plan.get("gpu_candidate")
    if not isinstance(gpu_candidate, Mapping):
        return None
    return gpu_candidate.get("observable_execute_dir")
