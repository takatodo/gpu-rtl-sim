"""Static authority checks for the Ibex #2188 benchmark target."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = REPO_ROOT / "config" / "ibex2188_boundary_benchmark.json"
BAD_REVISION = "668233699df9ec2a40413e69e0de0a5b10185980"
FIXED_REVISION = "9e4a950aa6aa0e20eb638aeeb78743d4a9ddaaeb"


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
        self.assertTrue(
            all(
                candidate["finite_values_status"].startswith("pending_")
                for candidate in candidates
            )
        )

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


if __name__ == "__main__":
    unittest.main()
