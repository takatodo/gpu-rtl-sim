import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR, HybridCliTestCase

sys.path.insert(0, TOOLS_DIR.as_posix())

from rtlmeter_vortex_first_gate_readiness import build_readiness  # noqa: E402


class RtlmeterVortexFirstGateReadinessTest(HybridCliTestCase):
    def _write_vortex_descriptor(self, root: Path) -> None:
        design = root / "third_party" / "rtlmeter" / "designs" / "Vortex"
        tests = design / "tests" / "hello"
        tests.mkdir(parents=True, exist_ok=True)
        for name in ("dcrs.bin", "init.bin", "post.bin"):
            (tests / name).write_bytes(b"demo")
        (design / "descriptor.yaml").write_text(
            "\n".join(
                [
                    "compile:",
                    "  verilogSourceFiles:",
                    "    - src/tb.sv",
                    "    - src/Vortex.sv",
                    "  verilogIncludeFiles:",
                    "    - src/VX_define.vh",
                    "  cppSourceFiles:",
                    "    - src/dpi/memory.cpp",
                    "  topModule: tb",
                    "  mainClock: tb.clk",
                    "execute:",
                    "  common:",
                    "    postHook: tests/post.bash",
                    "  tests:",
                    "    hello:",
                    "      files:",
                    "        - tests/hello/dcrs.bin",
                    "        - tests/hello/init.bin",
                    "        - tests/hello/post.bin",
                    "configurations:",
                    "  mini:",
                    "    execute:",
                    "      tests:",
                    "        hello:",
                    "          tags: [ sanity ]",
                    "        saxpy: {}",
                    "        sgemm: {}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_authority(self, root: Path) -> None:
        path = root / "config" / "rtlmeter_sidecar_authorities" / "rtlmeter_vortex_mini_hello.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "schema_role": "rtlmeter_sidecar_authority",
                    "status": "blocked_vortex_dpi_memory_and_gpu_observable_review",
                    "runtime_launchable": False,
                    "target": "rtlmeter_vortex_mini_hello",
                    "rtlmeter_case": "Vortex:mini:hello",
                    "coverage_output_target": "rtlmeter_stdout_pass_and_memory_post_condition",
                }
            ),
            encoding="utf-8",
        )

    def _write_template(self, root: Path) -> None:
        path = root / "config" / "slice_launch_templates" / "vortex_mini_hello.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "candidate_fail_closed",
                    "target": "Vortex.mini_hello",
                    "top_module": "tb",
                    "runtime_launchable": False,
                    "build": {
                        "mdir": "artifacts/vortex_mini_hello_obj_dir",
                        "host_probe_target": "vortex_mini_hello_host_probe",
                    },
                    "source_files": [
                        "third_party/rtlmeter/designs/Vortex/src/tb.sv",
                    ],
                    "source_closure": {
                        "status": "incomplete",
                        "missing_required_sources": ["dpi_memory_bridge_lowering"],
                    },
                    "acceptance": {
                        "non_dry_run_must_fail_until_source_closure_complete": True,
                        "speedup_claim_allowed_by_template_alone": False,
                    },
                }
            ),
            encoding="utf-8",
        )

    def _write_bridge_review(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_dpi_memory_bridge_review.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_dpi_memory_bridge_review",
                    "status": "reviewed_blocked_on_gpu_bridge_implementation",
                    "reviewed_bridge_boundary": True,
                    "implementation_ready": False,
                    "gpu_observable_ready": False,
                    "device_helper_ready_for_integration": True,
                    "device_helper_header": "src/hybrid/vortex_memory_model_device.h",
                    "device_buffers_materialized_for_upload": True,
                    "device_buffer_materialization": {
                        "status": "device_buffers_materialized",
                        "host_to_device_bytes": 37224,
                    },
                    "dcr_schedule_materialized": True,
                    "dcr_schedule": {
                        "status": "dcr_schedule_materialized",
                        "write_count": 9,
                        "device_schedule_bytes": 72,
                        "runtime_launchable": False,
                    },
                    "runtime_upload_helper_ready": True,
                    "runtime_upload_header": "src/hybrid/vortex_runtime_upload.h",
                    "observable_export_helper_ready": True,
                    "observable_export_header": "src/hybrid/vortex_observable_export.h",
                    "runtime_sequence_helper_ready": True,
                    "runtime_sequence_header": "src/hybrid/vortex_runtime_sequence.h",
                    "runtime_sequence": {
                        "helper_ready": True,
                        "invokes_upload_helper": True,
                        "invokes_observable_export_helper": True,
                        "applies_dcr_with_reset_asserted_summary": True,
                        "runtime_launchable": False,
                    },
                    "materialized_runtime_invocation_smoke_ready": True,
                    "materialized_runtime_invocation_smoke": {
                        "status": "materialized_runtime_invocation_smoke_ready_not_integrated",
                        "smoke_ready": True,
                        "host_to_device_bytes": 37224,
                        "device_to_host_initial_bytes": 88,
                        "runtime_launchable": False,
                    },
                    "generated_lowered_tb_invocation_smoke_passed": True,
                    "generated_lowered_tb_invocation_smoke": {
                        "status": "generated_lowered_tb_invocation_smoke_passed",
                        "generated_lowered_tb_invocation_smoke_passed": True,
                        "host_to_device_bytes": 37224,
                        "device_to_host_initial_bytes": 88,
                        "runtime_launchable": False,
                    },
                    "binary_input_summary": {
                        "status": "parsed",
                        "init_segment_count": 9,
                        "dcr_write_count": 9,
                    },
                    "gpu_memory_model_plan": {
                        "status": "abi_plan_ready",
                        "minimum_static_input_bytes": 37224,
                    },
                    "memory_model_reference": {
                        "status": "reference_validated",
                        "reference_semantics_ready": True,
                    },
                    "missing_prerequisites": [
                        "gpu_memory_model_for_64B_block_reads_writes_and_byteen",
                        "gpu_post_bin_memory_compare_or_export",
                        "runtime_execution_invokes_vortex_runtime_sequence_helper",
                        "stdout_TEST_PASSED_or_memory_post_condition_gpu_observable",
                    ],
                }
            ),
            encoding="utf-8",
        )

    def _write_source_closure_report(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_source_closure.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_source_closure",
                    "status": "descriptor_source_closure_complete",
                    "all_sources_exist": True,
                    "source_counts": {
                        "verilog": 126,
                        "include": 8,
                        "cpp": 1,
                        "total": 135,
                    },
                    "execution_authority": {
                        "runtime_launchable": False,
                    },
                }
            ),
            encoding="utf-8",
        )

    def _write_cpu_reference(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_cpu_reference_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_cpu_reference_summary",
                    "status": "cpu_reference_passed",
                    "case": "Vortex:mini:hello",
                    "cpu_reference_ready_for_hybrid_compare": True,
                    "stdout_test_passed": True,
                    "finish_observed": True,
                    "dcr_write_count": 9,
                    "metrics": {
                        "execute_elapsed_s": 0.22,
                        "execute_speed_khz": 185.89545454545453,
                        "execute_clocks": 40897,
                    },
                }
            ),
            encoding="utf-8",
        )

    def _write_wrapper_blocked_hybrid_candidate(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_hybrid_candidate_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_hybrid_candidate_summary",
                    "status": "hybrid_candidate_blocked_missing_reviewed_vortex_sidecar_context",
                    "invalid_sim_accel_option": False,
                    "wrapper_captured_sidecar_planning": True,
                    "wrapper_runtime_status": (
                        "rtlmeter_sidecar_execution_handoff_blocked_missing_reviewed_source_closure"
                    ),
                    "wrapper_inspection_status": "ready_for_rtlmeter_sidecar_planning",
                    "wrapper_sidecar_accel": "sidecar-gpu",
                    "wrapper_sidecar_states": "1",
                    "wrapper_sidecar_steps": "1",
                    "blocked_missing_reviewed_source_closure": True,
                    "sidecar_execution_invoked": False,
                    "hybrid_candidate_executed": False,
                    "measurement_ready": False,
                }
            ),
            encoding="utf-8",
        )

    def _write_authority_blocked_hybrid_candidate(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_hybrid_candidate_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_hybrid_candidate_summary",
                    "status": "hybrid_candidate_blocked_missing_vortex_authority_registry_source_closure",
                    "invalid_sim_accel_option": False,
                    "wrapper_captured_sidecar_planning": True,
                    "wrapper_runtime_status": (
                        "rtlmeter_sidecar_execution_handoff_blocked_missing_authority_registry_source_closure"
                    ),
                    "wrapper_inspection_status": "ready_for_rtlmeter_sidecar_planning",
                    "wrapper_sidecar_accel": "sidecar-gpu",
                    "wrapper_sidecar_states": "1",
                    "wrapper_sidecar_steps": "1",
                    "blocked_missing_reviewed_source_closure": False,
                    "blocked_missing_authority_registry_source_closure": True,
                    "handoff_metadata_ready": True,
                    "stdout_cycles_plan_seed": "Vortex:mini:hello",
                    "stdout_cycles_plan_authority_registry": (
                        "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json"
                    ),
                    "runner_contract_status": "rtlmeter_stdout_cycles_runner_contract_blocked",
                    "sidecar_execution_invoked": False,
                    "hybrid_candidate_executed": False,
                    "measurement_ready": False,
                }
            ),
            encoding="utf-8",
        )

    def _write_sidecar_verilate_blocked_hybrid_candidate(self, root: Path) -> None:
        path = root / "reports" / "rtlmeter_vortex_hybrid_candidate_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "surface": "rtlmeter_vortex_hybrid_candidate_summary",
                    "status": "hybrid_candidate_blocked_sidecar_verilate_execution",
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
                    "adapter_implementation_status": (
                        "rtlmeter_stdout_cycles_runner_adapter_implementation_runner_argv_ready"
                    ),
                    "reentry_guard_status": "rtlmeter_wrapper_reentry_guard_blocked_recursive_rtlmeter_run",
                    "sidecar_execution_invoked": False,
                    "hybrid_candidate_executed": False,
                    "measurement_ready": False,
                }
            ),
            encoding="utf-8",
        )

    def test_readiness_blocks_without_template_authority_or_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            (root / "reports").mkdir(exist_ok=True)

            summary = build_readiness(root)

        self.assertEqual(summary["status"], "blocked_missing_first_gate")
        self.assertEqual(summary["first_measurement_candidate"]["case"], "Vortex:mini:hello")
        self.assertTrue(summary["first_case_files_exist"])
        self.assertEqual(summary["configuration_tests"]["mini"], ["hello", "saxpy", "sgemm"])
        self.assertIn("slice_launch_template.vortex_mini_hello", summary["missing_prerequisites"])
        self.assertIn("rtlmeter_sidecar_authority.vortex_mini_hello", summary["missing_prerequisites"])
        self.assertIn("cpu_reference_report.vortex", summary["missing_prerequisites"])
        self.assertIn("cpu_vs_hybrid_timing_report.vortex", summary["missing_prerequisites"])
        self.assertIn("dpi_memory_bridge_review_for_gpu_sidecar", summary["missing_prerequisites"])
        self.assertIn("stdout_TEST_PASSED_or_memory_post_condition_gpu_observable", summary["missing_prerequisites"])
        self.assert_no_local_absolute_paths(json.dumps(summary, sort_keys=True))

    def test_readiness_uses_existing_fail_closed_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            self._write_authority(root)
            self._write_cpu_reference(root)
            (root / "reports").mkdir(exist_ok=True)

            summary = build_readiness(root)

        self.assertNotIn("rtlmeter_sidecar_authority.vortex_mini_hello", summary["missing_prerequisites"])
        self.assertNotIn("cpu_reference_report.vortex", summary["missing_prerequisites"])
        self.assertTrue(summary["cpu_reference"]["cpu_reference_ready_for_hybrid_compare"])
        self.assertEqual(summary["sidecar_authority"]["runtime_launchable"], False)
        self.assertEqual(
            summary["sidecar_authority"]["status"],
            "blocked_vortex_dpi_memory_and_gpu_observable_review",
        )

    def test_readiness_uses_existing_fail_closed_launch_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            self._write_template(root)
            (root / "reports").mkdir()

            summary = build_readiness(root)

        self.assertNotIn("slice_launch_template.vortex_mini_hello", summary["missing_prerequisites"])
        self.assertEqual(summary["slice_launch_template"]["status"], "candidate_fail_closed")
        self.assertEqual(summary["slice_launch_template"]["runtime_launchable"], False)
        self.assertEqual(summary["slice_launch_template"]["source_closure_status"], "incomplete")
        self.assertEqual(
            summary["slice_launch_template"]["non_dry_run_must_fail_until_source_closure_complete"],
            True,
        )
        self.assertEqual(summary["slice_launch_template"]["speedup_claim_allowed_by_template_alone"], False)

    def test_readiness_consumes_dpi_bridge_review_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            self._write_authority(root)
            self._write_template(root)
            self._write_cpu_reference(root)
            self._write_bridge_review(root)

            summary = build_readiness(root)

        self.assertNotIn("dpi_memory_bridge_review_for_gpu_sidecar", summary["missing_prerequisites"])
        self.assertIn("gpu_memory_model_for_64B_block_reads_writes_and_byteen", summary["missing_prerequisites"])
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["status"],
            "reviewed_blocked_on_gpu_bridge_implementation",
        )
        self.assertEqual(summary["dpi_memory_bridge_review"]["binary_input_summary"]["dcr_write_count"], 9)
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["gpu_memory_model_plan"]["minimum_static_input_bytes"],
            37224,
        )
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["memory_model_reference"]["status"],
            "reference_validated",
        )
        self.assertFalse(summary["dpi_memory_bridge_review"]["implementation_ready"])
        self.assertTrue(summary["dpi_memory_bridge_review"]["device_helper_ready_for_integration"])
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["device_helper_header"],
            "src/hybrid/vortex_memory_model_device.h",
        )
        self.assertTrue(summary["dpi_memory_bridge_review"]["device_buffers_materialized_for_upload"])
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["device_buffer_materialization"]["host_to_device_bytes"],
            37224,
        )
        self.assertTrue(summary["dpi_memory_bridge_review"]["dcr_schedule_materialized"])
        self.assertEqual(summary["dpi_memory_bridge_review"]["dcr_schedule"]["write_count"], 9)
        self.assertEqual(summary["dpi_memory_bridge_review"]["dcr_schedule"]["device_schedule_bytes"], 72)
        self.assertIn(
            "runtime_execution_invokes_vortex_runtime_sequence_helper",
            summary["missing_prerequisites"],
        )
        self.assertTrue(summary["dpi_memory_bridge_review"]["runtime_sequence_helper_ready"])
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["runtime_sequence_header"],
            "src/hybrid/vortex_runtime_sequence.h",
        )
        self.assertTrue(summary["dpi_memory_bridge_review"]["runtime_sequence"]["helper_ready"])
        self.assertIn(
            "connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence",
            summary["recommended_sequence"],
        )
        self.assertTrue(summary["dpi_memory_bridge_review"]["runtime_upload_helper_ready"])
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["runtime_upload_header"],
            "src/hybrid/vortex_runtime_upload.h",
        )
        self.assertTrue(summary["dpi_memory_bridge_review"]["observable_export_helper_ready"])
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["observable_export_header"],
            "src/hybrid/vortex_observable_export.h",
        )
        self.assertTrue(summary["dpi_memory_bridge_review"]["materialized_runtime_invocation_smoke_ready"])
        self.assertEqual(
            summary["dpi_memory_bridge_review"]["materialized_runtime_invocation_smoke"]["host_to_device_bytes"],
            37224,
        )

    def test_readiness_consumes_descriptor_source_closure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            self._write_authority(root)
            self._write_template(root)
            self._write_cpu_reference(root)
            self._write_source_closure_report(root)

            summary = build_readiness(root)

        self.assertEqual(
            summary["descriptor_source_closure"]["status"],
            "descriptor_source_closure_complete",
        )
        self.assertTrue(summary["descriptor_source_closure"]["all_sources_exist"])
        self.assertEqual(summary["descriptor_source_closure"]["source_counts"]["total"], 135)
        self.assertFalse(summary["descriptor_source_closure"]["runtime_launchable"])
        self.assertNotIn("complete_vortex_descriptor_dpi_source_closure", summary["recommended_sequence"])
        self.assertEqual(
            summary["recommended_sequence"][0],
            "integrate_lowered_tb_mem_access_with_vortex_device_helper",
        )

    def test_readiness_prioritizes_wrapper_source_closure_context_after_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            self._write_authority(root)
            self._write_template(root)
            self._write_cpu_reference(root)
            self._write_source_closure_report(root)
            self._write_bridge_review(root)
            self._write_wrapper_blocked_hybrid_candidate(root)

            summary = build_readiness(root)

        self.assertIn(
            "reviewed_vortex_sidecar_context_for_wrapper_handoff",
            summary["missing_prerequisites"],
        )
        self.assertNotIn("path_selected_sidecar_capable_verilator_or_wrapper", summary["missing_prerequisites"])
        self.assertEqual(
            summary["recommended_sequence"][0],
            "provide_reviewed_vortex_sidecar_context_for_wrapper_handoff",
        )
        self.assertTrue(summary["hybrid_candidate"]["wrapper_captured_sidecar_planning"])
        self.assertEqual(summary["hybrid_candidate"]["wrapper_sidecar_accel"], "sidecar-gpu")
        self.assertFalse(summary["hybrid_candidate"]["sidecar_execution_invoked"])

    def test_readiness_prioritizes_authority_registry_source_closure_after_context_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            self._write_authority(root)
            self._write_template(root)
            self._write_cpu_reference(root)
            self._write_source_closure_report(root)
            self._write_bridge_review(root)
            self._write_authority_blocked_hybrid_candidate(root)

            summary = build_readiness(root)

        self.assertIn(
            "reviewed_vortex_authority_registry_source_closure",
            summary["missing_prerequisites"],
        )
        self.assertNotIn("reviewed_vortex_sidecar_context_for_wrapper_handoff", summary["missing_prerequisites"])
        self.assertEqual(
            summary["recommended_sequence"][0],
            "review_vortex_authority_registry_source_closure_for_wrapper_handoff",
        )
        self.assertTrue(summary["hybrid_candidate"]["handoff_metadata_ready"])
        self.assertEqual(summary["hybrid_candidate"]["stdout_cycles_plan_seed"], "Vortex:mini:hello")

    def test_readiness_prioritizes_direct_sidecar_verilate_after_runner_command_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            self._write_authority(root)
            self._write_template(root)
            self._write_cpu_reference(root)
            self._write_source_closure_report(root)
            self._write_bridge_review(root)
            self._write_sidecar_verilate_blocked_hybrid_candidate(root)

            summary = build_readiness(root)

        self.assertIn(
            "direct_sidecar_verilate_execution_or_vsim_proxy_for_vortex",
            summary["missing_prerequisites"],
        )
        self.assertNotIn("reviewed_vortex_authority_registry_source_closure", summary["missing_prerequisites"])
        self.assertEqual(
            summary["recommended_sequence"][0],
            "enable_direct_sidecar_verilate_or_vsim_proxy_for_vortex",
        )
        self.assertTrue(summary["hybrid_candidate"]["runner_command_ready"])
        self.assertEqual(
            summary["hybrid_candidate"]["runner_contract_status"],
            "rtlmeter_stdout_cycles_runner_contract_ready",
        )

    def test_readiness_does_not_count_itself_as_timing_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            reports = root / "reports"
            reports.mkdir()
            (reports / "rtlmeter_vortex_first_gate_readiness.json").write_text("{}", encoding="utf-8")

            summary = build_readiness(root)

        self.assertEqual(summary["existing_vortex_reports"], [])
        self.assertIn("cpu_vs_hybrid_timing_report.vortex", summary["missing_prerequisites"])

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_vortex_descriptor(root)
            out = root / "reports" / "vortex_readiness.json"
            out.parent.mkdir()

            result = self.run_python_tool(
                "src/tools/rtlmeter_vortex_first_gate_readiness.py",
                "--repo-root",
                root.as_posix(),
                "--write-report",
                "--report-out",
                out.as_posix(),
            )
            stdout_payload = json.loads(result.stdout)
            report_payload = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, report_payload)
        self.assertEqual(report_payload["surface"], "rtlmeter_vortex_first_gate_readiness")
        self.assert_no_local_absolute_paths(result.stdout)

    def test_repo_fail_closed_template_refuses_non_dry_run(self) -> None:
        template = REPO_ROOT / "config" / "slice_launch_templates" / "vortex_mini_hello.json"
        payload = json.loads(template.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "candidate_fail_closed")
        self.assertEqual(payload["runtime_launchable"], False)
        self.assertEqual(payload["source_closure"]["status"], "incomplete")
        self.assertEqual(payload["source_closure"]["descriptor_source_closure_status"], "complete")
        self.assertEqual(
            payload["source_closure"]["descriptor_source_closure_report"],
            "reports/rtlmeter_vortex_source_closure.json",
        )

        dry_run = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/vortex_mini_hello.json",
            "--shape",
            "1x1",
            "--dry-run",
        )
        self.assertIn("verilator --cc", dry_run.stdout)

        non_dry_run = self.run_python_tool(
            "src/tools/run_hybrid_template.py",
            "config/slice_launch_templates/vortex_mini_hello.json",
            "--shape",
            "1x1",
            check=False,
        )
        self.assertNotEqual(non_dry_run.returncode, 0)
        self.assertIn("source_closure.status=incomplete refuses non-dry-run execution", non_dry_run.stderr)


if __name__ == "__main__":
    unittest.main()
