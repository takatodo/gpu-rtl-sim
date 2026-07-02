import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke import build_and_run_smoke  # noqa: E402


class RtlmeterVortexLoweredTbMemoryHelperIntegrationSmokeTest(HybridCliTestCase):
    def _copy_header(self, root: Path) -> None:
        dst = root / "src" / "hybrid"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / "src" / "hybrid" / "vortex_memory_model_device.h", dst / "vortex_memory_model_device.h")

    def _write_buffer(self, root: Path, name: str, data: bytes) -> dict[str, object]:
        path = root / "artifacts" / "vortex_buffers" / f"{name}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {
            "name": name,
            "bytes": len(data),
            "artifact": f"artifacts/vortex_buffers/{name}.bin",
            "sha256": "unused",
        }

    def _write_materialization(self, root: Path) -> Path:
        init_payload = bytes(range(128))
        post_payload = bytes([0xA0, 0xA1, 0xA2, 0xA3])
        buffers = [
            self._write_buffer(root, "vortex_init_segment_table", struct.pack("<QQQ", 0x1000, 0, len(init_payload))),
            self._write_buffer(root, "vortex_init_payload", init_payload),
            self._write_buffer(root, "vortex_post_segment_table", struct.pack("<QQQ", 0x1008, 0, len(post_payload))),
            self._write_buffer(root, "vortex_post_expected_payload", post_payload),
        ]
        path = root / "reports" / "materialization.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "device_buffers_materialized",
                    "device_buffers": buffers,
                    "inputs": {
                        "init_segments": 1,
                        "post_segments": 1,
                    },
                    "totals": {
                        "host_to_device_bytes": 180,
                        "device_to_host_initial_bytes": 88,
                    },
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_generated_c_harness_routes_memory_accesses_through_device_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._copy_header(root)
            materialization = self._write_materialization(root)

            report = build_and_run_smoke(
                root,
                materialization_report=materialization,
                artifact_dir=Path("artifacts/memory_helper_smoke"),
            )

        self.assertEqual(report["status"], "lowered_tb_memory_helper_integration_smoke_passed")
        self.assertTrue(report["lowered_tb_memory_helper_integration_smoke_passed"])
        self.assertEqual(report["init_segment_count"], 1)
        self.assertEqual(report["post_segment_count"], 1)
        self.assertIn("post_replay_mismatches=0", report["run_stdout"])
        self.assertIn("stdout_chars=12", report["run_stdout"])
        self.assertTrue(report["readiness_delta"]["generated_c_harness_calls_vortex_mem_access_device_helper"])
        self.assertIn("not_vortex_gpu_execution", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._copy_header(root)
            materialization = self._write_materialization(root)
            out = root / "reports" / "memory_helper_smoke.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.py",
                "--repo-root",
                root.as_posix(),
                "--materialization-report",
                materialization.as_posix(),
                "--artifact-dir",
                "artifacts/memory_helper_smoke",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke")
        self.assertEqual(report_payload["status"], "lowered_tb_memory_helper_integration_smoke_passed")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
