#!/usr/bin/env python3
"""Contract checks for the explicit resident GPU runtime boundary."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_VL_HYBRID = REPO_ROOT / "src" / "tools" / "run_vl_hybrid.py"
RESIDENT_GATE = REPO_ROOT / "config" / "scaling_gates" / "xuantie_e902_memory_resident_workload.json"
README = REPO_ROOT / "README.md"
RUNTIME = REPO_ROOT / "src" / "hybrid" / "run_vl_hybrid.c"


class ResidentRuntimeContractTest(unittest.TestCase):
    def test_resident_steps_rejects_host_patches_before_runtime_launch(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUN_VL_HYBRID),
                "--resident-steps",
                "--patch",
                "0:1",
                "--storage-size",
                "1",
                "--cubin",
                "/no/such/file",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--resident-steps rejects --patch and --patch-script", completed.stderr)

    def test_resident_gate_requires_resident_steps_for_every_run(self) -> None:
        gate = json.loads(RESIDENT_GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate"], "xuantie_e902_memory_resident_workload_scaling")
        self.assertGreater(len(gate["runs"]), 0)
        self.assertTrue(all(run.get("resident_steps") is True for run in gate["runs"]))

    def test_runtime_reports_resident_mode(self) -> None:
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("RUN_VL_HYBRID_RESIDENT_STEPS", runtime)
        self.assertIn('printf("resident_mode: %s\\n"', runtime)

    def test_readme_keeps_xuantie_boundary_limited(self) -> None:
        readme = README.read_text(encoding="utf-8")
        self.assertIn("XuanTie-E902 Resident Runtime Boundary", readme)
        self.assertIn("GPU resident mode beats", readme)
        self.assertIn("Not broad XuanTie family support", readme)
        self.assertIn("resident --patch / --patch-script semantics", readme)


if __name__ == "__main__":
    unittest.main()
