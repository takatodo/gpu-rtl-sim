"""Non-executing contract for an RTLMeter stdout/cycles sidecar runner."""

from __future__ import annotations

from collections.abc import Mapping

try:
    from .rtlmeter_stdout_cycles_plan import (
        EXPECTED_OBSERVABLES,
        build_rtlmeter_stdout_cycles_execution_plan,
    )
    from .rtlmeter_source_closure_authority import (
        reviewed_source_closure_missing_context,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_stdout_cycles_plan import (
        EXPECTED_OBSERVABLES,
        build_rtlmeter_stdout_cycles_execution_plan,
    )
    from rtlmeter_source_closure_authority import (
        reviewed_source_closure_missing_context,
    )


SURFACE = "rtlmeter_stdout_cycles_runner_contract"
STATUS_BLOCKED = "rtlmeter_stdout_cycles_runner_contract_blocked"
STATUS_READY = "rtlmeter_stdout_cycles_runner_contract_ready"
AUTHORITY_REGISTRY_ROLE = "rtlmeter_sidecar_authority"


def _copy_mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _source_closure_missing(value: object, prefix: str, *, expected_target: str | None = None) -> list[str]:
    return reviewed_source_closure_missing_context(value, prefix, expected_target=expected_target)


def _stdout_cycles_plan_missing_context(plan: Mapping[str, object]) -> list[str]:
    missing: list[str] = []
    if plan.get("surface") != "rtlmeter_stdout_cycles_execution_plan":
        missing.append("stdout_cycles_plan.surface")
    if plan.get("observables") != EXPECTED_OBSERVABLES:
        missing.append("stdout_cycles_plan.observables")
    if plan.get("uses_run_hybrid_template") is not False:
        missing.append("stdout_cycles_plan.uses_run_hybrid_template")
    if plan.get("requires_runtime_launch_template") is not False:
        missing.append("stdout_cycles_plan.requires_runtime_launch_template")
    if plan.get("execution_performed") is not False:
        missing.append("stdout_cycles_plan.execution_performed")
    if plan.get("measurement_performed") is not False:
        missing.append("stdout_cycles_plan.measurement_performed")

    policy = plan.get("acceptance_policy")
    if not isinstance(policy, Mapping):
        missing.append("stdout_cycles_plan.acceptance_policy")
    else:
        if policy.get("normalized_stdout_match") is not True:
            missing.append("stdout_cycles_plan.acceptance_policy.normalized_stdout_match")
        if policy.get("cycle_count_match") is not True:
            missing.append("stdout_cycles_plan.acceptance_policy.cycle_count_match")
        if policy.get("raw_state_equality_required") is not False:
            missing.append("stdout_cycles_plan.acceptance_policy.raw_state_equality_required")

    for role in ("cpu_reference", "gpu_candidate"):
        if not isinstance(plan.get(role), Mapping):
            missing.append(f"stdout_cycles_plan.{role}")
    gpu_candidate = plan.get("gpu_candidate")
    if not isinstance(gpu_candidate, Mapping):
        return missing
    if gpu_candidate.get("owner") != "sidecar":
        missing.append("stdout_cycles_plan.gpu_candidate.owner")
    if gpu_candidate.get("execution_kind") != "sidecar_required":
        missing.append("stdout_cycles_plan.gpu_candidate.execution_kind")
    if gpu_candidate.get("fallback_policy") != "forbidden":
        missing.append("stdout_cycles_plan.gpu_candidate.fallback_policy")
    if gpu_candidate.get("cpu_as_gpu_fallback_allowed") is not False:
        missing.append("stdout_cycles_plan.gpu_candidate.cpu_as_gpu_fallback_allowed")
    if not isinstance(gpu_candidate.get("command"), list) or not gpu_candidate.get("command"):
        missing.append("stdout_cycles_plan.gpu_candidate.command")
    if not isinstance(gpu_candidate.get("compile_args"), str) or not gpu_candidate.get("compile_args"):
        missing.append("stdout_cycles_plan.gpu_candidate.compile_args")
    return missing


def _handoff_missing_context(handoff_metadata: Mapping[str, object] | None) -> list[str]:
    if handoff_metadata is None:
        return ["handoff_metadata"]
    missing: list[str] = []
    if handoff_metadata.get("status") != "rtlmeter_sidecar_handoff_metadata_ready":
        missing.append("handoff_metadata_ready")

    schedule = handoff_metadata.get("schedule")
    if not isinstance(schedule, Mapping) or not isinstance(schedule.get("shape"), str):
        missing.append("schedule.shape")
    parser_payload = handoff_metadata.get("parser_payload")
    if not isinstance(parser_payload, Mapping) or not isinstance(parser_payload.get("mdir"), str):
        missing.append("parser_payload.mdir")

    context = handoff_metadata.get("sidecar_context")
    if not isinstance(context, Mapping):
        missing.append("sidecar_context.target")
        missing.extend(_source_closure_missing(None, "sidecar_context.source_closure"))
        return missing
    context_target = context.get("target")
    if not isinstance(context_target, str) or not context_target:
        missing.append("sidecar_context.target")
        context_target = None
    missing.extend(
        _source_closure_missing(
            context.get("source_closure"),
            "sidecar_context.source_closure",
            expected_target=context_target,
        )
    )
    return missing


def _target_from_handoff(handoff_metadata: Mapping[str, object] | None) -> str | None:
    if not isinstance(handoff_metadata, Mapping):
        return None
    context = handoff_metadata.get("sidecar_context")
    if not isinstance(context, Mapping):
        return None
    target = context.get("target")
    if not isinstance(target, str) or not target:
        return None
    return target


def _authority_registry_missing_context(
    authority_registry: Mapping[str, object] | None,
    *,
    expected_target: str | None = None,
) -> list[str]:
    if authority_registry is None:
        return ["authority_registry"]
    missing: list[str] = []
    if authority_registry.get("schema_role") != AUTHORITY_REGISTRY_ROLE:
        missing.append("authority_registry.schema_role")
    if authority_registry.get("runtime_launchable") is not False:
        missing.append("authority_registry.runtime_launchable")
    registry_target = authority_registry.get("target")
    if not isinstance(registry_target, str) or not registry_target:
        missing.append("authority_registry.target")
    elif expected_target is not None and registry_target != expected_target:
        missing.append("authority_registry.target_match")
    missing.extend(
        _source_closure_missing(
            authority_registry.get("source_closure"),
            "authority_registry.source_closure",
            expected_target=expected_target,
        )
    )
    return missing


def build_rtlmeter_stdout_cycles_runner_contract(
    *,
    stdout_cycles_plan: Mapping[str, object] | None = None,
    handoff_metadata: Mapping[str, object] | None = None,
    authority_registry: Mapping[str, object] | None = None,
    runner_implementation_ready: bool = False,
) -> dict[str, object]:
    """Return a non-executing RTLMeter-specific runner contract."""

    plan = stdout_cycles_plan or build_rtlmeter_stdout_cycles_execution_plan()
    missing = _stdout_cycles_plan_missing_context(plan)
    missing.extend(_handoff_missing_context(handoff_metadata))
    expected_target = _target_from_handoff(handoff_metadata)
    missing.extend(_authority_registry_missing_context(authority_registry, expected_target=expected_target))
    if not runner_implementation_ready:
        missing.append("rtlmeter_stdout_cycles_runner_implementation")

    cpu_reference = _copy_mapping(plan.get("cpu_reference"))
    gpu_candidate = _copy_mapping(plan.get("gpu_candidate"))
    acceptance_policy = _copy_mapping(plan.get("acceptance_policy"))
    schedule = _copy_mapping(handoff_metadata.get("schedule") if handoff_metadata else None)
    parser_payload = _copy_mapping(handoff_metadata.get("parser_payload") if handoff_metadata else None)
    sidecar_context = _copy_mapping(handoff_metadata.get("sidecar_context") if handoff_metadata else None)
    authority_registry_entry = (
        plan.get("authority_registry") if isinstance(plan.get("authority_registry"), str) else None
    )
    if isinstance(sidecar_context, Mapping) and isinstance(sidecar_context.get("template_or_target_registry_entry"), str):
        authority_registry_entry = str(sidecar_context["template_or_target_registry_entry"])

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": STATUS_BLOCKED if missing else STATUS_READY,
        "runner_kind": "rtlmeter_stdout_cycles_sidecar_runner",
        "source_plan_surface": plan.get("surface"),
        "source_plan_status": plan.get("status"),
        "source_handoff_surface": handoff_metadata.get("surface") if handoff_metadata else None,
        "source_handoff_status": handoff_metadata.get("status") if handoff_metadata else None,
        "missing_runner_context": missing,
        "seed": plan.get("seed"),
        "target": sidecar_context.get("target") if sidecar_context else None,
        "schedule": schedule,
        "parser_payload_mdir": parser_payload.get("mdir") if parser_payload else None,
        "observables": list(EXPECTED_OBSERVABLES),
        "acceptance_policy": acceptance_policy,
        "cpu_reference": cpu_reference,
        "gpu_candidate": gpu_candidate,
        "authority_registry_entry": authority_registry_entry,
        "uses_run_hybrid_template": False,
        "requires_runtime_launch_template": False,
        "run_hybrid_template_compatible": False,
        "launcher_command_argv": None,
        "runner_command_argv": None,
        "runner_command_role": "not_materialized",
        "execution_authority": False,
        "runtime_abi": False,
        "sidecar_runner_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "cpu_as_gpu_fallback": False,
        "rejected_execution_paths": [
            "src/tools/run_hybrid_template.py",
            "CPU reference command reported as GPU candidate",
        ],
        "next_required_boundary": "implement RTLMeter-specific sidecar wrapper that emits stdout/cycles evidence",
        "non_claims": [
            "runner contract does not execute RTLMeter",
            "runner contract does not invoke run_hybrid_template.py",
            "runner contract does not prove GPU correctness, timing, or speedup",
        ],
    }
