"""Recognize a Verilator native filelist/top pair against tracked known closures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

SURFACE = "verilator_native_known_closure"
REGISTRY_SCHEMA_ROLE = "verilator_native_known_closures"
DEFAULT_REGISTRY = Path("config/native_known_closures.json")
STATUS_RECOGNIZED = "verilator_native_known_closure_recognized"
STATUS_UNRECOGNIZED = "verilator_native_known_closure_unrecognized"
STATUS_REGISTRY_UNUSABLE = "verilator_native_known_closure_registry_unusable"
STATUS_FILELIST_MISSING = "verilator_native_known_closure_filelist_missing"
RECOGNIZED_TARGET_ONLY = (
    "recognized target only: native --sim-accel supports tracked known closures and "
    "fails closed for any other filelist/top pair"
)
NON_CLAIMS = (
    "recognition covers tracked known closures only, not arbitrary filelists",
    "recognition is not dependency inference and not automatic allocation",
    "recognition success is compile-side metadata, not GPU execution evidence",
    "no speedup or timing claim is made",
)


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "<local-absolute-path>"


def parse_verilator_filelist(filelist_path: Path) -> list[str]:
    """Return non-empty, non-comment filelist lines without inferring anything."""
    entries: list[str] = []
    for raw_line in filelist_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def _load_json(path: Path) -> Mapping[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, Mapping) else None


def _template_source_files(repo_root: Path, launch_template: object) -> list[str] | None:
    if not isinstance(launch_template, str) or not launch_template:
        return None
    template = _load_json(repo_root / launch_template)
    if template is None:
        return None
    source_files = template.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        return None
    return [str(item) for item in source_files]


def _closure_filelist_entries(repo_root: Path, closure: Mapping[str, object]) -> list[str] | None:
    inline_entries = closure.get("filelist_entries")
    if isinstance(inline_entries, list) and inline_entries:
        return [str(item) for item in inline_entries]
    return _template_source_files(repo_root, closure.get("launch_template"))


def _report(
    *,
    status: str,
    filelist_display: str | None,
    top_module: str | None,
    missing_context: list[str],
    diagnostic: str,
    closure: Mapping[str, object] | None = None,
) -> dict[str, object]:
    recognized = status == STATUS_RECOGNIZED
    report: dict[str, object] = {
        "schema_version": 1,
        "surface": SURFACE,
        "status": status,
        "recognized": recognized,
        "filelist_path": filelist_display,
        "top_module": top_module,
        "target": closure.get("target") if recognized and closure else None,
        "launch_template": closure.get("launch_template") if recognized and closure else None,
        "fail_closed": True,
        "arbitrary_filelist_supported": False,
        "dependency_inference_performed": False,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "missing_recognition_context": missing_context,
        "diagnostic": diagnostic,
        "non_claims": list(NON_CLAIMS),
    }
    return report


def recognize_verilator_native_known_closure(
    *,
    filelist_path: str | Path,
    top_module: str,
    repo_root: Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, object]:
    root = (repo_root or Path.cwd()).resolve()
    registry_file = root / (registry_path or DEFAULT_REGISTRY)
    filelist = Path(filelist_path)
    if not filelist.is_absolute():
        filelist = root / filelist
    filelist_display = _display_path(filelist, root)

    registry = _load_json(registry_file)
    closures = registry.get("closures") if isinstance(registry, Mapping) else None
    if (
        not isinstance(registry, Mapping)
        or registry.get("schema_role") != REGISTRY_SCHEMA_ROLE
        or not isinstance(closures, list)
    ):
        return _report(
            status=STATUS_REGISTRY_UNUSABLE,
            filelist_display=filelist_display,
            top_module=top_module,
            missing_context=["native_known_closures_registry"],
            diagnostic=f"{RECOGNIZED_TARGET_ONLY}; the tracked closure registry is missing or invalid",
        )
    if not filelist.is_file():
        return _report(
            status=STATUS_FILELIST_MISSING,
            filelist_display=filelist_display,
            top_module=top_module,
            missing_context=["filelist"],
            diagnostic=f"{RECOGNIZED_TARGET_ONLY}; the filelist does not exist",
        )

    entries = parse_verilator_filelist(filelist)
    for closure in closures:
        if not isinstance(closure, Mapping) or closure.get("top_module") != top_module:
            continue
        expected = _closure_filelist_entries(root, closure)
        if expected is not None and entries == expected:
            return _report(
                status=STATUS_RECOGNIZED,
                filelist_display=filelist_display,
                top_module=top_module,
                missing_context=[],
                diagnostic="filelist and top module match a tracked known closure exactly",
                closure=closure,
            )
    return _report(
        status=STATUS_UNRECOGNIZED,
        filelist_display=filelist_display,
        top_module=top_module,
        missing_context=["tracked_known_closure_match"],
        diagnostic=RECOGNIZED_TARGET_ONLY,
    )
