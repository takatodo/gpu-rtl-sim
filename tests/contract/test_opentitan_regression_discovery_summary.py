from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from summarize_opentitan_regression_discovery import build_summary  # noqa: E402


class OpenTitanRegressionDiscoverySummaryContractTest(unittest.TestCase):
    def test_current_seed_set_satisfies_consolidated_evidence_contract(self) -> None:
        summary = build_summary(REPO_ROOT)
        self.assertEqual(summary["status"], "pass")
        self.assertGreaterEqual(summary["ip_count"], 2)
        self.assertEqual(summary["target_count"], 3)
        for row in summary["targets"]:
            self.assertEqual(row["cpu_regression_status"], "pass")
            self.assertEqual(row["gpu_equivalence_status"], "pass")
            self.assertTrue(row["bad_oracle_violation_actions"])
            self.assertFalse(row["fixed_oracle_violation_actions"])
            self.assertTrue(row["cpu_gpu_semantic_match"])
            self.assertTrue(row["corpus_files_exist"])
            self.assertTrue(row["graph_exists"])
            self.assertEqual(row["random_campaign_count"], row["stratified_campaign_count"])


if __name__ == "__main__":
    unittest.main()
