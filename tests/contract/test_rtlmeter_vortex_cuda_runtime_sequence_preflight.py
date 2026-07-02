import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import rtlmeter_vortex_cuda_runtime_sequence_preflight as preflight  # noqa: E402


class RtlmeterVortexCudaRuntimeSequencePreflightTest(HybridCliTestCase):
    def _write_materialization(self, root: Path) -> Path:
        buffers = []
        specs = [
            ("vortex_init_segment_table", 216),
            ("vortex_init_payload", 36864),
            ("vortex_post_segment_table", 24),
            ("vortex_post_expected_payload", 48),
            ("vortex_dcr_write_table", 72),
            ("vortex_stdout_ring_initial", 64),
            ("vortex_post_compare_result_initial", 24),
        ]
        for name, size in specs:
            artifact = root / "artifacts" / "buffers" / f"{name}.bin"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(bytes([0]) * size)
            buffers.append(
                {
                    "name": name,
                    "bytes": size,
                    "artifact": artifact.relative_to(root).as_posix(),
                }
            )
        report = root / "reports" / "materialization.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "device_buffers": buffers,
                    "totals": {
                        "host_to_device_bytes": 37224,
                        "device_to_host_initial_bytes": 88,
                    },
                }
            ),
            encoding="utf-8",
        )
        return report

    def test_generated_source_runs_lowered_tb_runtime_sequence_with_real_cuda_driver_api(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization = preflight._load_json(self._write_materialization(root))
            buffers = preflight._collect_buffers(materialization, repo_root=root)
            source = preflight._generated_source(repo_root=root, buffers=buffers)

        self.assertIn("#include <cuda.h>", source)
        self.assertIn('#include "src/hybrid/vortex_lowered_tb_runtime_sequence.h"', source)
        self.assertIn("cuMemcpyDtoH(dst, (CUdeviceptr)src, bytes)", source)
        self.assertIn("vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary)", source)
        self.assertIn("apply_dcr_probe", source)
        self.assertIn("launch_noop_probe", source)
        self.assertIn("sequence_summary.dcr_applied_count != 9", source)
        self.assertIn("sequence_summary.upload.h2d_bytes != 37224u", source)

    def test_preflight_report_classifies_passed_fake_subprocess_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization = self._write_materialization(root)

            def fake_run(argv, **kwargs):
                class Result:
                    returncode = 0
                    stdout = (
                        "result=0\n"
                        "runtime_sequence_called=1\n"
                        "runtime_sequence_passed=1\n"
                        "authority_report_ready=1\n"
                        "authority_passed=1\n"
                        "authority_source=memory_post_condition\n"
                        "allocated_count=7\n"
                        "h2d_bytes=37224\n"
                        "d2h_initial_bytes=88\n"
                        "dcr_applied_count=9\n"
                        "kernel_launch_invoked=1\n"
                        "observable_export_invoked=1\n"
                        "buffers_released=1\n"
                        "probe_dcr_calls=9\n"
                        "probe_kernel_calls=1\n"
                    )
                    stderr = ""

                return Result()

            with mock.patch.object(preflight.subprocess, "run", side_effect=fake_run):
                report = preflight.build_and_run_preflight(
                    root,
                    materialization_report=materialization,
                    artifact_dir=Path("artifacts/preflight"),
                )

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["real_cuda_driver_api_invoked"])
        self.assertTrue(report["real_cuda_runtime_sequence_preflight_passed"])
        self.assertTrue(report["runtime_sequence_called"])
        self.assertTrue(report["runtime_sequence_passed"])
        self.assertTrue(report["kernel_callback_invoked"])
        self.assertTrue(report["observable_export_invoked"])
        self.assertTrue(report["preflight_authority_passed"])
        self.assertEqual(report["preflight_authority_source"], "memory_post_condition")
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["timing_measured"])
        self.assertIn("noop_kernel_callback_not_vortex_kernel_execution", report["non_claims"])
        self.assertIn("preflight_authority_is_not_vortex_observable_authority", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_preflight_report_classifies_cuda_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization = self._write_materialization(root)
            calls = {"count": 0}

            def fake_run(argv, **kwargs):
                calls["count"] += 1

                class Result:
                    stderr = ""

                result = Result()
                if calls["count"] == 1:
                    result.returncode = 0
                    result.stdout = ""
                else:
                    result.returncode = 10
                    result.stdout = "cuInit=100\n"
                return result

            with mock.patch.object(preflight.subprocess, "run", side_effect=fake_run):
                report = preflight.build_and_run_preflight(
                    root,
                    materialization_report=materialization,
                    artifact_dir=Path("artifacts/preflight"),
                )

        self.assertEqual(report["status"], "blocked_cuda_unavailable")
        self.assertFalse(report["real_cuda_runtime_sequence_preflight_passed"])
        self.assertEqual(report["run"]["returncode"], 10)


if __name__ == "__main__":
    import unittest

    unittest.main()
