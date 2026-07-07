import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainVortexRuntimeBridgeStubPatchTest(HybridCliTestCase):
    def _generated_main(self) -> str:
        return "\n".join(
            [
                "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
                '#include "verilated.h"',
                '#include "Vsim.h"',
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

    def _write_header(self, obj_dir: Path) -> None:
        header = obj_dir / "vortex_lowered_tb_runtime_sequence.h"
        header.write_text(
            "\n".join(
                [
                    "typedef struct { int kernel_launch_invoked; } VortexRuntimeSequenceSummary;",
                    "typedef struct { int runtime_sequence_called; } VortexLoweredTbRuntimeSummary;",
                    "static inline void vortex_runtime_sequence_summary_clear(VortexRuntimeSequenceSummary *s) {",
                    "    s->kernel_launch_invoked = 0;",
                    "}",
                    "static inline void vortex_lowered_tb_runtime_summary_clear(VortexLoweredTbRuntimeSummary *s) {",
                    "    s->runtime_sequence_called = 0;",
                    "}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_patches_generated_main_with_typed_bridge_stub_and_call(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch import (
            PATCH_BEGIN,
            patch_vortex_runtime_bridge_stub,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            self._write_header(main_cpp.parent)
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            report = patch_vortex_runtime_bridge_stub(
                main_cpp=main_cpp,
                repo_root=root,
                header_relative_from_obj_dir="vortex_lowered_tb_runtime_sequence.h",
            )
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_applied")
        self.assertTrue(report["bridge_stub_applied"])
        self.assertFalse(report["runtime_authority"])
        self.assertIn(PATCH_BEGIN, patched)
        self.assertIn('#include "vortex_lowered_tb_runtime_sequence.h"', patched)
        self.assertIn("VortexRuntimeSequenceSummary sequence_summary;", patched)
        self.assertIn("VortexLoweredTbRuntimeSummary tb_summary;", patched)
        self.assertIn("vortex_runtime_sequence_summary_clear(&sequence_summary);", patched)
        self.assertIn("vortex_lowered_tb_runtime_summary_clear(&tb_summary);", patched)
        self.assertIn("(void)rtlmeter_vortex_runtime_bridge_typed_stub();", patched)
        self.assertLess(patched.index(PATCH_BEGIN), patched.index("int main("))

    def test_bridge_stub_patch_is_idempotent(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch import PATCH_BEGIN, patch_vortex_runtime_bridge_stub

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            self._write_header(main_cpp.parent)
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            first = patch_vortex_runtime_bridge_stub(
                main_cpp=main_cpp,
                repo_root=root,
                header_relative_from_obj_dir="vortex_lowered_tb_runtime_sequence.h",
            )
            second = patch_vortex_runtime_bridge_stub(
                main_cpp=main_cpp,
                repo_root=root,
                header_relative_from_obj_dir="vortex_lowered_tb_runtime_sequence.h",
            )
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(first["status"], "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_applied")
        self.assertEqual(second["status"], "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_already_present")
        self.assertEqual(patched.count(PATCH_BEGIN), 1)

    def test_missing_header_or_unsupported_source_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch import patch_vortex_runtime_bridge_stub

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            missing_header = patch_vortex_runtime_bridge_stub(
                main_cpp=main_cpp,
                repo_root=root,
                header_relative_from_obj_dir="vortex_lowered_tb_runtime_sequence.h",
            )
            self._write_header(main_cpp.parent)
            main_cpp.write_text("// unsupported\n", encoding="utf-8")
            unsupported = patch_vortex_runtime_bridge_stub(
                main_cpp=main_cpp,
                repo_root=root,
                header_relative_from_obj_dir="vortex_lowered_tb_runtime_sequence.h",
            )

        self.assertEqual(
            missing_header["status"],
            "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_unsupported_source",
        )
        self.assertIn("vortex_lowered_tb_runtime_sequence_header", missing_header["missing_patch_context"])
        self.assertFalse(missing_header["bridge_stub_applied"])
        self.assertEqual(unsupported["status"], "rtlmeter_vsim_main_vortex_runtime_bridge_stub_patch_unsupported_source")
        self.assertFalse(unsupported["bridge_stub_applied"])


if __name__ == "__main__":
    import unittest

    unittest.main()
