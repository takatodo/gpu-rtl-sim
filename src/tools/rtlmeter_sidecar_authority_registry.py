"""RTLMeter sidecar authority registry helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

try:
    from .rtlmeter_source_closure_authority import source_closure_is_reviewed
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_source_closure_authority import source_closure_is_reviewed


AUTHORITY_REGISTRY_PREFIX = ("config", "rtlmeter_sidecar_authorities")
AUTHORITY_REGISTRY_ROLE = "rtlmeter_sidecar_authority"


def _copy_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return list(value)
    return value


def _repo_root(repo_root: str | Path | None = None) -> Path:
    return Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]


def authority_registry_entry(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".json":
        return None
    if path.parts[: len(AUTHORITY_REGISTRY_PREFIX)] != AUTHORITY_REGISTRY_PREFIX:
        return None
    return path.as_posix()


def reviewed_registry_source_closure(
    entry: object,
    *,
    repo_root: str | Path | None,
    target: str,
    case: object,
    source_files: list[str],
    include_files: list[str],
    filelist_entries: list[str],
) -> object | None:
    registry_entry = authority_registry_entry(entry)
    if registry_entry is None:
        return None
    try:
        payload = json.loads((_repo_root(repo_root) / registry_entry).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_role") != AUTHORITY_REGISTRY_ROLE
        or payload.get("runtime_launchable") is not False
        or payload.get("target") != target
    ):
        return None
    closure = payload.get("source_closure")
    if not isinstance(closure, Mapping):
        return None
    if closure.get("target") != target or closure.get("rtlmeter_case") != str(case):
        return None
    if (
        closure.get("source_files") != source_files
        or closure.get("include_files") != include_files
        or closure.get("filelist_entries") != filelist_entries
    ):
        return None
    return _copy_value(closure) if source_closure_is_reviewed(closure) else None
