import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainVortexProbeMarkerStripTest(HybridCliTestCase):
    def _patched_main(self) -> str:
        return "\n".join(
            [
                "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
                '#include "verilated.h"',
                '#include "Vsim.h"',
                "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_BEGIN */",
                "static int rtlmeter_vortex_runtime_invocation_expected_fail_probe() { return 0; }",
                "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_END */",
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */",
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {",
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);",
                "  return result;",
                "}",
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_END */",
                "int main(int argc, char** argv, char**) {",
                "    contextp->commandArgs(argc, argv);",
                "    /* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_BEGIN */",
                "    /* next_call_boundary=vortex_lowered_tb_invoke_runtime_sequence */",
                "    /* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_END */",
                "    /* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_CALL_BEGIN */",
                "    if (rtlmeter_vortex_runtime_invocation_expected_fail_probe() != 0) return 124;",
                "    /* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_CALL_END */",
                "    /* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */",
                "    if (rtlmeter_vortex_materialized_runtime_args_probe() != 0) return 123;",
                "    /* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_END */",
                "    while (VL_LIKELY(!contextp->gotFinish())) { topp->eval(); }",
                "    topp->final();",
                "}",
                "",
            ]
        )

    def test_strips_marker_and_invocation_probe_but_preserves_materialized_args_probe(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_probe_marker_strip import strip_vortex_probe_markers

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._patched_main(), encoding="utf-8")
            report = strip_vortex_probe_markers(main_cpp=main_cpp, repo_root=root)
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_vortex_probe_marker_strip_applied")
        self.assertTrue(report["probe_marker_stripped"])
        self.assertEqual(report["runtime_sequence_marker_removed"], 1)
        self.assertEqual(report["runtime_invocation_probe_removed"], 1)
        self.assertEqual(report["runtime_invocation_probe_call_removed"], 1)
        self.assertTrue(report["materialized_runtime_args_probe_preserved"])
        self.assertFalse(report["runtime_authority"])
        self.assertNotIn("RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_BEGIN", patched)
        self.assertNotIn("RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_BEGIN", patched)
        self.assertIn("RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN", patched)
        self.assertIn("rtlmeter_vortex_materialized_runtime_args_probe() != 0", patched)

    def test_strip_is_idempotent(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_probe_marker_strip import strip_vortex_probe_markers

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._patched_main(), encoding="utf-8")
            first = strip_vortex_probe_markers(main_cpp=main_cpp, repo_root=root)
            second = strip_vortex_probe_markers(main_cpp=main_cpp, repo_root=root)

        self.assertEqual(first["status"], "rtlmeter_vsim_main_vortex_probe_marker_strip_applied")
        self.assertEqual(second["status"], "rtlmeter_vsim_main_vortex_probe_marker_strip_already_stripped")
        self.assertTrue(second["materialized_runtime_args_probe_preserved"])

    def test_missing_or_unsupported_source_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_probe_marker_strip import strip_vortex_probe_markers

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = strip_vortex_probe_markers(main_cpp=root / "obj_dir" / "Vsim__main.cpp", repo_root=root)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text("// unsupported\n", encoding="utf-8")
            unsupported = strip_vortex_probe_markers(main_cpp=main_cpp, repo_root=root)

        self.assertEqual(missing["status"], "rtlmeter_vsim_main_vortex_probe_marker_strip_missing_source")
        self.assertFalse(missing["probe_marker_stripped"])
        self.assertEqual(unsupported["status"], "rtlmeter_vsim_main_vortex_probe_marker_strip_unsupported_source")
        self.assertIn("materialized_runtime_args_probe_boundary", unsupported["missing_patch_context"])

    def test_cli_writes_report_without_local_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._patched_main(), encoding="utf-8")
            out = root / "reports" / "strip.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_vsim_main_vortex_probe_marker_strip.py",
                "--repo-root",
                root.as_posix(),
                "--main-cpp",
                main_cpp.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vsim_main_vortex_probe_marker_strip")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
