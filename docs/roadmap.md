# Roadmap

## Weakest Point

Hybrid execution is close to a normal Verilator-style flow for generated templates. The remaining weakness is validation breadth: the generic host-probe builder is wired for generated clock/reset metadata, but more real targets should be exercised before treating it as universal.

## Current Frontier

`modern_llm_serving_rtl_hybrid_conditions` is complete for the scoped RTL-harness condition-finding objective. The current work is benchmark-pack maintenance after adding persistent resident ABI evidence.

Current priority:

`public_benchmark_pack_externalization_ready`

Current gate:

`config/scaling_gates/public_results_packaging_gate.json`

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

`Hold the refreshed public benchmark pack for review after publishing the wrapper summary schema, then choose whether to externalize results or open a new measurement goal.`

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

Make the refreshed public benchmark pack externalization-ready:

- gate: `config/scaling_gates/public_results_packaging_gate.json`
- audit: `config/scaling_gates/public_benchmark_pack_goal_completion_audit.json`
- document: `docs/results.md`
- newest evidence: `reports/persistent_resident_state_abi_probe_summary.json`
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

`legacy_cpu_seed_template_retirement_boundary`

Acceptance criteria:

- remove legacy CPU seed launch templates that are no longer active targets
- keep VeeR EL2 and XuanTie E902 represented only in `config/archived_targets.json`
- verify active target metadata does not reference retired template paths or retired target names
- keep runtime/pass changes, submodule imports, NN target additions, and MobileViT tooling out of this review boundary

Working tree review boundary:

`next_task: legacy_cpu_seed_template_retirement_boundary`

Review only the retirement of the old CPU seed launch-template files. The goal is to keep the active `config/slice_launch_templates/` surface aligned with `config/targets.json` while preserving historical context in `config/archived_targets.json`.

Review/stage boundary:

- `docs/roadmap.md`
- remove `config/slice_launch_templates/veer_el2.json`
- remove `config/slice_launch_templates/xuantie_e902.json`
- `tests/contract/test_resident_runtime_contract.py`

Exclude from this review boundary:

- `third_party/ITA`, `third_party/common_cells`, and `third_party/ibex`
- new NN target templates such as NVDLA, ITA, KV-cache, and LLM SoC kick templates
- non-rtlmeter overlays such as ITA, ibex, MobileViT, and NVDLA
- runtime/pass implementation changes under `src/hybrid/` and `src/passes/`
- broad existing-runner changes such as `build_vl_gpu.py`, `run_vl_hybrid.py`, `compare_vl_hybrid_modes.py`, and `gen_vl_gpu_kernel.py`
- generated-config tooling already closed by `verilator_like_hybrid_config_generation_boundary`
- generated output under `reports/`, `artifacts/`, and `work/`

Boundary acceptance:

- `config/slice_launch_templates/veer_el2.json` is absent
- `config/slice_launch_templates/xuantie_e902.json` is absent
- `config/targets.json` and `config/selection.json` do not reference `veer_el2`, `xuantie_e902`, or their retired launch-template paths
- `config/archived_targets.json` remains the place that records why VeeR EL2 and XuanTie E902 are archived
- `python3 -m unittest tests.contract.test_resident_runtime_contract -q` passes
- `python3 -m unittest discover -s tests/contract -q` passes

## Archive Boundary

Historical gate details remain in `records/scaling_gates/`, with `config/scaling_gates` kept as a compatibility link. Generated summaries are reproducible under `reports/`, and build/raw outputs are reproducible under `artifacts/`; both directories may contain local generated evidence. They should not be copied back into `selection.json`, `README.md`, or this roadmap as canonical decisions.
