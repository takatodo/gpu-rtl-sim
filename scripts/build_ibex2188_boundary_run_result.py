#!/usr/bin/env python3
"""Build an Ibex #2188 boundary run result from external runner observations.

Joins already produced per-point observations with the public sidecar selector
ABI and runner-owned timing rows, then writes the ``run_result.json`` consumed
by the sidecar evidence builder.  No RTL is compiled or executed here.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tools"))

from ibex2188_boundary_runner_io import read_object, sha256, write_json  # noqa: E402
from ibex2188_boundary_trials import build_boundary_trial_evidence  # noqa: E402


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _runner_identity(raw_runner: Any) -> dict[str, str]:
    if not isinstance(raw_runner, Mapping) or set(raw_runner) != {
        "status",
        "identity",
        "completed_at",
    }:
        raise ValueError("runner must contain status, identity, and completed_at")
    if raw_runner.get("status") != "pass":
        raise ValueError("runner status must be pass")
    return {
        "status": "pass",
        "identity": _nonempty_string(raw_runner.get("identity"), "runner identity"),
        "completed_at": _nonempty_string(
            raw_runner.get("completed_at"), "runner completed_at"
        ),
    }


def _timing_rows(raw_rows: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ValueError("timing must be a nonempty list")
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, Mapping) or set(raw) != {
            "trial_id",
            "launch_index",
            "cycle_evals",
            "start_offset_ns",
            "end_offset_ns",
        }:
            raise ValueError(f"timing row {index} shape is invalid")
        trial_id = _nonempty_string(raw.get("trial_id"), f"timing row {index} trial_id")
        launch_index = _nonnegative_int(
            raw.get("launch_index"), f"timing row {index} launch_index"
        )
        cycle_evals = _nonnegative_int(
            raw.get("cycle_evals"), f"timing row {index} cycle_evals"
        )
        start = _nonnegative_int(
            raw.get("start_offset_ns"), f"timing row {index} start_offset_ns"
        )
        end = _nonnegative_int(
            raw.get("end_offset_ns"), f"timing row {index} end_offset_ns"
        )
        if end < start:
            raise ValueError(f"timing row {index} end_offset_ns precedes start")
        rows.append(
            {
                "trial_id": trial_id,
                "launch_index": launch_index,
                "cycle_evals": cycle_evals,
                "start_offset_ns": start,
                "end_offset_ns": end,
            }
        )
    return rows


def _load_selector(sidecar_src: Path | None):
    if sidecar_src is not None:
        sys.path.insert(0, sidecar_src.as_posix())
    try:
        from verilator_model_sidecar.sweep_boundary import select_boundary_points
    except ImportError as error:
        raise ValueError(
            "verilator_model_sidecar.sweep_boundary.select_boundary_points is unavailable"
        ) from error
    return select_boundary_points


def build_run_result(
    *,
    experiment_contract: Mapping[str, Any],
    runner_observations: Mapping[str, Any],
    selector,
) -> dict[str, Any]:
    if not isinstance(experiment_contract, Mapping) or experiment_contract.get(
        "surface"
    ) != "rtl_boundary_experiment_contract":
        raise ValueError("experiment contract is invalid")
    if not isinstance(runner_observations, Mapping) or set(runner_observations) != {
        "runner",
        "point_results",
        "timing",
    }:
        raise ValueError("runner observations shape is invalid")
    runner = _runner_identity(runner_observations["runner"])
    point_results = runner_observations["point_results"]
    if not isinstance(point_results, list) or not point_results:
        raise ValueError("point_results must be a nonempty list")
    timing_rows = _timing_rows(runner_observations["timing"])
    timing_index = 0

    def timing_adapter(
        trial_id: str,
        launch_index: int,
        _group: Sequence[tuple[int, str, str, str]],
    ) -> Mapping[str, Any]:
        nonlocal timing_index
        if timing_index >= len(timing_rows):
            raise ValueError("runner timing is shorter than scheduled launches")
        row = timing_rows[timing_index]
        timing_index += 1
        if row["trial_id"] != trial_id or row["launch_index"] != launch_index:
            raise ValueError("runner timing order does not match scheduled launches")
        return {
            "cycle_evals": row["cycle_evals"],
            "start_offset_ns": row["start_offset_ns"],
            "end_offset_ns": row["end_offset_ns"],
        }

    trials = build_boundary_trial_evidence(
        experiment_contract, point_results, selector, timing_adapter
    )
    if timing_index != len(timing_rows):
        raise ValueError("runner timing contains unused rows")
    return {
        "runner": runner,
        "point_results": point_results,
        "trials": trials,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-contract", type=Path, required=True)
    parser.add_argument("--runner-observations", type=Path, required=True)
    parser.add_argument("--sidecar-src", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    selector = _load_selector(args.sidecar_src)
    output = build_run_result(
        experiment_contract=read_object(args.experiment_contract, "experiment contract"),
        runner_observations=read_object(args.runner_observations, "runner observations"),
        selector=selector,
    )
    write_json(args.out, output)
    print(
        json.dumps(
            {
                "status": "pass",
                "out": str(args.out),
                "points": len(output["point_results"]),
                "trials": len(output["trials"]),
                "run_result_sha256": sha256(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
