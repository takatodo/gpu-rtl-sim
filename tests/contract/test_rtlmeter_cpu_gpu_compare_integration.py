import json
import os
import subprocess
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
        self.assertIn("--compileArgs=--use-gpu", report["commands"]["gpu"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_fails_closed_when_prerequisites_are_missing(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import OPT_IN_ENV, run_rtlmeter_cpu_gpu_compare_integration

        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=Path(temp_dir),
                environ={OPT_IN_ENV: "1", "PATH": ""},
            )

        self.assertEqual(report["status"], "cannot_execute")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["ran_commands"])
        self.assertGreater(len(report["missing_prerequisites"]), 0)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_preflight_requires_named_executable_wrapper(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import _preflight

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "third_party/rtlmeter/venv/bin").mkdir(parents=True)
            (root / "third_party/rtlmeter/rtlmeter").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "third_party/rtlmeter/venv/bin/python3").write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator_dir = root / "bin"
            real_verilator_dir.mkdir()
            real_verilator = real_verilator_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")

            missing = _preflight(
                repo_root=root,
                sidecar_wrapper=wrapper.as_posix(),
                path_env=real_verilator_dir.as_posix(),
            )

        self.assertIn("RTLMETER_SIDECAR_VERILATOR_WRAPPER executable bit", missing)

    def test_execution_env_prepends_rtlmeter_root_for_repo_root_launch(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "third_party/rtlmeter/venv/bin").mkdir(parents=True)
            (root / "third_party/rtlmeter/rtlmeter").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "third_party/rtlmeter/venv/bin/python3").write_text("#!/bin/sh\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_verilator = bin_dir / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="stop after CPU")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: wrapper.as_posix(),
                    "PATH": bin_dir.as_posix(),
                    "PYTHONPATH": "existing",
                },
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "cpu_execution_failed")
        pythonpath = calls[0][1]["env"]["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(pythonpath[:2], [(root / "third_party/rtlmeter").as_posix(), "existing"])

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
