from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from edn23526_gpu_schedule import ACTION_DOMAIN, action_bits, patch_script  # noqa: E402
from run_edn23526_gpu_equivalence import GPU_TB, OBSERVABLES, _parse_cpu  # noqa: E402
from summarize_edn23526_campaign import _campaign, _metrics  # noqa: E402


class Edn23526GpuEquivalenceContractTest(unittest.TestCase):
    def test_contract_has_single_protocol_action(self) -> None:
        self.assertEqual(
            ACTION_DOMAIN,
            ("success_ack_ready", "success_ack_backpressured", "error_ack_ready", "error_ack_backpressured"),
        )
        self.assertTrue(GPU_TB.is_file())

    def test_gpu_observables_are_semantic_oracle_outputs(self) -> None:
        self.assertIn("protocol_violation_o", OBSERVABLES)
        self.assertIn("valid_after_error_o", OBSERVABLES)
        self.assertIn("csrng_req_valid_seen_o", OBSERVABLES)

    def test_schedule_uses_cpu_observed_drive_cycles(self) -> None:
        offsets = {"clk_i": 0, "rst_ni": 1, "start_i": 2, "inject_error_i": 3, "csrng_ready_i": 4}
        script = patch_script(offsets, action="error_ack_backpressured", drive_cycles=3).splitlines()
        self.assertEqual(script[0], "0:0 1:0 2:0 3:1 4:0")
        self.assertEqual(script.count("0:1"), 5)
        self.assertIn("0:0 2:0", script)

    def test_action_bits_distinguish_oracle_risk_from_coverage(self) -> None:
        self.assertEqual(action_bits("success_ack_ready"), (False, False))
        self.assertEqual(action_bits("error_ack_backpressured"), (True, True))

    def test_cpu_result_parser_extracts_gpu_contract_fields(self) -> None:
        result = _parse_cpu("RESULT done=1 protocol_violation=0 valid_after_error=1 valid_seen=1 coverage=1 drive_cycles=9 error=1 backpressure=0\n")
        self.assertEqual(result["protocol_violation"], 0)
        self.assertEqual(result["valid_after_error"], 1)
        self.assertEqual(result["drive_cycles"], 9)

    def test_campaign_metrics_separate_coverage_from_oracle(self) -> None:
        actions = {
            action: {"gpu": {"action_coverage": 1 << index, "protocol_violation": int(action == "error_ack_backpressured")}}
            for index, action in enumerate(ACTION_DOMAIN)
        }
        campaign = _campaign(ACTION_DOMAIN, actions)
        self.assertEqual(campaign["coverage_bitmap"], 0b1111)
        self.assertEqual(campaign["time_to_first_violation"], 4)
        self.assertEqual(_metrics([campaign])["time_to_first_violation"]["max"], 4)


if __name__ == "__main__":
    unittest.main()
