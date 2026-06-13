import json
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase
from tests.contract.test_rtlmeter_cpu_gpu_compare_integration import _write_minimal_rtlmeter_tree


class RtlmeterCpuGpuCompareDiagnosticsTest(HybridCliTestCase):
    def test_preflight_sanitizes_system_absolute_real_verilator(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            REAL_VERILATOR_ENV,
            REAL_VERILATOR_PREFLIGHT_SELECTED,
            build_real_verilator_preflight,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            _write_minimal_rtlmeter_tree(root)
            real_root = Path(temp_dir) / "usr/bin"
            real_root.mkdir(parents=True)
            real_verilator = real_root / "verilator"
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)

            report = build_real_verilator_preflight(
                repo_root=root,
                sidecar_wrapper=wrapper.as_posix(),
                environ={REAL_VERILATOR_ENV: real_verilator.as_posix(), "PATH": ""},
            )

        self.assertEqual(report["status"], REAL_VERILATOR_PREFLIGHT_SELECTED)
        self.assertEqual(report["selected_real_verilator"], "<local-absolute-path>")
        self.assertEqual(report["wrapper_path"], "wrapper/verilator")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_missing_gpu_runner_python_reports_fail_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            BLOCKER_GPU_RUNNER_EXECUTION_FAILED,
            OPT_IN_ENV,
            REAL_VERILATOR_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
            rtlmeter = root / "third_party/rtlmeter/rtlmeter"
            rtlmeter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            rtlmeter.chmod(0o755)
            real_verilator = root / "real" / "verilator"
            real_verilator.parent.mkdir()
            real_verilator.write_text("#!/bin/sh\n", encoding="utf-8")
            real_verilator.chmod(0o755)
            wrapper = root / "wrapper" / "verilator"
            wrapper.parent.mkdir()
            wrapper.write_text("#!/bin/sh\n", encoding="utf-8")
            wrapper.chmod(0o755)

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={
                    OPT_IN_ENV: "1",
                    WRAPPER_ENV: wrapper.as_posix(),
                    REAL_VERILATOR_ENV: real_verilator.as_posix(),
                    "PATH": "",
                },
            )

        self.assertEqual(report["status"], "gpu_execution_failed")
        self.assertEqual(report["gpu_failure_blocker"], BLOCKER_GPU_RUNNER_EXECUTION_FAILED)
        self.assertEqual(report["command_results"]["gpu"]["returncode"], 127)
        self.assertIn("python3", report["command_results"]["gpu"]["stderr"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_gpu_failure_classifies_nested_runner_outputs_missing_report(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            BLOCKER_RTL_METER_VSIM_OBSERVABLES_MISSING,
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_minimal_rtlmeter_tree(root)
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
            runner_report = {
                "status": "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing",
                "missing_observables": ["gpu:_rtlmeter_cycles.txt"],
            }

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 1:
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                return subprocess.CompletedProcess(command, 1, stdout=json.dumps(runner_report), stderr="")

            report = run_rtlmeter_cpu_gpu_compare_integration(
                repo_root=root,
                environ={OPT_IN_ENV: "1", WRAPPER_ENV: wrapper.as_posix(), "PATH": bin_dir.as_posix()},
                runner=fake_runner,
            )

        self.assertEqual(report["status"], "gpu_execution_failed")
        self.assertEqual(report["gpu_failure_blocker"], BLOCKER_RTL_METER_VSIM_OBSERVABLES_MISSING)
        self.assertEqual(
            report["stdout_cycles_sidecar_runner"]["status"],
            "rtlmeter_stdout_cycles_sidecar_runner_outputs_missing",
        )
        self.assertEqual(
            report["stdout_cycles_sidecar_runner"]["runner_stdout_report"]["missing_observables"],
            ["gpu:_rtlmeter_cycles.txt"],
        )
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["reviewed_proxy_metadata_observed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_classifies_narrow_runner_fail_closed_statuses(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_diagnostics import (
            BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_ENV_MISSING,
            BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_TARGET_UNUSABLE,
            BLOCKER_RTL_METER_WRAPPER_PHASE_GUARD,
            classify_gpu_failure_blocker,
        )

        cases = (
            (
                "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_target_unusable",
                BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_TARGET_UNUSABLE,
            ),
            (
                "rtlmeter_stdout_cycles_sidecar_runner_blocked_wrapper_phase_guard",
                BLOCKER_RTL_METER_WRAPPER_PHASE_GUARD,
            ),
            (
                "rtlmeter_stdout_cycles_sidecar_runner_vsim_sidecar_proxy_env_missing",
                BLOCKER_RTL_METER_VSIM_SIDECAR_PROXY_ENV_MISSING,
            ),
        )
        for status, blocker in cases:
            self.assertEqual(
                classify_gpu_failure_blocker(diagnostic_log=None, runner_observation={"status": status}),
                blocker,
            )
            self.assertEqual(
                classify_gpu_failure_blocker(
                    diagnostic_log=None,
                    runner_observation={"status": "rtlmeter_stdout_cycles_sidecar_runner_execution_failed", "runner_stdout_report": {"status": status}},
                ),
                blocker,
            )
