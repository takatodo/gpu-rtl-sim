from __future__ import annotations

from pathlib import Path

IMAGE_SUFFIXES: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
DEFAULT_IMAGENET_VAL_PREFIX = "ILSVRC2012_val_"
DEFAULT_IMAGENET_VAL_SUFFIX = ".JPEG"


def _read_labels(path: Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace(",", " ").split()
        if len(parts) != 2:
            raise ValueError(f"invalid label line {line_number}: {raw_line!r}")
        image_name, label_text = parts
        try:
            label = int(label_text)
        except ValueError as exc:
            raise ValueError(f"invalid integer label on line {line_number}: {label_text!r}") from exc
        if label < 0 or label > 999:
            raise ValueError(f"ImageNet label out of range on line {line_number}: {label}")
        if image_name in labels:
            raise ValueError(f"duplicate label entry: {image_name}")
        labels[image_name] = label
    return labels


def _normalize_label(raw_label: int, *, index_base: int, line_number: int) -> int:
    if index_base not in {0, 1}:
        raise ValueError(f"label_index_base must be 0 or 1, got {index_base}")
    label = raw_label - index_base
    if label < 0 or label > 999:
        raise ValueError(f"ImageNet label out of range on line {line_number}: {raw_label}")
    return label


def _read_imagenet_val_ground_truth(
    path: Path,
    *,
    label_index_base: int,
    filename_prefix: str = DEFAULT_IMAGENET_VAL_PREFIX,
    filename_suffix: str = DEFAULT_IMAGENET_VAL_SUFFIX,
) -> dict[str, int]:
    labels: dict[str, int] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace(",", " ").split()
        if len(parts) != 1:
            raise ValueError(f"invalid ImageNet val ground-truth line {line_number}: {raw_line!r}")
        try:
            raw_label = int(parts[0])
        except ValueError as exc:
            raise ValueError(f"invalid integer label on line {line_number}: {parts[0]!r}") from exc
        image_name = f"{filename_prefix}{line_number:08d}{filename_suffix}"
        labels[image_name] = _normalize_label(
            raw_label,
            index_base=label_index_base,
            line_number=line_number,
        )
    return labels


def _image_files(image_root: Path) -> dict[str, Path]:
    if image_root.is_file():
        if image_root.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"unsupported image suffix: {image_root}")
        return {image_root.name: image_root}
    if not image_root.is_dir():
        raise ValueError(f"image root does not exist: {image_root}")
    files: dict[str, Path] = {}
    for path in sorted(image_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if path.name in files:
            raise ValueError(f"duplicate image filename under root: {path.name}")
        files[path.name] = path
    return files


def _read_label_map(labels_path: Path, *, labels_format: str, label_index_base: int) -> dict[str, int]:
    if labels_format == "filename_label":
        return _read_labels(labels_path)
    if labels_format == "imagenet_val_ground_truth":
        return _read_imagenet_val_ground_truth(labels_path, label_index_base=label_index_base)
    raise ValueError(f"unsupported labels_format: {labels_format}")


def _matched_manifest_images(
    *,
    labels: dict[str, int],
    files: dict[str, Path],
    limit: int | None,
) -> tuple[list[dict[str, object]], list[str]]:
    images: list[dict[str, object]] = []
    missing_images: list[str] = []
    for image_name, label in labels.items():
        image_path = files.get(image_name)
        if image_path is None:
            missing_images.append(image_name)
            continue
        images.append({"image_id": image_name, "path": str(image_path), "label": label})
        if limit is not None and len(images) >= limit:
            break
    return images, missing_images


def build_file_manifest_payload(
    *,
    image_root: Path,
    labels_path: Path,
    labels_format: str,
    dataset_scope: str,
    limit: int | None,
    label_index_base: int,
    non_claims: list[str],
) -> dict[str, object]:
    labels = _read_label_map(labels_path, labels_format=labels_format, label_index_base=label_index_base)
    files = _image_files(image_root)
    images, missing_images = _matched_manifest_images(labels=labels, files=files, limit=limit)
    extra_images = sorted(name for name in files if name not in labels)
    return {
        "schema_version": 1,
        "target": "apple/mobilevit-small",
        "dataset_scope": dataset_scope,
        "image_root": str(image_root),
        "labels": str(labels_path),
        "labels_format": labels_format,
        "image_count": len(images),
        "images": images,
        "complete_label_image_match": not missing_images and not extra_images and (limit is None),
        "missing_images": missing_images,
        "extra_images": extra_images,
        "limited": limit is not None,
        "non_claims": non_claims,
    }
