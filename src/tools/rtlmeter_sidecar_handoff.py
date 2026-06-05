"""Metadata-only RTLMeter sidecar handoff boundary."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

try:
    from .rtlmeter_sidecar_launcher_invocation import build_rtlmeter_sidecar_launcher_invocation
    from .rtlmeter_verilator_path_wrapper import (
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )
    from .rtlmeter_source_closure_authority import (
        SOURCE_CLOSURE_AUTHORITY_SCOPE,
        SOURCE_CLOSURE_EXECUTION_AUTHORITY,
        SOURCE_CLOSURE_RUNNER_STRATEGY,
        source_closure_is_reviewed,
    )
    from .rtlmeter_sidecar_authority_registry import reviewed_registry_source_closure
    from .verilator_native_option_parser_stub_fixture import (
        NativeOptionParserStubError,
        parse_verilator_native_option_stub,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_sidecar_launcher_invocation import build_rtlmeter_sidecar_launcher_invocation
    from rtlmeter_verilator_path_wrapper import (
        STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING,
        inspect_rtlmeter_verilator_wrapper_argv,
    )
    from rtlmeter_source_closure_authority import (
        SOURCE_CLOSURE_AUTHORITY_SCOPE,
        SOURCE_CLOSURE_EXECUTION_AUTHORITY,
        SOURCE_CLOSURE_RUNNER_STRATEGY,
        source_closure_is_reviewed,
    )
    from rtlmeter_sidecar_authority_registry import reviewed_registry_source_closure
    from verilator_native_option_parser_stub_fixture import (
        NativeOptionParserStubError,
        parse_verilator_native_option_stub,
    )


SURFACE = "rtlmeter_sidecar_handoff"
STATUS_BLOCKED_MISSING_CONTEXT = "rtlmeter_sidecar_handoff_blocked_missing_context"
STATUS_METADATA_READY = "rtlmeter_sidecar_handoff_metadata_ready"
STATUS_UNSUPPORTED = "unsupported_rtlmeter_sidecar_handoff_request"
SOURCE_CLOSURE_COMPLETE_STATUS = "complete"
SOURCE_CLOSURE_INCOMPLETE_STATUS = "frontend_metadata_only_not_source_closure"
REQUIRED_SIDECAR_CONTEXT = tuple(
    "target mode template_or_target_registry_entry source_gate_or_manifest_ref "
    "host_probe_metadata coverage_output_target coverage_manifest "
    "state_and_report_path_rules compare_labels source_closure".split()
)
DEFAULT_SOURCE_GATE_OR_MANIFEST_REF = "for_codex/issues/FC-034-rtlmeter-first-seed-execution-integration.md"
DEFAULT_VERILATOR_MDIR = "obj_dir"


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


def _parser_payload_with_default_mdir(parser_payload: dict[str, object] | None) -> tuple[dict[str, object] | None, str | None]:
    if parser_payload is None:
        return None, None
    payload = dict(parser_payload)
    if payload.get("mdir") in (None, ""):
        payload["mdir"] = DEFAULT_VERILATOR_MDIR
        return payload, "verilator_default_obj_dir"
    return payload, "explicit"


def _target_name_from_case(case: object) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", str(case or "unknown")).strip("_").lower()
    return f"rtlmeter_{stem or 'unknown'}"


def _missing_context_fields(sidecar_context: Mapping[str, object] | None) -> list[str]:
    if sidecar_context is None:
        return list(REQUIRED_SIDECAR_CONTEXT)
    missing: list[str] = []
    for field in REQUIRED_SIDECAR_CONTEXT:
        value = sidecar_context.get(field)
        if value is None or value == "" or value == {} or value == []:
            missing.append(field)
        elif field == "source_closure" and not source_closure_is_reviewed(value):
            missing.append(field)
    return missing


def _status(*, ready: bool, missing_context: Sequence[str]) -> str:
    if not ready:
        return STATUS_UNSUPPORTED
    return STATUS_METADATA_READY if not missing_context else STATUS_BLOCKED_MISSING_CONTEXT


def build_rtlmeter_sidecar_handoff(
    argv: Sequence[str],
    *,
    sidecar_context: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return metadata for the next RTLMeter sidecar handoff without executing it."""

    inspection = inspect_rtlmeter_verilator_wrapper_argv(argv)
    schedule = _schedule_from_inspection(inspection)
    raw_parser_payload, parser_error = _parser_payload(argv)
    parser_payload, parser_payload_mdir_source = _parser_payload_with_default_mdir(raw_parser_payload)
    ready = inspection["status"] == STATUS_READY_FOR_RTL_METER_SIDECAR_PLANNING and schedule is not None
    missing_context = _missing_context_fields(sidecar_context)
    if parser_payload is None or parser_payload.get("mdir") in (None, ""):
        missing_context.append("mdir")

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": _status(ready=ready, missing_context=missing_context),
        "json_flow_role": "runtime_diagnostic",
        "runtime_abi": False,
        "execution_authority": False,
        "source_surface": inspection["surface"],
        "wrapper_inspection_status": inspection["status"],
        "schedule": schedule,
        "parser_payload": _copy_value(parser_payload) if parser_payload is not None else None,
        "parser_payload_mdir_source": parser_payload_mdir_source,
        "parser_error": parser_error,
        "sidecar_context": _copy_value(sidecar_context) if sidecar_context is not None else None,
        "missing_sidecar_context": missing_context,
        "sidecar_context_metadata_ready": ready and not missing_context,
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


def build_rtlmeter_sidecar_context_candidate(
    sidecar_contract: Mapping[str, object],
    *,
    source_gate_or_manifest_ref: str = DEFAULT_SOURCE_GATE_OR_MANIFEST_REF,
    template_or_target_registry_entry: str | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, object]:
    frontend_metadata = sidecar_contract.get("frontend_owned_build_metadata")
    if not isinstance(frontend_metadata, Mapping):
        raise ValueError("RTLMeter sidecar contract is missing frontend_owned_build_metadata")
    case = sidecar_contract.get("case")
    target = _target_name_from_case(case)
    source_files = [f"third_party/rtlmeter/{item}" for item in frontend_metadata.get("verilog_source_files", [])]
    include_files = [f"third_party/rtlmeter/{item}" for item in frontend_metadata.get("verilog_include_files", [])]
    filelist_entries = list(frontend_metadata.get("filelist_entries", []))
    source_closure: object = {
        "status": SOURCE_CLOSURE_INCOMPLETE_STATUS,
        "required_authority": SOURCE_CLOSURE_EXECUTION_AUTHORITY,
        "authority_scope": SOURCE_CLOSURE_AUTHORITY_SCOPE,
        "target": target,
        "mode": "rtlmeter_first_seed",
        "rtlmeter_case": str(case),
        "source_gate_or_manifest_ref": source_gate_or_manifest_ref,
        "source_files": source_files,
        "include_files": include_files,
        "filelist_entries": filelist_entries,
        "observables": ["normalized_stdout", "rtlmeter_cycles"],
        "runner_strategy": SOURCE_CLOSURE_RUNNER_STRATEGY,
        "host_probe_contract_status": "not_reviewed_for_rtlmeter_sidecar",
        "cpu_as_gpu_fallback_allowed": False,
        "execution_blocker": "blocked_host_probe_contract_mismatch",
        "compile_source_closure_is_not_hybrid_execution_closure": True,
    }
    reviewed_source_closure = reviewed_registry_source_closure(
        template_or_target_registry_entry,
        repo_root=repo_root,
        target=target,
        case=case,
        source_files=source_files,
        include_files=include_files,
        filelist_entries=filelist_entries,
    )
    if reviewed_source_closure is not None:
        source_closure = reviewed_source_closure
    return {
        "schema_version": 1,
        "surface": "rtlmeter_sidecar_context_candidate",
        "status": "candidate_context_with_reviewed_source_closure" if reviewed_source_closure is not None else "candidate_context_without_source_closure",
        "target": target,
        "mode": "rtlmeter_first_seed",
        "template_or_target_registry_entry": template_or_target_registry_entry,
        "source_gate_or_manifest_ref": source_gate_or_manifest_ref,
        "host_probe_metadata": {
            "top_module": frontend_metadata.get("top_module"),
            "main_clock": frontend_metadata.get("main_clock"),
            "prefix": frontend_metadata.get("prefix"),
            "status": "captured_from_rtlmeter_frontend_metadata_not_verified_host_probe",
        },
        "coverage_output_target": "rtlmeter_stdout_and_cycles_equivalence",
        "coverage_manifest": {"outputs": ["normalized_stdout", "rtlmeter_cycles"], "status": "policy_defined_not_observed"},
        "state_and_report_path_rules": {
            "artifact_root": f"artifacts/{target}_cpu_gpu_compare",
            "report": f"reports/{target}_cpu_gpu_compare.json",
            "status": "path_rules_declared_not_executed",
        },
        "compare_labels": {"cpu": "rtlmeter_cpu_reference", "gpu": "rtlmeter_sidecar_candidate"},
        "compile_source_closure": {
            "status": "complete",
            "source_files": source_files,
            "include_files": include_files,
            "defines": _copy_value(frontend_metadata.get("verilog_defines") or {}),
            "provenance": "rtlmeter_descriptor_capture",
        },
        "source_closure": source_closure,
        "non_claims": [
            "context candidate does not provide a reviewed RTLMeter launch template",
            "source closure is adopted only from a reviewed RTLMeter authority registry" if reviewed_source_closure is not None else "context candidate does not prove source closure",
            "context candidate does not execute sidecar stages or compare outputs",
        ],
    }
