"""Hugging Face streaming dataset helpers for MobileViT ImageNet manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable


def _label_from_hf_sample(sample: dict[str, object], *, index: int) -> int:
    label = sample.get("label")
    if not isinstance(label, int):
        raise ValueError(f"HF sample missing integer label at index {index}")
    if label < 0 or label > 999:
        raise ValueError(f"HF sample label out of range at index {index}: {label}")
    return label


def _image_from_hf_sample(sample: dict[str, object], *, index: int) -> object:
    image = sample.get("image")
    if image is None or not hasattr(image, "save"):
        raise ValueError(f"HF sample missing saveable image at index {index}")
    return image


def _iter_limited(samples: Iterable[dict[str, object]], limit: int | None) -> Iterable[tuple[int, dict[str, object]]]:
    for index, sample in enumerate(samples):
        if limit is not None and index >= limit:
            break
        yield index, sample


def _load_hf_dataset_samples(
    *,
    dataset_name: str,
    split: str,
    token: str | None,
    load_dataset_fn: Callable[..., Iterable[dict[str, object]]] | None,
) -> Iterable[dict[str, object]]:
    if load_dataset_fn is None:
        try:
            from datasets import load_dataset as load_dataset_fn
        except ImportError as exc:
            raise RuntimeError("missing Python dependency: datasets") from exc
    kwargs: dict[str, object] = {"split": split, "streaming": True}
    if token:
        kwargs["token"] = token
    return load_dataset_fn(dataset_name, **kwargs)


def _save_hf_streaming_images(
    *,
    samples: Iterable[dict[str, object]],
    split: str,
    image_dir: Path,
    limit: int | None,
) -> list[dict[str, object]]:
    images: list[dict[str, object]] = []
    for index, sample in _iter_limited(samples, limit):
        if not isinstance(sample, dict):
            raise ValueError(f"HF sample must be object at index {index}")
        label = _label_from_hf_sample(sample, index=index)
        image = _image_from_hf_sample(sample, index=index)
        image_name = f"{split}_{index:08d}.jpg"
        image_path = image_dir / image_name
        image.save(image_path)
        images.append({"image_id": image_name, "path": str(image_path), "label": label})
    return images


def build_hf_streaming_manifest_payload(
    *,
    output_dir: Path,
    dataset_scope: str,
    dataset_name: str,
    split: str,
    limit: int | None,
    token: str | None,
    load_dataset_fn: Callable[..., Iterable[dict[str, object]]] | None,
    non_claims: list[str],
) -> dict[str, object]:
    samples = _load_hf_dataset_samples(
        dataset_name=dataset_name,
        split=split,
        token=token,
        load_dataset_fn=load_dataset_fn,
    )
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    images = _save_hf_streaming_images(samples=samples, split=split, image_dir=image_dir, limit=limit)
    return {
        "schema_version": 1,
        "target": "apple/mobilevit-small",
        "dataset_scope": dataset_scope,
        "hf_dataset": dataset_name,
        "hf_split": split,
        "image_root": str(image_dir),
        "image_count": len(images),
        "images": images,
        "complete_label_image_match": limit is None,
        "missing_images": [],
        "extra_images": [],
        "limited": limit is not None,
        "source": "huggingface_datasets_streaming",
        "non_claims": non_claims,
    }
