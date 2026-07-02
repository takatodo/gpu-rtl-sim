import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVsimMainVortexMaterializedRuntimeArgsProbePatchTest(HybridCliTestCase):
    def _generated_main(self) -> str:
        return "\n".join(
            [
                "// DESCRIPTION: Verilator output: main() simulation loop, created with --main",
                '#include "verilated.h"',
                '#include "Vsim.h"',
                "",
                "typedef int VortexCuResult;",
                "typedef unsigned long VortexCuDeviceptr;",
                "typedef struct { int mismatch_count; } VortexPostCompareResult;",
                "typedef struct { const char *failed_stage; unsigned dcr_applied_count; int kernel_launch_invoked; int observable_export_invoked; int buffers_released; } VortexRuntimeSequenceSummary;",
                "typedef struct { int runtime_sequence_called; int runtime_sequence_passed; int authority_report_ready; int authority_passed; } VortexLoweredTbRuntimeSummary;",
                "typedef struct { int addr; int value; } VortexDcrWrite;",
                "typedef struct { const char *name; const void *host_data; unsigned bytes; int direction; unsigned char initial_value; VortexCuDeviceptr device_ptr; } VortexRuntimeBuffer;",
                "typedef struct { void *a; void *b; void *c; void *d; } VortexCudaUploadDriver;",
                "typedef struct { void *a; } VortexObservableExportDriver;",
                "typedef struct { const VortexCudaUploadDriver *upload_driver; VortexRuntimeBuffer *buffers; unsigned buffer_count; const VortexDcrWrite *dcr_writes; unsigned dcr_write_count; void *apply_dcr; void *dcr_user; void *launch_kernel; void *kernel_user; const VortexObservableExportDriver *export_driver; } VortexRuntimeSequenceArgs;",
                "static inline VortexCuResult vortex_lowered_tb_invoke_runtime_sequence(const VortexRuntimeSequenceArgs *, VortexRuntimeSequenceSummary *, VortexLoweredTbRuntimeSummary *) { return 0; }",
                '#include "../../../../../../../src/hybrid/vortex_lowered_tb_runtime_sequence.h"',
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

    def _write_artifacts(self, root: Path) -> None:
        from rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch import BUFFER_SPECS

        for spec in BUFFER_SPECS:
            path = root / spec.rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes([0]) * spec.bytes_)

    def test_patches_generated_main_with_materialized_runtime_args_probe(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch import (
            PATCH_BEGIN,
            patch_vortex_materialized_runtime_args_probe,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            self._write_artifacts(root)
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            report = patch_vortex_materialized_runtime_args_probe(
                main_cpp=main_cpp,
                repo_root=root,
                repo_root_relative_from_obj_dir="..",
            )
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(
            report["status"],
            "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_applied",
        )
        self.assertTrue(report["materialized_runtime_args_probe_applied"])
        self.assertFalse(report["runtime_authority"])
        self.assertEqual(report["buffer_count"], 7)
        self.assertEqual(report["host_to_device_bytes"], 37224)
        self.assertEqual(report["device_to_host_initial_bytes"], 88)
        self.assertIn(PATCH_BEGIN, patched)
        self.assertIn("VortexRuntimeSequenceArgs args = {", patched)
        self.assertIn("vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary)", patched)
        self.assertIn("if (rtlmeter_vortex_materialized_runtime_args_probe() != 0) return 123;", patched)

    def test_materialized_runtime_args_probe_patch_is_idempotent(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch import (
            PATCH_BEGIN,
            patch_vortex_materialized_runtime_args_probe,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            self._write_artifacts(root)
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            first = patch_vortex_materialized_runtime_args_probe(
                main_cpp=main_cpp,
                repo_root=root,
                repo_root_relative_from_obj_dir="..",
            )
            second = patch_vortex_materialized_runtime_args_probe(
                main_cpp=main_cpp,
                repo_root=root,
                repo_root_relative_from_obj_dir="..",
            )
            patched = main_cpp.read_text(encoding="utf-8")

        self.assertEqual(first["status"], "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_applied")
        self.assertEqual(
            second["status"],
            "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_already_present",
        )
        self.assertEqual(patched.count(PATCH_BEGIN), 1)

    def test_missing_artifacts_or_source_fail_closed(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch import (
            patch_vortex_materialized_runtime_args_probe,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = patch_vortex_materialized_runtime_args_probe(
                main_cpp=root / "obj_dir" / "Vsim__main.cpp",
                repo_root=root,
                repo_root_relative_from_obj_dir="..",
            )
            main_cpp = root / "obj_dir" / "Vsim__main.cpp"
            main_cpp.parent.mkdir()
            main_cpp.write_text(self._generated_main(), encoding="utf-8")
            missing_artifacts = patch_vortex_materialized_runtime_args_probe(
                main_cpp=main_cpp,
                repo_root=root,
                repo_root_relative_from_obj_dir="..",
            )

        self.assertEqual(
            missing["status"],
            "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_missing_source",
        )
        self.assertFalse(missing["materialized_runtime_args_probe_applied"])
        self.assertEqual(
            missing_artifacts["status"],
            "rtlmeter_vsim_main_vortex_materialized_runtime_args_probe_patch_unsupported_source",
        )
        self.assertIn("artifact.vortex_init_segment_table", missing_artifacts["missing_patch_context"])
        self.assertFalse(missing_artifacts["materialized_runtime_args_probe_applied"])


if __name__ == "__main__":
    import unittest

    unittest.main()
