#!/usr/bin/env python3
"""Run the tlul_fifo_sync scaling validation gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from named_patch_lowering import resolve_patch_script_lines


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
RUN_VL_HYBRID = SCRIPT_DIR / "run_vl_hybrid.py"
DEFAULT_GATE = REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync.json"
DEFAULT_MDIR = REPO_ROOT / "artifacts" / "tlul_fifo_sync_obj_dir"
DEFAULT_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_scaling_validation.json"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(path: Path, message: str) -> None:
    if not path.is_file():
        raise SystemExit(f"error: {message}: {path}")


def _patch_script_logical_steps(lines: list[str]) -> int:
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
        else:
            if repeat_stack:
                repeat_count, body_steps = repeat_stack.pop()
                repeat_stack.append((repeat_count, body_steps + 1))
            else:
                total += 1
    if repeat_stack:
        raise SystemExit("error: unterminated @repeat-seq")
    return total


def _run_case(
    *,
    gate: dict[str, object],
    mdir: Path,
    run: dict[str, object],
    storage_size: int,
    dump_dir: Path,
) -> dict[str, object]:
    name = str(run["name"])
    nstates = int(run["nstates"])
    steps = int(run["steps"])
    resident_steps = bool(run.get("resident_steps", False))
    patch_script_lines, lowering = resolve_patch_script_lines(gate=gate, run_cfg=run, mdir=mdir)
    dump_state = dump_dir / f"{name}_state.bin"
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
    if resident_steps:
        cmd.append("--resident-steps")
    effective_steps = steps
    patch_script_tmp: Path | None = None
    if patch_script_lines is not None:
        if not isinstance(patch_script_lines, list) or not all(
            isinstance(line, str) for line in patch_script_lines
        ):
            raise SystemExit(f"error: {name} patch_script_lines must be a list of strings")
        effective_steps = _patch_script_logical_steps(patch_script_lines)
        fd, tmp_name = tempfile.mkstemp(prefix=f"{name}_", suffix=".patch_script")
        patch_script_tmp = Path(tmp_name)
        with open(fd, "w", encoding="utf-8") as fp:
            fp.write("\n".join(patch_script_lines))
            fp.write("\n")
        cmd.extend(["--patch-script", str(patch_script_tmp)])
    try:
        started = time.perf_counter()
        completed = subprocess.run(cmd, text=True, capture_output=True)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    finally:
        if patch_script_tmp is not None:
            patch_script_tmp.unlink(missing_ok=True)
    expected_dump_bytes = storage_size * nstates
    dump_bytes = dump_state.stat().st_size if dump_state.is_file() else 0
    passed = completed.returncode == 0 and dump_bytes == expected_dump_bytes
    states_per_second = (
        (nstates * effective_steps) / (elapsed_ms / 1000.0) if elapsed_ms > 0 else None
    )
    return {
        "name": name,
        "nstates": nstates,
        "steps": effective_steps,
        "requested_steps": steps,
        "resident_steps": resident_steps,
        "patch_script_line_count": len(patch_script_lines) if isinstance(patch_script_lines, list) else 0,
        "patch_script_lowering": lowering,
        "returncode": completed.returncode,
        "elapsed_ms": elapsed_ms,
        "states_per_second": states_per_second,
        "dump_state": str(dump_state.relative_to(REPO_ROOT)),
        "dump_bytes": dump_bytes,
        "expected_dump_bytes": expected_dump_bytes,
        "passed": passed,
        "stdout_tail": completed.stdout.splitlines()[-20:],
        "stderr_tail": completed.stderr.splitlines()[-20:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--mdir", type=Path, default=DEFAULT_MDIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    gate_path = args.gate.resolve()
    mdir = args.mdir.resolve()
    json_out = args.json_out.resolve()
    _require_file(gate_path, "gate config not found")
    _require_file(RUN_VL_HYBRID, "run_vl_hybrid.py not found")
    meta_path = mdir / "vl_batch_gpu.meta.json"
    _require_file(meta_path, "GPU meta not found; run README build flow first")

    gate = _load_json(gate_path)
    meta = _load_json(meta_path)
    storage_size = int(meta["storage_size"])
    dump_dir = mdir / "scaling_validation"
    dump_dir.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)

    results = [
        _run_case(gate=gate, mdir=mdir, run=run, storage_size=storage_size, dump_dir=dump_dir)
        for run in gate["runs"]
    ]
    passed = all(bool(result["passed"]) for result in results)
    report = {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if passed else "fail",
        "storage_size": storage_size,
        "resident_steps": any(bool(run.get("resident_steps", False)) for run in gate["runs"]),
        "runs": results,
        "acceptance": {
            "all_required_runs_passed": passed,
            "correctness_policy": gate.get("correctness_policy"),
            "performance_policy": gate.get("performance_policy"),
        },
        "non_claims": gate.get("performance_policy", gate.get("correctness_policy", {})).get(
            "non_claims", []
        ),
    }
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {json_out.relative_to(REPO_ROOT)}")
    print(json.dumps({"status": report["status"], "runs": results}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
