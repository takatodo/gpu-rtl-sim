#!/usr/bin/env python3
"""Build canonical paired #2188 CPU ground truth from two runner observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping


TARGET_ID = "ibex2188"
CHECKPOINT = "directed_load_dependent_branch_one_cycle_response_v1"
ORACLE = "ibex2188.ecc_read_error_requires_major_alert_when_no_wb_forwarding.v1"
BAD = "668233699df9ec2a40413e69e0de0a5b10185980"
FIXED = "9e4a950aa6aa0e20eb638aeeb78743d4a9ddaaeb"


def _strict_object(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"{path} contains non-finite JSON value {value!r}")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{path} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise ValueError(f"{label} mismatch: expected {expected!r}, got {value!r}")


def _observation(raw: Mapping[str, Any], *, enabled: int) -> dict[str, Any]:
    _require(raw.get("surface"), "ibex2188_cpu_regression_observations", "surface")
    _require(raw.get("status"), "pass", "status")
    _require(raw.get("target_id"), TARGET_ID, "target")
    _require(raw.get("checkpoint_identity"), CHECKPOINT, "checkpoint")
    _require(raw.get("oracle_identity"), ORACLE, "oracle")
    _require(raw.get("bad_revision"), BAD, "bad revision")
    _require(raw.get("fixed_revision"), FIXED, "fixed revision")
    _require(raw.get("fault_port"), "a", "fault port")
    _require(raw.get("fault_bit"), 0, "fault bit")
    _require(raw.get("load_response_delay"), 1, "response delay")
    _require(raw.get("fault_enable"), enabled, "fault enable")
    revisions = raw.get("revisions")
    if not isinstance(revisions, Mapping) or set(revisions) != {"bad", "fixed"}:
        raise ValueError("revisions must contain exactly bad and fixed")
    labels: dict[str, int] = {}
    projections: dict[str, Mapping[str, Any]] = {}
    for revision in ("bad", "fixed"):
        row = revisions[revision]
        if not isinstance(row, Mapping):
            raise ValueError(f"{revision} row must be an object")
        label = row.get("oracle_violation")
        semantic = row.get("semantic")
        if not isinstance(label, int) or isinstance(label, bool) or label not in (0, 1):
            raise ValueError(f"{revision} oracle must be 0 or 1")
        if not isinstance(semantic, Mapping):
            raise ValueError(f"{revision} semantic projection must be an object")
        labels[revision] = label
        projections[revision] = semantic
    if enabled == 0:
        _require(labels, {"bad": 0, "fixed": 0}, "disabled control labels")
    else:
        _require(labels, {"bad": 1, "fixed": 0}, "guarded fault labels")
    return {"labels": labels, "semantic": projections}


def build(
    *,
    target_config: Mapping[str, Any],
    disabled_raw: Mapping[str, Any],
    guarded_raw: Mapping[str, Any],
    disabled_sha256: str,
    guarded_sha256: str,
    enumerate_sweep_space: Any,
    analyze_boundary_ground_truth: Any,
) -> dict[str, dict[str, Any]]:
    sweep = target_config.get("admitted_cpu_sweep", {}).get("sweep_space")
    if not isinstance(sweep, Mapping):
        raise ValueError("target config has no admitted CPU sweep space")
    disabled = _observation(disabled_raw, enabled=0)
    guarded = _observation(guarded_raw, enabled=1)
    enumeration = enumerate_sweep_space(sweep)
    point_by_value = {
        point["parameters"]["fault_enable"]: point
        for point in enumeration["points"]
    }
    if set(point_by_value) != {"disabled", "guarded_bit0"}:
        raise ValueError("canonical sweep points do not match the admitted action domain")
    ground_truth = {
        "schema_version": 1,
        "surface": "rtl_boundary_ground_truth",
        "sweep_space_sha256": enumeration["sweep_space_sha256"],
        "observations": [
            {
                "point_id": point_by_value["disabled"]["point_id"],
                "parameters": point_by_value["disabled"]["parameters"],
                "bad_oracle": disabled["labels"]["bad"],
                "fixed_oracle": disabled["labels"]["fixed"],
            },
            {
                "point_id": point_by_value["guarded_bit0"]["point_id"],
                "parameters": point_by_value["guarded_bit0"]["parameters"],
                "bad_oracle": guarded["labels"]["bad"],
                "fixed_oracle": guarded["labels"]["fixed"],
            },
        ],
    }
    return {
        "ground_truth": ground_truth,
        "analysis": analyze_boundary_ground_truth(sweep, ground_truth),
        "cpu_observation_bundle": {
            "schema_version": 1,
            "surface": "ibex2188_cpu_sweep_observations",
            "target_id": TARGET_ID,
            "checkpoint_identity": CHECKPOINT,
            "oracle_identity": ORACLE,
            "sweep_space_sha256": enumeration["sweep_space_sha256"],
            "source_observations": {
                "disabled": {
                    "sha256": disabled_sha256,
                    "semantic": disabled["semantic"],
                },
                "guarded_bit0": {
                    "sha256": guarded_sha256,
                    "semantic": guarded["semantic"],
                },
            },
        },
    }


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"refusing to replace existing output {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, required=True)
    parser.add_argument("--disabled-observation", type=Path, required=True)
    parser.add_argument("--guarded-observation", type=Path, required=True)
    parser.add_argument("--sidecar-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    sidecar_src = args.sidecar_root / "src"
    if not (sidecar_src / "verilator_model_sidecar" / "sweep_boundary.py").is_file():
        raise ValueError("sidecar root does not contain sweep_boundary.py")
    if args.out_dir.exists():
        raise ValueError(f"refusing to replace existing output directory {args.out_dir}")
    sys.path.insert(0, str(sidecar_src))
    from verilator_model_sidecar.sweep_boundary import (
        analyze_boundary_ground_truth,
        enumerate_sweep_space,
    )

    bundle = build(
        target_config=_strict_object(args.target_config),
        disabled_raw=_strict_object(args.disabled_observation),
        guarded_raw=_strict_object(args.guarded_observation),
        disabled_sha256=_sha256(args.disabled_observation),
        guarded_sha256=_sha256(args.guarded_observation),
        enumerate_sweep_space=enumerate_sweep_space,
        analyze_boundary_ground_truth=analyze_boundary_ground_truth,
    )
    args.out_dir.mkdir(parents=True)
    _write_json(args.out_dir / "ground_truth.json", bundle["ground_truth"])
    _write_json(args.out_dir / "ground_truth_analysis.json", bundle["analysis"])
    _write_json(args.out_dir / "cpu_observation_bundle.json", bundle["cpu_observation_bundle"])
    print(json.dumps({"status": "pass", "out_dir": str(args.out_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
