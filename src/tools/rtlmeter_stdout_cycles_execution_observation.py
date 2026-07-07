"""Execution observation boundary for RTLMeter stdout/cycles sidecar results."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_sidecar_proxy_marker import build_rtlmeter_sidecar_proxy_execution_evidence, observe_rtlmeter_sidecar_proxy_marker
    from .rtlmeter_stdout_cycles_observables import normalized_rtlmeter_stdout
    from .rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES
    from .rtlmeter_stdout_cycles_sidecar_runner import (
        STATUS_BLOCKED_PLAN,
        STATUS_BLOCKED_REJECTED_COMMAND,
        _copy_mapping,
        _plan_missing_context,
        _rejected_command_inputs,
        _strip_separator,
        materialize_rtlmeter_stdout_cycles_sidecar_runner_command,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_sidecar_proxy_marker import build_rtlmeter_sidecar_proxy_execution_evidence, observe_rtlmeter_sidecar_proxy_marker
    from rtlmeter_stdout_cycles_observables import normalized_rtlmeter_stdout
    from rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES
    from rtlmeter_stdout_cycles_sidecar_runner import (
        STATUS_BLOCKED_PLAN,
        STATUS_BLOCKED_REJECTED_COMMAND,
        _copy_mapping,
        _plan_missing_context,
        _rejected_command_inputs,
        _strip_separator,
        materialize_rtlmeter_stdout_cycles_sidecar_runner_command,
    )


STATUS_EXECUTION_NOT_REQUESTED = "rtlmeter_stdout_cycles_sidecar_runner_execution_not_requested"
STATUS_VSIM_PROXY_ENV_MISSING = "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_env_missing"
STATUS_EXECUTION_FAILED = "rtlmeter_stdout_cycles_sidecar_runner_execution_failed"
STATUS_OUTPUTS_MISSING = "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing"
STATUS_OBSERVABLES_READY = "rtlmeter_stdout_cycles_sidecar_runner_observables_ready"
RUNNER_REPORTED_FAILURE_STATUSES = {STATUS_VSIM_PROXY_ENV_MISSING, STATUS_EXECUTION_FAILED, STATUS_OUTPUTS_MISSING, "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_target_unusable", "rtlmeter_stdout_cycles_sidecar_runner_blocked_wrapper_phase_guard"}


def _sanitize_text(text: str) -> str:
    return re.sub(r"/(?:home|tmp|Users|var|mnt|workspace|root)/[^\s'\",;)]+", "<local-absolute-path>", text)


def _sanitize_object(value: object) -> object:
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_object(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_object(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _sanitize_object(item) for key, item in value.items()}
    return value


def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def _command_names_rtlmeter(command: object) -> bool:
    if not isinstance(command, list):
        return False
    return any(Path(str(item)).name == "rtlmeter" for item in command)


def _command_equals(left: object, right: object) -> bool:
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    return [str(item) for item in left] == [str(item) for item in right]


def rtlmeter_stdout_cycles_observable_paths(
    observable_execute_dir: object, repo_root: Path | None
) -> tuple[Path | None, Path | None]:
    if not isinstance(observable_execute_dir, str) or not observable_execute_dir:
        return None, None
    execute_dir = Path(observable_execute_dir)
    if not execute_dir.is_absolute() and repo_root is not None:
        execute_dir = repo_root / execute_dir
    return execute_dir / "_execute" / "stdout.log", execute_dir / "_rtlmeter_cycles.txt"


def _observable_paths(observable_execute_dir: object, repo_root: Path | None) -> tuple[Path | None, Path | None]:
    return rtlmeter_stdout_cycles_observable_paths(observable_execute_dir, repo_root)


def _read_observables(*, observable_execute_dir: object, repo_root: Path | None) -> dict[str, object]:
    stdout_log, cycle_count_file = _observable_paths(observable_execute_dir, repo_root)
    paths = {
        "stdout_log": _relative_path(stdout_log, repo_root) if stdout_log is not None else None,
        "cycle_count_file": _relative_path(cycle_count_file, repo_root) if cycle_count_file is not None else None,
    }
    missing: list[str] = []
    stdout_sha256 = None
    cycle_count = None

    if stdout_log is None or not stdout_log.is_file():
        missing.append("stdout_log")
    else:
        normalized_stdout = normalized_rtlmeter_stdout(stdout_log.read_text(encoding="utf-8"))
        stdout_sha256 = hashlib.sha256(normalized_stdout.encode("utf-8")).hexdigest()

    if cycle_count_file is None or not cycle_count_file.is_file():
        missing.append("cycle_count_file")
    else:
        try:
            cycle_count = int(cycle_count_file.read_text(encoding="utf-8").strip())
        except ValueError:
            missing.append("cycle_count_file.parse_int")

    return {
        "observable_paths": paths,
        "missing_observables": missing,
        "observables_ready": not missing,
        "normalized_stdout_sha256": stdout_sha256,
        "cycle_count": cycle_count,
    }


def _observable_stdout_contains(*, observable_execute_dir: object, repo_root: Path | None, needle: str) -> bool:
    stdout_log, _cycle_count_file = _observable_paths(observable_execute_dir, repo_root)
    if stdout_log is None or not stdout_log.is_file():
        return False
    return needle in stdout_log.read_text(encoding="utf-8", errors="replace")


def _runner_stdout_report(command_result: Mapping[str, object] | None) -> Mapping[str, object] | None:
    if not isinstance(command_result, Mapping):
        return None
    stdout = command_result.get("stdout")
    if not isinstance(stdout, str) or not stdout.strip():
        return None
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _vsim_sidecar_proxy_env_missing(
    command_result: Mapping[str, object] | None,
    runner_report: Mapping[str, object] | None,
    *,
    observable_stdout_has_missing_proxy_env: bool,
) -> bool:
    if isinstance(runner_report, Mapping):
        if runner_report.get("status") == STATUS_VSIM_PROXY_ENV_MISSING:
            return True
        if runner_report.get("vsim_sidecar_proxy_env_present") is False:
            inner = runner_report.get("command_result")
            if isinstance(inner, Mapping) and "missing RTLMETER_VSIM_SIDECAR_PROXY" in str(inner.get("stderr", "")):
                return True
    if observable_stdout_has_missing_proxy_env:
        return True
    if isinstance(command_result, Mapping):
        return "missing RTLMETER_VSIM_SIDECAR_PROXY" in " ".join(
            str(command_result.get(name, "")) for name in ("stdout", "stderr")
        )
    return False


def build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation(
    *,
    stdout_cycles_plan: Mapping[str, object] | None,
    command_result: Mapping[str, object] | None,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Observe a reviewed opt-in runner subprocess result without measuring speedup."""

    gpu_candidate = stdout_cycles_plan.get("gpu_candidate") if isinstance(stdout_cycles_plan, Mapping) else None
    if isinstance(gpu_candidate, Mapping):
        candidate_command = _strip_separator(gpu_candidate.get("command"))
        observable_execute_dir = gpu_candidate.get("observable_execute_dir")
        sidecar_candidate = gpu_candidate.get("owner") == "sidecar"
        sidecar_candidate = sidecar_candidate and gpu_candidate.get("cpu_as_gpu_fallback_allowed") is False
    else:
        candidate_command = None
        observable_execute_dir = None
        sidecar_candidate = False

    subprocess_invoked = command_result is not None
    returncode = command_result.get("returncode") if isinstance(command_result, Mapping) else None
    command_failed = not isinstance(returncode, int) or returncode != 0
    runner_command = materialize_rtlmeter_stdout_cycles_sidecar_runner_command(stdout_cycles_plan)
    executed_runner_command = (
        isinstance(command_result, Mapping) and _command_equals(command_result.get("command"), runner_command)
    )
    observable_status = _read_observables(observable_execute_dir=observable_execute_dir, repo_root=repo_root)
    observable_stdout_has_missing_proxy_env = _observable_stdout_contains(
        observable_execute_dir=observable_execute_dir,
        repo_root=repo_root,
        needle="missing RTLMETER_VSIM_SIDECAR_PROXY",
    )
    proxy_marker = observe_rtlmeter_sidecar_proxy_marker(
        observable_execute_dir=observable_execute_dir,
        repo_root=repo_root,
    )
    runner_stdout_report = _runner_stdout_report(command_result)
    missing_context = _plan_missing_context(stdout_cycles_plan)
    rejected = _rejected_command_inputs(candidate_command or [])

    if rejected:
        status = STATUS_BLOCKED_REJECTED_COMMAND
    elif missing_context:
        status = STATUS_BLOCKED_PLAN
    elif not subprocess_invoked:
        status = STATUS_EXECUTION_NOT_REQUESTED
    elif (
        isinstance(runner_stdout_report, Mapping)
        and runner_stdout_report.get("status") in RUNNER_REPORTED_FAILURE_STATUSES
    ):
        status = str(runner_stdout_report["status"])
    elif command_failed and _vsim_sidecar_proxy_env_missing(
        command_result,
        runner_stdout_report,
        observable_stdout_has_missing_proxy_env=observable_stdout_has_missing_proxy_env,
    ):
        status = STATUS_VSIM_PROXY_ENV_MISSING
    elif command_failed:
        status = STATUS_EXECUTION_FAILED
    elif not observable_status["observables_ready"]:
        status = STATUS_OUTPUTS_MISSING
    else:
        status = STATUS_OBSERVABLES_READY

    execution_performed = status == STATUS_OBSERVABLES_READY and executed_runner_command and sidecar_candidate
    proxy_authorized = proxy_marker.get("sidecar_execute_proxy_authorized_by_wrapper_branch") is True
    authorized_execution = execution_performed and proxy_authorized
    proxy_execution_evidence = build_rtlmeter_sidecar_proxy_execution_evidence(proxy_marker=proxy_marker, observables_ready=observable_status["observables_ready"], missing_observables=observable_status["missing_observables"], runner_command_observed=executed_runner_command, execution_performed=execution_performed, proxy_handoff_observed=authorized_execution)
    nested_proxy_evidence = runner_stdout_report.get("sidecar_proxy_execution_evidence") if isinstance(runner_stdout_report, Mapping) else None
    if isinstance(nested_proxy_evidence, Mapping) and isinstance(nested_proxy_evidence.get("blocking_context"), list):
        proxy_execution_evidence["blocking_context"] = sorted({*proxy_execution_evidence["blocking_context"], *(str(item) for item in nested_proxy_evidence["blocking_context"])})
    return {
        "schema_version": 1,
        "surface": "rtlmeter_stdout_cycles_sidecar_runner_execution_observation_boundary",
        "status": status,
        "runner_kind": "rtlmeter_stdout_cycles_sidecar_runner",
        "stdout_cycles_plan": _copy_mapping(stdout_cycles_plan),
        "missing_runner_execution_context": missing_context,
        "rejected_runner_execution_context": rejected,
        "candidate_command_argv": candidate_command,
        "observable_execute_dir": observable_execute_dir,
        "observables": list(EXPECTED_OBSERVABLES),
        "command_result": _sanitize_object(command_result) if command_result is not None else None,
        "runner_stdout_report": _sanitize_object(runner_stdout_report) if runner_stdout_report is not None else None,
        "observable_stdout_has_missing_proxy_env": observable_stdout_has_missing_proxy_env,
        **observable_status,
        **proxy_marker,
        "sidecar_proxy_execution_evidence": proxy_execution_evidence,
        "uses_run_hybrid_template": False,
        "requires_runtime_launch_template": False,
        "run_hybrid_template_compatible": False,
        "launcher_command_argv": None,
        "runner_command_argv": runner_command,
        "runner_command_role": "materialized_and_observed" if runner_command is not None else "not_materialized",
        "subprocess_invoked": subprocess_invoked,
        "rtlmeter_invoked": executed_runner_command and _command_names_rtlmeter(candidate_command),
        "adapter_invoked": executed_runner_command,
        "sidecar_runner_invoked": executed_runner_command and sidecar_candidate,
        "rtlmeter_vsim_proxy_handoff_status": "ready" if authorized_execution else "blocked",
        "rtlmeter_vsim_proxy_handoff_reached": authorized_execution,
        "rtlmeter_proxy_handoff_observed": authorized_execution,
        "coverage_output_compare_reached": False,
        "execution_performed": execution_performed,
        "measurement_performed": False,
        "reviewed_proxy_metadata_observed": authorized_execution,
        "runtime_abi": False,
        "cpu_as_gpu_fallback": False,
        "reviewed_proxy_metadata_requires_valid_proxy_marker": True,
        "reviewed_proxy_metadata_requires_execute_proxy_install": True,
        "reviewed_proxy_metadata_requires_source_patch_marker": True,
        "gpu_execution_claim_requires_valid_proxy_marker": True,
        "gpu_execution_claimed": False,
        "generated_report_is_source_of_truth": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "execution observation does not measure timing or speedup",
            "execution observation does not use run_hybrid_template.py",
            "execution observation does not treat generated reports as source of truth",
            "CPU execution is never reported as GPU execution",
            "RTLMeter stdout/cycles observation and equivalence alone do not claim GPU runtime or prove sidecar proxy execution",
            "reviewed proxy metadata is self-attested handoff evidence, not GPU execution authority",
            "A sidecar proxy marker alone does not prove RTLMeter-compatible Vsim execute proxy installation",
        ],
    }
