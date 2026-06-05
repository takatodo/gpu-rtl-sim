import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterStdoutCyclesSidecarRunnerCliTest(HybridCliTestCase):
    def test_cli_executes_inner_command_with_rtlmeter_phase(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner_cli import (
            VSIM_SIDECAR_PROXY_ENV,
            run_rtlmeter_stdout_cycles_sidecar_runner,
        )
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
        self.assertEqual(report["vsim_sidecar_proxy_env"], VSIM_SIDECAR_PROXY_ENV)
        self.assertFalse(report["vsim_sidecar_proxy_env_present"])
        self.assertTrue(report["execution_performed"])
        self.assertTrue(report["execution_authority_requires_valid_proxy_marker"])
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["sidecar_proxy_marker_valid"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_cli_forwards_vsim_sidecar_proxy_env_to_inner_command(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner_cli import (
            VSIM_SIDECAR_PROXY_ENV,
            run_rtlmeter_stdout_cycles_sidecar_runner,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            command = plan["gpu_candidate"]["command"]
            observable_dir = plan["gpu_candidate"]["observable_execute_dir"]
            proxy_path = (root / "bin" / "rtlmeter-vsim-sidecar-proxy").as_posix()
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
                environ={VSIM_SIDECAR_PROXY_ENV: proxy_path},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_observables_ready")
        self.assertEqual(calls[0][1]["env"][VSIM_SIDECAR_PROXY_ENV], proxy_path)
        self.assertEqual(report["vsim_sidecar_proxy_env"], VSIM_SIDECAR_PROXY_ENV)
        self.assertTrue(report["vsim_sidecar_proxy_env_present"])
        self.assertTrue(report["wrapper_phase_guard"]["vsim_sidecar_proxy_env_present"])
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_cli_valid_marker_alone_does_not_grant_execution_authority(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import write_rtlmeter_sidecar_proxy_marker
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner_cli import run_rtlmeter_stdout_cycles_sidecar_runner

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            command = plan["gpu_candidate"]["command"]
            observable_dir = plan["gpu_candidate"]["observable_execute_dir"]

            def fake_runner(command_argv, **kwargs):
                out = root / observable_dir
                (out / "_execute").mkdir(parents=True)
                (out / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (out / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")
                write_rtlmeter_sidecar_proxy_marker(observable_execute_dir=observable_dir, repo_root=root)
                return subprocess.CompletedProcess(command_argv, 0, stdout="", stderr="")

            report = run_rtlmeter_stdout_cycles_sidecar_runner(
                observable_execute_dir=observable_dir,
                command_argv=["--", *command],
                repo_root=root,
                environ={},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_observables_ready")
        self.assertTrue(report["execution_performed"])
        self.assertTrue(report["sidecar_proxy_marker_valid"])
        self.assertFalse(report["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertTrue(report["execution_authority_requires_execute_proxy_install"])
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_cli_proxy_installed_marker_grants_execution_authority_without_gpu_claim(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_proxy_marker import write_rtlmeter_sidecar_proxy_marker
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan
        from rtlmeter_stdout_cycles_sidecar_runner_cli import run_rtlmeter_stdout_cycles_sidecar_runner

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            command = plan["gpu_candidate"]["command"]
            observable_dir = plan["gpu_candidate"]["observable_execute_dir"]

            def fake_runner(command_argv, **kwargs):
                out = root / observable_dir
                (out / "_execute").mkdir(parents=True)
                (out / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (out / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")
                write_rtlmeter_sidecar_proxy_marker(
                    observable_execute_dir=observable_dir,
                    repo_root=root,
                    proxy_readiness={
                        "proxy_installed_by_wrapper_branch": True,
                        "execution_authority": True,
                    },
                )
                return subprocess.CompletedProcess(command_argv, 0, stdout="", stderr="")

            report = run_rtlmeter_stdout_cycles_sidecar_runner(
                observable_execute_dir=observable_dir,
                command_argv=["--", *command],
                repo_root=root,
                environ={},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_observables_ready")
        self.assertTrue(report["execution_performed"])
        self.assertTrue(report["sidecar_proxy_marker_valid"])
        self.assertTrue(report["sidecar_execute_proxy_installed_by_wrapper_branch"])
        self.assertTrue(report["execution_authority"])
        self.assertTrue(report["sidecar_execution_invoked"])
        self.assertFalse(report["gpu_execution_claimed"])

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

    def test_cli_failed_child_does_not_surface_stale_observables(self) -> None:
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
            (out / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
            (out / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")

            report = run_rtlmeter_stdout_cycles_sidecar_runner(
                observable_execute_dir=observable_dir,
                command_argv=["--", *command],
                repo_root=root,
                environ={},
                runner=lambda command_argv, **kwargs: subprocess.CompletedProcess(
                    command_argv, 7, stdout="", stderr="failed"
                ),
            )

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_execution_failed")
        self.assertEqual(report["missing_observables"], ["stdout_log", "cycle_count_file"])
        self.assertFalse(report["observables_ready"])
        self.assertIsNone(report["normalized_stdout_sha256"])
        self.assertIsNone(report["cycle_count"])
        self.assertFalse(report["execution_performed"])
        self.assertFalse(report["execution_authority"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["gpu_execution_claimed"])

    def test_observation_requires_materialized_runner_command_for_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_stdout_cycles_execution_observation import (
            build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation,
        )
        from rtlmeter_stdout_cycles_plan import build_rtlmeter_stdout_cycles_execution_plan

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_rtlmeter_stdout_cycles_execution_plan()
            observable_dir = plan["gpu_candidate"]["observable_execute_dir"]
            out = root / observable_dir
            (out / "_execute").mkdir(parents=True)
            (out / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
            (out / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")

            report = build_rtlmeter_stdout_cycles_sidecar_runner_execution_observation(
                stdout_cycles_plan=plan,
                command_result={
                    "command": ["python3", "wrong_runner.py"],
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                },
                repo_root=root,
            )

        self.assertEqual(report["status"], "rtlmeter_stdout_cycles_sidecar_runner_observables_ready")
        self.assertTrue(report["observables_ready"])
        self.assertFalse(report["adapter_invoked"])
        self.assertFalse(report["sidecar_runner_invoked"])
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
