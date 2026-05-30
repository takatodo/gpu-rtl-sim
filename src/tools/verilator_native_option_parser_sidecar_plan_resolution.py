"""Non-executing native-parser adapter to sidecar plan-resolution fixture."""

from __future__ import annotations

from collections.abc import Mapping

from hybrid_benchmark_sidecar_plan import sidecar_stage_plan
from hybrid_benchmark_specs import (
    BENCHMARKS,
    CORRECTNESS_POLICY_COVERAGE_OUTPUT,
    KIND_SLICE_TEMPLATE,
    SIDECAR_ACCEL,
    STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_UNSUPPORTED_FOR_STAGE_PLAN,
)
from verilator_native_option_parser_sidecar_handoff import (
    ADAPTER_SURFACE,
    CORRECTNESS_POLICY_REFERENCE_STATUS,
    FORBIDDEN_RESOLVED_SIDECAR_FIELDS,
    SIDECAR_OWNED_RESOLUTION_STATUS,
)


PLAN_RESOLUTION_SURFACE = "native_verilator_parser_sidecar_plan_resolution_fixture"
CONTEXT_SOURCE_REF_FIELD = "source_gate_or_manifest_ref"

PARSER_PRESERVED_BUILD_INPUT_FIELDS = (
    "ordinary_verilator_args",
    "mdir",
    "top_module",
    "source_files",
    "filelists",
    "defines",
    "include_dirs",
    "warning_flags",
)


class NativeParserSidecarPlanResolutionError(ValueError):
    """Raised when an adapter payload cannot be resolved to a sidecar plan."""


def _require_mapping_field(mapping: Mapping[str, object], field: str) -> object:
    if field not in mapping:
        raise NativeParserSidecarPlanResolutionError(f"missing required field {field!r}")
    return mapping[field]


def _require_string_field(mapping: Mapping[str, object], field: str) -> str:
    value = _require_mapping_field(mapping, field)
    if not isinstance(value, str) or not value:
        raise NativeParserSidecarPlanResolutionError(f"field {field!r} must be a non-empty string")
    return value


def _require_positive_int(mapping: Mapping[str, object], field: str) -> int:
    value = _require_mapping_field(mapping, field)
    if not isinstance(value, int) or value <= 0:
        raise NativeParserSidecarPlanResolutionError(f"field {field!r} must be a positive integer")
    return value


def _optional_positive_int(mapping: Mapping[str, object], field: str, default: int) -> int:
    value = mapping.get(field, default)
    if not isinstance(value, int) or value <= 0:
        raise NativeParserSidecarPlanResolutionError(f"context field {field!r} must be a positive integer")
    return value


def _validate_adapter_payload(adapter_payload: Mapping[str, object]) -> tuple[str, int, int]:
    if FORBIDDEN_RESOLVED_SIDECAR_FIELDS.intersection(adapter_payload):
        forbidden = sorted(FORBIDDEN_RESOLVED_SIDECAR_FIELDS.intersection(adapter_payload))
        raise NativeParserSidecarPlanResolutionError(
            f"adapter payload already contains sidecar-owned resolved fields: {forbidden}"
        )
    if adapter_payload.get("surface") != ADAPTER_SURFACE:
        raise NativeParserSidecarPlanResolutionError("adapter payload surface is not the reviewed handoff fixture")
    if adapter_payload.get("accelerator_mode") != SIDECAR_ACCEL:
        raise NativeParserSidecarPlanResolutionError(f"adapter payload accelerator_mode must be {SIDECAR_ACCEL!r}")
    if adapter_payload.get("correctness_policy_ref") != CORRECTNESS_POLICY_COVERAGE_OUTPUT:
        raise NativeParserSidecarPlanResolutionError(
            f"adapter payload correctness_policy_ref must be {CORRECTNESS_POLICY_COVERAGE_OUTPUT!r}"
        )
    if adapter_payload.get("correctness_policy_reference_status") != CORRECTNESS_POLICY_REFERENCE_STATUS:
        raise NativeParserSidecarPlanResolutionError("adapter payload correctness_policy_ref is not reference-only")
    if adapter_payload.get("sidecar_owned_resolution_status") != SIDECAR_OWNED_RESOLUTION_STATUS:
        raise NativeParserSidecarPlanResolutionError("adapter payload sidecar-owned fields are not unresolved")

    state_count = _require_positive_int(adapter_payload, "state_count")
    step_count = _require_positive_int(adapter_payload, "step_count")
    expected_shape = f"{state_count}x{step_count}"
    shape = _require_string_field(adapter_payload, "shape")
    if shape != expected_shape:
        raise NativeParserSidecarPlanResolutionError(
            f"adapter payload shape {shape!r} does not match state_count/step_count {expected_shape!r}"
        )
    return shape, state_count, step_count


def _target_registry_entry(sidecar_context: Mapping[str, object]) -> Mapping[str, object] | None:
    entry = sidecar_context.get("target_registry_entry")
    if entry is None:
        return None
    if not isinstance(entry, Mapping):
        raise NativeParserSidecarPlanResolutionError("context field 'target_registry_entry' must be a mapping")
    return entry


def _explicit_template(
    *,
    target: str,
    sidecar_context: Mapping[str, object],
    registry_entry: Mapping[str, object] | None,
) -> str | None:
    context_template = sidecar_context.get("template")
    if context_template is not None and not isinstance(context_template, str):
        raise NativeParserSidecarPlanResolutionError("context field 'template' must be a string")
    entry_template = registry_entry.get("template") if registry_entry is not None else None
    if entry_template is not None and not isinstance(entry_template, str):
        raise NativeParserSidecarPlanResolutionError("target_registry_entry field 'template' must be a string")
    if context_template is None and registry_entry is None:
        raise NativeParserSidecarPlanResolutionError(
            "explicit sidecar context must include template or target_registry_entry"
        )
    if context_template is not None and entry_template is not None and context_template != entry_template:
        raise NativeParserSidecarPlanResolutionError("context template and target_registry_entry template differ")

    if registry_entry is not None:
        entry_target = registry_entry.get("target", registry_entry.get("canonical_target"))
        if entry_target is not None and entry_target != target:
            raise NativeParserSidecarPlanResolutionError("target_registry_entry target does not match context target")
    return context_template if context_template is not None else entry_template


def _validate_context_template(target: str, template: str | None) -> None:
    try:
        spec = BENCHMARKS[target]
    except KeyError as exc:
        supported = ", ".join(sorted(BENCHMARKS))
        raise NativeParserSidecarPlanResolutionError(f"unsupported target {target!r}; supported: {supported}") from exc
    if spec.kind == KIND_SLICE_TEMPLATE and template != spec.template:
        raise NativeParserSidecarPlanResolutionError(
            f"context template for {target!r} must be the reviewed registry template {spec.template!r}"
        )


def _preserved_build_inputs(adapter_payload: Mapping[str, object]) -> dict[str, object]:
    return {field: adapter_payload.get(field) for field in PARSER_PRESERVED_BUILD_INPUT_FIELDS}


def _plan_resolution_readiness(plan: Mapping[str, object]) -> tuple[str, dict[str, object]]:
    stage_status = plan.get("status")
    if not isinstance(stage_status, str) or not stage_status:
        raise NativeParserSidecarPlanResolutionError("sidecar plan must include a non-empty status")

    readiness = plan.get("verilator_option_readiness")
    readiness_status = None
    missing_readiness_inputs: object = []
    if isinstance(readiness, Mapping):
        status = readiness.get("status")
        if isinstance(status, str) and status:
            readiness_status = status
        missing = readiness.get("missing", [])
        if isinstance(missing, list):
            missing_readiness_inputs = missing

    reason = plan.get("reason")
    if not isinstance(reason, str):
        reason = None

    ready = stage_status == "planned" and readiness_status == STATUS_READY_FOR_VERILATOR_OPTION_SHIM
    if ready:
        outer_status = STATUS_READY_FOR_VERILATOR_OPTION_SHIM
        not_ready_reason = None
    elif stage_status == STATUS_UNSUPPORTED_FOR_STAGE_PLAN:
        outer_status = STATUS_UNSUPPORTED_FOR_STAGE_PLAN
        not_ready_reason = reason
    elif stage_status == STATUS_PLANNED_NOT_READY_FOR_VERILATOR_OPTION_SHIM:
        outer_status = STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM
        not_ready_reason = reason
    else:
        outer_status = STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM
        not_ready_reason = reason or f"sidecar_stage_plan status {stage_status!r} is not direct-Verilator ready"

    return outer_status, {
        "stage_plan_status": stage_status,
        "verilator_option_readiness_status": readiness_status,
        "ready_for_direct_verilator_option": ready,
        "not_ready_reason": not_ready_reason,
        "status_source": "sidecar_stage_plan.status plus verilator_option_readiness.status",
        "missing_readiness_inputs": missing_readiness_inputs,
    }


def resolve_native_parser_adapter_payload_to_sidecar_plan(
    adapter_payload: Mapping[str, object],
    *,
    sidecar_context: Mapping[str, object],
) -> dict[str, object]:
    """Resolve reviewed parser adapter data to a non-executed sidecar stage plan."""

    shape, state_count, step_count = _validate_adapter_payload(adapter_payload)
    target = _require_string_field(sidecar_context, "target")
    mode = _require_string_field(sidecar_context, "mode")
    source_ref = _require_string_field(sidecar_context, CONTEXT_SOURCE_REF_FIELD)
    registry_entry = _target_registry_entry(sidecar_context)
    template = _explicit_template(target=target, sidecar_context=sidecar_context, registry_entry=registry_entry)
    _validate_context_template(target, template)

    limit = sidecar_context.get("limit")
    if limit is not None and not isinstance(limit, int):
        raise NativeParserSidecarPlanResolutionError("context field 'limit' must be an integer when provided")
    phases = _optional_positive_int(sidecar_context, "phases", 4)
    plan = sidecar_stage_plan(target=target, shape=shape, limit=limit, phases=phases, mode=mode)
    if plan.get("correctness_policy") != adapter_payload["correctness_policy_ref"]:
        raise NativeParserSidecarPlanResolutionError(
            "sidecar plan correctness policy does not match adapter correctness_policy_ref"
        )
    outer_status, readiness = _plan_resolution_readiness(plan)

    return {
        "schema_version": 1,
        "surface": PLAN_RESOLUTION_SURFACE,
        "status": outer_status,
        "adapter_payload_surface": adapter_payload["surface"],
        "sidecar_context": {
            "target": target,
            "mode": mode,
            "template": template,
            CONTEXT_SOURCE_REF_FIELD: source_ref,
            "target_registry_entry_supplied": registry_entry is not None,
        },
        "parser_schedule_constraints": {
            "accelerator_mode": adapter_payload["accelerator_mode"],
            "state_count": state_count,
            "step_count": step_count,
            "shape": shape,
        },
        "parser_preserved_build_inputs": _preserved_build_inputs(adapter_payload),
        "parser_input_resolution_role": {
            "shape": "schedule_constraint_for_sidecar_stage_plan",
            "source_files": "preserved_parser_input_not_source_closure",
            "filelists": "preserved_parser_input_not_filelist_expansion",
            "ordinary_verilator_args": "preserved_parser_input_not_command_synthesis",
        },
        "sidecar_stage_plan_invoked": True,
        "sidecar_handoff_contract_invoked": False,
        "command_synthesis_invoked": False,
        "efficiency_estimate_invoked": False,
        "execution_performed": False,
        "measurement_performed": False,
        "correctness_policy_ref_status": "reference_only_not_compare_evidence",
        "correctness_policy": plan["correctness_policy"],
        "plan_resolution_readiness": readiness,
        "stage_plan": plan,
        "non_claims": [
            "plan-resolution fixture does not execute commands",
            "plan-resolution fixture is not coverage-output equivalence evidence",
            "ready_for_verilator_option_shim is readiness only, not native Verilator execution evidence",
            "parser source files and filelists remain preserved inputs, not inferred source closure",
            "sidecar_handoff_contract, command synthesis, efficiency estimation, timing, and runtime ABI remain out of scope",
        ],
    }
