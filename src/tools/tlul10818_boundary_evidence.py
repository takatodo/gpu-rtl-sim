"""Pure evidence assembly for externally executed TL-UL #10818 sweeps."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tlul10818_boundary_json import json_copy, sha256_json
from tlul10818_boundary_points import (
    raw_points_by_id,
    target_projection_keys,
    validate_revision_projection,
)
from tlul10818_boundary_trials import (
    SelectorAdapter,
    TimingAdapter,
    build_boundary_trial_evidence,
)

__all__ = [
    "SelectorAdapter",
    "TimingAdapter",
    "build_boundary_evidence_bundle",
    "build_boundary_trial_evidence",
]


def _validate_trial_evidence_shape(raw_trials: Any, contract: Mapping[str, Any]) -> list[Any]:
    if not isinstance(raw_trials, list) or not raw_trials:
        raise ValueError("raw trial evidence must be a nonempty list")
    expected_trial_ids = {
        trial["trial_id"]
        for trial in contract.get("trials", [])
        if isinstance(trial, Mapping) and isinstance(trial.get("trial_id"), str)
    }
    if not expected_trial_ids:
        raise ValueError("experiment Contract trials are invalid")
    observed_trial_ids: list[str] = []
    required_fields = {
        "trial_id",
        "policy_trial",
        "fixed_confirmations",
        "executions",
        "launches",
        "trial_wall_time_ns",
    }
    for trial in raw_trials:
        if not isinstance(trial, Mapping):
            raise ValueError("raw trial evidence rows must be objects")
        if set(trial) != required_fields:
            raise ValueError("raw trial evidence row shape is invalid")
        trial_id = trial.get("trial_id")
        if not isinstance(trial_id, str) or not trial_id:
            raise ValueError("raw trial evidence trial_id is invalid")
        observed_trial_ids.append(trial_id)
        if not isinstance(trial.get("policy_trial"), Mapping):
            raise ValueError("raw trial evidence policy_trial must be an object")
        if not isinstance(trial.get("fixed_confirmations"), list):
            raise ValueError("raw trial evidence fixed_confirmations must be a list")
        if not isinstance(trial.get("executions"), list) or not trial["executions"]:
            raise ValueError("raw trial evidence executions must be a nonempty list")
        if not isinstance(trial.get("launches"), list) or not trial["launches"]:
            raise ValueError("raw trial evidence launches must be a nonempty list")
        wall_time = trial.get("trial_wall_time_ns")
        if isinstance(wall_time, bool) or not isinstance(wall_time, int) or wall_time < 0:
            raise ValueError("raw trial evidence trial_wall_time_ns is invalid")
    if len(set(observed_trial_ids)) != len(observed_trial_ids):
        raise ValueError("raw trial evidence contains duplicate trial_id")
    if set(observed_trial_ids) != expected_trial_ids:
        raise ValueError("raw trial evidence does not cover the Experiment Contract trials")
    return json_copy(raw_trials)


def _normalized_observation_rows(
    contract: Mapping[str, Any], raw_points: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    projection_keys, oracle_field = target_projection_keys(contract)
    action_domain, raw_by_id = raw_points_by_id(contract, raw_points)
    ground_truth_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []
    for action in action_domain:
        point_id = action["point_id"]
        revisions = raw_by_id[point_id].get("revisions")
        if not isinstance(revisions, Mapping) or set(revisions) != {"bad", "fixed"}:
            raise ValueError("point result revisions must contain bad and fixed")
        normalized_revisions: dict[str, Any] = {}
        oracles: dict[str, int] = {}
        for label in ("bad", "fixed"):
            normalized_revisions[label], oracles[label] = validate_revision_projection(
                revisions[label], projection_keys, oracle_field
            )
        ground_truth_rows.append(
            {
                "point_id": point_id,
                "parameters": json_copy(action["parameters"]),
                "bad_oracle": oracles["bad"],
                "fixed_oracle": oracles["fixed"],
            }
        )
        semantic_rows.append(
            {"point_id": point_id, "revisions": normalized_revisions}
        )
    return ground_truth_rows, semantic_rows


def build_boundary_evidence_bundle(
    contract_bundle: Mapping[str, Any], run_result: Mapping[str, Any]
) -> dict[str, Any]:
    """Derive sidecar ground truth and semantic observations from raw results."""
    if not isinstance(contract_bundle, Mapping) or set(contract_bundle) != {
        "experiment_contract",
        "semantic_manifests",
    }:
        raise ValueError("contract bundle shape is invalid")
    contract = contract_bundle["experiment_contract"]
    manifests = contract_bundle["semantic_manifests"]
    if (
        not isinstance(contract, Mapping)
        or contract.get("surface") != "rtl_boundary_experiment_contract"
    ):
        raise ValueError("experiment Contract is invalid")
    if not isinstance(manifests, Mapping) or set(manifests) != {"bad", "fixed"}:
        raise ValueError("semantic manifests must contain bad and fixed")
    target = contract.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("experiment Contract target is invalid")
    manifest_hashes = target.get("semantic_manifest_sha256")
    if not isinstance(manifest_hashes, Mapping) or any(
        manifest_hashes.get(label) != sha256_json(manifests[label])
        for label in ("bad", "fixed")
    ):
        raise ValueError("semantic manifests do not match the Experiment Contract")
    if not isinstance(run_result, Mapping) or set(run_result) != {
        "runner",
        "point_results",
        "trials",
    }:
        raise ValueError("run result shape is invalid")
    runner = run_result["runner"]
    if (
        not isinstance(runner, Mapping)
        or set(runner) != {"status", "identity", "completed_at"}
        or runner.get("status") != "pass"
        or not isinstance(runner.get("identity"), str)
        or not runner["identity"]
        or not isinstance(runner.get("completed_at"), str)
        or not runner["completed_at"]
    ):
        raise ValueError("external runner completion identity is invalid")
    ground_truth_rows, semantic_rows = _normalized_observation_rows(
        contract, run_result["point_results"]
    )
    trials = _validate_trial_evidence_shape(run_result["trials"], contract)
    return {
        "schema_version": 1,
        "surface": "rtl_boundary_evidence_bundle",
        "experiment_contract_sha256": sha256_json(contract),
        "runner": json_copy(runner),
        "semantic_manifests": json_copy(manifests),
        "ground_truth": {
            "schema_version": 1,
            "surface": "rtl_boundary_ground_truth",
            "sweep_space_sha256": contract["sweep_space_sha256"],
            "observations": ground_truth_rows,
        },
        "semantic_observations": semantic_rows,
        "trials": trials,
    }
