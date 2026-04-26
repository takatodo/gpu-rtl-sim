#!/usr/bin/env python3
"""Run the tlul_fifo_sync CPU baseline timing gate."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_GATE = REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_baseline.json"
DEFAULT_MDIR = REPO_ROOT / "artifacts" / "tlul_fifo_sync_obj_dir"
DEFAULT_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_cpu_baseline.json"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(path: Path, message: str) -> None:
    if not path.is_file():
        raise SystemExit(f"error: {message}: {path}")


def _run_probe_once(*, probe: Path, reset_cycles: int, post_reset_cycles: int) -> dict[str, object]:
    cmd = [
        str(probe),
        "--reset-cycles",
        str(reset_cycles),
        "--post-reset-cycles",
        str(post_reset_cycles),
    ]
    started = time.perf_counter()
    completed = subprocess.run(cmd, text=True, capture_output=True)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    parsed: dict[str, object] | None = None
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
    constructor_ok = bool(parsed and parsed.get("constructor_ok") is True)
    root_size = int(parsed.get("root_size", 0)) if parsed else 0
    return {
        "returncode": completed.returncode,
        "elapsed_ms": elapsed_ms,
        "constructor_ok": constructor_ok,
        "root_size": root_size,
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
    _require_file(gate_path, "CPU baseline gate config not found")
    probe = mdir / "tlul_slice_host_probe"
    meta_path = mdir / "vl_batch_gpu.meta.json"
    _require_file(probe, "tlul_slice_host_probe not found; run README host build first")
    _require_file(meta_path, "GPU meta not found; run README GPU build first")

    gate = _load_json(gate_path)
    meta = _load_json(meta_path)
    storage_size = int(meta["storage_size"])
    run_cfg = gate["runs"][0]
    reset_cycles = int(run_cfg["reset_cycles"])
    post_reset_cycles = int(run_cfg["post_reset_cycles"])
    reps = int(run_cfg["reps"])
    json_out.parent.mkdir(parents=True, exist_ok=True)

    reps_out = [
        _run_probe_once(
            probe=probe,
            reset_cycles=reset_cycles,
            post_reset_cycles=post_reset_cycles,
        )
        for _ in range(reps)
    ]
    elapsed = [float(rep["elapsed_ms"]) for rep in reps_out]
    all_passed = all(
        int(rep["returncode"]) == 0
        and bool(rep["constructor_ok"])
        and int(rep["root_size"]) == storage_size
        for rep in reps_out
    )
    report = {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if all_passed else "fail",
        "storage_size": storage_size,
        "reset_cycles": reset_cycles,
        "post_reset_cycles": post_reset_cycles,
        "reps": reps_out,
        "timing": {
            "rep_count": reps,
            "median_elapsed_ms": statistics.median(elapsed),
            "min_elapsed_ms": min(elapsed),
            "max_elapsed_ms": max(elapsed),
        },
        "acceptance": {
            "all_reps_passed": all_passed,
            "policy": gate["acceptance"],
        },
        "comparison_policy": gate["comparison_policy"],
    }
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {json_out.relative_to(REPO_ROOT)}")
    print(
        json.dumps(
            {
                "status": report["status"],
                "median_elapsed_ms": report["timing"]["median_elapsed_ms"],
                "rep_count": reps,
            },
            indent=2,
        )
    )
    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
