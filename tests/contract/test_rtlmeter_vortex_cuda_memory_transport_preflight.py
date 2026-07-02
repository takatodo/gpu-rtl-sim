import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import rtlmeter_vortex_cuda_memory_transport_preflight as preflight  # noqa: E402


class RtlmeterVortexCudaMemoryTransportPreflightTest(HybridCliTestCase):
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

    def test_generated_source_uses_cuda_driver_api_and_vortex_upload_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization = preflight._load_json(self._write_materialization(root))
            buffers = preflight._collect_buffers(materialization, repo_root=root)
            source = preflight._generated_source(repo_root=root, buffers=buffers)

        self.assertIn("#include <cuda.h>", source)
        self.assertIn("cuInit(0)", source)
        self.assertIn("cuCtxCreate(&ctx, 0, dev)", source)
        self.assertIn("cuMemAlloc(&ptr, bytes)", source)
        self.assertIn("cuMemcpyHtoD((CUdeviceptr)dst, src, bytes)", source)
        self.assertIn("vortex_upload_runtime_buffers(&driver, buffers, 7, &summary)", source)
        self.assertIn("summary.h2d_bytes != 37224u", source)

    def test_preflight_report_classifies_passed_fake_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization = self._write_materialization(root)

            def fake_run(argv, **kwargs):
                class Result:
                    returncode = 0
                    stdout = (
                        "allocated_count=7\n"
                        "h2d_copy_count=5\n"
                        "d2h_init_count=2\n"
                        "h2d_bytes=37224\n"
                        "d2h_initial_bytes=88\n"
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
        self.assertTrue(report["real_cuda_memory_transport_passed"])
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["timing_measured"])
        self.assertEqual(report["host_to_device_bytes"], 37224)
        self.assertEqual(report["device_to_host_initial_bytes"], 88)
        self.assertIn("not_vortex_kernel_execution", report["non_claims"])
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
        self.assertFalse(report["real_cuda_memory_transport_passed"])
        self.assertEqual(report["run"]["returncode"], 10)


if __name__ == "__main__":
    import unittest

    unittest.main()
