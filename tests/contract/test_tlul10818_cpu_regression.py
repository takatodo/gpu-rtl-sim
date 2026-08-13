from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from run_tlul10818_cpu_regression import ACTIONS, RTL_RELATIVE_PATHS, TESTBENCH
from run_tlul10818_gpu_equivalence import _patch_script


class Tlul10818CpuRegressionContractTest(unittest.TestCase):
    def test_contract_has_two_temporal_actions(self) -> None:
        self.assertEqual(ACTIONS, (0, 1))
        self.assertTrue(TESTBENCH.is_file())

    def test_contract_compiles_the_issue_module_and_its_direct_dependencies(self) -> None:
        self.assertIn("hw/ip/tlul/rtl/tlul_adapter_sram.sv", RTL_RELATIVE_PATHS)
        self.assertIn("hw/ip/tlul/rtl/tlul_pkg.sv", RTL_RELATIVE_PATHS)

    def test_gpu_schedule_keeps_backpressure_state_local(self) -> None:
        offsets = {"clk_i": 0, "rst_ni": 1, "start_i": 2, "d_backpressure_i": 3}
        immediate = _patch_script(offsets, backpressure=False).splitlines()
        stalled = _patch_script(offsets, backpressure=True).splitlines()
        self.assertEqual(len(immediate), len(stalled))
        self.assertIn("3:0", immediate[0])
        self.assertIn("3:1", stalled[0])


if __name__ == "__main__":
    unittest.main()
