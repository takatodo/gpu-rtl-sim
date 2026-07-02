import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_observable_authority_audit import build_audit  # noqa: E402


class RtlmeterVortexObservableAuthorityAuditTest(HybridCliTestCase):
    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _write_proxy_and_fake_reports(self, root: Path) -> None:
        self._write_json(
            root / "reports" / "runner.json",
            {
                "status": "rtlmeter_stdout_cycles_sidecar_runner_observables_ready",
                "observables_ready": True,
                "cycle_count": 40897,
                "rtlmeter_proxy_handoff_observed": True,
                "gpu_execution_claimed": False,
                "timing_measured": False,
                "speedup_claimed": False,
            },
        )
        self._write_json(
            root / "reports" / "generated_smoke.json",
            {
                "status": "generated_lowered_tb_invocation_smoke_passed",
                "generated_lowered_tb_invocation_smoke_passed": True,
                "run": {"stdout": "runtime_sequence_called=1\nauthority_passed=1\n"},
            },
        )
        self._write_json(
            root / "reports" / "memory_helper.json",
            {"status": "lowered_tb_memory_helper_integration_smoke_passed"},
        )
        self._write_json(
            root / "reports" / "materialized.json",
            {
                "status": "materialized_runtime_invocation_smoke_ready_not_integrated",
                "smoke_ready": True,
            },
        )
        vsim_main = root / "artifacts" / "obj_dir" / "Vsim__main.cpp"
        vsim_main.parent.mkdir(parents=True, exist_ok=True)
        vsim_main.write_text("int main() { return 0; }\n", encoding="utf-8")

    def test_proxy_and_fake_authority_do_not_claim_real_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertEqual(report["status"], "observable_authority_audit_proxy_and_fake_ready_real_runtime_missing")
        self.assertEqual(report["runner_cycle_count"], 40897)
        self.assertTrue(report["proxy_handoff_observed"])
        self.assertTrue(report["generated_fake_driver_authority_passed"])
        self.assertTrue(report["materialized_runtime_args_ready"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])
        self.assertIn(
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            report["missing_prerequisites"],
        )
        self.assertIn("fake_driver_authority_is_not_real_runtime_authority", report["non_claims"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_real_vsim_main_calls_still_require_gpu_execution_claim_for_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "vortex_mem_access_device_helper();\n"
                "vortex_lowered_tb_invoke_runtime_sequence();\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertTrue(report["real_verilator_memory_helper_call_observed"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])
        self.assertIn("real_runtime_execution_reports_vortex_observable_authority", report["missing_prerequisites"])

    def test_marker_symbols_do_not_count_as_real_runtime_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_BEGIN */\n"
                "/* next_call_boundary=vortex_lowered_tb_invoke_runtime_sequence */\n"
                "/* next_memory_boundary=vortex_mem_access_device_helper */\n"
                "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_END */\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_verilator_runtime_sequence_marker_observed"])
        self.assertTrue(report["real_verilator_lowered_tb_runtime_symbol_observed"])
        self.assertTrue(report["real_verilator_memory_helper_symbol_observed"])
        self.assertTrue(report["probe_or_marker_boundary_observed"])
        self.assertTrue(report["generated_lowered_tb_runtime_call_blocked_by_probe_markers"])
        self.assertTrue(report["generated_lowered_tb_memory_helper_call_blocked_by_probe_markers"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertFalse(report["real_verilator_memory_helper_call_observed"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])
        self.assertEqual(
            report["next_required_boundary"],
            "replace_probe_markers_with_real_generated_lowered_tb_runtime_and_memory_calls",
        )

    def test_generated_dpi_memory_helper_call_counts_separately_from_main_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "dpi_memory_helper_patch.json",
                {
                    "status": "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied",
                    "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_BEGIN */\n"
                "/* next_call_boundary=vortex_lowered_tb_invoke_runtime_sequence */\n"
                "/* next_memory_boundary=vortex_mem_access_device_helper */\n"
                "/* RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_END */\n",
                encoding="utf-8",
            )
            vsim_root = root / "artifacts" / "obj_dir" / "Vsim___024root__0.cpp"
            vsim_root.write_text(
                "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP() {\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */\n"
                "  vortex_mem_access_device_helper();\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */\n"
                "}\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                dpi_memory_helper_patch_report=Path("reports/dpi_memory_helper_patch.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
                vsim_root=Path("artifacts/obj_dir/Vsim___024root__0.cpp"),
            )

        self.assertTrue(report["real_verilator_dpi_memory_helper_call_observed"])
        self.assertTrue(report["real_verilator_memory_helper_call_observed"])
        self.assertTrue(report["generated_lowered_tb_runtime_call_blocked_by_probe_markers"])
        self.assertFalse(report["generated_lowered_tb_memory_helper_call_blocked_by_probe_markers"])
        self.assertIn(
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            report["missing_prerequisites"],
        )
        self.assertNotIn(
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
            report["missing_prerequisites"],
        )
        self.assertEqual(
            report["next_required_boundary"],
            "replace_probe_markers_with_real_generated_lowered_tb_runtime_call",
        )
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_runtime_stub_is_observed_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_RUNTIME_STUB_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_runtime_sequence_hook_stub() { return 0; }\n"
                "/* RTLMETER_VORTEX_RUNTIME_STUB_PATCH_END */\n"
                "/* RTLMETER_VORTEX_RUNTIME_STUB_CALL_BEGIN */\n"
                "(void)rtlmeter_vortex_runtime_sequence_hook_stub();\n"
                "/* RTLMETER_VORTEX_RUNTIME_STUB_CALL_END */\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_verilator_runtime_stub_observed"])
        self.assertFalse(report["real_verilator_runtime_stub_rebuilt"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_runtime_stub_rebuild_is_recorded_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "runtime_stub_rebuild.json",
                {"status": "passed", "returncode": 0},
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_RUNTIME_STUB_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_runtime_sequence_hook_stub() { return 0; }\n"
                "/* RTLMETER_VORTEX_RUNTIME_STUB_PATCH_END */\n"
                "/* RTLMETER_VORTEX_RUNTIME_STUB_CALL_BEGIN */\n"
                "(void)rtlmeter_vortex_runtime_sequence_hook_stub();\n"
                "/* RTLMETER_VORTEX_RUNTIME_STUB_CALL_END */\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                runtime_stub_rebuild_report=Path("reports/runtime_stub_rebuild.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_verilator_runtime_stub_observed"])
        self.assertTrue(report["real_verilator_runtime_stub_rebuilt"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_runtime_bridge_stub_rebuild_is_recorded_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "runtime_bridge_stub_rebuild.json",
                {"status": "passed", "returncode": 0},
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_runtime_bridge_typed_stub() {\n"
                "  VortexLoweredTbRuntimeSummary tb_summary;\n"
                "  vortex_lowered_tb_runtime_summary_clear(&tb_summary);\n"
                "  return tb_summary.runtime_sequence_called;\n"
                "}\n"
                "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_PATCH_END */\n"
                "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_CALL_BEGIN */\n"
                "(void)rtlmeter_vortex_runtime_bridge_typed_stub();\n"
                "/* RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_CALL_END */\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                runtime_bridge_stub_rebuild_report=Path("reports/runtime_bridge_stub_rebuild.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_verilator_runtime_bridge_stub_observed"])
        self.assertTrue(report["real_verilator_runtime_bridge_stub_rebuilt"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_runtime_invocation_probe_rebuild_is_recorded_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "runtime_invocation_probe_rebuild.json",
                {"status": "passed", "returncode": 0},
            )
            self._write_json(
                root / "reports" / "runtime_invocation_probe_execution.json",
                {
                    "status": "passed",
                    "returncode": 0,
                    "expected_fail_probe_executed_without_aborting_before_proxy": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_runtime_invocation_expected_fail_probe() {\n"
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(0, &sequence_summary, &tb_summary);\n"
                "  return result;\n"
                "}\n"
                "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_END */\n"
                "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_CALL_BEGIN */\n"
                "(void)rtlmeter_vortex_runtime_invocation_expected_fail_probe();\n"
                "/* RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_CALL_END */\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                runtime_invocation_probe_rebuild_report=Path("reports/runtime_invocation_probe_rebuild.json"),
                runtime_invocation_probe_execution_report=Path("reports/runtime_invocation_probe_execution.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_verilator_runtime_invocation_probe_observed"])
        self.assertTrue(report["real_verilator_runtime_invocation_probe_rebuilt"])
        self.assertTrue(report["real_verilator_runtime_invocation_probe_executed"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_materialized_runtime_args_probe_is_recorded_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "materialized_args_probe_rebuild.json",
                {"status": "passed", "returncode": 0},
            )
            self._write_json(
                root / "reports" / "materialized_args_probe_execution.json",
                {
                    "status": "passed",
                    "returncode": 0,
                    "materialized_runtime_args_probe_executed_without_aborting_before_proxy": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n"
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
                "  return result;\n"
                "}\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_END */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */\n"
                "(void)rtlmeter_vortex_materialized_runtime_args_probe();\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_END */\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                materialized_runtime_args_probe_rebuild_report=Path(
                    "reports/materialized_args_probe_rebuild.json"
                ),
                materialized_runtime_args_probe_execution_report=Path(
                    "reports/materialized_args_probe_execution.json"
                ),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_verilator_materialized_runtime_args_probe_observed"])
        self.assertTrue(report["real_verilator_materialized_runtime_args_probe_rebuilt"])
        self.assertTrue(report["real_verilator_materialized_runtime_args_probe_executed"])
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_real_cuda_materialized_authority_advances_to_timing_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "real_cuda_materialized_smoke.json",
                {
                    "status": "passed",
                    "returncode": 0,
                    "materialized_runtime_args_probe_passed": True,
                    "proxy_handoff_reached": True,
                    "materialized_runtime_args_probe_status": None,
                    "root_storage_kernel_last_stage": "after_cuCtxSynchronize",
                    "root_storage_kernel_failed_stage": None,
                    "runtime_authority": True,
                    "authority_report_ready": 1,
                    "authority_passed": 1,
                    "authority_source": "memory_post_condition",
                    "observable_export_invoked": 1,
                    "kernel_launch_invoked": 1,
                    "dcr_applied_count": 9,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */\n"
                "VortexCudaUploadDriver upload = {\n"
                "  rtlmeter_vortex_real_cuda_alloc,\n"
                "  rtlmeter_vortex_real_cuda_h2d,\n"
                "  rtlmeter_vortex_real_cuda_memset,\n"
                "  rtlmeter_vortex_real_cuda_free\n"
                "};\n"
                "VortexObservableExportDriver export_driver = {rtlmeter_vortex_real_cuda_d2h};\n"
                "VortexRuntimeSequenceArgs args = {\n"
                "  &upload, buffers, 7, dcr_writes, 9,\n"
                "  rtlmeter_vortex_real_cuda_dcr, 0,\n"
                "  rtlmeter_vortex_real_cuda_launch_root_storage_kernel, &root_image,\n"
                "  &export_driver\n"
                "};\n"
                "VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                real_cuda_materialized_runtime_smoke_report=Path(
                    "reports/real_cuda_materialized_smoke.json"
                ),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_cuda_materialized_runtime_smoke_passed"])
        self.assertTrue(report["real_cuda_materialized_runtime_authority_ready"])
        self.assertEqual(report["real_cuda_materialized_runtime_authority_source"], "memory_post_condition")
        self.assertTrue(report["real_runtime_observable_authority_ready"])
        self.assertNotIn(
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            report["missing_prerequisites"],
        )
        self.assertEqual(report["next_required_boundary"], "run_cpu_vs_hybrid_timing_for_Vortex_mini_hello")

    def test_unmarked_fake_driver_materialized_runtime_args_call_does_not_count_as_real_runtime_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "dpi_memory_helper_patch.json",
                {
                    "status": "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied",
                    "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_alloc(VortexCuDeviceptr* out, size_t bytes) {\n"
                "  return VORTEX_CUDA_SUCCESS;\n"
                "}\n"
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_h2d(VortexCuDeviceptr dst, const void* src, size_t bytes) {\n"
                "  return VORTEX_CUDA_SUCCESS;\n"
                "}\n"
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_kernel(void* user, VortexRuntimeBuffer* buffers, unsigned buffer_count) {\n"
                "  return VORTEX_CUDA_SUCCESS;\n"
                "}\n"
                "static VortexCuResult rtlmeter_vortex_runtime_args_probe_dtoh(void* dst, VortexCuDeviceptr src, size_t bytes) {\n"
                "  return VORTEX_CUDA_SUCCESS;\n"
                "}\n"
                "static int rtlmeter_vortex_materialized_runtime_args_call() {\n"
                "  VortexCudaUploadDriver upload = {\n"
                "    rtlmeter_vortex_runtime_args_probe_alloc,\n"
                "    rtlmeter_vortex_runtime_args_probe_h2d,\n"
                "    rtlmeter_vortex_runtime_args_probe_memset,\n"
                "    rtlmeter_vortex_runtime_args_probe_free\n"
                "  };\n"
                "  VortexRuntimeSequenceArgs args = {\n"
                "    &upload, buffers, 7, dcr_writes, 9,\n"
                "    rtlmeter_vortex_runtime_args_probe_dcr, 0,\n"
                "    rtlmeter_vortex_runtime_args_probe_kernel, 0,\n"
                "    &export_driver\n"
                "  };\n"
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
                "  return result;\n"
                "}\n",
                encoding="utf-8",
            )
            vsim_root = root / "artifacts" / "obj_dir" / "Vsim___024root__0.cpp"
            vsim_root.write_text(
                "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP() {\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */\n"
                "  vortex_mem_access_device_helper();\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */\n"
                "}\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                dpi_memory_helper_patch_report=Path("reports/dpi_memory_helper_patch.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
                vsim_root=Path("artifacts/obj_dir/Vsim___024root__0.cpp"),
            )

        self.assertTrue(report["fake_driver_materialized_runtime_args_call_observed"])
        self.assertTrue(report["real_verilator_lowered_tb_runtime_symbol_observed"])
        self.assertTrue(report["real_verilator_memory_helper_call_observed"])
        self.assertFalse(report["probe_or_marker_boundary_observed"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertEqual(
            report["next_required_boundary"],
            "replace_fake_driver_materialized_runtime_args_call_with_real_generated_lowered_tb_runtime_call",
        )
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_real_cuda_materialized_runtime_args_call_advances_to_root_storage_kernel_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "real_cuda_materialized_smoke.json",
                {
                    "status": "passed",
                    "returncode": 0,
                    "materialized_runtime_args_probe_passed": True,
                    "proxy_handoff_reached": True,
                    "materialized_runtime_args_probe_status": None,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "real_kernel_artifact_preflight.json",
                {
                    "status": "real_vortex_kernel_artifact_missing",
                    "kernel_artifact_ready": False,
                    "cubin_count": 0,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "kernel_artifact_build_attempt.json",
                {
                    "status": "failed_broken_module_landingpad_personality",
                    "landingpad_personality_error_observed": True,
                    "next_required_boundary": "fix_vortex_lowered_ir_landingpad_personality_before_kernel_artifact",
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "dpi_memory_helper_patch.json",
                {
                    "status": "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied",
                    "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n"
                "  VortexCudaUploadDriver upload = {\n"
                "    rtlmeter_vortex_real_cuda_alloc,\n"
                "    rtlmeter_vortex_real_cuda_h2d,\n"
                "    rtlmeter_vortex_real_cuda_memset,\n"
                "    rtlmeter_vortex_real_cuda_free\n"
                "  };\n"
                "  VortexObservableExportDriver export_driver = {rtlmeter_vortex_real_cuda_d2h};\n"
                "  VortexRuntimeSequenceArgs args = {\n"
                "    &upload, buffers, 7, dcr_writes, 9,\n"
                "    rtlmeter_vortex_real_cuda_dcr, 0,\n"
                "    rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0,\n"
                "    &export_driver\n"
                "  };\n"
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
                "  return result;\n"
                "}\n"
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_END */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */\n",
                encoding="utf-8",
            )
            vsim_root = root / "artifacts" / "obj_dir" / "Vsim___024root__0.cpp"
            vsim_root.write_text(
                "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP() {\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */\n"
                "  vortex_mem_access_device_helper();\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */\n"
                "}\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                real_cuda_materialized_runtime_smoke_report=Path(
                    "reports/real_cuda_materialized_smoke.json"
                ),
                real_kernel_artifact_preflight_report=Path(
                    "reports/real_kernel_artifact_preflight.json"
                ),
                kernel_artifact_build_attempt_report=Path(
                    "reports/kernel_artifact_build_attempt.json"
                ),
                dpi_memory_helper_patch_report=Path("reports/dpi_memory_helper_patch.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
                vsim_root=Path("artifacts/obj_dir/Vsim___024root__0.cpp"),
            )

        self.assertTrue(report["real_cuda_materialized_runtime_args_call_observed"])
        self.assertTrue(report["real_cuda_materialized_runtime_smoke_passed"])
        self.assertEqual(report["real_cuda_materialized_runtime_smoke_returncode"], 0)
        self.assertIsNone(report["real_cuda_materialized_runtime_smoke_probe_status"])
        self.assertFalse(report["real_vortex_kernel_artifact_ready"])
        self.assertEqual(report["real_vortex_kernel_artifact_status"], "real_vortex_kernel_artifact_missing")
        self.assertTrue(report["kernel_artifact_build_landingpad_blocked"])
        self.assertEqual(
            report["kernel_artifact_build_attempt_next_required_boundary"],
            "fix_vortex_lowered_ir_landingpad_personality_before_kernel_artifact",
        )
        self.assertTrue(report["real_verilator_materialized_runtime_args_probe_executed"])
        self.assertFalse(report["fake_driver_materialized_runtime_args_call_observed"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertEqual(
            report["next_required_boundary"],
            "fix_vortex_lowered_ir_landingpad_personality_before_kernel_artifact",
        )
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_real_cuda_materialized_runtime_with_kernel_artifact_advances_to_launch_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "real_kernel_artifact_preflight.json",
                {
                    "status": "real_vortex_kernel_artifact_ready",
                    "kernel_artifact_ready": True,
                    "cubin_count": 1,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "dpi_memory_helper_patch.json",
                {
                    "status": "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied",
                    "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n"
                "  VortexCudaUploadDriver upload = {\n"
                "    rtlmeter_vortex_real_cuda_alloc,\n"
                "    rtlmeter_vortex_real_cuda_h2d,\n"
                "    rtlmeter_vortex_real_cuda_memset,\n"
                "    rtlmeter_vortex_real_cuda_free\n"
                "  };\n"
                "  VortexObservableExportDriver export_driver = {rtlmeter_vortex_real_cuda_d2h};\n"
                "  VortexRuntimeSequenceArgs args = {\n"
                "    &upload, buffers, 7, dcr_writes, 9,\n"
                "    rtlmeter_vortex_real_cuda_dcr, 0,\n"
                "    rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0,\n"
                "    &export_driver\n"
                "  };\n"
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
                "  return result;\n"
                "}\n"
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_END */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */\n",
                encoding="utf-8",
            )
            vsim_root = root / "artifacts" / "obj_dir" / "Vsim___024root__0.cpp"
            vsim_root.write_text(
                "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP() {\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */\n"
                "  vortex_mem_access_device_helper();\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */\n"
                "}\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                real_kernel_artifact_preflight_report=Path(
                    "reports/real_kernel_artifact_preflight.json"
                ),
                dpi_memory_helper_patch_report=Path("reports/dpi_memory_helper_patch.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
                vsim_root=Path("artifacts/obj_dir/Vsim___024root__0.cpp"),
            )

        self.assertTrue(report["real_vortex_kernel_artifact_ready"])
        self.assertEqual(
            report["next_required_boundary"],
            "wire_real_vortex_kernel_artifact_into_materialized_runtime_callback",
        )

    def test_kernel_callback_preflight_refines_artifact_ready_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "real_kernel_artifact_preflight.json",
                {
                    "status": "real_vortex_kernel_artifact_ready",
                    "kernel_artifact_ready": True,
                    "ptx_count": 1,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "kernel_callback_preflight.json",
                {
                    "status": "blocked_by_gpu_artifact_prelaunch_rejection",
                    "artifact_ready": True,
                    "callback_wiring_ready": False,
                    "prelaunch_rejection_required": True,
                    "unsafe_syms_gep_count": 3358,
                    "next_required_boundary": (
                        "clear_vortex_gpu_artifact_prelaunch_rejection_or_build_root_syms_storage_launch_abi"
                    ),
                },
            )
            self._write_json(
                root / "reports" / "dpi_memory_helper_patch.json",
                {
                    "status": "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied",
                    "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n"
                "  VortexCudaUploadDriver upload = {\n"
                "    rtlmeter_vortex_real_cuda_alloc,\n"
                "    rtlmeter_vortex_real_cuda_h2d,\n"
                "    rtlmeter_vortex_real_cuda_memset,\n"
                "    rtlmeter_vortex_real_cuda_free\n"
                "  };\n"
                "  VortexObservableExportDriver export_driver = {rtlmeter_vortex_real_cuda_d2h};\n"
                "  VortexRuntimeSequenceArgs args = {\n"
                "    &upload, buffers, 7, dcr_writes, 9,\n"
                "    rtlmeter_vortex_real_cuda_dcr, 0,\n"
                "    rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0,\n"
                "    &export_driver\n"
                "  };\n"
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
                "  return result;\n"
                "}\n"
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_END */\n",
                encoding="utf-8",
            )
            vsim_root = root / "artifacts" / "obj_dir" / "Vsim___024root__0.cpp"
            vsim_root.write_text(
                "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP() {\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */\n"
                "  vortex_mem_access_device_helper();\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */\n"
                "}\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                real_kernel_artifact_preflight_report=Path("reports/real_kernel_artifact_preflight.json"),
                kernel_callback_preflight_report=Path("reports/kernel_callback_preflight.json"),
                dpi_memory_helper_patch_report=Path("reports/dpi_memory_helper_patch.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
                vsim_root=Path("artifacts/obj_dir/Vsim___024root__0.cpp"),
            )

        self.assertEqual(report["kernel_callback_preflight_status"], "blocked_by_gpu_artifact_prelaunch_rejection")
        self.assertFalse(report["kernel_callback_wiring_ready"])
        self.assertTrue(report["kernel_callback_prelaunch_rejection_required"])
        self.assertEqual(report["kernel_callback_unsafe_syms_gep_count"], 3358)
        self.assertIn("real_vortex_kernel_artifact_materialized_callback_wiring", report["missing_prerequisites"])
        self.assertIn("safe_root_or_syms_storage_launch_abi", report["missing_prerequisites"])
        self.assertEqual(
            report["next_required_boundary"],
            "clear_vortex_gpu_artifact_prelaunch_rejection_or_build_root_syms_storage_launch_abi",
        )

    def test_root_storage_kernel_callback_timeout_becomes_next_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "real_cuda_materialized_smoke.json",
                {
                    "status": "failed",
                    "returncode": None,
                    "timed_out": True,
                    "root_storage_kernel_stage_trace": ["before_cuModuleLoad"],
                    "root_storage_kernel_last_stage": "before_cuModuleLoad",
                    "materialized_runtime_args_probe_passed": False,
                    "materialized_runtime_args_probe_status": None,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "real_kernel_artifact_preflight.json",
                {
                    "status": "real_vortex_kernel_artifact_ready",
                    "kernel_artifact_ready": True,
                    "ptx_count": 1,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "kernel_callback_preflight.json",
                {
                    "status": "ready_to_run_real_kernel_callback_smoke",
                    "callback_wiring_ready": True,
                    "root_storage_callback_observed": True,
                    "prelaunch_rejection_required": False,
                    "next_required_boundary": "run_real_vortex_kernel_callback_smoke_and_observable_export",
                },
            )
            self._write_json(
                root / "reports" / "dpi_memory_helper_patch.json",
                {
                    "status": "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied",
                    "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n"
                "  VortexCudaUploadDriver upload = {\n"
                "    rtlmeter_vortex_real_cuda_alloc,\n"
                "    rtlmeter_vortex_real_cuda_h2d,\n"
                "    rtlmeter_vortex_real_cuda_memset,\n"
                "    rtlmeter_vortex_real_cuda_free\n"
                "  };\n"
                "  VortexObservableExportDriver export_driver = {rtlmeter_vortex_real_cuda_d2h};\n"
                "  VortexRuntimeSequenceArgs args = {\n"
                "    &upload, buffers, 7, dcr_writes, 9,\n"
                "    rtlmeter_vortex_real_cuda_dcr, 0,\n"
                "    rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0,\n"
                "    &export_driver\n"
                "  };\n"
                "  VortexCuResult result = vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary);\n"
                "  return result;\n"
                "}\n"
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_END */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN */\n"
                "/* RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN */\n",
                encoding="utf-8",
            )
            vsim_root = root / "artifacts" / "obj_dir" / "Vsim___024root__0.cpp"
            vsim_root.write_text(
                "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP() {\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */\n"
                "  vortex_mem_access_device_helper();\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */\n"
                "}\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                real_cuda_materialized_runtime_smoke_report=Path("reports/real_cuda_materialized_smoke.json"),
                real_cuda_return_before_eval_smoke_report=Path("reports/return_before_eval_smoke.json"),
                real_kernel_artifact_preflight_report=Path("reports/real_kernel_artifact_preflight.json"),
                kernel_callback_preflight_report=Path("reports/kernel_callback_preflight.json"),
                dpi_memory_helper_patch_report=Path("reports/dpi_memory_helper_patch.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
                vsim_root=Path("artifacts/obj_dir/Vsim___024root__0.cpp"),
            )

        self.assertTrue(report["real_cuda_materialized_runtime_smoke_timed_out"])
        self.assertEqual(report["real_cuda_root_storage_kernel_last_stage"], "before_cuModuleLoad")
        self.assertEqual(report["real_cuda_root_storage_kernel_stage_trace"], ["before_cuModuleLoad"])
        self.assertTrue(report["kernel_callback_wiring_ready"])
        self.assertEqual(
            report["next_required_boundary"],
            "debug_real_vortex_ptx_cuModuleLoad_jit_timeout",
        )

    def test_root_storage_kernel_illegal_memory_access_becomes_next_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "real_cuda_materialized_smoke.json",
                {
                    "status": "failed",
                    "returncode": 123,
                    "timed_out": False,
                    "module": "artifacts/slice/vl_eval_batch_gpu.cubin",
                    "root_storage_kernel_stage_trace": [
                        "before_cuModuleLoad",
                        "after_cuModuleLoad",
                        "after_cuModuleGetFunction",
                        "after_cuMemAllocRootStorage",
                        "before_cuMemcpyHtoDRootStorage",
                        "after_cuMemcpyHtoDRootStorage",
                        "before_cuLaunchKernel",
                        "after_cuLaunchKernel",
                    ],
                    "root_storage_kernel_last_stage": "after_cuLaunchKernel",
                    "root_storage_relocation_count": 65,
                    "root_storage_kernel_failure": {"stage": "cuLaunchOrSync", "result": 700},
                    "runtime_sequence_failure": {"stage": "kernel_launch", "result": 700, "index": -1},
                    "runtime_sequence_failed_stage": "kernel_launch",
                    "runtime_sequence_failed_result": 700,
                    "materialized_runtime_args_probe_passed": False,
                    "materialized_runtime_args_probe_status": 30,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "return_before_eval_smoke.json",
                {
                    "status": "passed",
                    "returncode": 0,
                    "module": "artifacts/slice/vl_eval_batch_gpu_return_before_eval.cubin",
                    "root_storage_kernel_stage_trace": [
                        "before_cuModuleLoad",
                        "after_cuModuleLoad",
                        "after_cuModuleGetFunction",
                        "after_cuMemAllocRootStorage",
                        "before_cuMemcpyHtoDRootStorage",
                        "after_cuMemcpyHtoDRootStorage",
                        "before_cuLaunchKernel",
                        "after_cuLaunchKernel",
                        "after_cuCtxSynchronize",
                    ],
                    "root_storage_kernel_last_stage": "after_cuCtxSynchronize",
                    "root_storage_kernel_failed_stage": None,
                    "root_storage_relocation_count": 65,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "all_std_ref_returns_arg_smoke.json",
                {
                    "status": "passed",
                    "returncode": 0,
                    "module": "artifacts/slice/vl_eval_batch_gpu_all_std_ref_returns_arg.cubin",
                    "root_storage_kernel_stage_trace": [
                        "before_cuModuleLoad",
                        "after_cuModuleLoad",
                        "after_cuModuleGetFunction",
                        "after_cuMemAllocRootStorage",
                        "before_cuMemcpyHtoDRootStorage",
                        "after_cuMemcpyHtoDRootStorage",
                        "before_cuLaunchKernel",
                        "after_cuLaunchKernel",
                        "after_cuCtxSynchronize",
                    ],
                    "root_storage_kernel_last_stage": "after_cuCtxSynchronize",
                    "root_storage_kernel_failed_stage": None,
                    "root_storage_relocation_count": 65,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "real_kernel_artifact_preflight.json",
                {
                    "status": "real_vortex_kernel_artifact_ready",
                    "kernel_artifact_ready": True,
                    "ptx_count": 1,
                    "runtime_authority": False,
                },
            )
            self._write_json(
                root / "reports" / "kernel_callback_preflight.json",
                {
                    "status": "ready_to_run_real_kernel_callback_smoke",
                    "callback_wiring_ready": True,
                    "root_storage_callback_observed": True,
                    "prelaunch_rejection_required": False,
                    "next_required_boundary": "run_real_vortex_kernel_callback_smoke_and_observable_export",
                },
            )
            self._write_json(
                root / "reports" / "dpi_memory_helper_patch.json",
                {
                    "status": "rtlmeter_vortex_generated_dpi_memory_helper_patch_applied",
                    "generated_dpi_wrapper_calls_vortex_mem_access_device_helper": True,
                    "runtime_authority": False,
                },
            )
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").parent.mkdir(parents=True, exist_ok=True)
            (root / "artifacts" / "obj_dir" / "Vsim__main.cpp").write_text(
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN */\n"
                "static int rtlmeter_vortex_materialized_runtime_args_probe() {\n"
                "  VortexRuntimeSequenceArgs args = {\n"
                "    &upload, buffers, 7, dcr_writes, 9,\n"
                "    rtlmeter_vortex_real_cuda_dcr, 0,\n"
                "    rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0,\n"
                "    &export_driver\n"
                "  };\n"
                "  return 0;\n"
                "}\n"
                "/* RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_END */\n",
                encoding="utf-8",
            )
            (root / "artifacts" / "obj_dir" / "Vsim___024root__0.cpp").write_text(
                "void Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP() {\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN */\n"
                "  vortex_mem_access_device_helper();\n"
                "  /* RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_END */\n"
                "}\n",
                encoding="utf-8",
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                real_cuda_materialized_runtime_smoke_report=Path("reports/real_cuda_materialized_smoke.json"),
                real_cuda_return_before_eval_smoke_report=Path("reports/return_before_eval_smoke.json"),
                real_cuda_all_std_ref_returns_arg_smoke_report=Path(
                    "reports/all_std_ref_returns_arg_smoke.json"
                ),
                real_kernel_artifact_preflight_report=Path("reports/real_kernel_artifact_preflight.json"),
                kernel_callback_preflight_report=Path("reports/kernel_callback_preflight.json"),
                dpi_memory_helper_patch_report=Path("reports/dpi_memory_helper_patch.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
                vsim_root=Path("artifacts/obj_dir/Vsim___024root__0.cpp"),
            )

        self.assertEqual(report["real_cuda_root_storage_kernel_last_stage"], "after_cuLaunchKernel")
        self.assertEqual(report["real_cuda_root_storage_relocation_count"], 65)
        self.assertEqual(report["real_cuda_materialized_runtime_smoke_module"], "artifacts/slice/vl_eval_batch_gpu.cubin")
        self.assertTrue(report["real_cuda_return_before_eval_smoke_passed"])
        self.assertEqual(
            report["real_cuda_return_before_eval_smoke_module"],
            "artifacts/slice/vl_eval_batch_gpu_return_before_eval.cubin",
        )
        self.assertEqual(report["real_cuda_return_before_eval_root_storage_relocation_count"], 65)
        self.assertTrue(report["real_cuda_all_std_ref_returns_arg_smoke_passed"])
        self.assertEqual(
            report["real_cuda_all_std_ref_returns_arg_smoke_module"],
            "artifacts/slice/vl_eval_batch_gpu_all_std_ref_returns_arg.cubin",
        )
        self.assertEqual(report["real_cuda_all_std_ref_returns_arg_root_storage_relocation_count"], 65)
        self.assertEqual(report["real_cuda_root_storage_kernel_failed_stage"], "cuLaunchOrSync")
        self.assertEqual(report["real_cuda_root_storage_kernel_failed_result"], 700)
        self.assertEqual(
            report["next_required_boundary"],
            "promote_vortex_std_ref_device_lowering_fix_and_run_observable_authority",
        )

    def test_canonical_std_ref_fix_smoke_advances_to_observable_authority_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "real_cuda_materialized_smoke.json",
                {
                    "status": "failed",
                    "returncode": 123,
                    "timed_out": False,
                    "root_storage_kernel_last_stage": "after_cuLaunchKernel",
                    "root_storage_relocation_count": 65,
                    "root_storage_kernel_failure": {"stage": "cuLaunchOrSync", "result": 700},
                    "runtime_sequence_failure": {"stage": "kernel_launch", "result": 700, "index": -1},
                    "materialized_runtime_args_probe_passed": False,
                    "runtime_authority": False,
                },
            )
            for name, module in [
                ("return_before_eval_smoke", "artifacts/slice/vl_eval_batch_gpu_return_before_eval.cubin"),
                ("all_std_ref_returns_arg_smoke", "artifacts/slice/vl_eval_batch_gpu_all_std_ref_returns_arg.cubin"),
                ("canonical_std_ref_fix_smoke", "artifacts/slice/vl_eval_batch_gpu_canonical_std_ref_fix.cubin"),
            ]:
                self._write_json(
                    root / "reports" / f"{name}.json",
                    {
                        "status": "passed",
                        "returncode": 0,
                        "module": module,
                        "root_storage_kernel_last_stage": "after_cuCtxSynchronize",
                        "root_storage_kernel_failed_stage": None,
                        "root_storage_relocation_count": 65,
                        "runtime_authority": False,
                    },
                )
            self._write_json(
                root / "reports" / "kernel_callback_preflight.json",
                {
                    "status": "ready_to_run_real_kernel_callback_smoke",
                    "callback_wiring_ready": True,
                    "prelaunch_rejection_required": False,
                },
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                real_cuda_materialized_runtime_smoke_report=Path("reports/real_cuda_materialized_smoke.json"),
                real_cuda_return_before_eval_smoke_report=Path("reports/return_before_eval_smoke.json"),
                real_cuda_all_std_ref_returns_arg_smoke_report=Path(
                    "reports/all_std_ref_returns_arg_smoke.json"
                ),
                real_cuda_canonical_std_ref_fix_smoke_report=Path(
                    "reports/canonical_std_ref_fix_smoke.json"
                ),
                kernel_callback_preflight_report=Path("reports/kernel_callback_preflight.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_cuda_canonical_std_ref_fix_smoke_passed"])
        self.assertEqual(
            report["real_cuda_canonical_std_ref_fix_smoke_module"],
            "artifacts/slice/vl_eval_batch_gpu_canonical_std_ref_fix.cubin",
        )
        self.assertEqual(report["real_cuda_canonical_std_ref_fix_root_storage_relocation_count"], 65)
        self.assertEqual(
            report["next_required_boundary"],
            "execute_real_vortex_gpu_runtime_and_export_authority",
        )

    def test_real_cuda_memory_transport_is_recorded_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "cuda_memory_transport.json",
                {
                    "status": "passed",
                    "real_cuda_driver_api_invoked": True,
                    "real_cuda_memory_transport_passed": True,
                    "host_to_device_bytes": 37224,
                    "device_to_host_initial_bytes": 88,
                    "runtime_authority": False,
                },
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                cuda_memory_transport_preflight_report=Path("reports/cuda_memory_transport.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_cuda_memory_transport_passed"])
        self.assertEqual(report["real_cuda_memory_transport_h2d_bytes"], 37224)
        self.assertEqual(report["real_cuda_memory_transport_d2h_initial_bytes"], 88)
        self.assertFalse(report["real_runtime_observable_authority_ready"])

    def test_real_cuda_runtime_sequence_preflight_is_recorded_without_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            self._write_json(
                root / "reports" / "cuda_runtime_sequence.json",
                {
                    "status": "passed",
                    "real_cuda_driver_api_invoked": True,
                    "real_cuda_runtime_sequence_preflight_passed": True,
                    "runtime_sequence_called": True,
                    "runtime_sequence_passed": True,
                    "kernel_callback_invoked": True,
                    "observable_export_invoked": True,
                    "preflight_authority_report_ready": True,
                    "preflight_authority_passed": True,
                    "preflight_authority_source": "memory_post_condition",
                    "host_to_device_bytes": 37224,
                    "device_to_host_initial_bytes": 88,
                    "dcr_applied_count": 9,
                    "runtime_authority": False,
                },
            )

            report = build_audit(
                root,
                runner_report=Path("reports/runner.json"),
                generated_smoke_report=Path("reports/generated_smoke.json"),
                memory_helper_smoke_report=Path("reports/memory_helper.json"),
                materialized_smoke_report=Path("reports/materialized.json"),
                cuda_runtime_sequence_preflight_report=Path("reports/cuda_runtime_sequence.json"),
                vsim_main=Path("artifacts/obj_dir/Vsim__main.cpp"),
            )

        self.assertTrue(report["real_cuda_runtime_sequence_preflight_passed"])
        self.assertEqual(report["real_cuda_runtime_sequence_preflight_h2d_bytes"], 37224)
        self.assertEqual(report["real_cuda_runtime_sequence_preflight_d2h_initial_bytes"], 88)
        self.assertEqual(report["real_cuda_runtime_sequence_preflight_dcr_applied_count"], 9)
        self.assertTrue(report["real_cuda_preflight_authority_report_ready"])
        self.assertTrue(report["real_cuda_preflight_authority_passed"])
        self.assertEqual(report["real_cuda_preflight_authority_source"], "memory_post_condition")
        self.assertFalse(report["real_runtime_observable_authority_ready"])
        self.assertIn("cuda_runtime_sequence_preflight_is_not_vortex_kernel_execution", report["non_claims"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_proxy_and_fake_reports(root)
            out = root / "reports" / "audit.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_observable_authority_audit.py",
                "--repo-root",
                root.as_posix(),
                "--runner-report",
                "reports/runner.json",
                "--generated-smoke-report",
                "reports/generated_smoke.json",
                "--memory-helper-smoke-report",
                "reports/memory_helper.json",
                "--materialized-smoke-report",
                "reports/materialized.json",
                "--vsim-main",
                "artifacts/obj_dir/Vsim__main.cpp",
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_observable_authority_audit")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
