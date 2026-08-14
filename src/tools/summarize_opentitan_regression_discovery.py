#!/usr/bin/env python3
"""Build a consolidated OpenTitan regression-discovery evidence table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TARGETS = (
    {
        "name": "tlul10818",
        "ip": "tlul",
        "cpu": "artifacts/tlul10818_cpu/tlul10818_cpu_regression.json",
        "equivalence": "artifacts/tlul10818_scale_equivalence/tlul10818_gpu_equivalence.json",
        "campaign": "artifacts/tlul10818_scale_campaign/tlul10818_campaign_summary.json",
        "corpus_dir": "artifacts/tlul10818_scale_campaign",
        "graph": "artifacts/tlul10818_scale_campaign/tlul10818_time_to_violation.svg",
    },
    {
        "name": "edn23526",
        "ip": "edn",
        "cpu": "artifacts/edn23526_cpu/edn23526_cpu_regression.json",
        "equivalence": "artifacts/edn23526_gpu_equivalence/edn23526_gpu_equivalence.json",
        "campaign": "artifacts/edn23526_campaign/edn23526_campaign_summary.json",
        "corpus_dir": "artifacts/edn23526_campaign",
        "graph": "artifacts/edn23526_campaign/edn23526_time_to_violation.svg",
    },
    {
        "name": "entropy10983",
        "ip": "entropy_src",
        "cpu": "artifacts/entropy10983_cpu/entropy10983_cpu_regression.json",
        "equivalence": "artifacts/entropy10983_gpu_equivalence/entropy10983_gpu_equivalence.json",
        "campaign": "artifacts/entropy10983_campaign/entropy10983_campaign_summary.json",
        "corpus_dir": "artifacts/entropy10983_campaign",
        "graph": "artifacts/entropy10983_campaign/entropy10983_time_to_violation.svg",
    },
)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _revision(report: dict[str, object], label: str) -> dict[str, object]:
    return next(item for item in report["revisions"] if item["label"] == label)


def _action_violation(action: dict[str, object]) -> bool:
    observed = action["gpu"]
    for key in ("oracle_violation", "protocol_violation", "early_sha3_process"):
        if key in observed:
            return bool(observed[key])
    return False


def _cpu_gpu_actions_match(revision: dict[str, object]) -> bool:
    return all(action["status"] == "pass" and action["cpu"] == action["gpu"] for action in revision["actions"])


def _corpus_files_exist(corpus_dir: Path) -> bool:
    return all((corpus_dir / name).is_file() for name in (
        "new_coverage_seeds.json",
        "oracle_violation_seeds.json",
        "known_regression_seeds.json",
    ))


def _corpus(corpus_dir: Path, name: str) -> dict[str, object]:
    return _load(corpus_dir / name)


def _minimal_violation_seeds(violation_corpus: dict[str, object]) -> list[str]:
    seeds = []
    for seed in violation_corpus["seeds"]:
        sequence = seed.get("minimal_action_sequence", [])
        if seed.get("oracle_violation") is True and len(sequence) == 1:
            seeds.append(sequence[0])
    return seeds


def _temporal_evidence(revision: dict[str, object]) -> dict[str, object]:
    drive_cycles = [
        int(action["drive_cycles"])
        for action in revision["actions"]
        if "drive_cycles" in action
    ]
    resident_batch = revision.get("gpu_resident_batch", {})
    return {
        "drive_cycles": sorted(set(drive_cycles)),
        "resident_batch_status": resident_batch.get("status"),
        "resident_batch_state_count": resident_batch.get("state_count"),
    }


def _has_temporal_evidence(evidence: dict[str, object]) -> bool:
    return bool(evidence["drive_cycles"]) or evidence["resident_batch_status"] == "pass"


def _cpu_oracle_split(cpu_report: dict[str, object]) -> bool:
    if cpu_report["status"] != "pass":
        return False
    bad = _revision(cpu_report, "bad")
    fixed = _revision(cpu_report, "fixed")
    if "observed_oracle_pass" in bad and "observed_oracle_pass" in fixed:
        return bad["observed_oracle_pass"] is False and fixed["observed_oracle_pass"] is True
    bad_expected = bad.get("expected", {})
    fixed_expected = fixed.get("expected", {})
    bad_observed = bad.get("observed", {})
    fixed_observed = fixed.get("observed", {})
    if any(bad_observed.get(key) != value for key, value in bad_expected.items()):
        return False
    if any(fixed_observed.get(key) != value for key, value in fixed_expected.items()):
        return False
    return any(bad_expected.get(key) == 1 and fixed_expected.get(key) == 0 for key in bad_expected)


def _target_summary(root: Path, target: dict[str, str]) -> dict[str, object]:
    cpu = _load(root / target["cpu"])
    equivalence = _load(root / target["equivalence"])
    campaign = _load(root / target["campaign"])
    corpus_dir = root / target["corpus_dir"]
    coverage_corpus = _corpus(corpus_dir, "new_coverage_seeds.json")
    violation_corpus = _corpus(corpus_dir, "oracle_violation_seeds.json")
    known_corpus = _corpus(corpus_dir, "known_regression_seeds.json")
    bad = _revision(equivalence, "bad")
    fixed = _revision(equivalence, "fixed")
    identities = campaign["identities"]
    budget = campaign["exploration_budget"]
    bad_violations = [action["action"] for action in bad["actions"] if _action_violation(action)]
    fixed_violations = [action["action"] for action in fixed["actions"] if _action_violation(action)]
    minimal_violation_seeds = _minimal_violation_seeds(violation_corpus)
    temporal_evidence = _temporal_evidence(bad)
    graph_path = root / target["graph"]
    return {
        "name": target["name"],
        "ip": target["ip"],
        "issue": equivalence["issue"],
        "cpu_regression_status": cpu["status"],
        "cpu_bad_fixed_oracle_split": _cpu_oracle_split(cpu),
        "gpu_equivalence_status": equivalence["status"],
        "bad_revision": identities["bad_revision"],
        "fixed_revision": identities["fixed_revision"],
        "checkpoint_identity": identities["checkpoint_identity"],
        "oracle_identity": identities["oracle_identity"],
        "bad_gpu_manifest_sha256": identities["bad_gpu_manifest_sha256"],
        "action_domain_size": len(campaign["action_domain"]),
        "bad_oracle_violation_actions": bad_violations,
        "fixed_oracle_violation_actions": fixed_violations,
        "minimal_oracle_violation_seeds": minimal_violation_seeds,
        "minimal_cpu_seed_reproduced": cpu["status"] == "pass" and bool(minimal_violation_seeds),
        "cpu_gpu_semantic_match": _cpu_gpu_actions_match(bad) and _cpu_gpu_actions_match(fixed),
        "temporal_evidence": temporal_evidence,
        "short_temporal_or_resident_batch_evidence": _has_temporal_evidence(temporal_evidence),
        "corpus_files_exist": _corpus_files_exist(corpus_dir),
        "new_coverage_seed_count": len(coverage_corpus["seeds"]),
        "oracle_violation_seed_count": len(violation_corpus["seeds"]),
        "known_regression_seed_count": len(known_corpus["seeds"]),
        "graph_exists": graph_path.is_file() and graph_path.stat().st_size > 0,
        "random_campaign_count": campaign["random"]["campaign_count"],
        "stratified_campaign_count": campaign["stratified"]["campaign_count"],
        "episodes_per_campaign": budget["episodes_per_campaign"],
        "random_time_to_first_violation": campaign["random"]["time_to_first_violation"],
        "stratified_time_to_first_violation": campaign["stratified"]["time_to_first_violation"],
    }


def _target_passed(row: dict[str, object]) -> bool:
    return (
        row["cpu_regression_status"] == "pass"
        and row["cpu_bad_fixed_oracle_split"]
        and row["gpu_equivalence_status"] == "pass"
        and bool(row["bad_oracle_violation_actions"])
        and not row["fixed_oracle_violation_actions"]
        and row["minimal_cpu_seed_reproduced"]
        and row["cpu_gpu_semantic_match"]
        and row["short_temporal_or_resident_batch_evidence"]
        and row["corpus_files_exist"]
        and row["new_coverage_seed_count"] > 0
        and row["oracle_violation_seed_count"] > 0
        and row["known_regression_seed_count"] > 0
        and row["graph_exists"]
        and row["random_campaign_count"] == row["stratified_campaign_count"]
    )


def _markdown(rows: list[dict[str, object]]) -> str:
    lines = [
        "| target | ip | action domain | minimal violation seeds | temporal evidence | random mean | stratified mean | long-tail random/stratified | status |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        random_time = row["random_time_to_first_violation"]
        stratified_time = row["stratified_time_to_first_violation"]
        temporal = row["temporal_evidence"]
        temporal_text = "drive_cycles=" + ",".join(str(value) for value in temporal["drive_cycles"])
        if temporal["resident_batch_status"] == "pass":
            temporal_text = f"resident_batch={temporal['resident_batch_state_count']}"
        lines.append(
            "| {name} | {ip} | {domain} | {minimal} | {temporal} | {rmean:g} | {smean:g} | {rtail:g}/{stail:g} | {status} |".format(
                name=row["name"],
                ip=row["ip"],
                domain=row["action_domain_size"],
                minimal=", ".join(row["minimal_oracle_violation_seeds"]),
                temporal=temporal_text,
                rmean=float(random_time["mean"]),
                smean=float(stratified_time["mean"]),
                rtail=float(random_time["long_tail_rate_after_episode_1"]),
                stail=float(stratified_time["long_tail_rate_after_episode_1"]),
                status="pass" if _target_passed(row) else "fail",
            )
        )
    return "\n".join(lines) + "\n"


def build_summary(root: Path) -> dict[str, object]:
    rows = [_target_summary(root, target) for target in TARGETS]
    ips = sorted({row["ip"] for row in rows})
    return {
        "schema_version": 1,
        "status": "pass" if len(ips) >= 2 and all(_target_passed(row) for row in rows) else "fail",
        "target_count": len(rows),
        "ip_count": len(ips),
        "ips": ips,
        "targets": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    summary = build_summary(root)
    args.out.mkdir(parents=True, exist_ok=True)
    summary_path = args.out / "opentitan_regression_discovery_summary.json"
    table_path = args.out / "opentitan_regression_discovery_summary.md"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    table_path.write_text(_markdown(summary["targets"]), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "summary": str(summary_path), "table": str(table_path)}, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
