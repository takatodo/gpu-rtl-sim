#!/usr/bin/env python3
"""Run the full justified Ibex #2188 boundary grid and emit runner observations.

The runner compiles both pinned revisions (CPU driver + GPU sidecar), executes
every admitted categorical x ordered point on both revisions through both
adapters, verifies CPU/GPU semantic equality, then replays the Contract's
selector trials through the shared selector interface while actually executing
each launch group (CPU sequential / GPU resident batch) and recording real
timing rows.  The emitted JSON is consumed by
scripts/build_ibex2188_boundary_run_result.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "tools"))

from ibex2188_boundary_compile import compile_revision  # noqa: E402
from ibex2188_boundary_runner_io import (  # noqa: E402
    batch_observables,
    batch_patch_script,
    cpu_command,
    cpu_observables,
    gpu_observe_one,
    parameters,
    read_object,
    require_success,
    run_repo,
    sha256,
    single_state_patch,
    write_json,
)
from ibex2188_boundary_trials import build_boundary_trial_evidence  # noqa: E402


def load_selector(sidecar_src: Path | None):
    if sidecar_src is not None:
        sys.path.insert(0, sidecar_src.as_posix())
    try:
        from verilator_model_sidecar.sweep_boundary import select_boundary_points
    except ImportError as error:
        raise ValueError(
            "verilator_model_sidecar.sweep_boundary.select_boundary_points is unavailable"
        ) from error
    return select_boundary_points


def projection_keys(contract: Mapping[str, Any]) -> list[str]:
    target = contract.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("experiment Contract target is invalid")
    return list(target.get("semantic_observables", [])) + [
        target.get("oracle_field")
    ]


def project(values: Mapping[str, Any], keys: Sequence[str]) -> dict[str, int]:
    missing = [key for key in keys if key not in values]
    if missing:
        raise ValueError(f"observable projection missing keys: {missing}")
    return {key: int(values[key]) for key in keys}


def compile_revisions(
    *,
    contract: Mapping[str, Any],
    verilator: Path,
    verilator_root: Path,
    bad_checkout: Path,
    fixed_checkout: Path,
    work_dir: Path,
) -> dict[str, dict[str, Any]]:
    target = contract["target"]
    revisions = target["revisions"]
    return {
        label: compile_revision(
            label=label,
            checkout=checkout,
            expected_revision=revisions[label],
            verilator=verilator,
            verilator_root=verilator_root,
            work_dir=work_dir,
        )
        for label, checkout in (("bad", bad_checkout), ("fixed", fixed_checkout))
    }


def point_results(
    *,
    contract: Mapping[str, Any],
    revisions: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    keys = projection_keys(contract)
    results: list[dict[str, Any]] = []
    for action in contract["action_domain"]:
        point_id = action["point_id"]
        action_parameters = parameters(action)
        revision_results: dict[str, Any] = {}
        for label in ("bad", "fixed"):
            revision = revisions[label]
            point_dir = revision["revision_dir"] / "points"
            point_dir.mkdir(parents=True, exist_ok=True)
            safe_name = action["action"].replace("/", "_")
            cpu_state = point_dir / f"{safe_name}.cpu.bin"
            gpu_state = point_dir / f"{safe_name}.gpu.bin"
            patch = point_dir / f"{safe_name}.patch"
            cpu, _ = cpu_observables(revision["cpu_binary"], action_parameters, cpu_state)
            gpu, _ = gpu_observe_one(revision, action_parameters, gpu_state, patch)
            if cpu != gpu:
                raise RuntimeError(
                    f"CPU/GPU semantic mismatch for {label} {point_id}: {cpu} != {gpu}"
                )
            revision_results[label] = {
                "cpu": project(cpu, keys),
                "gpu": project(gpu, keys),
            }
        results.append(
            {
                "point_id": point_id,
                "coverage_feature_ids": [f"coverage:{point_id}"],
                "revisions": revision_results,
            }
        )
    return results


def execute_timed_group(
    *,
    backend: Mapping[str, Any],
    revision: Mapping[str, Any],
    revision_label: str,
    trial_id: str,
    launch_index: int,
    group: Sequence[tuple[int, str, str, str]],
    point_rows: Sequence[Mapping[str, Any]],
    actions_by_point: Mapping[str, Mapping[str, Any]],
    work_dir: Path,
) -> int:
    if backend["kind"] == "cpu":
        cycle_evals = 0
        for _epoch, point_id, _revision, _purpose in group:
            action_parameters = parameters(actions_by_point[point_id])
            completed = subprocess.run(
                cpu_command(revision["cpu_binary"], action_parameters),
                text=True,
                capture_output=True,
                check=False,
            )
            require_success(completed, f"CPU timing execution {trial_id}:{launch_index}")
            cycle_evals += len(single_state_patch(action_parameters))
        return cycle_evals
    if backend["kind"] != "gpu":
        raise ValueError(f"unsupported backend kind: {backend['kind']}")
    launch_dir = work_dir / "trial_launches" / revision_label
    launch_dir.mkdir(parents=True, exist_ok=True)
    script, cycle_evals = batch_patch_script(
        actions_by_point=actions_by_point,
        group=group,
    )
    patch = launch_dir / f"{trial_id}_{launch_index}.patch"
    state = launch_dir / f"{trial_id}_{launch_index}.gpu.bin"
    patch.write_text(script, encoding="utf-8")
    completed = run_repo(
        [
            sys.executable,
            str(revision["hybrid_runner"]),
            "--mdir",
            str(revision["gpu_mdir"]),
            "--nstates",
            str(len(group)),
            "--resident-steps",
            "--patch-script",
            str(patch),
            "--dump-state",
            str(state),
        ],
        env=revision["env"],
    )
    require_success(completed, f"GPU timing launch {trial_id}:{launch_index}")
    observed = batch_observables(
        state.read_bytes(), len(group), revision["storage_size"]
    )
    for index, (_epoch, point_id, _rev, _purpose) in enumerate(group):
        expected = next(row for row in point_rows if row["point_id"] == point_id)
        expected_gpu = expected["revisions"][revision_label]["gpu"]
        observed_projection = {key: observed[index][key] for key in expected_gpu}
        if observed_projection != expected_gpu:
            raise RuntimeError(
                f"GPU timing launch mismatch for {trial_id}:{launch_index}:{point_id}"
            )
    return cycle_evals


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
        trial["trial_id"]: next(
            backend
            for backend in contract["backends"]
            if backend["backend_id"] == trial["backend_id"]
        )
        for trial in contract["trials"]
    }
    rows: list[dict[str, Any]] = []
    runner_start = time.monotonic_ns()

    def timing_adapter(
        trial_id: str, launch_index: int, group: Sequence[tuple[int, str, str, str]]
    ) -> Mapping[str, int]:
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

    # Replays the Contract trials through the shared selector ABI while the
    # timing adapter physically executes every launch group.
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
    revisions = compile_revisions(
        contract=experiment_contract,
        verilator=verilator,
        verilator_root=verilator_root,
        bad_checkout=bad_checkout,
        fixed_checkout=fixed_checkout,
        work_dir=work_dir,
    )
    point_rows = point_results(contract=experiment_contract, revisions=revisions)
    actions_by_point = {
        action["point_id"]: action for action in experiment_contract["action_domain"]
    }
    selector = load_selector(sidecar_src)
    timing = timing_rows(
        contract=experiment_contract,
        point_rows=point_rows,
        revisions=revisions,
        actions_by_point=actions_by_point,
        selector=selector,
        work_dir=work_dir,
    )
    return {
        "runner": {
            "status": "pass",
            "identity": runner_identity,
            "completed_at": datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
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
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("artifacts/ibex2188_boundary_runner_work"),
    )
    parser.add_argument(
        "--runner-identity", default="local-ibex2188-boundary-runner:v1"
    )
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
    print(
        json.dumps(
            {
                "status": "pass",
                "out": str(args.out),
                "points": len(observations["point_results"]),
                "timing_rows": len(observations["timing"]),
                "runner_identity": observations["runner"]["identity"],
                "runner_observations_sha256": sha256(observations),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
