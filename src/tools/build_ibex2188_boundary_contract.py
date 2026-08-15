#!/usr/bin/env python3
"""Build formal sidecar boundary-contract inputs for Ibex #2188."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from build_ibex2188_cpu_ground_truth import _strict_object, _write_json
SCHEMA_VERSION = 1
TARGET_ID = "ibex2188"
def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()
def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
def _seed(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
def _observable_rows(target: Mapping[str, Any]) -> list[dict[str, Any]]:
    projection = target.get("semantic_projection")
    if not isinstance(projection, Mapping):
        raise ValueError("target semantic_projection is missing")
    observables = projection.get("observables")
    oracle = projection.get("oracle")
    if not isinstance(observables, list) or not isinstance(oracle, Mapping):
        raise ValueError("target semantic projection is malformed")
    rows = []
    for row in [*observables, oracle]:
        if not isinstance(row, Mapping):
            raise ValueError("semantic projection rows must be objects")
        rows.append({
            "name": row["name"],
            "semantic_id": row["semantic_id"],
            "width_bits": row["width_bits"],
        })
    return rows
def _manifest(target: Mapping[str, Any], label: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "surface": "rtl_boundary_semantic_manifest",
        "target_id": target["target_id"],
        "revision_label": label,
        "revision_sha": target[f"{label}_revision"],
        "checkpoint_identity": target["checkpoint_identity"],
        "oracle_identity": target["oracle_identity"],
        "observables": _observable_rows(target),
    }
def _policy(kind: str, seed: str, configuration: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": kind,
        "algorithm_version": 1,
        "seed_sha256": _seed(seed),
        "configuration": dict(configuration),
    }
def build(
    *,
    target_document: Mapping[str, Any],
    ground_truth: Mapping[str, Any],
    cpu_bundle: Mapping[str, Any],
    enumerate_sweep_space: Any,
) -> dict[str, Any]:
    target = target_document.get("target")
    admitted = target_document.get("admitted_cpu_sweep")
    if target_document.get("surface") != "ibex2188_boundary_benchmark_target":
        raise ValueError("target document surface mismatch")
    if not isinstance(target, Mapping) or target.get("target_id") != TARGET_ID:
        raise ValueError("target document does not describe ibex2188")
    if not isinstance(admitted, Mapping) or not isinstance(
        admitted.get("sweep_space"), Mapping
    ):
        raise ValueError("target document has no admitted CPU sweep")
    if ground_truth.get("surface") != "rtl_boundary_ground_truth":
        raise ValueError("ground truth surface mismatch")
    if cpu_bundle.get("surface") != "ibex2188_cpu_sweep_observations":
        raise ValueError("CPU observation bundle surface mismatch")
    if ground_truth.get("sweep_space_sha256") != cpu_bundle.get("sweep_space_sha256"):
        raise ValueError("ground truth and CPU bundle sweep hashes differ")
    enumeration = enumerate_sweep_space(admitted["sweep_space"])
    if enumeration["sweep_space_sha256"] != ground_truth.get("sweep_space_sha256"):
        raise ValueError("sweep hash does not match sidecar enumeration")
    manifests = {"bad": _manifest(target, "bad"), "fixed": _manifest(target, "fixed")}
    action_domain = [
        {
            "point_id": point["point_id"],
            "action": f"fault_enable:{point['parameters']['fault_enable']}",
            "parameters": point["parameters"],
        }
        for point in enumeration["points"]
    ]
    observable_names = [
        row["name"] for row in target["semantic_projection"]["observables"]
    ]
    oracle_field = target["semantic_projection"]["oracle"]["name"]
    point_count = enumeration["point_count"]
    policies = {
        "random": _policy("random", "ibex2188-random-v1", {}),
        "stratified": _policy(
            "stratified", "ibex2188-stratified-v1", {"strata_axes": ["fault_enable"]}
        ),
        "novelty": _policy("novelty_boundary_guided", "ibex2188-novelty-v1", {}),
    }
    gpu_trials = [
        {
            "trial_id": f"{name}_gpu",
            "backend_id": "gpu",
            "policy": policy,
            "requested_count": point_count,
            "budget_logical_bad_queries": point_count,
        }
        for name, policy in policies.items()
    ]
    cpu_trial = {
        "trial_id": "random_cpu",
        "backend_id": "cpu",
        "policy": policies["random"],
        "requested_count": point_count,
        "budget_logical_bad_queries": point_count,
    }
    contract = {
        "schema_version": SCHEMA_VERSION,
        "surface": "rtl_boundary_experiment_contract",
        "experiment_id": "ibex2188-boundary-v1",
        "target": {
            "target_id": TARGET_ID,
            "issue": target["issue"],
            "ip": target["ip"],
            "checkpoint_identity": target["checkpoint_identity"],
            "oracle_identity": target["oracle_identity"],
            "revisions": {
                "bad": target["bad_revision"],
                "fixed": target["fixed_revision"],
            },
            "semantic_observables": observable_names,
            "oracle_field": oracle_field,
            "semantic_manifest_sha256": {
                label: _sha256(manifest) for label, manifest in manifests.items()
            },
        },
        "sweep_space": admitted["sweep_space"],
        "sweep_space_sha256": enumeration["sweep_space_sha256"],
        "action_domain": action_domain,
        "action_domain_sha256": _sha256(action_domain),
        "reconstructor": {
            "kind": "nearest_observed_graph",
            "algorithm_version": 1,
        },
        "backends": [
            {
                "backend_id": "cpu",
                "kind": "cpu",
                "executor_identity": "ibex2188-cpu-runner:v1",
                "resident_width": 1,
            },
            {
                "backend_id": "gpu",
                "kind": "gpu",
                "executor_identity": "ibex2188-gpu-profile:pending-v1",
                "resident_width": point_count,
            },
        ],
        "trials": [*gpu_trials, cpu_trial],
        "comparisons": [
            {
                "comparison_id": "selector-on-gpu",
                "kind": "selector",
                "trial_ids": [trial["trial_id"] for trial in gpu_trials],
            },
            {
                "comparison_id": "random-backend",
                "kind": "backend",
                "trial_ids": ["random_cpu", "random_gpu"],
            },
        ],
    }
    profile = {
        "schema_version": SCHEMA_VERSION,
        "surface": "ibex2188_boundary_profile_inputs",
        "status": "experiment_contract_ready_gpu_evidence_pending",
        "experiment_contract_sha256": _sha256(contract),
        "semantic_manifest_sha256": {
            label: _sha256(manifest) for label, manifest in manifests.items()
        },
        "ground_truth_sha256": _sha256(ground_truth),
        "cpu_observation_bundle_sha256": _sha256(cpu_bundle),
        "source_file_sha256": {},
    }
    return {
        "experiment_contract": contract,
        "semantic_manifest_bad": manifests["bad"],
        "semantic_manifest_fixed": manifests["fixed"],
        "profile": profile,
    }
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--cpu-observation-bundle", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out_dir.exists():
        raise ValueError(f"refusing to replace existing output directory {args.out_dir}")
    sidecar_src = args.sidecar_root / "src"
    if not (sidecar_src / "verilator_model_sidecar" / "sweep_boundary.py").is_file():
        raise ValueError("sidecar root does not contain sweep_boundary.py")
    sys.path.insert(0, str(sidecar_src))
    from verilator_model_sidecar.sweep_boundary import enumerate_sweep_space
    outputs = build(
        target_document=_strict_object(args.target_config),
        ground_truth=_strict_object(args.ground_truth),
        cpu_bundle=_strict_object(args.cpu_observation_bundle),
        enumerate_sweep_space=enumerate_sweep_space,
    )
    args.out_dir.mkdir(parents=True)
    for name in (
        "experiment_contract",
        "semantic_manifest_bad",
        "semantic_manifest_fixed",
    ):
        value = outputs[name]
        path = args.out_dir / f"{name}.json"
        _write_json(path, value)
        outputs["profile"]["source_file_sha256"][path.name] = _sha256_file(path)
    _write_json(args.out_dir / "profile.json", outputs["profile"])
    print(json.dumps({
        "status": "pass",
        "out_dir": str(args.out_dir),
        "experiment_contract_sha256": outputs["profile"]["experiment_contract_sha256"],
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
