from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

from named_patch_lowering import resolve_patch_script_lines
from run_tlul_fifo_sync_scaling_timing import (
    case_result_payload,
    parse_timing_metrics,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
RUN_VL_HYBRID = SCRIPT_DIR / "run_vl_hybrid.py"


def _resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def patch_script_logical_steps(lines: list[str]) -> int:
    total = 0
    repeat_stack: list[tuple[int, int]] = []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if parts[0] == "@repeat-seq":
            if len(parts) != 2:
                raise SystemExit("error: @repeat-seq requires exactly one count")
            repeat_stack.append((int(parts[1], 0), 0))
        elif parts[0] == "@end-repeat-seq":
            if not repeat_stack:
                raise SystemExit("error: @end-repeat-seq without @repeat-seq")
            repeat_count, body_steps = repeat_stack.pop()
            expanded = repeat_count * body_steps
            if repeat_stack:
                parent_count, parent_steps = repeat_stack.pop()
                repeat_stack.append((parent_count, parent_steps + expanded))
            else:
                total += expanded
        elif repeat_stack:
            repeat_count, body_steps = repeat_stack.pop()
            repeat_stack.append((repeat_count, body_steps + 1))
        else:
            total += 1
    if repeat_stack:
        raise SystemExit("error: unterminated @repeat-seq")
    return total


def write_patch_script_tmp(name: str, lines: list[str]) -> Path:
    fd, tmp_name = tempfile.mkstemp(prefix=f"{name}_", suffix=".patch_script")
    patch_script_tmp = Path(tmp_name)
    with open(fd, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))
        fp.write("\n")
    return patch_script_tmp


def prepare_patch_script(
    *,
    name: str,
    steps: int,
    patch_script_lines: object,
) -> tuple[int, Path | None]:
    if patch_script_lines is None:
        return steps, None
    if not isinstance(patch_script_lines, list) or not all(isinstance(line, str) for line in patch_script_lines):
        raise SystemExit(f"error: {name} patch_script_lines must be a list of strings")
    return patch_script_logical_steps(patch_script_lines), write_patch_script_tmp(name, patch_script_lines)


def validated_case_timing(name: str, run: dict[str, object]) -> tuple[int, int]:
    timing_repeats = int(run.get("timing_repeats", 1))
    if timing_repeats < 1:
        raise SystemExit(f"error: {name} timing_repeats must be >= 1")
    block_size = int(run.get("block_size", 256))
    if block_size < 1:
        raise SystemExit(f"error: {name} block_size must be >= 1")
    return timing_repeats, block_size


def case_command(
    *,
    mdir: Path,
    dump_state: Path,
    nstates: int,
    steps: int,
    build_result: dict[str, object] | None,
    resident_steps: bool,
    timing_repeats: int,
    block_size: int,
    block_size_was_requested: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        str(RUN_VL_HYBRID),
        "--mdir",
        str(mdir),
        "--nstates",
        str(nstates),
        "--steps",
        str(steps),
        "--dump-state",
        str(dump_state),
    ]
    if build_result is not None:
        cmd.extend(["--cubins", str(_resolve_repo_path(str(build_result["cubin"])))])
    if resident_steps:
        cmd.append("--resident-steps")
    if timing_repeats > 1:
        cmd.extend(["--timing-repeats", str(timing_repeats)])
    if block_size_was_requested:
        cmd.extend(["--block-size", str(block_size)])
    return cmd


def run_case_command(cmd: list[str], patch_script_tmp: Path | None) -> tuple[subprocess.CompletedProcess[str], float]:
    try:
        started = time.perf_counter()
        completed = subprocess.run(cmd, text=True, capture_output=True)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    finally:
        if patch_script_tmp is not None:
            patch_script_tmp.unlink(missing_ok=True)
    return completed, elapsed_ms


def case_command_and_patch(
    *,
    name: str,
    mdir: Path,
    dump_state: Path,
    nstates: int,
    steps: int,
    build_result: dict[str, object] | None,
    resident_steps: bool,
    timing_repeats: int,
    block_size: int,
    block_size_was_requested: bool,
    patch_script_lines: object,
) -> tuple[list[str], int, Path | None]:
    effective_steps, patch_script_tmp = prepare_patch_script(
        name=name,
        steps=steps,
        patch_script_lines=patch_script_lines,
    )
    cmd = case_command(
        mdir=mdir,
        dump_state=dump_state,
        nstates=nstates,
        steps=steps,
        build_result=build_result,
        resident_steps=resident_steps,
        timing_repeats=timing_repeats,
        block_size=block_size,
        block_size_was_requested=block_size_was_requested,
    )
    if patch_script_tmp is not None:
        cmd.extend(["--patch-script", str(patch_script_tmp)])
    return cmd, effective_steps, patch_script_tmp


def _case_build_result(
    *,
    name: str,
    run: dict[str, object],
    builds_by_name: dict[str, dict[str, object]] | None,
) -> tuple[object, dict[str, object] | None]:
    build_name = run.get("build")
    if build_name is None:
        return None, None
    if builds_by_name is None or str(build_name) not in builds_by_name:
        raise SystemExit(f"error: {name} references unknown build: {build_name}")
    return build_name, builds_by_name[str(build_name)]


def _run_case(
    *,
    gate: dict[str, object],
    mdir: Path,
    run: dict[str, object],
    storage_size: int,
    dump_dir: Path,
    builds_by_name: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    name = str(run["name"])
    nstates = int(run["nstates"])
    steps = int(run["steps"])
    resident_steps = bool(run.get("resident_steps", False))
    patch_script_lines, lowering = resolve_patch_script_lines(gate=gate, run_cfg=run, mdir=mdir)
    dump_state = dump_dir / f"{name}_state.bin"
    build_name, build_result = _case_build_result(name=name, run=run, builds_by_name=builds_by_name)
    timing_repeats, block_size = validated_case_timing(name, run)
    cmd, effective_steps, patch_script_tmp = case_command_and_patch(
        name=name,
        mdir=mdir,
        dump_state=dump_state,
        nstates=nstates,
        steps=steps,
        build_result=build_result,
        resident_steps=resident_steps,
        timing_repeats=timing_repeats,
        block_size=block_size,
        block_size_was_requested="block_size" in run,
        patch_script_lines=patch_script_lines,
    )
    completed, elapsed_ms = run_case_command(cmd, patch_script_tmp)
    expected_dump_bytes = storage_size * nstates
    dump_bytes = dump_state.stat().st_size if dump_state.is_file() else 0
    passed = completed.returncode == 0 and dump_bytes == expected_dump_bytes
    timing_metrics = parse_timing_metrics(completed.stdout)
    return case_result_payload(
        repo_root=REPO_ROOT,
        run=run,
        build_name=build_name,
        build_result=build_result,
        nstates=nstates,
        requested_steps=steps,
        effective_steps=effective_steps,
        resident_steps=resident_steps,
        timing_repeats=timing_repeats,
        block_size=block_size,
        patch_script_lines=patch_script_lines,
        lowering=lowering,
        completed=completed,
        elapsed_ms=elapsed_ms,
        dump_state=dump_state,
        dump_bytes=dump_bytes,
        expected_dump_bytes=expected_dump_bytes,
        passed=passed,
        timing_metrics=timing_metrics,
    )
