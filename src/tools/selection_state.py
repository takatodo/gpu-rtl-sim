"""Load project selection: merge extensions, targets list, and verification commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_EXTENSION_KEYS = (
    "completed_goal_evidence",
    "mobile_vit_cpu_kick_imagenet_accuracy",
)


def _inject_active_scope_targets(root: Path, data: dict[str, Any]) -> None:
    """Populate ``active_scope['targets']`` from ``config/targets.json`` (single source)."""
    scope = data.get("active_scope")
    if not isinstance(scope, dict):
        return
    targets_path = root / "config" / "targets.json"
    registry = json.loads(targets_path.read_text(encoding="utf-8"))
    active = registry.get("active_targets")
    if not isinstance(active, list):
        return
    names = [str(entry["name"]) for entry in active if isinstance(entry, dict) and entry.get("name")]
    scope["targets"] = names


def _inject_verification_commands(root: Path, data: dict[str, Any]) -> None:
    """Populate ``verification['commands']`` from ``commands_artifact`` when absent (P2 split)."""
    ver = data.get("verification")
    if not isinstance(ver, dict) or "commands" in ver:
        return
    rel = ver.get("commands_artifact")
    if not rel:
        return
    payload = json.loads((root / rel).read_text(encoding="utf-8"))
    cmds = payload.get("commands")
    if isinstance(cmds, list):
        ver["commands"] = cmds


def load_selection(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[2]
    path = root / "config" / "selection.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = int(data.get("schema_version", 2))
    ext_rel = data.get("selection_extensions")
    if schema >= 3 and ext_rel:
        ext_path = root / ext_rel
        ext = json.loads(ext_path.read_text(encoding="utf-8"))
        for key in _EXTENSION_KEYS:
            if key in ext:
                data[key] = ext[key]
    _inject_active_scope_targets(root, data)
    _inject_verification_commands(root, data)
    return data
