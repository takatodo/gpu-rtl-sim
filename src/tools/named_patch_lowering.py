"""Lower named memory delta schedules to existing patch-script lines."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from compare_vl_hybrid_modes import probe_root_layout


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPEATED_TO_STEPS_RE = re.compile(r"_repeated_to_(?P<steps>\d+)_logical_steps$")


def resolve_patch_script_lines(
    *,
    gate: dict[str, Any],
    run_cfg: dict[str, Any],
    mdir: Path,
) -> tuple[list[str] | None, dict[str, Any] | None]:
    """Return explicit patch-script lines for legacy or named-delta run configs."""

    patch_script_lines = run_cfg.get("patch_script_lines")
    if patch_script_lines is not None:
        if not isinstance(patch_script_lines, list) or not all(
            isinstance(line, str) for line in patch_script_lines
        ):
            raise SystemExit(f"error: {run_cfg['name']} patch_script_lines must be a list of strings")
        return patch_script_lines, None

    sequence_ref = run_cfg.get("named_patch_delta_sequence")
    if sequence_ref is None:
        return None, None
    if not isinstance(sequence_ref, str):
        raise SystemExit(f"error: {run_cfg['name']} named_patch_delta_sequence must be a string")

    source_gate = gate
    source_ref = sequence_ref
    if sequence_ref.startswith("source_gpu_gate."):
        source_gate_path = gate.get("source_gpu_gate")
        if not isinstance(source_gate_path, str):
            raise SystemExit(f"error: {gate['gate']} source_gpu_gate must be set")
        source_gate = _load_json(REPO_ROOT / source_gate_path)
        source_ref = sequence_ref.removeprefix("source_gpu_gate.")

    deltas = source_gate.get("named_patch_deltas")
    if not isinstance(deltas, list) or not all(isinstance(delta, dict) for delta in deltas):
        raise SystemExit(f"error: {source_gate['gate']} named_patch_deltas must be a list of objects")

    offsets = _named_rom_lane_offsets(mdir)
    requested_steps = int(run_cfg["steps"]) if "steps" in run_cfg else None
    lines = _lower_named_delta_sequence(
        deltas=deltas,
        offsets=offsets,
        sequence_ref=source_ref,
        requested_steps=requested_steps,
    )
    return lines, {
        "source": "named_patch_delta_sequence",
        "sequence_ref": sequence_ref,
        "source_gate": source_gate.get("gate"),
        "lowered_line_count": len(lines),
        "resolved_lane_offsets": offsets,
    }


def _load_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _named_rom_lane_offsets(mdir: Path) -> dict[str, int]:
    layout = probe_root_layout(mdir)
    offsets: dict[str, int] = {}
    for lane in ("ram0", "ram1", "ram2", "ram3"):
        suffix = f"x_iahb_mem_ctrl__DOT__{lane}__DOT__mem"
        matches = [entry for entry in layout if str(entry["name"]).endswith(suffix)]
        if len(matches) != 1:
            raise SystemExit(
                f"error: expected one generated root member ending with {suffix}, found {len(matches)}"
            )
        offsets[lane] = int(matches[0]["offset"])
    return offsets


def _lower_named_delta_sequence(
    *,
    deltas: list[dict[str, Any]],
    offsets: dict[str, int],
    sequence_ref: str,
    requested_steps: int | None,
) -> list[str]:
    if sequence_ref == "named_patch_deltas":
        max_step = max(int(delta["logical_step"]) for delta in deltas)
        steps = max(max_step + 1, requested_steps or 0)
        return _lines_for_steps(deltas=deltas, offsets=offsets, steps=steps)

    repeat_match = REPEATED_TO_STEPS_RE.search(sequence_ref)
    if sequence_ref.startswith("named_patch_deltas") and repeat_match:
        steps = int(repeat_match.group("steps"))
        return _lines_for_repeated_steps(deltas=deltas, offsets=offsets, steps=steps)

    raise SystemExit(f"error: unsupported named_patch_delta_sequence: {sequence_ref}")


def _lines_for_steps(
    *,
    deltas: list[dict[str, Any]],
    offsets: dict[str, int],
    steps: int,
) -> list[str]:
    by_step: dict[int, list[dict[str, Any]]] = {}
    for delta in deltas:
        by_step.setdefault(int(delta["logical_step"]), []).append(delta)
    return [_line_for_deltas(by_step.get(step, []), offsets) for step in range(steps)]


def _lines_for_repeated_steps(
    *,
    deltas: list[dict[str, Any]],
    offsets: dict[str, int],
    steps: int,
) -> list[str]:
    first_step_deltas = [delta for delta in deltas if int(delta["logical_step"]) == 0]
    recurring_deltas = [delta for delta in deltas if int(delta["logical_step"]) > 0]
    lines: list[str] = []
    for step in range(steps):
        if step == 0:
            lines.append(_line_for_deltas(first_step_deltas, offsets))
        elif step % 2 == 0:
            lines.append(_line_for_deltas(recurring_deltas, offsets))
        else:
            lines.append("-")
    return lines


def _line_for_deltas(deltas: list[dict[str, Any]], offsets: dict[str, int]) -> str:
    if not deltas:
        return "-"
    patches: list[str] = []
    for delta in deltas:
        lane = str(delta["lane"])
        if lane not in offsets:
            raise SystemExit(f"error: unsupported named ROM lane: {lane}")
        word_index = int(delta["word_index"])
        byte_value = int(delta["byte_value"])
        if not 0 <= byte_value <= 255:
            raise SystemExit(f"error: byte_value out of range: {byte_value}")
        patches.append(f"{offsets[lane] + word_index}:{byte_value}")
    return " ".join(patches)
