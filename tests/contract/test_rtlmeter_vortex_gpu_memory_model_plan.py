import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_gpu_memory_model_plan import build_plan  # noqa: E402


class RtlmeterVortexGpuMemoryModelPlanTest(HybridCliTestCase):
    def _write_input_summary(self, root: Path) -> Path:
        path = root / "reports" / "rtlmeter_vortex_binary_input_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_binary_input_summary",
                    "status": "parsed",
                    "case": "Vortex:mini:hello",
                    "files": {
                        "init": {"path": "third_party/rtlmeter/designs/Vortex/tests/hello/init.bin"},
                        "post": {"path": "third_party/rtlmeter/designs/Vortex/tests/hello/post.bin"},
                        "dcrs": {"path": "third_party/rtlmeter/designs/Vortex/tests/hello/dcrs.bin"},
                    },
                    "gpu_input_model": {"block_size_bytes": 64},
                    "init_memory": {
                        "segment_count": 9,
                        "total_payload_bytes": 36864,
                        "address_min_hex": "0x10000",
                        "address_max_exclusive_hex": "0x80008000",
                    },
                    "post_memory": {
                        "segment_count": 1,
                        "total_payload_bytes": 48,
                    },
                    "dcr_writes": {"write_count": 9},
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_plan_defines_memory_model_buffers_from_input_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_input_summary(root)

            plan = build_plan(root)

        self.assertEqual(plan["status"], "abi_plan_ready")
        self.assertFalse(plan["runtime_launchable"])
        self.assertEqual(plan["memory_model_abi"]["init_segments"], 9)
        self.assertEqual(plan["memory_model_abi"]["init_block_count"], 576)
        self.assertEqual(plan["memory_model_abi"]["post_block_count"], 1)
        self.assertEqual(plan["memory_model_abi"]["dcr_write_count"], 9)
        self.assertEqual(plan["memory_model_abi"]["segment_record_bytes"], 24)
        self.assertEqual(plan["memory_model_abi"]["segment_table_bytes"], 240)
        self.assertEqual(plan["memory_model_abi"]["minimum_static_input_bytes"], 37224)
        init_segment_table = plan["device_buffers"][0]
        self.assertEqual(init_segment_table["record_type"], "u64_addr_u64_payload_offset_u64_size_bytes")
        self.assertEqual(init_segment_table["bytes"], 216)
        self.assertIn("vortex_stdout_ring", [buffer["name"] for buffer in plan["device_buffers"]])
        self.assertIn("vortex_post_compare_result", [buffer["name"] for buffer in plan["device_buffers"]])
        self.assertIn("vortex_mem_access_device_helper", [entry["name"] for entry in plan["kernel_entrypoints"]])
        self.assert_no_local_absolute_paths(json.dumps(plan, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_input_summary(root)
            out = root / "reports" / "vortex_plan.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_gpu_memory_model_plan.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_gpu_memory_model_plan")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
