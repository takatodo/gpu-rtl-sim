"""Exact-loop CPU baseline helpers for the TL-UL FIFO sync gate."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from named_patch_lowering import resolve_patch_script_lines


REPO_ROOT = Path(__file__).resolve().parents[2]


def exact_loop_command(
    *,
    probe: Path,
    reset_cycles: int,
    post_reset_cycles: int,
    nstates: int,
    steps: int,
    dump_state: Path,
) -> list[str]:
    return [
        str(probe),
        "--reset-cycles",
        str(reset_cycles),
        "--post-reset-cycles",
        str(post_reset_cycles),
        "--repeat-states",
        str(nstates),
        "--repeat-eval-steps",
        str(steps),
        "--repeat-state-out",
        str(dump_state),
    ]


def write_patch_script_tmp(name: str, lines: list[str]) -> Path:
    fd, tmp_name = tempfile.mkstemp(prefix=f"{name}_", suffix=".patch_script")
    patch_script_tmp = Path(tmp_name)
    with open(fd, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))
        fp.write("\n")
    return patch_script_tmp


def exact_loop_patch_script(
    *,
    gate: dict[str, object],
    run_cfg: dict[str, object],
    mdir: Path,
) -> tuple[object, dict[str, object], Path | None]:
    patch_script_lines, lowering = resolve_patch_script_lines(gate=gate, run_cfg=run_cfg, mdir=mdir)
    if patch_script_lines is None:
        return patch_script_lines, lowering, None
    if not isinstance(patch_script_lines, list) or not all(isinstance(line, str) for line in patch_script_lines):
        raise SystemExit(f"error: {run_cfg['name']} patch_script_lines must be a list of strings")
    return patch_script_lines, lowering, write_patch_script_tmp(str(run_cfg["name"]), patch_script_lines)


def run_exact_loop_command(cmd: list[str], patch_script_tmp: Path | None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True)
    finally:
        if patch_script_tmp is not None:
            patch_script_tmp.unlink(missing_ok=True)


def exact_loop_probe_metrics(parsed: dict[str, object] | None) -> dict[str, object]:
    return {
        "elapsed_ms": float(parsed.get("elapsed_ms", 0.0)) if parsed else 0.0,
        "states_per_second": (
            float(parsed.get("state_steps_per_second", parsed.get("states_per_second", 0.0)))
            if parsed
            else None
        ),
        "constructor_ok": bool(parsed and parsed.get("constructor_ok") is True),
        "root_size": int(parsed.get("root_size", 0)) if parsed else 0,
    }


def exact_loop_result_payload(
    *,
    run_cfg: dict[str, object],
    nstates: int,
    steps: int,
    reset_cycles: int,
    post_reset_cycles: int,
    storage_size: int,
    dump_state: Path,
    patch_script_lines: object,
    lowering: dict[str, object],
    completed: subprocess.CompletedProcess[str],
    parsed: dict[str, object] | None,
) -> dict[str, object]:
    metrics = exact_loop_probe_metrics(parsed)
    expected_dump_bytes = storage_size * nstates
    dump_bytes = dump_state.stat().st_size if dump_state.is_file() else 0
    passed = (
        completed.returncode == 0
        and bool(metrics["constructor_ok"])
        and int(metrics["root_size"]) == storage_size
        and dump_bytes == expected_dump_bytes
    )
    return {
        "name": str(run_cfg["name"]),
        "nstates": nstates,
        "steps": steps,
        "reset_cycles": reset_cycles,
        "post_reset_cycles": post_reset_cycles,
        "returncode": completed.returncode,
        "patch_script_line_count": len(patch_script_lines) if isinstance(patch_script_lines, list) else 0,
        "patch_script_lowering": lowering,
        "elapsed_ms": metrics["elapsed_ms"],
        "states_per_second": metrics["states_per_second"],
        "constructor_ok": metrics["constructor_ok"],
        "root_size": metrics["root_size"],
        "cpu_final_state_dump": str(dump_state.relative_to(REPO_ROOT)),
        "dump_bytes": dump_bytes,
        "expected_dump_bytes": expected_dump_bytes,
        "dump_contract": "concat_root_storage_by_state",
        "throughput_unit": "state_steps_per_second",
        "passed": passed,
        "stdout_tail": completed.stdout.splitlines()[-20:],
        "stderr_tail": completed.stderr.splitlines()[-20:],
    }


def run_exact_loop_case(
    *,
    gate: dict[str, object],
    mdir: Path,
    probe: Path,
    run_cfg: dict[str, object],
    storage_size: int,
    dump_dir: Path,
    parse_probe_json,
) -> dict[str, object]:
    nstates = int(run_cfg["nstates"])
    steps = int(run_cfg["steps"])
    reset_cycles = int(run_cfg["reset_cycles"])
    post_reset_cycles = int(run_cfg["post_reset_cycles"])
    dump_state = dump_dir / f"{run_cfg['name']}_cpu_final_state.bin"
    cmd = exact_loop_command(
        probe=probe,
        reset_cycles=reset_cycles,
        post_reset_cycles=post_reset_cycles,
        nstates=nstates,
        steps=steps,
        dump_state=dump_state,
    )
    patch_script_lines, lowering, patch_script_tmp = exact_loop_patch_script(
        gate=gate,
        run_cfg=run_cfg,
        mdir=mdir,
    )
    if patch_script_tmp is not None:
        cmd.extend(["--patch-script", str(patch_script_tmp)])
    completed = run_exact_loop_command(cmd, patch_script_tmp)
    parsed = parse_probe_json(completed.stdout)
    return exact_loop_result_payload(
        run_cfg=run_cfg,
        nstates=nstates,
        steps=steps,
        reset_cycles=reset_cycles,
        post_reset_cycles=post_reset_cycles,
        storage_size=storage_size,
        dump_state=dump_state,
        patch_script_lines=patch_script_lines,
        lowering=lowering,
        completed=completed,
        parsed=parsed,
    )
