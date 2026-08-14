#!/usr/bin/env python3
"""Build the pre-runtime TL-UL #10818 boundary execution packet.

This tool is the JSON-only handoff before an external runner executes the DUT.
It turns a run spec into the canonical Experiment Contract, sidecar sweep
enumeration, semantic manifests, and a point-result template listing the exact
point IDs/actions and semantic keys that must later be observed.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from build_tlul10818_boundary_artifacts import _read_object, _write_json
from tlul10818_boundary_contract import build_boundary_experiment_contract


DEFAULT_TARGET_CONFIG = Path("config/tlul10818_boundary_benchmark.json")
DEFAULT_OUT_DIR = Path("artifacts/tlul10818_boundary_execution_packet")


def _load_sweep_enumerator(sidecar_src: Path | None):
    if sidecar_src is not None:
        sys.path.insert(0, sidecar_src.as_posix())
    try:
        from verilator_model_sidecar.sweep_boundary import enumerate_sweep_space
    except ImportError as error:
        raise ValueError(
            "verilator_model_sidecar.sweep_boundary.enumerate_sweep_space is unavailable"
        ) from error
    return enumerate_sweep_space


def _point_result_template(contract: Mapping[str, Any]) -> dict[str, Any]:
    target = contract["target"]
    projection_keys = list(target["semantic_observables"]) + [target["oracle_field"]]
    return {
        "schema_version": 1,
        "surface": "tlul10818_boundary_point_result_template",
        "experiment_id": contract["experiment_id"],
        "sweep_space_sha256": contract["sweep_space_sha256"],
        "action_domain_sha256": contract["action_domain_sha256"],
        "semantic_projection_keys": projection_keys,
        "oracle_field": target["oracle_field"],
        "rows": [
            {
                "point_id": action["point_id"],
                "action": action["action"],
                "parameters": action["parameters"],
                "required_revisions": ["bad", "fixed"],
                "required_adapters": ["cpu", "gpu"],
                "runner_must_fill": {
                    "coverage_feature_ids": "unique string array",
                    "revisions": {
                        revision: {
                            adapter: {key: "integer semantic value" for key in projection_keys}
                            for adapter in ("cpu", "gpu")
                        }
                        for revision in ("bad", "fixed")
                    },
                },
            }
            for action in contract["action_domain"]
        ],
    }


def build_execution_packet(
    *,
    target_config_path: Path,
    run_spec_path: Path,
    sidecar_src: Path | None,
    out_dir: Path,
) -> dict[str, str]:
    enumerate_sweep_space = _load_sweep_enumerator(sidecar_src)
    contract_bundle = build_boundary_experiment_contract(
        _read_object(target_config_path, "target config"),
        _read_object(run_spec_path, "run spec"),
        enumerate_sweep_space,
    )
    contract = contract_bundle["experiment_contract"]
    outputs = {
        "sweep_enumeration": out_dir / "sweep_enumeration.json",
        "experiment_contract": out_dir / "experiment_contract.json",
        "semantic_manifests": out_dir / "semantic_manifests.json",
        "point_result_template": out_dir / "point_result_template.json",
    }
    _write_json(outputs["sweep_enumeration"], enumerate_sweep_space(contract["sweep_space"]))
    _write_json(outputs["experiment_contract"], contract)
    _write_json(outputs["semantic_manifests"], contract_bundle["semantic_manifests"])
    _write_json(outputs["point_result_template"], _point_result_template(contract))
    return {key: value.as_posix() for key, value in outputs.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, default=DEFAULT_TARGET_CONFIG)
    parser.add_argument("--run-spec", type=Path, required=True)
    parser.add_argument("--sidecar-src", type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    outputs = build_execution_packet(
        target_config_path=args.target_config,
        run_spec_path=args.run_spec,
        sidecar_src=args.sidecar_src,
        out_dir=args.out_dir,
    )
    print(
        "wrote "
        f"{outputs['experiment_contract']} and {outputs['point_result_template']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
