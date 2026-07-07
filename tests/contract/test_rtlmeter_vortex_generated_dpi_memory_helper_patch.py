import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_generated_dpi_memory_helper_patch import (  # noqa: E402
    PatchContext,
    patch_generated_dpi_memory_helper,
)


class RtlmeterVortexGeneratedDpiMemoryHelperPatchTest(HybridCliTestCase):
    def _write_root_cpp(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '// Verilated -*- C++ -*-\n'
            '#include "Vsim__pch.h"\n'
            "\n"
            "extern \"C\" void mem_access(svBit req_rw, unsigned long long req_byteen, unsigned long long req_addr, const svBitVecVal* req_data, svBitVecVal* rsp_data);\n"
            "\n"
            "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP(CData/*0:0*/ req_rw, QData/*63:0*/ req_byteen, QData/*63:0*/ req_addr, VlWide<16>/*511:0*/ req_data, VlWide<16>/*511:0*/ &rsp_data) {\n"
            "    svBit req_rw__Vcvt;\n"
            "    req_rw__Vcvt = req_rw;\n"
            "    unsigned long long req_byteen__Vcvt;\n"
            "    req_byteen__Vcvt = req_byteen;\n"
            "    unsigned long long req_addr__Vcvt;\n"
            "    req_addr__Vcvt = req_addr;\n"
            "    svBitVecVal req_data__Vcvt[16];\n"
            "    VL_SET_SVBV_W(512, req_data__Vcvt, req_data);\n"
            "    svBitVecVal rsp_data__Vcvt[16];\n"
            "    mem_access(req_rw__Vcvt, req_byteen__Vcvt, req_addr__Vcvt, req_data__Vcvt, rsp_data__Vcvt);\n"
            "    VL_SET_W_SVBV(512, rsp_data, rsp_data__Vcvt + 0);\n"
            "}\n",
            encoding="utf-8",
        )

    def test_patch_adds_shadow_helper_call_without_claiming_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root_cpp = root / "obj_dir" / "Vsim___024root__0.cpp"
            self._write_root_cpp(root_cpp)

            report = patch_generated_dpi_memory_helper(PatchContext(root_cpp=root_cpp, repo_root=root))
            patched = root_cpp.read_text(encoding="utf-8")

        self.assertEqual(report["status"], "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied")
        self.assertTrue(report["generated_dpi_wrapper_calls_vortex_mem_access_device_helper"])
        self.assertFalse(report["runtime_authority"])
        self.assertIn("vortex_memory_model_device.h", patched)
        self.assertIn("RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN", patched)
        self.assertIn("vortex_mem_access_device_helper(", patched)
        self.assertIn("mem_access(req_rw__Vcvt, req_byteen__Vcvt, req_addr__Vcvt, req_data__Vcvt, rsp_data__Vcvt)", patched)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_patch_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root_cpp = root / "obj_dir" / "Vsim___024root__0.cpp"
            self._write_root_cpp(root_cpp)

            first = patch_generated_dpi_memory_helper(PatchContext(root_cpp=root_cpp, repo_root=root))
            second = patch_generated_dpi_memory_helper(PatchContext(root_cpp=root_cpp, repo_root=root))

        self.assertEqual(first["status"], "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied")
        self.assertEqual(second["status"], "rtlmeter_vortex_generated_dpi_memory_helper_patch_already_present")
        self.assertTrue(second["generated_dpi_memory_helper_patch_applied"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root_cpp = root / "obj_dir" / "Vsim___024root__0.cpp"
            out = root / "reports" / "dpi_patch.json"
            self._write_root_cpp(root_cpp)

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_generated_dpi_memory_helper_patch.py",
                "--repo-root",
                root.as_posix(),
                "--root-cpp",
                root_cpp.relative_to(root).as_posix(),
                "--write-report",
                "--report-out",
                out.relative_to(root).as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_generated_dpi_memory_helper_patch")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
