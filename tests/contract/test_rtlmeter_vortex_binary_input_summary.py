import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_binary_input_summary import build_summary  # noqa: E402


class RtlmeterVortexBinaryInputSummaryTest(HybridCliTestCase):
    def _write_inputs(self, root: Path) -> Path:
        test_dir = root / "vortex" / "hello"
        test_dir.mkdir(parents=True)
        init_payload = b"abcd"
        post_payload = b"xyz"
        (test_dir / "init.bin").write_bytes(struct.pack("<QQ", 0x1000, len(init_payload)) + init_payload)
        (test_dir / "post.bin").write_bytes(struct.pack("<QQ", 0x2000, len(post_payload)) + post_payload)
        (test_dir / "dcrs.bin").write_bytes(struct.pack(">II", 1, 0x80000000) + struct.pack(">II", 2, 3))
        return test_dir

    def test_summary_parses_memory_segments_and_dcr_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_inputs(root)

            summary = build_summary(root, test_dir=test_dir)

        self.assertEqual(summary["status"], "parsed")
        self.assertEqual(summary["init_memory"]["segment_count"], 1)
        self.assertEqual(summary["init_memory"]["segments"][0]["addr"], 0x1000)
        self.assertEqual(summary["post_memory"]["total_payload_bytes"], 3)
        self.assertEqual(summary["dcr_writes"]["write_count"], 2)
        self.assertEqual(summary["dcr_writes"]["writes"][0]["addr"], 1)
        self.assertEqual(summary["dcr_writes"]["writes"][0]["value"], 0x80000000)
        self.assertEqual(summary["gpu_input_model"]["memory_segment_format"], "little_endian_u64_addr_u64_size_payload")
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_inputs(root)
            out = root / "reports" / "vortex_inputs.json"
            out.parent.mkdir()

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_binary_input_summary.py",
                "--repo-root",
                root.as_posix(),
                "--test-dir",
                test_dir.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_binary_input_summary")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
