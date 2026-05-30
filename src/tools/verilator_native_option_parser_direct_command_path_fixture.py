"""Non-executing direct command-path fixture for future Verilator GPU options."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

try:
    from .verilator_native_option_parser_stub_fixture import (
        CORRECTNESS_POLICY,
        SOURCE_BOUNDARY_STATUS,
        NativeOptionParserStubError,
        parse_verilator_native_option_stub,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from verilator_native_option_parser_stub_fixture import (
        CORRECTNESS_POLICY,
        SOURCE_BOUNDARY_STATUS,
        NativeOptionParserStubError,
        parse_verilator_native_option_stub,
    )


DIRECT_COMMAND_PATH_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_fixture"
DIRECT_COMMAND_PATH_REJECTION_LAYER = "direct_command_path_fixture_contract"
DIRECT_COMMAND_PATH_STATUS = "fixture_contract_ready_for_sidecar_plan_boundary"
GENERATED_EVIDENCE_POLICY = "reports/ and artifacts/ are generated evidence only and never source of truth"
STATE_AND_REPORT_NAMING_RULES = "sidecar_owned_not_materialized_by_direct_command_path_fixture"

REQUIRED_CONTEXT_FIELDS = tuple("target mode template_or_target_registry_entry source_gate_or_manifest_ref".split())
PARSER_PRESERVED_BUILD_INPUT_FIELDS = tuple(
    "ordinary_verilator_args mdir top_module source_files filelists defines include_dirs warning_flags".split()
)
DIRECT_COMMAND_STAGE_ORDER = tuple(
    "verilator_build host_probe_build cpu_init_state cpu_reference_output gpu_artifact_build "
    "hybrid_sidecar_run coverage_output_compare".split()
)

DIRECT_COMMAND_PATH_FIXTURE_FIELDS = tuple(
    "schema_version surface status parser_payload parser_preserved_build_inputs sidecar_context "
    "accelerator_mode state_count step_count shape ordinary_verilator_args mdir top_module "
    "source_files filelists defines include_dirs warning_flags sidecar_plan_boundary correctness_policy_ref "
    "execution_performed measurement_performed timing_measured runtime_or_abi_changed "
    "source_closure_inferred filelists_expanded automatic_gpu_allocation_used non_claims".split()
)

SIDECAR_OWNED_FIELDS = frozenset(
    "sidecar_plan_boundary sidecar_stage_plan stage_plan state_authority state_files generated_reports compare "
    "acceptance_policy compare_labels coverage_output_target coverage_output_gate_or_manifest_ref "
    "host_probe_build_metadata_ref source_closure_authority init_state_path init_state_path_or_rule "
    "reference_dump_path reference_dump_path_or_rule candidate_dump_path candidate_dump_path_or_rule "
    "compare_report_path compare_report_path_or_rule verilator_command verilator_command_argv "
    "execution_performed measurement_performed timing_measured runtime_or_abi_changed source_closure_inferred "
    "filelists_expanded automatic_gpu_allocation_used".split()
)

NON_CLAIMS = (
    "direct command-path fixture does not execute Verilator or hybrid runtime",
    "direct command-path fixture does not materialize a sidecar stage plan",
    "direct command-path fixture keeps coverage_output_equivalence as later sidecar compare policy only",
    "direct command-path fixture does not infer source closure, expand filelists, select host-probe metadata, or allocate GPU work",
    "direct command-path fixture is not native Verilator option support",
)


class NativeParserDirectCommandPathFixtureError(ValueError):
    """Structured direct command-path fixture validation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.rejection_layer = DIRECT_COMMAND_PATH_REJECTION_LAYER

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "rejection_layer": self.rejection_layer, "message": str(self)}


def _error(code: str, message: str) -> NativeParserDirectCommandPathFixtureError:
    return NativeParserDirectCommandPathFixtureError(code, message)


def _has_option(tokens: Sequence[str], option: str) -> bool:
    prefix = f"{option}="
    return any(token == option or token.startswith(prefix) for token in tokens)


def _validate_direct_shape_spelling(argv: Sequence[str]) -> None:
    compact = _has_option(argv, "--sim-accel-shape")
    expanded = _has_option(argv, "--sim-accel-states") or _has_option(argv, "--sim-accel-steps")
    if compact and expanded:
        raise _error(
            "mixed_sim_accel_shape_spelling",
            "compact --sim-accel-shape must not be mixed with expanded --sim-accel-states/--sim-accel-steps "
            "in the direct native command-path fixture",
        )
    if compact:
        raise _error(
            "compact_shape_spelling_outside_native_minimum",
            "compact --sim-accel-shape is wrapper compatibility and outside the direct native command-path minimum; "
            "use --sim-accel-states and --sim-accel-steps",
        )


def _parse_direct_argv(argv: Sequence[str]) -> dict[str, object]:
    _validate_direct_shape_spelling(argv)
    try:
        return parse_verilator_native_option_stub(argv)
    except NativeOptionParserStubError as exc:
        raise _error(exc.code, str(exc)) from exc


def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _require_context(sidecar_context: Mapping[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for field in REQUIRED_CONTEXT_FIELDS:
        value = sidecar_context.get(field)
        if value is None or value == {} or value == "":
            raise _error("missing_explicit_sidecar_context", f"missing explicit sidecar context field {field!r}")
        normalized[field] = _copy_value(value)
    return normalized


def _reject_sidecar_owned_parser_fields(parser_payload: Mapping[str, object]) -> None:
    forbidden = sorted(SIDECAR_OWNED_FIELDS.intersection(parser_payload))
    if forbidden:
        raise _error(
            "sidecar_owned_field_prepopulated_by_parser",
            f"parser payload already contains sidecar-owned fields: {forbidden}",
        )


def _require_positive_int(parser_payload: Mapping[str, object], field: str) -> int:
    value = parser_payload.get(field)
    if type(value) is not int or value <= 0:
        raise _error("invalid_parser_payload", f"parser payload field {field!r} must be a positive integer")
    return value


def _require_list(parser_payload: Mapping[str, object], field: str) -> list[object]:
    value = parser_payload.get(field)
    if not isinstance(value, list):
        raise _error("invalid_parser_payload", f"parser payload field {field!r} must be a list")
    return list(value)


def _validate_parser_payload(parser_payload: Mapping[str, object]) -> tuple[int, int, str]:
    _reject_sidecar_owned_parser_fields(parser_payload)
    if parser_payload.get("accelerator_mode") != "sidecar-gpu":
        raise _error("invalid_parser_payload", "parser payload accelerator_mode must be 'sidecar-gpu'")
    if parser_payload.get("correctness_policy") != CORRECTNESS_POLICY:
        raise _error("invalid_parser_payload", f"parser payload correctness_policy must be {CORRECTNESS_POLICY!r}")
    state_count = _require_positive_int(parser_payload, "state_count")
    step_count = _require_positive_int(parser_payload, "step_count")
    shape = parser_payload.get("shape")
    expected_shape = f"{state_count}x{step_count}"
    if shape != expected_shape:
        raise _error("invalid_parser_payload", f"parser payload shape must be {expected_shape!r}")
    return state_count, step_count, expected_shape


def _preserved_build_inputs(parser_payload: Mapping[str, object]) -> dict[str, object]:
    preserved: dict[str, object] = {}
    for field in PARSER_PRESERVED_BUILD_INPUT_FIELDS:
        if field in ("mdir", "top_module"):
            preserved[field] = parser_payload.get(field)
        else:
            preserved[field] = _require_list(parser_payload, field)
    return preserved


def _sidecar_plan_boundary(sidecar_context: Mapping[str, object]) -> dict[str, object]:
    return {
        "source_boundary_status": SOURCE_BOUNDARY_STATUS,
        "source_closure_authority": "sidecar_owned_required_before_execution",
        "coverage_output_target": sidecar_context["target"],
        "coverage_output_gate_or_manifest_ref": sidecar_context["source_gate_or_manifest_ref"],
        "host_probe_build_metadata_ref": sidecar_context["template_or_target_registry_entry"],
        "state_and_report_naming_rules": STATE_AND_REPORT_NAMING_RULES,
        "stage_order_required": list(DIRECT_COMMAND_STAGE_ORDER),
        "generated_evidence_policy": GENERATED_EVIDENCE_POLICY,
        "non_claims": list(NON_CLAIMS),
    }


def define_direct_command_path_sidecar_plan_fixture(
    argv: Sequence[str] | None = None,
    *,
    sidecar_context: Mapping[str, object],
    parser_payload: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return direct command-path metadata without executing Verilator or sidecar stages."""

    if parser_payload is None:
        if argv is None:
            raise _error("missing_direct_command_argv", "direct command-path fixture requires argv or parser_payload")
        parser_payload = _parse_direct_argv(argv)
    else:
        parser_payload = dict(parser_payload)

    state_count, step_count, shape = _validate_parser_payload(parser_payload)
    normalized_context = _require_context(sidecar_context)
    preserved = _preserved_build_inputs(parser_payload)

    output = {
        "schema_version": 1,
        "surface": DIRECT_COMMAND_PATH_FIXTURE_SURFACE,
        "status": DIRECT_COMMAND_PATH_STATUS,
        "parser_payload": {str(key): _copy_value(value) for key, value in parser_payload.items()},
        "parser_preserved_build_inputs": preserved,
        "sidecar_context": normalized_context,
        "accelerator_mode": "sidecar-gpu",
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
        "sidecar_plan_boundary": _sidecar_plan_boundary(normalized_context),
        "correctness_policy_ref": CORRECTNESS_POLICY,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "source_closure_inferred": False,
        "filelists_expanded": False,
        "automatic_gpu_allocation_used": False,
        "non_claims": list(NON_CLAIMS),
    }
    assert tuple(output.keys()) == DIRECT_COMMAND_PATH_FIXTURE_FIELDS
    return output


def direct_command_parser_payload_to_sidecar_plan_fixture(
    parser_payload: Mapping[str, object], *, sidecar_context: Mapping[str, object]
) -> dict[str, object]:
    """Name the parser-payload to sidecar-boundary fixture step explicitly."""
    return define_direct_command_path_sidecar_plan_fixture(sidecar_context=sidecar_context, parser_payload=parser_payload)
