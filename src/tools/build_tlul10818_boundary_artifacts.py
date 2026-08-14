#!/usr/bin/env python3
"""Build TL-UL #10818 boundary JSON artifacts from external runner results.

This tool does not compile or execute RTL.  It only converts an externally
chosen run spec, a sidecar-generated sweep enumeration, and an already generated
runner result into the two JSON inputs consumed by the sidecar adjudicator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tlul10818_boundary_contract import build_boundary_experiment_contract
from tlul10818_boundary_evidence import build_boundary_evidence_bundle


DEFAULT_TARGET_CONFIG = Path("config/tlul10818_boundary_benchmark.json")
DEFAULT_OUT_DIR = Path("artifacts/tlul10818_boundary_benchmark")


def _read_object(path: Path, label: str) -> dict[str, Any]:
    def reject_constant(token: str) -> None:
        raise ValueError(f"{label} contains non-finite JSON token {token}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_artifacts(
    *,
    target_config_path: Path,
    run_spec_path: Path,
    sweep_enumeration_path: Path,
    run_result_path: Path,
    out_dir: Path,
) -> dict[str, str]:
    target_config = _read_object(target_config_path, "target config")
    run_spec = _read_object(run_spec_path, "run spec")
    sweep_enumeration = _read_object(sweep_enumeration_path, "sweep enumeration")
    run_result = _read_object(run_result_path, "run result")

    def sweep_enumerator(_sweep_space: dict[str, Any]) -> dict[str, Any]:
        return sweep_enumeration

    contract_bundle = build_boundary_experiment_contract(
        target_config, run_spec, sweep_enumerator
    )
    evidence = build_boundary_evidence_bundle(contract_bundle, run_result)

    contract_path = out_dir / "experiment_contract.json"
    evidence_path = out_dir / "evidence_bundle.json"
    _write_json(contract_path, contract_bundle["experiment_contract"])
    _write_json(evidence_path, evidence)
    return {
        "experiment_contract": contract_path.as_posix(),
        "evidence_bundle": evidence_path.as_posix(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, default=DEFAULT_TARGET_CONFIG)
    parser.add_argument("--run-spec", type=Path, required=True)
    parser.add_argument("--sweep-enumeration", type=Path, required=True)
    parser.add_argument("--run-result", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    outputs = build_artifacts(
        target_config_path=args.target_config,
        run_spec_path=args.run_spec,
        sweep_enumeration_path=args.sweep_enumeration,
        run_result_path=args.run_result,
        out_dir=args.out_dir,
    )
    print(
        "wrote "
        f"{outputs['experiment_contract']} and {outputs['evidence_bundle']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
