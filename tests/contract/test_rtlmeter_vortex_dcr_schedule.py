import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_dcr_schedule import build_schedule  # noqa: E402


class RtlmeterVortexDcrScheduleTest(HybridCliTestCase):
    def _write_dcrs(self, root: Path) -> Path:
        test_dir = root / "third_party" / "rtlmeter" / "designs" / "Vortex" / "tests" / "hello"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "dcrs.bin").write_bytes(
            struct.pack(">II", 0x00000001, 0x80000000)
            + struct.pack(">II", 0x00000002, 0x00000003)
            + struct.pack(">II", 0x00000010, 0x00000020)
        )
        return test_dir

    def test_schedule_materializes_tb_dcr_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_dcrs(root)

            summary = build_schedule(root, test_dir=test_dir)

        self.assertEqual(summary["status"], "dcr_schedule_materialized")
        self.assertEqual(summary["write_count"], 3)
        self.assertEqual(summary["input"]["encoding"], "big_endian_u32_addr_u32_value_pairs_for_sv_fread")
        self.assertEqual(summary["device_schedule"]["record_type"], "little_endian_u32_addr_u32_value")
        self.assertEqual(summary["device_schedule"]["bytes"], 24)
        self.assertTrue(summary["schedule_semantics"]["reset_asserted_during_all_dcr_writes"])
        self.assertEqual(
            summary["schedule_semantics"]["per_write"]["dcr_wr_valid_low_between_writes"],
            "delta_cycle_only",
        )
        self.assertEqual(
            summary["schedule_semantics"]["after_final_write"]["dcr_wr_valid_low_time_units_before_reset_deassert"],
            10,
        )
        self.assertEqual(summary["first_writes"][0]["addr_hex"], "0x00000001")
        self.assertIn("not_runtime_dcr_application", summary["non_claims"])
        self.assertIn(
            "runtime_execution_applies_vortex_dcr_schedule_while_reset_asserted",
            summary["readiness_delta"]["still_missing_for_runtime"],
        )
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report_and_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_dcrs(root)
            report = root / "reports" / "vortex_dcr_schedule.json"
            artifact_dir = root / "artifacts" / "vortex_dcr_schedule"
            report.parent.mkdir()

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_dcr_schedule.py",
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
            artifact_bytes = (artifact_dir / "vortex_dcr_schedule.bin").read_bytes()

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_dcr_schedule")
        self.assertEqual(
            artifact_bytes,
            struct.pack("<II", 0x00000001, 0x80000000)
            + struct.pack("<II", 0x00000002, 0x00000003)
            + struct.pack("<II", 0x00000010, 0x00000020),
        )
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
