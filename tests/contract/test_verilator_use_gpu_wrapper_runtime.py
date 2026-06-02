import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class VerilatorUseGpuWrapperRuntimeTest(HybridCliTestCase):
    def _touch_executable(self, path: Path) -> None:
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)

    def _supported_argv(self) -> list[str]:
        return [
            "--cc",
            "-f",
            "config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json",
            "--top-module",
            "pulp_ita_mha_gpu_cov_tb",
            "--use-gpu",
            "--sim-accel",
            "sidecar-gpu",
            "--sim-accel-states",
            "64",
            "--sim-accel-steps",
            "1",
        ]

    def _passing_compare_report(self) -> dict[str, object]:
        return {
            "selected_acceptance_policy": {
                "name": "coverage_output_equivalence",
                "passed": True,
            },
            "coverage_output_policy": {
                "mismatch_count": 0,
            },
        }

    def test_no_gpu_intent_delegates_to_real_verilator_without_reselecting_wrapper(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_wrapper_runtime import run_verilator_use_gpu_wrapper

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

            code = run_verilator_use_gpu_wrapper(
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
        from verilator_use_gpu_wrapper_runtime import run_verilator_use_gpu_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = Path(temp_dir) / "verilator"
            self._touch_executable(wrapper)
            stderr = io.StringIO()
            code = run_verilator_use_gpu_wrapper(
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

    def test_supported_use_gpu_invokes_first_path_authority(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_wrapper_runtime import run_verilator_use_gpu_wrapper

        stdout = io.StringIO()
        calls = []

        def fake_launcher(resolution, repo_root):
            calls.append((resolution, repo_root))
            return {"returncode": 0, "compare_report": self._passing_compare_report()}

        code = run_verilator_use_gpu_wrapper(
            self._supported_argv(),
            environ={"PATH": ""},
            runner=lambda *args, **kwargs: self.fail("GPU intent must not delegate to real Verilator"),
            launcher=fake_launcher,
            stdout=stdout,
        )
        report = json.loads(stdout.getvalue())

        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "verilator_use_gpu_first_path_executed")
        self.assertEqual(report["coverage_policy"], "coverage_output_equivalence")
        self.assertEqual(report["launcher_report"]["compare_report"]["coverage_output_policy"]["mismatch_count"], 0)
        self.assertEqual(len(calls), 1)
        self.assertTrue(report["sidecar_execution_invoked"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_unsupported_use_gpu_fails_closed_without_delegation(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_wrapper_runtime import run_verilator_use_gpu_wrapper

        argv = self._supported_argv()
        argv[argv.index("config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json")] = (
            "config/slice_launch_templates/pulp_ita_dotp.json"
        )
        stderr = io.StringIO()
        code = run_verilator_use_gpu_wrapper(
            argv,
            environ={"PATH": ""},
            runner=lambda *args, **kwargs: self.fail("unsupported GPU intent must not delegate"),
            launcher=lambda *args, **kwargs: self.fail("unsupported GPU intent must not launch sidecar"),
            stderr=stderr,
        )
        report = json.loads(stderr.getvalue())

        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "verilator_use_gpu_first_path_rejected")
        self.assertIn("reviewed_filelist_authority", report["missing_required_inputs"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["cpu_as_gpu_fallback"])

    def test_materializes_path_selected_wrapper_named_verilator(self) -> None:
        self.add_tools_to_path()
        from verilator_use_gpu_wrapper_runtime import WRAPPER_SELF_ENV, write_verilator_use_gpu_wrapper

        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = write_verilator_use_gpu_wrapper(Path(temp_dir) / "verilator", python_executable="python3")
            text = wrapper.read_text(encoding="utf-8")
            self.assertEqual(wrapper.name, "verilator")
            self.assertTrue(os.access(wrapper, os.X_OK))
            self.assertIn(WRAPPER_SELF_ENV, text)
            self.assertIn("verilator_use_gpu_wrapper_runtime.py", text)

    def test_documented_package_import_materializes_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wrapper = Path(temp_dir) / "verilator"
            command = (
                "from src.tools.verilator_use_gpu_wrapper_runtime import write_verilator_use_gpu_wrapper; "
                f"write_verilator_use_gpu_wrapper({str(wrapper)!r})"
            )
            self.run_command(["python3", "-c", command])

            self.assertEqual(wrapper.name, "verilator")
            self.assertTrue(os.access(wrapper, os.X_OK))
