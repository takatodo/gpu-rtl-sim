# Status

## Weakest Point

The project has accumulated historical gate state in files that should describe the current operating surface. That made `config/selection.json`, `README.md`, and this status document harder to treat as source of truth.

Current cleanup policy: keep `selection.json` current-state-only, keep historical gate records under `records/scaling_gates/` with `config/scaling_gates` as a compatibility link, and keep generated evidence reproducible under `reports/` and `artifacts/` without retaining it as source of truth.

Config minimization state: `records/scaling_gates/config_minimal_surface_completion_audit.json` records that the active `config/` file count is `146`, while `632` historical gate JSON records live under `records/scaling_gates/`. The compatibility path `config/scaling_gates` remains a symlink so existing CLI/test references continue to resolve. `reports/` and `artifacts/` are generated-output directories; generated evidence may be present locally, but current decisions do not depend on those files as source of truth.

Hybrid usability state: generated templates now carry generic host-probe build metadata and can use `src/tools/build_host_probe.py` without adding a per-target Makefile rule.

Candidate template selection state: `config/scaling_gates/candidate_template_clean_checkout_selection_gate.json` selects `NVDLA.nvdla_cmac_core_mac` as the primary next build/run/compare candidate and `NVDLA.nvdla_cmac_a2cacc` as the secondary reference candidate. Both are clean-checkout-ready through the tracked `third_party/rtlmeter` submodule and `src/tools/build_host_probe.py`; PULP ITA / LLM-serving RTL, MobileViT CPU-kick, and Ibex LLM SoC kick candidates remain deferred until their dependency boundaries and generic host-probe migration status are explicit.

NVDLA minimal build/run/compare state: `config/scaling_gates/nvdla_cmac_core_mac_minimal_build_run_compare_gate.json` records the `NVDLA.nvdla_cmac_core_mac` `1x1` minimal flow. `run_hybrid_template.py` now passes template `verilator_defines`, so `SYNTHESIS` and `DESIGNWARE_NOEXIST` select the tracked `NV_DW*` shims. The gate records Verilator build, generic host-probe build, GPU cubin build, hybrid run, and CPU-vs-hybrid `coverage_output_equivalence` compare with mismatch count `0`. This remains a minimal gate, not a broad speedup or full NVDLA claim.

NVDLA shape expansion state: `config/scaling_gates/nvdla_cmac_core_mac_template_shape_expansion_gate.json` records that `8x1`, `32x1`, and `8x4` all ran through `run_hybrid_template.py` and the generic host-probe builder with CPU-vs-hybrid `coverage_output_equivalence` mismatch count `0`. Raw full-state equality is still false and timing is scoped observed evidence only; this does not promote another active seed target or claim full NVDLA execution.

Next workstream review state: `config/scaling_gates/nvdla_shape_expansion_next_workstream_review_gate.json` selects `ita_dependency_clean_checkout_boundary` next. The weaker point is that this is larger than continuing to the NVDLA `a2cacc` secondary candidate, but it addresses the actual blocker before ITA, attention, softmax, MHA, or KV-cache RTL work: making `third_party/ITA` and `third_party/common_cells` canonical and reproducible in clean checkout. This review does not add a new active seed measurement.

ITA dependency boundary state: `config/scaling_gates/ita_dependency_clean_checkout_boundary_gate.json` now makes `third_party/ITA` and `third_party/common_cells` canonical gitlink submodules in `.gitmodules`, pinned to the previously recorded commits. This is still not an ITA build/run/compare result; the next task is to pick exactly one first ITA seed, such as `ita_dotp` or `ita_softmax_top`, in a later measurement gate.

ITA first seed selection state: `config/scaling_gates/ita_first_seed_selection_after_dependency_boundary_gate.json` selects `pulp_ita_dotp` as the first ITA active seed after the canonical dependency boundary. The weak point is explicit: `ita_dotp` is only the minimal attention-score dot-product datapath and is less representative than `ita_softmax_top`, full ITA/MHA, paged attention, or KV-cache serving state. The next_task is `implement_pulp_ita_dotp_overlay_template_generic_host_probe_gate`; this selection gate does not run ITA build/run/compare, does not import the candidate overlay/template, and does not make a speedup or correctness claim.

PULP ITA dotp overlay/template state: `config/scaling_gates/pulp_ita_dotp_overlay_template_generic_host_probe_gate.json` promotes the selected `pulp_ita_dotp` overlay, coverage manifest, and launch template as source. The template uses `src/tools/build_host_probe.py` with explicit `clk_i` and `reset_like_w` metadata, and `src/hybrid/Makefile` is not expanded with a `pulp_ita_dotp_host_probe` target. This is still not an ITA build/run/compare result; the next_task is `run_pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate`.

PULP ITA dotp first build/run/compare state: `config/scaling_gates/pulp_ita_dotp_first_generic_host_probe_build_run_compare_gate.json` records `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_dotp.json --shape 1x1`. Verilator build, generic host-probe build through `src/tools/build_host_probe.py`, GPU cubin build, hybrid run, and CPU-vs-hybrid compare all completed. The selected policy is `coverage_output_equivalence`; compared output was `29` words / `116` bytes with mismatch count `0`. Raw full-state equality remains false due to Verilator-internal fields only. This is a minimal `1x1` gate, not shape expansion or broad speedup evidence.

PULP ITA dotp shape expansion state: `config/scaling_gates/pulp_ita_dotp_shape_expansion_gate.json` records `64x1` and `1x64` through the generic host-probe path. Both shapes pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`. Observed single-run timing is scoped to this dotp seed: `64x1` has CPU elapsed `150.04 ms` and hybrid wall `1.321 ms`, while `1x64` has CPU elapsed `3.23146 ms` and hybrid wall `1.600 ms`. The trend is that state-parallel `64x1` is much more favorable than single-state repeated-step `1x64`, but this is not a broad modern-NN, softmax, MHA, or LLM-serving throughput claim.

PULP ITA dotp shape expansion review state: `config/scaling_gates/pulp_ita_dotp_shape_expansion_review_gate.json` selects `ita_softmax_top_dependency_template_boundary` next. The reason is not that dotp proves broad NN speedup; the reason is that dotp has answered the minimal attention-score datapath question while still missing softmax/reduction behavior. The next_task is `define_pulp_ita_softmax_top_dependency_template_boundary_gate`, and the review explicitly does not run softmax build/run/compare or permit recursive Bender imports.

PULP ITA softmax-top dependency/template boundary state: `config/scaling_gates/pulp_ita_softmax_top_dependency_template_boundary_gate.json` promotes the `pulp_ita_softmax_top` source boundary before measurement. It uses canonical `third_party/ITA` and `third_party/common_cells` sources plus repo overlays for `pulp_ita_cluster_clock_gating_sim.sv` and `pulp_ita_softmax_top_gpu_cov_tb.sv`. The launch template now uses `src/tools/build_host_probe.py` with explicit `clk_i` and `reset_like_w` metadata, and no `src/hybrid/Makefile` host-probe target is added. This is not softmax build/run/compare yet; next_task: run_pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.

PULP ITA softmax-top first build/run/compare state: `config/scaling_gates/pulp_ita_softmax_top_first_generic_host_probe_build_run_compare_gate.json` records `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_softmax_top.json --shape 1x1`. Verilator build, generic host-probe build through `src/tools/build_host_probe.py`, GPU cubin build, CPU run, hybrid run, and CPU-vs-hybrid compare all completed. The selected policy is `coverage_output_equivalence`; compared output was `29` words / `116` bytes with mismatch count `0`. Raw full-state equality remains false with `32` Verilator-internal-only mismatch bytes. Observed single-run timing is CPU elapsed `4.17958 ms`, hybrid GPU kernel total `1.08032 ms`, and hybrid wall `1.110 ms`; this is a minimal `1x1` gate, not shape expansion or broad speedup evidence. The next_task is `run_pulp_ita_softmax_top_shape_expansion_gate`.

PULP ITA softmax-top shape expansion state: `config/scaling_gates/pulp_ita_softmax_top_shape_expansion_gate.json` records `64x1` and `1x64` through the generic host-probe path. Both shapes pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`. Observed single-run timing is scoped to this softmax-top seed: `64x1` has CPU elapsed `149.823 ms` and hybrid wall `0.922 ms`, while `1x64` has CPU elapsed `3.96133 ms` and hybrid wall `1.517 ms`. The trend is that state-parallel `64x1` is much more favorable than single-state repeated-step `1x64`, but this is not a broad modern-NN, full ITA/MHA, or LLM-serving throughput claim. The next_task is `review_pulp_ita_softmax_top_shape_expansion_and_select_full_ita_or_hold`.

PULP ITA softmax-top shape expansion review state: `config/scaling_gates/pulp_ita_softmax_top_shape_expansion_review_gate.json` selects `full_ita_mha_dependency_template_boundary` next. The reason is that dotp has covered attention-score arithmetic and softmax-top has covered softmax/reduction behavior; the remaining representativeness gap is now the integrated full ITA/MHA top-level harness. This review does not run full ITA/MHA build/run/compare, does not switch to KV-cache, MobileViT, or runtime work, and does not allow broad speedup claims. The next_task is `define_pulp_ita_mha_dependency_template_boundary_gate`.

PULP ITA MHA dependency/template boundary state: `config/scaling_gates/pulp_ita_mha_dependency_template_boundary_gate.json` promotes the `pulp_ita_mha` source boundary before fresh measurement. It uses canonical `third_party/ITA` and `third_party/common_cells` sources plus repo overlays for `pulp_ita_cluster_clock_gating_sim.sv`, `pulp_ita_tc_sram_sim.sv`, and `pulp_ita_mha_gpu_cov_tb.sv`. The launch template now records `promoted_full_ita_mha_dependency_template_boundary` and uses `src/tools/build_host_probe.py` with explicit `clk_i` and `reset_like_w` metadata; no `src/hybrid/Makefile` host-probe target is added. This is not full ITA/MHA build/run/compare yet; the next_task is `run_pulp_ita_mha_first_generic_host_probe_build_run_compare_gate`.

PULP ITA MHA first build/run/compare state: `config/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json` records `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x1`. Verilator build, generic host-probe build through `src/tools/build_host_probe.py`, GPU cubin build, CPU run, hybrid run, and CPU-vs-hybrid compare all completed. The selected policy is `coverage_output_equivalence`; compared output was `29` words / `116` bytes with mismatch count `0`. Raw full-state equality remains false with `32` Verilator-internal-only mismatch bytes, while normalized final-state equivalence passes. Observed single-run timing is CPU elapsed `2.91612 ms`, hybrid GPU kernel total `0.856064 ms`, and hybrid wall `0.891 ms`; this is a minimal `1x1` gate, not shape expansion or broad speedup evidence. The next_task is `run_pulp_ita_mha_shape_expansion_gate`.

PULP ITA MHA shape expansion state: `config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json` records `32x1` and `1x32` through the generic host-probe path. Both shapes pass CPU-vs-hybrid `coverage_output_equivalence` with mismatch count `0`. Observed single-run timing is scoped to this full ITA/MHA seed: `32x1` has CPU elapsed `72.0539 ms` and hybrid wall `0.877 ms`, while `1x32` has CPU elapsed `2.93625 ms` and hybrid wall `1.453 ms`. The trend is that state-parallel `32x1` is much more favorable than single-state repeated-step `1x32`, but this is not a broad modern-NN or production LLM-serving throughput claim. The next_task is `review_pulp_ita_mha_shape_expansion_and_select_next_workload_or_hold`.

PULP ITA MHA shape expansion review state: `config/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json` selects `result_packaging_refresh` next. The reason is that the fresh full ITA/MHA generic-host-probe chain is complete through `1x1`, `32x1`, and `1x32`, while paged attention/KV-cache scale-up and resident execution optimization already have separate historical evidence and would broaden this review boundary. The next_task is `define_public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate`; this review does not run a new workload, change runtime/ABI behavior, or claim production LLM-serving throughput.

## Goal

`modern_llm_serving_rtl_hybrid_conditions`

Current priority:

`public_benchmark_pack_externalization_ready`

Current gate:

`config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`

## Current State

The full ITA/MHA plus larger paged KV-cache goal is complete and held for review. Full MHA was retried through the current hybrid path; the fresh 1x1 run wrote `reports/pulp_ita_mha_hybrid_1x1.txt` and passed coverage-output equivalence in `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`.

Full MHA scale-up state: `64x1` and `1x64` were measured in `reports/pulp_ita_mha_64x1_1x64_scaling_summary.json`; `64x1` is GPU-favorable while `1x64` remains a weak repeated-step shape for this single run.

Prefill/decode split state: `64x1` is recorded as prefill-like and `1x64` as decode-like in `reports/pulp_ita_mha_prefill_decode_split_summary.json`; the serving implication is that hybrid favors batched/state-parallel MHA-style work more than serial single-state decode-style work.

Resident decode state: `1x64` resident mode is recorded in `reports/pulp_ita_mha_resident_decode_1x64_summary.json`; it preserves coverage-output equivalence and improves hybrid wall by about 1.91x for this single run.

Resident decode batch-parallel state: `8x64`, `16x64`, and `32x64` resident modes are recorded in `reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json`; all pass coverage-output equivalence, and `32x64` improves per-state-step wall cost by about 26.06x over `1x64` resident for this single run.

Long-goal audit state: `config/scaling_gates/modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json` now maps correctness, speed, reproducibility, and non-claims to the current MHA, paged-attention, paged-KV, prefill/decode, resident, resident batch-parallel, persistent resident ABI, and MobileViT limit-128 CPU-kick plus hybrid control-boundary evidence.

Public results state: `config/scaling_gates/public_results_packaging_gate.json` now refreshes `docs/results.md` after the persistent resident ABI measurement, MobileViT limit-128 evidence, and wrapper summary schema publication. The public benchmark pack presents the conclusion, reproduction commands, result tables, wrapper summary reports, source evidence, and non-claims for external readers.

Public results MHA refresh state: `config/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json` defines the source-of-truth refresh after the fresh `pulp_ita_mha` generic-host-probe chain. `docs/results.md` now includes the `1x1`, `32x1`, and `1x32` compare reports, single-run timing table, and gate chain references while keeping reports/artifacts generated-only. This is not a new workload measurement, not repeat-median evidence, and not a production LLM-serving throughput claim; the next_task returns to `public_benchmark_pack_externalization_ready`.

Public benchmark pack externalization readiness state: `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json` records the minimum review surfaces, smoke commands, release checks, and evidence policy for handing the refreshed pack to an external reader. The status is `ready_for_external_review`; this is a packaging/readiness audit only, not a new measurement result or stronger performance claim.

Next measurement goal selection state: `config/scaling_gates/next_measurement_goal_selection_after_public_pack_readiness_gate.json` selects `persistent_resident_state_abi_repeat_median` after public-pack readiness. The first required gate is `persistent_resident_state_abi_repeat_median_measurement_gate`, which should reuse the existing persistent resident ABI entrypoint without changing runtime ABI or adding a new workload. Paged attention/KV-cache scale-up, additional prefill/decode work, and publish-only work remain deferred; this selection does not claim production paged attention, production KV-cache memory hierarchy, model-level Transformer inference, or a new timing result yet.

Persistent resident state ABI repeat-median state: `config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3`. The generated summary is `reports/persistent_resident_state_abi_repeat_median_summary.json`; all three samples pass coverage-output equivalence with mismatch count `0`. Median hybrid wall is `4.965 ms`, median GPU kernel total is `4.934624 ms`, and median hybrid wall per final state-step is `0.001212158203125 ms`. The gate reuses the existing persistent resident ABI measurement path and forbids runtime/ABI changes or new workload claims.

Next goal after persistent resident repeat-median: `config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json` selects `public_pack_refresh_after_persistent_resident_repeat_median`. The selected first gate is `public_results_packaging_refresh_after_persistent_resident_repeat_median_gate`; paged attention/KV-cache scale-up remains the strongest later measurement candidate, but it is deferred until the new repeat-median evidence is closed into the public pack. This is selection-only packaging/review work, not a new measurement, runtime/ABI change, or production serving claim.

Public results repeat-median refresh state: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json` defines the source-of-truth refresh after the persistent resident state ABI repeat-median result. It keeps `docs/results.md`, README, status, roadmap, and selection aligned around `reports/persistent_resident_state_abi_repeat_median_summary.json` as generated evidence only. The next_task returns to `public_benchmark_pack_externalization_ready`.

Reproduction state: `src/tools/run_results_reproduction.py --dry-run` now prints the representative MHA, resident decode, resident batch-decode, and paged-attention KV-score command sequence from one public entrypoint.

Repeat-median reproduction state: `src/tools/run_results_reproduction.py --repeat-median 3` measured `64x1`, `1x64`, `1x64` resident, `32x64` resident, and paged-attention KV-score `64x1`. The aggregate report is `reports/results_reproduction_median_summary.json`; all five median workloads pass coverage-output equivalence with mismatch count `0`.

Resident optimization state: `config/scaling_gates/resident_execution_optimization_next_gate.json` records that `1x64` resident median wall is `0.803x` vs non-resident `1x64`, while `32x64` resident improves wall per state-step by `33.70x` over `1x64` resident. The reproduction flow now generates init-state explicitly, captures compare stdout, records per-state-step metrics, and has a resident batch sweep CLI. The next workstream is to run and record that sweep, not to claim that resident mode alone fixes single-request decode latency.

Resident batch sweep state: `config/scaling_gates/resident_batch_sweep_measurement_gate.json` records `1x64`, `8x64`, `16x64`, and `32x64` resident median measurements from `reports/resident_batch_sweep_summary.json`. All pass coverage-output equivalence with mismatch count `0`. `16x64` has the best total wall median at `1.736 ms`; `32x64` has the best wall per-state-step median at `0.0010625 ms`, a `28.01x` improvement over `1x64` resident.

Resident batch sweep review: `config/scaling_gates/resident_batch_sweep_review_gate.json` selects `resident_state_reuse_experiment` next. Paged-attention/KV-cache scale-up remains deferred, but the current evidence points first at reducing resident decode-like host/GPU boundary cost while preserving coverage-output equivalence.

Resident state reuse experiment state: `config/scaling_gates/resident_state_reuse_experiment_gate.json` defines the experiment contract before any runtime ABI change and now has the public dry-run CLI. It fixes `coverage_output_equivalence`, a `16x64` default shape, four resident phases, explicit state authority rules, and a phase model where phases 2..N start from the previous phase GPU dump while comparing against cumulative CPU repeat references.

Resident state reuse measurement state: `config/scaling_gates/resident_state_reuse_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --resident-state-reuse 16x64 --resident-state-reuse-phases 4`. The summary is `reports/resident_state_reuse_experiment_summary.json`; all four phases pass coverage-output equivalence with mismatch count `0`. Phase 4 (`16x256`) has the best measured wall time per state-step at `0.000572265625 ms`. This is file-boundary state reuse, not a persistent in-GPU resident state ABI change.

Resident state reuse review: `config/scaling_gates/resident_state_reuse_review_gate.json` selects `persistent_resident_state_abi_probe` next. Paged-attention/KV-cache scale-up remains deferred, not cancelled. The selected next gap is to initialize device resident state once and advance multiple phases without reloading the previous phase GPU dump through a file boundary.

Persistent resident state ABI probe state: `config/scaling_gates/persistent_resident_state_abi_probe_gate.json` defines the probe before any runtime change and implements the public dry-run command `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --dry-run`. The planned report is `reports/persistent_resident_state_abi_probe_summary.json`. Non-dry-run execution is rejected until the implementation gate exists. This gate explicitly rejects a persistent-state claim if the next phase is implemented by reloading the previous phase GPU dump through `--init-state`.

Persistent resident state ABI implementation gate: `config/scaling_gates/persistent_resident_state_abi_probe_implementation_gate.json` now records the probe-only runtime surface. `src/tools/run_vl_hybrid.py` exposes persistent handle and phase flags, `src/hybrid/run_vl_hybrid.c` reads matching `RUN_VL_HYBRID_*` environment variables, and phase > 1 rejects deterministically until real device handle persistence exists. Existing resident and file-boundary state-reuse flows remain available.

Persistent resident device handle storage gate: `config/scaling_gates/persistent_resident_device_handle_storage_gate.json` records the first real process-scoped persistence measurement. `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4` writes `reports/persistent_resident_state_abi_probe_summary.json`; all four phase compares pass coverage-output equivalence with mismatch count `0`. The same in-process `d_storage` allocation is authoritative after phase 1 initialization, and phase dumps are diagnostic/compare evidence only.

Persistent resident storage review: `config/scaling_gates/persistent_resident_device_handle_storage_review_gate.json` records the scoped condition goal as satisfied and holds for review. Optional followups are cross-process persistent CUDA state, paged-attention/KV-cache scale-up, repeat-median timing for persistent resident ABI, and public results packaging refresh.

Public benchmark pack externalization state: `config/scaling_gates/public_results_packaging_gate.json` previously pointed the work at `public_benchmark_pack_externalization_ready`: keeping the public pack understandable to external readers by spelling out how to read the evidence, what generated reports mean, what prerequisites each path has, and which non-claims bound the result. The current gate is now `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`, which closes the newest persistent resident ABI timing evidence into the public pack. `docs/results.md` also carries the MobileViT `limit 128` ImageNet evidence as CPU-kick accuracy plus hybrid RTL control-boundary coverage-output equivalence, with explicit non-claims for RTL logits and full 50k ImageNet. The one-command entrypoint for that evidence is `python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128`.

Public reproduction smoke state: `docs/results.md` now records the first dry-run command set for external readers. This smoke validates public CLI parsing and command expansion only; it is not correctness or timing evidence.

Public archive dry-run state: `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` now prints the public pack include/exclude plan and the non-executed archive command without creating an archive. Archive files remain generated outputs and are not source of truth.

Generic benchmark CLI state: `config/scaling_gates/generic_hybrid_benchmark_cli_gate.json` adds `src/tools/run_hybrid_benchmark.py` as a target-oriented wrapper over existing proven flows. Initial supported dry-run targets are `pulp_ita_mha --shape`, `paged_attention_kv_score --shape`, and `mobile_vit --limit 128`; `pulp_ita_mha` also supports `--mode resident-state-reuse` and `--mode persistent-resident-state-abi`. The reusable dispatch lives in `src/tools/hybrid_benchmark.py`. `--summary-out` adds a unified generated summary schema for the wrapper, including target, shape or limit, mode, commands, expected reports, and collected coverage-output evidence when the benchmark is actually executed; dry-run summaries are marked as non-evidence. Fresh wrapper smokes for `pulp_ita_mha 1x1`, `paged_attention_kv_score 1x1`, `pulp_ita_mha 1x1 resident-state-reuse phases=2`, and `pulp_ita_mha 1x1 persistent-resident-state-abi phases=2` wrote matching `reports/hybrid_benchmark_*.json` summaries; all passed coverage-output equivalence with mismatch count `0`. `mobile_vit --limit 128 --summary-from-existing` writes `reports/hybrid_benchmark_mobile_vit_template_limit128.json` from the already generated MobileViT limit-128 reports without rerunning inference or hybrid commands.

The active conclusion is:

- CPU vs hybrid coverage-output equivalence passes on the selected MHA and paged KV evidence.
- Many independent states per launch are the favorable shape.
- Single-state repeated launches remain the weak shape.
- Current evidence is scoped to coverage-output equivalence, not raw Verilator internal state equivalence.

## Source Of Truth

Canonical current state:

- `config/README.md`
- `config/selection.json`
- `docs/status.md`
- `docs/roadmap.md`
- `README.md`

Generated evidence paths, regenerated by documented commands when needed:

- `reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json`
- `reports/pulp_ita_mha_first_hybrid_benchmark_summary.json`
- `reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json`
- `reports/results_reproduction_median_summary.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`
- `reports/persistent_resident_state_abi_probe_summary.json`
- `reports/persistent_resident_state_abi_repeat_median_summary.json`
- `reports/mobile_vit_hybrid_128_summary.json`
- `reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- `reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json`
- `reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json`
- `reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json`
- `reports/hybrid_benchmark_mobile_vit_template_limit128.json`

## Completed Gates

- `neural_network_rtl_paged_kv_cache_large_scaleup_gate.json`
- `neural_network_rtl_paged_kv_cache_large_review_gate.json`
- `neural_network_rtl_full_ita_mha_dependency_audit_gate.json`
- `neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json`
- `neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json`
- `neural_network_rtl_paged_attention_kv_score_harness_gate.json`
- `full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json`
- `hybrid_verilator_like_config_and_probe_generation_gate.json`
- `full_mha_hybrid_try_completion_audit.json`
- `full_mha_scaleup_64x1_1x64_gate.json`
- `prefill_decode_split_mha_benchmark_gate.json`
- `resident_decode_optimization_probe_gate.json`
- `resident_decode_batch_parallel_probe_gate.json`
- `modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json`
- `public_results_packaging_gate.json`
- `public_benchmark_pack_externalization_readiness_audit.json`
- `next_measurement_goal_selection_after_public_pack_readiness_gate.json`
- `public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json`
- `public_benchmark_pack_goal_completion_audit.json`
- `one_command_reproduction_flow_gate.json`
- `repeat_median_results_reproduction_gate.json`
- `resident_execution_optimization_next_gate.json`
- `resident_batch_sweep_measurement_gate.json`
- `resident_batch_sweep_review_gate.json`
- `resident_state_reuse_experiment_gate.json`
- `resident_state_reuse_measurement_gate.json`
- `resident_state_reuse_review_gate.json`
- `persistent_resident_state_abi_probe_gate.json`
- `persistent_resident_state_abi_probe_implementation_gate.json`
- `next_goal_selection_after_persistent_resident_repeat_median_gate.json`
- `persistent_resident_state_abi_repeat_median_measurement_gate.json`
- `public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`
- `persistent_resident_device_handle_storage_gate.json`
- `persistent_resident_device_handle_storage_review_gate.json`

## Active Harness Surface

- `overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv`
- `pulp_paged_kv_cache_large_host_probe`
- `tc_sram`

## MobileViT CPU-Kick State

MobileViT remains CPU-kick evidence:

- `mobile_vit_cpu_kick_imagenet_accuracy`
- `mobile_vit_cpu_kick_rtl_hybrid_boundary`
- `apple/mobilevit-small`
- `complete_full_imagenet_validation_cpu_kick_accuracy_measured`
- `top-1 0.77022`
- `mobile_vit_cpu_kick_rtl_proxy_host_probe`
- `mobile_vit_hybrid_imagenet_eval_gate`

The current gate for this branch is `records/scaling_gates/mobile_vit_hybrid_imagenet_eval_gate.json`. It defines `src/tools/mobile_vit_hybrid_imagenet_eval.py`, which splits an ImageNet manifest into `mobile_vit_cpu_kick_rtl_proxy` hybrid control-boundary batches while computing top-1/top-5 from CPU-kick predictions. A two-image scoped ImageNet run from the local HF parquet cache executed through hybrid and passed coverage-output equivalence; the follow-up `limit 128` scale-up also executed as one `cfg_batch_length=128` hybrid batch and passed coverage-output equivalence. The retained 128 summary is `reports/mobile_vit_hybrid_128_summary.json`: `evaluated_count=128`, `top1_accuracy=0.7734375`, `top5_accuracy=0.953125`, `coverage_output_equivalence_complete=true`. The completion audit is `records/scaling_gates/mobile_vit_hybrid_imagenet_limit_128_scaleup_completion_audit.json`. This is still not a claim that MobileViT numerical logits are produced by RTL or that the full 50k validation set was rerun through hybrid.
