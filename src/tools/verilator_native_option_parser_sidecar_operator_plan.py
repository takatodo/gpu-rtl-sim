"""Non-executing operator-plan metadata helper for ready handoff contracts."""
from __future__ import annotations
from collections.abc import Mapping
import shlex
from hybrid_benchmark_efficiency import efficiency_estimate
from hybrid_benchmark_sidecar_operator import sidecar_operator_plan, synthesized_verilator_command_argv, synthesized_verilator_estimate_command_argv
from hybrid_benchmark_specs import CORRECTNESS_POLICY_COVERAGE_OUTPUT, STATUS_READY_FOR_VERILATOR_OPTION_SHIM
from verilator_native_option_parser_sidecar_handoff_contract import HANDOFF_CONTRACT_FIXTURE_SURFACE
OPERATOR_PLAN_FIXTURE_SURFACE = "native_verilator_parser_sidecar_operator_plan_fixture"
HANDOFF_READY = "ready_for_sidecar_handoff_contract_metadata"
HANDOFF_NOT_READY = "not_ready_for_sidecar_handoff_contract_metadata"
HANDOFF_UNSUPPORTED = "unsupported_for_sidecar_handoff_contract_metadata"
PLAN_FLAGS = (
    "command_synthesis_invoked", "operator_plan_invoked", "efficiency_estimate_invoked", "execution_performed",
    "measurement_performed", "timing_measured", "runtime_or_abi_changed", "source_closure_inferred",
    "filelists_expanded", "automatic_gpu_allocation_used",
)
FALSE_READY_FLAGS = PLAN_FLAGS
FORBIDDEN_OPERATOR_PLAN_INPUT_FIELDS = frozenset((
    "operator_plan", "command_argv", "command", "estimate_command_argv", "estimate_command", "efficiency_estimate",
    "timing", "verilator_command", "verilator_command_argv", "verilator_estimate_command",
    "verilator_estimate_command_argv",
))
HANDOFF_CONTRACT_FIELDS = ("shape", "nstates", "steps", "state_files", "compare", "generated_reports", "non_claims")
STATE_FILE_FIELDS = ("init_state", "reference_dump", "candidate_dump")
COMPARE_FIELDS = ("correctness_policy", "acceptance_policy", "reference_label", "candidate_label", "coverage_output_target")
STAGE_REQUIRED_FIELDS = {
    "verilator_build": ("mdir", "top_module", "source_files"),
    "hybrid_sidecar_run": ("nstates", "steps", "init_state"),
    "coverage_output_compare": (
        "reference_dump", "candidate_dump", "acceptance_policy", "reference_label", "candidate_label",
        "coverage_output_target", "json_out",
    ),
}
class OperatorPlanHandoffContractError(ValueError): pass
def _fail(error_factory, message): raise error_factory(message)
def _mapping(mapping, field, error_factory):
    if field not in mapping:
        _fail(error_factory, f"missing required field {field!r}")
    value = mapping[field]
    if not isinstance(value, Mapping):
        _fail(error_factory, f"field {field!r} must be a mapping")
    return value
def _string(mapping, field, error_factory):
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        _fail(error_factory, f"field {field!r} must be a non-empty string")
    return value
def _positive_int(mapping, field, error_factory, *, default=None):
    value = mapping.get(field, default) if default is not None else mapping.get(field)
    if not isinstance(value, int) or value <= 0:
        _fail(error_factory, f"field {field!r} must be a positive integer")
    return value
def _require_fields(mapping, fields, label, error_factory):
    missing = [field for field in fields if field not in mapping]
    if missing:
        _fail(error_factory, f"{label} is missing required fields: {missing}")
def _stage(stage_plan, name, error_factory):
    stages = stage_plan.get("stages", [])
    if not isinstance(stages, list):
        _fail(error_factory, "stage_plan.stages must be a list")
    for item in stages:
        if isinstance(item, Mapping) and item.get("stage") == name:
            details = item.get("details", {})
            if not isinstance(details, Mapping):
                _fail(error_factory, f"stage {name!r} details must be a mapping")
            return details
    _fail(error_factory, f"missing required stage {name!r}")
    raise AssertionError("unreachable")
def _closed_status(status):
    if status == HANDOFF_UNSUPPORTED:
        return "unsupported_for_sidecar_operator_plan_metadata"
    return "not_ready_for_sidecar_operator_plan_metadata"
def _false_metadata_flags(handoff_invoked=True):
    return {"sidecar_handoff_contract_invoked": handoff_invoked, **{flag: False for flag in PLAN_FLAGS}}
def _closed_result(reason, handoff_metadata):
    readiness = handoff_metadata.get("plan_resolution_readiness")
    readiness_record = dict(readiness) if isinstance(readiness, Mapping) else {}
    missing = readiness_record.get("missing_readiness_inputs", [])
    return {
        "schema_version": 1,
        "surface": OPERATOR_PLAN_FIXTURE_SURFACE,
        "status": _closed_status(handoff_metadata.get("status")),
        "input_surface": handoff_metadata.get("surface"),
        "input_status": handoff_metadata.get("status"),
        "operator_plan_metadata_allowed": False,
        "fail_closed_reason": reason,
        "plan_resolution_readiness": readiness_record,
        "missing_readiness_inputs": missing if isinstance(missing, list) else [],
        **_false_metadata_flags(bool(handoff_metadata.get("sidecar_handoff_contract_invoked", False))),
        "non_claims": [
            "operator-plan closed result does not include command or operator-plan metadata",
            "closed handoff-contract metadata is not command synthesis evidence",
            "closed handoff-contract metadata is not timing or correctness evidence",
        ],
    }
def _validated_handoff_contract(handoff_metadata, error_factory):
    handoff = _mapping(handoff_metadata, "handoff_contract", error_factory)
    _require_fields(handoff, HANDOFF_CONTRACT_FIELDS, "handoff_contract", error_factory)
    nstates = _positive_int(handoff, "nstates", error_factory)
    steps = _positive_int(handoff, "steps", error_factory)
    shape = _string(handoff, "shape", error_factory)
    if shape != f"{nstates}x{steps}":
        _fail(error_factory, f"handoff_contract shape {shape!r} does not match nstates/steps {nstates}x{steps}")
    state_files = _mapping(handoff, "state_files", error_factory)
    compare = _mapping(handoff, "compare", error_factory)
    generated_reports = _mapping(handoff, "generated_reports", error_factory)
    _require_fields(state_files, STATE_FILE_FIELDS, "handoff_contract.state_files", error_factory)
    _require_fields(compare, COMPARE_FIELDS, "handoff_contract.compare", error_factory)
    _require_fields(generated_reports, ("compare_report",), "handoff_contract.generated_reports", error_factory)
    if compare.get("correctness_policy") != CORRECTNESS_POLICY_COVERAGE_OUTPUT:
        _fail(error_factory, "handoff_contract.compare correctness_policy is not coverage_output_equivalence")
    if not isinstance(handoff.get("non_claims"), list):
        _fail(error_factory, "handoff_contract.non_claims must be a list")
    return handoff
def _validate_stage_details(details, handoff, error_factory):
    run_shape = f"{details['hybrid_sidecar_run']['nstates']}x{details['hybrid_sidecar_run']['steps']}"
    if run_shape != handoff["shape"]:
        _fail(error_factory, f"hybrid_sidecar_run shape {run_shape!r} does not match handoff shape {handoff['shape']!r}")
    state_files = _mapping(handoff, "state_files", error_factory)
    compare = _mapping(handoff, "compare", error_factory)
    reports = _mapping(handoff, "generated_reports", error_factory)
    expected_pairs = [
        (state_files, "init_state", details["hybrid_sidecar_run"], "init_state"),
        (state_files, "reference_dump", details["coverage_output_compare"], "reference_dump"),
        (state_files, "candidate_dump", details["coverage_output_compare"], "candidate_dump"),
        (reports, "compare_report", details["coverage_output_compare"], "json_out"),
    ]
    expected_pairs.extend((compare, field, details["coverage_output_compare"], field) for field in COMPARE_FIELDS[1:])
    for left, left_field, right, right_field in expected_pairs:
        if left.get(left_field) != right.get(right_field):
            _fail(error_factory, f"handoff_contract.{left_field} does not match stage plan")
def _validate_stage_plan(handoff_metadata, handoff, error_factory):
    stage_plan = _mapping(handoff_metadata, "stage_plan", error_factory)
    expected = {"status": "planned", "shape": handoff.get("shape"), "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT}
    for field, value in expected.items():
        if stage_plan.get(field) != value:
            _fail(error_factory, f"stage_plan.{field} does not match expected {value!r}")
    readiness = _mapping(stage_plan, "verilator_option_readiness", error_factory)
    if readiness.get("status") != STATUS_READY_FOR_VERILATOR_OPTION_SHIM:
        _fail(error_factory, "stage_plan readiness is not ready_for_verilator_option_shim")
    details = {name: _stage(stage_plan, name, error_factory) for name in STAGE_REQUIRED_FIELDS}
    for name, fields in STAGE_REQUIRED_FIELDS.items():
        _require_fields(details[name], fields, f"stage {name!r}", error_factory)
    _validate_stage_details(details, handoff, error_factory)
    return stage_plan
def _validate_ready_input(handoff_metadata, error_factory):
    if handoff_metadata.get("sidecar_handoff_contract_invoked") is not True:
        _fail(error_factory, "field 'sidecar_handoff_contract_invoked' must be True")
    for field in FALSE_READY_FLAGS:
        if handoff_metadata.get(field) is not False:
            _fail(error_factory, f"field {field!r} must be False")
    expected_fields = (
        ("input_status", STATUS_READY_FOR_VERILATOR_OPTION_SHIM),
        ("correctness_policy", CORRECTNESS_POLICY_COVERAGE_OUTPUT),
        ("correctness_policy_ref_status", "reference_only_not_compare_evidence"),
    )
    for field, expected in expected_fields:
        if handoff_metadata.get(field) != expected:
            _fail(error_factory, f"field {field!r} must be {expected!r}")
    readiness = _mapping(handoff_metadata, "plan_resolution_readiness", error_factory)
    readiness_expected = {
        "ready_for_direct_verilator_option": True,
        "stage_plan_status": "planned",
        "verilator_option_readiness_status": STATUS_READY_FOR_VERILATOR_OPTION_SHIM,
    }
    for field, expected in readiness_expected.items():
        if readiness.get(field) != expected:
            _fail(error_factory, f"plan_resolution_readiness.{field} must be {expected!r}")
    handoff = _validated_handoff_contract(handoff_metadata, error_factory)
    cross = _mapping(handoff_metadata, "parser_schedule_cross_check", error_factory)
    if cross.get("shape_matches_handoff_contract") is not True:
        _fail(error_factory, "parser_schedule_cross_check.shape_matches_handoff_contract is not true")
    for left, right in (("shape", "shape"), ("state_count", "nstates"), ("step_count", "steps")):
        if cross.get(left) != handoff.get(right):
            _fail(error_factory, f"parser_schedule_cross_check.{left} does not match handoff_contract.{right}")
    return _validate_stage_plan(handoff_metadata, handoff, error_factory), handoff
def resolve_handoff_contract_to_operator_plan(
    handoff_metadata,
    *,
    error_factory=OperatorPlanHandoffContractError,
    command_builder=synthesized_verilator_command_argv,
    estimate_command_builder=synthesized_verilator_estimate_command_argv,
    efficiency_builder=efficiency_estimate,
    operator_plan_builder=sidecar_operator_plan,
):
    if handoff_metadata.get("surface") != HANDOFF_CONTRACT_FIXTURE_SURFACE:
        _fail(error_factory, "handoff-contract surface is not the reviewed fixture")
    forbidden = sorted(FORBIDDEN_OPERATOR_PLAN_INPUT_FIELDS.intersection(handoff_metadata))
    if forbidden:
        _fail(error_factory, f"handoff-contract result already contains operator-plan fields: {forbidden}")
    status = handoff_metadata.get("status")
    if status in (HANDOFF_NOT_READY, HANDOFF_UNSUPPORTED):
        return _closed_result("handoff-contract metadata is not ready for operator-plan metadata", handoff_metadata)
    if status != HANDOFF_READY:
        _fail(error_factory, "handoff-contract status is not ready_for_sidecar_handoff_contract_metadata")
    stage_plan, handoff = _validate_ready_input(handoff_metadata, error_factory)
    command_argv = command_builder(dict(stage_plan))
    estimate_command_argv = estimate_command_builder(command_argv)
    limit = stage_plan.get("limit")
    if limit is not None and not isinstance(limit, int):
        _fail(error_factory, "stage_plan.limit must be an integer when provided")
    estimate = efficiency_builder(
        target=_string(stage_plan, "target", error_factory),
        shape=_string(stage_plan, "shape", error_factory),
        limit=limit,
        mode=_string(stage_plan, "mode", error_factory),
        phases=_positive_int(stage_plan, "phases", error_factory, default=4),
    )
    command = shlex.join(command_argv)
    operator_plan = operator_plan_builder(command_argv=command_argv, command=command, efficiency_estimate=estimate, handoff_contract=dict(handoff))
    flags = _false_metadata_flags()
    flags.update(command_synthesis_invoked=True, operator_plan_invoked=True, efficiency_estimate_invoked=True)
    preserved_inputs = handoff_metadata.get("parser_preserved_build_inputs", {})
    input_role = handoff_metadata.get("parser_input_resolution_role", {})
    return {
        "schema_version": 1,
        "surface": OPERATOR_PLAN_FIXTURE_SURFACE,
        "status": "ready_for_sidecar_operator_plan_metadata",
        "input_surface": handoff_metadata["surface"],
        "input_status": handoff_metadata["status"],
        "operator_plan_metadata_allowed": True,
        **flags,
        "correctness_policy_ref_status": "reference_only_not_compare_evidence",
        "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
        "command_argv": command_argv,
        "command": command,
        "estimate_command_argv": estimate_command_argv,
        "estimate_command": shlex.join(estimate_command_argv),
        "estimate_flag": operator_plan["estimate_flag"],
        "requested_compatibility_entrypoint": operator_plan["requested_compatibility_entrypoint"],
        "efficiency_estimate": estimate,
        "handoff_contract": dict(handoff),
        "operator_plan": operator_plan,
        "plan_resolution_readiness": dict(_mapping(handoff_metadata, "plan_resolution_readiness", error_factory)),
        "parser_schedule_cross_check": dict(_mapping(handoff_metadata, "parser_schedule_cross_check", error_factory)),
        "parser_preserved_build_inputs": dict(preserved_inputs) if isinstance(preserved_inputs, Mapping) else {},
        "parser_input_resolution_role": dict(input_role) if isinstance(input_role, Mapping) else {},
        "estimate_metadata_boundary": "efficiency_estimate is non-executing planning metadata only, not measured timing or speedup evidence",
        "non_claims": [
            "operator-plan fixture does not execute commands",
            "operator-plan fixture is not native Verilator parser support",
            "operator-plan fixture is not sidecar runtime handoff validation",
            "operator-plan fixture is not RTL simulation execution",
            "operator-plan fixture is not coverage-output equivalence evidence",
            "efficiency_estimate metadata is not measured timing or speedup evidence",
            "parser source files and filelists remain preserved inputs, not inferred source closure",
            "arbitrary filelists and automatic GPU allocation remain out of scope",
        ],
    }
