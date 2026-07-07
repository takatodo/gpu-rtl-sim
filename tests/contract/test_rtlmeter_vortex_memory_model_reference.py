import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_memory_model_reference import (  # noqa: E402
    MEM_BLOCK_SIZE,
    VortexMemoryReference,
    build_reference,
)


class RtlmeterVortexMemoryModelReferenceTest(HybridCliTestCase):
    def _write_inputs(self, root: Path) -> Path:
        test_dir = root / "third_party" / "rtlmeter" / "designs" / "Vortex" / "tests" / "hello"
        test_dir.mkdir(parents=True, exist_ok=True)
        init_payload = bytes(range(64))
        post_payload = b"pass" + bytes(range(4, 16))
        (test_dir / "init.bin").write_bytes(struct.pack("<QQ", 0x1000, len(init_payload)) + init_payload)
        (test_dir / "post.bin").write_bytes(struct.pack("<QQ", 0x1000, len(post_payload)) + post_payload)
        (test_dir / "dcrs.bin").write_bytes(struct.pack(">II", 1, 0x80000000) + struct.pack(">II", 2, 3))
        return test_dir

    def test_reference_memory_access_matches_64b_block_and_byteen_semantics(self) -> None:
        ram = VortexMemoryReference()
        ram.write(0x1000, bytes([0] * MEM_BLOCK_SIZE))
        wdata = bytearray(MEM_BLOCK_SIZE)
        wdata[2] = 0xAA
        wdata[7] = 0xBB

        ram.mem_access(req_rw=True, byteen=(1 << 2) | (1 << 7), block_addr=0x1000 // MEM_BLOCK_SIZE, wdata=bytes(wdata))
        block = ram.mem_access(req_rw=False, byteen=0, block_addr=0x1000 // MEM_BLOCK_SIZE)

        self.assertEqual(block[2], 0xAA)
        self.assertEqual(block[7], 0xBB)
        self.assertEqual(block[1], 0)
        self.assertEqual(block[3], 0)

    def test_io_cout_write_captures_stdout_without_mutating_ram(self) -> None:
        ram = VortexMemoryReference()
        before = ram.read(0x40, 4)
        first = bytearray(MEM_BLOCK_SIZE)
        second = bytearray(MEM_BLOCK_SIZE)
        first[1] = ord("X")
        second[1] = ord("\n")

        ram.mem_access(req_rw=True, byteen=1 << 1, block_addr=1, wdata=bytes(first))
        ram.mem_access(req_rw=True, byteen=1 << 1, block_addr=1, wdata=bytes(second))

        self.assertEqual(before, ram.read(0x40, 4))
        self.assertEqual(ram.stdout_lines, ["#01: X\n"])

    def test_build_reference_validates_init_post_and_dcr_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_inputs(root)

            summary = build_reference(root, test_dir=test_dir)

        self.assertEqual(summary["status"], "reference_validated")
        self.assertFalse(summary["initial_post_compare"]["match"])
        self.assertGreater(summary["initial_post_compare"]["mismatch_count"], 0)
        self.assertEqual(summary["post_replay_self_check"]["status"], "passed")
        self.assertEqual(summary["io_cout_self_check"]["status"], "passed")
        self.assertEqual(summary["dcr_schedule"]["write_count"], 2)
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            test_dir = self._write_inputs(root)
            out = root / "reports" / "vortex_reference.json"
            out.parent.mkdir()

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_memory_model_reference.py",
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
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_memory_model_reference")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
