import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_cpu_reference_summary import build_summary  # noqa: E402


class RtlmeterVortexCpuReferenceSummaryTest(HybridCliTestCase):
    def _write_cpu_reference_artifact(self, root: Path) -> Path:
        work = root / "artifacts" / "vortex_cpu"
        compile_dir = work / "Vortex" / "mini" / "compile-0"
        execute_dir = work / "Vortex" / "mini" / "execute-0" / "hello"
        (compile_dir / "obj_dir").mkdir(parents=True)
        (execute_dir / "_execute").mkdir(parents=True)
        (execute_dir / "_postHook").mkdir(parents=True)
        for step in ("_files", "_verilate", "_cppbuild"):
            (compile_dir / step).mkdir(parents=True, exist_ok=True)
            (compile_dir / step / "status").write_text("success", encoding="utf-8")
        (execute_dir / "_execute" / "status").write_text("success", encoding="utf-8")
        (execute_dir / "_postHook" / "status").write_text("success", encoding="utf-8")
        (compile_dir / "obj_dir" / "Vsim").write_text("binary", encoding="utf-8")
        (compile_dir / "_verilate" / "metrics.json").write_text(
            json.dumps({"Vortex:mini": {"verilate": {"elapsed": 4.05, "memory": 437.716}}}),
            encoding="utf-8",
        )
        (compile_dir / "_cppbuild" / "metrics.json").write_text(
            json.dumps(
                {
                    "Vortex:mini": {
                        "cppbuild": {"elapsed": 11.53, "memory": 401.152},
                        "compile": {"elapsed": 15.58, "memory": 437.716},
                    }
                }
            ),
            encoding="utf-8",
        )
        (execute_dir / "_execute" / "metrics.json").write_text(
            json.dumps(
                {
                    "Vortex:mini:hello": {
                        "execute": {
                            "elapsed": 0.22,
                            "memory": 8.932,
                            "clocks": 40897,
                            "speed": 185.89545454545453,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        (execute_dir / "_execute" / "stdout.log").write_text(
            "\n".join(
                [
                    "DCR write: *00000001 = 80000000",
                    "#00: Thread  0 - H",
                    "Done",
                    "TEST PASSED",
                    "- verilogSourceFiles/tb.sv:134: Verilog $finish",
                ]
            ),
            encoding="utf-8",
        )
        return work

    def test_summary_accepts_passed_cpu_reference_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_cpu_reference_artifact(root)

            report = build_summary(root, work_root=work)

        self.assertEqual(report["status"], "cpu_reference_passed")
        self.assertTrue(report["cpu_reference_ready_for_hybrid_compare"])
        self.assertTrue(report["stdout_test_passed"])
        self.assertTrue(report["finish_observed"])
        self.assertEqual(report["metrics"]["execute_elapsed_s"], 0.22)
        self.assertIn("not_hybrid_execution", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_cpu_reference_artifact(root)
            out = root / "reports" / "vortex_cpu_reference.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_cpu_reference_summary.py",
                "--repo-root",
                root.as_posix(),
                "--work-root",
                work.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_cpu_reference_summary")
        self.assertEqual(report_payload["status"], "cpu_reference_passed")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
