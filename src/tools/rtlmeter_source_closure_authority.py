"""Reviewed RTLMeter source-closure authority checks."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


SOURCE_CLOSURE_COMPLETE_STATUS = "complete"
SOURCE_CLOSURE_EXECUTION_AUTHORITY = "reviewed_hybrid_execution_source_closure"
SOURCE_CLOSURE_AUTHORITY_SCOPE = "rtlmeter_stdout_cycles_sidecar_runner"
SOURCE_CLOSURE_HOST_PROBE_STATUS = "reviewed_for_rtlmeter_sidecar"
SOURCE_CLOSURE_RUNNER_STRATEGY = "rtlmeter_stdout_cycles_direct_wrapper"
EXPECTED_OBSERVABLES = ["normalized_stdout", "rtlmeter_cycles"]


def _missing_string_field(value: Mapping[str, object], field: str, prefix: str) -> list[str]:
    item = value.get(field)
    if not isinstance(item, str) or not item:
        return [f"{prefix}.{field}"]
    return []


def _repo_relative_string_list_missing(value: object, field: str, prefix: str) -> list[str]:
    if not isinstance(value, list) or not value:
        return [f"{prefix}.{field}"]
    missing: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            missing.append(f"{prefix}.{field}[{index}]")
            continue
        path = Path(item)
        if path.is_absolute() or ".." in path.parts:
            missing.append(f"{prefix}.{field}[{index}]")
    return missing


def reviewed_source_closure_missing_context(
    value: object,
    prefix: str,
    *,
    expected_target: str | None = None,
) -> list[str]:
    if not isinstance(value, Mapping):
        return [prefix]

    missing: list[str] = []
    if value.get("status") != SOURCE_CLOSURE_COMPLETE_STATUS:
        missing.append(f"{prefix}.status")
    if value.get("authority") != SOURCE_CLOSURE_EXECUTION_AUTHORITY:
        missing.append(f"{prefix}.authority")
    if value.get("authority_scope") != SOURCE_CLOSURE_AUTHORITY_SCOPE:
        missing.append(f"{prefix}.authority_scope")
    if value.get("runner_strategy") != SOURCE_CLOSURE_RUNNER_STRATEGY:
        missing.append(f"{prefix}.runner_strategy")
    if value.get("host_probe_contract_status") != SOURCE_CLOSURE_HOST_PROBE_STATUS:
        missing.append(f"{prefix}.host_probe_contract_status")
    if value.get("cpu_as_gpu_fallback_allowed") is not False:
        missing.append(f"{prefix}.cpu_as_gpu_fallback_allowed")
    if value.get("observables") != EXPECTED_OBSERVABLES:
        missing.append(f"{prefix}.observables")

    for field in ("target", "mode", "rtlmeter_case", "source_gate_or_manifest_ref"):
        missing.extend(_missing_string_field(value, field, prefix))
    target = value.get("target")
    if expected_target is not None and isinstance(target, str) and target and target != expected_target:
        missing.append(f"{prefix}.target_match")
    for field in ("source_files", "include_files", "filelist_entries"):
        missing.extend(_repo_relative_string_list_missing(value.get(field), field, prefix))

    review_evidence = value.get("review_evidence")
    if not isinstance(review_evidence, Mapping):
        missing.append(f"{prefix}.review_evidence")
    else:
        if review_evidence.get("reviewed") is not True:
            missing.append(f"{prefix}.review_evidence.reviewed")
        if not isinstance(review_evidence.get("review_ref"), str) or not review_evidence.get("review_ref"):
            missing.append(f"{prefix}.review_evidence.review_ref")
    return missing


def source_closure_is_reviewed(value: object) -> bool:
    return reviewed_source_closure_missing_context(value, "source_closure") == []
