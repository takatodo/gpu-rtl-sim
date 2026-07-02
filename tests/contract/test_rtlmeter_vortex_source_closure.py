import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_source_closure import build_source_closure  # noqa: E402


class RtlmeterVortexSourceClosureTest(HybridCliTestCase):
    def _write_descriptor(self, root: Path, *, include_missing: bool = False) -> None:
        design = root / "third_party" / "rtlmeter" / "designs" / "Vortex"
        (design / "src" / "dpi").mkdir(parents=True, exist_ok=True)
        (design / "src" / "fpnew").mkdir(parents=True, exist_ok=True)
        for rel_path in (
            "src/tb.sv",
            "src/Vortex.sv",
            "src/VX_define.vh",
            "src/fpnew/registers.svh",
            "src/dpi/memory.cpp",
        ):
            if include_missing and rel_path == "src/Vortex.sv":
                continue
            path = design / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("// fixture\n", encoding="utf-8")
        (design / "descriptor.yaml").write_text(
            "\n".join(
                [
                    "compile:",
                    "  verilogSourceFiles:",
                    "    - src/tb.sv",
                    "    - src/Vortex.sv",
                    "  verilogIncludeFiles:",
                    "    - src/VX_define.vh",
                    "    - src/fpnew/registers.svh",
                    "  verilogDefines:",
                    "    SIMULATION: 1",
                    "    XLEN_32: 1",
                    "  cppSourceFiles:",
                    "    - src/dpi/memory.cpp",
                    "  topModule: tb",
                    "  mainClock: tb.clk",
                    "  verilatorArgs:",
                    "    - --autoflush",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def test_source_closure_reports_complete_descriptor_owned_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_descriptor(root)

            summary = build_source_closure(root)

        self.assertEqual(summary["status"], "descriptor_source_closure_complete")
        self.assertTrue(summary["all_sources_exist"])
        self.assertEqual(summary["source_counts"]["verilog"], 2)
        self.assertEqual(summary["source_counts"]["include"], 2)
        self.assertEqual(summary["source_counts"]["cpp"], 1)
        self.assertEqual(summary["source_counts"]["total"], 5)
        self.assertEqual(summary["verilog_defines"]["SIMULATION"], "1")
        self.assertEqual(summary["verilator_args"], ["--autoflush"])
        self.assertFalse(summary["execution_authority"]["runtime_launchable"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_source_closure_reports_missing_descriptor_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_descriptor(root, include_missing=True)

            summary = build_source_closure(root)

        self.assertEqual(summary["status"], "descriptor_source_closure_incomplete")
        self.assertFalse(summary["all_sources_exist"])
        self.assertIn("third_party/rtlmeter/designs/Vortex/src/Vortex.sv", summary["missing_paths"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_descriptor(root)
            out = root / "reports" / "vortex_source_closure.json"
            out.parent.mkdir()

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_source_closure.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_source_closure")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    unittest.main()
