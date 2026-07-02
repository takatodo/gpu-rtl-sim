import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_nvdla_hot_ss_measurement_plan import build_plan  # noqa: E402


class RtlmeterNvdlaHotSsMeasurementPlanTest(HybridCliTestCase):
    def _write_queue_and_template(self, root: Path) -> Path:
        template = root / "config" / "slice_launch_templates" / "nvdla_cmac_a2cacc.json"
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text(json.dumps({"target": "NVDLA.nvdla_cmac_a2cacc"}), encoding="utf-8")
        queue = root / "reports" / "queue.json"
        queue.parent.mkdir(parents=True, exist_ok=True)
        queue.write_text(
            json.dumps(
                {
                    "surface": "rtlmeter_non_veer_hybrid_next_queue",
                    "queue": [
                        {
                            "id": "nvdla_hot_ss_measurement_extension",
                            "status": "ready_to_extend_measured_hot_ss",
                            "next_measurement": {
                                "preferred_shape": "1024x64",
                                "preferred_bucket": "state_batch_and_repeated_step",
                            },
                        },
                        {
                            "id": "vortex_mini_hello_first_cpu_vs_hybrid_gate",
                            "status": "blocked_until_runtime_authority_and_observable_export",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return queue

    def test_plan_expands_best_a2cacc_shape_without_claiming_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._write_queue_and_template(root)

            plan = build_plan(root, queue_path=queue.relative_to(root), repeat=5)

        self.assertEqual(plan["surface"], "rtlmeter_nvdla_hot_ss_measurement_plan")
        self.assertEqual(plan["status"], "planned_not_run")
        self.assertEqual(plan["target"], "NVDLA.nvdla_cmac_a2cacc")
        self.assertEqual(plan["source_queue_item"]["preferred_shape"], "1024x64")
        self.assertEqual(plan["planned_measurement_count"], 4)
        self.assertEqual(
            [item["shape"] for item in plan["planned_measurements"]],
            ["1024x64", "512x64", "2048x64", "1024x1"],
        )
        self.assertEqual(plan["planned_measurements"][0]["repeat"], 5)
        self.assertIn("--dry-run", plan["planned_measurements"][0]["commands"]["dry_run"])
        self.assertIn("--repeat", plan["planned_measurements"][0]["commands"]["repeat_median"])
        self.assertIn("NVDLA.nvdla_cmac_core_mac", plan["deferred"][0]["target"])
        self.assertIn("plan_only_not_measurement", plan["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(plan, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._write_queue_and_template(root)
            out = root / "reports" / "plan.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_nvdla_hot_ss_measurement_plan.py",
                "--repo-root",
                root.as_posix(),
                "--queue",
                queue.relative_to(root).as_posix(),
                "--repeat",
                "2",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["planned_measurements"][0]["repeat"], 2)
        self.assertEqual(report_payload["surface"], "rtlmeter_nvdla_hot_ss_measurement_plan")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
