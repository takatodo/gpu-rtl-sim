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


def build_rtlmeter_sidecar_proxy_marker_payload() -> dict[str, object]:
    return {
        "schema_version": MARKER_SCHEMA_VERSION,
        "schema_role": MARKER_SCHEMA_ROLE,
        "producer": MARKER_PRODUCER,
        "phase": MARKER_PHASE,
        "cpu_as_gpu_fallback": False,
        "ordinary_vsim_output": False,
        "execute_proxy_installed_by_wrapper_branch": False,
    }


def write_rtlmeter_sidecar_proxy_marker(*, observable_execute_dir: object, repo_root: Path | None) -> Path:
    marker_path = rtlmeter_sidecar_proxy_marker_path(observable_execute_dir, repo_root)
    if marker_path is None:
        raise ValueError("observable_execute_dir is required to write the RTLMeter sidecar proxy marker")
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_rtlmeter_sidecar_proxy_marker_payload()
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
    if payload.get("execute_proxy_installed_by_wrapper_branch") is not False:
        missing.append("execute_proxy_installed_by_wrapper_branch")
    return missing


def observe_rtlmeter_sidecar_proxy_marker(
    *, observable_execute_dir: object, repo_root: Path | None
) -> dict[str, object]:
    marker_path = rtlmeter_sidecar_proxy_marker_path(observable_execute_dir, repo_root)
    marker_path_text = _relative_path(marker_path, repo_root) if marker_path is not None else None
    if marker_path is None or not marker_path.is_file():
        return {
            "sidecar_proxy_marker_status": STATUS_MISSING,
            "sidecar_proxy_marker_path": marker_path_text,
            "sidecar_proxy_marker_present": False,
            "sidecar_proxy_marker_valid": False,
            "sidecar_execute_proxy_installed_by_wrapper_branch": False,
            "sidecar_proxy_marker_missing_context": ["marker_file"],
        }
    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "sidecar_proxy_marker_status": STATUS_INVALID,
            "sidecar_proxy_marker_path": marker_path_text,
            "sidecar_proxy_marker_present": True,
            "sidecar_proxy_marker_valid": False,
            "sidecar_execute_proxy_installed_by_wrapper_branch": False,
            "sidecar_proxy_marker_missing_context": ["marker_json"],
        }
    missing = _missing_marker_context(payload)
    return {
        "sidecar_proxy_marker_status": STATUS_VALID if not missing else STATUS_INVALID,
        "sidecar_proxy_marker_path": marker_path_text,
        "sidecar_proxy_marker_present": True,
        "sidecar_proxy_marker_valid": not missing,
        "sidecar_execute_proxy_installed_by_wrapper_branch": False,
        "sidecar_proxy_marker_missing_context": missing,
    }
