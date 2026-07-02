import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_generated_lowered_tb_invocation_smoke import build_and_run_smoke  # noqa: E402


class RtlmeterVortexGeneratedLoweredTbInvocationSmokeTest(HybridCliTestCase):
    def _copy_headers(self, root: Path) -> None:
        dst = root / "src" / "hybrid"
        dst.mkdir(parents=True, exist_ok=True)
        for name in [
            "vortex_memory_model_device.h",
            "vortex_runtime_upload.h",
            "vortex_observable_export.h",
            "vortex_runtime_sequence.h",
            "vortex_lowered_tb_runtime_sequence.h",
        ]:
            shutil.copyfile(REPO_ROOT / "src" / "hybrid" / name, dst / name)

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

    def _write_reports(self, root: Path) -> tuple[Path, Path]:
        buffers = [
            self._write_buffer(root, "vortex_init_segment_table", b"a" * 24),
            self._write_buffer(root, "vortex_init_payload", b"b" * 8),
            self._write_buffer(root, "vortex_post_segment_table", b"c" * 24),
            self._write_buffer(root, "vortex_post_expected_payload", b"d" * 4),
            self._write_buffer(
                root,
                "vortex_dcr_write_table",
                struct.pack("<II", 1, 0x80000000) + struct.pack("<II", 2, 0),
            ),
            self._write_buffer(root, "vortex_stdout_ring_initial", bytes(64)),
            self._write_buffer(root, "vortex_post_compare_result_initial", bytes(24)),
        ]
        materialization = root / "reports" / "materialization.json"
        materialization.parent.mkdir(parents=True, exist_ok=True)
        materialization.write_text(
            json.dumps(
                {
                    "status": "device_buffers_materialized",
                    "device_buffers": buffers,
                    "totals": {
                        "host_to_device_bytes": 76,
                        "device_to_host_initial_bytes": 88,
                    },
                }
            ),
            encoding="utf-8",
        )
        dcr = root / "reports" / "dcr.json"
        dcr.write_text(
            json.dumps(
                {
                    "status": "dcr_schedule_materialized",
                    "write_count": 2,
                    "device_schedule": {"bytes": 16},
                }
            ),
            encoding="utf-8",
        )
        return materialization, dcr

    def test_generated_c_harness_compiles_and_calls_lowered_tb_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._copy_headers(root)
            materialization, dcr = self._write_reports(root)

            report = build_and_run_smoke(
                root,
                materialization_report=materialization,
                dcr_schedule_report=dcr,
                artifact_dir=Path("artifacts/generated_smoke"),
            )

        self.assertEqual(report["status"], "generated_lowered_tb_invocation_smoke_passed")
        self.assertTrue(report["generated_lowered_tb_invocation_smoke_passed"])
        self.assertEqual(report["buffer_count"], 7)
        self.assertEqual(report["dcr_write_count"], 2)
        self.assertIn("runtime_sequence_called=1", report["run"]["stdout"])
        self.assertIn("authority_passed=1", report["run"]["stdout"])
        self.assertTrue(
            report["readiness_delta"]["generated_c_harness_calls_vortex_lowered_tb_invoke_runtime_sequence"]
        )
        self.assertIn("not_vortex_gpu_execution", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._copy_headers(root)
            materialization, dcr = self._write_reports(root)
            out = root / "reports" / "generated_smoke.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.py",
                "--repo-root",
                root.as_posix(),
                "--materialization-report",
                materialization.as_posix(),
                "--dcr-schedule-report",
                dcr.as_posix(),
                "--artifact-dir",
                "artifacts/generated_smoke",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_generated_lowered_tb_invocation_smoke")
        self.assertEqual(report_payload["status"], "generated_lowered_tb_invocation_smoke_passed")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
