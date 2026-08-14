#!/usr/bin/env python3
"""Derive reproducible random-vs-stratified evidence from EDN action results."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import subprocess
from pathlib import Path

from edn23526_gpu_schedule import ACTION_DOMAIN


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(path: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def _quantile_nearest_rank(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _campaign(order: tuple[str, ...], actions: dict[str, dict[str, object]]) -> dict[str, object]:
    coverage = 0
    gains: list[int] = []
    first_violation = None
    for episode, action in enumerate(order, start=1):
        observed = actions[action]["gpu"]
        action_coverage = int(observed["action_coverage"])
        gains.append(action_coverage & ~coverage)
        coverage |= action_coverage
        if first_violation is None and int(observed["protocol_violation"]):
            first_violation = episode
    return {
        "order": list(order),
        "coverage_gain_bitmap_by_episode": gains,
        "coverage_bitmap": coverage,
        "coverage_closure_episode": len(order),
        "time_to_first_violation": first_violation,
    }


def _metrics(campaigns: list[dict[str, object]]) -> dict[str, object]:
    times = [int(c["time_to_first_violation"]) for c in campaigns if c["time_to_first_violation"] is not None]
    return {
        "campaign_count": len(campaigns),
        "coverage_closure_episode": sorted({int(c["coverage_closure_episode"]) for c in campaigns}),
        "time_to_first_violation": {
            "mean": sum(times) / len(times),
            "p50": _quantile_nearest_rank(times, .50),
            "p95": _quantile_nearest_rank(times, .95),
            "max": max(times),
            "long_tail_rate_after_episode_1": sum(value > 1 for value in times) / len(times),
        },
        "coverage_progression": [
            {"episode": episode, "functional_bins_reached": episode}
            for episode in range(1, len(ACTION_DOMAIN) + 1)
        ],
    }


def _svg(random_metrics: dict[str, object], stratified_metrics: dict[str, object]) -> str:
    random_values = random_metrics["time_to_first_violation"]
    stratified_values = stratified_metrics["time_to_first_violation"]
    rows = [
        ("mean", random_values["mean"], stratified_values["mean"]),
        ("p50", random_values["p50"], stratified_values["p50"]),
        ("p95", random_values["p95"], stratified_values["p95"]),
        ("max", random_values["max"], stratified_values["max"]),
    ]
    maximum = max(float(value) for _, left, right in rows for value in (left, right))
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="560" height="260" viewBox="0 0 560 260">',
        '<style>text{font:14px sans-serif}.r{fill:#777}.s{fill:#2374ab}</style>',
        '<text x="20" y="24">EDN #23526: time to first oracle violation</text>',
    ]
    for index, (name, random_value, stratified_value) in enumerate(rows):
        y = 55 + 46 * index
        pieces.append(f'<text x="20" y="{y+15}">{name}</text>')
        for x, value, cls in ((110, float(random_value), 'r'), (330, float(stratified_value), 's')):
            width = 180 * value / maximum
            pieces.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{width:.1f}" height="16"/>')
            pieces.append(f'<text x="{x+width+5:.1f}" y="{y+14}">{value:g}</text>')
    pieces.extend(['<text x="110" y="248">random permutation</text>', '<text x="330" y="248">risk-stratified</text>', '</svg>'])
    return "".join(pieces) + "\n"


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
    actions = {str(item["action"]): item for item in bad["actions"]}
    if tuple(sorted(actions)) != tuple(sorted(ACTION_DOMAIN)):
        raise SystemExit("equivalence report does not contain the complete action domain")
    if any(item["status"] != "pass" for item in bad["actions"] + fixed["actions"]):
        raise SystemExit("equivalence report has an unproven action")
    all_orders = list(itertools.permutations(ACTION_DOMAIN))
    random_campaigns = [_campaign(order, actions) for order in all_orders]
    stratified_orders = [
        tuple(sorted(order, key=lambda action: (action != "error_ack_backpressured", action)))
        for order in all_orders
    ]
    stratified_campaigns = [_campaign(order, actions) for order in stratified_orders]
    identities = {
        "bad_revision": _git_head(args.bad_checkout),
        "fixed_revision": _git_head(args.fixed_checkout),
        "checkpoint_identity": "zero_initialized_device_clean_edn23526_gpu_tb_v1",
        "action_domain_sha256": hashlib.sha256(json.dumps(ACTION_DOMAIN).encode()).hexdigest(),
        "equivalence_report_sha256": _sha256(args.equivalence_report),
        "bad_gpu_manifest_sha256": bad["gpu_manifest_sha256"],
        "oracle_identity": "edn.csrng_req_valid_hold_after_error_ack_backpressured.v1",
    }
    args.out.mkdir(parents=True, exist_ok=True)
    coverage_seeds = [
        {"action": action, "coverage_bitmap": actions[action]["gpu"]["action_coverage"], "source": "GPU semantic action-bin"}
        for action in ACTION_DOMAIN
    ]
    violations = [
        {"action": action, "oracle_violation": True, "minimal_action_sequence": [action]}
        for action in ACTION_DOMAIN
        if actions[action]["gpu"]["protocol_violation"]
    ]
    known = [{"issue": report["issue"], "bad_actions": [seed["action"] for seed in violations], "fixed_expected_oracle_violation": False}]
    for name, value in (("new_coverage_seeds.json", coverage_seeds), ("oracle_violation_seeds.json", violations), ("known_regression_seeds.json", known)):
        (args.out / name).write_text(json.dumps({"identities": identities, "seeds": value}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    random_metrics = _metrics(random_campaigns)
    stratified_metrics = _metrics(stratified_campaigns)
    summary = {
        "schema_version": 1,
        "identities": identities,
        "action_domain": list(ACTION_DOMAIN),
        "exploration_budget": {
            "unit": "complete action-domain permutation",
            "campaigns_per_policy": len(all_orders),
            "episodes_per_campaign": len(ACTION_DOMAIN),
            "basis": "all permutations of the declared four-action domain",
        },
        "coverage_semantics": "explicit functional action-bin bitmap; not native Verilator coverage storage",
        "random": random_metrics,
        "stratified": stratified_metrics,
        "rejected_claim": "the stratified order is fixed before feedback; this is not online learning or PPO evidence",
    }
    summary_path = args.out / "edn23526_campaign_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "edn23526_time_to_violation.svg").write_text(_svg(random_metrics, stratified_metrics), encoding="utf-8")
    print(json.dumps({"status": "pass", "summary": str(summary_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
