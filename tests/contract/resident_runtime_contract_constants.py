from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SELECTION = REPO_ROOT / "config" / "selection.json"
TARGETS = REPO_ROOT / "config" / "targets.json"
CONFIG_README = REPO_ROOT / "config" / "README.md"
ARCHIVED_TARGETS = REPO_ROOT / "config" / "archived_targets.json"
SCALING_GATES_README = REPO_ROOT / "config" / "scaling_gates" / "README.md"
RECORDS_README = REPO_ROOT / "records" / "README.md"
CONFIG_MINIMAL_SURFACE_AUDIT = (
    REPO_ROOT / "records" / "scaling_gates" / "config_minimal_surface_completion_audit.json"
)
README = REPO_ROOT / "README.md"
STATUS = REPO_ROOT / "docs" / "status.md"
ROADMAP = REPO_ROOT / "docs" / "roadmap.md"
GITIGNORE = REPO_ROOT / ".gitignore"
GITMODULES = REPO_ROOT / ".gitmodules"
COMPARE_VL_HYBRID_MODES = REPO_ROOT / "src" / "tools" / "compare_vl_hybrid_modes.py"
TLUL_COVERAGE_OUTPUT_GATE = (
    REPO_ROOT / "config" / "scaling_gates" / "tlul_coverage_output_equivalence.json"
)
TLUL_FIFO_COVERAGE_MANIFEST = (
    REPO_ROOT
    / "overlays"
    / "rtlmeter"
    / "designs"
    / "OpenTitan"
    / "tests"
    / "tlul_fifo_sync_coverage_regions.json"
)
TLUL_SLICE_HOST_PROBE = REPO_ROOT / "src" / "hybrid" / "tlul_slice_host_probe.cpp"
TLUL_CPU_BASELINE_RUNNER = REPO_ROOT / "src" / "tools" / "run_tlul_fifo_sync_cpu_baseline.py"
RUN_VL_HYBRID_PY = REPO_ROOT / "src" / "tools" / "run_vl_hybrid.py"
RUN_VL_HYBRID_C = REPO_ROOT / "src" / "hybrid" / "run_vl_hybrid.c"

DEFAULT_SELECTION_EVIDENCE_KEYS = (
    "next_goal_selection_after_persistent_resident_repeat_median_gate",
    "public_results_packaging_refresh_after_persistent_resident_repeat_median_gate",
    "public_benchmark_pack_externalization_completion_gate",
    "next_measurement_selection_after_public_benchmark_pack_externalization_gate",
    "paged_attention_kv_cache_scale_up_measurement_gate",
    "paged_attention_kv_cache_scale_up_measurement_review_gate",
    "paged_attention_kv_cache_timing_summary_gate",
    "paged_attention_kv_cache_timing_summary_review_gate",
    "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
    "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate",
    "next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate",
    "paged_attention_kv_cache_repeat_median_timing_gate",
    "paged_attention_kv_cache_repeat_median_workflow_gate",
    "paged_attention_kv_cache_repeat_median_measurement_gate",
    "paged_attention_kv_cache_repeat_median_review_gate",
    "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate",
    "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate",
    "next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate",
    "config_generation_validation_breadth_gate",
    "config_generation_validation_breadth_dry_run_gate",
    "config_generation_validation_breadth_dry_run_review_gate",
    "config_generation_validation_breadth_execution_gate",
    "config_generation_validation_breadth_execution_result_gate",
    "config_generation_validation_breadth_execution_review_gate",
    "public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate",
    "public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate",
    "next_measurement_selection_after_config_generation_validation_breadth_public_pack_refresh_gate",
    "config_generation_validation_shape_breadth_gate",
    "config_generation_validation_shape_breadth_dry_run_gate",
    "config_generation_validation_shape_breadth_dry_run_review_gate",
    "config_generation_validation_shape_breadth_execution_gate",
    "config_generation_validation_shape_breadth_execution_result_gate",
    "config_generation_validation_shape_breadth_execution_review_gate",
    "public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate",
    "public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution_gate",
    "next_measurement_selection_after_config_generation_validation_shape_breadth_public_pack_refresh_gate",
    "config_generation_validation_additional_targets_gate",
    "config_generation_validation_additional_targets_dry_run_gate",
    "config_generation_validation_additional_targets_dry_run_review_gate",
    "config_generation_validation_additional_targets_execution_gate",
    "config_generation_validation_additional_targets_execution_result_gate",
    "config_generation_validation_additional_targets_execution_review_gate",
    "public_results_packaging_refresh_after_config_generation_validation_additional_targets_execution_gate",
    "public_benchmark_pack_externalization_completion_after_config_generation_validation_additional_targets_execution_gate",
    "next_measurement_selection_after_config_generation_validation_additional_targets_public_pack_refresh_gate",
    "tlul_template_schema_normalization_gate",
    "tlul_template_schema_normalization_implementation_gate",
    "tlul_template_schema_normalization_implementation_review_gate",
    "tlul_template_schema_normalization_execution_gate",
    "tlul_template_schema_normalization_execution_result_gate",
    "tlul_template_schema_normalization_execution_review_gate",
    "tlul_template_schema_normalization_breadth_gate",
    "resident_execution_overhead_breakdown_gate",
    "resident_execution_overhead_breakdown_analysis_gate",
    "resident_execution_overhead_runtime_boundary_review_gate",
    "persistent_resident_state_abi_shape_phase_sweep_gate",
    "public_benchmark_pack_externalization_completion_after_persistent_resident_state_abi_shape_phase_sweep_gate",
    "next_measurement_selection_after_persistent_resident_state_abi_shape_phase_sweep_public_pack_refresh_gate",
    "paged_attention_kv_cache_scale_up_continuation_gate",
    "paged_attention_kv_cache_scale_up_continuation_dry_run_gate",
    "paged_attention_kv_cache_scale_up_continuation_dry_run_review_gate",
    "paged_attention_kv_cache_scale_up_continuation_measurement_gate",
    "paged_attention_kv_cache_scale_up_continuation_measurement_review_gate",
    "public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_gate",
)

SPECIAL_SELECTION_EVIDENCE_PATHS = {
    "persistent_resident_state_abi_repeat_median_gate": (
        "config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json"
    ),
    "persistent_resident_state_abi_repeat_median_summary": (
        "reports/persistent_resident_state_abi_repeat_median_summary.json"
    ),
    "paged_attention_kv_cache_repeat_median_summary": (
        "reports/paged_attention_kv_cache_repeat_median_summary.json"
    ),
}

CURRENT_NN_AND_MOBILE_VIT_DOC_TOKENS = (
    "modern_llm_serving_rtl_hybrid_conditions",
    "neural_network_rtl_paged_kv_cache_large_scaleup_gate.json",
    "neural_network_rtl_paged_kv_cache_large_review_gate.json",
    "neural_network_rtl_full_ita_mha_dependency_audit_gate.json",
    "neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
    "neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json",
    "neural_network_rtl_paged_attention_kv_score_harness_gate.json",
    "full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json",
    "modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json",
    "public_results_packaging_gate.json",
    "one_command_reproduction_flow_gate.json",
    "repeat_median_results_reproduction_gate.json",
    "resident_execution_optimization_next_gate.json",
    "resident_batch_sweep_measurement_gate.json",
    "resident_batch_sweep_review_gate.json",
    "resident_state_reuse_experiment_gate.json",
    "resident_state_reuse_measurement_gate.json",
    "resident_state_reuse_review_gate.json",
    "persistent_resident_state_abi_probe_gate.json",
    "persistent_resident_state_abi_probe_implementation_gate.json",
    "persistent_resident_device_handle_storage_gate.json",
    "persistent_resident_device_handle_storage_review_gate.json",
    "docs/results.md",
    "src/tools/run_results_reproduction.py",
    "reports/results_reproduction_median_summary.json",
    "reports/resident_batch_sweep_summary.json",
    "reports/resident_state_reuse_experiment_summary.json",
    "reports/persistent_resident_state_abi_probe_summary.json",
    "reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json",
    "reports/pulp_ita_mha_first_hybrid_benchmark_summary.json",
    "reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json",
    "reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json",
    "reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
    "reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json",
    "pulp_paged_kv_cache_large_host_probe",
    "overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv",
    "tc_sram",
    "mobile_vit_cpu_kick_imagenet_accuracy",
    "mobile_vit_cpu_kick_rtl_hybrid_boundary",
    "apple/mobilevit-small",
    "complete_full_imagenet_validation_cpu_kick_accuracy_measured",
    "top-1 0.77022",
    "mobile_vit_cpu_kick_rtl_proxy_host_probe",
    "phase_12_mobile_vit_cpu_kick_rtl_hybrid_boundary",
    "phase_11_mobile_vit_cpu_kick_imagenet_accuracy",
    "select_mobile_vit_model_and_reference_eval_source: done",
    "define_mobile_vit_cpu_kick_control_contract: done",
    "define_mobile_vit_accuracy_metric_contract: done",
    "define_mobile_vit_reference_inference_contract: done",
    "define_mobile_vit_imagenet_manifest_builder_contract: done",
)
