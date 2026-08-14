#!/usr/bin/env python3
"""Admit externally generated TL-UL #10818 boundary observations.

This is a JSON-only pipeline for the handoff after an external runner or CI has
already executed the DUT.  It builds the Experiment Contract, converts runner
observations into sidecar-ready run results, builds the Evidence Bundle, and
delegates final adjudication/report generation to ``verilator-model-sidecar``.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from build_tlul10818_boundary_artifacts import _read_object, _write_json
from build_tlul10818_boundary_run_result import build_run_result
from tlul10818_boundary_contract import build_boundary_experiment_contract
from tlul10818_boundary_evidence import build_boundary_evidence_bundle


DEFAULT_TARGET_CONFIG = Path("config/tlul10818_boundary_benchmark.json")
DEFAULT_OUT_DIR = Path("artifacts/tlul10818_boundary_benchmark")
RTL_BOUNDARY_SCHEMA_VERSION = 1
RTL_BOUNDARY_ADJUDICATION_SURFACE = "rtl_boundary_adjudication"
RTL_BOUNDARY_PIPELINE_RESULT_SURFACE = "rtl_boundary_pipeline_result"


def _load_sidecar_adapters(sidecar_src: Path | None):
    if sidecar_src is not None:
        sys.path.insert(0, sidecar_src.as_posix())
    try:
        from verilator_model_sidecar.sweep_boundary import (
            enumerate_sweep_space,
            select_boundary_points,
        )
    except ImportError as error:
        raise ValueError(
            "verilator_model_sidecar sweep-boundary adapters are unavailable"
        ) from error
    return enumerate_sweep_space, select_boundary_points


def _fail_pipeline(message: str, *, out_dir: Path, run_spec: Path, runner_observations: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "pipeline_result.json"
    pipeline = {
        "schema_version": RTL_BOUNDARY_SCHEMA_VERSION,
        "surface": RTL_BOUNDARY_PIPELINE_RESULT_SURFACE,
        "status": "fail",
        "adjudication": {
            "schema_version": RTL_BOUNDARY_SCHEMA_VERSION,
            "surface": RTL_BOUNDARY_ADJUDICATION_SURFACE,
            "status": "fail",
            "issues": [{"code": "admission_input_error", "message": message}],
            "input_canonical_sha256": {
                "experiment_contract": None,
                "evidence_bundle": None,
            },
            "input_file_sha256": {
                "experiment_contract": None,
                "evidence_bundle": None,
            },
        },
        "report_bundle": None,
        "graph_artifact": None,
        "markdown_artifact": None,
    }
    _write_json(output, pipeline)
    return output


def admit_observations(
    *,
    target_config_path: Path,
    run_spec_path: Path,
    runner_observations_path: Path,
    sidecar_src: Path | None,
    out_dir: Path,
) -> dict[str, str]:
    enumerate_sweep_space, select_boundary_points = _load_sidecar_adapters(sidecar_src)
    target_config = _read_object(target_config_path, "target config")
    run_spec = _read_object(run_spec_path, "run spec")
    runner_observations = _read_object(
        runner_observations_path, "runner observations"
    )
    contract_bundle = build_boundary_experiment_contract(
        target_config, run_spec, enumerate_sweep_space
    )
    experiment_contract = contract_bundle["experiment_contract"]
    sweep_enumeration = enumerate_sweep_space(experiment_contract["sweep_space"])
    run_result = build_run_result(
        experiment_contract=experiment_contract,
        runner_observations=runner_observations,
        selector=select_boundary_points,
    )
    evidence_bundle = build_boundary_evidence_bundle(contract_bundle, run_result)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "run_spec": out_dir / "run_spec.json",
        "runner_observations": out_dir / "runner_observations.json",
        "sweep_enumeration": out_dir / "sweep_enumeration.json",
        "semantic_manifests": out_dir / "semantic_manifests.json",
        "experiment_contract": out_dir / "experiment_contract.json",
        "run_result": out_dir / "run_result.json",
        "evidence_bundle": out_dir / "evidence_bundle.json",
        "pipeline_result": out_dir / "pipeline_result.json",
    }
    _write_json(paths["run_spec"], run_spec)
    _write_json(paths["runner_observations"], runner_observations)
    _write_json(paths["sweep_enumeration"], sweep_enumeration)
    _write_json(paths["semantic_manifests"], contract_bundle["semantic_manifests"])
    _write_json(paths["experiment_contract"], experiment_contract)
    _write_json(paths["run_result"], run_result)
    _write_json(paths["evidence_bundle"], evidence_bundle)
    return {key: value.as_posix() for key, value in paths.items()}


def _run_adjudicator(
    *,
    sidecar_src: Path | None,
    adjudicator_bin: str,
    experiment_contract: Path,
    evidence_bundle: Path,
    pipeline_result: Path,
) -> None:
    env = os.environ.copy()
    if sidecar_src is not None:
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            sidecar_src.as_posix()
            if not existing
            else f"{sidecar_src.as_posix()}{os.pathsep}{existing}"
        )
    completed = subprocess.run(
        [
            adjudicator_bin,
            "adjudicate-boundary-benchmark",
            "--experiment-contract",
            experiment_contract.as_posix(),
            "--evidence",
            evidence_bundle.as_posix(),
            "--output",
            pipeline_result.as_posix(),
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "boundary adjudicator failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, default=DEFAULT_TARGET_CONFIG)
    parser.add_argument("--run-spec", type=Path, required=True)
    parser.add_argument("--runner-observations", type=Path, required=True)
    parser.add_argument("--sidecar-src", type=Path)
    parser.add_argument(
        "--adjudicator-bin",
        default="verilator-model-sidecar",
        help="Boundary adjudicator executable",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    try:
        outputs = admit_observations(
            target_config_path=args.target_config,
            run_spec_path=args.run_spec,
            runner_observations_path=args.runner_observations,
            sidecar_src=args.sidecar_src,
            out_dir=args.out_dir,
        )
        _run_adjudicator(
            sidecar_src=args.sidecar_src,
            adjudicator_bin=args.adjudicator_bin,
            experiment_contract=Path(outputs["experiment_contract"]),
            evidence_bundle=Path(outputs["evidence_bundle"]),
            pipeline_result=Path(outputs["pipeline_result"]),
        )
        print(f"wrote {outputs['pipeline_result']}")
        return 0
    except Exception as error:
        output = _fail_pipeline(
            str(error),
            out_dir=args.out_dir,
            run_spec=args.run_spec,
            runner_observations=args.runner_observations,
        )
        print(f"wrote {output}: status=fail", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
