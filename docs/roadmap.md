# Roadmap

## Weakest Point

Hybrid execution is close to a normal Verilator-style flow for generated templates. The remaining weakness is validation breadth: the generic host-probe builder is wired for generated clock/reset metadata, but more real targets should be exercised before treating it as universal.

## Current Frontier

`modern_llm_serving_rtl_hybrid_conditions` is complete for the scoped RTL-harness condition-finding objective. The current work is benchmark-pack maintenance after adding persistent resident ABI evidence.

Current priority:

`define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate`

Current gate:

`config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json`

## Plan

1. Keep active surface compact.
2. Keep `config/selection.json` current-state-only.
3. Keep `config/README.md` as the map for config roles and add/move rules.
4. Keep generated evidence reproducible under `reports/` and build outputs under `artifacts/`, but do not retain them as source of truth.
5. Make hybrid launch as close as possible to Verilator usage.
6. Generate config from target/top/overlay metadata.
7. Keep the public benchmark pack aligned with the latest correctness, timing, and non-claim evidence.
8. Validate generated host-probe metadata across more target shapes.

## Concrete Milestones

Large endpoint:

`Run modern LLM-serving-like RTL workloads through hybrid execution with correctness, speed trends, and reproduction evidence that are easy to regenerate and review.`

The concrete stages are:

1. Standardize execution.
   - Use `src/tools/run_hybrid_benchmark.py <target> --shape/--limit` as the target-oriented entrypoint.
   - Keep `src/tools/run_hybrid_template.py` available for lower-level slice-template runs.
   - Preserve `--dry-run`, `--preflight`, and `--summary-out` so commands can be reviewed before execution.

2. Fix correctness semantics.
   - Use `coverage_output_equivalence` as the accepted CPU vs hybrid policy.
   - Keep output-word selection in gates/manifests, not in generated reports.
   - Treat raw Verilator internal state mismatch as diagnostic unless it affects the declared coverage-output words.

3. Keep LLM-serving-like RTL workload coverage explicit.
   - Full ITA/MHA represents attention-like compute.
   - Paged-attention KV-score and paged KV-cache harnesses represent serving-state access patterns.
   - Prefill/decode split, resident state reuse, and persistent resident ABI represent serving execution modes.
   - MobileViT remains CPU-kick plus RTL control-boundary evidence, not RTL numerical inference.

4. Measure speed trends by shape and launch model.
   - Compare many-state single-launch shapes against single-state repeated-step shapes.
   - Track resident and persistent-resident modes separately from file-boundary state reuse.
   - Report per-state-step timing when it is the meaningful comparison unit.

5. Make evidence reproducible and reviewable.
   - Generated evidence lives under `reports/`; raw/build outputs live under `artifacts/`.
   - Gate/audit records live under `records/scaling_gates/`, with `config/scaling_gates` kept as a compatibility link.
   - Current decisions stay in `docs/status.md`, `docs/roadmap.md`, `config/selection.json`, and `README.md`.

6. Externalize the benchmark pack.
   - Keep `docs/results.md` aligned with current representative evidence.
   - Include reproduction commands, result summaries, non-claims, and the active correctness policy.
   - Use contract tests to pin public CLI/workflow behavior.

Current strongest next stage:

`Run the paged-attention/KV-cache scale-up measurement set after the dry-run boundary passed.`

Candidate-template selection gate:

- `config/scaling_gates/candidate_template_clean_checkout_selection_gate.json`
- selected primary: `NVDLA.nvdla_cmac_core_mac`
- selected secondary: `NVDLA.nvdla_cmac_a2cacc`
- deferred before promotion: PULP ITA / LLM-serving RTL, MobileViT CPU-kick, and Ibex LLM SoC kick
- reason: only the selected NVDLA candidates are clean-checkout-ready in this boundary using tracked `third_party/rtlmeter` plus `src/tools/build_host_probe.py` without adding Makefile host-probe targets

NVDLA minimal build/run/compare gate:

- `config/scaling_gates/nvdla_cmac_core_mac_minimal_build_run_compare_gate.json`
- command: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/nvdla_cmac_core_mac.json --shape 1x1`
- result: Verilator build, generic host-probe build, GPU cubin build, hybrid run, and CPU-vs-hybrid `coverage_output_equivalence` compare pass
- mismatch count: `0`
- non-claim: this is the minimal `1x1` boundary only, not broad speedup or full NVDLA execution

NVDLA template shape expansion gate:

- `config/scaling_gates/nvdla_cmac_core_mac_template_shape_expansion_gate.json`
- result: `8x1`, `32x1`, and `8x4` all pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`
- active seed: `NVDLA.nvdla_cmac_core_mac` remains the only active seed target
- planned shapes: `8x1`, `32x1`, `8x4`
- required boundary: `run_hybrid_template.py` plus `src/tools/build_host_probe.py`; no Makefile host-probe target and no second active seed target
- non-claim: raw full-state equality is false, timing is scoped observed evidence only, and this is not full NVDLA execution
- usability observation: `run_hybrid_template.py` currently rebuilds the generic host probe and forces GPU cubin regeneration on each measured shape

Next workstream review gate:

- `config/scaling_gates/nvdla_shape_expansion_next_workstream_review_gate.json`
- selected next workstream: `ita_dependency_clean_checkout_boundary`
- reason: the same-seed NVDLA `cmac_core_mac` template path has passed its planned shape expansion; the next blocker for the long-term LLM-serving RTL goal is making `third_party/ITA` and `third_party/common_cells` canonical in clean checkout
- deferred alternative: NVDLA `a2cacc` remains the secondary clean-checkout candidate, but it does not remove the ITA/LLM-serving dependency blocker
- non-claim: this is not an ITA build/run/compare result and does not promote a second active seed measurement

ITA dependency clean-checkout boundary gate:

- `config/scaling_gates/ita_dependency_clean_checkout_boundary_gate.json`
- status: `third_party/ITA` and `third_party/common_cells` are canonical gitlink submodules in `.gitmodules`
- pinned commits: ITA `ba96519becce195d64e85eb9a5302e8a1d5487e7`, common_cells `c27bce39ebb2e6bae52f60960814a2afca7bd4cb`
- required before ITA measurement: validate required source paths in a clean-checkout contract, keep repo-specific harnesses under `overlays/ITA`, and select exactly one first ITA seed
- non-claim: this is not an ITA build/run/compare result or approval to recursively import all Bender dependencies

ITA first seed selection after dependency boundary:

- `config/scaling_gates/ita_first_seed_selection_after_dependency_boundary_gate.json`
- selected first ITA active seed: `pulp_ita_dotp`
- selected upstream source: `third_party/ITA/src/ita_dotp.sv`
- selected reason: smallest source-backed ITA attention-score datapath with no local ITA dependency and no external `common_cells` dependency
- weak point: this is less representative than `ita_softmax_top`, full ITA/MHA, paged attention, or KV-cache serving state because it does not exercise softmax/reduction or decode-state behavior
- deferred first alternative: `pulp_ita_softmax_top`, because it pulls `ita_package`, `ita_max_finder`, `ita_register_file_1w_multi_port_read`, `ita_softmax`, `ita_serdiv`, `cf_math_pkg`, `fifo_v3`, and `lzc` into the boundary
- next_task: `implement_pulp_ita_dotp_overlay_template_generic_host_probe_gate`
- required boundary: use `src/tools/build_host_probe.py`; do not add a `src/hybrid/Makefile` host-probe target for the ITA seed
- non-claim: this is a selection-only gate, not an ITA build/run/compare result, speedup result, or correctness result

PULP ITA dotp overlay/template generic host-probe gate:

- `config/scaling_gates/pulp_ita_dotp_overlay_template_generic_host_probe_gate.json`
- promoted source boundary: `overlays/ITA/src/pulp_ita_dotp_gpu_cov_tb.sv`, `overlays/ITA/tests/pulp_ita_dotp_coverage_regions.json`, and `config/slice_launch_templates/pulp_ita_dotp.json`
- template target: `PULP_ITA.pulp_ita_dotp`
- upstream source: `third_party/ITA/src/ita_dotp.sv`
- host-probe builder: `src/tools/build_host_probe.py`
- host-probe clock/reset metadata: `pulp_ita_dotp_gpu_cov_tb__DOT__clk_i` and `pulp_ita_dotp_gpu_cov_tb__DOT__reset_like_w`
- dry-run smoke: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_dotp.json --shape 1x1 --dry-run`
- next_task: `run_pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate`
- non-claim: this is source-boundary promotion only, not a build/run/compare result, speedup result, or correctness result

PULP ITA dotp first generic host-probe build/run/compare gate:

- `config/scaling_gates/pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json`
- command: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_dotp.json --shape 1x1`
- result: Verilator build, generic host-probe build, GPU cubin build, hybrid run, and CPU-vs-hybrid `coverage_output_equivalence` compare pass
- mismatch count: `0`
- compared output: `29` words / `116` bytes
- raw full-state equality: false, with mismatch limited to Verilator-internal fields
- next_task: `run_pulp_ita_dotp_shape_expansion_gate`
- non-claim: this is the minimal `1x1` dotp boundary only, not softmax, full MHA, shape expansion, or broad speedup evidence

PULP ITA dotp shape expansion gate:

- `config/scaling_gates/pulp_ita_dotp_shape_expansion_gate.json`
- commands: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_dotp.json --shape 64x1` and `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_dotp.json --shape 1x64`
- result: both planned shapes pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`
- `64x1`: CPU elapsed `150.04 ms`, hybrid GPU kernel total `1.29024 ms`, hybrid wall `1.321 ms`
- `1x64`: CPU elapsed `3.23146 ms`, hybrid GPU kernel total `1.543168 ms`, hybrid wall `1.600 ms`
- trend: `64x1` state-parallel timing is much more favorable than `1x64` single-state repeated-step timing in this run
- next_task: `review_pulp_ita_dotp_shape_expansion_and_select_softmax_or_hold`
- non-claim: this is scoped dotp timing evidence only, not softmax, full MHA, production LLM-serving throughput, or broad modern-NN speedup

PULP ITA dotp shape expansion review gate:

- `config/scaling_gates/pulp_ita_dotp_shape_expansion_review_gate.json`
- reviewed result: `pulp_ita_dotp` `64x1` and `1x64` both pass `coverage_output_equivalence` with mismatch count `0`
- selected next workstream: `ita_softmax_top_dependency_template_boundary`
- reason: dotp covers attention-score arithmetic, but the modern attention gap now is softmax/reduction behavior
- required next boundary: `pulp_ita_softmax_top_dependency_template_boundary_gate`
- required source boundary: `ita_softmax_top`, `ita_package`, `ita_max_finder`, `ita_register_file_1w_multi_port_read`, `ita_softmax`, `ita_serdiv`, `cf_math_pkg`, `fifo_v3`, and `lzc`
- required execution boundary: use `src/tools/build_host_probe.py`; do not add a `src/hybrid/Makefile` host-probe target and do not recursively import all Bender dependencies
- non-claim: this is a review-only selection, not softmax build/run/compare or speedup evidence

PULP ITA softmax-top dependency/template boundary gate:

- `config/scaling_gates/pulp_ita_softmax_top_dependency_template_boundary_gate.json`
- promoted source boundary: `config/slice_launch_templates/pulp_ita_softmax_top.json`, `overlays/ITA/src/pulp_ita_softmax_top_gpu_cov_tb.sv`, `overlays/ITA/tests/pulp_ita_softmax_top_coverage_regions.json`, and `overlays/ITA/src/pulp_ita_cluster_clock_gating_sim.sv`
- required ITA sources: `ita_package`, `ita_max_finder`, `ita_register_file_1w_multi_port_read`, `ita_softmax`, `ita_serdiv`, and `ita_softmax_top`
- required common_cells sources: `cf_math_pkg`, `lzc`, and `fifo_v3`
- host-probe builder: `src/tools/build_host_probe.py`
- host-probe clock/reset metadata: `pulp_ita_softmax_top_gpu_cov_tb__DOT__clk_i` and `pulp_ita_softmax_top_gpu_cov_tb__DOT__reset_like_w`
- dry-run smoke: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_softmax_top.json --shape 1x1 --dry-run`
- next_task: `run_pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate`
- non-claim: this is source-boundary promotion only, not softmax build/run/compare, correctness, or speedup evidence

Config minimization audit:

- `records/scaling_gates/config_minimal_surface_completion_audit.json`
- active `config/` file count: `146`
- historical gate JSON records under `records/scaling_gates/`: `632`
- compatibility link: `config/scaling_gates -> ../records/scaling_gates`
- generated files under `reports/` and `artifacts/`: reproducible evidence only, never source of truth

## Completed NN Flow

The completed flow is:

1. `neural_network_rtl_paged_kv_cache_large_scaleup_gate.json`
2. `neural_network_rtl_paged_kv_cache_large_review_gate.json`
3. `neural_network_rtl_full_ita_mha_dependency_audit_gate.json`
4. `neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json`
5. `neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json`
6. `neural_network_rtl_paged_attention_kv_score_harness_gate.json`
7. `full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json`
8. `hybrid_verilator_like_config_and_probe_generation_gate.json`
9. `full_mha_hybrid_try_completion_audit.json`
10. `full_mha_scaleup_64x1_1x64_gate.json`
11. `prefill_decode_split_mha_benchmark_gate.json`
12. `resident_decode_optimization_probe_gate.json`
13. `resident_decode_batch_parallel_probe_gate.json`
14. `modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json`
15. `one_command_reproduction_flow_gate.json`
16. `repeat_median_results_reproduction_gate.json`
17. `resident_execution_optimization_next_gate.json`
18. `resident_batch_sweep_measurement_gate.json`
19. `resident_batch_sweep_review_gate.json`
20. `resident_state_reuse_experiment_gate.json`
21. `resident_state_reuse_measurement_gate.json`
22. `resident_state_reuse_review_gate.json`
23. `persistent_resident_state_abi_probe_gate.json`
24. `persistent_resident_state_abi_probe_implementation_gate.json`
25. `persistent_resident_device_handle_storage_gate.json`
26. `persistent_resident_device_handle_storage_review_gate.json`
27. `public_results_packaging_gate.json`
28. `public_benchmark_pack_goal_completion_audit.json`

Evidence summaries:

- `reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json`
- `reports/pulp_ita_mha_first_hybrid_benchmark_summary.json`
- `reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json`
- `reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json`
- `reports/results_reproduction_median_summary.json`
- `reports/resident_batch_sweep_summary.json`
- `reports/resident_state_reuse_experiment_summary.json`
- `reports/persistent_resident_state_abi_probe_summary.json`

External-facing synthesis:

- `docs/results.md`
- `src/tools/run_results_reproduction.py`
- `python3 src/tools/run_results_reproduction.py --repeat-median 3`
- `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4`
- `python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 1x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode resident-state-reuse --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode persistent-resident-state-abi --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --summary-from-existing --summary-out reports/hybrid_benchmark_mobile_vit_template_limit128.json`

## Next Goal

Record the completed persistent resident state ABI repeat-median measurement and select the next measurement boundary:

- gate: `config/scaling_gates/public_results_packaging_gate.json`
- audit: `config/scaling_gates/public_benchmark_pack_goal_completion_audit.json`
- readiness audit: `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`
- externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json`
- next measurement selection gate: `config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`
- next-goal selection gate: `config/scaling_gates/next_measurement_goal_selection_after_public_pack_readiness_gate.json`
- completed measurement goal: `persistent_resident_state_abi_repeat_median`
- completed gate: `persistent_resident_state_abi_repeat_median_measurement_gate`
- dry-run: `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3 --dry-run`
- measured report: `reports/persistent_resident_state_abi_repeat_median_summary.json`
- measured result: all three samples pass coverage-output equivalence, mismatch count `0`
- median hybrid wall: `4.965 ms`
- median GPU kernel total: `4.934624 ms`
- median hybrid wall per final state-step: `0.001212158203125 ms`
- document: `docs/results.md`
- newest evidence: `reports/persistent_resident_state_abi_repeat_median_summary.json`
- latest MobileViT evidence: `reports/mobile_vit_hybrid_128_summary.json`
- generic benchmark CLI gate: `config/scaling_gates/generic_hybrid_benchmark_cli_gate.json`
- generic benchmark summary schema: `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- template wrapper summary smoke: `reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- fresh wrapper summary smoke: `reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json`
- resident wrapper summary smoke: `reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json`
- persistent resident wrapper summary smoke: `reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json`
- MobileViT wrapper summary from existing evidence: `reports/hybrid_benchmark_mobile_vit_template_limit128.json`
- correctness policy: `coverage_output_equivalence`

Long-term goal: keep hybrid execution close to Verilator usage while making LLM-serving-like RTL workload correctness, speed trends, reproduction commands, and non-claims easy to regenerate and review.

Externalization readiness adds:

- a reader guide in `docs/results.md`
- a generated evidence boundary for `reports/` and `artifacts/`
- prerequisites for dry-run, wrapper summaries, persistent resident ABI, and MobileViT
- a public reproduction smoke command set using dry-run only
- a public release checklist for source-of-truth alignment, path hygiene, smoke, evidence scope, non-claims, and tests
- a public archive dry-run that prints package include/exclude paths without creating a source-of-truth archive
- contract tests that pin these public-pack explanations

Current measurement selection result:

- persistent resident state ABI repeat-median was selected and measured because it was the smallest next measurement that improves timing reproducibility for the newest serving-like execution-mode evidence
- defer paged attention / KV-cache scale-up because the public pack already includes larger paged KV-cache, paged-attention KV-score, and repeat-median paged-attention score evidence
- defer additional prefill/decode work until the persistent resident timing reproducibility gap is closed
- keep runtime/ABI changes out of the repeat-median gate
- keep publish-only as available downstream work, not the next engineering measurement gate
- do not change runtime ABI or add a new workload while selecting the next measurement after `persistent_resident_state_abi_repeat_median`

Representative comparisons:

- `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`

Relevant harness strings:

- `overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv`
- `pulp_paged_kv_cache_large_host_probe`
- `tc_sram`

## MobileViT Track

Completed CPU-kick references:

- `phase_11_mobile_vit_cpu_kick_imagenet_accuracy`
- `phase_12_mobile_vit_cpu_kick_rtl_hybrid_boundary`
- `select_mobile_vit_model_and_reference_eval_source: done`
- `define_mobile_vit_cpu_kick_control_contract: done`
- `define_mobile_vit_accuracy_metric_contract: done`
- `define_mobile_vit_reference_inference_contract: done`
- `define_mobile_vit_imagenet_manifest_builder_contract: done`
- `define_mobile_vit_cpu_kick_proxy_contract: done`
- `define_mobile_vit_cpu_kick_inference_contract: done`
- `define_mobile_vit_eval_pipeline_contract: done`
- `define_mobile_vit_goal_audit_contract: done`
- `install_mobile_vit_reference_dependencies_in_artifact_venv: done`
- `run_mobile_vit_reference_smoke: done`
- `provide_imagenet_validation_data_or_approved_scoped_subset_for_real_accuracy: done_full_imagenet_validation`
- `create_imagenet_manifest_or_record_dataset_access_blocker: done_full_imagenet_validation`

Tracked evidence:

- `mobile_vit_cpu_kick_imagenet_accuracy`
- `mobile_vit_cpu_kick_rtl_hybrid_boundary`
- `apple/mobilevit-small`
- `complete_full_imagenet_validation_cpu_kick_accuracy_measured`
- `top-1 0.77022`
- `mobile_vit_cpu_kick_rtl_proxy_host_probe`
- `mobile_vit_hybrid_imagenet_eval_gate`
- `mobile_vit_hybrid_imagenet_eval_completion_audit`
- `mobile_vit_hybrid_imagenet_limit_128_scaleup_completion_audit`
- `hybrid ImageNet eval path complete for a real cached two-image scoped subset and a limit-128 local-cache scale-up; full 50k scale-up remains optional`

## Next Gate

Recommended next gate:

`define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate`

Acceptance criteria:

- review `config/scaling_gates/next_measurement_goal_selection_after_public_pack_readiness_gate.json`
- review `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`
- review `config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json`
- review `config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json`
- review `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`
- review `config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json`
- review `config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`
- review `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json`
- review `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json`
- review `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json`
- review `config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json`
- preserve the measured repeat-median result for the existing `16x64` four-phase path
- preserve `coverage_output_equivalence` as the correctness policy
- keep reports and artifacts as generated evidence, not source of truth
- preserve the passed paged-attention/KV-cache scale-up dry-run record
- preserve the passed paged-attention/KV-cache scale-up measurement record
- verify the four generated compare reports passed `coverage_output_equivalence` with mismatch count `0`
- review `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json`
- review `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json`
- review `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`
- review `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`
- keep the measurement set on tracked `pulp_paged_kv_cache_large` and `pulp_paged_attention_kv_score` templates
- preserve the single-run timing summary for the same four measured shapes before making broader speedup claims
- define a publication-only refresh gate for the reviewed paged-attention/KV-cache correctness and timing evidence
- avoid importing unreviewed candidate overlays, MobileViT, Ibex, or quantized KV-cache files
- keep broad modern-NN, production LLM-serving, and raw full-state equality claims out of the externalization pack

Working tree review boundary:

`next_task: define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate`

Define only the public results packaging refresh after the reviewed paged-attention/KV-cache timing summary. Do not mix in runtime, MobileViT, Ibex, untracked candidate overlays, or new workload execution outputs.

Review/stage boundary:

- `docs/roadmap.md`
- `docs/status.md`
- `records/scaling_gates/ita_first_seed_selection_after_dependency_boundary_gate.json`
- `records/scaling_gates/pulp_ita_dotp_overlay_template_generic_host_probe_gate.json`
- `records/scaling_gates/pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json`
- `records/scaling_gates/pulp_ita_dotp_shape_expansion_gate.json`
- `records/scaling_gates/pulp_ita_dotp_shape_expansion_review_gate.json`
- `records/scaling_gates/pulp_ita_softmax_top_dependency_template_boundary_gate.json`
- `records/scaling_gates/pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.json`
- `records/scaling_gates/pulp_ita_softmax_top_shape_expansion_gate.json`
- `records/scaling_gates/pulp_ita_softmax_top_shape_expansion_review_gate.json`
- `records/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json`
- `records/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json`
- `records/scaling_gates/pulp_ita_mha_shape_expansion_gate.json`
- `records/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json`
- `records/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json`
- `records/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`
- `records/scaling_gates/next_measurement_goal_selection_after_public_pack_readiness_gate.json`
- `docs/results.md`
- `config/slice_launch_templates/pulp_ita_mha.json`
- `overlays/ITA/src/pulp_ita_tc_sram_sim.sv`
- `overlays/ITA/src/pulp_ita_mha_gpu_cov_tb.sv`
- `overlays/ITA/tests/pulp_ita_mha_coverage_regions.json`
- `config/slice_launch_templates/pulp_ita_dotp.json`
- `config/slice_launch_templates/pulp_ita_softmax_top.json`
- `overlays/ITA/src/pulp_ita_dotp_gpu_cov_tb.sv`
- `overlays/ITA/tests/pulp_ita_dotp_coverage_regions.json`
- `overlays/ITA/src/pulp_ita_cluster_clock_gating_sim.sv`
- `overlays/ITA/src/pulp_ita_softmax_top_gpu_cov_tb.sv`
- `overlays/ITA/tests/pulp_ita_softmax_top_coverage_regions.json`
- `records/scaling_gates/ita_dependency_clean_checkout_boundary_gate.json`
- `records/scaling_gates/nvdla_shape_expansion_next_workstream_review_gate.json`
- `records/scaling_gates/candidate_template_clean_checkout_selection_gate.json`
- `records/scaling_gates/nvdla_cmac_core_mac_minimal_build_run_compare_gate.json`
- `records/scaling_gates/nvdla_cmac_core_mac_template_shape_expansion_gate.json`
- `config/slice_launch_templates/nvdla_cmac_core_mac.json`
- `overlays/rtlmeter/designs/NVDLA/src/nvdla_cmac_core_mac_gpu_cov_tb.sv`
- `overlays/rtlmeter/designs/NVDLA/tests/nvdla_cmac_core_mac_coverage_regions.json`
- `src/tools/hybrid_template_runner.py`
- `tests/contract/test_full_ita_mha_larger_paged_kv_next.py`
- `tests/contract/test_hybrid_verilator_like_cli.py`

Exclude from this review boundary:

- `AGENTS.md`
- `src/hybrid/Makefile`
- `third_party/ITA`, `third_party/common_cells`, and `third_party/ibex` edits beyond validating required source paths
- additional NVDLA targets beyond `nvdla_cmac_core_mac`
- `ita_softmax_top`, KV-cache, LLM SoC, and MobileViT candidate templates and overlays
- MobileViT, tiny LLM serving, and LLM SoC CPU-kick tools/tests
- runtime/pass changes already closed by `resident_runtime_contract_completion_boundary`
- generated-config tooling already closed by `verilator_like_hybrid_config_generation_boundary`
- generated output under `reports/`, `artifacts/`, and `work/`

Boundary acceptance:

- candidate selection gate identifies `NVDLA.nvdla_cmac_core_mac` as primary and `NVDLA.nvdla_cmac_a2cacc` as secondary
- minimal build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`
- shape expansion gate records `8x1`, `32x1`, and `8x4` coverage-output pass with mismatch count `0`
- next workstream review selects `ita_dependency_clean_checkout_boundary`
- ITA dependency boundary gate records canonical `.gitmodules` entries and gitlinks for `third_party/ITA` and `third_party/common_cells`
- ITA first seed selection gate selects `pulp_ita_dotp` and defers `pulp_ita_softmax_top`
- `third_party/ITA/src/ita_dotp.sv` is the only required ITA source path for the first selected seed
- PULP ITA dotp overlay/template gate carries `build.host_probe_builder: src/tools/build_host_probe.py`
- dry-run emits `python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_dotp.json`
- PULP ITA dotp first build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`
- PULP ITA dotp first build/run/compare gate records raw full-state equality as false with Verilator-internal-only mismatch
- PULP ITA dotp shape expansion gate records `64x1` and `1x64` coverage-output pass with mismatch count `0`
- PULP ITA dotp shape expansion gate records `64x1` as much more favorable than `1x64` in scoped single-run timing
- PULP ITA dotp shape expansion review gate selects `ita_softmax_top_dependency_template_boundary` next
- PULP ITA dotp shape expansion review gate keeps softmax measurement separate from boundary definition
- PULP ITA softmax-top dependency/template boundary gate carries `build.host_probe_builder: src/tools/build_host_probe.py`
- dry-run emits `python3 src/tools/build_host_probe.py config/slice_launch_templates/pulp_ita_softmax_top.json`
- PULP ITA softmax-top first build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`
- PULP ITA softmax-top first build/run/compare gate records raw full-state equality as false with Verilator-internal-only mismatch
- PULP ITA softmax-top shape expansion gate records `64x1` and `1x64` coverage-output pass with mismatch count `0`
- PULP ITA softmax-top shape expansion gate records `64x1` as much more favorable than `1x64` in scoped single-run timing
- PULP ITA softmax-top shape expansion review gate selects `full_ita_mha_dependency_template_boundary` next
- PULP ITA softmax-top shape expansion review gate keeps full MHA measurement separate from boundary definition
- PULP ITA MHA dependency/template boundary gate carries `build.host_probe_builder: src/tools/build_host_probe.py`
- PULP ITA MHA dependency/template boundary gate keeps first full MHA measurement separate from boundary definition
- PULP ITA MHA first build/run/compare gate records `coverage_output_equivalence` pass with mismatch count `0`
- PULP ITA MHA first build/run/compare gate records raw full-state equality as false with Verilator-internal-only mismatch
- PULP ITA MHA shape expansion gate records `32x1` and `1x32` coverage-output pass with mismatch count `0`
- PULP ITA MHA shape expansion gate records `32x1` as much more favorable than `1x32` in scoped single-run timing
- the NVDLA `cmac_core_mac` template references only present source files
- the template carries `build.host_probe_builder: src/tools/build_host_probe.py`
- `run_hybrid_template.py` passes template `verilator_defines` into the Verilator command
- the overlay and coverage manifest are tracked source files
- `src/hybrid/Makefile` remains free of generated NVDLA host-probe targets
- no generated output is introduced as source of truth
- `python3 -m unittest tests.contract.test_resident_runtime_contract -q` passes
- `python3 -m unittest discover -s tests/contract -q` passes

## Archive Boundary

Historical gate details remain in `records/scaling_gates/`, with `config/scaling_gates` kept as a compatibility link. Generated summaries are reproducible under `reports/`, and build/raw outputs are reproducible under `artifacts/`; both directories may contain local generated evidence. They should not be copied back into `selection.json`, `README.md`, or this roadmap as canonical decisions.
