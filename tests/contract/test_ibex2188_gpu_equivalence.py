"""Static checks for the directed Ibex #2188 GPU equivalence runner."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts" / "run_ibex2188_gpu_equivalence.sh"
GPU_TB = REPO_ROOT / "examples" / "ibex2188" / "ibex2188_ecc_temporal_gpu_tb.sv"
CPU_DRIVER = REPO_ROOT / "examples" / "ibex2188" / "ibex2188_ecc_temporal_gpu_driver.cpp"
TARGET = REPO_ROOT / "config" / "ibex2188_boundary_benchmark.json"


class Ibex2188GpuEquivalenceTest(unittest.TestCase):
    def test_runner_is_shell_valid_and_pins_target_revisions(self) -> None:
        subprocess.run(["bash", "-n", str(RUNNER)], check=True)
        source = RUNNER.read_text(encoding="utf-8")
        target = json.loads(TARGET.read_text(encoding="utf-8"))["target"]
        self.assertIn(target["bad_revision"], source)
        self.assertIn(target["fixed_revision"], source)
        self.assertIn("build_vl_gpu.py", source)
        self.assertIn("run_vl_hybrid.py", source)
        self.assertIn("match", source)

    def test_gpu_tb_is_device_clean_and_targets_the_issue_guard(self) -> None:
        source = GPU_TB.read_text(encoding="utf-8")
        self.assertNotIn("always #", source)
        # strip comment lines before asserting no system-task / timing constructs
        code = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("//")
        )
        self.assertNotIn("$display", code)
        self.assertNotIn("$finish", code)
        self.assertNotIn("initial begin", code)
        self.assertNotIn("always #", code)
        self.assertIn("core_i.rf_rd_a_wb_match", source)
        self.assertIn("core_i.rf_write_wb == 1'b0", source)
        self.assertIn("register_file", source)
        self.assertIn("done_o", source)
        self.assertIn("oracle_violation_o", source)

    def test_cpu_driver_drives_the_same_gpu_tb(self) -> None:
        source = CPU_DRIVER.read_text(encoding="utf-8")
        self.assertIn("Vibex2188_ecc_temporal_gpu_tb.h", source)
        self.assertIn("--load-response-delay", source)
        self.assertIn("--dump-state", source)
        self.assertIn("done_o", source)
        self.assertIn("oracle_violation_o", source)


if __name__ == "__main__":
    unittest.main()
