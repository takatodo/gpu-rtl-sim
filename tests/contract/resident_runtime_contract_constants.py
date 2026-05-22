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
    'public_results_packaging_gate',
    'public_benchmark_pack_goal_completion_audit',
    'resident_execution_optimization_next_gate',
    'resident_batch_sweep_measurement_gate',
    'resident_batch_sweep_review_gate',
    'resident_state_reuse_experiment_gate',
    'resident_state_reuse_measurement_gate',
    'resident_state_reuse_review_gate',
    'persistent_resident_state_abi_probe_gate',
    'persistent_resident_state_abi_probe_implementation_gate',
    'persistent_resident_device_handle_storage_gate',
    'persistent_resident_device_handle_storage_review_gate',
    'next_goal_selection_after_persistent_resident_repeat_median_gate',
    'public_results_packaging_refresh_after_persistent_resident_repeat_median_gate',
    'public_benchmark_pack_externalization_completion_gate',
    'next_measurement_selection_after_public_benchmark_pack_externalization_gate',
    'paged_attention_kv_cache_scale_up_measurement_gate',
    'paged_attention_kv_cache_scale_up_measurement_review_gate',
    'paged_attention_kv_cache_timing_summary_gate',
    'paged_attention_kv_cache_timing_summary_review_gate',
    'public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate',
    'public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate',
    'next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate',
    'paged_attention_kv_cache_repeat_median_timing_gate',
    'paged_attention_kv_cache_repeat_median_workflow_gate',
    'paged_attention_kv_cache_repeat_median_measurement_gate',
    'paged_attention_kv_cache_repeat_median_review_gate',
    'public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate',
    'public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate',
    'next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate',
    'config_generation_validation_breadth_gate',
    'config_generation_validation_breadth_dry_run_gate',
    'config_generation_validation_breadth_dry_run_review_gate',
    'config_generation_validation_breadth_execution_gate',
    'generic_hybrid_benchmark_cli_gate',
)

SPECIAL_SELECTION_EVIDENCE_PATHS = {
    'full_ita_mha': {
        "gate": "config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
        "summary": "reports/pulp_ita_mha_first_hybrid_benchmark_summary.json",
        "compares": [
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json",
            "reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json"
        ],
        "completion_audit": "config/scaling_gates/full_mha_hybrid_try_completion_audit.json",
        "scaleup_64x1_1x64_gate": "config/scaling_gates/full_mha_scaleup_64x1_1x64_gate.json",
        "scaleup_64x1_1x64_summary": "reports/pulp_ita_mha_64x1_1x64_scaling_summary.json",
        "prefill_decode_split_gate": "config/scaling_gates/prefill_decode_split_mha_benchmark_gate.json",
        "prefill_decode_split_summary": "reports/pulp_ita_mha_prefill_decode_split_summary.json",
        "resident_decode_gate": "config/scaling_gates/resident_decode_optimization_probe_gate.json",
        "resident_decode_summary": "reports/pulp_ita_mha_resident_decode_1x64_summary.json",
        "resident_decode_batch_parallel_gate": "config/scaling_gates/resident_decode_batch_parallel_probe_gate.json",
        "resident_decode_batch_parallel_summary": "reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json"
    },
    'larger_paged_kv': {
        "gate": "config/scaling_gates/neural_network_rtl_paged_kv_cache_large_scaleup_gate.json",
        "review_gate": "config/scaling_gates/neural_network_rtl_paged_kv_cache_large_review_gate.json",
        "summary": "reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json"
    },
    'paged_attention_kv_score': {
        "gate": "config/scaling_gates/neural_network_rtl_paged_attention_kv_score_harness_gate.json",
        "summary": "reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json"
    },
    'completion_audit': "config/scaling_gates/full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json",
    'modern_llm_conditions_audit': "config/scaling_gates/modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json",
    'public_results_doc': "docs/results.md",
    'one_command_reproduction_gate': "config/scaling_gates/one_command_reproduction_flow_gate.json",
    'one_command_reproduction_cli': "src/tools/run_results_reproduction.py",
    'repeat_median_results_gate': "config/scaling_gates/repeat_median_results_reproduction_gate.json",
    'repeat_median_results_summary': "reports/results_reproduction_median_summary.json",
    'resident_batch_sweep_summary': "reports/resident_batch_sweep_summary.json",
    'resident_state_reuse_summary': "reports/resident_state_reuse_experiment_summary.json",
    'persistent_resident_state_abi_probe_summary': "reports/persistent_resident_state_abi_probe_summary.json",
    'persistent_resident_state_abi_repeat_median_gate': "config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json",
    'persistent_resident_state_abi_repeat_median_summary': "reports/persistent_resident_state_abi_repeat_median_summary.json",
    'paged_attention_kv_cache_repeat_median_summary': "reports/paged_attention_kv_cache_repeat_median_summary.json",
    'goal_review_gate': "config/scaling_gates/neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json",
    'dependency_audit': "config/scaling_gates/neural_network_rtl_full_ita_mha_dependency_audit_gate.json",
    'wrapper_summary_reports': {
        "pulp_ita_mha_template_1x1": "reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json",
        "paged_attention_kv_score_template_1x1": "reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json",
        "pulp_ita_mha_resident_state_reuse_1x1": "reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json",
        "pulp_ita_mha_persistent_resident_state_abi_1x1": "reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json",
        "mobile_vit_template_limit128": "reports/hybrid_benchmark_mobile_vit_template_limit128.json"
    },
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
