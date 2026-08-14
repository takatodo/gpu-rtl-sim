from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

from run_edn23526_cpu_regression import (  # noqa: E402
    ACTION_DOMAIN,
    PRIM_ALIAS,
    RTL_RELATIVE_PATHS,
    TESTBENCH,
    _parse_result,
)


class Edn23526CpuRegressionContractTest(unittest.TestCase):
    def test_contract_has_minimal_temporal_action(self) -> None:
        self.assertEqual(ACTION_DOMAIN, ("error_ack_backpressured",))
        self.assertTrue(TESTBENCH.is_file())

    def test_contract_compiles_edn_core_and_direct_protocol_dependencies(self) -> None:
        self.assertIn("hw/ip/edn/rtl/edn_core.sv", RTL_RELATIVE_PATHS)
        self.assertIn("hw/ip/edn/rtl/edn_main_sm.sv", RTL_RELATIVE_PATHS)
        self.assertIn("hw/ip/csrng/rtl/csrng_pkg.sv", RTL_RELATIVE_PATHS)

    def test_contract_records_direct_primitive_alias_surface(self) -> None:
        self.assertTrue(PRIM_ALIAS.is_file())
        self.assertIn("hw/ip/prim_generic/rtl/prim_generic_flop.sv", RTL_RELATIVE_PATHS)
        self.assertIn("hw/ip/prim_generic/rtl/prim_generic_buf.sv", RTL_RELATIVE_PATHS)

    def test_result_parser_extracts_oracle_observables(self) -> None:
        parsed = _parse_result("RESULT protocol_violation=1 valid_after_error=0\n")
        self.assertEqual(parsed, {"protocol_violation": 1, "valid_after_error": 0})


if __name__ == "__main__":
    unittest.main()
