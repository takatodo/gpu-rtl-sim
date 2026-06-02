"""Non-executing Verilator-process-to-launcher bridge fixture."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

try:
    from . import verilator_native_option_parser_direct_native_invocation_fixture as native
    from . import verilator_native_option_parser_process_to_launcher_cli_fixture as launcher
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    import verilator_native_option_parser_direct_native_invocation_fixture as native
    import verilator_native_option_parser_process_to_launcher_cli_fixture as launcher

DIRECT_COMMAND_STAGE_ORDER, REVIEWED_HANDOFF_CONTEXT_REF = native.DIRECT_COMMAND_STAGE_ORDER, native.REVIEWED_HANDOFF_CONTEXT_REF
EXPECTED_LAUNCHER_COMMAND_ARGV = launcher.EXPECTED_LAUNCHER_COMMAND_ARGV
PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF = launcher.PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF
PROCESS_TO_LAUNCHER_CLI_FIXTURE_SURFACE, PROCESS_TO_LAUNCHER_CLI_STATUS = launcher.PROCESS_TO_LAUNCHER_CLI_FIXTURE_SURFACE, launcher.PROCESS_TO_LAUNCHER_CLI_STATUS
STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE_REF = launcher.STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE_REF
ProcessToLauncherCliFixtureError = launcher.ProcessToLauncherCliFixtureError
define_process_to_launcher_cli_fixture = launcher.define_process_to_launcher_cli_fixture


GATE_PREFIX = "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_"
VERILATOR_PROCESS_LAUNCHER_BRIDGE_BOUNDARY_REVIEW_GATE_REF = GATE_PREFIX + "verilator_process_launcher_bridge_boundary_gate.json"
PROCESS_TO_LAUNCHER_CLI_EXECUTION_RUN_REVIEW_GATE_REF = GATE_PREFIX + "process_to_launcher_cli_execution_run_gate.json"
VERILATOR_PROCESS_LAUNCHER_BRIDGE_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_verilator_process_launcher_bridge_fixture"
VERILATOR_PROCESS_LAUNCHER_BRIDGE_STATUS = "verilator_process_launcher_bridge_metadata_ready_for_review"
VERILATOR_PROCESS_LAUNCHER_BRIDGE_FAILURE_CLASSES = tuple("verilator_process_parse_failure missing_explicit_sidecar_context source_or_template_authority_failure process_to_launcher_bridge_failure launcher_cli_invocation_failure sidecar_stage_failure compare_failure timing_claim_without_measurement".split())
VERILATOR_PROCESS_LAUNCHER_BRIDGE_FIELDS = tuple("schema_version surface status source_review_gate source_process_to_launcher_boundary_review_gate source_process_to_launcher_execution_run_review_gate process_to_launcher_cli_surface process_to_launcher_cli_status verilator_process_launcher_bridge_ready wrapper_mediated_process_launch_bridge process_to_launcher_cli_bridge_ready invocation_ready parser_payload parser_schedule sidecar_context source_or_template_authority sidecar_launcher_entrypoint launcher_command_argv launcher_command_role bridge_materialization_status required_stage_order preserved_failure_classes verilator_process_invoked wrapper_execution_used launcher_cli_invoked launcher_process_invoked sidecar_launcher_invoked_from_native_path sidecar_launch_reached_from_native_path sidecar_stage_execution_performed compare_execution_performed coverage_output_compare_reached_from_native_path native_path_compare_reached direct_verilator_sidecar_execution_proven coverage_output_equivalence_claim_reached_from_direct_verilator_sidecar_execution execution_performed measurement_performed timing_measured runtime_or_abi_changed automatic_gpu_allocation_used generated_reports_and_artifacts_source_of_truth non_claims".split())
VERILATOR_PROCESS_LAUNCHER_BRIDGE_NON_CLAIMS = tuple("Verilator process launcher bridge fixture binds reviewed process metadata to launcher argv only|Verilator process launcher bridge fixture does not start a Verilator process|Verilator process launcher bridge fixture does not start run_hybrid_template.py|Verilator process launcher bridge fixture does not execute sidecar stages or compare outputs|Verilator process launcher bridge fixture does not prove direct Verilator sidecar execution|reviewed process-to-launcher metadata and exact argv are not execution authority|generated reports and artifacts remain evidence only and are not source of truth".split("|"))
EXPECTED_PROCESS_TO_LAUNCHER_SCHEDULE = {"accelerator_mode": "sidecar-gpu", "state_count": 64, "step_count": 1, "shape": "64x1", "correctness_policy": "coverage_output_equivalence"}
NON_EXECUTION_FLAGS = tuple("launcher_cli_invoked launcher_process_invoked sidecar_launcher_invoked_from_native_path sidecar_launch_reached_from_native_path sidecar_stage_execution_performed compare_execution_performed coverage_output_compare_reached_from_native_path native_path_compare_reached direct_verilator_sidecar_execution_proven coverage_output_equivalence_claim_reached_from_direct_verilator_sidecar_execution execution_performed measurement_performed timing_measured runtime_or_abi_changed automatic_gpu_allocation_used generated_reports_and_artifacts_source_of_truth".split())


def _error(code: str, message: str) -> ProcessToLauncherCliFixtureError:
    return ProcessToLauncherCliFixtureError(code, message)


def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _validate_source_review_gate(source_review_gate: str) -> None:
    if source_review_gate != VERILATOR_PROCESS_LAUNCHER_BRIDGE_BOUNDARY_REVIEW_GATE_REF:
        raise _error(
            "source_or_template_authority_failure",
            "Verilator process launcher bridge fixture requires the reviewed bridge boundary gate",
        )


def _validate_process_to_launcher_metadata(metadata: Mapping[str, object]) -> None:
    if metadata.get("surface") != PROCESS_TO_LAUNCHER_CLI_FIXTURE_SURFACE:
        raise _error("process_to_launcher_bridge_failure", "process-to-launcher metadata surface is not reviewed")
    if metadata.get("status") != PROCESS_TO_LAUNCHER_CLI_STATUS:
        raise _error("process_to_launcher_bridge_failure", "process-to-launcher metadata status is not ready")
    if metadata.get("source_review_gate") != PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF:
        raise _error("source_or_template_authority_failure", "process-to-launcher metadata source review gate mismatch")
    if metadata.get("source_structured_invocation_review_gate") != STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE_REF:
        raise _error("source_or_template_authority_failure", "process-to-launcher metadata structured review mismatch")
    if metadata.get("process_to_launcher_cli_bridge_ready") is not True or metadata.get("invocation_ready") is not True:
        raise _error("process_to_launcher_bridge_failure", "process-to-launcher metadata is not bridge-ready")
    if metadata.get("parser_schedule") != EXPECTED_PROCESS_TO_LAUNCHER_SCHEDULE:
        raise _error("process_to_launcher_bridge_failure", "process-to-launcher metadata schedule is outside scope")
    if metadata.get("launcher_command_argv") != EXPECTED_LAUNCHER_COMMAND_ARGV:
        raise _error("process_to_launcher_bridge_failure", "process-to-launcher metadata launcher argv mismatch")
    if metadata.get("launcher_command_role") != "materialized_for_later_run_not_invoked_by_fixture":
        raise _error("process_to_launcher_bridge_failure", "process-to-launcher metadata launcher role is not non-executing")
    for flag in NON_EXECUTION_FLAGS:
        if metadata.get(flag) is not False:
            raise _error("process_to_launcher_bridge_failure", f"process-to-launcher metadata has enabled flag {flag!r}")


def _validate_explicit_context_matches_metadata(
    sidecar_context: Mapping[str, object], metadata: Mapping[str, object]
) -> None:
    metadata_context = metadata.get("sidecar_context")
    if not isinstance(metadata_context, Mapping):
        raise _error("missing_explicit_sidecar_context", "process-to-launcher metadata lacks sidecar context")
    for field in ("target", "mode", "template_or_target_registry_entry", "source_gate_or_manifest_ref"):
        if sidecar_context.get(field) != metadata_context.get(field):
            raise _error("source_or_template_authority_failure", f"sidecar context field {field!r} mismatch")


def _validate_reviewed_sidecar_context_authority(metadata: Mapping[str, object]) -> None:
    metadata_context = metadata.get("sidecar_context")
    if not isinstance(metadata_context, Mapping):
        raise _error("missing_explicit_sidecar_context", "process-to-launcher metadata lacks sidecar context")
    if metadata_context.get("source_gate_or_manifest_ref") != REVIEWED_HANDOFF_CONTEXT_REF:
        raise _error(
            "source_or_template_authority_failure",
            "process-to-launcher metadata sidecar context requires the reviewed handoff authority",
        )
    authority = metadata.get("source_or_template_authority")
    if not isinstance(authority, Mapping):
        raise _error("source_or_template_authority_failure", "process-to-launcher metadata lacks authority details")
    if authority.get("sidecar_context_source_gate_or_manifest_ref") != REVIEWED_HANDOFF_CONTEXT_REF:
        raise _error(
            "source_or_template_authority_failure",
            "process-to-launcher metadata authority does not match the reviewed handoff authority",
        )


def _authority(source_review_gate: str, process_to_launcher: Mapping[str, object]) -> dict[str, object]:
    context = process_to_launcher["sidecar_context"]
    return {
        "current_boundary_review_gate": source_review_gate,
        "source_process_to_launcher_boundary_review_gate": PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
        "source_process_to_launcher_execution_run_review_gate": PROCESS_TO_LAUNCHER_CLI_EXECUTION_RUN_REVIEW_GATE_REF,
        "process_to_launcher_metadata_surface": process_to_launcher["surface"],
        "process_to_launcher_metadata_status": process_to_launcher["status"],
        "sidecar_context_source_gate_or_manifest_ref": context["source_gate_or_manifest_ref"],
        "parser_payload_runtime_authority": False,
        "reviewed_process_to_launcher_metadata_runtime_authority": False,
        "exact_launcher_argv_execution_authority": False,
        "generated_command_text_execution_authority": False,
        "explicit_sidecar_context_required_for_launcher": True,
        "launcher_start_is_not_verilator_internal_sidecar_execution": True,
        "coverage_output_compare_claim_requires_future_compare_stage": True,
        "timing_claim_requires_separate_timing_gate": True,
    }


def _bridge_ready_status() -> dict[str, object]:
    return {
        "state": "verilator_process_metadata_bound_to_process_to_launcher_cli_fixture_for_later_run",
        "verilator_process_parse_failure": False,
        "process_to_launcher_bridge_failure": False,
        "launcher_cli_invocation_failure": False,
        "sidecar_stage_failure": False,
        "compare_failure": False,
        "timing_claim_without_measurement": False,
        "failure_class": "none",
    }


def define_verilator_process_launcher_bridge_fixture(
    argv: Sequence[str] | None = None,
    *,
    sidecar_context: Mapping[str, object],
    source_review_gate: str,
    parser_payload: Mapping[str, object] | None = None,
    bridge_metadata: Mapping[str, object] | None = None,
    process_to_launcher_cli_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return Verilator-process-to-launcher bridge metadata without executing it."""
    _validate_source_review_gate(source_review_gate)
    if process_to_launcher_cli_metadata is None:
        process_to_launcher = define_process_to_launcher_cli_fixture(
            argv,
            sidecar_context=sidecar_context,
            source_review_gate=PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
            parser_payload=parser_payload,
            bridge_metadata=bridge_metadata,
        )
    else:
        process_to_launcher = {str(key): _copy_value(value) for key, value in process_to_launcher_cli_metadata.items()}
        _validate_explicit_context_matches_metadata(sidecar_context, process_to_launcher)
    _validate_process_to_launcher_metadata(process_to_launcher)
    _validate_reviewed_sidecar_context_authority(process_to_launcher)
    output = {
        "schema_version": 1,
        "surface": VERILATOR_PROCESS_LAUNCHER_BRIDGE_FIXTURE_SURFACE,
        "status": VERILATOR_PROCESS_LAUNCHER_BRIDGE_STATUS,
        "source_review_gate": source_review_gate,
        "source_process_to_launcher_boundary_review_gate": PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF,
        "source_process_to_launcher_execution_run_review_gate": PROCESS_TO_LAUNCHER_CLI_EXECUTION_RUN_REVIEW_GATE_REF,
        "process_to_launcher_cli_surface": process_to_launcher["surface"],
        "process_to_launcher_cli_status": process_to_launcher["status"],
        "verilator_process_launcher_bridge_ready": True,
        "wrapper_mediated_process_launch_bridge": True,
        "process_to_launcher_cli_bridge_ready": process_to_launcher["process_to_launcher_cli_bridge_ready"],
        "invocation_ready": process_to_launcher["invocation_ready"],
        "parser_payload": _copy_value(process_to_launcher["parser_payload"]),
        "parser_schedule": _copy_value(process_to_launcher["parser_schedule"]),
        "sidecar_context": _copy_value(process_to_launcher["sidecar_context"]),
        "source_or_template_authority": _authority(source_review_gate, process_to_launcher),
        "sidecar_launcher_entrypoint": process_to_launcher["sidecar_launcher_entrypoint"],
        "launcher_command_argv": list(process_to_launcher["launcher_command_argv"]),
        "launcher_command_role": "materialized_for_later_run_not_invoked_by_fixture",
        "bridge_materialization_status": _bridge_ready_status(),
        "required_stage_order": list(DIRECT_COMMAND_STAGE_ORDER),
        "preserved_failure_classes": list(VERILATOR_PROCESS_LAUNCHER_BRIDGE_FAILURE_CLASSES),
        "verilator_process_invoked": False,
        "wrapper_execution_used": False,
        **{flag: False for flag in NON_EXECUTION_FLAGS},
        "non_claims": list(VERILATOR_PROCESS_LAUNCHER_BRIDGE_NON_CLAIMS),
    }
    assert tuple(output.keys()) == VERILATOR_PROCESS_LAUNCHER_BRIDGE_FIELDS
    return output
