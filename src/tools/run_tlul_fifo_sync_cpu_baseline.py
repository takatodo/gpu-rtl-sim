#!/usr/bin/env python3
"""Run the tlul_fifo_sync CPU baseline timing gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_tlul_fifo_sync_cpu_runner import run_selected_gate


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_GATE = REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_baseline.json"
DEFAULT_MULTISTATE_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_multistate_baseline.json"
)
DEFAULT_EXACT_LOOP_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_fifo_sync_cpu_exact_loop_baseline.json"
)
DEFAULT_MDIR = REPO_ROOT / "artifacts" / "tlul_fifo_sync_obj_dir"
DEFAULT_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_cpu_baseline.json"
DEFAULT_MULTISTATE_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_cpu_multistate_baseline.json"
DEFAULT_EXACT_LOOP_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_cpu_exact_loop_baseline.json"
DEFAULT_GPU_SCALING_REPORT = REPO_ROOT / "reports" / "tlul_fifo_sync_scaling_validation.json"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(path: Path, message: str) -> None:
    if not path.is_file():
        raise SystemExit(f"error: {message}: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--mdir", type=Path, default=DEFAULT_MDIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--multi-state", action="store_true")
    parser.add_argument("--exact-loop", action="store_true")
    parser.add_argument("--gpu-scaling-report", type=Path, default=DEFAULT_GPU_SCALING_REPORT)
    parser.add_argument(
        "--probe",
        type=Path,
        help="Host probe binary; defaults to <mdir>/tlul_slice_host_probe for existing TL-UL flows",
    )
    return parser


def _resolved_gate_path(args: argparse.Namespace) -> Path:
    if args.multi_state and args.exact_loop:
        raise SystemExit("error: choose only one of --multi-state or --exact-loop")
    if args.exact_loop and args.gate == DEFAULT_GATE:
        return DEFAULT_EXACT_LOOP_GATE.resolve()
    if args.multi_state and args.gate == DEFAULT_GATE:
        return DEFAULT_MULTISTATE_GATE.resolve()
    return args.gate.resolve()


def _resolved_json_out(args: argparse.Namespace) -> Path:
    if args.exact_loop and args.json_out == DEFAULT_REPORT:
        return DEFAULT_EXACT_LOOP_REPORT.resolve()
    if args.multi_state and args.json_out == DEFAULT_REPORT:
        return DEFAULT_MULTISTATE_REPORT.resolve()
    return args.json_out.resolve()


def main() -> None:
    args = build_parser().parse_args()
    gate_path = _resolved_gate_path(args)
    mdir = args.mdir.resolve()
    json_out = _resolved_json_out(args)
    gpu_scaling_report = args.gpu_scaling_report.resolve()
    _require_file(gate_path, "CPU baseline gate config not found")
    probe = args.probe.resolve() if args.probe else mdir / "tlul_slice_host_probe"
    meta_path = mdir / "vl_batch_gpu.meta.json"
    _require_file(probe, "host probe not found; run the matching README host build first")
    _require_file(meta_path, "GPU meta not found; run README GPU build first")

    gate = _load_json(gate_path)
    meta = _load_json(meta_path)
    storage_size = int(meta["storage_size"])
    json_out.parent.mkdir(parents=True, exist_ok=True)

    report = run_selected_gate(
        exact_loop=args.exact_loop,
        multi_state=args.multi_state,
        gate=gate,
        mdir=mdir,
        probe=probe,
        storage_size=storage_size,
        gpu_scaling_report=gpu_scaling_report,
        load_json=_load_json,
    )
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {json_out.relative_to(REPO_ROOT)}")
    print(json.dumps({"status": report["status"], "gate": report["gate"]}, indent=2))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
