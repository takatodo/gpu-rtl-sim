"""Metadata-only entrypoint declaration for a future RTLMeter stdout/cycles adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_sidecar_launcher_invocation import build_rtlmeter_sidecar_launcher_invocation
    from .rtlmeter_stdout_cycles_plan import (
        EXPECTED_OBSERVABLES,
        build_rtlmeter_stdout_cycles_execution_plan,
        sidecar_compile_args_from_wrapper_inspection,
    )
    from .rtlmeter_stdout_cycles_runner_contract import build_rtlmeter_stdout_cycles_runner_contract
    from .rtlmeter_stdout_cycles_runner_implementation import (
        build_rtlmeter_stdout_cycles_runner_implementation_boundary,
    )
    from .rtlmeter_stdout_cycles_sidecar_runner import (
        STATUS_RUNNER_ARGV_READY,
        build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_sidecar_launcher_invocation import build_rtlmeter_sidecar_launcher_invocation
    from rtlmeter_stdout_cycles_plan import (
        EXPECTED_OBSERVABLES,
        build_rtlmeter_stdout_cycles_execution_plan,
        sidecar_compile_args_from_wrapper_inspection,
    )
    from rtlmeter_stdout_cycles_runner_contract import build_rtlmeter_stdout_cycles_runner_contract
    from rtlmeter_stdout_cycles_runner_implementation import (
        build_rtlmeter_stdout_cycles_runner_implementation_boundary,
    )
    from rtlmeter_stdout_cycles_sidecar_runner import (
        STATUS_RUNNER_ARGV_READY,
        build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary,
    )


SURFACE = "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata"
STATUS_READY = "rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata_ready"
DEFAULT_RUNNER_ADAPTER_ENTRYPOINT = "rtlmeter_stdout_cycles_sidecar_runner_entrypoint"
STATUS_ADAPTER_IMPLEMENTATION_BLOCKED_CONTRACT = "rtlmeter_stdout_cycles_runner_adapter_implementation_blocked_contract"
STATUS_ADAPTER_IMPLEMENTATION_RUNNER_ARGV_READY = "rtlmeter_stdout_cycles_runner_adapter_implementation_runner_argv_ready"
STATUS_HANDOFF_BLOCKED = "rtlmeter_sidecar_execution_handoff_blocked_sidecar_verilate_execution"
STATUS_HANDOFF_BLOCKED_SOURCE_CLOSURE = "rtlmeter_sidecar_execution_handoff_blocked_missing_reviewed_source_closure"
STATUS_HANDOFF_BLOCKED_RUNTIME_TEMPLATE = "rtlmeter_sidecar_execution_handoff_blocked_missing_runtime_launch_template"
STATUS_HANDOFF_BLOCKED_AUTHORITY = "rtlmeter_sidecar_execution_handoff_blocked_missing_authority_registry_source_closure"
STATUS_HANDOFF_BLOCKED_RUNNER = "rtlmeter_sidecar_execution_handoff_blocked_missing_stdout_cycles_runner_implementation"
DEFAULT_RUNNER_SOURCE_PATH = "src/tools/rtlmeter_stdout_cycles_sidecar_runner.py"

def build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata(
    *,
    entrypoint: str = DEFAULT_RUNNER_ADAPTER_ENTRYPOINT,
    acceptance_policy: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return non-executing metadata for the future adapter entrypoint."""

    policy = {str(key): value for key, value in acceptance_policy.items()} if acceptance_policy else {}
    policy.update(
        {
            "normalized_stdout_match": True,
            "cycle_count_match": True,
            "raw_state_equality_required": False,
        }
    )

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": STATUS_READY,
        "runner_adapter_entrypoint": entrypoint,
        "runner_adapter_entrypoint_role": "declared_future_entrypoint_not_materialized",
        "adapter_kind": "rtlmeter_stdout_cycles_direct_wrapper",
        "source_contract_surface": "rtlmeter_stdout_cycles_runner_contract",
        "source_contract_required_missing_runner_context": ["rtlmeter_stdout_cycles_runner_implementation"],
        "required_command_source": "gpu_candidate.command",
        "required_wrapper_env": "RTLMETER_SIDECAR_VERILATOR_WRAPPER",
        "outputs": {
            "observable_execute_dir": "gpu_candidate.observable_execute_dir",
            "stdout_log": "_execute/stdout.log",
            "cycle_count_file": "_rtlmeter_cycles.txt",
            "observables": list(EXPECTED_OBSERVABLES),
        },
        "acceptance_policy": policy,
        "uses_run_hybrid_template": False,
        "requires_runtime_launch_template": False,
        "run_hybrid_template_compatible": False,
        "launcher_command_argv": None,
        "runner_command_argv": None,
        "runner_command_role": "not_materialized",
        "execution_authority": False,
        "runtime_abi": False,
        "adapter_invoked": False,
        "sidecar_runner_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "cpu_as_gpu_fallback": False,
        "non_claims": [
            "adapter metadata does not execute RTLMeter",
            "adapter metadata does not materialize a runner command",
            "adapter metadata does not name a tracked sidecar runner source file",
            "adapter metadata does not invoke run_hybrid_template.py",
            "adapter metadata does not prove GPU correctness, timing, or speedup",
        ],
    }

def build_rtlmeter_stdout_cycles_runner_adapter_implementation_boundary(
    *,
    runner_implementation_boundary: Mapping[str, object] | None,
    stdout_cycles_plan: Mapping[str, object] | None,
    runner_source_path: str = DEFAULT_RUNNER_SOURCE_PATH,
    repo_root: str | Path | None = None,
    python_executable: str = "python3",
) -> dict[str, object]:
    """Return non-executing diagnostics for the tracked runner adapter source."""

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    source_path = Path(runner_source_path)
    source_exists = (root / source_path).is_file() if not source_path.is_absolute() else source_path.is_file()
    source_boundary = build_rtlmeter_stdout_cycles_sidecar_runner_source_argv_boundary(
        runner_implementation_boundary=runner_implementation_boundary,
        stdout_cycles_plan=stdout_cycles_plan,
        runner_source_path=runner_source_path,
        python_executable=python_executable,
    )

    missing = list(source_boundary.get("missing_runner_source_context", []))
    if not source_exists:
        missing.append("runner_adapter_source_file")
    implementation_missing = []
    if isinstance(runner_implementation_boundary, Mapping):
        implementation_missing = list(runner_implementation_boundary.get("missing_implementation_context", []))
    if "runner_contract_missing_context" in implementation_missing:
        missing.append("runner_contract.missing_runner_context")

    ready = source_exists and source_boundary.get("status") == STATUS_RUNNER_ARGV_READY and not missing
    return {
        "schema_version": 1,
        "surface": "rtlmeter_stdout_cycles_runner_adapter_implementation_boundary",
        "status": STATUS_ADAPTER_IMPLEMENTATION_RUNNER_ARGV_READY if ready else STATUS_ADAPTER_IMPLEMENTATION_BLOCKED_CONTRACT,
        "runner_adapter_source_file": runner_source_path,
        "runner_adapter_source_file_exists": source_exists,
        "runner_source_argv_boundary": source_boundary,
        "missing_adapter_implementation_context": missing,
        "runner_command_argv": source_boundary.get("runner_command_argv") if ready else None,
        "runner_command_role": source_boundary.get("runner_command_role") if ready else "not_materialized",
        "uses_run_hybrid_template": False,
        "run_hybrid_template_compatible": False,
        "execution_authority": False,
        "runtime_abi": False,
        "sidecar_runner_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "cpu_as_gpu_fallback": False,
        "non_claims": [
            "adapter implementation boundary does not execute RTLMeter",
            "adapter implementation boundary does not invoke a materialized runner command",
            "adapter implementation boundary does not invoke run_hybrid_template.py",
            "adapter implementation boundary does not prove correctness, timing, or speedup",
        ],
    }

def _repo_root(repo_root: str | Path | None = None) -> Path:
    return Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]

def _relative_config_path(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".json":
        return None
    return path.as_posix()

def _authority_registry_path(plan: Mapping[str, object], context: Mapping[str, object] | None) -> str | None:
    entry = None
    if isinstance(context, Mapping):
        entry = _relative_config_path(context.get("template_or_target_registry_entry"))
    if entry and Path(entry).parts[:2] == ("config", "rtlmeter_sidecar_authorities"):
        return entry
    return _relative_config_path(plan.get("authority_registry"))

def _load_authority_registry(
    path: str | None,
    *,
    repo_root: str | Path | None = None,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    if path is None:
        return None, {"error": "authority_registry_path_missing"}
    config_path = _repo_root(repo_root) / path
    if not config_path.is_file():
        return None, {"path": path, "error": "authority_registry_file_missing"}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, {"path": path, "error": str(exc)}
    if not isinstance(payload, Mapping):
        return None, {"path": path, "error": "authority_registry_payload_must_be_object"}
    return {str(key): value for key, value in payload.items()}, None

def _context_string(context: Mapping[str, object] | None, field: str) -> str | None:
    if not isinstance(context, Mapping):
        return None
    value = context.get(field)
    return value if isinstance(value, str) and value else None

def _context_source_closure_string(context: Mapping[str, object] | None, field: str) -> str | None:
    if not isinstance(context, Mapping):
        return None
    closure = context.get("source_closure")
    if not isinstance(closure, Mapping):
        return None
    value = closure.get(field)
    return value if isinstance(value, str) and value else None

def _context_path_rules(context: Mapping[str, object] | None) -> Mapping[str, object]:
    if not isinstance(context, Mapping):
        return {}
    rules = context.get("state_and_report_path_rules")
    return rules if isinstance(rules, Mapping) else {}

def _stdout_cycles_plan_from_context(
    *,
    compile_args: str,
    context: Mapping[str, object] | None,
) -> dict[str, object]:
    seed = _context_string(context, "rtlmeter_case") or _context_source_closure_string(context, "rtlmeter_case")
    artifact_root = _context_string(context, "artifact_root")
    path_rules = _context_path_rules(context)
    if artifact_root is None:
        rule_root = path_rules.get("artifact_root") or path_rules.get("root")
        artifact_root = rule_root if isinstance(rule_root, str) and rule_root else None
    authority_registry = _authority_registry_path({"authority_registry": None}, context)

    kwargs: dict[str, object] = {"compile_args": compile_args}
    if seed is not None:
        kwargs["seed"] = seed
    if artifact_root is not None:
        kwargs["artifact_root"] = Path(artifact_root)
    if authority_registry is not None:
        kwargs["authority_registry"] = authority_registry
    return build_rtlmeter_stdout_cycles_execution_plan(**kwargs)

def _blocked_handoff_status(
    *,
    handoff_metadata: Mapping[str, object],
    launcher_invocation: Mapping[str, object],
    runner_contract: Mapping[str, object],
    adapter_implementation: Mapping[str, object],
) -> str:
    missing_context = handoff_metadata.get("missing_sidecar_context")
    if isinstance(missing_context, list) and "source_closure" in missing_context:
        return STATUS_HANDOFF_BLOCKED_SOURCE_CLOSURE

    missing_runner = runner_contract.get("missing_runner_context")
    if isinstance(missing_runner, list):
        if any(str(item).startswith("authority_registry.source_closure") for item in missing_runner):
            return STATUS_HANDOFF_BLOCKED_AUTHORITY
        if "rtlmeter_stdout_cycles_runner_implementation" in missing_runner:
            return STATUS_HANDOFF_BLOCKED_RUNNER
    if (
        isinstance(missing_runner, list)
        and not missing_runner
        and adapter_implementation.get("status") == STATUS_ADAPTER_IMPLEMENTATION_RUNNER_ARGV_READY
        and adapter_implementation.get("runner_command_argv")
    ):
        return STATUS_HANDOFF_BLOCKED

    missing_invocation = launcher_invocation.get("missing_invocation_context")
    if isinstance(missing_invocation, list) and any(
        item in missing_invocation for item in ("runtime_launch_template", "template_file", "template_execution_role")
    ):
        return STATUS_HANDOFF_BLOCKED_RUNTIME_TEMPLATE
    return STATUS_HANDOFF_BLOCKED

def _blocked_handoff_diagnostic(status: str) -> str:
    if status == STATUS_HANDOFF_BLOCKED_SOURCE_CLOSURE:
        return "RTLMeter sidecar handoff is blocked on reviewed hybrid execution source-closure authority"
    if status == STATUS_HANDOFF_BLOCKED_RUNTIME_TEMPLATE:
        return "RTLMeter sidecar handoff is blocked on a reviewed runtime launch template"
    if status == STATUS_HANDOFF_BLOCKED_AUTHORITY:
        return "RTLMeter sidecar handoff is blocked on authority-registry source-closure review"
    if status == STATUS_HANDOFF_BLOCKED_RUNNER:
        return "RTLMeter sidecar handoff is blocked on the stdout/cycles sidecar runner implementation"
    return "RTLMeter stdout/cycles runner argv is ready, but sidecar Verilate execution is not implemented"

def build_rtlmeter_stdout_cycles_wrapper_handoff_diagnostics(
    *,
    inspection: Mapping[str, object],
    handoff_metadata: Mapping[str, object],
    repo_root: str | Path | None = None,
) -> dict[str, object]:
    """Return non-executing stdout/cycles diagnostics for a captured RTLMeter handoff."""

    launcher_invocation = build_rtlmeter_sidecar_launcher_invocation(handoff_metadata, repo_root=repo_root)
    context = handoff_metadata.get("sidecar_context")
    stdout_cycles_execution_plan = _stdout_cycles_plan_from_context(
        compile_args=sidecar_compile_args_from_wrapper_inspection(inspection),
        context=context if isinstance(context, Mapping) else None,
    )
    registry_path = _authority_registry_path(
        stdout_cycles_execution_plan,
        context if isinstance(context, Mapping) else None,
    )
    authority_registry, authority_registry_load_error = _load_authority_registry(registry_path, repo_root=repo_root)
    stdout_cycles_runner_contract = build_rtlmeter_stdout_cycles_runner_contract(
        stdout_cycles_plan=stdout_cycles_execution_plan,
        handoff_metadata=handoff_metadata,
        authority_registry=authority_registry,
        runner_implementation_ready=True,
    )
    adapter_metadata = build_rtlmeter_stdout_cycles_runner_adapter_entrypoint_metadata()
    stdout_cycles_runner_implementation = build_rtlmeter_stdout_cycles_runner_implementation_boundary(
        runner_contract=stdout_cycles_runner_contract,
        runner_adapter_entrypoint_metadata=adapter_metadata,
    )
    stdout_cycles_runner_adapter_implementation = build_rtlmeter_stdout_cycles_runner_adapter_implementation_boundary(
        runner_implementation_boundary=stdout_cycles_runner_implementation,
        stdout_cycles_plan=stdout_cycles_execution_plan,
        repo_root=repo_root,
    )
    status = _blocked_handoff_status(
        handoff_metadata=handoff_metadata,
        launcher_invocation=launcher_invocation,
        runner_contract=stdout_cycles_runner_contract,
        adapter_implementation=stdout_cycles_runner_adapter_implementation,
    )
    return {
        "status": status,
        "diagnostic": _blocked_handoff_diagnostic(status),
        "launcher_invocation": launcher_invocation,
        "sidecar_authority_registry": authority_registry,
        "sidecar_authority_registry_load_error": authority_registry_load_error,
        "stdout_cycles_execution_plan": stdout_cycles_execution_plan,
        "stdout_cycles_runner_contract": stdout_cycles_runner_contract,
        "stdout_cycles_runner_implementation": stdout_cycles_runner_implementation,
        "stdout_cycles_runner_adapter_implementation": stdout_cycles_runner_adapter_implementation,
    }
