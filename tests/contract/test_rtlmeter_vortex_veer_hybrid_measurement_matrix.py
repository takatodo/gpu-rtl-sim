import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_veer_hybrid_measurement_matrix import build_matrix  # noqa: E402


class RtlmeterVortexVeerHybridMeasurementMatrixTest(HybridCliTestCase):
    def _write_descriptor(self, root: Path, design: str, *, cpp: bool = False) -> None:
        path = root / "third_party" / "rtlmeter" / "designs" / design / "descriptor.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        cpp_section = "\n  cppSourceFiles:\n    - src/dpi.cpp" if cpp else ""
        path.write_text(
            "\n".join(
                [
                    "compile:",
                    "  verilogSourceFiles:",
                    "    - src/tb_top.sv",
                    "  verilogIncludeFiles:",
                    "    - src/defs.vh",
                    cpp_section.rstrip(),
                    "  topModule: tb_top",
                    "  mainClock: tb_top.core_clk",
                    "execute:",
                    "  tests:",
                    "    hello:",
                    "      files:",
                    "        - tests/hello/program.hex",
                    "configurations:",
                    "  default:",
                    "    execute:",
                    "      tests:",
                    "        hello:",
                    "          tags: [ sanity ]",
                    "  mini:",
                    "    execute:",
                    "      tests:",
                    "        hello:",
                    "          tags: [ sanity ]",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_matrix_keeps_unmeasured_targets_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("Vortex", "VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design, cpp=design == "Vortex")
            self._write_json(
                root / "reports" / "rtlmeter_vortex_first_gate_readiness.json",
                {
                    "status": "blocked_missing_first_gate",
                    "missing_prerequisites": [
                        "reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
                        "cpu_vs_hybrid_timing_report.vortex",
                    ],
                    "recommended_sequence": [
                        "provide_reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
                        "connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence",
                    ],
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_vortex_dpi_memory_bridge_review.json",
                {
                    "status": "reviewed_blocked_on_gpu_bridge_implementation",
                    "missing_prerequisites": ["lowered_tb_mem_access_device_helper_integration"],
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_vortex_cpu_reference_summary.json",
                {
                    "status": "cpu_reference_passed",
                    "cpu_reference_ready_for_hybrid_compare": True,
                    "stdout_test_passed": True,
                    "metrics": {
                        "execute_elapsed_s": 0.22,
                        "execute_speed_khz": 185.89545454545453,
                        "execute_clocks": 40897,
                    },
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_vortex_hybrid_candidate_summary.json",
                {
                    "status": "hybrid_candidate_stdout_cycles_observed_proxy_handoff_blocked",
                    "invalid_sim_accel_option": False,
                    "wrapper_captured_sidecar_planning": True,
                    "wrapper_runtime_status": "rtlmeter_sidecar_execution_handoff_blocked_sidecar_verilate_execution",
                    "wrapper_inspection_status": "ready_for_rtlmeter_sidecar_planning",
                    "wrapper_sidecar_accel": "sidecar-gpu",
                    "wrapper_sidecar_states": "1",
                    "wrapper_sidecar_steps": "1",
                    "blocked_missing_reviewed_source_closure": False,
                    "blocked_missing_authority_registry_source_closure": False,
                    "blocked_sidecar_verilate_execution": True,
                    "handoff_metadata_ready": True,
                    "stdout_cycles_plan_seed": "Vortex:mini:hello",
                    "stdout_cycles_plan_authority_registry": (
                        "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json"
                    ),
                    "runner_contract_status": "rtlmeter_stdout_cycles_runner_contract_ready",
                    "runner_command_ready": True,
                    "runner_report_status": "rtlmeter_stdout_cycles_sidecar_runner_observables_ready",
                    "runner_observables_ready": True,
                    "runner_cycle_count": 40897,
                    "runner_proxy_handoff_observed": False,
                    "runner_gpu_execution_claimed": False,
                    "adapter_implementation_status": (
                        "rtlmeter_stdout_cycles_runner_adapter_implementation_runner_argv_ready"
                    ),
                    "reentry_guard_status": "rtlmeter_wrapper_reentry_guard_blocked_recursive_rtlmeter_run",
                    "sidecar_execution_invoked": False,
                    "hybrid_candidate_executed": False,
                    "measurement_ready": False,
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_vortex_ptx_module_load_diagnostic.json",
                {
                    "status": "ptxas_timeout",
                    "ptx_bytes": 25830851,
                    "ptx_lines": 1005601,
                    "entry_count": 13,
                    "func_count": 1081,
                    "ptxas_status": "ptxas_timeout",
                    "ptxas_timed_out": True,
                    "next_required_boundary": "split_or_precompile_vortex_ptx_before_cuModuleLoad_retry",
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json",
                {
                    "status": "passed",
                    "speedup_claimed": False,
                    "summary": {
                        "all_sidecar_samples_passed_correctness": True,
                        "sidecar_parallel_state_count": 16,
                        "sidecar_wall_s_median": 0.641226,
                        "gpu_kernel_ms_total_median": 262.026245,
                        "cpu_parallel_wall_s": 2.218887,
                        "sidecar_vs_cpu_parallel_ratio": 3.460382,
                    },
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_el2_sidecar_bridge.json",
                {"status": "verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed"},
            )

            report = build_matrix(root)

        rows = {row["case"]: row for row in report["rows"]}
        self.assertEqual(report["status"], "incomplete")
        self.assertFalse(report["summary"]["goal_complete"])
        self.assertEqual(report["summary"]["vortex_runner_cycle_count"], 40897)
        self.assertFalse(report["summary"]["vortex_runner_proxy_handoff_observed"])
        self.assertFalse(report["summary"]["vortex_runner_gpu_execution_claimed"])
        self.assertEqual(rows["Vortex:mini:hello"]["measurement_status"], "blocked_before_hybrid_measurement")
        self.assertTrue(rows["Vortex:mini:hello"]["cpu_reference_ready"])
        self.assertEqual(rows["Vortex:mini:hello"]["cpu_reference"]["execute_elapsed_s"], 0.22)
        self.assertIn(
            "cpu_vs_hybrid_timing_report.vortex",
            rows["Vortex:mini:hello"]["missing_prerequisites"],
        )
        self.assertIn(
            "reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
            rows["Vortex:mini:hello"]["missing_prerequisites"],
        )
        self.assertEqual(
            rows["Vortex:mini:hello"]["next_action"],
            "provide_reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
        )
        self.assertTrue(rows["Vortex:mini:hello"]["hybrid_candidate"]["wrapper_captured_sidecar_planning"])
        self.assertTrue(rows["Vortex:mini:hello"]["hybrid_candidate"]["handoff_metadata_ready"])
        self.assertEqual(rows["Vortex:mini:hello"]["hybrid_candidate"]["stdout_cycles_plan_seed"], "Vortex:mini:hello")
        self.assertTrue(rows["Vortex:mini:hello"]["hybrid_candidate"]["runner_command_ready"])
        self.assertTrue(rows["Vortex:mini:hello"]["hybrid_candidate"]["runner_observables_ready"])
        self.assertEqual(rows["Vortex:mini:hello"]["hybrid_candidate"]["runner_cycle_count"], 40897)
        self.assertEqual(
            rows["Vortex:mini:hello"]["hybrid_candidate"]["ptx_module_load_ptxas_status"],
            "ptxas_timeout",
        )
        self.assertEqual(
            rows["Vortex:mini:hello"]["hybrid_candidate"]["ptx_module_load_ptx_lines"],
            1005601,
        )
        self.assertFalse(rows["Vortex:mini:hello"]["hybrid_candidate"]["runner_proxy_handoff_observed"])
        self.assertFalse(rows["Vortex:mini:hello"]["hybrid_candidate"]["runner_gpu_execution_claimed"])
        self.assertEqual(rows["Vortex:mini:hello"]["hybrid_candidate"]["wrapper_sidecar_accel"], "sidecar-gpu")
        self.assertEqual(rows["VeeR-EH1:default:hello"]["measurement_status"], "design_present_hybrid_surface_missing")
        self.assertEqual(rows["VeeR-EH2:default:hello"]["measurement_status"], "design_present_hybrid_surface_missing")
        self.assertEqual(rows["VeeR-EL2:default:hello"]["measurement_status"], "hybrid_measured")
        self.assertEqual(
            rows["VeeR-EL2:default:hello"]["best_timing_report"]["report"],
            "reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json",
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_writes_report_and_markdown_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("Vortex", "VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design, cpp=design == "Vortex")
            out = root / "reports" / "matrix.json"
            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_veer_hybrid_measurement_matrix.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
                "--markdown",
            )
            payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertIn("| Target | Hybrid status | Observed evidence | GPU/timing claim |", result.stdout)
        self.assertEqual(payload["summary"]["target_count"], 4)
        self.assertFalse(payload["summary"]["goal_complete"])
        self.assert_no_local_absolute_paths(result.stdout)

    def test_markdown_surfaces_vortex_proxy_handoff_without_gpu_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("Vortex", "VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design, cpp=design == "Vortex")
            self._write_json(
                root / "reports" / "rtlmeter_vortex_first_gate_readiness.json",
                {
                    "status": "blocked_missing_first_gate",
                    "missing_prerequisites": [
                        "cpu_vs_hybrid_timing_report.vortex",
                        "hybrid_observable_authority",
                    ],
                    "recommended_sequence": ["invoke_vortex_observable_export_and_report_authority"],
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_vortex_dpi_memory_bridge_review.json",
                {"status": "reviewed", "missing_prerequisites": []},
            )
            self._write_json(
                root / "reports" / "rtlmeter_vortex_cpu_reference_summary.json",
                {
                    "status": "cpu_reference_passed",
                    "cpu_reference_ready_for_hybrid_compare": True,
                    "stdout_test_passed": True,
                    "metrics": {"execute_elapsed_s": 0.22, "execute_clocks": 40897},
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_vortex_hybrid_candidate_summary.json",
                {
                    "status": "hybrid_candidate_proxy_handoff_observed_timing_missing",
                    "runner_report_status": "rtlmeter_stdout_cycles_sidecar_runner_observables_ready",
                    "runner_observables_ready": True,
                    "runner_cycle_count": 40897,
                    "runner_proxy_handoff_observed": True,
                    "runner_gpu_execution_claimed": False,
                    "real_verilator_dpi_memory_helper_call_observed": True,
                    "real_verilator_memory_helper_call_observed": True,
                    "real_verilator_runtime_bridge_stub_observed": True,
                    "real_verilator_runtime_bridge_stub_rebuilt": True,
                    "real_verilator_runtime_invocation_probe_observed": True,
                    "real_verilator_runtime_invocation_probe_rebuilt": True,
                    "real_verilator_runtime_invocation_probe_executed": True,
                    "real_verilator_materialized_runtime_args_probe_observed": True,
                    "real_verilator_materialized_runtime_args_probe_rebuilt": True,
                    "real_verilator_materialized_runtime_args_probe_executed": True,
                    "real_cuda_materialized_runtime_smoke_passed": True,
                    "real_cuda_materialized_runtime_smoke_returncode": 0,
                    "real_cuda_materialized_runtime_smoke_probe_status": None,
                    "real_cuda_root_storage_kernel_stage_trace": [
                        "before_cuMemcpyHtoDRootStorage",
                        "after_cuMemcpyHtoDRootStorage",
                        "after_cuLaunchKernel",
                    ],
                    "real_cuda_root_storage_kernel_last_stage": "after_cuLaunchKernel",
                    "real_cuda_root_storage_relocation_count": 42,
                    "real_cuda_root_storage_kernel_failed_stage": "cuLaunchOrSync",
                    "real_cuda_root_storage_kernel_failed_result": 700,
                    "real_vortex_kernel_artifact_ready": False,
                    "real_vortex_kernel_artifact_status": "real_vortex_kernel_artifact_missing",
                    "real_vortex_kernel_artifact_count": 0,
                    "kernel_artifact_build_attempt_status": "failed_broken_module_landingpad_personality",
                    "kernel_artifact_build_landingpad_blocked": True,
                    "fake_driver_materialized_runtime_args_call_observed": True,
                    "real_cuda_materialized_runtime_args_call_observed": False,
                    "real_cuda_memory_transport_passed": True,
                    "real_cuda_memory_transport_h2d_bytes": 37224,
                    "real_cuda_memory_transport_d2h_initial_bytes": 88,
                    "real_cuda_runtime_sequence_preflight_passed": True,
                    "real_cuda_runtime_sequence_preflight_h2d_bytes": 37224,
                    "real_cuda_runtime_sequence_preflight_d2h_initial_bytes": 88,
                    "real_cuda_runtime_sequence_preflight_dcr_applied_count": 9,
                    "real_cuda_preflight_authority_report_ready": True,
                    "real_cuda_preflight_authority_passed": True,
                    "real_cuda_preflight_authority_source": "memory_post_condition",
                    "probe_or_marker_boundary_observed": True,
                    "generated_lowered_tb_runtime_call_blocked_by_probe_markers": True,
                    "generated_lowered_tb_memory_helper_call_blocked_by_probe_markers": True,
                    "next_required_boundary": (
                        "replace_probe_markers_with_real_generated_lowered_tb_runtime_and_memory_calls"
                    ),
                    "sidecar_execution_invoked": False,
                    "hybrid_candidate_executed": False,
                    "measurement_ready": False,
                },
            )

            report = build_matrix(root)
            out = self.run_python_tool(
                "src/tools/rtlmeter_vortex_veer_hybrid_measurement_matrix.py",
                "--repo-root",
                root.as_posix(),
                "--markdown",
            )

        vortex = {row["case"]: row for row in report["rows"]}["Vortex:mini:hello"]
        self.assertTrue(report["summary"]["vortex_runner_proxy_handoff_observed"])
        self.assertTrue(report["summary"]["vortex_real_verilator_memory_helper_call_observed"])
        self.assertTrue(report["summary"]["vortex_real_verilator_dpi_memory_helper_call_observed"])
        self.assertTrue(report["summary"]["vortex_real_verilator_runtime_bridge_stub_observed"])
        self.assertTrue(report["summary"]["vortex_real_verilator_runtime_bridge_stub_rebuilt"])
        self.assertTrue(report["summary"]["vortex_real_verilator_runtime_invocation_probe_observed"])
        self.assertTrue(report["summary"]["vortex_real_verilator_runtime_invocation_probe_rebuilt"])
        self.assertTrue(report["summary"]["vortex_real_verilator_runtime_invocation_probe_executed"])
        self.assertTrue(report["summary"]["vortex_real_verilator_materialized_runtime_args_probe_observed"])
        self.assertTrue(report["summary"]["vortex_real_verilator_materialized_runtime_args_probe_rebuilt"])
        self.assertTrue(report["summary"]["vortex_real_verilator_materialized_runtime_args_probe_executed"])
        self.assertTrue(report["summary"]["vortex_real_cuda_materialized_runtime_smoke_passed"])
        self.assertEqual(report["summary"]["vortex_real_cuda_materialized_runtime_smoke_returncode"], 0)
        self.assertIsNone(report["summary"]["vortex_real_cuda_materialized_runtime_smoke_probe_status"])
        self.assertEqual(
            vortex["real_cuda_root_storage_kernel_stage_trace"],
            [
                "before_cuMemcpyHtoDRootStorage",
                "after_cuMemcpyHtoDRootStorage",
                "after_cuLaunchKernel",
            ],
        )
        self.assertEqual(vortex["real_cuda_root_storage_kernel_failed_stage"], "cuLaunchOrSync")
        self.assertEqual(vortex["real_cuda_root_storage_kernel_failed_result"], 700)
        self.assertEqual(vortex["real_cuda_root_storage_relocation_count"], 42)
        self.assertEqual(
            report["summary"]["vortex_real_cuda_root_storage_kernel_stage_trace"],
            [
                "before_cuMemcpyHtoDRootStorage",
                "after_cuMemcpyHtoDRootStorage",
                "after_cuLaunchKernel",
            ],
        )
        self.assertEqual(report["summary"]["vortex_real_cuda_root_storage_relocation_count"], 42)
        self.assertFalse(report["summary"]["vortex_real_vortex_kernel_artifact_ready"])
        self.assertEqual(report["summary"]["vortex_real_vortex_kernel_artifact_status"], "real_vortex_kernel_artifact_missing")
        self.assertEqual(report["summary"]["vortex_real_vortex_kernel_artifact_count"], 0)
        self.assertEqual(
            report["summary"]["vortex_kernel_artifact_build_attempt_status"],
            "failed_broken_module_landingpad_personality",
        )
        self.assertTrue(report["summary"]["vortex_kernel_artifact_build_landingpad_blocked"])
        self.assertTrue(report["summary"]["vortex_fake_driver_materialized_runtime_args_call_observed"])
        self.assertFalse(report["summary"]["vortex_real_cuda_materialized_runtime_args_call_observed"])
        self.assertTrue(report["summary"]["vortex_real_cuda_memory_transport_passed"])
        self.assertTrue(report["summary"]["vortex_real_cuda_runtime_sequence_preflight_passed"])
        self.assertTrue(report["summary"]["vortex_real_cuda_preflight_authority_report_ready"])
        self.assertTrue(report["summary"]["vortex_real_cuda_preflight_authority_passed"])
        self.assertEqual(report["summary"]["vortex_real_cuda_preflight_authority_source"], "memory_post_condition")
        self.assertTrue(report["summary"]["vortex_probe_or_marker_boundary_observed"])
        self.assertTrue(report["summary"]["vortex_generated_lowered_tb_runtime_call_blocked_by_probe_markers"])
        self.assertTrue(report["summary"]["vortex_generated_lowered_tb_memory_helper_call_blocked_by_probe_markers"])
        self.assertEqual(
            report["summary"]["vortex_next_required_boundary"],
            "replace_probe_markers_with_real_generated_lowered_tb_runtime_and_memory_calls",
        )
        self.assertEqual(report["summary"]["vortex_runner_cycle_count"], 40897)
        self.assertFalse(report["summary"]["vortex_runner_gpu_execution_claimed"])
        self.assertIn("hybrid_observable_authority", vortex["missing_prerequisites"])
        self.assertIn("cycles=40897", out.stdout)
        self.assertIn("proxy_handoff=true", out.stdout)
        self.assertIn("runtime_bridge_stub_rebuilt=true", out.stdout)
        self.assertIn("runtime_invocation_probe_rebuilt=true", out.stdout)
        self.assertIn("cuda_runtime_sequence_preflight=true", out.stdout)
        self.assertIn("dpi_memory_helper=true", out.stdout)
        self.assertIn("preflight_authority=true:memory_post_condition", out.stdout)
        self.assertIn("probe_marker_block=true", out.stdout)
        self.assertIn("runtime_invocation_probe_executed=true", out.stdout)
        self.assertIn("materialized_runtime_args_probe_executed=true", out.stdout)
        self.assertIn("real_cuda_materialized_smoke=true", out.stdout)
        self.assertIn("real_vortex_kernel_artifact=false", out.stdout)
        self.assertIn("kernel_build_landingpad_block=true", out.stdout)
        self.assertIn("fake_driver_materialized_args_call=true", out.stdout)
        self.assertNotIn("real_cuda_materialized_args_call=true", out.stdout)
        self.assertIn("cuda_memory_transport=true", out.stdout)
        self.assertIn("gpu=False", out.stdout)

    def test_matrix_uses_veer_family_surface_audit_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("Vortex", "VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design, cpp=design == "Vortex")
            self._write_json(
                root / "reports" / "rtlmeter_veer_family_surface_audit.json",
                {
                    "surface": "rtlmeter_veer_family_surface_audit",
                    "rows": [
                        {
                            "design": "VeeR-EH1",
                            "status": "portable_descriptor_ready_surface_missing",
                            "ready_to_port_from_descriptor": True,
                            "missing_surface": [
                                "authority",
                                "state_layout_report",
                                "state_image_report",
                                "sidecar_bridge_report",
                                "timing_report",
                            ],
                            "direct_el2_reuse_blockers": [
                                "el2_state_layout_and_root_symbol_paths_are_fixed",
                                "hello_program_sha256_differs_from_el2",
                            ],
                            "testbench_surface": {"program_sha256_matches_el2": False},
                            "next_action": (
                                "create_design_specific_authority_state_layout_state_image_bridge_and_timing"
                            ),
                        },
                        {
                            "design": "VeeR-EH2",
                            "status": "sidecar_bridge_preflight_surface_missing",
                            "ready_to_port_from_descriptor": True,
                            "missing_surface": ["timing_report"],
                            "direct_el2_reuse_blockers": ["wrapper_instance_differs_from_el2_rvtop_wrapper"],
                            "testbench_surface": {"program_sha256_matches_el2": False},
                            "next_action": "review_sidecar_executable_and_run_timing",
                        },
                    ],
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_eh2_state_layout_inspection.json",
                {
                    "surface": "rtlmeter_veer_family_state_layout_preflight",
                    "state_layout_ready": False,
                    "missing_build_context": ["reviewed_root_field_offsets"],
                    "detected_layout": {
                        "root_header_probe": {
                            "root_header_observed": True,
                            "root_layout_probe_performed": True,
                            "root_offset_probe_performed": True,
                            "root_offset_probe_error": None,
                            "observed_marker_group_count": 4,
                            "mapped_marker_offset_group_count": 3,
                            "missing_marker_groups": ["cycle_counters"],
                            "root_field_offsets_reviewed": False,
                        }
                    },
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_eh2_sidecar_bridge.json",
                {
                    "surface": "rtlmeter_veer_family_sidecar_bridge_preflight",
                    "status": "blocked_veer_eh2_sidecar_executable_unreviewed",
                    "sidecar_bridge_preflight_ready": True,
                    "sidecar_bridge_invoked": False,
                    "sidecar_observables_ready": False,
                    "cpu_reference_observables_ready": True,
                    "missing_build_context": [
                        "reviewed_root_field_offsets",
                        "design_specific_sidecar_executable_implementation",
                        "timing_report",
                    ],
                    "gpu_execution_claimed": False,
                    "timing_measured": False,
                    "speedup_claimed": False,
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_eh2_root_offset_review.json",
                {
                    "surface": "rtlmeter_veer_family_root_offset_review",
                    "status": "blocked_veer_eh2_root_observable_offset_review_incomplete",
                    "root_offset_review_performed": True,
                    "root_field_offsets_reviewed_for_target": False,
                    "root_observable_offset_candidates_complete": False,
                    "observed_marker_groups": ["control_scalars", "pc_candidates", "mailbox_observables"],
                    "missing_marker_groups": ["cycle_counters"],
                    "missing_build_context": [
                        "cycle_counters_root_offset_mapping",
                        "complete_root_field_offset_abi_review",
                    ],
                },
            )

            report = build_matrix(root)

        rows = {row["case"]: row for row in report["rows"]}
        eh1 = rows["VeeR-EH1:default:hello"]
        eh2 = rows["VeeR-EH2:default:hello"]
        self.assertEqual(eh1["measurement_status"], "portable_descriptor_ready_hybrid_surface_missing")
        self.assertEqual(eh1["missing_prerequisites"][0], "authority")
        self.assertEqual(eh1["hybrid_surface_audit"]["status"], "portable_descriptor_ready_surface_missing")
        self.assertFalse(eh1["hybrid_surface_audit"]["program_sha256_matches_el2"])
        self.assertIn("hello_program_sha256_differs_from_el2", eh1["hybrid_surface_audit"]["direct_el2_reuse_blockers"])
        self.assertEqual(eh2["measurement_status"], "sidecar_bridge_preflight_hybrid_surface_missing")
        self.assertEqual(
            eh2["missing_prerequisites"],
            ["timing_report", "reviewed_root_field_offsets", "design_specific_sidecar_executable_implementation"],
        )
        self.assertEqual(
            eh2["sidecar_bridge_preflight"]["sidecar_bridge_report"],
            "reports/rtlmeter_veer_eh2_sidecar_bridge.json",
        )
        self.assertFalse(eh2["sidecar_bridge_preflight"]["sidecar_bridge_invoked"])
        self.assertEqual(
            eh2["state_layout_probe"]["state_layout_report"],
            "reports/rtlmeter_veer_eh2_state_layout_inspection.json",
        )
        self.assertTrue(eh2["state_layout_probe"]["root_layout_probe_performed"])
        self.assertTrue(eh2["state_layout_probe"]["root_offset_probe_performed"])
        self.assertEqual(eh2["state_layout_probe"]["mapped_marker_offset_group_count"], 3)
        self.assertFalse(eh2["state_layout_probe"]["root_field_offsets_reviewed"])
        self.assertEqual(eh2["state_layout_probe"]["missing_marker_groups"], ["cycle_counters"])
        self.assertEqual(
            eh2["root_offset_review"]["root_offset_review_report"],
            "reports/rtlmeter_veer_eh2_root_offset_review.json",
        )
        self.assertFalse(eh2["root_offset_review"]["root_field_offsets_reviewed_for_target"])
        self.assertEqual(eh2["root_offset_review"]["missing_marker_groups"], ["cycle_counters"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_matrix_prioritizes_eh1_ptxas_timeout_after_module_load_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("Vortex", "VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design, cpp=design == "Vortex")
            self._write_json(
                root / "reports" / "rtlmeter_veer_family_surface_audit.json",
                {
                    "surface": "rtlmeter_veer_family_surface_audit",
                    "rows": [
                        {
                            "design": "VeeR-EH1",
                            "status": "sidecar_bridge_preflight_surface_missing",
                            "ready_to_port_from_descriptor": True,
                            "missing_surface": ["timing_report"],
                            "direct_el2_reuse_blockers": [],
                            "testbench_surface": {"program_sha256_matches_el2": False},
                            "next_action": "execute_bridge_comparison_and_timing",
                        }
                    ],
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_eh1_sidecar_bridge.json",
                {
                    "surface": "rtlmeter_veer_family_sidecar_bridge_preflight",
                    "status": "blocked_veer_eh1_gpu_launch_timeout",
                    "sidecar_bridge_preflight_ready": True,
                    "sidecar_bridge_invoked": True,
                    "sidecar_observables_ready": False,
                    "run_vl_hybrid_stage_trace": {"last_stage": "before_cuModuleLoad"},
                    "ptxas_probe": {"status": "ptxas_timeout"},
                    "cpu_reference_observables_ready": True,
                    "missing_build_context": [
                        "successful_gpu_launch_without_timeout",
                        "executed_bridge_comparison",
                        "ptxas_cubin_probe_timeout",
                        "timing_report",
                    ],
                    "gpu_execution_claimed": False,
                    "timing_measured": False,
                    "speedup_claimed": False,
                },
            )

            report = build_matrix(root)

        eh1 = {row["case"]: row for row in report["rows"]}["VeeR-EH1:default:hello"]
        self.assertEqual(
            eh1["next_action"],
            "reduce_eh1_generated_ptx_module_compile_cost_before_bridge_comparison",
        )
        self.assertEqual(eh1["sidecar_bridge_preflight"]["ptxas_probe"]["status"], "ptxas_timeout")

    def test_matrix_prioritizes_eh1_entry_pruned_eval_only_fault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("Vortex", "VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design, cpp=design == "Vortex")
            self._write_json(
                root / "reports" / "rtlmeter_veer_family_surface_audit.json",
                {
                    "surface": "rtlmeter_veer_family_surface_audit",
                    "rows": [
                        {
                            "design": "VeeR-EH1",
                            "status": "sidecar_bridge_preflight_surface_missing",
                            "ready_to_port_from_descriptor": True,
                            "missing_surface": ["timing_report"],
                            "direct_el2_reuse_blockers": [],
                            "testbench_surface": {"program_sha256_matches_el2": False},
                            "next_action": "execute_bridge_comparison_and_timing",
                        }
                    ],
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_eh1_sidecar_bridge.json",
                {
                    "surface": "rtlmeter_veer_family_sidecar_bridge_preflight",
                    "status": "blocked_veer_eh1_gpu_launch_timeout",
                    "sidecar_bridge_preflight_ready": True,
                    "sidecar_bridge_invoked": True,
                    "sidecar_observables_ready": False,
                    "run_vl_hybrid_stage_trace": {"last_stage": "before_cuModuleLoad"},
                    "ptxas_probe": {"status": "ptxas_timeout"},
                    "entry_pruned_module_probe": {
                        "ptxas_status": "passed",
                        "bridge_status": "illegal_memory_access_at_first_eval_launch",
                        "eval_only_status": "illegal_memory_access_at_first_eval_launch",
                        "padded_storage_probe_status": "padded_storage_did_not_clear_first_eval_fault",
                        "padded_storage_bytes": 2097152,
                        "static_ptx_residue_probe_status": (
                            "reachable_stdout_finish_cpp_runtime_residue_detected"
                        ),
                    },
                    "cpu_reference_observables_ready": True,
                    "missing_build_context": [
                        "successful_gpu_launch_without_timeout",
                        "executed_bridge_comparison",
                        "entry_pruned_eval_kernel_illegal_memory_access",
                        "entry_pruned_eval_only_fault_confirmed",
                        "padded_storage_did_not_clear_eval_fault",
                        "reachable_stdout_finish_cpp_runtime_residue",
                        "timing_report",
                    ],
                    "gpu_execution_claimed": False,
                    "timing_measured": False,
                    "speedup_claimed": False,
                },
            )

            report = build_matrix(root)

        eh1 = {row["case"]: row for row in report["rows"]}["VeeR-EH1:default:hello"]
        self.assertEqual(
            eh1["next_action"],
            "remove_or_device_stub_eh1_reachable_stdout_finish_cpp_runtime_residue_before_bridge_comparison",
        )
        self.assertEqual(
            eh1["sidecar_bridge_preflight"]["entry_pruned_module_probe"]["eval_only_status"],
            "illegal_memory_access_at_first_eval_launch",
        )
        self.assertEqual(
            eh1["sidecar_bridge_preflight"]["entry_pruned_module_probe"]["padded_storage_probe_status"],
            "padded_storage_did_not_clear_first_eval_fault",
        )
        self.assertEqual(
            eh1["sidecar_bridge_preflight"]["entry_pruned_module_probe"]["static_ptx_residue_probe_status"],
            "reachable_stdout_finish_cpp_runtime_residue_detected",
        )

    def test_matrix_prioritizes_eh2_first_eval_launch_fault(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for design in ("Vortex", "VeeR-EH1", "VeeR-EH2", "VeeR-EL2"):
                self._write_descriptor(root, design, cpp=design == "Vortex")
            self._write_json(
                root / "reports" / "rtlmeter_veer_family_surface_audit.json",
                {
                    "surface": "rtlmeter_veer_family_surface_audit",
                    "rows": [
                        {
                            "design": "VeeR-EH2",
                            "status": "sidecar_bridge_preflight_surface_missing",
                            "ready_to_port_from_descriptor": True,
                            "missing_surface": ["timing_report"],
                            "direct_el2_reuse_blockers": [],
                            "testbench_surface": {"program_sha256_matches_el2": False},
                            "next_action": "execute_bridge_comparison_and_timing",
                        }
                    ],
                },
            )
            self._write_json(
                root / "reports" / "rtlmeter_veer_eh2_sidecar_bridge.json",
                {
                    "surface": "rtlmeter_veer_family_sidecar_bridge_preflight",
                    "status": "blocked_veer_eh2_gpu_launch_timeout",
                    "sidecar_bridge_preflight_ready": True,
                    "sidecar_bridge_invoked": True,
                    "sidecar_observables_ready": False,
                    "run_vl_hybrid_stage_trace": {"last_stage": "before_cuModuleLoad"},
                    "entry_pruned_module_probe": {
                        "bridge_status": "illegal_memory_access_at_first_step_sync",
                        "entry_pruned_sidecar_last_stage": "before_first_step_sync",
                        "entry_pruned_sidecar_sync_each_step": True,
                        "entry_pruned_sidecar_module_override": "artifacts/entry_pruned.cubin",
                        "static_ptx_runtime_residue_probe": {
                            "status": "cpp_verilator_runtime_residue_detected",
                            "runtime_residue_detected": True,
                            "residue_pattern_total": 1327,
                        },
                        "host_cleanup_eval_only_probe": {
                            "status": "host_cleanup_eval_only_still_illegal_memory_access",
                        },
                        "host_cleanup_v2_eval_only_probe": {
                            "status": "host_cleanup_v2_eval_only_still_illegal_memory_access",
                        },
                        "return_before_eval_probe": {
                            "status": "return_before_eval_passed",
                        },
                        "return_before_eval_call_probe": {
                            "status": "prologue_only_return_before_eval_call_passed",
                        },
                        "trigger_orinto_return_before_first_ix_probe": {
                            "status": "trigger_orinto_return_before_first_ix_still_illegal_memory_access",
                        },
                        "trigger_orinto_return_before_first_ix_stack64k_probe": {
                            "status": "trigger_orinto_return_before_first_ix_stack64k_still_illegal_memory_access",
                        },
                        "inline_orinto_return_after_probe": {
                            "status": "inline_orinto_return_after_still_illegal_memory_access",
                        },
                        "inline_orinto_noop_return_after_probe": {
                            "status": "inline_orinto_noop_return_after_passed",
                        },
                        "inline_orinto_after_dst_load_probe": {
                            "status": "inline_orinto_after_dst_load_passed",
                        },
                        "inline_orinto_after_src_load_probe": {
                            "status": "inline_orinto_after_src_load_passed",
                        },
                        "inline_orinto_before_store_probe": {
                            "status": "inline_orinto_before_store_passed",
                        },
                        "inline_orinto_store_u64_src_probe": {
                            "status": "inline_orinto_store_u64_src_passed",
                        },
                        "inline_orinto_store_u32_dst_probe": {
                            "status": "inline_orinto_store_u32_dst_still_illegal_memory_access",
                        },
                        "inline_orinto_store_u8_dst_probe": {
                            "status": "inline_orinto_store_u8_dst_still_illegal_memory_access",
                        },
                        "entry_store_nba_trigger_return_probe": {
                            "status": "entry_store_nba_trigger_return_passed",
                        },
                        "vlunpacked_lm1_canonical_eval_only_probe": {
                            "status": "vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access",
                        },
                        "vlunpacked_lm1_trigger_orinto_return_immediate_probe": {
                            "status": (
                                "vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access"
                            ),
                        },
                        "vlunpacked_lm1_orinto_rewrite_eval_only_probe": {
                            "status": "vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access",
                        },
                        "skip_store_return_after_eval_act_probe": {
                            "status": "skip_store_return_after_eval_act_still_illegal_memory_access",
                        },
                        "eval_act_return_after_callseq_probes": {
                            "951": {"status": "eval_act_return_after_callseq_951_passed"},
                            "952": {
                                "status": "eval_act_return_after_callseq_952_still_illegal_memory_access",
                            },
                        },
                        "dec_cam0_minimal_body_ret_probe": {
                            "status": "dec_cam0_minimal_body_ret_still_illegal_memory_access",
                        },
                        "eval_act_skip_callseq_952_953_954_return_after_954_probe": {
                            "status": "eval_act_skip_callseq_952_953_954_return_after_954_passed",
                        },
                    },
                    "cpu_reference_observables_ready": True,
                    "missing_build_context": [
                        "successful_gpu_launch_without_timeout",
                        "executed_bridge_comparison",
                        "entry_pruned_cubin_gpu_launch_failed",
                        "entry_pruned_cubin_gpu_launch_illegal_memory_access",
                        "entry_pruned_cubin_first_step_sync_illegal_memory_access",
                        "entry_pruned_cpp_verilator_runtime_residue_detected",
                        "eh2_host_cleanup_eval_only_did_not_clear_eval_fault",
                        "eh2_host_cleanup_v2_eval_only_did_not_clear_eval_fault",
                        "eh2_return_before_eval_launch_infrastructure_passed",
                        "eh2_prologue_pointer_setup_passed_before_eval_call",
                        "eh2_trigger_orinto_device_call_entry_fault",
                        "eh2_trigger_orinto_entry_fault_not_stack_limit",
                        "eh2_inline_orinto_loads_before_store_pass",
                        "eh2_inline_orinto_store_to_vnba_triggered_fault",
                        "eh2_adjacent_vact_triggered_store_passes",
                        "eh2_vnba_triggered_store_width_independent_fault",
                        "eh2_entry_context_vnba_triggered_store_passes",
                        "timing_report",
                    ],
                    "gpu_execution_claimed": False,
                    "timing_measured": False,
                    "speedup_claimed": False,
                },
            )

            report = build_matrix(root)

        eh2 = {row["case"]: row for row in report["rows"]}["VeeR-EH2:default:hello"]
        self.assertEqual(
            eh2["next_action"],
            "fix_eh2_eval_act_submodule_act_call_boundary_cuda700_before_bridge_timing",
        )
        self.assertEqual(
            eh2["sidecar_bridge_preflight"]["entry_pruned_module_probe"]["bridge_status"],
            "illegal_memory_access_at_first_step_sync",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
