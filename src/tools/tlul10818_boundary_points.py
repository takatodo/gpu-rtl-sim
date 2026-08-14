"""Validate raw TL-UL #10818 boundary point observations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tlul10818_boundary_json import canonical_bytes, json_copy


def target_projection_keys(contract: Mapping[str, Any]) -> tuple[set[Any], Any]:
    target = contract.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("experiment Contract target is invalid")
    projection_keys = set(target.get("semantic_observables", [])) | {
        target.get("oracle_field")
    }
    oracle_field = target.get("oracle_field")
    if None in projection_keys or not projection_keys:
        raise ValueError("target semantic projection is invalid")
    return projection_keys, oracle_field


def raw_points_by_id(
    contract: Mapping[str, Any], raw_points: Any
) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    action_domain = contract.get("action_domain")
    if not isinstance(action_domain, list) or not isinstance(raw_points, list):
        raise ValueError("action domain and point results must be lists")
    raw_by_id: dict[str, Mapping[str, Any]] = {}
    for raw in raw_points:
        if (
            not isinstance(raw, Mapping)
            or set(raw) - {"point_id", "revisions", "coverage_feature_ids"}
        ):
            raise ValueError("point result shape is invalid")
        point_id = raw.get("point_id")
        if not isinstance(point_id, str) or point_id in raw_by_id:
            raise ValueError("point result ID is invalid or duplicated")
        raw_by_id[point_id] = raw
    expected_ids = [row.get("point_id") for row in action_domain]
    if len(set(expected_ids)) != len(expected_ids) or set(raw_by_id) != set(expected_ids):
        raise ValueError("point results do not cover the complete action domain")
    return action_domain, raw_by_id


def validate_revision_projection(
    revision: Any, projection_keys: set[Any], oracle_field: Any
) -> tuple[dict[str, Any], int]:
    if not isinstance(revision, Mapping) or set(revision) != {"cpu", "gpu"}:
        raise ValueError("revision result must contain CPU and GPU projections")
    cpu = revision["cpu"]
    gpu = revision["gpu"]
    if not isinstance(cpu, Mapping) or not isinstance(gpu, Mapping):
        raise ValueError("CPU and GPU projections must be objects")
    if set(cpu) != projection_keys or set(gpu) != projection_keys:
        raise ValueError("CPU/GPU projection keys do not match semantic identity")
    if canonical_bytes(cpu) != canonical_bytes(gpu):
        raise ValueError("CPU/GPU semantic projections do not match")
    oracle = cpu[oracle_field]
    if isinstance(oracle, bool) or not isinstance(oracle, int) or oracle not in (0, 1):
        raise ValueError("semantic oracle must be integer 0 or 1")
    return {"cpu": json_copy(cpu), "gpu": json_copy(gpu)}, oracle


def oracle_and_coverage_by_point(
    contract: Mapping[str, Any], raw_points: Any
) -> tuple[dict[str, dict[str, int]], dict[str, list[str]]]:
    projection_keys, oracle_field = target_projection_keys(contract)
    action_domain, raw_by_id = raw_points_by_id(contract, raw_points)
    oracles: dict[str, dict[str, int]] = {}
    coverage: dict[str, list[str]] = {}
    for action in action_domain:
        point_id = action.get("point_id")
        raw = raw_by_id[point_id]
        revisions = raw.get("revisions")
        if not isinstance(revisions, Mapping) or set(revisions) != {"bad", "fixed"}:
            raise ValueError("point result revisions must contain bad and fixed")
        raw_features = raw.get("coverage_feature_ids", [])
        if (
            not isinstance(raw_features, list)
            or not all(isinstance(feature, str) and feature for feature in raw_features)
            or len(set(raw_features)) != len(raw_features)
        ):
            raise ValueError("point result coverage features are invalid")
        coverage[point_id] = list(raw_features)
        oracles[point_id] = {}
        for label in ("bad", "fixed"):
            _, oracle = validate_revision_projection(
                revisions[label], projection_keys, oracle_field
            )
            oracles[point_id][label] = oracle
    return oracles, coverage
