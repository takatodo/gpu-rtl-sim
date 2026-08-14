from __future__ import annotations

import unittest

from tests.contract import tlul10818_boundary_contract_checks


class Tlul10818BoundaryBenchmarkContractTest(unittest.TestCase):
    def test_boundary_contract_checks(self) -> None:
        tlul10818_boundary_contract_checks.run_contract_checks(self)


if __name__ == "__main__":
    unittest.main()
