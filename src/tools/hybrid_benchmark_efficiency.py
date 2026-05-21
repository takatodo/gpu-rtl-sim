"""Efficiency estimates for Verilator-like hybrid benchmark plans."""

from __future__ import annotations

import json
from pathlib import Path

from hybrid_benchmark_catalog import BENCHMARKS, KIND_SLICE_TEMPLATE, MODE_TEMPLATE
from hybrid_template_runner import load_template_plan
from hybrid_template_types import parse_shape
from results_reproduction_io import display_path, parse_hybrid_report


REPO_ROOT = Path(__file__).resolve().parents[2]


def _shape_class(shape: str | None) -> dict[str, object]:
    if shape is None:
        return {
            "speedup_class": "unknown",
            "reason": "no state/step shape was provided",
            "next_action": "provide --shape for RTL slice-template targets",
        }
    nstates, steps = parse_shape(shape)
    if nstates >= 16 and steps <= 4:
        return {
            "speedup_class": "high",
            "reason": "state-parallel shape can amortize GPU launch and transfer overhead",
            "next_action": "run or scale state-parallel shapes before optimizing runtime internals",
        }
    if nstates == 1 and steps > 1:
        return {
            "speedup_class": "low",
            "reason": "single-state repeated-step shapes tend to be launch-overhead limited",
            "next_action": "prefer resident execution or batch multiple states before claiming speedup",
        }
    return {
        "speedup_class": "medium",
        "reason": "shape has some parallelism but needs measurement before a speedup claim",
        "next_action": "measure this shape before using it as performance evidence",
    }


def _observed_template_efficiency(template: str, shape: str) -> dict[str, object] | None:
    plan = load_template_plan(Path(template), shape=shape)
    if not plan.cpu_report.exists() or not plan.hybrid_report.exists():
        return None
    cpu = json.loads(plan.cpu_report.read_text(encoding="utf-8"))
    hybrid = parse_hybrid_report(plan.hybrid_report, repo_root=REPO_ROOT)
    cpu_elapsed_ms = float(cpu["elapsed_ms"])
    hybrid_wall_ms = float(hybrid["hybrid_wall_ms"])
    return {
        "source": "existing_reports",
        "cpu_elapsed_ms": cpu_elapsed_ms,
        "hybrid_wall_ms": hybrid_wall_ms,
        "gpu_kernel_total_ms": hybrid["gpu_kernel_total_ms"],
        "cpu_to_hybrid_wall_speedup": cpu_elapsed_ms / hybrid_wall_ms if hybrid_wall_ms else None,
        "reports": {
            "cpu_report": display_path(plan.cpu_report, repo_root=REPO_ROOT),
            "hybrid_report": display_path(plan.hybrid_report, repo_root=REPO_ROOT),
        },
    }


def efficiency_estimate(
    *,
    target: str,
    shape: str | None,
    limit: int | None,
    mode: str,
    phases: int,
) -> dict[str, object]:
    spec = BENCHMARKS[target]
    estimate: dict[str, object] = {
        "schema_version": 1,
        "status": "estimated",
        "target": target,
        "shape": shape,
        "limit": limit,
        "mode": mode,
        "phases": phases,
        "non_claims": [
            "not a broad speedup claim for arbitrary RTL",
            "not timing evidence unless source is existing_reports",
            "coverage-output equivalence remains separate from performance",
        ],
    }
    if spec.kind == KIND_SLICE_TEMPLATE:
        estimate.update(_shape_class(shape))
        if mode == MODE_TEMPLATE and spec.template is not None and shape is not None:
            observed = _observed_template_efficiency(spec.template, shape)
            if observed is not None:
                estimate["status"] = "observed_from_existing_reports"
                estimate.update(observed)
        return estimate

    estimate.update(
        {
            "speedup_class": "unknown",
            "reason": "dataset-backed benchmark efficiency depends on host preprocessing and RTL proxy batch size",
            "next_action": "separate host preprocessing time from hybrid RTL control-boundary timing",
        }
    )
    return estimate


def format_efficiency_estimate(estimate: dict[str, object]) -> str:
    lines = [
        "# efficiency_estimate",
        f"status: {estimate['status']}",
        f"target: {estimate['target']}",
    ]
    if estimate.get("shape") is not None:
        lines.append(f"shape: {estimate['shape']}")
    if estimate.get("limit") is not None:
        lines.append(f"limit: {estimate['limit']}")
    lines.extend(
        [
            f"mode: {estimate['mode']}",
            f"speedup_class: {estimate['speedup_class']}",
            f"reason: {estimate['reason']}",
            f"next_action: {estimate['next_action']}",
        ]
    )
    if "cpu_to_hybrid_wall_speedup" in estimate:
        speedup = estimate["cpu_to_hybrid_wall_speedup"]
        if isinstance(speedup, float):
            lines.append(f"cpu_to_hybrid_wall_speedup: {speedup:.3f}x")
        else:
            lines.append(f"cpu_to_hybrid_wall_speedup: {speedup}")
    if "cpu_elapsed_ms" in estimate:
        lines.append(f"cpu_elapsed_ms: {estimate['cpu_elapsed_ms']}")
    if "hybrid_wall_ms" in estimate:
        lines.append(f"hybrid_wall_ms: {estimate['hybrid_wall_ms']}")
    lines.append("non_claims:")
    lines.extend(f"- {item}" for item in estimate["non_claims"])
    return "\n".join(lines)
