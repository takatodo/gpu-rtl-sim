"""Shared parquet helpers for MobileViT ImageNet manifest materialization."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import time


def hf_split_parquet_files(files: list[str], *, split: str) -> list[str]:
    prefix = f"data/{split}-"
    shards = sorted(path for path in files if path.startswith(prefix) and path.endswith(".parquet"))
    if not shards:
        raise ValueError(f"no parquet shards found for HF split: {split}")
    return shards


def hf_hub_download_with_retries(
    *,
    hf_hub_download_fn,
    attempts: int,
    **kwargs,
) -> str:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return hf_hub_download_fn(**kwargs)
        except Exception as exc:  # pragma: no cover - exercised through CLI/network failures.
            last_exc = exc
            if attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 30))
    assert last_exc is not None
    raise last_exc


def append_parquet_images(
    *,
    pq,
    image_module,
    shard_path: str | Path,
    split: str,
    image_dir: Path,
    images: list[dict[str, object]],
    limit: int | None,
    error_prefix: str,
) -> bool:
    table = pq.read_table(shard_path, columns=["image", "label"])
    for row in table.to_pylist():
        label = row.get("label")
        image = row.get("image")
        if not isinstance(label, int):
            raise ValueError(f"{error_prefix} sample missing integer label at index {len(images)}")
        if label < 0 or label > 999:
            raise ValueError(f"{error_prefix} sample label out of range at index {len(images)}: {label}")
        if not isinstance(image, dict) or not isinstance(image.get("bytes"), bytes):
            raise ValueError(f"{error_prefix} sample missing image bytes at index {len(images)}")
        image_name = f"{split}_{len(images):08d}.jpg"
        image_path = image_dir / image_name
        image_module.open(BytesIO(image["bytes"])).convert("RGB").save(image_path)
        images.append(
            {
                "image_id": image_name,
                "path": str(image_path),
                "label": label,
            }
        )
        if limit is not None and len(images) >= limit:
            return True
    return False


def hf_parquet_manifest(
    *,
    dataset_scope: str,
    split: str,
    image_dir: Path,
    images: list[dict[str, object]],
    completed_shards: list[str],
    shard_count: int,
    limit: int | None,
    source: str,
    extra: dict[str, object],
    non_claims: list[str],
) -> dict[str, object]:
    manifest = {
        "schema_version": 1,
        "target": "apple/mobilevit-small",
        "dataset_scope": dataset_scope,
        "hf_split": split,
        "image_root": str(image_dir),
        "image_count": len(images),
        "images": images,
        "complete_label_image_match": limit is None and len(completed_shards) == shard_count,
        "missing_images": [],
        "extra_images": [],
        "limited": limit is not None,
        "source": source,
        "completed_shards": completed_shards,
        "shard_count": shard_count,
        "non_claims": non_claims,
    }
    manifest.update(extra)
    return manifest
