"""Metadata-only RTLMeter sidecar handoff boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

try:
    from .rtlmeter_verilator_path_wrapper import (
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )
    from .verilator_native_option_parser_stub_fixture import (
        NativeOptionParserStubError,
        parse_verilator_native_option_stub,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_verilator_path_wrapper import (
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )
    from verilator_native_option_parser_stub_fixture import (
        NativeOptionParserStubError,
        parse_verilator_native_option_stub,
    )


SURFACE = "rtlmeter_sidecar_handoff"
STATUS_BLOCKED_MISSING_CONTEXT = "rtlmeter_sidecar_handoff_blocked_missing_context"
STATUS_UNSUPPORTED = "unsupported_rtlmeter_sidecar_handoff_request"
REQUIRED_SIDECAR_CONTEXT = (
    "target",
    "mode",
    "template_or_target_registry_entry",
    "source_gate_or_manifest_ref",
    "host_probe_metadata",
    "coverage_output_target",
    "coverage_manifest",
    "state_and_report_path_rules",
    "compare_labels",
    "source_closure",
)


def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _schedule_from_inspection(inspection: Mapping[str, object]) -> dict[str, object] | None:
    states = inspection.get("sidecar_states")
    steps = inspection.get("sidecar_steps")
    if not isinstance(states, str) or not isinstance(steps, str):
        return None
    try:
        nstates = int(states, 10)
        nsteps = int(steps, 10)
    except ValueError:
        return None
    if nstates <= 0 or nsteps <= 0:
        return None
    return {
        "accelerator_mode": "sidecar-gpu",
        "state_count": nstates,
        "step_count": nsteps,
        "shape": f"{nstates}x{nsteps}",
    }


def _parser_payload(argv: Sequence[str]) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    try:
        return parse_verilator_native_option_stub(argv), None
    except NativeOptionParserStubError as exc:
        return None, exc.to_dict()


def build_rtlmeter_sidecar_handoff(argv: Sequence[str]) -> dict[str, object]:
    """Return metadata for the next RTLMeter sidecar handoff without executing it."""

    inspection = inspect_rtlmeter_verilator_wrapper_argv(argv)
    schedule = _schedule_from_inspection(inspection)
    parser_payload, parser_error = _parser_payload(argv)
    ready = inspection["status"] == STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING and schedule is not None
    missing_context = list(REQUIRED_SIDECAR_CONTEXT)
    if parser_payload is None or parser_payload.get("mdir") in (None, ""):
        missing_context.append("mdir")

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": STATUS_BLOCKED_MISSING_CONTEXT if ready else STATUS_UNSUPPORTED,
        "json_flow_role": "runtime_diagnostic",
        "runtime_abi": False,
        "execution_authority": False,
        "source_surface": inspection["surface"],
        "wrapper_inspection_status": inspection["status"],
        "schedule": schedule,
        "parser_payload": _copy_value(parser_payload) if parser_payload is not None else None,
        "parser_error": parser_error,
        "missing_sidecar_context": missing_context,
        "sidecar_context_ready": False,
        "sidecar_launcher_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "cpu_as_gpu_fallback": False,
        "next_required_boundary": "rtlmeter sidecar context and source-closure authority",
        "non_claims": [
            "RTLMeter handoff metadata does not execute Verilator, sidecar stages, or compare outputs",
            "RTLMeter handoff metadata does not infer source closure, host-probe metadata, state paths, or report paths",
            "RTLMeter handoff metadata must not launch an unrelated repo-owned template as RTLMeter GPU evidence",
        ],
    }
