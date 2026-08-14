#!/usr/bin/env python3
"""Run TL-UL #10818 boundary points and emit runner observations."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tlul10818_boundary_evidence import build_boundary_trial_evidence
from tlul10818_boundary_runner_io import (
    compile_revision,
    cpu_observables,
    gpu_observe_one,
    read_object,
    semantic_projection,
    write_json,
)
from tlul10818_boundary_runner_launches import execute_timed_group, parameters


def load_selector(sidecar_src: Path | None):
    if sidecar_src is not None:
        sys.path.insert(0, sidecar_src.as_posix())
    try:
        from verilator_model_sidecar.sweep_boundary import select_boundary_points
    except ImportError as error:
        raise ValueError("verilator_model_sidecar.sweep_boundary.select_boundary_points is unavailable") from error
    return select_boundary_points


def coverage_features(action: Mapping[str, Any], bad_coverage: int, fixed_coverage: int) -> list[str]:
    features = {f"action:{action['action']}"}
    for label, bitmap in (("bad", bad_coverage), ("fixed", fixed_coverage)):
        for bit in range(32):
            if bitmap & (1 << bit):
                features.add(f"{label}:action_coverage_bit:{bit}")
    return sorted(features)


def point_results(
    *,
    contract: Mapping[str, Any],
    revisions: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for action in contract["action_domain"]:
        point_id = action["point_id"]
        action_parameters = parameters(action)
        revision_results: dict[str, Any] = {}
        coverage_by_revision: dict[str, int] = {}
        for label in ("bad", "fixed"):
            revision = revisions[label]
            point_dir = revision["revision_dir"] / "points"
            point_dir.mkdir(parents=True, exist_ok=True)
            safe_name = action["action"].replace("/", "_")
            cpu_state = point_dir / f"{safe_name}.cpu.bin"
            gpu_state = point_dir / f"{safe_name}.gpu.bin"
            patch = point_dir / f"{safe_name}.patch"
            cpu, cpu_coverage = cpu_observables(revision["cpu_binary"], action_parameters, cpu_state)
            gpu, _cycle_evals = gpu_observe_one(revision, action_parameters, gpu_state, patch)
            gpu_semantic = semantic_projection(gpu)
            if cpu != gpu_semantic:
                raise RuntimeError(f"CPU/GPU semantic mismatch for {label} {point_id}: {cpu} != {gpu_semantic}")
            revision_results[label] = {"cpu": cpu, "gpu": gpu_semantic}
            coverage_by_revision[label] = cpu_coverage | int(gpu["action_coverage"])
        results.append(
            {
                "point_id": point_id,
                "coverage_feature_ids": coverage_features(action, coverage_by_revision["bad"], coverage_by_revision["fixed"]),
                "revisions": revision_results,
            }
        )
    return results


def timing_rows(
    *,
    contract: Mapping[str, Any],
    point_rows: Sequence[Mapping[str, Any]],
    revisions: Mapping[str, Mapping[str, Any]],
    actions_by_point: Mapping[str, Mapping[str, Any]],
    selector,
    work_dir: Path,
) -> list[dict[str, Any]]:
    backend_by_trial = {
        trial["trial_id"]: next(backend for backend in contract["backends"] if backend["backend_id"] == trial["backend_id"])
        for trial in contract["trials"]
    }
    rows: list[dict[str, Any]] = []
    runner_start = time.monotonic_ns()

    def timing_adapter(trial_id: str, launch_index: int, group: Sequence[tuple[int, str, str, str]]) -> Mapping[str, int]:
        backend = backend_by_trial[trial_id]
        revision_labels = {revision for _epoch, _point, revision, _purpose in group}
        if len(revision_labels) != 1:
            raise ValueError("timing group must contain exactly one revision")
        revision_label = next(iter(revision_labels))
        start = time.monotonic_ns() - runner_start
        cycle_evals = execute_timed_group(
            backend=backend,
            revision=revisions[revision_label],
            revision_label=revision_label,
            trial_id=trial_id,
            launch_index=launch_index,
            group=group,
            point_rows=point_rows,
            actions_by_point=actions_by_point,
            work_dir=work_dir,
        )
        end = time.monotonic_ns() - runner_start
        row = {
            "trial_id": trial_id,
            "launch_index": launch_index,
            "cycle_evals": cycle_evals,
            "start_offset_ns": start,
            "end_offset_ns": end,
        }
        rows.append(row)
        return row

    build_boundary_trial_evidence(contract, point_rows, selector, timing_adapter)
    return rows


def build_runner_observations(
    *,
    experiment_contract: Mapping[str, Any],
    verilator: Path,
    verilator_root: Path,
    bad_checkout: Path,
    fixed_checkout: Path,
    sidecar_src: Path | None,
    work_dir: Path,
    runner_identity: str,
) -> dict[str, Any]:
    revision_sha = experiment_contract["target"].get("revisions")
    if not isinstance(revision_sha, Mapping) or set(revision_sha) != {"bad", "fixed"}:
        raise ValueError("experiment Contract target revisions are invalid")
    revisions = {
        label: compile_revision(
            label=label,
            checkout=checkout,
            expected_revision=revision_sha[label],
            verilator=verilator,
            verilator_root=verilator_root,
            work_dir=work_dir,
        )
        for label, checkout in (("bad", bad_checkout), ("fixed", fixed_checkout))
    }
    point_rows = point_results(contract=experiment_contract, revisions=revisions)
    actions_by_point = {action["point_id"]: action for action in experiment_contract["action_domain"]}
    timing = timing_rows(
        contract=experiment_contract,
        point_rows=point_rows,
        revisions=revisions,
        actions_by_point=actions_by_point,
        selector=load_selector(sidecar_src),
        work_dir=work_dir,
    )
    return {
        "runner": {
            "status": "pass",
            "identity": runner_identity,
            "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
        "point_results": point_rows,
        "timing": timing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-contract", required=True, type=Path)
    parser.add_argument("--verilator", required=True, type=Path)
    parser.add_argument("--verilator-root", type=Path)
    parser.add_argument("--bad", required=True, type=Path)
    parser.add_argument("--fixed", required=True, type=Path)
    parser.add_argument("--sidecar-src", type=Path)
    parser.add_argument("--work-dir", type=Path, default=Path("artifacts/tlul10818_boundary_runner_work"))
    parser.add_argument("--runner-identity", default="local-tlul10818-boundary-runner:v1")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    verilator = args.verilator.resolve()
    if not verilator.is_file():
        parser.error(f"missing Verilator executable: {verilator}")
    root = args.verilator_root.resolve() if args.verilator_root else verilator.parent.parent
    if not (root / "include").is_dir():
        parser.error(f"missing Verilator include root: {root / 'include'}")
    observations = build_runner_observations(
        experiment_contract=read_object(args.experiment_contract, "experiment contract"),
        verilator=verilator,
        verilator_root=root,
        bad_checkout=args.bad.resolve(),
        fixed_checkout=args.fixed.resolve(),
        sidecar_src=args.sidecar_src,
        work_dir=args.work_dir,
        runner_identity=args.runner_identity,
    )
    write_json(args.out, observations)
    print(json.dumps({"runner_observations": str(args.out), "status": "pass"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
