import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_nvdla_hot_ss_repeat_summary import build_summary  # noqa: E402


class RtlmeterNvdlaHotSsRepeatSummaryTest(HybridCliTestCase):
    def _write_plan(self, root: Path) -> Path:
        path = root / "reports" / "plan.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "target": "NVDLA.nvdla_cmac_a2cacc",
                    "planned_measurements": [
                        {"order": 1, "id": "a", "shape": "1024x64", "report_out": "reports/a.json"},
                        {"order": 2, "id": "b", "shape": "512x64", "report_out": "reports/b.json"},
                        {"order": 3, "id": "c", "shape": "2048x64", "report_out": "reports/c.json"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return path

    def _write_measurement(self, root: Path, rel: str, speedup: float) -> None:
        (root / rel).write_text(
            json.dumps(
                {
                    "status": "measured",
                    "repeat_count": 3,
                    "coverage_output_equivalence_all_passed": True,
                    "median": {"cpu_to_hybrid_wall_speedup": speedup, "hybrid_wall_ms": 1.0},
                    "samples": [
                        {"coverage_output": {"coverage_output_mismatch_count": 0}},
                        {"coverage_output": {"coverage_output_mismatch_count": 0}},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_summary_counts_measured_passed_and_favorable_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = self._write_plan(root)
            self._write_measurement(root, "reports/a.json", 10.0)
            self._write_measurement(root, "reports/b.json", 5.0)

            summary = build_summary(root, plan_path=plan.relative_to(root))

        self.assertEqual(summary["surface"], "rtlmeter_nvdla_hot_ss_repeat_summary")
        self.assertEqual(summary["planned_measurement_count"], 3)
        self.assertEqual(summary["measured_count"], 2)
        self.assertEqual(summary["coverage_passed_count"], 2)
        self.assertEqual(summary["gpu_favorable_count"], 2)
        self.assertEqual(summary["best_measured"]["shape"], "1024x64")
        self.assertEqual(summary["results"][2]["status"], "not_measured")
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = self._write_plan(root)
            self._write_measurement(root, "reports/a.json", 10.0)
            out = root / "reports" / "summary.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_nvdla_hot_ss_repeat_summary.py",
                "--repo-root",
                root.as_posix(),
                "--plan",
                plan.relative_to(root).as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_nvdla_hot_ss_repeat_summary")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
