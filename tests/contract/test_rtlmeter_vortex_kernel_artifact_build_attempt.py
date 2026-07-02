import json
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVortexKernelArtifactBuildAttemptTest(HybridCliTestCase):
    def test_classifies_landingpad_personality_failure(self) -> None:
        self.add_tools_to_path()
        import rtlmeter_vortex_kernel_artifact_build_attempt as attempt

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj_dir = root / "obj_dir"
            obj_dir.mkdir()

            fake = subprocess.CompletedProcess(
                args=[],
                returncode=-6,
                stdout="LandingPadInst needs to be in a function with a personality.\n",
                stderr="LLVM ERROR: Broken module found, compilation aborted!\n",
            )
            with mock.patch.object(attempt.subprocess, "run", return_value=fake):
                report = attempt.run_attempt(root, obj_dir=obj_dir)

        self.assertEqual(report["status"], "failed_broken_module_landingpad_personality")
        self.assertTrue(report["landingpad_personality_error_observed"])
        self.assertTrue(report["broken_module_observed"])
        self.assertFalse(report["kernel_artifact_ready"])
        self.assertEqual(
            report["next_required_boundary"],
            "fix_vortex_lowered_ir_landingpad_personality_before_kernel_artifact",
        )
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["timing_measured"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_reports_pass_when_ptx_exists_after_success(self) -> None:
        self.add_tools_to_path()
        import rtlmeter_vortex_kernel_artifact_build_attempt as attempt

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            obj_dir = root / "obj_dir"
            obj_dir.mkdir()
            (obj_dir / "vl_batch_gpu.ptx").write_text("// ptx\n", encoding="utf-8")
            fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with mock.patch.object(attempt.subprocess, "run", return_value=fake):
                report = attempt.run_attempt(root, obj_dir=obj_dir)

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["ptx_exists"])
        self.assertTrue(report["kernel_artifact_ready"])
        self.assertEqual(
            report["next_required_boundary"],
            "wire_real_vortex_kernel_artifact_into_materialized_runtime_callback",
        )

    def test_cli_writes_report_and_returns_nonzero_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out = root / "reports" / "attempt.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_kernel_artifact_build_attempt.py",
                "--repo-root",
                root.as_posix(),
                "--obj-dir",
                "missing_obj_dir",
                "--timeout-seconds",
                "1",
                "--write-report",
                "--report-out",
                out.as_posix(),
                check=False,
            )
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload, report_payload)
        self.assertEqual(payload["surface"], "rtlmeter_vortex_kernel_artifact_build_attempt")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
