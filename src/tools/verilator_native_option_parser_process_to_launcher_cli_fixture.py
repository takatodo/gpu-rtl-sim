"""Non-executing process-to-launcher CLI fixture for native parser output."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

try:
    from .verilator_native_option_parser_direct_native_invocation_fixture import (
        DIRECT_COMMAND_STAGE_ORDER,
        NativeParserDirectNativeInvocationFixtureError,
        define_sidecar_launcher_invocation_fixture,
    )
    from .verilator_native_option_parser_sidecar_launcher_invocation import (
        REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF,
        SIDECAR_LAUNCHER_INVOCATION_FIXTURE_SURFACE,
        SIDECAR_LAUNCHER_INVOCATION_STATUS,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from verilator_native_option_parser_direct_native_invocation_fixture import (
        DIRECT_COMMAND_STAGE_ORDER,
        NativeParserDirectNativeInvocationFixtureError,
        define_sidecar_launcher_invocation_fixture,
    )
    from verilator_native_option_parser_sidecar_launcher_invocation import (
        REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF,
        SIDECAR_LAUNCHER_INVOCATION_FIXTURE_SURFACE,
        SIDECAR_LAUNCHER_INVOCATION_STATUS,
    )


PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF = (
    "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_"
    "process_to_launcher_cli_boundary_gate.json"
)
STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE_REF = (
    "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_"
    "direct_launch_handoff_sidecar_launcher_invocation_run_gate.json"
)
PROCESS_TO_LAUNCHER_CLI_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_process_to_launcher_cli_fixture"
PROCESS_TO_LAUNCHER_CLI_STATUS = "process_to_launcher_cli_metadata_ready_for_review"
PROCESS_TO_LAUNCHER_CLI_REJECTION_LAYER = "process_to_launcher_cli_fixture_contract"
EXPECTED_LAUNCHER_COMMAND_ARGV = "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1".split()
FORBIDDEN_PARSER_AUTHORITY_FIELDS = frozenset(
    "execution_authority fixture_metadata_runtime_authority native_command_alone_execution_authority "
    "generated_command_text generated_command_text_source_of_truth generated_command_text_execution_authority "
    "launcher_command launcher_command_argv launcher_cli_argv verilator_command verilator_command_argv "
    "sidecar_stage_plan materialized_stage_plan sidecar_stage_execution_performed compare_execution_performed "
    "coverage_output_equivalence_recorded execution_performed measurement_performed timing_measured "
    "runtime_or_abi_changed automatic_gpu_allocation_used generated_reports_and_artifacts_source_of_truth".split()
)
PROCESS_TO_LAUNCHER_CLI_FAILURE_CLASSES = tuple(
    "process_parse_failure missing_explicit_sidecar_context source_or_template_authority_failure "
    "process_to_launcher_cli_bridge_failure launcher_cli_invocation_failure sidecar_stage_failure "
    "compare_failure timing_claim_without_measurement".split()
)
NON_EXECUTION_FLAGS = tuple(
    "launcher_cli_invoked launcher_process_invoked sidecar_launcher_invoked_from_native_path "
    "sidecar_launch_reached_from_native_path sidecar_stage_execution_performed compare_execution_performed "
    "coverage_output_compare_reached_from_native_path native_path_compare_reached direct_verilator_sidecar_execution_proven "
    "coverage_output_equivalence_claim_reached_from_direct_verilator_sidecar_execution execution_performed "
    "measurement_performed timing_measured runtime_or_abi_changed automatic_gpu_allocation_used generated_reports_and_artifacts_source_of_truth".split()
)
PROCESS_TO_LAUNCHER_CLI_FIELDS = tuple(
    "schema_version surface status source_review_gate source_structured_invocation_review_gate "
    "invocation_source_surface invocation_source_status native_invocation_surface "
    "process_to_launcher_cli_bridge_ready invocation_ready parser_payload parser_schedule sidecar_context "
    "source_or_template_authority sidecar_launcher_entrypoint launcher_command_argv launcher_command_role "
    "cli_materialization_status required_stage_order preserved_failure_classes launcher_cli_invoked "
    "launcher_process_invoked sidecar_launcher_invoked_from_native_path sidecar_launch_reached_from_native_path "
    "sidecar_stage_execution_performed compare_execution_performed coverage_output_compare_reached_from_native_path "
    "native_path_compare_reached direct_verilator_sidecar_execution_proven "
    "coverage_output_equivalence_claim_reached_from_direct_verilator_sidecar_execution execution_performed "
    "measurement_performed timing_measured runtime_or_abi_changed automatic_gpu_allocation_used "
    "generated_reports_and_artifacts_source_of_truth non_claims".split()
)
NON_CLAIMS = (
    "process-to-launcher CLI fixture materializes structured launcher argv only",
    "process-to-launcher CLI fixture does not start run_hybrid_template.py",
    "process-to-launcher CLI fixture does not execute sidecar stages or compare outputs",
    "process-to-launcher CLI fixture does not prove direct Verilator sidecar execution",
    "parser payloads and generated command text are not execution authority",
    "generated reports and artifacts remain evidence only and are not source of truth",
)


class ProcessToLauncherCliFixtureError(ValueError):
    """Structured process-to-launcher CLI fixture validation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.rejection_layer = PROCESS_TO_LAUNCHER_CLI_REJECTION_LAYER

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "rejection_layer": self.rejection_layer, "message": str(self)}


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
    if source_review_gate != PROCESS_TO_LAUNCHER_CLI_BOUNDARY_REVIEW_GATE_REF:
        raise _error(
            "source_or_template_authority_failure",
            "process-to-launcher CLI fixture requires the reviewed process-to-launcher boundary gate",
        )


def _reject_parser_payload_authority(parser_payload: Mapping[str, object] | None) -> None:
    if parser_payload is None:
        return
    forbidden = sorted(FORBIDDEN_PARSER_AUTHORITY_FIELDS.intersection(parser_payload))
    if forbidden:
        raise _error(
            "payload_authority_field_prepopulated_by_parser",
            f"parser payload already contains process-to-launcher authority fields: {forbidden}",
        )


def _build_launcher_invocation(
    argv: Sequence[str] | None,
    *,
    sidecar_context: Mapping[str, object],
    parser_payload: Mapping[str, object] | None,
    bridge_metadata: Mapping[str, object] | None,
) -> dict[str, object]:
    try:
        return define_sidecar_launcher_invocation_fixture(
            argv,
            sidecar_context=sidecar_context,
            source_review_gate=REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF,
            parser_payload=parser_payload,
            bridge_metadata=bridge_metadata,
        )
    except NativeParserDirectNativeInvocationFixtureError as exc:
        if exc.code == "sidecar_authority_failure":
            raise _error("source_or_template_authority_failure", str(exc)) from exc
        raise


def _validate_launcher_invocation(invocation: Mapping[str, object]) -> None:
    if invocation.get("surface") != SIDECAR_LAUNCHER_INVOCATION_FIXTURE_SURFACE:
        raise _error("process_to_launcher_cli_bridge_failure", "launcher invocation surface is not reviewed")
    if invocation.get("status") != SIDECAR_LAUNCHER_INVOCATION_STATUS:
        raise _error("process_to_launcher_cli_bridge_failure", "launcher invocation status is not ready")
    if invocation.get("invocation_ready") is not True:
        raise _error("process_to_launcher_cli_bridge_failure", "launcher invocation metadata is not ready")
    if invocation.get("launcher_command_argv") != EXPECTED_LAUNCHER_COMMAND_ARGV:
        raise _error("process_to_launcher_cli_bridge_failure", "launcher argv does not match the reviewed command")
    for flag in (
        "sidecar_launcher_invoked_from_native_path",
        "sidecar_launch_reached_from_native_path",
        "coverage_output_compare_reached_from_native_path",
        "native_path_compare_reached",
        "execution_performed",
        "measurement_performed",
        "timing_measured",
        "runtime_or_abi_changed",
        "automatic_gpu_allocation_used",
        "generated_reports_and_artifacts_source_of_truth",
    ):
        if invocation.get(flag) is not False:
            raise _error("process_to_launcher_cli_bridge_failure", f"launcher invocation has enabled flag {flag!r}")


def _source_or_template_authority(source_review_gate: str, invocation: Mapping[str, object]) -> dict[str, object]:
    context = invocation["sidecar_context"]
    return {
        "current_boundary_review_gate": source_review_gate,
        "structured_invocation_review_gate": STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE_REF,
        "reused_invocation_fixture_source_review_gate": REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF,
        "sidecar_context_source_gate_or_manifest_ref": context["source_gate_or_manifest_ref"],
        "payload_only_execution_authority": False,
        "generated_command_text_execution_authority": False,
        "structured_invocation_review_gate_alone_is_current_authority": False,
    }


def _ready_status() -> dict[str, object]:
    return {
        "state": "process_payload_bound_to_launcher_cli_argv_for_later_run",
        "process_to_launcher_cli_bridge_failure": False,
        "launcher_cli_invocation_failure": False,
        "sidecar_stage_failure": False,
        "compare_failure": False,
        "timing_claim_without_measurement": False,
        "failure_class": "none",
    }


def define_process_to_launcher_cli_fixture(
    argv: Sequence[str] | None = None,
    *,
    sidecar_context: Mapping[str, object],
    source_review_gate: str,
    parser_payload: Mapping[str, object] | None = None,
    bridge_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return process-to-launcher CLI argv metadata without executing it."""
    _validate_source_review_gate(source_review_gate)
    _reject_parser_payload_authority(parser_payload)
    invocation = _build_launcher_invocation(
        argv,
        sidecar_context=sidecar_context,
        parser_payload=parser_payload,
        bridge_metadata=bridge_metadata,
    )
    _validate_launcher_invocation(invocation)
    output = {
        "schema_version": 1,
        "surface": PROCESS_TO_LAUNCHER_CLI_FIXTURE_SURFACE,
        "status": PROCESS_TO_LAUNCHER_CLI_STATUS,
        "source_review_gate": source_review_gate,
        "source_structured_invocation_review_gate": STRUCTURED_LAUNCHER_INVOCATION_RUN_REVIEW_GATE_REF,
        "invocation_source_surface": invocation["surface"],
        "invocation_source_status": invocation["status"],
        "native_invocation_surface": invocation["native_invocation_surface"],
        "process_to_launcher_cli_bridge_ready": True,
        "invocation_ready": invocation["invocation_ready"],
        "parser_payload": _copy_value(invocation["parser_payload"]),
        "parser_schedule": _copy_value(invocation["parser_schedule"]),
        "sidecar_context": _copy_value(invocation["sidecar_context"]),
        "source_or_template_authority": _source_or_template_authority(source_review_gate, invocation),
        "sidecar_launcher_entrypoint": invocation["sidecar_launcher_entrypoint"],
        "launcher_command_argv": list(invocation["launcher_command_argv"]),
        "launcher_command_role": "materialized_for_later_run_not_invoked_by_fixture",
        "cli_materialization_status": _ready_status(),
        "required_stage_order": list(DIRECT_COMMAND_STAGE_ORDER),
        "preserved_failure_classes": list(PROCESS_TO_LAUNCHER_CLI_FAILURE_CLASSES),
        **{flag: False for flag in NON_EXECUTION_FLAGS},
        "non_claims": list(NON_CLAIMS),
    }
    assert tuple(output.keys()) == PROCESS_TO_LAUNCHER_CLI_FIELDS
    return output
