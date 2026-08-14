"""Low-level IO, compile, and point execution helpers for TL-UL #10818."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from compare_vl_hybrid_root_layout import probe_root_layout
from run_tlul10818_cpu_regression import REPO_ROOT
from run_tlul10818_gpu_equivalence import (
    CPU_DRIVER,
    HYBRID_RUNNER,
    OBSERVABLE_SUFFIXES,
    TOP,
    _base_verilator_command,
    _gpu_observables,
)
from tlul10818_boundary_schedule import boundary_patch_script_for_parameters


PROJECTION_KEYS = ("done", "d_data", "d_error", "intg_error", "oracle_violation")
RESULT_RE = re.compile(
    r"RESULT done=(\d+) oracle_violation=(\d+) d_data=([0-9a-fA-F]+) "
    r"d_error=(\d+) intg_error=(\d+) coverage=([0-9a-fA-F]+)"
)


def read_object(path: Path, label: str) -> dict[str, Any]:
    def reject_constant(token: str) -> None:
        raise ValueError(f"{label} contains non-finite JSON token {token}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_repo(command: Sequence[str], *, env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        env=dict(env) if env is not None else None,
        text=True,
        capture_output=True,
    )


def require_success(completed: subprocess.CompletedProcess[str], label: str) -> None:
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit {completed.returncode}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )


def patch_lines(offsets: Mapping[str, int], parameters: Mapping[str, Any]) -> list[list[str]]:
    script = boundary_patch_script_for_parameters(dict(offsets), parameters)
    return [line.split() for line in script.splitlines() if line.strip()]


def write_patch(path: Path, offsets: Mapping[str, int], parameters: Mapping[str, Any]) -> int:
    lines = patch_lines(offsets, parameters)
    path.write_text("\n".join(" ".join(line) for line in lines) + "\n", encoding="utf-8")
    return len(lines)


def cpu_command(binary: Path, parameters: Mapping[str, Any], dump_state: Path | None = None) -> list[str]:
    command = [str(binary)]
    if parameters["request_integrity"] == "malformed":
        command.append("--malformed")
    command.extend(["--backpressure-cycles", str(parameters["backpressure_cycles"])])
    command.extend(["--response-delay-cycles", str(parameters["response_delay_cycles"])])
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
    return (
        {
            "done": int(match.group(1)),
            "oracle_violation": int(match.group(2)),
            "d_data": int(match.group(3), 16),
            "d_error": int(match.group(4)),
            "intg_error": int(match.group(5)),
        },
        int(match.group(6), 16),
    )


def semantic_projection(values: Mapping[str, int]) -> dict[str, int]:
    return {key: int(values[key]) for key in PROJECTION_KEYS}


def gpu_observe_one(
    revision: Mapping[str, Any],
    parameters: Mapping[str, Any],
    out_path: Path,
    patch_path: Path,
) -> tuple[dict[str, int], int]:
    cycle_evals = write_patch(patch_path, revision["offsets"], parameters)
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
    return _gpu_observables(out_path, revision["offsets"]), cycle_evals


def layout_offsets(mdir: Path) -> dict[str, int]:
    fields = probe_root_layout(mdir)
    offsets: dict[str, int] = {}
    for semantic, suffix in OBSERVABLE_SUFFIXES.items():
        matches = [entry for entry in fields if str(entry["name"]).endswith(f"__DOT__{suffix}")]
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one generated field for {semantic}, got {len(matches)}")
        offsets[semantic] = int(matches[0]["offset"])
    for name in ("clk_i", "rst_ni", "start_i", "malformed_i", "d_backpressure_i", "response_valid_i"):
        matches = [entry for entry in fields if entry["name"] == name]
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one top input field {name}")
        offsets[name] = int(matches[0]["offset"])
    return offsets


def revision_sha(checkout: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    require_success(completed, f"git rev-parse {checkout}")
    return completed.stdout.strip()


def compile_revision(
    *,
    label: str,
    checkout: Path,
    expected_revision: str,
    verilator: Path,
    verilator_root: Path,
    work_dir: Path,
) -> dict[str, Any]:
    observed_revision = revision_sha(checkout)
    if observed_revision != expected_revision:
        raise ValueError(
            f"{label} checkout revision mismatch: expected {expected_revision}, got {observed_revision}"
        )
    revision_dir = work_dir / label
    gpu_mdir = revision_dir / "gpu_obj"
    cpu_mdir = revision_dir / "cpu_obj"
    revision_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["VERILATOR_ROOT"] = str(verilator_root)
    env["PYTHONPATH"] = str(REPO_ROOT / "src" / "tools")
    require_success(run_repo(_base_verilator_command(verilator, checkout, gpu_mdir), env=env), f"{label} GPU Verilator compile")
    require_success(
        run_repo(_base_verilator_command(verilator, checkout, cpu_mdir) + ["--exe", str(CPU_DRIVER), "--build"], env=env),
        f"{label} CPU Verilator build",
    )
    require_success(
        run_repo([sys.executable, str(REPO_ROOT / "src/tools/build_vl_gpu.py"), str(gpu_mdir), "--force"], env=env),
        f"{label} GPU sidecar build",
    )
    meta = read_object(gpu_mdir / "vl_batch_gpu.meta.json", f"{label} GPU metadata")
    storage_size = meta.get("storage_size")
    if isinstance(storage_size, bool) or not isinstance(storage_size, int) or storage_size <= 0:
        raise ValueError(f"{label} GPU storage_size is invalid")
    return {
        "label": label,
        "checkout": checkout,
        "revision": observed_revision,
        "revision_dir": revision_dir,
        "gpu_mdir": gpu_mdir,
        "cpu_binary": cpu_mdir / f"V{TOP}",
        "offsets": layout_offsets(gpu_mdir),
        "storage_size": storage_size,
        "env": env,
    }
