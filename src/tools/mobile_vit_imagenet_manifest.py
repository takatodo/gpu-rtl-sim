#!/usr/bin/env python3
"""Build an ImageNet-style manifest for MobileViT evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

from mobile_vit_imagenet_hf_parquet import (
    build_manifest_from_hf_parquet_shards as _build_hf_parquet_manifest_payload,
    build_manifest_from_local_hf_cache as _build_local_hf_cache_manifest_payload,
    hf_hub_download_with_retries as _hf_hub_download_with_retries,
    hf_split_parquet_files as _hf_split_parquet_files,
)
from mobile_vit_imagenet_local_manifest import (
    DEFAULT_IMAGENET_VAL_PREFIX,
    DEFAULT_IMAGENET_VAL_SUFFIX,
    IMAGE_SUFFIXES,
    build_file_manifest_payload,
)
from mobile_vit_imagenet_hf_stream import build_hf_streaming_manifest_payload

DEFAULT_HF_DATASET = "ILSVRC/imagenet-1k"
DEFAULT_HF_SPLIT = "validation"


def _validate_limit(limit: int | None) -> None:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")


def _write_manifest(output_path: Path, manifest: dict[str, object]) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _non_claims() -> list[str]:
    return [
        "not model inference",
        "not CPU-kicked execution",
        "not ImageNet accuracy by itself",
    ]


def build_manifest(
    *,
    image_root: Path,
    labels_path: Path,
    dataset_scope: str,
    output_path: Path,
    limit: int | None = None,
    labels_format: str = "filename_label",
    label_index_base: int = 0,
) -> dict[str, object]:
    _validate_limit(limit)
    manifest = build_file_manifest_payload(
        image_root=image_root,
        labels_path=labels_path,
        labels_format=labels_format,
        dataset_scope=dataset_scope,
        limit=limit,
        label_index_base=label_index_base,
        non_claims=_non_claims(),
    )
    return _write_manifest(output_path, manifest)


def build_manifest_from_hf_dataset(
    *,
    output_dir: Path,
    output_path: Path,
    dataset_scope: str,
    dataset_name: str = DEFAULT_HF_DATASET,
    split: str = DEFAULT_HF_SPLIT,
    limit: int | None = None,
    token: str | None = None,
    load_dataset_fn: Callable[..., Iterable[dict[str, object]]] | None = None,
) -> dict[str, object]:
    _validate_limit(limit)
    manifest = build_hf_streaming_manifest_payload(
        output_dir=output_dir,
        dataset_scope=dataset_scope,
        dataset_name=dataset_name,
        split=split,
        limit=limit,
        token=token,
        load_dataset_fn=load_dataset_fn,
        non_claims=_non_claims(),
    )
    return _write_manifest(output_path, manifest)


def build_manifest_from_hf_parquet_shards(
    *,
    output_dir: Path,
    output_path: Path,
    dataset_scope: str,
    dataset_name: str = DEFAULT_HF_DATASET,
    split: str = DEFAULT_HF_SPLIT,
    limit: int | None = None,
    token: str | None = None,
    download_attempts: int = 5,
) -> dict[str, object]:
    _validate_limit(limit)
    manifest = _build_hf_parquet_manifest_payload(
        output_dir=output_dir,
        dataset_scope=dataset_scope,
        dataset_name=dataset_name,
        split=split,
        limit=limit,
        token=token,
        download_attempts=download_attempts,
        non_claims=_non_claims(),
    )
    return _write_manifest(output_path, manifest)


def build_manifest_from_local_hf_cache(
    *,
    cache_dir: Path,
    output_dir: Path,
    output_path: Path,
    dataset_scope: str,
    split: str = DEFAULT_HF_SPLIT,
    limit: int | None = None,
) -> dict[str, object]:
    _validate_limit(limit)
    manifest = _build_local_hf_cache_manifest_payload(
        cache_dir=cache_dir,
        output_dir=output_dir,
        dataset_scope=dataset_scope,
        split=split,
        limit=limit,
        non_claims=_non_claims(),
    )
    return _write_manifest(output_path, manifest)


def main() -> None:
    from mobile_vit_imagenet_manifest_cli import run_manifest_cli

    run_manifest_cli()


if __name__ == "__main__":
    main()
