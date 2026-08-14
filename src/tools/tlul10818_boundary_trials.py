"""Build selector-trial evidence for TL-UL #10818 boundary runs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable, Sequence

from tlul10818_boundary_json import json_copy
from tlul10818_boundary_points import oracle_and_coverage_by_point


SelectorAdapter = Callable[
    [Mapping[str, Any], Mapping[str, Any], Sequence[Mapping[str, Any]], int],
    Sequence[str],
]
TimingAdapter = Callable[
    [str, int, Sequence[tuple[int, str, str, str]]],
    Mapping[str, Any],
]


def _validated_timing(
    timing: TimingAdapter,
    trial_id: str,
    launch_index: int,
    group: Sequence[tuple[int, str, str, str]],
) -> Mapping[str, Any]:
    timing_row = timing(trial_id, launch_index, group)
    if not isinstance(timing_row, Mapping):
        raise ValueError("trial timing Adapter must return an object")
    cycle_evals = timing_row.get("cycle_evals")
    start_offset_ns = timing_row.get("start_offset_ns")
    end_offset_ns = timing_row.get("end_offset_ns")
    if (
        isinstance(cycle_evals, bool)
        or not isinstance(cycle_evals, int)
        or cycle_evals < 0
    ):
        raise ValueError("trial timing cycle_evals is invalid")
    if (
        isinstance(start_offset_ns, bool)
        or not isinstance(start_offset_ns, int)
        or start_offset_ns < 0
        or isinstance(end_offset_ns, bool)
        or not isinstance(end_offset_ns, int)
        or end_offset_ns < start_offset_ns
    ):
        raise ValueError("trial timing offsets are invalid")
    return timing_row


def _trial_epochs(
    contract: Mapping[str, Any],
    trial_contract: Mapping[str, Any],
    selector: SelectorAdapter,
    oracles: Mapping[str, Mapping[str, int]],
    coverage: Mapping[str, list[str]],
) -> list[dict[str, Any]]:
    requested_count = trial_contract.get("requested_count")
    budget = trial_contract.get("budget_logical_bad_queries")
    if (
        isinstance(requested_count, bool)
        or not isinstance(requested_count, int)
        or requested_count <= 0
        or isinstance(budget, bool)
        or not isinstance(budget, int)
        or budget <= 0
    ):
        raise ValueError("experiment Contract trial budget is invalid")
    completed_batches: list[dict[str, Any]] = []
    epochs: list[dict[str, Any]] = []
    logical_bad_queries = 0
    seen_points: set[str] = set()
    while logical_bad_queries < budget:
        remaining = budget - logical_bad_queries
        raw_selected = selector(
            contract["sweep_space"],
            trial_contract["policy"],
            completed_batches,
            min(requested_count, remaining),
        )
        if not isinstance(raw_selected, Sequence) or isinstance(
            raw_selected, (str, bytes, bytearray)
        ):
            raise ValueError("selector returned an invalid point sequence")
        selected = list(raw_selected)
        if not selected:
            break
        if len(selected) > remaining:
            raise ValueError("selector exceeded the remaining trial budget")
        if any(
            not isinstance(point_id, str)
            or point_id not in oracles
            or point_id in seen_points
            for point_id in selected
        ):
            raise ValueError("selector returned an invalid or repeated point")
        observations = [
            {
                "point_id": point_id,
                "bad_oracle": oracles[point_id]["bad"],
                "coverage_feature_ids": coverage[point_id],
            }
            for point_id in selected
        ]
        epoch = {
            "epoch_index": len(epochs),
            "selected_point_ids": selected,
            "bad_observations": observations,
        }
        epochs.append(epoch)
        completed_batches.append(
            {"selected_point_ids": selected, "bad_observations": observations}
        )
        seen_points.update(selected)
        logical_bad_queries += len(selected)
    return epochs


def _execution_groups(
    epochs: Sequence[Mapping[str, Any]],
    confirmations: Sequence[Mapping[str, Any]],
    resident_width: int,
) -> list[list[tuple[int, str, str, str]]]:
    execution_specs = [
        (epoch["epoch_index"], point_id, "bad", "bad_search")
        for epoch in epochs
        for point_id in epoch["selected_point_ids"]
    ] + [
        (
            confirmation["epoch_index"],
            confirmation["point_id"],
            "fixed",
            "fixed_confirmation",
        )
        for confirmation in confirmations
    ]
    groups: list[list[tuple[int, str, str, str]]] = []
    for epoch_index in range(len(epochs)):
        for role in (("bad", "bad_search"), ("fixed", "fixed_confirmation")):
            role_specs = [
                spec
                for spec in execution_specs
                if spec[0] == epoch_index and spec[2:] == role
            ]
            for offset in range(0, len(role_specs), resident_width):
                groups.append(role_specs[offset : offset + resident_width])
    return groups


def build_boundary_trial_evidence(
    contract: Mapping[str, Any],
    point_results: Sequence[Mapping[str, Any]],
    selector: SelectorAdapter,
    timing: TimingAdapter,
) -> list[dict[str, Any]]:
    """Build sidecar-ready selector trial evidence from complete raw point results."""
    oracles, coverage = oracle_and_coverage_by_point(contract, point_results)
    backend_by_id = {
        backend["backend_id"]: backend
        for backend in contract.get("backends", [])
        if isinstance(backend, Mapping) and isinstance(backend.get("backend_id"), str)
    }
    if not backend_by_id:
        raise ValueError("experiment Contract backends are invalid")
    trials: list[dict[str, Any]] = []
    for trial_contract in contract.get("trials", []):
        if not isinstance(trial_contract, Mapping):
            raise ValueError("experiment Contract trial is invalid")
        trial_id = trial_contract.get("trial_id")
        backend = backend_by_id.get(trial_contract.get("backend_id"))
        if not isinstance(trial_id, str) or backend is None:
            raise ValueError("experiment Contract trial identity is invalid")
        epochs = _trial_epochs(contract, trial_contract, selector, oracles, coverage)
        confirmations = [
            {
                "point_id": observation["point_id"],
                "epoch_index": epoch["epoch_index"],
                "fixed_oracle": oracles[observation["point_id"]]["fixed"],
            }
            for epoch in epochs
            for observation in epoch["bad_observations"]
            if observation["bad_oracle"] == 1
        ]
        groups = _execution_groups(epochs, confirmations, backend["resident_width"])
        executions: list[dict[str, Any]] = []
        launches: list[dict[str, Any]] = []
        for launch_index, group in enumerate(groups):
            launch_id = f"{trial_id}:launch:{launch_index}"
            timing_row = _validated_timing(timing, trial_id, launch_index, group)
            execution_ids: list[str] = []
            for epoch_index, point_id, revision, purpose in group:
                execution_id = f"{trial_id}:execution:{len(executions)}"
                execution_ids.append(execution_id)
                executions.append(
                    {
                        "execution_id": execution_id,
                        "epoch_index": epoch_index,
                        "point_id": point_id,
                        "revision": revision,
                        "purpose": purpose,
                        "launch_id": launch_id,
                        "cycle_evals": timing_row["cycle_evals"],
                    }
                )
            launches.append(
                {
                    "launch_id": launch_id,
                    "backend_id": backend["backend_id"],
                    "executor_identity": backend["executor_identity"],
                    "resident_width": backend["resident_width"],
                    "execution_ids": execution_ids,
                    "start_offset_ns": timing_row["start_offset_ns"],
                    "end_offset_ns": timing_row["end_offset_ns"],
                }
            )
        if not epochs or not executions or not launches:
            raise ValueError("trial evidence did not schedule any execution")
        trials.append(
            {
                "trial_id": trial_id,
                "policy_trial": {
                    "schema_version": 1,
                    "surface": "rtl_boundary_policy_trial",
                    "sweep_space_sha256": contract["sweep_space_sha256"],
                    "policy": json_copy(trial_contract["policy"]),
                    "reconstructor": json_copy(contract["reconstructor"]),
                    "requested_count": trial_contract["requested_count"],
                    "budget_logical_bad_queries": trial_contract[
                        "budget_logical_bad_queries"
                    ],
                    "epochs": epochs,
                },
                "fixed_confirmations": confirmations,
                "executions": executions,
                "launches": launches,
                "trial_wall_time_ns": max(
                    launch["end_offset_ns"] for launch in launches
                ),
            }
        )
    return trials
