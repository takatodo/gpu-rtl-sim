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
| Current source of truth and reader pack | `README.md`, `config/selection.json`, `config/selection_extensions.json`, `config/selection_verification_commands.json`, `docs/status.md`, `docs/roadmap.md`, `docs/results.md`, `docs/tool_surface.md` | Current objective, status, roadmap, linked evidence maps, verification checklist, result narrative, reader guide, and small operator-facing tool surface. Canonical project-state decisions remain in `README.md`, `config/selection.json`, `docs/status.md`, and `docs/roadmap.md`; this document is the external-facing result pack. |
| Gate and audit evidence | Tracked `records/scaling_gates/*.json` selected by `src/tools/results_reproduction_manifest.py` | Machine-readable benchmark-pack scope, readiness, selected measurement gates, and completion audits. The archive dry-run filters record candidates to git-tracked files, so local candidate gates are not published as canonical pack content. |
| Reproduction tools | `src/tools/run_results_reproduction.py`, `src/tools/results_reproduction.py`, `src/tools/run_hybrid_benchmark.py`, `src/tools/hybrid_benchmark.py`, `src/tools/run_hybrid_template.py`, `src/tools/gen_hybrid_config.py` | Public CLI entrypoints and shared logic needed to regenerate evidence and inspect the filelist-to-template boundary. |
| Target templates | `config/slice_launch_templates/tlul_fifo_sync.json`, `config/slice_launch_templates/tlul_lc_gate.json`, `config/slice_launch_templates/tlul_adapter_host.json`, `config/slice_launch_templates/nvdla_cmac_core_mac.json`, `config/slice_launch_templates/pulp_ita_dotp.json`, `config/slice_launch_templates/pulp_ita_softmax_top.json`, `config/slice_launch_templates/pulp_ita_mha.json`, `config/slice_launch_templates/pulp_paged_kv_cache_large.json`, `config/slice_launch_templates/pulp_paged_attention_kv_score.json`, `config/slice_launch_templates/filelist_paged_attention_kv_score.json`, `config/slice_launch_templates/mobile_vit_cpu_kick_rtl_proxy.json` | Supported representative workload templates, the tracked config-generation validation breadth set, and the scoped materialized filelist-derived template. |
| Contract tests | `tests/contract/test_full_ita_mha_larger_paged_kv_next.py`, `tests/contract/test_hybrid_verilator_like_cli.py` | Public pack, wrapper summary, CLI, and local-path policy checks. |
| Generated review evidence | `reports/results_reproduction_median_summary.json`, `reports/persistent_resident_state_abi_probe_summary.json`, `reports/persistent_resident_state_abi_repeat_median_summary.json`, `reports/persistent_resident_state_abi_shape_phase_sweep_summary.json`, `reports/paged_attention_kv_cache_repeat_median_summary.json`, `reports/mobile_vit_hybrid_128_summary.json`, `reports/tlul_fifo_sync_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/tlul_lc_gate_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/tlul_adapter_host_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/nvdla_cmac_core_mac_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/nvdla_cmac_core_mac_cpu_vs_hybrid_8x1_coverage_output_compare.json`, `reports/nvdla_cmac_core_mac_cpu_vs_hybrid_8x4_coverage_output_compare.json`, `reports/pulp_ita_dotp_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_ita_dotp_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_ita_dotp_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_ita_softmax_top_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_ita_softmax_top_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_ita_softmax_top_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_128x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x128_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_256x1_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x256_coverage_output_compare.json`, `reports/filelist_paged_attention_kv_score_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_512x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x128_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1024x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x256_coverage_output_compare.json`, `reports/hybrid_benchmark_*.json` | Optional evidence snapshots for review; regenerate from documented commands when absent. |

The public archive dry-run filters gate/audit record candidates to git-tracked files before printing include lines. Historical or local candidate records under `records/scaling_gates/` are not public-pack content until they are intentionally tracked and covered by the manifest boundary tests.
| Non-pack outputs | `artifacts/` raw dumps and build trees | Reproducible local outputs; do not treat as canonical pack content. |

### Native Parser Adapter Boundary

`config/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` records the current native Verilator parser boundary as a non-executing adapter payload. The parser-owned data stops at `sidecar-gpu`, positive state/step counts, normalized shape, ordinary Verilator args, and preserved build inputs. Source closure, coverage-output selection, host-probe metadata, state paths, report paths, compare labels, and `coverage_output_equivalence` resolution remain sidecar-owned. This is public-pack evidence for the interface boundary only, not sidecar execution, timing, arbitrary RTL/filelist support, automatic allocation, upstream regression success, or upstream landing.

`config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` accepts that interface boundary and advances to a non-executing fixture implementation. The accepted public claim remains an interface decision only: `coverage_output_equivalence` is a later sidecar correctness-policy reference here, not native-parser compare evidence, and resolved state files, generated reports, compare labels, coverage targets, manifest refs, host-probe metadata, runtime handoff, timing, arbitrary source closure, and automatic allocation remain non-claims.

`config/scaling_gates/implement_verilator_native_option_parser_sidecar_handoff_fixture_gate.json` records the importable fixture implementation in `src/tools/verilator_native_option_parser_sidecar_handoff.py`. The helper preserves parser-owned fields, rejects unexpected correctness-policy refs, and rejects parser values that already contain resolved sidecar outputs. `config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json` accepts only that non-executing fixture, `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` defines that an adapter payload may reach sidecar planning only with explicit sidecar context such as target, mode, template or registry entry, and source gate/manifest reference, `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` accepts that definition, and `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json` implements the first non-executing helper that validates explicit context before calling `sidecar_stage_plan`. This remains fixture/definition/review evidence only, not native Verilator parser support, sidecar runtime handoff validation, RTL simulation, timing, arbitrary RTL/filelist support, or automatic allocation.

Filelist broader shape timing public refresh definition:

`config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json` pins the reviewed single-run timing evidence from two filelist-derived targets (`filelist_paged_attention_kv_score`, `filelist_known_template_pulp_ita_mha`) across `64x1` and `1x64`. The definition references the timing definition/result/review gates plus eight timing reports and four compare reports as generated evidence only, preserving `coverage_output_equivalence` mismatch count `0` and raw full-state equality as diagnostic/non-required. It is a packaging refresh definition, not a new measurement, execution result, repeat-median claim, broad speedup claim, GEM comparison, native Verilator option claim, arbitrary RTL support claim, automatic allocation claim, runtime/ABI change, production-serving claim, or raw full-state equality claim.

Filelist broader shape timing public refresh result/review:

`config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` and including the timing definition/result/review, source-of-truth docs, compact selection pointers, and twelve generated timing/compare reports as evidence-only paths. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json` accepts the packaging-only refresh and selects public benchmark-pack externalization completion next. This still adds no measurement, execution, repeat-median, broad speedup, GEM, native Verilator, arbitrary RTL/dependency inference, runtime/ABI, automatic allocation, production-serving, or raw full-state equality claim.

Filelist broader shape timing public-pack externalization completion:

`config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json` closes the public benchmark-pack boundary for the accepted single-run timing refresh. The closed scope remains two filelist-derived targets at `64x1` and `1x64`, `coverage_output_equivalence` mismatch count `0`, raw full-state equality false/non-required, and single-run timing ranges only. It selects next-measurement selection and adds no new measurement, execution, repeat-median, broad speedup, GEM comparison, native Verilator option support, arbitrary RTL/dependency inference, runtime/ABI change, automatic allocation, production-serving, or raw full-state equality claim.

### Broader Shape Timing Next Selection

`config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate` after the accepted single-run broader-shape timing refresh. The selected workstream is repeat-median timing for the same two reviewed filelist-derived targets at `64x1` and `1x64`; the gate is selection-only and adds no measurement, execution, repeat-median evidence, broad speedup evidence, GEM comparison, native Verilator option support, arbitrary RTL/dependency inference, runtime/ABI change, automatic allocation, production-serving, or raw full-state equality claim.

### Broader Shape Repeat-Median Definition

`config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate.json` defines the repeat-median timing boundary for the same two reviewed filelist-derived targets at `64x1` and `1x64`, with repeat count `3` and `coverage_output_equivalence` required for every repeat sample. The gate records that the existing `--filelist-shape-breadth-repeat-median` workflow is scoped to `32x1` / `1x32`, so the next step is a distinct public workflow for the broader-shape set. This is definition-only and adds no measurement, execution, repeat-median evidence, broad speedup evidence, GEM comparison, native Verilator option support, arbitrary RTL/dependency inference, runtime/ABI change, automatic allocation, production-serving, or raw full-state equality claim.

### Broader Shape Repeat-Median Workflow

`config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --filelist-broader-shape-repeat-median 3 --dry-run` for the same two reviewed filelist-derived targets at `64x1` and `1x64`. The dry run expands all four target/shape pairs into three samples each and writes no generated evidence. The workflow gate itself remains workflow-only; the non-dry-run measurement gate below records the repeat-count-3 timing evidence.

### Broader Shape Repeat-Median Measurement

`config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --filelist-broader-shape-repeat-median 3` exiting `0`. All 12 samples pass `coverage_output_equivalence` with mismatch count `0`. Median CPU-to-hybrid wall ratios are `129.02924528301887x` for `filelist_paged_attention_kv_score 64x1`, `2.204404109589041x` for `filelist_paged_attention_kv_score 1x64`, `121.47241379310344x` for `filelist_known_template_pulp_ita_mha 64x1`, and `1.7360211463550361x` for `filelist_known_template_pulp_ita_mha 1x64`. This is scoped repeat-count-3 evidence only; review is required before public-pack refresh or broader claims.

### Broader Shape Repeat-Median Review

`config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json` accepts the scoped repeat-count-3 measurement for the two reviewed filelist-derived targets at `64x1` and `1x64`. The accepted claim is limited to this: for these exact templates, `64x1` state-parallel shapes remain materially stronger than `1x64` single-state repeated-step shapes. The review records the weak points: repeat-count `3` is only a stability check, the target/shape scope is narrow, the `1x64` ratios are modest, automatic allocation policy is not proven, and generated reports are not source of truth. The selected next task is `define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate`.

### Broader Shape Repeat-Median Public Refresh

`config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json` defines the public-pack refresh boundary for the reviewed broader-shape repeat-median evidence. It keeps `docs/results.md`, README, status, roadmap, selection state, and the public-pack manifest aligned around the boundary, workflow, measurement, review, and refresh definition gates. It references `reports/filelist_broader_shape_repeat_median_summary.json` and the four broader median reports as generated evidence only. This is packaging definition only; the next task is `run_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate`.

`config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json` accepts the packaging-only refresh. The accepted scope remains the same two filelist-derived targets, two shapes, repeat count `3`, and generated reports as evidence-only paths. The next task is defining public benchmark-pack externalization completion for this scoped refresh.

`config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json` closes the public benchmark-pack boundary for the accepted broader-shape repeat-median refresh. It carries only the scoped two-target, two-shape, repeat-count-3 evidence and selects next-workstream selection. This adds no measurement, execution, runtime/ABI change, native Verilator option support, arbitrary RTL/dependency inference, automatic optimal allocation, GEM comparison, production-serving, or raw full-state equality claim.

`config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_public_pack_refresh_gate.json` selects scoped broader GPU allocation policy definition next. The selection uses the accepted `64x1` / `1x64` repeat-median result as input, but does not itself add measurement, execution, native Verilator option support, arbitrary RTL/dependency inference, automatic optimal allocation, GEM comparison, runtime/ABI change, production-serving, or raw full-state equality evidence.

`config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json` defines the scoped broader policy boundary. It recommends `64x1` with high confidence only for the two reviewed filelist-derived targets and keeps `32x1` as a reviewed fallback when the operator cannot use the broader shape. The next task is adding a distinct workflow; the gate adds no execution, measurement, native Verilator option support, arbitrary RTL/dependency inference, automatic optimal allocation, GEM comparison, runtime/ABI change, production-serving, or raw full-state equality evidence.

`config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --filelist-broader-shape-gpu-allocation-policy --dry-run` as a distinct broader policy workflow. The dry-run payload is JSON-only, recommends `64x1` with high confidence for the two reviewed filelist-derived targets, keeps `32x1` as a medium-confidence fallback, writes no reports or artifacts, and keeps native Verilator option support, arbitrary RTL/dependency inference, automatic optimal allocation, runtime/ABI change, GEM comparison, production-serving, and raw full-state equality as non-claims.

`config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_dry_run_review_gate.json` accepts that scoped broader policy dry-run and `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json` defines the packaging-only refresh. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_result_gate.json` records the public archive dry-run exiting `0`, `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_review_gate.json` accepts the refresh, and `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json` closes the public-pack boundary. `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_public_pack_refresh_gate.json` then selects scoped non-dry-run execution definition, `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json` fixes the two policy-recommended `64x1` commands, `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json` records both commands exiting `0` and passing `coverage_output_equivalence` with mismatch count `0`, `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json` accepts only that scoped execution result, `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json` defines the packaging-only public refresh for those accepted `64x1` reports, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json` records the archive dry-run exiting `0` with no archive creation before `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json` accepts it. `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json` then closes that public-pack boundary, `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_public_pack_refresh_gate.json` selects policy-selected `64x1` repeat-median timing, `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate.json` defines the two-target workflow boundary, `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --filelist-broader-policy-repeat-median 3 --dry-run`, and `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_review_gate.json` accepts the dry-run plan with six compare commands, two `64x1` targets, and no `1x64` plans. This still must not add timing, speedup, repeat-median, runtime/ABI, native Verilator option, arbitrary RTL/dependency inference, automatic optimal allocation, GEM, production-serving, or raw full-state equality claims until the non-dry-run measurement/review gate records them.

`config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_measurement_gate.json` now records the non-dry-run `python3 src/tools/run_results_reproduction.py --filelist-broader-policy-repeat-median 3` result for exactly those two policy-selected `64x1` workloads. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json` accepts the scoped measurement and selects public results packaging refresh next. The accepted public evidence is limited to the aggregate summary and median JSON reports; per-sample stdout reports may contain local paths and are not public-pack evidence.

`config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json` defines the packaging-only refresh for that accepted result. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` with `include_count=535`, `exclude_count=2`, no archive creation, and no per-sample stdout/local absolute paths in the manifest. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json` accepts the packaging-only refresh and selects public benchmark-pack externalization completion next.

`config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json` closes that public-pack boundary. The next gate is selection-only: choose the next measured workstream after the policy-selected `64x1` repeat-median evidence, without adding native Verilator option, arbitrary RTL/dependency inference, automatic optimal allocation, GEM, runtime/ABI, production-serving, or raw full-state equality claims from this evidence alone.

`config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_public_pack_refresh_gate.json` selects `define_verilator_native_option_prototype_boundary_gate` next. This is selection-only: it moves toward Verilator-option simplicity, but the native option, arbitrary RTL support, dependency inference, automatic optimal allocation, runtime/ABI change, GEM comparison, and production-serving claims remain deferred.

`config/scaling_gates/define_verilator_native_option_prototype_boundary_gate.json` defines that prototype boundary and advances to `run_verilator_native_option_prototype_boundary_dry_run_gate`. The boundary uses expanded `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1` as the primary future Verilator spelling, keeps compact `--sim-accel-shape 64x1` as wrapper/shim compatibility, and records that current `filelist_*` evidence is not yet direct shim target support.

`config/scaling_gates/verilator_native_option_prototype_boundary_dry_run_result_gate.json` records the plan-only dry-run for that boundary: two registered-target shim previews and two `64x1` filelist-template dry-runs all exit `0`. `config/scaling_gates/verilator_native_option_prototype_boundary_dry_run_review_gate.json` accepts the result and advances to `define_verilator_native_option_prototype_filelist_target_resolution_gate`, where the next decision is direct `filelist_*` registry support versus a separate planner. This is still not native Verilator parser support, arbitrary RTL support, dependency inference, automatic allocation, execution/timing evidence, runtime/ABI change, or production-serving throughput.

`config/scaling_gates/define_verilator_native_option_prototype_filelist_target_resolution_gate.json` selects static registry support for exactly two tracked filelist templates. `config/scaling_gates/verilator_native_option_prototype_filelist_registry_result_gate.json` records `--print-verilator-command`, `--operator-plan-json`, and sidecar discovery checks exiting `0`; `config/scaling_gates/verilator_native_option_prototype_filelist_registry_review_gate.json` accepts only that tracked-template support and advances to public-pack refresh definition. This is still not arbitrary filelist parsing, native Verilator parser support, dependency inference, automatic allocation, execution/timing evidence, runtime/ABI change, or production-serving throughput.

`config/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate.json` defines that public-pack refresh boundary and advances to the archive dry-run. The refresh is packaging-only: it carries the target-resolution definition, registry result, registry review, and refresh definition gates into the public manifest without adding measurement, execution, runtime/ABI changes, arbitrary filelist support, or native parser claims.

`config/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_result_gate.json` records the archive dry-run exiting `0` with `include_count=546`, `exclude_count=2`, and no archive creation. `config/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_review_gate.json` accepts that packaging-only result and advances to public benchmark-pack externalization completion for this tracked-template boundary.

`config/scaling_gates/public_benchmark_pack_externalization_completion_after_verilator_native_option_prototype_filelist_registry_gate.json` closes that public-pack boundary and advances to next-workstream selection. The closed scope remains exactly two static tracked `filelist_*` targets, five preview/operator-plan commands, and no new measurement, execution, native parser, arbitrary filelist, dependency inference, automatic allocation, or runtime/ABI claim.

`config/scaling_gates/next_measurement_selection_after_verilator_native_option_prototype_filelist_registry_public_pack_refresh_gate.json` selects `define_commit_split_and_public_pack_cleanup_gate` as the next workstream. This is a selection-only gate: it does not add measurement, execution, runtime/ABI changes, native parser support, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality. The reason is that the public-pack chain is now closed while the staged set exceeds the documented commit guard, so commit split planning is the next reproducibility step before further technical expansion.

`config/scaling_gates/define_commit_split_and_public_pack_cleanup_gate.json` defines the cleanup boundary without rewriting the index or committing. It pins the staged set at `263` files before the definition gate, projects `265` files after adding the definition record and focused contract test, and defines eight groups with estimated counts `15`, `26`, `71`, `30`, `24`, `59`, `28`, and `25`, each below the documented `100`-file commit guard. It also records remaining line-guard risks for one guarded script and two guarded contract tests. The gate advances to review and keeps measurement, execution, runtime/ABI, native parser, arbitrary filelist, dependency inference, automatic allocation, GEM, production-serving, and raw full-state equality as non-claims.

`config/scaling_gates/review_commit_split_and_public_pack_cleanup_gate.json` accepts the eight file-count groups as the operational split boundary. It does not rewrite the index or allow commits yet; the next task is resolving the line guard risks in `src/tools/results_reproduction_gpu_allocation_policy.py`, `tests/contract/test_hybrid_verilator_like_cli.py`, and `tests/contract/test_public_pack_repeat_median_refresh_gates.py`.

`config/scaling_gates/resolve_commit_split_line_guard_risks_gate.json` records that the per-file script and contract-test guards are now clean under `python3 src/tools/check_staged_large_files.py --max-files 999`. The remaining blocker is the staged file-count guard, so the next step is an index rewrite into the accepted eight groups.

`config/scaling_gates/execute_commit_split_index_rewrite_gate.json` records that the index rewrite completed as eight payload commits after a staged-only hook prerequisite. The largest payload commit touched `76` files, the worktree was clean afterward, and `make simple && make check` passed with `221` contract tests. This completion advances to `define_verilator_native_option_parser_boundary_gate` and still does not claim a native parser implementation, new measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/define_verilator_native_option_parser_boundary_gate.json` defines the next native parser boundary as the expanded Verilator-facing spelling `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` mapped into the existing sidecar handoff contract. It keeps `--sim-accel-shape <NxS>`, target-first registry lookup, terminal print modes, JSON operator plans, resident modes, and dataset-backed flows on the wrapper/shim compatibility side. The next task is `review_verilator_native_option_parser_boundary_gate`; this is definition-only and adds no Verilator parser implementation, source patch, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_boundary_gate.json` accepts that definition and advances to `run_verilator_native_option_parser_boundary_dry_run_gate`. The review keeps the weak point explicit: there is still no Verilator source tree or parser patch in this repository, and the parser boundary does not infer manifests, host-probe metadata, source closure, state paths, or report paths. Those are sidecar handoff-contract fields. The next gate is limited to non-executing previews and adds no execution, measurement, parser implementation, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/verilator_native_option_parser_boundary_dry_run_result_gate.json` records the non-executing dry-run result for that reviewed boundary and advances to `review_verilator_native_option_parser_boundary_dry_run_gate`. Twelve preview/rejection commands matched expected exits: ready `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` commands expose `64x1`, `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1`, and `coverage_output_equivalence`; estimate mode stays separate. The explicit weak point is that unknown accelerator names reject at argparse choices, while missing shape halves, mixed spelling, and non-positive counts reject through the shared mapper. This adds no execution, measurement, parser implementation, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_boundary_dry_run_gate.json` accepts the dry-run result and advances to `define_verilator_native_option_parser_stub_boundary_gate`. The acceptance is intentionally narrow: the ready previews and not-ready rejections are sufficient for the reviewed boundary, but the next gate must define where unknown accelerator validation belongs because today's `--sim-accel cuda` rejection happens at argparse choices instead of the shared mapper. This still adds no execution, measurement, parser implementation, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/define_verilator_native_option_parser_stub_boundary_gate.json` defines that next boundary and advances to `review_verilator_native_option_parser_stub_boundary_gate`. Unknown accelerator validation is assigned to the parser-stub validation contract; current argparse choices are recorded only as wrapper compatibility behavior. The gate also pins the structured handoff fields a future non-executing stub fixture must expose, while keeping target registry lookup, coverage manifest selection, host-probe metadata, state materialization, execution, and comparison on the sidecar side. This is definition-only and adds no parser implementation, source patch, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_stub_boundary_gate.json` accepts the parser-stub boundary and advances to `define_verilator_native_option_parser_stub_fixture_gate`. The review keeps the weakness explicit: this is still contract-only, there is no Verilator source tree or parser patch in this repository, and observable unknown-accelerator rejection still comes from wrapper argparse choices. The next gate must define a non-executing fixture that tests parser-stub validation and structured handoff fields without claiming parser implementation, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/define_verilator_native_option_parser_stub_fixture_gate.json` defines that fixture contract and advances to `review_verilator_native_option_parser_stub_fixture_gate`. The fixture remains non-executing and importable, not a public CLI: it must accept `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1`, reject unknown accelerators through parser-stub validation rather than wrapper argparse choices, reject missing/non-positive shape inputs, reject compact `--sim-accel-shape` as wrapper compatibility outside the native minimum, preserve ordinary Verilator build arguments, and serialize parser-only handoff fields. This still adds no helper implementation, parser implementation, source patch, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_stub_fixture_gate.json` accepts that fixture contract and advances to `implement_verilator_native_option_parser_stub_fixture_gate`. The review keeps the weakest point explicit: existing wrapper and shim CLIs still reject unknown accelerators through argparse choices, so the next gate must implement an importable non-executing helper that bypasses that behavior and tests the parser-stub validation contract directly. This adds no parser implementation, source patch, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving throughput, or raw full-state equality.

The parser path has since moved from fixture and overlay-patch definition into build-only and parser-smoke evidence. `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json` records descriptor validation, clean-checkout `git apply --check`, actual patch apply, `autoconf`, `configure`, and `make -j 28 verilator_bin` exiting `0` for the repaired repo-owned Verilator overlay patch. `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json` defines the lint-only built-binary accept/reject smoke boundary, `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json` accepts that boundary as narrow enough to execute, `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json` records the scoped parser-only smoke passing for two positive expanded spellings plus six rejection cases, `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_run_gate.json` accepts only that scoped smoke, `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` defines negative-count and non-numeric suffix hardening, `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` accepts in-place overlay patch implementation, `config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` records the descriptor/patch update that replaces `std::atoi` prefix parsing with full-token positive integer validation plus clean-checkout apply/location sanity, `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` records a rebuilt-binary parser-only smoke passing for two positive expanded spellings plus four hardening rejection cases, `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate.json` accepts only that scoped strict count-token result, `config/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` defines the current parser-to-adapter handoff boundary, `config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` accepts that boundary narrowly, `config/scaling_gates/implement_verilator_native_option_parser_sidecar_handoff_fixture_gate.json` implements the non-executing adapter fixture, `config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json` accepts only that fixture, `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` defines explicit target/mode/template context as required before the adapter can reach `sidecar_stage_plan`, `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` accepts only that non-executing planning definition, and `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json` implements the non-executing context-validation fixture. The suffix cases prove `std::atoi` prefix behavior is rejected, and separate-token negative cases reached strict value validation in this run. This is still not broad native parser support, sidecar execution, timing evidence, arbitrary RTL/filelist support, automatic GPU allocation, upstream regression success, or upstream landing.

Public archive dry-run:

This section is the scoped `public_pack_archive_ready` task inside the current public benchmark pack externalization objective.

Use this command to print the archive include/exclude plan without creating an archive file:

```bash
python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run
```

The archive dry-run is intentionally non-writing. It lists the same source-of-truth files, tracked gate/audit records, tools, templates, tests, and optional generated evidence snapshots as the public pack manifest. Record candidates that are not in git are excluded from the include plan so local candidate gates do not become canonical pack content accidentally. It also prints the non-executed command `tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>`. Archive files, if created outside this workflow, are generated outputs and must not become source of truth.

Public reproduction smoke:

Run these commands first when checking the public pack from a fresh checkout. They are dry-run commands, so they validate the public CLI surface and command expansion without requiring Verilator/CUDA execution, generated object directories, or ImageNet data.

```bash
python3 src/tools/run_results_reproduction.py --dry-run
python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi-shape-phase-sweep --dry-run
python3 src/tools/run_results_reproduction.py --filelist-broader-shape-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --filelist-broader-shape-gpu-allocation-policy --dry-run
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

Config-generation validation breadth execution result: `config/scaling_gates/config_generation_validation_breadth_execution_result_gate.json` records the non-dry-run execution of the same six tracked `1x1` build/run/compare commands. All six exited with code `0`; all selected `coverage_output_equivalence` policies passed with mismatch count `0` over `29` words / `116` bytes. Raw final-state equality remains false in all six reports because the residual differences are Verilator-internal diagnostic fields.

Config-generation validation breadth execution review: `config/scaling_gates/config_generation_validation_breadth_execution_review_gate.json` accepts the result and selects the next public/source-of-truth refresh. The public result narrative keeps the correctness policy and non-claims here; generated `reports/` and `artifacts/` remain non-canonical evidence.

Config-generation validation breadth public refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate.json` admits the six-template execution result into the public pack without adding timing, speedup, raw-state, runtime/ABI, or production-serving claims. Completion gate: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate.json` closes that publication boundary. Next-selection gate: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_breadth_public_pack_refresh_gate.json` selects `define_config_generation_validation_shape_breadth_gate`.

Config-generation validation shape-breadth execution result: `config/scaling_gates/config_generation_validation_shape_breadth_execution_result_gate.json` records the non-dry-run execution of all six tracked templates at `32x1` and `1x32`. All 12 commands exited with code `0`; all selected `coverage_output_equivalence` policies passed with mismatch count `0` over `29` words / `116` bytes per state. Raw final-state equality remains false for all 12 reports, and some `32x1` diagnostics include raw `other` mismatch bytes, so this is scoped coverage-output evidence rather than raw byte equality, timing, speedup, or production-serving evidence.

Config-generation validation shape-breadth public refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate.json` admits the 12-command shape-breadth result into the public pack without adding a new measurement, runtime/ABI change, workload import, timing claim, speedup claim, raw-state claim, or production-serving claim. The generated compare reports remain evidence under `reports/`, not source of truth.

Config-generation validation shape-breadth public-pack completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution_gate.json` closes the publication boundary for the 12-command shape-breadth execution. Next-selection gate: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_shape_breadth_public_pack_refresh_gate.json` selects `define_config_generation_validation_additional_targets_gate`, keeping the next step focused on additional tracked target breadth rather than timing, runtime tuning, or new workload import.

Config-generation validation additional-target execution result: `config/scaling_gates/config_generation_validation_additional_targets_execution_result_gate.json` records the non-dry-run execution of `nvdla_cmac_a2cacc`, `prim_count`, and `prim_secded_inv_39_32_enc` at `1x1`. All three commands exited with code `0`; all selected `coverage_output_equivalence` policies passed with mismatch count `0` over `29` words / `116` bytes per state. Raw final-state equality remains false for all three reports, so this is scoped coverage-output evidence rather than raw byte equality, timing, speedup, or production-serving evidence.

Config-generation validation additional-target public refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_additional_targets_execution_gate.json` admits the three-command additional-target result into the public pack without adding a new measurement, runtime/ABI change, workload import, timing claim, speedup claim, raw-state claim, or production-serving claim. The generated compare reports remain evidence under `reports/`, not source of truth.

Config-generation validation additional-target public-pack completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_additional_targets_execution_gate.json` closes the publication boundary for the three-command additional-target execution. Next-selection gate: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_additional_targets_public_pack_refresh_gate.json` selects `define_config_generation_validation_followup_gate`, keeping the next step focused on whether generated-config validation needs another scoped target set or should hand off to metadata-invariant review.

Config-generation validation follow-up: `config/scaling_gates/config_generation_validation_followup_gate.json` selects `define_tlul_template_schema_metadata_invariant_review_gate`. This is selection-only: it does not add another measurement, runtime/ABI change, workload import, timing claim, speedup claim, raw-state claim, or production-serving claim.

TL-UL/template schema metadata invariant review: `config/scaling_gates/tlul_template_schema_metadata_invariant_review_gate.json` defines the next dry-run boundary for representative template metadata invariants needed by generic host-probe and `coverage_output_equivalence` planning. This is definition-only and does not add build/run/compare evidence.

TL-UL/template schema metadata invariant dry-run: `config/scaling_gates/tlul_template_schema_metadata_invariant_review_dry_run_gate.json` records that all six representative `1x1 --dry-run` plans pass and preserve generic host-probe plus `coverage_output_equivalence` compare planning. Review gate: `config/scaling_gates/tlul_template_schema_metadata_invariant_review_dry_run_review_gate.json` keeps the result scoped to command-plan evidence and selects the execution definition boundary.

TL-UL/template schema metadata invariant execution definition: `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_gate.json` selects all six representative `1x1` non-dry-run commands for build/run/compare. The gate is definition-only; it adds no timing claim, runtime/ABI claim, raw full-state equality claim, or universal template guarantee.

TL-UL/template schema metadata invariant execution: `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_result_gate.json` records that all six representative `1x1` non-dry-run commands completed and passed `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes per state. Review gate: `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_review_gate.json` accepts the result for scoped output equivalence only; raw strict final-state equality remains false, and timing/speedup claims remain out of scope.

TL-UL/template schema metadata invariant public pack: `config/scaling_gates/public_results_packaging_refresh_after_tlul_template_schema_metadata_invariant_execution_gate.json` and `config/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_template_schema_metadata_invariant_execution_gate.json` include the six-command result in the public pack as scoped correctness evidence. Next-selection gate: `config/scaling_gates/next_measurement_selection_after_tlul_template_schema_metadata_invariant_public_pack_refresh_gate.json` selects `define_verilator_like_hybrid_entrypoint_option_surface_gate`; this is a usability boundary, not a new measurement, runtime/ABI change, timing claim, or Verilator-native option implementation.

Verilator-like hybrid entrypoint surface: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_gate.json` defines the first user-facing bridge as `run_hybrid_benchmark.py <target> --sim-accel-shape <NxS>` with dry-run, preflight/operator-plan, and synthesized command preview support. The reproducible input contract remains tracked slice-launch templates resolved from target names; raw filelists stay behind the tracked config boundary for now. This is not arbitrary filelist ingestion, automatic optimal GPU allocation for any design, or a Verilator-native option implementation.

Verilator-like hybrid entrypoint dry-run review: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_dry_run_gate.json` records six non-executing preview/operator-plan commands for `paged_attention_kv_score --sim-accel-shape 64x1`; all exited `0` and preserved the tracked-template handoff plus `coverage_output_equivalence` policy. `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_dry_run_review_gate.json` accepts this as option-surface evidence only and selects execution-gate definition next. It is not build/run/compare evidence, timing evidence, optimal GPU allocation, raw filelist ingestion, or a Verilator-native implementation.

Verilator-like hybrid entrypoint execution definition: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_gate.json` selects one non-dry-run operator command, `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_sim_accel_64x1.json`. The next accepted evidence must come from `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json` passing `coverage_output_equivalence`. This definition is not itself execution, timing, speedup, native Verilator option, raw filelist ingestion, or optimal GPU allocation evidence.

Verilator-like hybrid entrypoint execution review: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_result_gate.json` records that the selected non-dry-run operator command exited `0` and passed `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes per state. `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_review_gate.json` accepts the result only as scoped target-name plus `--sim-accel-shape` integration evidence. Raw strict final-state equality remains false, and the summary efficiency estimate is not fresh timing evidence.

Verilator-like hybrid entrypoint public pack: `config/scaling_gates/public_results_packaging_refresh_after_verilator_like_hybrid_entrypoint_option_surface_execution_gate.json` and `config/scaling_gates/public_benchmark_pack_externalization_completion_after_verilator_like_hybrid_entrypoint_option_surface_execution_gate.json` include the one-command target-name plus `--sim-accel-shape` execution result in the public pack as scoped integration evidence. Next-selection gate: `config/scaling_gates/next_measurement_selection_after_verilator_like_hybrid_entrypoint_option_surface_public_pack_refresh_gate.json` selects `define_filelist_to_verilator_like_hybrid_plan_boundary_gate`; this is a usability boundary, not a native Verilator option, arbitrary RTL support, timing, or optimal GPU-allocation claim.

Filelist-facing hybrid plan boundary: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_gate.json` defines a plan-only contract for repeatable `--source` RTL paths plus explicit target/top/overlay/clock/reset metadata through `src/tools/gen_hybrid_config.py --dry-run`. The next validation gate must prove the accepted command emits coverage manifest, slice-template, scaling-gate, generic host-probe metadata, and `coverage_output_equivalence` planning, and that missing filelist/overlay input is rejected. This remains a plan boundary, not arbitrary RTL execution, automatic inference, native Verilator support, timing, or optimal GPU allocation.

Filelist-facing hybrid plan dry-run review: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_dry_run_gate.json` records that `gen_hybrid_config.py --source third_party/ITA/src/ita.sv --overlay overlays/ITA/src/pulp_paged_attention_kv_score_gpu_cov_tb.sv --dry-run` exited `0` and printed manifest/template/gate drafts, host-probe metadata, and `coverage_output_equivalence` planning without writing source-of-truth files. The missing source/overlay refusal exited `1` with an explicit error. `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_dry_run_review_gate.json` accepts this as plan-only evidence and selects materialization definition next.

Filelist-facing hybrid plan materialization definition: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_gate.json` permits only the three reviewed dry-run payloads to be written as tracked source and forbids overwriting existing files. The next accepted evidence is file materialization plus JSON/metadata checks, not Verilator build/run/compare success, correctness evidence, native Verilator support, or optimal GPU allocation.

Filelist-facing hybrid plan materialization review: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_result_gate.json` records exactly three materialized JSON files for `filelist_paged_attention_kv_score`: the generated coverage manifest, generated launch template, and generated scaling-gate record. `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_review_gate.json` accepts only that source-materialization boundary and selects `define_filelist_materialized_template_dry_run_gate` next. This remains separate from Verilator build/run/compare correctness.

Filelist materialized template dry-run review: `config/scaling_gates/filelist_materialized_template_dry_run_gate.json` defines the first `run_hybrid_template.py` dry-run boundary for the generated filelist template. `config/scaling_gates/filelist_materialized_template_dry_run_result_gate.json` records exit `0` and a seven-stage command plan for `config/slice_launch_templates/filelist_paged_attention_kv_score.json --shape 1x1 --dry-run`; `config/scaling_gates/filelist_materialized_template_dry_run_review_gate.json` accepts this command-plan evidence and selects `define_filelist_materialized_template_execution_gate` next. This is not build/run/compare correctness, timing, native Verilator option, arbitrary RTL, or optimal GPU-allocation evidence.

Filelist materialized template execution definition: `config/scaling_gates/filelist_materialized_template_execution_gate.json` selects `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/filelist_paged_attention_kv_score.json --shape 1x1` as the next non-dry-run build/run/compare command. Later result review must require `coverage_output_equivalence` mismatch count `0` and must keep raw full-state equality, timing, native Verilator option, arbitrary RTL, and optimal GPU-allocation claims out of scope unless separately proven.

Filelist materialized template execution review: `config/scaling_gates/filelist_materialized_template_execution_result_gate.json` records the initial source-closure failure, the repaired template source list, and the successful rerun of `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/filelist_paged_attention_kv_score.json --shape 1x1`. The compare report `reports/filelist_paged_attention_kv_score_cpu_vs_hybrid_1x1_coverage_output_compare.json` passes `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes; raw strict final-state equality remains false with Verilator-internal-only mismatches. `config/scaling_gates/filelist_materialized_template_execution_review_gate.json` accepts only scoped materialized-template execution evidence and selects public-pack refresh next.

Filelist materialized template public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_gate.json`, `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_result_gate.json`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_review_gate.json` include the scoped filelist gate chain, generated filelist template, generated coverage manifest, generator helpers, and optional compare report in the public pack. This is a packaging refresh only; it adds no new execution, timing, speedup, arbitrary RTL, native Verilator option, or optimal GPU-allocation claim.

Filelist materialized template public-pack completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_materialized_template_execution_gate.json` closes the public-pack boundary for the scoped filelist materialized-template execution result. `config/scaling_gates/next_measurement_selection_after_filelist_materialized_template_public_pack_refresh_gate.json` selects `define_filelist_source_closure_dependency_policy_gate` next, because the first execution attempt failed until the generated template's source closure was made explicit.

Filelist source-closure dependency policy: `config/scaling_gates/filelist_source_closure_dependency_policy_gate.json` defines the follow-up policy. Future filelist-derived template execution requires an explicit complete source closure, while a known tracked template source closure may be copied when that is the reviewed boundary. This is still not automatic dependency inference for arbitrary RTL, native Verilator option support, timing, speedup, or optimal GPU allocation.

Filelist source-closure dependency policy dry-run: `config/scaling_gates/filelist_source_closure_dependency_policy_dry_run_result_gate.json` records that the `ita.sv` leaf-source dry-run is marked `incomplete`, while the explicit 29-file ITA/common_cells source closure dry-run is marked `complete`. `config/scaling_gates/filelist_source_closure_dependency_policy_dry_run_review_gate.json` accepts this as metadata-only evidence and selects a non-dry-run refusal boundary next. This does not add build/run/compare evidence, timing evidence, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation.

Filelist source-closure non-dry-run refusal: `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_gate.json`, `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_result_gate.json`, and `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_review_gate.json` record the minimal guard. Templates that explicitly declare `source_closure.status=incomplete` or `refused` now fail before Verilator in non-dry-run execution; the same template can still be inspected with `--dry-run`. Unknown source closure is not claimed complete, but remains compatible risk metadata. This is not build/run/compare evidence, timing evidence, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation.

Filelist source-closure refusal public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_gate.json`, `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_result_gate.json`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_review_gate.json` add the refusal guard gate chain plus `tests/contract/test_hybrid_config_template_cli.py` and `tests/contract/test_hybrid_verilator_like_config_generation.py` to the public-pack manifest. This is packaging-only evidence and does not add execution, timing, speedup, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation claims.

Filelist source-closure refusal public-pack completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_source_closure_refusal_gate.json` closes the source-closure refusal public-pack boundary. `config/scaling_gates/next_measurement_selection_after_filelist_source_closure_refusal_public_pack_refresh_gate.json` selects `define_filelist_known_template_source_closure_copy_gate` next, focused on reducing operator burden by copying reviewed source closure from a known tracked template without claiming arbitrary RTL dependency inference.

Filelist known-template source-closure copy dry-run: `config/scaling_gates/filelist_known_template_source_closure_copy_gate.json`, `config/scaling_gates/filelist_known_template_source_closure_copy_dry_run_result_gate.json`, and `config/scaling_gates/filelist_known_template_source_closure_copy_dry_run_review_gate.json` add the reviewed dry-run operator boundary for `gen_hybrid_config.py --source-closure-from-template`. The accepted case copies a complete source closure from `config/slice_launch_templates/filelist_paged_attention_kv_score.json`, records the reference template and source-file hash, and refuses incomplete references or requested sources missing from the copied closure. This does not add execution, timing, speedup, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation claims.

Filelist known-template source-closure copy materialization definition: `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_gate.json` defines the write boundary after the dry-run review. It permits only the generated manifest/template/gate payload paths, requires complete copied source-closure metadata to remain visible, and makes the generator refuse existing source-of-truth files by default. This is still definition-only evidence, not hybrid execution, timing, speedup, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation.

Filelist known-template source-closure copy materialization review: `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_result_gate.json` and `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_review_gate.json` record and accept the materialization of exactly three JSON payloads for `filelist_known_template_paged_attention_kv_score`. The generated launch template keeps `source_closure.status=complete`, `provenance=copied_from_known_tracked_template`, `reference_template`, and `source_files_sha256`. This remains materialized source evidence only, not hybrid execution, timing, speedup, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation.

Filelist known-template source-closure copy materialized-template dry-run review: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_gate.json`, `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_result_gate.json`, and `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_review_gate.json` record and accept the first `run_hybrid_template.py --dry-run` command plan for the materialized copied-closure template. The plan has seven stages, preserves `src/tools/build_host_probe.py`, and ends in a `coverage_output_equivalence` compare command. This is command-plan evidence only, not build/run/compare, timing, speedup, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation.

Filelist known-template source-closure copy materialized-template execution review: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_gate.json`, `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_result_gate.json`, and `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_review_gate.json` record and accept the first non-dry-run build/run/compare for the materialized copied-closure template. The selected `coverage_output_equivalence` policy passed with mismatch count `0` over `29` words / `116` bytes. Raw strict final-state equality remains false with Verilator-internal-only mismatch bytes, so this is scoped output evidence, not raw byte equality, timing, speedup, arbitrary RTL dependency inference, native Verilator option support, or automatic optimal GPU allocation.

Filelist known-template source-closure copy execution public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_gate.json`, `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_result_gate.json`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_review_gate.json` add the known-template copy chain, materialized generated source, first benchmark gate, execution review gates, and optional compare report to the public-pack dry-run include plan. This is packaging-only evidence and does not add execution, timing, speedup, arbitrary RTL dependency inference, native Verilator option support, raw full-state equality, or automatic optimal GPU allocation claims.

Filelist known-template source-closure copy execution externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_known_template_source_closure_copy_execution_gate.json` closes the public-pack boundary for the selected `1x1` copied-closure execution. `config/scaling_gates/next_measurement_selection_after_filelist_known_template_source_closure_copy_execution_public_pack_refresh_gate.json` selects source-closure reference inventory next, because breadth validation should not proceed as if one paged-attention copied reference proves multiple independent complete-reference families.

Known-template source-closure reference inventory and independent promotion: `config/scaling_gates/known_template_source_closure_reference_inventory_gate.json`, `config/scaling_gates/known_template_source_closure_reference_inventory_result_gate.json`, and `config/scaling_gates/known_template_source_closure_reference_inventory_review_gate.json` record that 137 tracked launch templates previously contained only two complete source-closure templates. One is the legacy paged-attention filelist template without reference/hash metadata, and one is its copied derivative. `config/scaling_gates/known_template_source_closure_independent_reference_promotion_gate.json` selects `PULP_ITA.pulp_ita_mha` as the first independent complete-reference promotion candidate. `config/scaling_gates/known_template_source_closure_independent_reference_promotion_result_gate.json` records the metadata promotion with `source_closure.status=complete`, `source_file_count=29`, and source-file hash `073d53d91f23bf47eb907188096c21672b36801ed6fd7f8d218130c913322b89`. `config/scaling_gates/known_template_source_closure_independent_reference_promotion_review_gate.json` accepts it as metadata-only evidence, and `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_independent_reference_promotion_review_gate.json` selects copy breadth validation next. This adds no new execution or timing claim.

Known-template source-closure copy breadth validation definition: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_gate.json` fixes the next dry-run-only validation boundary. It includes one paged-attention copied-lineage regression case, one independent `PULP_ITA.pulp_ita_mha` reference-copy case, and one requested-source-absent refusal case. This is definition-only and adds no materialization, build/run/compare, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation claim.

Known-template source-closure copy breadth validation dry-run result: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_dry_run_result_gate.json` records the two accepted dry-run results and one refusal result. The accepted cases emitted complete copied source-closure metadata for the paged-attention copied-lineage regression and the independent `PULP_ITA.pulp_ita_mha` reference-copy case. The refusal case exited `1` because the requested source was absent from the copied closure. This is dry-run evidence only.

Known-template source-closure copy breadth validation dry-run review: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_dry_run_review_gate.json` accepts the dry-run result only as policy/breadth evidence and keeps materialization, execution, timing, speedup, arbitrary dependency inference, native Verilator support, and optimal GPU allocation out of scope. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_validation_dry_run_review_gate.json` selects materialization definition next.

Known-template source-closure copy breadth materialization definition: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_gate.json` defines the tracked-source write boundary for the reviewed MHA-copy dry-run. It permits exactly three new `filelist_known_template_pulp_ita_mha` source files and requires the already materialized paged-attention copied-lineage outputs to refuse overwrite. This is definition-only and adds no build/run/compare, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation claim.

Known-template source-closure copy breadth materialization result: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_result_gate.json` records the scoped source write. The existing paged-attention copied-lineage materialization refused overwrite, and the MHA-copy materialization wrote exactly the generated coverage manifest, launch template, and first benchmark gate for `filelist_known_template_pulp_ita_mha`. The generated template keeps complete copied source-closure metadata and the expected `PULP_ITA.pulp_ita_mha` reference hash. This is materialized source evidence only.

Known-template source-closure copy breadth materialization review: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_review_gate.json` accepts the MHA-copy materialized source evidence and the paged-attention overwrite refusal. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_materialization_review_gate.json` selects materialized-template dry-run definition next. This adds no Verilator build/run/compare, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation claim.

Known-template source-closure copy breadth materialized-template dry-run definition: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_gate.json` defines the `1x1 --dry-run` command-plan boundary for `config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json`. The plan must use the materialized MHA-copy source list and `src/tools/build_host_probe.py`, then end in a `coverage_output_equivalence` compare plan. This is definition-only and adds no execution or timing claim.

Known-template source-closure copy breadth materialized-template dry-run result: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_result_gate.json` records exit `0` and the expected seven-stage command plan for the materialized MHA-copy template. It uses the copied MHA source closure, `src/tools/build_host_probe.py`, planned GPU cubin build, planned hybrid run, and a final planned `coverage_output_equivalence` compare. This adds no Verilator execution, correctness, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation claim.

Known-template source-closure copy breadth materialized-template dry-run review: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_review_gate.json` accepts the command-plan evidence, and `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_materialized_template_dry_run_review_gate.json` selects non-dry-run execution definition next. The selection gate itself adds no execution, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation claim.

Known-template source-closure copy breadth materialized-template execution definition: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_gate.json` selects the matching non-dry-run `1x1` build/run/compare command for `config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json`. The later result must pass `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes. This definition adds no execution result, timing, speedup, shape breadth, arbitrary dependency inference, native Verilator option, or automatic GPU allocation claim.

Known-template source-closure copy breadth materialized-template execution result: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_result_gate.json` records the materialized MHA-copy template `1x1` non-dry-run build/run/compare passing `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes. Raw strict final-state equality remains false with `31` Verilator-internal mismatch bytes only. This remains scoped correctness evidence for the selected materialized template, not timing, speedup, shape breadth, arbitrary dependency inference, native Verilator option, or automatic GPU allocation evidence.

Known-template source-closure copy breadth materialized-template execution review: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_review_gate.json` accepts the scoped MHA-copy `1x1` execution evidence and records the generator-policy repair that copies reference Verilator args along with source closure metadata. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_execution_review_gate.json` selects public results packaging refresh before shape breadth or timing work.

Known-template source-closure copy breadth execution public-pack refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_gate.json` defines the packaging boundary for the accepted MHA-copy execution evidence. It includes the breadth source-closure copy records, materialized `filelist_known_template_pulp_ita_mha` template, generated coverage manifest, first benchmark gate, generator helpers, and optional compare report path while keeping reports/artifacts non-canonical.

Known-template source-closure copy breadth execution public-pack refresh result: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_result_gate.json` records the public-pack archive dry-run exiting `0`. The include list contains the accepted MHA-copy execution gate/result/review, materialized template, coverage manifest, first benchmark gate, `src/tools/hybrid_config_generator.py`, and optional compare report. This is packaging evidence only and creates no archive.

Known-template source-closure copy breadth execution public-pack refresh review: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_review_gate.json` accepts the packaging-only dry-run result. The next boundary is defining public benchmark pack externalization completion for the accepted MHA-copy execution refresh; this still does not add timing, speedup, shape breadth, arbitrary RTL support, native Verilator option, or automatic GPU allocation claims.

Known-template source-closure copy breadth execution public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_known_template_source_closure_copy_breadth_execution_gate.json` closes the MHA-copy publication boundary. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_execution_public_pack_refresh_gate.json` selects the Verilator-compatible GPU hybrid minimal bench suite as the next validation target.

Verilator-compatible GPU hybrid minimal bench suite: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_gate.json` adds `python3 src/tools/run_hybrid_benchmark.py --minimal-bench-suite`. The first result gate, `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_result_gate.json`, records exit `0` and a five-entry JSON descriptor for automation surface, high/low shape-fit estimates, resident decode-like mitigation, and filelist-derived execution evidence. This is suite-definition evidence, not fresh timing or broad speedup evidence.

Verilator-compatible GPU hybrid minimal bench suite run: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_run_result_gate.json` records `python3 src/tools/run_hybrid_benchmark.py --run-minimal-bench-suite` exiting `0`. It validates the operator-plan preview, state-parallel high class, single-state repeated-step low class, resident decode-like dry-run, explicit filelist source-closure metadata, and filelist MHA-copy execution evidence. Existing report evidence shows `157.725x` CPU-to-hybrid wall speedup for `paged_attention_kv_score 64x1` from `reports/pulp_paged_attention_kv_score_cpu_repeat_64x1.json` and `reports/pulp_paged_attention_kv_score_hybrid_64x1.txt`, and `2.164x` for `1x64` from `reports/pulp_paged_attention_kv_score_cpu_repeat_1x64.json` and `reports/pulp_paged_attention_kv_score_hybrid_1x64.txt`, preserving the current conclusion that state-parallel shapes are the stronger GPU-hybrid fit.

Verilator-compatible GPU hybrid minimal bench suite completion: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_run_review_gate.json` accepts the run result. `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_completion_audit.json` records the completion audit for the current objective: Verilator-compatible operator input, filelist-derived input evidence, one public command for automation checks, scoped speed tendency evidence, explicit correctness policy, and docs/tests are all present.

Next measured benchmark after minimal suite completion: `config/scaling_gates/next_measured_benchmark_selection_after_verilator_compatible_gpu_hybrid_minimal_bench_suite_completion_gate.json` selects the persistent resident decode-like follow-up because the suite already distinguishes state-parallel high-fit and single-state repeated-step low-fit cases, while resident decode-like was only dry-run checked there. `config/scaling_gates/define_persistent_resident_decode_like_followup_measurement_gate.json` defines `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3` as the next measured command. This reuses the existing `pulp_ita_mha` persistent resident ABI path and does not claim direct Verilator-native option support, arbitrary RTL support, automatic GPU allocation, runtime/ABI changes, or production LLM-serving throughput.

Persistent resident decode-like follow-up result: `config/scaling_gates/persistent_resident_decode_like_followup_measurement_result_gate.json` records the selected command exiting `0`; `config/scaling_gates/persistent_resident_decode_like_followup_measurement_review_gate.json` accepts it. The generated summary is `reports/persistent_resident_state_abi_repeat_median_summary.json`. All three repeat samples pass `coverage_output_equivalence` with maximum mismatch count `0`. Median hybrid wall is `5.692 ms`, median GPU kernel total is `5.705824 ms`, median hybrid wall per final state-step is `0.0013896484375 ms`, and median GPU kernel total per final state-step is `0.0013930234375 ms`. These numbers are scoped to `pulp_ita_mha`, `16x64`, four phases, repeat `3`, and the existing persistent resident ABI path.

Persistent resident decode-like public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_gate.json` defines the refresh boundary. `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0`; `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_review_gate.json` accepts it. The refresh includes the selection, definition, result, review, source-of-truth docs, compact selection pointer, and optional generated summary report when present. This is packaging evidence only, not a new measurement or a broader speedup claim.

Persistent resident decode-like public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_persistent_resident_decode_like_followup_measurement_gate.json` closes the public benchmark pack boundary after the accepted refresh. The completion record keeps the result scoped to `pulp_ita_mha`, `16x64`, four phases, repeat `3`, and the existing persistent resident ABI path.

Next measured benchmark selection after persistent resident decode-like refresh: `config/scaling_gates/next_measurement_selection_after_persistent_resident_decode_like_followup_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_timing_measurement_gate`. This is a selection record only; it does not add timing evidence, native Verilator option support, arbitrary RTL dependency inference, automatic optimal GPU allocation, runtime/ABI changes, or production LLM-serving throughput.

Filelist shape-breadth timing measurement definition: `config/scaling_gates/define_filelist_shape_breadth_timing_measurement_gate.json` defines four later run commands: `filelist_paged_attention_kv_score` at `32x1` and `1x32`, plus `filelist_known_template_pulp_ita_mha` at `32x1` and `1x32`. This is definition-only; it does not add timing evidence, repeat-median evidence, arbitrary RTL dependency inference, native Verilator option support, automatic optimal GPU allocation, runtime/ABI changes, or production LLM-serving throughput.

Filelist shape-breadth timing measurement result: `config/scaling_gates/filelist_shape_breadth_timing_measurement_result_gate.json` records all four scoped filelist-derived runs passing `coverage_output_equivalence` with mismatch count `0`. The two `32x1` state-parallel cases show observed CPU-to-hybrid wall speedups of `87.13301x` and `87.73713x`; the two `1x32` single-state repeated-step cases show `2.346763x` and `3.327072x`. This is single-run evidence for the exact target/shape pairs only, not repeat-median or broad speedup evidence.

Filelist shape-breadth timing measurement review: `config/scaling_gates/filelist_shape_breadth_timing_measurement_review_gate.json` accepts that four-command result as scoped evidence and selects `define_public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_gate` next. The accepted claim remains limited to the exact filelist-derived target/shape pairs, with `coverage_output_equivalence` as the correctness policy and raw full-state equality diagnostic only.

Filelist shape-breadth public-pack refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_gate.json` defines the public-pack archive dry-run boundary for the accepted four-command result. It does not add measurement, runtime/ABI changes, repeat-median evidence, native Verilator option support, arbitrary RTL dependency inference, automatic GPU allocation, or production LLM-serving throughput.

Filelist shape-breadth public-pack refresh result and review: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` and including the filelist timing definition, result, review, refresh definition, source-of-truth docs, compact selection pointers, and optional generated report snapshots. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_review_gate.json` accepts the packaging-only refresh and selects the public benchmark pack externalization completion boundary next.

Filelist shape-breadth public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_timing_measurement_gate.json` closes the public benchmark pack boundary for the accepted four-command result. This is completion-only; it adds no new measurement, repeat-median timing, runtime/ABI change, native Verilator option support, arbitrary RTL support, dependency inference, automatic GPU allocation, or production LLM-serving throughput.

Next measured benchmark selection after filelist shape-breadth public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_timing_measurement_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_repeat_median_timing_gate`. This is selection-only; it does not add repeat-median timing evidence yet, native Verilator option support, arbitrary RTL dependency inference, automatic optimal GPU allocation, runtime/ABI changes, or production LLM-serving throughput.

Filelist shape-breadth repeat-median timing definition: `config/scaling_gates/define_filelist_shape_breadth_repeat_median_timing_gate.json` fixes repeat count `3` for the same two filelist-derived targets at `32x1` and `1x32`. It records that the prior public repeat-median CLIs did not cover this exact filelist set. This is definition-only and adds no timing evidence, runtime/ABI change, native Verilator option support, arbitrary RTL dependency inference, automatic GPU allocation, or production LLM-serving throughput.

Filelist shape-breadth repeat-median workflow: `config/scaling_gates/filelist_shape_breadth_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-repeat-median 3 --dry-run` for the four filelist-derived target/shape pairs. The dry-run emits twelve compare samples and the aggregate write plan for `reports/filelist_shape_breadth_repeat_median_summary.json`; it does not add timing evidence by itself.

Filelist shape-breadth repeat-median measurement: `config/scaling_gates/filelist_shape_breadth_repeat_median_measurement_gate.json` records the non-dry-run `python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-repeat-median 3` command exiting `0`. All 12 samples pass `coverage_output_equivalence` with mismatch count `0`. Median CPU-to-hybrid wall ratios are `68.83243486073675x` for `filelist_paged_attention_kv_score 32x1`, `2.67586493987049x` for `filelist_paged_attention_kv_score 1x32`, `76.07629547960308x` for `filelist_known_template_pulp_ita_mha 32x1`, and `6.705723524656427x` for `filelist_known_template_pulp_ita_mha 1x32`. This remains scoped repeat-count-3 evidence for these exact filelist-derived templates, not broad speedup evidence, native Verilator option support, arbitrary RTL dependency inference, automatic GPU allocation, or production LLM-serving throughput.

Filelist shape-breadth repeat-median review: `config/scaling_gates/filelist_shape_breadth_repeat_median_review_gate.json` accepts the scoped measurement for public-pack refresh. The review keeps sample variability as the main weak point, especially the `filelist_known_template_pulp_ita_mha 1x32` CPU samples, so the accepted conclusion is a scoped state-parallel-over-repeated-step trend rather than paper-grade statistics or broad speedup evidence.

Filelist shape-breadth repeat-median public-pack refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_gate.json` records the public packaging boundary for the reviewed repeat-count-3 evidence. The next step is the public-pack archive dry-run; the generated summary and four median reports stay evidence-only and are not source of truth.

Filelist shape-breadth repeat-median public-pack refresh result/review: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_review_gate.json` accepts the packaging-only result. This led into the public benchmark pack externalization completion boundary for the scoped repeat-count-3 evidence.

Filelist shape-breadth repeat-median public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_repeat_median_gate.json` closes the public benchmark pack boundary for the scoped repeat-count-3 evidence. The next step is selecting the next measured benchmark after this refresh; no new measurement, runtime/ABI change, native Verilator option support, arbitrary dependency inference, automatic GPU allocation claim, or production serving claim is added by the completion gate.

Next measured workstream selection after filelist shape-breadth repeat-median public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_repeat_median_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_gate`. This is selection-only: it acknowledges that the previously deferred allocation-policy work now has repeat-median-backed filelist evidence, but still does not claim broad speedup, native Verilator support, arbitrary RTL/dependency inference, automatic optimal allocation, runtime/ABI changes, or production LLM-serving throughput.

Filelist shape-breadth GPU allocation policy definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_gate.json` defines a scoped policy boundary from the reviewed repeat-count-3 evidence. It recommends `32x1` for the two reviewed filelist-derived templates only when source closure is complete and repeat-median timing is present; unknown targets, incomplete source closure, and missing timing evidence are refused or marked low-confidence. This is definition-only and does not implement native Verilator support, arbitrary RTL/dependency inference, automatic optimal allocation for any design, runtime/ABI changes, or production LLM-serving throughput.

Filelist shape-breadth GPU allocation policy dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_result_gate.json` records `python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-gpu-allocation-policy --dry-run` exiting `0`, with JSON-only stdout, no report/artifact writes, two `32x1` high-confidence recommendations, and explicit refused/low-confidence cases. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_review_gate.json` accepts this scoped policy surface and selects `define_filelist_shape_breadth_gpu_allocation_policy_execution_gate` next.

Filelist shape-breadth GPU allocation policy execution definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_execution_gate.json` defines execution/application as applying the accepted `32x1` policy to existing tracked template command plans for the two reviewed filelist-derived targets, starting with dry-run validation. It selects `run_filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_gate` next and still does not claim non-dry-run evidence, arbitrary RTL support, native Verilator integration, runtime/ABI changes, or automatic optimal GPU allocation for any design.

Filelist shape-breadth GPU allocation policy execution dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_result_gate.json` records both policy-selected `32x1 --dry-run` tracked-template commands exiting `0`, and `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_review_gate.json` accepts the command-plan evidence. This selects `define_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate` next; no build/run/compare, new timing, native Verilator, runtime/ABI, or arbitrary allocation claim is added.

Filelist shape-breadth GPU allocation policy non-dry-run execution definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json` selects both reviewed policy-selected `32x1` tracked-template commands for non-dry-run build/run/compare. The required later acceptance is command exit `0`, expected compare reports under `reports/`, and `coverage_output_equivalence` mismatch count `0`; this definition still adds no timing, native Verilator, runtime/ABI, arbitrary RTL, or automatic optimal allocation claim.

Filelist shape-breadth GPU allocation policy non-dry-run execution result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json` records both reviewed policy-selected `32x1` commands exiting `0`, writing their expected compare reports, selecting `coverage_output_equivalence`, and passing with mismatch count `0`. Each report compares `32` state pairs over `29` output words / `116` bytes per state (`928` words / `3712` bytes total per report). `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json` accepts only that scoped execution and selects `define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate` next; raw full-state equality remains false, so this is not timing, native Verilator, arbitrary RTL, runtime/ABI, automatic optimal-allocation, or production-serving evidence.

Filelist shape-breadth GPU allocation policy non-dry-run public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json` defines a packaging-only refresh for the accepted scoped execution result. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` and including the execution definition/result/review, public source-of-truth docs, compact selection pointers, and the two compare reports as generated evidence. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json` accepts that refresh and selects `define_public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate` next; no new execution, timing, native Verilator, arbitrary RTL, runtime/ABI, automatic optimal-allocation, or production-serving claim is added.

Filelist shape-breadth GPU allocation policy non-dry-run public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json` closes the public benchmark-pack boundary after the packaging refresh. The closed scope remains the two reviewed filelist-derived `32x1` commands, `coverage_output_equivalence` mismatch count `0`, `29` words / `116` bytes per state, and raw full-state equality not required and not met. It selects `select_next_measurement_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_public_pack_refresh` next and adds no new measurement, execution, timing/speedup, native Verilator, arbitrary RTL, runtime/ABI, automatic optimal-allocation, or production-serving claim.

Next measured workstream selection after filelist GPU allocation policy non-dry-run public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate`. This is a selection-only gate: the evidence remains two reviewed filelist-derived targets at `32x1` with `coverage_output_equivalence` mismatch count `0`, and the next gate must define broader explicit shapes without claiming native Verilator option support, arbitrary RTL support, runtime/ABI changes, broad speedup, or automatic optimal allocation.

Filelist shape-breadth GPU allocation policy broader shape sweep definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate.json` defines the next dry-run boundary for the same two reviewed filelist-derived targets. The selected additional probes are `64x1` as a larger state-parallel shape and `1x64` as a larger repeated-step shape; `32x1` remains the accepted baseline and `1x32` remains the existing repeated-step control. This gate adds no new measurement, timing/speedup claim, native Verilator support, runtime/ABI change, arbitrary RTL support, or GEM comparison evidence.

Filelist shape-breadth GPU allocation policy broader shape sweep dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_result_gate.json` records all four selected `64x1` / `1x64` dry-run command plans exiting `0`, preserving `coverage_output_equivalence` as the later correctness policy and writing no generated reports. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_review_gate.json` accepts only command-plan evidence and led to the non-dry-run definition gate. This is not correctness, timing/speedup, GEM comparison, native Verilator, arbitrary RTL, runtime/ABI, or automatic optimal allocation evidence.

Filelist shape-breadth GPU allocation policy broader shape sweep non-dry-run boundary: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json` selects the four non-dry-run build/run/compare commands corresponding to the accepted dry-run plans. The boundary covers `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` at `64x1` and `1x64`; later acceptance requires exit `0`, expected compare reports, and `coverage_output_equivalence` mismatch count `0`. This definition adds no measurement, timing/speedup, GEM comparison, native Verilator option, arbitrary RTL, runtime/ABI, or automatic optimal-allocation claim.

Filelist shape-breadth GPU allocation policy broader shape sweep non-dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json` records the four accepted commands running non-dry-run. All commands exited `0`, all selected `coverage_output_equivalence`, and all reports have mismatch count `0`. The generated reports are `reports/filelist_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`, `reports/filelist_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/filelist_known_template_pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json`, and `reports/filelist_known_template_pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json`. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_review_gate.json` accepts the scoped four-command evidence and selects public results packaging refresh next; this is still not timing/speedup, repeat-median, GEM comparison, native Verilator option, arbitrary RTL, runtime/ABI, automatic optimal-allocation, production-serving, or raw full-state equality evidence.

Filelist shape-breadth GPU allocation policy broader shape sweep public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json` defines a packaging-only refresh for the accepted scoped four-command result. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` and including the execution definition/result/review, public source-of-truth docs, compact selection pointers, and the four compare reports as generated evidence. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_review_gate.json` accepts that refresh and selects `define_public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate` next; no new execution, timing/speedup, repeat-median, GEM comparison, native Verilator option, arbitrary RTL, runtime/ABI, automatic-optimal-allocation, production-serving, or raw full-state equality claim is added.

Filelist shape-breadth GPU allocation policy broader shape sweep public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json` closes the publication boundary after that public-pack refresh. The closed scope remains the four reviewed `64x1` / `1x64` commands, `coverage_output_equivalence` mismatch count `0`, `29` words / `116` bytes per state, and raw full-state equality not required and not met. It selects `select_next_measurement_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_public_pack_refresh` next and adds no new measurement, execution, timing/speedup, repeat-median, GEM comparison, native Verilator option, arbitrary RTL, runtime/ABI, automatic-optimal-allocation, production-serving, or raw full-state equality claim.

Next measured workstream selection after broader shape-sweep public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate`. The next evidence gap is timing for the same four `64x1` / `1x64` target/shape pairs; this selection adds no timing evidence by itself and keeps repeat-median, GEM comparison, native Verilator option support, arbitrary RTL/dependency inference, runtime/ABI changes, production-serving, and automatic optimal allocation as non-claims.

Filelist shape-breadth GPU allocation policy broader shape sweep timing boundary: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json` defines the four existing `run_hybrid_template.py` commands for `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` at `64x1` and `1x64`. It records the CPU, hybrid wall, GPU-kernel, speedup-ratio, per-state-step, and mismatch-count fields required by the next result gate while keeping reports generated-only. This is still definition-only, not a timing result, repeat-median result, native Verilator option, arbitrary RTL/dependency inference, runtime/ABI change, GEM comparison, production-serving, or automatic optimal allocation evidence.

Filelist shape-breadth GPU allocation policy broader shape sweep timing result: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json` records the four defined commands as single-run timing evidence. `filelist_paged_attention_kv_score` measured CPU `144.353 ms` vs hybrid wall `1.133 ms` at `64x1`, and CPU `12.4622 ms` vs hybrid wall `1.502 ms` at `1x64`. `filelist_known_template_pulp_ita_mha` measured CPU `242.812 ms` vs hybrid wall `1.133 ms` at `64x1`, and CPU `3.53559 ms` vs hybrid wall `1.817 ms` at `1x64`. All four compare reports pass `coverage_output_equivalence` with mismatch count `0`; raw full-state equality is false and non-required. This remains single-run timing, not repeat-median, broad speedup, GEM comparison, native Verilator option, arbitrary RTL/dependency inference, runtime/ABI, production-serving, automatic optimal allocation, or raw full-state equality evidence.

Filelist shape-breadth GPU allocation policy broader shape sweep timing review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json` accepts the scoped result and selects public-pack refresh definition next. The accepted claim is only that the same two reviewed filelist-derived templates pass `coverage_output_equivalence` and show the scoped single-run state-parallel-vs-repeated-step timing tendency at `64x1` / `1x64`; repeat-median, broad speedup, GEM comparison, native Verilator option, arbitrary RTL/dependency inference, runtime/ABI, production-serving, automatic optimal allocation, and raw full-state equality remain non-claims.

Next measured workstream selection after broader shape-sweep timing public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate`. The next evidence gap is repeatability for the same four `64x1` / `1x64` target/shape pairs; this selection adds no repeat-median evidence by itself and keeps broad speedup, GEM comparison, native Verilator option support, arbitrary RTL/dependency inference, runtime/ABI changes, production-serving, and automatic optimal allocation as non-claims.

Filelist shape-breadth GPU allocation policy broader shape sweep repeat-median boundary, measurement, review, public refresh, completion, next selection, and policy definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate.json` fixes `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` at `64x1` and `1x64` for repeat-count `3` timing. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_workflow_gate.json` adds the public `--filelist-broader-shape-repeat-median` workflow, `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_measurement_gate.json` records the non-dry-run result with all 12 samples passing `coverage_output_equivalence` and mismatch count `0`, `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json` accepts only the scoped result for public-pack packaging, `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json` defines the public-pack refresh, `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json` accepts the archive dry-run, `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json` closes the public-pack boundary, `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_public_pack_refresh_gate.json` selects scoped broader GPU allocation policy definition next, and `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json` defines the sidecar policy boundary. This adds scoped repeat-count-3 evidence for the exact two filelist-derived templates only; broad speedup, GEM comparison, native Verilator option support, arbitrary RTL/dependency inference, runtime/ABI, production-serving, automatic optimal allocation, and raw full-state equality remain non-claims.

Later measurement and publication gates are summarized through the current machine-readable selection state and the tracked public-pack manifest rather than by listing every local candidate record. Candidate gate files remain non-canonical until they are intentionally tracked and admitted by the manifest boundary tests.

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
| resident batch sweep | `16x64` best total wall | `1.736` | `1.665024` | `0.070976` | uploaded init-state per resident workload | existing-evidence analysis record |
| resident batch sweep | `32x64` best per-state-step wall | `2.176` | `2.141184` | `0.034816` | uploaded init-state per resident workload | existing-evidence analysis record |
| file-boundary state reuse | phase 4 `16x256` | `2.344` | `2.302016` | `0.041984` | previous phase GPU dump reloaded through files | existing-evidence analysis record |
| persistent resident ABI repeat-median | `16x64..16x256`, repeat `3` | `4.965` | `4.934624` | `0.030376` | in-process `d_storage` authoritative after phase 1 | existing-evidence analysis record |

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

For the filelist-derived shape-breadth four-shape repeat-median workflow, use:

```bash
python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-repeat-median 3
```

The aggregate report is `reports/filelist_shape_breadth_repeat_median_summary.json`.

For the filelist-derived broader-shape repeat-median workflow, use:

```bash
python3 src/tools/run_results_reproduction.py --filelist-broader-shape-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --filelist-broader-shape-repeat-median 3
```

The aggregate report is `reports/filelist_broader_shape_repeat_median_summary.json`.

For the policy-selected broader filelist repeat-median workflow, use:

```bash
python3 src/tools/run_results_reproduction.py --filelist-broader-policy-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --filelist-broader-policy-repeat-median 3
```

The aggregate report is `reports/filelist_broader_policy_repeat_median_summary.json`.

Measured repeat-count-3 medians for this scoped policy-selected run:

- `filelist_paged_attention_kv_score 64x1`: CPU `133.607 ms`, hybrid wall `0.917 ms`, GPU kernel total `0.887808 ms`, CPU-to-hybrid-wall ratio `145.7001090512541`, coverage-output mismatch count `0`.
- `filelist_known_template_pulp_ita_mha 64x1`: CPU `137.82 ms`, hybrid wall `0.986 ms`, GPU kernel total `0.953344 ms`, CPU-to-hybrid-wall ratio `139.77687626774846`, coverage-output mismatch count `0`.

For the broader scoped GPU allocation policy dry-run, use:

```bash
python3 src/tools/run_results_reproduction.py --filelist-broader-shape-gpu-allocation-policy --dry-run
```

This command writes no generated evidence.

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
python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json
```

Those three commands are the shortest operator path: discover sidecar-ready targets, inspect the terminal command plus efficiency estimate, then emit the same non-executing plan as JSON for automation.

The fuller reference remains:

```bash
python3 src/tools/run_hybrid_benchmark.py --list-targets
python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --estimate-efficiency
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --estimate-efficiency-json
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --sidecar-gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-command
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-estimate-command
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-efficiency-estimate
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json
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

Use `--list-targets` to inspect supported target names, aliases, required `--shape` or `--limit` arguments, supported modes, and the current `sidecar_gpu` option-shim discovery status before running a measurement. Use `--list-targets sidecar_gpu` for the focused sidecar discovery view referenced by operator-plan JSON discovery hints. It is a discovery command only; it does not run benchmarks, write reports, or create measurement evidence.

For ready slice-template targets, `--list-targets` also exposes `sidecar_gpu.shape_spellings`: the expanded `--sim-accel-states <N> --sim-accel-steps <S>` form, compact `--sim-accel-shape <NxS>`, and wrapper `--shape <NxS>`. The focused `--list-targets sidecar_gpu` view includes `shortest_operator_path`, matching the three documented commands above. The same block includes terminal and JSON operator-plan command templates plus concrete `64x1` non-executing commands to try immediately; these use `sidecar_gpu.recommended_entrypoint` (`--sim-accel-shape <NxS>`), while `sidecar_gpu.compatibility_entrypoint` keeps the expanded spelling explicit for future direct-Verilator compatibility.

Use `--help` on `run_hybrid_benchmark.py` for the shortest supported Verilator-like examples: target discovery, compact `--sim-accel-shape`, terminal command preview, terminal estimate-command preview, terminal operator plan, and JSON operator plan.

Use `--estimate-efficiency` on `run_hybrid_benchmark.py` for a short terminal-oriented estimate after the dry-run or execution command list. It prints the speedup class, reason, next action, scoped observed speedup when existing reports are available, and the non-claims that separate performance estimates from CPU/GPU equivalence. Use `--estimate-efficiency-json` when automation needs the same data.

Use `--sidecar-gpu` as the shortest operator-facing spelling for the existing hybrid sidecar GPU flow plus the human-readable efficiency estimate. It is an alias for usability, not a new correctness policy or a stronger speedup claim.

When `--summary-out` writes a wrapper summary and the direct-option preview can be synthesized, the summary includes the same `discovery_hint` as operator-plan JSON. This keeps generated summaries aligned with discovery while preserving the existing non-claim that dry-run summaries are not correctness or timing evidence.

The wrapper now also accepts `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` and compact `--sim-accel-shape <NxS>` as tested compatibility spellings. A `--sim-accel-*` shape spelling is enough to enter the sidecar preview path on the wrapper, while the long-term direct Verilator spelling remains explicit. `docs/verilator_sidecar_option.md` records the target `verilator --sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` interface and the non-claims that must survive that migration.

Template-target `--preflight` output now includes `sidecar_stage_plan`, a stage-level view of the intended direct-Verilator boundary: Verilator build, host probe build, CPU reference output, GPU artifact build, hybrid sidecar run, and `coverage_output_equivalence` compare. Stages include structured `details` for the Verilator build inputs, state files, launch shape, and compare policy. This is still non-executed planning evidence.

Preflight, summary, and operator-plan JSON keep raw and effective accelerator metadata separate. `operator_entrypoint.sim_accel` records the explicit selector if present, while `operator_entrypoint.effective_sim_accel` records the normalized sidecar path selected by `--sidecar-gpu` or `--sim-accel-*` shape spelling.

The stage plan also includes `verilator_option_readiness`. `ready_for_verilator_option_shim` means the plan has the minimum structured inputs needed for a future shim, but it is not execution evidence and does not claim Verilator itself implements `--sim-accel`.

`src/tools/verilator_sidecar_shim.py` is the non-executing JSON handoff for automation. It includes `efficiency_estimate` and `sidecar_stage_plan`, exits `0` for ready, `2` for not-ready target/mode, and `1` for input or planning errors with JSON on stderr.

The shim can now select one planned stage with `--stage <name> --emit-command` and expose that command at top level while still not executing it. This is intended for the future Verilator option boundary, where Verilator can consume structured stage intent without scraping the full plan.

`--emit-verilator-command` adds a more direct handoff preview: synthesized `verilator_command_argv` and shell-quoted `verilator_command` fields containing the Verilator build inputs plus `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`. This remains non-executed planning output.

`--print-verilator-command` is the terminal-only variant: it prints only the shell-quoted command when the shim is ready, while not-ready targets keep the JSON status output and exit code `2`. This command-only behavior is preserved even when invoked through the short `--sidecar-gpu` alias. `--print-verilator-estimate-command` is the matching command-only variant for an estimate-annotated future Verilator run; it prints the same command with `--sim-accel-estimate-efficiency` appended and no human estimate block.

`--print-efficiency-estimate` is the terminal-only estimate variant. It prints the speedup class, reason, next action, and non-claims carried by the JSON report without executing commands, and cannot be combined with command-only output. Not-ready targets keep the human estimate but return exit code `2`.

`--print-operator-plan` combines the terminal command preview, terminal estimate-command preview, and terminal efficiency estimate in one non-executing view. Ready targets stay terminal-oriented; not-ready targets return the same JSON status and exit code `2` used by `--operator-plan-json`. The print-only modes remain mutually exclusive so command-only output can stay script-friendly.

`run_hybrid_benchmark.py` also exposes terminal previews with the compact `--sim-accel-shape <NxS>` spelling, for example `--sim-accel-shape 64x1 --print-operator-plan` or `--sim-accel-shape 64x1 --print-verilator-estimate-command`. This is the shortest target-first terminal path from discovery to direct-option preview; the shim JSON remains the automation path for structured stage details and stable not-ready exit codes. The expanded `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` spelling remains available as the explicit future-Verilator form.

`run_hybrid_benchmark.py --sim-accel-shape <NxS> --operator-plan-json` provides the same target-first operator plan as JSON. It exits `0` with `status: planned` when ready and exits `2` with `status: not_ready_for_verilator_option_shim` when the target cannot synthesize the direct-option preview. Its `schema_role` is `target_first_operator_plan`, and its `operator_entrypoint` records the wrapper spelling and shape spelling that produced the plan. Ready reports include top-level `requested_compatibility_entrypoint`, the concrete expanded suffix included in `command`, plus `estimate_command` with `--sim-accel-estimate-efficiency`; `discovery_hint` repeats the requested compatibility spelling while linking automation back to the same `64x1` starting-shape example exposed by `--list-targets`. `requested_shape`, `recommended_shape_matches_request`, `recommended_entrypoint`, and `compatibility_entrypoint` make it explicit when the actual plan shape differs from that starting point and which spelling should be preferred. The shim remains the fuller readiness and stage-detail handoff. It is still non-executing planning output and keeps `correctness_policy: coverage_output_equivalence` separate from the efficiency estimate. Generated compare reports must be read through the selected `coverage_output_equivalence` policy; raw final-state `match` can be false without invalidating the operator plan's correctness policy.

For not-ready targets, `--operator-plan-json` also exposes top-level `missing` and `fallback_command` fields so automation can route the operator without digging into the full `sidecar_stage_plan`.

The readiness vocabulary is intentionally shared across target discovery, wrapper operator-plan JSON, and shim JSON: `ready_for_template_shape`, `ready_for_verilator_option_shim`, and `not_ready_for_verilator_option_shim`.

Wrapper `--operator-plan-json` emits the operator-plan fields at top level. Shim JSON nests the same synthesized command/handoff shape under `operator_plan` when the command is available. Both forms group command argv, shell-quoted command, estimate-command argv, shell-quoted estimate command, concrete requested compatibility entrypoint, efficiency estimate, and `coverage_output_equivalence` as the correctness policy.

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
- tracked records selected by `src/tools/results_reproduction_manifest.py` and printed by `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run`
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
