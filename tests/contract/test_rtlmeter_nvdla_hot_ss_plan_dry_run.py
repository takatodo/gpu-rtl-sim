import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_nvdla_hot_ss_plan_dry_run import run_dry_run_plan  # noqa: E402


class RtlmeterNvdlaHotSsPlanDryRunTest(HybridCliTestCase):
    def _write_plan(self, root: Path) -> Path:
        path = root / "reports" / "plan.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "target": "NVDLA.nvdla_cmac_a2cacc",
                    "planned_measurements": [
                        {
                            "order": 1,
                            "id": "confirm_best",
                            "shape": "1024x64",
                            "commands": {
                                "dry_run": [
                                    "PYTHONDONTWRITEBYTECODE=1",
                                    "python3",
                                    "src/tools/run_hybrid_template.py",
                                    "config/slice_launch_templates/nvdla_cmac_a2cacc.json",
                                    "--shape",
                                    "1024x64",
                                    "--dry-run",
                                ]
                            },
                        },
                        {
                            "order": 2,
                            "id": "neighbor",
                            "shape": "512x64",
                            "commands": {
                                "dry_run": [
                                    "PYTHONDONTWRITEBYTECODE=1",
                                    "python3",
                                    "src/tools/run_hybrid_template.py",
                                    "config/slice_launch_templates/nvdla_cmac_a2cacc.json",
                                    "--shape",
                                    "512x64",
                                    "--dry-run",
                                ]
                            },
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_dry_run_report_uses_runner_and_keeps_relative_plan_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = self._write_plan(root)

            def runner(argv, env_update, repo_root):
                self.assertEqual(repo_root, root)
                self.assertEqual(env_update["PYTHONDONTWRITEBYTECODE"], "1")
                self.assertEqual(argv[0], "python3")
                return subprocess.CompletedProcess(argv, 0, stdout="dry ok\n", stderr="")

            report = run_dry_run_plan(root, plan_path=plan.relative_to(root), runner=runner)

        self.assertEqual(report["surface"], "rtlmeter_nvdla_hot_ss_plan_dry_run")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["source_plan"], "reports/plan.json")
        self.assertEqual(report["dry_run_count"], 2)
        self.assertEqual(report["passed_count"], 2)
        self.assertTrue(report["all_dry_runs_passed"])
        self.assertEqual(report["results"][0]["argv"][0], "python3")
        self.assertIn("dry_run_preflight_only", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_dry_run_failure_is_reported_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = self._write_plan(root)

            def runner(argv, env_update, repo_root):
                return subprocess.CompletedProcess(argv, 2, stdout="", stderr="bad template\n")

            report = run_dry_run_plan(root, plan_path=plan.relative_to(root), runner=runner)

        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["passed_count"], 0)
        self.assertFalse(report["all_dry_runs_passed"])
        self.assertIn("bad template", report["results"][0]["stderr_tail"])


if __name__ == "__main__":
    unittest.main()
