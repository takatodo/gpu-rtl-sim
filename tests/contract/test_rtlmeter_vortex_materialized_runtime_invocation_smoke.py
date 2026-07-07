import hashlib
import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_materialized_runtime_invocation_smoke import build_smoke  # noqa: E402


class RtlmeterVortexMaterializedRuntimeInvocationSmokeTest(HybridCliTestCase):
    def _write_artifact(self, root: Path, name: str, data: bytes) -> dict[str, object]:
        path = root / "artifacts" / "vortex_buffers" / f"{name}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {
            "name": name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "artifact": f"artifacts/vortex_buffers/{name}.bin",
        }

    def _write_ready_inputs(self, root: Path) -> tuple[Path, Path, Path]:
        buffers = [
            self._write_artifact(root, "vortex_init_segment_table", b"a" * 24),
            self._write_artifact(root, "vortex_init_payload", b"b" * 8),
            self._write_artifact(root, "vortex_post_segment_table", b"c" * 24),
            self._write_artifact(root, "vortex_post_expected_payload", b"d" * 4),
            self._write_artifact(root, "vortex_dcr_write_table", b"e" * 16),
            self._write_artifact(root, "vortex_stdout_ring_initial", bytes(64)),
            self._write_artifact(root, "vortex_post_compare_result_initial", bytes(24)),
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
                    "device_schedule": {
                        "bytes": 16,
                        "sha256": hashlib.sha256(b"e" * 16).hexdigest(),
                    },
                }
            ),
            encoding="utf-8",
        )
        header = root / "src" / "hybrid" / "vortex_lowered_tb_runtime_sequence.h"
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text(
            "\n".join(
                [
                    "vortex_lowered_tb_invoke_runtime_sequence",
                    "vortex_run_runtime_sequence",
                    "authority_report_ready",
                    "authority_passed",
                ]
            ),
            encoding="utf-8",
        )
        return materialization, dcr, header

    def test_ready_when_materialized_buffers_schedule_and_header_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization, dcr, header = self._write_ready_inputs(root)

            report = build_smoke(
                root,
                materialization_report=materialization,
                dcr_schedule_report=dcr,
                lowered_tb_header=header,
            )

        self.assertEqual(report["status"], "materialized_runtime_invocation_smoke_ready_not_integrated")
        self.assertTrue(report["smoke_ready"])
        self.assertEqual(report["buffer_count"], 7)
        self.assertEqual(report["host_to_device_bytes"], 76)
        self.assertEqual(report["dcr_schedule_bytes"], 16)
        self.assertEqual(report["missing_prerequisites"], [])
        self.assertIn(
            "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            report["still_missing_for_execution"],
        )
        self.assertIn("not_vortex_gpu_execution", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_blocks_when_required_artifact_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization, dcr, header = self._write_ready_inputs(root)
            (root / "artifacts" / "vortex_buffers" / "vortex_stdout_ring_initial.bin").unlink()

            report = build_smoke(
                root,
                materialization_report=materialization,
                dcr_schedule_report=dcr,
                lowered_tb_header=header,
            )

        self.assertEqual(report["status"], "blocked_materialized_runtime_invocation_smoke")
        self.assertFalse(report["smoke_ready"])
        self.assertIn("buffer_artifact.vortex_stdout_ring_initial", report["missing_prerequisites"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            materialization, dcr, header = self._write_ready_inputs(root)
            out = root / "reports" / "smoke.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_materialized_runtime_invocation_smoke.py",
                "--repo-root",
                root.as_posix(),
                "--materialization-report",
                materialization.as_posix(),
                "--dcr-schedule-report",
                dcr.as_posix(),
                "--lowered-tb-header",
                header.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_materialized_runtime_invocation_smoke")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
