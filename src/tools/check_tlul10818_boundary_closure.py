#!/usr/bin/env python3
"""Check whether TL-UL #10818 has an externally owned admitted closure profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from validate_tlul10818_boundary_profile import (
    DEFAULT_CONFIG,
    _read_object,
    validate_profile,
)


def _profiles(config: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    profiles = config.get("admitted_benchmark_profiles")
    if not isinstance(profiles, list):
        raise ValueError("config admitted_benchmark_profiles must be a list")
    return [profile for profile in profiles if isinstance(profile, Mapping)]


def check_closure(*, config_path: Path, artifact_dir: Path | None = None) -> dict[str, Any]:
    config = _read_object(config_path, "target config")
    checked: list[dict[str, Any]] = []
    for profile in _profiles(config):
        profile_id = profile.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id:
            continue
        try:
            validation = validate_profile(
                config_path=config_path,
                profile_id=profile_id,
                artifact_dir=artifact_dir,
            )
        except Exception as error:  # noqa: BLE001 - report fail-closed profile reason.
            checked.append(
                {
                    "profile_id": profile_id,
                    "status": "invalid",
                    "reason": str(error),
                }
            )
            continue
        authority = validation["runtime_authority"]
        row = {
            "profile_id": profile_id,
            "status": "valid",
            "artifact_dir": validation["artifact_dir"],
            "runtime_authority": authority,
            "point_count": validation["point_count"],
            "ground_truth_summary": validation["ground_truth_summary"],
        }
        checked.append(row)
        if authority.get("external_closure") is True:
            return {
                "status": "pass",
                "closure_profile_id": profile_id,
                "closure": row,
                "checked_profiles": checked,
            }
    return {
        "status": "fail",
        "reason": "no_valid_external_closure_profile",
        "checked_profiles": checked,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args(argv)
    result = check_closure(
        config_path=args.target_config,
        artifact_dir=args.artifact_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
