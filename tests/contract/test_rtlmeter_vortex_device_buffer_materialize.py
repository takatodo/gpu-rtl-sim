import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_device_buffer_materialize import build_materialization  # noqa: E402


class RtlmeterVortexDeviceBufferMaterializeTest(HybridCliTestCase):
    def _write_inputs(self, root: Path) -> Path:
        test_dir = root / "third_party" / "rtlmeter" / "designs" / "Vortex" / "tests" / "hello"
        test_dir.mkdir(parents=True, exist_ok=True)
        init_a = b"abcd"
        init_b = b"XYZ"
        post = b"ok"
        (test_dir / "init.bin").write_bytes(
            struct.pack("<QQ", 0x1000, len(init_a))
            + init_a
            + struct.pack("<QQ", 0x2000, len(init_b))
            + init_b
        )
        (test_dir / "post.bin").write_bytes(struct.pack("<QQ", 0x1002, len(post)) + post)
        (test_dir / "dcrs.bin").write_bytes(struct.pack(">II", 1, 0x80000000) + struct.pack(">II", 2, 3))
        return test_dir

    def test_materialization_builds_segment_payload_and_dcr_buffers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_inputs(root)

            summary = build_materialization(root, test_dir=test_dir)

        self.assertEqual(summary["status"], "device_buffers_materialized")
        self.assertEqual(summary["abi"]["segment_record_bytes"], 24)
        self.assertEqual(summary["inputs"]["init_segments"], 2)
        self.assertEqual(summary["inputs"]["init_payload_bytes"], 7)
        self.assertEqual(summary["segment_records"]["init"][0]["payload_offset"], 0)
        self.assertEqual(summary["segment_records"]["init"][1]["payload_offset"], 4)
        buffers = {item["name"]: item for item in summary["device_buffers"]}
        self.assertEqual(buffers["vortex_init_segment_table"]["bytes"], 48)
        self.assertEqual(buffers["vortex_init_payload"]["bytes"], 7)
        self.assertEqual(buffers["vortex_post_segment_table"]["bytes"], 24)
        self.assertEqual(buffers["vortex_dcr_write_table"]["bytes"], 16)
        self.assertEqual(summary["totals"]["host_to_device_bytes"], 97)
        self.assertEqual(summary["abi"]["post_compare_result_bytes"], 24)
        self.assertEqual(summary["totals"]["device_to_host_initial_bytes"], 88)
        self.assertTrue(summary["readiness_delta"]["device_buffers_materialized"])
        self.assertIn("not_device_upload", summary["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_inputs(root)
            report = root / "reports" / "vortex_buffers.json"
            artifact_dir = root / "artifacts" / "vortex_buffers"
            report.parent.mkdir()

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_device_buffer_materialize.py",
                "--repo-root",
                root.as_posix(),
                "--test-dir",
                test_dir.as_posix(),
                "--artifact-dir",
                artifact_dir.as_posix(),
                "--write-report",
                "--report-out",
                report.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(stdout_payload, report_payload)
            self.assertEqual(report_payload["surface"], "rtlmeter_vortex_device_buffer_materialize")
            init_table = artifact_dir / "vortex_init_segment_table.bin"
            self.assertTrue(init_table.is_file())
            self.assertEqual(init_table.read_bytes()[:24], struct.pack("<QQQ", 0x1000, 0, 4))
            dcr_table = artifact_dir / "vortex_dcr_write_table.bin"
            self.assertEqual(dcr_table.read_bytes(), struct.pack("<II", 1, 0x80000000) + struct.pack("<II", 2, 3))
            self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
