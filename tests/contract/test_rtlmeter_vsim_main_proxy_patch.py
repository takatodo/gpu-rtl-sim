import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainProxyPatchTest(HybridCliTestCase):
    def _generated_main(self) -> str:
        return "\n".join(
            [
                "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
                '#include "verilated.h"',
                '#include "Vsim.h"',
                "int main(int argc, char** argv, char**) {",
                "    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};",
                "    contextp->commandArgs(argc, argv);",
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

    def test_missing_vsim_main_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_proxy_patch import patch_rtlmeter_vsim_main_proxy_marker

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = patch_rtlmeter_vsim_main_proxy_marker(
                main_cpp=root / "obj_dir" / "Vsim__main.cpp",
                repo_root=root,
            )

        self.assertEqual(report["status"], "rtlmeter_vsim_main_proxy_patch_missing_source")
        self.assertFalse(report["patched_by_wrapper_branch"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertIn("main_cpp", report["missing_patch_context"])

    def test_unsupported_vsim_main_without_main_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_proxy_patch import patch_rtlmeter_vsim_main_proxy_marker

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            original = "// generated but no entrypoint\n"
            main_cpp.write_text(original, encoding="utf-8")
            report = patch_rtlmeter_vsim_main_proxy_marker(main_cpp=main_cpp, repo_root=root)
            after = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_proxy_patch_unsupported_source")
        self.assertFalse(report["patched_by_wrapper_branch"])
        self.assertFalse(report["reviewed_proxy_metadata_observed"])
        self.assertIn("#include \"verilated.h\"", report["missing_patch_context"])
        self.assertEqual(after, original)

    def test_rejects_non_vsim_main_path_without_mutating_file(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_proxy_patch import patch_rtlmeter_vsim_main_proxy_marker

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vother__main.cpp"
            main_cpp.parent.mkdir()
            original = self._generated_main()
            main_cpp.write_text(original, encoding="utf-8")
            report = patch_rtlmeter_vsim_main_proxy_marker(main_cpp=main_cpp, repo_root=root)
            after = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_proxy_patch_unsupported_source")
        self.assertIn("rtlmeter_vsim_main_path", report["missing_patch_context"])
        self.assertEqual(after, original)

    def test_patches_vsim_main_with_fail_closed_proxy_handoff(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_proxy_patch import (
            PATCH_BEGIN,
            PROXY_ENV,
            patch_rtlmeter_vsim_main_proxy_marker,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            report = patch_rtlmeter_vsim_main_proxy_marker(main_cpp=main_cpp, repo_root=root)
            patched_text = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_proxy_patch_applied")
        self.assertEqual(report["main_cpp"], "obj_dir/Vsim__main.cpp")
        self.assertTrue(report["patched_by_wrapper_branch"])
        self.assertTrue(report["reviewed_proxy_metadata_observed"])
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertFalse(report["ordinary_vsim_output"])
        self.assertIn(PATCH_BEGIN, patched_text)
        self.assertIn("#include <unistd.h>", patched_text)
        self.assertIn(f'std::getenv("{PROXY_ENV}")', patched_text)
        self.assertIn("execv(rtlmeter_sidecar_proxy, argv);", patched_text)
        self.assertIn("return 125;", patched_text)
        self.assertIn("return 126;", patched_text)
        self.assertIn("int main(int argc, char** argv, char**)", patched_text)
        self.assertLess(patched_text.index(PATCH_BEGIN), patched_text.index("    // Simulate until $finish"))

    def test_patch_is_idempotent(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_proxy_patch import PATCH_BEGIN, patch_rtlmeter_vsim_main_proxy_marker

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            first = patch_rtlmeter_vsim_main_proxy_marker(main_cpp=main_cpp, repo_root=root)
            second = patch_rtlmeter_vsim_main_proxy_marker(main_cpp=main_cpp, repo_root=root)
            patched_text = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(first["status"], "rtlmeter_vsim_main_proxy_patch_applied")
        self.assertEqual(second["status"], "rtlmeter_vsim_main_proxy_patch_already_present")
        self.assertEqual(patched_text.count(PATCH_BEGIN), 1)
        self.assertTrue(second["patched_by_wrapper_branch"])
        self.assertTrue(second["reviewed_proxy_metadata_observed"])

    def test_rejects_unbalanced_proxy_markers_without_mutating_file(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_proxy_patch import PATCH_BEGIN, patch_rtlmeter_vsim_main_proxy_marker

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            original = PATCH_BEGIN + "\n" + self._generated_main()
            main_cpp.write_text(original, encoding="utf-8")
            report = patch_rtlmeter_vsim_main_proxy_marker(main_cpp=main_cpp, repo_root=root)
            after = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vsim_main_proxy_patch_unsupported_source")
        self.assertIn("proxy_patch_markers", report["missing_patch_context"])
        self.assertEqual(after, original)
