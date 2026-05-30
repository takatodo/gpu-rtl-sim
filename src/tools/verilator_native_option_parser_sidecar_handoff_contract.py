"""Non-executing handoff-contract metadata helper for ready plan-resolution results."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from hybrid_benchmark_sidecar_operator import sidecar_handoff_contract
from hybrid_benchmark_specs import CORRECTNESS_POLICY_COVERAGE_OUTPUT, STATUS_READY_FOR_VERILATOR_OPTION_SHIM
from hybrid_benchmark_specs import STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM, STATUS_UNSUPPORTED_FOR_STAGE_PLAN

PLAN_RESOLUTION_SURFACE = "native_verilator_parser_sidecar_plan_resolution_fixture"
HANDOFF_CONTRACT_FIXTURE_SURFACE = "native_verilator_parser_sidecar_plan_resolution_handoff_contract_fixture"

REQUIRED_HYBRID_RUN_DETAIL_FIELDS = ("nstates", "steps", "init_state")
REQUIRED_COMPARE_DETAIL_FIELDS = ("reference_dump", "candidate_dump", "acceptance_policy", "reference_label")
REQUIRED_COMPARE_DETAIL_FIELDS += ("candidate_label", "coverage_output_target", "json_out")
FORBIDDEN_HANDOFF_CONTRACT_INPUT_FIELDS = frozenset(
    ("handoff_contract", "operator_plan", "command_argv", "verilator_command")
    + ("verilator_command_argv", "timing", "efficiency_estimate")
)


class HandoffContractPlanResolutionError(ValueError):
    pass


ErrorFactory = Callable[[str], Exception]
HandoffBuilder = Callable[[dict[str, object]], dict[str, object]]


def _raise(error_factory: ErrorFactory, message: str) -> None:
    raise error_factory(message)


def _mapping_value(mapping: Mapping[str, object], field: str, error_factory: ErrorFactory) -> Mapping[str, object]:
    if field not in mapping:
        _raise(error_factory, f"missing required field {field!r}")
    value = mapping[field]
    if not isinstance(value, Mapping):
        _raise(error_factory, f"field {field!r} must be a mapping")
    return value


def _closed_status(status: object) -> str:
    if status == STATUS_UNSUPPORTED_FOR_STAGE_PLAN:
        return "unsupported_for_sidecar_handoff_contract_metadata"
    return "not_ready_for_sidecar_handoff_contract_metadata"


def _closed_result(reason: str, plan_resolution: Mapping[str, object]) -> dict[str, object]:
    readiness = plan_resolution.get("plan_resolution_readiness")
    readiness_record: dict[str, object] = {}
    missing_readiness_inputs: object = []
    stage_plan_status = None
    if isinstance(readiness, Mapping):
        readiness_record = dict(readiness)
        missing_readiness_inputs = readiness.get("missing_readiness_inputs", [])
        stage_plan_status = readiness.get("stage_plan_status")
    return {
        "schema_version": 1,
        "surface": HANDOFF_CONTRACT_FIXTURE_SURFACE,
        "status": _closed_status(plan_resolution.get("status")),
        "input_surface": plan_resolution.get("surface"),
        "input_status": plan_resolution.get("status"),
        "handoff_contract_metadata_allowed": False,
        "fail_closed_reason": reason,
        "stage_plan_status": stage_plan_status,
        "plan_resolution_readiness": readiness_record,
        "missing_readiness_inputs": missing_readiness_inputs,
        "sidecar_handoff_contract_invoked": False,
        "command_synthesis_invoked": False,
        "operator_plan_invoked": False,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "source_closure_inferred": False,
        "filelists_expanded": False,
        "automatic_gpu_allocation_used": False,
        "non_claims": [
            "handoff-contract closed result does not include handoff_contract metadata",
            "not-ready and unsupported plan-resolution outputs are not runtime handoff validation",
            "not-ready and unsupported plan-resolution outputs are not correctness or timing evidence",
        ],
    }


def _require_flag(mapping: Mapping[str, object], field: str, expected: bool, error_factory: ErrorFactory) -> None:
    if mapping.get(field) is not expected:
        _raise(error_factory, f"field {field!r} must be {expected!r}")


def _stage_details(
    stage_plan: Mapping[str, object],
    stage_name: str,
    error_factory: ErrorFactory,
) -> Mapping[str, object]:
    stages = stage_plan.get("stages", [])
    if not isinstance(stages, list):
        _raise(error_factory, "stage_plan.stages must be a list")
    for stage in stages:
        if isinstance(stage, Mapping) and stage.get("stage") == stage_name:
            details = stage.get("details", {})
            if not isinstance(details, Mapping):
                _raise(error_factory, f"stage {stage_name!r} details must be a mapping")
            return details
    _raise(error_factory, f"missing required stage {stage_name!r}")
    raise AssertionError("unreachable")


def _require_detail_fields(
    details: Mapping[str, object],
    fields: tuple[str, ...],
    stage_name: str,
    error_factory: ErrorFactory,
) -> None:
    missing = [field for field in fields if field not in details]
    if missing:
        _raise(error_factory, f"stage {stage_name!r} is missing detail fields: {missing}")


def _validate_ready_input(
    plan_resolution: Mapping[str, object],
    *,
    error_factory: ErrorFactory,
) -> Mapping[str, object]:
    forbidden = sorted(FORBIDDEN_HANDOFF_CONTRACT_INPUT_FIELDS.intersection(plan_resolution))
    if forbidden:
        _raise(error_factory, f"plan-resolution result already contains handoff/execution fields: {forbidden}")
    if plan_resolution.get("surface") != PLAN_RESOLUTION_SURFACE:
        _raise(error_factory, "plan-resolution surface is not the reviewed fixture")
    _require_flag(plan_resolution, "sidecar_stage_plan_invoked", True, error_factory)
    _require_flag(plan_resolution, "sidecar_handoff_contract_invoked", False, error_factory)
    _require_flag(plan_resolution, "command_synthesis_invoked", False, error_factory)
    _require_flag(plan_resolution, "efficiency_estimate_invoked", False, error_factory)
    _require_flag(plan_resolution, "execution_performed", False, error_factory)
    _require_flag(plan_resolution, "measurement_performed", False, error_factory)
    if plan_resolution.get("status") != STATUS_READY_FOR_VERILATOR_OPTION_SHIM:
        _raise(error_factory, "outer status is not ready_for_verilator_option_shim")
    if plan_resolution.get("correctness_policy") != CORRECTNESS_POLICY_COVERAGE_OUTPUT:
        _raise(error_factory, "plan-resolution correctness_policy is not coverage_output_equivalence")
    if plan_resolution.get("correctness_policy_ref_status") != "reference_only_not_compare_evidence":
        _raise(error_factory, "correctness policy ref is not reference-only")

    readiness = _mapping_value(plan_resolution, "plan_resolution_readiness", error_factory)
    if readiness.get("ready_for_direct_verilator_option") is not True:
        _raise(error_factory, "ready_for_direct_verilator_option is not true")
    if readiness.get("stage_plan_status") != "planned":
        _raise(error_factory, "plan_resolution_readiness.stage_plan_status is not planned")
    if readiness.get("verilator_option_readiness_status") != STATUS_READY_FOR_VERILATOR_OPTION_SHIM:
        _raise(error_factory, "readiness status is not ready_for_verilator_option_shim")

    stage_plan = _mapping_value(plan_resolution, "stage_plan", error_factory)
    if stage_plan.get("status") != "planned":
        _raise(error_factory, "stage_plan.status is not planned")
    stage_readiness = _mapping_value(stage_plan, "verilator_option_readiness", error_factory)
    if stage_readiness.get("status") != STATUS_READY_FOR_VERILATOR_OPTION_SHIM:
        _raise(error_factory, "stage_plan readiness is not ready_for_verilator_option_shim")
    _validate_shapes(plan_resolution, stage_plan, error_factory)
    return stage_plan


def _validate_shapes(
    plan_resolution: Mapping[str, object],
    stage_plan: Mapping[str, object],
    error_factory: ErrorFactory,
) -> None:
    parser_schedule = _mapping_value(plan_resolution, "parser_schedule_constraints", error_factory)
    parser_shape = parser_schedule.get("shape")
    state_count = parser_schedule.get("state_count")
    step_count = parser_schedule.get("step_count")
    if not isinstance(parser_shape, str) or not parser_shape:
        _raise(error_factory, "parser_schedule_constraints.shape must be a non-empty string")
    if not isinstance(state_count, int) or state_count <= 0:
        _raise(error_factory, "parser_schedule_constraints.state_count must be a positive integer")
    if not isinstance(step_count, int) or step_count <= 0:
        _raise(error_factory, "parser_schedule_constraints.step_count must be a positive integer")
    expected_parser_shape = f"{state_count}x{step_count}"
    if parser_shape != expected_parser_shape:
        _raise(
            error_factory,
            f"parser_schedule_constraints.shape {parser_shape!r} does not match state/step {expected_parser_shape!r}",
        )
    if parser_shape != stage_plan.get("shape"):
        _raise(
            error_factory,
            f"parser_schedule_constraints.shape {parser_shape!r} does not match stage_plan.shape {stage_plan.get('shape')!r}",
        )
    hybrid_run_details = _stage_details(stage_plan, "hybrid_sidecar_run", error_factory)
    compare_details = _stage_details(stage_plan, "coverage_output_compare", error_factory)
    _require_detail_fields(hybrid_run_details, REQUIRED_HYBRID_RUN_DETAIL_FIELDS, "hybrid_sidecar_run", error_factory)
    _require_detail_fields(compare_details, REQUIRED_COMPARE_DETAIL_FIELDS, "coverage_output_compare", error_factory)
    run_shape = f"{hybrid_run_details['nstates']}x{hybrid_run_details['steps']}"
    if run_shape != parser_shape:
        _raise(error_factory, f"hybrid_sidecar_run shape {run_shape!r} does not match parser shape {parser_shape!r}")


def resolve_plan_resolution_to_handoff_contract(
    plan_resolution: Mapping[str, object],
    *,
    error_factory: ErrorFactory = HandoffContractPlanResolutionError,
    handoff_builder: HandoffBuilder = sidecar_handoff_contract,
) -> dict[str, object]:
    """Build or fail-close non-executing sidecar_handoff_contract metadata."""

    if plan_resolution.get("surface") != PLAN_RESOLUTION_SURFACE:
        _raise(error_factory, "plan-resolution surface is not the reviewed fixture")
    if plan_resolution.get("status") in (
        STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
        STATUS_UNSUPPORTED_FOR_STAGE_PLAN,
    ):
        return _closed_result("plan-resolution result is not ready for sidecar_handoff_contract metadata", plan_resolution)
    stage_plan = _validate_ready_input(plan_resolution, error_factory=error_factory)
    handoff_contract = handoff_builder(dict(stage_plan))
    parser_schedule = _mapping_value(plan_resolution, "parser_schedule_constraints", error_factory)
    readiness = _mapping_value(plan_resolution, "plan_resolution_readiness", error_factory)
    return {
        "schema_version": 1,
        "surface": HANDOFF_CONTRACT_FIXTURE_SURFACE,
        "status": "ready_for_sidecar_handoff_contract_metadata",
        "input_surface": plan_resolution["surface"],
        "input_status": plan_resolution["status"],
        "sidecar_handoff_contract_invoked": True,
        "command_synthesis_invoked": False,
        "operator_plan_invoked": False,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "source_closure_inferred": False,
        "filelists_expanded": False,
        "automatic_gpu_allocation_used": False,
        "correctness_policy_ref_status": "reference_only_not_compare_evidence",
        "correctness_policy": CORRECTNESS_POLICY_COVERAGE_OUTPUT,
        "parser_schedule_cross_check": {
            "accelerator_mode": parser_schedule["accelerator_mode"],
            "state_count": parser_schedule["state_count"],
            "step_count": parser_schedule["step_count"],
            "shape": parser_schedule["shape"],
            "shape_matches_handoff_contract": parser_schedule["shape"] == handoff_contract["shape"],
        },
        "plan_resolution_readiness": dict(readiness),
        "handoff_contract": handoff_contract,
        "non_claims": [
            "handoff-contract fixture does not execute commands",
            "handoff-contract fixture is not sidecar runtime handoff validation",
            "handoff-contract fixture is not coverage-output equivalence evidence",
            "parser source files and filelists remain preserved inputs, not inferred source closure",
            "command synthesis, operator plan, execution, timing, runtime ABI, and automatic allocation remain out of scope",
        ],
    }
