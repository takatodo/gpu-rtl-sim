"""Hybrid RTL batch planning helpers for MobileViT ImageNet evaluation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable

from hybrid_template_runner import HybridTemplatePlan, command_plan, load_template_plan
from mobile_vit_hybrid_imagenet_inputs import (
    batch_sizes as _batch_sizes_impl,
    load_json as _load_json,
)


MAX_RTL_PROXY_BATCH = 1024
RunPlanFn = Callable[[HybridTemplatePlan], None]


def _batch_sizes(count: int, *, batch_size: int) -> list[int]:
    return _batch_sizes_impl(count, batch_size=batch_size, max_batch_size=MAX_RTL_PROXY_BATCH)


def _commands_as_strings(plan: HybridTemplatePlan) -> list[str]:
    return [" ".join(command) for command in command_plan(plan)]


def _display_path(path: Path) -> str:
    if path.is_absolute():
        try:
            return str(path.relative_to(Path.cwd()))
        except ValueError:
            return str(path)
    return str(path)


def _compare_passed(path: Path) -> bool:
    data = _load_json(path)
    selected = data.get("selected_acceptance_policy")
    if isinstance(selected, dict) and selected.get("passed") is True:
        return True
    coverage = data.get("coverage_output_policy")
    return isinstance(coverage, dict) and coverage.get("passed") is True


def imagenet_batch_plan(*, template_path: Path, index: int, size: int, cfg_seed: int) -> HybridTemplatePlan:
    plan = load_template_plan(
        template_path,
        shape="1x1",
        cfg_batch_length=size,
        cfg_seed=cfg_seed + index - 1,
    )
    batch_tag = f"imagenet_batch{index}_{size}"
    return replace(
        plan,
        cpu_init_state=plan.mdir / f"{plan.target_name}_{batch_tag}_cpu_init_1x1.bin",
        cpu_reference_state=plan.mdir / f"{plan.target_name}_{batch_tag}_cpu_repeat_1x1.bin",
        gpu_candidate_state=plan.mdir / f"{plan.target_name}_{batch_tag}_gpu_from_cpu_init_1x1.bin",
        cpu_init_report=Path("reports") / f"{plan.target_name}_{batch_tag}_cpu_init_1x1.json",
        cpu_report=Path("reports") / f"{plan.target_name}_{batch_tag}_cpu_repeat_1x1.json",
        hybrid_report=Path("reports") / f"{plan.target_name}_{batch_tag}_hybrid_1x1.txt",
        compare_report=Path("reports") / f"{plan.target_name}_{batch_tag}_cpu_vs_hybrid_1x1_coverage_output_compare.json",
    )


def run_hybrid_batches(
    *,
    image_count: int,
    hybrid_batch_size: int,
    hybrid_template_path: Path,
    cfg_seed: int,
    dry_run: bool,
    runner: RunPlanFn,
) -> tuple[list[dict[str, object]], bool]:
    batches: list[dict[str, object]] = []
    compare_passes: list[bool] = []
    for index, size in enumerate(_batch_sizes(image_count, batch_size=hybrid_batch_size), start=1):
        plan = imagenet_batch_plan(template_path=hybrid_template_path, index=index, size=size, cfg_seed=cfg_seed)
        batch = {
            "batch_index": index,
            "image_count": size,
            "cfg_batch_length": size,
            "shape": "1x1",
            "compare_report": _display_path(plan.compare_report),
            "commands": _commands_as_strings(plan),
        }
        if dry_run:
            batch["status"] = "planned_dry_run"
        else:
            runner(plan)
            passed = _compare_passed(plan.compare_report)
            compare_passes.append(passed)
            batch["status"] = "passed" if passed else "failed"
            batch["coverage_output_equivalence_passed"] = passed
        batches.append(batch)
    hybrid_checks_complete = (not dry_run) and bool(compare_passes) and all(compare_passes)
    return batches, hybrid_checks_complete


def hybrid_imagenet_summary(
    *,
    manifest: dict[str, object],
    manifest_path: Path,
    cpu_kick_predictions_path: Path,
    cpu_kick_infer_generated: bool,
    cpu_kick_batch_size: int,
    accuracy_report_path: Path,
    hybrid_template_path: Path,
    model_id: str,
    image_count: int,
    hybrid_batch_size: int,
    dry_run: bool,
    accuracy: dict[str, object],
    batches: list[dict[str, object]],
    hybrid_checks_complete: bool,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "target": model_id,
        "dataset_scope": manifest.get("dataset_scope", "unknown"),
        "manifest": str(manifest_path),
        "cpu_kick_predictions": str(cpu_kick_predictions_path),
        "cpu_kick_infer_generated": cpu_kick_infer_generated,
        "cpu_kick_batch_size": cpu_kick_batch_size if cpu_kick_infer_generated else None,
        "accuracy_report": str(accuracy_report_path),
        "hybrid_template": str(hybrid_template_path),
        "evaluated_count": accuracy["evaluated_count"],
        "top1_accuracy": accuracy["top1_accuracy"],
        "top5_accuracy": accuracy["top5_accuracy"],
        "accuracy_claim_allowed": accuracy["accuracy_claim_allowed"],
        "hybrid_control": {
            "target": "mobile_vit_cpu_kick_rtl_proxy",
            "execution_status": "planned_dry_run" if dry_run else "executed",
            "image_count": image_count,
            "hybrid_batch_size": hybrid_batch_size,
            "batch_count": len(batches),
            "coverage_output_equivalence_complete": hybrid_checks_complete,
            "batches": batches,
        },
        "ready_hybrid_imagenet_eval_claim": (
            accuracy["accuracy_claim_allowed"] is True and hybrid_checks_complete
        ),
        "non_claims": [
            "not MobileViT numerical inference in RTL",
            "not ImageNet accuracy from RTL logits",
            "hybrid RTL proxy checks the CPU-visible LOAD_MODEL/LOAD_IMAGE/KICK_INFER/POLL_DONE boundary",
            "accuracy is computed from CPU-kick prediction records",
        ],
    }
