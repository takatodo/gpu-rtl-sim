"""Patch schedules and CPU/GPU observable helpers for the Ibex #2188 runner."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from run_vl_equiv_utils import (
    read_object,
    require_success,
    revision_sha,
    run_repo,
    sha256,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TOP = "ibex2188_ecc_temporal_gpu_tb"
GPU_TB = REPO_ROOT / "examples" / "ibex2188" / "ibex2188_ecc_temporal_gpu_tb.sv"
CPU_DRIVER = REPO_ROOT / "examples" / "ibex2188" / "ibex2188_ecc_temporal_gpu_driver.cpp"
BUILD_VL_GPU = REPO_ROOT / "src" / "tools" / "build_vl_gpu.py"
HYBRID_RUNNER = REPO_ROOT / "src" / "tools" / "run_vl_hybrid.py"
BAD_REVISION = "668233699df9ec2a40413e69e0de0a5b10185980"
FIXED_REVISION = "9e4a950aa6aa0e20eb638aeeb78743d4a9ddaaeb"

# Root-state byte offsets (probe-verified against both pinned revisions).
INPUT_OFFSETS = {
    "clk_i": 104,
    "rst_ni": 105,
    "fault_enable_i": 106,
    "inject_port_b_i": 107,
    "fault_bit_i": 108,
    "load_response_delay_i": 109,
}
OBSERVABLE_OFFSETS = {
    "done": 110,
    "oracle_violation": 111,
    "fault_seen": 112,
    "alert_seen": 113,
    "rf_read_enable": 114,
    "rf_wb_match": 115,
    "rf_write_wb": 116,
    "rf_ecc_error_id": 117,
    "instruction_valid_id": 118,
    "alert_major_internal": 119,
}
ALL_OBSERVABLE_KEYS = tuple(OBSERVABLE_OFFSETS)

RESULT_RE = re.compile(
    r"RESULT done=(\d+) oracle_violation=(\d+) fault_seen=(\d+) alert_seen=(\d+) "
    r"rf_read_enable=(\d+) rf_wb_match=(\d+) rf_write_wb=(\d+) rf_ecc_error_id=(\d+) "
    r"instruction_valid_id=(\d+) alert_major_internal=(\d+)"
)


def parameters(action: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = action.get("parameters")
    if not isinstance(raw, Mapping):
        raise ValueError("action parameters are invalid")
    return raw


def fault_enable_i(parameters: Mapping[str, Any]) -> int:
    mode = parameters.get("fault_enable")
    if mode == "disabled":
        return 0
    if mode == "guarded_bit0":
        return 1
    raise ValueError(f"unsupported fault_enable mode: {mode!r}")


def fault_bit_i(parameters: Mapping[str, Any]) -> int:
    return 0


def delay_i(parameters: Mapping[str, Any]) -> int:
    delay = parameters.get("load_response_delay_cycles")
    if delay not in (0, 1):
        raise ValueError(f"unsupported load_response_delay_cycles: {delay!r}")
    return int(delay)


def single_state_patch(parameters: Mapping[str, Any]) -> list[str]:
    """One patch schedule per point: 1 reset/control line + 11 clock cycles."""
    lines = [
        " ".join(
            [
                f"{INPUT_OFFSETS['clk_i']}:0",
                f"{INPUT_OFFSETS['rst_ni']}:0",
                f"{INPUT_OFFSETS['fault_enable_i']}:{fault_enable_i(parameters)}",
                f"{INPUT_OFFSETS['inject_port_b_i']}:0",
                f"{INPUT_OFFSETS['fault_bit_i']}:{fault_bit_i(parameters)}",
                f"{INPUT_OFFSETS['load_response_delay_i']}:{delay_i(parameters)}",
            ]
        )
    ]
    for cycle in range(11):
        rst = 1 if cycle >= 2 else 0
        lines.append(f"{INPUT_OFFSETS['clk_i']}:1 {INPUT_OFFSETS['rst_ni']}:{rst}")
        lines.append(f"{INPUT_OFFSETS['clk_i']}:0 {INPUT_OFFSETS['rst_ni']}:{rst}")
    return lines


def patch_script(parameters: Mapping[str, Any]) -> str:
    return "\n".join(single_state_patch(parameters)) + "\n"


def batch_patch_script(
    *,
    actions_by_point: Mapping[str, Mapping[str, Any]],
    group: Sequence[tuple[int, str, str, str]],
) -> tuple[str, int]:
    scripts = [
        single_state_patch(parameters(actions_by_point[point_id]))
        for _epoch_index, point_id, _revision, _purpose in group
    ]
    lines: list[str] = []
    for step_index in range(max(len(steps) for steps in scripts)):
        tokens: list[str] = []
        for state_index, steps in enumerate(scripts):
            if step_index >= len(steps):
                continue
            for token in steps[step_index].split():
                offset, value = token.split(":", 1)
                tokens.append(f"@{state_index}:{offset}:{value}")
        lines.append(" ".join(tokens))
    return "\n".join(lines) + "\n", len(lines)


def cpu_command(
    binary: Path, parameters: Mapping[str, Any], dump_state: Path | None = None
) -> list[str]:
    command = [str(binary)]
    if fault_enable_i(parameters) == 0:
        command.append("--no-fault")
    command.extend(["--fault-bit", str(fault_bit_i(parameters))])
    command.extend(["--load-response-delay", str(delay_i(parameters))])
    if dump_state is not None:
        command.extend(["--dump-state", str(dump_state)])
    return command


def cpu_observables(binary: Path, parameters: Mapping[str, Any], dump_state: Path) -> tuple[dict[str, int], int]:
    completed = subprocess.run(
        cpu_command(binary, parameters, dump_state),
        text=True,
        capture_output=True,
        check=False,
    )
    require_success(completed, "CPU point execution")
    match = RESULT_RE.search(completed.stdout)
    if match is None:
        raise RuntimeError(f"CPU result line missing:\n{completed.stdout}\n{completed.stderr}")
    values = {
        "done": int(match.group(1)),
        "oracle_violation": int(match.group(2)),
        "fault_seen": int(match.group(3)),
        "alert_seen": int(match.group(4)),
        "rf_read_enable": int(match.group(5)),
        "rf_wb_match": int(match.group(6)),
        "rf_write_wb": int(match.group(7)),
        "rf_ecc_error_id": int(match.group(8)),
        "instruction_valid_id": int(match.group(9)),
        "alert_major_internal": int(match.group(10)),
    }
    return values, len(single_state_patch(parameters))


def read_observables(image: bytes, base: int) -> dict[str, int]:
    return {name: image[base + offset] for name, offset in OBSERVABLE_OFFSETS.items()}


def gpu_observe_one(
    revision: Mapping[str, Any],
    parameters: Mapping[str, Any],
    out_path: Path,
    patch_path: Path,
) -> tuple[dict[str, int], int]:
    patch_path.write_text(patch_script(parameters), encoding="utf-8")
    completed = run_repo(
        [
            sys.executable,
            str(HYBRID_RUNNER),
            "--mdir",
            str(revision["gpu_mdir"]),
            "--nstates",
            "1",
            "--resident-steps",
            "--patch-script",
            str(patch_path),
            "--dump-state",
            str(out_path),
        ],
        env=revision["env"],
    )
    require_success(completed, "GPU point execution")
    image = out_path.read_bytes()
    if len(image) != revision["storage_size"]:
        raise RuntimeError(
            f"unexpected GPU state bytes={len(image)} storage={revision['storage_size']}"
        )
    return read_observables(image, 0), len(single_state_patch(parameters))


def batch_observables(image: bytes, state_count: int, storage_size: int) -> list[dict[str, int]]:
    if len(image) != storage_size * state_count:
        raise RuntimeError(f"unexpected batch dump bytes={len(image)} storage={storage_size}")
    return [
        read_observables(image, state_index * storage_size)
        for state_index in range(state_count)
    ]
