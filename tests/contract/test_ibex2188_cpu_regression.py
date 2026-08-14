"""Static checks for the directed Ibex #2188 CPU regression runner."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts" / "run_ibex2188_cpu_regression.sh"
TESTBENCH = REPO_ROOT / "examples" / "ibex2188" / "ibex2188_ecc_temporal_tb.sv"
TARGET = REPO_ROOT / "config" / "ibex2188_boundary_benchmark.json"


class Ibex2188CpuRegressionTest(unittest.TestCase):
    def test_runner_is_shell_valid_and_pins_target_revisions(self) -> None:
        subprocess.run(["bash", "-n", str(RUNNER)], check=True)
        source = RUNNER.read_text(encoding="utf-8")
        target = json.loads(TARGET.read_text(encoding="utf-8"))["target"]
        self.assertIn(target["bad_revision"], source)
        self.assertIn(target["fixed_revision"], source)
        self.assertIn("output path already exists", source)
        self.assertIn("IBEX2188_RESULT", source)

    def test_testbench_targets_the_issue_guard_and_alert_oracle(self) -> None:
        source = TESTBENCH.read_text(encoding="utf-8")
        self.assertIn("core_i.rf_rd_a_wb_match", source)
        self.assertIn("core_i.rf_write_wb == 1'b0", source)
        self.assertIn("alert_major_internal_o", source)
        self.assertIn("directed_load_dependent_branch_one_cycle_response_v1", RUNNER.read_text())


if __name__ == "__main__":
    unittest.main()
