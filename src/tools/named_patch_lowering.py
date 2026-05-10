"""Validate active TL-UL patch-script configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def resolve_patch_script_lines(
    *,
    gate: dict[str, Any],
    run_cfg: dict[str, Any],
    mdir: Path,
) -> tuple[list[str] | None, dict[str, Any] | None]:
    """Return explicit patch-script lines for active TL-UL run configs."""

    del gate, mdir
    patch_script_lines = run_cfg.get("patch_script_lines")
    if patch_script_lines is not None:
        if not isinstance(patch_script_lines, list) or not all(
            isinstance(line, str) for line in patch_script_lines
        ):
            raise SystemExit(f"error: {run_cfg['name']} patch_script_lines must be a list of strings")
        return patch_script_lines, None

    sequence_ref = run_cfg.get("named_patch_delta_sequence")
    if sequence_ref is not None:
        raise SystemExit(
            "error: named_patch_delta_sequence is outside the reduced active TL-UL surface"
        )

    return None, None
