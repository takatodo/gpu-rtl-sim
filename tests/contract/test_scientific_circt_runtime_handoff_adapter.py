import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_runtime_handoff_adapter as adapter  # noqa: E402


class ScientificCirctRuntimeHandoffAdapterTest(HybridCliTestCase):
    def _abi(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_runtime_handoff_abi",
            "status": "handoff_abi_ready",
            "candidate": "microgpt_attention_head",
            "shape": "1024x1",
            "nstates": 1024,
            "handoff_abi": {
                "logical_input_bytes": 20480,
                "logical_output_bytes": 32768,
                "correctness_policy": "cpu_reference_outputs_equal_gpu_outputs_for_same_input_batch",
            },
        }

    def test_run_adapter_records_correctness_pass(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            stdout = ""
            if argv and argv[0].endswith("microgpt_attention_head_handoff_adapter"):
                self.assertEqual(argv[-4:], ["1024", "5", "1000", "8"])
                stdout = json.dumps(
                    {
                        "status": "adapter_correctness_passed",
                        "nstates": 1024,
                        "repeat": 5,
                        "inner_repeat": 1000,
                        "integration_batches": 8,
                        "input_bytes": 20480,
                        "output_bytes": 32768,
                        "mismatch_count": 0,
                        "cpu_control_checksum": 123,
                        "gpu_control_checksum": 123,
                        "cpu_ms": 1.0,
                        "gpu_end_to_end_ms": 0.5,
                        "gpu_kernel_ms": 0.125,
                        "cpu_to_gpu_end_to_end_speedup": 2.0,
                        "cpu_to_gpu_kernel_speedup": 8.0,
                        "cuda_status": "success",
                    }
                )
            return {"argv": [adapter._sanitize(arg) for arg in argv], "returncode": 0, "stdout": stdout, "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(adapter.shutil, "which", return_value="/usr/bin/nvcc"), \
             mock.patch.object(adapter, "_run", side_effect=fake_run):
            report = adapter.run_adapter(self._abi(), Path(temp_dir), inner_repeat=1000, integration_batches=8)

        self.assertEqual(report["status"], "adapter_correctness_passed")
        self.assertIn("adapter_library", report)
        self.assertTrue(report["input_bytes_match_abi"])
        self.assertTrue(report["output_bytes_match_abi"])
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertEqual(report["observed"]["mismatch_count"], 0)
        self.assertEqual(report["repeat"], 5)
        self.assertEqual(report["inner_repeat"], 1000)
        self.assertEqual(report["integration_batches"], 8)
        self.assertEqual(report["timing_scope"], "adapter_local_repeat_average_per_integration_batch")
        self.assertEqual(report["fused_work_scope"], "single_handoff_with_inner_repeated_attention_head_arithmetic")
        self.assertTrue(report["cpu_vs_gpu_control_checksum_equal"])
        self.assertEqual(report["average"]["cpu_to_gpu_end_to_end_speedup"], 2.0)
        self.assertEqual(report["average"]["cpu_to_gpu_kernel_speedup"], 8.0)
        self.assertIn("not_broad_runtime_speedup_claim", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_rejects_wrong_byte_counts(self) -> None:
        bad = self._abi()
        bad["handoff_abi"]["logical_input_bytes"] = 7
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                adapter.run_adapter(bad, Path(temp_dir))

    def test_failed_adapter_run_is_fail_closed(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            return {"argv": [adapter._sanitize(arg) for arg in argv], "returncode": 1, "stdout": "", "stderr": "no cuda"}

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(adapter, "_run", side_effect=fake_run):
            report = adapter.run_adapter(self._abi(), Path(temp_dir))

        self.assertEqual(report["status"], "failed_nvcc_build")

    def test_cli_writes_report(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            stdout = ""
            if argv and argv[0].endswith("microgpt_attention_head_handoff_adapter"):
                self.assertEqual(argv[-4:], ["1024", "7", "123", "4"])
                stdout = json.dumps(
                    {
                        "status": "adapter_correctness_passed",
                        "nstates": 1024,
                        "repeat": 7,
                        "inner_repeat": 123,
                        "integration_batches": 4,
                        "input_bytes": 20480,
                        "output_bytes": 32768,
                        "mismatch_count": 0,
                        "cpu_control_checksum": 456,
                        "gpu_control_checksum": 456,
                        "cpu_ms": 1.4,
                        "gpu_end_to_end_ms": 0.7,
                        "gpu_kernel_ms": 0.2,
                        "cpu_to_gpu_end_to_end_speedup": 2.0,
                        "cpu_to_gpu_kernel_speedup": 7.0,
                        "cuda_status": "success",
                    }
                )
            return {"argv": [adapter._sanitize(arg) for arg in argv], "returncode": 0, "stdout": stdout, "stderr": ""}

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(adapter, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            abi = root / "abi.json"
            out = root / "adapter.json"
            abi.write_text(json.dumps(self._abi()), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = adapter.main(
                    [
                        "--abi",
                        abi.as_posix(),
                        "--out-dir",
                        (root / "out").as_posix(),
                        "--repeat",
                        "7",
                        "--inner-repeat",
                        "123",
                        "--integration-batches",
                        "4",
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "adapter_correctness_passed")
        self.assertEqual(payload["repeat"], 7)
        self.assertEqual(payload["inner_repeat"], 123)
        self.assertEqual(payload["integration_batches"], 4)
        self.assertEqual(payload["average"]["cpu_to_gpu_kernel_speedup"], 7.0)
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
