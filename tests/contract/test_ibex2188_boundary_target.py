"""Static authority checks for the Ibex #2188 benchmark target."""

from __future__ import annotations

import json
import hashlib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = REPO_ROOT / "config" / "ibex2188_boundary_benchmark.json"
BAD_REVISION = "668233699df9ec2a40413e69e0de0a5b10185980"
FIXED_REVISION = "9e4a950aa6aa0e20eb638aeeb78743d4a9ddaaeb"


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


class Ibex2188BoundaryTargetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.target_document = json.loads(TARGET_PATH.read_text(encoding="utf-8"))

    def test_pins_the_public_issue_and_parent_fix_pair(self) -> None:
        target = self.target_document["target"]
        self.assertEqual(self.target_document["schema_version"], 1)
        self.assertEqual(
            self.target_document["surface"], "ibex2188_boundary_benchmark_target"
        )
        self.assertEqual(
            target["issue"], "https://github.com/lowRISC/ibex/issues/2188"
        )
        self.assertEqual(target["bad_revision"], BAD_REVISION)
        self.assertEqual(target["fixed_revision"], FIXED_REVISION)
        self.assertEqual(target["fix_commit"], FIXED_REVISION)
        self.assertNotEqual(target["bad_revision"], target["fixed_revision"])

    def test_requires_the_ecc_capable_writeback_configuration(self) -> None:
        configuration = self.target_document["target"]["configuration"]
        self.assertEqual(configuration["named_configuration"], "opentitan")
        self.assertEqual(configuration["SecureIbex"], 1)
        self.assertEqual(configuration["WritebackStage"], 1)
        self.assertEqual(configuration["RegFile"], "ibex_pkg::RegFileFF")
        self.assertEqual(configuration["RegFileECC"], "derived_from_SecureIbex")

    def test_oracle_projection_is_separate_and_not_a_predeclared_grid(self) -> None:
        projection = self.target_document["target"]["semantic_projection"]
        observable_names = [row["name"] for row in projection["observables"]]
        observable_ids = [row["semantic_id"] for row in projection["observables"]]
        self.assertEqual(len(observable_names), len(set(observable_names)))
        self.assertEqual(len(observable_ids), len(set(observable_ids)))
        self.assertNotIn(projection["oracle"]["name"], observable_names)
        self.assertNotIn(projection["oracle"]["semantic_id"], observable_ids)
        candidates = self.target_document["sweep_axis_candidates"]
        self.assertGreaterEqual(len(candidates), 1)
        self.assertTrue(
            all("values" not in candidate for candidate in candidates),
            "finite axis values require the external directed-wrapper Contract",
        )
        statuses = {candidate["name"]: candidate["finite_values_status"] for candidate in candidates}
        self.assertEqual(statuses.pop("fault_enable"), "admitted_cpu_sweep")
        self.assertEqual(
            statuses.pop("load_response_delay_cycles"),
            "verified_ordered_control",
        )
        self.assertTrue(all(status.startswith("pending_") for status in statuses.values()))

    def test_current_cpu_evidence_preserves_the_issue_guard_transition(self) -> None:
        evidence = self.target_document["current_cpu_evidence"]
        self.assertEqual(evidence["bad_oracle_violation"], 1)
        self.assertEqual(evidence["fixed_oracle_violation"], 0)
        bad = evidence["semantic_projection_at_injection"]["bad"]
        fixed = evidence["semantic_projection_at_injection"]["fixed"]
        self.assertEqual(
            {key: bad[key] for key in ("rf_read_enable", "rf_wb_match", "rf_write_wb", "instruction_valid_id")},
            {key: fixed[key] for key in ("rf_read_enable", "rf_wb_match", "rf_write_wb", "instruction_valid_id")},
        )
        self.assertEqual((bad["rf_ecc_error_id"], bad["alert_major_internal"]), (0, 0))
        self.assertEqual((fixed["rf_ecc_error_id"], fixed["alert_major_internal"]), (1, 1))

    def test_admitted_cpu_sweep_evidence_is_hash_pinned(self) -> None:
        evidence = self.target_document["current_cpu_sweep_evidence"]
        self.assertEqual(evidence["status"], "admitted_cpu_ground_truth")
        self.assertEqual(evidence["point_count"], 4)
        self.assertEqual(evidence["bad_failure_count"], 1)
        self.assertEqual(evidence["fixed_failure_count"], 0)
        self.assertEqual(evidence["bad_boundary_edge_count"], 2)
        self.assertEqual(evidence["disappeared_failure_count"], 1)
        for artifact in evidence["artifacts"].values():
            path = REPO_ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )

    def test_admitted_cpu_sweep_analysis_matches_the_boundary_contract(self) -> None:
        artifacts = self.target_document["current_cpu_sweep_evidence"]["artifacts"]
        analysis = json.loads(
            (REPO_ROOT / artifacts["analysis"]["path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(analysis["surface"], "rtl_boundary_analysis")
        self.assertEqual(analysis["point_count"], 4)
        self.assertEqual(
            [
                (row["parameters"]["fault_enable"], row["parameters"]["load_response_delay_cycles"])
                for row in analysis["observations"]
            ],
            [
                ("disabled", 0),
                ("disabled", 1),
                ("guarded_bit0", 0),
                ("guarded_bit0", 1),
            ],
        )
        self.assertEqual(
            [(row["bad_oracle"], row["fixed_oracle"]) for row in analysis["observations"]],
            [(0, 0), (0, 0), (0, 0), (1, 0)],
        )
        self.assertEqual(analysis["revisions"]["bad"]["fail_point_count"], 1)
        self.assertEqual(analysis["revisions"]["bad"]["boundary_edge_count"], 2)
        self.assertEqual(analysis["revisions"]["bad"]["failure_component_count"], 1)
        self.assertEqual(analysis["revisions"]["fixed"]["fail_point_count"], 0)
        self.assertEqual(
            len(analysis["bad_to_fixed"]["disappeared_failure_point_ids"]),
            1,
        )

    def test_boundary_profile_inputs_are_hash_pinned_and_gpu_ready(self) -> None:
        profile = self.target_document["current_boundary_profile_inputs"]
        self.assertEqual(
            profile["status"], "experiment_contract_and_gpu_evidence_ready"
        )
        for artifact in profile["artifacts"].values():
            path = REPO_ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"]
            )
        contract = json.loads(
            (REPO_ROOT / profile["artifacts"]["experiment_contract"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["surface"], "rtl_boundary_experiment_contract")
        self.assertEqual(contract["experiment_id"], "ibex2188-boundary-v1")
        self.assertEqual(contract["target"]["target_id"], "ibex2188")
        self.assertEqual(canonical_sha256(contract), profile["experiment_contract_sha256"])
        self.assertEqual(
            contract["sweep_space_sha256"],
            self.target_document["current_cpu_sweep_evidence"]["sweep_space_sha256"],
        )
        self.assertEqual(
            [row["action"] for row in contract["action_domain"]],
            [
                "fault_enable:disabled__load_response_delay_cycles:0",
                "fault_enable:disabled__load_response_delay_cycles:1",
                "fault_enable:guarded_bit0__load_response_delay_cycles:0",
                "fault_enable:guarded_bit0__load_response_delay_cycles:1",
            ],
        )
        self.assertEqual(
            {trial["trial_id"] for trial in contract["trials"]},
            {
                "random_gpu",
                "stratified_gpu",
                "ordered_refinement_gpu",
                "novelty_gpu",
                "random_cpu",
            },
        )
        self.assertIn(
            "ordered_refinement_gpu",
            {trial["trial_id"] for trial in contract["trials"]},
        )
        ordered = next(
            trial for trial in contract["trials"] if trial["trial_id"] == "ordered_refinement_gpu"
        )
        self.assertEqual(
            ordered["policy"]["kind"], "ordered_refinement"
        )
        self.assertEqual(
            ordered["policy"]["configuration"]["axis"], "load_response_delay_cycles"
        )


if __name__ == "__main__":
    unittest.main()
