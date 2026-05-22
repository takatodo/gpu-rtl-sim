from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


RunCpuKickInferenceFn = Callable[..., dict[str, object]]


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def limited_images(manifest: dict[str, object], *, limit: int | None) -> list[dict[str, object]]:
    images = manifest.get("images")
    if not isinstance(images, list):
        raise ValueError("manifest missing images list")
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        images = images[:limit]
    result: list[dict[str, object]] = []
    for item in images:
        if not isinstance(item, dict):
            raise ValueError("manifest image entries must be objects")
        image_id = item.get("image_id")
        label = item.get("label")
        if not isinstance(image_id, str) or not image_id:
            raise ValueError("manifest image entry missing image_id")
        if not isinstance(label, int):
            raise ValueError(f"manifest image entry missing integer label: {image_id}")
        result.append(item)
    if not result:
        raise ValueError("manifest has no images to evaluate")
    return result


def batch_sizes(count: int, *, batch_size: int, max_batch_size: int) -> list[int]:
    if batch_size <= 0:
        raise ValueError("hybrid_batch_size must be positive")
    if batch_size > max_batch_size:
        raise ValueError(f"hybrid_batch_size must be <= {max_batch_size}")
    return [min(batch_size, count - start) for start in range(0, count, batch_size)]


def dry_run_cpu_kick_predictions(
    *,
    manifest: dict[str, object],
    manifest_path: Path,
    output_path: Path,
    model_id: str,
    image_count: int,
    batch_size: int,
) -> dict[str, object]:
    predictions = {
        "schema_version": 1,
        "target": model_id,
        "dataset_scope": manifest.get("dataset_scope", "unknown"),
        "manifest": str(manifest_path),
        "source_predictions": "planned_cpu_kicked_mobile_vit_inference",
        "requested_image_count": image_count,
        "prediction_count": 0,
        "batch_size": batch_size,
        "predictions": [],
        "non_claims": ["dry-run did not execute MobileViT inference"],
    }
    write_json(output_path, predictions)
    return predictions


def load_or_generate_cpu_kick_predictions(
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
    run_cpu_kick_inference_fn: RunCpuKickInferenceFn,
) -> tuple[dict[str, object], bool]:
    if not run_cpu_kick_infer:
        return load_json(output_path), False
    if cpu_kick_batch_size <= 0:
        raise ValueError("cpu_kick_batch_size must be positive")
    if dry_run:
        return (
            dry_run_cpu_kick_predictions(
                manifest=manifest,
                manifest_path=manifest_path,
                output_path=output_path,
                model_id=model_id,
                image_count=image_count,
                batch_size=cpu_kick_batch_size,
            ),
            True,
        )
    return (
        run_cpu_kick_inference_fn(
            manifest_path=manifest_path,
            output_path=output_path,
            model_id=model_id,
            limit=limit,
            batch_size=cpu_kick_batch_size,
        ),
        True,
    )
