import json
import tempfile
from pathlib import Path
from unittest import mock

from tests.contract.hybrid_cli_helpers import HybridCliTestCase


class RtlmeterVeerEl2TimingTest(HybridCliTestCase):
    def _write_bounded_progress_report(
        self,
        path: Path,
        *,
        mcycle: int = 499,
        minstret: int = 321,
        actual_launches: int = 506,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "observables_emitted",
                    "steps": 1003,
                    "sidecar_state_count": 2,
                    "pair_cycle_loop_fusion": {
                        "kernel_launches": 5,
                        "cycles": 5000,
                        "fallback": 0,
                    },
                    "run_vl_hybrid_timing": {
                        "gpu_kernel_timed_launch_count": actual_launches,
                    },
                    "pair_cycle_fusion": {
                        "launched": 500,
                        "fallback": 0,
                    },
                    "materialized": {
                        "dccm_bank_words": 371,
                        "iccm_bank_words": 0,
                        "dccm_bank_skipped_missing_bank": 0,
                        "iccm_bank_skipped_missing_bank": 0,
                        "dccm_bank_skipped_out_of_range": 0,
                        "iccm_bank_skipped_out_of_range": 0,
                    },
                    "observables": {
                        "mcycle": mcycle,
                        "minstret": minstret,
                        "pc_hex": "0x40000164",
                        "finish_marker_observed": False,
                        "stdout_stream_reconstructed": False,
                    },
                    "stdout_trace": {
                        "diagnostic": "final-observable stdout reconstruction is reviewed only for the hello program",
                        "stdout_stream_reconstructed": False,
                        "trace_rows": 0,
                        "step_trace_disabled": True,
                    },
                    "step_trace_disabled": True,
                    "final_observable_stdout_requested": True,
                    "parallel_state_validation": {
                        "parallel_state_observables_match": True,
                        "parallel_state_matching_count": 2,
                    },
                }
            ),
            encoding="utf-8",
        )

    def _write_cpu_serial_baseline_report(
        self,
        path: Path,
        *,
        case: str = "VeeR-EL2:default:dhry",
        rtlmeter_cycles: int = 6_000_000,
        wall_s: float = 40.0,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "serial_results": [
                        {
                            "case": case,
                            "case_instance": "veer_el2_default_dhry",
                            "observables": {
                                "status": "observables_ready",
                                "rtlmeter_cycles": rtlmeter_cycles,
                                "execute_dir": "artifacts/cpu/VeeR-EL2/default/execute-0/dhry",
                            },
                            "passed": True,
                            "wall_s": wall_s,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _write_mixed_gpu_sidecar_report(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "observables_emitted",
                    "sidecar_state_count": 3,
                    "state_images": [
                        "artifacts/veer/veer_el2_dhry_state_image.json",
                        "artifacts/veer/veer_el2_cmark_state_image.json",
                        "artifacts/veer/veer_el2_cmark_iccm_state_image.json",
                    ],
                    "init_replication_scope": "per_state_mixed_init",
                    "init_replication_mode": "host_uploaded_concatenated_state_images",
                    "materialized": {
                        "mixed_state_preload": True,
                        "state_count": 3,
                        "program_preloads": [
                            "third_party/rtlmeter/designs/VeeR-EL2/tests/dhry/program.hex",
                            "third_party/rtlmeter/designs/VeeR-EL2/tests/cmark/program.hex",
                            "third_party/rtlmeter/designs/VeeR-EL2/tests/cmark_iccm/program.hex",
                        ],
                        "program_sha256s": ["sha-dhry", "sha-cmark", "sha-cmark-iccm"],
                        "per_state": [
                            {"state_index": 0, "program_sha256": "sha-dhry", "dccm_bank_words": 371, "iccm_bank_words": 0},
                            {"state_index": 1, "program_sha256": "sha-cmark", "dccm_bank_words": 0, "iccm_bank_words": 0},
                            {"state_index": 2, "program_sha256": "sha-cmark-iccm", "dccm_bank_words": 342, "iccm_bank_words": 7674},
                        ],
                    },
                    "parallel_state_validation": {
                        "parallel_state_count": 3,
                        "parallel_state_validation_status": "mixed_state_final_observables_recorded",
                        "parallel_state_observables_match": None,
                        "per_state_observability_contract": {
                            "status": "incomplete_mixed_state_stdout",
                            "finish_marker_per_state": True,
                            "final_counters_per_state": True,
                            "stdout_per_state": False,
                            "rtlmeter_cycles_per_state": False,
                            "unsupported_reason": "mixed-state stdout/cycle emission is only implemented for state0",
                        },
                    },
                    "run_vl_hybrid_timing": {
                        "gpu_kernel_time_ms_total": 10.0,
                        "gpu_kernel_timed_launch_count": 10,
                        "pair_cycle_loop_fusion": {
                            "kernel_launches": 1,
                            "cycles": 10,
                            "fallback": 0,
                        },
                    },
                    "phase_timing_s": {
                        "run_vl_hybrid_wall_s": 0.5,
                    },
                }
            ),
            encoding="utf-8",
        )

    def _write_cpu_mixed_baseline_report(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "cases": [
                        "VeeR-EL2:default:dhry",
                        "VeeR-EL2:default:cmark",
                        "VeeR-EL2:default:cmark_iccm",
                    ],
                    "summary": {
                        "case_count": 3,
                        "parallel_wall_s": 37.0,
                        "serial_sum_case_wall_s": 107.0,
                        "parallel_speedup_vs_serial_sum": 2.89,
                        "all_runs_passed": True,
                        "all_observables_match": True,
                    },
                }
            ),
            encoding="utf-8",
        )

    def _write_same_window_compare_report(
        self,
        path: Path,
        *,
        status: str = "match",
        aligned_rows: int = 49125,
        compared_field_count: int = 62,
        mismatch_count: int = 0,
        first_mismatch: object = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": status,
                    "aligned_rows": aligned_rows,
                    "alignment": "cpu_post_reset_posedges = gpu_step + 3",
                    "compared_field_count": compared_field_count,
                    "cpu_report": "reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_50002.json",
                    "gpu_trace": (
                        "artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/"
                        "dhry_lmem_control_trace_50000/_sidecar/veer_el2_step_trace.csv"
                    ),
                    "excluded_fields": ["pc_din"],
                    "first_mismatch": first_mismatch,
                    "range": {
                        "gpu_step_start": 875,
                        "gpu_step_end": 49999,
                    },
                    "total_mismatched_field_observations": mismatch_count,
                }
            ),
            encoding="utf-8",
        )

    def test_plan_is_non_executing_and_points_at_existing_gate(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        report = build_veer_el2_timing_report(samples=3, execute=False)

        self.assertEqual(report["surface"], "rtlmeter_veer_el2_timing")
        self.assertEqual(report["status"], "opt_in_required")
        self.assertEqual(report["batch_count"], 1)
        self.assertEqual(report["total_sample_count"], 3)
        self.assertFalse(report["timing_measured"])
        self.assertFalse(report["speedup_claimed"])
        self.assertIn("run-veer-el2-sidecar-bridge", report["command"])
        self.assertEqual(report["methodology"]["central_tendency"], "median")
        self.assertIn("stability_gate", report["methodology"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_bounded_progress_summary_passes_when_architectural_counters_advance(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_bounded_progress_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = [
                "reports/rtlmeter_veer_el2_dhry_bounded_progress_500.json",
                "reports/rtlmeter_veer_el2_cmark_bounded_progress_500.json",
            ]
            for report_path in reports:
                self._write_bounded_progress_report(root / report_path)

            summary = build_bounded_progress_summary(
                report_paths=reports,
                repo_root=root,
                min_mcycle=1,
                min_minstret=1,
                max_actual_launches=100000,
            )

        self.assertEqual(summary["surface"], "rtlmeter_veer_el2_timing.bounded_progress_summary")
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["report_count"], 2)
        self.assertEqual(summary["passed_report_count"], 2)
        self.assertTrue(summary["bounded_progress_evidence"])
        self.assertEqual(summary["reports"][0]["pair_cycle_loop_fusion_kernel_launches"], 5)
        self.assertEqual(summary["reports"][0]["pair_cycle_loop_fusion_cycles"], 5000)
        self.assertEqual(summary["reports"][0]["pair_cycle_loop_fusion_fallback"], 0)
        self.assertEqual(summary["reports"][0]["dccm_bank_words"], 371)
        self.assertEqual(summary["reports"][0]["iccm_bank_words"], 0)
        self.assertEqual(summary["reports"][0]["dccm_bank_skipped_missing_bank"], 0)
        self.assertEqual(summary["reports"][0]["iccm_bank_skipped_missing_bank"], 0)
        self.assertFalse(summary["timing_measured"])
        self.assertTrue(summary["gpu_execution_claimed"])
        self.assertFalse(summary["speedup_claimed"])
        self.assertFalse(summary["usefulness_claimed"])
        self.assertEqual(summary["failed_reports"], [])
        self.assertEqual(summary["reports"][0]["mcycle"], 499)
        self.assertEqual(summary["reports"][0]["minstret"], 321)
        self.assertFalse(summary["reports"][0]["stdout_stream_reconstructed"])
        self.assertFalse(summary["reports"][0]["stdout_trace_stream_reconstructed"])
        self.assertTrue(summary["reports"][0]["step_trace_disabled"])
        self.assertTrue(summary["reports"][0]["final_observable_stdout_requested"])
        self.assertEqual(summary["reports"][0]["stdout_trace_rows"], 0)
        self.assertIn("reviewed only for the hello program", summary["reports"][0]["stdout_trace_diagnostic"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_bounded_progress_summary_fails_closed_for_missing_or_stalled_reports(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_bounded_progress_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stalled = "reports/stalled.json"
            missing = "reports/missing.json"
            self._write_bounded_progress_report(root / stalled, mcycle=0, minstret=0)

            summary = build_bounded_progress_summary(
                report_paths=[stalled, missing],
                repo_root=root,
                min_mcycle=1,
                min_minstret=1,
                max_actual_launches=100000,
            )

        self.assertEqual(summary["status"], "incomplete")
        self.assertFalse(summary["bounded_progress_evidence"])
        self.assertEqual(summary["passed_report_count"], 0)
        self.assertEqual(summary["failed_reports"], ["reports/stalled.json", "reports/missing.json"])
        self.assertEqual(summary["missing_reports"], ["reports/missing.json"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_bounded_projection_summary_marks_negative_usefulness_without_positive_claim(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_bounded_projection_usefulness_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar_report = "artifacts/gpu/_sidecar/veer_el2_sidecar_executable_report.json"
            cpu_report = "reports/rtlmeter_cpu_dhry_serial_baseline.json"
            self._write_bounded_progress_report(
                root / sidecar_report,
                mcycle=100_000,
                minstret=95_864,
                actual_launches=10,
            )
            loaded = json.loads((root / sidecar_report).read_text(encoding="utf-8"))
            loaded["run_vl_hybrid_timing"]["gpu_kernel_time_ms_total"] = 20_000.0
            loaded["phase_timing_s"] = {"run_vl_hybrid_wall_s": 22.0}
            (root / sidecar_report).write_text(json.dumps(loaded), encoding="utf-8")
            self._write_cpu_serial_baseline_report(root / cpu_report)

            summary = build_bounded_projection_usefulness_summary(
                sidecar_report_path=sidecar_report,
                cpu_baseline_report_path=cpu_report,
                case="VeeR-EL2:default:dhry",
                repo_root=root,
                min_progress_fraction=0.01,
                negative_ratio_threshold=10.0,
            )

        self.assertEqual(summary["surface"], "rtlmeter_veer_el2_timing.bounded_projection_usefulness_summary")
        self.assertEqual(summary["status"], "negative_usefulness_projected")
        self.assertEqual(summary["errors"], [])
        self.assertEqual(summary["cpu_cycle_source"], "serial_results[].observables.rtlmeter_cycles")
        self.assertEqual(summary["cpu_rtlmeter_cycles"], 6_000_000)
        self.assertEqual(summary["cpu_serial_wall_s"], 40.0)
        self.assertEqual(summary["gpu_mcycle"], 100_000)
        self.assertEqual(summary["gpu_minstret"], 95_864)
        self.assertFalse(summary["gpu_finish_marker_observed"])
        self.assertFalse(summary["gpu_stdout_stream_reconstructed"])
        self.assertFalse(summary["gpu_stdout_trace_stream_reconstructed"])
        self.assertEqual(summary["gpu_actual_timed_launches"], 10)
        self.assertEqual(summary["progress_fraction_of_cpu_rtlmeter_cycles"], 1.0 / 60.0)
        self.assertEqual(summary["projection_scale_to_cpu_rtlmeter_cycles"], 60.0)
        self.assertEqual(summary["projected_gpu_kernel_s_to_cpu_rtlmeter_cycles"], 1200.0)
        self.assertEqual(summary["projected_run_vl_hybrid_wall_s_to_cpu_rtlmeter_cycles"], 1320.0)
        self.assertEqual(summary["projected_gpu_kernel_vs_cpu_serial_ratio"], 30.0)
        self.assertEqual(summary["projected_run_vl_hybrid_wall_vs_cpu_serial_ratio"], 33.0)
        self.assertTrue(summary["bounded_projection_evidence"])
        self.assertTrue(summary["negative_usefulness_decision"])
        self.assertFalse(summary["timing_measured"])
        self.assertTrue(summary["bounded_timing_measured"])
        self.assertFalse(summary["full_program_timing_measured"])
        self.assertFalse(summary["speedup_claimed"])
        self.assertFalse(summary["usefulness_claimed"])
        self.assertIn("not full-program GPU timing", summary["non_claims"][1])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_bounded_projection_summary_fails_closed_for_tiny_progress(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_bounded_projection_usefulness_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar_report = "artifacts/gpu/_sidecar/veer_el2_sidecar_executable_report.json"
            cpu_report = "reports/rtlmeter_cpu_dhry_serial_baseline.json"
            self._write_bounded_progress_report(root / sidecar_report, mcycle=1_000)
            loaded = json.loads((root / sidecar_report).read_text(encoding="utf-8"))
            loaded["run_vl_hybrid_timing"]["gpu_kernel_time_ms_total"] = 20_000.0
            loaded["phase_timing_s"] = {"run_vl_hybrid_wall_s": 22.0}
            (root / sidecar_report).write_text(json.dumps(loaded), encoding="utf-8")
            self._write_cpu_serial_baseline_report(root / cpu_report)

            summary = build_bounded_projection_usefulness_summary(
                sidecar_report_path=sidecar_report,
                cpu_baseline_report_path=cpu_report,
                case="VeeR-EL2:default:dhry",
                repo_root=root,
                min_progress_fraction=0.01,
                negative_ratio_threshold=10.0,
            )

        self.assertEqual(summary["status"], "incomplete")
        self.assertEqual(summary["errors"], [])
        self.assertLess(summary["progress_fraction_of_cpu_rtlmeter_cycles"], 0.01)
        self.assertFalse(summary["bounded_projection_evidence"])
        self.assertFalse(summary["negative_usefulness_decision"])
        self.assertFalse(summary["speedup_claimed"])
        self.assertFalse(summary["usefulness_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_mixed_state_gpu_cpu_summary_passes_without_speedup_claim(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_mixed_state_gpu_cpu_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gpu_report = "artifacts/veer/mixed/_sidecar/veer_el2_sidecar_executable_report.json"
            cpu_report = "reports/rtlmeter_cpu_mixed_program_parallel_baseline.json"
            self._write_mixed_gpu_sidecar_report(root / gpu_report)
            self._write_cpu_mixed_baseline_report(root / cpu_report)

            summary = build_mixed_state_gpu_cpu_summary(
                sidecar_report_path=gpu_report,
                cpu_baseline_report_path=cpu_report,
                repo_root=root,
            )

        self.assertEqual(summary["surface"], "rtlmeter_veer_el2_timing.mixed_state_gpu_cpu_summary")
        self.assertEqual(summary["status"], "mixed_state_gpu_smoke_passed")
        self.assertEqual(summary["recommended_action"], "continue_only_after_full_finish_stdout_or_definition_gate")
        self.assertEqual(summary["errors"], [])
        self.assertTrue(summary["gpu_mixed_state_preload"])
        self.assertEqual(summary["gpu_state_count"], 3)
        self.assertEqual(summary["cpu_case_count"], 3)
        self.assertEqual(summary["gpu_init_replication_mode"], "host_uploaded_concatenated_state_images")
        self.assertEqual(summary["cpu_parallel_wall_s"], 37.0)
        self.assertEqual(summary["gpu_run_vl_hybrid_wall_s"], 0.5)
        self.assertAlmostEqual(summary["gpu_wall_vs_cpu_parallel_ratio"], 0.5 / 37.0)
        self.assertTrue(summary["mixed_state_gpu_execution_claimed"])
        self.assertFalse(summary["timing_measured"])
        self.assertTrue(summary["bounded_timing_measured"])
        self.assertFalse(summary["full_program_timing_measured"])
        self.assertFalse(summary["speedup_claimed"])
        self.assertFalse(summary["usefulness_claimed"])
        self.assertFalse(summary["gpu_per_state_stdout_complete"])
        self.assertFalse(summary["gpu_per_state_cycles_complete"])
        self.assertFalse(
            summary["materially_different_definition_gate"]["required_before_more_gpu_performance_work"]
        )
        self.assertIn("state0 stdout does not prove", summary["non_claims"][2])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_mixed_state_gpu_cpu_summary_projects_negative_when_bounded_window_is_slow(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_mixed_state_gpu_cpu_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gpu_report = "artifacts/veer/mixed/_sidecar/veer_el2_sidecar_executable_report.json"
            cpu_report = "reports/rtlmeter_cpu_mixed_program_parallel_baseline.json"
            self._write_mixed_gpu_sidecar_report(root / gpu_report)
            gpu = json.loads((root / gpu_report).read_text(encoding="utf-8"))
            gpu["run_vl_hybrid_timing"]["gpu_kernel_time_ms_total"] = 20_000.0
            gpu["phase_timing_s"]["run_vl_hybrid_wall_s"] = 22.0
            gpu["parallel_state_validation"]["state_observables"] = [
                {"state_index": 0, "mcycle": 100_000},
                {"state_index": 1, "mcycle": 100_000},
                {"state_index": 2, "mcycle": 100_000},
            ]
            (root / gpu_report).write_text(json.dumps(gpu), encoding="utf-8")
            self._write_cpu_mixed_baseline_report(root / cpu_report)
            cpu = json.loads((root / cpu_report).read_text(encoding="utf-8"))
            cpu["comparison"] = [
                {"case": "VeeR-EL2:default:dhry", "parallel_cycles": 6_000_000},
                {"case": "VeeR-EL2:default:cmark", "parallel_cycles": 5_000_000},
                {"case": "VeeR-EL2:default:cmark_iccm", "parallel_cycles": 6_000_000},
            ]
            (root / cpu_report).write_text(json.dumps(cpu), encoding="utf-8")

            summary = build_mixed_state_gpu_cpu_summary(
                sidecar_report_path=gpu_report,
                cpu_baseline_report_path=cpu_report,
                repo_root=root,
            )

        self.assertEqual(summary["status"], "mixed_state_gpu_negative_projection")
        self.assertEqual(
            summary["recommended_action"],
            "stop_current_gpu_path_or_define_materially_different_implementation",
        )
        self.assertEqual(summary["cpu_max_parallel_cycles"], 6_000_000)
        self.assertEqual(summary["gpu_min_mcycle"], 100_000)
        self.assertEqual(summary["projection_scale_to_cpu_max_cycles"], 60.0)
        self.assertEqual(summary["projected_gpu_kernel_s_to_cpu_max_cycles"], 1200.0)
        self.assertEqual(summary["projected_gpu_kernel_vs_cpu_parallel_ratio"], 1200.0 / 37.0)
        self.assertTrue(summary["mixed_state_negative_projection_decision"])
        definition_gate = summary["materially_different_definition_gate"]
        self.assertTrue(definition_gate["required_before_more_gpu_performance_work"])
        self.assertEqual(
            definition_gate["current_observability_gap"],
            "per-state mixed-program stdout/cycle observability is incomplete",
        )
        self.assertIn(
            "per_state_finish_stdout_cycle_observability",
            definition_gate["requirements"],
        )
        self.assertEqual(definition_gate["owner"], "FC-037 / GitHub #2")
        self.assertFalse(summary["speedup_claimed"])
        self.assertFalse(summary["usefulness_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_same_window_trace_equivalence_summary_passes_for_matching_compare(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_same_window_trace_equivalence_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = "reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_50000.json"
            self._write_same_window_compare_report(root / report_path)

            summary = build_same_window_trace_equivalence_summary(
                report_paths=[report_path],
                repo_root=root,
                min_aligned_rows=49125,
                min_compared_fields=62,
            )

        self.assertEqual(summary["surface"], "rtlmeter_veer_el2_timing.same_window_trace_equivalence_summary")
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["report_count"], 1)
        self.assertEqual(summary["passed_report_count"], 1)
        self.assertTrue(summary["same_window_trace_equivalence_evidence"])
        self.assertEqual(summary["reports"][0]["aligned_rows"], 49125)
        self.assertEqual(summary["reports"][0]["compared_field_count"], 62)
        self.assertEqual(summary["reports"][0]["gpu_step_start"], 875)
        self.assertEqual(summary["reports"][0]["gpu_step_end"], 49999)
        self.assertEqual(summary["reports"][0]["excluded_fields"], ["pc_din"])
        self.assertFalse(summary["timing_measured"])
        self.assertTrue(summary["gpu_execution_claimed"])
        self.assertFalse(summary["speedup_claimed"])
        self.assertFalse(summary["usefulness_claimed"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_same_window_trace_equivalence_summary_fails_closed_for_mismatch_or_missing(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_same_window_trace_equivalence_summary

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mismatch = "reports/mismatch.json"
            missing = "reports/missing.json"
            self._write_same_window_compare_report(
                root / mismatch,
                status="mismatch",
                aligned_rows=49124,
                compared_field_count=62,
                mismatch_count=1,
                first_mismatch={"gpu_step": 900, "field": "pc"},
            )

            summary = build_same_window_trace_equivalence_summary(
                report_paths=[mismatch, missing],
                repo_root=root,
                min_aligned_rows=49125,
                min_compared_fields=62,
            )

        self.assertEqual(summary["status"], "incomplete")
        self.assertFalse(summary["same_window_trace_equivalence_evidence"])
        self.assertEqual(summary["passed_report_count"], 0)
        self.assertEqual(summary["failed_reports"], ["reports/mismatch.json", "reports/missing.json"])
        self.assertEqual(summary["missing_reports"], ["reports/missing.json"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_report_command_sanitizes_caller_absolute_paths(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        root = Path.cwd()
        report = build_veer_el2_timing_report(
            samples=3,
            execute=False,
            repo_root=root,
            cpu_execute_dir=str(root / "artifacts/cpu/VeeR-EL2/default/execute-0/hello"),
            sidecar_execute_dir=str(root / "artifacts/sidecar/hello"),
            state_image=str(root / "artifacts/state.json"),
            mdir=str(root / "artifacts/obj_dir"),
            sidecar_executable=str(root / "src/tools/veer_el2_sidecar_executable.py"),
            sidecar_nstates=4,
            cpu_parallel_report=str(root / "reports/cpu_parallel.json"),
        )

        self.assertEqual(report["sidecar_env"], {"VEER_EL2_SIDECAR_NSTATES": "4"})
        self.assertEqual(report["methodology"]["sidecar_nstates_override"], 4)
        self.assertEqual(report["launch_count_feasibility"]["status"], "missing_rtlmeter_cycles")
        self.assertEqual(report["command"][0], "VEER_EL2_SIDECAR_NSTATES=4")
        self.assertIn("artifacts/cpu/VeeR-EL2/default/execute-0/hello", report["command"])
        self.assertEqual(report["methodology"]["cpu_parallel_source"], "reports/cpu_parallel.json")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_launch_count_feasibility_passes_for_current_hello_cycles(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu_execute_dir = root / "artifacts/cpu/VeeR-EL2/default/execute-0/hello"
            (cpu_execute_dir / "_execute").mkdir(parents=True)
            (cpu_execute_dir / "_execute/stdout.log").write_text("TEST_PASSED\n", encoding="utf-8")
            (cpu_execute_dir / "_rtlmeter_cycles.txt").write_text("2229\n", encoding="utf-8")
            (cpu_execute_dir / "_execute/metrics.json").write_text(
                json.dumps({"VeeR-EL2:default:hello": {"execute": {"elapsed": 0.04, "clocks": 2229}}}),
                encoding="utf-8",
            )

            report = build_veer_el2_timing_report(
                samples=1,
                execute=False,
                repo_root=root,
                cpu_execute_dir="artifacts/cpu/VeeR-EL2/default/execute-0/hello",
            )

        feasibility = report["launch_count_feasibility"]
        self.assertEqual(feasibility["status"], "passed")
        self.assertTrue(feasibility["feasible"])
        self.assertEqual(feasibility["sidecar_clock_cycles"], 727)
        self.assertEqual(feasibility["estimated_pair_cycle_fusion_launched"], 727)
        self.assertEqual(feasibility["estimated_actual_timed_launches"], 733)
        self.assertFalse(report["timing_measured"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_blocks_cmark_scale_launch_count_before_bridge(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu_execute_dir = root / "artifacts/cpu/VeeR-EL2/default/execute-0/cmark"
            (cpu_execute_dir / "_execute").mkdir(parents=True)
            (cpu_execute_dir / "_execute/stdout.log").write_text("TEST_PASSED\n", encoding="utf-8")
            (cpu_execute_dir / "_rtlmeter_cycles.txt").write_text("5277908\n", encoding="utf-8")
            (cpu_execute_dir / "_execute/metrics.json").write_text(
                json.dumps({"VeeR-EL2:default:cmark": {"execute": {"elapsed": 32.66, "clocks": 5277908}}}),
                encoding="utf-8",
            )

            report = build_veer_el2_timing_report(
                case="VeeR-EL2:default:cmark",
                samples=1,
                execute=True,
                repo_root=root,
                cpu_execute_dir="artifacts/cpu/VeeR-EL2/default/execute-0/cmark",
                max_pair_cycle_fused_launches=100000,
                bridge_runner=lambda **kwargs: self.fail("launch-count blocked run must not invoke bridge"),
            )

        feasibility = report["launch_count_feasibility"]
        self.assertEqual(report["status"], "blocked_launch_count_feasibility")
        self.assertEqual(report["missing_prerequisites"], ["pair_cycle_launch_count_feasibility"])
        self.assertFalse(report["timing_measured"])
        self.assertFalse(report["gpu_execution_claimed"])
        self.assertEqual(feasibility["status"], "blocked_pair_cycle_launch_count")
        self.assertFalse(feasibility["feasible"])
        self.assertEqual(feasibility["sidecar_clock_cycles"], 5276406)
        self.assertEqual(feasibility["estimated_pair_cycle_fusion_launched"], 5276406)
        self.assertEqual(feasibility["estimated_actual_timed_launches"], 5276412)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_report_command_records_clock_patch_mode_env(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        with mock.patch.dict(
            "os.environ",
            {
                "VEER_EL2_SIDECAR_CLOCK_PATCH_MODE": "resident_pair_cycle",
                "VEER_EL2_SIDECAR_DISABLE_STEP_TRACE": "1",
                "VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT": "1",
                "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE": "1",
                "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP": "1",
                "VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING": "1",
                "VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS": "3",
            },
            clear=False,
        ):
            report = build_veer_el2_timing_report(samples=1, execute=False, sidecar_nstates=16)

        self.assertEqual(
            report["sidecar_env"],
            {
                "VEER_EL2_SIDECAR_CLOCK_PATCH_MODE": "resident_pair_cycle",
                "VEER_EL2_SIDECAR_DISABLE_STEP_TRACE": "1",
                "VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT": "1",
                "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE": "1",
                "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP": "1",
                "VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING": "1",
                "VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS": "3",
                "VEER_EL2_SIDECAR_NSTATES": "16",
            },
        )
        self.assertEqual(report["command"][0], "VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle")
        self.assertEqual(report["command"][1], "VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1")
        self.assertEqual(report["command"][2], "VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT=1")
        self.assertEqual(report["command"][3], "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1")
        self.assertEqual(report["command"][4], "VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP=1")
        self.assertEqual(report["command"][5], "VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING=1")
        self.assertEqual(report["command"][6], "VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS=3")
        self.assertEqual(report["command"][7], "VEER_EL2_SIDECAR_NSTATES=16")

    def test_in_process_hybrid_timing_repeats_block_cpu_wall_comparison(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import _summarize_samples
        from verilator_native_sidecar_make_driver import STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED

        summary = _summarize_samples(
            [
                {
                    "sidecar_bridge_status": STATUS_VEER_EL2_SIDECAR_COMPARE_PASSED,
                    "sidecar_wall_s": 1.0,
                    "sidecar_run_report": {
                        "parallel_state_count": 16,
                        "patch_drive_scope": "all_states",
                        "parallel_state_validation": {
                            "parallel_state_validation_status": "all_final_observables_match_state0"
                        },
                        "run_vl_hybrid_timing": {
                            "gpu_kernel_time_ms_total": 250.0,
                            "gpu_kernel_time_repeat_count": 3,
                        },
                    },
                }
            ],
            cpu_elapsed=0.04,
            parallel_wall=2.0,
            cpu_parallel_case_count=16,
        )

        self.assertEqual(summary["timing_comparison_scope"], "in_process_hybrid_repeat_diagnostic")
        self.assertFalse(summary["gpu_cpu_parallel_comparison_valid"])
        self.assertEqual(
            summary["cpu_parallel_wall_time_outcome"],
            "insufficient_comparable_cpu_parallel_baseline",
        )
        self.assertEqual(summary["serial_cpu_wall_time_outcome"], "insufficient_serial_cpu_baseline")
        self.assertEqual(summary["gpu_kernel_time_repeat_count_median"], 3.0)

    def test_invalid_sidecar_nstates_is_reported_without_execution(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        report = build_veer_el2_timing_report(
            samples=1,
            execute=True,
            sidecar_nstates=0,
            bridge_runner=lambda **kwargs: self.fail("invalid nstates must not invoke bridge"),
        )

        self.assertEqual(report["status"], "invalid_sidecar_nstates")
        self.assertEqual(report["missing_prerequisites"], ["sidecar_nstates"])
        self.assertFalse(report["timing_measured"])

    def test_execute_records_repeated_sidecar_timing_without_speedup_claim(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu_execute_dir = root / "artifacts/cpu/VeeR-EL2/default/execute-0/hello"
            (cpu_execute_dir / "_execute").mkdir(parents=True)
            (cpu_execute_dir / "_execute/stdout.log").write_text("TEST_PASSED\n", encoding="utf-8")
            (cpu_execute_dir / "_rtlmeter_cycles.txt").write_text("2229\n", encoding="utf-8")
            (cpu_execute_dir / "_execute/metrics.json").write_text(
                json.dumps(
                    {
                        "VeeR-EL2:default:hello": {
                            "execute": {
                                "elapsed": 0.04,
                                "user": 0.03,
                                "system": 0.01,
                                "memory": 8.756,
                                "clocks": 2229,
                                "speed": 55.725,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            cpu_parallel_report = root / "reports/cpu_parallel.json"
            cpu_parallel_report.parent.mkdir(parents=True)
            cpu_parallel_report.write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "cases": ["VeeR-EL2:default:hello"] * 8,
                        "case_instances": [
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_1"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_2"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_3"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_4"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_5"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_6"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_7"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_8"},
                        ],
                        "summary": {
                            "case_count": 8,
                            "max_workers": 8,
                            "serial_sum_case_wall_s": 2.0,
                            "parallel_wall_s": 1.0,
                            "parallel_speedup_vs_serial_sum": 2.0,
                            "parallel_efficiency": 1.0,
                            "all_runs_passed": True,
                            "all_observables_match": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            sidecar_execute_dir = root / "artifacts/sidecar/hello"

            def fake_bridge(**kwargs):
                self.assertEqual(kwargs["sidecar_env"], {"VEER_EL2_SIDECAR_NSTATES": "8"})
                run_report = sidecar_execute_dir / "_sidecar/veer_el2_sidecar_executable_report.json"
                run_report.parent.mkdir(parents=True, exist_ok=True)
                run_report.write_text(
                    json.dumps(
                        {
                            "status": "observables_emitted",
                            "mapped_fields_cache": {"status": "hit"},
                            "run_vl_hybrid_launcher_mode": "direct_hybrid_runtime",
                            "run_vl_hybrid_timing": {
                                "gpu_kernel_time_ms_total": 1.5,
                                "gpu_kernel_time_ms_per_launch": 0.75,
                                "gpu_kernel_timing_logical_step_count": 1457,
                                "gpu_kernel_timed_launch_count": 727,
                                "gpu_kernel_time_ms_per_actual_launch": 0.002063,
                            },
                            "phase_timing_s": {
                                "run_vl_hybrid_wall_s": 0.2,
                                "host_overhead_estimate_s": 0.8,
                                "total_sidecar_executable_s": 1.0,
                            },
                            "resident_patch_schedule": {
                                "logical": 1457,
                                "records": 23344,
                                "blocks": 3,
                            },
                            "clock_reset_patch": {
                                "patch_script_mode": "full_clock_reset_fields",
                                "logical_steps": 1457,
                            },
                            "patch_eval_fusion": {
                                "requested": True,
                                "available": True,
                                "launched": 1457,
                                "fallback": 0,
                                "mode": "state_grouped_patch_eval",
                            },
                            "pair_cycle_fusion": {
                                "requested": True,
                                "available": True,
                                "launched": 727,
                                "fallback": 0,
                                "mode": "low_eval_high_eval",
                            },
                            "pair_cycle_loop_fusion": {
                                "requested": True,
                                "available": True,
                                "kernel_launches": 1,
                                "cycles": 727,
                                "fallback": 0,
                                "chunk": 1000,
                                "mode": "looped_low_eval_high_eval",
                            },
                            "state_local_patch_schedule": {
                                "logical": 1457,
                                "records": 4371,
                                "blocks": 3,
                            },
                            "pair_cycle_state_local_fusion": {
                                "requested": True,
                                "available": True,
                                "launched": 727,
                                "fallback": 0,
                                "mode": "state_local_low_eval_high_eval",
                            },
                            "resident_pair_cycle": {
                                "requested": True,
                                "launched": 727,
                                "fallback": 0,
                                "start": 3,
                                "mode": "low_eval_high_eval",
                            },
                            "observables": {
                                "cycles": 2229,
                                "mcycle": 726,
                                "debug_path": str(root / "artifacts/sidecar/state.json"),
                                "stdout_stream_reconstructed": True,
                            },
                            "parallel_state_count": 8,
                            "init_replication_mode": "device_kernel",
                            "patch_drive_scope": "all_states",
                            "parallel_state_validation": {
                                "parallel_state_validation_status": "all_final_observables_match_state0",
                                "parallel_state_observables_match": True,
                                "parallel_state_matching_count": 8,
                            },
                            "stdout_trace_state_scope": "state0_only",
                            "step_trace_copy_mode": "device_buffered_coalesced_d2d_trace",
                            "step_trace_filter": {
                                "mode": "clock_high_after_reset",
                                "start": 4,
                                "stride": 2,
                                "rows": 727,
                                "capacity": 1457,
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                return {
                    "status": "verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed",
                    "missing_build_context": [],
                    "sidecar_executable_invocation_mode": "in_process_veer_el2_sidecar",
                    "phase_timing_s": {
                        "sidecar_executable_wall_s": 1.1,
                        "compare_observables_s": 0.01,
                        "total_bridge_s": 1.2,
                    },
                    "comparison": {
                        "status": "passed",
                        "normalized_stdout_match": True,
                        "cycle_count_match": True,
                        "cpu_cycles": 2229,
                        "gpu_cycles": 2229,
                    },
                }

            report = build_veer_el2_timing_report(
                samples=3,
                batches=2,
                execute=True,
                repo_root=root,
                cpu_execute_dir="artifacts/cpu/VeeR-EL2/default/execute-0/hello",
                sidecar_execute_dir="artifacts/sidecar/hello",
                cpu_parallel_report="reports/cpu_parallel.json",
                sidecar_nstates=8,
                bridge_runner=fake_bridge,
            )

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["timing_measured"])
        self.assertFalse(report["speedup_claimed"])
        self.assertEqual(report["batch_count"], 2)
        self.assertEqual(report["total_sample_count"], 6)
        self.assertTrue(report["summary"]["all_sidecar_samples_passed_correctness"])
        self.assertEqual(report["summary"]["cpu_reference_elapsed_s"], 0.04)
        self.assertEqual(report["summary"]["cpu_parallel_wall_s"], 1.0)
        self.assertTrue(report["summary"]["cpu_parallel_comparison_valid"])
        self.assertEqual(
            report["summary"]["cpu_parallel_wall_time_outcome"],
            "sidecar_faster_than_comparable_cpu_parallel_baseline",
        )
        self.assertIn(
            report["summary"]["preliminary_outcome"],
            {
                "sidecar_slower_than_serial_cpu",
                "sidecar_faster_than_serial_cpu",
                "sidecar_faster_than_comparable_cpu_parallel_baseline",
            },
        )
        self.assertEqual(report["summary"]["gpu_kernel_ms_total_median"], 1.5)
        self.assertEqual(report["summary"]["gpu_kernel_timing_logical_step_count_median"], 1457.0)
        self.assertEqual(report["summary"]["gpu_kernel_timed_launch_count_median"], 727.0)
        self.assertEqual(report["summary"]["gpu_kernel_time_ms_per_actual_launch_median"], 0.002063)
        self.assertEqual(
            report["summary"]["sidecar_executable_invocation_mode_counts"],
            {"in_process_veer_el2_sidecar": 6},
        )
        self.assertEqual(report["summary"]["run_vl_hybrid_launcher_mode_counts"], {"direct_hybrid_runtime": 6})
        self.assertEqual(report["summary"]["sidecar_parallel_state_count"], 8)
        self.assertEqual(report["summary"]["init_replication_mode_counts"], {"device_kernel": 6})
        self.assertEqual(
            report["summary"]["step_trace_copy_mode_counts"],
            {"device_buffered_coalesced_d2d_trace": 6},
        )
        self.assertEqual(
            report["summary"]["step_trace_filter_counts"],
            {"clock_high_after_reset:start=4,stride=2": 6},
        )
        self.assertEqual(report["summary"]["step_trace_filter_rows_median"], 727.0)
        self.assertEqual(report["summary"]["step_trace_filter_capacity_median"], 1457.0)
        self.assertEqual(report["summary"]["resident_patch_records_median"], 23344.0)
        self.assertEqual(report["summary"]["resident_patch_logical_steps_median"], 1457.0)
        self.assertEqual(report["summary"]["state_local_patch_records_median"], 4371.0)
        self.assertEqual(report["summary"]["state_local_patch_logical_steps_median"], 1457.0)
        self.assertEqual(report["summary"]["clock_patch_mode_counts"], {"full_clock_reset_fields": 6})
        self.assertEqual(report["summary"]["patch_eval_fusion_mode_counts"], {"state_grouped_patch_eval": 6})
        self.assertEqual(report["summary"]["patch_eval_fusion_available_counts"], {"true": 6})
        self.assertEqual(report["summary"]["patch_eval_fusion_launched_median"], 1457.0)
        self.assertEqual(report["summary"]["patch_eval_fusion_fallback_median"], 0.0)
        self.assertEqual(report["summary"]["pair_cycle_fusion_mode_counts"], {"low_eval_high_eval": 6})
        self.assertEqual(report["summary"]["pair_cycle_fusion_available_counts"], {"true": 6})
        self.assertEqual(report["summary"]["pair_cycle_fusion_launched_median"], 727.0)
        self.assertEqual(report["summary"]["pair_cycle_fusion_fallback_median"], 0.0)
        self.assertEqual(
            report["summary"]["pair_cycle_loop_fusion_mode_counts"],
            {"looped_low_eval_high_eval": 6},
        )
        self.assertEqual(report["summary"]["pair_cycle_loop_fusion_available_counts"], {"true": 6})
        self.assertEqual(report["summary"]["pair_cycle_loop_fusion_kernel_launches_median"], 1.0)
        self.assertEqual(report["summary"]["pair_cycle_loop_fusion_cycles_median"], 727.0)
        self.assertEqual(report["summary"]["pair_cycle_loop_fusion_fallback_median"], 0.0)
        self.assertEqual(report["summary"]["pair_cycle_loop_fusion_chunk_median"], 1000.0)
        self.assertEqual(
            report["summary"]["pair_cycle_state_local_fusion_mode_counts"],
            {"state_local_low_eval_high_eval": 6},
        )
        self.assertEqual(report["summary"]["pair_cycle_state_local_fusion_available_counts"], {"true": 6})
        self.assertEqual(report["summary"]["pair_cycle_state_local_fusion_launched_median"], 727.0)
        self.assertEqual(report["summary"]["pair_cycle_state_local_fusion_fallback_median"], 0.0)
        self.assertEqual(report["summary"]["resident_pair_cycle_mode_counts"], {"low_eval_high_eval": 6})
        self.assertEqual(report["summary"]["resident_pair_cycle_launched_median"], 727.0)
        self.assertEqual(report["summary"]["resident_pair_cycle_fallback_median"], 0.0)
        self.assertTrue(report["summary"]["parallel_state_validation_complete"])
        self.assertEqual(report["summary"]["sidecar_parallel_validation_status_counts"], {"all_final_observables_match_state0": 6})
        self.assertGreater(report["summary"]["sidecar_parallel_states_per_s_median"], 0.0)
        self.assertGreater(report["summary"]["sidecar_wall_s_per_parallel_state_median"], 0.0)
        self.assertEqual(report["summary"]["phase_timing_s_median"]["run_vl_hybrid_wall_s"], 0.2)
        self.assertEqual(report["summary"]["phase_timing_s_median"]["host_overhead_estimate_s"], 0.8)
        self.assertEqual(report["summary"]["bridge_phase_timing_s_median"]["sidecar_executable_wall_s"], 1.1)
        self.assertEqual(report["summary"]["mapped_fields_cache_status_counts"], {"hit": 6})
        self.assertEqual(report["summary"]["timing_stability"]["batch_count"], 2)
        self.assertEqual(report["summary"]["timing_stability"]["samples_per_batch"], 3)
        self.assertEqual(report["summary"]["timing_stability"]["total_sample_count"], 6)
        self.assertEqual(
            report["summary"]["timing_stability"]["timing_stability_outcome"],
            "stable_repeated_batch_outcome",
        )
        self.assertEqual(len(report["summary"]["batch_summaries"]), 2)
        self.assertEqual(len(report["sidecar_batches"]), 2)
        self.assertEqual(len(report["sidecar_samples"]), 6)
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_reports_mixed_batch_cpu_parallel_stability_without_claim(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu_execute_dir = root / "artifacts/cpu/VeeR-EL2/default/execute-0/hello"
            (cpu_execute_dir / "_execute").mkdir(parents=True)
            (cpu_execute_dir / "_execute/stdout.log").write_text("TEST_PASSED\n", encoding="utf-8")
            (cpu_execute_dir / "_rtlmeter_cycles.txt").write_text("2229\n", encoding="utf-8")
            (cpu_execute_dir / "_execute/metrics.json").write_text(
                json.dumps({"VeeR-EL2:default:hello": {"execute": {"elapsed": 0.04}}}),
                encoding="utf-8",
            )
            cpu_parallel_report = root / "reports/cpu_parallel.json"
            cpu_parallel_report.parent.mkdir(parents=True)
            cpu_parallel_report.write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "cases": ["VeeR-EL2:default:hello", "VeeR-EL2:default:hello"],
                        "case_instances": [
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_1"},
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_2"},
                        ],
                        "summary": {
                            "case_count": 2,
                            "max_workers": 2,
                            "parallel_wall_s": 1.0,
                            "all_runs_passed": True,
                            "all_observables_match": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            sidecar_execute_dir = root / "artifacts/sidecar/hello"
            phase_values = iter([0.8, 0.8, 1.2, 1.2])

            def fake_bridge(**kwargs):
                run_report = sidecar_execute_dir / "_sidecar/veer_el2_sidecar_executable_report.json"
                run_report.parent.mkdir(parents=True, exist_ok=True)
                phase = next(phase_values)
                run_report.write_text(
                    json.dumps(
                        {
                            "status": "observables_emitted",
                            "run_vl_hybrid_launcher_mode": "direct_hybrid_runtime",
                            "run_vl_hybrid_timing": {"gpu_kernel_time_ms_total": 1.5},
                            "phase_timing_s": {"run_vl_hybrid_wall_s": phase},
                            "parallel_state_count": 2,
                            "init_replication_mode": "device_kernel",
                            "patch_drive_scope": "all_states",
                            "parallel_state_validation": {
                                "parallel_state_validation_status": "all_final_observables_match_state0",
                                "parallel_state_observables_match": True,
                                "parallel_state_matching_count": 2,
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                return {
                    "status": "verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed",
                    "missing_build_context": [],
                    "sidecar_executable_invocation_mode": "in_process_veer_el2_sidecar",
                    "phase_timing_s": {"sidecar_executable_wall_s": phase},
                    "comparison": {"status": "passed", "normalized_stdout_match": True, "cycle_count_match": True},
                }

            with mock.patch(
                "rtlmeter_veer_el2_timing.time.monotonic",
                side_effect=[0.0, 0.8, 0.8, 1.6, 1.6, 2.8, 2.8, 4.0],
            ):
                report = build_veer_el2_timing_report(
                    samples=2,
                    batches=2,
                    execute=True,
                    repo_root=root,
                    cpu_execute_dir="artifacts/cpu/VeeR-EL2/default/execute-0/hello",
                    sidecar_execute_dir="artifacts/sidecar/hello",
                    cpu_parallel_report="reports/cpu_parallel.json",
                    bridge_runner=fake_bridge,
                )

        stability = report["summary"]["timing_stability"]
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["speedup_claimed"])
        self.assertEqual(stability["cpu_parallel_faster_batch_count"], 1)
        self.assertEqual(stability["cpu_parallel_slower_batch_count"], 1)
        self.assertFalse(stability["stable_cpu_parallel_outcome"])
        self.assertEqual(stability["timing_stability_outcome"], "unstable_mixed_cpu_parallel_outcomes")
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_rejects_single_or_mixed_cpu_parallel_baseline_as_incomplete(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cpu_execute_dir = root / "artifacts/cpu/VeeR-EL2/default/execute-0/hello"
            (cpu_execute_dir / "_execute").mkdir(parents=True)
            (cpu_execute_dir / "_execute/stdout.log").write_text("TEST_PASSED\n", encoding="utf-8")
            (cpu_execute_dir / "_rtlmeter_cycles.txt").write_text("2229\n", encoding="utf-8")
            (cpu_execute_dir / "_execute/metrics.json").write_text(
                json.dumps({"VeeR-EL2:default:hello": {"execute": {"elapsed": 0.04}}}),
                encoding="utf-8",
            )
            cpu_parallel_report = root / "reports/cpu_parallel.json"
            cpu_parallel_report.parent.mkdir(parents=True)
            cpu_parallel_report.write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "cases": ["VeeR-EL2:default:hello", "VeeR-EL2:default:cmark"],
                        "case_instances": [
                            {"case": "VeeR-EL2:default:hello", "case_instance": "hello_1"},
                            {"case": "VeeR-EL2:default:cmark", "case_instance": "cmark_1"},
                        ],
                        "summary": {
                            "case_count": 2,
                            "max_workers": 2,
                            "parallel_wall_s": 1.0,
                            "all_runs_passed": True,
                            "all_observables_match": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            sidecar_execute_dir = root / "artifacts/sidecar/hello"

            def fake_bridge(**kwargs):
                run_report = sidecar_execute_dir / "_sidecar/veer_el2_sidecar_executable_report.json"
                run_report.parent.mkdir(parents=True, exist_ok=True)
                run_report.write_text(
                    json.dumps(
                        {
                            "status": "observables_emitted",
                            "run_vl_hybrid_launcher_mode": "direct_hybrid_runtime",
                            "run_vl_hybrid_timing": {"gpu_kernel_time_ms_total": 1.5},
                            "parallel_state_count": 2,
                            "init_replication_mode": "device_kernel",
                            "patch_drive_scope": "all_states",
                            "parallel_state_validation": {
                                "parallel_state_validation_status": "all_final_observables_match_state0",
                                "parallel_state_observables_match": True,
                                "parallel_state_matching_count": 2,
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                return {
                    "status": "verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed",
                    "missing_build_context": [],
                    "sidecar_executable_invocation_mode": "in_process_veer_el2_sidecar",
                    "comparison": {"status": "passed", "normalized_stdout_match": True, "cycle_count_match": True},
                }

            report = build_veer_el2_timing_report(
                samples=2,
                execute=True,
                repo_root=root,
                cpu_execute_dir="artifacts/cpu/VeeR-EL2/default/execute-0/hello",
                sidecar_execute_dir="artifacts/sidecar/hello",
                cpu_parallel_report="reports/cpu_parallel.json",
                bridge_runner=fake_bridge,
            )

        self.assertEqual(report["status"], "incomplete")
        self.assertFalse(report["timing_measured"])
        self.assertFalse(report["summary"]["cpu_parallel_comparison_valid"])
        self.assertIn("cpu_parallel_baseline", report["missing_prerequisites"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_execute_is_incomplete_when_required_timing_evidence_is_missing(self) -> None:
        self.add_tools_to_path()
        from rtlmeter_veer_el2_timing import build_veer_el2_timing_report

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar_execute_dir = root / "artifacts/sidecar/hello"

            def fake_bridge(**kwargs):
                run_report = sidecar_execute_dir / "_sidecar/veer_el2_sidecar_executable_report.json"
                run_report.parent.mkdir(parents=True, exist_ok=True)
                run_report.write_text(json.dumps({"status": "observables_emitted"}), encoding="utf-8")
                return {
                    "status": "verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed",
                    "missing_build_context": [],
                    "sidecar_executable_invocation_mode": "in_process_veer_el2_sidecar",
                    "comparison": {
                        "status": "passed",
                        "normalized_stdout_match": True,
                        "cycle_count_match": True,
                    },
                }

            report = build_veer_el2_timing_report(
                samples=2,
                execute=True,
                repo_root=root,
                cpu_execute_dir="artifacts/cpu/VeeR-EL2/default/execute-0/hello",
                sidecar_execute_dir="artifacts/sidecar/hello",
                cpu_parallel_report="reports/cpu_parallel.json",
                bridge_runner=fake_bridge,
            )

        self.assertEqual(report["status"], "incomplete")
        self.assertFalse(report["timing_measured"])
        self.assertIn("serial_cpu_metrics", report["missing_prerequisites"])
        self.assertIn("serial_cpu_observables", report["missing_prerequisites"])
        self.assertIn("cpu_parallel_baseline", report["missing_prerequisites"])
        self.assertIn("gpu_kernel_timing", report["missing_prerequisites"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_cli_dry_run_outputs_json(self) -> None:
        result = self.run_python_tool("src/tools/rtlmeter_veer_el2_timing.py", "--samples", "2", "--batches", "3", check=True)

        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "opt_in_required")
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["batch_count"], 3)
        self.assertEqual(report["total_sample_count"], 6)
        self.assert_no_local_absolute_paths(result.stdout)
