"""Core scoring helpers for MobileViT accuracy reports."""

from __future__ import annotations

from typing import Iterable

from mobile_vit_accuracy_report import accuracy_report, scope_allows_accuracy_claim


def entries_by_id(entries: Iterable[dict[str, object]]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for entry in entries:
        image_id = entry.get("image_id")
        if not isinstance(image_id, str) or not image_id:
            raise ValueError("manifest entry missing non-empty image_id")
        if not isinstance(entry.get("label"), int):
            raise ValueError(f"manifest label must be int for image_id: {image_id}")
        if image_id in out:
            raise ValueError(f"duplicate image_id in manifest: {image_id}")
        out[image_id] = entry
    return out


def topk_classes(prediction: dict[str, object]) -> list[int]:
    top5 = prediction.get("top5")
    if not isinstance(top5, list) or not top5:
        raise ValueError("prediction missing non-empty top5 list")
    classes: list[int] = []
    for item in top5:
        if isinstance(item, int):
            classes.append(item)
        elif isinstance(item, dict) and isinstance(item.get("class_id"), int):
            classes.append(item["class_id"])
        else:
            raise ValueError(f"invalid top5 item: {item!r}")
    if len(classes) > 5:
        raise ValueError("top5 list has more than five entries")
    return classes


def prediction_image_id(prediction: dict[str, object]) -> str:
    image_id = prediction.get("image_id")
    if not isinstance(image_id, str) or not image_id:
        raise ValueError("prediction entry missing non-empty image_id")
    return image_id


def score_prediction(
    *,
    prediction: dict[str, object],
    manifest_by_id: dict[str, dict[str, object]],
) -> tuple[str, bool, bool] | None:
    image_id = prediction_image_id(prediction)
    if image_id not in manifest_by_id:
        return None
    label = manifest_by_id[image_id].get("label")
    if not isinstance(label, int):
        raise ValueError(f"manifest label must be int for image_id: {image_id}")
    topk = topk_classes(prediction)
    return image_id, topk[0] == label, label in topk


def missing_prediction_ids(
    *,
    manifest_by_id: dict[str, dict[str, object]],
    seen_predictions: set[str],
) -> list[str]:
    return [image_id for image_id in manifest_by_id if image_id not in seen_predictions]


def compute_accuracy(
    *,
    manifest: dict[str, object],
    predictions: dict[str, object],
) -> dict[str, object]:
    manifest_entries = manifest.get("images")
    prediction_entries = predictions.get("predictions")
    if not isinstance(manifest_entries, list):
        raise ValueError("manifest missing images list")
    if not isinstance(prediction_entries, list):
        raise ValueError("predictions missing predictions list")

    manifest_by_id = entries_by_id(manifest_entries)
    total = 0
    top1_correct = 0
    top5_correct = 0
    missing_predictions: list[str] = []
    extra_predictions: list[str] = []

    seen_predictions: set[str] = set()
    for prediction in prediction_entries:
        scored = score_prediction(prediction=prediction, manifest_by_id=manifest_by_id)
        if scored is None:
            extra_predictions.append(prediction_image_id(prediction))
            continue
        image_id, top1_hit, top5_hit = scored
        seen_predictions.add(image_id)
        total += 1
        if top1_hit:
            top1_correct += 1
        if top5_hit:
            top5_correct += 1

    missing_predictions = missing_prediction_ids(
        manifest_by_id=manifest_by_id,
        seen_predictions=seen_predictions,
    )
    return accuracy_report(
        manifest=manifest,
        predictions=predictions,
        manifest_by_id=manifest_by_id,
        total=total,
        top1_correct=top1_correct,
        top5_correct=top5_correct,
        missing_predictions=missing_predictions,
        extra_predictions=extra_predictions,
    )
