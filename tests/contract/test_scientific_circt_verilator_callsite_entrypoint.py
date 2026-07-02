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

import scientific_circt_verilator_callsite_entrypoint as callsite  # noqa: E402


class ScientificCirctVerilatorCallsiteEntrypointTest(HybridCliTestCase):
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
        }

    def _observed_stdout(self) -> str:
        return json.dumps(
            {
                "status": "direct_verilator_callsite_entrypoint_passed",
                "nstates": 1024,
                "repeat": 5,
                "inner_repeat": 1000,
                "integration_batches": 8,
                "verilator_callsite_used": True,
                "hybrid_status": "hybrid_entrypoint_passed",
                "mismatch_count": 0,
                "verilator_control_checksum": 99,
                "timed_gpu_control_checksum": 99,
                "cpu_vs_gpu_output_equal": True,
                "cpu_vs_gpu_control_checksum_equal": True,
                "cpu_ms": 1.0,
                "gpu_end_to_end_ms": 0.1,
                "gpu_kernel_ms": 0.02,
                "bridge_hybrid_wall_ms": 8.0,
                "bridge_hybrid_wall_ms_per_integration_batch": 0.2,
                "cpu_to_bridge_hybrid_wall_speedup": 5.0,
                "cpu_to_gpu_end_to_end_speedup": 10.0,
                "cpu_to_gpu_kernel_speedup": 50.0,
            }
        )

    def _write_mdir(self, root: Path) -> Path:
        mdir = root / "obj_dir"
        mdir.mkdir()
        for name in ("Vsim.h", "Vsim__ALL.a", "verilated.o", "verilated_threads.o"):
            (mdir / name).write_text("", encoding="utf-8")
        return mdir

    def test_measure_records_verilator_generated_callsite_boundary(self) -> None:
        compile_calls: list[tuple[Path, Path, Path, Path]] = []
        run_calls: list[list[str]] = []

        def fake_compile(source: Path, binary: Path, mdir: Path, verilator_root: Path) -> dict[str, object]:
            compile_calls.append((source, binary, mdir, verilator_root))
            return {
                "argv": ["g++", "-O2", "-std=c++17", callsite._display_path(source), "-o", callsite._display_path(binary)],
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "process_wall_ms": 1.0,
            }

        def fake_run(argv: list[str]) -> dict[str, object]:
            run_calls.append(argv)
            return {
                "argv": [callsite._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": self._observed_stdout(),
                "stderr": "",
                "process_wall_ms": 9.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(callsite, "_verilator_root", return_value=(Path("/verilator"), None)), \
             mock.patch.object(callsite, "_compile_bridge", side_effect=fake_compile), \
             mock.patch.object(callsite, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            library = root / "adapter.so"
            bridge_source = root / "bridge.cpp"
            library.write_text("", encoding="utf-8")
            bridge_source.write_text("", encoding="utf-8")
            mdir = self._write_mdir(root)
            report = callsite.measure_verilator_callsite_entrypoint(
                self._adapter(library),
                out_dir=root / "out",
                bridge_source=bridge_source,
                mdir=mdir,
            )

        self.assertEqual(report["status"], "direct_verilator_callsite_entrypoint_timing_measured")
        self.assertEqual(report["entrypoint_kind"], "src_hybrid_cxx_bridge_verilator_generated_callsite")
        self.assertEqual(report["cpu_callsite_kind"], "verilator_generated_Vsim_eval")
        self.assertEqual(report["gpu_callsite_kind"], "adapter_shared_library_dlopen")
        self.assertTrue(report["verilator_callsite_used"])
        self.assertTrue(report["cpu_vs_gpu_output_equal"])
        self.assertTrue(report["cpu_vs_gpu_control_checksum_equal"])
        self.assertFalse(report["subprocess_used_for_adapter"])
        self.assertEqual(compile_calls[0][2], mdir)
        self.assertEqual(run_calls[0][-4:], ["1024", "5", "1000", "8"])
        self.assertEqual(report["cpu_to_bridge_hybrid_wall_speedup"], 5.0)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_missing_mdir_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(callsite, "_verilator_root", return_value=(Path("/verilator"), None)):
            root = Path(temp_dir)
            library = root / "adapter.so"
            library.write_text("", encoding="utf-8")
            report = callsite.measure_verilator_callsite_entrypoint(
                self._adapter(library),
                out_dir=root / "out",
                bridge_source=Path("src/hybrid/scientific_circt_verilator_callsite_bridge.cpp"),
                mdir=root / "missing_obj_dir",
            )
        self.assertEqual(report["status"], "failed_missing_verilator_callsite_inputs")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_bridge_build_failure_fails_closed(self) -> None:
        def fake_compile(source: Path, binary: Path, mdir: Path, verilator_root: Path) -> dict[str, object]:
            return {
                "argv": ["g++", callsite._display_path(source)],
                "returncode": 1,
                "stdout": "",
                "stderr": "compile failed",
                "process_wall_ms": 1.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(callsite, "_verilator_root", return_value=(Path("/verilator"), None)), \
             mock.patch.object(callsite, "_compile_bridge", side_effect=fake_compile):
            root = Path(temp_dir)
            library = root / "adapter.so"
            source = root / "bridge.cpp"
            library.write_text("", encoding="utf-8")
            source.write_text("", encoding="utf-8")
            mdir = self._write_mdir(root)
            report = callsite.measure_verilator_callsite_entrypoint(
                self._adapter(library),
                out_dir=root / "out",
                bridge_source=source,
                mdir=mdir,
            )
        self.assertEqual(report["status"], "failed_verilator_callsite_bridge_build")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        def fake_compile(source: Path, binary: Path, mdir: Path, verilator_root: Path) -> dict[str, object]:
            return {"argv": [], "returncode": 0, "stdout": "", "stderr": "", "process_wall_ms": 1.0}

        def fake_run(argv: list[str]) -> dict[str, object]:
            return {
                "argv": [callsite._sanitize(arg) for arg in argv],
                "returncode": 0,
                "stdout": self._observed_stdout(),
                "stderr": "",
                "process_wall_ms": 9.0,
            }

        with tempfile.TemporaryDirectory() as temp_dir, \
             mock.patch.object(callsite, "_verilator_root", return_value=(Path("/verilator"), None)), \
             mock.patch.object(callsite, "_compile_bridge", side_effect=fake_compile), \
             mock.patch.object(callsite, "_run", side_effect=fake_run):
            root = Path(temp_dir)
            library = root / "adapter.so"
            library.write_text("", encoding="utf-8")
            adapter_report = root / "adapter.json"
            adapter_report.write_text(json.dumps(self._adapter(library)), encoding="utf-8")
            mdir = self._write_mdir(root)
            out = root / "report.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = callsite.main(
                    [
                        "--adapter-report",
                        adapter_report.as_posix(),
                        "--mdir",
                        mdir.as_posix(),
                        "--out-dir",
                        (root / "out").as_posix(),
                        "--write-report",
                        "--report-out",
                        out.as_posix(),
                    ]
                )
            payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(payload["status"], "direct_verilator_callsite_entrypoint_timing_measured")
        self.assert_no_local_absolute_paths(json.dumps(payload, sort_keys=True))

    def test_bridge_source_uses_verilator_model_and_gpu_output_symbol(self) -> None:
        source = (
            REPO_ROOT / "src" / "hybrid" / "scientific_circt_verilator_callsite_bridge.cpp"
        ).read_text(encoding="utf-8")
        self.assertIn("#include \"Vsim.h\"", source)
        self.assertIn("Vsim top", source)
        self.assertIn("top.eval()", source)
        self.assertIn("microgpt_attention_head_handoff_adapter_run_gpu_outputs", source)
        self.assertIn("microgpt_attention_head_handoff_adapter_run_hybrid_json", source)


if __name__ == "__main__":
    unittest.main()
