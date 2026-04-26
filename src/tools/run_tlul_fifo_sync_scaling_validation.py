#!/usr/bin/env python3
"""Run the tlul_fifo_sync scaling validation gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


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


def _run_case(
    *,
    mdir: Path,
    run: dict[str, object],
    storage_size: int,
    dump_dir: Path,
) -> dict[str, object]:
    name = str(run["name"])
    nstates = int(run["nstates"])
    steps = int(run["steps"])
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
    started = time.perf_counter()
    completed = subprocess.run(cmd, text=True, capture_output=True)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    expected_dump_bytes = storage_size * nstates
    dump_bytes = dump_state.stat().st_size if dump_state.is_file() else 0
    passed = completed.returncode == 0 and dump_bytes == expected_dump_bytes
    states_per_second = (nstates * steps) / (elapsed_ms / 1000.0) if elapsed_ms > 0 else None
    return {
        "name": name,
        "nstates": nstates,
        "steps": steps,
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
        _run_case(mdir=mdir, run=run, storage_size=storage_size, dump_dir=dump_dir)
        for run in gate["runs"]
    ]
    passed = all(bool(result["passed"]) for result in results)
    report = {
        "schema_version": 1,
        "gate": gate["gate"],
        "target": gate["target"],
        "status": "ok" if passed else "fail",
        "storage_size": storage_size,
        "runs": results,
        "acceptance": {
            "all_required_runs_passed": passed,
            "correctness_policy": gate["correctness_policy"],
            "performance_policy": gate["performance_policy"],
        },
        "non_claims": gate["performance_policy"]["non_claims"],
    }
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {json_out.relative_to(REPO_ROOT)}")
    print(json.dumps({"status": report["status"], "runs": results}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
