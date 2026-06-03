"""RTLMeter sidecar launcher invocation metadata."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_source_closure_authority import (
        reviewed_source_closure_missing_context,
        source_closure_is_reviewed,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_source_closure_authority import (
        reviewed_source_closure_missing_context,
        source_closure_is_reviewed,
    )


HANDOFF_SURFACE = "rtlmeter_sidecar_handoff"
HANDOFF_METADATA_READY = "rtlmeter_sidecar_handoff_metadata_ready"
STATUS_LAUNCHER_METADATA_READY = "rtlmeter_sidecar_launcher_invocation_metadata_ready"
STATUS_LAUNCHER_BLOCKED = "rtlmeter_sidecar_launcher_invocation_blocked"
AUTHORITY_REGISTRY_ROLE = "rtlmeter_sidecar_authority"
RUNTIME_TEMPLATE_ROLE = "runnable_hybrid_template"
RUNTIME_TEMPLATE_PREFIX = ("config", "slice_launch_templates")
AUTHORITY_REGISTRY_PREFIX = ("config", "rtlmeter_sidecar_authorities")


def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return list(value)
    return value


def _relative_template_path(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path.as_posix()


def _path_has_prefix(path: str, prefix: tuple[str, ...]) -> bool:
    return Path(path).parts[: len(prefix)] == prefix


def _is_runtime_template_path(path: str) -> bool:
    return _path_has_prefix(path, RUNTIME_TEMPLATE_PREFIX) and Path(path).suffix == ".json"


def _is_authority_registry_path(path: str) -> bool:
    return _path_has_prefix(path, AUTHORITY_REGISTRY_PREFIX) and Path(path).suffix == ".json"


def _json_payload(config_path: str, repo_root: Path, *, error_prefix: str) -> tuple[dict[str, object] | None, str | None]:
    path = repo_root / config_path
    if not path.is_file():
        return None, f"{error_prefix}_file"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, f"{error_prefix}_json"
    if not isinstance(loaded, Mapping):
        return None, f"{error_prefix}_payload"
    return {str(key): _copy_value(value) for key, value in loaded.items()}, None


def _template_payload(template_path: str, repo_root: Path) -> tuple[dict[str, object] | None, str | None]:
    return _json_payload(template_path, repo_root, error_prefix="template")


def _target_missing_context(payload: Mapping[str, object], expected_target: object, prefix: str) -> list[str]:
    target = payload.get("target")
    if not isinstance(target, str) or not target:
        return [f"{prefix}.target" if prefix else "template_target"]
    if target != expected_target:
        return [f"{prefix}.target_match" if prefix else "template_target_match"]
    return []


def _runtime_template_missing_context(
    template_path: str,
    template_payload: Mapping[str, object],
    *,
    expected_target: object,
) -> list[str]:
    missing: list[str] = []
    if not _is_runtime_template_path(template_path):
        missing.append("runtime_launch_template")
    missing.extend(_target_missing_context(template_payload, expected_target, ""))
    missing.extend(reviewed_source_closure_missing_context(template_payload.get("source_closure"), "template_source_closure"))
    if template_payload.get("template_execution_role") != RUNTIME_TEMPLATE_ROLE:
        missing.append("template_execution_role")
    return missing


def _authority_registry_missing_context(
    registry_payload: Mapping[str, object],
    *,
    expected_target: object,
) -> list[str]:
    missing: list[str] = []
    if registry_payload.get("schema_role") != AUTHORITY_REGISTRY_ROLE:
        missing.append("authority_registry.schema_role")
    if registry_payload.get("runtime_launchable") is not False:
        missing.append("authority_registry.runtime_launchable")
    missing.extend(_target_missing_context(registry_payload, expected_target, "authority_registry"))
    missing.extend(
        reviewed_source_closure_missing_context(
            registry_payload.get("source_closure"),
            "authority_registry.source_closure",
        )
    )
    return missing


def _entry_missing_context(entry: str, root: Path, target: object) -> tuple[list[str], str | None, str | None]:
    missing: list[str] = []
    authority_registry_entry = None
    runtime_launch_template = None
    entry_is_authority_registry = _is_authority_registry_path(entry)
    entry_payload, entry_error = _json_payload(
        entry,
        root,
        error_prefix="authority_registry" if entry_is_authority_registry else "template",
    )
    if entry_error is not None:
        return [entry_error], None, None
    entry_is_authority_registry = entry_is_authority_registry or entry_payload.get("schema_role") == AUTHORITY_REGISTRY_ROLE
    if not entry_is_authority_registry:
        return _runtime_template_missing_context(entry, entry_payload, expected_target=target), None, entry

    authority_registry_entry = entry
    missing.extend(_authority_registry_missing_context(entry_payload, expected_target=target))
    runtime_launch_template = _relative_template_path(entry_payload.get("runtime_launch_template"))
    if runtime_launch_template is None:
        missing.append("runtime_launch_template")
        return missing, authority_registry_entry, None
    template_payload, template_error = _template_payload(runtime_launch_template, root)
    if template_error is not None:
        missing.append(template_error)
    else:
        missing.extend(_runtime_template_missing_context(runtime_launch_template, template_payload, expected_target=target))
    return missing, authority_registry_entry, runtime_launch_template


def build_rtlmeter_sidecar_launcher_invocation(
    handoff_metadata: Mapping[str, object],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, object]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    missing: list[str] = []
    if handoff_metadata.get("surface") != HANDOFF_SURFACE:
        missing.append("handoff_surface")
    if handoff_metadata.get("status") != HANDOFF_METADATA_READY:
        missing.append("handoff_metadata_ready")

    schedule = handoff_metadata.get("schedule")
    shape = schedule.get("shape") if isinstance(schedule, Mapping) else None
    if not isinstance(shape, str) or not shape:
        missing.append("schedule.shape")

    context = handoff_metadata.get("sidecar_context")
    target = context.get("target") if isinstance(context, Mapping) else None
    if not isinstance(target, str) or not target:
        missing.append("sidecar_context.target")
    source_closure = context.get("source_closure") if isinstance(context, Mapping) else None
    if not source_closure_is_reviewed(source_closure):
        missing.append("sidecar_context.source_closure")

    authority_registry_entry = None
    runtime_launch_template = None
    entry = _relative_template_path(
        context.get("template_or_target_registry_entry") if isinstance(context, Mapping) else None
    )
    if entry is None:
        missing.append("sidecar_context.template_or_target_registry_entry")
    else:
        entry_missing, authority_registry_entry, runtime_launch_template = _entry_missing_context(entry, root, target)
        missing.extend(entry_missing)

    launcher_argv = None
    if not missing and isinstance(shape, str) and runtime_launch_template is not None:
        launcher_argv = ["python3", "src/tools/run_hybrid_template.py", runtime_launch_template, "--shape", shape]

    return {
        "schema_version": 1,
        "surface": "rtlmeter_sidecar_launcher_invocation",
        "status": STATUS_LAUNCHER_METADATA_READY if not missing else STATUS_LAUNCHER_BLOCKED,
        "source_surface": handoff_metadata.get("surface"),
        "source_status": handoff_metadata.get("status"),
        "missing_invocation_context": missing,
        "schedule": _copy_value(schedule) if schedule is not None else None,
        "sidecar_context": _copy_value(context) if context is not None else None,
        "authority_registry_entry": authority_registry_entry,
        "runtime_launch_template": runtime_launch_template,
        "sidecar_launcher_entrypoint": "src/tools/run_hybrid_template.py",
        "launcher_command_argv": launcher_argv,
        "launcher_command_role": "materialized_for_later_run_not_invoked" if launcher_argv else "not_materialized",
        "sidecar_launcher_invoked": False,
        "sidecar_execution_invoked": False,
        "coverage_output_compare_reached": False,
        "execution_performed": False,
        "measurement_performed": False,
        "generated_reports_and_artifacts_source_of_truth": False,
        "non_claims": [
            "RTLMeter launcher invocation metadata does not execute run_hybrid_template.py",
            "RTLMeter launcher invocation metadata requires a reviewed RTLMeter template before materializing argv",
            "RTLMeter launcher invocation metadata does not prove correctness, timing, speedup, or native Verilator execution",
        ],
    }
