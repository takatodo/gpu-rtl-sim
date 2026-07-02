import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "tools"))

from rtlmeter_hybrid_measurement_difficulty import build_summary, to_markdown  # noqa: E402


class RtlmeterHybridMeasurementDifficultyTest(unittest.TestCase):
    def _write_matrix(self, root: Path) -> Path:
        reports = root / "reports"
        reports.mkdir()
        matrix = reports / "matrix.json"
        matrix.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "rows": [
                        {
                            "case": "Vortex:mini:hello",
                            "design": "Vortex",
                            "measurement_status": "blocked_before_hybrid_measurement",
                            "timing_status": "not_measured",
                            "correctness_status": "not_measured",
                            "speedup_claimed": False,
                            "missing_prerequisites": [
                                "real_runtime_execution_reports_vortex_observable_authority",
                                "cpu_vs_hybrid_timing_report.vortex",
                            ],
                            "next_action": "connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence",
                            "hybrid_candidate": {
                                "probe_or_marker_boundary_observed": True,
                                "fake_driver_materialized_runtime_args_call_observed": True,
                                "real_cuda_materialized_runtime_args_call_observed": True,
                                "real_vortex_kernel_artifact_ready": False,
                                "kernel_artifact_build_landingpad_blocked": True,
                                "real_cuda_materialized_runtime_smoke_timed_out": True,
                                "real_cuda_root_storage_kernel_last_stage": "before_cuModuleLoad",
                                "ptx_module_load_ptxas_status": "ptxas_timeout",
                                "ptx_module_load_ptxas_timed_out": True,
                                "real_runtime_observable_authority_ready": False,
                                "real_cuda_memory_transport_passed": True,
                                "real_cuda_runtime_sequence_preflight_passed": True,
                                "real_cuda_runtime_sequence_preflight_h2d_bytes": 37224,
                                "real_cuda_runtime_sequence_preflight_d2h_initial_bytes": 88,
                            },
                        },
                        {
                            "case": "VeeR-EL2:default:hello",
                            "design": "VeeR-EL2",
                            "measurement_status": "measured",
                            "timing_status": "measured",
                            "correctness_status": "passed",
                            "speedup_claimed": False,
                            "missing_prerequisites": [],
                            "best_timing_report": {
                                "sidecar_vs_cpu_parallel_ratio": 3.460382,
                                "serial_cpu_wall_time_outcome": "sidecar_slower_than_serial_cpu",
                                "cpu_parallel_wall_time_outcome": (
                                    "sidecar_faster_than_comparable_cpu_parallel_baseline"
                                ),
                            },
                        },
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return matrix

    def test_summarizes_measurement_difficulty_without_claiming_speedup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            matrix = self._write_matrix(root)
            summary = build_summary(root, matrix_path=matrix)

        self.assertEqual(summary["status"], "hybrid_measurement_difficulty_summarized")
        self.assertEqual(summary["measured_count"], 1)
        self.assertEqual(summary["unmeasured_count"], 1)
        vortex = summary["rows"][0]
        self.assertEqual(vortex["case"], "Vortex:mini:hello")
        self.assertEqual(vortex["transfer"]["total_known_transfer_bytes"], 37312)
        self.assertIn("probe_or_marker_boundary_still_in_execution_path", vortex["primary_blockers"])
        self.assertIn(
            "fake_driver_materialized_runtime_args_call_still_in_execution_path",
            vortex["primary_blockers"],
        )
        self.assertIn("real_vortex_kernel_artifact_missing", vortex["primary_blockers"])
        self.assertIn("vortex_lowered_ir_landingpad_personality_fix_required", vortex["primary_blockers"])
        self.assertIn("real_vortex_cuModuleLoad_jit_timeout", vortex["primary_blockers"])
        self.assertIn(
            "vortex_ptxas_timeout_reproduces_cuModuleLoad_jit_cost",
            vortex["primary_blockers"],
        )
        self.assertIn("real_runtime_observable_authority_missing", vortex["primary_blockers"])
        self.assertFalse(vortex["speedup_claimed"])
        self.assertIn("not_speedup_claim", summary["non_claims"])

    def test_markdown_table_contains_core_columns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            matrix = self._write_matrix(root)
            summary = build_summary(root, matrix_path=matrix)
            markdown = to_markdown(summary)

        self.assertIn("| case | status | difficulty | first blockers | transfer risk | measured comparison |", markdown)
        self.assertIn("Vortex:mini:hello", markdown)
        self.assertIn("37312 bytes known", markdown)
        self.assertIn("parallel ratio 3.460382", markdown)

    def test_return_before_eval_success_refines_vortex_cuda_700_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            reports.mkdir()
            matrix = reports / "matrix.json"
            matrix.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rows": [
                            {
                                "case": "Vortex:mini:hello",
                                "design": "Vortex",
                                "measurement_status": "blocked_before_hybrid_measurement",
                                "timing_status": "not_measured",
                                "correctness_status": "not_measured",
                                "missing_prerequisites": [],
                                "hybrid_candidate": {
                                    "real_cuda_materialized_runtime_smoke_failed_stage": "kernel_launch",
                                    "real_cuda_root_storage_kernel_failed_stage": "cuLaunchOrSync",
                                    "real_cuda_root_storage_kernel_failed_result": 700,
                                    "real_cuda_root_storage_relocation_count": 65,
                                    "real_cuda_return_before_eval_smoke_passed": True,
                                    "real_runtime_observable_authority_ready": False,
                                },
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_summary(root, matrix_path=matrix)

        vortex = summary["rows"][0]
        self.assertIn("real_vortex_eval_internal_kernel_illegal_memory_access", vortex["primary_blockers"])
        self.assertNotIn(
            "real_vortex_relocated_syms_image_kernel_illegal_memory_access",
            vortex["primary_blockers"],
        )

    def test_all_std_ref_returns_arg_probe_refines_vortex_cuda_700_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            reports.mkdir()
            matrix = reports / "matrix.json"
            matrix.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rows": [
                            {
                                "case": "Vortex:mini:hello",
                                "design": "Vortex",
                                "measurement_status": "blocked_before_hybrid_measurement",
                                "timing_status": "not_measured",
                                "correctness_status": "not_measured",
                                "missing_prerequisites": [],
                                "hybrid_candidate": {
                                    "real_cuda_materialized_runtime_smoke_failed_stage": "kernel_launch",
                                    "real_cuda_root_storage_kernel_failed_stage": "cuLaunchOrSync",
                                    "real_cuda_root_storage_kernel_failed_result": 700,
                                    "real_cuda_root_storage_relocation_count": 65,
                                    "real_cuda_return_before_eval_smoke_passed": True,
                                    "real_cuda_all_std_ref_returns_arg_smoke_passed": True,
                                    "real_runtime_observable_authority_ready": False,
                                },
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_summary(root, matrix_path=matrix)

        vortex = summary["rows"][0]
        self.assertIn(
            "vortex_std_ref_device_lowering_fix_not_promoted_to_canonical_artifact",
            vortex["primary_blockers"],
        )
        self.assertNotIn("real_vortex_eval_internal_kernel_illegal_memory_access", vortex["primary_blockers"])

    def test_canonical_std_ref_fix_probe_refines_vortex_blocker_to_authority(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            reports.mkdir()
            matrix = reports / "matrix.json"
            matrix.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rows": [
                            {
                                "case": "Vortex:mini:hello",
                                "design": "Vortex",
                                "measurement_status": "blocked_before_hybrid_measurement",
                                "timing_status": "not_measured",
                                "correctness_status": "not_measured",
                                "missing_prerequisites": [],
                                "hybrid_candidate": {
                                    "real_cuda_materialized_runtime_smoke_failed_stage": "kernel_launch",
                                    "real_cuda_root_storage_kernel_failed_stage": "cuLaunchOrSync",
                                    "real_cuda_root_storage_kernel_failed_result": 700,
                                    "real_cuda_return_before_eval_smoke_passed": True,
                                    "real_cuda_all_std_ref_returns_arg_smoke_passed": True,
                                    "real_cuda_canonical_std_ref_fix_smoke_passed": True,
                                    "real_runtime_observable_authority_ready": False,
                                },
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_summary(root, matrix_path=matrix)

        vortex = summary["rows"][0]
        self.assertIn(
            "real_runtime_observable_authority_missing_after_canonical_std_ref_fix",
            vortex["primary_blockers"],
        )
        self.assertNotIn(
            "vortex_std_ref_device_lowering_fix_not_promoted_to_canonical_artifact",
            vortex["primary_blockers"],
        )

    def test_eh2_static_ptx_runtime_residue_is_reported_as_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reports = root / "reports"
            reports.mkdir()
            matrix = reports / "matrix.json"
            matrix.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "rows": [
                            {
                                "case": "VeeR-EH2:default:hello",
                                "design": "VeeR-EH2",
                                "measurement_status": "sidecar_bridge_preflight_hybrid_surface_missing",
                                "timing_status": "not_measured",
                                "correctness_status": "not_measured",
                                "missing_prerequisites": [
                                    "successful_gpu_launch_without_timeout",
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
                                    "eh2_entry_context_vnba_triggered_store_passes",
                                    "eh2_eval_phase_vnba_store_passes_with_direct_root",
                                    "eh2_reference_wrapper_get_cvta_vnba_store_still_faults",
                                    "eh2_minimal_eval_phase_vnba_store_passes",
                                    "eh2_std_ref_get_canonical_eval_only_still_faults",
                                    "eh2_std_ref_get_canonical_eval_prologue_passes_before_phase_act",
                                    "eh2_std_ref_get_canonical_one_phase_act_still_faults",
                                    "eh2_std_ref_get_canonical_phase_act_orinto_still_faults",
                                    "eh2_vlunpacked_lm1_phase_act_before_orinto_passes",
                                    "eh2_vlunpacked_lm1_trigger_orinto_helper_call_entry_fault",
                                    "eh2_vlunpacked_lm1_orinto_rewrite_did_not_clear_eval_fault",
                                    "eh2_orinto_store_value_or_store_itself_is_not_only_fault",
                                    "eh2_skip_store_timing_resume_passes",
                                    "eh2_skip_store_eval_act_boundary_fault",
                                    "eh2_padded2m_does_not_clear_eval_phase_vnba_store_fault",
                                    "eh2_maxr128_does_not_clear_eval_phase_vnba_store_fault",
                                    "timing_report",
                                ],
                                "sidecar_bridge_preflight": {
                                    "entry_pruned_module_probe": {
                                        "bridge_status": "illegal_memory_access_at_first_step_sync",
                                        "static_ptx_runtime_residue_probe": {
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
                                            "status": (
                                                "trigger_orinto_return_before_first_ix_still_illegal_memory_access"
                                            ),
                                        },
                                        "trigger_orinto_return_before_first_ix_stack64k_probe": {
                                            "status": (
                                                "trigger_orinto_return_before_first_ix_stack64k_still_illegal_memory_access"
                                            ),
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
                                        "store_vnba_after_triggers_direct_root_probe": {
                                            "status": "eval_phase_act_store_vnba_after_triggers_direct_root_passed",
                                        },
                                        "inline_orinto_store_vnba_cvta_global_probe": {
                                            "status": (
                                                "inline_orinto_store_vnba_cvta_global_still_illegal_memory_access"
                                            ),
                                        },
                                        "minimal_store_vnba_probe": {
                                            "status": "eval_phase_act_minimal_store_vnba_passed",
                                        },
                                        "std_ref_get_canonical_eval_only_probe": {
                                            "status": "std_ref_get_canonical_eval_only_still_illegal_memory_access",
                                        },
                                        "std_ref_get_canonical_eval_return_before_phase_act_probe": {
                                            "status": "std_ref_get_canonical_eval_return_before_phase_act_passed",
                                        },
                                        "std_ref_get_canonical_eval_return_after_one_phase_act_probe": {
                                            "status": (
                                                "std_ref_get_canonical_eval_return_after_one_phase_act_still_illegal_memory_access"
                                            ),
                                        },
                                        "std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe": {
                                            "status": (
                                                "std_ref_get_canonical_phase_act_return_after_orinto_ret0_still_illegal_memory_access"
                                            ),
                                        },
                                        "std_ref_get_canonical_trigger_orinto_return_before_store_probe": {
                                            "status": (
                                                "std_ref_get_canonical_trigger_orinto_return_before_store_passed"
                                            ),
                                        },
                                        "std_ref_get_canonical_trigger_orinto_return_after_store_probe": {
                                            "status": (
                                                "std_ref_get_canonical_trigger_orinto_return_after_store_still_illegal_memory_access"
                                            ),
                                        },
                                        "vlunpacked_lm1_canonical_eval_only_probe": {
                                            "status": (
                                                "vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access"
                                            ),
                                        },
                                        "vlunpacked_lm1_phase_act_return_before_orinto_probe": {
                                            "status": "vlunpacked_lm1_phase_act_return_before_orinto_passed",
                                        },
                                        "vlunpacked_lm1_trigger_orinto_return_immediate_probe": {
                                            "status": (
                                                "vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access"
                                            ),
                                        },
                                        "vlunpacked_lm1_orinto_rewrite_eval_only_probe": {
                                            "status": (
                                                "vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access"
                                            ),
                                        },
                                        "orinto_store_skip_eval_only_probe": {
                                            "status": "orinto_store_skip_eval_only_still_illegal_memory_access",
                                        },
                                        "orinto_store_zero_eval_only_probe": {
                                            "status": "orinto_store_zero_eval_only_still_illegal_memory_access",
                                        },
                                        "orinto_store_dst_eval_only_probe": {
                                            "status": "orinto_store_dst_eval_only_still_illegal_memory_access",
                                        },
                                        "skip_store_return_after_timing_resume_probe": {
                                            "status": "skip_store_return_after_timing_resume_passed",
                                        },
                                        "skip_store_return_after_eval_act_probe": {
                                            "status": (
                                                "skip_store_return_after_eval_act_still_illegal_memory_access"
                                            ),
                                        },
                                        "eval_act_return_after_callseq_probes": {
                                            "951": {"status": "eval_act_return_after_callseq_951_passed"},
                                            "952": {
                                                "status": (
                                                    "eval_act_return_after_callseq_952_still_illegal_memory_access"
                                                ),
                                            },
                                        },
                                        "dec_cam0_minimal_body_ret_probe": {
                                            "status": "dec_cam0_minimal_body_ret_still_illegal_memory_access",
                                        },
                                        "eval_act_skip_callseq_952_953_954_return_after_954_probe": {
                                            "status": (
                                                "eval_act_skip_callseq_952_953_954_return_after_954_passed"
                                            ),
                                        },
                                    }
                                },
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_summary(root, matrix_path=matrix)

        eh2 = summary["rows"][0]
        self.assertIn(
            "entry_pruned_cpp_verilator_runtime_residue_in_gpu_ptx",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_existing_host_cleanup_still_faults_at_first_eval",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_extended_host_cleanup_still_faults_at_eval_callee",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_launch_and_prologue_pass_eval_callee_internal_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_trigger_orinto_device_call_abi_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_trigger_orinto_stack_limit_override_did_not_clear_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_eval_phase_vnba_triggered_store_context_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_vnba_store_fault_is_context_sensitive_not_raw_address",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_vnba_store_passes_when_root_is_recomputed_directly",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_reference_wrapper_get_pointer_store_path_still_faults",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_vnba_fault_requires_full_eval_context_not_plain_store",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_std_ref_get_canonicalization_did_not_clear_eval_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_std_ref_get_canonical_eval_prologue_passes",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_std_ref_get_canonical_fault_is_in_phase_act",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_std_ref_get_canonical_trigger_orinto_still_faults",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_std_ref_get_canonical_trigger_orinto_loads_and_or_pass",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_std_ref_get_canonical_trigger_orinto_dst_store_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_canonicalization_did_not_clear_eval_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_phase_act_before_orinto_passes",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_trigger_orinto_helper_call_entry_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_vlunpacked_lm1_inlined_orinto_store_context_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_orinto_store_value_or_store_itself_is_not_only_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_skip_store_timing_resume_passes",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_post_vlunpacked_lm1_eval_act_boundary_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_eval_act_dec_cam0_act_sequent_boundary_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_eval_act_submodule_act_call_boundary_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_padded_storage_does_not_clear_vnba_store_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "eh2_register_cap_does_not_clear_vnba_store_fault",
            eh2["primary_blockers"],
        )
        self.assertIn(
            "entry_pruned_cpp_verilator_runtime_residue_detected",
            eh2["immediate_next_requirements"],
        )

    def test_cli_writes_json_and_markdown_without_local_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            matrix = self._write_matrix(root)
            out = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "src" / "tools" / "rtlmeter_hybrid_measurement_difficulty.py"),
                    "--repo-root",
                    str(root),
                    "--matrix",
                    matrix.as_posix(),
                    "--write-report",
                    "--report-out",
                    "reports/difficulty.json",
                    "--markdown-out",
                    "reports/difficulty.md",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            report_text = (root / "reports" / "difficulty.json").read_text(encoding="utf-8")
            markdown_text = (root / "reports" / "difficulty.md").read_text(encoding="utf-8")

        self.assertIn("VeeR-EL2:default:hello", out.stdout)
        self.assertNotIn(td, report_text)
        self.assertIn("rtlmeter_hybrid_measurement_difficulty", report_text)
        self.assertIn("Vortex:mini:hello", markdown_text)


if __name__ == "__main__":
    unittest.main()
