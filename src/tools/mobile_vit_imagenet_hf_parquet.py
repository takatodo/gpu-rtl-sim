from __future__ import annotations

from pathlib import Path

from mobile_vit_imagenet_hf_parquet_helpers import (
    append_parquet_images,
    hf_hub_download_with_retries,
    hf_parquet_manifest,
    hf_split_parquet_files,
)


DEFAULT_HF_SPLIT = "validation"


def build_manifest_from_hf_parquet_shards(
    *,
    output_dir: Path,
    dataset_scope: str,
    dataset_name: str,
    split: str,
    limit: int | None,
    token: str | None,
    download_attempts: int,
    non_claims: list[str],
) -> dict[str, object]:
    try:
        import pyarrow.parquet as pq
        from huggingface_hub import HfApi, hf_hub_download
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("missing Python dependency: pyarrow, huggingface_hub, or PIL") from exc

    files = HfApi(token=token).list_repo_files(dataset_name, repo_type="dataset")
    shards = hf_split_parquet_files(files, split=split)
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    images: list[dict[str, object]] = []
    completed_shards: list[str] = []
    stop = False
    for shard in shards:
        local_shard = hf_hub_download_with_retries(
            hf_hub_download_fn=hf_hub_download,
            attempts=download_attempts,
            repo_id=dataset_name,
            repo_type="dataset",
            filename=shard,
            token=token,
        )
        stop = append_parquet_images(
            pq=pq,
            image_module=Image,
            shard_path=local_shard,
            split=split,
            image_dir=image_dir,
            images=images,
            limit=limit,
            error_prefix="HF parquet",
        )
        completed_shards.append(shard)
        if stop:
            break

    return hf_parquet_manifest(
        dataset_scope=dataset_scope,
        split=split,
        image_dir=image_dir,
        images=images,
        completed_shards=completed_shards,
        shard_count=len(shards),
        limit=limit,
        source="huggingface_hub_parquet_shards",
        extra={"hf_dataset": dataset_name, "download_attempts": download_attempts},
        non_claims=non_claims,
    )


def build_manifest_from_local_hf_cache(
    *,
    cache_dir: Path,
    output_dir: Path,
    dataset_scope: str,
    split: str,
    limit: int | None,
    non_claims: list[str],
) -> dict[str, object]:
    try:
        import pyarrow.parquet as pq
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("missing Python dependency: pyarrow or PIL") from exc

    shard_paths = sorted((cache_dir / "snapshots").glob(f"*/data/{split}-*.parquet"))
    if not shard_paths:
        raise ValueError(f"no cached parquet shards found for split: {split}")

    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    images: list[dict[str, object]] = []
    completed_shards: list[str] = []
    stop = False
    for shard_path in shard_paths:
        stop = append_parquet_images(
            pq=pq,
            image_module=Image,
            shard_path=shard_path,
            split=split,
            image_dir=image_dir,
            images=images,
            limit=limit,
            error_prefix="cached parquet",
        )
        completed_shards.append(str(shard_path))
        if stop:
            break

    return hf_parquet_manifest(
        dataset_scope=dataset_scope,
        split=split,
        image_dir=image_dir,
        images=images,
        completed_shards=completed_shards,
        shard_count=len(shard_paths),
        limit=limit,
        source="local_huggingface_cache_parquet_shards",
        extra={"cache_dir": str(cache_dir)},
        non_claims=non_claims,
    )
