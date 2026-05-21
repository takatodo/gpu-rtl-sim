# Results

## Conclusion

The hybrid runtime is useful for scoped modern-LLM-serving-like RTL harnesses when the workload has many independent states per launch and correctness is checked with coverage-output equivalence.

The strongest measured condition is state-parallel execution. The weakest baseline condition is a single state advanced across many repeated launches. Resident execution only slightly changes the `1x64` median in the latest run, while resident batch-parallel decode restores much of the throughput shape by amortizing one resident launch across many states.

The persistent resident ABI probe adds a stronger decode-like condition: one process can keep the same GPU `d_storage` allocation authoritative across four cumulative `16x64` phases, with phase dumps used only as compare evidence rather than as the next phase input.

The current result is a scoped RTL-harness conclusion. It is not a production LLM serving benchmark.

## How To Read This Pack

Read this benchmark pack in this order:

1. Start with the conclusion and non-claims in this document.
2. Use `docs/tool_surface.md` to find the small operator-facing CLI set before reading helper modules.
3. Use `config/selection.json`, `config/selection_extensions.json`, and `config/selection_verification_commands.json` (referenced from selection; merge with `src/tools/selection_state.load_selection` when you need the full tree), plus `docs/status.md` and `docs/roadmap.md`, as the canonical current project state.
4. Treat `reports/*.json` as generated evidence from documented commands, not as hand-authored decisions.
5. Use wrapper summaries named `reports/hybrid_benchmark_*.json` as the compact review surface for target, shape or limit, execution mode, commands, expected reports, and collected evidence.
6. Use `--dry-run` commands before running measurements to inspect the exact command sequence and expected generated outputs.

Evidence status terms:

| Term | Meaning |
| --- | --- |
| `executed` | The wrapper command executed benchmark commands and collected evidence from the resulting reports. |
| `existing_evidence` | The wrapper summary was built from already generated reports without rerunning the benchmark commands. |
| `coverage_output_equivalence` | CPU and hybrid agree on the declared output word set; this is not raw full-state equality. |
| `reports/` | Generated summaries and comparisons; useful evidence, but not source of truth. |
| `artifacts/` | Generated build outputs, binaries, state dumps, and raw runtime material. |

Local cleanup: large or stale trees under `artifacts/` (for example `mobile_vit/venv`, unused `*_obj_dir`) may be deleted to reclaim disk when you can rerun documented commands; see README **Artifact Policy → Local disk hygiene**.

External pack boundary:

- A published review bundle may include generated `reports/*.json` files as evidence snapshots.
- A clean checkout should treat those reports as reproducible outputs and regenerate them from the documented commands when needed.
- Canonical decisions remain in `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, and `README.md`.

Prerequisites by path:

| Path | Needs |
| --- | --- |
| `python3 src/tools/run_results_reproduction.py --dry-run` | Python only; prints commands and expected outputs. |
| `python3 src/tools/run_hybrid_benchmark.py ... --dry-run` | Python only; prints target-oriented wrapper commands. |
| Wrapper summary generation with `--summary-out` | Existing tool inputs plus generated `reports/` evidence when collecting results. |
| Persistent resident ABI measurements | Verilator object directories, CUDA-capable runtime, and the hybrid host/GPU build outputs under `artifacts/`. |
| MobileViT `limit 128` | Python MobileViT dependencies, local Hugging Face ImageNet parquet cache, and generated CPU-kick/hybrid proxy reports. |

Public pack manifest:

| Group | Include | Reason |
| --- | --- | --- |
| Current source of truth and reader pack | `README.md`, `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, `docs/results.md`, `docs/tool_surface.md` | Current objective, status, roadmap, result narrative, reader guide, and small operator-facing tool surface. Canonical project-state decisions remain in `README.md`, `config/selection.json`, `docs/status.md`, and `docs/roadmap.md`; this document is the external-facing result pack. |
| Gate and audit evidence | `records/scaling_gates/public_results_packaging_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`, `records/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json`, `records/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json`, `records/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_gate.json`, `records/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json`, `records/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json`, `records/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json`, `records/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json`, `records/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json`, `records/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json`, `records/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json`, `records/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json`, `records/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate.json`, `records/scaling_gates/config_generation_validation_breadth_gate.json`, `records/scaling_gates/config_generation_validation_breadth_dry_run_gate.json`, `records/scaling_gates/config_generation_validation_breadth_dry_run_review_gate.json`, `records/scaling_gates/config_generation_validation_breadth_execution_gate.json`, `records/scaling_gates/config_generation_validation_breadth_execution_result_gate.json`, `records/scaling_gates/config_generation_validation_breadth_execution_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate.json`, `records/scaling_gates/next_measurement_selection_after_config_generation_validation_breadth_public_pack_refresh_gate.json`, `records/scaling_gates/config_generation_validation_shape_breadth_gate.json`, `records/scaling_gates/config_generation_validation_shape_breadth_dry_run_gate.json`, `records/scaling_gates/config_generation_validation_shape_breadth_dry_run_review_gate.json`, `records/scaling_gates/config_generation_validation_shape_breadth_execution_gate.json`, `records/scaling_gates/config_generation_validation_shape_breadth_execution_result_gate.json`, `records/scaling_gates/config_generation_validation_shape_breadth_execution_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution_gate.json`, `records/scaling_gates/next_measurement_selection_after_config_generation_validation_shape_breadth_public_pack_refresh_gate.json`, `records/scaling_gates/resident_execution_overhead_breakdown_gate.json`, `records/scaling_gates/resident_execution_overhead_breakdown_analysis_gate.json`, `records/scaling_gates/resident_execution_overhead_runtime_boundary_review_gate.json`, `records/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_gate.json`, `records/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_workflow_gate.json`, `records/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_measurement_gate.json`, `records/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_measurement_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_persistent_resident_state_abi_shape_phase_sweep_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_persistent_resident_state_abi_shape_phase_sweep_gate.json`, `records/scaling_gates/next_measurement_selection_after_persistent_resident_state_abi_shape_phase_sweep_public_pack_refresh_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_continuation_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_continuation_dry_run_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_continuation_dry_run_review_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_continuation_measurement_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_continuation_measurement_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_continuation_gate.json`, `records/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_continuation_public_pack_refresh_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_template_schema_metadata_invariant_execution_gate.json`, `records/scaling_gates/next_measurement_selection_after_tlul_template_schema_metadata_invariant_public_pack_refresh_gate.json`, `records/scaling_gates/resident_execution_launch_overhead_reduction_gate.json`, `records/scaling_gates/resident_execution_launch_overhead_reduction_analysis_gate.json`, `records/scaling_gates/resident_execution_launch_overhead_reduction_analysis_review_gate.json`, `records/scaling_gates/single_state_repeated_launch_isolation_measurement_gate.json`, `records/scaling_gates/single_state_repeated_launch_isolation_measurement_result_gate.json`, `records/scaling_gates/single_state_repeated_launch_isolation_measurement_review_gate.json`, `records/scaling_gates/single_state_launch_orchestration_cleanup_gate.json`, `records/scaling_gates/single_state_launch_orchestration_cleanup_surface_inspection_gate.json`, `records/scaling_gates/repeat_median_summary_helper_cleanup_implementation_gate.json`, `records/scaling_gates/repeat_median_summary_helper_cleanup_review_gate.json`, `records/scaling_gates/next_goal_selection_after_helper_cleanup_review_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_followup_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_followup_dry_run_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_followup_measurement_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_followup_measurement_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_followup_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_followup_gate.json`, `records/scaling_gates/public_benchmark_pack_goal_completion_audit.json`, `records/scaling_gates/generic_hybrid_benchmark_cli_gate.json`, `records/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json`, `records/scaling_gates/pulp_ita_mha_shape_expansion_gate.json`, `records/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json` | Machine-readable benchmark-pack scope, externalization readiness, completion audit, wrapper summary schema, the fresh full ITA/MHA generic-host-probe chain, the persistent resident repeat-median selection/measurement/refresh/completion chain, the paged-attention/KV-cache scale-up and repeat-median chain, the config-generation validation breadth and shape-breadth definition, dry-run, execution, result, review, and refresh chain, and the resident overhead breakdown plus persistent resident ABI shape/phase sweep definition, workflow, measurement, review, public refresh, completion, next-measurement selection, and paged-attention/KV-cache continuation definition, dry-run result, dry-run review, measurement result, measurement review, public refresh, externalization completion, next-measurement selection, continuation repeat-median definition, single-state repeated-launch isolation measurement result and review, launch/orchestration cleanup definition, cleanup surface inspection, and repeat-median summary helper cleanup implementation and review, and next-goal selection, and paged-attention/KV-cache follow-up definition, dry-run, measurement, measurement review, public refresh, and externalization completion; these are also available through the `config/scaling_gates` compatibility symlink. |
| Reproduction tools | `src/tools/run_results_reproduction.py`, `src/tools/results_reproduction.py`, `src/tools/run_hybrid_benchmark.py`, `src/tools/hybrid_benchmark.py`, `src/tools/run_hybrid_template.py` | Public CLI entrypoints and shared logic needed to regenerate evidence. |
| Target templates | `config/slice_launch_templates/tlul_fifo_sync.json`, `config/slice_launch_templates/tlul_lc_gate.json`, `config/slice_launch_templates/tlul_adapter_host.json`, `config/slice_launch_templates/nvdla_cmac_core_mac.json`, `config/slice_launch_templates/pulp_ita_dotp.json`, `config/slice_launch_templates/pulp_ita_softmax_top.json`, `config/slice_launch_templates/pulp_ita_mha.json`, `config/slice_launch_templates/pulp_paged_kv_cache_large.json`, `config/slice_launch_templates/pulp_paged_attention_kv_score.json`, `config/slice_launch_templates/mobile_vit_cpu_kick_rtl_proxy.json` | Supported representative workload templates and the tracked config-generation validation breadth set. |
| Contract tests | `tests/contract/test_full_ita_mha_larger_paged_kv_next.py`, `tests/contract/test_hybrid_verilator_like_cli.py` | Public pack, wrapper summary, CLI, and local-path policy checks. |
| Generated review evidence | `reports/results_reproduction_median_summary.json`, `reports/persistent_resident_state_abi_probe_summary.json`, `reports/persistent_resident_state_abi_repeat_median_summary.json`, `reports/persistent_resident_state_abi_shape_phase_sweep_summary.json`, `reports/paged_attention_kv_cache_repeat_median_summary.json`, `reports/mobile_vit_hybrid_128_summary.json`, `reports/tlul_fifo_sync_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/tlul_lc_gate_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/tlul_adapter_host_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/nvdla_cmac_core_mac_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/nvdla_cmac_core_mac_cpu_vs_hybrid_8x1_coverage_output_compare.json`, `reports/nvdla_cmac_core_mac_cpu_vs_hybrid_8x4_coverage_output_compare.json`, `reports/pulp_ita_dotp_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_ita_dotp_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_ita_dotp_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_ita_softmax_top_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_ita_softmax_top_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_ita_softmax_top_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_128x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x128_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_256x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x256_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_512x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x128_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1024x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x256_coverage_output_compare.json`, `reports/hybrid_benchmark_*.json` | Optional evidence snapshots for review; regenerate from documented commands when absent. |

The public archive dry-run also includes the paged-attention/KV-cache next-shapes definition, dry-run, dry-run review, measurement, measurement review, public-results refresh, externalization completion, next-measurement selection, and repeat-median definition gates, plus the four generated next-shapes compare reports as evidence snapshots only. It now includes `records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json`, `records/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_public_pack_refresh_gate.json`, `records/scaling_gates/config_generation_validation_additional_targets_gate.json`, `records/scaling_gates/config_generation_validation_additional_targets_dry_run_gate.json`, `records/scaling_gates/config_generation_validation_additional_targets_dry_run_review_gate.json`, `records/scaling_gates/config_generation_validation_additional_targets_execution_gate.json`, `records/scaling_gates/config_generation_validation_additional_targets_execution_result_gate.json`, `records/scaling_gates/config_generation_validation_additional_targets_execution_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_additional_targets_execution_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_additional_targets_execution_gate.json`, `records/scaling_gates/tlul_template_schema_normalization_gate.json`, `records/scaling_gates/tlul_template_schema_normalization_implementation_gate.json`, `records/scaling_gates/tlul_template_schema_normalization_implementation_review_gate.json`, `records/scaling_gates/tlul_template_schema_normalization_execution_gate.json`, `records/scaling_gates/tlul_template_schema_normalization_execution_result_gate.json`, `records/scaling_gates/tlul_template_schema_normalization_execution_review_gate.json`, `records/scaling_gates/tlul_template_schema_normalization_breadth_gate.json`, `reports/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json`, `reports/paged_kv_next_shapes_repeat_pulp_paged_kv_cache_large_1024x1_median.json`, `reports/paged_kv_next_shapes_repeat_pulp_paged_kv_cache_large_1x256_median.json`, `reports/paged_kv_next_shapes_repeat_pulp_paged_attention_kv_score_256x1_median.json`, and `reports/paged_kv_next_shapes_repeat_pulp_paged_attention_kv_score_1x256_median.json` as generated repeat-median evidence snapshots only.

The paged-attention/KV-cache scale-up follow-up public refresh is `records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_followup_gate.json`. It keeps the reviewed repeat-count `3` continuation and next-shapes summaries in the public pack, with all eight representative cases passing `coverage_output_equivalence` and mismatch count `0`; it does not add a new measurement, runtime/ABI change, production serving claim, or raw full-state equality claim.

The matching externalization completion is `records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_followup_gate.json`. It closes that publication boundary; the machine-readable open pointer after subsequent gate work is `current_priority` in `config/selection.json` (for example resident execution optimization follow-up measurement).

The current TL-UL schema-normalization breadth public refresh is `records/scaling_gates/tlul_template_schema_normalization_breadth_public_pack_refresh_gate.json`. It closes the reviewed `tlul_sink`, `tlul_request_loopback`, and `tlul_adapter_host` `1x1` build/run/compare result into the public pack: all three selected `coverage_output_equivalence` policies pass with mismatch count `0` over `29` words / `116` bytes. The metadata matrix is defined in `records/scaling_gates/tlul_legacy_clock_reset_metadata_matrix_gate.json` for `tlul_fifo_sync`, `tlul_sink`, `tlul_request_loopback`, and `tlul_adapter_host`; `records/scaling_gates/public_results_packaging_refresh_after_tlul_legacy_clock_reset_metadata_matrix_execution_gate.json` closes the reviewed four-target non-dry-run `1x1` build/run/compare result into the public pack boundary, and `records/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_legacy_clock_reset_metadata_matrix_execution_gate.json` closes the externalization boundary. `records/scaling_gates/next_measurement_selection_after_tlul_legacy_clock_reset_metadata_matrix_public_pack_refresh_gate.json` selects `tlul_template_schema_normalization_more_breadth` next, `records/scaling_gates/tlul_template_schema_normalization_more_breadth_gate.json` defines the next dry-run boundary for `tlul_socket_m1`, `tlul_socket_1n`, `tlul_adapter_reg`, and `tlul_adapter_sram`, `records/scaling_gates/tlul_template_schema_normalization_more_breadth_dry_run_gate.json` records all four dry-run command plans exiting with code `0`, `records/scaling_gates/tlul_template_schema_normalization_more_breadth_dry_run_review_gate.json` accepts the dry-run boundary, `records/scaling_gates/tlul_template_schema_normalization_more_breadth_execution_gate.json` defines the matching non-dry-run `1x1` build/run/compare boundary, `records/scaling_gates/tlul_template_schema_normalization_more_breadth_execution_result_gate.json` records all four non-dry-run results passing `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes per target, `records/scaling_gates/tlul_template_schema_normalization_more_breadth_execution_review_gate.json` accepts the result, `records/scaling_gates/public_results_packaging_refresh_after_tlul_template_schema_normalization_more_breadth_execution_gate.json` keeps the reviewed evidence in the public pack boundary, and `records/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_template_schema_normalization_more_breadth_execution_gate.json` closes the externalization boundary. `records/scaling_gates/next_measurement_selection_after_tlul_template_schema_normalization_more_breadth_public_pack_refresh_gate.json` selects `tlul_template_schema_normalization_even_more_breadth` next, `records/scaling_gates/tlul_template_schema_normalization_even_more_breadth_gate.json` defines the next dry-run boundary for `tlul_lc_gate`, `tlul_err_resp`, `tlul_err`, and `tlul_cmd_intg_chk`, `records/scaling_gates/tlul_template_schema_normalization_even_more_breadth_dry_run_gate.json` records all four dry-run command plans exiting with code `0`, `records/scaling_gates/tlul_template_schema_normalization_even_more_breadth_dry_run_review_gate.json` accepts the dry-run boundary, `records/scaling_gates/tlul_template_schema_normalization_even_more_breadth_execution_gate.json` defines the matching non-dry-run execution boundary, `records/scaling_gates/tlul_template_schema_normalization_even_more_breadth_execution_result_gate.json` records all four non-dry-run commands passing `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes per target, and `records/scaling_gates/tlul_template_schema_normalization_even_more_breadth_execution_review_gate.json` accepts the scoped correctness result, and `records/scaling_gates/public_results_packaging_refresh_after_tlul_template_schema_normalization_even_more_breadth_execution_gate.json` keeps that reviewed evidence in the public pack boundary, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_template_schema_normalization_even_more_breadth_execution_gate.json` closes the externalization boundary, and `records/scaling_gates/next_measurement_selection_after_tlul_template_schema_normalization_even_more_breadth_public_pack_refresh_gate.json` selects `config_generation_validation_followup`. `records/scaling_gates/config_generation_validation_followup_gate.json` defines the four tracked follow-up templates, `records/scaling_gates/config_generation_validation_followup_dry_run_gate.json` records all four dry-run command plans exiting with code `0`, `records/scaling_gates/config_generation_validation_followup_dry_run_review_gate.json` accepts the command-plan boundary, `records/scaling_gates/config_generation_validation_followup_execution_gate.json` defines the matching non-dry-run boundary, and `records/scaling_gates/config_generation_validation_followup_execution_result_gate.json` records all four non-dry-run commands passing `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes per target, and `records/scaling_gates/config_generation_validation_followup_execution_review_gate.json` accepts that scoped correctness result. `records/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_followup_execution_gate.json` keeps the reviewed four-target evidence in the public pack boundary. `records/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_followup_execution_gate.json` closes that publication boundary. `records/scaling_gates/tlul_template_schema_metadata_invariant_review_gate.json`, `records/scaling_gates/tlul_template_schema_metadata_invariant_review_dry_run_gate.json`, `records/scaling_gates/tlul_template_schema_metadata_invariant_review_dry_run_review_gate.json`, `records/scaling_gates/tlul_template_schema_metadata_invariant_execution_gate.json`, `records/scaling_gates/tlul_template_schema_metadata_invariant_execution_result_gate.json`, `records/scaling_gates/tlul_template_schema_metadata_invariant_execution_review_gate.json`, and `records/scaling_gates/public_results_packaging_refresh_after_tlul_template_schema_metadata_invariant_execution_gate.json`, and `records/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_template_schema_metadata_invariant_execution_gate.json` carry the later TL-UL metadata-invariant boundary; all four tracked `1x1` commands pass `coverage_output_equivalence` with mismatch count `0`, and generated compare reports remain regenerable evidence only. This is scoped correctness evidence only, not timing, speedup, raw full-state equality, universal legacy-template validation, or production serving evidence.
| Non-pack outputs | `artifacts/` raw dumps and build trees | Reproducible local outputs; do not treat as canonical pack content. |

Public archive dry-run:

This section is the scoped `public_pack_archive_ready` task inside the current public benchmark pack externalization objective.

Use this command to print the archive include/exclude plan without creating an archive file:

```bash
python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run
```

The archive dry-run is intentionally non-writing. It lists the same source-of-truth files, gate/audit records, tools, templates, tests, and optional generated evidence snapshots as the public pack manifest. It also prints the non-executed command `tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>`. Archive files, if created outside this workflow, are generated outputs and must not become source of truth.

Public reproduction smoke:

Run these commands first when checking the public pack from a fresh checkout. They are dry-run commands, so they validate the public CLI surface and command expansion without requiring Verilator/CUDA execution, generated object directories, or ImageNet data.

```bash
python3 src/tools/run_results_reproduction.py --dry-run
python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi-shape-phase-sweep --dry-run
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/tlul_fifo_sync.json --shape 1x1 --dry-run
```

Passing this smoke set means the public commands are parseable and expand to the expected workflow. It does not prove correctness or timing; those claims require the generated evidence reports listed below.

## Public Release Checklist

This section is the scoped `public_release_checklist_ready` task inside the current public benchmark pack externalization objective.

Before publishing or handing off the benchmark pack, verify:

| Check | How to verify | Required result |
| --- | --- | --- |
| Source-of-truth alignment | Inspect `README.md`, `config/selection.json`, `docs/status.md`, and `docs/roadmap.md`. | All list the same `current_priority` and `current_priority_source_artifact` as `config/selection.json` (see **追跡タスク** in `docs/roadmap.md` / `docs/status.md` when the chain moves). |
| Reader guide and boundaries | Inspect `docs/results.md`. | It includes `How To Read This Pack`, `External pack boundary`, `Prerequisites by path`, `Public pack manifest`, and `Public reproduction smoke`. |
| Local path hygiene | Search public docs, gates, and wrapper summaries for local absolute paths. | No machine-local absolute path prefixes are exposed. |
| Smoke commands | Run the public reproduction smoke commands above. | All commands exit successfully and do not write benchmark evidence. |
| Archive dry-run | Run `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run`. | The command prints include/exclude paths and does not create an archive. |
| Evidence claims | Inspect `docs/results.md` and `reports/hybrid_benchmark_*.json`. | Correctness claims are scoped to `coverage_output_equivalence`; `existing_evidence` is not presented as fresh execution. |
| Non-claims | Inspect `docs/results.md:Non-Claims`. | Production serving, raw full-state equality, RTL logits/ImageNet accuracy, and paper-grade confidence are not claimed. |
| Contract tests | Run `python3 -m unittest discover -s tests/contract -q`. | All contract tests pass, with expected skips only. |

Externalization readiness audit:

`config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`

The audit records the minimum review surfaces, smoke commands, release checks, evidence policy, and persistent resident repeat-median refresh for handing this pack to an external reader. Its `ready_for_external_review` status means the pack is organized for review; it is not a new measurement result and does not strengthen the timing or correctness claims beyond the referenced evidence.

## Correctness Condition

The accepted correctness policy is:

```text
coverage_output_equivalence
```

The comparison target is the declared output word set, not raw Verilator state. Raw state may differ because host-only Verilator internals, scheduler state, and pointer-like fields are not stable CPU-vs-GPU comparison targets.

For GPU execution initialized from a CPU state image, host-only internals must be sanitized before upload.

Representative compare evidence:

| Workload | Shape | Compare report | Result |
| --- | --- | --- | --- |
| Full ITA/MHA | `1x1` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA fresh generic-host-probe | `32x1` | `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA fresh generic-host-probe | `1x32` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA | `64x1` | `reports/pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA | `1x64` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA resident | `1x64` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x64_resident_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA resident batch | `32x64` | `reports/pulp_ita_mha_cpu_vs_hybrid_32x64_resident_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA persistent resident ABI | `16x64..16x256` | `reports/persistent_resident_state_abi_probe_summary.json` | pass, mismatch `0` |
| Paged KV-cache large | `256x1` | `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json` | pass, mismatch `0` |
| Paged KV-cache large | `1x64` | `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json` | pass, mismatch `0` |
| Paged KV-cache large next-shapes | `1024x1` | `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1024x1_coverage_output_compare.json` | pass, mismatch `0` |
| Paged KV-cache large next-shapes | `1x256` | `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x256_coverage_output_compare.json` | pass, mismatch `0` |
| Paged-attention KV score | `64x1` | `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json` | pass, mismatch `0` |
| Paged-attention KV score | `1x64` | `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json` | pass, mismatch `0` |
| Paged-attention KV score next-shapes | `256x1` | `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_256x1_coverage_output_compare.json` | pass, mismatch `0` |
| Paged-attention KV score next-shapes | `1x256` | `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x256_coverage_output_compare.json` | pass, mismatch `0` |
| MobileViT CPU-kick RTL proxy | `cfg_batch_length=128` | `reports/mobile_vit_cpu_kick_rtl_proxy_imagenet_batch1_128_cpu_vs_hybrid_1x1_coverage_output_compare.json` | pass, mismatch `0` |

For the paged KV-cache and paged-attention KV-score scale-up rows, correctness is based on `selected_acceptance_policy.passed` and `coverage_output_policy.mismatch_count == 0`. Top-level raw/full-state `match` is not the acceptance target and may be false; raw/full-state mismatch is diagnostic information only. These four rows are correctness evidence, not timing or speedup evidence.

## Performance Summary

Paged-attention/KV-cache scale-up single-run timing:

| Workload | Shape | Interpretation | CPU elapsed ms | Hybrid wall ms | GPU kernel total ms | CPU / hybrid wall | Evidence |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Paged KV-cache large | `256x1` | state-parallel | `599.228` | `1.266` | `1.233920` | `473.32385466034754x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |
| Paged KV-cache large | `1x64` | single-state repeated | `2.93242` | `1.907` | `1.878016` | `1.5377136864184584x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |
| Paged-attention KV score | `64x1` | state-parallel attention-score proxy | `137.923` | `1.666` | `1.635328` | `82.78691476590637x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |
| Paged-attention KV score | `1x64` | single-state repeated attention-score proxy | `2.69249` | `1.404` | `1.300480` | `1.9177279202279203x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |

This is single-run timing from generated reports for the already reviewed four-shape measurement set. It is not repeat-median timing or production LLM-serving throughput evidence.

Paged-attention/KV-cache repeat-median timing, generated with `python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3`:

| Workload | Shape | Interpretation | CPU elapsed ms median | Hybrid wall ms median | GPU kernel total ms median | CPU / hybrid wall median | Evidence |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Paged KV-cache large | `256x1` | state-parallel KV-cache | `613.931` | `1.259` | `1.223680` | `487.6338363780779x` | `reports/paged_kv_repeat_pulp_paged_kv_cache_large_256x1_median.json` |
| Paged KV-cache large | `1x64` | single-state repeated KV-cache | `3.60037` | `1.823` | `1.789952` | `1.9749698299506309x` | `reports/paged_kv_repeat_pulp_paged_kv_cache_large_1x64_median.json` |
| Paged-attention KV score | `64x1` | state-parallel attention-score proxy | `145.936` | `1.068` | `1.038336` | `136.6441947565543x` | `reports/paged_kv_repeat_pulp_paged_attention_kv_score_64x1_median.json` |
| Paged-attention KV score | `1x64` | single-state repeated attention-score proxy | `3.16693` | `1.601` | `1.561600` | `1.978094940662086x` | `reports/paged_kv_repeat_pulp_paged_attention_kv_score_1x64_median.json` |

All four paged-attention/KV-cache repeat-median workloads passed coverage-output equivalence with mismatch count `0`. The aggregate report is `reports/paged_attention_kv_cache_repeat_median_summary.json`. This is repeat-count `3` timing evidence for scoped RTL harnesses, not production LLM-serving throughput.

Review gate: `config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json` accepts this scoped result for the public pack and selects `define_public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median` next. Public refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json` closes the repeat-median evidence into this public results pack. Completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json` closes the publication boundary before selecting the next measurement. These gates explicitly do not claim paper-grade statistical confidence, production paged attention, production KV-cache memory hierarchy, model-level Transformer inference, raw full-state equality, or production LLM-serving throughput.

Next-selection gate: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate.json` selects `config_generation_validation_breadth` after the repeat-median public pack is closed. This is selection-only and does not add a measurement, runtime/ABI change, workload promotion, or production serving claim.

Config-generation validation breadth gate: `config/scaling_gates/config_generation_validation_breadth_gate.json` defines the tracked template set for generated config and generic host-probe metadata validation: NVDLA `cmac_core_mac`, ITA `dotp`, ITA `softmax_top`, ITA `mha`, paged-attention KV-score, and larger paged KV-cache. This is definition-only; MobileViT, Ibex, quantized KV-cache, and untracked candidate overlays are deferred.

Config-generation validation breadth dry-run gate: `config/scaling_gates/config_generation_validation_breadth_dry_run_gate.json` records the six tracked `1x1 --dry-run` command plans. All exited with code `0`, emitted `src/tools/build_host_probe.py`, and preserved `coverage_output_equivalence` compare plans. This remains command-plan evidence only, not fresh build/run/compare measurement evidence.

Config-generation validation breadth dry-run review: `config/scaling_gates/config_generation_validation_breadth_dry_run_review_gate.json` accepts the command-plan boundary and selects `define_config_generation_validation_breadth_execution_gate` next. It explicitly does not claim Verilator build success, generic host-probe compile success, hybrid execution, or CPU-vs-hybrid coverage-output equivalence for the six-template breadth set.

Config-generation validation breadth execution boundary: `config/scaling_gates/config_generation_validation_breadth_execution_gate.json` fixes the next real execution set as the same six tracked `1x1` build/run/compare commands. This is still definition-only; real correctness evidence requires the next execution gate to produce compare reports with `coverage_output_equivalence` mismatch count `0`.

Config-generation validation breadth execution result: `config/scaling_gates/config_generation_validation_breadth_execution_result_gate.json` records that all six tracked `1x1` build/run/compare commands passed `coverage-output equivalence` with mismatch count `0`. This validates the generated config and generic host-probe path across the selected breadth set, but it is not timing or speedup evidence and does not claim raw full-state equality.

Config-generation validation breadth execution review: `config/scaling_gates/config_generation_validation_breadth_execution_review_gate.json` accepts the six-template correctness result and selects a public-results packaging refresh next. This keeps generated reports and artifacts as evidence only and does not add timing, speedup, runtime/ABI, new-workload, or production serving claims.

Config-generation validation breadth public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate.json` keeps the reviewed six-template `1x1` correctness result in the public pack. It includes the breadth definition, dry-run, execution, result, and review gates plus the six tracked launch templates, while keeping generated reports non-canonical and avoiding timing, speedup, runtime/ABI, new-workload, raw full-state equality, and production serving claims.

Public benchmark pack externalization completion after config-generation validation breadth: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate.json` closes the publication boundary after the config-generation validation breadth refresh. It is completion-only packaging work and selects `select_next_measurement_after_config_generation_validation_breadth_public_pack_refresh` next.

Next measurement selection after config-generation validation breadth public refresh: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_breadth_public_pack_refresh_gate.json` selected the shape-breadth definition work. Config-generation validation shape breadth definition: `config/scaling_gates/config_generation_validation_shape_breadth_gate.json` fixes the non-`1x1` tracked-template dry-run set. Shape-breadth dry-run result: `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_gate.json` records 12 dry-run command plans with exit code `0`. Shape-breadth dry-run review: `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_review_gate.json` accepts that result. Shape-breadth execution definition: `config/scaling_gates/config_generation_validation_shape_breadth_execution_gate.json` fixes 12 non-dry-run build/run/compare commands using `src/tools/build_host_probe.py` and `coverage_output_equivalence`. Shape-breadth execution result: `config/scaling_gates/config_generation_validation_shape_breadth_execution_result_gate.json` records all 12 commands passing `coverage_output_equivalence` with mismatch count `0`. Shape-breadth execution review: `config/scaling_gates/config_generation_validation_shape_breadth_execution_review_gate.json` accepts that result and selects a public-results packaging refresh next. Shape-breadth public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate.json` keeps the reviewed 12-command non-`1x1` correctness result in the public pack. Public benchmark pack externalization completion after config-generation validation shape breadth: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution_gate.json` closes the publication boundary. Next measurement selection after config-generation validation shape breadth public refresh: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_shape_breadth_public_pack_refresh_gate.json` selects resident execution overhead breakdown. Resident execution overhead breakdown definition: `config/scaling_gates/resident_execution_overhead_breakdown_gate.json` fixes the existing-evidence analysis boundary. Resident execution overhead breakdown analysis: `config/scaling_gates/resident_execution_overhead_breakdown_analysis_gate.json` records existing-evidence-only wall-minus-kernel residuals. Resident execution overhead runtime-boundary review: `config/scaling_gates/resident_execution_overhead_runtime_boundary_review_gate.json` selects persistent resident ABI shape/phase sweep next. Persistent resident ABI shape/phase sweep definition: `config/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_gate.json` fixes the four-case repeat-median matrix. Persistent resident ABI shape/phase sweep workflow: `config/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_workflow_gate.json` implements `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi-shape-phase-sweep --dry-run`, distinct per-case reports, and `reports/persistent_resident_state_abi_shape_phase_sweep_summary.json`. Persistent resident ABI shape/phase sweep measurement: `config/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_measurement_gate.json` records all four cases passing `coverage_output_equivalence` with mismatch count `0`; median hybrid wall is `3.036 ms`, `5.646 ms`, `8.367 ms`, and `5.244 ms` for `16x64_p2_r3`, `16x64_p4_r3`, `16x128_p4_r3`, and `32x64_p4_r3` respectively. Persistent resident ABI shape/phase sweep measurement review: `config/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_measurement_review_gate.json` accepts this result. Persistent resident ABI shape/phase sweep public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_state_abi_shape_phase_sweep_gate.json` keeps the reviewed four-case evidence in this public pack. Public benchmark pack externalization completion after persistent resident ABI shape/phase sweep: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_persistent_resident_state_abi_shape_phase_sweep_gate.json` closes the publication boundary. Next measurement selection after persistent resident ABI shape/phase sweep public refresh: `config/scaling_gates/next_measurement_selection_after_persistent_resident_state_abi_shape_phase_sweep_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_continuation_gate` next. Paged-attention/KV-cache scale-up continuation definition: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_gate.json` fixes tracked `pulp_paged_kv_cache_large` `512x1` and `1x128`, plus tracked `pulp_paged_attention_kv_score` `128x1` and `1x128`. Paged-attention/KV-cache scale-up continuation dry-run: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_dry_run_gate.json` passed 4 dry-run command plans. Paged-attention/KV-cache scale-up continuation dry-run review: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_dry_run_review_gate.json` accepts the dry-run command plan and selects `run_paged_attention_kv_cache_scale_up_continuation_measurement_gate`; no runtime/ABI change, workload import, timing claim, production serving claim, or raw full-state equality claim is added. Paged-attention/KV-cache scale-up continuation measurement: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_measurement_gate.json` records all four non-dry-run build/run/compare commands passing `coverage_output_equivalence` with mismatch count `0` and selects `review_paged_attention_kv_cache_scale_up_continuation_measurement_gate`; raw full-state equality remains out of scope. Paged-attention/KV-cache scale-up continuation measurement review: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_measurement_review_gate.json` accepts the measurement result and selects `define_public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_gate`. Paged-attention/KV-cache scale-up continuation public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_gate.json` keeps the reviewed four-report correctness evidence in the public pack and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh`. Public benchmark pack externalization completion after paged-attention/KV-cache scale-up continuation: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_continuation_gate.json` closes the publication boundary and selects `select_next_measurement_after_paged_attention_kv_cache_scale_up_continuation_public_pack_refresh` next. Next measurement selection after paged-attention/KV-cache scale-up continuation public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_continuation_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_continuation_repeat_median_gate` next. Paged-attention/KV-cache scale-up continuation repeat-median boundary: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_gate.json` fixes the same four continuation shapes, requires repeat count `3`, records the workflow gap, and selects `add_paged_attention_kv_cache_scale_up_continuation_repeat_median_workflow` next. Paged-attention/KV-cache scale-up continuation repeat-median measurement: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_measurement_gate.json` records `reports/paged_attention_kv_cache_scale_up_continuation_repeat_median_summary.json`; all four shapes pass `coverage_output_equivalence` with mismatch count `0`. Paged-attention/KV-cache scale-up continuation repeat-median review: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_review_gate.json` accepts the scoped repeat-count `3` result and selects `define_public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_repeat_median` next. Paged-attention/KV-cache scale-up continuation repeat-median public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_gate.json` keeps the reviewed repeat-count `3` timing evidence in the public pack and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh`. Public benchmark pack externalization completion after paged-attention/KV-cache scale-up continuation repeat-median: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_gate.json` closes the publication boundary and selects `select_next_measurement_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_public_pack_refresh` next. Next measurement selection after paged-attention/KV-cache scale-up continuation repeat-median public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_next_shapes_gate` next. Paged-attention/KV-cache scale-up next-shapes definition: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_gate.json` pins `pulp_paged_kv_cache_large` `1024x1` and `1x256`, plus `pulp_paged_attention_kv_score` `256x1` and `1x256`. Paged-attention/KV-cache scale-up next-shapes dry-run: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_dry_run_gate.json` passed 4 dry-run command plans. Paged-attention/KV-cache scale-up next-shapes dry-run review: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_dry_run_review_gate.json` accepts that command-plan boundary. Paged-attention/KV-cache scale-up next-shapes measurement: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_measurement_gate.json` records all four non-dry-run build/run/compare commands passing `coverage_output_equivalence` with mismatch count `0`. Paged-attention/KV-cache scale-up next-shapes measurement review: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_measurement_review_gate.json` accepts that scoped correctness result and selects a public-results packaging refresh next. Paged-attention/KV-cache scale-up next-shapes public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_next_shapes_gate.json` keeps the reviewed four-report correctness evidence in the public pack and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh` next. Public benchmark pack externalization completion after paged-attention/KV-cache scale-up next-shapes: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_next_shapes_gate.json` closes that publication boundary and selects `select_next_measurement_after_paged_attention_kv_cache_scale_up_next_shapes_public_pack_refresh` next. Next measurement selection after paged-attention/KV-cache scale-up next-shapes public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_next_shapes_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate` next, with repeat count `3` required before timing-stability claims. Paged-attention/KV-cache scale-up next-shapes repeat-median boundary: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json` fixes the same four next-shapes, records the workflow gap, and selects `add_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_workflow` next. Paged-attention/KV-cache scale-up next-shapes repeat-median measurement: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_measurement_gate.json` records `reports/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json`; all four shapes pass `coverage_output_equivalence` with mismatch count `0`; median wall ratios are `1088.195`, `0.907`, `387.388`, and `0.996` for `1024x1`, `1x256`, `256x1`, and `1x256` respectively. This is scoped repeat-count `3` timing evidence only. Paged-attention/KV-cache scale-up next-shapes repeat-median review: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_review_gate.json` accepts the scoped result for public-pack use and selects `define_public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median` next. Paged-attention/KV-cache scale-up next-shapes repeat-median public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json` keeps the reviewed repeat-count `3` timing evidence in the public pack, includes the generated summary plus four median reports as evidence snapshots only, and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh` next. Public benchmark pack externalization completion after paged-attention/KV-cache scale-up next-shapes repeat-median: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json` closes that publication boundary and selects `select_next_measurement_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_public_pack_refresh` next. Next measurement selection after paged-attention/KV-cache scale-up next-shapes repeat-median public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_public_pack_refresh_gate.json` selects `define_config_generation_validation_additional_targets_gate` next, because generated-config validation breadth is the current weakest point.

Repeat-median timing highlights, generated with `python3 src/tools/run_results_reproduction.py --repeat-median 3`:

| Workload | Shape | Interpretation | CPU elapsed ms | Hybrid wall ms | Ratio / improvement | Evidence |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Full ITA/MHA | `64x1` | state-parallel, prefill-like | `177.257` | `1.286` | CPU / hybrid wall `137.84x` | `reports/pulp_ita_mha_64x1_median.json` |
| Full ITA/MHA | `1x64` | single-state repeated, decode-like baseline | `3.03036` | `1.622` | CPU / hybrid wall `1.87x` | `reports/pulp_ita_mha_1x64_median.json` |
| Full ITA/MHA resident | `1x64` | resident decode-like | `3.21449` | `2.020` | wall `0.80x` vs non-resident `1x64` | `reports/pulp_ita_mha_1x64_resident_median.json` |
| Full ITA/MHA resident batch | `32x64` | resident batch decode-like | `72.5432` | `1.918` | wall per-state-step `33.70x` over resident `1x64` | `reports/pulp_ita_mha_32x64_resident_median.json` |
| Paged-attention KV score | `64x1` | state-parallel attention-score proxy | `145.323` | `1.199` | CPU / hybrid wall `121.20x` | `reports/pulp_paged_attention_kv_score_64x1_median.json` |

All five repeat-median workloads passed coverage-output equivalence with mismatch count `0`. The aggregate report is `reports/results_reproduction_median_summary.json`.

Fresh full ITA/MHA generic-host-probe chain:

| Workload | Shape | Interpretation | CPU elapsed ms | Hybrid wall ms | Result | Gate |
| --- | --- | --- | ---: | ---: | --- | --- |
| Full ITA/MHA fresh generic-host-probe | `1x1` | minimal smoke | `2.91612` | `0.891` | pass, mismatch `0` | `config/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json` |
| Full ITA/MHA fresh generic-host-probe | `32x1` | state-parallel | `72.0539` | `0.877` | pass, mismatch `0` | `config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json` |
| Full ITA/MHA fresh generic-host-probe | `1x32` | single-state repeated-step | `2.93625` | `1.453` | pass, mismatch `0` | `config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json` |

This fresh chain is single-run evidence for the generic host-probe path. It is separate from the repeat-median table above and is not a paper-ready statistical benchmark.

Persistent resident ABI probe:

| Workload | Shape | Interpretation | Hybrid wall ms | GPU kernel total ms | Result | Evidence |
| --- | --- | --- | ---: | ---: | --- | --- |
| Full ITA/MHA persistent resident ABI | `16x64..16x256` | one process, same `d_storage` across four cumulative phases | `4.517` | `4.486688` | all phases pass, mismatch `0` | `reports/persistent_resident_state_abi_probe_summary.json` |

Persistent resident ABI repeat-median:

| Workload | Shape | Interpretation | Hybrid wall ms median | GPU kernel total ms median | Per final state-step wall ms median | Result | Evidence |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| Full ITA/MHA persistent resident ABI | `16x64..16x256`, repeat `3` | same existing persistent resident ABI path, no runtime/ABI change | `4.965` | `4.934624` | `0.001212158203125` | all samples pass, mismatch `0` | `reports/persistent_resident_state_abi_repeat_median_summary.json` |

Resident execution overhead breakdown analysis:

| Mode | Source point | Wall ms | GPU kernel ms | Wall minus kernel residual ms | State boundary | Evidence |
| --- | --- | ---: | ---: | ---: | --- | --- |
| resident batch sweep | `16x64` best total wall | `1.736` | `1.665024` | `0.070976` | uploaded init-state per resident workload | `config/scaling_gates/resident_execution_overhead_breakdown_analysis_gate.json` |
| resident batch sweep | `32x64` best per-state-step wall | `2.176` | `2.141184` | `0.034816` | uploaded init-state per resident workload | `config/scaling_gates/resident_execution_overhead_breakdown_analysis_gate.json` |
| file-boundary state reuse | phase 4 `16x256` | `2.344` | `2.302016` | `0.041984` | previous phase GPU dump reloaded through files | `config/scaling_gates/resident_execution_overhead_breakdown_analysis_gate.json` |
| persistent resident ABI repeat-median | `16x64..16x256`, repeat `3` | `4.965` | `4.934624` | `0.030376` | in-process `d_storage` authoritative after phase 1 | `config/scaling_gates/resident_execution_overhead_breakdown_analysis_gate.json` |

These rows are existing-evidence accounting only. They are not apples-to-apples speedup claims across modes, and the wall-minus-kernel residual is not a full profiler attribution.

## MobileViT ImageNet Evidence

MobileViT is included as CPU-kick ImageNet evidence plus a hybrid RTL control-boundary check. The model logits and accuracy are produced by CPU-kick MobileViT inference records; the hybrid RTL proxy verifies the CPU-visible `LOAD_MODEL` / `LOAD_IMAGE` / `KICK_INFER` / `POLL_DONE` boundary with coverage-output equivalence.

| Scope | Images | Accuracy source | Top-1 | Top-5 | CPU-kick events | Hybrid batch | Compare result | Evidence |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| smoke | `2` | CPU-kick predictions | `1.0` | `1.0` | `2` kick / `2` done | `cfg_batch_length=2`, `1` batch | pass, mismatch `0` | `reports/mobile_vit_hybrid_smoke_summary.json` |
| scale-up | `128` | CPU-kick predictions | `0.7734375` | `0.953125` | `128` kick / `128` done | `cfg_batch_length=128`, `1` batch | pass, mismatch `0` | `reports/mobile_vit_hybrid_128_summary.json` |

The `limit 128` run uses the local Hugging Face ImageNet parquet cache:

```bash
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128
```

## Reproduction

The public one-command entrypoint for the representative result set is:

```bash
python3 src/tools/run_results_reproduction.py --dry-run
```

Inspect the command sequence first. For a full run, remove `--dry-run`:

```bash
python3 src/tools/run_results_reproduction.py
```

The command expands into the representative MHA, resident decode, resident batch-decode, and paged-attention KV-score runs used by this document.

For repeat-median timing evidence, use:

```bash
python3 src/tools/run_results_reproduction.py --repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --repeat-median 3
```

For the current paged-attention/KV-cache four-shape repeat-median workflow, use:

```bash
python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3
```

The aggregate report is `reports/paged_attention_kv_cache_repeat_median_summary.json`.

For the paged-attention/KV-cache scale-up continuation four-shape repeat-median workflow, use:

```bash
python3 src/tools/run_results_reproduction.py --paged-kv-continuation-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --paged-kv-continuation-repeat-median 3
```

The aggregate report is `reports/paged_attention_kv_cache_scale_up_continuation_repeat_median_summary.json`.

For persistent resident ABI repeat-median timing evidence, use:

```bash
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3
```

The lower-level template runner remains available for individual slice templates:

```bash
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x1 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 32x1 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x32 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x64 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1 --dry-run --estimate-efficiency
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1 --dry-run --estimate-efficiency-json
```

`--estimate-efficiency` is the operator-facing form: it prints the target, shape, `high` / `medium` / `low` class, reason, and non-claims after the command plan. `--estimate-efficiency-json` prints the same report as JSON for contract tests and automation. If matching CPU and hybrid reports already exist, the estimate includes observed CPU/hybrid wall-time ratio for that exact target and shape; otherwise it remains a shape-based estimate. Equivalence and performance remain separate claims.

The target-oriented benchmark runner provides a shorter Verilator-like interface for supported workloads:

```bash
python3 src/tools/run_hybrid_benchmark.py --list-targets
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --estimate-efficiency
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --estimate-efficiency-json
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --sidecar-gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_paged_kv_cache_large --shape 256x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode resident-state-reuse --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 1x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_paged_kv_cache_large --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_paged_kv_cache_large_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode resident-state-reuse --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode persistent-resident-state-abi --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --summary-from-existing --summary-out reports/hybrid_benchmark_mobile_vit_template_limit128.json
```

Use `--list-targets` to inspect supported target names, aliases, required `--shape` or `--limit` arguments, and supported modes before running a measurement. It is a discovery command only; it does not run benchmarks, write reports, or create measurement evidence.

Use `--estimate-efficiency` on `run_hybrid_benchmark.py` for a short terminal-oriented estimate after the dry-run or execution command list. It prints the speedup class, reason, next action, scoped observed speedup when existing reports are available, and the non-claims that separate performance estimates from CPU/GPU equivalence. Use `--estimate-efficiency-json` when automation needs the same data.

Use `--sidecar-gpu` as the shortest operator-facing spelling for the existing hybrid sidecar GPU flow plus the human-readable efficiency estimate. It is an alias for usability, not a new correctness policy or a stronger speedup claim.

The wrapper now also accepts `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` and compact `--sim-accel-shape <NxS>` as tested compatibility spellings. The intended long-term spelling is a direct Verilator option. `docs/verilator_sidecar_option.md` records the target `verilator --sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` interface and the non-claims that must survive that migration.

Template-target `--preflight` output now includes `sidecar_stage_plan`, a stage-level view of the intended direct-Verilator boundary: Verilator build, host probe build, CPU reference output, GPU artifact build, hybrid sidecar run, and `coverage_output_equivalence` compare. This is still non-executed planning evidence.

`--summary-out` writes a generated unified wrapper summary under `reports/` by default. The schema records target, shape or limit, mode, command list, expected reports, and collected evidence when commands actually execute; dry-run summaries explicitly remain non-evidence.

`--summary-from-existing` writes the same wrapper schema from already generated reports without rerunning benchmark commands. It is useful for publishing the current benchmark pack, but it is not fresh execution evidence by itself.

Wrapper summary schema fields:

```text
schema_version
tool
target
shape
limit
mode
phases
execution_mode
command_count
commands
expected_reports
evidence
non_claims
```

Wrapper summary reports currently published in this benchmark pack:

| Target | Mode | Shape / limit | Execution mode | Summary report | Evidence status |
| --- | --- | --- | --- | --- | --- |
| `pulp_ita_mha` | `template` | `1x1` | `executed` | `reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json` | pass, mismatch `0` |
| `paged_attention_kv_score` | `template` | `1x1` | `executed` | `reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json` | pass, mismatch `0` |
| `pulp_ita_mha` | `resident-state-reuse` | `1x1`, `2` phases | `executed` | `reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json` | pass, mismatch `0` |
| `pulp_ita_mha` | `persistent-resident-state-abi` | `1x1`, `2` phases | `executed` | `reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json` | pass, mismatch `0` |
| `mobile_vit` | `template` | `limit=128` | `existing_evidence` | `reports/hybrid_benchmark_mobile_vit_template_limit128.json` | collected from existing MobileViT limit-128 evidence |

Generated binaries and raw state dumps go under `artifacts/`; generated summaries and comparisons go under `reports/`.

The resident decode batch-parallel measurements were produced from the existing `pulp_ita_mha` Verilator object directory with `run_vl_hybrid.py --resident-steps`, CPU repeat-state dumps, and `compare_vl_hybrid_modes.py --acceptance-policy coverage_output_equivalence`.

The persistent resident ABI probe is reproduced with:

```bash
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --dry-run
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4
```

The MobileViT ImageNet `limit 128` evidence is reproduced with:

```bash
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128
```

## Non-Claims

This repository does not claim:

- not production LLM serving throughput
- not cross-process persistent CUDA state
- not model-level Transformer inference
- not production KV-cache memory hierarchy
- not production paged attention
- not MobileViT numerical inference in RTL
- not ImageNet accuracy from RTL logits
- not full 50k ImageNet hybrid execution
- not quantized model accuracy
- not broad speedup for arbitrary RTL
- not raw full-state equality
- paper-grade statistical confidence beyond repeat-count 3 representative medians

## Source Evidence

Canonical state and completion audit:

- `README.md`
- `config/selection.json`
- `docs/results.md`
- `docs/status.md`
- `docs/roadmap.md`
- `config/scaling_gates/public_results_packaging_gate.json`
- `config/scaling_gates/public_benchmark_pack_goal_completion_audit.json`
- `config/scaling_gates/generic_hybrid_benchmark_cli_gate.json`
- `config/scaling_gates/one_command_reproduction_flow_gate.json`
- `config/scaling_gates/repeat_median_results_reproduction_gate.json`
- `config/scaling_gates/modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json`
- `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`
- `config/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json`
- `config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json`
- `config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json`
- `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`
- `config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json`
- `config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json`
- `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json`
- `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json`
- `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json`
- `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json`
- `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json`
- `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate.json`
- `config/scaling_gates/config_generation_validation_breadth_gate.json`
- `config/scaling_gates/config_generation_validation_breadth_dry_run_gate.json`
- `config/scaling_gates/config_generation_validation_breadth_dry_run_review_gate.json`
- `config/scaling_gates/config_generation_validation_breadth_execution_gate.json`
- `config/scaling_gates/config_generation_validation_breadth_execution_result_gate.json`
- `config/scaling_gates/config_generation_validation_breadth_execution_review_gate.json`
- `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate.json`
- `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate.json`
- `config/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json`
- `config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json`
- `config/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json`
- `config/scaling_gates/mobile_vit_hybrid_imagenet_eval_gate.json`
- `config/scaling_gates/mobile_vit_hybrid_imagenet_limit_128_scaleup_completion_audit.json`

Result summaries:

- `reports/pulp_ita_mha_first_hybrid_benchmark_summary.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`
- `reports/pulp_ita_mha_64x1_1x64_scaling_summary.json`
- `reports/pulp_ita_mha_prefill_decode_split_summary.json`
- `reports/pulp_ita_mha_resident_decode_1x64_summary.json`
- `reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json`
- `reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json`
- `reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json`
- `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json`
- `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json`
- `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`
- `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`
- `reports/results_reproduction_median_summary.json`
- `reports/persistent_resident_state_abi_probe_summary.json`
- `reports/persistent_resident_state_abi_repeat_median_summary.json`
- `reports/pulp_ita_mha_64x1_median.json`
- `reports/pulp_ita_mha_1x64_median.json`
- `reports/pulp_ita_mha_1x64_resident_median.json`
- `reports/pulp_ita_mha_32x64_resident_median.json`
- `reports/pulp_paged_attention_kv_score_64x1_median.json`
- `reports/mobile_vit_hybrid_smoke_summary.json`
- `reports/mobile_vit_hybrid_128_summary.json`
- `reports/mobile_vit_hybrid_128_accuracy.json`
- `reports/mobile_vit_hybrid_128_cpu_kick_predictions.json`
- `reports/mobile_vit_cpu_kick_rtl_proxy_imagenet_batch1_128_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- `reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- `reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json`
- `reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json`
- `reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json`
- `reports/hybrid_benchmark_mobile_vit_template_limit128.json`
