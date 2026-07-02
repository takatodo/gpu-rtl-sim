import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from scientific_circt_runtime_handoff_abi import build_handoff_abi  # noqa: E402


class ScientificCirctRuntimeHandoffAbiTest(HybridCliTestCase):
    def _matrix(self) -> dict[str, object]:
        top = {
            "rank": 1,
            "candidate": "microgpt_attention_head",
            "shape": "1024x1",
            "nstates": 1024,
            "steps": 1,
            "cpu_owner": "microgpt_sequence_order_and_kv_cache_authority",
            "gpu_subsystem": "microgpt_attention_head_arithmetic",
            "cpu_to_gpu_end_to_end_speedup": 6.38015,
            "cpu_to_gpu_kernel_speedup": 26.5253,
            "cpu_ms": 0.700777,
            "gpu_end_to_end_ms": 0.109837,
            "gpu_kernel_ms": 0.0264192,
        }
        return {
            "surface": "scientific_circt_hybrid_dispatch_matrix",
            "top_runtime_integration_candidate": top,
            "runtime_integration_queue": [top],
        }

    def _protocol(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_hybrid_protocol",
            "candidates": {
                "microgpt_attention_head": {
                    "status": "protocol_ready",
                    "cpu_owner": "microgpt_sequence_order_and_kv_cache_authority",
                    "gpu_subsystem": "microgpt_attention_head_arithmetic",
                }
            },
        }

    def _timing_report(self) -> dict[str, object]:
        return {
            "surface": "scientific_circt_testbench",
            "status": "measured",
            "candidate": "microgpt_attention_head",
            "shape": "1024x1",
            "median": {"cpu_to_gpu_end_to_end_speedup": 6.38015},
        }

    def test_builds_ready_handoff_abi_for_top_queue_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sv = root / "microgpt_attention_head.sv"
            cpu = root / "Vsim"
            gpu = root / "microgpt_attention_head_gpu_timing"
            for path in (sv, cpu, gpu):
                path.write_text("ok\n", encoding="utf-8")
            report = build_handoff_abi(self._matrix(), self._protocol(), self._timing_report(), sv, cpu, gpu)

        self.assertEqual(report["status"], "handoff_abi_ready")
        self.assertEqual(report["candidate"], "microgpt_attention_head")
        self.assertEqual(report["shape"], "1024x1")
        self.assertEqual(report["handoff_abi"]["logical_input_bytes"], 20480)
        self.assertEqual(report["handoff_abi"]["logical_output_bytes"], 32768)
        self.assertEqual(report["handoff_abi"]["logical_roundtrip_bytes"], 53248)
        self.assertEqual(report["handoff_abi"]["input_struct"]["bytes_per_state"], 20)
        self.assertEqual(report["handoff_abi"]["output_struct"]["bytes_per_state"], 32)
        self.assertIn("not_runtime_speedup_claim", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_missing_artifact_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sv = root / "microgpt_attention_head.sv"
            cpu = root / "Vsim"
            gpu = root / "missing_gpu_timing"
            for path in (sv, cpu):
                path.write_text("ok\n", encoding="utf-8")
            report = build_handoff_abi(self._matrix(), self._protocol(), self._timing_report(), sv, cpu, gpu)

        self.assertEqual(report["status"], "handoff_abi_incomplete")
        self.assertFalse(report["artifacts_ready"])

    def test_rejects_non_top_candidate(self) -> None:
        matrix = self._matrix()
        matrix["top_runtime_integration_candidate"]["candidate"] = "dense_matmul_tile"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(ValueError):
                build_handoff_abi(
                    matrix,
                    self._protocol(),
                    self._timing_report(),
                    root / "a.sv",
                    root / "cpu",
                    root / "gpu",
                )

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            matrix = root / "matrix.json"
            protocol = root / "protocol.json"
            timing = root / "timing.json"
            sv = root / "microgpt_attention_head.sv"
            cpu = root / "Vsim"
            gpu = root / "microgpt_attention_head_gpu_timing"
            out = root / "handoff.json"
            matrix.write_text(json.dumps(self._matrix()), encoding="utf-8")
            protocol.write_text(json.dumps(self._protocol()), encoding="utf-8")
            timing.write_text(json.dumps(self._timing_report()), encoding="utf-8")
            for path in (sv, cpu, gpu):
                path.write_text("ok\n", encoding="utf-8")
            result = self.run_python_tool(
                "src/tools/scientific_circt_runtime_handoff_abi.py",
                "--matrix",
                matrix.as_posix(),
                "--protocol",
                protocol.as_posix(),
                "--timing-report",
                timing.as_posix(),
                "--systemverilog",
                sv.as_posix(),
                "--cpu-reference-binary",
                cpu.as_posix(),
                "--gpu-timing-binary",
                gpu.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout), payload)
        self.assertEqual(payload["status"], "handoff_abi_ready")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
