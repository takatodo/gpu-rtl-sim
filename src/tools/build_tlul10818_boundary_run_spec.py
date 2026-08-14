#!/usr/bin/env python3
"""Build a TL-UL #10818 boundary run spec from external experiment choices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


POLICY_KINDS = (
    "random",
    "stratified",
    "refinement",
    "novelty",
)


def _positive_int(text: str, label: str) -> int:
    try:
        value = int(text, 10)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{label} must be a positive integer") from error
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{label} must be a positive integer")
    return value


def _axis_values(text: str) -> list[int]:
    try:
        values = [int(item, 10) for item in text.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("axis values must be comma-separated integers") from error
    if not values or any(value < 0 for value in values):
        raise argparse.ArgumentTypeError("axis values must be nonnegative integers")
    if len(values) != len(set(values)) or values != sorted(values):
        raise argparse.ArgumentTypeError("axis values must be unique and increasing")
    return values


def _sha256_text(text: str) -> str:
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise argparse.ArgumentTypeError("seed must be a lowercase SHA-256 hex string")
    return text


def _nonempty(text: str, label: str) -> str:
    if not text:
        raise argparse.ArgumentTypeError(f"{label} must be nonempty")
    return text


def build_run_spec(
    *,
    experiment_id: str,
    backpressure_cycles: Sequence[int],
    response_delay_cycles: Sequence[int],
    cpu_executor_identity: str,
    gpu_executor_identity: str,
    gpu_resident_width: int,
    requested_count: int,
    budget_logical_bad_queries: int,
    seed_sha256: str,
) -> dict[str, object]:
    policies = {
        "random": {
            "kind": "random",
            "algorithm_version": 1,
            "seed_sha256": seed_sha256,
            "configuration": {},
        },
        "stratified": {
            "kind": "stratified",
            "algorithm_version": 1,
            "seed_sha256": seed_sha256,
            "configuration": {"strata_axes": ["request_integrity"]},
        },
        "refinement": {
            "kind": "ordered_refinement",
            "algorithm_version": 1,
            "seed_sha256": seed_sha256,
            "configuration": {"axis": "backpressure_cycles"},
        },
        "novelty": {
            "kind": "novelty_boundary_guided",
            "algorithm_version": 1,
            "seed_sha256": seed_sha256,
            "configuration": {},
        },
    }
    trials = [
        {
            "trial_id": f"{name}_gpu",
            "backend_id": "gpu",
            "policy": policies[name],
            "requested_count": requested_count,
            "budget_logical_bad_queries": budget_logical_bad_queries,
        }
        for name in POLICY_KINDS
    ]
    trials.append(
        {
            "trial_id": "random_cpu",
            "backend_id": "cpu",
            "policy": policies["random"],
            "requested_count": requested_count,
            "budget_logical_bad_queries": budget_logical_bad_queries,
        }
    )
    return {
        "experiment_id": experiment_id,
        "finite_axis_values": {
            "backpressure_cycles": list(backpressure_cycles),
            "response_delay_cycles": list(response_delay_cycles),
        },
        "backends": [
            {
                "backend_id": "cpu",
                "kind": "cpu",
                "executor_identity": cpu_executor_identity,
                "resident_width": 1,
            },
            {
                "backend_id": "gpu",
                "kind": "gpu",
                "executor_identity": gpu_executor_identity,
                "resident_width": gpu_resident_width,
            },
        ],
        "trials": trials,
        "comparisons": [
            {
                "comparison_id": "selectors-on-gpu",
                "kind": "selector",
                "trial_ids": [f"{name}_gpu" for name in POLICY_KINDS],
            },
            {
                "comparison_id": "random-cpu-gpu",
                "kind": "backend",
                "trial_ids": ["random_cpu", "random_gpu"],
            },
        ],
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True, type=lambda text: _nonempty(text, "experiment-id"))
    parser.add_argument("--backpressure-cycles", required=True, type=_axis_values)
    parser.add_argument("--response-delay-cycles", required=True, type=_axis_values)
    parser.add_argument("--cpu-executor-identity", required=True, type=lambda text: _nonempty(text, "cpu-executor-identity"))
    parser.add_argument("--gpu-executor-identity", required=True, type=lambda text: _nonempty(text, "gpu-executor-identity"))
    parser.add_argument("--gpu-resident-width", required=True, type=lambda text: _positive_int(text, "gpu-resident-width"))
    parser.add_argument("--requested-count", required=True, type=lambda text: _positive_int(text, "requested-count"))
    parser.add_argument("--budget-logical-bad-queries", required=True, type=lambda text: _positive_int(text, "budget-logical-bad-queries"))
    parser.add_argument("--seed-sha256", required=True, type=_sha256_text)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    values = vars(args).copy()
    out = values.pop("out")
    _write_json(out, build_run_spec(**values))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
