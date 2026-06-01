import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterCpuGpuCompareIntegrationTest(HybridCliTestCase):
    def test_default_run_is_non_executing_and_report_safe(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import run_rtlmeter_cpu_gpu_compare_integration

        report = run_rtlmeter_cpu_gpu_compare_integration(environ={})

        self.assertEqual(report["surface"], "rtlmeter_cpu_gpu_compare_integration")
        self.assertEqual(report["status"], "opt_in_required")
        self.assertEqual(report["seed"], "Example:kind:hello")
        self.assertFalse(report["canonical_project_state_changed"])
        self.assertFalse(report["generated_report_is_source_of_truth"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["ran_commands"])
        self.assertEqual(report["commands"]["cpu"][0], "third_party/rtlmeter/rtlmeter")
        self.assertIn("--compileArgs", report["commands"]["gpu"])
        self.assertIn("--use-gpu", report["commands"]["gpu"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_fails_closed_when_prerequisites_are_missing(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import OPT_IN_ENV, run_rtlmeter_cpu_gpu_compare_integration

        report = run_rtlmeter_cpu_gpu_compare_integration(environ={OPT_IN_ENV: "1"})

        self.assertEqual(report["status"], "cannot_execute")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["ran_commands"])
        self.assertGreater(len(report["missing_prerequisites"]), 0)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_compare_observables_uses_normalized_stdout_and_cycles(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import compare_rtlmeter_observables

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu = root / "cpu"
            gpu = root / "gpu"
            for path in (cpu / "_execute", gpu / "_execute"):
                path.mkdir(parents=True)
            (cpu / "_execute" / "stdout.log").write_text("    0.01 | hello\n", encoding="utf-8")
            (gpu / "_execute" / "stdout.log").write_text("    9.99 | hello\n", encoding="utf-8")
            (cpu / "_rtlmeter_cycles.txt").write_text("12\n", encoding="utf-8")
            (gpu / "_rtlmeter_cycles.txt").write_text("12\n", encoding="utf-8")

            comparison = compare_rtlmeter_observables(cpu, gpu)

        self.assertEqual(comparison["status"], "passed")
        self.assertTrue(comparison["normalized_stdout_match"])
        self.assertTrue(comparison["cycle_count_match"])
        self.assertEqual(comparison["cpu_cycles"], 12)
        self.assertEqual(comparison["gpu_cycles"], 12)

    def test_write_report_keeps_report_generated_and_relative(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import run_rtlmeter_cpu_gpu_compare_integration

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            report = run_rtlmeter_cpu_gpu_compare_integration(
                write_report=True,
                report_path="reports/sample.json",
                repo_root=repo_root,
                environ={},
            )
            written = json.loads((repo_root / "reports/sample.json").read_text(encoding="utf-8"))

        self.assertEqual(report["report_path"], "reports/sample.json")
        self.assertEqual(written["status"], "opt_in_required")
        self.assertFalse(written["generated_report_is_source_of_truth"])
        self.assert_no_local_absolute_paths(json.dumps(written, sort_keys=True))

    def test_cli_emits_non_executing_json_by_default(self) -> None:
        result = self.run_python_tool("src/tools/rtlmeter_cpu_gpu_compare_integration.py")
        report = json.loads(result.stdout)

        self.assertEqual(report["status"], "opt_in_required")
        self.assertFalse(report["ran_commands"])
        self.assert_no_local_absolute_paths(result.stdout)
