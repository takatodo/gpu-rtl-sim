"""Non-executing RTLMeter stdout/cycles sidecar runner argv boundary."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_stdout_cycles_plan import EXPECTED_OBSERVABLES


SURFACE = "rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary"
STATUS_BLOCKED_IMPLEMENTATION = "rtlmeter_stdout_cycles_sidecar_runner_blocked_implementation_boundary"
STATUS_BLOCKED_PLAN = "rtlmeter_stdout_cycles_sidecar_runner_blocked_plan"
STATUS_BLOCKED_REJECTED_COMMAND = "rtlmeter_stdout_cycles_sidecar_runner_blocked_rejected_command"
STATUS_RUNNER_ARGV_READY = "rtlmeter_stdout_cycles_sidecar_runner_argv_metadata_ready"
IMPLEMENTATION_SURFACE = "rtlmeter_stdout_cycles_runner_implementation"
IMPLEMENTATION_READY = "rtlmeter_stdout_cycles_runner_implementation_adapter_entrypoint_metadata_ready"
DEFAULT_RUNNER_SOURCE_PATH = "src/tools/rtlmeter_stdout_cycles_sidecar_runner.py"


def _copy_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _strip_separator(command_argv: object) -> list[str] | None:
    if not isinstance(command_argv, list) or not command_argv:
        return None
    command = [str(item) for item in command_argv]
    if command and command[0] == "--":
        return command[1:]
    return command


def _has_option_value(command: list[str], option: str, expected: str) -> bool:
    for index, item in enumerate(command):
        if item == option and index + 1 < len(command) and command[index + 1] == expected:
            return True
        if item == f"{option}={expected}":
            return True
    return False


def _has_work_root(command: list[str]) -> bool:
    return "--workRoot" in command or any(item.startswith("--workRoot=") for item in command)


def _rejected_command_inputs(command: list[str]) -> list[str]:
    rejected: list[str] = []
    previous = None
    for item in command:
        name = Path(item).name
        if name == "run_hybrid_template.py":
            rejected.append("run_hybrid_template.py")
        if previous == "-m" and item.replace("/", ".").endswith("run_hybrid_template"):
            rejected.append("python -m run_hybrid_template")
        previous = item
    return rejected


def _command_missing_context(command: list[str] | None, seed: object, compile_args: object) -> list[str]:
    if command is None:
        return ["stdout_cycles_plan.gpu_candidate.command"]
    missing: list[str] = []
    if not any(Path(item).name == "rtlmeter" for item in command):
        missing.append("stdout_cycles_plan.gpu_candidate.command.rtlmeter")
    if "run" not in command:
        missing.append("stdout_cycles_plan.gpu_candidate.command.run")
    if not isinstance(seed, str) or not seed or not _has_option_value(command, "--cases", seed):
        missing.append("stdout_cycles_plan.gpu_candidate.command.cases")
    if not _has_work_root(command):
        missing.append("stdout_cycles_plan.gpu_candidate.command.workRoot")
    if not isinstance(compile_args, str) or "--sim-accel sidecar-gpu" not in compile_args:
        missing.append("stdout_cycles_plan.gpu_candidate.compile_args.sidecar_accel")
    if "--sim-accel sidecar-gpu" not in " ".join(command):
        missing.append("stdout_cycles_plan.gpu_candidate.command.sidecar_accel")
    return missing


def _implementation_missing_context(boundary: Mapping[str, object] | None) -> list[str]:
    if boundary is None:
        return ["runner_implementation_boundary"]
    missing: list[str] = []
    if boundary.get("surface") != IMPLEMENTATION_SURFACE:
        missing.append("runner_implementation_boundary.surface")
    if boundary.get("status") != IMPLEMENTATION_READY:
        missing.append("runner_implementation_boundary.status")
    if boundary.get("runner_command_argv") is not None:
        missing.append("runner_implementation_boundary.runner_command_argv")
    if boundary.get("execution_authority") is not False:
        missing.append("runner_implementation_boundary.execution_authority")
    if boundary.get("sidecar_execution_invoked") is not False:
        missing.append("runner_implementation_boundary.sidecar_execution_invoked")
    return missing


def _plan_missing_context(plan: Mapping[str, object] | None) -> list[str]:
    if plan is None:
        return ["stdout_cycles_plan"]
    missing: list[str] = []
    if plan.get("surface") != "rtlmeter_stdout_cycles_execution_plan":
        missing.append("stdout_cycles_plan.surface")
    if plan.get("observables") != EXPECTED_OBSERVABLES:
        missing.append("stdout_cycles_plan.observables")

    gpu_candidate = plan.get("gpu_candidate")
    if not isinstance(gpu_candidate, Mapping):
        return [*missing, "stdout_cycles_plan.gpu_candidate"]
    command = _strip_separator(gpu_candidate.get("command"))
    missing.extend(_command_missing_context(command, plan.get("seed"), gpu_candidate.get("compile_args")))
    if not isinstance(gpu_candidate.get("observable_execute_dir"), str) or not gpu_candidate.get(
        "observable_execute_dir"
    ):
        missing.append("stdout_cycles_plan.gpu_candidate.observable_execute_dir")
    if gpu_candidate.get("cpu_as_gpu_fallback_allowed") is not False:
        missing.append("stdout_cycles_plan.gpu_candidate.cpu_as_gpu_fallback_allowed")
    return missing


def build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary(
    *,
    runner_implementation_boundary: Mapping[str, object] | None,
    stdout_cycles_plan: Mapping[str, object] | None,
    runner_source_path: str = DEFAULT_RUNNER_SOURCE_PATH,
    python_executable: str = "python3",
) -> dict[str, object]:
    """Return runner argv metadata for a later reviewed run without invoking anything."""

    implementation = _copy_mapping(runner_implementation_boundary)
    plan = _copy_mapping(stdout_cycles_plan)
    missing_implementation = _implementation_missing_context(runner_implementation_boundary)
    missing_plan = _plan_missing_context(stdout_cycles_plan)
    command = None
    observable_execute_dir = None
    rejected: list[str] = []

    if isinstance(stdout_cycles_plan, Mapping):
        gpu_candidate = stdout_cycles_plan.get("gpu_candidate")
        if isinstance(gpu_candidate, Mapping):
            command = _strip_separator(gpu_candidate.get("command"))
            observable_execute_dir = gpu_candidate.get("observable_execute_dir")
            if command is not None:
                rejected = _rejected_command_inputs(command)

    runner_command_argv = None
    runner_command_role = "not_materialized"
    if missing_implementation:
        status = STATUS_BLOCKED_IMPLEMENTATION
    elif rejected:
        status = STATUS_BLOCKED_REJECTED_COMMAND
    elif missing_plan:
        status = STATUS_BLOCKED_PLAN
    else:
        status = STATUS_RUNNER_ARGV_READY
        runner_command_argv = [
            python_executable,
            runner_source_path,
            "--observable-execute-dir",
            str(observable_execute_dir),
            "--",
            *list(command or []),
        ]
        runner_command_role = "materialized_for_later_run_not_invoked"

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": status,
        "runner_kind": "rtlmeter_stdout_cycles_sidecar_runner",
        "runner_implementation_boundary": implementation,
        "stdout_cycles_plan": plan,
        "missing_runner_source_context": [*missing_implementation, *missing_plan],
        "rejected_runner_source_context": rejected,
        "runner_source_path": runner_source_path,
        "runner_source_cli_implemented": False,
        "candidate_command_argv": command,
        "observable_execute_dir": observable_execute_dir,
        "observables": list(EXPECTED_OBSERVABLES),
        "acceptance_policy": {
            "normalized_stdout_match": True,
            "cycle_count_match": True,
            "raw_state_equality_required": False,
        },
        "uses_run_hybrid_template": False,
        "requires_runtime_launch_template": False,
        "run_hybrid_template_compatible": False,
        "launcher_command_argv": None,
        "runner_command_argv": runner_command_argv,
        "runner_command_role": runner_command_role,
        "subprocess_invoked": False,
        "rtlmeter_invoked": False,
        "adapter_invoked": False,
        "sidecar_runner_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "execution_authority": False,
        "runtime_abi": False,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "next_required_boundary": "review subprocess execution and stdout/cycles observation separately",
        "non_claims": [
            "runner source argv boundary does not execute RTLMeter",
            "runner source argv boundary does not invoke a materialized command",
            "runner source argv boundary does not observe stdout/cycles outputs",
            "runner source argv boundary does not invoke run_hybrid_template.py",
            "runner source argv boundary does not prove GPU correctness, timing, or speedup",
        ],
    }
