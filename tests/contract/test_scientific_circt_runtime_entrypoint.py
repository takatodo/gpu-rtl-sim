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

import scientific_circt_runtime_entrypoint as entrypoint  # noqa: E402


class ScientificCirctRuntimeEntrypointTest(HybridCliTestCase):
    def _adapter(self, binary: Path, library: Path | None = None) -> dict[str, object]:
        return {
            "surface": "scientific_circt_runtime_handoff_adapter",
            "status": "adapter_correctness_passed",
            "candidate": "microgpt_attention_head",
            "shape": "1024x1",
            "nstates": 1024,
            "repeat": 5,
            "inner_repeat": 1000,
            "integration_batches": 8,
            "adapter_binary": binary.as_posix(),
            "adapter_library": (library or binary.with_suffix(".so")).as_posix(),
            "average": {
                "cpu_ms": 0.8,
                "gpu_end_to_end_ms": 0.1,
                "gpu_kernel_ms": 0.02,
                "cpu_to_gpu_end_to_end_speedup": 8.0,
                "cpu_to_gpu_kernel_speedup": 40.0,
            },
        }

    def test_measure_entrypoint_records_process_wall_per_batch(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            self.assertEqual(argv[-4:], ["1024", "5", "1000", "8"])
            return {
                "argv": [entrypoint._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "status": "adapter_correctness_passed",
                        "nstates": 1024,
                        "repeat": 5,
                        "inner_repeat": 1000,
                        "integration_batches": 8,
                        "input_bytes": 20480,
                        "output_bytes": 32768,
                        "mismatch_count": 0,
                        "cpu_control_checksum": 55,
                        "gpu_control_checksum": 55,
                        "cpu_ms": 0.8,
                        "gpu_end_to_end_ms": 0.1,
                        "gpu_kernel_ms": 0.02,
                        "cpu_to_gpu_end_to_end_speedup": 8.0,
                        "cpu_to_gpu_kernel_speedup": 40.0,
                    }
                ),
                "stderr": "",
                "process_wall_ms": 80.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(entrypoint, "_run", side_effect=fake_run):
            binary = Path(temp_dir) / "adapter"
            binary.write_text("", encoding="utf-8")
            report = entrypoint.measure_entrypoint(self._adapter(binary))

        self.assertEqual(report["status"], "entrypoint_timing_measured")
        self.assertEqual(report["entrypoint_kind"], "process_mediated_adapter_binary")
        self.assertEqual(report["process_wall_ms_per_integration_batch"], 2.0)
        self.assertEqual(report["cpu_to_process_wall_speedup"], 0.4)
        self.assertAlmostEqual(report["process_extra_ms_per_integration_batch"], 1.1)
        self.assertAlmostEqual(report["process_extra_to_adapter_gpu_end_to_end_ratio"], 11.0)
        self.assertEqual(report["resident_reuse_break_even_integration_batches"], 2)
        self.assertEqual(report["resident_reuse_target_integration_batches"], 3)
        self.assertEqual(
            report["next_required_evidence"],
            "resident_or_in_process_entrypoint_with_at_least_target_integration_batches_and_cpu_vs_gpu_equality",
        )
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertTrue(report["cpu_vs_gpu_control_checksum_equal"])
        self.assertIn("not_direct_verilator_entrypoint", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_missing_binary_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = entrypoint.measure_entrypoint(self._adapter(Path(temp_dir) / "missing"))
        self.assertEqual(report["status"], "failed_missing_adapter_binary")

    def test_missing_library_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binary = Path(temp_dir) / "adapter"
            binary.write_text("", encoding="utf-8")
            report = entrypoint.measure_in_process_entrypoint(
                self._adapter(binary, Path(temp_dir) / "missing.so")
            )
        self.assertEqual(report["status"], "failed_missing_adapter_library")

    def test_measure_in_process_entrypoint_records_library_wall_per_batch(self) -> None:
        def fake_call(
            library: Path,
            nstates: int,
            repeat: int,
            inner_repeat: int,
            integration_batches: int,
            symbol: str = "microgpt_attention_head_handoff_adapter_run_json",
        ) -> dict[str, object]:
            self.assertEqual(library.name, "adapter.so")
            self.assertEqual((nstates, repeat, inner_repeat, integration_batches), (1024, 5, 1000, 8))
            if symbol == "microgpt_attention_head_handoff_adapter_run_hybrid_json":
                payload = {
                    "status": "hybrid_entrypoint_passed",
                    "nstates": 1024,
                    "repeat": 5,
                    "inner_repeat": 1000,
                    "integration_batches": 8,
                    "input_bytes": 20480,
                    "output_bytes": 32768,
                    "gpu_control_checksum": 55,
                    "gpu_end_to_end_ms": 0.1,
                    "gpu_kernel_ms": 0.02,
                    "cuda_status": "success",
                }
            else:
                payload = {
                    "status": "adapter_correctness_passed",
                    "nstates": 1024,
                    "repeat": 5,
                    "inner_repeat": 1000,
                    "integration_batches": 8,
                    "input_bytes": 20480,
                    "output_bytes": 32768,
                    "mismatch_count": 0,
                    "cpu_control_checksum": 55,
                    "gpu_control_checksum": 55,
                    "cpu_ms": 0.8,
                    "gpu_end_to_end_ms": 0.1,
                    "gpu_kernel_ms": 0.02,
                    "cpu_to_gpu_end_to_end_speedup": 8.0,
                    "cpu_to_gpu_kernel_speedup": 40.0,
                }
            return {
                "library": entrypoint._display_path(library),
                "symbol": symbol,
                "returncode": 0,
                "stdout": json.dumps(payload),
                "in_process_wall_ms": 12.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(entrypoint, "_call_in_process_library", side_effect=fake_call):
            root = Path(temp_dir)
            binary = root / "adapter"
            library = root / "adapter.so"
            binary.write_text("", encoding="utf-8")
            library.write_text("", encoding="utf-8")
            report = entrypoint.measure_in_process_entrypoint(self._adapter(binary, library))

        self.assertEqual(report["status"], "in_process_entrypoint_timing_measured")
        self.assertEqual(report["entrypoint_kind"], "in_process_adapter_library")
        self.assertFalse(report["subprocess_used"])
        self.assertTrue(report["warmup_run_excluded_from_timing"])
        self.assertEqual(len(report["calls"]), 2)
        self.assertEqual(report["calls"][0]["stage"], "in_process_warmup_adapter_library_run")
        self.assertEqual(report["calls"][1]["stage"], "in_process_timed_hybrid_library_run")
        self.assertEqual(report["in_process_wall_ms_per_integration_batch"], 0.3)
        self.assertAlmostEqual(report["cpu_to_in_process_wall_speedup"], 0.8 / 0.3)
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertTrue(report["cpu_vs_gpu_control_checksum_equal"])
        self.assertTrue(report["timed_gpu_checksum_matches_correctness"])
        self.assertEqual(
            report["next_required_evidence"],
            "direct_verilator_or_broader_hybrid_runtime_entrypoint_after_in_process_adapter_library_timing",
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        def fake_run(argv: list[str]) -> dict[str, object]:
            return {
                "argv": [entrypoint._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "status": "adapter_correctness_passed",
                        "nstates": 1024,
                        "repeat": 5,
                        "inner_repeat": 1000,
                        "integration_batches": 8,
                        "input_bytes": 20480,
                        "output_bytes": 32768,
                        "mismatch_count": 0,
                        "cpu_control_checksum": 99,
                        "gpu_control_checksum": 99,
                        "cpu_ms": 0.8,
                        "gpu_end_to_end_ms": 0.1,
                        "gpu_kernel_ms": 0.02,
                        "cpu_to_gpu_end_to_end_speedup": 8.0,
                        "cpu_to_gpu_kernel_speedup": 40.0,
                    }
                ),
                "stderr": "",
                "process_wall_ms": 40.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(entrypoint, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            binary = root / "adapter"
            binary.write_text("", encoding="utf-8")
            adapter_report = root / "adapter.json"
            out = root / "entrypoint.json"
            adapter_report.write_text(json.dumps(self._adapter(binary)), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = entrypoint.main(
                    [
                        "--adapter-report",
                        adapter_report.as_posix(),
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "entrypoint_timing_measured")
        self.assertEqual(payload["process_wall_ms_per_integration_batch"], 1.0)
        self.assertAlmostEqual(payload["process_extra_ms_per_integration_batch"], 0.1)
        self.assertEqual(payload["resident_reuse_break_even_integration_batches"], 1)
        self.assertEqual(payload["resident_reuse_target_integration_batches"], 2)
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))

    def test_cli_writes_in_process_report(self) -> None:
        def fake_call(
            library: Path,
            nstates: int,
            repeat: int,
            inner_repeat: int,
            integration_batches: int,
            symbol: str = "microgpt_attention_head_handoff_adapter_run_json",
        ) -> dict[str, object]:
            if symbol == "microgpt_attention_head_handoff_adapter_run_hybrid_json":
                payload = {
                    "status": "hybrid_entrypoint_passed",
                    "nstates": nstates,
                    "repeat": repeat,
                    "inner_repeat": inner_repeat,
                    "integration_batches": integration_batches,
                    "input_bytes": 20480,
                    "output_bytes": 32768,
                    "gpu_control_checksum": 77,
                    "gpu_end_to_end_ms": 0.1,
                    "gpu_kernel_ms": 0.02,
                    "cuda_status": "success",
                }
            else:
                payload = {
                    "status": "adapter_correctness_passed",
                    "nstates": nstates,
                    "repeat": repeat,
                    "inner_repeat": inner_repeat,
                    "integration_batches": integration_batches,
                    "input_bytes": 20480,
                    "output_bytes": 32768,
                    "mismatch_count": 0,
                    "cpu_control_checksum": 77,
                    "gpu_control_checksum": 77,
                    "cpu_ms": 0.8,
                    "gpu_end_to_end_ms": 0.1,
                    "gpu_kernel_ms": 0.02,
                    "cpu_to_gpu_end_to_end_speedup": 8.0,
                    "cpu_to_gpu_kernel_speedup": 40.0,
                }
            return {
                "library": entrypoint._display_path(library),
                "symbol": symbol,
                "returncode": 0,
                "stdout": json.dumps(payload),
                "in_process_wall_ms": 8.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(entrypoint, "_call_in_process_library", side_effect=fake_call):
            root = Path(temp_dir)
            binary = root / "adapter"
            library = root / "adapter.so"
            binary.write_text("", encoding="utf-8")
            library.write_text("", encoding="utf-8")
            adapter_report = root / "adapter.json"
            out = root / "entrypoint.json"
            adapter_report.write_text(json.dumps(self._adapter(binary, library)), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = entrypoint.main(
                    [
                        "--adapter-report",
                        adapter_report.as_posix(),
                        "--mode",
                        "in-process",
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "in_process_entrypoint_timing_measured")
        self.assertEqual(payload["in_process_wall_ms_per_integration_batch"], 0.2)
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
