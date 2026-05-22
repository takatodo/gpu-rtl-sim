from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

from mobile_vit_imagenet_manifest import (
    DEFAULT_HF_DATASET,
    DEFAULT_HF_SPLIT,
    build_manifest_from_hf_dataset,
    build_manifest_from_hf_parquet_shards,
)


def build_hf_manifest(
    *,
    output_dir: Path,
    manifest_path: Path,
    dataset_scope: str,
    dataset_name: str,
    split: str,
    limit: int | None,
    token: str | None,
    download_attempts: int,
    load_dataset_fn: Callable[..., Iterable[dict[str, object]]] | None,
) -> dict[str, object]:
    if load_dataset_fn is not None:
        return build_manifest_from_hf_dataset(
            output_dir=output_dir,
            output_path=manifest_path,
            dataset_scope=dataset_scope,
            dataset_name=dataset_name,
            split=split,
            limit=limit,
            token=token,
            load_dataset_fn=load_dataset_fn,
        )
    return build_manifest_from_hf_parquet_shards(
        output_dir=output_dir,
        output_path=manifest_path,
        dataset_scope=dataset_scope,
        dataset_name=dataset_name,
        split=split,
        limit=limit,
        token=token,
        download_attempts=download_attempts,
    )


def clone_report(
    *,
    manifest: dict[str, object],
    output_dir: Path,
    manifest_path: Path,
    dataset_name: str,
    split: str,
    dataset_scope: str,
    token: str | None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool": "src/tools/mobile_vit_clone_imagenet_data.py",
        "source": manifest.get("source", "huggingface_datasets_streaming"),
        "dataset": dataset_name,
        "split": split,
        "dataset_scope": dataset_scope,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "image_count": manifest["image_count"],
        "limited": manifest["limited"],
        "token_used": bool(token),
        "completion_claim_allowed": False,
        "next_task": "run_mobile_vit_cpu_kick_infer_pipeline_on_materialized_manifest",
        "non_claims": [
            "not model inference",
            "not CPU-kicked execution",
            "not ImageNet accuracy by itself",
        ],
    }


def clone_hf_imagenet_data(
    *,
    output_dir: Path,
    manifest_path: Path,
    report_path: Path,
    dataset_name: str = DEFAULT_HF_DATASET,
    split: str = DEFAULT_HF_SPLIT,
    dataset_scope: str = "imagenet_validation",
    limit: int | None = None,
    token: str | None = None,
    require_token: bool = True,
    download_attempts: int = 5,
    load_dataset_fn: Callable[..., Iterable[dict[str, object]]] | None = None,
) -> dict[str, object]:
    if require_token and not token:
        raise RuntimeError("HF token is required for gated ImageNet data")
    manifest = build_hf_manifest(
        output_dir=output_dir,
        manifest_path=manifest_path,
        dataset_scope=dataset_scope,
        dataset_name=dataset_name,
        split=split,
        limit=limit,
        token=token,
        download_attempts=download_attempts,
        load_dataset_fn=load_dataset_fn,
    )
    report = clone_report(
        manifest=manifest,
        output_dir=output_dir,
        manifest_path=manifest_path,
        dataset_name=dataset_name,
        split=split,
        dataset_scope=dataset_scope,
        token=token,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
