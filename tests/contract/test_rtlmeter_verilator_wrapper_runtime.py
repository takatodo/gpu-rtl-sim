import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVerilatorWrapperRuntimeTest(HybridCliTestCase):
    def _touch_executable(self, path: Path) -> None:
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)

    def test_no_gpu_intent_delegates_to_real_verilator_without_reselecting_wrapper(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wrapper = root / "wrapper" / "verilator"
            real = root / "real" / "verilator"
            wrapper.parent.mkdir()
            real.parent.mkdir()
            self._touch_executable(wrapper)
            self._touch_executable(real)
            calls = []

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 7)

            code = run_rtlmeter_verilator_wrapper(
                ["--cc", "--top-module", "top", "-f", "filelist"],
                executable=wrapper,
                environ={"PATH": f"{wrapper.parent}{os.pathsep}{real.parent}"},
                runner=fake_runner,
            )

        self.assertEqual(code, 7)
        self.assertEqual(calls[0][0], [str(real), "--cc", "--top-module", "top", "-f", "filelist"])
        self.assertNotEqual(calls[0][0][0], str(wrapper))

    def test_missing_real_verilator_fails_without_cpu_as_gpu_fallback(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = Path(temp_dir) / "verilator"
            self._touch_executable(wrapper)
            stderr = io.StringIO()
            code = run_rtlmeter_verilator_wrapper(
                ["--cc", "--top-module", "top", "-f", "filelist"],
                executable=wrapper,
                environ={"PATH": str(wrapper.parent)},
                stderr=stderr,
            )
            report = json.loads(stderr.getvalue())

        self.assertEqual(code, 127)
        self.assertEqual(report["status"], "real_verilator_missing")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["delegated_to_real_verilator"])

    def test_use_gpu_fails_closed_until_schedule_is_explicit(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            ["--cc", "--top-module", "top", "-f", "filelist", "--use-gpu"],
            environ={"PATH": ""},
            runner=lambda *args, **kwargs: self.fail("GPU intent must not delegate to real Verilator"),
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "use_gpu_requires_explicit_sidecar_schedule")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["sidecar_execution_invoked"])

    def test_expanded_sidecar_schedule_reaches_runtime_boundary_but_does_not_execute_yet(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import run_rtlmeter_verilator_wrapper

        stderr = io.StringIO()
        code = run_rtlmeter_verilator_wrapper(
            [
                "--cc",
                "--top-module",
                "top",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ],
            environ={"PATH": ""},
            runner=lambda *args, **kwargs: self.fail("sidecar execution is not implemented in this wrapper"),
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "sidecar_schedule_captured_execution_not_implemented")
        self.assertEqual(report["inspection_status"], "ready_for_rtlmeter_sidecar_planning")
        self.assertFalse(report["cpu_as_gpu_fallback"])
        handoff = report["handoff_metadata"]
        self.assertEqual(handoff["surface"], "rtlmeter_sidecar_handoff")
        self.assertEqual(handoff["status"], "rtlmeter_sidecar_handoff_blocked_missing_context")
        self.assertEqual(handoff["schedule"]["shape"], "64x1")
        self.assertIn("template_or_target_registry_entry", handoff["missing_sidecar_context"])
        self.assertIn("host_probe_metadata", handoff["missing_sidecar_context"])
        self.assertFalse(handoff["sidecar_execution_invoked"])
        self.assertFalse(handoff["cpu_as_gpu_fallback"])

    def test_rtlmeter_sidecar_handoff_preserves_parser_inputs_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_sidecar_handoff import build_rtlmeter_sidecar_handoff

        handoff = build_rtlmeter_sidecar_handoff(
            [
                "--cc",
                "--main",
                "--top-module",
                "top",
                "+incdir+verilogIncludeFiles",
                "+define+__RTLMETER_MAIN_CLOCK=top.clk",
                "-f",
                "filelist",
                "--sim-accel",
                "sidecar-gpu",
                "--sim-accel-states",
                "64",
                "--sim-accel-steps",
                "1",
            ]
        )

        self.assertEqual(handoff["schedule"]["state_count"], 64)
        self.assertEqual(handoff["schedule"]["step_count"], 1)
        self.assertEqual(handoff["parser_payload"]["top_module"], "top")
        self.assertIn("filelist", handoff["parser_payload"]["filelists"])
        self.assertIn("+incdir+verilogIncludeFiles", handoff["parser_payload"]["include_dirs"])
        self.assertFalse(handoff["execution_authority"])
        self.assertFalse(handoff["sidecar_launcher_invoked"])
        self.assertFalse(handoff["coverage_output_compare_reached"])

    def test_materialized_wrapper_is_named_verilator_and_executable(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = write_rtlmeter_verilator_wrapper(Path(temp_dir) / "verilator", python_executable="python3")

            self.assertEqual(wrapper.name, "verilator")
            self.assertTrue(os.access(wrapper, os.X_OK))
            self.assertIn("rtlmeter_verilator_wrapper_runtime.py", wrapper.read_text(encoding="utf-8"))
