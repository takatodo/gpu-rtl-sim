"""Timed CPU/GPU launch execution for TL-UL #10818 boundary trials."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from run_tlul10818_gpu_equivalence import HYBRID_RUNNER
from run_vl_equiv_utils import batch_observables

from tlul10818_boundary_runner_io import (
    cpu_command,
    patch_lines,
    require_success,
    run_repo,
)


def parameters(action: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = action.get("parameters")
    if not isinstance(raw, Mapping):
        raise ValueError("action parameters are invalid")
    return raw


def batch_patch_script(
    *,
    offsets: Mapping[str, int],
    actions_by_point: Mapping[str, Mapping[str, Any]],
    group: Sequence[tuple[int, str, str, str]],
) -> tuple[str, int]:
    scripts = [
        patch_lines(offsets, parameters(actions_by_point[point_id]))
        for _epoch_index, point_id, _revision, _purpose in group
    ]
    lines: list[str] = []
    for step_index in range(max(len(steps) for steps in scripts)):
        tokens: list[str] = []
        for state_index, steps in enumerate(scripts):
            if step_index >= len(steps):
                continue
            for token in steps[step_index]:
                offset, value = token.split(":", 1)
                tokens.append(f"@{state_index}:{offset}:{value}")
        lines.append(" ".join(tokens))
    return "\n".join(lines) + "\n", len(lines)


def execute_timed_group(
    *,
    backend: Mapping[str, Any],
    revision: Mapping[str, Any],
    revision_label: str,
    trial_id: str,
    launch_index: int,
    group: Sequence[tuple[int, str, str, str]],
    point_rows: Sequence[Mapping[str, Any]],
    actions_by_point: Mapping[str, Mapping[str, Any]],
    work_dir: Path,
) -> int:
    if backend["kind"] == "cpu":
        cycle_evals = 0
        for _epoch, point_id, _revision, _purpose in group:
            action_parameters = parameters(actions_by_point[point_id])
            completed = subprocess.run(
                cpu_command(revision["cpu_binary"], action_parameters),
                text=True,
                capture_output=True,
                check=False,
            )
            require_success(completed, f"CPU timing execution {trial_id}:{launch_index}")
            cycle_evals += len(patch_lines(revision["offsets"], action_parameters))
        return cycle_evals
    if backend["kind"] != "gpu":
        raise ValueError(f"unsupported backend kind: {backend['kind']}")
    launch_dir = work_dir / "trial_launches" / revision_label
    launch_dir.mkdir(parents=True, exist_ok=True)
    script, cycle_evals = batch_patch_script(
        offsets=revision["offsets"],
        actions_by_point=actions_by_point,
        group=group,
    )
    patch = launch_dir / f"{trial_id}_{launch_index}.patch"
    state = launch_dir / f"{trial_id}_{launch_index}.gpu.bin"
    patch.write_text(script, encoding="utf-8")
    completed = run_repo(
        [
            sys.executable,
            str(HYBRID_RUNNER),
            "--mdir",
            str(revision["gpu_mdir"]),
            "--nstates",
            str(len(group)),
            "--resident-steps",
            "--patch-script",
            str(patch),
            "--dump-state",
            str(state),
        ],
        env=revision["env"],
    )
    require_success(completed, f"GPU timing launch {trial_id}:{launch_index}")
    observed = batch_observables(state.read_bytes(), len(group), revision["storage_size"], revision["offsets"])
    for index, (_epoch, point_id, _rev, _purpose) in enumerate(group):
        expected = next(row for row in point_rows if row["point_id"] == point_id)
        expected_gpu = dict(expected["revisions"][revision_label]["gpu"])
        expected_gpu["action_coverage"] = observed[index]["action_coverage"]
        if dict(observed[index]) != expected_gpu:
            raise RuntimeError(f"GPU timing launch mismatch for {trial_id}:{launch_index}:{point_id}")
    return cycle_evals
