#!/usr/bin/env python3
"""Copy an admitted TL-UL #10818 profile into its stable artifact directory."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from validate_tlul10818_boundary_profile import (
    DEFAULT_CONFIG,
    _profile,
    _read_object,
    _sha256,
    validate_profile,
)


def _copy_verified(src: Path, dst: Path, expected_sha256: str) -> None:
    if not src.is_file():
        raise ValueError(f"source artifact is missing: {src}")
    observed = _sha256(src)
    if observed != expected_sha256:
        raise ValueError(f"source artifact SHA mismatch: {src.name}")
    if dst.exists():
        if not dst.is_file():
            raise ValueError(f"destination exists and is not a file: {dst}")
        if _sha256(dst) != expected_sha256:
            raise ValueError(f"destination artifact differs: {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _report_artifacts(source_dir: Path, pipeline: Mapping[str, Any]) -> dict[str, tuple[Path, str]]:
    result: dict[str, tuple[Path, str]] = {}
    for key in ("graph_artifact", "markdown_artifact"):
        artifact = pipeline.get(key)
        if not isinstance(artifact, Mapping):
            raise ValueError(f"{key} must be an object")
        path = artifact.get("path")
        digest = artifact.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            raise ValueError(f"{key} is invalid")
        result[path] = (source_dir / path, digest)
    return result


def _manifest_artifacts(source_dir: Path) -> dict[str, tuple[Path, str]]:
    manifest = _read_object(source_dir / "admission_manifest.json", "admission manifest")
    rows = manifest.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise ValueError("admission manifest artifacts must be nonempty")
    result: dict[str, tuple[Path, str]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("admission manifest artifact row must be an object")
        path = row.get("path")
        digest = row.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            raise ValueError("admission manifest artifact row is invalid")
        result[path] = (source_dir / path, digest)
    return result


def materialize_profile(
    *,
    config_path: Path,
    profile_id: str,
    source_dir: Path,
    destination_dir: Path | None = None,
) -> dict[str, Any]:
    config = _read_object(config_path, "target config")
    profile = _profile(config, profile_id)
    target_dir = destination_dir if destination_dir is not None else Path(str(profile["artifact_dir"]))
    validate_profile(
        config_path=config_path,
        profile_id=profile_id,
        artifact_dir=source_dir,
    )
    artifact_hashes = profile.get("artifact_sha256")
    if not isinstance(artifact_hashes, Mapping):
        raise ValueError("profile artifact_sha256 must be an object")
    copied: set[str] = set()
    for name, digest in artifact_hashes.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ValueError("profile artifact hash rows must be string:string")
        _copy_verified(source_dir / name, target_dir / name, digest)
        copied.add(name)
    for relative_path, (src, digest) in _manifest_artifacts(source_dir).items():
        _copy_verified(src, target_dir / relative_path, digest)
        copied.add(relative_path)
    pipeline = _read_object(source_dir / "pipeline_result.json", "pipeline result")
    for relative_path, (src, digest) in _report_artifacts(source_dir, pipeline).items():
        _copy_verified(src, target_dir / relative_path, digest)
        copied.add(relative_path)
    validation = validate_profile(
        config_path=config_path,
        profile_id=profile_id,
        artifact_dir=target_dir,
    )
    return {
        "status": "pass",
        "profile_id": profile_id,
        "source_dir": source_dir.as_posix(),
        "artifact_dir": target_dir.as_posix(),
        "copied_artifacts": sorted(copied),
        "validation": validation,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--destination-dir", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(materialize_profile(
        config_path=args.target_config,
        profile_id=args.profile_id,
        source_dir=args.source_dir,
        destination_dir=args.destination_dir,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
