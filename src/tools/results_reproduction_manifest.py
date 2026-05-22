"""Public result-pack path manifest for results reproduction workflows."""

from results_reproduction_manifest_sources import PUBLIC_PACK_SOURCE_PATHS


def _gate_records(*names: str) -> tuple[str, ...]:
    return tuple(f"records/scaling_gates/{name}.json" for name in names)


def _report_paths(*names: str) -> tuple[str, ...]:
    return tuple(f"reports/{name}" for name in names)


def _execution_gate_records(stem: str) -> tuple[str, ...]:
    return _gate_records(
        f"{stem}_gate", f"{stem}_dry_run_gate", f"{stem}_dry_run_review_gate",
        f"{stem}_execution_gate", f"{stem}_execution_result_gate", f"{stem}_execution_review_gate",
        f"public_results_packaging_refresh_after_{stem}_execution_gate",
        f"public_benchmark_pack_externalization_completion_after_{stem}_execution_gate",
        f"next_measurement_selection_after_{stem}_public_pack_refresh_gate",
    )


def _measurement_gate_records(stem: str) -> tuple[str, ...]:
    return _gate_records(
        f"{stem}_gate", f"{stem}_dry_run_gate", f"{stem}_dry_run_review_gate",
        f"{stem}_measurement_gate", f"{stem}_measurement_review_gate",
        f"public_results_packaging_refresh_after_{stem}_gate",
        f"public_benchmark_pack_externalization_completion_after_{stem}_gate",
        f"next_measurement_selection_after_{stem}_public_pack_refresh_gate",
    )


PUBLIC_PACK_RECORD_PATHS = (
    *_gate_records(
        "public_results_packaging_gate", "public_benchmark_pack_externalization_readiness_audit",
        "public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate",
        "next_goal_selection_after_persistent_resident_repeat_median_gate",
        "persistent_resident_state_abi_repeat_median_measurement_gate",
        "public_results_packaging_refresh_after_persistent_resident_repeat_median_gate",
        "public_benchmark_pack_externalization_completion_gate",
        "next_measurement_selection_after_public_benchmark_pack_externalization_gate",
        "paged_attention_kv_cache_scale_up_measurement_gate",
        "paged_attention_kv_cache_scale_up_measurement_review_gate",
        "paged_attention_kv_cache_timing_summary_gate", "paged_attention_kv_cache_timing_summary_review_gate",
        "public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate",
        "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate",
        "next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate",
        "paged_attention_kv_cache_repeat_median_timing_gate",
        "paged_attention_kv_cache_repeat_median_workflow_gate",
        "paged_attention_kv_cache_repeat_median_measurement_gate", "paged_attention_kv_cache_repeat_median_review_gate",
        "public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate",
        "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate",
        "next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate",
    ),
    *_execution_gate_records("config_generation_validation_breadth"),
    *_execution_gate_records("config_generation_validation_shape_breadth"),
    *_gate_records(
        "resident_execution_overhead_breakdown_gate", "resident_execution_overhead_breakdown_analysis_gate",
        "resident_execution_overhead_runtime_boundary_review_gate",
        "persistent_resident_state_abi_shape_phase_sweep_workflow_gate",
    ),
    *_measurement_gate_records("persistent_resident_state_abi_shape_phase_sweep"),
    *_measurement_gate_records("paged_attention_kv_cache_scale_up_continuation"),
    *_gate_records("paged_attention_kv_cache_scale_up_continuation_repeat_median_workflow_gate"),
    *_measurement_gate_records("paged_attention_kv_cache_scale_up_continuation_repeat_median"),
    *_measurement_gate_records("paged_attention_kv_cache_scale_up_next_shapes"),
    *_gate_records("paged_attention_kv_cache_scale_up_next_shapes_repeat_median_workflow_gate"),
    *_measurement_gate_records("paged_attention_kv_cache_scale_up_next_shapes_repeat_median"),
    *_execution_gate_records("config_generation_validation_additional_targets"),
    *_gate_records(
        "tlul_template_schema_normalization_gate", "tlul_template_schema_normalization_implementation_gate",
        "tlul_template_schema_normalization_implementation_review_gate",
        "tlul_template_schema_normalization_execution_gate",
        "tlul_template_schema_normalization_execution_result_gate",
        "tlul_template_schema_normalization_execution_review_gate",
        "tlul_template_schema_normalization_breadth_public_pack_refresh_gate",
        "public_benchmark_pack_externalization_completion_after_tlul_template_schema_normalization_breadth_gate",
    ),
    *_execution_gate_records("tlul_template_schema_normalization_breadth"),
    *_execution_gate_records("tlul_legacy_clock_reset_metadata_matrix"),
    *_execution_gate_records("tlul_template_schema_normalization_more_breadth"),
    *_execution_gate_records("tlul_template_schema_normalization_even_more_breadth"),
    *_execution_gate_records("config_generation_validation_followup"),
    *_gate_records(
        "tlul_template_schema_metadata_invariant_review_gate",
        "tlul_template_schema_metadata_invariant_review_dry_run_gate",
        "tlul_template_schema_metadata_invariant_review_dry_run_review_gate",
        "tlul_template_schema_metadata_invariant_execution_gate",
        "tlul_template_schema_metadata_invariant_execution_result_gate",
        "tlul_template_schema_metadata_invariant_execution_review_gate",
        "public_results_packaging_refresh_after_tlul_template_schema_metadata_invariant_execution_gate",
        "public_benchmark_pack_externalization_completion_after_tlul_template_schema_metadata_invariant_execution_gate",
        "next_measurement_selection_after_tlul_template_schema_metadata_invariant_public_pack_refresh_gate",
        "resident_execution_launch_overhead_reduction_gate", "resident_execution_launch_overhead_reduction_analysis_gate",
        "resident_execution_launch_overhead_reduction_analysis_review_gate",
        "single_state_repeated_launch_isolation_measurement_gate",
        "single_state_repeated_launch_isolation_measurement_result_gate",
        "single_state_repeated_launch_isolation_measurement_review_gate",
        "single_state_launch_orchestration_cleanup_gate",
        "single_state_launch_orchestration_cleanup_surface_inspection_gate",
        "repeat_median_summary_helper_cleanup_implementation_gate", "repeat_median_summary_helper_cleanup_review_gate",
        "next_goal_selection_after_helper_cleanup_review_gate",
        "paged_attention_kv_cache_scale_up_followup_gate", "paged_attention_kv_cache_scale_up_followup_dry_run_gate",
        "paged_attention_kv_cache_scale_up_followup_measurement_gate",
        "paged_attention_kv_cache_scale_up_followup_measurement_review_gate",
        "public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_followup_gate",
        "public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_followup_gate",
        "public_benchmark_pack_goal_completion_audit",
        "generic_hybrid_benchmark_cli_gate",
        "pulp_ita_mha_first_generic_host_probe_build_run_compare_gate",
        "pulp_ita_mha_shape_expansion_gate",
        "pulp_ita_mha_shape_expansion_review_gate",
    ),
)

PUBLIC_PACK_REPORT_PATHS = (
    *_report_paths(
        "results_reproduction_median_summary.json", "persistent_resident_state_abi_probe_summary.json",
        "persistent_resident_state_abi_repeat_median_summary.json",
        "persistent_resident_state_abi_shape_phase_sweep_summary.json", "mobile_vit_hybrid_128_summary.json",
        "tlul_fifo_sync_cpu_vs_hybrid_1x1_coverage_output_compare.json",
        "tlul_lc_gate_cpu_vs_hybrid_1x1_coverage_output_compare.json",
        "tlul_adapter_host_cpu_vs_hybrid_1x1_coverage_output_compare.json",
        "nvdla_cmac_core_mac_cpu_vs_hybrid_1x1_coverage_output_compare.json",
        "nvdla_cmac_core_mac_cpu_vs_hybrid_8x1_coverage_output_compare.json",
        "nvdla_cmac_core_mac_cpu_vs_hybrid_8x4_coverage_output_compare.json",
        "pulp_ita_dotp_cpu_vs_hybrid_64x1_coverage_output_compare.json",
        "pulp_ita_dotp_cpu_vs_hybrid_1x64_coverage_output_compare.json",
        "pulp_ita_softmax_top_cpu_vs_hybrid_64x1_coverage_output_compare.json",
        "pulp_ita_softmax_top_cpu_vs_hybrid_1x64_coverage_output_compare.json",
        "pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json",
        "pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
        "pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json",
        "pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json",
        "pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json",
        "pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json",
        "pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json",
        "pulp_paged_kv_cache_large_cpu_vs_hybrid_512x1_coverage_output_compare.json",
        "pulp_paged_kv_cache_large_cpu_vs_hybrid_1x128_coverage_output_compare.json",
        "pulp_paged_kv_cache_large_cpu_vs_hybrid_1024x1_coverage_output_compare.json",
        "pulp_paged_kv_cache_large_cpu_vs_hybrid_1x256_coverage_output_compare.json",
        "pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json",
        "pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json",
        "pulp_paged_attention_kv_score_cpu_vs_hybrid_128x1_coverage_output_compare.json",
        "pulp_paged_attention_kv_score_cpu_vs_hybrid_1x128_coverage_output_compare.json",
        "pulp_paged_attention_kv_score_cpu_vs_hybrid_256x1_coverage_output_compare.json",
        "pulp_paged_attention_kv_score_cpu_vs_hybrid_1x256_coverage_output_compare.json",
        "paged_attention_kv_cache_repeat_median_summary.json",
        "paged_kv_repeat_pulp_paged_kv_cache_large_256x1_median.json",
        "paged_kv_repeat_pulp_paged_kv_cache_large_1x64_median.json",
        "paged_kv_repeat_pulp_paged_attention_kv_score_64x1_median.json",
        "paged_kv_repeat_pulp_paged_attention_kv_score_1x64_median.json",
        "paged_attention_kv_cache_scale_up_continuation_repeat_median_summary.json",
        "paged_kv_continuation_repeat_pulp_paged_kv_cache_large_512x1_median.json",
        "paged_kv_continuation_repeat_pulp_paged_kv_cache_large_1x128_median.json",
        "paged_kv_continuation_repeat_pulp_paged_attention_kv_score_128x1_median.json",
        "paged_kv_continuation_repeat_pulp_paged_attention_kv_score_1x128_median.json",
        "paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json",
        "paged_kv_next_shapes_repeat_pulp_paged_kv_cache_large_1024x1_median.json",
        "paged_kv_next_shapes_repeat_pulp_paged_kv_cache_large_1x256_median.json",
        "paged_kv_next_shapes_repeat_pulp_paged_attention_kv_score_256x1_median.json",
        "paged_kv_next_shapes_repeat_pulp_paged_attention_kv_score_1x256_median.json",
        "hybrid_benchmark_pulp_ita_mha_template_1x1.json",
        "hybrid_benchmark_paged_attention_kv_score_template_1x1.json",
        "hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json",
        "hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json",
        "hybrid_benchmark_mobile_vit_template_limit128.json",
    ),
)

PUBLIC_PACK_ARCHIVE_PATHS = (
    *PUBLIC_PACK_SOURCE_PATHS,
    *PUBLIC_PACK_RECORD_PATHS,
    *PUBLIC_PACK_REPORT_PATHS,
)
