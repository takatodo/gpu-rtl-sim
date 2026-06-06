import json
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterCpuGpuCompareStaleRegressionTest(HybridCliTestCase):
    def test_stale_gpu_observables_matching_cpu_do_not_pass_without_runner_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_cpu_gpu_compare_integration import (
            OPT_IN_ENV,
            WRAPPER_ENV,
            run_rtlmeter_cpu_gpu_compare_integration,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rtlmeter_root = root / "third_party/rtlmeter"
            (rtlmeter_root / "src").mkdir(parents=True)
            (rtlmeter_root / "designs/Example").mkdir(parents=True)
            (rtlmeter_root / "designs/Example/descriptor.yaml").write_text(
                "\n".join(
                    [
                        "compile:",
                        "  topModule: top",
                        "  mainClock: clk",
                        "  verilogSourceFiles:",
                        "    - src/top.v",
                        "configurations:",
                        "  kind:",
                        "    compile: {}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
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
            base = root / "artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare"
            cpu_execute = base / "cpu/Example/kind/execute-0/hello"
            gpu_execute = base / "gpu/Example/kind/execute-0/hello"
            calls = []

            def write_observables(path: Path) -> None:
                (path / "_execute").mkdir(parents=True, exist_ok=True)
                (path / "_execute/stdout.log").write_text("    0.01 | Hello World!\n", encoding="utf-8")
                (path / "_rtlmeter_cycles.txt").write_text("1000000\n", encoding="utf-8")

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if len(calls) == 1:
                    write_observables(cpu_execute)
                    write_observables(gpu_execute)
                else:
                    from rtlmeter_stdout_cycles_sidecar_runner_cli import run_rtlmeter_stdout_cycles_sidecar_runner

                    observable_index = command.index("--observable-execute-dir")
                    separator_index = command.index("--")
                    run_rtlmeter_stdout_cycles_sidecar_runner(
                        observable_execute_dir=command[observable_index + 1],
                        command_argv=command[separator_index:],
                        repo_root=root,
                        environ=kwargs["env"],
                        runner=lambda inner_command, **inner_kwargs: subprocess.CompletedProcess(
                            inner_command, 0, stdout="", stderr=""
                        ),
                    )
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            import rtlmeter_sidecar_contract_mapping
            import rtlmeter_verilator_command_capture

            original_capture = rtlmeter_sidecar_contract_mapping.capture_rtlmeter_verilator_command
            original_repo_root = rtlmeter_verilator_command_capture._repo_root
            try:
                rtlmeter_verilator_command_capture._repo_root = lambda: root
                rtlmeter_sidecar_contract_mapping.capture_rtlmeter_verilator_command = (
                    lambda case, extra_args=(): rtlmeter_verilator_command_capture.capture_rtlmeter_verilator_command(
                        case,
                        rtlmeter_root=rtlmeter_root,
                        extra_args=extra_args,
                    )
                )
                report = run_rtlmeter_cpu_gpu_compare_integration(
                    repo_root=root,
                    environ={OPT_IN_ENV: "1", WRAPPER_ENV: wrapper.as_posix(), "PATH": bin_dir.as_posix()},
                    runner=fake_runner,
                )
            finally:
                rtlmeter_sidecar_contract_mapping.capture_rtlmeter_verilator_command = original_capture
                rtlmeter_verilator_command_capture._repo_root = original_repo_root

        self.assertEqual(report["status"], "gpu_observables_not_ready")
        self.assertEqual(report["missing_runner_report"], "rtlmeter_stdout_cycles_sidecar_runner_json_stdout")
        self.assertIsNone(report["comparison"])
        self.assertTrue(report["stdout_cycles_sidecar_runner"]["execution_performed"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["execution_authority"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["sidecar_execution_invoked"])
        self.assertFalse(report["stdout_cycles_sidecar_runner"]["gpu_execution_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))
