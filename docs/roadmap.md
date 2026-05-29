# Roadmap

## Weakest Point

Hybrid execution is close to a normal Verilator-style flow for generated templates, but "native" is still only a prototype boundary. The commit split is complete and the overlay patch descriptor/apply-check review is accepted; the weak point is now adding only the descriptor and patch files without confusing them with the existing sidecar shim, tracked-template registry, arbitrary filelist planning, dependency inference, automatic allocation, or a landed Verilator parser patch.

## Current Frontier

`modern_llm_serving_rtl_hybrid_conditions` is complete for the scoped RTL-harness condition-finding objective. The current work is implementing the smallest overlay patch descriptor/apply-check payload before any native parser support claim.

Current priority:

`implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate`

Current gate:

`config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json`

Current alignment check: `config/selection.json`, `docs/status.md`, and this roadmap agree on the **current_priority** and **current_priority_source_artifact** strings above. Historical completion gates may still list older `next_task` labels; treat `selection.json` as authoritative for the open pointer.

## 追跡タスク (Tracked tasks)

1. **Native option parser overlay patch descriptor/apply-check implementation**: Add only the accepted descriptor and patch files, then validate descriptor JSON and `git apply --check` against the pinned Verilator commit.
2. **Simple verification doc**: Keep `docs/migration_notes.md` “Gap from a minimal verification setup” accurate when entrypoints or prerequisites change.
3. **Gate chain hygiene**: When advancing `current_priority`, update `completed_goal_evidence` in `config/selection_extensions.json` only with tracked records; keep linked source-of-truth files clone-reproducible.

**Recommended cleanup order** (deeper refactors): see **「整理の順序（推奨）」** in `docs/migration_notes.md`.

## Plan

1. Keep active surface compact.
2. Keep `config/selection.json` compact (core pointer) and historical maps in `config/selection_extensions.json`; merge via `src/tools/selection_state.py` when tooling needs the full selection.
3. Keep `config/README.md` as the map for config roles and add/move rules.
4. Keep generated evidence reproducible under `reports/` and build outputs under `artifacts/`, but do not retain them as source of truth.
5. Make hybrid launch as close as possible to Verilator usage.
6. Generate config from target/top/overlay metadata.
7. Keep the public benchmark pack aligned with the latest correctness, timing, and non-claim evidence.
8. Validate generated host-probe metadata across more target shapes.
9. Keep commits review-sized and let `.githooks/pre-commit` reject oversized staged files, too many staged files, oversized script deltas, oversized total script line counts, too many new scripts, and non-shrinking oversized contract tests before they enter normal history.

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

Implement the native Verilator option parser overlay patch descriptor/apply-check payload after accepting its boundary.

Parser boundary definition:

- source gate: `config/scaling_gates/define_verilator_native_option_parser_source_patch_boundary_gate.json`
- source review gate: `config/scaling_gates/review_verilator_native_option_parser_source_patch_boundary_gate.json`
- descriptor/apply-check definition gate: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json`
- descriptor/apply-check review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json`
- selected next gate: `implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate`
- scope: overlay patch descriptor/apply-check file implementation only, not public CLI, native parser support, or execution
- defined native minimum: `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`
- wrapper/shim compatibility kept out of native minimum: `--sim-accel-shape <NxS>`, target-first registry lookup, print modes, JSON operator plans, resident modes, and dataset-backed flows
- parser non-inference: coverage manifests, host-probe metadata, source closure, state paths, and report paths are sidecar handoff-contract fields, not parser-discovered fields
- dry-run result: 12 non-executing preview/rejection commands matched expected exits; the two static `filelist_*` targets expose `64x1`, the expanded future Verilator spelling, and `coverage_output_equivalence`; estimate mode is separate
- accepted caveat: missing shape halves, mixed shape spelling, and non-positive counts reject through the shared mapper, but unknown accelerators currently reject at argparse choices
- definition assigns unknown-accelerator validation to the parser-stub validation contract and records current argparse choices as wrapper compatibility only
- review accepts that assignment narrowly, with the caveat that current observable rejection still happens through wrapper argparse choices
- fixture must make unknown accelerator rejection, paired positive state/step validation, compact-shape rejection outside the native minimum, ordinary Verilator arg preservation, and structured handoff fields testable without a Verilator source tree
- fixture contract is defined as an importable helper contract, not a public CLI, and it must not call target registry lookup, source closure inference, coverage manifest selection, host-probe metadata, execution, compare, or allocation logic
- implementation adds `src/tools/verilator_native_option_parser_stub_fixture.py` and `parse_verilator_native_option_stub`, bypassing wrapper argparse choices rather than counting current CLI rejection behavior as success
- implementation review accepts the helper narrowly and requires the next gate to define the source/overlay patch boundary before any native parser claim
- source-patch boundary selects a future repo-owned overlay patch descriptor under `overlays/verilator/patches/`, while keeping vendored Verilator source and a Verilator submodule out of scope
- source-patch boundary review accepts that boundary and requires the next gate to pin descriptor schema/path, upstream Verilator ref, touched upstream files, and a reproducible apply-check command before any patch implementation claim
- descriptor/apply-check definition pins upstream Verilator `v5.048` at `d0aa828c217410fffc73d92077b6f4f54830357c`, future descriptor and patch paths under `overlays/verilator/patches/`, first source touch candidates `src/V3Options.h` and `src/V3Options.cpp`, and expected apply-check exit code `0`
- descriptor/apply-check review accepts the boundary narrowly, treats the pinned commit as the peeled release-tag commit, and allows the next gate to add only the accepted descriptor and patch files plus source-of-truth/test/doc alignment
- structured handoff fields are pinned before any native parser support claim
- non-claim: this does not add parser implementation, execution, measurement, runtime/ABI support, arbitrary RTL dependency inference, automatic optimal GPU allocation, GEM comparison, raw full-state equality, or production-serving throughput

Historical completed stage:

The accepted commit split was executed as eight payload commits plus one staged-only hook prerequisite. The largest payload commit touched `76` files, below the documented `100`-file commit guard, and `make simple && make check` passed with `221` contract tests.

Broader-shape GPU allocation policy dry-run:

- source gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json`
- workflow boundary: `python3 src/tools/run_results_reproduction.py --filelist-broader-shape-gpu-allocation-policy --dry-run` exposes the conservative `64x1` recommendation and reviewed `32x1` fallback without mutating templates or running measurements
- evidence expectation: boundary, workflow, measurement, review, refresh definition, refresh result, refresh review, and externalization completion gates remain tracked by the public-pack manifest
- report expectation: `reports/filelist_broader_shape_repeat_median_summary.json` and the four median report paths remain generated evidence only
- acceptance: the next selection gate chooses exactly one follow-up workstream and keeps automatic allocation, native Verilator option support, arbitrary dependency inference, and broad speedup as non-claims unless separately proven
- non-claim: this does not add new measurement, runtime/ABI support, arbitrary RTL dependency inference, automatic optimal GPU allocation, native Verilator option support, GEM comparison, raw full-state equality, or production-serving throughput

Config-generation validation breadth execution:

- selected tracked templates: `nvdla_cmac_core_mac`, `pulp_ita_dotp`, `pulp_ita_softmax_top`, `pulp_ita_mha`, `pulp_paged_attention_kv_score`, and `pulp_paged_kv_cache_large`
- execution commands: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/<template>.json --shape 1x1`
- execution result: all six non-dry-run commands exited with code `0`
- coverage result: all six selected `coverage_output_equivalence` policies passed with mismatch count `0` over `29` words / `116` bytes
- raw state result: strict raw final-state equality is false in all six reports, with mismatches limited to Verilator-internal diagnostic fields
- next task after review: `define_public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate` (now completed by the public refresh chain below)
- non-claim: this is not timing evidence, speedup evidence, runtime/ABI change, raw full-state equality, universal template validation, or production LLM-serving throughput

Config-generation validation breadth public refresh:

- refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate.json`
- completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate.json`
- next-selection gate: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_breadth_public_pack_refresh_gate.json`
- selected next workstream: `config_generation_validation_shape_breadth`
- shape-breadth definition gate: `config/scaling_gates/config_generation_validation_shape_breadth_gate.json`
- shape-breadth dry-run gate: `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_gate.json`
- shape-breadth dry-run review gate: `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_review_gate.json`
- shape-breadth execution gate: `config/scaling_gates/config_generation_validation_shape_breadth_execution_gate.json`
- shape-breadth execution result gate: `config/scaling_gates/config_generation_validation_shape_breadth_execution_result_gate.json`
- shape-breadth execution review gate: `config/scaling_gates/config_generation_validation_shape_breadth_execution_review_gate.json`
- shape-breadth public refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate.json`
- shape-breadth public completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution_gate.json`
- shape-breadth next-selection gate: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_shape_breadth_public_pack_refresh_gate.json`
- additional-target definition gate: `config/scaling_gates/config_generation_validation_additional_targets_gate.json`
- additional-target dry-run review gate: `config/scaling_gates/config_generation_validation_additional_targets_dry_run_review_gate.json`
- additional-target execution gate: `config/scaling_gates/config_generation_validation_additional_targets_execution_gate.json`
- additional-target execution review gate: `config/scaling_gates/config_generation_validation_additional_targets_execution_review_gate.json`
- additional-target public refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_additional_targets_execution_gate.json`
- additional-target public completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_additional_targets_execution_gate.json`
- additional-target next-selection gate: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_additional_targets_public_pack_refresh_gate.json`
- generated-config follow-up gate: `config/scaling_gates/config_generation_validation_followup_gate.json`
- metadata invariant review gate: `config/scaling_gates/tlul_template_schema_metadata_invariant_review_gate.json`
- metadata invariant dry-run review gate: `config/scaling_gates/tlul_template_schema_metadata_invariant_review_dry_run_review_gate.json`
- metadata invariant execution gate: `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_gate.json`
- metadata invariant execution review gate: `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_review_gate.json`
- metadata invariant public refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_tlul_template_schema_metadata_invariant_execution_gate.json`
- metadata invariant public completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_template_schema_metadata_invariant_execution_gate.json`
- metadata invariant next-selection gate: `config/scaling_gates/next_measurement_selection_after_tlul_template_schema_metadata_invariant_public_pack_refresh_gate.json`
- Verilator-like hybrid entrypoint surface gate: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_gate.json`
- Verilator-like hybrid entrypoint dry-run gate: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_dry_run_gate.json`
- Verilator-like hybrid entrypoint dry-run review gate: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_dry_run_review_gate.json`
- Verilator-like hybrid entrypoint execution gate: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_gate.json`
- Verilator-like hybrid entrypoint execution result gate: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_result_gate.json`
- Verilator-like hybrid entrypoint execution review gate: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_review_gate.json`
- Verilator-like hybrid entrypoint public refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_verilator_like_hybrid_entrypoint_option_surface_execution_gate.json`
- Verilator-like hybrid entrypoint public completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_verilator_like_hybrid_entrypoint_option_surface_execution_gate.json`
- Verilator-like hybrid entrypoint next-selection gate: `config/scaling_gates/next_measurement_selection_after_verilator_like_hybrid_entrypoint_option_surface_public_pack_refresh_gate.json`
- filelist-facing hybrid plan boundary gate: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_gate.json`
- filelist-facing hybrid plan dry-run gate: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_dry_run_gate.json`
- filelist-facing hybrid plan dry-run review gate: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_dry_run_review_gate.json`
- filelist-facing hybrid plan materialization gate: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_gate.json`
- filelist-facing hybrid plan materialization result gate: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_result_gate.json`
- filelist-facing hybrid plan materialization review gate: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_review_gate.json`
- filelist materialized template dry-run gate: `config/scaling_gates/filelist_materialized_template_dry_run_gate.json`
- filelist materialized template dry-run result gate: `config/scaling_gates/filelist_materialized_template_dry_run_result_gate.json`
- filelist materialized template dry-run review gate: `config/scaling_gates/filelist_materialized_template_dry_run_review_gate.json`
- filelist materialized template execution gate: `config/scaling_gates/filelist_materialized_template_execution_gate.json`
- filelist materialized template execution result gate: `config/scaling_gates/filelist_materialized_template_execution_result_gate.json`
- filelist materialized template execution review gate: `config/scaling_gates/filelist_materialized_template_execution_review_gate.json`
- filelist materialized template public refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_gate.json`
- filelist materialized template public refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_result_gate.json`
- filelist materialized template public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_review_gate.json`
- filelist materialized template public completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_materialized_template_execution_gate.json`
- filelist materialized template next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_materialized_template_public_pack_refresh_gate.json`
- filelist source-closure dependency policy gate: `config/scaling_gates/filelist_source_closure_dependency_policy_gate.json`
- source-closure dry-run result gate: `config/scaling_gates/filelist_source_closure_dependency_policy_dry_run_result_gate.json`
- source-closure dry-run review gate: `config/scaling_gates/filelist_source_closure_dependency_policy_dry_run_review_gate.json`
- source-closure non-dry-run refusal gate: `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_gate.json`
- source-closure non-dry-run refusal result gate: `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_result_gate.json`
- source-closure non-dry-run refusal review gate: `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_review_gate.json`
- source-closure refusal public refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_gate.json`
- source-closure refusal public refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_result_gate.json`
- source-closure refusal public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_review_gate.json`
- source-closure refusal public completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_source_closure_refusal_gate.json`
- source-closure refusal next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_source_closure_refusal_public_pack_refresh_gate.json`
- known-template source-closure copy definition gate: `config/scaling_gates/filelist_known_template_source_closure_copy_gate.json`
- known-template source-closure copy dry-run result gate: `config/scaling_gates/filelist_known_template_source_closure_copy_dry_run_result_gate.json`
- known-template source-closure copy dry-run review gate: `config/scaling_gates/filelist_known_template_source_closure_copy_dry_run_review_gate.json`
- known-template source-closure copy materialization definition gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_gate.json`
- known-template source-closure copy materialization result gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_result_gate.json`
- known-template source-closure copy materialization review gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_review_gate.json`
- known-template materialized-template dry-run gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_gate.json`
- known-template materialized-template dry-run result gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_result_gate.json`
- known-template materialized-template dry-run review gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_review_gate.json`
- known-template materialized-template execution gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_gate.json`
- known-template materialized-template execution result gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_result_gate.json`
- known-template materialized-template execution review gate: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_review_gate.json`
- known-template execution public-pack refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_gate.json`
- known-template execution public-pack refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_result_gate.json`
- known-template execution public-pack refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_review_gate.json`
- known-template execution public-pack completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_known_template_source_closure_copy_execution_gate.json`
- known-template execution next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_known_template_source_closure_copy_execution_public_pack_refresh_gate.json`
- known-template source-closure reference inventory gate: `config/scaling_gates/known_template_source_closure_reference_inventory_gate.json`
- known-template source-closure reference inventory result gate: `config/scaling_gates/known_template_source_closure_reference_inventory_result_gate.json`
- known-template source-closure reference inventory review gate: `config/scaling_gates/known_template_source_closure_reference_inventory_review_gate.json`
- known-template source-closure reference inventory next-selection gate: `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_reference_inventory_gate.json`
- known-template independent reference promotion gate: `config/scaling_gates/known_template_source_closure_independent_reference_promotion_gate.json`
- known-template independent reference promotion result gate: `config/scaling_gates/known_template_source_closure_independent_reference_promotion_result_gate.json`
- known-template independent reference promotion review gate: `config/scaling_gates/known_template_source_closure_independent_reference_promotion_review_gate.json`
- known-template independent reference promotion next-selection gate: `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_independent_reference_promotion_review_gate.json`
- known-template source-closure copy breadth validation gate: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_gate.json`
- known-template source-closure copy breadth validation dry-run result gate: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_dry_run_result_gate.json`
- known-template source-closure copy breadth validation dry-run review gate: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_dry_run_review_gate.json`
- known-template source-closure copy breadth validation next-selection gate: `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_validation_dry_run_review_gate.json`
- known-template source-closure copy breadth materialization gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_gate.json`
- known-template source-closure copy breadth materialization result gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_result_gate.json`
- known-template source-closure copy breadth materialization review gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_review_gate.json`
- known-template source-closure copy breadth materialization next-selection gate: `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_materialization_review_gate.json`
- known-template source-closure copy breadth materialized-template dry-run gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_gate.json`
- known-template source-closure copy breadth materialized-template dry-run result gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_result_gate.json`
- known-template source-closure copy breadth materialized-template dry-run review gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_review_gate.json`
- known-template source-closure copy breadth materialized-template dry-run next-selection gate: `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_materialized_template_dry_run_review_gate.json`
- known-template source-closure copy breadth materialized-template execution gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_gate.json`
- known-template source-closure copy breadth materialized-template execution result gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_result_gate.json`
- known-template source-closure copy breadth materialized-template execution review gate: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_review_gate.json`
- known-template source-closure copy breadth execution next-selection gate: `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_execution_review_gate.json`
- known-template source-closure copy breadth execution public-pack refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_gate.json`
- known-template source-closure copy breadth execution public-pack refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_result_gate.json`
- known-template source-closure copy breadth execution public-pack refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_review_gate.json`
- known-template source-closure copy breadth execution public-pack completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_known_template_source_closure_copy_breadth_execution_gate.json`
- known-template source-closure copy breadth execution next-selection gate: `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_execution_public_pack_refresh_gate.json`
- Verilator-compatible GPU hybrid minimal bench suite gate: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_gate.json`
- Verilator-compatible GPU hybrid minimal bench suite result gate: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_result_gate.json`
- Verilator-compatible GPU hybrid minimal bench suite run result gate: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_run_result_gate.json`
- Verilator-compatible GPU hybrid minimal bench suite run review gate: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_run_review_gate.json`
- Verilator-compatible GPU hybrid minimal bench suite completion audit: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_completion_audit.json`
- minimal-suite follow-up selection gate: `config/scaling_gates/next_measured_benchmark_selection_after_verilator_compatible_gpu_hybrid_minimal_bench_suite_completion_gate.json`
- persistent resident decode-like follow-up definition gate: `config/scaling_gates/define_persistent_resident_decode_like_followup_measurement_gate.json`
- persistent resident decode-like follow-up result gate: `config/scaling_gates/persistent_resident_decode_like_followup_measurement_result_gate.json`
- persistent resident decode-like follow-up review gate: `config/scaling_gates/persistent_resident_decode_like_followup_measurement_review_gate.json`
- persistent resident decode-like public-pack refresh gate: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_gate.json`
- persistent resident decode-like public-pack refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_result_gate.json`
- persistent resident decode-like public-pack refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_review_gate.json`
- persistent resident decode-like public-pack externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_persistent_resident_decode_like_followup_measurement_gate.json`
- next benchmark selection gate: `config/scaling_gates/next_measurement_selection_after_persistent_resident_decode_like_followup_public_pack_refresh_gate.json`
- filelist shape-breadth timing definition gate: `config/scaling_gates/define_filelist_shape_breadth_timing_measurement_gate.json`
- filelist shape-breadth timing result gate: `config/scaling_gates/filelist_shape_breadth_timing_measurement_result_gate.json`
- filelist shape-breadth timing review gate: `config/scaling_gates/filelist_shape_breadth_timing_measurement_review_gate.json`
- filelist shape-breadth public-pack refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_gate.json`
- filelist shape-breadth public-pack refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_result_gate.json`
- filelist shape-breadth public-pack refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_review_gate.json`
- filelist shape-breadth public-pack externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_timing_measurement_gate.json`
- filelist shape-breadth next measurement selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_timing_measurement_public_pack_refresh_gate.json`
- filelist shape-breadth repeat-median timing definition gate: `config/scaling_gates/define_filelist_shape_breadth_repeat_median_timing_gate.json`
- filelist shape-breadth repeat-median workflow gate: `config/scaling_gates/filelist_shape_breadth_repeat_median_workflow_gate.json`
- filelist shape-breadth repeat-median measurement gate: `config/scaling_gates/filelist_shape_breadth_repeat_median_measurement_gate.json`
- filelist shape-breadth repeat-median review gate: `config/scaling_gates/filelist_shape_breadth_repeat_median_review_gate.json`
- filelist shape-breadth repeat-median public-pack refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_gate.json`
- filelist shape-breadth repeat-median public-pack refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_result_gate.json`
- filelist shape-breadth repeat-median public-pack refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_review_gate.json`
- filelist shape-breadth repeat-median public-pack externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_repeat_median_gate.json`
- filelist shape-breadth repeat-median next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_repeat_median_public_pack_refresh_gate.json`
- filelist shape-breadth GPU allocation policy definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_gate.json`
- filelist shape-breadth GPU allocation policy dry-run result gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_result_gate.json`
- filelist shape-breadth GPU allocation policy dry-run review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_review_gate.json`
- filelist shape-breadth GPU allocation policy execution definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_execution_gate.json`
- filelist shape-breadth GPU allocation policy execution dry-run result gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_result_gate.json`
- filelist shape-breadth GPU allocation policy execution dry-run review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_review_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run execution definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run execution result gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run execution review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run public refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run public refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run public externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy non-dry-run next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_public_pack_refresh_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep dry-run result gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep dry-run review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep non-dry-run definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep non-dry-run result gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep non-dry-run review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep public refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep public refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep public externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_public_pack_refresh_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing result gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing public refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing public refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing public externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep timing next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_public_pack_refresh_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep repeat-median measurement gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_measurement_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep repeat-median review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep repeat-median public refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep repeat-median public refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep repeat-median public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep repeat-median public externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep repeat-median next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_public_pack_refresh_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy workflow gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_workflow_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy dry-run review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy public refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy public-pack externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_public_pack_refresh_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run execution definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run execution result gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run execution review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run public refresh definition gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run public refresh result gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run public-pack externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy non-dry-run next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_public_pack_refresh_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median definition gate: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median workflow gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_workflow_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median dry-run review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median measurement gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_measurement_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median review gate: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median public refresh review gate: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median public-pack externalization completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json`
- filelist shape-breadth GPU allocation policy broader shape sweep policy repeat-median next-selection gate: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_public_pack_refresh_gate.json`
- current next task: `implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate`
- reason: the compact suite validates automation surface, high/low shape classes, resident dry-run, and filelist execution evidence; the resident decode-like mitigation is measured, public-pack refreshed, and externalized, and the scoped filelist-derived repeat-median result is accepted, public-pack refreshed, externally closed, selected for conservative policy broadening, defined, separated into a dry-run workflow, reviewed, packaged into a public-refresh definition, accepted as a public-pack archive dry-run, externally closed, selected for scoped non-dry-run execution definition, and fixed to the two policy-recommended `64x1` commands

Config-generation validation shape breadth definition:

- selected tracked templates: the same six templates used by the `1x1` breadth execution
- selected shapes: `32x1` and `1x32`
- planned dry-run commands: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/<template>.json --shape <32x1|1x32> --dry-run`
- dry-run result: all 12 command plans exited with code `0`, emitted `src/tools/build_host_probe.py`, avoided Makefile host-probe targets, and preserved `coverage_output_equivalence`
- execution definition: all 12 reviewed commands are selected for real build/run/compare
- execution result: all 12 non-dry-run commands completed build/run/compare and passed `coverage_output_equivalence` with mismatch count `0`
- review result: accepted for public packaging refresh; raw full-state equality remains false and timing/speedup claims remain out of scope
- public refresh: defined and includes the 12-command shape-breadth result in the public pack without adding timing, speedup, raw-state, runtime/ABI, or production-serving claims
- public completion: closed and selected additional tracked target breadth next
- likely first added targets: `nvdla_cmac_a2cacc`, `prim_count`, and `prim_secded_inv_39_32_enc`
- additional-target definition: selects `nvdla_cmac_a2cacc`, `prim_count`, and `prim_secded_inv_39_32_enc` at `1x1 --dry-run`
- execution definition: all six representative metadata-invariant commands are selected for real build/run/compare
- execution result: all six non-dry-run commands completed build/run/compare and passed `coverage_output_equivalence` with mismatch count `0`
- execution review: accepted for public packaging refresh; raw full-state equality remains false and timing/speedup claims remain out of scope
- public refresh/completion: closed and selected Verilator-like hybrid entrypoint surface definition next
- entrypoint surface definition: target-name plus `--sim-accel-shape <NxS>` is the first operator-facing bridge; raw filelist input remains deferred
- entrypoint dry-run/review: six non-executing preview/operator-plan commands exited `0`, preserved tracked-template handoff plus `coverage_output_equivalence`, and exposed synthesized Verilator command spelling
- entrypoint execution definition: one non-dry-run `paged_attention_kv_score --sim-accel-shape 64x1` operator command is selected for build/run/compare
- entrypoint execution/review: the selected operator command exited `0` and passed `coverage_output_equivalence` with mismatch count `0`; raw strict final-state equality remains false
- entrypoint public refresh/completion: closed and selected filelist-to-hybrid-plan boundary next
- filelist-facing boundary definition: repeatable `--source` plus explicit top/overlay/clock/reset metadata is the first plan-only contract
- filelist-facing dry-run/review: one accepted plan command and one missing source/overlay refusal were accepted as plan-only evidence
- filelist-facing materialization definition: exactly three reviewed payload paths may be written; existing source overwrite remains forbidden
- filelist-facing materialization/review: exactly three JSON source files were written and accepted as materialized source, not execution evidence
- filelist materialized template dry-run/review: the generated template dry-run exited `0`, produced the expected seven-stage command plan, and preserved `coverage_output_equivalence`
- filelist materialized template execution definition: the matching non-dry-run `1x1` command is selected; later acceptance requires `coverage_output_equivalence` mismatch count `0`
- filelist materialized template execution/review: the first attempt exposed incomplete source closure; after repairing the template source list, the `1x1` build/run/compare passed `coverage_output_equivalence` with mismatch count `0`
- filelist materialized template public refresh/review: public manifest now includes the scoped filelist gate chain, generated filelist template/coverage manifest, generator helpers, and optional compare report
- filelist materialized template public completion/next-selection: externalization is closed, and the next workstream is selected as source-closure dependency policy
- filelist source-closure dependency policy definition: explicit complete source closure is required for execution; arbitrary RTL dependency inference remains a non-claim
- source-closure dry-run/review: the `ita.sv` leaf-source case is marked incomplete, the explicit 29-file ITA/common_cells closure is marked complete, and arbitrary RTL dependency inference remains a non-claim
- source-closure non-dry-run refusal/review: templates marked `incomplete` or `refused` are stopped before Verilator in non-dry-run mode; dry-run remains plan-only and unknown remains risk metadata
- source-closure refusal public refresh/review: the refusal gate chain and contract test are in the public-pack manifest
- source-closure refusal public completion/next-selection: externalization is closed and known-template source-closure copy is selected next
- next task: `define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate`
- current scope reminder: the execution gate must not add runtime/ABI changes, raw full-state equality claims, universal template validation, arbitrary dependency inference, arbitrary automatic GPU allocation claims, broad speedup claims beyond the scoped reviewed repeat-count-3 result, GEM comparison claims, native Verilator option claims, or production LLM-serving throughput claims

TL-UL template schema normalization breadth:

- selected tracked templates: `nvdla_cmac_a2cacc`, `prim_count`, and `prim_secded_inv_39_32_enc`
- execution result: all three non-dry-run `1x1` build/run/compare commands exited with code `0`
- coverage result: all three selected `coverage_output_equivalence` policies passed with mismatch count `0`
- selected breadth templates: `tlul_sink`, `tlul_request_loopback`, and `tlul_adapter_host`
- dry-run commands: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/<template>.json --shape 1x1 --dry-run`
- dry-run result: all three selected dry-run commands exited with code `0`
- execution commands: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/<template>.json --shape 1x1`
- execution breadth result: all three selected non-dry-run commands exited with code `0`
- coverage breadth result: all three selected `coverage_output_equivalence` policies passed with mismatch count `0` over `29` words / `116` bytes
- historical gate-chain details are intentionally summarized here. Use tracked records under `records/scaling_gates/`, `config/selection_extensions.json`, and the public-pack manifest for clone-reproducible evidence. Local candidate records are not canonical until tracked.
- deferred: MobileViT CPU-kick, Ibex, quantized KV-cache, and untracked PULP candidates
- non-claim: this is not timing evidence, speedup evidence, runtime/ABI change, raw full-state equality, or production LLM-serving throughput claim

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
- active `config/` file count: `143`
- tracked gate JSON records under `records/scaling_gates/`: `803`
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
- `python3 src/tools/run_hybrid_benchmark.py --list-targets`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py pulp_paged_kv_cache_large --shape 256x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 1x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py pulp_paged_kv_cache_large --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_paged_kv_cache_large_template_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode resident-state-reuse --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode persistent-resident-state-abi --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --summary-from-existing --summary-out reports/hybrid_benchmark_mobile_vit_template_limit128.json`

## Next Goal

This section is a historical milestone snapshot from the persistent resident state ABI repeat-median packaging boundary. For the open pointer, use **Current Frontier** above, `config/selection.json`, `README.md`, and **Next Gate** below.

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

`implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate`

Acceptance criteria:

- use `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json` as the source artifact
- add `overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json`
- add `overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch`
- validate the descriptor with `python3 -m json.tool`
- run the accepted external-checkout `git apply --check` against Verilator `v5.048` peeled commit `d0aa828c217410fffc73d92077b6f4f54830357c`
- keep the upstream patch touch set to `src/V3Options.h` and `src/V3Options.cpp`
- keep `--sim-accel-estimate-efficiency`, compact shape spelling, `src/V3OptionParser.*`, `src/VlcMain.cpp`, docs, and upstream `test_regress/t/` outside this implementation unless a new review expands scope
- keep vendored Verilator source, execution, measurement, source closure inference, automatic allocation, and arbitrary RTL/filelist support out of scope
- keep the accepted parser-only handoff fields tied to `coverage_output_equivalence`
- preserve the two tracked `filelist_*` targets as evidence only, without claiming arbitrary filelist support
- keep generated reports and artifacts non-canonical
- add no parser implementation, measurement, runtime/ABI, arbitrary RTL, automatic allocation, GEM, production-serving, or raw full-state equality claim
- keep arbitrary filelist planning, dependency inference, automatic allocation, resident optimization, and GEM comparison as deferred workstreams

Deferred technical workstreams:

- native Verilator parser boundary
- arbitrary filelist-to-sidecar planner
- filelist dependency inference
- broader automatic GPU allocation policy
- resident execution optimization
- GEM comparison boundary

## Archive Boundary

Historical gate details remain in `records/scaling_gates/`, with `config/scaling_gates` kept as a compatibility link. Generated summaries are reproducible under `reports/`, and build/raw outputs are reproducible under `artifacts/`; both directories may contain local generated evidence. They should not be copied back into `selection.json`, `README.md`, or this roadmap as canonical decisions.
