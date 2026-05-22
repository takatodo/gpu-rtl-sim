#!/usr/bin/env python3
"""Run MobileViT ImageNet evaluation with a hybrid RTL control-boundary check."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

from hybrid_template_runner import run_plan
from mobile_vit_accuracy_core import compute_accuracy
from mobile_vit_hybrid_preflight import _cached_hf_validation_shards, build_preflight_report
from mobile_vit_hybrid_imagenet_defaults import DEFAULT_MODEL_ID, DEFAULT_TEMPLATE
from mobile_vit_hybrid_eval_core import (
    MAX_RTL_PROXY_BATCH,
    RunPlanFn,
    hybrid_imagenet_summary,
    run_hybrid_batches,
)
from mobile_vit_hybrid_imagenet_inputs import (
    limited_images as _limited_images,
    load_json as _load_json,
    load_or_generate_cpu_kick_predictions as _load_or_generate_cpu_kick_predictions_impl,
    write_json as _write_json,
)


def _run_cpu_kick_inference(**kwargs: object) -> dict[str, object]:
    module = import_module("mobile_vit_cpu_kick_infer")
    return module.run_cpu_kick_inference(**kwargs)


def parse_args():
    from mobile_vit_hybrid_imagenet_cli import parse_args as _parse_args

    return _parse_args()


def _load_or_generate_cpu_kick_predictions(
    *,
    manifest: dict[str, object],
    manifest_path: Path,
    output_path: Path,
    model_id: str,
    image_count: int,
    limit: int | None,
    run_cpu_kick_infer: bool,
    cpu_kick_batch_size: int,
    dry_run: bool,
) -> tuple[dict[str, object], bool]:
    return _load_or_generate_cpu_kick_predictions_impl(
        manifest=manifest,
        manifest_path=manifest_path,
        output_path=output_path,
        model_id=model_id,
        image_count=image_count,
        limit=limit,
        run_cpu_kick_infer=run_cpu_kick_infer,
        cpu_kick_batch_size=cpu_kick_batch_size,
        dry_run=dry_run,
        run_cpu_kick_inference_fn=_run_cpu_kick_inference,
    )


def run_hybrid_imagenet_eval(
    *,
    manifest_path: Path,
    cpu_kick_predictions_path: Path,
    accuracy_report_path: Path,
    summary_path: Path,
    hybrid_template_path: Path = DEFAULT_TEMPLATE,
    model_id: str = DEFAULT_MODEL_ID,
    limit: int | None = None,
    hybrid_batch_size: int = MAX_RTL_PROXY_BATCH,
    cfg_seed: int = 1,
    run_cpu_kick_infer: bool = False,
    cpu_kick_batch_size: int = 1,
    dry_run: bool = False,
    run_plan_fn: RunPlanFn | None = None,
) -> dict[str, object]:
    manifest = _load_json(manifest_path)
    images = _limited_images(manifest, limit=limit)
    predictions, cpu_kick_infer_generated = _load_or_generate_cpu_kick_predictions(
        manifest=manifest,
        manifest_path=manifest_path,
        output_path=cpu_kick_predictions_path,
        model_id=model_id,
        image_count=len(images),
        limit=limit,
        run_cpu_kick_infer=run_cpu_kick_infer,
        cpu_kick_batch_size=cpu_kick_batch_size,
        dry_run=dry_run,
    )
    accuracy = compute_accuracy(manifest={**manifest, "images": images}, predictions=predictions)
    _write_json(accuracy_report_path, accuracy)

    runner = run_plan_fn or (lambda plan: run_plan(plan, dry_run=False))
    batches, hybrid_checks_complete = run_hybrid_batches(
        image_count=len(images),
        hybrid_batch_size=hybrid_batch_size,
        hybrid_template_path=hybrid_template_path,
        cfg_seed=cfg_seed,
        dry_run=dry_run,
        runner=runner,
    )
    summary = hybrid_imagenet_summary(
        manifest=manifest,
        manifest_path=manifest_path,
        cpu_kick_predictions_path=cpu_kick_predictions_path,
        cpu_kick_infer_generated=cpu_kick_infer_generated,
        cpu_kick_batch_size=cpu_kick_batch_size,
        accuracy_report_path=accuracy_report_path,
        hybrid_template_path=hybrid_template_path,
        model_id=model_id,
        image_count=len(images),
        hybrid_batch_size=hybrid_batch_size,
        dry_run=dry_run,
        accuracy=accuracy,
        batches=batches,
        hybrid_checks_complete=hybrid_checks_complete,
    )
    _write_json(summary_path, summary)
    return summary


def main() -> None:
    args = parse_args()
    if args.preflight:
        from mobile_vit_hybrid_imagenet_cli import run_preflight_from_args

        run_preflight_from_args(args)
        return
    summary = run_hybrid_imagenet_eval(
        manifest_path=args.manifest,
        cpu_kick_predictions_path=args.cpu_kick_predictions,
        accuracy_report_path=args.accuracy_report,
        summary_path=args.summary,
        hybrid_template_path=args.hybrid_template,
        model_id=args.model_id,
        limit=args.limit,
        hybrid_batch_size=args.hybrid_batch_size,
        cfg_seed=args.cfg_seed,
        run_cpu_kick_infer=args.run_cpu_kick_infer,
        cpu_kick_batch_size=args.cpu_kick_batch_size,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
