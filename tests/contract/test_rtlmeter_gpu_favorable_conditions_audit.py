import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_gpu_favorable_conditions_audit import build_audit  # noqa: E402


class RtlmeterGpuFavorableConditionsAuditTest(HybridCliTestCase):
    def _write_inputs(self, root: Path, *, favorable: bool = True) -> tuple[Path, Path]:
        reports = root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        nvdla = reports / "nvdla.json"
        vortex = reports / "vortex.json"
        nvdla.write_text(
            json.dumps(
                {
                    "planned_measurement_count": 4,
                    "measured_count": 4,
                    "coverage_passed_count": 4,
                    "gpu_favorable_count": 4 if favorable else 3,
                    "best_measured": {
                        "shape": "2048x64",
                        "median": {"cpu_to_hybrid_wall_speedup": 2553.0 if favorable else 0.5},
                    },
                }
            ),
            encoding="utf-8",
        )
        vortex.write_text(
            json.dumps(
                {
                    "status": "blocked_missing_first_gate",
                    "missing_prerequisites": [
                        "cpu_vs_hybrid_timing_report.vortex",
                        "lowered_tb_mem_access_device_helper_integration",
                    ],
                }
            ),
            encoding="utf-8",
        )
        return nvdla, vortex

    def test_audit_marks_goal_satisfied_by_nvdla_hot_ss(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nvdla, vortex = self._write_inputs(root)

            audit = build_audit(root, nvdla_summary_path=nvdla.relative_to(root), vortex_readiness_path=vortex.relative_to(root))

        self.assertEqual(audit["surface"], "rtlmeter_gpu_favorable_conditions_audit")
        self.assertEqual(audit["status"], "goal_satisfied_by_nvdla_hot_ss")
        self.assertTrue(audit["completion_decision"]["achieved"])
        self.assertEqual(audit["nvdla"]["gpu_favorable_count"], 4)
        self.assertEqual(audit["nvdla"]["best_shape"], "2048x64")
        self.assertFalse(audit["vortex"]["cpu_vs_hybrid_timing_present"])
        self.assertEqual(audit["veer"]["role"], "portability_evidence_not_gpu_favorable_condition_basis")
        self.assert_no_local_absolute_paths(json.dumps(audit, sort_keys=True))

    def test_audit_requires_all_planned_nvdla_shapes_to_be_favorable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nvdla, vortex = self._write_inputs(root, favorable=False)

            audit = build_audit(root, nvdla_summary_path=nvdla.relative_to(root), vortex_readiness_path=vortex.relative_to(root))

        self.assertEqual(audit["status"], "not_satisfied")
        self.assertFalse(audit["completion_decision"]["achieved"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nvdla, vortex = self._write_inputs(root)
            out = root / "reports" / "audit.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_gpu_favorable_conditions_audit.py",
                "--repo-root",
                root.as_posix(),
                "--nvdla-summary",
                nvdla.relative_to(root).as_posix(),
                "--vortex-readiness",
                vortex.relative_to(root).as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertTrue(report_payload["completion_decision"]["achieved"])
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
