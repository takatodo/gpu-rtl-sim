import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainVortexRuntimeInvocationProbePatchTest(HybridCliTestCase):
    def _generated_main(self) -> str:
        return "\n".join(
            [
                "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
                '#include "verilated.h"',
                '#include "Vsim.h"',
                "",
                "typedef int VortexCuResult;",
                "typedef struct { const char *failed_stage; } VortexRuntimeSequenceSummary;",
                "typedef struct { int runtime_sequence_called; int runtime_sequence_passed; int authority_report_ready; } VortexLoweredTbRuntimeSummary;",
                "static inline VortexCuResult vortex_lowered_tb_invoke_runtime_sequence(const void *, VortexRuntimeSequenceSummary *, VortexLoweredTbRuntimeSummary *) { return 1; }",
                "",
                "//======================",
                "",
                "int main(int argc, char** argv, char**) {",
                "    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};",
                "    contextp->commandArgs(argc, argv);",
                '    const std::unique_ptr<Vsim> topp{new Vsim{contextp.get(), ""}};',
                "    /* RTLMETER_SIDECAR_PROXY_PATCH_BEGIN */",
                "    /* RTLMETER_SIDECAR_PROXY_PATCH_END */",
                "    while (VL_LIKELY(!contextp->gotFinish())) {",
                "        topp->eval();",
                "    }",
                "    topp->final();",
                "}",
                "",
            ]
        )

    def test_patches_generated_main_with_expected_fail_invocation_probe(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch import (
            PATCH_BEGIN,
            patch_vortex_runtime_invocation_probe,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            report = patch_vortex_runtime_invocation_probe(main_cpp=main_cpp, repo_root=root)
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(
            report["status"],
            "rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch_applied",
        )
        self.assertTrue(report["invocation_probe_applied"])
        self.assertFalse(report["runtime_authority"])
        self.assertIn(PATCH_BEGIN, patched)
        self.assertIn("vortex_lowered_tb_invoke_runtime_sequence(0, &sequence_summary, &tb_summary)", patched)
        self.assertIn("if (rtlmeter_vortex_runtime_invocation_expected_fail_probe() != 0) return 124;", patched)

    def test_invocation_probe_patch_is_idempotent(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch import (
            PATCH_BEGIN,
            patch_vortex_runtime_invocation_probe,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            first = patch_vortex_runtime_invocation_probe(main_cpp=main_cpp, repo_root=root)
            second = patch_vortex_runtime_invocation_probe(main_cpp=main_cpp, repo_root=root)
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(first["status"], "rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch_applied")
        self.assertEqual(second["status"], "rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch_already_present")
        self.assertEqual(patched.count(PATCH_BEGIN), 1)

    def test_missing_or_unsupported_source_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch import patch_vortex_runtime_invocation_probe

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = patch_vortex_runtime_invocation_probe(main_cpp=root / "obj_dir" / "Vsim__main.cpp", repo_root=root)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text("// unsupported\n", encoding="utf-8")
            unsupported = patch_vortex_runtime_invocation_probe(main_cpp=main_cpp, repo_root=root)

        self.assertEqual(
            missing["status"],
            "rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch_missing_source",
        )
        self.assertFalse(missing["invocation_probe_applied"])
        self.assertEqual(
            unsupported["status"],
            "rtlmeter_vsim_main_vortex_runtime_invocation_probe_patch_unsupported_source",
        )
        self.assertFalse(unsupported["invocation_probe_applied"])


if __name__ == "__main__":
    import unittest

    unittest.main()
