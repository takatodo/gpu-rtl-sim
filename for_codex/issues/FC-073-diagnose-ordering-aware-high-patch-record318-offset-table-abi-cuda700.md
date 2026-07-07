# FC-073: Diagnose Ordering-Aware High Patch Record 318 Offset-Table ABI CUDA700

Status: in progress
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/73
Parent: FC-069 / https://github.com/takatodo/gpu-rtl-sim/issues/69
Related: FC-067 / https://github.com/takatodo/gpu-rtl-sim/issues/67, FC-068 / https://github.com/takatodo/gpu-rtl-sim/issues/68
Target files: `src/hybrid/run_vl_hybrid.c`, `src/passes/vlgpugen.cpp`, `src/tools/gategpt_testbench_probe.py`, `tests/contract/test_gategpt_testbench_probe.py`, `README.md`, `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, `for_codex/issues.md`

## Objective

Diagnose the FC-069 full-logical-phase ordering-aware token-loop CUDA700 boundary for high-patch record `318`.

## Latest Update

Stage116 residual CFG-edge boundary probing is implemented and locally measured on the Stage114 census-bearing 2-state full-phase probe. Stage109 still reports `same_saved_addr_changed` after high-eval callee0, Stage110 direct callee0 body/store watchpoint remains `clean_no_body_store`, and Stage111 maps `source_id=5` to `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`. Stage112 split-range probing has checked source ids `1..13134` and all `13,134` nested-body store candidates are clean for the adjacent pair-offset write window. Stage113 direct deeper-call boundaries are also clean.

`reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage114_candidate_census_range_1_228_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage114_candidate_census_range_129_128_runtime.json` record the refreshed Stage114 census runs. They show `11,954` non-store memory-effect candidates in the Stage111 nested callee: `11,951` diagnostic-origin atomicrmw candidates, `0` cmpxchg candidates, and `3` design-origin LLVM memory intrinsic candidates. The design-origin candidates are source ids `1..3`, covered by the refreshed clean `1..128` run; the refreshed `129..256` run is also clean and diagnostic-only. Stage114 clean summaries still show `before_direct_param_record318=0`, `after_direct_param_record318=38666621`, `after_saved_addr_record318=38666621`, `target_overlaps_window=false`, `saved_after_polluted=false`, `view_mask=0`, and `mismatch_count=2`.

`reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage115_refined_same_saved_addr_runtime.json` records the refreshed Stage115 run. It keeps Stage114 clean and census-complete (`selected_design_origin_count=3`, `design_origin_candidate_count=3`, `stage114_design_origin_census_complete=true`) and classifies the remaining boundary as `token_loop_stage115_phase1_stage114_design_origin_clean_residual_high_eval_callee0_same_saved_addr_pollution` with `stage114_design_origin_clean_residual_source=stage108_after_callee_stage109_same_saved_addr_stage114_clean`.

`reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_1_228_runtime.json` records the first Stage116 residual CFG-edge run. An initial attempt exposed an instrumentation bug: Stage116 inserted entry probes into EH pad successors, which made `opt-18` reject the generated IR because `landingpad` was no longer the first non-PHI instruction. The current implementation excludes EH pads and the refreshed report reaches runtime. `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_129_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_385_128_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_513_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_769_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_1025_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_1281_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_1537_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_1793_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_2049_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_2305_256_runtime.json` and `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_2561_190_runtime.json` record the follow-up ranges. Together they classify CFG-edge entry-after-PHI source ids `1..2750 / 2750` as clean with `classification=token_loop_stage116_phase1_callee0_nested_body_residual_boundary_clean`, `split_result=clean_no_residual_boundary`, `source_id=0`, `before_direct_param_record318=0`, `after_direct_param_record318=38666621`, and `after_saved_addr_record318=38666621`.

Current classification: Stage124 transition probing has not found final write-source authority. Stage118 block `1760` is clean/raw-clean through candidate `2021`, and Stage119/120 narrow the dirty area to the compact CFG-clone producer-selector skipped span. Stage121 source611/source613/source615/source618/source620/source624 evidence classifies known diagnostic atomics as counter perturbations, and source622 becomes clean only with `VLGPUGEN_STAGE121_DIAGNOSTIC_MARKER_READ_SOURCE_IDS=622`, so it is marker-read perturbation. Stage121 now suppresses selected diagnostic atomics/marker reads across the Stage120 candidate set before the after-read is inserted. The source625 global-suppression run is clean after those diagnostic targets are neutralized. Stage122 expanded-progress ABI reaches runtime with two lifecycle events at `boundary_kind=non_diagnostic_lifecycle_after_suppressed_span`, but reports no concrete record318/adjacent-window writer. Stage123 source1324 is excluded as adjacent diagnostic-counter traffic after the source1324-suppressed report removes its event while CPU oracle mismatch remains `2`/`0` and record318 remains polluted. Stage124 adds `VLGPUGEN_STAGE124_RECORD318_TRANSITION_PROBE=1`: the full `1..1536` run `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage124_record318_transition_source1_1536_after_source1324_suppression_ptxas300_runtime.json` times out in `ptxas`, while source windows/runs through source975 (`source1..256`, `source257..512`, `source513..768`, `source769..896`, source897,count128, source960,count1, source968,count1, source972,count1, source974,count1, and source975,count1) reach runtime with `stage124_record318_transition_found=false`, `mismatch_count=2`, and `semantic_authority=false`. Unsuppressed source976,count1 is incomplete, but adding source976 to Stage121 diagnostic atomic suppression restores source976 completion; source977,count1 through source1005,count1 also complete with no transition. Unsuppressed source1006,count1 is incomplete, but adding source1006 to Stage121 diagnostic atomic suppression restores source1006 completion with `transition_found=false` and no semantic authority. Source1007,count1 through source1019,count1 reach runtime under the source976/source1006 suppression frontier with `transition_found=false`, `scan_complete=true`, and no semantic authority. Unsuppressed source1020,count1 is incomplete; adding source1020 to Stage121 diagnostic atomic suppression restores source1020 completion with `transition_found=false`, `scan_complete=true`, and no semantic authority. Source1021,count1 through source1028,count1 reach runtime under the source976/source1006/source1020 suppression frontier with `transition_found=false`, `scan_complete=true`, and no semantic authority. Dirty Stage117 block boundary `source_id=1760` remains upstream context.

Current next action: `advance_stage124_source1029_after_sources976_1006_1020_diagnostic_atomic_suppression_cuda700`.

Source611, source613, source615, source618, source620, source622, source624,
source625 global-suppression, Stage123 source940 IR/runtime evidence, the
source1325..1536 tail scan, and the source1324 suppression/exclusion run are
complete enough to avoid treating the diagnostic counter/marker series as final
write-source authority. Do not continue by mechanically extending
producer-selector diagnostic suppression ids. Stage122 already expanded the
progress ABI and showed that the first dirty lifecycle edge has no concrete write
target; Stage123 source1324 then found a reproducible adjacent candidate that
maps to CFG-clone liveout counter traffic, and suppressing source1324 removes
only that adjacent event while record318 remains polluted. The next useful work
is to instrument the still-dirty record318 transition path that Stage123 does
not classify as a concrete store/atomic/mem-intrinsic writer. Keep final
write-source authority unclaimed until that validation is complete.

Stage117 update: the previous `1..256` report is not accepted as Stage117 runtime evidence because generated IR lacked Stage117 instrumentation due stale `vlgpugen` pass-tool build order. Pass-tool freshness is now fixed so stale pass tools rebuild before IR generation. With the lightweight saved-address Stage117 probe and a 900s `ptxas` bound, `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_light_block_body_boundary_range_1_2048_ptxas900_runtime.json` reaches runtime: all three entry slices pass `ptxas`, preflight passes, and classification is `token_loop_stage117_phase1_callee0_nested_body_block_body_boundary_same_saved_addr_changed`. The first `COUNT=1024` run was clean, but `COUNT=2048` finds a dirty Stage117 block-body boundary at `source_id=1760` with `split_result=same_saved_addr_changed`, `before_direct_param_record318=0`, `after_direct_param_record318=38666621`, `after_saved_addr_record318=38666621`, `saved_after_polluted=true`, and `semantic_authority=false`. Stage117 source-id mapping is now parser-backed: `source_id=1760` maps to `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:834516` metadata row, control-word line `333831`, reconstructed block `vl_batch_gpu.ll:327571` / `%19690`, and first Stage117 probe line `327575` in `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`; `control_word=72058702139492064`. This is a dirty boundary, not final adjacent-window write-source authority.

Stage119/120/121/122/123/124 implementation update: skipped-span boundary probing for the Stage118-exhausted residual is implemented. Stage119 instruments contiguous spans that Stage118 intentionally skips, including compact CFG-clone/probe spans such as `compact.cfg_clone`, `producer_selector`, `materialized_store`, and `liveout`. Stage120 instruments instruction boundaries inside one mapped skipped span using `VLGPUGEN_STAGE120_BLOCK_SOURCE_ID`, `VLGPUGEN_STAGE120_SKIP_SPAN_SOURCE_ID`, `VLGPUGEN_STAGE120_INSTRUCTION_START`, and `VLGPUGEN_STAGE120_INSTRUCTION_COUNT`; `VLGPUGEN_STAGE120_SPAN_EDGE_PROBE=1` instruments the aggregate skipped-span entry-to-exit edge with `boundary_kind_id=6`, `VLGPUGEN_STAGE120_AGGREGATE_EDGE_PROBE=1` instruments prefix aggregate edges with `boundary_kind_id=7`, and `VLGPUGEN_STAGE120_LOW_PERTURBATION_PROBE=1` removes the before/saved-address observation for after-only classification. Stage123 adds concrete write-window bisection with `VLGPUGEN_STAGE123_CONCRETE_WRITE_WINDOW_BISECTION_PROBE=1`; Stage124 adds post-suppression transition probing with `VLGPUGEN_STAGE124_RECORD318_TRANSITION_PROBE=1`. Runtime prints the skipped-span instruction boundary, Stage122 lifecycle probe, Stage123 concrete write-window probe, and Stage124 transition probe; the progress fallback grew to 192 counters, with Stage122 expanded-ABI slots at `168..175`, Stage123 slots at `176..183`, and Stage124 slots at `184..191`.

Stage118 ptxas-surface follow-up: `rtlmeter_vortex_ptx_entry_slice.py` now avoids treating semicolon-terminated `.func` declarations as function bodies, with a focused contract test. A dry-run regeneration report, `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_reduced_probe.json`, still produces large Stage118 slices (`762827`, `762985`, and `766310` lines), so this parser fix is correct but not sufficient; the next work remains shrinking retained prefix/global/reachable PTX surface or slice freshness before retrying `ptxas`.

Stage118 slice-freshness and split-surface mitigation: `gategpt_entry_sliced_cubin_chain.py` now writes a `*.cubin.slice.json` manifest after a successful `ptxas` run and only reuses an existing CUBIN when the current slice content hash, CUBIN path, GPU target, and ptxas options match that manifest. The entry-sliced specs now keep `vl_eval_batch_gpu` and `vl_patch_eval_pair_cycle_loop_batch_gpu` out of the helper support/feedback CUBINs because those symbols are already available from the token-loop slice. `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_default_split_ptxas1_probe.json` shows the helper slices shrink to `418` and `483` lines and both pass `ptxas` within a 1s bound; the remaining blocker is the token-loop slice at `766310` lines, which still times out. This narrows the ptxas blocker from three huge slices to one huge token-loop slice; it does not identify the final adjacent-window write source.

Stage118 token-loop stub-surface diagnosis: `rtlmeter_vortex_ptx_entry_slice.py --stub-func` can now replace selected reachable `.func` bodies with ret-only diagnostic stubs for ptxas-surface experiments only. `reports/gategpt_tb_core_stage118_token_loop_stub_slice_probe.json` stubs `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` and `__vlgpu_compact_cluster_outline_frame_stub`, reducing the token-loop slice from `766310` to `5066` lines; `ptxas` then produces `artifacts/gategpt_tb_core_ptx_entry_slice_stage118_stub_probe/vl_tb_core_ordering_aware_phase_resident_token_loop_gpu.cubin`. This confirms the remaining ptxas blocker is the reachable high-eval callee/compact-outline body surface, not the token-loop entry body itself. The stub CUBIN is not runtime evidence and must not be used to classify Stage118 instruction range `1281`.

Stage112 source-summary guardrail: `src/tools/gategpt_stage112_store_source_summary.py` joins Stage112 runtime events with the LLVM metadata map without promoting static rows to runtime authority. `reports/gategpt_tb_core_stage112_store_source_static_candidate_summary.json` records static source candidates `1415` and `1533` as `_Z40Vtb_core___024root___nba_sequent__TOP__0` `expected_liveout` zero-clear stores, but the paired runtime report is `clean_no_nested_body_store` with `source_id=0`, so `runtime_authority=false`. These rows are useful suspects for static review, not final adjacent-window write-source authority.

Stage118 opt-in guard surface probe: the earlier `1281,count=64` 120s ptxas-only blocker is now superseded. The same opt-in guard with a 300s `ptxas` bound reaches runtime for `1281..1344` and `1345..1408`; both raw Stage118 events are `clean_no_instruction_boundary`, but their report-level classifier fields remain stale pre-fix Stage112-incomplete results. Classifier-fixed runtime reports now cover `1409..2021` clean, and the later `2049..2112` request is exhausted by metadata.

Stage118/119/120 runtime update: prior Stage118 reports classify `1..1280` clean; opt-in-guard 300s reports add raw-clean runtime events for `1281..1344` and `1345..1408`; classifier-fixed runtime classifications cover `1409..2021` clean. The Stage118 `2049..2112` request classifies `token_loop_stage118_phase1_callee0_nested_body_block_instruction_boundary_range_exhausted_diagnostic_alias_clean` with `candidate_count=max_source_id=2021`, `selected_count=0`, `instrumented_count=0`, and `range_exhausted=true`; the existing diagnostic allocation alias scan is complete/clean, so the residual is not explained by a known diagnostic allocation overlap. Extended Stage119 finds dirty `source_id=2` and maps it to `compact.cfg_clone.entry_phi.producer_selector.counters3969`; Stage120 ranges `1..1536 / 1536` inside that mapped span are clean, and the `1537..1792` follow-up is metadata-exhausted. The aggregate span-edge probe is dirty. Regular aggregate-edge prefix bisection with target metadata converged to clean `source609` and dirty `source610`; low-perturbation probing then made `source610` clean and left `source611` dirty as `after_only_polluted`.

No semantic pass, speedup, usefulness, 16-state scale, runtime-noop, semantic-guard, proof-complete, actual-valid authority, or broad gateGPT PASS/FAIL authority is claimed.

## Current Evidence

`reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_light_block_body_boundary_range_1_2048_ptxas900_runtime.json` records the current fresh lightweight Stage117 attempt. With `VLGPUGEN_STAGE117_BOUNDARY_START=1`, `VLGPUGEN_STAGE117_BOUNDARY_COUNT=2048`, and a 900s `ptxas` bound, all three entry slices pass `ptxas`, preflight passes, and the run reaches runtime classification `token_loop_stage117_phase1_callee0_nested_body_block_body_boundary_same_saved_addr_changed`. The event has `source_id=1760`, `split_result=same_saved_addr_changed`, `before_direct_param_record318=0`, `after_direct_param_record318=38666621`, `after_saved_addr_record318=38666621`, `saved_after_polluted=true`, `direct_before_after_changed=true`, and `semantic_authority=false`. The prior fresh `COUNT=1024` run remains clean evidence for the first one thousand twenty-four source ids, while this run identifies a dirty Stage117 block-body boundary, not the final adjacent-window write source. Current IR mapping evidence points to `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:834516` metadata row and reconstructed block `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:327571` / `%19690` in `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`; the patched control-word store is `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu_patched.ll:333201`, `control_word=72058702139492064`. `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_block_body_boundary_range_1_64_runtime.json` records the earlier 300s ptxas blocker for the non-lightweight range, and the older `1..256` report is kept only as stale-build-order evidence. Stage116 residual-boundary reports remain the preceding clean boundary evidence; Stage115, Stage114, Stage113, and Stage112 reports retain the prior narrowing history.

Interpretation: the wrong value is not merely a stale progress slot. Generated IR/PTX inspection shows stage76 slot7 is stored directly from the actual high-patch offset-table load (`%high_off` / `ld.global.u64`), stage77 shows that same loaded offset drives `high_dst = storage_base + 38666621`, stage78 shows pointer provenance is correct while a raw-address reload reads the same wrong value, stage79 shows the wrong value is visible from the token-loop cycle-entry sample onward, stage80 narrows the first observed transition to after state setup but before `CycleCondBB`, stage81 narrows it further to after phase set, stage82 narrows it to after the edge-split pre-cycle-cond bridge but before/at the first `CycleCondBB` load, stage83 proves the record-318 pointer delta is correct while repeated same-address loads agree on `38666621`, stage84 proves the pair-offset base/address still match expected while record319 is also wrong at CycleCondBB, stage85 proves pre-cycle record318/319 are clean but CycleCondBB changes to wrong const-pool-like values, stage86 proves the observed bad CycleCondBB tuple is on the backedge (`predecessor_id=2`, `cycle_idx=26`) while the carried clean pre-cycle value remains `0`, stage87 shows the high-patch store destination on that backedge is not in the pair-offset record317..320 window, and stage88 proves the CycleCondBB base/delta/address are still correct while typed/raw/byte reload views all read the same wrong value. PTX inspection closes the earlier next-action: the CycleCondBB loads are emitted as `ld.volatile.global.u64 [%rd18+2544]` where `%rd18` is `cvta.to.global.u64 param_1`, and stage88 stores use `param_1` as the recorded base. Host launch inspection closes the corresponding ABI concern: `params[1]` is `&d_pair_offsets`, with `d_pair_offsets = schedule->d_offsets + low_start*sizeof(size_t)`, and existing diagnostics record `token_loop_arg_pack_pair_offsets_matches_probe=true`. Stage89 shows direct `param_1+2544`, typed, raw, and byte reload views all read `38666621` on the backedge while the carried pre-cycle value remains `0`. Stage90 carries the `HighEvalDoneBB` direct reload into `CycleCondBB` by PHI and compares it with CycleCond direct/typed/byte reloads under a sealed `progress_stage=90` / `epoch_coherent=true` snapshot. It records HighEvalDone direct `38666621` and CycleCond direct/typed/byte `38666621`, while the carried clean pre-cycle value remains `0`. Stage91 then adds a HighEval-entry start marker before the entry direct reload, but the run still reports `progress_stage=90`. Stage92 adds a post-high-patch-store tuple after `B.CreateAlignedStore(HighPatchValue, HighDst, Align(1))`, but the refreshed run still reports `progress_stage=90`; therefore the kernel faults before completing that store. Stage93 records the OOB target, and Stage94 suppresses the OOB store before creating the real pointer. Stage95 host-side labels show the pair-offset table is clean after upload and at phase 1 pre-launch, then polluted at phase 1 post-sync. Stage96 adjacent-record parsing shows records `318..322` have uploaded-offset mismatches, records `319..322` are polluted in addition to target record `318`, pair-values remain matched, and phase 2 pre-launch inherits the same mismatch set. Stage97 shows the phase 1 general launch argument/table alias scan is clean. Stage98 shows intended internal writer destinations are also clean with `internal_writer_count=0`. Stage99 shows diagnostic allocation aliases are also clean. Stage100 shows the high-patch store/guard device watchpoint is complete and clean (`write_source_found=false`). Stage101 shows the low_eval call-site tuple is reached and internally stable while already polluted. Stage102 shows the low-patch-to-low-eval tuple is also internally stable and already polluted at `cycle_idx=1`; therefore the next diagnostic should move before low patch/cycle entry rather than keep focusing on eval or low-patch stores.

## Tasks

- [x] Add host-side resident schedule/control-step diagnostics around record `318` before upload.
- [x] Add device-side diagnostics for the high-patch offset table consumed by the ordering-aware token loop.
- [x] Compare source schedule record `318`, uploaded/read-back record `318`, pair-table readback, and device progress observation.
- [x] Rule out wrong pair-table base, wrong stride, record-index mismatch, adjacent-record mixup, simple OOB, host read tearing, stage67 write-group incompletion, and load-address mismatch as the current boundary.
- [x] Pack stage67 epoch markers with high-patch index plus record without increasing the 10-counter ABI.
- [x] Add stage70 record/address progress markers without increasing the 10-counter ABI.
- [x] Classify the previous boundary as `stage70_loaded_offset_value_mismatch_after_matching_record_addr`.
- [x] Add stage70 after-load/storage-GEP/progress-store-source value-path markers without increasing the 10-counter ABI.
- [x] Classify the previous boundary as `stage70_loaded_offset_value_mismatch_before_storage_gep`.
- [x] Add stage70 normal-load, volatile-reload, and byte-address-reload markers without increasing the 10-counter ABI.
- [x] Classify the previous boundary as `stage70_offset_table_load_mismatch_all_reload_paths`.
- [x] Add a pre-token-loop device probe for the same pair-offset table load address.
- [x] Classify the previous boundary as `pre_token_probe_matches_pair_but_token_loop_reload_differs`.
- [x] Add a stage70 token-loop-internal sealed tuple for pair-offset base, load address, record, normal load, volatile reload, and byte reload.
- [x] Classify the previous boundary as `token_loop_stage70_tuple_base_addr_matches_but_load_differs`.
- [x] Add a stage76 same-kernel sentinel tuple for cycle-entry, pre-high-patch, and stage70 pair-offset loads.
- [x] Move the stage76 entry sample into a dedicated one-shot `cycle.entry.probe` block before the low-patch loop.
- [x] Classify the previous boundary as `token_loop_entry_pair_offset_load_already_differs`.
- [x] Diagnose same-module launch/ABI provenance for the pre-token probe and token-loop launch arg pack.
- [x] Diagnose that the wrong token-loop-loaded offset drives the storage GEP immediately before the illegal store.
- [x] Diagnose pointer provenance and raw-address reload behavior for the high-patch record `318` load.
- [x] Add a stage79 lifecycle tuple for cycle-entry, after-low-patch, after-low-eval, before-high-patch, and before-high-load record `318` offset observations.
- [x] Classify the previous boundary as `token_loop_pair_offset_wrong_at_cycle_entry_before_low_patch`.
- [x] Add a stage80 entry-to-cycle-cond tuple for token-loop entry, first progress store, state setup, cycle-cond, and cycle-entry record `318` offset observations.
- [x] Classify the previous boundary as `token_loop_stage80_pair_offset_changes_before_cycle_cond`.
- [x] Add a stage81 state-setup-to-cycle-cond tuple for state setup, predicate done, terminal-mask done, phase-set done, and cycle-cond record `318` offset observations.
- [x] Classify the previous boundary as `token_loop_stage81_pair_offset_changes_between_phase_set_and_cycle_cond`.
- [x] Split the `phase.set.done -> cycle.cond` edge and add a stage82 post-phase-set/pre-cycle-cond tuple for record `318`.
- [x] Classify the previous boundary as `token_loop_stage82_pair_offset_changes_between_pre_cycle_cond_and_cycle_cond`.
- [x] Add a stage83 sealed `CycleCondBB` entry load tuple for the record-318 pointer delta, first typed volatile load, second typed volatile load, and raw-address reload.
- [x] Classify the previous boundary as `token_loop_stage83_cycle_cond_loads_same_wrong_value`.
- [x] Add a stage84 base/neighbor/byte tuple for pair-offset base, record318 address, record317, byte-reassembled record318, and record319.
- [x] Classify the previous boundary as `token_loop_stage84_cycle_cond_neighbor_records_also_wrong`.
- [x] Add a stage85 pre-cycle-vs-CycleCondBB tuple for record318 typed/byte and record319 typed views.
- [x] Classify the previous boundary as `token_loop_stage85_cycle_cond_view_changes_after_clean_pre_cycle`.
- [x] Add a stage86 CycleCondBB boundary-source tuple for predecessor, carried pre-cycle value, direct typed/byte loads, pair-values word, and self-check.
- [x] Classify the previous boundary as `token_loop_stage86_backedge_cycle_cond_load_path_mismatch_after_clean_carried_value`.
- [x] Add a stage87 backedge high-patch writer tuple for pair-offset base, high destination, destination delta, CycleCond record318, and writer mask.
- [x] Classify the previous boundary as `token_loop_stage87_no_high_patch_pair_offset_window_writer_backedge_reload_still_wrong`.
- [x] Add a stage88 CycleCondBB reload-view tuple for control/base/record318 delta/typed/raw/byte views.
- [x] Classify the current boundary as `token_loop_stage88_cycle_cond_view_same_wrong_value_at_expected_addr`.
- [x] Inspect generated PTX/SASS for the CycleCondBB `ld.global` / cache / param-alias path.
- [x] Add a stage89 backedge tuple comparing direct `param_1+2544` reload, carried clean pre-cycle value, and existing CycleCondBB typed/raw/byte reloads.
- [x] Run the full-phase 2-state CUDA700 probe and capture the stage89 tuple.
- [x] Add a stage90 high-eval-done-vs-CycleCond tuple using a PHI-carried `HighEvalDoneBB` direct `param_1+2544` reload.
- [x] Add parser/test support for Stage90 Displaced Snapshot handling.
- [x] Rerun the full-phase 2-state CUDA700 probe after the stage90 displaced-snapshot parser support.
- [x] Seal or otherwise stabilize the stage90 progress tuple so `progress_stage=90` and `epoch_coherent=true` can be observed before claiming edge-to-CycleCond memory-view authority.
- [x] Add a stage91 HighEval-entry start tuple before the HighEval entry direct reload.
- [x] Add a stage92 post-high-patch-store tuple after `B.CreateAlignedStore(HighPatchValue, HighDst, Align(1))`.
- [x] Rerun the full-phase 2-state CUDA700 probe and classify the stage92 boundary.
- [x] Add a stage93 pre-store target tuple for high-patch store address, offset, delta, value, and OOB flags.
- [x] Rerun the full-phase 2-state CUDA700 probe and classify the stage93 store target boundary.
- [x] Guard/fail-close the OOB high-patch store target before creating the real store pointer.
- [x] Rerun the full-phase 2-state probe and classify the Stage94 guard boundary.
- [x] Rerun/diagnose the phase 2 pair-offset pollution boundary after the OOB guard.
- [x] Classify phase 2 record-318 uploaded/pair/pre-token offset pollution after the Stage94 guard.
- [x] Add diagnostic labels for post-schedule-upload, pre-token-loop-launch, and post-token-loop-sync record `318` snapshots.
- [x] Classify the Stage95 boundary where phase 1 post-sync already has record `318` polluted to `38666621`.
- [x] Classify the Stage96 boundary where phase 1 post-sync has multi-record pair-offset pollution across records `318..322` while pair-values remain matched.
- [x] Add token-loop launch argument/table alias scan for phase 1 pair-offset pollution.
- [x] Rerun the full-phase 2-state probe to collect the token-loop argument/table alias scan and classify the Stage97 boundary.
- [x] Add token-loop internal pair-offset-table writer scan for intended phase-set, patch, and feedback writer destinations.
- [x] Rerun the full-phase 2-state probe to collect the Stage98 writer scan and classify the Stage98 boundary.
- [x] Extend the alias scan to progress/cfg-clone/region timing diagnostic allocations and classify the Stage99 boundary.
- [x] Add Stage100 high-patch store/guard device write watchpoint and classify the clean boundary.
- [x] Diagnose the remaining phase-1 pair-offset table pollution after the clean device write watchpoint by bracketing eval/call-site memory-view changes.
- [x] Add Stage102 low-patch-to-low-eval memory-view bracketing and classify the cycle-entry polluted boundary.
- [x] Diagnose the pre-cycle-cond/cycle-cond pair-offset pollution boundary with Stage104 and classify `cycle_cond_entry` as the first polluted checkpoint.
- [x] Add Stage110 callee0 body/store pair-offset watchpoint instrumentation, runtime summary printing, and parser/classifier tests.
- [x] Confirm the Stage110 runtime probe is blocked before launch by stale entry-sliced CUBINs after the Stage110 PTX rebuild.
- [x] Add opt-in `.func` reachability pruning for gateGPT entry slices and verify it halves the PTX slice size without weakening freshness checks.
- [x] Reduce Stage110 token-loop CUBIN `ptxas` cost enough to produce a fresh bounded token-loop CUBIN for direct-body scope.
- [x] Rerun the full-phase 2-state probe and collect the Stage110 direct body/store watchpoint result.
- [x] Diagnose nested call or non-store pair-offset pollution under high-eval callee0.
- [ ] Bracket or watchpoint inside `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` without closure-wide store instrumentation.
- [ ] Diagnose the CycleCondBB entry PHI/control-word pair-offset pollution boundary.
- [x] Add Stage112 source-id range splitting so the nested-body watchpoint can reach runtime without all-store `ptxas` timeout.
- [x] Run Stage112 source ids `1..256` and classify the clean range.
- [x] Run Stage112 source ids `129..256` and classify the clean range.
- [x] Run Stage112 source ids `257..384` and classify the clean range.
- [x] Run Stage112 source ids `385..512` and classify the clean range.
- [x] Run Stage112 source ids `513..1024` and classify the clean range.
- [x] Run Stage112 source ids `1025..1536` and classify the clean range.
- [x] Run Stage112 source ids `1537..2048` and classify the clean range.
- [x] Run Stage112 source ids `2049..2560` and classify the clean range.
- [x] Run Stage112 source ids `2561..3072` and classify the clean range.
- [x] Run Stage112 source ids `3073..3584` and classify the clean range.
- [x] Run Stage112 source ids `3585..4096` and classify the clean range.
- [x] Run Stage112 source ids `4097..4608` and classify the clean range.
- [x] Run Stage112 source ids `4609..5120` and classify the clean range.
- [x] Run Stage112 source ids `5121..5632` and classify the clean range.
- [x] Run Stage112 source ids `5633..6144` and classify the clean range.
- [x] Run Stage112 source ids `6145..6656` and classify the clean range.
- [x] Run Stage112 source ids `6657..7168` and classify the clean range.
- [x] Run Stage112 source ids `7169..7680` and classify the clean range.
- [x] Run Stage112 source ids `7681..8192` and classify the clean range.
- [x] Run Stage112 source ids `8193..8704` and classify the clean range.
- [x] Run Stage112 source ids `8705..9216` and classify the clean range.
- [x] Run Stage112 source ids `9217..9728` and classify the clean range.
- [x] Run Stage112 source ids `9729..10240` and classify the clean range.
- [x] Run Stage112 source ids `10241..10752` and classify the clean range.
- [x] Run Stage112 source ids `10753..11264` and classify the clean range.
- [x] Run Stage112 source ids `11265..11776` and classify the clean range.
- [x] Run Stage112 source ids `11777..12288` and classify the clean range.
- [x] Run Stage112 source ids `12289..12800` and classify the clean range.
- [x] Run Stage112 source ids `12801..13134` and classify the final clean range.
- [x] Continue Stage112 nested-body source-id range probing until a write source is found or the complete nested-body store set is clean.
- [x] Add and run Stage113 direct deeper-call boundary diagnostics after the complete Stage112 nested-body store set is clean.
- [x] Add and run the first Stage114 non-store memory-effect diagnostic range `1..128` after Stage112 stores and Stage113 deeper-call boundaries are clean.
- [x] Run Stage114 non-store memory-effect diagnostic range `129..256` and classify the cumulative range `1..256` as clean.
- [x] Add Stage114 candidate census metadata and parse it into the ordering-aware report.
- [x] Re-run Stage114 `1..128` with census metadata and confirm all design-origin non-store memory-effect candidates are clean.
- [x] Re-run Stage114 `129..256` with census metadata and confirm the range is diagnostic-origin only and clean.
- [x] Inspect remaining diagnostic-origin atomics versus residual `CycleCond` / PHI pollution before adding any broader Stage114 range sweep.
- [x] Add Stage115 residual classification so Stage114 design-origin-clean census evidence avoids broadening Stage114.
- [x] Re-run the census-bearing 2-state full-phase probe and classify the residual source as Stage108 after-callee / Stage109 same-saved-address high-eval callee0 pollution.
- [x] Add Stage116 residual CFG-edge entry-after-PHI boundary instrumentation, runtime summary printing, and parser/classifier support.
- [x] Fix Stage116 EH-pad instrumentation so `landingpad` blocks remain verifier-valid under `opt-18`.
- [x] Run Stage116 residual boundary source ids `1..128` and classify the clean range.
- [x] Run Stage116 residual boundary source ids `129..384` and classify the cumulative range `1..384 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `385..512` and classify the cumulative range `1..512 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `513..768` and classify the cumulative range `1..768 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `769..1024` and classify the cumulative range `1..1024 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `1025..1280` and classify the cumulative range `1..1280 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `1281..1536` and classify the cumulative range `1..1536 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `1537..1792` and classify the cumulative range `1..1792 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `1793..2048` and classify the cumulative range `1..2048 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `2049..2304` and classify the cumulative range `1..2304 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `2305..2560` and classify the cumulative range `1..2560 / 2750` as clean.
- [x] Run Stage116 residual boundary source ids `2561..2750` and classify the complete range `1..2750 / 2750` as clean.
- [x] Complete Stage116 residual boundary source-id range probing with the full CFG-edge entry-after-PHI set clean.
- [x] Add Stage117 nested-body block-body boundary instrumentation, runtime summary printing, parser/classifier support, CLI range controls, and contract coverage.
- [x] Add pass-tool freshness rebuild coverage so stale `vlgpugen` cannot generate Stage117-free IR before rebuilding.
- [x] Mitigate Stage117 token-loop `ptxas` blocker for the lightweight `COUNT=1024` probe by using a 900s bound; all three entry slices pass.
- [x] Run fresh lightweight Stage117 nested-body block-body boundary `COUNT=1024` and classify the first one thousand twenty-four block-body source ids as `clean_no_block_body_boundary`.
- [x] Expand fresh lightweight Stage117 nested-body block-body boundary probing to `COUNT=2048` and classify `source_id=1760` as `same_saved_addr_changed`.
- [x] Map the dirty Stage117 boundary to current generated IR: `vl_batch_gpu.ll:834516` metadata row and reconstructed block `vl_batch_gpu.ll:327571` / `%19690` in `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`; patched control-word store `vl_batch_gpu_patched.ll:333201`, `control_word=72058702139492064`.
- [x] Add parser-backed Stage117 source-id-to-IR mapping summary coverage for `source_id=1760` so future reports can expose metadata row, control-word line, LLVM block label, and first Stage117 probe line without hand reconstruction.
- [x] Add Stage118 source-id 1760 intrablock boundary probe to split block `%19690` and turn the Stage117 dirty block-body boundary into a smaller source-level/basic-block diagnostic surface.
- [x] Run Stage118 source-id 1760 intrablock boundary probe with default instruction range `1..256` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `257..512` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `513..768` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `769..1024` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `1025..1280` and classify it as clean.
- [x] Record the superseded Stage118 `1281..1536,count=256` and `1281..1344,count=64` 900s timeout attempts as historical ptxas-surface blockers.
- [x] Rerun Stage118 source-id 1760 intrablock boundary probe for `1281..1344` and `1345..1408` with the opt-in guard and a 300s ptxas bound; both reach runtime with raw Stage118 `clean_no_instruction_boundary` events, but retain stale pre-fix report-level classifier fields.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for `1409..1472`, `1473..1536`, `1537..1600`, and `1601..1664`; all classify clean after the classifier-continuation fix.
- [x] Add Stage112 metadata/runtime source-summary guardrail and record that static candidates `1415` and `1533` are not runtime write-source authority under the paired clean runtime report.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `1665..1728` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `1729..1792` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `1793..1856` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `1857..1920` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `1921..1984` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `1985..2048` and classify it as clean.
- [x] Run Stage118 source-id 1760 intrablock boundary probe for instruction range `2049..2112`; classify it as metadata-proven `range_exhausted` with `candidate_count=max_source_id=2021`, not clean and not dirty.
- [x] Reclassify Stage118 exhaustion with existing post-sync diagnostic allocation alias evidence; alias scan is complete/clean (`found=false`, `overlap_names=none`).
- [x] Add Stage119 source-id `1760` skipped-span boundary probe to inspect skipped Stage118 spans / diagnostic-inserted boundaries not covered by normal instruction candidates.
- [x] Run Stage119 source-id `1760` skipped-span boundary probe for range `1..256` and classify the first runtime result.
- [x] Run Stage119 source-id `1760` skipped-span boundary probe for range `257..512` and classify it as metadata-exhausted/incomplete.
- [x] Extend Stage119 source-id `1760` skipped-span boundary candidate extraction/probe surface to compact CFG-clone/probe spans.
- [x] Map Stage119 dirty `source_id=2` to `compact.cfg_clone.entry_phi.producer_selector.counters3969` in generated LLVM IR.
- [x] Add Stage120 instruction-boundary splitting for Stage119 `source_id=2` compact CFG-clone entry-PHI producer-selector span.
- [x] Run Stage120 block `1760`, skipped span `2`, instruction range `1..256` and classify it as clean.
- [x] Run Stage120 block `1760`, skipped span `2`, instruction range `257..512` and classify it as clean.
- [x] Run Stage120 block `1760`, skipped span `2`, instruction range `513..768` and classify it as clean.
- [x] Run Stage120 block `1760`, skipped span `2`, instruction range `769..1024` and classify it as clean.
- [x] Run Stage120 block `1760`, skipped span `2`, instruction range `1025..1280` and classify it as clean.
- [x] Run Stage120 block `1760`, skipped span `2`, instruction range `1281..1536` and classify it as clean.
- [x] Run Stage120 block `1760`, skipped span `2`, instruction range `1537..1792` and classify it as metadata-exhausted.
- [x] Add and run Stage120 span-edge probe for block `1760`, skipped span `2`; classify the aggregate entry-to-exit edge as `same_saved_addr_changed`.
- [x] Inspect/map the Stage120 span-edge source IR; record metadata row `252360`, `metadata_opcode=span_edge`, `metadata_span_skipped_count=1536`, first `load compact.cfg_clone.entry_phi.producer_selector.counters3969`, and last opcode `atomicrmw`.
- [x] Add Stage120 aggregate-edge prefix probe mode and CLI/env opt-in.
- [x] Run Stage120 aggregate-edge `source384` and classify it as clean.
- [x] Run Stage120 aggregate-edge `source576` and classify it as clean.
- [x] Run Stage120 aggregate-edge `source768` and classify it as dirty.
- [x] Run Stage120 aggregate-edge `source672` and classify it as dirty with fixed aggregate-edge metadata name.
- [x] Run Stage120 aggregate-edge `source624` and classify it as dirty with `metadata_instruction_name=skipped_span_entry_to_instruction_624`.
- [x] Run Stage120 aggregate-edge `source600` and classify it as clean.
- [x] Run Stage120 aggregate-edge `source612` and classify it as dirty with `metadata_instruction_name=skipped_span_entry_to_instruction_612`.
- [x] Run Stage120 aggregate-edge `source606` and classify it as clean.
- [x] Run Stage120 aggregate-edge `source609` and classify it as clean.
- [x] Add Stage120 aggregate-edge target opcode/name metadata and parser support.
- [x] Rerun Stage120 aggregate-edge `source611` after target metadata and classify it as dirty; this supersedes older source611-clean evidence.
- [x] Run Stage120 aggregate-edge `source610` and classify it as dirty with target `getelementptr compact.cfg_clone.entry_phi.producer_selector.original_side_dominates.sample8882`.
- [x] Inspect refreshed Stage120 aggregate-edge `source610`/`source611`/`source612` target metadata; identify `source610` as the first dirty prefix after clean `source609`.
- [x] Implement/run low-perturbation Stage120 aggregate-edge `source610` probe and classify regular `source610` dirty as observation-sensitive diagnostic perturbation.
- [x] Run low-perturbation Stage120 aggregate-edge `source611` probe and classify it as `after_only_polluted` targeting `atomicrmw`.
- [x] Inspect Stage120 low-perturbation aggregate-edge `source611` IR/semantics; identify the mapped `atomicrmw` as diagnostic `__vlgpu_single_entry_cfg_clone_liveout_counters` traffic, not final pair-offset write-source authority.
- [x] Confirm the `source611` low-perturbation report keeps diagnostic allocation / adjacent-window alias scans clean (`diagnostic_allocation_pair_offsets_overlap_count=0`, no adjacent-window overlap).
- [x] Implement a minimal Stage121/source611 diagnostic-atomic suppression or no-counter-write probe.
- [x] Rerun low-perturbation aggregate-edge `source611` with the diagnostic atomic suppressed; `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage121_source611_diagnostic_atomic_suppression_ptxas300_runtime.json` classifies the targeted boundary as clean.
- [x] If suppression makes `source611` clean, classify the current boundary as diagnostic counter perturbation and continue semantic write-source search beyond source611.
- [x] Continue beyond `source611` by inspecting/probing `source612` / `original_side_opcode`; source612 after source611 suppression remains `after_only_polluted` and maps to `getelementptr`.
- [x] Probe `source613` / original-side opcode diagnostic atomic; after source611 suppression it remains `after_only_polluted`.
- [x] Add `--ordering-aware-stage121-diagnostic-atomic-suppression-source-id` and use it to suppress `source613`; the targeted source613 boundary becomes clean in `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage121_source613_diagnostic_atomic_suppression_ptxas300_runtime.json`.
- [x] Continue beyond `source613` by probing `source614` / `original_side_safety_mask`; source614 remains after-only polluted with source613 suppressed, and skipping source615 makes the targeted boundary clean.
- [x] Add multi-source Stage121 diagnostic atomic suppression through `--ordering-aware-stage121-diagnostic-atomic-suppression-source-ids` / `VLGPUGEN_STAGE121_DIAGNOSTIC_ATOMIC_SOURCE_IDS`.
- [x] Probe source616/source618 with sources `613,615` suppressed; source616 maps to `zext .cfg_clone.liveout.zext8885` and source618 skip makes the targeted boundary clean.
- [x] Probe source619 with sources `613,615,618` suppressed; source619 remains after-only polluted and maps to `producer_side_original_selected_encoded_value.sample8887`/`getelementptr`.
- [x] Probe source620, the following diagnostic atomic after source619; self-probe remains after-only polluted even with sources `611,613,615,618,620` suppressed.
- [x] Probe source621 with and without source620 suppression; both runs are clean, so the marker-slot GEP is not the current frontier.
- [x] Probe source622 with sources `611,613,615,618,620` suppressed; it remains after-only polluted and maps to `materialized_store_order_marker.read8889` / `load`.
- [x] Probe source623 with sources `611,613,615,618,620` suppressed; it is clean.
- [x] Inspect source622 marker-read semantics; add targeted Stage121 marker-read suppression and show the targeted source622 boundary becomes clean.
- [x] Probe source624 after source622 marker-read suppression; it remains after-only polluted and maps to diagnostic `atomicrmw`.
- [x] Probe source624 with source624 also added to diagnostic atomic suppression; it still remains after-only polluted because Stage120 observes before that diagnostic atomic.
- [x] Freeze the producer-selector diagnostic perturbation series through Stage123/source1324 exclusion without accepting final write-source authority.
- [x] Implement Stage124 record318 transition probing after source1324 exclusion.
- [x] Run Stage124 source ranges `1..256`, `257..512`, `513..768`, and `769..896`; all reach runtime with no transition source.
- [x] Run Stage124 source897,count128; it reaches runtime with `source_id=897`, `result=after_only_polluted`, `transition_found=false`, and no semantic authority.
- [x] Run Stage124 source960,count1 and source968,count1; both reach runtime with `result=after_only_polluted`, `transition_found=false`, and no semantic authority.
- [x] Run Stage124 source972,count1, source974,count1, and source975,count1; all reach runtime with `result=after_only_polluted`, `transition_complete=true`, `scan_complete=true`, `transition_found=false`, and no semantic authority.
- [x] Run Stage124 source976,count1, source992,count1, source1024,count1, and source1025,count128 without the source976 suppression frontier; all are incomplete reachability attempts with `transition_complete=false` / `scan_complete=false`, not scanned frontier evidence.
- [x] Bisect the Stage124 reachability boundary through adjacent source975 complete / source976 incomplete.
- [x] Diagnose source976 Stage124 reachability incompletion as diagnostic atomic perturbation by adding source976 to Stage121 diagnostic atomic suppression.
- [x] Run Stage124 source976,count1 and source977,count1 with source976 suppression; both reach runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source978,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source979,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source980,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source981,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source982,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source983,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source984,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source985,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source986,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source987,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source988,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source989,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source990,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source991,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source992,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source993,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source994,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source995,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source996,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source997,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source998,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source999,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1000,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1001,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1002,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1003,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1004,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1005,count1 with source976 suppression; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1006,count1 with source976 suppression; it is incomplete with `transition_complete=false` / `scan_complete=false` and is not scanned frontier evidence.
- [x] Add source1006 to Stage121 diagnostic atomic suppression and rerun source1006,count1; completion is restored with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1007,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1008,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1009,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1010,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1011,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1012,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1013,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1014,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1015,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1016,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1017,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1018,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1019,count1 with source976/source1006 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1020,count1 with source976/source1006 suppression carried forward; it is incomplete with `transition_complete=false` and `scan_complete=false`.
- [x] Add source1020 to Stage121 diagnostic atomic suppression and rerun source1020,count1; completion is restored with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1021,count1 with source976/source1006/source1020 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1022,count1 with source976/source1006/source1020 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Run Stage124 source1023,count1 with source976/source1006/source1020 suppression carried forward; it reaches runtime with `transition_found=false` and no semantic authority.
- [x] Retry Stage124 at source1024 with source976/source1006/source1020 diagnostic atomic suppression carried forward; it reaches runtime with `transition_found=false`, `scan_complete=true`, and no semantic authority.
- [x] Retry Stage124 at source1025 with source976/source1006/source1020 diagnostic atomic suppression carried forward; it reaches runtime with `transition_found=false`, `scan_complete=true`, and no semantic authority.
- [x] Retry Stage124 at source1026 with source976/source1006/source1020 diagnostic atomic suppression carried forward; it reaches runtime with `transition_found=false`, `scan_complete=true`, and no semantic authority.
- [x] Retry Stage124 at source1027 with source976/source1006/source1020 diagnostic atomic suppression carried forward; it reaches runtime with `transition_found=false`, `scan_complete=true`, and no semantic authority.
- [x] Retry Stage124 at source1028 with source976/source1006/source1020 diagnostic atomic suppression carried forward; it reaches runtime with `transition_found=false`, `scan_complete=true`, and no semantic authority.
- [ ] Retry Stage124 at source1029 with source976/source1006/source1020 diagnostic atomic suppression carried forward.
- [x] Sync GitHub #73 with the Stage124 source1024 retry completion and source1025 retry next action.
- [x] Sync GitHub #73 with the Stage124 source1025 retry completion and source1026 retry next action.
- [x] Sync GitHub #73 with the Stage124 source1026 retry completion and source1027 retry next action.
- [x] Sync GitHub #73 with the Stage124 source1027 retry completion and source1028 retry next action.
- [x] Sync GitHub #73 with the Stage124 source1028 retry completion and source1029 retry next action.
- [x] Sync GitHub #73 with the Stage124 source972/source974/source975/source976 adjacent-boundary evidence and next action.
- [x] Sync GitHub #73 with the Stage124 source978 completion and source979 next action.
- [x] Sync GitHub #73 with the Stage124 source979 completion and source980 next action.
- [x] Sync GitHub #73 with the Stage124 source980 completion and source981 next action.
- [x] Sync GitHub #73 with the Stage124 source981 completion and source982 next action.
- [x] Sync GitHub #73 with the Stage124 source982 completion and source983 next action.
- [x] Sync GitHub #73 with the Stage124 source983 completion and source984 next action.
- [x] Sync GitHub #73 with the Stage124 source984 completion and source985 next action.
- [x] Sync GitHub #73 with the Stage124 source985 completion and source986 next action.
- [x] Sync GitHub #73 with the Stage124 source986 completion and source987 next action.
- [x] Sync GitHub #73 with the Stage124 source987 completion and source988 next action.
- [x] Sync GitHub #73 with the Stage124 source988 completion and source989 next action.
- [x] Sync GitHub #73 with the Stage124 source989 completion and source990 next action.
- [x] Sync GitHub #73 with the Stage124 source990 completion and source991 next action.
- [x] Sync GitHub #73 with the Stage124 source991 completion and source992 next action.
- [x] Sync GitHub #73 with the Stage124 source992 completion and source993 next action.
- [x] Sync GitHub #73 with the Stage124 source993 completion and source994 next action.
- [x] Sync GitHub #73 with the Stage124 source994 completion and source995 next action.
- [x] Sync GitHub #73 with the Stage124 source995 completion and source996 next action.
- [x] Sync GitHub #73 with the Stage124 source996 completion and source997 next action.
- [x] Sync GitHub #73 with the Stage124 source997 completion and source998 next action.
- [x] Sync GitHub #73 with the Stage124 source998 completion and source999 next action.
- [x] Sync GitHub #73 with the Stage124 source999 completion and source1000 next action.
- [x] Sync GitHub #73 with the Stage124 source1000 completion and source1001 next action.
- [x] Sync GitHub #73 with the Stage124 source1001 completion and source1002 next action.
- [x] Sync GitHub #73 with the Stage124 source1002 completion and source1003 next action.
- [x] Sync GitHub #73 with the Stage124 source1003 completion and source1004 next action.
- [x] Sync GitHub #73 with the Stage124 source1004 completion and source1005 next action.
- [x] Sync GitHub #73 with the Stage124 source1005 completion and source1006 next action.
- [x] Sync GitHub #73 with the Stage124 source1006 incomplete/restored-completion evidence and source1007 next action.
- [x] Sync GitHub #73 with the Stage124 source1007 completion and source1008 next action.
- [x] Sync GitHub #73 with the Stage124 source1008 completion and source1009 next action.
- [x] Sync GitHub #73 with the Stage124 source1009 completion and source1010 next action.
- [x] Sync GitHub #73 with the Stage124 source1010 completion and source1011 next action.
- [x] Sync GitHub #73 with the Stage124 source1011 completion and source1012 next action.
- [x] Sync GitHub #73 with the Stage124 source1012 completion and source1013 next action.
- [x] Sync GitHub #73 with the Stage124 source1013 completion and source1014 next action.
- [x] Sync GitHub #73 with the Stage124 source1014 completion and source1015 next action.
- [x] Sync GitHub #73 with the Stage124 source1015 completion and source1016 next action.
- [x] Sync GitHub #73 with the Stage124 source1016 completion and source1017 next action.
- [x] Sync GitHub #73 with the Stage124 source1017 completion and source1018 next action.
- [x] Sync GitHub #73 with the Stage124 source1018 completion and source1019 next action.
- [x] Sync GitHub #73 with the Stage124 source1019 completion and source1020 next action.
- [x] Sync GitHub #73 with the Stage124 source1020 incomplete/restored-completion evidence and source1021 next action.
- [x] Sync GitHub #73 with the Stage124 source1021 completion and source1022 next action.
- [x] Sync GitHub #73 with the Stage124 source1022 completion and source1023 next action.
- [x] Sync GitHub #73 with the Stage124 source1023 completion and source1024 retry next action.
- [x] Close the `suppression remains after_only_polluted` branch as not taken; suppression made the targeted source611 boundary clean.
- [ ] Diagnose the high-eval callee0 same-saved-address residual pair-offset pollution after complete Stage116 clean evidence.
- [ ] Diagnose why the loaded offset becomes `38666621` before permitting the full high-patch store.
- [ ] Only diagnose the `HighEvalDoneBB -> CycleCondBB` landing / CycleCond entry reload transition if sealed stage90 shows `HighEvalDone=0` and `CycleCond=38666621`.
- [x] Preserve the full-phase fail-closed behavior on CUDA700.
- [x] Keep all diagnostics opt-in or scoped to the ordering-aware full-phase probe path.
- [x] Do not advance to token-sequence correctness, actual-valid authority, 16-state scale, or timing until record `318` loaded-offset authority is explained or fixed.

## Acceptance

- The report states one concrete classification for record `318`.
- Host-side expected offset for `control.steps[318]` is recorded.
- Uploaded/read-back table value for record `318` is recorded.
- Pair-table readback at the expected load address is recorded.
- Device-observed loaded record, load address, and loaded-offset value are recorded.
- If fixed, the full-phase 2-state probe progresses past `stage=70` or reaches a new named boundary.
- If not fixed, the report names the next smallest diagnostic target.
- No broad gateGPT PASS/FAIL, full-phase semantic pass, speedup, usefulness, 16-state scale, runtime-noop, semantic-guard, proof-complete, or actual-valid authority is claimed.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest   tests.contract.test_gategpt_entry_sliced_cubin_chain   tests.contract.test_rtlmeter_vortex_ptx_entry_slice.RtlmeterVortexPtxEntrySliceTest.test_prunes_unreferenced_funcs_when_requested   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage76_cuda700_classifies_same_kernel_offset_change   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage77_classifies_oob_storage_gep_before_store   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage78_classifies_raw_addr_reload_same_wrong_value   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage79_classifies_low_patch_mutation_window   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage80_classifies_entry_device_view_mismatch   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage81_classifies_terminal_mask_change   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage82_classifies_edge_probe_change   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage83_classifies_same_address_wrong_load   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage84_classifies_neighbor_records_wrong   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage85_classifies_clean_pre_cycle_then_cycle_cond_wrong   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage86_classifies_backedge_cycle_cond_mismatch   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage87_classifies_no_high_patch_pair_offset_writer   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage88_classifies_same_wrong_reload_view   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage94_classifies_oob_store_guarded_fail_closed_no_semantic_authority   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage95_classifies_phase1_post_sync_pair_offset_pollution   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage96_classifies_multi_record_offset_table_pollution   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_full_phase_smoke_stage97_classifies_clean_arg_table_alias_scan   tests.contract.test_gategpt_testbench_probe.GateGptTestbenchProbeTest.test_gpu_runtime_summary_parser_extracts_smoke_metrics -q

PYTHONDONTWRITEBYTECODE=1 python3 src/tools/gategpt_testbench_probe.py   --repo-dir artifacts/external_gateGPT   --run-gpu-ordering-aware-full-phase-smoke   --ordering-aware-state-count 2   --ordering-aware-stage112-store-start 12801   --ordering-aware-stage112-store-count 334   --ordering-aware-stage114-effect-start 1   --ordering-aware-stage114-effect-count 128   --ordering-aware-stage116-boundary-start 129   --ordering-aware-stage116-boundary-count 256   --regenerate-ordering-aware-entry-sliced-cubins   --ordering-aware-entry-sliced-ptxas-timeout-seconds 900   --gpu-jobs 2   --write-report   --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage116_residual_boundary_range_129_256_runtime.json

PYTHONDONTWRITEBYTECODE=1 python3 src/tools/gategpt_testbench_probe.py   --repo-dir artifacts/external_gateGPT   --run-gpu-ordering-aware-full-phase-smoke   --ordering-aware-state-count 2   --ordering-aware-stage112-store-start 12801   --ordering-aware-stage112-store-count 334   --ordering-aware-stage114-effect-start 1   --ordering-aware-stage114-effect-count 128   --ordering-aware-stage117-boundary-start 1   --ordering-aware-stage117-boundary-count 2048   --regenerate-ordering-aware-entry-sliced-cubins   --ordering-aware-entry-sliced-ptxas-timeout-seconds 900   --gpu-jobs 2   --write-report   --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_light_block_body_boundary_range_1_2048_ptxas900_runtime.json

python3 -m json.tool config/selection.json >/dev/null
python3 -m json.tool reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state.json >/dev/null
git diff --check -- README.md config/selection.json docs/status.md docs/roadmap.md for_codex/issues.md for_codex/issues/FC-073-diagnose-ordering-aware-high-patch-record318-offset-table-abi-cuda700.md src/hybrid/run_vl_hybrid.c src/passes/vlgpugen.cpp src/tools/gategpt_entry_sliced_cubin_chain.py src/tools/gategpt_testbench_probe.py tests/contract/test_gategpt_entry_sliced_cubin_chain.py tests/contract/test_gategpt_testbench_probe.py
```

## Non-claims

- No actual-valid authority.
- No full-phase semantic pass.
- No speedup or usefulness claim.
- No 16-state scale claim.
- No semantic-guard, runtime-noop, or proof-complete claim.
- No broad gateGPT PASS/FAIL authority.
