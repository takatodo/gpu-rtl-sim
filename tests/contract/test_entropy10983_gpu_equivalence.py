from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from entropy10983_gpu_schedule import ACTION_DOMAIN, patch_script  # noqa: E402
from run_entropy10983_gpu_equivalence import GPU_TB, OBSERVABLES, _parse_cpu  # noqa: E402
from summarize_entropy10983_campaign import _metrics  # noqa: E402


class Entropy10983GpuEquivalenceContractTest(unittest.TestCase):
    def test_contract_has_minimal_temporal_action(self) -> None:
        self.assertEqual(ACTION_DOMAIN, ("health_tests_before_fw_sha3_start",))
        self.assertTrue(GPU_TB.is_file())

    def test_gpu_observables_are_semantic_oracle_outputs(self) -> None:
        self.assertIn("early_sha3_process_o", OBSERVABLES)
        self.assertIn("fw_start_o", OBSERVABLES)
        self.assertIn("main_sm_err_o", OBSERVABLES)

    def test_schedule_uses_cpu_observed_drive_cycles(self) -> None:
        offsets = {"clk_i": 0, "rst_ni": 1, "start_i": 2}
        script = patch_script(offsets, drive_cycles=3).splitlines()
        self.assertEqual(script[0], "0:0 1:0 2:0")
        self.assertEqual(script.count("0:1"), 5)
        self.assertIn("0:0 2:0", script)

    def test_cpu_result_parser_extracts_gpu_contract_fields(self) -> None:
        result = _parse_cpu("RESULT done=1 early_sha3_process=1 sha3_process=0 fw_start=0 main_sm_err=0 state=128 coverage=1 drive_cycles=12\n")
        self.assertEqual(result["early_sha3_process"], 1)
        self.assertEqual(result["fw_start"], 0)
        self.assertEqual(result["drive_cycles"], 12)

    def test_campaign_metrics_record_degenerate_one_action_domain(self) -> None:
        action = ACTION_DOMAIN[0]
        record = {"gpu": {"early_sha3_process": 1, "action_coverage": 1}}
        metrics = _metrics(action, record)
        self.assertEqual(metrics["campaign_count"], 1)
        self.assertEqual(metrics["time_to_first_violation"]["max"], 1)
        self.assertEqual(metrics["time_to_first_violation"]["long_tail_rate_after_episode_1"], 0.0)


if __name__ == "__main__":
    unittest.main()
