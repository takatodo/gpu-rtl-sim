#!/usr/bin/env python3
"""Derive corpus and degenerate policy evidence from entropy_src action results."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from entropy10983_gpu_schedule import ACTION_DOMAIN


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(path: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def _metrics(action: str, action_record: dict[str, object]) -> dict[str, object]:
    observed = action_record["gpu"]
    return {
        "campaign_count": 1,
        "coverage_closure_episode": [1],
        "time_to_first_violation": {
            "mean": 1.0 if int(observed["early_sha3_process"]) else None,
            "p50": 1 if int(observed["early_sha3_process"]) else None,
            "p95": 1 if int(observed["early_sha3_process"]) else None,
            "max": 1 if int(observed["early_sha3_process"]) else None,
            "long_tail_rate_after_episode_1": 0.0,
        },
        "coverage_progression": [{"episode": 1, "functional_bins_reached": int(observed["action_coverage"] != 0)}],
        "order": [action],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equivalence-report", type=Path, required=True)
    parser.add_argument("--bad-checkout", type=Path, required=True)
    parser.add_argument("--fixed-checkout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.equivalence_report.read_text(encoding="utf-8"))
    bad = next(item for item in report["revisions"] if item["label"] == "bad")
    fixed = next(item for item in report["revisions"] if item["label"] == "fixed")
    if report["action_domain"] != list(ACTION_DOMAIN):
        raise SystemExit("equivalence report does not contain the declared entropy_src action domain")
    if any(item["status"] != "pass" for item in bad["actions"] + fixed["actions"]):
        raise SystemExit("equivalence report has an unproven action")
    action = ACTION_DOMAIN[0]
    bad_action = bad["actions"][0]
    fixed_action = fixed["actions"][0]
    identities = {
        "bad_revision": _git_head(args.bad_checkout),
        "fixed_revision": _git_head(args.fixed_checkout),
        "checkpoint_identity": report["checkpoint_identity"],
        "action_domain_sha256": hashlib.sha256(json.dumps(ACTION_DOMAIN).encode()).hexdigest(),
        "equivalence_report_sha256": _sha256(args.equivalence_report),
        "bad_gpu_manifest_sha256": bad["gpu_manifest_sha256"],
        "oracle_identity": "entropy_src.main_sm.no_sha3_process_before_fw_override_insert_start.v1",
    }
    args.out.mkdir(parents=True, exist_ok=True)
    coverage_seeds = [{
        "action": action,
        "coverage_bitmap": bad_action["gpu"]["action_coverage"],
        "source": "GPU semantic action-bin",
    }]
    violations = [{
        "action": action,
        "oracle_violation": bool(bad_action["gpu"]["early_sha3_process"]),
        "minimal_action_sequence": [action],
    }]
    known = [{
        "issue": report["issue"],
        "bad_actions": [action] if bad_action["gpu"]["early_sha3_process"] else [],
        "fixed_expected_oracle_violation": False,
        "fixed_observed_oracle_violation": bool(fixed_action["gpu"]["early_sha3_process"]),
    }]
    for name, value in (("new_coverage_seeds.json", coverage_seeds), ("oracle_violation_seeds.json", violations), ("known_regression_seeds.json", known)):
        (args.out / name).write_text(json.dumps({"identities": identities, "seeds": value}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    policy_metrics = _metrics(action, bad_action)
    summary = {
        "schema_version": 1,
        "identities": identities,
        "action_domain": list(ACTION_DOMAIN),
        "exploration_budget": {
            "unit": "complete action-domain permutation",
            "campaigns_per_policy": 1,
            "episodes_per_campaign": 1,
            "basis": "the declared minimal trigger domain has one action",
        },
        "coverage_semantics": "explicit functional action-bin bitmap; not native Verilator coverage storage",
        "random": policy_metrics,
        "stratified": policy_metrics,
        "rejected_claim": "random and stratified are identical on the one-action minimal domain; this is corpus evidence, not policy or PPO evidence",
    }
    summary_path = args.out / "entropy10983_campaign_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "summary": str(summary_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
