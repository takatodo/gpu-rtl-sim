#!/usr/bin/env python3
"""Aggregate scientific CIRCT CPU/GPU timing reports into hybrid advantage evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, int | float) else None


def _display_path(path: Path) -> str:
    return re.sub(r"/(home|tmp|Users|var|mnt|workspace|root)/[^\s\"']+", "<local-path>", path.as_posix())


def _shape_nstates(shape: str) -> int | None:
    head, sep, tail = shape.partition("x")
    return int(head) if sep and tail == "1" and head.isdigit() else None


def analyze_timing_report(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    median = report.get("median")
    if not isinstance(median, dict):
        raise ValueError(f"{path}: missing median object")
    e2e = _number(median.get("cpu_to_gpu_end_to_end_speedup"))
    kernel = _number(median.get("cpu_to_gpu_kernel_speedup"))
    shape = str(report.get("shape"))
    classes = []
    classes.append("gpu_end_to_end_favorable" if e2e is not None and e2e > 1.0 else "cpu_end_to_end_favorable")
    classes.append("gpu_kernel_favorable" if kernel is not None and kernel > 1.0 else "cpu_kernel_favorable")
    return {
        "source": _display_path(path),
        "candidate": report.get("candidate"),
        "shape": shape,
        "nstates": _shape_nstates(shape),
        "status": report.get("status"),
        "classifications": classes,
        "cpu_ms": _number(median.get("cpu_ms")),
        "gpu_end_to_end_ms": _number(median.get("gpu_end_to_end_ms")),
        "gpu_kernel_ms": _number(median.get("gpu_kernel_ms")),
        "cpu_to_gpu_end_to_end_speedup": e2e,
        "cpu_to_gpu_kernel_speedup": kernel,
        "inner_repeat": report.get("inner_repeat"),
    }


def aggregate(paths: list[Path]) -> dict[str, Any]:
    records = [analyze_timing_report(path, _load(path)) for path in paths]
    measured = [record for record in records if record.get("status") == "measured"]
    e2e_favorable = [record for record in measured if "gpu_end_to_end_favorable" in record["classifications"]]
    kernel_favorable = [record for record in measured if "gpu_kernel_favorable" in record["classifications"]]
    first_e2e = min(e2e_favorable, key=lambda r: r["nstates"] or 10**18) if e2e_favorable else None
    best_e2e = max(measured, key=lambda r: r["cpu_to_gpu_end_to_end_speedup"] or -1) if measured else None
    best_kernel = max(measured, key=lambda r: r["cpu_to_gpu_kernel_speedup"] or -1) if measured else None
    by_candidate = {}
    for candidate in sorted({str(record.get("candidate")) for record in measured}):
        group = [record for record in measured if record.get("candidate") == candidate]
        group_e2e = [record for record in group if "gpu_end_to_end_favorable" in record["classifications"]]
        first = min(group_e2e, key=lambda r: r["nstates"] or 10**18) if group_e2e else None
        by_candidate[candidate] = {
            "record_count": len(group),
            "gpu_end_to_end_favorable": len(group_e2e),
            "cpu_end_to_end_favorable": len(group) - len(group_e2e),
            "gpu_kernel_favorable": sum(1 for record in group if "gpu_kernel_favorable" in record["classifications"]),
            "first_gpu_end_to_end_favorable_shape": first["shape"] if first else None,
            "best_gpu_end_to_end": max(group, key=lambda r: r["cpu_to_gpu_end_to_end_speedup"] or -1),
        }
    return {
        "schema_version": 1,
        "surface": "scientific_circt_hybrid_advantage",
        "status": "analyzed" if measured else "no_measured_reports",
        "record_count": len(records),
        "counts": {
            "measured": len(measured),
            "gpu_end_to_end_favorable": len(e2e_favorable),
            "cpu_end_to_end_favorable": len(measured) - len(e2e_favorable),
            "gpu_kernel_favorable": len(kernel_favorable),
        },
        "first_gpu_end_to_end_favorable_shape": first_e2e["shape"] if first_e2e else None,
        "best_gpu_end_to_end": best_e2e,
        "best_gpu_kernel": best_kernel,
        "by_candidate": by_candidate,
        "records": records,
        "hybrid_recommendation": {
            "recommended_action": (
                "use_gpu_for_state_parallel_batches_at_or_above_first_favorable_shape"
                if first_e2e
                else "keep_cpu_end_to_end_until_larger_batch_or_more_arithmetic_intensity"
            ),
            "reason": "end_to_end_speedup_includes_launch_and_transfer_overhead",
        },
        "non_claims": [
            "not_a_general_rtl_speedup_claim",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path)
    args = parser.parse_args(argv)
    result = aggregate(args.report)
    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out")
            return 2
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
