#!/usr/bin/env python3
"""Build an all-candidate CPU/GPU dispatch matrix from the hybrid protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scientific_circt_hybrid_protocol import _load, decide

REPORT = Path("reports/scientific_circt_hybrid_dispatch_matrix.json")
DEFAULT_NSTATES = (64, 256, 1024)
SUMMARY = Path("reports/scientific_circt_testbench_hybrid_advantage.json")


def _shape_key(nstates: int, steps: int) -> str:
    return f"{nstates}x{steps}"


def _validate_points(nstates_points: list[int], steps: int) -> None:
    if steps <= 0:
        raise ValueError("steps must be positive")
    if not nstates_points:
        raise ValueError("at least one --nstates value is required")
    for nstates in nstates_points:
        if nstates <= 0:
            raise ValueError("--nstates values must be positive")


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, int | float) else None


def _evidence_by_candidate_shape(summary: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    if summary is None:
        return {}
    records = summary.get("records")
    if not isinstance(records, list):
        raise ValueError("summary missing records array")
    evidence = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        candidate = record.get("candidate")
        shape = record.get("shape")
        if not isinstance(candidate, str) or not isinstance(shape, str):
            continue
        evidence[(candidate, shape)] = {
            "status": record.get("status"),
            "source": record.get("source"),
            "classifications": record.get("classifications", []),
            "cpu_ms": record.get("cpu_ms"),
            "gpu_end_to_end_ms": record.get("gpu_end_to_end_ms"),
            "gpu_kernel_ms": record.get("gpu_kernel_ms"),
            "cpu_to_gpu_end_to_end_speedup": record.get("cpu_to_gpu_end_to_end_speedup"),
            "cpu_to_gpu_kernel_speedup": record.get("cpu_to_gpu_kernel_speedup"),
            "inner_repeat": record.get("inner_repeat"),
        }
    return evidence


def _ranked_runtime_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gpu_rows = [record for record in records if record["decision"] == "select_gpu_state_parallel"]
    ranked = sorted(
        gpu_rows,
        key=lambda record: (
            _number(record["timing_evidence"].get("cpu_to_gpu_end_to_end_speedup")) or -1.0,
            _number(record["timing_evidence"].get("cpu_to_gpu_kernel_speedup")) or -1.0,
            record["candidate"],
            record["shape"],
        ),
        reverse=True,
    )
    queue = []
    for rank, record in enumerate(ranked, start=1):
        timing = record["timing_evidence"]
        queue.append(
            {
                "rank": rank,
                "candidate": record["candidate"],
                "shape": record["shape"],
                "nstates": record["nstates"],
                "steps": record["steps"],
                "gpu_subsystem": record.get("gpu_subsystem"),
                "cpu_owner": record.get("cpu_owner"),
                "cpu_to_gpu_end_to_end_speedup": timing.get("cpu_to_gpu_end_to_end_speedup"),
                "cpu_to_gpu_kernel_speedup": timing.get("cpu_to_gpu_kernel_speedup"),
                "cpu_ms": timing.get("cpu_ms"),
                "gpu_end_to_end_ms": timing.get("gpu_end_to_end_ms"),
                "gpu_kernel_ms": timing.get("gpu_kernel_ms"),
                "next_required_evidence": (
                    "broader_hybrid_runtime_entrypoint_with_amortized_integration_timing"
                ),
            }
        )
    return queue


def _ranked_source_variant_runtime_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    promoted = [record for record in records if record["decision"] == "promote_to_hls_gpu"]
    ranked = sorted(
        promoted,
        key=lambda record: (
            _number(record.get("variant_speedup")) or -1.0,
            _number(record.get("speedup_delta")) or -1.0,
            record["candidate"],
            record["source_variant"],
        ),
        reverse=True,
    )
    queue = []
    for rank, record in enumerate(ranked, start=1):
        queue.append(
            {
                "rank": rank,
                "candidate": record["candidate"],
                "source_variant": record["source_variant"],
                "shape": record["shape"],
                "nstates": record["nstates"],
                "steps": record["steps"],
                "gpu_subsystem": record.get("gpu_subsystem"),
                "cpu_owner": record.get("cpu_owner"),
                "baseline_speedup": record.get("baseline_speedup"),
                "variant_speedup": record.get("variant_speedup"),
                "speedup_delta": record.get("speedup_delta"),
                "next_required_evidence": "runtime_handoff_boundary_with_amortized_integration_timing",
            }
        )
    return queue


def _select_next_source_variant_runtime_boundary(queue: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not queue:
        return None
    inference = [
        item for item in queue if item["candidate"] == "microgpt_inference_slice"
    ]
    if inference:
        selected = dict(inference[0])
        selected["selection_reason"] = (
            "best promoted fuller-slice boundary after attention-head runtime evidence; "
            "MLP is slightly faster but less representative of token-loop/cache handoff"
        )
        return selected
    selected = dict(queue[0])
    selected["selection_reason"] = "highest promoted source-variant speedup"
    return selected


def build_matrix(
    protocol: dict[str, Any],
    nstates_points: list[int],
    steps: int = 1,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_points(nstates_points, steps)
    candidates = protocol.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("protocol missing candidates object")

    evidence = _evidence_by_candidate_shape(summary)
    records: list[dict[str, Any]] = []
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    by_shape: dict[str, dict[str, int]] = {
        _shape_key(nstates, steps): {"select_gpu_state_parallel": 0, "select_cpu": 0}
        for nstates in nstates_points
    }

    for candidate in sorted(candidates):
        rows: list[dict[str, Any]] = []
        for nstates in nstates_points:
            decision = decide(protocol, str(candidate), nstates, steps)
            shape = _shape_key(nstates, steps)
            timing = evidence.get((str(candidate), shape))
            row = {
                "candidate": str(candidate),
                "shape": shape,
                "nstates": nstates,
                "steps": steps,
                "decision": decision["decision"],
                "reason": decision["reason"],
                "fallback_used": decision["fallback_used"],
                "min_gpu_nstates": decision.get("min_gpu_nstates"),
                "gpu_subsystem": decision.get("gpu_subsystem"),
                "cpu_owner": decision.get("cpu_owner"),
                "timing_evidence": timing or {"status": "not_attached"},
            }
            rows.append(row)
            records.append(row)
            by_shape[row["shape"]][row["decision"]] += 1
        by_candidate[str(candidate)] = rows

    source_variants = protocol.get("source_variants", {})
    if not isinstance(source_variants, dict):
        raise ValueError("protocol source_variants must be an object when present")
    source_variant_records: list[dict[str, Any]] = []
    by_source_variant: dict[str, list[dict[str, Any]]] = {}
    by_source_variant_shape: dict[str, dict[str, int]] = {
        _shape_key(nstates, steps): {
            "promote_to_hls_gpu": 0,
            "keep_baseline_gpu_or_cpu": 0,
            "select_cpu": 0,
        }
        for nstates in nstates_points
    }
    for source_variant in sorted(source_variants):
        payload = source_variants[source_variant]
        if not isinstance(payload, dict):
            continue
        candidate = payload.get("candidate")
        if not isinstance(candidate, str):
            continue
        rows = []
        for nstates in nstates_points:
            decision = decide(protocol, candidate, nstates, steps, str(source_variant))
            shape = _shape_key(nstates, steps)
            row = {
                "candidate": candidate,
                "source_variant": str(source_variant),
                "shape": shape,
                "measured_policy_shape": decision.get("shape"),
                "nstates": nstates,
                "steps": steps,
                "decision": decision["decision"],
                "reason": decision["reason"],
                "fallback_used": decision["fallback_used"],
                "min_gpu_nstates": decision.get("min_gpu_nstates"),
                "gpu_subsystem": decision.get("gpu_subsystem"),
                "cpu_owner": decision.get("cpu_owner"),
                "baseline_speedup": decision.get("baseline_speedup"),
                "variant_speedup": decision.get("variant_speedup"),
                "speedup_delta": decision.get("speedup_delta"),
            }
            rows.append(row)
            source_variant_records.append(row)
            by_source_variant_shape[row["shape"]][row["decision"]] += 1
        by_source_variant[str(source_variant)] = rows

    gpu_count = sum(1 for record in records if record["decision"] == "select_gpu_state_parallel")
    cpu_count = sum(1 for record in records if record["decision"] == "select_cpu")
    source_variant_promote_count = sum(
        1 for record in source_variant_records if record["decision"] == "promote_to_hls_gpu"
    )
    source_variant_keep_baseline_count = sum(
        1 for record in source_variant_records if record["decision"] == "keep_baseline_gpu_or_cpu"
    )
    source_variant_select_cpu_count = sum(
        1 for record in source_variant_records if record["decision"] == "select_cpu"
    )
    shape_points = [_shape_key(nstates, steps) for nstates in nstates_points]
    runtime_queue = _ranked_runtime_queue(records)
    source_variant_queue = _ranked_source_variant_runtime_queue(source_variant_records)
    next_source_variant_boundary = _select_next_source_variant_runtime_boundary(source_variant_queue)
    return {
        "schema_version": 1,
        "surface": "scientific_circt_hybrid_dispatch_matrix",
        "status": "matrix_ready" if records else "matrix_empty",
        "source_surface": protocol.get("surface"),
        "protocol_status": protocol.get("status"),
        "evidence_source_surface": summary.get("surface") if isinstance(summary, dict) else None,
        "measured_speedup_records_attached": sum(
            1 for record in records if record["timing_evidence"].get("status") == "measured"
        ),
        "candidate_count": len(candidates),
        "shape_points": shape_points,
        "steps": steps,
        "record_count": len(records),
        "gpu_decision_count": gpu_count,
        "cpu_decision_count": cpu_count,
        "runtime_integration_queue": runtime_queue,
        "top_runtime_integration_candidate": runtime_queue[0] if runtime_queue else None,
        "source_variant_count": len(source_variants),
        "source_variant_decision_count": len(source_variant_records),
        "source_variant_promote_count": source_variant_promote_count,
        "source_variant_keep_baseline_count": source_variant_keep_baseline_count,
        "source_variant_select_cpu_count": source_variant_select_cpu_count,
        "source_variant_runtime_integration_queue": source_variant_queue,
        "selected_next_source_variant_runtime_boundary": next_source_variant_boundary,
        "by_shape": by_shape,
        "by_candidate": by_candidate,
        "by_source_variant_shape": by_source_variant_shape,
        "by_source_variant": by_source_variant,
        "records": records,
        "source_variant_records": source_variant_records,
        "interpretation": (
            "compile-time CPU/GPU selection matrix over measured scientific CIRCT candidates; "
            "CPU remains the fail-closed default below each candidate threshold, and HLS-friendly "
            "source variants are promoted only when equality holds and the measured variant beats "
            "the baseline candidate"
        ),
        "non_claims": protocol.get(
            "non_claims",
            [
                "not_runtime_abi_authority",
                "not_a_general_rtl_speedup_claim",
                "not_rtlmeter_evidence",
                "not_full_microgpt_execution",
                "not_automatic_partitioning",
            ],
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=Path("reports/scientific_circt_hybrid_protocol.json"))
    parser.add_argument(
        "--summary",
        type=Path,
        default=SUMMARY,
        help="Scientific hybrid advantage summary used to attach measured speedup evidence.",
    )
    parser.add_argument(
        "--nstates",
        type=int,
        action="append",
        default=None,
        help="State batch size to include; repeat for multiple points. Defaults to 64, 256, and 1024.",
    )
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)

    try:
        report = build_matrix(
            _load(args.protocol),
            args.nstates or list(DEFAULT_NSTATES),
            args.steps,
            _load(args.summary),
        )
    except Exception as exc:
        print(str(exc))
        return 2

    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "matrix_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
