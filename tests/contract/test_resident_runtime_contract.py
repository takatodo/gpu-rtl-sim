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
VEER_EL2_RESIDENT_GATE = REPO_ROOT / "config" / "scaling_gates" / "veer_el2_resident_workload.json"
VEER_EL2_CPU_GATE = REPO_ROOT / "config" / "scaling_gates" / "veer_el2_cpu_exact_loop_resident_workload.json"
VEER_EL2_TEMPLATE = REPO_ROOT / "config" / "slice_launch_templates" / "veer_el2.json"
VEER_EL2_ASSETS = REPO_ROOT / "third_party" / "rtlmeter" / "designs" / "VeeR-EL2"
TARGETS = REPO_ROOT / "config" / "targets.json"
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

    def test_veer_el2_resident_gate_is_defined_before_asset_copy(self) -> None:
        gate = json.loads(VEER_EL2_RESIDENT_GATE.read_text(encoding="utf-8"))
        cpu_gate = json.loads(VEER_EL2_CPU_GATE.read_text(encoding="utf-8"))
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate"], "veer_el2_resident_workload_scaling")
        self.assertEqual(gate["target"], "veer_el2")
        self.assertGreater(len(gate["runs"]), 0)
        self.assertTrue(all(run.get("resident_steps") is True for run in gate["runs"]))
        self.assertEqual(cpu_gate["source_gpu_gate"], "config/scaling_gates/veer_el2_resident_workload.json")
        veer_targets = [target for target in targets["active_targets"] if target["name"] == "veer_el2"]
        self.assertEqual(len(veer_targets), 1)
        self.assertIn(
            veer_targets[0]["status"],
            {"resident_gate_defined_before_asset_copy", "asset_boundary_materialized"},
        )

    def test_veer_el2_asset_boundary_is_materialized_without_work_history(self) -> None:
        template = json.loads(VEER_EL2_TEMPLATE.read_text(encoding="utf-8"))
        required_paths = [
            VEER_EL2_ASSETS / "descriptor.yaml",
            VEER_EL2_ASSETS / "LICENSE-VeeR-EL2",
            REPO_ROOT / template["runner_args_template"]["coverage_tb_path"],
            REPO_ROOT / template["enrollment"]["runtime_input_path"],
            VEER_EL2_ASSETS / "tests" / "veer_el2_coverage_regions.json",
            VEER_EL2_ASSETS / "tests" / "veer_el2_program_hex_target_config.json",
        ]
        for path in required_paths:
            self.assertTrue(path.exists(), str(path.relative_to(REPO_ROOT)))
        copied_files = [path.relative_to(VEER_EL2_ASSETS).parts[0] for path in VEER_EL2_ASSETS.rglob("*") if path.is_file()]
        self.assertNotIn("work", copied_files)
        self.assertNotIn("output", copied_files)

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
        self.assertIn("config/scaling_gates/veer_el2_resident_workload.json", readme)
        self.assertIn("validate_veer_el2_asset_boundary", readme)


if __name__ == "__main__":
    unittest.main()
