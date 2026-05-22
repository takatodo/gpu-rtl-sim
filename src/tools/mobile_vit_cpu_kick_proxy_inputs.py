from __future__ import annotations


def manifest_by_id(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    images = manifest.get("images")
    if not isinstance(images, list):
        raise ValueError("manifest missing images list")
    out: dict[str, dict[str, object]] = {}
    for item in images:
        if not isinstance(item, dict):
            raise ValueError("manifest image entries must be objects")
        image_id = item.get("image_id")
        label = item.get("label")
        if not isinstance(image_id, str) or not image_id:
            raise ValueError("manifest image entry missing image_id")
        if not isinstance(label, int):
            raise ValueError(f"manifest image entry missing integer label: {image_id}")
        if image_id in out:
            raise ValueError(f"duplicate manifest image_id: {image_id}")
        out[image_id] = item
    return out


def prediction_by_id(predictions: dict[str, object]) -> dict[str, dict[str, object]]:
    entries = predictions.get("predictions")
    if not isinstance(entries, list):
        raise ValueError("predictions missing predictions list")
    out: dict[str, dict[str, object]] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("prediction entries must be objects")
        image_id = item.get("image_id")
        top5 = item.get("top5")
        if not isinstance(image_id, str) or not image_id:
            raise ValueError("prediction entry missing image_id")
        if not isinstance(top5, list) or not top5:
            raise ValueError(f"prediction entry missing top5: {image_id}")
        if image_id in out:
            raise ValueError(f"duplicate prediction image_id: {image_id}")
        out[image_id] = item
    return out


def top5_class_ids(prediction: dict[str, object]) -> list[int]:
    out: list[int] = []
    for item in prediction["top5"]:
        if isinstance(item, int):
            out.append(item)
        elif isinstance(item, dict) and isinstance(item.get("class_id"), int):
            out.append(item["class_id"])
        else:
            raise ValueError(f"invalid top5 item: {item!r}")
    if len(out) > 5:
        raise ValueError("top5 has more than five entries")
    return out


def limited_image_ids(manifest_items: dict[str, dict[str, object]], limit: int | None) -> list[str]:
    image_ids = list(manifest_items)
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        image_ids = image_ids[:limit]
    return image_ids
