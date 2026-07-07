import json
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainVortexRealCudaMaterializedRuntimePatchTest(HybridCliTestCase):
    def _main_with_fake_materialized_runtime(self) -> str:
        return "\n".join(
            [
                "#include <unistd.h>",
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */",
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_alloc(VortexCuDeviceptr* out, size_t bytes) { return 0; }",
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_h2d(VortexCuDeviceptr dst, const void* src, size_t bytes) { return 0; }",
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_memset(VortexCuDeviceptr dst, unsigned char value, size_t bytes) { return 0; }",
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_free(VortexCuDeviceptr ptr) { return 0; }",
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_dcr(void* user, uint32_t addr, uint32_t value, int reset_asserted) { return 0; }",
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_kernel(void* user, VortexRuntimeBuffer* buffers, unsigned buffer_count) { return 0; }",
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_dtoh(void* dst, VortexCuDeviceptr src, size_t bytes) { return 0; }",
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {",
                "    VortexCudaUploadDriver upload = {",
                "        rtlmeter_vortex_runtime_args_probe_alloc,",
                "        rtlmeter_vortex_runtime_args_probe_h2d,",
                "        rtlmeter_vortex_runtime_args_probe_memset,",
                "        rtlmeter_vortex_runtime_args_probe_free",
                "    };",
                "    VortexObservableExportDriver export_driver = {rtlmeter_vortex_runtime_args_probe_dtoh};",
                "    VortexRuntimeSequenceArgs args = {",
                "        &upload, buffers, 7, dcr_writes, 9,",
                "        rtlmeter_vortex_runtime_args_probe_dcr, 0,",
                "        rtlmeter_vortex_runtime_args_probe_kernel, 0,",
                "        &export_driver",
                "    };",
                "    VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);",
                "    for (unsigned i = 0; i < 5; ++i) { free((void*)buffers[i].host_data); buffers[i].host_data = 0; }",
                "    return result;",
                "}",
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_END */",
                "int main() {",
                "    /* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */",
                "    if (rtlmeter_vortex_materialized_runtime_args_probe() != 0) return 123;",
                "    /* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_END */",
                "    return 0;",
                "}",
                "",
            ]
        )

    def test_patches_callback_table_without_renaming_fake_definitions(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch import (
            PATCH_BEGIN,
            patch_real_cuda_materialized_runtime,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._main_with_fake_materialized_runtime(), encoding="utf-8")
            report = patch_real_cuda_materialized_runtime(main_cpp=main_cpp, repo_root=root)
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(
            report["status"],
            "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_applied",
        )
        self.assertTrue(report["real_cuda_materialized_runtime_patch_applied"])
        self.assertTrue(report["materialized_runtime_args_status_diagnostic_applied"])
        self.assertFalse(report["runtime_authority"])
        self.assertIn(PATCH_BEGIN, patched)
        self.assertIn("static VortexCuResult rtlmeter_vortex_runtime_args_probe_alloc", patched)
        self.assertIn("rtlmeter_vortex_real_cuda_alloc,", patched)
        self.assertIn("VortexObservableExportDriver export_driver = {rtlmeter_vortex_real_cuda_d2h};", patched)
        self.assertIn("rtlmeter_vortex_real_cuda_dcr, 0,", patched)
        self.assertIn("RtlmeterVortexRootStorageImage root_image", patched)
        self.assertIn("reinterpret_cast<const unsigned char*>(topp->rootp) - 192u", patched)
        self.assertIn("rtlmeter_vortex_real_cuda_launch_root_storage_kernel, &root_image,", patched)
        self.assertIn("cuModuleLoad", patched)
        self.assertIn("cuLaunchKernel", patched)
        self.assertIn("before_cuMemcpyHtoDRootStorage", patched)
        self.assertIn("relocated_root_image", patched)
        self.assertIn("rtlmeter_vortex_root_storage_relocation_count count=%zu", patched)
        self.assertIn("cuMemcpyHtoD(rtlmeter_vortex_root_storage, relocated_root_image, storage_size)", patched)
        self.assertIn("rtlmeter_vortex_root_storage", patched)
        self.assertIn("rtlmeter_vortex_root_storage_kernel_stage", patched)
        self.assertIn('rtlmeter_vortex_root_storage_kernel_stage("before_cuModuleLoad")', patched)
        self.assertIn('rtlmeter_vortex_root_storage_kernel_stage("before_cuLaunchKernel")', patched)
        self.assertIn("rtlmeter_vortex_runtime_authority authority_report_ready=%d", patched)
        self.assertIn("tb_summary.authority_source ? tb_summary.authority_source : \"none\"", patched)
        self.assertTrue(report["root_storage_kernel_callback_wired"])
        self.assertIn("rtlmeter_vortex_real_cuda_context_open", patched)
        self.assertIn("rtlmeter_vortex_real_cuda_context_close", patched)
        self.assertIn("rtlmeter_vortex_materialized_runtime_args_probe_status=%d", patched)
        self.assertIn("rtlmeter_vortex_materialized_runtime_args_probe(topp.get())", patched)

    def test_patch_is_idempotent(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch import (
            patch_real_cuda_materialized_runtime,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._main_with_fake_materialized_runtime(), encoding="utf-8")
            first = patch_real_cuda_materialized_runtime(main_cpp=main_cpp, repo_root=root)
            second = patch_real_cuda_materialized_runtime(main_cpp=main_cpp, repo_root=root)

        self.assertEqual(first["status"], "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_applied")
        self.assertEqual(
            second["status"],
            "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_already_present",
        )
        self.assertTrue(second["materialized_runtime_args_status_diagnostic_applied"])

    def test_upgrades_existing_real_cuda_patch_with_status_diagnostic(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch import (
            MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC,
            MATERIALIZED_ARGS_PROBE_CALL_OLD,
            patch_real_cuda_materialized_runtime,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._main_with_fake_materialized_runtime(), encoding="utf-8")
            first = patch_real_cuda_materialized_runtime(main_cpp=main_cpp, repo_root=root)
            text_without_diagnostic = main_cpp.read_text(encoding="utf-8").replace(
                MATERIALIZED_ARGS_PROBE_CALL_DIAGNOSTIC,
                MATERIALIZED_ARGS_PROBE_CALL_OLD,
            )
            main_cpp.write_text(text_without_diagnostic, encoding="utf-8")
            upgraded = patch_real_cuda_materialized_runtime(main_cpp=main_cpp, repo_root=root)
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(first["status"], "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_applied")
        self.assertEqual(
            upgraded["status"],
            "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_applied",
        )
        self.assertTrue(upgraded["real_cuda_materialized_runtime_patch_applied"])
        self.assertTrue(upgraded["materialized_runtime_args_status_diagnostic_applied"])
        self.assertIn("rtlmeter_vortex_real_cuda_launch_root_storage_kernel, &root_image,", patched)
        self.assertIn("before_cuMemcpyHtoDRootStorage", patched)
        self.assertIn("relocated_root_image", patched)
        self.assertIn("cuModuleLoad", patched)
        self.assertIn("rtlmeter_vortex_root_storage_kernel_stage", patched)
        self.assertIn("rtlmeter_vortex_runtime_authority authority_report_ready=%d", patched)
        self.assertIn("rtlmeter_vortex_materialized_runtime_args_probe_status=%d", patched)

    def test_missing_or_unsupported_source_fails_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch import (
            patch_real_cuda_materialized_runtime,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = patch_real_cuda_materialized_runtime(main_cpp=root / "obj_dir" / "Vsim__main.cpp", repo_root=root)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text("// unsupported\n", encoding="utf-8")
            unsupported = patch_real_cuda_materialized_runtime(main_cpp=main_cpp, repo_root=root)

        self.assertEqual(missing["status"], "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_missing_source")
        self.assertFalse(missing["real_cuda_materialized_runtime_patch_applied"])
        self.assertEqual(
            unsupported["status"],
            "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch_unsupported_source",
        )
        self.assertIn("include_anchor", unsupported["missing_patch_context"])

    def test_cli_writes_report_without_local_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._main_with_fake_materialized_runtime(), encoding="utf-8")
            out = root / "reports" / "real_cuda_patch.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch.py",
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
        self.assertEqual(report_payload["surface"], "rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
