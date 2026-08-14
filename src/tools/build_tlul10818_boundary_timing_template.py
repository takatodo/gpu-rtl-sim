#!/usr/bin/env python3
"""Build the timing-row checklist for TL-UL #10818 boundary observations.

This tool is for the external-runner handoff after point results exist.  Trial
scheduling depends on observed bad-revision oracle bits, so the required timing
rows cannot be known from the run spec alone.  The output is a template: it
names the launch order that the runner must time, but it does not fabricate
``cycle_evals`` or wall-time values for admission.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from build_tlul10818_boundary_artifacts import _read_object, _write_json
from tlul10818_boundary_evidence import build_boundary_trial_evidence


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


def build_timing_template(
    *,
    experiment_contract: Mapping[str, Any],
    point_results: Sequence[Mapping[str, Any]],
    selector,
) -> dict[str, Any]:
    def zero_timing(
        _trial_id: str,
        _launch_index: int,
        _group: Sequence[tuple[int, str, str, str]],
    ) -> Mapping[str, int]:
        return {"cycle_evals": 0, "start_offset_ns": 0, "end_offset_ns": 0}

    trials = build_boundary_trial_evidence(
        experiment_contract, point_results, selector, zero_timing
    )
    rows: list[dict[str, Any]] = []
    for trial in trials:
        executions_by_id = {
            execution["execution_id"]: execution for execution in trial["executions"]
        }
        for launch_index, launch in enumerate(trial["launches"]):
            rows.append(
                {
                    "trial_id": trial["trial_id"],
                    "launch_index": launch_index,
                    "backend_id": launch["backend_id"],
                    "resident_width": launch["resident_width"],
                    "execution_requests": [
                        {
                            "point_id": executions_by_id[execution_id]["point_id"],
                            "revision": executions_by_id[execution_id]["revision"],
                            "purpose": executions_by_id[execution_id]["purpose"],
                            "epoch_index": executions_by_id[execution_id]["epoch_index"],
                        }
                        for execution_id in launch["execution_ids"]
                    ],
                    "runner_must_fill": [
                        "cycle_evals",
                        "start_offset_ns",
                        "end_offset_ns",
                    ],
                }
            )
    return {
        "schema_version": 1,
        "surface": "tlul10818_boundary_timing_template",
        "experiment_id": experiment_contract.get("experiment_id"),
        "sweep_space_sha256": experiment_contract.get("sweep_space_sha256"),
        "action_domain_sha256": experiment_contract.get("action_domain_sha256"),
        "timing_rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-contract", type=Path, required=True)
    parser.add_argument("--point-results", type=Path, required=True)
    parser.add_argument("--sidecar-src", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    selector = _load_selector(args.sidecar_src)
    raw_point_results = _read_object(args.point_results, "point results")
    point_results = raw_point_results.get("point_results")
    if not isinstance(point_results, list):
        raise ValueError("point results input must contain point_results")
    _write_json(
        args.out,
        build_timing_template(
            experiment_contract=_read_object(
                args.experiment_contract, "experiment contract"
            ),
            point_results=point_results,
            selector=selector,
        ),
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
