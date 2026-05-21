"""Efficiency reports for hybrid template execution plans."""

from __future__ import annotations

import json
from pathlib import Path

from hybrid_template_types import HybridTemplatePlan
from results_reproduction_io import display_path, parse_hybrid_report


REPO_ROOT = Path(__file__).resolve().parents[2]


def _shape_class(plan: HybridTemplatePlan) -> dict[str, str]:
    if plan.nstates >= 16 and plan.steps <= 4:
        return {
            "speedup_class": "high",
            "reason": "state-parallel shape can amortize GPU launch and transfer overhead",
        }
    if plan.nstates == 1 and plan.steps > 1:
        return {
            "speedup_class": "low",
            "reason": "single-state repeated-step shapes tend to be launch-overhead limited",
        }
    return {
        "speedup_class": "medium",
        "reason": "shape needs measurement before a speedup claim",
    }


def template_efficiency_report(plan: HybridTemplatePlan) -> dict[str, object]:
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "estimated",
        "target": plan.target_name,
        "shape": f"{plan.nstates}x{plan.steps}",
        **_shape_class(plan),
        "non_claims": [
            "estimate only; not repeat-median evidence",
            "not a broad speedup claim for arbitrary RTL",
            "coverage-output equivalence remains separate from performance",
        ],
    }
    if not plan.cpu_report.exists() or not plan.hybrid_report.exists():
        return report

    cpu = json.loads(plan.cpu_report.read_text(encoding="utf-8"))
    hybrid = parse_hybrid_report(plan.hybrid_report, repo_root=REPO_ROOT)
    cpu_elapsed_ms = float(cpu["elapsed_ms"])
    hybrid_wall_ms = float(hybrid["hybrid_wall_ms"])
    report.update(
        {
            "status": "observed_from_existing_reports",
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
    )
    return report


def format_template_efficiency_report(report: dict[str, object]) -> str:
    lines = [
        "# efficiency_estimate",
        f"status: {report['status']}",
        f"target: {report['target']}",
        f"shape: {report['shape']}",
        f"speedup_class: {report['speedup_class']}",
        f"reason: {report['reason']}",
    ]
    if "cpu_to_hybrid_wall_speedup" in report:
        speedup = report["cpu_to_hybrid_wall_speedup"]
        lines.append(f"cpu_to_hybrid_wall_speedup: {speedup:.3f}x" if isinstance(speedup, float) else f"cpu_to_hybrid_wall_speedup: {speedup}")
    if "cpu_elapsed_ms" in report:
        lines.append(f"cpu_elapsed_ms: {report['cpu_elapsed_ms']}")
    if "hybrid_wall_ms" in report:
        lines.append(f"hybrid_wall_ms: {report['hybrid_wall_ms']}")
    lines.append("non_claims:")
    lines.extend(f"- {item}" for item in report["non_claims"])
    return "\n".join(lines)
