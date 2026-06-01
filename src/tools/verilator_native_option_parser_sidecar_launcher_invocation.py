"""Shared builder for non-executing sidecar-launcher invocation metadata."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

try:
    from .results_reproduction_legacy_commands import hybrid_template_command
    from .verilator_sidecar_options import shape_from_states_steps
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from results_reproduction_legacy_commands import hybrid_template_command
    from verilator_sidecar_options import shape_from_states_steps


SIDECAR_LAUNCHER_BRIDGE_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_sidecar_launcher_bridge_fixture"
SIDECAR_LAUNCHER_INVOCATION_FIXTURE_SURFACE = "native_verilator_parser_direct_command_path_sidecar_launcher_invocation_fixture"
SIDECAR_LAUNCHER_BRIDGE_STATUS = "sidecar_launcher_bridge_metadata_ready_for_review"
SIDECAR_LAUNCHER_INVOCATION_STATUS = "sidecar_launcher_invocation_metadata_ready_for_review"
REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF = "config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_gate.json"
SIDECAR_LAUNCHER_INVOCATION_FIELDS = tuple(("schema_version surface status native_invocation_surface bridge_surface bridge_status bridge_ready invocation_ready source_review_gate parser_payload parser_schedule sidecar_context sidecar_launcher_entrypoint launcher_command_argv launcher_command_role invocation_status required_stage_order preserved_failure_classes sidecar_launcher_invoked_from_native_path sidecar_launch_reached_from_native_path coverage_output_compare_reached_from_native_path native_path_compare_reached execution_performed measurement_performed timing_measured runtime_or_abi_changed automatic_gpu_allocation_used generated_reports_and_artifacts_source_of_truth non_claims").split())
INVOCATION_FAILURE_CLASSES = tuple("process_parse_failure missing_explicit_sidecar_context sidecar_launcher_bridge_failure sidecar_launcher_invocation_failure sidecar_stage_failure compare_failure timing_claim_without_measurement".split())
INVOCATION_NON_CLAIMS = (
    "native invocation fixture does not execute Verilator or hybrid runtime",
    "native invocation fixture does not make native command text runtime authority",
    "native invocation fixture requires explicit reviewed sidecar context before any later execution",
    "native invocation fixture does not materialize or execute sidecar stages",
    "native invocation fixture does not infer source closure, expand filelists, time execution, or allocate GPU work",
    "native invocation fixture is not native Verilator option support",
    "direct launch handoff fixture does not execute sidecar stages or compare outputs",
    "sidecar launcher bridge fixture does not call the sidecar launcher",
    "sidecar launcher bridge fixture does not make native-path compare or timing claims",
    "sidecar launcher invocation fixture materializes argv only and does not start the launcher",
    "sidecar launcher invocation fixture does not make native-path compare, timing, or speedup claims",
    "generated reports and artifacts remain evidence only and are not source of truth",
)


class SidecarLauncherInvocationBuildError(ValueError):
    """Structured fallback error used when no project error factory is provided."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


ErrorFactory = Callable[[str, str], Exception]


def _default_error(code: str, message: str) -> Exception:
    return SidecarLauncherInvocationBuildError(code, message)


def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _fail(error_factory: ErrorFactory, code: str, message: str) -> None:
    raise error_factory(code, message)


def _validate_source_review_gate(source_review_gate: str, error_factory: ErrorFactory) -> None:
    if source_review_gate != REVIEWED_SIDECAR_LAUNCHER_RUN_CONTEXT_REF:
        _fail(error_factory, "sidecar_launcher_bridge_failure", "launcher invocation fixture requires the reviewed sidecar-launcher run gate")


def _validate_invocation_scope(native_result: Mapping[str, object], error_factory: ErrorFactory) -> dict[str, object]:
    context = native_result["sidecar_context"]
    if context["target"] != "pulp_ita_mha" or context["template_or_target_registry_entry"] != "config/slice_launch_templates/pulp_ita_mha.json":
        _fail(error_factory, "unsupported_sidecar_launcher_invocation_scope", "launcher invocation fixture is scoped to pulp_ita_mha template context")
    try:
        expected = shape_from_states_steps(states=64, steps=1)
    except ValueError as exc:  # pragma: no cover - constant validation cannot fail.
        _fail(error_factory, "sidecar_launcher_invocation_failure", str(exc))
    if native_result["state_count"] != expected.nstates or native_result["step_count"] != expected.steps or native_result["shape"] != expected.shape:
        _fail(error_factory, "unsupported_sidecar_launcher_invocation_scope", "launcher invocation fixture is scoped to pulp_ita_mha 64x1")
    return {
        "accelerator_mode": native_result["accelerator_mode"],
        "state_count": native_result["state_count"],
        "step_count": native_result["step_count"],
        "shape": native_result["shape"],
        "correctness_policy": native_result["correctness_policy_ref"],
    }


def _validate_bridge_fixture_for_invocation(
    bridge: Mapping[str, object],
    native_result: Mapping[str, object],
    error_factory: ErrorFactory,
) -> None:
    if bridge.get("surface") != SIDECAR_LAUNCHER_BRIDGE_FIXTURE_SURFACE or bridge.get("status") != SIDECAR_LAUNCHER_BRIDGE_STATUS:
        _fail(error_factory, "sidecar_launcher_bridge_failure", "launcher invocation fixture requires reviewed sidecar-launcher bridge metadata")
    if bridge.get("bridge_ready") is not True:
        _fail(error_factory, "sidecar_launcher_bridge_failure", "sidecar-launcher bridge metadata is not ready")
    if bridge.get("sidecar_launcher_entrypoint") != "src/tools/run_hybrid_template.py":
        _fail(error_factory, "sidecar_launcher_bridge_failure", "sidecar-launcher bridge metadata does not name the reviewed launcher")
    if bridge.get("sidecar_launcher_entrypoint_role") != "reference_only_not_invoked_by_fixture":
        _fail(error_factory, "sidecar_launcher_bridge_failure", "sidecar-launcher bridge metadata must be reference-only before invocation materialization")
    for flag in (
        "sidecar_launch_reached_from_native_path",
        "coverage_output_compare_reached_from_native_path",
        "native_path_compare_reached",
        "execution_performed",
        "measurement_performed",
        "timing_measured",
        "runtime_or_abi_changed",
        "automatic_gpu_allocation_used",
    ):
        if bridge.get(flag) is not False:
            _fail(error_factory, "sidecar_launcher_bridge_failure", f"bridge metadata has enabled flag {flag!r}")
    if bridge.get("sidecar_context") != native_result["sidecar_context"]:
        _fail(error_factory, "sidecar_launcher_bridge_failure", "bridge metadata sidecar context does not match parser context")


def _materialize_sidecar_launcher_command(sidecar_context: Mapping[str, object], shape: str, error_factory: ErrorFactory) -> list[str]:
    template = sidecar_context.get("template_or_target_registry_entry")
    if template != "config/slice_launch_templates/pulp_ita_mha.json" or shape != "64x1":
        _fail(error_factory, "sidecar_launcher_invocation_failure", "launcher command materialization is scoped to pulp_ita_mha 64x1")
    command = hybrid_template_command(template=str(template), shape=shape)
    argv = list(command.argv)
    if argv != ["python3", "src/tools/run_hybrid_template.py", str(template), "--shape", shape]:
        _fail(error_factory, "sidecar_launcher_invocation_failure", "existing launcher command helper returned an unexpected argv shape")
    return argv


def _ready_invocation_status() -> dict[str, object]:
    return {
        "state": "launcher_command_argv_materialized_for_later_run",
        "bridge_failure": False,
        "launcher_invocation_construction_failure": False,
        "sidecar_stage_failure": False,
        "compare_failure": False,
        "timing_claim_without_measurement": False,
        "failure_class": "none",
    }


def build_sidecar_launcher_invocation_fixture(
    *,
    native_result: Mapping[str, object],
    bridge_metadata: Mapping[str, object],
    source_review_gate: str,
    required_stage_order: Sequence[str],
    error_factory: ErrorFactory = _default_error,
) -> dict[str, object]:
    """Return launcher argv metadata without executing the launcher."""
    _validate_source_review_gate(source_review_gate, error_factory)
    parser_schedule = _validate_invocation_scope(native_result, error_factory)
    bridge = {str(key): _copy_value(value) for key, value in bridge_metadata.items()}
    _validate_bridge_fixture_for_invocation(bridge, native_result, error_factory)
    launcher_argv = _materialize_sidecar_launcher_command(native_result["sidecar_context"], str(parser_schedule["shape"]), error_factory)
    output = {
        "schema_version": 1,
        "surface": SIDECAR_LAUNCHER_INVOCATION_FIXTURE_SURFACE,
        "status": SIDECAR_LAUNCHER_INVOCATION_STATUS,
        "native_invocation_surface": native_result["surface"],
        "bridge_surface": bridge["surface"],
        "bridge_status": bridge["status"],
        "bridge_ready": True,
        "invocation_ready": True,
        "source_review_gate": source_review_gate,
        "parser_payload": _copy_value(native_result["parser_payload"]),
        "parser_schedule": parser_schedule,
        "sidecar_context": _copy_value(native_result["sidecar_context"]),
        "sidecar_launcher_entrypoint": bridge["sidecar_launcher_entrypoint"],
        "launcher_command_argv": launcher_argv,
        "launcher_command_role": "materialized_for_later_run_not_invoked_by_fixture",
        "invocation_status": _ready_invocation_status(),
        "required_stage_order": list(required_stage_order),
        "preserved_failure_classes": list(INVOCATION_FAILURE_CLASSES),
        "sidecar_launcher_invoked_from_native_path": False,
        "sidecar_launch_reached_from_native_path": False,
        "coverage_output_compare_reached_from_native_path": False,
        "native_path_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "timing_measured": False,
        "runtime_or_abi_changed": False,
        "automatic_gpu_allocation_used": False,
        "generated_reports_and_artifacts_source_of_truth": False,
        "non_claims": list(INVOCATION_NON_CLAIMS),
    }
    assert tuple(output.keys()) == SIDECAR_LAUNCHER_INVOCATION_FIELDS
    return output
