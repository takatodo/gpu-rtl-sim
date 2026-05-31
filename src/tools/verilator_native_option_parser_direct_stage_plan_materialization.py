"""Non-executing direct command-path to sidecar stage-plan bridge."""

from __future__ import annotations

from collections.abc import Mapping

try:
    from .verilator_native_option_parser_direct_command_path_fixture import (
        DIRECT_COMMAND_PATH_FIXTURE_FIELDS,
        DIRECT_COMMAND_PATH_FIXTURE_SURFACE,
        DIRECT_COMMAND_PATH_STATUS,
        NativeParserDirectCommandPathFixtureError,
    )
    from .verilator_native_option_parser_direct_command_payload_validation import (
        validate_direct_command_parser_payload,
    )
    from .verilator_native_option_parser_sidecar_handoff import (
        NativeParserSidecarHandoffError,
        build_native_parser_sidecar_handoff,
    )
    from .verilator_native_option_parser_sidecar_plan_resolution import (
        NativeParserSidecarPlanResolutionError,
        resolve_native_parser_adapter_payload_to_sidecar_plan,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from verilator_native_option_parser_direct_command_path_fixture import (
        DIRECT_COMMAND_PATH_FIXTURE_FIELDS,
        DIRECT_COMMAND_PATH_FIXTURE_SURFACE,
        DIRECT_COMMAND_PATH_STATUS,
        NativeParserDirectCommandPathFixtureError,
    )
    from verilator_native_option_parser_direct_command_payload_validation import (
        validate_direct_command_parser_payload,
    )
    from verilator_native_option_parser_sidecar_handoff import (
        NativeParserSidecarHandoffError,
        build_native_parser_sidecar_handoff,
    )
    from verilator_native_option_parser_sidecar_plan_resolution import (
        NativeParserSidecarPlanResolutionError,
        resolve_native_parser_adapter_payload_to_sidecar_plan,
    )


DIRECT_STAGE_PLAN_MATERIALIZATION_SURFACE = (
    "native_verilator_parser_direct_command_path_sidecar_stage_plan_materialization_fixture"
)
REFERENCE_ONLY_FLAGS = tuple(
    "execution_performed measurement_performed timing_measured runtime_or_abi_changed "
    "source_closure_inferred filelists_expanded automatic_gpu_allocation_used".split()
)
MATERIALIZATION_FIELDS = tuple(
    "schema_version surface status direct_fixture_surface adapter_payload_surface "
    "plan_resolution_surface sidecar_context parser_schedule_constraints "
    "parser_preserved_build_inputs adapter_payload plan_resolution stage_plan "
    "sidecar_stage_plan_invoked sidecar_handoff_contract_invoked command_synthesis_invoked "
    "efficiency_estimate_invoked execution_performed measurement_performed timing_measured "
    "runtime_or_abi_changed source_closure_inferred filelists_expanded automatic_gpu_allocation_used "
    "correctness_policy_ref_status correctness_policy non_claims".split()
)


def _error(code: str, message: str) -> NativeParserDirectCommandPathFixtureError:
    return NativeParserDirectCommandPathFixtureError(code, message)


def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _require_mapping(mapping: Mapping[str, object], field: str) -> Mapping[str, object]:
    value = mapping.get(field)
    if not isinstance(value, Mapping):
        raise _error("invalid_direct_stage_plan_materialization_input", f"field {field!r} must be a mapping")
    return value


def _require_equal(mapping: Mapping[str, object], field: str, expected: object) -> None:
    if mapping.get(field) != expected:
        raise _error("direct_fixture_result_parser_payload_mismatch", f"field {field!r} does not match parser payload")


def _validate_direct_fixture_keyset(result: Mapping[str, object]) -> None:
    missing = [field for field in DIRECT_COMMAND_PATH_FIXTURE_FIELDS if field not in result]
    unknown = [key for key in result if key not in DIRECT_COMMAND_PATH_FIXTURE_FIELDS]
    if missing or unknown:
        raise _error(
            "invalid_direct_fixture_result",
            f"direct fixture result fields must match reviewed keyset; missing={missing!r} unknown={unknown!r}",
        )


def _validate_parser_payload_against_direct_result(
    result: Mapping[str, object], parser_payload: Mapping[str, object]
) -> None:
    state_count, step_count, shape, preserved = validate_direct_command_parser_payload(
        parser_payload,
        error_factory=_error,
    )
    expected = {
        "state_count": state_count,
        "step_count": step_count,
        "shape": shape,
        "ordinary_verilator_args": preserved["ordinary_verilator_args"],
        "mdir": preserved["mdir"],
        "top_module": preserved["top_module"],
        "source_files": preserved["source_files"],
        "filelists": preserved["filelists"],
        "defines": preserved["defines"],
        "include_dirs": preserved["include_dirs"],
        "warning_flags": preserved["warning_flags"],
        "correctness_policy_ref": parser_payload["correctness_policy"],
    }
    for field, value in expected.items():
        _require_equal(result, field, value)


def _validate_direct_fixture_result(result: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object]]:
    _validate_direct_fixture_keyset(result)
    if result.get("schema_version") != 1:
        raise _error("invalid_direct_fixture_result", "direct fixture result schema_version is not 1")
    if result.get("surface") != DIRECT_COMMAND_PATH_FIXTURE_SURFACE:
        raise _error("invalid_direct_fixture_result", "direct fixture result surface is not reviewed")
    if result.get("status") != DIRECT_COMMAND_PATH_STATUS:
        raise _error("invalid_direct_fixture_result", "direct fixture result status is not ready for sidecar boundary")
    enabled = [field for field in REFERENCE_ONLY_FLAGS if result.get(field) is not False]
    if enabled:
        raise _error("direct_fixture_result_not_reference_only", f"direct fixture result has enabled flags: {enabled}")
    parser_payload = _require_mapping(result, "parser_payload")
    _validate_parser_payload_against_direct_result(result, parser_payload)
    return parser_payload, _require_mapping(result, "sidecar_context")


def _require_string(mapping: Mapping[str, object], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        raise _error("missing_explicit_sidecar_context", f"missing explicit sidecar context field {field!r}")
    return value


def _normalized_plan_resolution_context(sidecar_context: Mapping[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {
        "target": _require_string(sidecar_context, "target"),
        "mode": _require_string(sidecar_context, "mode"),
        "source_gate_or_manifest_ref": _require_string(sidecar_context, "source_gate_or_manifest_ref"),
    }
    entry = sidecar_context.get("template_or_target_registry_entry")
    if isinstance(entry, str) and entry:
        normalized["template"] = entry
    elif isinstance(entry, Mapping) and entry:
        normalized["target_registry_entry"] = _copy_value(entry)
    else:
        raise _error(
            "missing_explicit_sidecar_context",
            "template_or_target_registry_entry must be a non-empty string or mapping",
        )
    if "limit" in sidecar_context:
        limit = sidecar_context["limit"]
        if type(limit) is not int:
            raise _error("missing_explicit_sidecar_context", "optional sidecar context field 'limit' must be an int")
        normalized["limit"] = limit
    if "phases" in sidecar_context:
        phases = sidecar_context["phases"]
        if type(phases) is not int or phases <= 0:
            raise _error("missing_explicit_sidecar_context", "optional sidecar context field 'phases' must be positive")
        normalized["phases"] = phases
    return normalized


def materialize_direct_command_path_sidecar_stage_plan_fixture(
    direct_fixture_result: Mapping[str, object],
) -> dict[str, object]:
    """Resolve a direct fixture result to non-executed sidecar stage-plan metadata."""

    parser_payload, sidecar_context = _validate_direct_fixture_result(direct_fixture_result)
    normalized_context = _normalized_plan_resolution_context(sidecar_context)
    try:
        adapter_payload = build_native_parser_sidecar_handoff(parser_payload)
        plan_resolution = resolve_native_parser_adapter_payload_to_sidecar_plan(
            adapter_payload,
            sidecar_context=normalized_context,
        )
    except (NativeParserSidecarHandoffError, NativeParserSidecarPlanResolutionError) as exc:
        raise _error("invalid_sidecar_stage_plan_materialization_bridge", str(exc)) from exc

    output = {
        "schema_version": 1,
        "surface": DIRECT_STAGE_PLAN_MATERIALIZATION_SURFACE,
        "status": plan_resolution["status"],
        "direct_fixture_surface": direct_fixture_result["surface"],
        "adapter_payload_surface": adapter_payload["surface"],
        "plan_resolution_surface": plan_resolution["surface"],
        "sidecar_context": normalized_context,
        "parser_schedule_constraints": plan_resolution["parser_schedule_constraints"],
        "parser_preserved_build_inputs": plan_resolution["parser_preserved_build_inputs"],
        "adapter_payload": adapter_payload,
        "plan_resolution": plan_resolution,
        "stage_plan": plan_resolution["stage_plan"],
        "sidecar_stage_plan_invoked": True,
        "sidecar_handoff_contract_invoked": False,
        "command_synthesis_invoked": False,
        "efficiency_estimate_invoked": False,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "source_closure_inferred": False,
        "filelists_expanded": False,
        "automatic_gpu_allocation_used": False,
        "correctness_policy_ref_status": plan_resolution["correctness_policy_ref_status"],
        "correctness_policy": plan_resolution["correctness_policy"],
        "non_claims": [
            "direct stage-plan materialization fixture does not execute commands",
            "direct stage-plan materialization fixture is not coverage-output equivalence evidence",
            "direct fixture parser inputs remain preserved inputs, not source closure or filelist expansion",
            "native Verilator option support, timing, runtime ABI, command synthesis, and allocation remain out of scope",
        ],
    }
    assert tuple(output.keys()) == MATERIALIZATION_FIELDS
    return output
