"""MobileViT ImageNet reproduction plan."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_types import ReproductionCommand

DEFAULT_HF_CACHE_DATASET_DIR = Path.home() / ".cache" / "huggingface" / "hub" / "datasets--ILSVRC--imagenet-1k"
MOBILE_VIT_PYTHON = "artifacts/mobile_vit/venv/bin/python"
MOBILE_VIT_OUTPUT_DIR = "artifacts/mobile_vit/apple_mobilevit_small"
MOBILE_VIT_MANIFEST_128 = f"{MOBILE_VIT_OUTPUT_DIR}/imagenet_manifest_128.json"
MOBILE_VIT_HF_IMAGENET_128_DIR = f"{MOBILE_VIT_OUTPUT_DIR}/hf_imagenet_val_128"
MOBILE_VIT_CPU_KICK_PREDICTIONS_128 = "reports/mobile_vit_hybrid_128_cpu_kick_predictions.json"
MOBILE_VIT_ACCURACY_REPORT_128 = "reports/mobile_vit_hybrid_128_accuracy.json"
MOBILE_VIT_SUMMARY_REPORT_128 = "reports/mobile_vit_hybrid_128_summary.json"


def _mobile_vit_manifest_command() -> ReproductionCommand:
    return ReproductionCommand(
        [
            MOBILE_VIT_PYTHON,
            "src/tools/mobile_vit_imagenet_manifest.py",
            "--hf-cache-dir",
            str(DEFAULT_HF_CACHE_DATASET_DIR),
            "--hf-output-dir",
            MOBILE_VIT_HF_IMAGENET_128_DIR,
            "--dataset-scope",
            "scoped_subset:imagenet_local_cache_128",
            "--output",
            MOBILE_VIT_MANIFEST_128,
            "--limit",
            "128",
        ]
    )


def _mobile_vit_hybrid_eval_command() -> ReproductionCommand:
    return ReproductionCommand(
        [
            "env",
            "HF_HUB_OFFLINE=1",
            "TRANSFORMERS_OFFLINE=1",
            MOBILE_VIT_PYTHON,
            "src/tools/mobile_vit_hybrid_imagenet_eval.py",
            "--manifest",
            MOBILE_VIT_MANIFEST_128,
            "--cpu-kick-predictions",
            MOBILE_VIT_CPU_KICK_PREDICTIONS_128,
            "--accuracy-report",
            MOBILE_VIT_ACCURACY_REPORT_128,
            "--summary",
            MOBILE_VIT_SUMMARY_REPORT_128,
            "--run-cpu-kick-infer",
            "--cpu-kick-batch-size",
            "16",
            "--hybrid-batch-size",
            "128",
        ]
    )


def mobile_vit_imagenet_128_plan() -> list[ReproductionCommand]:
    return [_mobile_vit_manifest_command(), _mobile_vit_hybrid_eval_command()]
