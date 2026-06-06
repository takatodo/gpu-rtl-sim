"""Fail-closed RTLMeter sidecar proxy marker observation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

MARKER_FILENAME = "_rtlmeter_sidecar_proxy_marker.json"
MARKER_SCHEMA_VERSION = 1
MARKER_SCHEMA_ROLE = "rtlmeter_sidecar_proxy_marker"
MARKER_PRODUCER = "rtlmeter_verilator_wrapper_runtime"
MARKER_PHASE = "sidecar_verilate"
STATUS_MISSING = "rtlmeter_sidecar_proxy_marker_missing"
STATUS_INVALID = "rtlmeter_sidecar_proxy_marker_invalid"
STATUS_VALID = "rtlmeter_sidecar_proxy_marker_valid"

def _relative_path(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    if path.is_absolute():
        return "<local-absolute-path>"
    return path.as_posix()


def rtlmeter_sidecar_proxy_marker_path(observable_execute_dir: object, repo_root: Path | None) -> Path | None:
    if not isinstance(observable_execute_dir, str) or not observable_execute_dir:
        return None
    execute_dir = Path(observable_execute_dir)
    if not execute_dir.is_absolute() and repo_root is not None:
        execute_dir = repo_root / execute_dir
    return execute_dir / MARKER_FILENAME


def build_rtlmeter_sidecar_proxy_marker_payload(
    *, proxy_readiness: Mapping[str, object] | None = None
) -> dict[str, object]:
    proxy_installed = (
        isinstance(proxy_readiness, Mapping)
        and proxy_readiness.get("proxy_installed_by_wrapper_branch") is True
    )
    proxy_authorized = proxy_installed and isinstance(proxy_readiness, Mapping) and proxy_readiness.get("proxy_authorized_by_wrapper_branch") is True and proxy_readiness.get("execution_authority") is True
    main_patch = proxy_readiness.get("vsim_main_proxy_patch") if isinstance(proxy_readiness, Mapping) else None
    proxy_source_patch = (
        isinstance(main_patch, Mapping)
        and main_patch.get("patched_by_wrapper_branch") is True
        and main_patch.get("execution_authority") is True
    )
    payload = {
        "schema_version": MARKER_SCHEMA_VERSION,
        "schema_role": MARKER_SCHEMA_ROLE,
        "producer": MARKER_PRODUCER,
        "phase": MARKER_PHASE,
        "cpu_as_gpu_fallback": False,
        "ordinary_vsim_output": False,
        "execute_proxy_installed_by_wrapper_branch": proxy_installed,
        "execute_proxy_source_patch_by_wrapper_branch": proxy_source_patch,
        "execute_proxy_authorized_by_wrapper_branch": proxy_authorized and proxy_source_patch,
    }
    if proxy_readiness is not None:
        payload["direct_sidecar_proxy_readiness"] = dict(proxy_readiness)
    return payload


def write_rtlmeter_sidecar_proxy_marker(
    *,
    observable_execute_dir: object,
    repo_root: Path | None,
    proxy_readiness: Mapping[str, object] | None = None,
) -> Path:
    marker_path = rtlmeter_sidecar_proxy_marker_path(observable_execute_dir, repo_root)
    if marker_path is None:
        raise ValueError("observable_execute_dir is required to write the RTLMeter sidecar proxy marker")
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_rtlmeter_sidecar_proxy_marker_payload(proxy_readiness=proxy_readiness)
    marker_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return marker_path


def _missing_marker_context(payload: object) -> list[str]:
    if not isinstance(payload, Mapping):
        return ["payload"]
    missing: list[str] = []
    if payload.get("schema_version") != MARKER_SCHEMA_VERSION:
        missing.append("schema_version")
    if payload.get("schema_role") != MARKER_SCHEMA_ROLE:
        missing.append("schema_role")
    if payload.get("producer") != MARKER_PRODUCER:
        missing.append("producer")
    if payload.get("phase") != MARKER_PHASE:
        missing.append("phase")
    if payload.get("cpu_as_gpu_fallback") is not False:
        missing.append("cpu_as_gpu_fallback")
    if payload.get("ordinary_vsim_output") is not False:
        missing.append("ordinary_vsim_output")
    proxy_installed = payload.get("execute_proxy_installed_by_wrapper_branch")
    if proxy_installed not in (False, True):
        missing.append("execute_proxy_installed_by_wrapper_branch")
    proxy_source_patch = payload.get("execute_proxy_source_patch_by_wrapper_branch", False)
    if proxy_source_patch not in (False, True):
        missing.append("execute_proxy_source_patch_by_wrapper_branch")
    proxy_authorized = payload.get(
        "execute_proxy_authorized_by_wrapper_branch",
        proxy_installed is True and proxy_source_patch is True,
    )
    if proxy_authorized not in (False, True):
        missing.append("execute_proxy_authorized_by_wrapper_branch")
    if proxy_authorized is True and proxy_installed is not True:
        missing.append("execute_proxy_installed_by_wrapper_branch")
    if proxy_authorized is True and proxy_source_patch is not True:
        missing.append("execute_proxy_source_patch_by_wrapper_branch")
    if proxy_authorized is True:
        readiness = payload.get("direct_sidecar_proxy_readiness")
        if not isinstance(readiness, Mapping):
            missing.append("direct_sidecar_proxy_readiness")
        else:
            if readiness.get("execution_authority") is not True:
                missing.append("direct_sidecar_proxy_readiness.execution_authority")
            if readiness.get("proxy_authorized_by_wrapper_branch", True) is not True:
                missing.append("direct_sidecar_proxy_readiness.proxy_authorized_by_wrapper_branch")
            target = readiness.get("vsim_sidecar_proxy_target")
            if not isinstance(target, Mapping) or target.get("reviewed_proxy_target") is not True:
                missing.append("direct_sidecar_proxy_readiness.vsim_sidecar_proxy_target.reviewed_proxy_target")
            if proxy_installed is True and readiness.get("proxy_installed_by_wrapper_branch") is not True:
                missing.append("direct_sidecar_proxy_readiness.proxy_installed_by_wrapper_branch")
            main_patch = readiness.get("vsim_main_proxy_patch")
            readiness_source_patch = readiness.get("proxy_source_patch_by_wrapper_branch") is True
            readiness_source_patch = readiness_source_patch or (
                isinstance(main_patch, Mapping)
                and main_patch.get("patched_by_wrapper_branch") is True
                and main_patch.get("execution_authority") is True
            )
            if proxy_source_patch is True and not readiness_source_patch:
                missing.append("direct_sidecar_proxy_readiness.proxy_source_patch_by_wrapper_branch")
    return missing


def _sidecar_proxy_evidence(
    *,
    marker_status: str,
    marker_path: str | None,
    marker_present: bool,
    marker_valid: bool,
    proxy_installed: bool,
    source_patch: bool,
    proxy_authorized: bool,
    missing_context: list[str],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface": "rtlmeter_sidecar_proxy_marker_evidence",
        "sidecar_proxy_marker_status": marker_status,
        "sidecar_proxy_marker_path": marker_path,
        "sidecar_proxy_marker_present": marker_present,
        "sidecar_proxy_marker_valid": marker_valid,
        "sidecar_execute_proxy_installed_by_wrapper_branch": proxy_installed,
        "sidecar_execute_proxy_source_patch_by_wrapper_branch": source_patch,
        "sidecar_execute_proxy_authorized_by_wrapper_branch": proxy_authorized,
        "sidecar_proxy_marker_missing_context": list(missing_context),
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
    }


def build_rtlmeter_sidecar_proxy_execution_evidence(
    *,
    proxy_marker: Mapping[str, object],
    observables_ready: bool,
    missing_observables: object,
    runner_command_observed: bool,
    execution_performed: bool,
    execution_authority: bool,
) -> dict[str, object]:
    blocking_context = list(proxy_marker.get("sidecar_proxy_marker_missing_context", []))
    if not observables_ready and isinstance(missing_observables, list):
        blocking_context.extend(str(item) for item in missing_observables)
    if not runner_command_observed:
        blocking_context.append("runner_command_not_observed")
    for field in (
        "sidecar_proxy_marker_valid",
        "sidecar_execute_proxy_installed_by_wrapper_branch",
        "sidecar_execute_proxy_source_patch_by_wrapper_branch",
        "sidecar_execute_proxy_authorized_by_wrapper_branch",
    ):
        if proxy_marker.get(field) is not True:
            blocking_context.append(field)
    return {
        "schema_version": 1,
        "surface": "rtlmeter_stdout_cycles_sidecar_proxy_execution_evidence",
        "status": "ready" if execution_authority else "blocked",
        "observables_ready": observables_ready,
        "runner_command_observed": runner_command_observed,
        "sidecar_proxy_marker_status": proxy_marker.get("sidecar_proxy_marker_status"),
        "sidecar_proxy_marker_valid": proxy_marker.get("sidecar_proxy_marker_valid") is True,
        "sidecar_execute_proxy_installed_by_wrapper_branch": proxy_marker.get("sidecar_execute_proxy_installed_by_wrapper_branch") is True,
        "sidecar_execute_proxy_source_patch_by_wrapper_branch": proxy_marker.get("sidecar_execute_proxy_source_patch_by_wrapper_branch") is True,
        "sidecar_execute_proxy_authorized_by_wrapper_branch": proxy_marker.get("sidecar_execute_proxy_authorized_by_wrapper_branch") is True,
        "execution_performed": execution_performed,
        "execution_authority": execution_authority,
        "rtlmeter_vsim_proxy_handoff_status": "ready" if execution_authority else "blocked",
        "rtlmeter_vsim_proxy_handoff_reached": execution_authority,
        "sidecar_execution_invoked": execution_authority,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "blocking_context": sorted(set(blocking_context)),
    }


def observe_rtlmeter_sidecar_proxy_marker(
    *, observable_execute_dir: object, repo_root: Path | None
) -> dict[str, object]:
    marker_path = rtlmeter_sidecar_proxy_marker_path(observable_execute_dir, repo_root)
    marker_path_text = _relative_path(marker_path, repo_root) if marker_path is not None else None
    if marker_path is None or not marker_path.is_file():
        evidence = _sidecar_proxy_evidence(
            marker_status=STATUS_MISSING,
            marker_path=marker_path_text,
            marker_present=False,
            marker_valid=False,
            proxy_installed=False,
            source_patch=False,
            proxy_authorized=False,
            missing_context=["marker_file"],
        )
        return {
            "sidecar_proxy_marker_status": STATUS_MISSING,
            "sidecar_proxy_marker_path": marker_path_text,
            "sidecar_proxy_marker_present": False,
            "sidecar_proxy_marker_valid": False,
            "sidecar_execute_proxy_installed_by_wrapper_branch": False,
            "sidecar_execute_proxy_source_patch_by_wrapper_branch": False,
            "sidecar_execute_proxy_authorized_by_wrapper_branch": False,
            "sidecar_proxy_marker_missing_context": ["marker_file"],
            "sidecar_proxy_evidence": evidence,
        }
    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        evidence = _sidecar_proxy_evidence(
            marker_status=STATUS_INVALID,
            marker_path=marker_path_text,
            marker_present=True,
            marker_valid=False,
            proxy_installed=False,
            source_patch=False,
            proxy_authorized=False,
            missing_context=["marker_json"],
        )
        return {
            "sidecar_proxy_marker_status": STATUS_INVALID,
            "sidecar_proxy_marker_path": marker_path_text,
            "sidecar_proxy_marker_present": True,
            "sidecar_proxy_marker_valid": False,
            "sidecar_execute_proxy_installed_by_wrapper_branch": False,
            "sidecar_execute_proxy_source_patch_by_wrapper_branch": False,
            "sidecar_execute_proxy_authorized_by_wrapper_branch": False,
            "sidecar_proxy_marker_missing_context": ["marker_json"],
            "sidecar_proxy_evidence": evidence,
        }
    missing = _missing_marker_context(payload)
    marker_valid = not missing
    proxy_installed = marker_valid and payload.get("execute_proxy_installed_by_wrapper_branch") is True
    source_patch = marker_valid and payload.get("execute_proxy_source_patch_by_wrapper_branch", False) is True
    proxy_authorized = (
        marker_valid
        and payload.get(
            "execute_proxy_authorized_by_wrapper_branch",
            payload.get("execute_proxy_installed_by_wrapper_branch") is True
            and payload.get("execute_proxy_source_patch_by_wrapper_branch") is True,
        )
        is True
    )
    marker_status = STATUS_VALID if marker_valid else STATUS_INVALID
    evidence = _sidecar_proxy_evidence(
        marker_status=marker_status,
        marker_path=marker_path_text,
        marker_present=True,
        marker_valid=marker_valid,
        proxy_installed=proxy_installed,
        source_patch=source_patch,
        proxy_authorized=proxy_authorized,
        missing_context=missing,
    )
    return {
        "sidecar_proxy_marker_status": marker_status,
        "sidecar_proxy_marker_path": marker_path_text,
        "sidecar_proxy_marker_present": True,
        "sidecar_proxy_marker_valid": marker_valid,
        "sidecar_execute_proxy_installed_by_wrapper_branch": proxy_installed,
        "sidecar_execute_proxy_source_patch_by_wrapper_branch": source_patch,
        "sidecar_execute_proxy_authorized_by_wrapper_branch": proxy_authorized,
        "sidecar_proxy_marker_missing_context": missing,
        "sidecar_proxy_evidence": evidence,
    }
