#!/usr/bin/env python3
"""Build a TL-UL #10818 admitted-profile entry from admitted artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from validate_tlul10818_boundary_profile import _read_object, _require_mapping, _sha256


REQUIRED_ARTIFACTS = (
    "run_spec.json",
    "experiment_contract.json",
    "sweep_enumeration.json",
    "runner_observations.json",
    "run_result.json",
    "evidence_bundle.json",
    "pipeline_result.json",
    "admission_manifest.json",
)


def _boolean(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("value must be 'true' or 'false'")


def _ground_truth_summary(pipeline: Mapping[str, Any]) -> dict[str, int]:
    adjudication = _require_mapping(pipeline.get("adjudication"), "adjudication")
    analysis = _require_mapping(
        adjudication.get("ground_truth_analysis"), "ground_truth_analysis"
    )
    revisions = _require_mapping(analysis.get("revisions"), "ground truth revisions")
    bad = _require_mapping(revisions.get("bad"), "bad ground truth")
    fixed = _require_mapping(revisions.get("fixed"), "fixed ground truth")
    bad_to_fixed = _require_mapping(analysis.get("bad_to_fixed"), "bad_to_fixed")
    minimal = _require_mapping(
        bad.get("minimal_failing_points"), "bad minimal_failing_points"
    )
    disappeared = bad_to_fixed.get("disappeared_failure_point_ids")
    point_ids = minimal.get("point_ids")
    if not isinstance(disappeared, list) or not isinstance(point_ids, list):
        raise ValueError("ground truth point-id lists are invalid")
    return {
        "bad_fail_point_count": int(bad["fail_point_count"]),
        "bad_pass_point_count": int(bad["pass_point_count"]),
        "bad_boundary_edge_count": int(bad["boundary_edge_count"]),
        "bad_failure_component_count": int(bad["failure_component_count"]),
        "bad_minimal_failing_point_count": len(point_ids),
        "fixed_fail_point_count": int(fixed["fail_point_count"]),
        "bad_to_fixed_disappeared_failure_count": len(disappeared),
    }


def _comparison_ids(pipeline: Mapping[str, Any]) -> dict[str, list[str]]:
    adjudication = _require_mapping(pipeline.get("adjudication"), "adjudication")
    return {
        "selector": [
            str(row["comparison_id"])
            for row in adjudication.get("selector_comparisons", [])
        ],
        "backend": [
            str(row["comparison_id"])
            for row in adjudication.get("backend_comparisons", [])
        ],
    }


def _report_sha256(pipeline: Mapping[str, Any]) -> dict[str, str]:
    graph = _require_mapping(pipeline.get("graph_artifact"), "graph_artifact")
    markdown = _require_mapping(pipeline.get("markdown_artifact"), "markdown_artifact")
    if not isinstance(graph.get("sha256"), str) or not isinstance(markdown.get("sha256"), str):
        raise ValueError("report artifact SHA rows are invalid")
    return {
        "graph_svg": graph["sha256"],
        "markdown_report": markdown["sha256"],
    }


def build_profile(
    *,
    source_dir: Path,
    profile_id: str,
    artifact_dir: str,
    description: str,
    authority_kind: str,
    external_closure: bool,
) -> dict[str, Any]:
    run_spec = _read_object(source_dir / "run_spec.json", "run spec")
    runner_observations = _read_object(
        source_dir / "runner_observations.json", "runner observations"
    )
    pipeline = _read_object(source_dir / "pipeline_result.json", "pipeline result")
    manifest = _read_object(source_dir / "admission_manifest.json", "admission manifest")
    if pipeline.get("status") != "pass":
        raise ValueError("pipeline_result status must be pass")
    if manifest.get("status") != "pass":
        raise ValueError("admission_manifest status must be pass")
    runner = _require_mapping(runner_observations.get("runner"), "runner observations runner")
    runner_identity = runner.get("identity")
    if runner.get("status") != "pass" or not isinstance(runner_identity, str) or not runner_identity:
        raise ValueError("runner observations runner identity/status is invalid")
    artifact_sha256: dict[str, str] = {}
    for name in REQUIRED_ARTIFACTS:
        artifact_sha256[name] = _sha256(source_dir / name)
    return {
        "profile_id": profile_id,
        "status": "admitted_pass",
        "description": description,
        "experiment_id": run_spec["experiment_id"],
        "runtime_authority": {
            "authority_kind": authority_kind,
            "external_closure": external_closure,
            "runner_identity": runner_identity,
        },
        "finite_axis_values": run_spec["finite_axis_values"],
        "point_count": int(pipeline["adjudication"]["ground_truth_analysis"]["point_count"]),
        "ground_truth_summary": _ground_truth_summary(pipeline),
        "comparison_ids": _comparison_ids(pipeline),
        "artifact_dir": artifact_dir,
        "artifact_sha256": artifact_sha256,
        "report_sha256": _report_sha256(pipeline),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--authority-kind", required=True)
    parser.add_argument("--external-closure", required=True, type=_boolean)
    args = parser.parse_args(argv)
    print(json.dumps(build_profile(
        source_dir=args.source_dir,
        profile_id=args.profile_id,
        artifact_dir=args.artifact_dir,
        description=args.description,
        authority_kind=args.authority_kind,
        external_closure=args.external_closure,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
