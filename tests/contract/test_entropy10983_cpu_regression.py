from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from run_entropy10983_cpu_regression import ACTION_DOMAIN, RTL_RELATIVE_PATHS, TESTBENCH, _parse_result  # noqa: E402


class Entropy10983CpuRegressionContractTest(unittest.TestCase):
    def test_contract_has_minimal_temporal_action(self) -> None:
        self.assertEqual(ACTION_DOMAIN, ("health_tests_before_fw_sha3_start",))
        self.assertTrue(TESTBENCH.is_file())

    def test_contract_compiles_main_sm_and_sparse_fsm_dependency(self) -> None:
        self.assertIn("hw/ip/entropy_src/rtl/entropy_src_main_sm.sv", RTL_RELATIVE_PATHS)
        self.assertIn("hw/ip/prim/rtl/prim_sparse_fsm_flop.sv", RTL_RELATIVE_PATHS)

    def test_result_parser_extracts_oracle_observables(self) -> None:
        parsed = _parse_result("RESULT early_sha3_process=1 sha3_process=0 fw_start=0 main_sm_err=0 state=1af\n")
        self.assertEqual(parsed["early_sha3_process"], 1)
        self.assertEqual(parsed["fw_start"], 0)
        self.assertEqual(parsed["main_sm_err"], 0)


if __name__ == "__main__":
    unittest.main()
