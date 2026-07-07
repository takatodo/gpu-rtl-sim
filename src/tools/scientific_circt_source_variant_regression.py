#!/usr/bin/env python3
"""FC-076: regression/negative-example harness over recorded source-variant rows.

Pins the FC-074 promoted/fallback source-variant boundary behavior recorded in
`records/scaling_gates/scientific_circt_source_variant_regression_reference.json`
against repeat-sampled real runs of
`scientific_circt_source_variant_bridge_emit.run_source_variant`. Promoted
rows (`expected_policy: promote_to_hls_gpu`) are checked for CPU/GPU oracle
agreement and an in-band, improving speedup; the fallback row
(`expected_policy: fallback_baseline_no_speedup_improvement`) is checked for
fail-closed rejection before any GPU dispatch.

This module holds the importable decision logic only; the thin CLI lives in
`scientific_circt_source_variant_regression_cli.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import statistics
from typing import Any, Callable

import scientific_circt_source_variant_bridge_emit as bridge_emit

REFERENCE = Path("records/scaling_gates/scientific_circt_source_variant_regression_reference.json")

DISPATCHED_STATUSES = {"runtime_handoff_boundary_measured", "src_hybrid_verilator_runtime_handoff_measured"}


@dataclass(frozen=True)
class RegressionCase:
    source_variant: str
    expected_policy: str
    recorded_variant_speedup: float
    recorded_baseline_speedup: float
    relative_band: float
    absolute_floor: float
    min_improvement_margin: float
    provenance: dict[str, Any]


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def load_reference(path: Path = REFERENCE) -> list[RegressionCase]:
    payload = _load(path)
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{path}: expected non-empty rows array")
    cases: list[RegressionCase] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: each row must be an object")
        tolerance = row.get("tolerance") if isinstance(row.get("tolerance"), dict) else {}
        cases.append(
            RegressionCase(
                source_variant=str(row["source_variant"]),
                expected_policy=str(row["expected_policy"]),
                recorded_variant_speedup=float(row["recorded_variant_speedup"]),
                recorded_baseline_speedup=float(row["recorded_baseline_speedup"]),
                relative_band=float(tolerance["relative_band"]),
                absolute_floor=float(tolerance["absolute_floor"]),
                min_improvement_margin=float(tolerance["min_improvement_margin"]),
                provenance=row.get("provenance") if isinstance(row.get("provenance"), dict) else {},
            )
        )
    return cases


def default_real_runner(row: dict[str, Any], matrix: dict[str, Any], hls_summary: dict[str, Any]) -> dict[str, Any]:
    return bridge_emit.run_source_variant(row, matrix=matrix, hls_summary=hls_summary)


def _sample_from_report(report: dict[str, Any]) -> dict[str, Any]:
    average = report.get("average") if isinstance(report.get("average"), dict) else {}
    return {
        "output_equal": report.get("cpu_vs_gpu_output_equal") is True,
        "checksum_equal": report.get("cpu_vs_gpu_control_checksum_equal") is True,
        "observed_speedup": average.get("cpu_to_bridge_hybrid_wall_speedup"),
        "status": report.get("status"),
    }


def run_variant_samples(
    row: dict[str, Any],
    matrix: dict[str, Any],
    hls_summary: dict[str, Any],
    repeats: int,
    *,
    runner: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]] = default_real_runner,
) -> list[dict[str, Any]]:
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    return [_sample_from_report(runner(row, matrix, hls_summary)) for _ in range(repeats)]


def median_speedup(samples: list[dict[str, Any]]) -> float | None:
    numeric = [sample.get("observed_speedup") for sample in samples if isinstance(sample.get("observed_speedup"), int | float)]
    return float(statistics.median(numeric)) if numeric else None


def decide_promote_case(case: RegressionCase, samples: list[dict[str, Any]]) -> tuple[bool, str]:
    """Every sample must be a valid, dispatched, agreeing oracle before the
    median is even computed: a non-success status or a failed output/checksum
    oracle fails closed as `oracle_mismatch`; a missing or non-finite
    speedup (NaN comparisons are always false, so NaN must not slip through
    the band check below) fails closed as `speedup_out_of_band`.
    """
    if not samples:
        return False, "oracle_mismatch"
    for sample in samples:
        oracle_ok = (
            sample.get("status") in DISPATCHED_STATUSES
            and sample.get("output_equal") is True
            and sample.get("checksum_equal") is True
        )
        if not oracle_ok:
            return False, "oracle_mismatch"
        speedup = sample.get("observed_speedup")
        if isinstance(speedup, bool) or not isinstance(speedup, int | float) or not math.isfinite(speedup):
            return False, "speedup_out_of_band"
    median = median_speedup(samples)
    band = max(case.absolute_floor, case.recorded_variant_speedup * case.relative_band)
    if median is None or abs(median - case.recorded_variant_speedup) > band:
        return False, "speedup_out_of_band"
    if median <= case.recorded_baseline_speedup + case.min_improvement_margin:
        return False, "lost_improvement_margin"
    return True, "passed"


def decide_fallback_case(case: RegressionCase, run_report: dict[str, Any]) -> tuple[bool, str]:
    """Pass only a fallback row that was rejected at exactly the metadata
    gate for a policy/entrypoint reason before any dispatch. A row that
    cleared the gate and then died later (build failure, missing artifacts,
    ...) is a different failure and must not be conflated with the intended
    fail-closed rejection.
    """
    status = run_report.get("status")
    commands = run_report.get("commands") if isinstance(run_report.get("commands"), list) else []
    dispatched_command = any(
        isinstance(command, dict) and command.get("stage") == "source_variant_runtime_handoff_run" for command in commands
    )
    if status in DISPATCHED_STATUSES or dispatched_command:
        return False, "fallback_variant_was_dispatched"
    metadata_gate = run_report.get("metadata_gate") if isinstance(run_report.get("metadata_gate"), dict) else {}
    failed_checks = metadata_gate.get("failed_checks")
    failed_checks = failed_checks if isinstance(failed_checks, list) else []
    gate_rejected_on_policy = status == "src_hybrid_verilator_metadata_gate_rejected" and (
        "policy" in failed_checks or "entrypoint_kind" in failed_checks
    )
    if not gate_rejected_on_policy:
        return False, "fallback_rejection_not_metadata_gate"
    return True, "passed"


def inject_corrupted_samples(kind: str) -> list[dict[str, Any]]:
    """Synthetic sample sets that must drive decide_promote_case to fail closed.

    kind="oracle": one of three samples reports a CPU/GPU output mismatch.
    kind="speedup": all samples report a speedup far below any recorded
    variant speedup in the reference, so the band check fails regardless of
    which reference row it is checked against.
    """
    if kind == "oracle":
        return [
            {"output_equal": False, "checksum_equal": True, "observed_speedup": 10.0, "status": "runtime_handoff_boundary_failed"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 10.0, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 10.0, "status": "runtime_handoff_boundary_measured"},
        ]
    if kind == "speedup":
        return [
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 0.1, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 0.1, "status": "runtime_handoff_boundary_measured"},
            {"output_equal": True, "checksum_equal": True, "observed_speedup": 0.1, "status": "runtime_handoff_boundary_measured"},
        ]
    raise ValueError(f"unknown corruption kind: {kind}")
