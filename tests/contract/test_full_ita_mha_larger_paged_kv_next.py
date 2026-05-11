import json
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NEXT_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "neural_network_rtl_full_ita_mha_and_larger_paged_kv_next_gate.json"
)
LARGE_KV_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "neural_network_rtl_paged_kv_cache_large_scaleup_gate.json"
)
LARGE_KV_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "neural_network_rtl_paged_kv_cache_large_review_gate.json"
)
FULL_ITA_MHA_AUDIT_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "neural_network_rtl_full_ita_mha_dependency_audit_gate.json"
)
FULL_ITA_MHA_BENCHMARK_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json"
)
GOAL_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json"
)
PAGED_ATTENTION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "neural_network_rtl_paged_attention_kv_score_harness_gate.json"
)
COMPLETION_AUDIT = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json"
)
MODERN_LLM_COMPLETION_AUDIT = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json"
)
PUBLIC_RESULTS_GATE = REPO_ROOT / "config" / "scaling_gates" / "public_results_packaging_gate.json"
PUBLIC_RESULTS_MHA_REFRESH_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json"
)
PUBLIC_RESULTS_PERSISTENT_REPEAT_MEDIAN_REFRESH_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json"
)
PUBLIC_BENCHMARK_PACK_COMPLETION_AUDIT = (
    REPO_ROOT / "config" / "scaling_gates" / "public_benchmark_pack_goal_completion_audit.json"
)
PUBLIC_BENCHMARK_PACK_EXTERNALIZATION_AUDIT = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_benchmark_pack_externalization_readiness_audit.json"
)
PUBLIC_BENCHMARK_PACK_EXTERNALIZATION_COMPLETION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_benchmark_pack_externalization_completion_gate.json"
)
NEXT_MEASUREMENT_GOAL_SELECTION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "next_measurement_goal_selection_after_public_pack_readiness_gate.json"
)
NEXT_MEASUREMENT_AFTER_PUBLIC_PACK_EXTERNALIZATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "next_measurement_selection_after_public_benchmark_pack_externalization_gate.json"
)
PAGED_ATTENTION_KV_CACHE_SCALE_UP_MEASUREMENT_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_scale_up_measurement_gate.json"
)
PAGED_ATTENTION_KV_CACHE_SCALE_UP_MEASUREMENT_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_scale_up_measurement_review_gate.json"
)
PAGED_ATTENTION_KV_CACHE_TIMING_SUMMARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_timing_summary_gate.json"
)
PAGED_ATTENTION_KV_CACHE_TIMING_SUMMARY_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_timing_summary_review_gate.json"
)
PUBLIC_RESULTS_PAGED_ATTENTION_KV_TIMING_REFRESH_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json"
)
PUBLIC_PACK_COMPLETION_AFTER_PAGED_ATTENTION_KV_TIMING_REFRESH_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json"
)
NEXT_MEASUREMENT_AFTER_PAGED_ATTENTION_KV_TIMING_REFRESH_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json"
)
PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_TIMING_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_repeat_median_timing_gate.json"
)
PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_WORKFLOW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_repeat_median_workflow_gate.json"
)
PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_MEASUREMENT_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_repeat_median_measurement_gate.json"
)
PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "paged_attention_kv_cache_repeat_median_review_gate.json"
)
PUBLIC_RESULTS_PAGED_ATTENTION_KV_REPEAT_MEDIAN_REFRESH_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json"
)
PUBLIC_PACK_COMPLETION_AFTER_PAGED_ATTENTION_KV_REPEAT_MEDIAN_REFRESH_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json"
)
ONE_COMMAND_REPRODUCTION_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "one_command_reproduction_flow_gate.json"
)
REPEAT_MEDIAN_RESULTS_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "repeat_median_results_reproduction_gate.json"
)
RESIDENT_OPTIMIZATION_NEXT_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_execution_optimization_next_gate.json"
)
RESIDENT_BATCH_SWEEP_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_batch_sweep_measurement_gate.json"
)
RESIDENT_BATCH_SWEEP_REVIEW_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_batch_sweep_review_gate.json"
)
RESIDENT_STATE_REUSE_EXPERIMENT_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_state_reuse_experiment_gate.json"
)
RESIDENT_STATE_REUSE_MEASUREMENT_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_state_reuse_measurement_gate.json"
)
RESIDENT_STATE_REUSE_REVIEW_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_state_reuse_review_gate.json"
)
PERSISTENT_RESIDENT_STATE_ABI_PROBE_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "persistent_resident_state_abi_probe_gate.json"
)
PERSISTENT_RESIDENT_STATE_ABI_IMPLEMENTATION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "persistent_resident_state_abi_probe_implementation_gate.json"
)
PERSISTENT_RESIDENT_DEVICE_HANDLE_STORAGE_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "persistent_resident_device_handle_storage_gate.json"
)
PERSISTENT_RESIDENT_DEVICE_HANDLE_STORAGE_REVIEW_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "persistent_resident_device_handle_storage_review_gate.json"
)
PERSISTENT_RESIDENT_STATE_ABI_REPEAT_MEDIAN_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "persistent_resident_state_abi_repeat_median_measurement_gate.json"
)
NEXT_GOAL_AFTER_PERSISTENT_RESIDENT_REPEAT_MEDIAN_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "next_goal_selection_after_persistent_resident_repeat_median_gate.json"
)
CANDIDATE_TEMPLATE_SELECTION_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "candidate_template_clean_checkout_selection_gate.json"
)
NVDLA_CMAC_CORE_MAC_MINIMAL_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "nvdla_cmac_core_mac_minimal_build_run_compare_gate.json"
)
NVDLA_CMAC_CORE_MAC_TEMPLATE_SHAPE_EXPANSION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "nvdla_cmac_core_mac_template_shape_expansion_gate.json"
)
NVDLA_SHAPE_EXPANSION_NEXT_WORKSTREAM_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "nvdla_shape_expansion_next_workstream_review_gate.json"
)
ITA_DEPENDENCY_CLEAN_CHECKOUT_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "ita_dependency_clean_checkout_boundary_gate.json"
)
ITA_FIRST_SEED_SELECTION_AFTER_DEPENDENCY_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "ita_first_seed_selection_after_dependency_boundary_gate.json"
)
PULP_ITA_DOTP_OVERLAY_TEMPLATE_GENERIC_HOST_PROBE_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_dotp_overlay_template_generic_host_probe_gate.json"
)
PULP_ITA_DOTP_FIRST_GENERIC_HOST_PROBE_BUILD_RUN_COMPARE_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json"
)
PULP_ITA_DOTP_SHAPE_EXPANSION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_dotp_shape_expansion_gate.json"
)
PULP_ITA_DOTP_SHAPE_EXPANSION_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_dotp_shape_expansion_review_gate.json"
)
PULP_ITA_SOFTMAX_TOP_DEPENDENCY_TEMPLATE_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_softmax_top_dependency_template_boundary_gate.json"
)
PULP_ITA_SOFTMAX_TOP_FIRST_GENERIC_HOST_PROBE_BUILD_RUN_COMPARE_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.json"
)
PULP_ITA_SOFTMAX_TOP_SHAPE_EXPANSION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_softmax_top_shape_expansion_gate.json"
)
PULP_ITA_SOFTMAX_TOP_SHAPE_EXPANSION_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_softmax_top_shape_expansion_review_gate.json"
)
PULP_ITA_MHA_DEPENDENCY_TEMPLATE_BOUNDARY_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_mha_dependency_template_boundary_gate.json"
)
PULP_ITA_MHA_FIRST_GENERIC_HOST_PROBE_BUILD_RUN_COMPARE_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json"
)
PULP_ITA_MHA_SHAPE_EXPANSION_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_mha_shape_expansion_gate.json"
)
PULP_ITA_MHA_SHAPE_EXPANSION_REVIEW_GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "pulp_ita_mha_shape_expansion_review_gate.json"
)
REPEAT_MEDIAN_RESULTS_SUMMARY = REPO_ROOT / "reports" / "results_reproduction_median_summary.json"
RESIDENT_BATCH_SWEEP_SUMMARY = REPO_ROOT / "reports" / "resident_batch_sweep_summary.json"
RESIDENT_STATE_REUSE_SUMMARY = REPO_ROOT / "reports" / "resident_state_reuse_experiment_summary.json"
PERSISTENT_RESIDENT_STATE_ABI_SUMMARY = (
    REPO_ROOT / "reports" / "persistent_resident_state_abi_probe_summary.json"
)
SELECTION = REPO_ROOT / "config" / "selection.json"
STATUS = REPO_ROOT / "docs" / "status.md"
ROADMAP = REPO_ROOT / "docs" / "roadmap.md"
README = REPO_ROOT / "README.md"
RESULTS = REPO_ROOT / "docs" / "results.md"
MAKEFILE = REPO_ROOT / "src" / "hybrid" / "Makefile"
NVDLA_CMAC_A2CACC_OVERLAY = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "src"
    / "nvdla_cmac_a2cacc_gpu_cov_tb.sv"
)
NVDLA_CMAC_A2CACC_MANIFEST = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "tests"
    / "nvdla_cmac_a2cacc_coverage_regions.json"
)
NVDLA_CMAC_A2CACC_TEMPLATE = (
    REPO_ROOT / "config" / "slice_launch_templates" / "nvdla_cmac_a2cacc.json"
)
NVDLA_CMAC_CORE_MAC_OVERLAY = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "src"
    / "nvdla_cmac_core_mac_gpu_cov_tb.sv"
)
NVDLA_CMAC_CORE_MAC_MANIFEST = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "NVDLA"
    / "tests"
    / "nvdla_cmac_core_mac_coverage_regions.json"
)
NVDLA_CMAC_CORE_MAC_TEMPLATE = (
    REPO_ROOT / "config" / "slice_launch_templates" / "nvdla_cmac_core_mac.json"
)
LARGE_KV_OVERLAY = REPO_ROOT / "overlays" / "ITA" / "src" / "pulp_paged_kv_cache_large_gpu_cov_tb.sv"
LARGE_KV_MANIFEST = (
    REPO_ROOT / "overlays" / "ITA" / "tests" / "pulp_paged_kv_cache_large_coverage_regions.json"
)
LARGE_KV_TEMPLATE = REPO_ROOT / "config" / "slice_launch_templates" / "pulp_paged_kv_cache_large.json"
LARGE_KV_SUMMARY = REPO_ROOT / "reports" / "pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json"
FULL_ITA_TC_SRAM_OVERLAY = REPO_ROOT / "overlays" / "ITA" / "src" / "pulp_ita_tc_sram_sim.sv"
FULL_ITA_MHA_OVERLAY = REPO_ROOT / "overlays" / "ITA" / "src" / "pulp_ita_mha_gpu_cov_tb.sv"
FULL_ITA_MHA_MANIFEST = (
    REPO_ROOT / "overlays" / "ITA" / "tests" / "pulp_ita_mha_coverage_regions.json"
)
FULL_ITA_MHA_TEMPLATE = REPO_ROOT / "config" / "slice_launch_templates" / "pulp_ita_mha.json"
FULL_ITA_MHA_SUMMARY = REPO_ROOT / "reports" / "pulp_ita_mha_first_hybrid_benchmark_summary.json"
FULL_ITA_MHA_COMPARE = (
    REPO_ROOT / "reports" / "pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json"
)
FULL_ITA_MHA_COMPARE_32X1 = (
    REPO_ROOT / "reports" / "pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json"
)
FULL_ITA_MHA_COMPARE_1X32 = (
    REPO_ROOT / "reports" / "pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json"
)
FULL_ITA_MHA_SCALEUP_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "full_mha_scaleup_64x1_1x64_gate.json"
)
FULL_ITA_MHA_SCALEUP_SUMMARY = (
    REPO_ROOT / "reports" / "pulp_ita_mha_64x1_1x64_scaling_summary.json"
)
FULL_ITA_MHA_COMPARE_64X1 = (
    REPO_ROOT / "reports" / "pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json"
)
FULL_ITA_MHA_COMPARE_1X64 = (
    REPO_ROOT / "reports" / "pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json"
)
PULP_ITA_DOTP_OVERLAY = REPO_ROOT / "overlays" / "ITA" / "src" / "pulp_ita_dotp_gpu_cov_tb.sv"
PULP_ITA_DOTP_MANIFEST = (
    REPO_ROOT / "overlays" / "ITA" / "tests" / "pulp_ita_dotp_coverage_regions.json"
)
PULP_ITA_DOTP_TEMPLATE = REPO_ROOT / "config" / "slice_launch_templates" / "pulp_ita_dotp.json"
PULP_ITA_CLUSTER_CLOCK_GATING_SHIM = (
    REPO_ROOT / "overlays" / "ITA" / "src" / "pulp_ita_cluster_clock_gating_sim.sv"
)
PULP_ITA_SOFTMAX_TOP_OVERLAY = (
    REPO_ROOT / "overlays" / "ITA" / "src" / "pulp_ita_softmax_top_gpu_cov_tb.sv"
)
PULP_ITA_SOFTMAX_TOP_MANIFEST = (
    REPO_ROOT / "overlays" / "ITA" / "tests" / "pulp_ita_softmax_top_coverage_regions.json"
)
PULP_ITA_SOFTMAX_TOP_TEMPLATE = REPO_ROOT / "config" / "slice_launch_templates" / "pulp_ita_softmax_top.json"
FULL_ITA_MHA_PREFILL_DECODE_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "prefill_decode_split_mha_benchmark_gate.json"
)
FULL_ITA_MHA_PREFILL_DECODE_SUMMARY = (
    REPO_ROOT / "reports" / "pulp_ita_mha_prefill_decode_split_summary.json"
)
FULL_ITA_MHA_RESIDENT_DECODE_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_decode_optimization_probe_gate.json"
)
FULL_ITA_MHA_RESIDENT_DECODE_SUMMARY = (
    REPO_ROOT / "reports" / "pulp_ita_mha_resident_decode_1x64_summary.json"
)
FULL_ITA_MHA_RESIDENT_BATCH_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "resident_decode_batch_parallel_probe_gate.json"
)
FULL_ITA_MHA_RESIDENT_BATCH_SUMMARY = (
    REPO_ROOT / "reports" / "pulp_ita_mha_resident_decode_batch_parallel_summary.json"
)
PAGED_ATTENTION_OVERLAY = (
    REPO_ROOT / "overlays" / "ITA" / "src" / "pulp_paged_attention_kv_score_gpu_cov_tb.sv"
)
PAGED_ATTENTION_MANIFEST = (
    REPO_ROOT / "overlays" / "ITA" / "tests" / "pulp_paged_attention_kv_score_coverage_regions.json"
)
PAGED_ATTENTION_TEMPLATE = REPO_ROOT / "config" / "slice_launch_templates" / "pulp_paged_attention_kv_score.json"
PAGED_ATTENTION_SUMMARY = (
    REPO_ROOT / "reports" / "pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json"
)
PAGED_ATTENTION_COMPARE_1X1 = (
    REPO_ROOT / "reports" / "pulp_paged_attention_kv_score_cpu_vs_hybrid_1x1_coverage_output_compare.json"
)
PAGED_ATTENTION_COMPARE_64X1 = (
    REPO_ROOT / "reports" / "pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json"
)
PAGED_ATTENTION_COMPARE_1X64 = (
    REPO_ROOT / "reports" / "pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json"
)
HYBRID_BENCHMARK_WRAPPER_SUMMARIES = [
    REPO_ROOT / "reports" / "hybrid_benchmark_pulp_ita_mha_template_1x1.json",
    REPO_ROOT / "reports" / "hybrid_benchmark_paged_attention_kv_score_template_1x1.json",
    REPO_ROOT / "reports" / "hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json",
    REPO_ROOT / "reports" / "hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json",
    REPO_ROOT / "reports" / "hybrid_benchmark_mobile_vit_template_limit128.json",
]
HYBRID_BENCHMARK_REQUIRED_SCHEMA_FIELDS = {
    "schema_version",
    "tool",
    "target",
    "shape",
    "limit",
    "mode",
    "phases",
    "execution_mode",
    "command_count",
    "commands",
    "expected_reports",
    "evidence",
    "non_claims",
}
LOCAL_ABSOLUTE_PATH_MARKERS = (
    "/home/",
    "/tmp/",
    "/Users/",
    "/var/",
    "/mnt/",
    "/workspace/",
    "/root/",
)


def _git_ls_files(path: Path) -> str:
    return subprocess.check_output(
        ["git", "ls-files", "--", str(path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


class FullItaMhaAndLargerPagedKvNextGateTest(unittest.TestCase):
    def test_selection_points_to_large_paged_kv_scaleup_gate(self) -> None:
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))

        self.assertEqual(selection["top_level_goal"], "modern_llm_serving_rtl_hybrid_conditions")
        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )

    def test_gate_records_both_requested_followups_and_selected_first_workstream(self) -> None:
        gate = json.loads(NEXT_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["status"],
            "defined_dual_followup_select_larger_paged_kv_first",
        )
        self.assertEqual(
            gate["prior_completion_audit"],
            "config/scaling_gates/modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json",
        )
        self.assertEqual(
            gate["requested_followups"],
            [
                "full ITA/MHA execution",
                "larger paged attention / KV-cache scale-up",
            ],
        )
        by_name = {entry["name"]: entry for entry in gate["workstreams"]}
        self.assertEqual(by_name["larger_paged_attention_kv_cache_scaleup"]["status"], "selected_first")
        self.assertEqual(
            by_name["larger_paged_attention_kv_cache_scaleup"]["selected_target"],
            "pulp_paged_kv_cache_large",
        )
        self.assertEqual(
            by_name["full_ita_mha_execution"]["status"],
            "dependency_audit_required_before_overlay",
        )
        self.assertEqual(
            by_name["full_ita_mha_execution"]["candidate_upstream_top"],
            "third_party/ITA/src/ita.sv",
        )

    def test_gate_preserves_non_claims_and_acceptance_policy(self) -> None:
        gate = json.loads(NEXT_GATE.read_text(encoding="utf-8"))

        self.assertTrue(gate["acceptance_policy"]["keep_prior_completion_audit_unchanged"])
        self.assertTrue(gate["acceptance_policy"]["new_public_workflow_requires_contract_test_and_doc_mention"])
        self.assertTrue(gate["acceptance_policy"]["full_ita_mha_claim_requires_separate_dependency_and_stimulus_audit"])
        self.assertIn("not full ITA/MHA execution yet", gate["non_claims"])
        self.assertIn("not full paged attention yet", gate["non_claims"])
        self.assertIn("not raw full-state equality", gate["non_claims"])

    def test_large_paged_kv_gate_defines_scaleup_target_and_contract(self) -> None:
        gate = json.loads(LARGE_KV_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "all_planned_shapes_passed_coverage_output_equivalence")
        self.assertEqual(gate["completed_task"], "define_pulp_paged_kv_cache_large_scaleup_gate")
        self.assertEqual(
            gate["parent_followup_gate"],
            "config/scaling_gates/neural_network_rtl_full_ita_mha_and_larger_paged_kv_next_gate.json",
        )
        self.assertEqual(gate["selected_next_seed"]["target"], "pulp_paged_kv_cache_large")
        self.assertEqual(
            gate["selected_next_seed"]["planned_overlay"],
            "overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv",
        )
        self.assertEqual(
            gate["selected_next_seed"]["planned_coverage_manifest"],
            "overlays/ITA/tests/pulp_paged_kv_cache_large_coverage_regions.json",
        )
        self.assertEqual(
            gate["selected_next_seed"]["planned_launch_template"],
            "config/slice_launch_templates/pulp_paged_kv_cache_large.json",
        )
        self.assertEqual(
            gate["selected_next_seed"]["planned_host_probe_target"],
            "pulp_paged_kv_cache_large_host_probe",
        )

        scaleup = gate["scaleup_contract"]
        self.assertGreaterEqual(scaleup["minimum_page_count"], 8)
        self.assertGreaterEqual(scaleup["minimum_slots_per_page"], 16)
        self.assertGreaterEqual(scaleup["minimum_total_logical_slots"], 128)
        self.assertTrue(scaleup["required_state_growth_over_base"])

        coverage = gate["coverage_output_contract"]
        self.assertEqual(coverage["total_words_per_state"], 29)
        self.assertEqual(coverage["total_bytes_per_state"], 116)
        self.assertEqual(coverage["acceptance_policy"], "coverage_output_equivalence")
        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_required"])
        self.assertTrue(gate["acceptance_policy"]["all_planned_shapes_required_before_classification"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "review_pulp_paged_kv_cache_large_first_compare_result_and_select_next_full_ita_or_scaleup_step",
        )

        planned_shapes = {(shape["nstates"], shape["steps"]) for shape in gate["planned_shapes"]}
        self.assertEqual(planned_shapes, {(1, 1), (64, 1), (1, 64), (256, 1)})
        self.assertIn("not full paged attention", gate["non_claims"])
        self.assertIn("not full ITA/MHA execution", gate["non_claims"])

        result = gate["result"]
        self.assertEqual(result["summary_report"], "reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json")
        self.assertTrue(result["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(set(result["measured_shapes"]), {"1x1", "64x1", "1x64", "256x1"})

    def test_large_paged_kv_workflow_files_are_wired(self) -> None:
        self.assertTrue(LARGE_KV_OVERLAY.exists())
        self.assertTrue(LARGE_KV_MANIFEST.exists())
        self.assertTrue(LARGE_KV_TEMPLATE.exists())

        overlay = LARGE_KV_OVERLAY.read_text(encoding="utf-8")
        manifest = json.loads(LARGE_KV_MANIFEST.read_text(encoding="utf-8"))
        template = json.loads(LARGE_KV_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn("module pulp_paged_kv_cache_large_gpu_cov_tb", overlay)
        self.assertIn("PageCount = 8", overlay)
        self.assertIn("SlotsPerPage = 16", overlay)
        self.assertIn("TotalSlots = PageCount * SlotsPerPage", overlay)
        self.assertIn("PageWidth = 3", overlay)
        self.assertIn("OffsetWidth = 4", overlay)
        self.assertIn("SlotWidth = 7", overlay)

        self.assertEqual(manifest["target"], "PULP_ITA.pulp_paged_kv_cache_large")
        self.assertEqual(manifest["top_module"], "pulp_paged_kv_cache_large_gpu_cov_tb")
        self.assertEqual(template["target"], "PULP_ITA.pulp_paged_kv_cache_large")
        self.assertEqual(template["top_module"], "pulp_paged_kv_cache_large_gpu_cov_tb")
        self.assertEqual(template["build"]["mdir"], "artifacts/pulp_paged_kv_cache_large_obj_dir")
        self.assertEqual(template["build"]["host_probe_target"], "pulp_paged_kv_cache_large_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(
            template["build"]["host_probe"]["clock_field"],
            "pulp_paged_kv_cache_large_gpu_cov_tb__DOT__clk_i",
        )
        self.assertEqual(template["scaleup_contract"]["total_logical_slots"], 128)

    def test_large_paged_kv_first_summary_records_all_planned_shapes_passing(self) -> None:
        gate = json.loads(LARGE_KV_GATE.read_text(encoding="utf-8"))
        summary = gate["result"]

        self.assertEqual(gate["selected_next_seed"]["target"], "pulp_paged_kv_cache_large")
        self.assertEqual(summary["storage_size_bytes"], 1600)
        self.assertTrue(summary["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(set(summary["measured_shapes"]), {"1x1", "64x1", "1x64", "256x1"})
        self.assertEqual(gate["coverage_output_contract"]["total_words_per_state"], 29)
        self.assertEqual(gate["coverage_output_contract"]["total_bytes_per_state"], 116)
        self.assertEqual(summary["summary_report"], "reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json")
        for report in summary["compare_reports"]:
            self.assertTrue(report.startswith("reports/"))
            self.assertTrue(report.endswith("_coverage_output_compare.json"))

    def test_large_paged_kv_review_selects_full_ita_mha_next(self) -> None:
        gate = json.loads(LARGE_KV_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "reviewed_select_full_ita_mha_dependency_audit_next")
        self.assertEqual(
            gate["reviewed_summary"],
            "reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json",
        )
        self.assertTrue(gate["result_summary"]["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(gate["result_summary"]["mismatch_count"], 0)
        self.assertEqual(gate["selected_next_workstream"]["name"], "full_ita_mha_execution")
        self.assertEqual(
            gate["selected_next_workstream"]["next_gate"],
            "config/scaling_gates/neural_network_rtl_full_ita_mha_dependency_audit_gate.json",
        )
        self.assertEqual(
            gate["next_task"],
            "implement_pulp_ita_mha_minimal_dependency_stubs_and_lint_probe",
        )
        self.assertIn("not full ITA/MHA execution", gate["non_claims"])
        self.assertIn("not full paged attention", gate["non_claims"])

    def test_full_ita_mha_dependency_audit_records_blockers_and_stimulus_scope(self) -> None:
        gate = json.loads(FULL_ITA_MHA_AUDIT_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["status"],
            "dependency_overlays_lint_passed_select_full_ita_overlay_next",
        )
        self.assertEqual(gate["candidate_top"]["target"], "pulp_ita_mha")
        self.assertEqual(gate["candidate_top"]["upstream_top_source"], "third_party/ITA/src/ita.sv")
        self.assertEqual(gate["candidate_top"]["planned_overlay"], "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv")
        self.assertEqual(gate["candidate_top"]["planned_host_probe_target"], "pulp_ita_mha_host_probe")
        self.assertIn("third_party/ITA/src/ita.sv", gate["candidate_source_files"])
        self.assertIn("third_party/ITA/src/ita_accumulator.sv", gate["candidate_source_files"])
        self.assertIn("overlays/ITA/src/pulp_ita_cluster_clock_gating_sim.sv", gate["candidate_source_files"])
        self.assertIn("overlays/ITA/src/pulp_ita_tc_sram_sim.sv", gate["candidate_source_files"])

        blockers = {entry["module"]: entry for entry in gate["direct_lint_probe"]["observed_missing_modules"]}
        self.assertEqual(gate["direct_lint_probe"]["status"], "passed_after_dependency_overlays")
        self.assertIn("cluster_clock_gating", blockers)
        self.assertIn("tc_sram", blockers)
        self.assertIn("existing overlays/ITA/src/pulp_ita_cluster_clock_gating_sim.sv", blockers["cluster_clock_gating"]["resolution"])
        self.assertIn("overlays/ITA/src/pulp_ita_tc_sram_sim.sv", blockers["tc_sram"]["resolution"])
        self.assertEqual(gate["direct_lint_probe"]["lint_result"]["status"], "passed")
        self.assertIn("-Wno-UNOPTFLAT", gate["direct_lint_probe"]["lint_result"]["required_warning_suppression"])

        stimulus = gate["stimulus_audit"]
        self.assertIn("Q, K, V, QK, AV, and OW", stimulus["first_overlay_scope"])
        self.assertEqual(stimulus["first_compare_policy"], "coverage_output_equivalence")
        self.assertFalse(gate["acceptance_policy"]["new_tc_sram_overlay_required"])
        self.assertEqual(gate["acceptance_policy"]["new_tc_sram_overlay"], "overlays/ITA/src/pulp_ita_tc_sram_sim.sv")
        self.assertFalse(gate["acceptance_policy"]["full_ita_mha_claim_allowed_by_audit_alone"])
        self.assertEqual(gate["next_task"], "implement_pulp_ita_mha_overlay_manifest_template_host_probe")

    def test_full_ita_mha_dependency_stub_exists(self) -> None:
        self.assertTrue(FULL_ITA_TC_SRAM_OVERLAY.exists())
        overlay = FULL_ITA_TC_SRAM_OVERLAY.read_text(encoding="utf-8")
        self.assertIn("module tc_sram", overlay)
        self.assertIn("parameter int unsigned NumWords", overlay)
        self.assertIn("parameter int unsigned NumPorts", overlay)
        self.assertIn("output data_t [NumPorts-1:0] rdata_o", overlay)

    def test_full_ita_mha_overlay_template_and_host_probe_are_wired(self) -> None:
        self.assertTrue(FULL_ITA_MHA_OVERLAY.exists())
        self.assertTrue(FULL_ITA_MHA_MANIFEST.exists())
        self.assertTrue(FULL_ITA_MHA_TEMPLATE.exists())

        overlay = FULL_ITA_MHA_OVERLAY.read_text(encoding="utf-8")
        manifest = json.loads(FULL_ITA_MHA_MANIFEST.read_text(encoding="utf-8"))
        template = json.loads(FULL_ITA_MHA_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn("module pulp_ita_mha_gpu_cov_tb", overlay)
        self.assertIn("ita i_ita", overlay)
        self.assertIn("real_toggle_subset_word17_o", overlay)
        self.assertEqual(manifest["target"], "PULP_ITA.pulp_ita_mha")
        self.assertEqual(manifest["top_module"], "pulp_ita_mha_gpu_cov_tb")
        self.assertEqual(manifest["coverage_domain"], "toggle_real_subset_bitmap")
        self.assertEqual(template["status"], "promoted_full_ita_mha_dependency_template_boundary")
        self.assertEqual(template["target"], "PULP_ITA.pulp_ita_mha")
        self.assertEqual(
            template["source_gate"],
            "config/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json",
        )
        self.assertEqual(template["build"]["host_probe_target"], "pulp_ita_mha_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(
            template["build"]["host_probe"]["clock_field"],
            "pulp_ita_mha_gpu_cov_tb__DOT__clk_i",
        )

    def test_generated_host_probe_targets_do_not_expand_makefile_surface(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        generated_targets = (
            "nvdla_cmac_a2cacc_host_probe",
            "nvdla_cmac_core_mac_host_probe",
            "nvdla_cmac_core_mac_flat_host_probe",
            "pulp_ita_dotp_host_probe",
            "pulp_ita_softmax_top_host_probe",
            "pulp_ita_mha_host_probe",
            "pulp_kv_cache_host_probe",
            "pulp_paged_kv_cache_host_probe",
            "pulp_paged_kv_cache_large_host_probe",
            "pulp_paged_attention_kv_score_host_probe",
            "mobile_vit_cpu_kick_rtl_proxy_host_probe",
        )
        for target in generated_targets:
            with self.subTest(target=target):
                self.assertNotIn(target, makefile)

        for template_path in (
            PULP_ITA_DOTP_TEMPLATE,
            PULP_ITA_SOFTMAX_TOP_TEMPLATE,
            LARGE_KV_TEMPLATE,
            FULL_ITA_MHA_TEMPLATE,
            PAGED_ATTENTION_TEMPLATE,
        ):
            with self.subTest(template=template_path.name):
                template = json.loads(template_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    template["build"]["host_probe_builder"],
                    "src/tools/build_host_probe.py",
                )

    def test_nvdla_cmac_a2cacc_candidate_template_uses_generic_host_probe_builder(self) -> None:
        self.assertTrue(NVDLA_CMAC_A2CACC_OVERLAY.exists())
        self.assertTrue(NVDLA_CMAC_A2CACC_MANIFEST.exists())
        self.assertTrue(NVDLA_CMAC_A2CACC_TEMPLATE.exists())

        overlay = NVDLA_CMAC_A2CACC_OVERLAY.read_text(encoding="utf-8")
        manifest = json.loads(NVDLA_CMAC_A2CACC_MANIFEST.read_text(encoding="utf-8"))
        template = json.loads(NVDLA_CMAC_A2CACC_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn("module nvdla_cmac_a2cacc_gpu_cov_tb", overlay)
        self.assertIn("NV_NVDLA_RT_cmac_a2cacc", overlay)
        self.assertEqual(manifest["target"], "NVDLA.nvdla_cmac_a2cacc")
        self.assertEqual(template["target"], "NVDLA.nvdla_cmac_a2cacc")
        self.assertEqual(template["top_module"], "nvdla_cmac_a2cacc_gpu_cov_tb")
        self.assertEqual(
            template["source_files"],
            ["third_party/rtlmeter/designs/NVDLA/src/NV_NVDLA_RT_cmac_a2cacc.v"],
        )
        self.assertEqual(template["build"]["host_probe_target"], "nvdla_cmac_a2cacc_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(
            template["build"]["host_probe"]["clock_field"],
            "nvdla_cmac_a2cacc_gpu_cov_tb__DOT__nvdla_core_clk",
        )
        self.assertNotIn("makefile", template["planned_overlay"])

    def test_nvdla_cmac_core_mac_candidate_template_uses_generic_host_probe_builder(self) -> None:
        self.assertTrue(NVDLA_CMAC_CORE_MAC_OVERLAY.exists())
        self.assertTrue(NVDLA_CMAC_CORE_MAC_MANIFEST.exists())
        self.assertTrue(NVDLA_CMAC_CORE_MAC_TEMPLATE.exists())

        overlay = NVDLA_CMAC_CORE_MAC_OVERLAY.read_text(encoding="utf-8")
        manifest = json.loads(NVDLA_CMAC_CORE_MAC_MANIFEST.read_text(encoding="utf-8"))
        template = json.loads(NVDLA_CMAC_CORE_MAC_TEMPLATE.read_text(encoding="utf-8"))

        self.assertIn("module nvdla_cmac_core_mac_gpu_cov_tb", overlay)
        self.assertIn("NV_NVDLA_CMAC_CORE_mac", overlay)
        self.assertEqual(manifest["target"], "NVDLA.nvdla_cmac_core_mac")
        self.assertEqual(manifest["top_module"], template["top_module"])
        self.assertEqual(template["target"], "NVDLA.nvdla_cmac_core_mac")
        self.assertEqual(
            template["source_gate"],
            "config/scaling_gates/nvdla_cmac_core_mac_minimal_build_run_compare_gate.json",
        )
        self.assertEqual(template["top_module"], "nvdla_cmac_core_mac_gpu_cov_tb")
        self.assertEqual(
            template["source_files"],
            [
                "third_party/rtlmeter/designs/NVDLA/src/NV_NVDLA_CMAC_CORE_mac.v",
                "third_party/rtlmeter/designs/NVDLA/src/NV_NVDLA_CMAC_CORE_MAC_mul.v",
                "third_party/rtlmeter/designs/NVDLA/src/NV_NVDLA_CMAC_CORE_MAC_exp.v",
                "third_party/rtlmeter/designs/NVDLA/src/NV_NVDLA_CMAC_CORE_MAC_nan.v",
                "third_party/rtlmeter/designs/NVDLA/src/NV_DW02_tree.v",
                "third_party/rtlmeter/designs/NVDLA/src/NV_DW_minmax.v",
            ],
        )
        for source_file in template["source_files"]:
            self.assertTrue(source_file.startswith("third_party/rtlmeter/"))
            self.assertTrue((REPO_ROOT / source_file).exists())

        self.assertEqual(
            template["verilator_args"],
            [
                "--flatten",
                "-Wno-fatal",
                "-Wno-WIDTHXZEXPAND",
                "-Wno-WIDTHTRUNC",
                "-Wno-WIDTHEXPAND",
            ],
        )
        self.assertEqual(template["verilator_defines"], ["SYNTHESIS", "DESIGNWARE_NOEXIST"])
        self.assertEqual(
            template["build"]["host_probe_target"],
            "nvdla_cmac_core_mac_flat_host_probe",
        )
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(template["build"]["verilator_mode"], "flattened")
        self.assertEqual(
            template["build"]["host_probe"]["clock_field"],
            "nvdla_cmac_core_mac_gpu_cov_tb__DOT__nvdla_core_clk",
        )
        self.assertFalse(template["build"]["host_probe"]["probe_syms_state"])
        self.assertNotIn("makefile", template["planned_overlay"])

    def test_nvdla_cmac_core_mac_minimal_build_run_compare_gate_is_recorded(self) -> None:
        gate = json.loads(NVDLA_CMAC_CORE_MAC_MINIMAL_GATE.read_text(encoding="utf-8"))
        template = json.loads(NVDLA_CMAC_CORE_MAC_TEMPLATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            gate["status"],
            "minimal_1x1_build_run_compare_passed_coverage_output_equivalence",
        )
        self.assertEqual(gate["target_full_name"], "NVDLA.nvdla_cmac_core_mac")
        self.assertEqual(gate["template"], "config/slice_launch_templates/nvdla_cmac_core_mac.json")
        self.assertEqual(gate["overlay"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["overlay"]["makefile_target_required"])
        self.assertEqual(gate["build_contract"]["storage_size_bytes"], 24768)
        self.assertEqual(gate["build_contract"]["verilator_defines"], template["verilator_defines"])
        self.assertEqual(gate["build_contract"]["verilator_args"], template["verilator_args"])
        self.assertIn("-Wno-fatal", gate["build_contract"]["verilator_args"])
        self.assertEqual(gate["measured_shape"]["nstates"], 1)
        self.assertEqual(gate["measured_shape"]["steps"], 1)
        self.assertTrue(gate["measured_shape"]["coverage_output_equivalence_passed"])
        self.assertEqual(gate["measured_shape"]["coverage_output_mismatch_count"], 0)
        self.assertTrue(gate["acceptance_policy"]["host_probe_built_with_generic_builder"])
        self.assertTrue(gate["acceptance_policy"]["gpu_cubin_built"])
        self.assertTrue(gate["acceptance_policy"]["hybrid_run_completed"])
        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_gate_passed"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_match_required"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "nvdla_cmac_core_mac_template_shape_expansion_gate",
        )
        self.assertIn("not broad CPU versus hybrid speedup", gate["non_claims"])
        self.assertIn("not raw full-state equality", gate["non_claims"])

        for token in (
            "nvdla_cmac_core_mac_minimal_build_run_compare_gate.json",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/nvdla_cmac_core_mac.json --shape 1x1",
            "coverage_output_equivalence",
            "mismatch count: `0`",
            "run_hybrid_template.py` passes template `verilator_defines`",
            "nvdla_cmac_core_mac_template_shape_expansion_gate",
        ):
            self.assertIn(token, combined_docs)

    def test_nvdla_cmac_core_mac_template_shape_expansion_gate_is_next(self) -> None:
        gate = json.loads(NVDLA_CMAC_CORE_MAC_TEMPLATE_SHAPE_EXPANSION_GATE.read_text(encoding="utf-8"))
        minimal_gate = json.loads(NVDLA_CMAC_CORE_MAC_MINIMAL_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            gate["status"],
            "completed_template_shape_expansion_coverage_output_equivalence",
        )
        self.assertEqual(
            gate["source_minimal_gate"],
            "config/scaling_gates/nvdla_cmac_core_mac_minimal_build_run_compare_gate.json",
        )
        self.assertEqual(minimal_gate["next_task"], gate["gate"])
        self.assertEqual(gate["target_full_name"], "NVDLA.nvdla_cmac_core_mac")
        self.assertEqual(gate["template"], "config/slice_launch_templates/nvdla_cmac_core_mac.json")
        self.assertEqual(gate["entrypoint"], "src/tools/run_hybrid_template.py")
        self.assertEqual(
            gate["active_seed_policy"]["active_seed_target"],
            "NVDLA.nvdla_cmac_core_mac",
        )
        self.assertTrue(gate["active_seed_policy"]["do_not_add_second_active_seed_before_gate_completion"])
        self.assertEqual(
            [shape["shape"] for shape in gate["planned_shapes"]],
            ["8x1", "32x1", "8x4"],
        )
        self.assertTrue(gate["acceptance_policy"]["verilator_like_entrypoint_required"])
        self.assertTrue(gate["acceptance_policy"]["generic_host_probe_builder_required"])
        self.assertTrue(gate["acceptance_policy"]["all_planned_shapes_must_pass_coverage_output_equivalence"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_match_required"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertIn("not promotion of a second active seed target", gate["non_claims"])
        self.assertEqual(
            gate["next_task"],
            "review_nvdla_cmac_core_mac_shape_expansion_results_then_choose_a2cacc_or_ita_boundary",
        )

        for command in gate["required_commands"]["dry_run_smoke"]:
            self.assertIn("python3 src/tools/run_hybrid_template.py", command)
            self.assertIn("config/slice_launch_templates/nvdla_cmac_core_mac.json", command)
            self.assertIn("--dry-run", command)

        result = gate["result"]
        self.assertEqual(result["status"], "all_planned_shapes_passed_coverage_output_equivalence")
        self.assertTrue(result["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(result["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(result["raw_full_state_match_all_shapes"])
        self.assertTrue(result["normalized_final_state_equivalence_all_shapes"])
        self.assertEqual(result["storage_size_bytes"], 24768)

        measured = {shape["shape"]: shape for shape in result["measured_shapes"]}
        self.assertEqual(set(measured), {"8x1", "32x1", "8x4"})
        for shape, expected_nstates, expected_steps in (("8x1", 8, 1), ("32x1", 32, 1), ("8x4", 8, 4)):
            with self.subTest(shape=shape):
                entry = measured[shape]
                self.assertEqual(entry["nstates"], expected_nstates)
                self.assertEqual(entry["steps"], expected_steps)
                self.assertIn(
                    f"python3 src/tools/run_hybrid_template.py config/slice_launch_templates/nvdla_cmac_core_mac.json --shape {shape}",
                    entry["command"],
                )
                self.assertTrue(entry["coverage_output_equivalence_passed"])
                self.assertEqual(entry["coverage_output_mismatch_count"], 0)
                self.assertFalse(entry["raw_full_state_match"])
                self.assertTrue(entry["normalized_final_state_equivalence"])
                self.assertIn(
                    f"reports/nvdla_cmac_core_mac_cpu_vs_hybrid_{shape}_coverage_output_compare.json",
                    entry["coverage_output_compare_report"],
                )

        for token in (
            "nvdla_cmac_core_mac_template_shape_expansion_gate.json",
            "`8x1`, `32x1`, and `8x4` all pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`",
            "raw full-state equality is false",
        ):
            self.assertIn(token, combined_docs)

    def test_nvdla_shape_expansion_next_workstream_review_selects_ita_dependency_boundary(self) -> None:
        gate = json.loads(NVDLA_SHAPE_EXPANSION_NEXT_WORKSTREAM_REVIEW_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "selected_ita_dependency_boundary_next")
        self.assertEqual(
            gate["source_shape_expansion_gate"],
            "config/scaling_gates/nvdla_cmac_core_mac_template_shape_expansion_gate.json",
        )
        self.assertEqual(
            gate["completed_nvdla_evidence"]["active_seed_target"],
            "NVDLA.nvdla_cmac_core_mac",
        )
        self.assertEqual(gate["completed_nvdla_evidence"]["measured_shapes"], ["8x1", "32x1", "8x4"])
        self.assertTrue(gate["completed_nvdla_evidence"]["all_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(gate["completed_nvdla_evidence"]["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(gate["completed_nvdla_evidence"]["raw_full_state_match_all_shapes"])
        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["nvdla_cmac_a2cacc_secondary_minimal_gate"]["decision"], "defer")
        self.assertEqual(options["ita_dependency_clean_checkout_boundary"]["decision"], "select_next")
        self.assertEqual(
            gate["selected_next_workstream"]["name"],
            "ita_dependency_clean_checkout_boundary",
        )
        self.assertEqual(
            gate["selected_next_workstream"]["next_gate"],
            "ita_dependency_clean_checkout_boundary_gate",
        )
        self.assertFalse(gate["acceptance_policy"]["new_active_seed_measurement_allowed_by_gate"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "define_ita_dependency_clean_checkout_boundary_gate")
        self.assertIn("not an ITA build/run/compare result", gate["non_claims"])
        self.assertIn("not promotion of a second active seed measurement", gate["non_claims"])

        for token in (
            "nvdla_shape_expansion_next_workstream_review_gate.json",
            "selected next workstream: `ita_dependency_clean_checkout_boundary`",
            "third_party/ITA` and `third_party/common_cells` canonical",
        ):
            self.assertIn(token, combined_docs)

    def test_ita_dependency_clean_checkout_boundary_is_defined_before_measurement(self) -> None:
        gate = json.loads(ITA_DEPENDENCY_CLEAN_CHECKOUT_BOUNDARY_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )
        gitmodules = (REPO_ROOT / ".gitmodules").read_text(encoding="utf-8")

        self.assertEqual(gate["status"], "implemented_canonical_dependency_boundary_before_measurement")
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/nvdla_shape_expansion_next_workstream_review_gate.json",
        )
        self.assertEqual(
            gate["current_clean_checkout_observation"]["gitmodules_contains"],
            ["third_party/rtlmeter", "third_party/ITA", "third_party/common_cells"],
        )
        self.assertTrue(gate["current_clean_checkout_observation"]["third_party_ita_is_currently_canonical"])
        self.assertTrue(gate["current_clean_checkout_observation"]["third_party_common_cells_is_currently_canonical"])
        self.assertIn(
            "canonical only through their .gitmodules entries and gitlink commits",
            gate["current_clean_checkout_observation"]["policy"],
        )
        required = {
            dependency["path"]: dependency
            for dependency in gate["selected_boundary"]["required_dependencies"]
        }
        self.assertEqual(required["third_party/ITA"]["historical_pinned_commit"], "ba96519becce195d64e85eb9a5302e8a1d5487e7")
        self.assertEqual(
            required["third_party/common_cells"]["historical_pinned_revision"],
            "c27bce39ebb2e6bae52f60960814a2afca7bd4cb",
        )
        self.assertEqual(
            gate["selected_boundary"]["first_allowed_seed_after_boundary"],
            "one of ita_dotp or ita_softmax_top, not both in the same measurement gate",
        )
        self.assertFalse(gate["acceptance_policy"]["define_only"])
        self.assertTrue(gate["acceptance_policy"]["dependency_import_performed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["ita_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["implementation_result"]["status"], "canonical_gitlinks_added")
        gitlinks = {entry["path"]: entry for entry in gate["implementation_result"]["gitlinks"]}
        self.assertEqual(gitlinks["third_party/ITA"]["mode"], "160000")
        self.assertEqual(gitlinks["third_party/ITA"]["commit"], "ba96519becce195d64e85eb9a5302e8a1d5487e7")
        self.assertEqual(gitlinks["third_party/common_cells"]["mode"], "160000")
        self.assertEqual(gitlinks["third_party/common_cells"]["commit"], "c27bce39ebb2e6bae52f60960814a2afca7bd4cb")
        self.assertFalse(gate["implementation_result"]["measurement_performed"])
        self.assertFalse(gate["implementation_result"]["runtime_or_pass_changes"])
        self.assertEqual(gate["next_task"], "select_one_first_ita_seed_after_dependency_boundary")
        self.assertIn("not approval to recursively import all Bender dependencies", gate["non_claims"])
        self.assertIn("third_party/rtlmeter", gitmodules)
        self.assertIn("third_party/ITA", gitmodules)
        self.assertIn("third_party/common_cells", gitmodules)
        ls_files = subprocess.check_output(
            ["git", "ls-files", "-s", "third_party/ITA", "third_party/common_cells"],
            cwd=REPO_ROOT,
            text=True,
        )
        self.assertIn("160000 ba96519becce195d64e85eb9a5302e8a1d5487e7", ls_files)
        self.assertIn("160000 c27bce39ebb2e6bae52f60960814a2afca7bd4cb", ls_files)

        for token in (
            "ita_dependency_clean_checkout_boundary_gate.json",
            "`third_party/ITA` and `third_party/common_cells` are canonical gitlink submodules",
            "pulp_ita_dotp",
        ):
            self.assertIn(token, combined_docs)

    def test_ita_first_seed_selection_after_dependency_boundary_selects_dotp_only(self) -> None:
        gate = json.loads(ITA_FIRST_SEED_SELECTION_AFTER_DEPENDENCY_BOUNDARY_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "selected_ita_dotp_first_seed_after_dependency_boundary")
        self.assertEqual(
            gate["source_dependency_boundary_gate"],
            "config/scaling_gates/ita_dependency_clean_checkout_boundary_gate.json",
        )
        self.assertTrue(gate["selection_rule"]["only_one_active_ita_seed"])
        self.assertFalse(gate["selection_rule"]["measurement_performed_by_this_gate"])
        self.assertTrue(gate["selection_rule"]["avoid_recursive_bender_import"])

        options = {entry["candidate"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["ita_dotp"]["decision"], "select_first_active_seed")
        self.assertEqual(options["ita_dotp"]["target"], "pulp_ita_dotp")
        self.assertEqual(options["ita_dotp"]["line_count"], 34)
        self.assertEqual(options["ita_dotp"]["dependency_surface"]["local_ita_dependencies"], [])
        self.assertEqual(options["ita_dotp"]["dependency_surface"]["external_common_cells_dependencies"], [])
        self.assertIn("Less representative than softmax", options["ita_dotp"]["weakness"])
        self.assertEqual(options["ita_softmax_top"]["decision"], "defer_until_after_dotp_boundary")
        self.assertIn("cf_math_pkg", options["ita_softmax_top"]["dependency_surface"]["external_common_cells_dependencies"])
        self.assertIn("fifo_v3", options["ita_softmax_top"]["dependency_surface"]["external_common_cells_dependencies"])
        self.assertIn("lzc", options["ita_softmax_top"]["dependency_surface"]["external_common_cells_dependencies"])

        selected = gate["selected_seed"]
        self.assertEqual(selected["target"], "pulp_ita_dotp")
        self.assertEqual(selected["upstream_source"], "third_party/ITA/src/ita_dotp.sv")
        self.assertEqual(selected["required_submodule"], "third_party/ITA")
        self.assertEqual(selected["source_line_count"], 34)
        self.assertTrue((REPO_ROOT / selected["upstream_source"]).exists())
        self.assertEqual(gate["deferred_seed"]["target"], "pulp_ita_softmax_top")
        self.assertIn("third_party/common_cells/src/fifo_v3.sv", gate["deferred_seed"]["required_sources_before_measurement"])
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "implement_pulp_ita_dotp_overlay_template_generic_host_probe_gate",
        )
        self.assertIn("use src/tools/build_host_probe.py", " ".join(gate["required_next_gate"]["scope"]))
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["overlay_or_template_import_performed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "implement_pulp_ita_dotp_overlay_template_generic_host_probe_gate")
        self.assertIn("not softmax execution", gate["non_claims"])
        self.assertIn("not a correctness result", gate["non_claims"])

        for token in (
            "ita_first_seed_selection_after_dependency_boundary_gate.json",
            "selected first ITA active seed: `pulp_ita_dotp`",
            "third_party/ITA/src/ita_dotp.sv",
            "defers `pulp_ita_softmax_top`",
            "pulp_ita_dotp_overlay_template_generic_host_probe_gate.json",
            "not an ITA build/run/compare result",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_dotp_overlay_template_uses_generic_host_probe_builder(self) -> None:
        gate = json.loads(PULP_ITA_DOTP_OVERLAY_TEMPLATE_GENERIC_HOST_PROBE_GATE.read_text(encoding="utf-8"))
        overlay = PULP_ITA_DOTP_OVERLAY.read_text(encoding="utf-8")
        manifest = json.loads(PULP_ITA_DOTP_MANIFEST.read_text(encoding="utf-8"))
        template = json.loads(PULP_ITA_DOTP_TEMPLATE.read_text(encoding="utf-8"))
        makefile = MAKEFILE.read_text(encoding="utf-8")
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "promoted_dotp_overlay_template_with_generic_host_probe_builder")
        self.assertEqual(gate["source_selection_gate"], "config/scaling_gates/ita_first_seed_selection_after_dependency_boundary_gate.json")
        self.assertEqual(gate["target"], "pulp_ita_dotp")
        self.assertEqual(gate["coverage_domain"], "toggle_real_subset_bitmap")
        self.assertEqual(gate["upstream"]["source"], "third_party/ITA/src/ita_dotp.sv")
        target_scope = {entry["target"]: entry for entry in gate["target_scope"]}
        self.assertEqual(
            target_scope["pulp_ita_dotp"]["coverage_manifest"],
            "overlays/ITA/tests/pulp_ita_dotp_coverage_regions.json",
        )
        self.assertEqual(gate["promoted_source_boundary"]["coverage_tb"], "overlays/ITA/src/pulp_ita_dotp_gpu_cov_tb.sv")
        self.assertEqual(gate["promoted_source_boundary"]["coverage_manifest"], "overlays/ITA/tests/pulp_ita_dotp_coverage_regions.json")
        self.assertEqual(gate["promoted_source_boundary"]["launch_template"], "config/slice_launch_templates/pulp_ita_dotp.json")
        self.assertEqual(gate["promoted_source_boundary"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["promoted_source_boundary"]["makefile_target_required"])

        self.assertIn("module pulp_ita_dotp_gpu_cov_tb", overlay)
        self.assertIn("ita_dotp #(", overlay)
        self.assertIn("real_toggle_subset_word17_o", overlay)
        self.assertEqual(manifest["target"], "PULP_ITA.pulp_ita_dotp")
        self.assertEqual(manifest["top_module"], "pulp_ita_dotp_gpu_cov_tb")
        self.assertEqual(manifest["coverage_domain"], "toggle_real_subset_bitmap")
        self.assertEqual(template["status"], "promoted_first_ita_seed_boundary")
        self.assertEqual(template["target"], "PULP_ITA.pulp_ita_dotp")
        self.assertEqual(template["source_gate"], "config/scaling_gates/pulp_ita_dotp_overlay_template_generic_host_probe_gate.json")
        self.assertEqual(template["top_module"], "pulp_ita_dotp_gpu_cov_tb")
        self.assertEqual(template["source_files"], ["third_party/ITA/src/ita_dotp.sv"])
        self.assertIn("--flatten", template["verilator_args"])
        self.assertEqual(template["build"]["host_probe_target"], "pulp_ita_dotp_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(template["build"]["host_probe"]["clock_field"], "pulp_ita_dotp_gpu_cov_tb__DOT__clk_i")
        self.assertEqual(template["build"]["host_probe"]["reset_field"], "pulp_ita_dotp_gpu_cov_tb__DOT__reset_like_w")
        self.assertEqual(template["build"]["host_probe"]["reset_asserted_value"], "1U")
        self.assertEqual(template["build"]["host_probe"]["reset_deasserted_value"], "0U")
        self.assertTrue(template["build"]["host_probe"]["host_clock_control"])
        self.assertFalse(template["build"]["host_probe"]["host_reset_control"])
        self.assertNotIn("makefile", template["planned_overlay"])
        self.assertNotIn("pulp_ita_dotp_host_probe", makefile)

        coverage = gate["coverage_output_contract"]
        self.assertEqual(coverage["total_words_per_state"], 29)
        self.assertEqual(coverage["total_bytes_per_state"], 116)
        self.assertEqual(coverage["acceptance_policy"], "coverage_output_equivalence")
        self.assertFalse(gate["acceptance_policy"]["measurement_performed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "run_pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate")

        dry_run = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_dotp.json",
                "--shape",
                "1x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_dotp.json", dry_run.stdout)
        self.assertNotIn("make -C src/hybrid pulp_ita_dotp_host_probe", dry_run.stdout)

        for path in (PULP_ITA_DOTP_TEMPLATE, PULP_ITA_DOTP_OVERLAY, PULP_ITA_DOTP_MANIFEST):
            self.assertTrue(_git_ls_files(path))

        for token in (
            "pulp_ita_dotp_overlay_template_generic_host_probe_gate.json",
            "src/tools/build_host_probe.py",
            "pulp_ita_dotp_gpu_cov_tb__DOT__clk_i",
            "pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json",
            "not a build/run/compare result",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_dotp_first_generic_host_probe_build_run_compare_passed_1x1(self) -> None:
        gate = json.loads(PULP_ITA_DOTP_FIRST_GENERIC_HOST_PROBE_BUILD_RUN_COMPARE_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "minimal_1x1_build_run_compare_passed_coverage_output_equivalence")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/pulp_ita_dotp_overlay_template_generic_host_probe_gate.json",
        )
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_dotp")
        self.assertEqual(gate["active_seed"], "pulp_ita_dotp")
        self.assertEqual(gate["shape"], "1x1")
        self.assertEqual(
            gate["command"],
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_dotp.json --shape 1x1",
        )
        self.assertEqual(gate["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["makefile_target_required"])
        for step, passed in gate["build_run_compare_steps"].items():
            with self.subTest(step=step):
                self.assertTrue(passed)

        coverage = gate["coverage_output_contract"]
        self.assertEqual(coverage["coverage_output_target"], "pulp_ita_dotp")
        self.assertEqual(coverage["acceptance_policy"], "coverage_output_equivalence")
        self.assertEqual(coverage["compared_word_count"], 29)
        self.assertEqual(coverage["compared_byte_count"], 116)

        measured = gate["measured_shape"]
        self.assertEqual(measured["shape"], "1x1")
        self.assertEqual(measured["storage_size_bytes"], 576)
        self.assertFalse(measured["raw_full_state_match"])
        self.assertEqual(measured["raw_full_state_mismatch_count"], 32)
        self.assertEqual(
            measured["raw_full_state_mismatch_role_summary"]["verilator_internal"]["mismatch_bytes"],
            32,
        )
        self.assertTrue(measured["normalized_final_state_equivalence_passed"])
        self.assertTrue(measured["coverage_output_equivalence_passed"])
        self.assertEqual(measured["coverage_output_mismatch_count"], 0)
        self.assertEqual(measured["cpu_elapsed_ms"], 3.12573)
        self.assertEqual(measured["hybrid_gpu_kernel_time_ms_total"], 1.40288)
        self.assertEqual(measured["hybrid_wall_time_ms"], 1.46)

        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_gate_passed"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_match_required"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["shape_expansion_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "run_pulp_ita_dotp_shape_expansion_gate")
        self.assertIn("not shape expansion evidence", gate["non_claims"])
        self.assertEqual([entry["shape"] for entry in gate["deferred_shapes"]], ["64x1", "1x64"])

        if (REPO_ROOT / measured["coverage_output_compare_report"]).exists():
            report = json.loads((REPO_ROOT / measured["coverage_output_compare_report"]).read_text(encoding="utf-8"))
            self.assertTrue(report["selected_acceptance_policy"]["passed"])
            self.assertEqual(report["selected_acceptance_policy"]["name"], "coverage_output_equivalence")
            self.assertEqual(report["coverage_output_policy"]["mismatch_count"], 0)
            self.assertEqual(report["coverage_output_policy"]["compared_word_count"], 29)
            self.assertEqual(report["coverage_output_policy"]["compared_byte_count"], 116)

        for token in (
            "pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json",
            "coverage_output_equivalence` compare pass",
            "mismatch count: `0`",
            "raw full-state equality: false",
            "pulp_ita_dotp_shape_expansion_gate.json",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_dotp_shape_expansion_records_64x1_and_1x64(self) -> None:
        gate = json.loads(PULP_ITA_DOTP_SHAPE_EXPANSION_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "all_planned_shapes_passed_coverage_output_equivalence")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json",
        )
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_dotp")
        self.assertEqual(gate["active_seed"], "pulp_ita_dotp")
        self.assertEqual(gate["planned_shapes"], ["64x1", "1x64"])
        self.assertEqual(gate["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["makefile_target_required"])
        self.assertEqual(gate["acceptance_policy"], "coverage_output_equivalence")
        self.assertTrue(gate["result_summary"]["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(gate["result_summary"]["max_coverage_output_mismatch_count"], 0)
        self.assertIn("64x1 state-parallel", gate["result_summary"]["trend"])
        self.assertIn("1x64 single-state", gate["result_summary"]["trend"])

        shapes = {entry["shape"]: entry for entry in gate["measured_shapes"]}
        self.assertEqual(set(shapes), {"64x1", "1x64"})
        self.assertEqual(shapes["64x1"]["nstates"], 64)
        self.assertEqual(shapes["64x1"]["steps"], 1)
        self.assertEqual(shapes["64x1"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(shapes["64x1"]["coverage_output_compared_word_count"], 1856)
        self.assertEqual(shapes["64x1"]["coverage_output_compared_byte_count"], 7424)
        self.assertEqual(shapes["64x1"]["cpu_elapsed_ms"], 150.04)
        self.assertEqual(shapes["64x1"]["hybrid_gpu_kernel_time_ms_total"], 1.29024)
        self.assertEqual(shapes["64x1"]["hybrid_wall_time_ms"], 1.321)
        self.assertGreater(shapes["64x1"]["cpu_to_hybrid_wall_speedup_ratio"], 100.0)
        self.assertFalse(shapes["64x1"]["raw_full_state_match"])

        self.assertEqual(shapes["1x64"]["nstates"], 1)
        self.assertEqual(shapes["1x64"]["steps"], 64)
        self.assertEqual(shapes["1x64"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(shapes["1x64"]["coverage_output_compared_word_count"], 29)
        self.assertEqual(shapes["1x64"]["coverage_output_compared_byte_count"], 116)
        self.assertEqual(shapes["1x64"]["cpu_elapsed_ms"], 3.23146)
        self.assertEqual(shapes["1x64"]["hybrid_gpu_kernel_time_ms_total"], 1.543168)
        self.assertEqual(shapes["1x64"]["hybrid_wall_time_ms"], 1.6)
        self.assertGreater(shapes["1x64"]["cpu_to_hybrid_wall_speedup_ratio"], 2.0)
        self.assertLess(
            shapes["1x64"]["cpu_to_hybrid_wall_speedup_ratio"],
            shapes["64x1"]["cpu_to_hybrid_wall_speedup_ratio"],
        )
        self.assertFalse(shapes["1x64"]["raw_full_state_match"])

        for shape, entry in shapes.items():
            with self.subTest(shape=shape):
                self.assertTrue(entry["coverage_output_equivalence_passed"])
                self.assertTrue(entry["normalized_final_state_equivalence_passed"])
                self.assertEqual(
                    entry["raw_full_state_mismatch_role_summary"]["verilator_internal"]["field_count"],
                    4,
                )
                if (REPO_ROOT / entry["coverage_output_compare_report"]).exists():
                    report = json.loads((REPO_ROOT / entry["coverage_output_compare_report"]).read_text(encoding="utf-8"))
                    self.assertTrue(report["selected_acceptance_policy"]["passed"])
                    self.assertEqual(report["coverage_output_policy"]["mismatch_count"], 0)

        dry_run_64 = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_dotp.json",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        dry_run_1x64 = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_dotp.json",
                "--shape",
                "1x64",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        for stdout in (dry_run_64.stdout, dry_run_1x64.stdout):
            self.assertIn("python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_dotp.json", stdout)
            self.assertIn("--coverage-output-target pulp_ita_dotp", stdout)
            self.assertNotIn("make -C src/hybrid pulp_ita_dotp_host_probe", stdout)

        self.assertFalse(gate["acceptance_policy_summary"]["broad_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy_summary"]["second_active_ita_seed_allowed_by_gate"])
        self.assertEqual(gate["next_task"], "review_pulp_ita_dotp_shape_expansion_and_select_softmax_or_hold")
        self.assertIn("not softmax execution", gate["non_claims"])
        self.assertIn("not broad modern-NN speedup", gate["non_claims"])

        for token in (
            "pulp_ita_dotp_shape_expansion_gate.json",
            "both planned shapes pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`",
            "`64x1`: CPU elapsed `150.04 ms`, hybrid GPU kernel total `1.29024 ms`, hybrid wall `1.321 ms`",
            "`1x64`: CPU elapsed `3.23146 ms`, hybrid GPU kernel total `1.543168 ms`, hybrid wall `1.600 ms`",
            "pulp_ita_dotp_shape_expansion_review_gate.json",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_dotp_shape_expansion_review_selects_softmax_boundary(self) -> None:
        gate = json.loads(PULP_ITA_DOTP_SHAPE_EXPANSION_REVIEW_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "selected_ita_softmax_top_dependency_template_boundary_next")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/pulp_ita_dotp_shape_expansion_gate.json")
        self.assertEqual(gate["reviewed_seed"], "pulp_ita_dotp")
        reviewed = gate["reviewed_result"]
        self.assertEqual(reviewed["planned_shapes"], ["64x1", "1x64"])
        self.assertTrue(reviewed["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(reviewed["max_coverage_output_mismatch_count"], 0)
        self.assertIn("does not exercise softmax", reviewed["weakness"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["hold_for_more_dotp_evidence"]["decision"], "defer")
        self.assertEqual(
            options["move_to_ita_softmax_top_dependency_template_boundary"]["decision"],
            "select_next",
        )
        self.assertEqual(options["jump_to_full_ita_mha"]["decision"], "defer")

        selected = gate["selected_next_workstream"]
        self.assertEqual(selected["name"], "ita_softmax_top_dependency_template_boundary")
        self.assertEqual(selected["target"], "pulp_ita_softmax_top")
        self.assertEqual(selected["upstream_source"], "third_party/ITA/src/ita_softmax_top.sv")
        self.assertEqual(
            selected["required_next_gate"],
            "pulp_ita_softmax_top_dependency_template_boundary_gate",
        )
        self.assertFalse(selected["measurement_allowed_by_review_gate"])
        active_seed_policy = gate["active_seed_policy"]
        self.assertEqual(active_seed_policy["completed_or_held_seed"], "pulp_ita_dotp")
        self.assertEqual(active_seed_policy["only_next_active_ita_seed"], "pulp_ita_softmax_top")
        self.assertFalse(active_seed_policy["second_active_seed_measurement_allowed_by_this_gate"])

        dependency = gate["required_dependency_boundary"]
        self.assertIn("third_party/ITA/src/ita_softmax_top.sv", dependency["required_ita_sources"])
        self.assertIn("third_party/ITA/src/ita_serdiv.sv", dependency["required_ita_sources"])
        self.assertIn("third_party/common_cells/src/cf_math_pkg.sv", dependency["required_common_cells_sources"])
        self.assertIn("third_party/common_cells/src/fifo_v3.sv", dependency["required_common_cells_sources"])
        self.assertIn("third_party/common_cells/src/lzc.sv", dependency["required_common_cells_sources"])
        self.assertIn("Do not recursively import all Bender dependencies", dependency["dependency_policy"])

        template = gate["required_template_boundary"]
        self.assertEqual(template["coverage_tb"], "overlays/ITA/src/pulp_ita_softmax_top_gpu_cov_tb.sv")
        self.assertEqual(template["coverage_manifest"], "overlays/ITA/tests/pulp_ita_softmax_top_coverage_regions.json")
        self.assertEqual(template["launch_template"], "config/slice_launch_templates/pulp_ita_softmax_top.json")
        self.assertEqual(template["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(template["makefile_target_allowed"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["second_active_seed_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "define_pulp_ita_softmax_top_dependency_template_boundary_gate")
        self.assertIn("not softmax build/run/compare", gate["non_claims"])
        self.assertIn("not approval to recursively import all Bender dependencies", gate["non_claims"])

        for token in (
            "pulp_ita_dotp_shape_expansion_review_gate.json",
            "selected next workstream: `ita_softmax_top_dependency_template_boundary`",
            "required next boundary: `pulp_ita_softmax_top_dependency_template_boundary_gate`",
            "pulp_ita_softmax_top_dependency_template_boundary_gate.json",
            "not softmax build/run/compare",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_softmax_top_dependency_template_boundary_is_promoted_before_measurement(self) -> None:
        gate = json.loads(PULP_ITA_SOFTMAX_TOP_DEPENDENCY_TEMPLATE_BOUNDARY_GATE.read_text(encoding="utf-8"))
        overlay = PULP_ITA_SOFTMAX_TOP_OVERLAY.read_text(encoding="utf-8")
        shim = PULP_ITA_CLUSTER_CLOCK_GATING_SHIM.read_text(encoding="utf-8")
        manifest = json.loads(PULP_ITA_SOFTMAX_TOP_MANIFEST.read_text(encoding="utf-8"))
        template = json.loads(PULP_ITA_SOFTMAX_TOP_TEMPLATE.read_text(encoding="utf-8"))
        makefile = MAKEFILE.read_text(encoding="utf-8")
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "promoted_softmax_dependency_template_boundary_before_measurement")
        self.assertEqual(gate["source_review_gate"], "config/scaling_gates/pulp_ita_dotp_shape_expansion_review_gate.json")
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_softmax_top")
        self.assertEqual(gate["active_seed"], "pulp_ita_softmax_top")
        self.assertEqual(gate["coverage_domain"], "toggle_real_subset_bitmap")
        self.assertEqual(gate["upstream"]["source"], "third_party/ITA/src/ita_softmax_top.sv")

        expected_sources = [
            "third_party/common_cells/src/cf_math_pkg.sv",
            "third_party/common_cells/src/lzc.sv",
            "third_party/common_cells/src/fifo_v3.sv",
            "overlays/ITA/src/pulp_ita_cluster_clock_gating_sim.sv",
            "third_party/ITA/src/ita_package.sv",
            "third_party/ITA/src/ita_max_finder.sv",
            "third_party/ITA/src/ita_register_file_1w_multi_port_read.sv",
            "third_party/ITA/src/ita_softmax.sv",
            "third_party/ITA/src/ita_serdiv.sv",
            "third_party/ITA/src/ita_softmax_top.sv",
        ]
        self.assertEqual(template["source_files"], expected_sources)
        self.assertEqual(gate["template_contract"]["source_files"], expected_sources)
        for source in expected_sources:
            self.assertTrue((REPO_ROOT / source).exists(), source)

        self.assertIn("module pulp_ita_softmax_top_gpu_cov_tb", overlay)
        self.assertIn("ita_softmax_top dut", overlay)
        self.assertIn("real_toggle_subset_word17_o", overlay)
        self.assertIn("module cluster_clock_gating", shim)
        self.assertEqual(manifest["target"], "PULP_ITA.pulp_ita_softmax_top")
        self.assertEqual(manifest["top_module"], "pulp_ita_softmax_top_gpu_cov_tb")
        self.assertEqual(manifest["coverage_domain"], "toggle_real_subset_bitmap")
        self.assertEqual(template["status"], "promoted_softmax_dependency_template_boundary")
        self.assertEqual(template["target"], "PULP_ITA.pulp_ita_softmax_top")
        self.assertEqual(
            template["source_gate"],
            "config/scaling_gates/pulp_ita_softmax_top_dependency_template_boundary_gate.json",
        )
        self.assertEqual(template["top_module"], "pulp_ita_softmax_top_gpu_cov_tb")
        self.assertIn("--flatten", template["verilator_args"])
        self.assertIn("+define+ITA_M=16", template["verilator_args"])
        self.assertEqual(template["build"]["host_probe_target"], "pulp_ita_softmax_top_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(
            template["build"]["host_probe"]["clock_field"],
            "pulp_ita_softmax_top_gpu_cov_tb__DOT__clk_i",
        )
        self.assertEqual(
            template["build"]["host_probe"]["reset_field"],
            "pulp_ita_softmax_top_gpu_cov_tb__DOT__reset_like_w",
        )
        self.assertEqual(template["build"]["host_probe"]["reset_asserted_value"], "1U")
        self.assertEqual(template["build"]["host_probe"]["reset_deasserted_value"], "0U")
        self.assertTrue(template["build"]["host_probe"]["host_clock_control"])
        self.assertFalse(template["build"]["host_probe"]["host_reset_control"])
        self.assertNotIn("makefile", template["planned_overlay"])
        self.assertNotIn("pulp_ita_softmax_top_host_probe", makefile)

        boundary = gate["dependency_boundary"]
        self.assertIn("third_party/ITA/src/ita_softmax_top.sv", boundary["required_ita_sources"])
        self.assertIn("third_party/common_cells/src/fifo_v3.sv", boundary["required_common_cells_sources"])
        self.assertIn("overlays/ITA/src/pulp_ita_cluster_clock_gating_sim.sv", boundary["required_overlay_sources"])
        self.assertIn("do not recursively import all Bender dependencies", boundary["policy"])

        coverage = gate["coverage_output_contract"]
        self.assertEqual(coverage["total_words_per_state"], 29)
        self.assertEqual(coverage["total_bytes_per_state"], 116)
        self.assertEqual(coverage["acceptance_policy"], "coverage_output_equivalence")
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["makefile_host_probe_target_allowed"])
        self.assertEqual(gate["next_task"], "run_pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate")
        self.assertIn("not softmax build/run/compare yet", gate["non_claims"])

        dry_run = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_softmax_top.json",
                "--shape",
                "1x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_softmax_top.json", dry_run.stdout)
        self.assertIn("--coverage-output-target pulp_ita_softmax_top", dry_run.stdout)
        self.assertNotIn("make -C src/hybrid pulp_ita_softmax_top_host_probe", dry_run.stdout)

        for path in (
            PULP_ITA_SOFTMAX_TOP_TEMPLATE,
            PULP_ITA_CLUSTER_CLOCK_GATING_SHIM,
            PULP_ITA_SOFTMAX_TOP_OVERLAY,
            PULP_ITA_SOFTMAX_TOP_MANIFEST,
        ):
            self.assertTrue(_git_ls_files(path))

        for token in (
            "pulp_ita_softmax_top_dependency_template_boundary_gate.json",
            "required common_cells sources: `cf_math_pkg`, `lzc`, and `fifo_v3`",
            "src/tools/build_host_probe.py",
            "next_task: run_pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate",
            "not softmax build/run/compare",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_passed_1x1(self) -> None:
        gate = json.loads(
            PULP_ITA_SOFTMAX_TOP_FIRST_GENERIC_HOST_PROBE_BUILD_RUN_COMPARE_GATE.read_text(encoding="utf-8")
        )
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "minimal_1x1_build_run_compare_passed_coverage_output_equivalence")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/pulp_ita_softmax_top_dependency_template_boundary_gate.json",
        )
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_softmax_top")
        self.assertEqual(gate["active_seed"], "pulp_ita_softmax_top")
        self.assertEqual(gate["shape"], "1x1")
        self.assertEqual(
            gate["command"],
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_softmax_top.json --shape 1x1",
        )
        self.assertEqual(gate["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["makefile_target_required"])
        for step, passed in gate["build_run_compare_steps"].items():
            with self.subTest(step=step):
                self.assertTrue(passed)

        coverage = gate["coverage_output_contract"]
        self.assertEqual(coverage["coverage_output_target"], "pulp_ita_softmax_top")
        self.assertEqual(coverage["acceptance_policy"], "coverage_output_equivalence")
        self.assertEqual(coverage["compared_word_count"], 29)
        self.assertEqual(coverage["compared_byte_count"], 116)
        self.assertEqual(coverage["manifest_covered_word_count"], 18)

        measured = gate["measured_shape"]
        self.assertEqual(measured["shape"], "1x1")
        self.assertEqual(measured["nstates"], 1)
        self.assertEqual(measured["steps"], 1)
        self.assertEqual(measured["storage_size_bytes"], 1344)
        self.assertFalse(measured["raw_full_state_match"])
        self.assertEqual(measured["raw_full_state_mismatch_count"], 32)
        self.assertEqual(
            measured["raw_full_state_mismatch_role_summary"]["verilator_internal"]["mismatch_bytes"],
            32,
        )
        self.assertIsNone(measured["normalized_final_state_equivalence_passed"])
        self.assertTrue(measured["coverage_output_equivalence_passed"])
        self.assertEqual(measured["coverage_output_mismatch_count"], 0)
        self.assertEqual(measured["cpu_elapsed_ms"], 4.17958)
        self.assertEqual(measured["hybrid_gpu_kernel_time_ms_total"], 1.08032)
        self.assertEqual(measured["hybrid_wall_time_ms"], 1.11)

        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_gate_passed"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_match_required"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["shape_expansion_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "run_pulp_ita_softmax_top_shape_expansion_gate")
        self.assertIn("not shape expansion evidence", gate["non_claims"])
        self.assertEqual([entry["shape"] for entry in gate["deferred_shapes"]], ["64x1", "1x64"])

        if (REPO_ROOT / measured["coverage_output_compare_report"]).exists():
            report = json.loads((REPO_ROOT / measured["coverage_output_compare_report"]).read_text(encoding="utf-8"))
            self.assertTrue(report["selected_acceptance_policy"]["passed"])
            self.assertEqual(report["selected_acceptance_policy"]["name"], "coverage_output_equivalence")
            self.assertEqual(report["coverage_output_policy"]["mismatch_count"], 0)
            self.assertEqual(report["coverage_output_policy"]["compared_word_count"], 29)
            self.assertEqual(report["coverage_output_policy"]["compared_byte_count"], 116)

        for token in (
            "pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.json",
            "selected policy is `coverage_output_equivalence`",
            "mismatch count `0`",
            "Raw full-state equality remains false",
            "pulp_ita_softmax_top_shape_expansion_gate",
            "review_pulp_ita_softmax_top_shape_expansion_and_select_full_ita_or_hold",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_softmax_top_shape_expansion_records_64x1_and_1x64(self) -> None:
        gate = json.loads(PULP_ITA_SOFTMAX_TOP_SHAPE_EXPANSION_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "all_planned_shapes_passed_coverage_output_equivalence")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.json",
        )
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_softmax_top")
        self.assertEqual(gate["active_seed"], "pulp_ita_softmax_top")
        self.assertEqual(gate["planned_shapes"], ["64x1", "1x64"])
        self.assertEqual(gate["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["makefile_target_required"])
        self.assertEqual(gate["acceptance_policy"], "coverage_output_equivalence")
        self.assertTrue(gate["result_summary"]["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(gate["result_summary"]["max_coverage_output_mismatch_count"], 0)
        self.assertIn("64x1 state-parallel", gate["result_summary"]["trend"])
        self.assertIn("1x64 single-state", gate["result_summary"]["trend"])

        shapes = {entry["shape"]: entry for entry in gate["measured_shapes"]}
        self.assertEqual(set(shapes), {"64x1", "1x64"})
        self.assertEqual(shapes["64x1"]["nstates"], 64)
        self.assertEqual(shapes["64x1"]["steps"], 1)
        self.assertEqual(shapes["64x1"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(shapes["64x1"]["coverage_output_compared_state_pair_count"], 64)
        self.assertEqual(shapes["64x1"]["coverage_output_compared_word_count"], 1856)
        self.assertEqual(shapes["64x1"]["coverage_output_compared_byte_count"], 7424)
        self.assertEqual(shapes["64x1"]["cpu_elapsed_ms"], 149.823)
        self.assertEqual(shapes["64x1"]["hybrid_gpu_kernel_time_ms_total"], 0.891904)
        self.assertEqual(shapes["64x1"]["hybrid_wall_time_ms"], 0.922)
        self.assertGreater(shapes["64x1"]["cpu_to_hybrid_wall_speedup_ratio"], 100.0)
        self.assertFalse(shapes["64x1"]["raw_full_state_match"])

        self.assertEqual(shapes["1x64"]["nstates"], 1)
        self.assertEqual(shapes["1x64"]["steps"], 64)
        self.assertEqual(shapes["1x64"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(shapes["1x64"]["coverage_output_compared_state_pair_count"], 1)
        self.assertEqual(shapes["1x64"]["coverage_output_compared_word_count"], 29)
        self.assertEqual(shapes["1x64"]["coverage_output_compared_byte_count"], 116)
        self.assertEqual(shapes["1x64"]["cpu_elapsed_ms"], 3.96133)
        self.assertEqual(shapes["1x64"]["hybrid_gpu_kernel_time_ms_total"], 1.303552)
        self.assertEqual(shapes["1x64"]["hybrid_wall_time_ms"], 1.517)
        self.assertGreater(shapes["1x64"]["cpu_to_hybrid_wall_speedup_ratio"], 2.0)
        self.assertLess(
            shapes["1x64"]["cpu_to_hybrid_wall_speedup_ratio"],
            shapes["64x1"]["cpu_to_hybrid_wall_speedup_ratio"],
        )
        self.assertFalse(shapes["1x64"]["raw_full_state_match"])

        for shape, entry in shapes.items():
            with self.subTest(shape=shape):
                self.assertTrue(entry["coverage_output_equivalence_passed"])
                self.assertTrue(entry["normalized_final_state_equivalence_passed"])
                self.assertEqual(
                    entry["raw_full_state_mismatch_role_summary"]["verilator_internal"]["field_count"],
                    4,
                )
                if (REPO_ROOT / entry["coverage_output_compare_report"]).exists():
                    report = json.loads((REPO_ROOT / entry["coverage_output_compare_report"]).read_text(encoding="utf-8"))
                    self.assertTrue(report["selected_acceptance_policy"]["passed"])
                    self.assertEqual(report["coverage_output_policy"]["mismatch_count"], 0)

        dry_run_64 = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_softmax_top.json",
                "--shape",
                "64x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        dry_run_1x64 = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_softmax_top.json",
                "--shape",
                "1x64",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        for stdout in (dry_run_64.stdout, dry_run_1x64.stdout):
            self.assertIn("python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_softmax_top.json", stdout)
            self.assertIn("--coverage-output-target pulp_ita_softmax_top", stdout)
            self.assertNotIn("make -C src/hybrid pulp_ita_softmax_top_host_probe", stdout)

        self.assertFalse(gate["acceptance_policy_summary"]["broad_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy_summary"]["second_active_ita_seed_allowed_by_gate"])
        self.assertEqual(gate["next_task"], "review_pulp_ita_softmax_top_shape_expansion_and_select_full_ita_or_hold")
        self.assertIn("not full ITA execution", gate["non_claims"])
        self.assertIn("not broad modern-NN speedup", gate["non_claims"])

        for token in (
            "pulp_ita_softmax_top_shape_expansion_gate.json",
            "Both shapes pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`",
            "`64x1` has CPU elapsed `149.823 ms` and hybrid wall `0.922 ms`",
            "`1x64` has CPU elapsed `3.96133 ms` and hybrid wall `1.517 ms`",
            "review_pulp_ita_softmax_top_shape_expansion_and_select_full_ita_or_hold",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_softmax_top_shape_expansion_review_selects_full_ita_mha_boundary(self) -> None:
        gate = json.loads(PULP_ITA_SOFTMAX_TOP_SHAPE_EXPANSION_REVIEW_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "selected_full_ita_mha_dependency_template_boundary_next")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/pulp_ita_softmax_top_shape_expansion_gate.json",
        )
        self.assertEqual(gate["reviewed_seed"], "pulp_ita_softmax_top")
        reviewed = gate["reviewed_result"]
        self.assertEqual(reviewed["planned_shapes"], ["64x1", "1x64"])
        self.assertTrue(reviewed["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(reviewed["max_coverage_output_mismatch_count"], 0)
        self.assertIn("not the full ITA/MHA", reviewed["weakness"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["hold_for_more_softmax_top_evidence"]["decision"], "defer")
        self.assertEqual(
            options["move_to_full_ita_mha_dependency_template_boundary"]["decision"],
            "select_next",
        )
        self.assertEqual(options["divert_to_kv_cache_or_mobile_vit_or_runtime"]["decision"], "defer")

        selected = gate["selected_next_workstream"]
        self.assertEqual(selected["name"], "full_ita_mha_dependency_template_boundary")
        self.assertEqual(selected["target"], "pulp_ita_mha")
        self.assertEqual(selected["upstream_source"], "third_party/ITA/src/ita.sv")
        self.assertEqual(selected["required_next_gate"], "pulp_ita_mha_dependency_template_boundary_gate")
        self.assertFalse(selected["measurement_allowed_by_review_gate"])

        active_seed_policy = gate["active_seed_policy"]
        self.assertEqual(active_seed_policy["completed_or_held_seed"], "pulp_ita_softmax_top")
        self.assertEqual(active_seed_policy["only_next_active_ita_seed"], "pulp_ita_mha")
        self.assertFalse(active_seed_policy["second_active_seed_measurement_allowed_by_this_gate"])

        dependency = gate["required_dependency_boundary"]
        self.assertIn("third_party/ITA/src/ita.sv", dependency["required_ita_sources"])
        self.assertIn("third_party/ITA/src/ita_controller.sv", dependency["required_ita_sources"])
        self.assertIn("third_party/ITA/src/ita_sumdotp.sv", dependency["required_ita_sources"])
        self.assertIn("third_party/ITA/src/ita_softmax_top.sv", dependency["required_ita_sources"])
        self.assertIn("third_party/common_cells/src/cf_math_pkg.sv", dependency["required_common_cells_sources"])
        self.assertIn("overlays/ITA/src/pulp_ita_tc_sram_sim.sv", dependency["required_overlay_sources"])
        self.assertIn("do not recursively import all Bender dependencies", dependency["dependency_policy"])

        template = gate["required_template_boundary"]
        self.assertEqual(template["coverage_tb"], "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv")
        self.assertEqual(template["coverage_manifest"], "overlays/ITA/tests/pulp_ita_mha_coverage_regions.json")
        self.assertEqual(template["launch_template"], "config/slice_launch_templates/pulp_ita_mha.json")
        self.assertEqual(template["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(template["makefile_target_allowed"])
        self.assertEqual(template["first_measurement_shapes_after_boundary"], ["1x1", "32x1", "1x32"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["second_active_seed_measurement_allowed_by_this_gate"])
        self.assertTrue(policy["full_ita_mha_dependency_boundary_selected"])
        self.assertFalse(policy["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "define_pulp_ita_mha_dependency_template_boundary_gate")
        self.assertIn("not full ITA/MHA build/run/compare", gate["non_claims"])
        self.assertIn("not a KV-cache, MobileViT, or runtime workstream switch", gate["non_claims"])

        for token in (
            "pulp_ita_softmax_top_shape_expansion_review_gate.json",
            "selects `full_ita_mha_dependency_template_boundary` next",
            "next_task is `define_pulp_ita_mha_dependency_template_boundary_gate`",
            "does not run full ITA/MHA build/run/compare",
            "does not switch to KV-cache, MobileViT, or runtime work",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_mha_dependency_template_boundary_is_promoted_before_measurement(self) -> None:
        gate = json.loads(PULP_ITA_MHA_DEPENDENCY_TEMPLATE_BOUNDARY_GATE.read_text(encoding="utf-8"))
        template = json.loads(FULL_ITA_MHA_TEMPLATE.read_text(encoding="utf-8"))
        manifest = json.loads(FULL_ITA_MHA_MANIFEST.read_text(encoding="utf-8"))
        makefile = MAKEFILE.read_text(encoding="utf-8")
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "promoted_full_ita_mha_dependency_template_boundary_before_measurement")
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/pulp_ita_softmax_top_shape_expansion_review_gate.json",
        )
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_mha")
        self.assertEqual(gate["active_seed"], "pulp_ita_mha")
        self.assertEqual(gate["upstream"]["source"], "third_party/ITA/src/ita.sv")
        self.assertEqual(gate["coverage_domain"], "toggle_real_subset_bitmap")

        boundary = gate["dependency_boundary"]
        for source in (
            "third_party/ITA/src/ita.sv",
            "third_party/ITA/src/ita_controller.sv",
            "third_party/ITA/src/ita_sumdotp.sv",
            "third_party/ITA/src/ita_softmax_top.sv",
        ):
            self.assertIn(source, boundary["required_ita_sources"])
        self.assertIn("third_party/common_cells/src/cf_math_pkg.sv", boundary["required_common_cells_sources"])
        self.assertIn("overlays/ITA/src/pulp_ita_tc_sram_sim.sv", boundary["required_overlay_sources"])
        self.assertIn("do not recursively import all Bender dependencies", boundary["policy"])
        for source in (
            boundary["required_common_cells_sources"]
            + boundary["required_overlay_sources"]
            + boundary["required_ita_sources"]
        ):
            self.assertTrue((REPO_ROOT / source).exists(), source)

        promoted = gate["promoted_source_boundary"]
        self.assertEqual(promoted["coverage_tb"], "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv")
        self.assertEqual(promoted["coverage_manifest"], "overlays/ITA/tests/pulp_ita_mha_coverage_regions.json")
        self.assertEqual(promoted["launch_template"], "config/slice_launch_templates/pulp_ita_mha.json")
        self.assertEqual(promoted["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(promoted["makefile_target_required"])
        self.assertEqual(promoted["template_status"], "promoted_full_ita_mha_dependency_template_boundary")

        self.assertEqual(template["status"], "promoted_full_ita_mha_dependency_template_boundary")
        self.assertEqual(template["source_gate"], "config/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(
            template["build"]["host_probe"]["clock_field"],
            gate["template_contract"]["host_probe_clock_field"],
        )
        self.assertEqual(
            template["build"]["host_probe"]["reset_field"],
            gate["template_contract"]["host_probe_reset_field"],
        )
        self.assertEqual(gate["template_contract"]["host_probe_reset_asserted_value"], "1U")
        self.assertFalse(template["build"]["host_probe"]["host_reset_control"])
        self.assertNotIn("pulp_ita_mha_host_probe", makefile)

        self.assertEqual(manifest["target"], "PULP_ITA.pulp_ita_mha")
        self.assertEqual(manifest["coverage_domain"], "toggle_real_subset_bitmap")
        self.assertEqual(gate["coverage_output_contract"]["manifest_region_words"]["count"], 18)
        self.assertEqual(gate["coverage_output_contract"]["total_words_per_state"], 29)
        self.assertEqual(gate["coverage_output_contract"]["total_bytes_per_state"], 116)
        target_scope = gate["target_scope"][0]
        self.assertEqual(target_scope["target"], "pulp_ita_mha")
        self.assertEqual(target_scope["status"], "promoted_full_ita_mha_dependency_template_boundary")
        self.assertEqual(target_scope["launch_template"], "config/slice_launch_templates/pulp_ita_mha.json")
        self.assertEqual(target_scope["coverage_manifest"], "overlays/ITA/tests/pulp_ita_mha_coverage_regions.json")
        self.assertEqual(target_scope["mdir"], "artifacts/pulp_ita_mha_obj_dir")
        self.assertEqual(
            target_scope["cpu_reference_state"],
            "artifacts/pulp_ita_mha_obj_dir/pulp_ita_mha_cpu_repeat_1x1.bin",
        )
        self.assertEqual(
            target_scope["gpu_candidate_state"],
            "artifacts/pulp_ita_mha_obj_dir/pulp_ita_mha_gpu_from_cpu_init_1x1.bin",
        )
        self.assertEqual(
            gate["required_next_gate"]["name"],
            "run_pulp_ita_mha_first_generic_host_probe_build_run_compare_gate",
        )
        self.assertEqual(gate["required_next_gate"]["shape"], "1x1")
        self.assertEqual([entry["shape"] for entry in gate["deferred_shapes"]], ["32x1", "1x32"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "run_pulp_ita_mha_first_generic_host_probe_build_run_compare_gate")
        self.assertIn("not full ITA/MHA build/run/compare yet", gate["non_claims"])

        dry_run = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_mha.json",
                "--shape",
                "1x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_mha.json", dry_run.stdout)
        self.assertIn("--coverage-output-target pulp_ita_mha", dry_run.stdout)
        self.assertNotIn("make -C src/hybrid pulp_ita_mha_host_probe", dry_run.stdout)

        for token in (
            "pulp_ita_mha_dependency_template_boundary_gate.json",
            "promotes the `pulp_ita_mha` source boundary",
            "src/tools/build_host_probe.py",
            "next_task is `run_pulp_ita_mha_first_generic_host_probe_build_run_compare_gate`",
            "not full ITA/MHA build/run/compare yet",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_mha_first_generic_host_probe_build_run_compare_passed_1x1(self) -> None:
        gate = json.loads(PULP_ITA_MHA_FIRST_GENERIC_HOST_PROBE_BUILD_RUN_COMPARE_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "minimal_1x1_build_run_compare_passed_coverage_output_equivalence")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json",
        )
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_mha")
        self.assertEqual(gate["active_seed"], "pulp_ita_mha")
        self.assertEqual(gate["shape"], "1x1")
        self.assertEqual(
            gate["command"],
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x1",
        )
        self.assertEqual(gate["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["makefile_target_required"])
        for step, passed in gate["build_run_compare_steps"].items():
            with self.subTest(step=step):
                self.assertTrue(passed)

        coverage = gate["coverage_output_contract"]
        self.assertEqual(coverage["coverage_output_target"], "pulp_ita_mha")
        self.assertEqual(coverage["acceptance_policy"], "coverage_output_equivalence")
        self.assertEqual(coverage["compared_word_count"], 29)
        self.assertEqual(coverage["compared_byte_count"], 116)
        self.assertEqual(coverage["manifest_covered_word_count"], 18)

        measured = gate["measured_shape"]
        self.assertEqual(measured["shape"], "1x1")
        self.assertEqual(measured["nstates"], 1)
        self.assertEqual(measured["steps"], 1)
        self.assertEqual(measured["storage_size_bytes"], 6144)
        self.assertFalse(measured["raw_full_state_match"])
        self.assertEqual(measured["raw_full_state_mismatch_count"], 32)
        self.assertEqual(
            measured["raw_full_state_mismatch_role_summary"]["verilator_internal"]["mismatch_bytes"],
            32,
        )
        self.assertTrue(measured["normalized_final_state_equivalence_passed"])
        self.assertTrue(measured["coverage_output_equivalence_passed"])
        self.assertEqual(measured["coverage_output_mismatch_count"], 0)
        self.assertEqual(measured["cpu_elapsed_ms"], 2.91612)
        self.assertEqual(measured["hybrid_gpu_kernel_time_ms_total"], 0.856064)
        self.assertEqual(measured["hybrid_wall_time_ms"], 0.891)

        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_gate_passed"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_match_required"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy"]["shape_expansion_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "run_pulp_ita_mha_shape_expansion_gate")
        self.assertIn("not shape expansion evidence", gate["non_claims"])
        self.assertEqual([entry["shape"] for entry in gate["deferred_shapes"]], ["32x1", "1x32"])

        if (REPO_ROOT / measured["coverage_output_compare_report"]).exists():
            report = json.loads((REPO_ROOT / measured["coverage_output_compare_report"]).read_text(encoding="utf-8"))
            self.assertTrue(report["selected_acceptance_policy"]["passed"])
            self.assertEqual(report["selected_acceptance_policy"]["name"], "coverage_output_equivalence")
            self.assertEqual(report["coverage_output_policy"]["mismatch_count"], 0)
            self.assertEqual(report["coverage_output_policy"]["compared_word_count"], 29)
            self.assertEqual(report["coverage_output_policy"]["compared_byte_count"], 116)

        for token in (
            "pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
            "selected policy is `coverage_output_equivalence`",
            "mismatch count `0`",
            "Raw full-state equality remains false",
            "pulp_ita_mha_shape_expansion_gate",
            "run_pulp_ita_mha_shape_expansion_gate",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_mha_shape_expansion_records_32x1_and_1x32(self) -> None:
        gate = json.loads(PULP_ITA_MHA_SHAPE_EXPANSION_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "all_planned_shapes_passed_coverage_output_equivalence")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
        )
        self.assertEqual(gate["target"], "PULP_ITA.pulp_ita_mha")
        self.assertEqual(gate["active_seed"], "pulp_ita_mha")
        self.assertEqual(gate["planned_shapes"], ["32x1", "1x32"])
        self.assertEqual(gate["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertFalse(gate["makefile_target_required"])
        self.assertEqual(gate["acceptance_policy"], "coverage_output_equivalence")
        self.assertTrue(gate["result_summary"]["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(gate["result_summary"]["max_coverage_output_mismatch_count"], 0)
        self.assertIn("32x1 state-parallel", gate["result_summary"]["trend"])
        self.assertIn("1x32 single-state", gate["result_summary"]["trend"])

        coverage = gate["coverage_output_contract"]
        self.assertEqual(
            coverage["coverage_gate"],
            "config/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json",
        )
        self.assertEqual(coverage["coverage_output_target"], "pulp_ita_mha")
        self.assertEqual(coverage["strict_output_word_count_per_state"], 29)
        self.assertEqual(coverage["strict_output_byte_count_per_state"], 116)
        self.assertEqual(coverage["manifest_covered_word_count"], 18)

        shapes = {entry["shape"]: entry for entry in gate["measured_shapes"]}
        self.assertEqual(set(shapes), {"32x1", "1x32"})
        self.assertEqual(shapes["32x1"]["nstates"], 32)
        self.assertEqual(shapes["32x1"]["steps"], 1)
        self.assertEqual(shapes["32x1"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(shapes["32x1"]["coverage_output_compared_state_pair_count"], 32)
        self.assertEqual(shapes["32x1"]["coverage_output_compared_word_count"], 928)
        self.assertEqual(shapes["32x1"]["coverage_output_compared_byte_count"], 3712)
        self.assertEqual(shapes["32x1"]["cpu_elapsed_ms"], 72.0539)
        self.assertEqual(shapes["32x1"]["hybrid_gpu_kernel_time_ms_total"], 0.848896)
        self.assertEqual(shapes["32x1"]["hybrid_wall_time_ms"], 0.877)
        self.assertGreater(shapes["32x1"]["cpu_to_hybrid_wall_speedup_ratio"], 80.0)
        self.assertFalse(shapes["32x1"]["raw_full_state_match"])

        self.assertEqual(shapes["1x32"]["nstates"], 1)
        self.assertEqual(shapes["1x32"]["steps"], 32)
        self.assertEqual(shapes["1x32"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(shapes["1x32"]["coverage_output_compared_state_pair_count"], 1)
        self.assertEqual(shapes["1x32"]["coverage_output_compared_word_count"], 29)
        self.assertEqual(shapes["1x32"]["coverage_output_compared_byte_count"], 116)
        self.assertEqual(shapes["1x32"]["cpu_elapsed_ms"], 2.93625)
        self.assertEqual(shapes["1x32"]["hybrid_gpu_kernel_time_ms_total"], 1.42336)
        self.assertEqual(shapes["1x32"]["hybrid_wall_time_ms"], 1.453)
        self.assertGreater(shapes["1x32"]["cpu_to_hybrid_wall_speedup_ratio"], 2.0)
        self.assertLess(
            shapes["1x32"]["cpu_to_hybrid_wall_speedup_ratio"],
            shapes["32x1"]["cpu_to_hybrid_wall_speedup_ratio"],
        )
        self.assertFalse(shapes["1x32"]["raw_full_state_match"])

        for shape, entry in shapes.items():
            with self.subTest(shape=shape):
                self.assertTrue(entry["coverage_output_equivalence_passed"])
                self.assertTrue(entry["normalized_final_state_equivalence_passed"])
                self.assertEqual(
                    entry["raw_full_state_mismatch_role_summary"]["verilator_internal"]["field_count"],
                    4,
                )
                if (REPO_ROOT / entry["coverage_output_compare_report"]).exists():
                    report = json.loads((REPO_ROOT / entry["coverage_output_compare_report"]).read_text(encoding="utf-8"))
                    self.assertTrue(report["selected_acceptance_policy"]["passed"])
                    self.assertEqual(report["coverage_output_policy"]["mismatch_count"], 0)

        dry_run_32 = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_mha.json",
                "--shape",
                "32x1",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        dry_run_1x32 = subprocess.run(
            [
                "python3",
                "src/tools/run_hybrid_template.py",
                "config/slice_launch_templates/pulp_ita_mha.json",
                "--shape",
                "1x32",
                "--dry-run",
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        for stdout in (dry_run_32.stdout, dry_run_1x32.stdout):
            self.assertIn("python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_mha.json", stdout)
            self.assertIn("--coverage-output-target pulp_ita_mha", stdout)
            self.assertNotIn("make -C src/hybrid pulp_ita_mha_host_probe", stdout)

        self.assertFalse(gate["acceptance_policy_summary"]["broad_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy_summary"]["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertFalse(gate["acceptance_policy_summary"]["second_active_ita_seed_allowed_by_gate"])
        self.assertEqual(gate["next_task"], "review_pulp_ita_mha_shape_expansion_and_select_next_workload_or_hold")
        self.assertIn("not broad modern-NN speedup", gate["non_claims"])
        self.assertIn("not production LLM-serving throughput", gate["non_claims"])

        for token in (
            "pulp_ita_mha_shape_expansion_gate.json",
            "Both shapes pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`",
            "`32x1` has CPU elapsed `72.0539 ms` and hybrid wall `0.877 ms`",
            "`1x32` has CPU elapsed `2.93625 ms` and hybrid wall `1.453 ms`",
            "review_pulp_ita_mha_shape_expansion_and_select_next_workload_or_hold",
        ):
            self.assertIn(token, combined_docs)

    def test_pulp_ita_mha_shape_expansion_review_selects_result_packaging_refresh(self) -> None:
        gate = json.loads(PULP_ITA_MHA_SHAPE_EXPANSION_REVIEW_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["status"], "reviewed_select_result_packaging_refresh_next")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json")
        self.assertEqual(gate["reviewed_seed"], "pulp_ita_mha")
        self.assertEqual(gate["reviewed_result"]["planned_shapes"], ["32x1", "1x32"])
        self.assertTrue(gate["reviewed_result"]["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(gate["reviewed_result"]["max_coverage_output_mismatch_count"], 0)
        self.assertIn("32x1 state-parallel", gate["reviewed_result"]["trend"])
        self.assertIn("single-run timing", gate["reviewed_result"]["weakness"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["paged_attention_kv_cache_scale_up"]["decision"], "defer")
        self.assertEqual(options["resident_execution_optimization"]["decision"], "defer")
        self.assertEqual(options["result_packaging_refresh"]["decision"], "select_next")
        self.assertIn("workload-specific templates", options["paged_attention_kv_cache_scale_up"]["weakness"])
        self.assertIn("runtime/pass", options["resident_execution_optimization"]["weakness"])
        self.assertIn("does not create new measurement evidence", options["result_packaging_refresh"]["weakness"])

        selected = gate["selected_next_workstream"]
        self.assertEqual(selected["name"], "result_packaging_refresh")
        self.assertEqual(
            selected["required_next_gate"],
            "public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate",
        )
        self.assertFalse(selected["measurement_allowed_by_review_gate"])
        self.assertIn("fresh pulp_ita_mha first and shape-expansion gate chain", selected["scope"][0])

        self.assertTrue(gate["acceptance_policy"]["review_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "define_public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate",
        )
        self.assertIn("not a new workload measurement", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        for token in (
            "pulp_ita_mha_shape_expansion_review_gate.json",
            "selects `result_packaging_refresh` next",
            "paged attention/KV-cache scale-up",
            "resident execution optimization",
            "define_public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate",
            "reports and artifacts as generated evidence, not source of truth",
        ):
            self.assertIn(token, combined_docs)

    def test_candidate_template_clean_checkout_selection_gate_selects_nvdla_first(self) -> None:
        gate = json.loads(CANDIDATE_TEMPLATE_SELECTION_GATE.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            gate["status"],
            "complete_selection_ready_for_next_build_run_compare_gate",
        )
        self.assertEqual(
            gate["selected_for_next_build_run_compare_gate"]["primary"],
            "NVDLA.nvdla_cmac_core_mac",
        )
        self.assertEqual(
            gate["selected_for_next_build_run_compare_gate"]["secondary"],
            "NVDLA.nvdla_cmac_a2cacc",
        )
        self.assertEqual(
            gate["selected_for_next_build_run_compare_gate"]["next_gate"],
            "nvdla_cmac_core_mac_minimal_build_run_compare_gate",
        )

        selected = {entry["target"]: entry for entry in gate["candidate_inventory"]}
        for target, template_path, overlay_path, manifest_path in (
            (
                "NVDLA.nvdla_cmac_core_mac",
                NVDLA_CMAC_CORE_MAC_TEMPLATE,
                NVDLA_CMAC_CORE_MAC_OVERLAY,
                NVDLA_CMAC_CORE_MAC_MANIFEST,
            ),
            (
                "NVDLA.nvdla_cmac_a2cacc",
                NVDLA_CMAC_A2CACC_TEMPLATE,
                NVDLA_CMAC_A2CACC_OVERLAY,
                NVDLA_CMAC_A2CACC_MANIFEST,
            ),
        ):
            with self.subTest(target=target):
                entry = selected[target]
                template = json.loads(template_path.read_text(encoding="utf-8"))
                self.assertEqual(entry["host_probe_builder"], "src/tools/build_host_probe.py")
                self.assertFalse(entry["makefile_target_required"])
                self.assertTrue(entry["clean_checkout_ready"])
                self.assertEqual(entry["source_roots"], ["third_party/rtlmeter"])
                self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
                self.assertNotIn("makefile", template["planned_overlay"])
                self.assertTrue(_git_ls_files(template_path))
                self.assertTrue(_git_ls_files(overlay_path))
                self.assertTrue(_git_ls_files(manifest_path))
                for source_file in template["source_files"]:
                    self.assertTrue(source_file.startswith("third_party/rtlmeter/"))
                    self.assertTrue((REPO_ROOT / source_file).exists())

        deferred_groups = {entry["group"]: entry for entry in gate["deferred_candidate_groups"]}
        self.assertIn("PULP ITA / LLM-serving RTL", deferred_groups)
        self.assertIn("MobileViT CPU-kick", deferred_groups)
        self.assertIn("Ibex LLM SoC kick", deferred_groups)
        self.assertIn("third_party/ITA", json.dumps(deferred_groups["PULP ITA / LLM-serving RTL"]))
        self.assertIn("third_party/common_cells", json.dumps(deferred_groups["PULP ITA / LLM-serving RTL"]))
        self.assertIn("third_party/ibex", json.dumps(deferred_groups["Ibex LLM SoC kick"]))
        self.assertIn("not a CPU-vs-hybrid benchmark result", gate["non_claims"])
        self.assertIn("not a speedup claim", gate["non_claims"])
        self.assertIn(
            "not approval to import ITA, common_cells, or ibex without a dependency boundary",
            gate["non_claims"],
        )

        for token in (
            "candidate_template_clean_checkout_selection_gate.json",
            "NVDLA.nvdla_cmac_core_mac",
            "NVDLA.nvdla_cmac_a2cacc",
            "PULP ITA / LLM-serving RTL",
            "MobileViT CPU-kick",
            "Ibex LLM SoC kick",
            "nvdla_cmac_core_mac_minimal_build_run_compare_gate",
            "src/tools/build_host_probe.py",
            "third_party/rtlmeter",
        ):
            self.assertIn(token, combined_docs)

    def test_full_ita_mha_first_benchmark_gate_records_passing_smoke_compare(self) -> None:
        gate = json.loads(FULL_ITA_MHA_BENCHMARK_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "three_shapes_passed_coverage_output_equivalence")
        self.assertEqual(gate["target"], "pulp_ita_mha")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/neural_network_rtl_full_ita_mha_dependency_audit_gate.json")
        self.assertEqual(gate["overlay"]["coverage_tb"], "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv")
        self.assertEqual(gate["overlay"]["coverage_manifest"], "overlays/ITA/tests/pulp_ita_mha_coverage_regions.json")
        self.assertEqual(gate["overlay"]["launch_template"], "config/slice_launch_templates/pulp_ita_mha.json")
        self.assertEqual(gate["build_evidence"]["storage_size_bytes"], 6144)

        coverage = gate["coverage_output_contract"]
        self.assertEqual(coverage["total_words_per_state"], 29)
        self.assertEqual(coverage["total_bytes_per_state"], 116)
        self.assertEqual(coverage["acceptance_policy"], "coverage_output_equivalence")
        self.assertTrue(gate["acceptance_policy"]["cpu_vs_hybrid_compared"])
        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_gate_passed"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])

        result = gate["result"]
        self.assertEqual(result["status"], "three_shapes_passed_coverage_output_equivalence")
        self.assertEqual(result["summary_report"], "reports/pulp_ita_mha_first_hybrid_benchmark_summary.json")
        self.assertTrue(result["all_planned_shapes_passed_coverage_output_equivalence"])
        self.assertEqual(result["measured_shape_count"], 3)
        by_shape = {(shape["nstates"], shape["steps"]): shape for shape in result["measured_shapes"]}
        self.assertEqual(set(by_shape), {(1, 1), (32, 1), (1, 32)})
        for shape in by_shape.values():
            self.assertTrue(shape["coverage_output_equivalence_passed"])
            self.assertEqual(shape["coverage_output_mismatch_count"], 0)
        self.assertEqual(
            gate["next_task"],
            "review_full_ita_mha_and_larger_paged_kv_goal_completion_or_select_paged_attention_gap",
        )
        self.assertIn("not raw full-state equality", gate["non_claims"])

    def test_goal_review_keeps_goal_open_for_paged_attention_gap(self) -> None:
        gate = json.loads(GOAL_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "not_complete_select_paged_attention_gap")
        checklist = {entry["requirement"]: entry for entry in gate["prompt_to_artifact_checklist"]}
        self.assertEqual(checklist["larger paged KV-cache scale-up"]["status"], "satisfied")
        self.assertEqual(
            checklist["full ITA/MHA execution"]["status"],
            "satisfied_for_scoped_reduced_parameter_harness",
        )
        self.assertEqual(checklist["larger paged attention"]["status"], "missing")
        self.assertFalse(gate["completion_decision"]["goal_complete"])
        self.assertEqual(gate["selected_next_gap"]["name"], "paged_attention_kv_score_harness")
        self.assertEqual(gate["next_task"], "define_paged_attention_kv_score_harness_gate")
        self.assertIn("not full paged attention yet", gate["non_claims"])

    def test_paged_attention_kv_score_gate_defines_remaining_harness(self) -> None:
        gate = json.loads(PAGED_ATTENTION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "all_planned_shapes_passed_coverage_output_equivalence")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json")
        seed = gate["selected_next_seed"]
        self.assertEqual(seed["target"], "pulp_paged_attention_kv_score")
        self.assertEqual(seed["planned_overlay"], "overlays/ITA/src/pulp_paged_attention_kv_score_gpu_cov_tb.sv")
        self.assertEqual(seed["planned_coverage_manifest"], "overlays/ITA/tests/pulp_paged_attention_kv_score_coverage_regions.json")
        self.assertEqual(seed["planned_launch_template"], "config/slice_launch_templates/pulp_paged_attention_kv_score.json")
        self.assertEqual(seed["planned_host_probe_target"], "pulp_paged_attention_kv_score_host_probe")
        self.assertIn("deterministic Q/K score accumulation over selected prior slots", gate["required_rtl_behaviors"])
        self.assertIn("prior-slot KV read through the page table", gate["required_rtl_behaviors"])
        self.assertEqual(gate["coverage_output_contract"]["total_words_per_state"], 29)
        self.assertTrue(gate["acceptance_policy"]["all_planned_shapes_required_before_completion_review"])
        self.assertEqual(
            gate["next_task"],
            "audit_full_ita_mha_larger_paged_attention_kv_goal_completion",
        )
        self.assertIn("not full production paged attention", gate["non_claims"])

        result = gate["result"]
        self.assertEqual(result["measured_shape_count"], 3)
        self.assertTrue(result["all_planned_shapes_passed_coverage_output_equivalence"])
        by_shape = {(shape["nstates"], shape["steps"]): shape for shape in result["measured_shapes"]}
        self.assertEqual(set(by_shape), {(1, 1), (64, 1), (1, 64)})
        for shape in by_shape.values():
            self.assertTrue(shape["coverage_output_equivalence_passed"])
            self.assertEqual(shape["coverage_output_mismatch_count"], 0)

    def test_paged_attention_kv_score_files_and_summary_are_wired(self) -> None:
        self.assertTrue(PAGED_ATTENTION_OVERLAY.exists())
        self.assertTrue(PAGED_ATTENTION_MANIFEST.exists())
        self.assertTrue(PAGED_ATTENTION_TEMPLATE.exists())

        overlay = PAGED_ATTENTION_OVERLAY.read_text(encoding="utf-8")
        manifest = json.loads(PAGED_ATTENTION_MANIFEST.read_text(encoding="utf-8"))
        template = json.loads(PAGED_ATTENTION_TEMPLATE.read_text(encoding="utf-8"))
        summary = json.loads(PAGED_ATTENTION_GATE.read_text(encoding="utf-8"))["result"]

        self.assertIn("module pulp_paged_attention_kv_score_gpu_cov_tb", overlay)
        self.assertIn("ScoreWindow = 4", overlay)
        self.assertIn("function automatic logic [31:0] score_key", overlay)
        self.assertIn("selected_key_q", overlay)
        self.assertEqual(manifest["target"], "PULP_ITA.pulp_paged_attention_kv_score")
        self.assertEqual(manifest["top_module"], "pulp_paged_attention_kv_score_gpu_cov_tb")
        self.assertEqual(template["target"], "PULP_ITA.pulp_paged_attention_kv_score")
        self.assertEqual(template["build"]["host_probe_target"], "pulp_paged_attention_kv_score_host_probe")
        self.assertEqual(template["build"]["host_probe_builder"], "src/tools/build_host_probe.py")
        self.assertEqual(
            template["build"]["host_probe"]["clock_field"],
            "pulp_paged_attention_kv_score_gpu_cov_tb__DOT__clk_i",
        )

        self.assertTrue(summary["all_planned_shapes_passed_coverage_output_equivalence"])
        by_shape = {f"{shape['nstates']}x{shape['steps']}": shape for shape in summary["measured_shapes"]}
        self.assertEqual(set(by_shape), {"1x1", "64x1", "1x64"})
        for shape in by_shape.values():
            self.assertTrue(shape["coverage_output_equivalence_passed"])
            self.assertEqual(shape["coverage_output_mismatch_count"], 0)
            self.assertTrue(shape["coverage_output_compare_report"].startswith("reports/"))

    def test_completion_audit_marks_scoped_goal_complete(self) -> None:
        audit = json.loads(COMPLETION_AUDIT.read_text(encoding="utf-8"))

        self.assertEqual(audit["status"], "objective_satisfied_for_scoped_rtl_harness_goal")
        self.assertTrue(audit["completion_decision"]["complete"])
        checklist = {entry["requirement"]: entry for entry in audit["prompt_to_artifact_checklist"]}
        self.assertEqual(checklist["larger paged attention / KV-cache scale-up"]["status"], "satisfied")
        self.assertEqual(
            checklist["full ITA/MHA execution"]["status"],
            "satisfied_for_scoped_reduced_parameter_full_top",
        )
        self.assertEqual(
            checklist["paged attention, not only KV-cache"]["status"],
            "satisfied_for_minimal_paged_attention_kv_score_harness",
        )
        self.assertEqual(audit["next_task"], "hold_for_review_after_full_ita_mha_larger_paged_attention_kv_goal_completion")
        self.assertIn("not production paged attention", audit["non_claims"])

    def test_full_ita_mha_first_summary_and_compare_record_coverage_output_pass(self) -> None:
        gate = json.loads(FULL_ITA_MHA_BENCHMARK_GATE.read_text(encoding="utf-8"))
        summary = gate["result"]

        self.assertEqual(gate["target"], "pulp_ita_mha")
        self.assertEqual(summary["storage_size_bytes"], 6144)
        self.assertTrue(summary["all_planned_shapes_passed_coverage_output_equivalence"])
        by_shape = {f"{shape['nstates']}x{shape['steps']}": shape for shape in summary["measured_shapes"]}
        self.assertEqual(set(by_shape), {"1x1", "32x1", "1x32"})
        for shape in by_shape.values():
            self.assertTrue(shape["coverage_output_equivalence_passed"])
            self.assertEqual(shape["coverage_output_mismatch_count"], 0)
            self.assertTrue(shape["coverage_output_compare_report"].startswith("reports/"))
        self.assertEqual(gate["coverage_output_contract"]["total_words_per_state"], 29)
        self.assertEqual(gate["coverage_output_contract"]["total_bytes_per_state"], 116)

    def test_full_ita_mha_scaleup_64x1_and_1x64_records_tendency(self) -> None:
        gate = json.loads(FULL_ITA_MHA_SCALEUP_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "passed_coverage_output_equivalence_and_recorded_timing_tendency")
        self.assertEqual(gate["target"], "pulp_ita_mha")
        self.assertTrue(gate["conclusion"]["matches_prior_hypothesis"])
        self.assertEqual(gate["runs"]["state_parallel_64x1"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(gate["runs"]["single_state_repeated_1x64"]["coverage_output_mismatch_count"], 0)
        self.assertGreater(
            gate["runs"]["state_parallel_64x1"]["cpu_elapsed_ms_div_hybrid_reported_wall_ms"],
            100.0,
        )
        self.assertLess(
            gate["runs"]["single_state_repeated_1x64"]["cpu_elapsed_ms_div_hybrid_reported_wall_ms"],
            1.0,
        )
        self.assertIn("strongly favorable", gate["conclusion"]["state_parallel"])
        self.assertIn("remains weak", gate["conclusion"]["repeated_step"])
        self.assertIn("not raw full-state equality", gate["non_claims"])

    def test_full_ita_mha_prefill_decode_split_records_serving_view(self) -> None:
        gate = json.loads(FULL_ITA_MHA_PREFILL_DECODE_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "passed_prefill_decode_split_recorded_from_full_mha_scaleup")
        self.assertEqual(gate["target"], "pulp_ita_mha")
        self.assertEqual(gate["prefill_like"]["shape"], "64x1")
        self.assertEqual(gate["decode_like"]["shape"], "1x64")
        self.assertTrue(gate["acceptance_policy"]["prefill_like_coverage_output_equivalence_passed"])
        self.assertTrue(gate["acceptance_policy"]["decode_like_coverage_output_equivalence_passed"])
        self.assertEqual(gate["acceptance_policy"]["prefill_like_mismatch_count"], 0)
        self.assertEqual(gate["acceptance_policy"]["decode_like_mismatch_count"], 0)
        self.assertTrue(gate["acceptance_policy"]["prefill_like_hybrid_favorable"])
        self.assertTrue(gate["acceptance_policy"]["decode_like_hybrid_weak"])
        self.assertFalse(gate["acceptance_policy"]["speedup_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["prefill_like"]["classification"], "hybrid_favorable")
        self.assertEqual(gate["decode_like"]["classification"], "hybrid_weak")
        self.assertIn("not real token prefill/decode semantics", gate["non_claims"])

    def test_full_ita_mha_resident_decode_probe_records_improvement(self) -> None:
        gate = json.loads(FULL_ITA_MHA_RESIDENT_DECODE_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["status"],
            "passed_resident_decode_probe_improved_timing_and_kept_coverage_output_equivalence",
        )
        self.assertTrue(gate["acceptance_policy"]["baseline_coverage_output_passed"])
        self.assertTrue(gate["acceptance_policy"]["resident_coverage_output_passed"])
        self.assertEqual(gate["acceptance_policy"]["baseline_mismatch_count"], 0)
        self.assertEqual(gate["acceptance_policy"]["resident_mismatch_count"], 0)
        self.assertTrue(gate["acceptance_policy"]["resident_gpu_kernel_total_improved"])
        self.assertTrue(gate["acceptance_policy"]["resident_hybrid_wall_improved"])
        self.assertGreater(gate["resident_decode_like_1x64"]["gpu_kernel_total_ms"], 0.0)
        self.assertGreater(gate["baseline_decode_like_1x64"]["gpu_kernel_total_ms"], gate["resident_decode_like_1x64"]["gpu_kernel_total_ms"])
        self.assertIn("single-run timing only", gate["non_claims"])

    def test_full_ita_mha_resident_decode_batch_parallel_records_improvement(self) -> None:
        gate = json.loads(FULL_ITA_MHA_RESIDENT_BATCH_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["status"],
            "passed_resident_decode_batch_parallel_improves_per_state_step_and_keeps_coverage_output_equivalence",
        )
        self.assertEqual(gate["target"], "pulp_ita_mha")
        self.assertEqual(gate["acceptance_policy"]["baseline_shape"], "1x64")
        self.assertEqual(set(gate["acceptance_policy"]["compare_shapes"]), {"8x64", "16x64", "32x64"})
        self.assertTrue(gate["result"]["all_coverage_output_passed"])
        self.assertTrue(gate["result"]["all_resident_mode"])
        self.assertGreater(gate["result"]["best_gpu_per_state_step_improvement_ratio"], 1.0)
        self.assertGreater(gate["result"]["best_wall_per_state_step_improvement_ratio"], 1.0)

        checklist_reports = {
            entry["item"]: entry["report"]
            for entry in gate["checklist"]
            if entry["item"].startswith("measure ")
        }
        self.assertEqual(set(checklist_reports), {"measure 8x64 resident", "measure 16x64 resident", "measure 32x64 resident"})
        for report in checklist_reports.values():
            self.assertTrue(report.startswith("reports/"))
        self.assertEqual(gate["result"]["best_gpu_per_state_step_shape"], "32x64")
        self.assertIn("not a claim that larger batches reduce single-request latency", gate["non_claims"])

    def test_modern_llm_completion_audit_maps_conditions_to_current_evidence(self) -> None:
        audit = json.loads(MODERN_LLM_COMPLETION_AUDIT.read_text(encoding="utf-8"))

        self.assertEqual(
            audit["status"],
            "objective_satisfied_for_scoped_llm_serving_rtl_condition_investigation",
        )
        self.assertTrue(audit["completion_decision"]["complete"])
        checklist = {entry["requirement"]: entry for entry in audit["prompt_to_artifact_checklist"]}
        for requirement in (
            "modern LLM serving-like RTL workload",
            "correct hybrid runtime behavior",
            "fast execution conditions",
            "reproducible operation",
            "active surface and generated output separation",
            "non-claims and remaining limits",
        ):
            self.assertIn(requirement, checklist)
            self.assertNotEqual(checklist[requirement]["status"], "missing")

        conditions = audit["condition_statement"]
        self.assertIn("coverage-output equivalence", conditions["correctness_condition"])
        self.assertIn("state-parallel", conditions["fast_condition"])
        self.assertIn("Resident execution helps", conditions["decode_condition"])
        self.assertIn("32x64", conditions["batch_decode_condition"])
        self.assertIn("run_results_reproduction.py", conditions["reproducibility_condition"])
        self.assertEqual(
            audit["measured_condition_highlights"]["resident_decode_batch_parallel_32x64"][
                "coverage_output_mismatch_count"
            ],
            0,
        )
        self.assertGreater(
            audit["measured_condition_highlights"]["resident_decode_batch_parallel_32x64"][
                "wall_per_state_step_improvement_ratio_vs_1x64_resident"
            ],
            1.0,
        )
        mobile_vit = audit["measured_condition_highlights"]["mobile_vit_imagenet_128_cpu_kick_hybrid_proxy"]
        self.assertEqual(mobile_vit["evaluated_count"], 128)
        self.assertEqual(mobile_vit["coverage_output_mismatch_count"], 0)
        self.assertEqual(
            mobile_vit["one_command"],
            "python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128",
        )
        self.assertEqual(
            audit["representative_evidence"]["mobile_vit_imagenet_128"],
            "reports/mobile_vit_hybrid_128_summary.json",
        )
        self.assertIn("not production LLM serving throughput", audit["residual_non_claims"])
        self.assertIn("not MobileViT numerical inference in RTL", audit["residual_non_claims"])
        self.assertIn("single-run timing for the latest resident batch-parallel result", audit["residual_non_claims"])

    def test_public_results_packaging_records_conclusion_repro_tables_and_non_claims(self) -> None:
        gate = json.loads(PUBLIC_RESULTS_GATE.read_text(encoding="utf-8"))
        results = RESULTS.read_text(encoding="utf-8")

        self.assertEqual(
            gate["status"],
            "refreshed_public_benchmark_pack_after_wrapper_summary_schema_publication",
        )
        self.assertEqual(gate["results_doc"], "docs/results.md")
        self.assertEqual(
            gate["current_priority"],
            "public_benchmark_pack_externalization_ready",
        )
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/persistent_resident_device_handle_storage_review_gate.json",
        )
        self.assertIn("persistent resident ABI", gate["objective"])
        self.assertIn("Verilator", gate["benchmark_pack_scope"]["long_term_goal"])
        self.assertEqual(
            gate["benchmark_pack_scope"]["next_goal"],
            "public_benchmark_pack_externalization_ready",
        )
        self.assertIn(
            "python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --dry-run",
            gate["benchmark_pack_scope"]["entrypoints"],
        )
        self.assertIn(
            "python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run",
            gate["benchmark_pack_scope"]["entrypoints"],
        )
        self.assertIn(
            "reports/persistent_resident_state_abi_probe_summary.json",
            gate["benchmark_pack_scope"]["representative_reports"],
        )
        self.assertIn(
            "reports/mobile_vit_hybrid_128_summary.json",
            gate["benchmark_pack_scope"]["representative_reports"],
        )
        self.assertIn(
            "reports/hybrid_benchmark_mobile_vit_template_limit128.json",
            gate["benchmark_pack_scope"]["representative_reports"],
        )
        checklist = {entry["requirement"]: entry for entry in gate["prompt_to_artifact_checklist"]}
        for requirement in (
            "結論",
            "再現手順",
            "表",
            "非主張",
            "実測 evidence",
            "契約テスト",
            "wrapper summary schema",
            "local absolute path policy",
            "public pack manifest",
            "public reproduction smoke",
            "public_release_checklist_ready",
        ):
            self.assertEqual(checklist[requirement]["status"], "satisfied")

        for heading in (
            "## Conclusion",
            "## How To Read This Pack",
            "## Correctness Condition",
            "## Performance Summary",
            "## MobileViT ImageNet Evidence",
            "## Reproduction",
            "## Non-Claims",
            "## Source Evidence",
        ):
            self.assertIn(heading, results)
        for token in (
            "coverage_output_equivalence",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 32x1 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x32 --dry-run",
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1 --dry-run",
            "Fresh full ITA/MHA generic-host-probe chain",
            "pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
            "pulp_ita_mha_shape_expansion_gate.json",
            "pulp_ita_mha_shape_expansion_review_gate.json",
            "public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json",
            "`32x1` | state-parallel | `72.0539` | `0.877`",
            "`1x32` | single-state repeated-step | `2.93625` | `1.453`",
            "not a paper-ready statistical benchmark",
            "reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json",
            "reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json",
            "reports/results_reproduction_median_summary.json",
            "reports/persistent_resident_state_abi_probe_summary.json",
            "--persistent-resident-state-abi 16x64",
            "cross-process persistent CUDA state",
            "not raw full-state equality",
            "production LLM serving throughput",
            "Repeat-median timing highlights",
            "reports/mobile_vit_hybrid_128_summary.json",
            "reports/mobile_vit_cpu_kick_rtl_proxy_imagenet_batch1_128_cpu_vs_hybrid_1x1_coverage_output_compare.json",
            "cfg_batch_length=128",
            "0.7734375",
            "0.953125",
            "not MobileViT numerical inference in RTL",
            "not ImageNet accuracy from RTL logits",
            "python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128",
            "Wrapper summary schema fields:",
            "Evidence status terms:",
            "Treat `reports/*.json` as generated evidence",
            "External pack boundary:",
            "Prerequisites by path:",
            "A clean checkout should treat those reports as reproducible outputs",
            "CUDA-capable runtime",
            "local Hugging Face ImageNet parquet cache",
            "Public pack manifest:",
            "Public reproduction smoke:",
            "## Public Release Checklist",
            "public_release_checklist_ready",
            "Current source of truth",
            "Current source of truth and reader pack",
            "this document is the external-facing result pack",
            "Gate and audit evidence",
            "Reproduction tools",
            "Target templates",
            "Contract tests",
            "Generated review evidence",
            "Non-pack outputs",
            "`existing_evidence`",
            "`executed`",
            "reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json",
            "reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json",
            "reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json",
            "reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json",
            "reports/hybrid_benchmark_mobile_vit_template_limit128.json",
            "existing_evidence",
        ):
            self.assertIn(token, results)
        self.assertEqual(gate["next_task"], "public_benchmark_pack_externalization_ready")

    def test_public_results_packaging_refresh_after_mha_shape_expansion_is_defined(self) -> None:
        gate = json.loads(PUBLIC_RESULTS_MHA_REFRESH_GATE.read_text(encoding="utf-8"))
        results = RESULTS.read_text(encoding="utf-8")
        combined_docs = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                results,
            ]
        )

        self.assertEqual(
            gate["status"],
            "defined_public_results_packaging_refresh_after_fresh_mha_shape_expansion",
        )
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json",
        )
        self.assertEqual(gate["selected_workstream"], "result_packaging_refresh")
        self.assertEqual(gate["results_doc"], "docs/results.md")
        self.assertEqual(
            gate["fresh_mha_gate_chain"],
            [
                "config/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json",
                "config/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
                "config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json",
                "config/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json",
            ],
        )

        evidence = gate["fresh_mha_evidence"]
        self.assertEqual(evidence["correctness_policy"], "coverage_output_equivalence")
        self.assertTrue(evidence["all_listed_shapes_passed"])
        self.assertEqual(evidence["max_coverage_output_mismatch_count"], 0)
        shapes = {entry["shape"]: entry for entry in evidence["shapes"]}
        self.assertEqual(set(shapes), {"1x1", "32x1", "1x32"})
        self.assertEqual(shapes["1x1"]["hybrid_wall_time_ms"], 0.891)
        self.assertEqual(shapes["32x1"]["cpu_elapsed_ms"], 72.0539)
        self.assertEqual(shapes["32x1"]["hybrid_wall_time_ms"], 0.877)
        self.assertEqual(shapes["1x32"]["cpu_elapsed_ms"], 2.93625)
        self.assertEqual(shapes["1x32"]["hybrid_wall_time_ms"], 1.453)

        self.assertTrue(gate["acceptance_policy"]["documentation_refresh_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(gate["next_task"], "public_benchmark_pack_externalization_ready")
        self.assertIn("not repeat-median statistical evidence", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        for token in (
            "public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json",
            "Fresh full ITA/MHA generic-host-probe chain",
            "pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
            "pulp_ita_mha_shape_expansion_gate.json",
            "pulp_ita_mha_shape_expansion_review_gate.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json",
            "This fresh chain is single-run evidence",
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        ):
            self.assertIn(token, combined_docs)

    def test_public_benchmark_pack_completion_audit_maps_objective_to_evidence(self) -> None:
        audit = json.loads(PUBLIC_BENCHMARK_PACK_COMPLETION_AUDIT.read_text(encoding="utf-8"))

        self.assertEqual(audit["status"], "complete_public_benchmark_pack_current_revision")
        self.assertEqual(audit["source_packaging_gate"], "config/scaling_gates/public_results_packaging_gate.json")
        self.assertEqual(
            audit["source_packaging_gate_status"],
            "refreshed_public_benchmark_pack_after_wrapper_summary_schema_publication",
        )
        self.assertEqual(audit["current_priority"], "public_benchmark_pack_externalization_ready")
        self.assertEqual(audit["next_task"], "public_benchmark_pack_externalization_ready")
        self.assertTrue(audit["completion_decision"]["achieved"])

        checklist = {entry["requirement"]: entry for entry in audit["prompt_to_artifact_checklist"]}
        for requirement in (
            "LLM serving に近い RTL workload",
            "Verilator に近い簡単さで hybrid 実行",
            "正しさ",
            "速度傾向",
            "再現手順",
            "公開可能な benchmark pack",
            "非主張を明示",
            "検証",
            "wrapper summary schema",
            "local absolute path policy",
            "public pack manifest",
        ):
            self.assertEqual(checklist[requirement]["status"], "satisfied")

        persistent = audit["measured_evidence_summary"]["persistent_resident_state_abi"]
        self.assertEqual(persistent["state_authority"], "in_process_gpu_d_storage_after_phase_1")
        self.assertTrue(persistent["all_coverage_output_passed"])
        self.assertEqual(persistent["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(persistent["hybrid_wall_ms"], 4.517)
        mobile_vit = audit["measured_evidence_summary"]["mobile_vit_imagenet_128"]
        self.assertEqual(mobile_vit["evaluated_count"], 128)
        self.assertEqual(mobile_vit["top1_accuracy"], 0.7734375)
        self.assertTrue(mobile_vit["coverage_output_equivalence_complete"])
        self.assertEqual(mobile_vit["coverage_output_mismatch_count"], 0)
        self.assertEqual(
            mobile_vit["one_command"],
            "python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128",
        )
        self.assertIn("not cross-process persistent CUDA state", audit["non_claims"])
        self.assertIn("not ImageNet accuracy from RTL logits", audit["non_claims"])
        wrapper = audit["measured_evidence_summary"]["wrapper_summary_schema"]
        self.assertEqual(wrapper["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(wrapper["mobile_vit_execution_mode"], "existing_evidence")
        self.assertIn("reports/hybrid_benchmark_mobile_vit_template_limit128.json", wrapper["reports"])

    def test_public_benchmark_pack_externalization_readiness_is_documented(self) -> None:
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        gate = json.loads(PUBLIC_RESULTS_GATE.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(gate["current_priority"], "public_benchmark_pack_externalization_ready")
        self.assertEqual(gate["next_task"], "public_benchmark_pack_externalization_ready")
        self.assertEqual(
            gate["minimum_public_dry_run_smoke"],
            [
                "python3 src/tools/run_results_reproduction.py --dry-run",
                "python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run",
            ],
        )
        for token in (
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
            "How To Read This Pack",
            "External pack boundary:",
            "Prerequisites by path:",
            "Public pack manifest:",
            "README.md`, `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, `docs/results.md",
            "records/scaling_gates/public_results_packaging_gate.json",
            "records/scaling_gates/public_benchmark_pack_goal_completion_audit.json",
            "records/scaling_gates/generic_hybrid_benchmark_cli_gate.json",
            "config/scaling_gates/public_results_packaging_gate.json",
            "src/tools/run_results_reproduction.py",
            "src/tools/results_reproduction.py",
            "src/tools/run_hybrid_benchmark.py",
            "src/tools/hybrid_benchmark.py",
            "tests/contract/test_full_ita_mha_larger_paged_kv_next.py",
            "tests/contract/test_hybrid_verilator_like_cli.py",
            "config/slice_launch_templates/pulp_ita_mha.json",
            "reports/hybrid_benchmark_*.json",
            "python3 src/tools/run_results_reproduction.py --dry-run",
            "python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run",
            "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run",
            "python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run",
            "Public archive dry-run:",
            "public_pack_archive_ready",
            "candidate_template_clean_checkout_selection_gate.json",
            "nvdla_cmac_core_mac_minimal_build_run_compare_gate.json",
            "nvdla_cmac_core_mac_template_shape_expansion_gate.json",
            "nvdla_shape_expansion_next_workstream_review_gate.json",
            "ita_dependency_clean_checkout_boundary_gate.json",
            "ita_first_seed_selection_after_dependency_boundary_gate.json",
            "pulp_ita_dotp_overlay_template_generic_host_probe_gate.json",
            "pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json",
            "pulp_ita_dotp_shape_expansion_gate.json",
            "pulp_ita_dotp_shape_expansion_review_gate.json",
            "pulp_ita_softmax_top_dependency_template_boundary_gate.json",
            "pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.json",
            "pulp_ita_softmax_top_shape_expansion_gate.json",
            "pulp_ita_softmax_top_shape_expansion_review_gate.json",
            "pulp_ita_mha_dependency_template_boundary_gate.json",
            "pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
            "pulp_ita_mha_shape_expansion_gate.json",
            "pulp_ita_mha_shape_expansion_review_gate.json",
            "public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json",
            "next_task: select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
            "review `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json`",
            "Review/stage boundary:",
            "docs/roadmap.md",
            "docs/status.md",
            "records/scaling_gates/ita_first_seed_selection_after_dependency_boundary_gate.json",
            "records/scaling_gates/pulp_ita_dotp_overlay_template_generic_host_probe_gate.json",
            "records/scaling_gates/pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json",
            "records/scaling_gates/pulp_ita_dotp_shape_expansion_gate.json",
            "records/scaling_gates/pulp_ita_dotp_shape_expansion_review_gate.json",
            "records/scaling_gates/pulp_ita_softmax_top_dependency_template_boundary_gate.json",
            "records/scaling_gates/pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.json",
            "records/scaling_gates/pulp_ita_softmax_top_shape_expansion_gate.json",
            "records/scaling_gates/pulp_ita_softmax_top_shape_expansion_review_gate.json",
            "records/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json",
            "records/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json",
            "records/scaling_gates/pulp_ita_mha_shape_expansion_gate.json",
            "records/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json",
            "docs/results.md",
            "config/slice_launch_templates/pulp_ita_mha.json",
            "overlays/ITA/src/pulp_ita_tc_sram_sim.sv",
            "overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv",
            "overlays/ITA/tests/pulp_ita_mha_coverage_regions.json",
            "config/slice_launch_templates/pulp_ita_dotp.json",
            "config/slice_launch_templates/pulp_ita_softmax_top.json",
            "overlays/ITA/src/pulp_ita_dotp_gpu_cov_tb.sv",
            "overlays/ITA/tests/pulp_ita_dotp_coverage_regions.json",
            "overlays/ITA/src/pulp_ita_cluster_clock_gating_sim.sv",
            "overlays/ITA/src/pulp_ita_softmax_top_gpu_cov_tb.sv",
            "overlays/ITA/tests/pulp_ita_softmax_top_coverage_regions.json",
            "records/scaling_gates/ita_dependency_clean_checkout_boundary_gate.json",
            "records/scaling_gates/nvdla_shape_expansion_next_workstream_review_gate.json",
            "records/scaling_gates/candidate_template_clean_checkout_selection_gate.json",
            "records/scaling_gates/nvdla_cmac_core_mac_minimal_build_run_compare_gate.json",
            "records/scaling_gates/nvdla_cmac_core_mac_template_shape_expansion_gate.json",
            "config/slice_launch_templates/nvdla_cmac_core_mac.json",
            "overlays/rtlmeter/designs/NVDLA/src/nvdla_cmac_core_mac_gpu_cov_tb.sv",
            "overlays/rtlmeter/designs/NVDLA/tests/nvdla_cmac_core_mac_coverage_regions.json",
            "src/tools/hybrid_template_runner.py",
            "tests/contract/test_hybrid_verilator_like_cli.py",
            "Exclude from this review boundary:",
            "src/hybrid/Makefile",
            "third_party/ITA`, `third_party/common_cells`, and `third_party/ibex` edits beyond validating required source paths",
            "third_party/ibex",
            "additional NVDLA targets beyond `nvdla_cmac_core_mac`",
            "`ita_softmax_top`, KV-cache, LLM SoC, and MobileViT candidate templates and overlays",
            "MobileViT, tiny LLM serving, and LLM SoC CPU-kick tools/tests",
            "runtime/pass changes already closed by `resident_runtime_contract_completion_boundary`",
            "generated-config tooling already closed by `verilator_like_hybrid_config_generation_boundary`",
            "candidate selection gate identifies `NVDLA.nvdla_cmac_core_mac` as primary",
            "minimal build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`",
            "next workstream review selects `ita_dependency_clean_checkout_boundary`",
            "ITA dependency boundary gate records canonical `.gitmodules` entries and gitlinks for `third_party/ITA` and `third_party/common_cells`",
            "ITA first seed selection gate selects `pulp_ita_dotp` and defers `pulp_ita_softmax_top`",
            "`third_party/ITA/src/ita_dotp.sv` is the only required ITA source path for the first selected seed",
            "PULP ITA dotp overlay/template gate carries `build.host_probe_builder: src/tools/build_host_probe.py`",
            "dry-run emits `python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_dotp.json`",
            "PULP ITA dotp first build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`",
            "PULP ITA dotp first build/run/compare gate records raw full-state equality as false with Verilator-internal-only mismatch",
            "PULP ITA dotp shape expansion gate records `64x1` and `1x64` coverage-output pass with mismatch count `0`",
            "PULP ITA dotp shape expansion gate records `64x1` as much more favorable than `1x64` in scoped single-run timing",
            "PULP ITA dotp shape expansion review gate selects `ita_softmax_top_dependency_template_boundary` next",
            "PULP ITA dotp shape expansion review gate keeps softmax measurement separate from boundary definition",
            "PULP ITA softmax-top dependency/template boundary gate carries `build.host_probe_builder: src/tools/build_host_probe.py`",
            "dry-run emits `python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_softmax_top.json`",
            "PULP ITA softmax-top first build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`",
            "PULP ITA softmax-top first build/run/compare gate records raw full-state equality as false with Verilator-internal-only mismatch",
            "PULP ITA softmax-top shape expansion gate records `64x1` and `1x64` coverage-output pass with mismatch count `0`",
            "PULP ITA softmax-top shape expansion gate records `64x1` as much more favorable than `1x64` in scoped single-run timing",
            "PULP ITA softmax-top shape expansion review gate selects `full_ita_mha_dependency_template_boundary` next",
            "PULP ITA softmax-top shape expansion review gate keeps full MHA measurement separate from boundary definition",
            "PULP ITA MHA dependency/template boundary gate carries `build.host_probe_builder: src/tools/build_host_probe.py`",
            "PULP ITA MHA dependency/template boundary gate keeps first full MHA measurement separate from boundary definition",
            "PULP ITA MHA first build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`",
            "PULP ITA MHA first build/run/compare gate records raw full-state equality as false with Verilator-internal-only mismatch",
            "PULP ITA MHA shape expansion gate records `32x1` and `1x32` coverage-output pass with mismatch count `0`",
            "PULP ITA MHA shape expansion gate records `32x1` as much more favorable than `1x32` in scoped single-run timing",
            "the NVDLA `cmac_core_mac` template references only present source files",
            "the template carries `build.host_probe_builder: src/tools/build_host_probe.py`",
            "`run_hybrid_template.py` passes template `verilator_defines` into the Verilator command",
            "`src/hybrid/Makefile` remains free of generated NVDLA host-probe targets",
            "no generated output is introduced as source of truth",
            "python3 -m unittest tests.contract.test_resident_runtime_contract -q",
            "tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>",
            "reports/` and `artifacts/` as generated evidence/output only",
            "A clean checkout should treat those reports as reproducible outputs",
            "Source-of-truth alignment",
            "Local path hygiene",
            "Smoke commands",
            "Evidence claims",
            "Non-claims",
            "Contract tests",
            "Archive dry-run",
            "python3 -m unittest discover -s tests/contract -q",
            "coverage_output_equivalence",
            "not raw full-state equality",
        ):
            self.assertIn(token, combined)

    def test_public_benchmark_pack_externalization_readiness_audit_is_defined(self) -> None:
        audit = json.loads(PUBLIC_BENCHMARK_PACK_EXTERNALIZATION_AUDIT.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(audit["audit"], "public_benchmark_pack_externalization_readiness")
        self.assertEqual(audit["status"], "ready_for_external_review")
        self.assertEqual(audit["current_priority"], "public_benchmark_pack_externalization_ready")
        self.assertEqual(audit["source_packaging_gate"], "config/scaling_gates/public_results_packaging_gate.json")
        self.assertEqual(
            audit["source_refresh_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
        )
        self.assertTrue(audit["decision"]["externalization_ready"])
        self.assertEqual(audit["results_doc"], "docs/results.md")
        self.assertEqual(audit["evidence_policy"]["correctness_policy"], "coverage_output_equivalence")
        self.assertTrue(audit["evidence_policy"]["generated_reports_are_evidence_only"])
        self.assertFalse(audit["evidence_policy"]["generated_artifacts_are_source_of_truth"])
        self.assertFalse(audit["evidence_policy"]["existing_evidence_is_fresh_execution"])
        self.assertEqual(
            audit["minimum_public_dry_run_smoke"],
            [
                "python3 src/tools/run_results_reproduction.py --dry-run",
                "python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run",
                "python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run",
            ],
        )
        for check in (
            "source_of_truth_alignment",
            "reader_guide_and_boundaries",
            "local_path_hygiene",
            "public_smoke_commands",
            "archive_dry_run",
            "evidence_claim_scope",
            "non_claims",
            "contract_tests",
        ):
            self.assertIn(check, audit["release_checks"])
        for path in (
            "README.md",
            "config/selection.json",
            "docs/status.md",
            "docs/roadmap.md",
            "docs/results.md",
            "records/scaling_gates/public_results_packaging_gate.json",
            "records/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json",
            "records/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json",
            "records/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json",
            "records/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json",
            "records/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
            "records/scaling_gates/public_benchmark_pack_goal_completion_audit.json",
            "records/scaling_gates/generic_hybrid_benchmark_cli_gate.json",
        ):
            self.assertIn(path, audit["required_review_surfaces"])
        for non_claim in (
            "not a new measurement result",
            "not production LLM serving throughput",
            "not raw full-state equality",
            "not cross-process persistent CUDA state",
            "not full 50k ImageNet hybrid execution",
            "not production paged attention",
            "not broad speedup for arbitrary RTL",
            "not ImageNet accuracy from RTL logits",
        ):
            self.assertIn(non_claim, audit["non_claims"])
        self.assertEqual(audit["next_task"], "run_public_release_checklist_or_choose_next_measurement_goal")

        for token in (
            "public_benchmark_pack_externalization_readiness_audit.json",
            "ready_for_external_review",
            "Externalization readiness audit:",
            "minimum review surfaces, smoke commands, release checks, and evidence policy",
            "`docs/results.md` is the external-facing result pack and reader guide",
            "reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json",
            "reports/hybrid_benchmark_mobile_vit_template_limit128.json",
            "next_goal_selection_after_persistent_resident_repeat_median_gate.json",
            "persistent_resident_state_abi_repeat_median_measurement_gate.json",
            "persistent resident repeat-median refresh",
            "reports/persistent_resident_state_abi_repeat_median_summary.json",
            "not a new measurement result",
        ):
            self.assertIn(token, combined)

    def test_public_benchmark_pack_externalization_completion_gate_is_defined(self) -> None:
        gate = json.loads(PUBLIC_BENCHMARK_PACK_EXTERNALIZATION_COMPLETION_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "public_benchmark_pack_externalization_completion_gate")
        self.assertEqual(
            gate["status"],
            "complete_public_benchmark_pack_externalization_boundary_after_repeat_median_refresh",
        )
        self.assertEqual(gate["completed_priority"], "public_benchmark_pack_externalization_ready")
        self.assertEqual(
            gate["source_readiness_audit"],
            "config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json",
        )
        self.assertEqual(
            gate["source_refresh_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
        )
        self.assertEqual(gate["results_doc"], "docs/results.md")
        self.assertTrue(gate["decision"]["externalization_boundary_complete"])
        self.assertTrue(gate["release_check_evidence"]["archive_dry_run_includes_repeat_median_refresh"])
        self.assertEqual(
            gate["release_check_evidence"]["latest_generated_evidence"],
            "reports/persistent_resident_state_abi_repeat_median_summary.json",
        )
        self.assertTrue(gate["acceptance_policy"]["completion_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_workload_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(
            gate["next_task"],
            "select_next_measurement_after_public_benchmark_pack_externalization",
        )
        self.assertIn("paged_attention_kv_cache_scale_up", gate["candidate_next_measurement_options"])
        self.assertIn("not a new measurement result", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_benchmark_pack_externalization_completion_gate"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["next_measurement_selection_after_public_benchmark_pack_externalization_gate"],
            "config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_scale_up_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_scale_up_measurement_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        )

        for token in (
            "public_benchmark_pack_externalization_completion_gate.json",
            "next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
            "paged_attention_kv_cache_scale_up_measurement_gate.json",
            "select_next_measurement_after_public_benchmark_pack_externalization",
            "define_paged_attention_kv_cache_scale_up_measurement_gate",
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
            "paged-attention/KV-cache scale-up",
            "public benchmark pack externalization boundary",
            "The next_task is `select_next_measurement_after_public_benchmark_pack_externalization`",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
        ):
            self.assertIn(token, combined)

    def test_next_measurement_after_public_pack_externalization_selects_paged_attention_kv_scaleup(self) -> None:
        gate = json.loads(NEXT_MEASUREMENT_AFTER_PUBLIC_PACK_EXTERNALIZATION_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "next_measurement_selection_after_public_benchmark_pack_externalization_gate")
        self.assertEqual(gate["status"], "selected_paged_attention_kv_cache_scale_up_next")
        self.assertEqual(
            gate["source_completion_gate"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json",
        )
        self.assertEqual(gate["source_results_doc"], "docs/results.md")
        self.assertEqual(gate["selected_next_goal"]["name"], "paged_attention_kv_cache_scale_up")
        self.assertEqual(
            gate["selected_next_goal"]["first_gate"],
            "define_paged_attention_kv_cache_scale_up_measurement_gate",
        )
        self.assertEqual(gate["next_task"], "define_paged_attention_kv_cache_scale_up_measurement_gate")
        self.assertTrue(gate["acceptance_policy"]["selection_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_workload_allowed_by_this_gate"])
        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_required_for_later_measurement"])
        self.assertTrue(gate["acceptance_policy"]["contract_tests_required_for_next_public_workflow"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_equality_required"])
        self.assertFalse(gate["acceptance_policy"]["reports_and_artifacts_are_source_of_truth"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["paged_attention_kv_cache_scale_up"]["decision"], "select_next")
        self.assertEqual(options["full_ita_mha_or_mha_shape_expansion"]["decision"], "defer")
        self.assertEqual(options["prefill_decode_split_followup"]["decision"], "defer")
        self.assertEqual(options["resident_or_persistent_resident_optimization_followup"]["decision"], "defer")
        self.assertEqual(options["quantized_kv_cache_boundary"]["decision"], "defer")
        self.assertIn("avoid importing unreviewed candidate overlays", options["paged_attention_kv_cache_scale_up"]["weakness"])
        self.assertIn("not a new measurement result", gate["non_claims"])
        self.assertIn("not a new workload import", gate["non_claims"])
        self.assertIn("not raw full-state equality", gate["non_claims"])
        self.assertIn("not quantized model accuracy", gate["non_claims"])

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )

        for token in (
            "next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
            "paged_attention_kv_cache_scale_up_measurement_gate.json",
            "define_paged_attention_kv_cache_scale_up_measurement_gate",
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
            "paged_attention_kv_cache_scale_up",
            "paged-attention/KV-cache scale-up",
            "avoid importing unreviewed candidate overlays",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_scale_up_measurement_gate_is_defined(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_SCALE_UP_MEASUREMENT_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_scale_up_measurement_gate")
        self.assertEqual(gate["status"], "all_measurement_commands_passed_coverage_output_equivalence")
        self.assertEqual(
            gate["source_selection_gate"],
            "config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
        )
        self.assertEqual(gate["selected_workstream"], "paged_attention_kv_cache_scale_up")
        self.assertEqual(gate["current_priority"], "review_paged_attention_kv_cache_scale_up_measurement")
        self.assertEqual(gate["next_task"], "review_paged_attention_kv_cache_scale_up_measurement")

        tracked_inputs = gate["tracked_inputs"]
        for key in (
            "paged_kv_cache_large_template",
            "paged_attention_kv_score_template",
            "paged_kv_cache_large_overlay",
            "paged_attention_kv_score_overlay",
            "paged_kv_cache_large_coverage_manifest",
            "paged_attention_kv_score_coverage_manifest",
        ):
            self.assertTrue((REPO_ROOT / tracked_inputs[key]).exists(), key)
            self.assertNotEqual(_git_ls_files(REPO_ROOT / tracked_inputs[key]), "", key)

        self.assertEqual(
            [entry["shape"] for entry in gate["measurement_set"]],
            ["256x1", "1x64", "64x1", "1x64"],
        )
        self.assertIn(
            "python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_kv_cache_large.json --shape 256x1 --dry-run",
            gate["dry_run_commands"],
        )
        self.assertIn(
            "python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run",
            gate["dry_run_commands"],
        )
        self.assertIn(
            "reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json",
            gate["expected_reports"],
        )
        dry_run_result = gate["dry_run_result"]
        self.assertEqual(dry_run_result["status"], "passed")
        self.assertEqual(dry_run_result["command_count"], 4)
        self.assertTrue(dry_run_result["all_commands_exited_zero"])
        self.assertFalse(dry_run_result["created_measurement_reports"])
        self.assertFalse(dry_run_result["created_artifacts"])
        self.assertTrue(dry_run_result["no_local_absolute_paths_in_stdout"])
        self.assertTrue(dry_run_result["tracked_surface_only"])
        self.assertEqual(
            [entry["exit_code"] for entry in dry_run_result["checked_commands"]],
            [0, 0, 0, 0],
        )
        self.assertIn(
            "overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv",
            dry_run_result["observed_expanded_paths"],
        )
        self.assertIn(
            "records/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json",
            dry_run_result["observed_expanded_paths"],
        )
        readiness = gate["measurement_readiness"]
        self.assertTrue(readiness["tracked_templates_confirmed"])
        self.assertTrue(readiness["tracked_overlays_confirmed"])
        self.assertTrue(readiness["tracked_coverage_manifests_confirmed"])
        self.assertFalse(readiness["untracked_candidate_overlays_used"])
        self.assertTrue(readiness["coverage_output_equivalence_required_for_measurement"])
        self.assertTrue(readiness["expected_reports_are_planned_until_non_dry_measurement"])

        measured = gate["measured_result"]
        self.assertEqual(measured["status"], "passed")
        self.assertEqual(measured["command_count"], 4)
        self.assertTrue(measured["all_commands_exited_zero"])
        self.assertTrue(measured["all_expected_reports_present"])
        self.assertTrue(measured["all_coverage_output_passed"])
        self.assertEqual(measured["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(measured["acceptance_policy"], "coverage_output_equivalence")
        self.assertFalse(measured["raw_full_state_equality_required"])
        self.assertFalse(measured["raw_full_state_all_matched"])
        self.assertFalse(measured["reports_and_artifacts_are_source_of_truth"])
        self.assertFalse(measured["speedup_claim_allowed_by_compare_reports_alone"])
        self.assertEqual(
            [entry["name"] for entry in measured["measured_shapes"]],
            [
                "paged_kv_cache_large_state_parallel_scale",
                "paged_kv_cache_large_single_state_repeated",
                "paged_attention_kv_score_state_parallel",
                "paged_attention_kv_score_single_state_repeated",
            ],
        )
        self.assertEqual(
            [entry["shape"] for entry in measured["measured_shapes"]],
            ["256x1", "1x64", "64x1", "1x64"],
        )
        self.assertEqual(
            [entry["coverage_output_mismatch_count"] for entry in measured["measured_shapes"]],
            [0, 0, 0, 0],
        )
        for entry in measured["measured_shapes"]:
            self.assertTrue(entry["coverage_output_equivalence_passed"])
            self.assertTrue(entry["coverage_output_compare_report"].startswith("reports/"))
            self.assertFalse(Path(entry["coverage_output_compare_report"]).is_absolute())
            report_path = REPO_ROOT / entry["coverage_output_compare_report"]
            self.assertTrue(report_path.exists(), entry["coverage_output_compare_report"])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["selected_acceptance_policy"]["name"], "coverage_output_equivalence")
            self.assertTrue(report["selected_acceptance_policy"]["passed"])
            self.assertTrue(report["coverage_output_policy"]["passed"])
            self.assertEqual(report["coverage_output_policy"]["mismatch_count"], 0)

        policy = gate["acceptance_policy"]
        self.assertFalse(policy["measurement_boundary_only"])
        self.assertTrue(policy["measurement_executed_after_passing_dry_run"])
        self.assertTrue(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required_for_measurement"])
        self.assertEqual(policy["max_mismatch_count_required"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertFalse(policy["speedup_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["contract_tests_required"])

        self.assertIn("not production paged attention", gate["non_claims"])
        self.assertIn("not production KV-cache memory hierarchy", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_scale_up_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_scale_up_measurement_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        )

        for token in (
            "paged_attention_kv_cache_scale_up_measurement_gate.json",
            "paged_attention_kv_cache_scale_up_measurement_review_gate.json",
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
            "all four paged-attention/KV-cache scale-up measurement commands exited with code `0`",
            "reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json",
            "reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json",
            "Top-level raw/full-state `match` is not the acceptance target",
            "config/slice_launch_templates/pulp_paged_kv_cache_large.json",
            "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
            "Do not mix in runtime, MobileViT, Ibex, untracked candidate overlays",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_scale_up_measurement_review_selects_timing_summary(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_SCALE_UP_MEASUREMENT_REVIEW_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_scale_up_measurement_review_gate")
        self.assertEqual(gate["status"], "reviewed_select_timing_summary_gate_next")
        self.assertEqual(
            gate["source_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
        )
        self.assertEqual(gate["reviewed_workstream"], "paged_attention_kv_cache_scale_up")

        reviewed = gate["reviewed_result"]
        self.assertEqual(reviewed["planned_command_count"], 4)
        self.assertTrue(reviewed["all_planned_commands_exited_zero"])
        self.assertTrue(reviewed["all_compare_reports_passed_coverage_output_equivalence"])
        self.assertEqual(reviewed["max_coverage_output_mismatch_count"], 0)
        self.assertIn("selected_acceptance_policy.passed", reviewed["coverage_success_fields"])
        self.assertIn("coverage_output_policy.mismatch_count", reviewed["coverage_success_fields"])
        self.assertFalse(reviewed["raw_full_state_equality_required"])
        self.assertFalse(reviewed["raw_full_state_all_matched"])
        self.assertFalse(reviewed["reports_and_artifacts_are_source_of_truth"])

        self.assertEqual(
            [entry["coverage_output_mismatch_count"] for entry in gate["reviewed_reports"]],
            [0, 0, 0, 0],
        )
        for entry in gate["reviewed_reports"]:
            self.assertTrue(entry["compare_report"].startswith("reports/"))
            self.assertFalse(Path(entry["compare_report"]).is_absolute())
            self.assertFalse(entry["raw_full_state_match"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["paged_attention_kv_cache_timing_summary"]["decision"], "select_next")
        self.assertEqual(options["public_results_packaging_refresh"]["decision"], "defer")
        self.assertEqual(options["resident_execution_optimization"]["decision"], "defer")
        self.assertEqual(options["new_paged_attention_or_quantized_kv_workload"]["decision"], "defer")
        self.assertIn("compare reports alone do not contain timing fields", options["paged_attention_kv_cache_timing_summary"]["reason"])

        selected = gate["selected_next_workstream"]
        self.assertEqual(selected["name"], "paged_attention_kv_cache_timing_summary")
        self.assertEqual(selected["required_next_gate"], "paged_attention_kv_cache_timing_summary_gate")
        self.assertEqual(selected["next_task"], "define_paged_attention_kv_cache_timing_summary_gate")
        self.assertFalse(selected["new_measurement_allowed_by_review_gate"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["speedup_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["timing_summary_gate_selected"])
        self.assertTrue(policy["contract_tests_required"])
        self.assertEqual(gate["next_task"], "define_paged_attention_kv_cache_timing_summary_gate")

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_scale_up_measurement_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json",
        )
        self.assertIn("not a new measurement result", gate["non_claims"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        for token in (
            "paged_attention_kv_cache_scale_up_measurement_review_gate.json",
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
            "timing summary gate",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_timing_summary_gate_is_defined(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_TIMING_SUMMARY_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_timing_summary_gate")
        self.assertEqual(gate["status"], "defined_single_run_timing_summary_for_review")
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json",
        )
        self.assertEqual(
            gate["source_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
        )
        self.assertEqual(gate["current_priority"], "review_paged_attention_kv_cache_timing_summary")

        scope = gate["timing_scope"]
        self.assertEqual(scope["repeat_count"], 1)
        self.assertTrue(scope["timing_evidence_is_generated"])
        self.assertFalse(scope["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(scope["correctness_policy"], "coverage_output_equivalence")
        self.assertTrue(scope["all_coverage_output_passed"])
        self.assertEqual(scope["max_coverage_output_mismatch_count"], 0)

        self.assertEqual(
            [entry["shape"] for entry in gate["timing_reports"]],
            ["256x1", "1x64", "64x1", "1x64"],
        )
        self.assertEqual(
            [entry["coverage_output_mismatch_count"] for entry in gate["timing_reports"]],
            [0, 0, 0, 0],
        )
        expected_wall_ratios = [
            473.32385466034754,
            1.5377136864184584,
            82.78691476590637,
            1.9177279202279203,
        ]
        self.assertEqual(
            [entry["cpu_to_hybrid_wall_ratio"] for entry in gate["timing_reports"]],
            expected_wall_ratios,
        )
        for entry in gate["timing_reports"]:
            self.assertTrue(entry["cpu_report"].startswith("reports/"))
            self.assertTrue(entry["hybrid_report"].startswith("reports/"))
            self.assertTrue(entry["compare_report"].startswith("reports/"))
            self.assertFalse(Path(entry["cpu_report"]).is_absolute())
            self.assertFalse(Path(entry["hybrid_report"]).is_absolute())
            self.assertFalse(Path(entry["compare_report"]).is_absolute())

        summary = gate["summary"]
        self.assertEqual(
            summary["state_parallel_shapes"],
            ["pulp_paged_kv_cache_large 256x1", "pulp_paged_attention_kv_score 64x1"],
        )
        self.assertEqual(
            summary["single_state_repeated_shapes"],
            ["pulp_paged_kv_cache_large 1x64", "pulp_paged_attention_kv_score 1x64"],
        )
        self.assertEqual(summary["state_parallel_wall_ratio_range"], [82.78691476590637, 473.32385466034754])
        self.assertEqual(summary["single_state_repeated_wall_ratio_range"], [1.5377136864184584, 1.9177279202279203])
        self.assertIn("single-run evidence", summary["interpretation"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["summary_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertTrue(policy["single_run_timing_only"])
        self.assertFalse(policy["repeat_median_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["contract_tests_required"])
        self.assertEqual(gate["next_task"], "review_paged_attention_kv_cache_timing_summary")

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        )
        self.assertIn("not repeat-median timing", gate["non_claims"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])

        for token in (
            "paged_attention_kv_cache_timing_summary_gate.json",
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
            "Paged-attention/KV-cache scale-up single-run timing",
            "473.32385466034754x",
            "82.78691476590637x",
            "not repeat-median timing",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_timing_summary_review_selects_public_refresh(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_TIMING_SUMMARY_REVIEW_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_timing_summary_review_gate")
        self.assertEqual(gate["status"], "reviewed_select_public_results_packaging_refresh_next")
        self.assertEqual(
            gate["source_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(gate["reviewed_workstream"], "paged_attention_kv_cache_timing_summary")

        reviewed = gate["reviewed_result"]
        self.assertEqual(reviewed["timing_report_count"], 4)
        self.assertEqual(reviewed["repeat_count"], 1)
        self.assertTrue(reviewed["all_coverage_output_passed"])
        self.assertEqual(reviewed["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(reviewed["state_parallel_wall_ratio_range"], [82.78691476590637, 473.32385466034754])
        self.assertEqual(reviewed["single_state_repeated_wall_ratio_range"], [1.5377136864184584, 1.9177279202279203])
        self.assertIn("single-run observations", reviewed["weakness"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(
            options["public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary"]["decision"],
            "select_next",
        )
        self.assertEqual(options["repeat_median_timing"]["decision"], "defer")
        self.assertEqual(options["resident_execution_optimization"]["decision"], "defer")
        self.assertEqual(options["new_paged_attention_or_quantized_kv_workload"]["decision"], "defer")

        selected = gate["selected_next_workstream"]
        self.assertEqual(selected["name"], "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary")
        self.assertEqual(
            selected["required_next_gate"],
            "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
        )
        self.assertEqual(
            selected["next_task"],
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
        )
        self.assertFalse(selected["new_measurement_allowed_by_review_gate"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertTrue(policy["single_run_timing_only"])
        self.assertFalse(policy["repeat_median_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["public_results_packaging_refresh_selected"])
        self.assertTrue(policy["contract_tests_required"])
        self.assertEqual(
            gate["next_task"],
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
        )

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_timing_summary_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        )
        self.assertIn("not repeat-median timing", gate["non_claims"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])

        for token in (
            "paged_attention_kv_cache_timing_summary_review_gate.json",
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
            "publication-only packaging",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        ):
            self.assertIn(token, combined)

    def test_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_is_defined(self) -> None:
        gate = json.loads(PUBLIC_RESULTS_PAGED_ATTENTION_KV_TIMING_REFRESH_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate")
        self.assertEqual(
            gate["status"],
            "defined_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary",
        )
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json",
        )
        self.assertEqual(
            gate["source_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            gate["source_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json",
        )
        self.assertEqual(gate["selected_workstream"], "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary")
        self.assertEqual(gate["results_doc"], "docs/results.md")

        evidence = gate["paged_attention_kv_cache_timing_evidence"]
        self.assertEqual(evidence["correctness_policy"], "coverage_output_equivalence")
        self.assertTrue(evidence["all_coverage_output_passed"])
        self.assertEqual(evidence["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(evidence["repeat_count"], 1)
        self.assertTrue(evidence["single_run_timing_only"])
        self.assertEqual(evidence["state_parallel_wall_ratio_range"], [82.78691476590637, 473.32385466034754])
        self.assertEqual(evidence["single_state_repeated_wall_ratio_range"], [1.5377136864184584, 1.9177279202279203])
        self.assertEqual(
            [entry["shape"] for entry in evidence["timing_reports"]],
            ["256x1", "1x64", "64x1", "1x64"],
        )
        self.assertEqual(
            [entry["cpu_to_hybrid_wall_ratio"] for entry in evidence["timing_reports"]],
            [473.32385466034754, 1.5377136864184584, 82.78691476590637, 1.9177279202279203],
        )
        for entry in evidence["timing_reports"]:
            self.assertTrue(entry["compare_report"].startswith("reports/"))
            self.assertFalse(Path(entry["compare_report"]).is_absolute())

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["documentation_refresh_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertTrue(policy["single_run_timing_only"])
        self.assertFalse(policy["repeat_median_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["broad_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["contract_tests_required"])
        self.assertEqual(gate["next_task"], "public_benchmark_pack_externalization_ready")

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertIn("not repeat-median timing", gate["non_claims"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        for token in (
            "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json",
            "define_paged_attention_kv_cache_repeat_median_timing_gate",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
            "473.32385466034754x",
            "82.78691476590637x",
            "not repeat-median timing",
        ):
            self.assertIn(token, combined)

    def test_public_pack_completion_after_paged_attention_kv_cache_timing_refresh_is_defined(self) -> None:
        gate = json.loads(PUBLIC_PACK_COMPLETION_AFTER_PAGED_ATTENTION_KV_TIMING_REFRESH_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            gate["gate"],
            "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate",
        )
        self.assertEqual(
            gate["status"],
            "complete_public_benchmark_pack_externalization_after_paged_attention_kv_cache_timing_summary",
        )
        self.assertEqual(gate["completed_priority"], "public_benchmark_pack_externalization_ready")
        self.assertEqual(
            gate["source_refresh_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            gate["source_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertTrue(gate["decision"]["externalization_boundary_complete"])
        self.assertTrue(gate["release_check_evidence"]["archive_dry_run_includes_paged_attention_kv_cache_timing_refresh"])
        self.assertTrue(gate["release_check_evidence"]["single_run_timing_only"])
        self.assertEqual(
            gate["release_check_evidence"]["latest_generated_evidence"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertTrue(gate["acceptance_policy"]["completion_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_workload_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(
            gate["next_task"],
            "select_next_measurement_after_paged_attention_kv_cache_timing_summary_public_pack_refresh",
        )
        self.assertIn("paged_attention_kv_cache_repeat_median_timing", gate["candidate_next_measurement_options"])
        self.assertIn("not repeat-median timing", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json",
        )

        for token in (
            "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json",
            "select_next_measurement_after_paged_attention_kv_cache_timing_summary_public_pack_refresh",
            "define_paged_attention_kv_cache_repeat_median_timing_gate",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
        ):
            self.assertIn(token, combined)

    def test_next_measurement_after_paged_attention_kv_cache_timing_refresh_selects_repeat_median(self) -> None:
        gate = json.loads(NEXT_MEASUREMENT_AFTER_PAGED_ATTENTION_KV_TIMING_REFRESH_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate")
        self.assertEqual(gate["status"], "selected_paged_attention_kv_cache_repeat_median_timing_next")
        self.assertEqual(
            gate["source_completion_gate"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            gate["source_refresh_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(
            gate["source_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(gate["source_results_doc"], "docs/results.md")

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["paged_attention_kv_cache_repeat_median_timing"]["decision"], "select_next")
        self.assertEqual(options["resident_execution_optimization"]["decision"], "defer")
        self.assertEqual(options["paged_attention_kv_cache_scale_up_continuation"]["decision"], "defer")
        self.assertEqual(options["quantized_kv_cache_boundary"]["decision"], "defer")
        self.assertEqual(options["full_ita_mha_additional_shapes"]["decision"], "defer")
        self.assertIn("timing stability", options["paged_attention_kv_cache_repeat_median_timing"]["reason"])

        selected = gate["selected_next_goal"]
        self.assertEqual(selected["name"], "paged_attention_kv_cache_repeat_median_timing")
        self.assertEqual(selected["first_gate"], "define_paged_attention_kv_cache_repeat_median_timing_gate")
        self.assertTrue(any("reuse the four reviewed shapes" in item for item in selected["scope"]))

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["selection_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required_for_later_measurement"])
        self.assertTrue(policy["repeat_median_required_for_next_measurement_gate"])
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["contract_tests_required_for_next_public_workflow"])
        self.assertEqual(gate["next_task"], "define_paged_attention_kv_cache_repeat_median_timing_gate")

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate"],
            "config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json",
        )
        self.assertIn("not repeat-median timing yet", gate["non_claims"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        for token in (
            "next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json",
            "define_paged_attention_kv_cache_repeat_median_timing_gate",
            "paged_attention_kv_cache_repeat_median_timing",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
            "next_task: select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_repeat_median_timing_gate_is_defined(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_TIMING_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_repeat_median_timing_gate")
        self.assertEqual(gate["status"], "defined_repeat_median_timing_boundary_pending_workflow")
        self.assertEqual(
            gate["source_selection_gate"],
            "config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json",
        )
        self.assertEqual(
            gate["source_single_run_timing_summary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json",
        )
        self.assertEqual(gate["selected_workstream"], "paged_attention_kv_cache_repeat_median_timing")
        self.assertEqual(gate["current_priority"], "add_paged_attention_kv_cache_repeat_median_workflow")

        boundary = gate["measurement_boundary"]
        self.assertEqual(boundary["repeat_count"], 3)
        self.assertEqual(boundary["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(boundary["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(boundary["raw_full_state_equality_required"])
        self.assertFalse(boundary["runtime_or_abi_change_allowed"])
        self.assertFalse(boundary["new_workload_allowed"])
        self.assertFalse(boundary["untracked_candidate_overlay_allowed"])
        self.assertFalse(boundary["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(
            [entry["shape"] for entry in boundary["required_shapes"]],
            ["256x1", "1x64", "64x1", "1x64"],
        )
        self.assertEqual(
            [entry["target"] for entry in boundary["required_shapes"]],
            [
                "pulp_paged_kv_cache_large",
                "pulp_paged_kv_cache_large",
                "pulp_paged_attention_kv_score",
                "pulp_paged_attention_kv_score",
            ],
        )
        for entry in boundary["required_shapes"]:
            self.assertTrue(entry["template"].startswith("config/slice_launch_templates/"))
            self.assertTrue(entry["single_run_compare_report"].startswith("reports/"))
            self.assertFalse(Path(entry["single_run_compare_report"]).is_absolute())
        for metric in (
            "cpu_elapsed_ms",
            "hybrid_wall_ms",
            "hybrid_gpu_kernel_total_ms",
            "cpu_to_hybrid_wall_ratio",
            "hybrid_wall_ms_per_state_step",
        ):
            self.assertIn(metric, boundary["required_median_fields"])

        gap = gate["workflow_gap"]
        self.assertFalse(gap["existing_repeat_median_cli_covers_required_four_shape_set"])
        self.assertIn("does not cover", gap["reason"])
        self.assertIn("src/tools/results_reproduction.py", gap["required_next_workflow"])
        self.assertEqual(
            gate["planned_public_interface"]["proposed_dry_run_command"],
            "python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3 --dry-run",
        )
        self.assertEqual(
            gate["planned_public_interface"]["planned_summary_report"],
            "reports/paged_attention_kv_cache_repeat_median_summary.json",
        )

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required_for_later_measurement"])
        self.assertEqual(policy["repeat_count_required_for_later_measurement"], 3)
        self.assertEqual(policy["required_shape_count"], 4)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertTrue(policy["public_workflow_change_requires_contract_test"])
        self.assertTrue(policy["docs_mention_required_for_public_workflow"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertEqual(gate["next_task"], "add_paged_attention_kv_cache_repeat_median_workflow")

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_repeat_median_timing_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json",
        )
        self.assertIn("not repeat-median timing yet", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        for token in (
            "paged_attention_kv_cache_repeat_median_timing_gate.json",
            "add_paged_attention_kv_cache_repeat_median_workflow",
            "--paged-kv-repeat-median 3 --dry-run",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_repeat_median_workflow_gate_is_defined(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_WORKFLOW_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_repeat_median_workflow_gate")
        self.assertEqual(gate["status"], "added_paged_attention_kv_cache_repeat_median_workflow")
        self.assertEqual(
            gate["source_boundary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json",
        )
        self.assertEqual(gate["public_cli"], "src/tools/run_results_reproduction.py")
        self.assertEqual(gate["shared_module"], "src/tools/results_reproduction.py")
        self.assertEqual(gate["current_priority"], "run_paged_attention_kv_cache_repeat_median_timing_gate")

        interface = gate["public_interface"]
        self.assertEqual(
            interface["dry_run_command"],
            "python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3 --dry-run",
        )
        self.assertEqual(
            interface["command"],
            "python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3",
        )
        self.assertEqual(interface["repeat_count"], 3)
        self.assertEqual(interface["summary_report"], "reports/paged_attention_kv_cache_repeat_median_summary.json")

        scope = gate["workflow_scope"]
        self.assertEqual(scope["shape_count"], 4)
        self.assertEqual(scope["correctness_policy"], "coverage_output_equivalence")
        self.assertFalse(scope["raw_full_state_equality_required"])
        self.assertFalse(scope["reports_and_artifacts_are_source_of_truth"])
        workloads = {entry["name"]: entry for entry in scope["required_workloads"]}
        self.assertEqual(
            set(workloads),
            {
                "pulp_paged_kv_cache_large_256x1",
                "pulp_paged_kv_cache_large_1x64",
                "pulp_paged_attention_kv_score_64x1",
                "pulp_paged_attention_kv_score_1x64",
            },
        )
        self.assertEqual(workloads["pulp_paged_kv_cache_large_256x1"]["shape"], "256x1")
        self.assertEqual(workloads["pulp_paged_kv_cache_large_1x64"]["median_report"], "reports/paged_kv_repeat_pulp_paged_kv_cache_large_1x64_median.json")
        self.assertEqual(workloads["pulp_paged_attention_kv_score_64x1"]["source_gate"], "config/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json")
        self.assertEqual(workloads["pulp_paged_attention_kv_score_1x64"]["target"], "pulp_paged_attention_kv_score")
        for entry in workloads.values():
            self.assertTrue(entry["source_gate"].startswith("config/scaling_gates/"))
            self.assertTrue(entry["median_report"].startswith("reports/"))
            self.assertFalse(Path(entry["median_report"]).is_absolute())

        dry_run = gate["dry_run_result"]
        self.assertEqual(dry_run["status"], "passed")
        self.assertTrue(dry_run["all_four_shapes_present"])
        self.assertEqual(dry_run["sample_count_per_shape"], 3)
        self.assertFalse(dry_run["local_absolute_paths_in_stdout"])
        self.assertFalse(dry_run["writes_generated_evidence"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["workflow_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required_for_later_measurement"])
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertTrue(policy["public_cli_has_contract_test"])
        self.assertEqual(gate["next_task"], "run_paged_attention_kv_cache_repeat_median_timing_gate")

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_repeat_median_workflow_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json",
        )
        self.assertIn("not repeat-median timing yet", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        for token in (
            "paged_attention_kv_cache_repeat_median_workflow_gate.json",
            "--paged-kv-repeat-median 3 --dry-run",
            "reports/paged_attention_kv_cache_repeat_median_summary.json",
            "run_paged_attention_kv_cache_repeat_median_timing_gate",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_repeat_median_measurement_gate_is_defined(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_MEASUREMENT_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_repeat_median_measurement_gate")
        self.assertEqual(gate["status"], "measured_paged_attention_kv_cache_repeat_median")
        self.assertEqual(
            gate["source_boundary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json",
        )
        self.assertEqual(
            gate["source_workflow_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json",
        )
        self.assertEqual(gate["repeat_count"], 3)
        self.assertEqual(gate["current_priority"], "review_paged_attention_kv_cache_repeat_median_timing")
        self.assertEqual(gate["summary_report"], "reports/paged_attention_kv_cache_repeat_median_summary.json")

        scope = gate["measurement_scope"]
        self.assertEqual(scope["shape_count"], 4)
        self.assertEqual(scope["correctness_policy"], "coverage_output_equivalence")
        self.assertFalse(scope["runtime_or_abi_change_allowed"])
        self.assertFalse(scope["new_workload_allowed"])
        self.assertFalse(scope["reports_and_artifacts_are_source_of_truth"])

        result = gate["measured_result"]
        self.assertTrue(result["all_coverage_output_passed"])
        self.assertEqual(result["max_coverage_output_mismatch_count"], 0)
        workloads = {entry["name"]: entry for entry in result["workloads"]}
        self.assertEqual(
            set(workloads),
            {
                "pulp_paged_kv_cache_large_256x1",
                "pulp_paged_kv_cache_large_1x64",
                "pulp_paged_attention_kv_score_64x1",
                "pulp_paged_attention_kv_score_1x64",
            },
        )
        self.assertEqual(workloads["pulp_paged_kv_cache_large_256x1"]["cpu_elapsed_ms_median"], 613.931)
        self.assertEqual(workloads["pulp_paged_kv_cache_large_256x1"]["hybrid_wall_ms_median"], 1.259)
        self.assertEqual(workloads["pulp_paged_kv_cache_large_256x1"]["coverage_output_mismatch_count"], 0)
        self.assertEqual(workloads["pulp_paged_kv_cache_large_1x64"]["cpu_to_hybrid_wall_ratio_median"], 1.9749698299506309)
        self.assertEqual(workloads["pulp_paged_attention_kv_score_64x1"]["cpu_to_hybrid_wall_ratio_median"], 136.6441947565543)
        self.assertEqual(workloads["pulp_paged_attention_kv_score_1x64"]["hybrid_gpu_kernel_total_ms_median"], 1.5616)
        self.assertEqual(
            result["summary"]["state_parallel_wall_ratio_range_median"],
            [136.6441947565543, 487.6338363780779],
        )
        self.assertEqual(
            result["summary"]["single_state_repeated_wall_ratio_range_median"],
            [1.9749698299506309, 1.978094940662086],
        )

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertTrue(policy["all_samples_must_pass_coverage_output_equivalence"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertTrue(policy["review_gate_required"])
        self.assertEqual(gate["next_task"], "review_paged_attention_kv_cache_repeat_median_timing")

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_repeat_median_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_repeat_median_summary"],
            "reports/paged_attention_kv_cache_repeat_median_summary.json",
        )

        for token in (
            "paged_attention_kv_cache_repeat_median_measurement_gate.json",
            "reports/paged_attention_kv_cache_repeat_median_summary.json",
            "613.931",
            "487.6338363780779",
            "review_paged_attention_kv_cache_repeat_median_timing",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
        ):
            self.assertIn(token, combined)

    def test_paged_attention_kv_cache_repeat_median_review_selects_public_pack_refresh(self) -> None:
        gate = json.loads(PAGED_ATTENTION_KV_CACHE_REPEAT_MEDIAN_REVIEW_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "paged_attention_kv_cache_repeat_median_review_gate")
        self.assertEqual(
            gate["status"],
            "reviewed_paged_attention_kv_cache_repeat_median_select_public_pack_refresh",
        )
        self.assertEqual(
            gate["source_boundary_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json",
        )
        self.assertEqual(
            gate["source_workflow_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json",
        )
        self.assertEqual(
            gate["source_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json",
        )
        self.assertEqual(gate["reviewed_summary_report"], "reports/paged_attention_kv_cache_repeat_median_summary.json")
        self.assertEqual(
            gate["current_priority"],
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median",
        )

        result = gate["review_result"]
        self.assertEqual(result["decision"], "accept_measurement_for_scoped_result_pack")
        self.assertTrue(result["all_coverage_output_passed"])
        self.assertEqual(result["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(result["repeat_count"], 3)
        self.assertEqual(
            result["state_parallel_wall_ratio_range_median"],
            [136.6441947565543, 487.6338363780779],
        )
        self.assertEqual(
            result["single_state_repeated_wall_ratio_range_median"],
            [1.9749698299506309, 1.978094940662086],
        )
        self.assertIn("state-parallel", result["interpretation"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(
            options["public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median"]["decision"],
            "select_next",
        )
        self.assertEqual(options["resident_execution_optimization"]["decision"], "defer")
        self.assertEqual(options["quantized_kv_cache_boundary"]["decision"], "defer")
        self.assertTrue(any("repeat-count 3 is a stability check" in point for point in gate["weak_points"]))
        self.assertIn(
            "scoped RTL harnesses are not production paged attention or full LLM serving",
            gate["weak_points"],
        )

        selected = gate["selected_next_workstream"]
        self.assertEqual(
            selected["name"],
            "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median",
        )
        self.assertEqual(
            selected["next_gate"],
            "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate",
        )
        self.assertEqual(
            gate["next_task"],
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median",
        )

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["review_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["public_pack_refresh_required_before_next_measurement"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["paged_attention_kv_cache_repeat_median_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json",
        )

        for token in (
            "paged_attention_kv_cache_repeat_median_review_gate.json",
            "define_public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median",
            "repeat-count `3` is not paper-grade statistics",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json",
        ):
            self.assertIn(token, combined)

    def test_public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_is_defined(self) -> None:
        gate = json.loads(PUBLIC_RESULTS_PAGED_ATTENTION_KV_REPEAT_MEDIAN_REFRESH_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            gate["gate"],
            "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate",
        )
        self.assertEqual(
            gate["status"],
            "defined_public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median",
        )
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json",
        )
        self.assertEqual(
            gate["source_measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json",
        )
        self.assertEqual(
            gate["selected_workstream"],
            "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median",
        )
        self.assertEqual(gate["results_doc"], "docs/results.md")

        evidence = gate["paged_attention_kv_cache_repeat_median_evidence"]
        self.assertEqual(evidence["correctness_policy"], "coverage_output_equivalence")
        self.assertTrue(evidence["all_coverage_output_passed"])
        self.assertEqual(evidence["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(evidence["repeat_count"], 3)
        self.assertEqual(evidence["summary_report"], "reports/paged_attention_kv_cache_repeat_median_summary.json")
        self.assertEqual(
            evidence["measurement_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json",
        )
        self.assertEqual(
            evidence["state_parallel_wall_ratio_range_median"],
            [136.6441947565543, 487.6338363780779],
        )
        self.assertEqual(
            evidence["single_state_repeated_wall_ratio_range_median"],
            [1.9749698299506309, 1.978094940662086],
        )
        self.assertEqual(
            [entry["shape"] for entry in evidence["timing_reports"]],
            ["256x1", "1x64", "64x1", "1x64"],
        )
        self.assertEqual(
            [entry["cpu_to_hybrid_wall_ratio_median"] for entry in evidence["timing_reports"]],
            [487.6338363780779, 1.9749698299506309, 136.6441947565543, 1.978094940662086],
        )
        for entry in evidence["timing_reports"]:
            self.assertTrue(entry["median_report"].startswith("reports/"))
            self.assertFalse(Path(entry["median_report"]).is_absolute())

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["documentation_refresh_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertFalse(policy["untracked_candidate_overlay_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(policy["repeat_count"], 3)
        self.assertFalse(policy["broad_speedup_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertTrue(policy["contract_tests_required"])
        self.assertEqual(gate["next_task"], "public_benchmark_pack_externalization_ready")
        self.assertIn("not a new measurement result", gate["non_claims"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        self.assertEqual(selection["current_priority"], "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh")
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json",
        )

        for token in (
            "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json",
            "reports/paged_attention_kv_cache_repeat_median_summary.json",
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
            "not production LLM serving throughput",
        ):
            self.assertIn(token, combined)

    def test_public_pack_completion_after_paged_attention_kv_cache_repeat_median_refresh_is_defined(self) -> None:
        gate = json.loads(
            PUBLIC_PACK_COMPLETION_AFTER_PAGED_ATTENTION_KV_REPEAT_MEDIAN_REFRESH_GATE.read_text(encoding="utf-8")
        )
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            gate["gate"],
            "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate",
        )
        self.assertEqual(
            gate["status"],
            "complete_public_benchmark_pack_externalization_after_paged_attention_kv_cache_repeat_median",
        )
        self.assertEqual(gate["completed_priority"], "public_benchmark_pack_externalization_ready")
        self.assertEqual(
            gate["source_refresh_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json",
        )
        self.assertTrue(gate["decision"]["externalization_boundary_complete"])
        evidence = gate["release_check_evidence"]
        self.assertTrue(evidence["archive_dry_run_includes_paged_attention_kv_cache_repeat_median_refresh"])
        self.assertEqual(evidence["repeat_count"], 3)
        self.assertTrue(evidence["all_coverage_output_passed"])
        self.assertEqual(evidence["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(evidence["latest_generated_evidence"], "reports/paged_attention_kv_cache_repeat_median_summary.json")

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["completion_only"])
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertEqual(policy["max_coverage_output_mismatch_count"], 0)
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertFalse(policy["reports_and_artifacts_are_source_of_truth"])
        self.assertFalse(policy["production_llm_serving_claim_allowed_by_gate_alone"])
        self.assertEqual(
            gate["next_task"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertIn("config_generation_validation_breadth", gate["candidate_next_measurement_options"])
        self.assertIn("not a new measurement result", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )

        for token in (
            "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
            "reports/paged_attention_kv_cache_repeat_median_summary.json",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
        ):
            self.assertIn(token, combined)

    def test_next_measurement_goal_selection_after_public_pack_readiness_is_defined(self) -> None:
        gate = json.loads(NEXT_MEASUREMENT_GOAL_SELECTION_GATE.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "next_measurement_goal_selection_after_public_pack_readiness_gate")
        self.assertEqual(gate["status"], "selected_persistent_resident_state_abi_repeat_median_next")
        self.assertEqual(
            gate["source_readiness_audit"],
            "config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json",
        )
        self.assertEqual(gate["selected_next_goal"]["name"], "persistent_resident_state_abi_repeat_median")
        self.assertEqual(
            gate["selected_next_goal"]["first_gate"],
            "persistent_resident_state_abi_repeat_median_measurement_gate",
        )
        self.assertEqual(gate["next_task"], "define_persistent_resident_state_abi_repeat_median_measurement_gate")
        self.assertTrue(gate["acceptance_policy"]["selection_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_required_for_later_measurement"])

        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["paged_attention_kv_cache_scale_up"]["decision"], "defer")
        self.assertEqual(options["prefill_decode_additional_benchmark"]["decision"], "defer")
        self.assertEqual(options["resident_execution_optimization"]["decision"], "select_next")
        self.assertEqual(options["publish_only"]["decision"], "defer")
        self.assertIn("timing reproducibility", options["resident_execution_optimization"]["reason"])
        self.assertIn("not production paged attention", gate["non_claims"])
        self.assertIn("not production KV-cache memory hierarchy", gate["non_claims"])
        self.assertIn("not a new workload", gate["non_claims"])
        self.assertIn("not model-level Transformer inference", gate["non_claims"])

        for token in (
            "next_measurement_goal_selection_after_public_pack_readiness_gate.json",
            "persistent_resident_state_abi_repeat_median",
            "persistent_resident_state_abi_repeat_median_measurement_gate",
            "persistent resident state ABI repeat-median measurement",
            "do not change runtime ABI or add a new workload",
        ):
            self.assertIn(token, combined)

    def test_persistent_resident_state_abi_repeat_median_measurement_gate_is_defined(self) -> None:
        gate = json.loads(PERSISTENT_RESIDENT_STATE_ABI_REPEAT_MEDIAN_GATE.read_text(encoding="utf-8"))
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "persistent_resident_state_abi_repeat_median_measurement_gate")
        self.assertEqual(
            gate["status"],
            "measured_repeat_median_for_existing_persistent_resident_abi",
        )
        self.assertEqual(gate["shape"], "16x64")
        self.assertEqual(gate["phases"], 4)
        self.assertEqual(gate["repeat_count"], 3)
        self.assertEqual(
            gate["command"],
            "python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3",
        )
        self.assertEqual(
            gate["dry_run_command"],
            "python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3 --dry-run",
        )
        self.assertEqual(gate["summary_report"], "reports/persistent_resident_state_abi_repeat_median_summary.json")
        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_required"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_workload_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["generated_reports_are_source_of_truth"])
        self.assertIn("hybrid_wall_ms", gate["summary_schema"]["metric_fields"])
        self.assertTrue(gate["measured_result"]["all_coverage_output_passed"])
        self.assertEqual(gate["measured_result"]["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(gate["measured_result"]["hybrid_wall_ms"]["median"], 4.965)
        self.assertEqual(gate["measured_result"]["gpu_kernel_total_ms"]["median"], 4.934624)
        self.assertEqual(
            gate["measured_result"]["hybrid_wall_ms_per_final_state_step"]["median"],
            0.001212158203125,
        )
        self.assertIn("not a runtime or ABI change", gate["non_claims"])
        self.assertIn("not a new workload", gate["non_claims"])
        self.assertEqual(
            gate["next_task"],
            "select_next_measurement_goal_after_persistent_resident_state_abi_repeat_median",
        )

        for token in (
            "persistent_resident_state_abi_repeat_median_measurement_gate.json",
            "--persistent-resident-state-abi-repeat-median 3",
            "reports/persistent_resident_state_abi_repeat_median_summary.json",
            "forbids runtime/ABI changes or new workload claims",
            "Median hybrid wall is `4.965 ms`",
            "public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
        ):
            self.assertIn(token, combined)

    def test_next_goal_after_persistent_resident_repeat_median_selects_public_pack_refresh(self) -> None:
        gate = json.loads(
            NEXT_GOAL_AFTER_PERSISTENT_RESIDENT_REPEAT_MEDIAN_GATE.read_text(encoding="utf-8")
        )
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(gate["gate"], "next_goal_selection_after_persistent_resident_repeat_median_gate")
        self.assertEqual(
            gate["status"],
            "selected_public_pack_refresh_after_persistent_resident_repeat_median",
        )
        self.assertEqual(
            gate["source_measurement_gate"],
            "config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json",
        )
        self.assertEqual(
            gate["selected_next_goal"]["name"],
            "public_pack_refresh_after_persistent_resident_repeat_median",
        )
        self.assertEqual(
            gate["selected_next_goal"]["first_gate"],
            "public_results_packaging_refresh_after_persistent_resident_repeat_median_gate",
        )
        options = {entry["option"]: entry for entry in gate["options_reviewed"]}
        self.assertEqual(options["public_pack_refresh_after_persistent_resident_repeat_median"]["decision"], "select_next")
        self.assertEqual(options["paged_attention_kv_cache_scale_up"]["decision"], "defer")
        self.assertIn("strongest next measurement candidate", options["paged_attention_kv_cache_scale_up"]["reason"])
        self.assertTrue(gate["acceptance_policy"]["selection_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["generated_reports_are_source_of_truth"])
        self.assertIn("not a new measurement result", gate["non_claims"])
        self.assertIn("not production LLM serving throughput", gate["non_claims"])
        self.assertEqual(
            gate["next_task"],
            "define_public_results_packaging_refresh_after_persistent_resident_repeat_median_gate",
        )

        for token in (
            "next_goal_selection_after_persistent_resident_repeat_median_gate.json",
            "public_pack_refresh_after_persistent_resident_repeat_median",
            "public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
            "current selected goal is complete",
        ):
            self.assertIn(token, combined)

    def test_public_results_packaging_refresh_after_persistent_repeat_median_is_defined(self) -> None:
        gate = json.loads(PUBLIC_RESULTS_PERSISTENT_REPEAT_MEDIAN_REFRESH_GATE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        combined_docs = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )

        self.assertEqual(
            gate["status"],
            "defined_public_results_packaging_refresh_after_persistent_resident_repeat_median",
        )
        self.assertEqual(
            gate["source_selection_gate"],
            "config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json",
        )
        self.assertEqual(
            gate["source_measurement_gate"],
            "config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json",
        )
        self.assertEqual(gate["selected_workstream"], "public_pack_refresh_after_persistent_resident_repeat_median")
        self.assertEqual(gate["results_doc"], "docs/results.md")

        evidence = gate["persistent_resident_repeat_median_evidence"]
        self.assertEqual(evidence["correctness_policy"], "coverage_output_equivalence")
        self.assertTrue(evidence["all_samples_passed"])
        self.assertEqual(evidence["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(evidence["shape"], "16x64")
        self.assertEqual(evidence["repeat_count"], 3)
        self.assertEqual(evidence["median_hybrid_wall_ms"], 4.965)
        self.assertEqual(evidence["median_gpu_kernel_total_ms"], 4.934624)
        self.assertEqual(evidence["summary_report"], "reports/persistent_resident_state_abi_repeat_median_summary.json")

        self.assertTrue(gate["acceptance_policy"]["documentation_refresh_only"])
        self.assertFalse(gate["acceptance_policy"]["new_measurement_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["new_workload_allowed_by_this_gate"])
        self.assertFalse(gate["acceptance_policy"]["reports_and_artifacts_are_source_of_truth"])
        self.assertEqual(gate["next_task"], "public_benchmark_pack_externalization_ready")
        self.assertIn("not a new measurement result", gate["non_claims"])
        self.assertIn("not cross-process persistent CUDA state", gate["non_claims"])
        self.assertIn("not paper-grade statistical confidence beyond repeat-count 3 representative medians", gate["non_claims"])
        self.assertIn("reports and artifacts are generated evidence, not source of truth", gate["non_claims"])

        self.assertEqual(
            selection["current_priority"],
            "select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        )
        self.assertEqual(
            selection["current_priority_source_artifact"],
            "config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json",
        )
        self.assertEqual(
            selection["completed_goal_evidence"]["public_results_packaging_refresh_after_persistent_resident_repeat_median_gate"],
            "config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
        )

        for token in (
            "public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json",
            "public_benchmark_pack_externalization_completion_gate.json",
            "next_measurement_selection_after_public_benchmark_pack_externalization_gate.json",
            "paged_attention_kv_cache_scale_up_measurement_gate.json",
            "reports/persistent_resident_state_abi_repeat_median_summary.json",
            "Persistent resident ABI repeat-median",
            "All point at `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`",
            "next_task: select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh",
        ):
            self.assertIn(token, combined_docs)

    def test_published_hybrid_benchmark_wrapper_summaries_are_reviewable(self) -> None:
        published_docs = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                RESULTS.read_text(encoding="utf-8"),
            ]
        )
        for path in HYBRID_BENCHMARK_WRAPPER_SUMMARIES:
            with self.subTest(path=path.name):
                if not path.exists():
                    self.assertIn(relative_path := path.relative_to(REPO_ROOT).as_posix(), published_docs)
                    self.assertTrue(relative_path.startswith("reports/hybrid_benchmark_"))
                    continue
                summary = json.loads(path.read_text(encoding="utf-8"))
                relative_path = path.relative_to(REPO_ROOT).as_posix()

                self.assertIn(relative_path, published_docs)
                self.assertLessEqual(
                    HYBRID_BENCHMARK_REQUIRED_SCHEMA_FIELDS,
                    set(summary),
                )
                self.assertEqual(summary["tool"], "src/tools/run_hybrid_benchmark.py")
                self.assertIn(summary["execution_mode"], {"executed", "existing_evidence"})
                self.assertEqual(summary["command_count"], len(summary["commands"]))
                self.assertEqual(summary["evidence"]["status"], "collected")
                self.assertTrue(summary["evidence"]["coverage_output_passed"])
                if "coverage_output_mismatch_count" in summary["evidence"]:
                    self.assertEqual(summary["evidence"]["coverage_output_mismatch_count"], 0)
                else:
                    self.assertEqual(summary["execution_mode"], "existing_evidence")
                    self.assertEqual(summary["target"], "mobile_vit")
                self.assertIn(
                    "coverage-output equivalence is not raw full-state equality",
                    summary["non_claims"],
                )

                encoded = json.dumps(summary, sort_keys=True)
                for marker in LOCAL_ABSOLUTE_PATH_MARKERS:
                    self.assertNotIn(marker, encoded)

                for report in summary["expected_reports"].values():
                    if not isinstance(report, str):
                        continue
                    self.assertIsInstance(report, str)
                    self.assertTrue(report.startswith("reports/"))
                    self.assertFalse(Path(report).is_absolute())

    def test_one_command_reproduction_flow_records_public_cli(self) -> None:
        gate = json.loads(ONE_COMMAND_REPRODUCTION_GATE.read_text(encoding="utf-8"))
        results = RESULTS.read_text(encoding="utf-8")

        self.assertEqual(gate["status"], "passed_representative_results_have_one_command_reproduction_flow")
        self.assertEqual(gate["public_cli"], "src/tools/run_results_reproduction.py")
        self.assertEqual(gate["shared_module"], "src/tools/results_reproduction.py")
        self.assertEqual(gate["dry_run_command"], "python3 src/tools/run_results_reproduction.py --dry-run")
        self.assertTrue(gate["acceptance_policy"]["public_cli_is_thin"])
        self.assertTrue(gate["acceptance_policy"]["reusable_logic_in_shared_module"])
        workloads = {entry["name"]: entry for entry in gate["representative_workloads"]}
        self.assertEqual(
            set(workloads),
            {
                "full_ita_mha_prefill_like",
                "full_ita_mha_decode_like",
                "full_ita_mha_resident_decode",
                "full_ita_mha_resident_batch_decode",
                "paged_attention_kv_score_state_parallel",
                "mobile_vit_imagenet_128_cpu_kick_hybrid_proxy",
            },
        )
        self.assertEqual(workloads["full_ita_mha_resident_batch_decode"]["shape"], "32x64")
        self.assertEqual(
            workloads["mobile_vit_imagenet_128_cpu_kick_hybrid_proxy"]["shape"],
            "cfg_batch_length=128",
        )
        self.assertEqual(
            gate["mobile_vit_imagenet_128_dry_run_command"],
            "python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run",
        )
        self.assertIn("python3 src/tools/run_results_reproduction.py --dry-run", results)
        self.assertIn("python3 src/tools/run_results_reproduction.py", results)
        self.assertIn("python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128", results)

    def test_repeat_median_results_records_required_workloads(self) -> None:
        gate = json.loads(REPEAT_MEDIAN_RESULTS_GATE.read_text(encoding="utf-8"))
        results = RESULTS.read_text(encoding="utf-8")

        self.assertEqual(gate["status"], "passed_repeat_median_representative_results")
        self.assertEqual(gate["public_cli"], "src/tools/run_results_reproduction.py")
        self.assertEqual(gate["shared_module"], "src/tools/results_reproduction.py")
        self.assertEqual(gate["repeat_count"], 3)
        self.assertEqual(gate["summary_report"], "reports/results_reproduction_median_summary.json")
        self.assertTrue(gate["acceptance_policy"]["source_reports_required"])
        self.assertTrue(gate["acceptance_policy"]["median_reports_required"])
        self.assertTrue(gate["acceptance_policy"]["contract_tests_required"])

        required = {entry["name"]: entry for entry in gate["required_workloads"]}
        self.assertEqual(
            set(required),
            {
                "pulp_ita_mha_64x1",
                "pulp_ita_mha_1x64",
                "pulp_ita_mha_1x64_resident",
                "pulp_ita_mha_32x64_resident",
                "pulp_paged_attention_kv_score_64x1",
            },
        )
        self.assertEqual(required["pulp_ita_mha_32x64_resident"]["shape"], "32x64")
        self.assertTrue(required["pulp_ita_mha_32x64_resident"]["resident_mode"])

        result = gate["result"]
        self.assertTrue(result["all_workloads_passed"])
        self.assertEqual(result["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(result["median_report_count"], 5)
        self.assertEqual(result["source_report_count_per_workload"]["cpu"], 3)
        self.assertEqual(result["source_report_count_per_workload"]["hybrid"], 3)
        self.assertEqual(result["source_report_count_per_workload"]["compare"], 3)
        highlights = result["median_highlights"]
        self.assertEqual(set(highlights), set(required))
        self.assertGreater(highlights["pulp_ita_mha_64x1"]["cpu_elapsed_div_hybrid_wall"], 100.0)
        self.assertGreater(
            highlights["pulp_ita_mha_32x64_resident"]["wall_per_state_step_ratio_vs_1x64_resident"],
            30.0,
        )

        self.assertIn("Repeat-median timing highlights", results)
        self.assertIn("python3 src/tools/run_results_reproduction.py --repeat-median 3", results)
        self.assertIn("reports/results_reproduction_median_summary.json", results)

    def test_resident_execution_optimization_next_gate_uses_median_evidence(self) -> None:
        gate = json.loads(RESIDENT_OPTIMIZATION_NEXT_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "implemented_public_resident_batch_sweep_dry_run_ready")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/repeat_median_results_reproduction_gate.json")
        self.assertEqual(gate["source_summary"], "reports/results_reproduction_median_summary.json")
        self.assertEqual(gate["repeat_count"], 3)
        self.assertFalse(gate["acceptance_policy"]["single_state_resident_speedup_claim_allowed"])
        self.assertFalse(gate["acceptance_policy"]["runtime_abi_change_allowed_by_this_gate"])
        self.assertTrue(gate["acceptance_policy"]["large_speedup_claim_requires_batch_parallel_resident_shape"])

        evidence = gate["median_evidence"]
        for item in evidence.values():
            self.assertTrue(item["coverage_output_passed"])
            self.assertEqual(item["coverage_output_mismatch_count"], 0)
            self.assertTrue(item["report"].startswith("reports/"))
            self.assertGreater(item["hybrid_wall_ms_median"], 0)

        derived = gate["derived_metrics"]
        self.assertEqual(
            derived["resident_1x64_vs_nonresident_1x64"]["classification"],
            "resident_single_state_median_slower",
        )
        self.assertGreater(
            derived["resident_batch_32x64_vs_resident_1x64"]["wall_per_state_step_ratio_1x64_over_32x64"],
            30.0,
        )
        self.assertEqual(
            gate["selected_next_workstream"]["name"],
            "resident_state_reuse_and_batch_decode_optimization_plan",
        )
        self.assertIn(
            "run_resident_batch_sweep_measurement_and_record_gate",
            gate["next_task"],
        )
        self.assertIn(
            "python3 src/tools/run_results_reproduction.py --resident-batch-sweep 1,8,16,32 --resident-batch-sweep-repeat 3",
            gate["implemented_public_commands"],
        )

    def test_resident_batch_sweep_measurement_gate_records_sweep_results(self) -> None:
        gate = json.loads(RESIDENT_BATCH_SWEEP_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "passed_resident_batch_sweep_measurement")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/resident_execution_optimization_next_gate.json")
        self.assertEqual(gate["summary_report"], "reports/resident_batch_sweep_summary.json")
        self.assertEqual(gate["repeat_count"], 3)
        self.assertEqual(gate["batch_states"], [1, 8, 16, 32])
        self.assertTrue(gate["acceptance_policy"]["init_state_generation_required"])
        self.assertTrue(gate["acceptance_policy"]["compare_stdout_capture_required"])
        self.assertTrue(gate["acceptance_policy"]["per_state_step_metrics_required"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_equality_required"])

        workloads = {entry["shape"]: entry for entry in gate["measured_shapes"]}
        self.assertEqual(set(workloads), {"1x64", "8x64", "16x64", "32x64"})
        for shape, workload in workloads.items():
            self.assertTrue(workload["resident_mode"], shape)
            self.assertTrue(workload["coverage_output_passed"], shape)
            self.assertEqual(workload["coverage_output_mismatch_count"], 0)
            self.assertGreater(workload["hybrid_wall_ms_median"], 0)
            self.assertGreater(workload["hybrid_wall_ms_per_state_step_median"], 0)
            self.assertTrue(workload["report"].startswith("reports/"))

        self.assertEqual(gate["result"]["best_total_wall_shape"], "16x64")
        self.assertEqual(gate["result"]["best_wall_per_state_step_shape"], "32x64")
        self.assertGreater(gate["result"]["wall_per_state_step_ratio_1x64_over_32x64"], 20.0)
        self.assertIn(
            "review_resident_batch_sweep_and_select_state_reuse_or_paged_attention_scaleup",
            gate["next_task"],
        )

    def test_resident_batch_sweep_review_selects_state_reuse_experiment(self) -> None:
        gate = json.loads(RESIDENT_BATCH_SWEEP_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "reviewed_select_resident_state_reuse_experiment_next")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/resident_batch_sweep_measurement_gate.json")
        self.assertEqual(gate["reviewed_summary"], "reports/resident_batch_sweep_summary.json")
        self.assertEqual(gate["decision"]["selected_workstream"], "resident_state_reuse_experiment")
        self.assertEqual(gate["decision"]["deferred_workstream"], "paged_attention_kv_cache_scaleup")
        self.assertTrue(gate["acceptance_policy"]["next_runtime_abi_change_requires_separate_gate"])
        self.assertTrue(gate["acceptance_policy"]["coverage_output_equivalence_required"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_equality_required"])

        reviewed = gate["reviewed_result"]
        self.assertTrue(reviewed["all_workloads_passed"])
        self.assertEqual(reviewed["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(reviewed["best_total_wall_shape"], "16x64")
        self.assertEqual(reviewed["best_wall_per_state_step_shape"], "32x64")
        self.assertGreater(reviewed["wall_per_state_step_ratio_1x64_over_32x64"], 20.0)

        contract = gate["next_experiment_contract"]
        self.assertEqual(contract["name"], "resident_state_reuse_experiment")
        self.assertEqual(contract["required_correctness_policy"], "coverage_output_equivalence")
        self.assertIn("an explicit gate before runtime ABI changes", contract["required_outputs"])
        self.assertIn("which state is authoritative", " ".join(contract["first_design_questions"]))
        self.assertEqual(gate["next_task"], "define_resident_state_reuse_experiment_gate")

    def test_resident_state_reuse_experiment_gate_defines_contract_before_abi_change(self) -> None:
        gate = json.loads(RESIDENT_STATE_REUSE_EXPERIMENT_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "implemented_resident_state_reuse_dry_run_cli")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/resident_batch_sweep_review_gate.json")
        self.assertEqual(gate["current_priority"], "measure_resident_state_reuse_experiment")
        self.assertEqual(gate["target"], "pulp_ita_mha")

        experiment = gate["experiment"]
        self.assertEqual(experiment["name"], "resident_state_reuse_experiment")
        self.assertIn("--resident-state-reuse 16x64", experiment["planned_public_dry_run_command"])
        self.assertIn("--resident-state-reuse-phases 4", experiment["planned_public_dry_run_command"])
        self.assertEqual(experiment["planned_report"], "reports/resident_state_reuse_experiment_summary.json")
        self.assertEqual(len(experiment["planned_phase_reports"]), 4)

        state_contract = gate["state_authority_contract"]
        self.assertIn("CPU-generated 1x1 init-state", state_contract["initial_authority"])
        self.assertEqual(state_contract["comparison_policy"], "coverage_output_equivalence")
        self.assertIn("diagnostic only", state_contract["raw_state_policy"])

        measurement = gate["measurement_contract"]
        self.assertEqual(measurement["minimum_phases"], 4)
        self.assertEqual(measurement["default_shape"], "16x64")
        self.assertIn("per-phase compare JSON", measurement["must_record"])
        self.assertIn("GPU kernel timing", measurement["must_separate"])

        policy = gate["acceptance_policy"]
        self.assertFalse(policy["runtime_abi_change_allowed_by_this_gate"])
        self.assertTrue(policy["public_dry_run_required_before_measurement"])
        self.assertTrue(policy["public_dry_run_implemented"])
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertFalse(policy["raw_full_state_equality_required"])
        dry_run = gate["implemented_dry_run"]
        self.assertEqual(dry_run["cli"], "src/tools/run_results_reproduction.py")
        self.assertEqual(dry_run["shared_module"], "src/tools/results_reproduction.py")
        self.assertEqual(dry_run["observed_phase_shapes"], ["16x64", "16x128", "16x192", "16x256"])
        self.assertIn("previous phase GPU dump", dry_run["phase_model"])
        self.assertEqual(gate["next_task"], "run_resident_state_reuse_experiment_and_record_gate")

    def test_resident_state_reuse_measurement_gate_records_phase_results(self) -> None:
        gate = json.loads(RESIDENT_STATE_REUSE_MEASUREMENT_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "passed_resident_state_reuse_experiment")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/resident_state_reuse_experiment_gate.json")
        self.assertEqual(gate["summary_report"], "reports/resident_state_reuse_experiment_summary.json")
        self.assertIn("--resident-state-reuse 16x64", gate["command"])
        self.assertIn("--resident-state-reuse-phases 4", gate["command"])
        self.assertEqual(gate["current_priority"], "hold_for_review_after_resident_state_reuse_measurement")

        result = gate["result"]
        self.assertEqual(result["status"], "measured_resident_state_reuse_experiment")
        self.assertEqual(result["shape"], "16x64")
        self.assertEqual(result["phase_count"], 4)
        self.assertTrue(result["all_coverage_output_passed"])
        self.assertEqual(result["max_coverage_output_mismatch_count"], 0)

        phase_shapes = [phase["shape"] for phase in gate["measured_phases"]]
        self.assertEqual(phase_shapes, ["16x64", "16x128", "16x192", "16x256"])
        self.assertEqual(gate["result"]["phase_shapes"], phase_shapes)
        self.assertEqual(gate["result"]["best_wall_per_state_step_phase"], 4)
        self.assertEqual(gate["result"]["best_wall_per_state_step_shape"], "16x256")
        self.assertEqual(gate["result"]["best_wall_per_state_step_ms"], 0.000572265625)

        for phase in gate["measured_phases"]:
            self.assertTrue(phase["coverage_output_passed"], phase["shape"])
            self.assertEqual(phase["coverage_output_mismatch_count"], 0)
            for report in phase["reports"].values():
                self.assertTrue(report.startswith("reports/"), report)

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["coverage_output_equivalence_required"])
        self.assertTrue(policy["explicit_phase_state_authority_required"])
        self.assertTrue(policy["compare_stdout_capture_required"])
        self.assertFalse(policy["runtime_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertIn("not a runtime ABI change", gate["non_claims"])
        self.assertEqual(
            gate["next_task"],
            "review_resident_state_reuse_and_select_runtime_abi_or_paged_attention_scaleup",
        )

    def test_resident_state_reuse_review_selects_persistent_state_abi_probe(self) -> None:
        gate = json.loads(RESIDENT_STATE_REUSE_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "reviewed_select_persistent_resident_state_abi_probe_next")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/resident_state_reuse_measurement_gate.json")
        self.assertEqual(gate["reviewed_summary"], "reports/resident_state_reuse_experiment_summary.json")
        self.assertEqual(gate["decision"]["selected_workstream"], "persistent_resident_state_abi_probe")
        self.assertEqual(gate["decision"]["deferred_workstream"], "paged_attention_kv_cache_scaleup")
        self.assertIn("persistent GPU-resident state ABI gap", gate["decision"]["rationale"])

        reviewed = gate["reviewed_result"]
        self.assertTrue(reviewed["all_coverage_output_passed"])
        self.assertEqual(reviewed["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(reviewed["best_wall_per_state_step_phase"], 4)
        self.assertEqual(reviewed["best_wall_per_state_step_shape"], "16x256")

        contract = gate["next_probe_contract"]
        self.assertEqual(contract["name"], "persistent_resident_state_abi_probe")
        self.assertEqual(contract["required_correctness_policy"], "coverage_output_equivalence")
        self.assertIn("without reloading the previous phase GPU dump", " ".join(contract["required_behaviors"]))
        self.assertTrue(gate["acceptance_policy"]["next_runtime_abi_change_requires_separate_implementation_gate"])
        self.assertTrue(gate["acceptance_policy"]["file_boundary_state_reuse_not_enough_for_persistent_abi_claim"])
        self.assertFalse(gate["acceptance_policy"]["raw_full_state_equality_required"])
        self.assertIn("not persistent GPU-resident state implemented yet", gate["non_claims"])
        self.assertEqual(gate["next_task"], "define_persistent_resident_state_abi_probe_gate")

    def test_persistent_resident_state_abi_probe_gate_defines_dry_run_before_runtime_change(self) -> None:
        gate = json.loads(PERSISTENT_RESIDENT_STATE_ABI_PROBE_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["status"],
            "implemented_persistent_resident_state_abi_probe_dry_run_before_runtime_change",
        )
        self.assertEqual(gate["source_gate"], "config/scaling_gates/resident_state_reuse_review_gate.json")
        self.assertEqual(gate["current_priority"], "define_persistent_resident_state_abi_probe_implementation_gate")
        self.assertEqual(gate["target"], "pulp_ita_mha")
        self.assertEqual(gate["selected_workstream"], "persistent_resident_state_abi_probe")
        self.assertEqual(gate["deferred_workstream"], "paged_attention_kv_cache_scaleup")
        self.assertIn("file-boundary reloads", gate["problem_statement"])

        baseline = gate["baseline_evidence"]
        self.assertEqual(baseline["measurement_gate"], "config/scaling_gates/resident_state_reuse_measurement_gate.json")
        self.assertEqual(baseline["summary_report"], "reports/resident_state_reuse_experiment_summary.json")
        self.assertTrue(baseline["all_coverage_output_passed"])
        self.assertEqual(baseline["max_coverage_output_mismatch_count"], 0)

        contract = gate["probe_contract"]
        self.assertEqual(contract["minimum_shape"], "16x64")
        self.assertEqual(contract["minimum_phases"], 4)
        self.assertEqual(contract["correctness_policy"], "coverage_output_equivalence")
        self.assertEqual(contract["state_authority"]["device_authority_after_init"], "GPU-resident state handle")
        self.assertEqual(
            contract["state_authority"]["forbidden_phase_boundary"],
            "previous phase GPU dump reloaded via --init-state",
        )
        self.assertIn("--persistent-resident-state-abi 16x64", contract["planned_public_dry_run_command"])
        self.assertEqual(contract["planned_report"], "reports/persistent_resident_state_abi_probe_summary.json")

        boundaries = gate["implementation_boundaries"]
        self.assertFalse(boundaries["runtime_change_allowed_by_this_gate"])
        self.assertTrue(boundaries["existing_file_boundary_flow_must_remain_available"])
        self.assertTrue(boundaries["existing_resident_steps_mode_must_remain_available"])

        dry_run = gate["implemented_dry_run"]
        self.assertEqual(dry_run["cli"], "src/tools/run_results_reproduction.py")
        self.assertEqual(dry_run["shared_module"], "src/tools/results_reproduction.py")
        self.assertEqual(dry_run["observed_phase_shapes"], ["16x64", "16x128", "16x192", "16x256"])
        self.assertIn("do not include --init-state for the previous phase GPU dump", dry_run["phase_model"])
        self.assertEqual(
            dry_run["non_dry_run_status"],
            "rejected_until_persistent_resident_state_abi_probe_implementation_gate",
        )

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["public_dry_run_required_before_runtime_change"])
        self.assertTrue(policy["new_public_cli_requires_contract_test_and_doc_mention"])
        self.assertTrue(policy["must_reject_persistent_claim_if_state_reloaded_from_previous_phase_dump"])
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertIn("not implemented yet", gate["non_claims"])
        self.assertEqual(gate["next_task"], "define_persistent_resident_state_abi_probe_implementation_gate")

    def test_persistent_resident_state_abi_implementation_gate_defines_runtime_surface(self) -> None:
        gate = json.loads(PERSISTENT_RESIDENT_STATE_ABI_IMPLEMENTATION_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "implemented_persistent_resident_state_abi_runtime_surface_probe_only")
        self.assertEqual(gate["source_gate"], "config/scaling_gates/persistent_resident_state_abi_probe_gate.json")
        self.assertEqual(gate["current_priority"], "define_persistent_resident_device_handle_storage_gate")
        self.assertIn("run_vl_hybrid.py and run_vl_hybrid.c", gate["problem_statement"])

        steps = {step["step"]: step for step in gate["implementation_plan"]}
        self.assertIn("add_python_wrapper_flags", steps)
        self.assertIn("add_c_runner_surface", steps)
        self.assertIn("enable_reproduction_non_dry_run_after_surface", steps)
        self.assertTrue(
            any(
                "--persistent-resident-state-abi-handle" in item
                for item in steps["add_python_wrapper_flags"]["required_behavior"]
            )
        )
        self.assertIn("reject phase > 1 with --init-state because that would recreate file-boundary state reuse", steps["add_python_wrapper_flags"]["required_behavior"])
        self.assertIn("reject non-phase-1 persistent use until real device handle persistence is implemented", steps["add_c_runner_surface"]["required_behavior"])

        contract = gate["planned_runtime_contract"]
        self.assertEqual(
            contract["environment"]["RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_HANDLE"],
            "forwarded handle name",
        )
        self.assertEqual(
            contract["initial_surface_semantics"]["phase_gt_1"],
            "must reject until real persistent device handle restore/lookup exists",
        )
        self.assertEqual(contract["initial_surface_semantics"]["forbidden"], "silently falling back to --init-state from a previous phase GPU dump")

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["phase_gt_1_init_state_reload_forbidden"])
        self.assertTrue(policy["existing_file_boundary_state_reuse_flow_must_remain_available"])
        self.assertTrue(policy["existing_resident_steps_flow_must_remain_available"])
        self.assertTrue(policy["deterministic_rejection_is_acceptable_before_real_handle_persistence"])
        surface = gate["implemented_runtime_surface"]
        self.assertIn("--persistent-resident-state-abi-handle", surface["python_wrapper"]["flags"])
        self.assertIn("RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_HANDLE", surface["c_runner"]["environment"])
        self.assertEqual(surface["c_runner"]["surface_status"], "probe_surface_phase1_only")
        self.assertEqual(
            surface["c_runner"]["phase_gt_1_behavior"],
            "deterministic rejection until real device handle persistence exists",
        )
        self.assertIn("make -C src/hybrid run_vl_hybrid", surface["verification"])
        self.assertIn("not real persistent device handle storage", gate["non_claims"])
        self.assertEqual(gate["next_task"], "define_persistent_resident_device_handle_storage_gate")

    def test_persistent_resident_device_handle_storage_gate_scopes_first_real_persistence_step(self) -> None:
        gate = json.loads(PERSISTENT_RESIDENT_DEVICE_HANDLE_STORAGE_GATE.read_text(encoding="utf-8"))

        self.assertEqual(gate["status"], "measured_in_process_persistent_resident_device_handle_storage")
        self.assertEqual(
            gate["source_gate"],
            "config/scaling_gates/persistent_resident_state_abi_probe_implementation_gate.json",
        )
        self.assertEqual(gate["current_priority"], "review_in_process_persistent_resident_device_handle_storage")
        self.assertEqual(gate["selected_scope"]["name"], "in_process_persistent_resident_device_handle_storage")
        self.assertIn("one CUDA context and one device allocation", gate["selected_scope"]["reason"])
        self.assertIn("cross-process persistent CUDA allocation", gate["selected_scope"]["explicitly_out_of_scope"])

        storage = gate["storage_contract"]
        self.assertEqual(storage["handle_lifetime"], "one run_vl_hybrid process invocation")
        self.assertIn("same d_storage allocation", storage["device_storage"])
        self.assertEqual(storage["state_authority"], "GPU d_storage is authoritative after phase 1 initialization")
        self.assertIn("not the authority for the next phase", storage["final_dump"])

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["device_storage_authority_required_after_phase_1"])
        self.assertTrue(policy["phase_gt_1_init_state_reload_forbidden"])
        self.assertTrue(policy["all_phase_compare_reports_required_before_summary"])
        self.assertFalse(policy["raw_full_state_equality_required"])
        self.assertEqual(
            gate["measurement_target"]["summary_report"],
            "reports/persistent_resident_state_abi_probe_summary.json",
        )
        measured = gate["measured_result"]
        self.assertEqual(measured["summary_report"], "reports/persistent_resident_state_abi_probe_summary.json")
        self.assertTrue(measured["all_coverage_output_passed"])
        self.assertEqual(measured["max_coverage_output_mismatch_count"], 0)
        self.assertEqual(measured["state_authority"], "in_process_gpu_d_storage_after_phase_1")
        self.assertEqual(measured["phase_shapes"], ["16x64", "16x128", "16x192", "16x256"])
        self.assertEqual(measured["status"], "measured_persistent_resident_state_abi_probe")
        self.assertEqual(measured["hybrid_wall_ms"], 4.517)
        self.assertEqual(measured["hybrid_gpu_kernel_total_ms"], 4.486688)
        self.assertGreater(measured["hybrid_gpu_kernel_per_state_us"], 0)
        self.assertIn("not cross-process persistent CUDA state", gate["non_claims"])
        self.assertEqual(gate["next_task"], "review_in_process_persistent_resident_device_handle_storage")

    def test_persistent_resident_device_handle_storage_review_holds_after_satisfaction(self) -> None:
        gate = json.loads(PERSISTENT_RESIDENT_DEVICE_HANDLE_STORAGE_REVIEW_GATE.read_text(encoding="utf-8"))

        self.assertEqual(
            gate["status"],
            "reviewed_in_process_persistent_resident_storage_satisfies_scoped_condition_goal",
        )
        self.assertEqual(gate["source_gate"], "config/scaling_gates/persistent_resident_device_handle_storage_gate.json")
        self.assertEqual(gate["current_priority"], "hold_for_review_after_persistent_resident_storage_measurement")
        self.assertEqual(gate["decision"]["scoped_condition_goal_status"], "satisfied")
        self.assertEqual(gate["reviewed_result"]["max_coverage_output_mismatch_count"], 0)
        self.assertTrue(gate["reviewed_result"]["all_coverage_output_passed"])
        self.assertIn("cross_process_persistent_cuda_state", gate["decision"]["optional_followups"])
        self.assertIn("not cross-process persistent CUDA state", gate["non_claims"])
        self.assertEqual(gate["next_task"], "hold_for_review_after_persistent_resident_storage_measurement")

    def test_source_of_truth_mentions_new_followup(self) -> None:
        combined = "\n".join(
            [
                STATUS.read_text(encoding="utf-8"),
                ROADMAP.read_text(encoding="utf-8"),
                README.read_text(encoding="utf-8"),
            ]
        )

        self.assertIn("modern_llm_serving_rtl_hybrid_conditions", combined)
        self.assertIn("neural_network_rtl_paged_kv_cache_large_scaleup_gate.json", combined)
        self.assertIn("neural_network_rtl_paged_kv_cache_large_review_gate.json", combined)
        self.assertIn("neural_network_rtl_full_ita_mha_dependency_audit_gate.json", combined)
        self.assertIn("neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json", combined)
        self.assertIn("neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json", combined)
        self.assertIn("neural_network_rtl_paged_attention_kv_score_harness_gate.json", combined)
        self.assertIn("full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json", combined)
        self.assertIn("select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh", combined)
        self.assertIn("hybrid_verilator_like_config_and_probe_generation_gate.json", combined)
        self.assertIn("full_mha_hybrid_try_completion_audit.json", combined)
        self.assertIn("full_mha_scaleup_64x1_1x64_gate.json", combined)
        self.assertIn("prefill_decode_split_mha_benchmark_gate.json", combined)
        self.assertIn("resident_decode_optimization_probe_gate.json", combined)
        self.assertIn("resident_decode_batch_parallel_probe_gate.json", combined)
        self.assertIn("modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json", combined)
        self.assertIn("public_results_packaging_gate.json", combined)
        self.assertIn("public_benchmark_pack_goal_completion_audit.json", combined)
        self.assertIn("one_command_reproduction_flow_gate.json", combined)
        self.assertIn("repeat_median_results_reproduction_gate.json", combined)
        self.assertIn("resident_execution_optimization_next_gate.json", combined)
        self.assertIn("resident_batch_sweep_measurement_gate.json", combined)
        self.assertIn("resident_batch_sweep_review_gate.json", combined)
        self.assertIn("resident_state_reuse_experiment_gate.json", combined)
        self.assertIn("resident_state_reuse_measurement_gate.json", combined)
        self.assertIn("resident_state_reuse_review_gate.json", combined)
        self.assertIn("persistent_resident_state_abi_probe_gate.json", combined)
        self.assertIn("persistent_resident_state_abi_probe_implementation_gate.json", combined)
        self.assertIn("persistent_resident_device_handle_storage_gate.json", combined)
        self.assertIn("persistent_resident_device_handle_storage_review_gate.json", combined)
        self.assertIn("reports/persistent_resident_state_abi_probe_summary.json", combined)
        self.assertIn("--persistent-resident-state-abi 16x64", combined)
        self.assertIn("docs/results.md", combined)
        self.assertIn("src/tools/run_results_reproduction.py", combined)
        self.assertIn("python3 src/tools/run_results_reproduction.py --repeat-median 3", combined)
        self.assertIn("reports/pulp_ita_mha_64x1_1x64_scaling_summary.json", combined)
        self.assertIn("reports/pulp_ita_mha_prefill_decode_split_summary.json", combined)
        self.assertIn("reports/pulp_ita_mha_resident_decode_1x64_summary.json", combined)
        self.assertIn("reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json", combined)
        self.assertIn("reports/pulp_ita_mha_hybrid_1x1.txt", combined)
        self.assertIn("reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json", combined)
        self.assertIn("reports/pulp_ita_mha_first_hybrid_benchmark_summary.json", combined)
        self.assertIn("reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json", combined)
        self.assertIn("reports/results_reproduction_median_summary.json", combined)
        self.assertIn("reports/resident_batch_sweep_summary.json", combined)
        self.assertIn("reports/resident_state_reuse_experiment_summary.json", combined)
        self.assertIn("reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json", combined)
        self.assertIn("reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json", combined)
        self.assertIn("reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json", combined)
        self.assertIn("pulp_paged_kv_cache_large_host_probe", combined)
        self.assertIn("overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv", combined)
        self.assertIn("tc_sram", combined)


if __name__ == "__main__":
    unittest.main()
