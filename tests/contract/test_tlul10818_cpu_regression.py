from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from run_tlul10818_cpu_regression import ACTIONS, RTL_RELATIVE_PATHS, TESTBENCH


class Tlul10818CpuRegressionContractTest(unittest.TestCase):
    def test_contract_has_two_temporal_actions(self) -> None:
        self.assertEqual(ACTIONS, (0, 1))
        self.assertTrue(TESTBENCH.is_file())

    def test_contract_compiles_the_issue_module_and_its_direct_dependencies(self) -> None:
        self.assertIn("hw/ip/tlul/rtl/tlul_adapter_sram.sv", RTL_RELATIVE_PATHS)
        self.assertIn("hw/ip/tlul/rtl/tlul_pkg.sv", RTL_RELATIVE_PATHS)


if __name__ == "__main__":
    unittest.main()
