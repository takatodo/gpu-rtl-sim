import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_broader_runtime_entrypoint as broader  # noqa: E402


class ScientificCirctBroaderRuntimeEntrypointTest(HybridCliTestCase):
    def _adapter(self, library: Path) -> dict[str, object]:
        return {
            "surface": "scientific_circt_runtime_handoff_adapter",
            "status": "adapter_correctness_passed",
            "candidate": "microgpt_attention_head",
            "shape": "1024x1",
            "nstates": 1024,
            "repeat": 5,
            "inner_repeat": 1000,
            "integration_batches": 8,
            "adapter_library": library.as_posix(),
            "average": {
                "cpu_ms": 0.8,
                "gpu_end_to_end_ms": 0.1,
                "gpu_kernel_ms": 0.02,
            },
        }

    def _bridge_stdout(self) -> str:
        return json.dumps(
            {
                "status": "broader_runtime_entrypoint_passed",
                "nstates": 1024,
                "repeat": 5,
                "inner_repeat": 1000,
                "integration_batches": 8,
                "correctness_status": "adapter_correctness_passed",
                "hybrid_status": "hybrid_entrypoint_passed",
                "mismatch_count": 0,
                "cpu_control_checksum": 55,
                "correctness_gpu_control_checksum": 55,
                "timed_gpu_control_checksum": 55,
                "cpu_vs_gpu_output_equal": True,
                "cpu_vs_gpu_control_checksum_equal": True,
                "timed_gpu_checksum_matches_correctness": True,
                "cpu_ms": 0.8,
                "gpu_end_to_end_ms": 0.1,
                "gpu_kernel_ms": 0.02,
                "bridge_hybrid_wall_ms": 8.0,
                "bridge_hybrid_wall_ms_per_integration_batch": 0.2,
                "cpu_to_bridge_hybrid_wall_speedup": 4.0,
                "cpu_to_gpu_end_to_end_speedup": 8.0,
                "cpu_to_gpu_kernel_speedup": 40.0,
            }
        )

    def test_measure_broader_runtime_entrypoint_records_bridge_boundary(self) -> None:
        compile_calls: list[tuple[Path, Path]] = []
        run_calls: list[list[str]] = []

        def fake_compile(source: Path, binary: Path) -> dict[str, object]:
            compile_calls.append((source, binary))
            return {
                "argv": ["cc", "-O2", broader._display_path(source), "-ldl", "-o", broader._display_path(binary)],
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        def fake_run(argv: list[str]) -> dict[str, object]:
            run_calls.append(argv)
            return {
                "argv": [broader._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": self._bridge_stdout(),
                "stderr": "",
                "process_wall_ms": 9.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(broader, "_compile_bridge", side_effect=fake_compile), \
             mock.patch.object(broader, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            library = root / "adapter.so"
            bridge_source = root / "scientific_circt_adapter_bridge.c"
            library.write_text("", encoding="utf-8")
            bridge_source.write_text("", encoding="utf-8")
            report = broader.measure_broader_runtime_entrypoint(
                self._adapter(library),
                out_dir=root / "out",
                bridge_source=bridge_source,
            )

        self.assertEqual(report["status"], "broader_hybrid_entrypoint_timing_measured")
        self.assertEqual(report["entrypoint_kind"], "src_hybrid_c_bridge_dlopen_adapter_library")
        self.assertEqual(report["adapter_invocation_kind"], "dlopen_in_process_shared_library")
        self.assertFalse(report["subprocess_used_for_adapter"])
        self.assertTrue(report["python_process_spawn_used_for_bridge"])
        self.assertTrue(report["warmup_run_excluded_from_timing"])
        self.assertEqual(compile_calls[0][0], bridge_source)
        self.assertEqual(run_calls[0][-4:], ["1024", "5", "1000", "8"])
        self.assertEqual(run_calls[0][1], library.as_posix())
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertTrue(report["cpu_vs_gpu_control_checksum_equal"])
        self.assertTrue(report["timed_gpu_checksum_matches_correctness"])
        self.assertEqual(report["bridge_hybrid_wall_ms_per_integration_batch"], 0.2)
        self.assertEqual(report["cpu_to_bridge_hybrid_wall_speedup"], 4.0)
        self.assertIn("not_direct_verilator_entrypoint", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_missing_library_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = broader.measure_broader_runtime_entrypoint(
                self._adapter(Path(temp_dir) / "missing.so")
            )
        self.assertEqual(report["status"], "failed_missing_adapter_library")

    def test_bridge_compile_failure_fails_closed(self) -> None:
        def fake_compile(source: Path, binary: Path) -> dict[str, object]:
            return {
                "argv": ["cc", "-O2", broader._display_path(source), "-ldl", "-o", broader._display_path(binary)],
                "returncode": 1,
                "stdout": "",
                "stderr": "compile failed",
                "process_wall_ms": 1.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            broader, "_compile_bridge", side_effect=fake_compile
        ):
            root = Path(temp_dir)
            library = root / "adapter.so"
            source = root / "bridge.c"
            library.write_text("", encoding="utf-8")
            source.write_text("", encoding="utf-8")
            report = broader.measure_broader_runtime_entrypoint(
                self._adapter(library),
                out_dir=root / "out",
                bridge_source=source,
            )
        self.assertEqual(report["status"], "failed_broader_hybrid_bridge_build")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_bridge_run_failure_fails_closed(self) -> None:
        def fake_compile(source: Path, binary: Path) -> dict[str, object]:
            return {"argv": [], "returncode": 0, "stdout": "", "stderr": "", "process_wall_ms": 1.0}

        def fake_run(argv: list[str]) -> dict[str, object]:
            return {
                "argv": [broader._sanitize(arg) for arg in argv],
                "returncode": 1,
                "stdout": "{\"status\":\"failed_dlopen_adapter_library\"}",
                "stderr": broader._sanitize("/home/example/adapter.so failed"),
                "process_wall_ms": 2.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(broader, "_compile_bridge", side_effect=fake_compile), \
             mock.patch.object(broader, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            library = root / "adapter.so"
            source = root / "bridge.c"
            library.write_text("", encoding="utf-8")
            source.write_text("", encoding="utf-8")
            report = broader.measure_broader_runtime_entrypoint(
                self._adapter(library),
                out_dir=root / "out",
                bridge_source=source,
            )
        self.assertEqual(report["status"], "failed_broader_hybrid_bridge_run")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        def fake_compile(source: Path, binary: Path) -> dict[str, object]:
            return {
                "argv": ["cc", "-O2", broader._display_path(source), "-ldl", "-o", broader._display_path(binary)],
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        def fake_run(argv: list[str]) -> dict[str, object]:
            return {
                "argv": [broader._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": self._bridge_stdout(),
                "stderr": "",
                "process_wall_ms": 8.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(broader, "_compile_bridge", side_effect=fake_compile), \
             mock.patch.object(broader, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            library = root / "adapter.so"
            library.write_text("", encoding="utf-8")
            adapter_report = root / "adapter.json"
            out = root / "broader.json"
            adapter_report.write_text(json.dumps(self._adapter(library)), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = broader.main(
                    [
                        "--adapter-report",
                        adapter_report.as_posix(),
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                        "--out-dir",
                        (root / "out").as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "broader_hybrid_entrypoint_timing_measured")
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))

    def test_bridge_source_uses_expected_adapter_symbols(self) -> None:
        source = (REPO_ROOT / "src" / "hybrid" / "scientific_circt_adapter_bridge.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("dlopen", source)
        self.assertIn("dlsym", source)
        self.assertIn("microgpt_attention_head_handoff_adapter_run_json", source)
        self.assertIn("microgpt_attention_head_handoff_adapter_run_hybrid_json", source)


if __name__ == "__main__":
    unittest.main()
