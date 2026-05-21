from __future__ import annotations

from pathlib import Path

from hybrid_benchmark_catalog import BENCHMARKS
from hybrid_benchmark_paths import display_path
from hybrid_benchmark_specs import (
    KIND_MOBILE_VIT_IMAGENET,
    KIND_SLICE_TEMPLATE,
    MODE_PERSISTENT_RESIDENT_STATE_ABI,
    MODE_RESIDENT_STATE_REUSE,
    MODE_TEMPLATE,
)
from hybrid_template_runner import load_template_plan


def expected_reports(
    *,
    target: str,
    shape: str | None,
    limit: int | None,
    mode: str,
    phases: int,
) -> dict[str, object]:
    spec = BENCHMARKS[target]
    if spec.kind == KIND_SLICE_TEMPLATE and mode == MODE_TEMPLATE:
        assert spec.template is not None
        assert shape is not None
        plan = load_template_plan(Path(spec.template), shape=shape)
        return {
            "cpu_report": display_path(plan.cpu_report),
            "hybrid_report": display_path(plan.hybrid_report),
            "compare_report": display_path(plan.compare_report),
        }
    if spec.kind == KIND_SLICE_TEMPLATE and mode == MODE_RESIDENT_STATE_REUSE:
        return {
            "aggregate_summary": "reports/resident_state_reuse_experiment_summary.json",
            "phase_count": phases,
        }
    if spec.kind == KIND_SLICE_TEMPLATE and mode == MODE_PERSISTENT_RESIDENT_STATE_ABI:
        return {
            "aggregate_summary": "reports/persistent_resident_state_abi_probe_summary.json",
            "phase_count": phases,
        }
    if spec.kind == KIND_MOBILE_VIT_IMAGENET:
        assert limit is not None
        return {
            "aggregate_summary": f"reports/mobile_vit_hybrid_{limit}_summary.json",
            "accuracy_report": f"reports/mobile_vit_hybrid_{limit}_accuracy.json",
        }
    return {}
