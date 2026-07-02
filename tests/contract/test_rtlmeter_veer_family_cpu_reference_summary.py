import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_veer_family_cpu_reference_summary import build_summary  # noqa: E402


class RtlmeterVeerFamilyCpuReferenceSummaryTest(HybridCliTestCase):
    def _write_cpu_reference(self, root: Path, design: str, *, cycles: int, stdout: str) -> None:
        case = f"{design}:default:hello"
        design_config = f"{design}:default"
        work_root = root / f"artifacts/rtlmeter_{design.lower().replace('-', '_')}_cpu_reference"
        compile_dir = work_root / design / "default" / "compile-0"
        execute_dir = work_root / design / "default" / "execute-0" / "hello"
        for rel in ["_files", "_verilate", "_cppbuild"]:
            (compile_dir / rel).mkdir(parents=True, exist_ok=True)
            (compile_dir / rel / "status").write_text("success\n", encoding="utf-8")
        (compile_dir / "obj_dir").mkdir(parents=True, exist_ok=True)
        (compile_dir / "obj_dir" / "Vsim").write_text("", encoding="utf-8")
        (compile_dir / "_verilate" / "metrics.json").write_text(
            json.dumps({design_config: {"verilate": {"elapsed": 1.0, "memory": 2.0}}}),
            encoding="utf-8",
        )
        (compile_dir / "_cppbuild" / "metrics.json").write_text(
            json.dumps(
                {
                    design_config: {
                        "cppbuild": {"elapsed": 3.0},
                        "compile": {"elapsed": 4.0, "memory": 5.0},
                    }
                }
            ),
            encoding="utf-8",
        )
        for rel in ["_files", "_execute", "_postHook"]:
            (execute_dir / rel).mkdir(parents=True, exist_ok=True)
            (execute_dir / rel / "status").write_text("success\n", encoding="utf-8")
        (execute_dir / "_execute" / "metrics.json").write_text(
            json.dumps({case: {"execute": {"elapsed": 0.03, "clocks": cycles, "speed": 34.8}}}),
            encoding="utf-8",
        )
        (execute_dir / "_execute" / "stdout.log").write_text(stdout, encoding="utf-8")
        (execute_dir / "_rtlmeter_cycles.txt").write_text(str(cycles), encoding="utf-8")

    def test_summary_accepts_eh1_cpu_reference_observables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_cpu_reference(
                root,
                "VeeR-EH1",
                cycles=1044,
                stdout="Finished : minstret = 335, mcycle = 1038\nTEST_PASSED\nVerilog $finish\n",
            )

            report = build_summary(root, design="VeeR-EH1")

        self.assertEqual(report["surface"], "rtlmeter_veer_family_cpu_reference_summary")
        self.assertEqual(report["status"], "cpu_reference_passed")
        self.assertTrue(report["cpu_reference_ready_for_hybrid_compare"])
        self.assertEqual(report["rtlmeter_cycles"], 1044)
        self.assertEqual(report["finished_records"][0]["minstret"], 335)
        self.assertEqual(report["metrics"]["execute_clocks"], 1044)
        self.assertFalse(any("gpu" == item for item in report["non_claims"]))
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report_for_eh2(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_cpu_reference(
                root,
                "VeeR-EH2",
                cycles=2325,
                stdout=(
                    "TEST_PASSED\n"
                    "Finished hart0 : minstret = 921, mcycle = 2319\n"
                    "Finished hart1 : minstret = 1357, mcycle = 2251\n"
                    "Verilog $finish\n"
                ),
            )
            out = root / "reports/eh2.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_veer_family_cpu_reference_summary.py",
                "--repo-root",
                root.as_posix(),
                "--design",
                "VeeR-EH2",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertIn('"status": "cpu_reference_passed"', result.stdout)
        self.assertEqual(payload["finished_records"][1]["hart"], 1)
        self.assertEqual(payload["rtlmeter_cycles"], 2325)
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
