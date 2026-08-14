"""Pure semantic-identity projection for the TL-UL #10818 benchmark."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from tlul10818_gpu_schedule import boundary_contract_projection


POLICY_KINDS = {
    "random", "stratified", "ordered_refinement", "novelty_boundary_guided"
}

def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _descriptor(raw: Any, label: str) -> tuple[dict[str, Any], str]:
    if not isinstance(raw, Mapping) or set(raw) != {
        "name", "rtl_signal", "semantic_id", "width_bits"
    }:
        raise ValueError(f"{label} must contain name, rtl_signal, semantic_id, and width_bits")
    for field in ("name", "rtl_signal", "semantic_id"):
        if not isinstance(raw.get(field), str) or not raw[field]:
            raise ValueError(f"{label} {field} must be a nonempty string")
    width = raw.get("width_bits")
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ValueError(f"{label} width_bits must be a positive integer")
    return {
        "name": raw["name"],
        "semantic_id": raw["semantic_id"],
        "width_bits": width,
    }, raw["rtl_signal"]


def build_boundary_semantic_identity(target_config: Mapping[str, Any]) -> dict[str, Any]:
    """Build the Experiment Contract target and paired semantic manifests."""
    if not isinstance(target_config, Mapping):
        raise ValueError("target config must be an object")
    target = target_config.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("target config must contain target")
    required = {
        "target_id", "issue", "ip", "checkpoint_identity", "oracle_identity",
        "bad_revision", "fixed_revision", "semantic_projection",
    }
    if set(target) != required:
        raise ValueError("target config target fields do not match semantic identity Contract")
    for field in required - {"semantic_projection"}:
        value = target[field]
        if not isinstance(value, str) or not value:
            raise ValueError(f"target {field} must be a nonempty string")
    revisions = {"bad": target["bad_revision"], "fixed": target["fixed_revision"]}
    if any(len(value) != 40 or any(c not in "0123456789abcdef" for c in value)
           for value in revisions.values()) or revisions["bad"] == revisions["fixed"]:
        raise ValueError("bad and fixed revisions must be distinct lowercase Git SHAs")
    projection = target["semantic_projection"]
    if not isinstance(projection, Mapping) or set(projection) != {"observables", "oracle"}:
        raise ValueError("semantic_projection must contain observables and oracle")
    raw_observables = projection["observables"]
    if not isinstance(raw_observables, list) or not raw_observables:
        raise ValueError("semantic observables must be a nonempty list")
    observables: list[dict[str, Any]] = []
    rtl_signals: list[str] = []
    for index, raw in enumerate(raw_observables):
        descriptor, rtl_signal = _descriptor(raw, f"semantic observable {index}")
        observables.append(descriptor)
        rtl_signals.append(rtl_signal)
    oracle, oracle_rtl_signal = _descriptor(projection["oracle"], "semantic oracle")
    all_descriptors = observables + [oracle]
    for field in ("name", "semantic_id"):
        values = [row[field] for row in all_descriptors]
        if len(values) != len(set(values)):
            raise ValueError(f"semantic {field} values must be unique")
    if len(rtl_signals + [oracle_rtl_signal]) != len(set(rtl_signals + [oracle_rtl_signal])):
        raise ValueError("semantic rtl_signal values must be unique")
    manifests = {
        label: {
            "schema_version": 1,
            "surface": "rtl_boundary_semantic_manifest",
            "target_id": target["target_id"],
            "revision_label": label,
            "revision_sha": revision,
            "checkpoint_identity": target["checkpoint_identity"],
            "oracle_identity": target["oracle_identity"],
            "observables": [dict(row) for row in all_descriptors],
        }
        for label, revision in revisions.items()
    }
    return {
        "target": {
            "target_id": target["target_id"],
            "issue": target["issue"],
            "ip": target["ip"],
            "checkpoint_identity": target["checkpoint_identity"],
            "oracle_identity": target["oracle_identity"],
            "revisions": revisions,
            "semantic_observables": [row["name"] for row in observables],
            "oracle_field": oracle["name"],
            "semantic_manifest_sha256": {
                label: _canonical_sha256(manifest)
                for label, manifest in manifests.items()
            },
        },
        "semantic_manifests": manifests,
    }


def _json_copy(value: Any, label: str) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False, ensure_ascii=True))
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError(f"{label} must be finite JSON data") from error


def build_boundary_experiment_contract(
    target_config: Mapping[str, Any],
    run_spec: Mapping[str, Any],
    sweep_enumerator: Any,
) -> dict[str, Any]:
    """Build a complete sidecar Contract without executing the DUT."""
    if not isinstance(run_spec, Mapping) or set(run_spec) != {
        "experiment_id", "finite_axis_values", "backends", "trials", "comparisons"
    }:
        raise ValueError("run spec fields do not match the Experiment Contract builder")
    experiment_id = run_spec["experiment_id"]
    if not isinstance(experiment_id, str) or not experiment_id:
        raise ValueError("run spec experiment_id must be a nonempty string")
    finite_values = run_spec["finite_axis_values"]
    if not isinstance(finite_values, Mapping) or set(finite_values) != {
        "backpressure_cycles", "response_delay_cycles"
    }:
        raise ValueError("run spec finite_axis_values do not match the runner axes")
    projection = boundary_contract_projection(
        backpressure_cycles=finite_values["backpressure_cycles"],
        response_delay_cycles=finite_values["response_delay_cycles"],
        sweep_enumerator=sweep_enumerator,
    )
    semantic = build_boundary_semantic_identity(target_config)
    backends = _json_copy(run_spec["backends"], "run spec backends")
    trials = _json_copy(run_spec["trials"], "run spec trials")
    comparisons = _json_copy(run_spec["comparisons"], "run spec comparisons")
    if not all(isinstance(value, list) and value for value in (backends, trials, comparisons)):
        raise ValueError("run spec backends, trials, and comparisons must be nonempty lists")
    backend_by_id = {
        row.get("backend_id"): row for row in backends if isinstance(row, Mapping)
    }
    trial_by_id = {
        row.get("trial_id"): row for row in trials if isinstance(row, Mapping)
    }
    if len(backend_by_id) != len(backends) or len(trial_by_id) != len(trials):
        raise ValueError("run spec backend and trial IDs must be present and unique")

    def policy_kind(trial: Mapping[str, Any]) -> Any:
        policy = trial.get("policy")
        return policy.get("kind") if isinstance(policy, Mapping) else None

    if {policy_kind(trial) for trial in trials} != POLICY_KINDS:
        raise ValueError("run spec must contain exactly the four declared policy kinds")
    selector_ok = False
    backend_ok = False
    for comparison in comparisons:
        if not isinstance(comparison, Mapping):
            raise ValueError("run spec comparison must be an object")
        members = [trial_by_id.get(trial_id) for trial_id in comparison.get("trial_ids", [])]
        if not members or any(member is None for member in members):
            raise ValueError("run spec comparison references an unknown trial")
        budgets = {
            (member.get("requested_count"), member.get("budget_logical_bad_queries"))
            for member in members
        }
        if comparison.get("kind") == "selector":
            backend_ids = {member.get("backend_id") for member in members}
            kinds = {policy_kind(member) for member in members}
            selector_ok = selector_ok or (
                kinds == POLICY_KINDS
                and len(backend_ids) == 1
                and backend_by_id.get(next(iter(backend_ids)), {}).get("kind") == "gpu"
                and len(budgets) == 1
            )
        elif comparison.get("kind") == "backend" and len(members) == 2:
            backend_kinds = {
                backend_by_id.get(member.get("backend_id"), {}).get("kind")
                for member in members
            }
            backend_ok = backend_ok or (
                backend_kinds == {"cpu", "gpu"}
                and _canonical_sha256(members[0].get("policy"))
                == _canonical_sha256(members[1].get("policy"))
                and len(budgets) == 1
            )
    if not selector_ok or not backend_ok:
        raise ValueError("run spec lacks the required fair selector/backend comparisons")
    contract = {
        "schema_version": 1,
        "surface": "rtl_boundary_experiment_contract",
        "experiment_id": experiment_id,
        "target": semantic["target"],
        **projection,
        "reconstructor": {"kind": "nearest_observed_graph", "algorithm_version": 1},
        "backends": backends,
        "trials": trials,
        "comparisons": comparisons,
    }
    return {
        "experiment_contract": contract,
        "semantic_manifests": semantic["semantic_manifests"],
    }
