import json
import sys
import tempfile
from pathlib import Path

from tests.contract.hybrid_cli_helpers import TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_hybrid_candidate_summary import build_summary  # noqa: E402


class RtlmeterVortexHybridCandidateSummaryTest(HybridCliTestCase):
    def _write_blocked_candidate(self, root: Path) -> Path:
        work = root / "artifacts" / "vortex_hybrid"
        verilate = work / "Vortex" / "mini" / "compile-0" / "_verilate"
        verilate.mkdir(parents=True)
        verilate.joinpath("status").write_text("failure", encoding="utf-8")
        verilate.joinpath("cmd").write_text(
            "verilator --cc --sim-accel sidecar-gpu --sim-accel-states 1 --sim-accel-steps 1",
            encoding="utf-8",
        )
        verilate.joinpath("stdout.log").write_text("%Error: Invalid option: --sim-accel\n", encoding="utf-8")
        return work

    def _write_wrapper_blocked_candidate(self, root: Path) -> Path:
        work = root / "artifacts" / "vortex_hybrid_wrapper"
        verilate = work / "Vortex" / "mini" / "compile-0" / "_verilate"
        verilate.mkdir(parents=True)
        verilate.joinpath("status").write_text("failure", encoding="utf-8")
        verilate.joinpath("cmd").write_text(
            "verilator --cc --sim-accel sidecar-gpu --sim-accel-states 1 --sim-accel-steps 1",
            encoding="utf-8",
        )
        payload = {
            "schema_version": 1,
            "surface": "rtlmeter_verilator_wrapper_runtime",
            "status": "rtlmeter_sidecar_execution_handoff_blocked_missing_reviewed_source_closure",
            "cpu_as_gpu_fallback": False,
            "sidecar_execution_invoked": False,
            "wrapper_inspection": {
                "surface": "rtlmeter_verilator_path_wrapper",
                "status": "ready_for_rtlmeter_sidecar_planning",
                "sidecar_accel": "sidecar-gpu",
                "sidecar_states": "1",
                "sidecar_steps": "1",
            },
            "handoff_metadata": {
                "status": "rtlmeter_sidecar_handoff_blocked_missing_context",
                "missing_sidecar_context": ["target", "source_closure"],
            },
            "launcher_invocation": {
                "status": "rtlmeter_sidecar_launcher_invocation_blocked",
                "sidecar_execution_invoked": False,
            },
            "sidecar_authority_registry": {
                "target": "rtlmeter_example_kind_hello",
                "runtime_launchable": False,
            },
        }
        prefixed = "\n".join(f"    0.11 | {line}" for line in json.dumps(payload, indent=2).splitlines())
        verilate.joinpath("stdout.log").write_text(prefixed + "\n", encoding="utf-8")
        return work

    def _write_wrapper_authority_blocked_candidate(self, root: Path) -> Path:
        work = root / "artifacts" / "vortex_hybrid_context"
        verilate = work / "Vortex" / "mini" / "compile-0" / "_verilate"
        verilate.mkdir(parents=True)
        verilate.joinpath("status").write_text("failure", encoding="utf-8")
        verilate.joinpath("cmd").write_text(
            "verilator --cc --sim-accel sidecar-gpu --sim-accel-states 1 --sim-accel-steps 1",
            encoding="utf-8",
        )
        payload = {
            "schema_version": 1,
            "surface": "rtlmeter_verilator_wrapper_runtime",
            "status": "rtlmeter_sidecar_execution_handoff_blocked_missing_authority_registry_source_closure",
            "cpu_as_gpu_fallback": False,
            "sidecar_execution_invoked": False,
            "wrapper_inspection": {
                "surface": "rtlmeter_verilator_path_wrapper",
                "status": "ready_for_rtlmeter_sidecar_planning",
                "sidecar_accel": "sidecar-gpu",
                "sidecar_states": "1",
                "sidecar_steps": "1",
            },
            "handoff_metadata": {
                "status": "rtlmeter_sidecar_handoff_metadata_ready",
                "missing_sidecar_context": [],
            },
            "stdout_cycles_execution_plan": {
                "seed": "Vortex:mini:hello",
                "authority_registry": "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json",
                "gpu_candidate": {
                    "work_root": "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu",
                    "observable_execute_dir": (
                        "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/execute-0/hello"
                    ),
                },
            },
            "stdout_cycles_runner_contract": {
                "status": "rtlmeter_stdout_cycles_runner_contract_blocked",
                "missing_runner_context": [
                    "authority_registry.source_closure.status",
                    "authority_registry.source_closure.review_evidence",
                ],
            },
        }
        prefixed = "\n".join(f"    0.11 | {line}" for line in json.dumps(payload, indent=2).splitlines())
        verilate.joinpath("stdout.log").write_text(prefixed + "\n", encoding="utf-8")
        return work

    def _write_wrapper_sidecar_verilate_blocked_candidate(self, root: Path) -> Path:
        work = root / "artifacts" / "vortex_hybrid_sidecar_verilate"
        verilate = work / "Vortex" / "mini" / "compile-0" / "_verilate"
        verilate.mkdir(parents=True)
        verilate.joinpath("status").write_text("failure", encoding="utf-8")
        verilate.joinpath("cmd").write_text(
            "verilator --cc --sim-accel sidecar-gpu --sim-accel-states 1 --sim-accel-steps 1",
            encoding="utf-8",
        )
        payload = {
            "schema_version": 1,
            "surface": "rtlmeter_verilator_wrapper_runtime",
            "status": "rtlmeter_sidecar_execution_handoff_blocked_sidecar_verilate_execution",
            "cpu_as_gpu_fallback": False,
            "sidecar_execution_invoked": False,
            "wrapper_inspection": {
                "surface": "rtlmeter_verilator_path_wrapper",
                "status": "ready_for_rtlmeter_sidecar_planning",
                "sidecar_accel": "sidecar-gpu",
                "sidecar_states": "1",
                "sidecar_steps": "1",
            },
            "handoff_metadata": {"status": "rtlmeter_sidecar_handoff_metadata_ready"},
            "stdout_cycles_execution_plan": {
                "seed": "Vortex:mini:hello",
                "authority_registry": "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json",
                "gpu_candidate": {
                    "work_root": "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu",
                    "observable_execute_dir": (
                        "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/execute-0/hello"
                    ),
                },
            },
            "stdout_cycles_runner_contract": {
                "status": "rtlmeter_stdout_cycles_runner_contract_ready",
                "missing_runner_context": [],
            },
            "stdout_cycles_runner_adapter_implementation": {
                "status": "rtlmeter_stdout_cycles_runner_adapter_implementation_runner_argv_ready",
                "runner_command_argv": ["python3", "src/tools/rtlmeter_stdout_cycles_sidecar_runner.py"],
            },
            "reentry_guard": {
                "status": "rtlmeter_wrapper_reentry_guard_blocked_recursive_rtlmeter_run",
                "direct_sidecar_verilate_phase_allowed": False,
            },
        }
        prefixed = "\n".join(f"    0.11 | {line}" for line in json.dumps(payload, indent=2).splitlines())
        verilate.joinpath("stdout.log").write_text(prefixed + "\n", encoding="utf-8")
        return work

    def _write_runner_observables_ready_proxy_blocked(self, root: Path) -> Path:
        report = root / "reports" / "runner.json"
        report.parent.mkdir(parents=True)
        report.write_text(
            json.dumps(
                {
                    "status": "rtlmeter_stdout_cycles_sidecar_runner_observables_ready",
                    "observables_ready": True,
                    "missing_observables": [],
                    "cycle_count": 40897,
                    "execution_performed": True,
                    "rtlmeter_proxy_handoff_observed": False,
                    "gpu_execution_claimed": False,
                    "timing_measured": False,
                    "speedup_claimed": False,
                }
            ),
            encoding="utf-8",
        )
        return report

    def _write_runner_proxy_handoff_observed(self, root: Path) -> Path:
        report = root / "reports" / "runner_proxy.json"
        report.parent.mkdir(parents=True)
        report.write_text(
            json.dumps(
                {
                    "status": "rtlmeter_stdout_cycles_sidecar_runner_observables_ready",
                    "observables_ready": True,
                    "missing_observables": [],
                    "cycle_count": 40897,
                    "execution_performed": True,
                    "rtlmeter_proxy_handoff_observed": True,
                    "reviewed_proxy_metadata_observed": True,
                    "gpu_execution_claimed": False,
                    "timing_measured": False,
                    "speedup_claimed": False,
                }
            ),
            encoding="utf-8",
        )
        return report

    def _write_observable_authority_audit_proxy_and_fake_ready(self, root: Path) -> Path:
        report = root / "reports" / "observable_authority_audit.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "status": "observable_authority_audit_proxy_and_fake_ready_real_runtime_missing",
                    "proxy_handoff_observed": True,
                    "generated_fake_driver_authority_passed": True,
                    "real_verilator_lowered_tb_runtime_call_observed": False,
                    "fake_driver_materialized_runtime_args_call_observed": True,
                    "real_cuda_materialized_runtime_args_call_observed": False,
                    "real_verilator_memory_helper_call_observed": False,
                    "real_verilator_dpi_memory_helper_call_observed": False,
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
                    "real_vortex_kernel_artifact_ready": False,
                    "real_vortex_kernel_artifact_status": "real_vortex_kernel_artifact_missing",
                    "real_vortex_kernel_artifact_count": 0,
                    "kernel_artifact_build_attempt_status": "failed_broken_module_landingpad_personality",
                    "kernel_artifact_build_landingpad_blocked": True,
                    "kernel_artifact_build_attempt_next_required_boundary": "fix_vortex_lowered_ir_landingpad_personality_before_kernel_artifact",
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
                    "real_runtime_observable_authority_ready": False,
                    "next_required_boundary": (
                        "replace_probe_markers_with_real_generated_lowered_tb_runtime_and_memory_calls"
                    ),
                    "missing_prerequisites": [
                        "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
                        "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
                        "real_runtime_execution_reports_vortex_observable_authority",
                        "cpu_vs_hybrid_timing_report.vortex",
                    ],
                }
            ),
            encoding="utf-8",
        )
        return report

    def test_summary_classifies_invalid_verilator_gpu_option(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_blocked_candidate(root)

            report = build_summary(root, work_root=work)

        self.assertEqual(report["status"], "hybrid_candidate_blocked_invalid_verilator_option")
        self.assertTrue(report["invalid_sim_accel_option"])
        self.assertFalse(report["hybrid_candidate_executed"])
        self.assertFalse(report["measurement_ready"])
        self.assertIn("path_selected_sidecar_capable_verilator_or_wrapper", report["readiness_delta"]["still_missing_for_measurement"])
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_summary_classifies_wrapper_captured_missing_source_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_wrapper_blocked_candidate(root)

            report = build_summary(root, work_root=work)

        self.assertEqual(report["status"], "hybrid_candidate_blocked_missing_reviewed_vortex_sidecar_context")
        self.assertFalse(report["invalid_sim_accel_option"])
        self.assertTrue(report["wrapper_captured_sidecar_planning"])
        self.assertEqual(report["wrapper_runtime_status"], "rtlmeter_sidecar_execution_handoff_blocked_missing_reviewed_source_closure")
        self.assertEqual(report["wrapper_inspection_status"], "ready_for_rtlmeter_sidecar_planning")
        self.assertEqual(report["wrapper_sidecar_accel"], "sidecar-gpu")
        self.assertEqual(report["wrapper_sidecar_states"], "1")
        self.assertEqual(report["wrapper_sidecar_steps"], "1")
        self.assertEqual(report["handoff_status"], "rtlmeter_sidecar_handoff_blocked_missing_context")
        self.assertFalse(report["sidecar_execution_invoked"])
        self.assertFalse(report["hybrid_candidate_executed"])
        self.assertFalse(report["cpu_as_gpu_fallback"])
        self.assertIn(
            "reviewed_vortex_sidecar_context_for_wrapper_handoff",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assertNotIn(
            "path_selected_sidecar_capable_verilator_or_wrapper",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_summary_classifies_wrapper_context_ready_but_authority_registry_source_closure_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_wrapper_authority_blocked_candidate(root)

            report = build_summary(root, work_root=work)

        self.assertEqual(report["status"], "hybrid_candidate_blocked_missing_vortex_authority_registry_source_closure")
        self.assertTrue(report["wrapper_captured_sidecar_planning"])
        self.assertTrue(report["handoff_metadata_ready"])
        self.assertTrue(report["blocked_missing_authority_registry_source_closure"])
        self.assertFalse(report["blocked_missing_reviewed_source_closure"])
        self.assertEqual(report["stdout_cycles_plan_seed"], "Vortex:mini:hello")
        self.assertEqual(
            report["stdout_cycles_plan_authority_registry"],
            "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json",
        )
        self.assertEqual(report["runner_contract_status"], "rtlmeter_stdout_cycles_runner_contract_blocked")
        self.assertIn(
            "reviewed_vortex_authority_registry_source_closure",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assertNotIn(
            "reviewed_vortex_sidecar_context_for_wrapper_handoff",
            report["readiness_delta"]["still_missing_for_measurement"],
        )

    def test_summary_classifies_sidecar_verilate_execution_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_wrapper_sidecar_verilate_blocked_candidate(root)

            report = build_summary(root, work_root=work)

        self.assertEqual(report["status"], "hybrid_candidate_blocked_sidecar_verilate_execution")
        self.assertTrue(report["blocked_sidecar_verilate_execution"])
        self.assertTrue(report["handoff_metadata_ready"])
        self.assertEqual(report["runner_contract_status"], "rtlmeter_stdout_cycles_runner_contract_ready")
        self.assertTrue(report["runner_command_ready"])
        self.assertEqual(
            report["adapter_implementation_status"],
            "rtlmeter_stdout_cycles_runner_adapter_implementation_runner_argv_ready",
        )
        self.assertEqual(
            report["reentry_guard_status"],
            "rtlmeter_wrapper_reentry_guard_blocked_recursive_rtlmeter_run",
        )
        self.assertIn(
            "direct_sidecar_verilate_execution_or_vsim_proxy_for_vortex",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assertNotIn(
            "reviewed_vortex_authority_registry_source_closure",
            report["readiness_delta"]["still_missing_for_measurement"],
        )

    def test_summary_separates_stdout_cycles_observation_from_hybrid_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_wrapper_sidecar_verilate_blocked_candidate(root)
            runner_report = self._write_runner_observables_ready_proxy_blocked(root)

            report = build_summary(root, work_root=work, runner_report_path=runner_report)

        self.assertEqual(report["status"], "hybrid_candidate_stdout_cycles_observed_proxy_handoff_blocked")
        self.assertTrue(report["runner_observables_ready"])
        self.assertTrue(report["runner_execution_performed"])
        self.assertEqual(report["runner_cycle_count"], 40897)
        self.assertFalse(report["runner_proxy_handoff_observed"])
        self.assertFalse(report["hybrid_candidate_executed"])
        self.assertFalse(report["measurement_ready"])
        self.assertFalse(report["runner_gpu_execution_claimed"])
        self.assertFalse(report["runner_timing_measured"])
        self.assertFalse(report["runner_speedup_claimed"])
        self.assertIn(
            "reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assertNotIn(
            "direct_sidecar_verilate_execution_or_vsim_proxy_for_vortex",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_summary_records_proxy_handoff_without_gpu_execution_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_wrapper_sidecar_verilate_blocked_candidate(root)
            runner_report = self._write_runner_proxy_handoff_observed(root)

            report = build_summary(root, work_root=work, runner_report_path=runner_report)

        self.assertEqual(report["status"], "hybrid_candidate_proxy_handoff_observed_timing_missing")
        self.assertTrue(report["runner_observables_ready"])
        self.assertTrue(report["runner_proxy_handoff_observed"])
        self.assertEqual(report["runner_cycle_count"], 40897)
        self.assertFalse(report["hybrid_candidate_executed"])
        self.assertFalse(report["measurement_ready"])
        self.assertFalse(report["runner_gpu_execution_claimed"])
        self.assertFalse(report["runner_timing_measured"])
        self.assertFalse(report["runner_speedup_claimed"])
        self.assertIn(
            "hybrid_observable_authority",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assertNotIn(
            "reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assert_no_local_absolute_paths(json.dumps(report, sort_keys=True))

    def test_summary_consumes_observable_authority_audit_without_claiming_real_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_wrapper_sidecar_verilate_blocked_candidate(root)
            runner_report = self._write_runner_proxy_handoff_observed(root)
            audit_report = self._write_observable_authority_audit_proxy_and_fake_ready(root)

            report = build_summary(
                root,
                work_root=work,
                runner_report_path=runner_report,
                observable_authority_audit_path=audit_report,
            )

        self.assertEqual(report["status"], "hybrid_candidate_proxy_handoff_observed_timing_missing")
        self.assertEqual(
            report["observable_authority_audit_status"],
            "observable_authority_audit_proxy_and_fake_ready_real_runtime_missing",
        )
        self.assertTrue(report["proxy_handoff_observable_evidence_ready"])
        self.assertTrue(report["generated_fake_driver_authority_passed"])
        self.assertFalse(report["real_verilator_lowered_tb_runtime_call_observed"])
        self.assertTrue(report["fake_driver_materialized_runtime_args_call_observed"])
        self.assertFalse(report["real_cuda_materialized_runtime_args_call_observed"])
        self.assertFalse(report["real_verilator_memory_helper_call_observed"])
        self.assertFalse(report["real_verilator_dpi_memory_helper_call_observed"])
        self.assertTrue(report["real_verilator_runtime_bridge_stub_observed"])
        self.assertTrue(report["real_verilator_runtime_bridge_stub_rebuilt"])
        self.assertTrue(report["real_verilator_runtime_invocation_probe_observed"])
        self.assertTrue(report["real_verilator_runtime_invocation_probe_rebuilt"])
        self.assertTrue(report["real_verilator_runtime_invocation_probe_executed"])
        self.assertTrue(report["real_verilator_materialized_runtime_args_probe_observed"])
        self.assertTrue(report["real_verilator_materialized_runtime_args_probe_rebuilt"])
        self.assertTrue(report["real_verilator_materialized_runtime_args_probe_executed"])
        self.assertTrue(report["real_cuda_materialized_runtime_smoke_passed"])
        self.assertEqual(report["real_cuda_materialized_runtime_smoke_returncode"], 0)
        self.assertIsNone(report["real_cuda_materialized_runtime_smoke_probe_status"])
        self.assertFalse(report["real_vortex_kernel_artifact_ready"])
        self.assertEqual(report["real_vortex_kernel_artifact_status"], "real_vortex_kernel_artifact_missing")
        self.assertEqual(report["real_vortex_kernel_artifact_count"], 0)
        self.assertEqual(report["kernel_artifact_build_attempt_status"], "failed_broken_module_landingpad_personality")
        self.assertTrue(report["kernel_artifact_build_landingpad_blocked"])
        self.assertTrue(report["real_cuda_memory_transport_passed"])
        self.assertEqual(report["real_cuda_memory_transport_h2d_bytes"], 37224)
        self.assertEqual(report["real_cuda_memory_transport_d2h_initial_bytes"], 88)
        self.assertTrue(report["real_cuda_runtime_sequence_preflight_passed"])
        self.assertEqual(report["real_cuda_runtime_sequence_preflight_h2d_bytes"], 37224)
        self.assertEqual(report["real_cuda_runtime_sequence_preflight_d2h_initial_bytes"], 88)
        self.assertEqual(report["real_cuda_runtime_sequence_preflight_dcr_applied_count"], 9)
        self.assertTrue(report["real_cuda_preflight_authority_report_ready"])
        self.assertTrue(report["real_cuda_preflight_authority_passed"])
        self.assertEqual(report["real_cuda_preflight_authority_source"], "memory_post_condition")
        self.assertTrue(report["probe_or_marker_boundary_observed"])
        self.assertTrue(report["generated_lowered_tb_runtime_call_blocked_by_probe_markers"])
        self.assertTrue(report["generated_lowered_tb_memory_helper_call_blocked_by_probe_markers"])
        self.assertEqual(
            report["next_required_boundary"],
            "replace_probe_markers_with_real_generated_lowered_tb_runtime_and_memory_calls",
        )
        self.assertFalse(report["real_runtime_observable_authority_ready"])
        self.assertFalse(report["hybrid_observable_authority_ready"])
        self.assertIn(
            "real_runtime_execution_reports_vortex_observable_authority",
            report["readiness_delta"]["still_missing_for_measurement"],
        )
        self.assertNotIn(
            "hybrid_observable_authority",
            report["readiness_delta"]["still_missing_for_measurement"],
        )

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            work = self._write_blocked_candidate(root)
            out = root / "reports" / "vortex_hybrid_candidate.json"

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_hybrid_candidate_summary.py",
                "--repo-root",
                root.as_posix(),
                "--work-root",
                work.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_hybrid_candidate_summary")
        self.assertEqual(report_payload["status"], "hybrid_candidate_blocked_invalid_verilator_option")
        self.assert_no_local_absolute_paths(result.stdout)


if __name__ == "__main__":
    import unittest

    unittest.main()
