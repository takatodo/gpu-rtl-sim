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


def _relative_path(path: Path | None, repo_root: Path | None) -> str | None:
    if path is None:
        return None
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def _rtlmeter_compile_dir(work_root: object, seed: object) -> Path | None:
    if not isinstance(work_root, str) or not isinstance(seed, str):
        return None
    parts = seed.split(":")
    if len(parts) != 3:
        return None
    return Path(work_root) / parts[0] / parts[1] / "compile-0"


def direct_sidecar_proxy_readiness(report: Mapping[str, object], *, repo_root: Path | None) -> dict[str, object]:
    plan = report.get("stdout_cycles_execution_plan")
    gpu_candidate = plan.get("gpu_candidate") if isinstance(plan, Mapping) else None
    seed = plan.get("seed") if isinstance(plan, Mapping) else None
    work_root = gpu_candidate.get("work_root") if isinstance(gpu_candidate, Mapping) else None
    observable_execute_dir = (
        gpu_candidate.get("observable_execute_dir") if isinstance(gpu_candidate, Mapping) else None
    )

    compile_dir = _rtlmeter_compile_dir(work_root, seed)
    if compile_dir is not None and not compile_dir.is_absolute() and repo_root is not None:
        compile_dir = repo_root / compile_dir
    expected_vsim = compile_dir / "obj_dir" / "Vsim" if compile_dir is not None else None
    missing_context: list[str] = []
    if compile_dir is None:
        missing_context.append("rtlmeter_compile_dir")
    if expected_vsim is None or not expected_vsim.exists():
        missing_context.append("expected_obj_dir_vsim")
    missing_context.append("execute_proxy_installer")

    return {
        "schema_version": 1,
        "surface": "rtlmeter_direct_sidecar_proxy_readiness",
        "status": "rtlmeter_direct_sidecar_proxy_not_installed",
        "observable_execute_dir": observable_execute_dir,
        "rtlmeter_compile_dir": _relative_path(compile_dir, repo_root),
        "expected_vsim_path": _relative_path(expected_vsim, repo_root),
        "expected_vsim_present": bool(expected_vsim is not None and expected_vsim.exists()),
        "proxy_installable": False,
        "proxy_installed_by_wrapper_branch": False,
        "ordinary_vsim_unclaimable": True,
        "execution_authority": False,
        "missing_proxy_context": missing_context,
    }
