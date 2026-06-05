import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterStdoutCyclesSidecarRunnerCliTest(HybridCliTestCase):
    def test_cli_executes_inner_command_with_rtlmeter_phase(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner_cli import run_rtlmeter_stdout_cycles_sidecar_runner
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            command = plan["gpu_candidate"]["command"]
            observable_dir = plan["gpu_candidate"]["observable_execute_dir"]
            calls = []

            def fake_runner(command_argv, **kwargs):
                calls.append((command_argv, kwargs))
                out = root / observable_dir
                (out / "_execute").mkdir(parents=True)
                (out / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (out / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")
                return subprocess.CompletedProcess(command_argv, 0, stdout="", stderr="")

            report = run_rtlmeter_stdout_cycles_sidecar_runner(
                observable_execute_dir=observable_dir,
                command_argv=["--", *command],
                repo_root=root,
                environ={},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_observables_ready")
        self.assertEqual(calls[0][0], command)
        self.assertEqual(calls[0][1]["env"][PHASE_ENV], PHASE_RTL_METER_RUN)
        self.assertTrue(report["runner_source_cli_implemented"])
        self.assertTrue(report["execution_performed"])
        self.assertTrue(report["execution_authority"])
        self.assertTrue(report["sidecar_execution_invoked"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_cli_removes_stale_observables_before_inner_command(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner_cli import run_rtlmeter_stdout_cycles_sidecar_runner

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            command = plan["gpu_candidate"]["command"]
            observable_dir = plan["gpu_candidate"]["observable_execute_dir"]
            out = root / observable_dir
            (out / "_execute").mkdir(parents=True)
            (out / "_execute/stdout.log").write_text("stale\n", encoding="utf-8")
            (out / "_rtlmeter_cycles.txt").write_text("1\n", encoding="utf-8")

            def fake_runner(command_argv, **kwargs):
                self.assertFalse((out / "_execute/stdout.log").exists())
                self.assertFalse((out / "_rtlmeter_cycles.txt").exists())
                return subprocess.CompletedProcess(command_argv, 0, stdout="", stderr="")

            report = run_rtlmeter_stdout_cycles_sidecar_runner(
                observable_execute_dir=observable_dir,
                command_argv=["--", *command],
                repo_root=root,
                environ={},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing")
        self.assertFalse(report["observables_ready"])
        self.assertFalse(report["execution_performed"])
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_cli_blocks_reentry_without_mutating_stale_observables(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner_cli import (
            STATUS_BLOCKED_WRAPPER_PHASE,
            run_rtlmeter_stdout_cycles_sidecar_runner,
        )
        from rtlmeter_verilator_wrapper_phase import PHASE_ENV, PHASE_RTL_METER_RUN

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            command = plan["gpu_candidate"]["command"]
            observable_dir = plan["gpu_candidate"]["observable_execute_dir"]
            out = root / observable_dir
            (out / "_execute").mkdir(parents=True)
            (out / "_execute/stdout.log").write_text("stale\n", encoding="utf-8")
            (out / "_rtlmeter_cycles.txt").write_text("1\n", encoding="utf-8")

            report = run_rtlmeter_stdout_cycles_sidecar_runner(
                observable_execute_dir=observable_dir,
                command_argv=["--", *command],
                repo_root=root,
                environ={PHASE_ENV: PHASE_RTL_METER_RUN},
                runner=lambda *_args, **_kwargs: self.fail("runner must not be called"),
            )

            self.assertTrue((out / "_execute/stdout.log").exists())
            self.assertTrue((out / "_rtlmeter_cycles.txt").exists())

        self.assertEqual(report["status"], STATUS_BLOCKED_WRAPPER_PHASE)
        self.assertFalse(report["execution_performed"])
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["sidecar_execution_invoked"])
