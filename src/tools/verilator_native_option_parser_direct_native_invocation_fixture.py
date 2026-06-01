"""Non-executing native-invocation fixture for the direct command path."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
try:
    from . import verilator_native_option_parser_direct_command_path_fixture as _direct
    from .verilator_native_option_parser_sidecar_launcher_invocation import (
        INVOCATION_FAILURE_CLASSES,
        REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF,
        SIDECAR_LAUNCHER_INVOCATION_FIELDS,
        SIDECAR_LAUNCHER_INVOCATION_FIXTURE_SURFACE,
        SIDECAR_LAUNCHER_INVOCATION_STATUS,
        build_sidecar_launcher_invocation_fixture,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    import verilator_native_option_parser_direct_command_path_fixture as _direct
    from verilator_native_option_parser_sidecar_launcher_invocation import (
        INVOCATION_FAILURE_CLASSES,
        REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF,
        SIDECAR_LAUNCHER_INVOCATION_FIELDS,
        SIDECAR_LAUNCHER_INVOCATION_FIXTURE_SURFACE,
        SIDECAR_LAUNCHER_INVOCATION_STATUS,
        build_sidecar_launcher_invocation_fixture,
    )
DIRECT_COMMAND_PATH_FIXTURE_FIELDS = _direct.DIRECT_COMMAND_PATH_FIXTURE_FIELDS
DIRECT_COMMAND_PATH_FIXTURE_SURFACE = _direct.DIRECT_COMMAND_PATH_FIXTURE_SURFACE
DIRECT_COMMAND_PATH_STATUS = _direct.DIRECT_COMMAND_PATH_STATUS
DIRECT_COMMAND_STAGE_ORDER = _direct.DIRECT_COMMAND_STAGE_ORDER
NativeParserDirectCommandPathFixtureError = _direct.NativeParserDirectCommandPathFixtureError
define_direct_command_path_sidecar_plan_fixture = _direct.define_direct_command_path_sidecar_plan_fixture
NATIVE_INVOCATION_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_native_invocation_fixture"
DIRECT_LAUNCH_HANDOFF_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_direct_launch_handoff_fixture"
SIDECAR_LAUNCHER_BRIDGE_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_sidecar_launcher_bridge_fixture"
NATIVE_INVOCATION_REJECTION_LAYER = "direct_command_path_native_invocation_fixture_contract"
NATIVE_INVOCATION_STATUS = "native_invocation_metadata_ready_for_review"
DIRECT_LAUNCH_HANDOFF_STATUS = "direct_launch_handoff_metadata_ready_for_review"
SIDECAR_LAUNCHER_BRIDGE_STATUS = "sidecar_launcher_bridge_metadata_ready_for_review"
REVIEWED_HANDOFF_CONTEXT_REF = "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json"
REQUIRED_CONTEXT_FIELDS = tuple("target mode template_or_target_registry_entry source_gate_or_manifest_ref".split())
ALLOWED_CONTEXT_FIELDS = frozenset(REQUIRED_CONTEXT_FIELDS)
FALSE_AUTHORITY_FLAGS = tuple(
    "verilator_process_invoked wrapper_execution_used fixture_metadata_runtime_authority "
    "generated_command_text_source_of_truth generated_command_text_execution_authority "
    "native_command_alone_execution_authority sidecar_stage_plan_metadata_execution_authority "
    "materialized_stage_plan_metadata_execution_authority execution_performed measurement_performed timing_measured "
    "runtime_or_abi_changed source_closure_inferred filelists_expanded automatic_gpu_allocation_used".split()
)
NATIVE_INVOCATION_FIELDS = tuple(("schema_version surface status direct_fixture_surface parser_payload parser_preserved_build_inputs sidecar_context native_invocation accelerator_mode state_count step_count shape ordinary_verilator_args mdir top_module source_files filelists defines include_dirs warning_flags reviewed_sidecar_handoff_boundary required_stage_order correctness_policy_ref correctness_policy_ref_status verilator_process_invoked wrapper_execution_used fixture_metadata_runtime_authority generated_command_text_source_of_truth generated_command_text_execution_authority native_command_alone_execution_authority sidecar_stage_plan_metadata_execution_authority materialized_stage_plan_metadata_execution_authority execution_performed measurement_performed timing_measured runtime_or_abi_changed source_closure_inferred filelists_expanded automatic_gpu_allocation_used non_claims").split())
DIRECT_LAUNCH_HANDOFF_FIELDS = tuple(("schema_version surface status native_invocation_surface handoff_ready sidecar_context sidecar_launcher_entrypoint required_stage_order preserved_failure_classes sidecar_launch_reached_from_native_path coverage_output_compare_reached_from_native_path execution_performed measurement_performed timing_measured runtime_or_abi_changed automatic_gpu_allocation_used non_claims").split())
SIDECAR_LAUNCHER_BRIDGE_FIELDS = tuple(("schema_version surface status handoff_surface bridge_ready sidecar_context sidecar_launcher_entrypoint sidecar_launcher_entrypoint_role required_stage_order preserved_failure_classes sidecar_launch_reached_from_native_path coverage_output_compare_reached_from_native_path native_path_compare_reached execution_performed measurement_performed timing_measured runtime_or_abi_changed automatic_gpu_allocation_used non_claims").split())
PRESERVED_FAILURE_CLASSES = tuple("process_parse_failure missing_explicit_sidecar_context sidecar_authority_failure direct_launch_handoff_failure sidecar_stage_failure compare_failure timing_claim_without_measurement".split())
BRIDGE_FAILURE_CLASSES = tuple("process_parse_failure missing_explicit_sidecar_context sidecar_authority_failure sidecar_launcher_bridge_failure sidecar_stage_failure compare_failure timing_claim_without_measurement".split())
NON_CLAIMS = ("native invocation fixture does not execute Verilator or hybrid runtime", "native invocation fixture does not make native command text runtime authority", "native invocation fixture requires explicit reviewed sidecar context before any later execution", "native invocation fixture does not materialize or execute sidecar stages", "native invocation fixture does not infer source closure, expand filelists, time execution, or allocate GPU work", "native invocation fixture is not native Verilator option support")
HANDOFF_NON_CLAIMS = NON_CLAIMS + ("direct launch handoff fixture does not execute sidecar stages or compare outputs",)
BRIDGE_NON_CLAIMS = HANDOFF_NON_CLAIMS + ("sidecar launcher bridge fixture does not call the sidecar launcher", "sidecar launcher bridge fixture does not make native-path compare or timing claims")
class NativeParserDirectNativeInvocationFixtureError(ValueError):
    """Structured native-invocation fixture validation error."""
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.rejection_layer = NATIVE_INVOCATION_REJECTION_LAYER
    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "rejection_layer": self.rejection_layer, "message": str(self)}
def _error(code: str, message: str) -> NativeParserDirectNativeInvocationFixtureError:
    return NativeParserDirectNativeInvocationFixtureError(code, message)
def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return value
def _require_string(mapping: Mapping[str, object], field: str) -> str:
    value = mapping.get(field)
    if type(value) is not str or not value.strip():
        raise _error("missing_explicit_sidecar_context", f"missing explicit sidecar context field {field!r}")
    return value
def _normalize_template_or_registry_entry(target: str, entry: object) -> str | dict[str, object]:
    if isinstance(entry, str) and entry:
        return entry
    if isinstance(entry, Mapping) and entry:
        copied = {str(key): _copy_value(value) for key, value in entry.items()}
        entry_target = copied.get("target", copied.get("canonical_target"))
        if entry_target is not None and entry_target != target:
            raise _error("ambiguous_explicit_sidecar_context", "target_registry_entry target does not match context target")
        template = copied.get("template")
        if template is not None and type(template) is not str:
            raise _error("ambiguous_explicit_sidecar_context", "target_registry_entry template must be a string")
        return copied
    raise _error("missing_explicit_sidecar_context", "template_or_target_registry_entry must be a non-empty string or mapping")
def _normalize_sidecar_context(sidecar_context: Mapping[str, object]) -> dict[str, object]:
    unknown = [key for key in sidecar_context if key not in ALLOWED_CONTEXT_FIELDS]
    if unknown:
        raise _error("ambiguous_explicit_sidecar_context", f"sidecar context contains non-boundary fields: {unknown!r}")
    target = _require_string(sidecar_context, "target")
    return {
        "target": target,
        "mode": _require_string(sidecar_context, "mode"),
        "template_or_target_registry_entry": _normalize_template_or_registry_entry(
            target, sidecar_context.get("template_or_target_registry_entry")
        ),
        "source_gate_or_manifest_ref": _require_string(sidecar_context, "source_gate_or_manifest_ref"),
    }
def _direct_fixture_result(argv: Sequence[str] | None, *, sidecar_context: Mapping[str, object], parser_payload: Mapping[str, object] | None) -> dict[str, object]:
    try:
        return define_direct_command_path_sidecar_plan_fixture(argv, sidecar_context=sidecar_context, parser_payload=parser_payload)
    except NativeParserDirectCommandPathFixtureError as exc:
        raise _error(exc.code, str(exc)) from exc
def _validate_native_argv(argv: Sequence[str] | None) -> None:
    if argv is None:
        return
    if not argv:
        raise _error("missing_native_invocation_argv", "native invocation fixture requires non-empty argv")
    if str(argv[0]).rsplit("/", 1)[-1] != "verilator":
        raise _error("non_verilator_native_invocation", "native invocation argv must start with a Verilator command")
def _validate_direct_fixture_result(result: Mapping[str, object]) -> None:
    missing = [field for field in DIRECT_COMMAND_PATH_FIXTURE_FIELDS if field not in result]
    unknown = [key for key in result if key not in DIRECT_COMMAND_PATH_FIXTURE_FIELDS]
    if missing or unknown:
        raise _error("invalid_direct_fixture_result", f"direct fixture fields mismatch: {missing=!r} {unknown=!r}")
    if result.get("surface") != DIRECT_COMMAND_PATH_FIXTURE_SURFACE:
        raise _error("invalid_direct_fixture_result", "direct fixture surface is not reviewed")
    if result.get("status") != DIRECT_COMMAND_PATH_STATUS:
        raise _error("invalid_direct_fixture_result", "direct fixture status is not ready")
    enabled = [field for field in FALSE_AUTHORITY_FLAGS[-7:] if result.get(field) is not False]
    if enabled:
        raise _error("direct_fixture_result_not_reference_only", f"direct fixture result has enabled flags: {enabled}")
def _native_invocation_metadata(argv: Sequence[str] | None) -> dict[str, object]:
    return {
        "argv": list(argv) if argv is not None else [],
        "argv_role": "metadata_only_not_execution_authority",
        "minimum_future_invocation_form": [
            "verilator", "--cc", "<ordinary Verilator build inputs>", "--sim-accel", "sidecar-gpu",
            "--sim-accel-states", "<positive N>", "--sim-accel-steps", "<positive S>",
        ],
        "requires_real_verilator_process_before_execution": True,
        "requires_explicit_sidecar_context_before_execution": True,
        "native_command_alone_is_execution_authority": False,
        "generated_command_text_is_source_of_truth": False,
    }
def define_direct_command_path_native_invocation_fixture(argv: Sequence[str] | None = None, *, sidecar_context: Mapping[str, object], parser_payload: Mapping[str, object] | None = None) -> dict[str, object]:
    """Return native-invocation handoff metadata without executing commands."""
    _validate_native_argv(argv)
    normalized_context = _normalize_sidecar_context(sidecar_context)
    result = _direct_fixture_result(argv, sidecar_context=normalized_context, parser_payload=parser_payload)
    _validate_direct_fixture_result(result)
    output = {
        "schema_version": 1,
        "surface": NATIVE_INVOCATION_FIXTURE_SURFACE,
        "status": NATIVE_INVOCATION_STATUS,
        "direct_fixture_surface": result["surface"],
        "parser_payload": _copy_value(result["parser_payload"]),
        "parser_preserved_build_inputs": _copy_value(result["parser_preserved_build_inputs"]),
        "sidecar_context": _copy_value(normalized_context),
        "native_invocation": _native_invocation_metadata(argv),
        "accelerator_mode": result["accelerator_mode"],
        "state_count": result["state_count"],
        "step_count": result["step_count"],
        "shape": result["shape"],
        "ordinary_verilator_args": _copy_value(result["ordinary_verilator_args"]),
        "mdir": result["mdir"],
        "top_module": result["top_module"],
        "source_files": _copy_value(result["source_files"]),
        "filelists": _copy_value(result["filelists"]),
        "defines": _copy_value(result["defines"]),
        "include_dirs": _copy_value(result["include_dirs"]),
        "warning_flags": _copy_value(result["warning_flags"]),
        "reviewed_sidecar_handoff_boundary": _copy_value(result["sidecar_plan_boundary"]),
        "required_stage_order": list(DIRECT_COMMAND_STAGE_ORDER),
        "correctness_policy_ref": result["correctness_policy_ref"],
        "correctness_policy_ref_status": "future_compare_result_only_not_native_invocation_evidence",
        "verilator_process_invoked": False,
        "wrapper_execution_used": False,
        "fixture_metadata_runtime_authority": False,
        "generated_command_text_source_of_truth": False,
        "generated_command_text_execution_authority": False,
        "native_command_alone_execution_authority": False,
        "sidecar_stage_plan_metadata_execution_authority": False,
        "materialized_stage_plan_metadata_execution_authority": False,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "source_closure_inferred": False,
        "filelists_expanded": False,
        "automatic_gpu_allocation_used": False,
        "non_claims": list(NON_CLAIMS),
    }
    assert tuple(output.keys()) == NATIVE_INVOCATION_FIELDS
    return output
def parser_payload_to_direct_command_path_native_invocation_fixture(parser_payload: Mapping[str, object], *, sidecar_context: Mapping[str, object]) -> dict[str, object]:
    """Name the parser-payload native-invocation fixture step explicitly."""
    return define_direct_command_path_native_invocation_fixture(sidecar_context=sidecar_context, parser_payload=parser_payload)
def _validate_direct_launch_handoff_scope(result: Mapping[str, object]) -> None:
    context = result["sidecar_context"]
    if context["target"] != "pulp_ita_mha" or result["shape"] != "64x1":
        raise _error("unsupported_direct_launch_handoff_scope", "direct launch handoff fixture is scoped to pulp_ita_mha 64x1")
    if context["template_or_target_registry_entry"] != "config/slice_launch_templates/pulp_ita_mha.json":
        raise _error("unsupported_direct_launch_handoff_scope", "direct launch handoff fixture requires the pulp_ita_mha template")
    if context["source_gate_or_manifest_ref"] != REVIEWED_HANDOFF_CONTEXT_REF:
        raise _error("sidecar_authority_failure", "direct launch handoff fixture requires the exact reviewed handoff authority")
def define_direct_launch_handoff_fixture(argv: Sequence[str] | None = None, *, sidecar_context: Mapping[str, object], parser_payload: Mapping[str, object] | None = None) -> dict[str, object]:
    """Return non-executing metadata for the native parser to sidecar-launcher handoff."""
    result = define_direct_command_path_native_invocation_fixture(argv, sidecar_context=sidecar_context, parser_payload=parser_payload)
    _validate_direct_launch_handoff_scope(result)
    output = {
        "schema_version": 1,
        "surface": DIRECT_LAUNCH_HANDOFF_FIXTURE_SURFACE,
        "status": DIRECT_LAUNCH_HANDOFF_STATUS,
        "native_invocation_surface": result["surface"],
        "handoff_ready": True,
        "sidecar_context": _copy_value(result["sidecar_context"]),
        "sidecar_launcher_entrypoint": "src/tools/run_hybrid_template.py",
        "required_stage_order": list(DIRECT_COMMAND_STAGE_ORDER),
        "preserved_failure_classes": list(PRESERVED_FAILURE_CLASSES),
        "sidecar_launch_reached_from_native_path": False,
        "coverage_output_compare_reached_from_native_path": False,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "automatic_gpu_allocation_used": False,
        "non_claims": list(HANDOFF_NON_CLAIMS),
    }
    assert tuple(output.keys()) == DIRECT_LAUNCH_HANDOFF_FIELDS
    return output
def _validate_handoff_fixture_for_bridge(handoff: Mapping[str, object]) -> None:
    if handoff.get("surface") != DIRECT_LAUNCH_HANDOFF_FIXTURE_SURFACE or handoff.get("status") != DIRECT_LAUNCH_HANDOFF_STATUS:
        raise _error("sidecar_launcher_bridge_failure", "bridge fixture requires reviewed direct-launch handoff metadata")
    if handoff.get("handoff_ready") is not True or handoff.get("sidecar_launcher_entrypoint") != "src/tools/run_hybrid_template.py":
        raise _error("sidecar_launcher_bridge_failure", "handoff metadata is not bridge-ready for the reviewed sidecar launcher")
    if handoff.get("sidecar_launch_reached_from_native_path") is not False or handoff.get("coverage_output_compare_reached_from_native_path") is not False:
        raise _error("sidecar_launcher_bridge_failure", "bridge fixture must remain non-executing")
def define_sidecar_launcher_bridge_fixture(argv: Sequence[str] | None = None, *, sidecar_context: Mapping[str, object], parser_payload: Mapping[str, object] | None = None) -> dict[str, object]:
    """Return non-executing metadata for the handoff-to-launcher bridge."""
    handoff = define_direct_launch_handoff_fixture(argv, sidecar_context=sidecar_context, parser_payload=parser_payload)
    _validate_handoff_fixture_for_bridge(handoff)
    output = {
        "schema_version": 1,
        "surface": SIDECAR_LAUNCHER_BRIDGE_FIXTURE_SURFACE,
        "status": SIDECAR_LAUNCHER_BRIDGE_STATUS,
        "handoff_surface": handoff["surface"],
        "bridge_ready": True,
        "sidecar_context": _copy_value(handoff["sidecar_context"]),
        "sidecar_launcher_entrypoint": handoff["sidecar_launcher_entrypoint"],
        "sidecar_launcher_entrypoint_role": "reference_only_not_invoked_by_fixture",
        "required_stage_order": list(DIRECT_COMMAND_STAGE_ORDER),
        "preserved_failure_classes": list(BRIDGE_FAILURE_CLASSES),
        "sidecar_launch_reached_from_native_path": False,
        "coverage_output_compare_reached_from_native_path": False,
        "native_path_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "automatic_gpu_allocation_used": False,
        "non_claims": list(BRIDGE_NON_CLAIMS),
    }
    assert tuple(output.keys()) == SIDECAR_LAUNCHER_BRIDGE_FIELDS
    return output
def define_sidecar_launcher_invocation_fixture(
    argv: Sequence[str] | None = None,
    *,
    sidecar_context: Mapping[str, object],
    source_review_gate: str,
    parser_payload: Mapping[str, object] | None = None,
    bridge_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Materialize the reviewed sidecar-launcher argv without executing it."""
    native_result = define_direct_command_path_native_invocation_fixture(
        argv,
        sidecar_context=sidecar_context,
        parser_payload=parser_payload,
    )
    bridge = (
        {str(key): _copy_value(value) for key, value in bridge_metadata.items()}
        if bridge_metadata is not None
        else define_sidecar_launcher_bridge_fixture(argv, sidecar_context=sidecar_context, parser_payload=parser_payload)
    )
    output = build_sidecar_launcher_invocation_fixture(
        native_result=native_result,
        bridge_metadata=bridge,
        source_review_gate=source_review_gate,
        required_stage_order=DIRECT_COMMAND_STAGE_ORDER,
        error_factory=_error,
    )
    assert tuple(output.keys()) == SIDECAR_LAUNCHER_INVOCATION_FIELDS
    return output
