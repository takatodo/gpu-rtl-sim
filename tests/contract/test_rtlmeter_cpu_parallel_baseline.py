import json
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class FakeProcess:
    def __init__(self, command, *, cwd, env, text, stdout, stderr):
        self.command = command
        self.returncode = 0
        self._polled = False

    def poll(self):
        if self._polled:
            return self.returncode
        self._polled = True
        return self.returncode

    def communicate(self):
        return ("", "")


class RtlmeterCpuParallelBaselineTest(HybridCliTestCase):
    def test_plan_is_non_executing_and_has_isolated_roots(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_parallel_baseline import build_cpu_parallel_baseline_report

        report = build_cpu_parallel_baseline_report(
            cases=["VeeR-EL2:default:cmark", "VeeR-EL2:default:cmark_iccm"],
            execute=False,
        )

        self.assertEqual(report["surface"], "rtlmeter_cpu_parallel_baseline")
        self.assertEqual(report["status"], "opt_in_required")
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["speedup_claimed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        serial_roots = [
            entry["command"][entry["command"].index("--executeRoot") + 1]
            for entry in report["commands"]
            if entry["mode"] == "serial"
        ]
        parallel_roots = [
            entry["command"][entry["command"].index("--executeRoot") + 1]
            for entry in report["commands"]
            if entry["mode"] == "parallel"
        ]
        self.assertEqual(len(set(serial_roots + parallel_roots)), 4)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_plan_supports_duplicate_case_instances_with_isolated_roots(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_parallel_baseline import build_cpu_parallel_baseline_report

        report = build_cpu_parallel_baseline_report(
            cases=["VeeR-EL2:default:hello", "VeeR-EL2:default:hello"],
            execute=False,
        )

        self.assertTrue(report["duplicate_cases_supported"])
        self.assertEqual(
            [item["case_instance"] for item in report["case_instances"]],
            ["veer_el2_default_hello_1", "veer_el2_default_hello_2"],
        )
        serial_roots = [
            entry["command"][entry["command"].index("--executeRoot") + 1]
            for entry in report["commands"]
            if entry["mode"] == "serial"
        ]
        serial_work_roots = [
            entry["command"][entry["command"].index("--workRoot") + 1]
            for entry in report["commands"]
            if entry["mode"] == "serial"
        ]
        parallel_roots = [
            entry["command"][entry["command"].index("--executeRoot") + 1]
            for entry in report["commands"]
            if entry["mode"] == "parallel"
        ]
        parallel_work_roots = [
            entry["command"][entry["command"].index("--workRoot") + 1]
            for entry in report["commands"]
            if entry["mode"] == "parallel"
        ]
        self.assertEqual(len(set(serial_roots + parallel_roots)), 4)
        self.assertEqual(len(set(serial_work_roots + parallel_work_roots)), 4)
        self.assertIn("veer_el2_default_hello_1", serial_roots[0])
        self.assertIn("veer_el2_default_hello_2", serial_roots[1])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_compares_serial_and_parallel_observables(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_parallel_baseline import build_cpu_parallel_baseline_report, execute_dir

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = ["VeeR-EL2:default:cmark", "VeeR-EL2:default:cmark_iccm"]

            def write_outputs(execute_root: str, case: str) -> None:
                directory = root / execute_dir(execute_root, case)
                (directory / "_execute").mkdir(parents=True, exist_ok=True)
                cycles = "111" if case.endswith(":cmark") else "222"
                stdout = "  0.01 | TEST_PASSED\n"
                (directory / "_execute/stdout.log").write_text(stdout, encoding="utf-8")
                (directory / "_rtlmeter_cycles.txt").write_text(cycles, encoding="utf-8")

            def fake_runner(command, **kwargs):
                case = command[command.index("--cases") + 1]
                execute_root = command[command.index("--executeRoot") + 1]
                write_outputs(execute_root, case)
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            class WritingFakeProcess(FakeProcess):
                def __init__(self, command, **kwargs):
                    super().__init__(command, **kwargs)
                    case = command[command.index("--cases") + 1]
                    execute_root = command[command.index("--executeRoot") + 1]
                    write_outputs(execute_root, case)

            report = build_cpu_parallel_baseline_report(
                cases=cases,
                compile_root="artifacts/compile",
                artifact_root="artifacts/probe",
                max_workers=2,
                timeout_minutes=1,
                execute=True,
                repo_root=root,
                environ={},
                runner=fake_runner,
                popen_factory=WritingFakeProcess,
            )

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["summary"]["all_runs_passed"])
        self.assertTrue(report["summary"]["all_observables_match"])
        self.assertEqual(report["summary"]["case_count"], 2)
        self.assertGreater(report["summary"]["completed_cases_per_second_parallel"], 0)
        self.assertTrue(all(item["serial_parallel_observables_match"] for item in report["comparison"]))
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_compares_duplicate_case_instances_independently(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_parallel_baseline import build_cpu_parallel_baseline_report, execute_dir

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cases = ["VeeR-EL2:default:hello", "VeeR-EL2:default:hello"]

            def write_outputs(execute_root: str, case: str) -> None:
                directory = root / execute_dir(execute_root, case)
                (directory / "_execute").mkdir(parents=True, exist_ok=True)
                (directory / "_execute/stdout.log").write_text("TEST_PASSED\n", encoding="utf-8")
                (directory / "_rtlmeter_cycles.txt").write_text("2229\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                case = command[command.index("--cases") + 1]
                execute_root = command[command.index("--executeRoot") + 1]
                write_outputs(execute_root, case)
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            class WritingFakeProcess(FakeProcess):
                def __init__(self, command, **kwargs):
                    super().__init__(command, **kwargs)
                    case = command[command.index("--cases") + 1]
                    execute_root = command[command.index("--executeRoot") + 1]
                    write_outputs(execute_root, case)

            report = build_cpu_parallel_baseline_report(
                cases=cases,
                compile_root="artifacts/compile",
                artifact_root="artifacts/hello_parallel_probe",
                max_workers=2,
                timeout_minutes=1,
                execute=True,
                repo_root=root,
                environ={},
                runner=fake_runner,
                popen_factory=WritingFakeProcess,
            )

        self.assertEqual(report["status"], "passed")
        self.assertEqual(
            [item["case_instance"] for item in report["comparison"]],
            ["veer_el2_default_hello_1", "veer_el2_default_hello_2"],
        )
        self.assertTrue(all(item["serial_parallel_observables_match"] for item in report["comparison"]))
        self.assertEqual(len({item["execute_root"] for item in report["serial_results"]}), 2)
        self.assertEqual(len({item["work_root"] for item in report["serial_results"]}), 2)
        self.assertEqual(len({item["execute_root"] for item in report["parallel_results"]}), 2)
        self.assertEqual(len({item["work_root"] for item in report["parallel_results"]}), 2)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_sanitizes_absolute_compile_root_in_results(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_parallel_baseline import build_cpu_parallel_baseline_report, execute_dir

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            compile_root = root / "artifacts/compile"

            def write_outputs(execute_root: str, case: str) -> None:
                directory = root / execute_dir(execute_root, case)
                (directory / "_execute").mkdir(parents=True, exist_ok=True)
                (directory / "_execute/stdout.log").write_text("TEST_PASSED\n", encoding="utf-8")
                (directory / "_rtlmeter_cycles.txt").write_text("2229\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                case = command[command.index("--cases") + 1]
                execute_root = command[command.index("--executeRoot") + 1]
                write_outputs(execute_root, case)
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            class WritingFakeProcess(FakeProcess):
                def __init__(self, command, **kwargs):
                    super().__init__(command, **kwargs)
                    case = command[command.index("--cases") + 1]
                    execute_root = command[command.index("--executeRoot") + 1]
                    write_outputs(execute_root, case)

            report = build_cpu_parallel_baseline_report(
                cases=["VeeR-EL2:default:hello", "VeeR-EL2:default:hello"],
                compile_root=str(compile_root),
                artifact_root="artifacts/hello_parallel_probe",
                max_workers=2,
                timeout_minutes=1,
                execute=True,
                repo_root=root,
                environ={},
                runner=fake_runner,
                popen_factory=WritingFakeProcess,
            )

        self.assertEqual(report["status"], "passed")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_dry_run_outputs_json(self) -> None:
        result = self.run_python_tool(
            "src/tools/rtlmeter_cpu_parallel_baseline.py",
            "--cases",
            "VeeR-EL2:default:cmark",
            "VeeR-EL2:default:cmark_iccm",
            check=True,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "opt_in_required")
        self.assertEqual(report["cases"], ["VeeR-EL2:default:cmark", "VeeR-EL2:default:cmark_iccm"])
        self.assert_no_local_absolute_paths(result.stdout)
