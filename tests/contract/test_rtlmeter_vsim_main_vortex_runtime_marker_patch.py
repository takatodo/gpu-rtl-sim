import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainVortexRuntimeMarkerPatchTest(HybridCliTestCase):
    def _generated_main(self) -> str:
        return "\n".join(
            [
                "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
                '#include "verilated.h"',
                '#include "Vsim.h"',
                "int main(int argc, char** argv, char**) {",
                "    Verilated::debug(0);",
                "    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};",
                "    contextp->threads(1);",
                "    contextp->commandArgs(argc, argv);",
                "    // Construct the Verilated model, from Vtop.h generated from Verilating",
                '    const std::unique_ptr<Vsim> topp{new Vsim{contextp.get(), ""}};',
                "    // Simulate until $finish",
                "    while (VL_LIKELY(!contextp->gotFinish())) {",
                "        topp->eval();",
                "    }",
                "    topp->final();",
                "    contextp->statsPrintSummary();",
                "}",
                "",
            ]
        )

    def test_missing_source_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_marker_patch import patch_vortex_runtime_sequence_marker

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = patch_vortex_runtime_sequence_marker(
                main_cpp=root / "obj_dir" / "Vsim__main.cpp",
                repo_root=root,
            )

        self.assertEqual(report["status"], "rtlmeter_vsim_main_vortex_runtime_marker_patch_missing_source")
        self.assertFalse(report["marker_applied"])
        self.assertFalse(report["runtime_authority"])
        self.assertIn("main_cpp", report["missing_patch_context"])

    def test_patches_generated_main_with_fail_closed_marker(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_marker_patch import (
            PATCH_BEGIN,
            patch_vortex_runtime_sequence_marker,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            report = patch_vortex_runtime_sequence_marker(main_cpp=main_cpp, repo_root=root)
            patched_text = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_vortex_runtime_marker_patch_applied")
        self.assertTrue(report["marker_applied"])
        self.assertFalse(report["runtime_authority"])
        self.assertFalse(report["timing_measured"])
        self.assertIn(PATCH_BEGIN, patched_text)
        self.assertIn("vortex_lowered_tb_invoke_runtime_sequence", patched_text)
        self.assertIn("vortex_mem_access_device_helper", patched_text)
        self.assertLess(
            patched_text.index(PATCH_BEGIN),
            patched_text.index("    // Construct the Verilated model"),
        )

    def test_marker_patch_is_idempotent(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_marker_patch import (
            PATCH_BEGIN,
            patch_vortex_runtime_sequence_marker,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            first = patch_vortex_runtime_sequence_marker(main_cpp=main_cpp, repo_root=root)
            second = patch_vortex_runtime_sequence_marker(main_cpp=main_cpp, repo_root=root)
            patched_text = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(first["status"], "rtlmeter_vsim_main_vortex_runtime_marker_patch_applied")
        self.assertEqual(second["status"], "rtlmeter_vsim_main_vortex_runtime_marker_patch_already_present")
        self.assertEqual(patched_text.count(PATCH_BEGIN), 1)
        self.assertTrue(second["marker_applied"])
        self.assertFalse(second["runtime_authority"])

    def test_rejects_unsupported_source_without_mutating(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_marker_patch import patch_vortex_runtime_sequence_marker

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            original = "// no generated main sentinels\n"
            main_cpp.write_text(original, encoding="utf-8")
            report = patch_vortex_runtime_sequence_marker(main_cpp=main_cpp, repo_root=root)
            after = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_vortex_runtime_marker_patch_unsupported_source")
        self.assertFalse(report["marker_applied"])
        self.assertEqual(after, original)


if __name__ == "__main__":
    import unittest

    unittest.main()
