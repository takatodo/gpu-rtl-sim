# Roadmap

## Goal Frame

The roadmap should be read as a GPU sidecar roadmap, not a Verilator-only roadmap. Verilator is the current compatibility frontend and the near-term native UX target; CIRCT is a planned second frontend. The shared target is a sidecar contract that carries frontend-owned RTL/build metadata into sidecar-owned GPU build, execution, and compare stages.

JSON is an inspection format for that contract. Automation may read it for diagnostics, but it should not become execution authority or the mandatory runtime ABI.

## Three Layers

1. Current execution support: keep supported template and benchmark flows reproducible through sidecar build/run/compare, with `coverage_output_equivalence` as the accepted CPU-vs-hybrid policy.
2. Preview UX: harden the Verilator-compatible `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` surface through wrappers, shims, and reviewed launcher boundaries before broader native claims.
3. Long-term goal: move toward a frontend-neutral sidecar contract that Verilator and CIRCT can both feed, while measuring the conditions where LLM-serving-like RTL workloads benefit from hybrid CPU/GPU execution.

Future shorthand such as `verilator --use-gpu -f filelist.f --top-module top` and `gpu-sidecar --frontend verilator/circt ...` stays directional until a reviewed gate proves the corresponding execution path.

## Weakest Point

Current weak point for the active OpenTitan regression-discovery gate is
promoting entropy_src #10983 from GPU semantic equivalence to the same corpus
contract already proven for TL-UL #10818 and EDN #23526. TL-UL and EDN prove
fixed revisions, checkpoints, action domains, independent oracles,
semantic-manifest identity, bad-revision oracle violations, fixed-revision
non-reproduction, CPU/GPU semantic equivalence, separated corpora, and
random-vs-stratified long-tail metrics. entropy_src #10983 now has bad/fixed
CPU/GPU semantic equivalence for the minimal action. No PPO, semantic-state
packing, full OpenTitan scale, or extra batch-size claim is currently required
to prove the active Contract.

Historical RTLMeter context: #2 / FC-037 has a refreshed VeeR-EL2 `hello` timing result,
and that GPU sidecar path is still much slower than serial CPU, while the
latest three-batch timing gate is stable against the comparable CPU-parallel
floor across seven-sample batch medians.
#63 / FC-064 already
clears the VeeR-EL2 state-image/stdout/cycles correctness prerequisite. The
measured FC-037 report shows serial RTLMeter CPU elapsed `0.04s`, eight-state
sidecar wall median `0.610509s`, GPU kernel total median `224.068604ms`,
comparable eight-worker CPU-parallel `hello` wall `1.509886s`, and
`cpu_parallel_wall_time_outcome=sidecar_faster_than_comparable_cpu_parallel_baseline`.
The latest filtered sixteen-state scaling report shows sidecar wall median
`0.768573s`, GPU kernel total median `268.161011ms`, comparable
sixteen-worker CPU-parallel wall `2.218887s`,
`sidecar_vs_cpu_parallel_ratio=2.887022`, and per-state wall `0.048036s`.
Bridge preflight median is now `0.000406s`, the GPU
sidecar launches `nstates=16`, all-state clock/reset patching is active, final
observables match state 0 across all sixteen states, and state-0 stdout/cycles
still compare against the CPU reference. The bridge now invokes the reviewed Python sidecar in-process,
and the sidecar calls the hybrid C runtime directly instead of launching
through `run_vl_hybrid.py`; step-trace field reads use a device-buffered DtoD
trace path with high-phase filtering (`727` rows from a `1457`-step capacity),
rising-edge mailbox reconstruction, final counter fallback, and
`resident_patch_records_median=69936.0`,
init-state replication uses the device kernel path, and patch application uses
the device-resident patch schedule. The latest report records
`timing_stability_outcome=stable_repeated_batch_outcome` across three batches,
but serial CPU remains much faster. The current blocker has moved beyond
non-`hello` loop-collapse eligibility: fixed-flat-memory `dhry` now has
same-window trace equivalence and a phase-aware pair-cycle loop kernel that
preserves the `vl_ico_batch_gpu` plus `vl_eval_loop_batch_gpu` sequence in
bounded diagnostics. Patch/eval fusion was tested and
left opt-in because it preserved correctness but did not improve the repeated
16-state median. The opt-in
`VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=posedge_only` diagnostic reduced logical
steps to `730` but failed RTLMeter stdout correctness and left VeeR counters at
zero, so high-only clock patching is rejected. The follow-up FC-037 path is a
pair-cycle/resident-step mode that keeps ordered low-eval then high-eval
semantics inside one runtime operation; that opt-in path now passes the
repeated 16-state gate and improves the latest representative wall time, but it
is still slower than serial CPU and not yet robust enough for a broad usefulness
claim. A confirmatory repeated gate also improves the non-fusion representative,
but its first batch regressed enough to keep pair-cycle opt-in rather than
promoting it as the default. The true fused pair-cycle kernel now passes the
full repeated gate and sets the current best 16-state VeeR sidecar wall median,
but it is still far slower than serial CPU.

Historical context follows for audit. If older text below names another current bridge task, prefer the `Current Frontier` section above.

Hybrid execution is close to a normal Verilator-style flow for generated templates, but "native" is still only a prototype boundary. The chain now includes a reviewed patched-binary parser-only retry, an accepted sidecar authority boundary, a first scoped native sidecar run, a review accepting only separated parser-success plus reviewed `pulp_ita_mha 64x1` sidecar build/run/compare evidence, a definition of the direct launch authority chain, a review accepting that definition only for a scoped future run, a run record that stops at `direct_launch_handoff_failure`, a review accepting that failure as honest, a definition of the minimal direct-launch handoff implementation boundary, a review accepting only that narrow boundary, a metadata-only direct-launch handoff fixture implementation, a review accepting that fixture only as readiness metadata, a definition of the first real handoff run boundary, a review accepting that boundary only for a scoped future run, a scoped handoff run that still records `direct_launch_handoff_failure`, a review accepting that failure as honest, a native-process to sidecar-launcher bridge boundary definition/review, a metadata-only bridge fixture implementation, a review accepting that fixture only as metadata, a scoped sidecar-launcher run boundary definition/review, a scoped sidecar-launcher run that stops at `sidecar_launcher_bridge_failure`, a review accepting that failure as honest, a definition of the launcher-invocation implementation boundary, a review accepting that boundary only for a scoped fixture implementation, a non-executing launcher-invocation fixture implementation, a review accepting that fixture only as argv materialization metadata, a definition of the launcher-invocation run boundary, a review accepting that boundary for a scoped future run, a scoped launcher-invocation run that starts the reviewed structured `run_hybrid_template.py` argv and reaches coverage-output compare with mismatch count `0`, a review accepting only that structured launcher invocation evidence, a definition/review of the missing Verilator-facing process-to-launcher CLI boundary, a non-executing process-to-launcher CLI fixture implementation/review, a definition/review of the first scoped process-to-launcher CLI execution boundary, a scoped process-to-launcher CLI run that starts the exact `run_hybrid_template.py` argv and reaches coverage-output compare with mismatch count `0`, a review accepting that run only as process-to-launcher evidence from reviewed fixture metadata, a Verilator-process-to-launcher bridge execution boundary definition/review, a scoped bridge execution attempt that honestly records `process_to_launcher_bridge_failure`, a review accepting that failure as honest, a definition of the minimal observable-ordering implementation boundary, and a review accepting that boundary only for a helper implementation. The weak point is now implementing the helper without over-reading observable ordering as bridge-path launcher start, direct Verilator sidecar execution, bridge-path compare, broad native option support, timing evidence, automatic allocation, runtime/ABI change, arbitrary filelist support, or production throughput.

## Current Frontier

The current work is OpenTitan temporal protocol GPU resident
regression-discovery. TL-UL #10818, EDN #23526, and entropy_src #10983
establish the current three-issue seed set.

Current priority:

`opentitan_temporal_protocol_gpu_resident_regression_discovery`

Next concrete action:

`review_three_issue_seed_set_and_select_next_expansion`

Current source artifact:

`artifacts/entropy10983_campaign/entropy10983_campaign_summary.json`

Historical FC-069 update: Stage118/119/120/121/122/123/124 gateGPT narrowing remains historical evidence for the previous frontier. It is not the active OpenTitan regression-discovery next action.

Stage117 update: the previous `1..256` report is not accepted as Stage117 runtime evidence because generated IR lacked Stage117 instrumentation due stale `vlgpugen` pass-tool build order. Pass-tool freshness is now fixed so stale pass tools rebuild before IR generation. With the lightweight saved-address Stage117 probe and a 900s `ptxas` bound, `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_light_block_body_boundary_range_1_2048_ptxas900_runtime.json` reaches runtime: all three entry slices pass `ptxas`, preflight passes, and classification is `token_loop_stage117_phase1_callee0_nested_body_block_body_boundary_same_saved_addr_changed`. The first `COUNT=1024` run was clean, but `COUNT=2048` finds a dirty Stage117 block-body boundary at `source_id=1760` with `split_result=same_saved_addr_changed`, `before_direct_param_record318=0`, `after_direct_param_record318=38666621`, `after_saved_addr_record318=38666621`, `saved_after_polluted=true`, and `semantic_authority=false`. Current IR mapping evidence points to `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:834516` metadata row and reconstructed block `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:327571` / `%19690` in `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`; the patched control-word store is `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu_patched.ll:333201`, `control_word=72058702139492064`. This is a dirty boundary, not final adjacent-window write-source authority.

Stage118 implementation update: the pass instruments intrablock instruction boundaries inside Stage117 block source-id `1760`, defaulting to `VLGPUGEN_STAGE118_BLOCK_SOURCE_ID=1760`, `VLGPUGEN_STAGE118_INSTRUCTION_START=1`, and `VLGPUGEN_STAGE118_INSTRUCTION_COUNT=256`. Runtime printing exposes `ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_instruction_boundary`, and the parser/classifier recognizes dirty, clean, and incomplete Stage118 outcomes. The progress fallback has since expanded to 160 counters after Stage119 was added.

Stage118 ptxas-surface follow-up: `rtlmeter_vortex_ptx_entry_slice.py` now avoids treating semicolon-terminated `.func` declarations as function bodies, with a focused contract test. A dry-run regeneration report, `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_reduced_probe.json`, still produces large Stage118 slices (`762827`, `762985`, and `766310` lines), so this parser fix is correct but not sufficient; the next work remains shrinking retained prefix/global/reachable PTX surface or slice freshness before retrying `ptxas`.

Stage118 slice-freshness and split-surface mitigation: `gategpt_entry_sliced_cubin_chain.py` now writes a `*.cubin.slice.json` manifest after a successful `ptxas` run and only reuses an existing CUBIN when the current slice content hash, CUBIN path, GPU target, and ptxas options match that manifest. The entry-sliced specs now keep `vl_eval_batch_gpu` and `vl_patch_eval_pair_cycle_loop_batch_gpu` out of the helper support/feedback CUBINs because those symbols are already available from the token-loop slice. `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_default_split_ptxas1_probe.json` shows the helper slices shrink to `418` and `483` lines and both pass `ptxas` within a 1s bound; the remaining blocker is the token-loop slice at `766310` lines, which still times out. This narrows the ptxas blocker from three huge slices to one huge token-loop slice; it does not identify the final adjacent-window write source.

Stage118 token-loop stub-surface diagnosis: `rtlmeter_vortex_ptx_entry_slice.py --stub-func` can now replace selected reachable `.func` bodies with ret-only diagnostic stubs for ptxas-surface experiments only. `reports/gategpt_tb_core_stage118_token_loop_stub_slice_probe.json` stubs `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` and `__vlgpu_compact_cluster_outline_frame_stub`, reducing the token-loop slice from `766310` to `5066` lines; `ptxas` then produces `artifacts/gategpt_tb_core_ptx_entry_slice_stage118_stub_probe/vl_tb_core_ordering_aware_phase_resident_token_loop_gpu.cubin`. This confirms the remaining ptxas blocker is the reachable high-eval callee/compact-outline body surface, not the token-loop entry body itself. The stub CUBIN is not runtime evidence and must not be used to classify Stage118 instruction range `1281`.

Stage112 source-summary guardrail: `src/tools/gategpt_stage112_store_source_summary.py` joins Stage112 runtime events with the LLVM metadata map without promoting static rows to runtime authority. `reports/gategpt_tb_core_stage112_store_source_static_candidate_summary.json` records static source candidates `1415` and `1533` as `_Z40Vtb_core___024root___nba_sequent__TOP__0` `expected_liveout` zero-clear stores, but the paired runtime report is `clean_no_nested_body_store` with `source_id=0`, so `runtime_authority=false`. These rows are useful suspects for static review, not final adjacent-window write-source authority.

Stage118 opt-in guard surface probe: the earlier `1281,count=64` 120s ptxas-only blocker is now superseded. The same opt-in guard with a 300s `ptxas` bound reaches runtime for `1281..1344` and `1345..1408`; both raw Stage118 events are `clean_no_instruction_boundary`, but their report-level classifier fields remain stale pre-fix Stage112-incomplete results. Classifier-fixed runtime reports now cover `1409..2021` clean, and the later `2049..2112` request is exhausted by metadata.

Stage119/120 implementation/runtime update: skipped-span boundary diagnostics inspect contiguous spans that Stage118 intentionally skips, including compact CFG-clone/probe spans such as `compact.cfg_clone`, `producer_selector`, `materialized_store`, and `liveout`. Stage120 splits one mapped skipped span into instruction-level boundaries using `VLGPUGEN_STAGE120_BLOCK_SOURCE_ID`, `VLGPUGEN_STAGE120_SKIP_SPAN_SOURCE_ID`, `VLGPUGEN_STAGE120_INSTRUCTION_START`, and `VLGPUGEN_STAGE120_INSTRUCTION_COUNT`; `VLGPUGEN_STAGE120_SPAN_EDGE_PROBE=1` probes the aggregate span entry-to-exit edge with `boundary_kind_id=6`, `VLGPUGEN_STAGE120_AGGREGATE_EDGE_PROBE=1` probes prefix aggregate edges with `boundary_kind_id=7`, and `VLGPUGEN_STAGE120_LOW_PERTURBATION_PROBE=1` removes the before/saved-address observation for after-only classification. Runtime printing exposes `ordering_aware_token_loop_high_eval_callee0_nested_call_body_block_skipped_span_instruction_boundary`; and `gategpt_testbench_probe.py` parses/classifies dirty, clean, exhausted, span-edge, aggregate-edge, and after-only low-perturbation Stage120 outcomes. Local verification passed; low-perturbation probing refines the stable dirty prefix to `source611` / `atomicrmw`.

Stage121 now also has a marker-read suppression diagnostic for source-id gated `materialized_store_order_marker.read` loads via `VLGPUGEN_STAGE121_DIAGNOSTIC_MARKER_READ_SOURCE_IDS`. The source622 run used it and became clean; that is perturbation-control evidence only, not final write-source or semantic runtime authority.

gateGPT切り出し条件: gateGPTを深掘りする場合は、全体`tb_core`高速化ではなく、計算ブロック型RTLのGPU適用境界を測る。採用条件は、(1)入出力契約が小さく固定できる、(2)状態間独立またはbatch化できる、(3)算術密度が高い、(4)host/device往復がbatchあたり1回以下、(5)CPU oracleとbit/word単位で比較できる、(6)CIRCT/HLSまたはVerilator loweringのどちら由来かを分けて記録できること。除外条件は、逐次token loop、PHI/liveout/valid authorityが主役、stdout/PASS/finish依存、巨大root-state差分、または1シナリオだけの細粒度制御であること。最初の候補は`exp_unit`、matvec/norm/attention系の固定幅サブブロック、比較対象はRTLMeterで得た制御・CPU型RTL境界とする。

現在の実験ゴール: FC-070 / #71 は `microgpt_inference_slice,inference2_hls_friendly,1024x1` の metadata-gated runtime boundary と gateGPT `exp_unit` 比較レーンまで closure-ready。FC-072 / #72 は scoped complete として、`src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` の candidate/source_variant/shape/layout/symbol gate を metadata surface 由来の generated header に切り出した。CPUは token loop/sampler/full KV-cache と未知・非対応形状を持ち、GPUは測定済み batched arithmetic だけを持つ。これは full microGPT、whole `tb_core`、自動partitioning、任意RTL bridge generation、multi-row source emitter、またはJSONだけのruntime ABI authorityを主張しない。

FC-070 / #71 progress: `scientific_circt_source_variant_runtime_dispatcher.py` accepts requested `--shape` and `--steps` gates, passes the selected metadata row into `build_runtime_handoff_report`, and the `src-hybrid-verilator` handoff validates candidate/source_variant/shape/entrypoint/runtime-boundary/layout/symbols before compile/run. The C++ bridge also checks compact metadata argv and returns `failed_metadata_gate` before `dlopen` on mismatch. The metadata-gated execute path now measures `inference2_hls_friendly,1024x1`: `reports/scientific_circt_source_variant_verilator_entrypoint.json` records `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, and `cpu_to_bridge_hybrid_wall_speedup=6.2165001599863245x`; the dispatcher report records `runtime_dispatch_measured` with nested `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, and `cpu_to_bridge_hybrid_wall_speedup=15.461002763357895x`. The gateGPT `exp_unit` comparison lane is refreshed in `reports/gategpt_testbench_probe.json`: `tb_exp` vector, distinct-state, and resident patch paths all pass `103/103` with mismatch `0`; resident repeat median is `1.422 ms` wall / `1.348608 ms` kernel versus CPU process-wall median `14.788301952648908 ms`. This remains narrow `tb_exp` comparison evidence with `speedup_claimed=false` and `usefulness_claimed=false`, not broad gateGPT or arbitrary RTL usefulness. The next implementation issue is FC-072 / #72: generate or otherwise reuse source-variant bridge code from metadata while preserving the same fail-closed gates.

FC-072 / #72 progress: the scoped src-hybrid bridge gate is now derived from the source-variant metadata helper and materialized as `artifacts/scientific_circt/source_variant_verilator_entrypoint/scientific_circt_source_variant_bridge_gate.h` before compiling the Verilator-callsite bridge. `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` consumes generated `SCI_CIRCT_BRIDGE_EXPECTED_*` macros and still returns `failed_metadata_gate` before `dlopen` if argv metadata does not match. The refreshed handoff report records `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, generated header source `source_variant_metadata_row`, and `cpu_to_bridge_hybrid_wall_speedup=16.76826214888755x`; the dispatcher report records `runtime_dispatch_measured` with nested generated-header handoff and `cpu_to_bridge_hybrid_wall_speedup=15.600012129935479x`. This is still scoped to `inference2_hls_friendly,1024x1`, not arbitrary RTL bridge generation.

FC-072 / #72 closure audit: scoped acceptance is met. A broader reusable bridge source emitter for multiple metadata rows remains a possible follow-up only if the project explicitly needs that wider surface.

Current FC-069 evidence boundary: Stage109 proves record `318` changes after high-eval `callee_index=0`; Stage112/113/114/116 remain clean and Stage117/119/120 narrow the dirty area to compact CFG-clone producer-selector diagnostics. Source622/source624/source625 global-suppression evidence closes the producer-selector line as diagnostic counter/marker perturbation, Stage122 shows the first post-suppression lifecycle edge is dirty but not a concrete writer, and Stage123 source1324 is now excluded as CFG-clone liveout-counter traffic because its suppression removes the adjacent event but leaves record318 polluted.

## 追跡タスク (Tracked tasks)

1. **RTLMeter VeeR-EL2 timing/usefulness gate**: FC-064 / #63 now reaches normalized stdout match and RTLMeter cycle-count match, and FC-037 / #2 now records three-batch timing stability results for eight-state, sixteen-state, and thirty-two-state sidecar gates with matching CPU-parallel `hello` baselines. The 16-state fused pair-cycle gate remains the best total-latency result with `sidecar_wall_s_median=0.641226`, `pair_cycle_fusion_launched_median=727.0`, and fallback median `0.0`. The 32-state fused pair-cycle gate passes 21/21 correctness samples and improves per-state wall and states/s by `1.349465x` versus 16-state, but total wall worsens to `0.950341s` and serial CPU remains about `23.758525x` faster. Patch/eval fusion and `posedge_only` have both been tried; `posedge_only` failed correctness. State-local patch compression also passes correctness and cuts records by `32x`, but regresses timing to `sidecar_wall_s_median=2.452390`, so it is not promoted. The cmark preload probe now fails closed rather than producing a false hello-backed state image, and reviewed matching preload materialization exists for `cmark`, `cmark_iccm`, and `dhry`. The current `dhry` fixed-flat-memory path has bounded same-window trace equivalence, 100k no-finish progress, phase-aware loop-collapse evidence through 100000 cycles, and a generated negative-usefulness projection for the current single-scenario GPU path. The mixed-state GPU init path now also reaches 100000 bounded cycles for `dhry`/`cmark`/`cmark_iccm` using one shared kernel sequence and per-state preloads, but its projection is about `36.95x` slower than the CPU mixed parallel baseline by GPU-kernel time alone. `reports/rtlmeter_hybrid_advantage_summary.json` now quantifies the split: `cpu_parallel_favorable=1`, `gpu_sidecar_unfavorable=4`, `gpu_sidecar_favorable=0`, `launch_feasibility_blocked=1`, and `gpu_bounded_progress=1`, with `prefer_cpu_parallel_control_with_gpu_bounded_batch_probes` as the current hybrid action.
2. **RTLMeter non-VeeR usefulness candidates**: `reports/rtlmeter_non_veer_usefulness_candidates.json` now separates measured NVDLA evidence from fail-closed Vortex first-gate readiness. NVDLA has `measured_shape_count=20` and `gpu_favorable_shape_count=20` across existing `cmac_core_mac` / `cmac_a2cacc` scoped coverage-output-equivalent hybrid gates; the best wall ratio is `11764.742765273311x` at `1024x64` for `nvdla_cmac_a2cacc`. A 2026-06-17 `NVDLA.nvdla_cmac_core_mac` `32x1` repeat-median refresh reached CPU reference capture but full-core GPU artifact generation stayed in `ptxas` for more than ten minutes and reached about 36 GiB RSS before being stopped, so the next useful NVDLA path is smaller hot SS partitioning rather than broad full-core lowering. Vortex readiness now has its own report at `reports/rtlmeter_vortex_first_gate_readiness.json`: `Vortex:mini:hello` is the first gate because its binary inputs exist and it is the descriptor sanity test, `config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json` records a fail-closed `runtime_launchable=false` authority for stdout `TEST PASSED` plus memory post-condition, and `config/slice_launch_templates/vortex_mini_hello.json` records a fail-closed `runtime_launchable=false` / `source_closure.status=incomplete` launch-template marker. `reports/rtlmeter_vortex_source_closure.json` now validates the descriptor-owned source closure: all `126` Verilog sources, `8` include files, and `1` CPP DPI source exist locally, without granting runtime launch authority. `reports/rtlmeter_vortex_dpi_memory_bridge_review.json` reviews the DPI boundary and shows that the gate is no longer blocked on understanding the bridge. `src/hybrid/vortex_memory_model_device.h` provides a host-compilable helper for 64-byte block initialization, byte-enable writes, IO_COUT capture, and post compare semantics. `reports/rtlmeter_vortex_device_buffer_materialize.json` materializes the runtime upload inputs into `artifacts/rtlmeter_vortex_mini_hello_device_buffers`: `37224` host-to-device bytes and `88` initial device-to-host bytes across `7` buffers. `reports/rtlmeter_vortex_dcr_schedule.json` materializes the ordered `9` DCR writes into a `72` byte little-endian runtime table and records the reset/valid timing protocol from `tb.sv`; it is still not runtime DCR application. `src/hybrid/vortex_runtime_upload.h`, `src/hybrid/vortex_observable_export.h`, and `src/hybrid/vortex_runtime_sequence.h` provide fake-driver-tested upload/export/runtime-sequence helpers, and `reports/rtlmeter_vortex_cuda_runtime_sequence_preflight.json` proves the sequence shape against the real CUDA Driver API with a no-op kernel callback. Vortex has now crossed the first CPU-vs-hybrid gate: the canonical `vlgpugen` std::ref pointer-return fix CUBIN reaches `after_cuCtxSynchronize`, exports `memory_post_condition` authority, and `reports/rtlmeter_vortex_timing.json` records hybrid median `0.4504947270033881s` versus CPU `0.22s` (`hybrid_vs_cpu_ratio=2.047703304560855`, no speedup claim). Treat Vortex `mini:hello` as a measured negative first gate; try Vortex `mini:saxpy` or `mini:sgemm` only after the active EH1/EH2 measurement blockers are addressed.
   `reports/rtlmeter_non_veer_hybrid_measurement_summary.json` now adds the comparable hybrid split index: `measured_design_count=2`, `measured_shape_count=20`, `gpu_favorable_shape_count=20`, `unmeasured_first_gate_candidate_count=2`, NVDLA `favorable_ratio=1.0`, and Vortex `cpu_vs_hybrid_timing_present=false`. This makes the current next step explicit: extend NVDLA hot-SS measurement before claiming broader RTLMeter GPU usefulness, while keeping Vortex as the next architecture-diverse first-gate once its lowered-TB invocation and observable authority are wired.
   `reports/rtlmeter_non_veer_hybrid_next_queue.json` now turns that split into an ordered next-measurement queue. Priority 1 is `nvdla_hot_ss_measurement_extension`: repeat or extend the best measured NVDLA hot-SS bucket, `state_batch_and_repeated_step`, with preferred shape `1024x64` on `nvdla_cmac_a2cacc`. Priority 2 is `vortex_mini_hello_first_cpu_vs_hybrid_gate`; its current first blocker has moved past memory-helper integration and kernel artifact generation to real artifact wiring.
   Latest Vortex audit refinement: `reports/rtlmeter_vortex_observable_authority_audit.json` now reports `real_runtime_observable_authority_ready=true`, `real_cuda_materialized_runtime_authority_ready=true`, and authority source `memory_post_condition`. `reports/rtlmeter_vortex_timing.json` measures three authority-passing repeats and records hybrid median `0.4504947270033881s` versus CPU `0.22s`, so this is a measured negative first gate, not a speedup claim.
   This latest audit refinement supersedes the older same-paragraph shorthand that described generated lowered-TB invocation/authority, verifier-clean artifact generation, missing callback wiring, or PTX module-load/JIT timeout as the remaining Vortex blocker. The observed immediate blocker is kernel illegal memory access, not descriptor source ambiguity, DPI-format ambiguity, memory-helper integration, landingpad/personality verification, callback ABI wiring, or `cuModuleLoad`.
   `reports/rtlmeter_nvdla_hot_ss_measurement_plan.json` now materializes priority 1 as a concrete, non-executing NVDLA plan: repeat-median confirm `1024x64`, check `512x64`, probe `2048x64`, and separate the state-batch effect with `1024x1`, all on `NVDLA.nvdla_cmac_a2cacc`. This keeps the next useful measurement on the small hot-SS target and leaves `NVDLA.nvdla_cmac_core_mac` deferred because of the recent high `ptxas` compile-cost observation.
   `reports/rtlmeter_nvdla_hot_ss_plan_dry_run.json` preflights all four planned commands successfully. The first plan item now has repeat-median evidence in `reports/nvdla_cmac_a2cacc_repeat_median_1024x64.json`: `repeat_count=3`, `coverage_output_equivalence_all_passed=true`, coverage-output mismatch count `0` in all samples, median CPU `2142.1 ms`, median hybrid wall `1.755 ms`, and median CPU/hybrid wall speedup `1430.950752393981x`. Treat this as scoped NVDLA hot-SS usefulness evidence only; raw final-state equality still fails on Verilator/internal fields.
   The lower-neighbor `512x64` plan item now also passes repeat-median coverage-output equivalence in `reports/nvdla_cmac_a2cacc_repeat_median_512x64.json`, with median CPU `1056.75 ms`, median hybrid wall `1.602 ms`, and median CPU/hybrid wall speedup `663.2209737827715x`. The larger-state `2048x64` plan item also passes in `reports/nvdla_cmac_a2cacc_repeat_median_2048x64.json`, with median CPU `4244.47 ms`, median hybrid wall `1.662 ms`, and median CPU/hybrid wall speedup `2553.8327316486166x`. The state-batch-only `1024x1` plan item passes in `reports/nvdla_cmac_a2cacc_repeat_median_1024x1.json`, with median CPU `2090.2 ms`, median hybrid wall `2.628 ms`, and median CPU/hybrid wall speedup `791.3432267884323x`. `reports/rtlmeter_nvdla_hot_ss_repeat_summary.json` summarizes the four-shape plan as four measured, four coverage-passed, and four GPU-favorable shapes; `2048x64` is the best measured shape. State batching alone is favorable, and repeated-step batching improves the best observed wall ratio further.
   `reports/rtlmeter_gpu_favorable_conditions_audit.json` now closes the current search question as `goal_satisfied_by_nvdla_hot_ss`: NVDLA `a2cacc` scoped hot-SS has reproducible positive evidence, while Vortex now has a measured architecture-diverse first CPU-vs-hybrid gate, but it is slower than the CPU reference and remains a negative first-gate result.
3. **Scientific CIRCT HLS-friendly source variants**: `reports/scientific_circt_verilator_callsite_entrypoint.json` first closed the scoped direct Verilator-generated callsite boundary for `microgpt_attention_head,1024x1` with output/checksum equality and `cpu_to_bridge_hybrid_wall_speedup=6.126758590128443x`. The follow-up `reports/scientific_circt_hls_attention_head4.json` measures a four-independent-head HLS-friendly source variant and improves bridge-wall speedup to `13.301119215779238x`. `reports/scientific_circt_hls_mlp_block_variants.json` extends the same pattern: `mlp4_hls_friendly` improves baseline MLP speedup from `2.28894x` to `9.922827450510521x`, `inference2_hls_friendly` improves baseline inference speedup from `3.62419x` to `9.799333107174757x`, while `block2_hls_friendly` lowers and matches output/checksum but does not improve the already GPU-favorable block baseline (`5.56609843788867x` versus `5.75973x`). The selection policy now has source-variant actions: promote attention/MLP/inference HLS variants, keep the baseline for block2.
4. **Docs pointer sync**: Keep `config/selection.json`, `docs/status.md`, this roadmap, README, and `for_codex/issues.md` aligned on `advance_stage124_source1065_after_sources976_1006_1020_diagnostic_atomic_suppression_cuda700`.
5. **Simple verification doc**: Keep `docs/migration_notes.md` “Gap from a minimal verification setup” accurate when entrypoints or prerequisites change.
6. **Gate chain hygiene**: When advancing `current_priority`, update `completed_goal_evidence` in `config/selection_extensions.json` only with tracked records; keep linked source-of-truth files clone-reproducible.
7. **Native Verilator sidecar track**: Keep #59 as a related native-path side track under #46, not the global current priority while FC-069 integrates the gateGPT ordering-aware token-loop path. Do not treat stamp/build-driver success as shim-entry evidence; the final `obj_dir/V<top>` link inputs must include the sidecar shim object/library or equivalent repo-owned runtime object.
8. **RTLMeter first seed**: Keep `Example:kind:hello` scoped and non-claiming. The reviewed stdout/cycles source-closure authority now exists in the RTLMeter authority registry, runner argv handoff executes through a thin runner CLI before stdout/cycles observation, and the latest real opt-in run reaches `status=passed` / `comparison=passed` with marker-backed `execution_authority=true` and `sidecar_execution_invoked=true`. This is historical first-seed proxy/marker handoff evidence only: `gpu_execution_claimed=false`, `speedup_claimed=false`, `runtime_abi=false`, CPU-as-GPU fallback is forbidden, and metadata-only authority registries, `run_hybrid_template.py` launch templates, and runner metadata must not become RTLMeter acceleration evidence. The proxy lane (#49/#51/#53) is frozen under the native Verilator sidecar goal; current RTLMeter correctness is gated on FC-064 / #63 for VeeR-EL2, with FC-058 / #58 retained as related native-path context.
9. **RTLMeter VeeR-EL2 design CPU**: FC-064 / #63 is the passing fail-closed automatic readiness gate for `VeeR-EL2:default:hello`. The current inspection verifies source closure, program identity, observable expression binding, PC/GPR schema, ICCM/DCCM 4-bank ECC preload schema, GPU state-image initialization schema, and RTLMeter stdout/cycles compare binding. The materializer emits the reviewed extracted state image for `hello` with inactive ICCM/DCCM bank preloads. A real VeeR build records an automatic root-image to syms-state-image rebuild, produces `vl_batch_gpu.cubin` (`storage_size=433472`), and maps 52 required root fields from the generated layout, including reset/nmi vectors. The reviewed executable `src/tools/veer_el2_sidecar_executable.py` consumes the extracted state image, materializes a syms-state init image, writes the reset/nmi vectors, drives a clock/reset patch, launches the generated artifact, dumps GPU state, and writes sidecar stdout/cycles files without copying CPU observables. The bridge reaches `status=verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed` with `cpu_cycles=2229` and `gpu_cycles=2229`. FC-037 timing now records `sidecar_slower_than_serial_cpu` for `hello`; no GPU usefulness or speedup claim is allowed.

**Recommended cleanup order** (deeper refactors): see **「整理の順序（推奨）」** in `docs/migration_notes.md`.

## Plan

1. Keep active surface compact.
2. Keep `config/selection.json` compact (core pointer) and historical maps in `config/selection_extensions.json`; merge via `src/tools/selection_state.py` when tooling needs the full selection.
3. Keep `config/README.md` as the map for config roles and add/move rules.
4. Keep generated evidence reproducible under `reports/` and build outputs under `artifacts/`, but do not retain them as source of truth.
5. Make hybrid launch as close as possible to Verilator usage first, while keeping the sidecar boundary frontend-neutral enough for CIRCT.
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

Use FC-073 / #73 as the current gateGPT token-loop diagnosis gate. The required
advance is no longer broad RTLMeter timing, Stage117 dirty-boundary discovery,
Stage118 normal intrablock instruction probing, Stage119 skipped-span
identification, or Stage120/121 producer-selector diagnostic-atomic probing.
The current blocker has moved into Stage124 record318 transition probing after
source1324/source976/source1006/source1020 diagnostic suppression. Stage124 has reached source1058
with source976/source1006/source1020 suppression and `transition_found=false`; the next
action is source1065 with source976/source1006/source1020 suppression carried forward.
Do not treat CUBIN/PTX generation,
root-field mapping, materializer readiness, prelaunch readiness, or correctness
alone as RTLMeter speedup or usefulness evidence.

Parser boundary definition:

- source gate: `config/scaling_gates/define_verilator_native_option_parser_source_patch_boundary_gate.json`
- source review gate: `config/scaling_gates/review_verilator_native_option_parser_source_patch_boundary_gate.json`
- descriptor/apply-check definition gate: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json`
- descriptor/apply-check review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json`
- descriptor/apply-check implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json`
- descriptor/apply-check implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_implementation_gate.json`
- build-only validation definition gate: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json`
- build-only validation review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json`
- build-only validation run gate: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json`
- compile-fix definition gate: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_compile_fix_gate.json`
- compile-fix review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json`
- compile-fix implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_compile_fix_gate.json`
- compile-fix build-only validation run gate: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json`
- compile-fix build-only validation review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json`
- parser-behavior definition gate: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json`
- parser-behavior definition review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json`
- parser-behavior smoke run gate: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json`
- parser-behavior smoke review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_run_gate.json`
- parser-integer hardening definition gate: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json`
- parser-integer hardening review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json`
- parser-integer hardening implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json`
- parser-integer hardening smoke run gate: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json`
- parser-integer hardening smoke review gate: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate.json`
- parser-to-adapter handoff boundary gate: `config/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json`
- parser-to-adapter handoff boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json`
- parser-to-adapter handoff fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_handoff_fixture_gate.json`
- parser-to-adapter handoff fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json`
- parser-to-sidecar plan-resolution boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json`
- parser-to-sidecar plan-resolution boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json`
- parser-to-sidecar plan-resolution fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json`
- parser-to-sidecar plan-resolution fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate.json`
- parser-to-sidecar plan-resolution status hardening definition gate: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json`
- parser-to-sidecar plan-resolution status hardening review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json`
- parser-to-sidecar plan-resolution status hardening implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json`
- parser-to-sidecar plan-resolution status hardening implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate.json`
- parser-to-sidecar plan-resolution handoff-contract boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json`
- parser-to-sidecar plan-resolution handoff-contract boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json`
- parser-to-sidecar plan-resolution handoff-contract fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate.json`
- parser-to-sidecar plan-resolution handoff-contract fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_implementation_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening definition gate: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_implementation_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan execution boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan execution boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan sidecar execution run gate: `config/scaling_gates/run_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_gate.json`
- parser-to-sidecar plan-resolution handoff-contract-to-operator-plan sidecar execution run review gate: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_run_gate.json`
- direct command-path boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_boundary_gate.json`
- direct command-path boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_boundary_gate.json`
- direct command-path fixture definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_fixture_gate.json`
- direct command-path fixture review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_gate.json`
- direct command-path fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_gate.json`
- direct command-path fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_implementation_gate.json`
- direct command-path fixture payload validation hardening definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json`
- direct command-path fixture payload validation hardening review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json`
- direct command-path fixture payload validation hardening implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json`
- direct command-path fixture payload validation hardening implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_implementation_gate.json`
- direct command-path sidecar stage-plan materialization boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate.json`
- direct command-path sidecar stage-plan materialization boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate.json`
- direct command-path sidecar stage-plan materialization fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_gate.json`
- direct command-path sidecar stage-plan materialization fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_implementation_gate.json`
- direct command-path sidecar stage-plan execution boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate.json`
- direct command-path sidecar stage-plan execution boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate.json`
- direct command-path sidecar stage-plan execution run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_gate.json`
- direct command-path sidecar stage-plan execution run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_run_gate.json`
- direct command-path native invocation boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_boundary_gate.json`
- direct command-path native invocation boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_boundary_gate.json`
- direct command-path native invocation fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_fixture_gate.json`
- direct command-path native invocation fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_fixture_implementation_gate.json`
- direct command-path native invocation execution boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate.json`
- direct command-path native invocation execution boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate.json`
- direct command-path native invocation execution run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_execution_gate.json`
- direct command-path native invocation execution run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_execution_run_gate.json`
- direct command-path native invocation patched-binary selection definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_selection_gate.json`
- direct command-path native invocation patched-binary selection review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_selection_gate.json`
- direct command-path native invocation patched-binary retry run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_gate.json`
- direct command-path native invocation patched-binary retry run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_run_gate.json`
- direct command-path native invocation sidecar authority boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json`
- direct command-path native invocation sidecar authority boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json`
- direct command-path native invocation first scoped sidecar execution boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate.json`
- direct command-path native invocation first scoped sidecar execution boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate.json`
- direct command-path native invocation first scoped sidecar execution run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_gate.json`
- direct command-path native invocation first scoped sidecar execution run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_run_gate.json`
- direct command-path native invocation direct sidecar launch boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate.json`
- direct command-path native invocation direct sidecar launch boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate.json`
- direct command-path native invocation direct sidecar launch run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_gate.json`
- direct command-path native invocation direct sidecar launch run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_run_gate.json`
- direct command-path native invocation direct-launch handoff implementation boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json`
- direct command-path native invocation direct-launch handoff implementation boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json`
- direct command-path native invocation direct-launch handoff fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_gate.json`
- direct command-path native invocation direct-launch handoff fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_implementation_gate.json`
- direct command-path native invocation direct-launch handoff run boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate.json`
- direct command-path native invocation direct-launch handoff run boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate.json`
- direct command-path native invocation direct-launch handoff run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_gate.json`
- direct command-path native invocation direct-launch handoff run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_gate.json`
- direct command-path native invocation sidecar-launcher bridge boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate.json`
- direct command-path native invocation sidecar-launcher bridge boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate.json`
- direct command-path native invocation sidecar-launcher bridge fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_gate.json`
- direct command-path native invocation sidecar-launcher bridge fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_implementation_gate.json`
- direct command-path native invocation sidecar-launcher run boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json`
- direct command-path native invocation sidecar-launcher run boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json`
- direct command-path native invocation sidecar-launcher run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_gate.json`
- direct command-path native invocation sidecar-launcher run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_gate.json`
- direct command-path native invocation sidecar-launcher invocation boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate.json`
- direct command-path native invocation sidecar-launcher invocation boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate.json`
- direct command-path native invocation sidecar-launcher invocation fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_fixture_gate.json`
- direct command-path native invocation sidecar-launcher invocation fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_fixture_implementation_gate.json`
- direct command-path native invocation sidecar-launcher invocation run boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate.json`
- direct command-path native invocation sidecar-launcher invocation run boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate.json`
- direct command-path native invocation sidecar-launcher invocation run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_gate.json`
- direct command-path native invocation sidecar-launcher invocation run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_gate.json`
- direct command-path native invocation process-to-launcher CLI boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate.json`
- direct command-path native invocation process-to-launcher CLI boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate.json`
- direct command-path native invocation process-to-launcher CLI fixture implementation gate: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_gate.json`
- direct command-path native invocation process-to-launcher CLI fixture implementation review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_implementation_gate.json`
- direct command-path native invocation process-to-launcher CLI execution boundary definition gate: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate.json`
- direct command-path native invocation process-to-launcher CLI execution boundary review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate.json`
- direct command-path native invocation process-to-launcher CLI execution run gate: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_gate.json`
- process-to-launcher CLI execution run review gate: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_run_gate.json`
- selected next gate: `review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_helper_implementation_gate`
- scope: attempt only the reviewed `pulp_ita_mha` / `64x1` direct-launch handoff path before public CLI broadening, automatic allocation, arbitrary filelist support, or timing
- defined native minimum: `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`
- wrapper/shim compatibility kept out of native minimum: `--sim-accel-shape <NxS>`, target-first registry lookup, print modes, JSON operator plans, resident modes, and dataset-backed flows
- parser non-inference: coverage manifests, host-probe metadata, source closure, state paths, and report paths are sidecar handoff-contract fields, not parser-discovered fields
- handoff boundary: native parser values stop at an adapter payload; the parser preserves ordinary Verilator build inputs and positive state/step schedule fields, while source closure, coverage target, state/report paths, host-probe metadata, and compare details remain sidecar-owned
- handoff review: accepts the adapter payload only and clarifies that `coverage_output_equivalence` is a later sidecar correctness-policy reference, not native-parser compare evidence
- handoff fixture implementation: adds `src/tools/verilator_native_option_parser_sidecar_handoff.py` as the adapter authority and keeps resolved sidecar outputs absent from the payload
- handoff fixture review: accepts that non-executing adapter authority, fixes `correctness_policy_ref` as reference-only, and advances to defining sidecar plan resolution
- plan-resolution boundary definition: requires explicit sidecar context such as target, mode, template or registry entry, and source gate/manifest reference before an adapter payload may call or mirror `sidecar_stage_plan`; parser-owned values remain schedule and preserved Verilator build inputs only
- plan-resolution boundary review: accepts only that explicit-context, non-executing planning definition and selects a fixture that must reject payload-only resolution
- handoff-contract fixture review: accepts only metadata-only, ready-only construction after adding an explicit `efficiency_estimate_invoked` rejection before `sidecar_handoff_contract(stage_plan)`
- operator-plan boundary definition: defines whether accepted metadata can feed non-executing command argv, estimate-command, efficiency-estimate, and operator-plan metadata, and defines rejection for closed, unsupported, malformed, or prepopulated metadata
- dry-run result: 12 non-executing preview/rejection commands matched expected exits; the two static `filelist_*` targets expose `64x1`, the expanded future Verilator spelling, and `coverage_output_equivalence`; estimate mode is separate
- accepted caveat: missing shape halves, mixed shape spelling, and non-positive counts reject through the shared mapper, but unknown accelerators currently reject at argparse choices
- definition assigns unknown-accelerator validation to the parser-stub validation contract and records current argparse choices as wrapper compatibility only
- review accepts that assignment narrowly, with the caveat that current observable rejection still happens through wrapper argparse choices
- fixture must make unknown accelerator rejection, paired positive state/step validation, compact-shape rejection outside the native minimum, ordinary Verilator arg preservation, and structured handoff fields testable without a Verilator source tree
- fixture contract is defined as an importable helper contract, not a public CLI, and it must not call target registry lookup, source closure inference, coverage manifest selection, host-probe metadata, execution, compare, or allocation logic
- direct command-path fixture implementation: adds `src/tools/verilator_native_option_parser_direct_command_path_fixture.py` as an importable non-executing helper that returns reference-only `sidecar_plan_boundary` metadata and rejects parser-prepopulated sidecar-owned fields
- implementation adds `src/tools/verilator_native_option_parser_stub_fixture.py` and `parse_verilator_native_option_stub`, bypassing wrapper argparse choices rather than counting current CLI rejection behavior as success
- implementation review accepts the helper narrowly and requires the next gate to define the source/overlay patch boundary before any native parser claim
- source-patch boundary selects a future repo-owned overlay patch descriptor under `overlays/verilator/patches/`, while keeping vendored Verilator source and a Verilator submodule out of scope
- source-patch boundary review accepts that boundary and requires the next gate to pin descriptor schema/path, upstream Verilator ref, touched upstream files, and a reproducible apply-check command before any patch implementation claim
- descriptor/apply-check definition pins upstream Verilator `v5.048` at `d0aa828c217410fffc73d92077b6f4f54830357c`, future descriptor and patch paths under `overlays/verilator/patches/`, first source touch candidates `src/V3Options.h` and `src/V3Options.cpp`, and expected apply-check exit code `0`
- descriptor/apply-check review accepts the boundary narrowly, treats the pinned commit as the peeled release-tag commit, and allows the next gate to add only the accepted descriptor and patch files plus source-of-truth/test/doc alignment
- descriptor/apply-check implementation adds the descriptor and patch files, validates descriptor JSON, and records `git apply --check` exit code `0` against Verilator `v5.048` peeled commit; the patch touches only `src/V3Options.h` and `src/V3Options.cpp` and leaves the new options undocumented to keep docs/test_regress out of first patch scope
- descriptor/apply-check implementation review accepts only the descriptor and patch applicability evidence, records that Verilator build/regression/execution/timing are still unproven, and selects a build-only validation definition gate next
- build-only validation definition selects an external clean-checkout apply plus `make ... verilator_bin` command sequence and keeps parser behavior, upstream regression, docs/test_regress, sidecar runtime/ABI, execution, timing, arbitrary filelist support, and automatic allocation deferred
- build-only validation review accepts the narrow `verilator_bin` build boundary and requires the run gate to record whether `VERILATOR_INSTALL` was supplied or mechanically defaulted
- build-only validation run records descriptor validation and apply-check success, a checkout-local `VERILATOR_INSTALL` default, `verilator_bin` target reached, and `make` exit code `2`; the failure is patch compile/link, caused by `V3Options.h` additions after `#endif  // guard`
- compile-fix definition keeps the existing patch path, rejects zero-context hunks, and pins contextual anchors for `V3Options.h` fields/accessors plus `V3Options.cpp` notify/parser/registration hunks
- compile-fix review accepts the in-place repair boundary, with the caveat that the `V3Options.cpp` `};` helper anchor is valid only with `callStrSetter` prior context and `parseOptsList()` bounds
- compile-fix implementation updates the existing descriptor/patch, validates descriptor JSON, passes clean-checkout `git apply --check`, applies the patch, and records post-apply location sanity for `V3Options.h` and `V3Options.cpp`; `make verilator_bin` remains deferred to the next build-only rerun gate
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
- historical next task at this checkpoint: `review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_helper_implementation_gate`; historical project priority at that checkpoint was `rtlmeter_veer_el2_timing_usefulness_measurement_gate`
- reason: the compact suite validates debug inspection surface, high/low shape classes, resident dry-run, and filelist execution evidence; the resident decode-like mitigation is measured, public-pack refreshed, and externalized, and the scoped filelist-derived repeat-median result is accepted, public-pack refreshed, externally closed, selected for conservative policy broadening, defined, separated into a dry-run workflow, reviewed, packaged into a public-refresh definition, accepted as a public-pack archive dry-run, externally closed, selected for scoped non-dry-run execution definition, and fixed to the two policy-recommended `64x1` commands

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
- active `config/` file count: `146`
- tracked gate JSON records under `records/scaling_gates/`: `966`
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

Active RTLMeter Vortex/VeeR hybrid-measurement objective:

- Use `reports/rtlmeter_vortex_veer_hybrid_measurement_matrix.json` as the
  generated review table for `Vortex:mini:hello`,
  `VeeR-EH1:default:hello`, `VeeR-EH2:default:hello`, and
  `VeeR-EL2:default:hello`.
- The matrix summary now raises the Vortex runner observation fields to the top
  level: `vortex_runner_cycle_count=40897`,
  `vortex_runner_proxy_handoff_observed=true`, and
  `vortex_runner_gpu_execution_claimed=false`. It also records
  `vortex_generated_fake_driver_authority_passed=true` and
  `vortex_real_verilator_runtime_sequence_marker_observed=true`, while
  `vortex_real_verilator_runtime_stub_rebuilt=true`,
  `vortex_real_verilator_runtime_bridge_stub_rebuilt=true`, and
  `vortex_real_verilator_runtime_invocation_probe_executed=true`, with
  `vortex_real_verilator_materialized_runtime_args_probe_executed=true` and
  `vortex_real_cuda_memory_transport_passed=true`,
  `vortex_real_cuda_memory_transport_h2d_bytes=37224`,
  `vortex_real_cuda_memory_transport_d2h_initial_bytes=88`,
  `vortex_real_cuda_runtime_sequence_preflight_passed=true`,
  `vortex_real_cuda_runtime_sequence_preflight_h2d_bytes=37224`,
  `vortex_real_cuda_runtime_sequence_preflight_d2h_initial_bytes=88`, and
  `vortex_real_runtime_observable_authority_ready=false`; the matrix also
  records `vortex_real_vortex_kernel_artifact_ready=true`,
  `vortex_kernel_artifact_build_attempt_status=passed`,
  and `vortex_kernel_artifact_build_landingpad_blocked=false`. A
  syms-state-image rebuild clears the generated artifact prelaunch rejection
  (`prelaunch_rejection_required=false`), and the generated `Vsim__main.cpp`
  now wires `rtlmeter_vortex_real_cuda_launch_root_storage_kernel` with the
  root-storage launch ABI observed. The full PTX remains too expensive for
  bounded `ptxas`, but the canonical std::ref-fix single-entry CUBIN reaches
  `after_cuCtxSynchronize`, exports `memory_post_condition` authority, and
  `reports/rtlmeter_vortex_timing.json` records the first CPU-vs-hybrid timing
  gate as a measured negative result. The runtime marker and expected-fail invocation probe were stripped
  from generated `Vsim__main.cpp`, and the obj_dir rebuild passes.
- Use `reports/rtlmeter_hybrid_measurement_difficulty.json` as the generated
  triage table for measurement difficulty. It currently classifies
  `Vortex:mini:hello` as measured/low difficulty score `1` with a measured
  negative CPU-vs-hybrid result, `VeeR-EH1:default:hello` as high difficulty
  score `6`, `VeeR-EH2:default:hello` as high difficulty score `25`, and
  `VeeR-EL2:default:hello` as measured/low difficulty score `1`. It also
  records EH1's first GPU eval-launch CUDA 700 path and EH2's current
  post-prelaunch blocker: the syms-state image artifact clears unsafe syms GEP
  coverage (`storage_size=623168`, `root_offset_in_state=192`), the
  entry-pruned CUBIN clears module load, but first eval still fails with CUDA
  700 and the entry-pruned PTX slice contains `1456` C++/Verilator
  runtime-residue hits across `134` suspicious function definitions. The
  expanded host-cleanup path removes the remaining scheduler/container call
  sites, but direct no-patch eval-only still fails at `before_first_step_sync`
  with CUDA 700. Return-before-eval and prologue-only return-before-eval-call
  probes both pass. Staged `_eval` / `eval_phase__act` probes now show
  `eval_triggers__act` is safe, but the `trigger_orInto__act` region faults;
  inline probes narrow that to an eval-phase-context store into
  `__VnbaTriggered` at `root+472408`. No-op, destination load, source load, and
  before-store probes pass; adjacent `__VactTriggered`, root-base, and
  entry-context `__VnbaTriggered` stores pass; padded 2MiB state and maxr128 do
  not clear it. Direct-root/minimal `__VnbaTriggered` store probes now pass, the
  reference-wrapper/cvta store path still faults, and
  `std::reference_wrapper::get()` canonicalization is applied in `vlgpugen`; the
  canonical full eval-only CUBIN still fails with CUDA 700. Follow-up probes
  show `_eval` passes before `eval_phase__act`, one `eval_phase__act` call
  faults, and ret0 `eval_phase__act` still faults by the
  `trigger_orInto__act` boundary. The latest `trigger_orInto__act` probes pass
  entry, dst-load, src-load, and before-store, then the after-store probe faults
  with CUDA 700. `VlUnpacked<T,1>` index-call canonicalization rewrites `57`
  single-element index calls; after that, `eval_phase__act` can return before
  `trigger_orInto__act`, but an immediate-return `trigger_orInto__act` helper
  call still faults with CUDA 700. A targeted rewrite now replaces that EH2
  helper call with inlined load/or/store and removes the call from the eval
  entry slice, but the rewritten eval-only CUBIN still faults at first-step
  sync. Store-value probes show skip/zero/dst variants all still fault, while
  skip-store return probes pass through `trigger_anySet__act` and
  `timing_resume`; returning after `eval_act` still faults. Follow-up
  `eval_act` return probes pass after callseq `950` and `951`, then fault after
  callseq `952`. Deeper probes show `dec_cam[0]` still faults even with a
  minimal `ret` body; skipping only callseq `952`, or callseq `952` and `953`,
  still faults, while skipping callseq `952`, `953`, and `954` passes. A
  follow-up vlgpugen pass canonicalizes `VlWide<N>` pointer conversions
  (`cvPj` and `cvPKj`) to their first pointer argument; the latest EH2 lowering
  reports `VlWide pointer conversions canonicalized: 16394`. The regenerated
  entry-pruned CUBIN builds with `ptxas -O0`, but eval-only execution still
  fails at first-step sync with CUDA 700. Current post-`VlWide` probes show
  kernel relocation and `_eval` prologue pass, `eval_phase__act` passes through
  `eval_triggers__act` and trigger-merge loads, and a nonzero trigger store
  passes when `_eval` returns immediately. With normal `_eval` continuation,
  NBA `trigger_anySet` passes before `eval_nba`, then CUDA 700 appears after
  crossing `eval_nba`. The remaining EH2 blocker is now
  `localize_eh2_post_vlwide_eval_phase_nba_eval_nba_cuda700_before_bridge_timing`.
  This is blocker metadata only, not a timing result or speedup claim.
- Treat `VeeR-EL2:default:hello` as the only measured row. Its best current
  measured sidecar row is
  `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json`
  (`sidecar_wall_s_median=0.641226`,
  `sidecar_vs_cpu_parallel_ratio=3.460382`, correctness passed, speedup not
  claimed).
- `reports/rtlmeter_veer_family_surface_audit.json` now classifies
  `VeeR-EH1:default:hello` and `VeeR-EH2:default:hello` as
  `sidecar_bridge_preflight_surface_missing`: descriptor/testbench preload and
  mailbox evidence are present enough to start a design-specific port. The
  fail-closed EH1/EH2 authority registries, state-layout preflight reports, and
  preload state-image materializer reports now exist. Fail-closed sidecar bridge
  preflight reports also exist. The state-image and bridge reports keep
  `state_layout_ready=false`, `sidecar_bridge_invoked=false`,
  `gpu_execution_claimed=false`, `timing_measured=false`, and
  `speedup_claimed=false`. EH1/EH2 CPU reference observables now pass with
  `1044` RTLMeter cycles / `0.03s` for EH1 and `2325` RTLMeter cycles / `0.06s`
  for EH2, so the bridge preflight no longer lacks CPU reference observables.
  The matrix now folds the EH bridge preflight `missing_build_context` into
  row-level missing prerequisites. After applying the repo-owned mailbox
  public-flat overlay and rebuilding the EH1/EH2 CPU-reference workRoots, the
  generated `Vsim___024root.h` marker and offset probe now runs against
  `root_obj_dir_variant=mailbox_public_flat` for both targets. The root-offset
  reviews have complete marker groups for control scalars, PC candidates, cycle
  counters, mailbox observables, and GPR observables, and now select the
  root-offset ABI for both targets. The patch/rebuild, ABI-review, and
  EH-specific executable-boundary blockers are gone. Both still need an
  executed bridge comparison and timing. Do not reuse the measured EL2
  executable directly for EH1 or EH2; its authority target, root-symbol/state-layout paths, and `hello`
  program SHA are EL2-specific.
- Treat `Vortex:mini:hello` as the immediate engineering path: replace the no-op
  runtime callback with a root-storage-backed real kernel launch/export, export
  stdout or memory post-condition authority, and run the first CPU-vs-hybrid
  timing report.
  `reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json` now
  confirms the real materialized buffer artifacts and DCR schedule are ready for
  that call boundary, and
  `reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json` now
  proves a generated lowered-TB-shaped C harness can consume those artifacts and
  call the runtime sequence.
  `reports/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json` now
  proves a generated lowered-TB-shaped C harness can also route the real
  materialized memory artifacts through `vortex_memory_model_device.h`, replay
  the post condition to zero mismatches, and capture `TEST PASSED` bytes through
  IO_COUT. `reports/rtlmeter_vortex_cuda_runtime_sequence_preflight.json` now
  proves the real CUDA Driver API upload/DCR-callback/no-op-kernel-callback/
  observable-export/release sequence for `37224` H2D and `88` D2H-init bytes.
  `reports/rtlmeter_vortex_real_kernel_artifact_preflight.json` and
  `reports/rtlmeter_vortex_kernel_artifact_build_attempt.json` now show that the
  real Vortex PTX/meta artifact exists and that the build attempt passes without
  the previous landingpad/personality verifier error. This is still not Vortex
  kernel execution or timing.
  `reports/rtlmeter_vortex_cpu_reference_summary.json` now records the
  native CPU reference as passed (`0.22s`, `40897` clocks, `TEST PASSED`), and
  `reports/rtlmeter_vortex_hybrid_candidate_summary.json` records the current
  hybrid candidate as fail-closed after the PATH-selected wrapper captures the
  sidecar planning request and Vortex context makes the handoff metadata ready.
  The reviewed Vortex authority registry source closure, stdout/cycles runner
  contract, runner argv handoff, and direct-native stdout/cycles observation are
  now ready. The latest observed runner reaches `40897` cycles and `TEST PASSED`
  with `rtlmeter_proxy_handoff_observed=true`, while keeping
  `gpu_execution_claimed=false` and `speedup_claimed=false`. The remaining
  implementation work starts with the root-storage-backed kernel callback, then
  observable export authority, real Verilator
  generated lowered-TB integration, and CPU-vs-hybrid timing; it is not binary
  input parsing, wrapper selection, sidecar context selection, or host-side
  buffer materialization.
- Treat `VeeR-EH1` and `VeeR-EH2` as portability broadening work after Vortex or
  after an explicit priority change; they are descriptor-ready with fail-closed
  preload state images, CPU reference observables, and bridge preflight reports,
  and their mailbox-public-flat CPU-reference root headers have complete
  marker/offset candidate groups plus selected root-offset ABI entries.
  The generated matrix now carries bridge-internal missing context upward. EH1
  has a generated PTX module artifact ready for bridge execution. EH2 has a
  generated syms-state-image PTX artifact with
  `gpu_artifact_prelaunch_rejection_required=false`,
  `unsafe_syms_gep_covered_by_state_image=true`, and
  `root_offset_in_state=192`; the full PTX bridge still invokes
  `run_vl_hybrid` and times out at `before_cuModuleLoad` after `60s`, but the
  eval+patch entry-pruned EH2 CUBIN builds with `ptxas -O0`, launches the step-0
  patch+eval pair, and with `RUN_VL_HYBRID_SYNC_EACH_STEP=1` fails at
  `before_first_step_sync` with `CUDA error 700`; a no-patch eval-only probe
  reproduces the same fault, and 2MiB padded storage, a 64KiB stack limit, plus
  zero-init storage do not clear it. The static EH2 PTX residue probe now counts
  `1456` C++/Verilator runtime-residue hits and `134` suspicious function
  definitions. The expanded host-cleanup passes remove the remaining
  `VlDelayScheduler`, `VlCoroutineHandle`, `std::multimap`, and `_Rb_tree` call
  sites, but direct no-patch eval-only still fails with CUDA 700. Return-before-
  eval and prologue-only return-before-eval-call probes both pass. Staged and
  inline probes place the first CUDA 700 at the eval-phase-context
  `__VnbaTriggered` store (`root+472408`): loads and OR pass, adjacent and
  entry-context stores pass, and padded 2MiB plus maxr128 do not clear it.
  Direct-root/minimal store probes pass, the reference-wrapper/cvta path faults,
  and `std::reference_wrapper::get()` canonicalization still leaves the full
  eval-only CUBIN failing with CUDA 700. Canonical return probes now place the
  remaining fault inside `eval_phase__act` at the `trigger_orInto__act`
  destination-store path: entry, dst-load, src-load, and before-store pass, but
  after-store faults with CUDA 700. `VlUnpacked<T,1>` index-call canonicalization
  now rewrites `57` single-element index calls; after that, `eval_phase__act`
  passes when returning before `trigger_orInto__act`, but the immediate-return
  `trigger_orInto__act` helper call still faults with CUDA 700. A targeted
  rewrite removes that helper call by inlining load/or/store, but the rewritten
  eval-only CUBIN still faults at first-step sync. Store-value probes show
  skip/zero/dst variants all still fault, while skip-store return probes pass
  through `trigger_anySet__act` and `timing_resume`; returning after `eval_act`
  still faults. Follow-up `eval_act` return probes pass after callseq `950` and
  `951`, then fault after callseq `952`; deeper skip probes show callseq
  `952`/`953`/`954` are the first submodule act call boundary. A follow-up
  vlgpugen pass canonicalizes `VlWide<N>` pointer conversions (`cvPj` and
  `cvPKj`), but the rebuilt entry-pruned eval-only CUBIN still faults at
  first-step sync. Current probes pass through kernel relocation, `_eval`
  prologue and `eval_phase__act` trigger evaluation. A nonzero trigger store
  passes when `_eval` returns immediately; NBA `trigger_anySet` then passes
  before `eval_nba`, and CUDA 700 appears after crossing `eval_nba`. The next
  EH2 blocker is
  `localize_eh2_post_vlwide_eval_phase_nba_eval_nba_cuda700_before_bridge_timing`.
  EH1
  bounded bridge execution now reaches the real `run_vl_hybrid` call for `19`
  logical steps after root-image materialization. Stage tracing shows CUDA init,
  device lookup, and context creation pass, then the run times out after `20s`
  at `before_cuModuleLoad`; the next EH1 blocker is the PTX module load/JIT
  timeout behind `successful_gpu_launch_without_timeout`. A bounded offline
  cubin probe confirms this is not just a runtime timeout:
  `reports/rtlmeter_veer_eh1_ptxas_o0_probe.json` records `ptxas --opt-level 0`
  timing out after `180s` on the `17,684,220` byte / `630,613` line PTX, with
  `6,674,492` KB max RSS and no cubin output. The entry-pruned probe
  `reports/rtlmeter_veer_eh1_entry_pruned_module_probe.json` keeps only
  `vl_eval_batch_gpu` and `vl_apply_patch_schedule_gpu`; that `ptxas -O0` run
  passes in `17.98s` and emits an `11,701,952` byte cubin. The cubin loads,
  resolves both kernels, uploads the init state, and reaches the first synced
  eval launch, then fails with CUDA illegal memory access. Static PTX review
  then found reachable stdout/finish C++ runtime residue on that path. The
  required host-I/O stub pass now erases `47` EH1 host-I/O call sites and leaves
  zero matching calls in `vl_batch_gpu.host_io_stub_probe.ll`. Regenerating the
  host-I/O-stubbed single-entry eval CUBIN now succeeds (`6735488` bytes,
  `ptxas -O0` `15.29s`), but the eval-only bridge still exits with
  `CUDA error 700` at the first GPU eval launch. Runtime trace records
  `NUM_REGS=255`, `LOCAL_SIZE_BYTES=1776`, and last stage `before_final_sync`;
  a padded `2097152` byte init-state still faults, while compute-sanitizer is
  blocked before the first instrumented CUDA API in this environment. The next
  EH1 action is isolating the remaining scheduler/container/ABI device fault
  before stdout/cycles comparison.

| Case | Status | Next action |
|---|---|---|
| `Vortex:mini:hello` | Measured correctness/timing with no speedup claim: CPU `0.22s` / `40897` clocks; canonical real-CUDA materialized runtime reaches `after_cuCtxSynchronize`, exports `memory_post_condition`, and `reports/rtlmeter_vortex_timing.json` records hybrid median `0.4504947270033881s`, `hybrid_vs_cpu_ratio=2.047703304560855`, `cpu_vs_hybrid_speedup=0.48835199795434103` | Treat as measured negative first gate; continue EH1/EH2 unblock/timing |
| `VeeR-EH1:default:hello` | Not measured; CPU reference and mailbox-public-flat rebuild pass; root-offset ABI review ready; full generated PTX times out at module load, but entry-pruned eval+patch cubin builds in `17.98s`, loads, resolves kernels, uploads init state, and fails at the first synced `vl_eval_batch_gpu` launch with CUDA illegal memory access; host-I/O-stubbed probe IR now has zero matching stdout/finish/string call sites; regenerated host-I/O-stubbed single-entry eval CUBIN builds (`6735488` bytes, `ptxas -O0` `15.29s`) but the eval-only bridge still exits with `CUDA error 700` at first eval launch; runtime trace records `NUM_REGS=255`, `LOCAL_SIZE_BYTES=1776`, and a padded `2097152` byte init-state still faults | Isolate remaining scheduler/container/ABI device fault, then stdout/cycles comparison and timing |
| `VeeR-EH2:default:hello` | Not measured; CPU reference and mailbox-public-flat rebuild pass; root-offset ABI review ready; syms-state PTX artifact clears prelaunch rejection; full PTX bridge still times out after `60s` at `before_cuModuleLoad` on the `44377841` byte PTX, but the eval+patch entry-pruned CUBIN builds with `ptxas -O0`, loads, resolves kernels, uploads init state, launches step-0 patch+eval, and with sync-each-step fails at `before_first_step_sync` with `CUDA error 700`; a no-patch eval-only probe reproduces it, and padded2m, stack64k, plus zero-init probes do not clear it; `VlWide<N>` pointer conversions are canonicalized (`16394` rewrites); current post-`VlWide` probes show nonzero trigger store can pass if `_eval` returns immediately; NBA `trigger_anySet` passes before `eval_nba`, then CUDA 700 appears after crossing `eval_nba` | Localize/fix post-`VlWide` `eval_phase__nba` / `eval_nba` CUDA700, then bridge comparison and timing |
| `VeeR-EL2:default:hello` | Measured correctness-pass baseline; no speedup claim | Keep as measured baseline, not as a broad GPU-usefulness claim |

Recommended next gate:

`define_scientific_circt_source_variant_regression_harness_gate`

Acceptance criteria:

- use `for_codex/issues.md` and GitHub #69 as the source artifact/tracker
- verify `README.md`, `docs/status.md`, this roadmap, `for_codex/issues.md`, and `config/selection.json` agree that FC-069 is current
- use the latest schedule-owned ordering-aware result as the baseline: `16/16` source probe passed, the non-diagnostic same-CPU-oracle baseline is GPU wall `404.986 ms` / kernel `404.90036 ms` versus CPU oracle `107.71662899060175 ms` (`3.759735184762744x` slower), and no speedup/usefulness is claimed
- treat the guarded/liveout diagnostic path as validation-only and performance-negative: GPU wall `19232.031 ms` / kernel `19231.960938 ms`, `178.5428227769548x` slower than the same CPU oracle
- use the compact CFG clone materialization result as the new baseline: `65` blocks, `944` cloned instructions, `65` cloned terminators, `48` PHIs, `48` static CFG-clone liveout stores, unsupported terminators `0`, and `outline_call_count=3434752`
- resolve the baseline-isolation blocker: outline entry reaches `compact_cluster.cfg_clone.entry` and the generated IR verifies; post-capture compare validates reached CFG-clone liveout capture points (`liveout_frame_store_count=82434048`, `compare_count=250480`, `mismatch_count=0`, authority=true). The non-diagnostic same-CPU-oracle baseline is measured and still negative (`baseline_gpu_wall_ms=404.986`, `baseline_gpu_kernel_ms=404.90036`, CPU oracle `107.71662899060175 ms`, `3.759735184762744x` slower); the diagnostic guarded/liveout path is GPU wall `19232.031 ms` / kernel `19231.960938 ms` and remains validation-only at `178.5428227769548x` slower. The Pass emits partition-local eval continuation guard static shape for `8` guarded regions with `1344` successor-PHI incoming values. Runtime-noop derivation is blocked by successor PHI live-out for all `832` inspected selects (`0` elision-safe, authority `no_runtime_noop_derivation_authority`). Successor-PHI continuation user classification is complete for `168` successor PHIs / direct users / direct load users / load-consumed PHIs, with `0` direct non-load users, `168` load-result direct users, `0` unsupported load-result users, and `1` candidate cluster under `classification_only_no_runtime_skip_or_select_elision_authority`, so the analyzer keeps CPU-oracle validation blocked until inactive-path noop/skip authority and runtime guard execution observation exist.
- keep the older CFG-clone memory-read isolation, shadow liveout compare, valid-frame, and select-only PHI repair gates as historical preconditions; they are no longer the active next gate after successor-PHI continuation user classification.
- implement or measure the current next action recorded near the top of this roadmap
- do not claim speedup from a single run or from comparison against serial CPU alone
- keep broad `verilator --use-gpu`, arbitrary filelist inference, automatic GPU allocation, RTLMeter speedup/usefulness, CIRCT execution, raw-state equality, JSON runtime ABI, and production-readiness claims out of scope unless later gates prove them

Scientific-compute CIRCT side lane:

- `reports/scientific_circt_gpu_candidate_plan.json` is the current plan-only
  evidence for converting scientific kernels through CIRCT-generated
  SystemVerilog, Verilator, lowered LLVM IR suitability, and repeat-median
  CPU/hybrid measurement.
- The CIRCT toolchain is available through
  `source artifacts/toolchains/circt-firtool-1.149.0/env.sh`; the first
  materialization target, `dense_matmul_tile`, now lowers through `firtool` to
  SystemVerilog and passes a Verilator CPU reference observable.
- The first GPU timing surface for `dense_matmul_tile` is now measured at
  `64x1`, `256x1`, and `1024x1` with `inner_repeat=1000`. End-to-end timing is
  CPU-favorable at `64x1` but GPU-favorable at `256x1` and `1024x1`; kernel-only
  timing is GPU-favorable at all three measured shapes.
- `reports/scientific_circt_dense_matmul_tile_hybrid_advantage.json` connects
  the three timing reports to a common scientific hybrid summary and identifies
  `256x1` as the first measured end-to-end GPU-favorable shape.
- `batched_reduction` now follows the same testbench path:
  CIRCT-generated SystemVerilog, Verilator CPU reference, CUDA timing at
  `64x1`/`256x1`/`1024x1`, and hybrid advantage aggregation. It also first
  becomes end-to-end GPU-favorable at `256x1`.
- `reports/scientific_circt_gpu_selection_policy.json` now turns the repeated
  boundary into an explicit compile-time policy. After adding
  `stencil_2d_tile`, `softmax_exp_pipeline`, `microgpt_math_block`,
  `microgpt_attention_head`, `microgpt_mlp_slice`, `microgpt_block_slice`, and
  `microgpt_inference_slice`, the policy is
  candidate-specific: dense matmul, batched reduction, softmax/exp, microGPT
  math, the source-derived attention-head slice, and the block-level slice
  plus the two-token inference slice select GPU at `nstates >= 256`, while
  stencil and the reduced-width MLP slice select GPU at `nstates >= 1024`; all
  require `steps=1` and GPU-favorable measured kernel timing.
- The softmax/exp gate is now measured: `64x1` remains CPU-favorable
  end-to-end (`0.601074x`), while `256x1` (`1.86415x`) and `1024x1`
  (`5.75945x`) are GPU-favorable. This argues for a microGPT IR partition
  probe next: preserve matmul, reduction, and softmax-like arithmetic as
  GPU-selectable kernels instead of pushing only gateGPT-generated Verilator
  root-state control through late LLVM tweaks.
- `reports/scientific_circt_microgpt_ir_partition_probe.json` now projects the
  measured policy onto a microGPT-style graph at `256x1`: 8/10 nodes select
  GPU state-parallel candidates, while token-loop control and KV-cache state
  update remain CPU/new-mapping candidates. This is still not microGPT
  execution or CIRCT lowering of a full model, but it gives the next experiment
  a concrete partition target.
- `microgpt_math_block` now turns that partition target into a measured
  composite CIRCT/SystemVerilog testbench for dense-dot, softmax/exp-like, and
  reduction arithmetic. It passes Verilator CPU reference and records
  end-to-end speedups `0.239753x` at `64x1`, `1.2195x` at `256x1`, and
  `4.23625x` at `1024x1`; kernel-only timing is GPU-favorable at all three
  measured shapes. This is still not full microGPT execution, but it moves the
  lane beyond a policy-only partition probe.
- `microgpt_attention_head` now adds the first measured attention-head slice
  derived from the actual `third_party/microgpt.py` attention loop
  (`n_head=4`, `head_dim=4`). It passes CIRCT/SystemVerilog, Verilator CPU
  reference, and CUDA timing at the same shapes: `0.602488x` end-to-end at
  `64x1`, `1.8243x` at `256x1`, and `6.41385x` at `1024x1`, with kernel-only
  timing GPU-favorable at all three shapes. This is still not full block-size
  microGPT inference.
- `microgpt_mlp_slice` now adds the first measured source-derived MLP slice for
  the `mlp_fc1 -> ReLU -> mlp_fc2` structure. It passes CIRCT/SystemVerilog,
  Verilator CPU reference, and CUDA timing at the same shapes: `0.339622x`
  end-to-end at `64x1`, `0.333924x` at `256x1`, and `2.28894x` at `1024x1`,
  with kernel-only timing GPU-favorable at all three shapes. This is still not
  full hidden-width microGPT MLP inference, and it records that this light slice
  needs a larger batch than the attention/math slices.
- `microgpt_block_slice` now adds a measured block-level source-derived slice
  combining attention-style aggregation, residual-style addition, and MLP-style
  arithmetic. It passes CIRCT/SystemVerilog, Verilator CPU reference, and CUDA
  timing at the same shapes: `0.52329x` end-to-end at `64x1`, `1.70084x` at
  `256x1`, and `5.75973x` at `1024x1`, with kernel-only timing GPU-favorable at
  all three shapes. This is still not full `block_size` microGPT inference, but
  it is the strongest current direct-CIRCT bridge from isolated slices toward a
  fuller inference-slice lowering.
- `microgpt_inference_slice` now adds a measured two-token source-derived
  inference slice with token/position embedding-style arithmetic,
  KV-cache-style reuse, token1 attention over token0 and itself,
  residual/MLP-style arithmetic, and logit-style outputs. It passes
  CIRCT/SystemVerilog, Verilator CPU reference, and CUDA timing at the same
  shapes: `0.249726x` end-to-end at `64x1`, `1.24281x` at `256x1`, and
  `3.62419x` at `1024x1`, with kernel-only timing GPU-favorable at all three
  shapes. This is still not full `block_size` microGPT execution or
  training/autograd, but it is the current best direct-CIRCT bridge toward a
  fuller inference path.
- The comparison report now scans the actual `third_party/microgpt.py` source:
  it exposes `linear`, `softmax`, `rmsnorm`, `gpt`, attention, MLP, and
  autograd-training structure, and the comparison now records both
  `microgpt_math_block`, `microgpt_attention_head`, `microgpt_mlp_slice`, and
  `microgpt_block_slice`, and `microgpt_inference_slice` as measured
  direct-CIRCT slices. The next direct-CIRCT step should therefore use that
  source as the semantic guide for a fuller inference-slice lowering, not only
  the earlier hand-shaped math block.
- `reports/scientific_circt_hybrid_protocol.json` now turns the measured
  policy into a compile-time CPU/GPU handoff protocol for the nine measured
  candidates and HLS-friendly source variants. It is `protocol_ready`, records
  `source_variant_ready_count=3`, uses dispatch key
  `candidate,source_variant,nstates,steps`, requires `steps=1`, and falls back
  to CPU below each candidate or promoted-variant threshold. For the
  microGPT-style lane, CPU keeps token-loop control, sampler/observable
  authority, and full KV-cache state authority, while GPU owns only the
  measured arithmetic batch. The tool also emits a single dispatch decision, so
  `microgpt_inference_slice,256,1` selects GPU,
  `microgpt_inference_slice,inference2_hls_friendly,1024,1` promotes the HLS
  variant, `block2_hls_friendly` keeps the baseline GPU/CPU decision, and
  unknown candidates/variants, `64x1`, and step mismatches select CPU with
  fail-closed reasons. This is the bridge from measured usefulness to a future
  runtime ABI; it does not claim runtime ABI authority, PCIe framing cost, full
  microGPT execution, automatic HLS rewriting, or automatic partitioning.
- `reports/scientific_circt_hybrid_dispatch_matrix.json` now expands that
  protocol into the measured `64x1`/`256x1`/`1024x1` matrix. The current matrix
  has 27 candidate/shape decisions with measured speedup evidence attached to
  every row: 16 select GPU and 11 select CPU. `64x1` stays CPU for all
  candidates, `256x1` selects GPU for seven candidates, and `1024x1` selects
  GPU for all nine. This is still compile-time dispatch evidence over measured
  timing reports only, not runtime ABI, PCIe framing, RTLMeter, full microGPT
  execution, or automatic partitioning evidence.
  The report also ranks the 16 GPU-selected rows for runtime integration. The
  current top row is `microgpt_attention_head` at `1024x1` with measured
  end-to-end speedup `6.41385x`; next evidence is broader hybrid runtime
  entrypoint wiring plus amortized integration timing.
  It also expands 12 HLS source-variant decisions: three promoted rows at
  `1024x1`, three `keep_baseline_gpu_or_cpu` rows for `block2_hls_friendly`,
  and six CPU fallbacks below the promoted thresholds. The promoted runtime
  handoff candidate queue ranks `attention_head4_hls_friendly`
  (`13.301119215779238x`), `mlp4_hls_friendly` (`9.922827450510521x`), and
  `inference2_hls_friendly` (`9.799333107174757x`). The next runtime boundary
  to implement is `inference2_hls_friendly`: attention already has the scoped
  runtime evidence lane, and inference is the fuller token/cache slice even
  though MLP is slightly faster.
- `reports/scientific_circt_source_variant_runtime_handoff.json` now executes
  that selected boundary as a scoped runtime handoff measurement. It reuses the
  generated `inference2_hls_friendly` direct-callsite binary and GPU shared
  library, records CPU/GPU output and checksum equality, and measures CPU
  `1.5594159200000002 ms`, GPU end-to-end `0.1436130933333333 ms`, GPU kernel
  `0.04580693379044533 ms`, and bridge wall `0.16406808 ms` per integration
  batch. The observed CPU-to-bridge-wall speedup is
  `9.504688053885925x`, close to the selection-matrix expectation. CPU retains
  token-loop, sampler/output, and KV-cache authority; GPU owns only the
  HLS-friendly batched arithmetic source variant. The next gate is no longer
  choosing the boundary, but factoring this selected source-variant handoff into
  the broader `src/hybrid` or direct Verilator callsite path without claiming
  full microGPT execution, PCIe framing, RTLMeter evidence, automatic HLS
  rewriting, or production runtime readiness.
- `reports/scientific_circt_source_variant_verilator_entrypoint.json` now moves
  that selected boundary into a checked-in `src/hybrid` Verilator-callsite
  bridge. `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp`
  builds against the generated `inference2_hls_friendly` `obj_dir`, calls
  `Vsim::eval()` for the CPU callsite, loads the GPU shared library with
  `dlopen`/`dlsym`, and records output/checksum equality. The measured
  CPU-to-bridge-wall speedup is `9.982658965614949x` with bridge wall
  `0.15218008 ms` per integration batch. The next gate is to generalize this
  bridge pattern into a reusable runtime-boundary dispatcher or generator while
  preserving the existing candidate/source_variant/shape policy checks.
- `reports/scientific_circt_source_variant_runtime_dispatcher.json` now closes
  that generalization gate for the first source variant. The dispatcher reads
  the HLS dispatch matrix, rejects non-selected source variants, verifies the
  registered candidate/source_variant/shape tuple, and invokes the checked-in
  `src_hybrid_verilator_callsite_bridge` for
  `inference2_hls_friendly,1024x1`. The measured CPU-to-bridge-wall speedup is
  `11.09435972584612x` with bridge wall `0.14075793333333333 ms` per
  integration batch, and nested CPU/GPU output/checksum equality still holds.
  The next gate is to broaden the dispatcher registry or generator beyond this
  first inference slice while retaining CPU-fail-closed behavior for
  unsupported or below-threshold source variants.
- The selected long-running validation case now passes:
  `reports/scientific_circt_source_variant_runtime_dispatcher_soak_summary.json`
  records a `3600` second `source_variant_runtime_dispatcher_soak` over the
  same `inference2_hls_friendly,1024x1` boundary. It produced `2574`
  per-iteration dispatcher reports, with all `2574` preserving
  `runtime_dispatch_measured`, nested
  `src_hybrid_verilator_runtime_handoff_measured`, output equality, and control
  checksum equality. Median CPU-to-bridge-wall speedup is
  `10.731542472816859x`, with p10 `8.363504353854227x` and p90
  `11.829942667042333x`. The next gate is no longer one-hour stability for the
  first boundary, but broadening the dispatcher registry or generator while
  keeping unsupported/below-threshold source variants CPU-fail-closed.
- `reports/scientific_circt_source_variant_metadata.json` now records the
  metadata surface needed before broadening bridge generation. It is
  `source_variant_metadata_ready` with four complete rows for
  `attention_head4_hls_friendly`, `mlp4_hls_friendly`,
  `inference2_hls_friendly`, and `block2_hls_friendly`, including GPU symbols,
  input/output layout, artifact paths, Verilator `obj_dir`, entrypoint kind,
  runtime boundary kind, and fallback policy. The extracted input/output bytes
  per state are `80/128`, `16/64`, `8/48`, and `24/32`.
- `reports/scientific_circt_source_variant_runtime_dispatcher_multi.json`
  now broadens dispatch across that metadata-described source-variant set.
  `attention_head4_hls_friendly`, `mlp4_hls_friendly`, and
  `inference2_hls_friendly` dispatch to measured equality-checked GPU
  boundaries, while `block2_hls_friendly` is kept as
  `runtime_dispatch_fallback_baseline` because it does not improve over its
  baseline speedup. The measured CPU-to-bridge-wall speedups in this report are
  `11.31933596913315x`, `9.466548203869824x`, and `11.420283475548267x` for
  the three promoted rows. The next gate is to emit reusable bridge source from
  the metadata surface; direct-callsite reuse is enough for this fixed set, but
  should not be hand-expanded per variant.
- `reports/heavy_rtl_candidate_matrix.json` now sets the heavy RTL broadening
  gate for PULP/NoC-style targets. It contains six rows with a common schema for
  source closure, template availability, build/run/compare evidence,
  CPU/hybrid timing, state-parallel shape, single-state repeated-step shape, and
  policy. The next-stage repeat-median pass promoted three additional rows:
  `pulp_paged_attention_kv_score 64x1`, `tlul_socket_1n 32x1`,
  `tlul_socket_m1 32x1`, and BlackParrot `bsg_wormhole_router` at `32x1`,
  `64x1`, `128x1`, and `256x1`, all with three coverage-output-equivalent
  samples.
  The median CPU-to-hybrid wall speedups are `159.01406799531068x`,
  `75.23948126801153x`, `77.24226694915255x`, and BlackParrot
  `32.76216804527645x`, `158.28447339847992x`, `259.4919886899152x`, and
  `651.817697228145x` across the four measured shapes.
  BlackParrot
  `bsg_wormhole_router` now has a source-backed slice template, coverage
  overlay, coverage manifest, and coverage-output gate. Its packet-pattern
  repeat-median reports pass `coverage_output_equivalence` in every sample
  through `256x1`, so the matrix now has five
  `promote_state_parallel_measurement` rows and one
  `resident_or_shape_sweep_required` row. The next heavy-RTL gate is now
  `config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json`:
  it defines a `256x4` resident packet-pattern timing target. The template
  runner now exposes the dry-run resident command-plan surface with
  `--resident-steps` and explicit `--patch-script`; execution is blocked until
  the BlackParrot packet-pattern patch script is materialized or recorded as
  the named FC-071 blocker.
  `tlul_fifo_sync` remains a favorable but not-yet-general policy row until
  resident or shape-sweep evidence is added.
- `reports/scientific_circt_runtime_handoff_abi.json` now defines the first
  runtime handoff ABI candidate from that top row. It is
  `handoff_abi_ready` for `microgpt_attention_head,1024x1`, with
  array-of-structs layout, 20 input bytes/state, 32 output bytes/state, and
  53,248 logical roundtrip bytes. CPU keeps sequence/KV-cache authority and GPU
  owns only the measured attention-head arithmetic batch. The first adapter
  correctness and warmed fused timing gate is now closed; the next gate is
  broader hybrid runtime entrypoint wiring plus amortized integration timing.
- `reports/scientific_circt_runtime_handoff_adapter.json` now closes that
  correctness gate for `microgpt_attention_head,1024x1`: the generated adapter
  source builds with `nvcc`, runs the 1,024-state batch, observes 20,480 input
  bytes and 32,768 output bytes matching the ABI, and records CPU-vs-GPU output
  equality with `mismatch_count=0`. It now also records a 15-batch
  adapter-local integration loop and builds the shared library used by the
  in-process entrypoint. This is scoped positive runtime-adapter evidence: the
  warmed fused attention-head handoff preserves the measured candidate speedup
  region after adapter-local amortization.
- `reports/scientific_circt_runtime_entrypoint.json` now measures the first
  subprocess-free in-process adapter-library entrypoint. The warmup correctness
  call preserves CPU-vs-GPU output/checksum equality, the timed GPU-only library
  call matches the correctness checksum, and the timed path is CPU-favorable.
  Detailed timing numbers live in `reports/scientific_circt_runtime_entrypoint.json`
  and `docs/status.md`. Next gate: connect the same shared-library style boundary
  to a direct Verilator or broader hybrid runtime entrypoint without broadening
  the speedup claim beyond `microgpt_attention_head,1024x1`.
- `reports/scientific_circt_hls_attention_head4.json` now tests the HLS-style
  source-variant question directly. It materializes four explicit independent
  attention heads per state, lowers them through FIRRTL/SystemVerilog, links a
  Verilator CPU callsite, loads a separate CUDA shared library, and compares the
  output buffer/checksum before timing. The measured result is
  `hls_variant_improved`: bridge-wall speedup improves from the direct-callsite
  baseline `6.126758590128443x` to `13.301119215779238x`. Next scientific work
  should generalize this source/IR-level reshaping criterion rather than spend
  effort on small late LLVM tweaks over already-obscured root-state control.
- `reports/scientific_circt_hls_mlp_block_variants.json` now runs the same
  direct-callsite measurement for `mlp4_hls_friendly`,
  `block2_hls_friendly`, and `inference2_hls_friendly`. All three lower through
  FIRRTL/SystemVerilog, build the Verilator CPU callsite, build a CUDA shared
  library, and match CPU/GPU output plus checksum. `mlp4_hls_friendly` is
  positive (`2.28894x` baseline to `9.922827450510521x` bridge-wall speedup),
  `inference2_hls_friendly` is positive (`3.62419x` to
  `9.799333107174757x`), and `block2_hls_friendly` is a measured
  non-promotion case (`5.56609843788867x` versus `5.75973x`). This turns the
  HLS direction into a policy rule: duplicate/explicit independent units are
  useful only when equality holds and direct-callsite speedup improves.
- `reports/scientific_circt_evidence_audit.json` now includes that dispatch
  matrix in the readiness audit. The current audit records
  `status=evidence_ready`, `candidate_count=9`, `ready_candidate_count=9`, and
  dispatch-matrix measured speedup evidence attached to all 27 candidate/shape
  rows.
- gateGPT should remain the external RTL testbench lane, especially because it
  appears to have already been optimized toward FPGA implementation. For GPU
  discovery, direct microGPT IR/CIRCT is the better first surface because the
  regular arithmetic is still explicit before FPGA-oriented scheduling and
  root-state control obscure it.
- Static suitability should use the eval datapath entry rather than the whole
  Verilator generated support surface; the entry-scoped dense matmul report
  reaches `recommended_path=gpu_state_parallel`, but this is not timing or
  usefulness evidence.
- The candidate plan deliberately keeps branch-heavy sparse/control kernels in
  the CPU-parallel-or-new-mapping bucket until static suitability and measured
  evidence say otherwise.
- This lane must not claim broad RTL, Verilator, RTLMeter, or automatic hybrid
  partitioning speedup beyond the gates that have actually produced evidence.
  At this point, CIRCT lowering, Verilator CPU reference, and scoped CUDA timing
  are proven only for `dense_matmul_tile`, `batched_reduction`,
  `stencil_2d_tile`, and `softmax_exp_pipeline`.

Deferred technical workstreams:

- native Verilator parser boundary
- arbitrary filelist-to-sidecar planner
- filelist dependency inference
- broader automatic GPU allocation policy
- resident execution optimization
- GEM comparison boundary

## Archive Boundary

Historical gate details remain in `records/scaling_gates/`, with `config/scaling_gates` kept as a compatibility link. Generated summaries are reproducible under `reports/`, and build/raw outputs are reproducible under `artifacts/`; both directories may contain local generated evidence. They should not be copied back into `selection.json`, `README.md`, or this roadmap as canonical decisions.
