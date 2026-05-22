#!/usr/bin/env python3
"""Run the tlul_fifo_sync scaling validation gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_tlul_fifo_sync_scaling_cases import (
    DEFAULT_GATE,
    DEFAULT_MDIR,
    DEFAULT_REPORT,
    REPO_ROOT,
    RUN_VL_HYBRID,
    _load_json,
    _require_file,
    _run_builds,
    _run_gate_cases,
    _scaling_report,
)
from run_tlul_fifo_sync_scaling_timing import (
    format_gpu_event_timing,
    format_gpu_event_timing_repeat,
    parse_timing_metrics,
)


_parse_timing_metrics = parse_timing_metrics
_format_gpu_event_timing = format_gpu_event_timing
_format_gpu_event_timing_repeat = format_gpu_event_timing_repeat


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--mdir", type=Path, default=DEFAULT_MDIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_REPORT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
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

    build_results, builds_by_name, builds_passed = _run_builds(gate)
    gate_runs, results, runs_passed = _run_gate_cases(
        gate=gate,
        mdir=mdir,
        storage_size=storage_size,
        dump_dir=dump_dir,
        builds_by_name=builds_by_name,
    )
    report = _scaling_report(
        gate=gate,
        storage_size=storage_size,
        gate_runs=gate_runs,
        build_results=build_results,
        results=results,
        builds_passed=builds_passed,
        runs_passed=runs_passed,
    )
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {json_out.relative_to(REPO_ROOT)}")
    print(json.dumps({"status": report["status"], "runs": results}, indent=2))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
