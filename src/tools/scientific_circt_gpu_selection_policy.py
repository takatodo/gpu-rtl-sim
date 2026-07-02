#!/usr/bin/env python3
"""Compile-time selection policy for measured scientific CIRCT GPU candidates."""

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


def _shape_nstates(shape: str | None) -> int | None:
    if not shape:
        return None
    match = re.fullmatch(r"(\d+)x1", shape)
    return int(match.group(1)) if match else None


def _candidate_policy(candidate: str, payload: dict[str, Any]) -> dict[str, Any]:
    first_shape = payload.get("first_gpu_end_to_end_favorable_shape")
    min_nstates = _shape_nstates(str(first_shape)) if first_shape else None
    kernel_ok = int(payload.get("gpu_kernel_favorable") or 0) == int(payload.get("record_count") or -1)
    action = "select_gpu_state_parallel" if min_nstates and kernel_ok else "measure_more_before_gpu"
    return {
        "candidate": candidate,
        "recommended_action": action,
        "min_gpu_nstates": min_nstates,
        "required_steps": 1,
        "first_gpu_end_to_end_favorable_shape": first_shape,
        "kernel_favorable_all_measured_shapes": kernel_ok,
        "evidence_record_count": payload.get("record_count"),
        "reason": "requires measured end-to-end favorable boundary and kernel-favorable measured shapes",
    }


def _variant_decision(variant: dict[str, Any]) -> dict[str, Any]:
    comparison = variant.get("comparison") if isinstance(variant.get("comparison"), dict) else {}
    candidate = str(variant.get("candidate") or "unknown")
    name = str(variant.get("variant") or "unknown")
    speedup_improved = comparison.get("speedup_improved") is True
    output_equal = variant.get("cpu_vs_gpu_output_equal") is True
    checksum_equal = variant.get("cpu_vs_gpu_control_checksum_equal") is True
    if speedup_improved and output_equal and checksum_equal:
        action = "promote_to_hls_gpu"
    elif output_equal and checksum_equal:
        action = "keep_baseline_gpu_or_cpu"
    else:
        action = "reject_variant"
    return {
        "candidate": candidate,
        "source_variant": name,
        "shape": variant.get("shape"),
        "recommended_action": action,
        "baseline_speedup": comparison.get("baseline_speedup"),
        "variant_speedup": comparison.get("variant_speedup"),
        "speedup_delta": comparison.get("speedup_delta"),
        "speedup_improved": speedup_improved,
        "cpu_vs_gpu_output_equal": output_equal,
        "cpu_vs_gpu_control_checksum_equal": checksum_equal,
        "reason": "promote only when CPU/GPU equality holds and measured variant speedup exceeds baseline",
    }


def _variant_decisions(reports: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for report in reports or []:
        variants = report.get("variants")
        if isinstance(variants, list):
            decisions.extend(_variant_decision(item) for item in variants if isinstance(item, dict))
        elif report.get("variant"):
            decisions.append(_variant_decision(report))
    return decisions


def build_policy(summary: dict[str, Any], hls_variant_reports: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    by_candidate = summary.get("by_candidate")
    if not isinstance(by_candidate, dict):
        raise ValueError("summary missing by_candidate object")
    candidates = {
        str(candidate): _candidate_policy(str(candidate), payload)
        for candidate, payload in by_candidate.items()
        if isinstance(payload, dict)
    }
    gpu_ready = [name for name, policy in candidates.items() if policy["recommended_action"] == "select_gpu_state_parallel"]
    source_variant_decisions = _variant_decisions(hls_variant_reports)
    return {
        "schema_version": 1,
        "surface": "scientific_circt_gpu_selection_policy",
        "status": "policy_ready" if gpu_ready else "needs_more_measurement",
        "source_surface": summary.get("surface"),
        "default_policy": {
            "unmeasured_candidate_action": "measure_before_gpu",
            "below_min_nstates_action": "select_cpu",
            "transfer_and_launch_overhead_included": True,
        },
        "candidates": candidates,
        "source_variants": source_variant_decisions,
        "source_variant_ready_count": sum(
            1 for item in source_variant_decisions if item["recommended_action"] == "promote_to_hls_gpu"
        ),
        "gpu_ready_candidate_count": len(gpu_ready),
        "non_claims": [
            "not_a_general_rtl_speedup_claim",
            "not_rtlmeter_evidence",
            "not_automatic_partitioning",
            "not_automatic_hls_rewrite",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--hls-variant-report", type=Path, action="append", default=[])
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path)
    args = parser.parse_args(argv)
    report = build_policy(_load(args.summary), [_load(path) for path in args.hls_variant_report])
    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out")
            return 2
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
