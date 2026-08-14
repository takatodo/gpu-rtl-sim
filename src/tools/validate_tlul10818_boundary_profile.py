#!/usr/bin/env python3
"""Validate pinned TL-UL #10818 boundary benchmark profile artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CONFIG = Path("config/tlul10818_boundary_benchmark.json")


def _read_object(path: Path, label: str) -> dict[str, Any]:
    def reject_constant(token: str) -> None:
        raise ValueError(f"{label} contains non-finite JSON token {token}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile(config: Mapping[str, Any], profile_id: str) -> Mapping[str, Any]:
    profiles = config.get("admitted_benchmark_profiles")
    if not isinstance(profiles, list):
        raise ValueError("config admitted_benchmark_profiles must be a list")
    matches = [
        profile
        for profile in profiles
        if isinstance(profile, Mapping) and profile.get("profile_id") == profile_id
    ]
    if len(matches) != 1:
        raise ValueError(f"profile {profile_id!r} must appear exactly once")
    return matches[0]


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _validate_artifact_hashes(profile: Mapping[str, Any], artifact_dir: Path) -> None:
    artifacts = _require_mapping(profile.get("artifact_sha256"), "artifact_sha256")
    if not artifacts:
        raise ValueError("artifact_sha256 must not be empty")
    for name, expected in artifacts.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError("artifact_sha256 rows must be string:string")
        path = artifact_dir / name
        if not path.is_file():
            raise ValueError(f"missing pinned artifact: {path}")
        observed = _sha256(path)
        if observed != expected:
            raise ValueError(f"artifact SHA mismatch for {name}: {observed} != {expected}")


def _validate_manifest(profile: Mapping[str, Any], artifact_dir: Path) -> None:
    manifest = _read_object(artifact_dir / "admission_manifest.json", "admission manifest")
    if manifest.get("status") != "pass":
        raise ValueError("admission manifest status must be pass")
    rows = manifest.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise ValueError("admission manifest artifacts must be nonempty")
    expected = _require_mapping(profile.get("artifact_sha256"), "artifact_sha256")
    for row in rows:
        row = _require_mapping(row, "admission manifest artifact row")
        role_path = row.get("path")
        digest = row.get("sha256")
        if not isinstance(role_path, str) or not isinstance(digest, str):
            raise ValueError("admission manifest artifact row is invalid")
        path = artifact_dir / role_path
        if not path.is_file():
            raise ValueError(f"admission manifest path is missing: {path}")
        if _sha256(path) != digest:
            raise ValueError(f"admission manifest SHA mismatch: {role_path}")
        if path.name in expected and expected[path.name] != digest:
            raise ValueError(f"profile/manifest SHA mismatch: {path.name}")


def _validate_run_spec(profile: Mapping[str, Any], artifact_dir: Path) -> None:
    spec = _read_object(artifact_dir / "run_spec.json", "run spec")
    if spec.get("experiment_id") != profile.get("experiment_id"):
        raise ValueError("run spec experiment_id does not match profile")
    if spec.get("finite_axis_values") != profile.get("finite_axis_values"):
        raise ValueError("run spec finite_axis_values do not match profile")


def _validate_runner_authority(profile: Mapping[str, Any], artifact_dir: Path) -> Mapping[str, Any]:
    authority = _require_mapping(profile.get("runtime_authority"), "runtime_authority")
    runner_identity = authority.get("runner_identity")
    authority_kind = authority.get("authority_kind")
    external_closure = authority.get("external_closure")
    if not isinstance(runner_identity, str) or not runner_identity:
        raise ValueError("runtime_authority runner_identity must be a nonempty string")
    if not isinstance(authority_kind, str) or not authority_kind:
        raise ValueError("runtime_authority authority_kind must be a nonempty string")
    if not isinstance(external_closure, bool):
        raise ValueError("runtime_authority external_closure must be a boolean")
    observations = _read_object(
        artifact_dir / "runner_observations.json", "runner observations"
    )
    runner = _require_mapping(observations.get("runner"), "runner observations runner")
    if runner.get("identity") != runner_identity:
        raise ValueError("runner identity does not match profile runtime_authority")
    if runner.get("status") != "pass":
        raise ValueError("runner observations status must be pass")
    return authority


def _validate_report_artifacts(profile: Mapping[str, Any], artifact_dir: Path, pipeline: Mapping[str, Any]) -> None:
    report_hashes = _require_mapping(profile.get("report_sha256"), "report_sha256")
    for label, artifact_key in (("graph_svg", "graph_artifact"), ("markdown_report", "markdown_artifact")):
        artifact = _require_mapping(pipeline.get(artifact_key), artifact_key)
        path = artifact.get("path")
        digest = artifact.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            raise ValueError(f"{artifact_key} is invalid")
        if report_hashes.get(label) != digest:
            raise ValueError(f"profile {label} SHA does not match pipeline")
        if _sha256(artifact_dir / path) != digest:
            raise ValueError(f"{artifact_key} file SHA mismatch")


def _validate_ground_truth(profile: Mapping[str, Any], pipeline: Mapping[str, Any]) -> None:
    if pipeline.get("status") != "pass":
        raise ValueError("pipeline status must be pass")
    adjudication = _require_mapping(pipeline.get("adjudication"), "adjudication")
    if adjudication.get("status") != "pass" or adjudication.get("issues") != []:
        raise ValueError("adjudication must pass with no issues")
    analysis = _require_mapping(adjudication.get("ground_truth_analysis"), "ground_truth_analysis")
    revisions = _require_mapping(analysis.get("revisions"), "ground_truth revisions")
    bad = _require_mapping(revisions.get("bad"), "bad ground truth")
    fixed = _require_mapping(revisions.get("fixed"), "fixed ground truth")
    bad_to_fixed = _require_mapping(analysis.get("bad_to_fixed"), "bad_to_fixed")
    summary = _require_mapping(profile.get("ground_truth_summary"), "ground_truth_summary")
    observed = {
        "bad_fail_point_count": bad.get("fail_point_count"),
        "bad_pass_point_count": bad.get("pass_point_count"),
        "bad_boundary_edge_count": bad.get("boundary_edge_count"),
        "bad_failure_component_count": bad.get("failure_component_count"),
        "bad_minimal_failing_point_count": len(
            _require_mapping(bad.get("minimal_failing_points"), "bad minimal_failing_points").get("point_ids", [])
        ),
        "fixed_fail_point_count": fixed.get("fail_point_count"),
        "bad_to_fixed_disappeared_failure_count": len(
            bad_to_fixed.get("disappeared_failure_point_ids", [])
        ),
    }
    if analysis.get("point_count") != profile.get("point_count"):
        raise ValueError("ground truth point_count does not match profile")
    if observed != summary:
        raise ValueError(f"ground truth summary mismatch: {observed} != {summary}")
    comparison_ids = _require_mapping(profile.get("comparison_ids"), "comparison_ids")
    selector_ids = [row.get("comparison_id") for row in adjudication.get("selector_comparisons", [])]
    backend_ids = [row.get("comparison_id") for row in adjudication.get("backend_comparisons", [])]
    if selector_ids != comparison_ids.get("selector") or backend_ids != comparison_ids.get("backend"):
        raise ValueError("comparison IDs do not match profile")


def validate_profile(*, config_path: Path, profile_id: str, artifact_dir: Path | None = None) -> dict[str, Any]:
    config = _read_object(config_path, "target config")
    profile = _profile(config, profile_id)
    root = artifact_dir if artifact_dir is not None else Path(str(profile["artifact_dir"]))
    _validate_artifact_hashes(profile, root)
    _validate_manifest(profile, root)
    _validate_run_spec(profile, root)
    runtime_authority = _validate_runner_authority(profile, root)
    pipeline = _read_object(root / "pipeline_result.json", "pipeline result")
    _validate_report_artifacts(profile, root, pipeline)
    _validate_ground_truth(profile, pipeline)
    return {
        "status": "pass",
        "profile_id": profile_id,
        "artifact_dir": root.as_posix(),
        "runtime_authority": runtime_authority,
        "point_count": profile["point_count"],
        "ground_truth_summary": profile["ground_truth_summary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(validate_profile(
        config_path=args.target_config,
        profile_id=args.profile_id,
        artifact_dir=args.artifact_dir,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
