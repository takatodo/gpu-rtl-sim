# Status

## Project Goal Frame

The external-facing goal is a frontend-neutral GPU sidecar runtime for RTL compiler flows. Verilator is the current compatibility frontend and the direct Verilator GPU UX remains the near-term operator target. The current canonical preview and parser-minimum spelling is `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`; `--use-gpu` is only a long-term shorthand UX concept. CIRCT should be treated as a planned second frontend that can produce equivalent sidecar metadata without making the runtime Verilator-specific.

The sidecar contract is an implementation/runtime boundary, not a JSON-first design. JSON reports and operator plans are useful for debug and review inspection, but canonical execution should flow through importable helpers and structured metadata.

## Current Priority

Goal: `ibex2188_temporal_boundary_discovery_benchmark`

Current priority: `ibex2188_temporal_boundary_discovery_benchmark`

Current next action: `none_ibex2188_boundary_benchmark_fixed_point_reached`

Current status: `COMPLETED` (BFV Fixed Point reached)

Current source artifact: `config/ibex2188_boundary_benchmark.json`

Latest boundary-discovery update: TL-UL #10818 remains the first admitted GPU
boundary benchmark. Ibex #2188 is now the second completed known-bug benchmark.
`config/ibex2188_boundary_benchmark.json` pins the public issue, bad/fixed
revisions, ECC-capable OpenTitan Ibex configuration, checkpoint, independent
oracle, semantic projection, and the four-point
`fault_enable x load_response_delay_cycles` CPU/GPU grid. The pinned profile
records one bad-revision failure, two bad boundary edges, one failure component,
one disappeared failure, zero fixed failures, four selector policies on the GPU
backend, and the same random selector trace on CPU/GPU. The Contract is at its
Fixed Point; no selector speedup, PPO/RL, unknown-bug, or exploit claim is made.

Historical FC-069 update: Stage118 block-source `1760` is clean/raw-clean through candidate `2021`, and extended Stage119 maps dirty `source_id=2` to `compact.cfg_clone.entry_phi.producer_selector.counters3969` with `skipped_count=1536`. Stage121 now suppresses selected diagnostic atomics/marker reads before Stage120 after-observation and applies the selected suppression ids across the candidate set, not only the selected probe source. The source625 global-suppression run is clean after suppressing source611/source613/source615/source618/source620/source624 atomics plus source622 marker-read, classifying that producer-selector frontier as diagnostic perturbation traffic. Stage122 expanded-progress ABI then proved the first post-suppression lifecycle edge is still dirty but has no concrete record318/adjacent write target. Stage123 source1324 is excluded as adjacent diagnostic-counter traffic because suppressing it removes the Stage123 concrete write-window event while the CPU oracle still fails and record318 remains polluted. Stage124 transition evidence remains historical; use the OpenTitan paragraph above for the current priority.

Stage117 update: the previous `1..256` report is not accepted as Stage117 runtime evidence because generated IR lacked Stage117 instrumentation due stale `vlgpugen` pass-tool build order. Pass-tool freshness is now fixed so stale pass tools rebuild before IR generation. With the lightweight saved-address Stage117 probe and a 900s `ptxas` bound, `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_light_block_body_boundary_range_1_2048_ptxas900_runtime.json` reaches runtime: all three entry slices pass `ptxas`, preflight passes, and classification is `token_loop_stage117_phase1_callee0_nested_body_block_body_boundary_same_saved_addr_changed`. The first `COUNT=1024` run was clean, but `COUNT=2048` finds a dirty Stage117 block-body boundary at `source_id=1760` with `split_result=same_saved_addr_changed`, `before_direct_param_record318=0`, `after_direct_param_record318=38666621`, `after_saved_addr_record318=38666621`, `saved_after_polluted=true`, and `semantic_authority=false`. The Stage117 source-id mapping is now parser-backed in `gategpt_testbench_probe.py`: `source_id=1760` maps to `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:834516` metadata row, control-word line `333831`, reconstructed block `vl_batch_gpu.ll:327571` / `%19690`, and first Stage117 probe line `327575` in `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`; `control_word=72058702139492064`. This is a dirty boundary, not final adjacent-window write-source authority.

Stage119/120/121/122/123/124 implementation update: Stage119 skipped-span boundary diagnostics inspect contiguous spans that Stage118 intentionally skips, including compact CFG-clone/probe spans. Stage120 splits one mapped skipped span into instruction-level boundaries using `VLGPUGEN_STAGE120_BLOCK_SOURCE_ID`, `VLGPUGEN_STAGE120_SKIP_SPAN_SOURCE_ID`, `VLGPUGEN_STAGE120_INSTRUCTION_START`, and `VLGPUGEN_STAGE120_INSTRUCTION_COUNT`; `VLGPUGEN_STAGE120_SPAN_EDGE_PROBE=1` probes the aggregate span entry-to-exit edge with `boundary_kind_id=6`, `VLGPUGEN_STAGE120_AGGREGATE_EDGE_PROBE=1` probes prefix aggregate edges with `boundary_kind_id=7`, and `VLGPUGEN_STAGE120_LOW_PERTURBATION_PROBE=1` removes the before/saved-address observation to distinguish diagnostic perturbation from a stable after-only polluted edge. Stage123 adds `VLGPUGEN_STAGE123_CONCRETE_WRITE_WINDOW_BISECTION_PROBE=1` to scan concrete store/atomic/mem-intrinsic candidates after Stage121 diagnostic suppression. Stage124 adds `VLGPUGEN_STAGE124_RECORD318_TRANSITION_PROBE=1` to scan post-suppression record318 transitions after source1324 exclusion. Runtime printing exposes the Stage122 lifecycle probe, Stage123 concrete write-window probe, and Stage124 transition probe; the progress fallback is now 192 counters, with Stage122 slots at `168..175`, Stage123 slots at `176..183`, and Stage124 slots at `184..191`.

Stage121 diagnostic suppression now has two separate opt-in surfaces: `VLGPUGEN_STAGE121_DIAGNOSTIC_ATOMIC_SOURCE_IDS` for known diagnostic atomics and `VLGPUGEN_STAGE121_DIAGNOSTIC_MARKER_READ_SOURCE_IDS` for targeted `materialized_store_order_marker.read` loads. The marker-read path is gated by Stage120 aggregate-edge plus low-perturbation mode and explicit source ids; it is a perturbation-control diagnostic, not runtime skip authority or final pair-offset write-source authority. The suppression is applied before the Stage120 after-read is inserted, which avoids classifying an after-read that was positioned by an instruction later erased by the diagnostic suppression.

Stage118 ptxas-surface follow-up: `rtlmeter_vortex_ptx_entry_slice.py` now avoids treating semicolon-terminated `.func` declarations as function bodies, with a focused contract test. A dry-run regeneration report, `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_reduced_probe.json`, still produces large Stage118 slices (`762827`, `762985`, and `766310` lines), so this parser fix is correct but not sufficient; the next work remains shrinking retained prefix/global/reachable PTX surface or slice freshness before retrying `ptxas`.

Stage118 slice-freshness and split-surface mitigation: `gategpt_entry_sliced_cubin_chain.py` now writes a `*.cubin.slice.json` manifest after a successful `ptxas` run and only reuses an existing CUBIN when the current slice content hash, CUBIN path, GPU target, and ptxas options match that manifest. The entry-sliced specs now keep `vl_eval_batch_gpu` and `vl_patch_eval_pair_cycle_loop_batch_gpu` out of the helper support/feedback CUBINs because those symbols are already available from the token-loop slice. `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_default_split_ptxas1_probe.json` shows the helper slices shrink to `418` and `483` lines and both pass `ptxas` within a 1s bound; the remaining blocker is the token-loop slice at `766310` lines, which still times out. This narrows the ptxas blocker from three huge slices to one huge token-loop slice; it does not identify the final adjacent-window write source.

Stage118 token-loop stub-surface diagnosis: `rtlmeter_vortex_ptx_entry_slice.py --stub-func` can now replace selected reachable `.func` bodies with ret-only diagnostic stubs for ptxas-surface experiments only. `reports/gategpt_tb_core_stage118_token_loop_stub_slice_probe.json` stubs `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` and `__vlgpu_compact_cluster_outline_frame_stub`, reducing the token-loop slice from `766310` to `5066` lines; `ptxas` then produces `artifacts/gategpt_tb_core_ptx_entry_slice_stage118_stub_probe/vl_tb_core_ordering_aware_phase_resident_token_loop_gpu.cubin`. This confirms the remaining ptxas blocker is the reachable high-eval callee/compact-outline body surface, not the token-loop entry body itself. The stub CUBIN is not runtime evidence and must not be used to classify Stage118 instruction range `1281`.

Stage112 source-summary guardrail: `src/tools/gategpt_stage112_store_source_summary.py` joins Stage112 runtime events with the LLVM metadata map without promoting static rows to runtime authority. `reports/gategpt_tb_core_stage112_store_source_static_candidate_summary.json` records static source candidates `1415` and `1533` as `_Z40Vtb_core___024root___nba_sequent__TOP__0` `expected_liveout` zero-clear stores, but the paired runtime report is `clean_no_nested_body_store` with `source_id=0`, so `runtime_authority=false`. These rows are useful suspects for static review, not final adjacent-window write-source authority.

Stage118 opt-in guard surface probe: the earlier `1281,count=64` 120s ptxas-only blocker is now superseded. The same opt-in guard with a 300s `ptxas` bound reaches runtime for `1281..1344` and `1345..1408`; both raw Stage118 events are `clean_no_instruction_boundary`, but their report-level classifier fields remain stale pre-fix Stage112-incomplete results. Classifier-fixed runtime reports now cover `1409..2021` clean, and the later `2049..2112` request is exhausted by metadata.

Stage118/119/120/121/122/123 runtime update: prior Stage118 reports classify `1..2021` clean/raw-clean and `2049..2112` is metadata-exhausted. Extended Stage119 finds the dirty skipped span at `source_id=2`, mapped to `compact.cfg_clone.entry_phi.producer_selector.counters3969`. Stage120 ranges `1..1536 / 1536` inside that span are clean; the aggregate span-edge probe is dirty. Stage121 demonstrates that the producer-selector frontier is a diagnostic perturbation series: known atomic perturbations are suppressible, source622 marker-read suppression makes the targeted boundary clean, and source625 global suppression records no new dirty source after the diagnostic targets are neutralized before Stage120 observation. Stage122 observes the first non-diagnostic lifecycle edge after that suppressed span; it is dirty as `after_only_polluted`, but its target classification is `write_source_kind=none` and `write_source_found=false`. Stage123 source940 is not reproducible as a single-source event, source1324 is reproducible as an adjacent counter candidate, and source1325..1536 is clean for further concrete write-window candidates. Suppressing source1324 removes that adjacent event but does not fix the CPU oracle or record318 pollution, so the next useful work is a Stage124-style transition/non-concrete write-source diagnostic rather than more producer-selector counter suppression.

gateGPT切り出し条件: gateGPTを深掘りする場合は、全体`tb_core`高速化ではなく、計算ブロック型RTLのGPU適用境界を測る。採用条件は、(1)入出力契約が小さく固定できる、(2)状態間独立またはbatch化できる、(3)算術密度が高い、(4)host/device往復がbatchあたり1回以下、(5)CPU oracleとbit/word単位で比較できる、(6)CIRCT/HLSまたはVerilator loweringのどちら由来かを分けて記録できること。除外条件は、逐次token loop、PHI/liveout/valid authorityが主役、stdout/PASS/finish依存、巨大root-state差分、または1シナリオだけの細粒度制御であること。最初の候補は`exp_unit`、matvec/norm/attention系の固定幅サブブロック、比較対象はRTLMeterで得た制御・CPU型RTL境界とする。

現在の実験ゴール: FC-070 / #71 は `microgpt_inference_slice,inference2_hls_friendly,1024x1` の metadata-gated runtime boundary と gateGPT `exp_unit` 比較レーンまで closure-ready。FC-072 / #72 は scoped complete として、`src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` の candidate/source_variant/shape/layout/symbol gate を metadata surface 由来の generated header に切り出した。CPUは token loop/sampler/full KV-cache と未知・非対応形状を持ち、GPUは測定済み batched arithmetic だけを持つ。これは full microGPT、whole `tb_core`、自動partitioning、任意RTL bridge generation、multi-row source emitter、またはJSONだけのruntime ABI authorityを主張しない。

FC-070 / #71 progress: `scientific_circt_source_variant_runtime_dispatcher.py` accepts requested `--shape` and `--steps` gates, passes the selected metadata row into `build_runtime_handoff_report`, and the `src-hybrid-verilator` handoff validates candidate/source_variant/shape/entrypoint/runtime-boundary/layout/symbols before compile/run. The C++ bridge also checks compact metadata argv and returns `failed_metadata_gate` before `dlopen` on mismatch. The metadata-gated execute path now measures `inference2_hls_friendly,1024x1`: `reports/scientific_circt_source_variant_verilator_entrypoint.json` records `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, and `cpu_to_bridge_hybrid_wall_speedup=6.2165001599863245x`; the dispatcher report records `runtime_dispatch_measured` with nested `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, and `cpu_to_bridge_hybrid_wall_speedup=15.461002763357895x`. The gateGPT `exp_unit` comparison lane is refreshed in `reports/gategpt_testbench_probe.json`: `tb_exp` vector, distinct-state, and resident patch paths all pass `103/103` with mismatch `0`; resident repeat median is `1.422 ms` wall / `1.348608 ms` kernel versus CPU process-wall median `14.788301952648908 ms`. This remains narrow `tb_exp` comparison evidence with `speedup_claimed=false` and `usefulness_claimed=false`, not broad gateGPT or arbitrary RTL usefulness. The next implementation issue is FC-072 / #72: generate or otherwise reuse source-variant bridge code from metadata while preserving the same fail-closed gates.

FC-072 / #72 progress: the scoped src-hybrid bridge gate is now derived from the source-variant metadata helper and materialized as `artifacts/scientific_circt/source_variant_verilator_entrypoint/scientific_circt_source_variant_bridge_gate.h` before compiling the Verilator-callsite bridge. `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` consumes generated `SCI_CIRCT_BRIDGE_EXPECTED_*` macros and still returns `failed_metadata_gate` before `dlopen` if argv metadata does not match. The refreshed handoff report records `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, generated header source `source_variant_metadata_row`, and `cpu_to_bridge_hybrid_wall_speedup=16.76826214888755x`; the dispatcher report records `runtime_dispatch_measured` with nested generated-header handoff and `cpu_to_bridge_hybrid_wall_speedup=15.600012129935479x`. This is still scoped to `inference2_hls_friendly,1024x1`, not arbitrary RTL bridge generation.

FC-072 / #72 closure audit: scoped acceptance is met. A broader reusable bridge source emitter for multiple metadata rows remains a possible follow-up only if the project explicitly needs that wider surface.

FC-074 / #74 completion: the broader emitter now exists and is measured. `src/tools/scientific_circt_bridge_spec.py` derives a fail-closed `BridgeSpec` from one metadata row (port names, exact GPU symbol stems, and the per-variant input-fill and inner_repeat-mix formulas all come from the HLS generator modules' public constants, never from JSON alone), and the generated header drives the single reviewed bridge `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp`. All 3 promoted rows (`attention_head4_hls_friendly`, `mlp4_hls_friendly`, `inference2_hls_friendly`) pass `scientific_circt_source_variant_bridge_emit.py --run` with `mismatch_count=0` and output/checksum equality; `block2_hls_friendly` and unknown/unsupported rows fail closed before `dlopen`, and the metadata gate is mandatory on every source-variant handoff path with candidate/source_variant/shape/steps==1 bound across selected boundary, metadata row, and HLS summary. Gate record: `records/scaling_gates/scientific_circt_source_variant_bridge_spec_generated_bridge_gate.json`. Correctness acceptance only; no new timing or speedup claim.

Current FC-069 evidence boundary: Stage109 proves record `318` changes after high-eval `callee_index=0`; Stage112/113/114/116 remain clean and Stage117/119/120 narrow the dirty area to compact CFG-clone producer-selector diagnostics. Source622/source624/source625 global-suppression evidence confirms a diagnostic counter/marker perturbation series, Stage122 shows pollution persists after that suppressed span without a concrete writer, and Stage123 source1324 is now excluded as adjacent CFG-clone liveout-counter traffic because its suppression removes the adjacent event but leaves record318 polluted and the CPU oracle failing. No final write-source or semantic authority claim exists.

The first data-backed manifest is now available for `tb_exp`: `test_exp_z.hex`
and `test_exp_e.hex` each contribute 103 signed 16-bit values, the init-state
targets are `tb_exp__DOT__zs` and `tb_exp__DOT__es`, and the field-offset
manifest covers seven drive/observe fields including `clk`, `zin`, the exp
pipeline state, interpolation result, and the two arrays. The probe now runs that
GPU vector sequence and records a passing bench-specific result: 103/103 cases
match, zero mismatches, `semantic_equivalence_claimed=true`, and `tb_exp`
stdout/finish export remains unclaimed. The observed output is reconstructed
from the generated C++ expression
`pos_r ? 2048 : big_r ? 0 : signed(interp) < 0 ? 0 : signed(interp[15:0])`
because `eo` is not a root field. The LLVM/runtime blocker has narrowed:
`vlgpugen` now keeps top-level phase closures for root images, and the
timing-scheduler-context pass preserves trigger-bearing act phases instead of
deleting their bodies. Remaining gateGPT work is broader output authority:
export stdout/finish as device observables, then measure whether the
bench-specific scenarios can be batched usefully.
`tb_matvec` is now another data-backed bench with a passing GPU DUT-output
contract. The probe maps `generated/test_in.hex` into
`tb_matvec__DOT__u_vmem__DOT__mem[0..23]`, runs one explicit reset/start/clock
sequence, observes `mv_done`, and compares final
`tb_matvec__DOT__u_vmem__DOT__mem[64..87]` against `generated/test_wq.hex`. The
result is 24/24 matched outputs, zero mismatches,
`semantic_equivalence_claimed=true`, and no stdout/finish export claim.
`tb_norm` is now the second data-backed bench with a passing GPU DUT-output
contract. The probe maps `generated/test_norm_in.hex` into
`tb_norm__DOT__u_vmem__DOT__mem[0..23]`, runs one explicit reset/start/clock
sequence, observes `n_done`, and compares final
`tb_norm__DOT__u_vmem__DOT__mem[64..87]` against
`generated/test_norm_out.hex`. The result is 24/24 matched outputs, zero
mismatches, `semantic_equivalence_claimed=true`, and no stdout/finish export
claim.
`tb_core` is now covered by a structured GPU root-state sequence compare. The
probe runs one GPU launch per generated token, carries the state dump through
`--init-state`, feeds sampled `rng_out` into the next `rng_in`, and compares the
greedy token sequence `1 12 1 25 1`, sampled token sequence
`18 15 19 16 8 15 4`, and cycle summary `CYCLES_PER_TOKEN=1157`,
`AVG_CYCLES=1322 over 12 tokens (last=1489)`. The result passes with zero token
or cycle-summary mismatches and `semantic_equivalence_claimed=true`, but it uses
14 GPU launches and 47,656 logical steps, so no speedup/usefulness claim is
made.
`tb_attn` is now the third data-backed bench with a passing GPU DUT-output
contract. The probe maps `generated/test_attn_q.hex` into
`tb_attn__DOT__u_vmem__DOT__mem[0..23]`, `generated/test_attn_k.hex` into
`tb_attn__DOT__u_vmem__DOT__mem[32..415]`, and
`generated/test_attn_v.hex` into `tb_attn__DOT__u_vmem__DOT__mem[448..831]`.
The GPU run observes `a_done` and compares final
`tb_attn__DOT__u_vmem__DOT__mem[864..887]` against
`generated/test_attn_out.hex`. The result is 24/24 matched outputs, zero
mismatches, `semantic_equivalence_claimed=true`, and no stdout/finish export
claim.

Native Verilator sidecar owner-goal tracking is explicit on GitHub. FC-053 /
#46 is the native-path umbrella for the owner endpoint:

```text
verilator --sim-accel sidecar-gpu ... -f filelist --top-module top
make -C obj_dir -f V<top>.mk
obj_dir/V<top>
```

The native Verilator side track remains FC-059 / #59 -> FC-057 / #57 -> FC-058 / #58
-> FC-056 / #56 -> FC-045 / #19. It is not the global current priority while
FC-037 / #2 measures RTLMeter VeeR timing/usefulness. FC-059 still
needs to prove the make-built `obj_dir/V<top>` links and enters a minimal
in-process sidecar shim directly, without `run_hybrid_template.py` runtime
delegation. This is shim-entry smoke only; it is not GPU artifact load, kernel
launch, coverage equivalence, timing, speedup, arbitrary filelist support, or
CPU-as-GPU fallback.

## Three Layers

1. Current execution support: scoped template and benchmark flows reach the sidecar build/run/compare path and use `coverage_output_equivalence` for CPU-vs-hybrid correctness.
2. Preview UX: the near-term Verilator-compatible surface is `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` through repo wrappers, shims, and reviewed non-executing previews where applicable.
3. Long-term goal: a frontend-neutral sidecar contract for Verilator and CIRCT that identifies when LLM-serving-like RTL workloads can be run correctly and efficiently with hybrid CPU/GPU execution.

General arbitrary `-f filelist.f --top-module top` support, broad `--use-gpu` execution, CIRCT execution, automatic allocation, production timing, RTLMeter acceleration, mandatory JSON ABI, and raw full-state equality remain non-claims unless a later gate records and reviews them.

RTLMeter first-seed state: `Example:kind:hello` now has an opt-in CPU/reference
vs sidecar-candidate compare helper that fails closed. The RTLMeter authority
registry carries reviewed stdout/cycles sidecar source-closure authority for the
first seed, and context candidates may adopt it only from
`config/rtlmeter_sidecar_authorities/*.json` when the captured
source/include/filelist closure matches. The runner argv handoff is implemented
as a thin CLI plus importable helper, and the latest real opt-in first-seed run
reaches stdout/cycles comparison with `status=passed`, `comparison=passed`,
`sidecar_execution_invoked=true`, and `execution_authority=true` through the
reviewed runner proxy/marker path. This is historical first-seed proxy/marker
handoff evidence only: `gpu_execution_claimed=false`, `speedup_claimed=false`,
`runtime_abi=false`, CPU-as-GPU fallback remains forbidden, no RTLMeter
acceleration is claimed, and the generated report remains evidence only. The
proxy lane (#49/#51/#53) is frozen under the native Verilator sidecar goal; the
current RTLMeter correctness task is FC-064 / #63 for the VeeR-EL2 direct
sidecar bridge. FC-058 / #58 remains related native-path context after FC-057.

RTLMeter VeeR-EL2 design-CPU state: FC-064 / #63 now recognizes exactly the
tracked `VeeR-EL2:default:hello` `tb_top` filelist and verifies program
identity, observable expression binding, PC/GPR schema, and ICCM/DCCM 4-bank
ECC preload schema, plus the GPU state-image initialization schema, against the
generated root/testbench/C++ markers. The state-image materializer now writes a
reproducible extracted image for the reviewed `hello` program; that program has
no ICCM/DCCM preload sentinels, so derived bank preloads are inactive with zero
nonzero entries. The direct `veer_el2_sidecar_execution_bridge` now consumes
the extracted state image and compares sidecar stdout/cycles against the CPU
reference. The reviewed sidecar executable materializes a syms-state init image,
launches the generated GPU artifact, dumps GPU state, writes sidecar
observables, reconstructs normalized stdout, and aligns `_rtlmeter_cycles.txt`
to RTLMeter's `tb_top.core_clk` count. The bridge passes stdout/cycles
equivalence while still keeping `gpu_execution_claimed=false` and
`speedup_claimed=false`.
A real VeeR GPU artifact build now auto-promotes the root image into a
`Vsim__Syms` state image when `%vlSymsp` coverage requires it, then emits
`vl_batch_gpu.cubin` with `storage_size=433472`. `vl_batch_gpu.meta.json`
reports `state_image_kind=verilator_syms_image`,
`prelaunch_rejection_required=false`, and
`unsafe_syms_gep_covered_by_state_image=true`. The bridge/build report now maps 52 required VeeR
root fields from the generated layout, including PC candidates, GPR 1..31,
ICCM/DCCM banks, reset/clock inputs, reset/nmi vectors, and stdout/cycle observables. The concrete
bridge report also reviews the root-image materializer feasibility: control
scalars and the inactive ICCM/DCCM bank sections are byte-materializable from
the mapped offsets, and the 383-byte `program_staging_lmem` and
`program_staging_imem` sections now map to generated
`VlGpuFlatByteMem<0x80000000U, 65536U>` fields. The bridge materializer review
accepts those program-staging sections as flat GPU byte windows. The optimized
artifact metadata now records `nonflat_assoc_array_detected=false` and
`assoc_array_gpu_lowering_supported=true`; residual `_Rb_tree` markers are from
the timing/coroutine scheduler, not program memory. The stdout/cycles bridge reaches
`sidecar_observables_ready=true`; GPU final state reaches `mcycle=726`,
`minstret=330`, and `finish_marker_observed=true`, matching the architectural
counters printed by CPU stdout. The GPU side now reconstructs normalized stdout
to match the CPU reference, and its `_rtlmeter_cycles.txt` value is aligned to
RTLMeter's `tb_top.core_clk` count, `2229`, while keeping VeeR architectural
`mcycle=726` as a diagnostic. The stdout/cycles comparison passes. This is not
speedup evidence. The current FC-037 scaling timing is now recorded in
`reports/rtlmeter_veer_el2_timing_nstates16.json`: 21 sidecar correctness
samples pass across three seven-sample batches. The GPU sidecar now launches
`nstates=16`, drives clock/reset patches across all sixteen state strides, and validates all final
state observables against state 0 while keeping the stdout trace scoped to
state 0. Serial RTLMeter CPU elapsed is `0.04s`, the comparable sixteen-worker
CPU-parallel `hello` baseline wall is `2.218887s`, sidecar wall median across
all samples is `0.768573s`, GPU kernel total median is `268.161011ms`, bridge
preflight median is `0.000406s`, and
`cpu_parallel_wall_time_outcome=sidecar_faster_than_comparable_cpu_parallel_baseline`.
The batch medians are `0.768573s`, `0.706345s`, and `0.884339s`, with
`timing_stability_outcome=stable_repeated_batch_outcome` for this CPU-parallel
comparison. Per-state wall is now `0.048036s`; compared with the prior
eight-state gate, total wall is `1.258905x` worse but states/s and per-state
wall improve by about `1.589x`. A previous filtered sixteen-state run reached
`0.643080s`, so the latest rerun shows significant wall-time variability rather
than a robust new speedup. This remains evidence that
state-parallel GPU execution is moving in the useful direction, even though
total wall remains much slower than serial CPU. The sidecar now
calls the hybrid C runtime directly instead of launching through `run_vl_hybrid.py`, with
`run_vl_hybrid_launcher_mode_counts={"direct_hybrid_runtime": 21}`. The bridge
now invokes the reviewed Python sidecar in-process, with
`sidecar_executable_invocation_mode_counts={"in_process_veer_el2_sidecar": 21}`. Step
tracing uses a coalesced device-buffered DtoD trace path with
`step_trace_copy_mode_counts={"device_buffered_coalesced_d2d_trace": 21}`,
and a high-phase trace filter
(`step_trace_filter_counts={"start=4,stride=2": 21}`,
`step_trace_filter_rows_median=727.0`, capacity median `1457.0`,
`resident_patch_records_median=69936.0`) that keeps
only mailbox data in the state-0 per-step trace while using rising-edge
reconstruction and final-state counter fallback; init-state
replication uses the device kernel path with
`init_replication_mode_counts={"device_kernel": 21}`, and patch application
uses the device-resident patch schedule with
`patch_drive_scope_counts={"all_states": 21}`. `gpu_cpu_parallel_comparison_valid=true` and
`parallel_state_validation_complete=true`, but the sidecar remains much slower
than serial CPU, so `speedup_claimed=false`.

Patch/eval fusion was tried as the next launch-overhead reduction candidate.
The regenerated VeeR CUBIN contains `vl_patch_eval_batch_gpu`, and
`reports/rtlmeter_veer_el2_timing_nstates16_fusion.json` passes 21/21
correctness samples with `patch_eval_fusion_available_counts={"true": 21}` and
`patch_eval_fusion_launched_median=1457.0`. It is not retained as the default
because its full-gate `sidecar_wall_s_median=0.774456` is slightly worse than
the current non-fusion representative `0.768573`. Fusion remains explicit opt-in
only through `VEER_EL2_SIDECAR_FUSED_PATCH_EVAL=1`; the next overhead target is
trace/output reduction, fewer logical eval steps, or a more substantial
resident-step kernel.

The first fewer-logical-steps diagnostic is now measured as an explicit opt-in
sidecar mode: `VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=posedge_only`.
`reports/rtlmeter_veer_el2_timing_posedge_only_smoke.json` records
`status=failed`, `clock_patch_mode_counts={"experimental_posedge_only_clock_high_fields": 1}`,
`resident_patch_logical_steps_median=730.0`, `resident_patch_records_median=35040.0`,
`gpu_kernel_ms_total_median=18.813951`, and `sidecar_wall_s_median=0.523930`.
Those lower kernel/patch numbers are not useful because correctness failed:
normalized stdout did not match, stdout was not reconstructed, and the VeeR
state stayed at `mcycle=0`, `minstret=0`, `pc=0`. High-only clock patching is
therefore rejected as an acceleration path. The next implementation direction
was a pair-cycle/resident-step mode that preserves ordered low-eval then
high-eval semantics inside one runtime operation. That opt-in path is now
measured with `VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle`.
`reports/rtlmeter_veer_el2_timing_pair_cycle_nstates16.json` records
`status=passed`, `total_sample_count=21`,
`resident_pair_cycle_mode_counts={"low_eval_high_eval": 21}`,
`resident_pair_cycle_launched_median=727.0`, fallback median `0.0`,
`sidecar_wall_s_median=0.692794`, `gpu_kernel_ms_total_median=267.055115`,
`sidecar_run_vl_hybrid_wall_s_median=0.682324`, and
`sidecar_host_overhead_estimate_s_median=0.419148`. This improves the latest
non-fusion representative `0.768573s` by `1.109382x` while preserving
stdout/cycles and all-state final-observable validation, but it still does not
beat serial CPU and does not beat the previous best filtered 16-state
observation `0.643080s`. The confirmatory gate
`reports/rtlmeter_veer_el2_timing_pair_cycle_confirm_nstates16.json` also
passes 21/21 correctness samples and remains faster than non-fusion
(`sidecar_wall_s_median=0.707203`, `1.086778x`), but its batch medians
`0.868907`, `0.673572`, and `0.685787` show enough variability that pair-cycle
should remain opt-in for now.
The true fused pair-cycle follow-up emits `vl_patch_eval_pair_cycle_batch_gpu`
and is selected through `VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1` together with
`resident_pair_cycle`. `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json`
passes 21/21 correctness samples with
`pair_cycle_fusion_available_counts={"true": 21}`,
`pair_cycle_fusion_launched_median=727.0`, fallback median `0.0`,
`sidecar_wall_s_median=0.641226`,
`sidecar_wall_s_batch_medians=[0.620763, 0.649879, 0.641226]`,
`gpu_kernel_ms_total_median=262.026245`, and
`sidecar_run_vl_hybrid_wall_s_median=0.631477`. This is the current best
16-state VeeR sidecar result, improving the latest non-fusion representative by
`1.198599x`, the pair-cycle confirm gate by `1.102892x`, and the previous best
filtered observation by `1.002891x`. It remains about `16.030650x` slower than
serial CPU.
The runtime/reporting path now records actual timed GPU launch count separately
from logical step count. The actual-launch smoke
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_actual_launch_smoke.json`
passes correctness and reports `gpu_kernel_timing_logical_step_count_median=1457.0`,
`gpu_kernel_timed_launch_count_median=733.0`, and
`gpu_kernel_time_ms_per_actual_launch_median=0.373625`; this separates the 727
fused pair-cycle kernels from the six reset/deassert patch/eval launches.
The 32-state scale point has now been measured. CPU-parallel duplicate-`hello`
baseline `reports/rtlmeter_cpu_parallel_hello32_baseline.json` passes with
`parallel_wall_s=4.246739`, `parallel_speedup_vs_serial_sum=6.845413`, and
`parallel_efficiency=0.213919`. The first 32-state sidecar attempt failed closed
because one clock/reset patch row needed 96 patches and the runtime script limit
was 64; `src/hybrid/run_vl_hybrid.c` now allows 256 patches per step and has a
contract test covering 32-state patch script expansion. The repeated 32-state
gate `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json` passes
21/21 correctness samples with `sidecar_wall_s_median=0.950341`,
`sidecar_wall_s_batch_medians=[0.840963, 0.906735, 0.956599]`,
`gpu_kernel_ms_total_median=357.866486`,
`gpu_kernel_timed_launch_count_median=733.0`,
`gpu_kernel_time_ms_per_actual_launch_median=0.488222`,
`resident_patch_records_median=139872.0`, and
`sidecar_vs_cpu_parallel_ratio=4.468648`. Compared with the 16-state fused gate,
total wall is `1.482069x` worse, but per-state wall improves by `1.349465x` and
states/s improves by `1.349465x`; serial CPU remains about `23.758525x` faster.
The state-local resident patch compression follow-up
`reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json`
also passes 21/21 correctness samples and launches the state-local fused
pair-cycle kernel 727 times with no fallback. It reduces stored patch records by
`32x` (`139872` to `4371`), but worsens wall and kernel time:
`sidecar_wall_s_median=2.452390`,
`gpu_kernel_ms_total_median=1675.526123`, and the wall is `2.580537x` slower
than the expanded 32-state fused path. This path is rejected as a performance
direction and remains opt-in diagnostic evidence only.
The next useful direction is a real design-CPU workload rather than more
duplicate `hello`, but the current materializer authority is still hello-only.
A cmark preload probe now fails closed in
`reports/veer_el2_cmark_state_image_materialize_after_fix.json` with
`state_image_materialized=false` because `--rtlmeter-program-hex` does not match
the reviewed accepted preload. This fixes a fail-open path where a mismatched
program could previously detect the mismatch but still write a hello state
image. Non-`hello` GPU timing now requires a reviewed program-preload
authority/materializer before measurement.

## Weakest Point

Current weak point: #2 / FC-037 has measured the first RTLMeter VeeR-EL2
`hello` sidecar timing stability gate, and it is not broadly useful yet:
sixteen-state sidecar wall median is `0.768573s` versus `0.04s` serial CPU elapsed
and `2.218887s` comparable sixteen-worker CPU-parallel wall, with GPU kernel total
median `268.161011ms`. #63 / FC-064 clears the stdout/cycles prerequisite. The
three-batch gate is stable against the CPU-parallel floor in the latest run, and
all-state final observable validation is complete for `nstates=16`, but serial
CPU is still much faster. The current blocker has moved past generic
resident-step overhead and past the `nk==1` loop-eligibility problem:
fixed-flat-memory non-`hello` `dhry` has same-window trace equivalence, bounded
100k no-finish progress, and a phase-aware pair-cycle loop kernel that preserves
the `vl_ico_batch_gpu` + `vl_eval_loop_batch_gpu` sequence. Bounded 10/100/1000
cycle loop runs are byte-identical to resident fallback, and the 1000-cycle
run reduces actual timed launches from `6009` to `10` and GPU kernel total from
`272.929400ms` to `238.399490ms`. The 100000-cycle phase-aware loop summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_progress.json`
also passes bounded progress with one loop kernel, `10` actual timed launches,
`mcycle=99999`, `minstret=95864`, and no finish marker. Its GPU kernel total is
`22404.386719ms`. The bounded projection report
`reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_negative_projection.json`
records `negative_usefulness_decision=true`: projecting that measured window to
CPU RTLMeter cycles `5984259` gives about `1340.75s` GPU-kernel time versus the
measured CPU serial `37.240654s`, about `36.00x` slower by GPU-kernel time
alone. This is a negative usefulness decision for the current bounded GPU path,
not full `dhry` finish/stdout or a positive usefulness/speedup claim.
Patch/eval fusion has been tried and is
correctness-safe but not a timing win on the repeated 16-state gate. The
`posedge_only` clock patch diagnostic reduced kernel work but failed
correctness. The opt-in pair-cycle mode preserves low/high clock semantics and
improves the latest repeated 16-state representative, but it remains slower than
serial CPU and not yet robust against historical wall-time variability. The
true fused pair-cycle kernel now reduces the paired runtime path and sets the
current best 16-state sidecar latency result. The 32-state gate improves
throughput scaling but not total latency, and serial CPU remains much faster.
The state-local patch compression attempt reduced record count but regressed
kernel time and wall time, so the next blocker is not simply compressing patch
records; it is reducing trace/host overhead, avoiding per-thread local patch-loop
regressions, or using more real useful work per state instead of duplicating the
tiny `hello` workload.
Before measuring `cmark` or another longer design-CPU program on the GPU, the
preload identity/materialization gate is now cleared for the reviewed
`cmark`, `cmark_iccm`, and `dhry` program images. The fixed materializer still
refuses arbitrary or mismatched program identity instead of producing a
misleading hello image. This is not timing evidence: full non-`hello` timing is
now blocked by launch-count feasibility, because the current pair-cycle path
would require millions of GPU launches for full RTLMeter design-CPU programs.
The explicit pre-run feasibility reports
`reports/rtlmeter_veer_el2_timing_cmark_launch_feasibility.json` and
`reports/rtlmeter_veer_el2_timing_cmark_iccm_launch_feasibility.json` stop
before bridge execution with estimated actual timed launch counts `5276412` and
`6024133`, respectively, against the current threshold `100000`. The next
useful work is launch-count collapse with resident multi-cycle execution or a
meaningful bounded non-`hello` program milestone. The current bounded smoke reports
`reports/rtlmeter_veer_el2_dhry_bounded_smoke.json`,
`reports/rtlmeter_veer_el2_cmark_bounded_smoke.json`, and
`reports/rtlmeter_veer_el2_cmark_iccm_bounded_smoke.json` show that reviewed
non-`hello` state images reach the GPU resident pair-cycle fused launch path for
a one-cycle, two-state run. They emit sidecar observables and record seven
actual timed GPU launches, but they are not full RTLMeter correctness, timing,
speedup, or usefulness evidence.
The follow-up 500-cycle bounded progress reports
`reports/rtlmeter_veer_el2_dhry_bounded_progress_500.json`,
`reports/rtlmeter_veer_el2_cmark_bounded_progress_500.json`, and
`reports/rtlmeter_veer_el2_cmark_iccm_bounded_progress_500.json` advance the
architectural counters on the GPU sidecar path: all reach `mcycle=499`, with
`minstret=321`, `342`, and `418` respectively. These reports prove short
non-`hello` instruction execution on the GPU path, but they still do not finish
the RTLMeter programs or support a speedup/usefulness claim.
The aggregate bounded-progress gate is now reproducible through
`src/tools/rtlmeter_veer_el2_timing.py --bounded-progress-reports ...` and is
captured in `reports/rtlmeter_veer_el2_non_hello_bounded_progress_summary.json`
with `status=passed`, `timing_measured=false`, and `speedup_claimed=false`.
The first resident multi-cycle launch-collapse surface is now in code, built
into the local tools, and exercised by a bounded final-observable-only
diagnostic: `vl_patch_eval_pair_cycle_loop_batch_gpu`,
`RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP`, and
`VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP` are used in
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_no_trace_500.json`. With
`VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1`, the `dhry` 500-cycle run records
`pair_cycle_loop_fusion.kernel_launches=1`, `cycles=500`, `fallback=0`, and
`gpu_kernel_timed_launch_count=7`; the previous traced 500-cycle bounded
progress shape used `506` actual timed launches. Final observables still match
across two GPU states and reach `mcycle=499`, `minstret=321`. This proves the
loop kernel is actually used and collapses launch count for a bounded run.
The same loop path now reaches a full `hello` program event in
`reports/rtlmeter_veer_el2_hello_pair_cycle_loop_no_trace_full_event.json`:
727 design-CPU cycles collapse to one loop kernel and seven actual timed
launches, `finish_marker_observed=true`, `mcycle=726`, `minstret=330`, and
`cycles=2229`, matching the prior stdout/cycles correctness gate's final
counters. This is still not full RTLMeter stdout correctness, full timing,
speedup, or usefulness evidence by itself because stdout reconstruction is
disabled. The same loop-collapse surface now has a larger non-`hello` bounded
diagnostic:
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_5000_summary.json` passes
for `dhry`, `cmark`, and `cmark_iccm` 5000-cycle no-trace runs. The individual
reports are
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_no_trace_5000.json`,
`reports/rtlmeter_veer_el2_cmark_pair_cycle_loop_no_trace_5000.json`, and
`reports/rtlmeter_veer_el2_cmark_iccm_pair_cycle_loop_no_trace_5000.json`.
All three reach `mcycle=4999` with `minstret=4821`, `4842`, and `4918`, use
`pair_cycle_loop_fusion.kernel_launches=5` for `5000` design-CPU cycles, and
stay at `gpu_kernel_timed_launch_count=21` with fallback `0` and all-state
final-observable validation. This is stronger bounded progress and
launch-count-collapse evidence for reviewed non-`hello` preloads, but it is not
full RTLMeter correctness or speedup evidence because the programs do not
finish and stdout is not reconstructed.
The same 5000-cycle non-`hello` gate now passes with an explicit larger loop
chunk:
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_5000_summary.json`.
Forwarding `VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK=5000` through the
sidecar and allowing that specific `run_vl_hybrid` env above the old 1000 cap
reduces the shape from five loop kernels / 11 actual timed GPU launches to one
loop kernel / seven actual timed GPU launches. `dhry`, `cmark`, and
`cmark_iccm` still reach `mcycle=4999`, retire `4821`, `4842`, and `4918`
instructions, and keep fallback `0`; `cmark` and `cmark_iccm` bounded GPU
kernel time drops from about `2.75s` to about `1.11s`. A longer `dhry` finish
probe,
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk50000_final_stdout_50000.json`,
reaches `mcycle=49999` and `minstret=49821` but still has
`finish_marker_observed=false`. Non-`hello` stdout remains gated because
final-observable stdout reconstruction is reviewed only for the known hello
program SHA.
The program-image completeness blocker is now narrower. The sidecar syms init
materializer writes reviewed DCCM/ICCM ECC bank preload entries into the GPU
init blob. The refreshed summary
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_bank_init_5000_summary.json`
passes with one loop kernel and seven actual timed GPU launches for all three
reviewed non-`hello` programs. It records bank preload word counts of
`dhry=371/0`, `cmark=0/0`, and `cmark_iccm=342/7674` for DCCM/ICCM. The changed
`dhry` and `cmark_iccm` PC/minstret values prove the prior sidecar init was
missing bank-preloaded state. The longer bank-init `dhry` probe
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk200000_dccm_init_final_stdout_200000.json`
reaches `mcycle=199999` and `minstret=191985` in one loop kernel but still does
not observe the RTLMeter finish marker.
The CPU comparison follow-up now records
`reports/rtlmeter_cpu_dhry_serial_baseline.json`: full CPU RTLMeter `dhry`
finishes at `5984259` cycles with `37.240654s` serial wall, meaning the 200000
cycle GPU probe covers only about `3.34%` of the CPU completion window. The
bounded CPU snapshot workflow now exists for the matching `dhry` point:
`src/tools/rtlmeter_veer_el2_cpu_snapshot.py` writes 5k, 50k, and 200k-window
reports for `dhry`. CPU reaches `minstret=4473`, `47757`, and `192038` at
`mcycle=4999`, `49999`, and `199999`; the matching GPU bank-init reports have
`4421`, `47705`, and `191985`. Raw PC fields differ at all three windows. This
is near progress, but not same-cycle equivalence or usefulness; the mismatch is
already visible by `mcycle=4999`, so the next blocker is initial state,
preload, reset/clock, or observation-point alignment, plus the large slowdown
(`1.226972s` CPU run wall versus `43.9320625s` GPU kernel time at
`mcycle=199999`). A follow-up without `+iterations=17500` does not resolve the
gap: CPU retires exactly 65 more instructions than GPU at all three windows.
CPU sampled at `mcycle-65` nearly matches the long-window GPU PC/minstret but
does not explain the short-window PC mismatch, so the next task is not the
Dhrystone iteration count alone. A post-reset cycle-targeted CPU snapshot
follow-up narrows this further: `post_reset_posedges=N+2` aligns CPU `mcycle`
with the GPU windows, but `minstret` stays at `4486`, `47770`, and `192050`
against GPU `4421`, `47705`, and `191985`, and PC still differs.

Historical pre-fix trace-debug context follows; the later fixed flat-memory
compare through 50000 cycles supersedes this mismatch thread for the traced
fields, so do not treat the `gpu_step=895` notes below as the current blocker.
The early CPU snapshots cover post-reset posedges `1`, `2`, `3`, `4`, and `500`:
CPU stays at `mcycle=0`, `minstret=0`, `pc=0` through posedge `3`, reaches
`mcycle=497`, `minstret=360`, `pc=0x400002d1` at posedge `500`. The 500-cycle
snapshot also fixed the CPU snapshot JSON parser for program stdout that
touches the JSON line. A regenerated bank-init GPU comparison now changes the
blocker: CPU/GPU match
through 875 cycles when CPU uses `post_reset_posedges=N+2`; 500, 750, and 875
cycle windows all match `mcycle`, `minstret`, PC, and mailbox byte. At 1000
cycles they diverge (`minstret` CPU/GPU `746/709`, PC `0x40000194/0x40000270`,
obuf `117/32`), and the delta grows by 2000 and 5000 cycles. The trace pass now
adds GPU `mcycle`/`minstret`/`pc` step-trace fields and compares
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_trace_full_1000.json`
against `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_trace_875_1002.json`.
The first exact mismatch is now
`reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_debug_875_1000.json`:
`gpu_step=895` maps to CPU `post_reset_posedges=898`, and counters, registered
PC, decode next-PC, `pc_din`, instruction, and mailbox still match
(`mcycle=895`, `minstret=669`, `pc=0x4000026e`, `pc_d=0x40000270`,
`instr_d=0x0334c4b3`, `obuf=32`). The first differing fields are `decode_d`
and `fetch_stall`: CPU has `decode_d=1` / `fetch_stall=0`, while GPU has
`decode_d=0` / `fetch_stall=1`. The later `pc_d` split at `gpu_step=896`,
registered-PC mismatch at `gpu_step=897`, and `minstret` lag at
`gpu_step=898` are downstream, so the active blocker is why the GPU eval path
keeps `ifu_pmu_fetch_stall` asserted one sampled cycle longer and delays
`dec_i0_decode_d`, not longer finish probing.
A phase-split GPU artifact was then built to test whether splitting Verilator
eval phases could remove that ordering mismatch. The first attempt exposed an
over-broad GPU pass stub: `vl-stub-timing-scheduler-context` had replaced
`_eval_phase__act` with `return false`. `src/passes/VlGpuPasses.cpp` now only
applies that stub when the function directly calls host scheduler/context APIs,
and `src/passes/vlgpugen.cpp` now emits phase kernels with the same syms
self-pointer repair used by `vl_eval_batch_gpu`. It also uses
`vl_nba_loop_batch_gpu` around `_eval_phase__nba` instead of the legacy
unguarded `vl_nba_comb_batch_gpu` / `vl_nba_sequent_batch_gpu` sequence when
the NBA phase helper is reachable. That fixes the all-zero phase trace:
`reports/rtlmeter_veer_el2_dhry_phase_nba_loop_trial_summary.json` records
`launch_sequence=["vl_ico_batch_gpu","vl_eval_loop_batch_gpu"]`, where the
combined eval-loop kernel runs act settle, NBA, then loops back through act
settle when NBA changed state. The 1000-cycle `dhry` trace reaches the same
final observables as the single eval kernel (`mcycle=999`, `minstret=709`,
`pc=0x40000270`, `pc_d=0x40000274`, `obuf=32`). However it still reproduces the
prior `gpu_step=895` mismatch (`fetch_stall=1` / `decode_d=0`), so phase split
ordering is not the fix. The follow-up input trace is
`reports/rtlmeter_veer_el2_dhry_fetch_inputs_compare_875_1000.json`. It shows
that at `gpu_step=895` / CPU post-reset `898`, `decode_valid_gate=1` and
`fetch_fbwrite=0x038` match, while GPU alone has `decode_misc2ff=4`,
`decode_i0_exublock=1`, and `fetch_consume_gate=0`. The next implementation
task is fixing or further isolating the `misc2ff`/exublock and fetch-consume
gate update ordering. The AXI input trace
`reports/rtlmeter_veer_el2_dhry_axi_inputs_compare_875_1000.json` shows the
valid IFU response inputs match through the divergent window; only invalid
`lmem_axi_rdata` filler differs. The next concrete debug target is therefore
inside IFU fetch-buffer consume generation, not external instruction response
timing. The IFU consume/request trace
`reports/rtlmeter_veer_el2_dhry_ifu_consume_compare_875_1000.json` still first
diverges at `gpu_step=895` / CPU post-reset `898`; at `gpu_step=894` the added
IFU fields all match. At the first divergent row, `tb_ifu_axi_arready`,
`ifu_bus_cmd_valid`, `ifu_bus_rd_addr_count`, `ifu_fetch_addr_f`,
`ifu_pmp_addr`, `tb_ifu_axi_rvalid/rid/rdata`, `ifu_ifc_miss_f`,
`ifu_mem_miss_f`, and `ifu_mem_miss_state` still match, but
`ifu_ifc_fetch_req_bf` is `CPU=1` / `GPU=0` and `ifu_ifc_fb_write_ns` is
`CPU=4` / `GPU=8`. The ALN consume trace
`reports/rtlmeter_veer_el2_dhry_aln_consume_compare_875_1000.json` narrows the
same first functional mismatch further: at `gpu_step=895`, `ifu_aln_bundle2`
and `ifu_ifc_fetch_ready` still match, but GPU keeps `ifu_aln_sf0val=3` and
does not assert `ifu_aln_shift_f1_f0` / `ifu_aln_shift_f2_f1`, while CPU has
`ifu_aln_sf0val=0` and both shifts asserted. The next fix target is therefore
ALN sf/shift next-state or state-update ordering feeding IFC fetch-buffer
consume/request, not the IFC table output alone.
The ALN DIN/trigger follow-up
`reports/rtlmeter_veer_el2_dhry_aln_trigger_compare_875_1000.json` confirms
the ALN bundle flops still match at the first functional mismatch
(`bundle1=0`, `bundle2=63`), but GPU next-state outputs are stale:
`ifu_aln_bundle1_din=0` vs CPU `8`, `ifu_aln_bundle2_din=63` vs CPU `15`,
`ifu_aln_sf0val=3` vs CPU `0`, and both shift outputs remain deasserted.
Post-step `root_act_triggered` and `root_nba_triggered` are already clear on
both sides, so any trigger-mask difference must be captured inside phase
execution. The next implementation target is
`Vsim___024root___nba_comb__TOP__18` recompute ordering or a phase-local ALN
dependency recompute after active/sequent updates.
The focused opt-in post-NBA recompute experiment is recorded in
`reports/rtlmeter_veer_el2_dhry_post_nba_recompute_compare_875_1000.json`.
It adds a diagnostic `--veer-aln-post-nba-recompute` path that calls
`TOP__16`, `TOP__17`, and `TOP__18` after a changed NBA phase, then reruns the
bounded `dhry` trace. The first mismatch does not move: `gpu_step=895` / CPU
post-reset `898` still diverges on the same ALN DIN/sf/shift and downstream IFU
consume fields. The default artifact was rebuilt without that diagnostic
recompute. This rules out a simple missing post-NBA `TOP__18` call; the next
target is the immediate input set read by `TOP__18` or the lowered ordering
inside that function.
The follow-up direct-input trace is
`reports/rtlmeter_veer_el2_dhry_top18_inputs_compare_875_1000.json`, with CPU
evidence in `reports/rtlmeter_veer_el2_cpu_dhry_top18_inputs_875_1002.json`
and GPU evidence under
`artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_top18_inputs_trace_1000/_sidecar/`.
It expands the step trace to 82 fields, still under the runtime limit of 96,
and keeps the first functional mismatch at `gpu_step=895` / CPU post-reset
`898`. The new signal that matters is `ifu_pmu_instr_aligned`: GPU has `0`
while CPU has `1`. At that same row, `bundle2`, `aligndata`, `alignfromf1`,
brdata enable, `ic_hit_f`, ECC/error, and freeff inputs still match. Because
`ifu_pmu_instr_aligned` is computed in `TOP__17` from matching `bundle2` and
`dec_i0_decode_d`, the active debug target moves upstream to
`dec_i0_decode_d` / `i0_exublock_d` generation and its lowered update order,
not an ALN-only `TOP__18` recompute.
The exublock-input follow-up is now captured in
`reports/rtlmeter_veer_el2_dhry_exublock_inputs_compare_875_1000.json`, with
CPU evidence in
`reports/rtlmeter_veer_el2_cpu_dhry_exublock_inputs_875_1002.json` and GPU
evidence under
`artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_exublock_inputs_trace_1000/_sidecar/`.
It fills the current runtime trace budget exactly (`96` fields without
`step`) and still keeps the first functional mismatch at `gpu_step=895` / CPU
post-reset `898`. The added `i0_exublock_d` source candidates
(`misc1ff`, halt/presync/LSU idle, nonblock-load, rs enable, hazard, e1/r_d/wb
flops) do not explain the first split; the only visible exublock-side upstream
state mismatch at that row is still `decode_misc2ff=4` on GPU versus `0` on
CPU, together with `decode_i0_exublock=1` versus `0`. The next target is
therefore `misc2ff` DIN/enable/update ordering or a narrower replacement trace
around that flop, not more ALN-only tracing.
Generated-code inspection makes that next trace concrete: the root exposes
`dec__decode__misc2ff__...____Vcellinp__...__dffs__din`, and bit 2 of
`misc2ff` is driven by `i0_div_decode_d` or self-hold through old
`misc2ff[2]` while `exu_div_wren=0` and `dec_div_cancel=0`. The next bounded
trace should replace matched low-value exublock columns with the `misc2ff` gated
DIN, `exu_div_wren`, `dec_div_cancel`, `dec_debug_valid_d`, `exu_flush_final`,
and, if needed for neighboring bits, LSU packet/address trigger sources.
The `misc2ff` DIN trace is recorded in
`reports/rtlmeter_veer_el2_dhry_misc2ff_inputs_compare_875_1000.json`, using
CPU evidence
`reports/rtlmeter_veer_el2_cpu_dhry_misc2ff_inputs_875_1002.json` and GPU
evidence under
`artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_misc2ff_inputs_trace_1000/_sidecar/`.
It keeps the 96-field trace cap and moves the first functional split earlier to
`gpu_step=894` / CPU post-reset `897`: GPU has `decode_misc2ff_din=4` while CPU
has `0`, because CPU asserts `exu_div_wren=1` and GPU keeps it `0`.
The direct divider-input follow-up is
`reports/rtlmeter_veer_el2_dhry_div_inputs_compare_875_1000.json`, with CPU
evidence `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_1002.json` and GPU
evidence under
`artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_div_inputs_trace_1000/_sidecar/`.
That trace shows the earliest functional split yet at `gpu_step=890` / CPU
post-reset `893`: `exu_div_i_misc_ff_din` and `exu_div_shortq` differ before
the later `exu_div_wren` pulse is missed. The next target is divider
`shortq`/`i_misc_ff` update ordering or the arithmetic inputs feeding those
signals, not another decode-side `misc2ff` trace.
The deeper divider trace is now recorded in
`reports/rtlmeter_veer_el2_dhry_div_deep_compare_875_1000.json`, with CPU
evidence `reports/rtlmeter_veer_el2_cpu_dhry_div_deep_875_1002.json` and GPU
evidence under
`artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_div_deep_trace_1000/_sidecar/`.
That split was not a divider state-layout bug. The root cause was the flat
`lmem` model: `$readmemh` wrote program records outside
`VlGpuFlatByteMem<0x80000000U, 65536U>`, and unmapped writes polluted the
default byte to `0x0a`. The later runtime read from the `@10000000` control
address therefore returned `0x0a0a0a0a...` on GPU instead of the Dhrystone
iteration value `1000`, feeding `tb_lmem_axi_rdata`, `exu_div_a_ff`,
`exu_div_dw_shortq_raw`, `exu_div_shortq`, and `exu_div_i_misc_ff_din`.
The flat-memory patch separates unmapped writes from the default read value and
materializes a 16-byte `0x10000000` control window after the 64 KiB program
window. The rebuilt CUBIN uses `syms_storage_size=433536`. The post-fix compare
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_1000.json` maps CPU
rows as `cpu_post_reset_posedges=gpu_step+3` and reports `status=match` across
125 aligned rows and 62 compared fields from GPU steps `875..999`. At the
previous failing row (`gpu_step=890` / CPU post-reset `893`),
`tb_lmem_axi_rdata`, `exu_div_a_ff`, `exu_div_dw_shortq_raw`,
`exu_div_shortq`, `exu_div_i_misc_ff_din`, `exu_div_i_b_ff`, `exu_div_q_ff`,
and `exu_div_r_ff` now match. `pc_din` is excluded from that report because the
prior ad-hoc CPU counterpart was invalid. The same fixed layout now extends to
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_2000.json`, which
reports `status=match` across GPU steps `875..1999`, 1125 aligned rows, and the
same 62 compared fields with zero mismatched field observations. The matching
CPU snapshot report is `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_2002.json`;
it ends at post-reset `2002` with `mcycle=1999`, `minstret=1598`,
`pc=0x40000417`, and mailbox byte `0x0a`. The latest same-window extension is
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_5000.json`, using CPU
evidence `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_5002.json` and GPU
trace `dhry_lmem_control_trace_5000`; it reports `status=match` across GPU
steps `875..4999`, 4125 aligned rows, and 62 compared fields with zero
mismatched field observations. This reaches the prior 5000-cycle bounded
progress milestone with same-window CPU/GPU trace equivalence, but still is not
full `dhry` finish, stdout correctness, timing, speedup, or usefulness evidence.
The latest long-window extension is
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_50000.json`, with CPU
evidence `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_50002.json` and GPU
trace `dhry_lmem_control_trace_50000`; it reports `status=match` across GPU
steps `875..49999`, 49125 aligned rows, and 62 compared fields with zero
mismatched field observations. This makes the earlier 50k raw PC/minstret gap a
pre-fix artifact for the traced fields, but still does not prove program finish
or speed. The automatic summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_trace_equivalence_875_50000.json`
now checks that same-window report with thresholds of 49125 aligned rows and 62
compared fields, returning `status=passed`, `timing_measured=false`,
`speedup_claimed=false`, and `usefulness_claimed=false`.
The first stdout-safe longer-progress gate is still bounded-only. The refreshed
summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_stdout_safe_progress_100000_loopfix.json`
repeats the no-trace fixed-flat-memory run with `mcycle=99999`,
`minstret=95864`, `finish_marker_observed=false`, `step_trace_disabled=true`,
and `final_observable_stdout_requested=true`; it keeps `timing_measured=false`,
`speedup_claimed=false`, and `usefulness_claimed=false`. For non-`hello`,
final-observable stdout reconstruction remains explicitly reviewed-blocked.
The loop-collapse blocker is now cleared for bounded phase-aware diagnostics:
`dhry_lmem_control_loop_notrace_10_phaseaware_loop`,
`dhry_lmem_control_loop_notrace_100_phaseaware_loop`, and
`dhry_lmem_control_loop_notrace_1000_phaseaware_loop` all produce GPU dumps that
match their resident-fallback controls byte-for-byte. The 1000-cycle control
uses `6009` actual timed launches and `272.929400ms` GPU kernel total; the
phase-aware loop uses `10` actual timed launches and `238.399490ms` GPU kernel
total. This is still bounded progress only: non-`hello` stdout remains
reviewed-blocked, full `dhry` finish is not proven, and wrapper wall did not
robustly improve in the 1000-cycle sample. The 100000-cycle phase-aware loop
reaches `mcycle=99999` with no finish marker in `22.889812s` runtime wall and
`22404.386719ms` GPU kernel time. The generated negative projection report now
projects this bounded window to about `36.00x` slower than CPU serial by
GPU-kernel time alone, so the current GPU path is recorded as not useful for
this RTLMeter `dhry` gate. Full non-`hello` finish/stdout remains future
correctness work rather than another loop-eligibility fix.
Separately,
`reports/rtlmeter_cpu_mixed_program_parallel_baseline.json` validates the
design-CPU parallel SIM direction: `dhry`, `cmark`, and `cmark_iccm` run as
separate CPU simulations with matching stdout/cycle observables, reducing wall
from `107.522775s` serial-sum to `37.079953s` with three workers
(`2.899755x`, efficiency `0.966585`). This is a useful CPU baseline path, not a
GPU speedup claim.
The GPU side now has a matching mixed-state bounded projection:
`reports/rtlmeter_veer_el2_mixed_state_dhry_cmark_cmark_iccm_100000_projection.json`
summarizes a 100000-cycle run where `state0=dhry`, `state1=cmark`, and
`state2=cmark_iccm` use distinct syms-state preloads while sharing the same
generated GPU kernels. The run uses `host_uploaded_concatenated_state_images`,
records distinct program SHA/preload materialization per state, and reaches
`status=mixed_state_gpu_negative_projection`: all three states reach
`mcycle=99999`, the GPU kernel window is `22735.765625ms`, and projection to
the CPU mixed baseline max cycle count `6025629` gives about `1369.99s` GPU
kernel time versus `37.079953s` CPU mixed parallel wall, about `36.95x` slower.
This clears the previous same-scenario-only GPU init path limitation and points
away from usefulness for the current mixed GPU path, but it is not full-program
finish, full-program timing, or non-state0 stdout correctness.
The next task order is now: stop treating the current mixed-state GPU path as a
promising optimization, define a materially different GPU implementation only if
it includes a launch-count reduction mechanism plus per-state finish/stdout
observability, keep the CPU mixed parallel baseline as the comparison floor, and
keep FC-037 / GitHub #2 as the task owner.
For FC-037, "materially different" now means all of: resident execution that
advances many design-CPU cycles per device operation, a per-state
finish/stdout/cycle observable contract, explicit superstep entry/exit and
unsupported-side-effect checks, a named GEM-like/data-parallel lowering
candidate when LLVM pass work is proposed, and a usefulness comparison against
the mixed-program CPU-parallel baseline rather than serial CPU alone. Without
that definition, more loop-eligibility work on the current bounded GPU path is
out of scope for a usefulness claim.
The mixed-state GPU/CPU summary now exposes this as a machine-readable next
action: negative projections should return
`recommended_action=stop_current_gpu_path_or_define_materially_different_implementation`
and set `materially_different_definition_gate.required_before_more_gpu_performance_work=true`.
The hello path now adds an explicit final-observable stdout mode,
`VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT=1`, scoped to the reviewed hello
program SHA. `reports/rtlmeter_veer_el2_hello_pair_cycle_loop_final_stdout_bridge.json`
passes the CPU normalized stdout/cycles comparison with
`normalized_stdout_match=true`, `cycle_count_match=true`, and `gpu_cycles=2229`;
the sidecar evidence is captured in
`reports/rtlmeter_veer_el2_hello_pair_cycle_loop_final_stdout_sidecar.json` with
`step_trace_copy_mode=disabled_final_observable_stdout`,
`stdout_stream_reconstructed=true`, and `gpu_kernel_timed_launch_count=7`.
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_smoke.json`
proved the same mode was reachable through the timing runner. The optimized
rebuild follow-up is now
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_nstates16.json`:
21/21 correctness samples pass with
`sidecar_wall_s_median=0.751716`,
`sidecar_wall_s_batch_medians=[0.733165, 0.812418, 0.705006]`,
`gpu_kernel_ms_total_median=259.037048`,
`pair_cycle_loop_fusion.kernel_launches=1`, and
`gpu_kernel_timed_launch_count=7`. It is faster than the comparable
sixteen-worker CPU-parallel `hello` baseline, but remains about `18.8x` slower
than serial CPU and about `1.17x` slower than the current best sixteen-state
fused pair-cycle sidecar result. The next bottleneck is sidecar load/host
overhead or a general device-side trace path for non-`hello` stdout, not a
broad usefulness claim. The new opt-in stage-timing smoke
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_stage_timing_smoke.json`
passes correctness and records machine-readable `run_vl_hybrid` stage timings:
`after_cuCtxCreate=346.810ms`, `after_cuInit=157.850ms`,
`after_final_sync=265.491ms`, `after_dump_state=8.076ms`,
`after_kernel_resolution=7.763ms`, and `after_cuModuleLoad=5.486ms`. This shows
the next overhead target is persistent CUDA runtime/context reuse; final state
dump is not the dominant cost.
The first in-process repeat diagnostic
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_inprocess_repeats_smoke.json`
now reuses one CUDA context/runtime setup with
`VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS=3` and restores VeeR state from a
device snapshot between repeats. Correctness passes, with
`gpu_kernel_time_repeat_count_median=3.0`,
`gpu_kernel_ms_total_median=253.576187`, and
`gpu_kernel_timed_launch_count_median=7.0`. The report is explicitly scoped as
`in_process_hybrid_repeat_diagnostic` and sets
`cpu_parallel_comparison_valid=false`, because multiple GPU repeats inside one
sidecar process cannot be compared as one CPU RTLMeter run. This narrows the
next step: context reuse removes setup from the repeat loop, but the tiny
`hello` kernel loop still costs about the same order as the prior single-run
kernel timing, so usefulness needs a less tiny workload/general non-`hello`
trace or deeper kernel/runtime reduction.

Historical context follows for audit. If an older paragraph below names a different current weak point, prefer the `Current Priority` section and this paragraph.

The commit-split cleanup is complete, and the repaired Verilator native-option
overlay patch has a long reviewed history through parser acceptance, scoped
template-runner sidecar execution, and process-to-launcher metadata. That
historical chain is prerequisite evidence only; it is not the current priority.
FC-037 / #2 remains the related VeeR-EL2 RTLMeter timing/usefulness lane, not
the current implementation priority while FC-069 is active.

Current cleanup policy: keep `config/selection.json` compact (core pointer and operational fields), park bulky historical maps in `config/selection_extensions.json`, keep historical gate records under `records/scaling_gates/` with `config/scaling_gates` as a compatibility link, and keep generated evidence reproducible under `reports/` and `artifacts/` without retaining it as source of truth.

Config minimization state: `records/scaling_gates/config_minimal_surface_completion_audit.json` records that the active `config/` file count is `146`, while `966` tracked gate JSON records live under `records/scaling_gates/`. The compatibility path `config/scaling_gates` remains a symlink so existing CLI/test references continue to resolve. `reports/` and `artifacts/` are generated-output directories; generated evidence may be present locally, but current decisions do not depend on those files as source of truth.

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

## Historical Goal Snapshot

`modern_llm_serving_rtl_hybrid_conditions`

Historical priority:

`define_scientific_circt_source_variant_regression_harness_gate`

Historical source artifact:

`records/scaling_gates/select_scientific_circt_source_variant_regression_harness_after_fc074_gate.json`

## 追跡タスク

- `isolate_entry_dispatch_cfg_clone_memory_reads_before_wiring` で、
  #69 / FC-069 の schedule-owned token-loop launch は `16/16` source probe
  と CPU wall 比較まで到達済み。通常 eval の select-mux transform は
  `normal_eval_rewritten_select_count=2344` / `transform_rewritten_select_count=2688`
  まで測定済みだが、最新の通常 ordering-aware は GPU wall `408.384 ms` /
  GPU kernel `408.310425 ms` / CPU oracle `82.39628802402876 ms` で、
  CPU 比 `4.956339779298132x` slower。guarded bitmap trial は
  `phase_state_partition_bitmap` と partition count `13` で 16/16 states を保ったが
  `354.541 ms` GPU wall / `354.494232 ms` GPU kernel で速度改善にはならない。
  LLVM pass の partition-local shape metadata は
  `select_only_phi_edge_region=8`, `effectful_memory_phi_edge_region=3`,
  `multi_successor_continuation=2` を記録し、select-only PHI-edge outline は
  compact CFG clone path に進む前の到達済み slice。select-only PHI repair は `8` blocks /
  `832` moved selects / `1344` repaired successor-PHI edges まで到達し、
  skip-successor PHI incoming も `8/8` regions / `1344` incoming values で
  定義済みだが、`authority=no_runtime_skip_authority` のため runtime no-op、
  partition-aware skip、speedup/usefulness はまだ未証明。
	  post-repair static safety classification は `8` inspected / `8` candidates /
	  `0` rejected を記録し、partition-match target も `8/8` 見えている。
	  target function 側の predicate context は global ABI で到達済み:
	  `context_slot_count=7`, `concrete_abi_available=true`,
	  `context_load_count=7`, `context_load_metadata_count=7`。control-flow guard lowering は
	  `8/8` 済みで、liveout store/load rewrite も `48/48` rewired まで到達済み。最新 probe では compact CFG clone は `65` blocks / `944` cloned instructions / `65` terminators / `48` PHIs / `48` static liveout stores まで materialize し、unsupported operand/terminator/liveout は `0` まで減った。post-capture compare 追加後は `outline_call_count=3434752`、`liveout_frame_store_count=82434048`、`compare_count=250480`、`mismatch_count=0` となり、reached capture points の single-entry CFG-clone liveout CPU-oracle validation は authority=true になった。最新 runtime impact では non-diagnostic baseline GPU wall `404.986 ms` / kernel `404.90036 ms`、guarded/liveout diagnostic GPU wall `18776.885 ms` / kernel `18796.03125 ms`、同一 CPU oracle `107.71662899060175 ms`。CFG-clone diagnostic ABI なしの baseline でも CPU 比はまだ `3.759735184762744x` slower。Pass は partition-local eval continuation guard の static shape を `8/8/8` regions / `1344` successor-PHI incoming まで emit した。runtime-noop derivation は `832` inspected selects すべてが successor PHI live-out で blocked、`0` elision-safe、authority は `no_runtime_noop_derivation_authority`。successor-PHI continuation user classification は `168` successor PHIs / direct users / direct load users / load-consumed PHIs、`0` direct non-load users、`168` load-result direct users、`0` unsupported load-result users、`1` candidate cluster まで完了したが、authority は `classification_only_no_runtime_skip_or_select_elision_authority` だけ。compact cluster body clone は materialize 済みで、successor-PHI liveout mapping summary も `48/48` mapped、frame-mapping-needed/edge-split-needed/unsupported は `0/0/0` まで分類済みだが、authority は `semantic_cfg_clone_entry_dispatch_wired_no_runtime_noop_authority` だが runtime noop/skip authority はまだ無い。device-observed runtime summary はあるが、832/832 blocked selects が successor PHI live-out に流れ、0 elision-safe のため inactive-path noop/skip authority が無く、CPU-oracle validation は未成立。checked-slot diagnostic は実行でき、`checked_slots=0..23` の `24/48` だけ materialized、各 slot count は `6270`、`mismatch_count=0`。slots `24..47` は未観測なので guarded skip state-equivalence proof complete には進めない。post-lowering component root を増やす root-dispatch-only 修正は試したが、shadow-payload load / select / PHI use の dominance が壊れて `Instruction does not dominate all uses` で `tb_core` IR 検証に失敗したため採用しない。component-local remap 実験は verifier を通したが、static liveout store が `24/48` に落ち、unsupported liveout `24`、unsupported operand `96`、unsupported PHI incoming `240`、runtime checked/actual-valid slots `none` まで後退したため採用しない。entry-frame seed / shadow cross-block undef 実験は verifier と `48/48` static liveout stores / unsupported `0` を保ったが、runtime は `checked_slots=0..23` / `actual_valid_slots=0..23` のままで、static inactive successor-PHI select mapping が `0/832` に後退したため採用しない。PHI-incoming-only edge liveout 実験も verifier/PTX は通したが runtime は同じ `24/48` のままで、static inactive successor-PHI select mapping が `0/832` に後退したため採用しない。external successor-exit edge だけに `storeCfgCloneLiveOut` を入れる実験も verifier/PTX は通したが runtime は同じ `24/48` のままで、static mapping も `0/832` に後退したため採用しない。runtime noop/skip reassessment は `successor_phi_liveout_inactive_value_semantics_unproven` で blocked だった。この古い continuation 次ゲートと後続の refreshed full-phase `stage=0`/`cycle=0` 可視性 gate は supersede 済み。Stage111 で record `318` の変化境界は `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` の nested call まで絞れ、Stage112 split ranges `1..13134` は全 `13,134` nested-body store candidates clean、Stage113 direct deeper-call boundaries も clean、Stage114 ranges `1..256` non-store memory effects も clean だったため、現在の FC-069 次ゲートは `inspect_stage114_remaining_diagnostic_origin_atomics_or_residual_cyclecond_phi_cuda700`。
  stale host-runtime ABI は `src/hybrid` 入力が新しい場合に runtime binary を rebuild することで解消した。
  この negative gap を、stage timing で支配的な
  `before_final_sync=360.61 ms` から kernel body cost と state scale に分解した。
  terminal-mask direct lookup は fallback 付きで実装済みで、16-state の terminal_mask counter は `9294` まで下がった。
  4/8/16/32-state sweep は `68.258934 -> 40.522724125 -> 22.4732570625 -> 12.59289075 ms/state`
  まで改善するが 32-state でも別生成の 32-scenario CPU oracle 比で `2.710562354615603x` slower。opt-in diagnostic region counter では
  16-state の `cycle_body=4884742382` の内訳として `high_eval=3629021127` が支配的で、32-state でも `cycle_body=4884742382` / `high_eval=3629021127`。eval direct-call では
  `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` が `11593` counted instructions と最大、かつ `poor_for_narrow_peephole_pass` なので、
  次は eval-callee hot path 解析または state-scale 拡張で判断する。IR 分類では terminal-mask direct lookup は実装済みで、
  phase-control record の phase/state partition、patch-record division/base hoist
  が残りの LLVM/lowering 候補、multi-phase resident sequence は構造候補として残し、
  speedup/usefulness claim は引き続き false のままにする。
- `docs/migration_notes.md` の「シンプル検証からの乖離」節を、前提変更時に見直す。
- 新規ゲート完了時は `config/selection_extensions.json` の `completed_goal_evidence` / `records/scaling_gates/public_benchmark_pack_goal_completion_audit.json` の整合を取る。
- ゲート JSON に残る履歴表記の例: `next_task: select_next_measurement_after_paged_attention_kv_cache_scale_up_next_shapes_public_pack_refresh`（正の源泉は常に `config/selection.json` の `current_priority` を優先）。マージ後の全体像が必要なら `src/tools/selection_state.py` の `load_selection` を参照。

## Current State

Fresh local LLM-serving-like RTL rerun state: on 2026-05-13 JST, `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x1` and `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 1x1` both completed non-dry-run through Verilator build, generic host-probe build, GPU cubin build, hybrid run, and CPU-vs-hybrid compare. The selected policy is `coverage_output_equivalence`; both refreshed compare reports pass with mismatch count `0` over `29` words / `116` bytes. Raw full-state equality remains false in both reports due to Verilator-internal-only mismatch bytes, so this is a scoped output-equivalence rerun, not a raw state-equality claim or production LLM-serving throughput claim.

Commit guard state: `.githooks/pre-commit` is the active local hook path via `git config core.hooksPath .githooks`. It runs the staged-only guard `src/tools/check_staged_large_files.py`, rejects staged files larger than `5 MiB`, rejects commits with more than `100` staged non-submodule file changes including deletions and type changes, rejects guarded script deltas above `250` added lines per guarded script, rejects guarded scripts above `300` total lines per guarded script, rejects more than `3` new guarded scripts per commit, rejects non-shrinking contract tests above `1200` total lines or `250` added lines, rejects `artifacts/` generated output in normal source commits, uses staged blob SHA batch-size checks for files that still have staged content, skips submodule gitlinks, and reports `GPU_TOGGLE_MAX_COMMIT_FILE_BYTES` / `GPU_TOGGLE_MAX_COMMIT_FILE_COUNT` / `GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES` / `GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES` / `GPU_TOGGLE_MAX_NEW_SCRIPT_FILES` / `GPU_TOGGLE_MAX_CONTRACT_TEST_ADDED_LINES` / `GPU_TOGGLE_MAX_CONTRACT_TEST_TOTAL_LINES` as reviewed local override knobs. The broader `tests.contract.test_tracked_tool_dependency_boundary` active-surface contract stays under `make surface` and `make check`, because it intentionally reads the current active tree and is too broad for partial commit-split index states. This supports the current active-surface policy by keeping generated or bulky data out of normal source commits, keeping scripts and contract tests from accreting one-off workflows, and keeping commits review-sized without making unrelated unstaged split groups block the staged guard.

TL-UL template schema and later launch-overhead follow-up gates are retained as tracked gate records when they are canonical. Local candidate records under `records/scaling_gates/` are not current source of truth unless they are tracked and selected by `config/selection.json` or the public-pack manifest. Raw strict final-state equality remains diagnostic only; the scoped correctness policy is `coverage_output_equivalence`.

Native parser-to-sidecar handoff boundary state: `config/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` defines a non-executing adapter boundary from native Verilator parser values to the existing sidecar plan surface. Parser-owned fields are limited to the accelerator selector, positive state/step counts, normalized shape, ordinary Verilator args, and preserved build inputs; sidecar-owned source closure, coverage target, state paths, report paths, host-probe metadata, and compare policy are referenced but not populated by the parser. This adds no adapter implementation, runtime/ABI integration, RTL simulation, timing, arbitrary RTL/filelist support, automatic allocation, upstream regression success, or upstream landing claim.

Native parser-to-sidecar handoff boundary review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` accepts that boundary narrowly and selects a non-executing fixture implementation next. The review clarifies that `coverage_output_equivalence` is only a later sidecar correctness-policy reference, not parser-populated compare evidence. The fixture must not produce resolved `state_files`, generated reports, compare labels, coverage targets, manifest refs, host-probe metadata, runtime handoff, timing, source closure inference, or automatic allocation.

Native parser-to-sidecar handoff fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_handoff_fixture_gate.json` adds `src/tools/verilator_native_option_parser_sidecar_handoff.py`. The helper maps parser-stub values into a non-executing adapter payload, preserves ordinary Verilator args and classified build inputs without expansion, emits `correctness_policy_ref` only as a later sidecar policy reference, rejects unexpected correctness-policy refs, and rejects parser values that already contain resolved sidecar outputs. It does not call the sidecar stage planner or `sidecar_handoff_contract`, does not run compare or RTL simulation, and does not infer source closure, state paths, report paths, coverage targets, host-probe metadata, runtime handoff, timing, or automatic allocation.

Native parser-to-sidecar handoff fixture review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json` accepts only that non-executing fixture implementation. The next boundary is `define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate`, which must define how an accepted adapter payload can resolve into the existing sidecar stage-plan surface while keeping sidecar-owned source closure, coverage-output targets, host-probe metadata, state/report paths, compare labels, execution, timing, and automatic allocation out of the parser layer.

Native parser-to-sidecar plan-resolution boundary state: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` defines that the adapter payload alone is insufficient to resolve a sidecar plan. A plan-resolution layer must receive explicit sidecar context such as target, mode, template or registry entry, and source gate/manifest reference before calling or mirroring `sidecar_stage_plan`; parser-owned inputs stay limited to schedule values and preserved Verilator build inputs. Source closure, filelist expansion, coverage-output target selection, host-probe metadata, state/report paths, compare labels, final compare policy, `sidecar_handoff_contract`, execution, timing, and automatic allocation remain sidecar-owned.

Native parser-to-sidecar plan-resolution boundary review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` accepts only the explicit-context, non-executing definition and selects `implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate`. The next fixture must reject payload-only resolution and may call or mirror `sidecar_stage_plan` only after explicit sidecar context exists; it must not execute RTL, materialize state files from parser-only input, compare outputs, measure timing, change runtime/ABI, or claim arbitrary RTL/filelist support.

Native parser-to-sidecar plan-resolution fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json` adds `src/tools/verilator_native_option_parser_sidecar_plan_resolution.py`. The helper accepts reviewed adapter payload plus explicit target/mode/template or registry-entry context and a source gate/manifest reference, validates shape and template consistency, then calls existing `sidecar_stage_plan` as a non-executing plan authority. Parser `source_files`, `filelists`, and ordinary Verilator args remain preserved inputs only; the fixture does not infer source closure, synthesize commands, produce `sidecar_handoff_contract`, execute RTL, compare outputs, measure timing, change runtime/ABI, or claim arbitrary RTL/filelist support or automatic allocation. The next gate is reviewing this implementation boundary.

Native parser-to-sidecar plan-resolution fixture review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate.json` accepts only the explicit-context, non-executing template-plan fixture. The accepted weakness is that the helper's outer `status: planned` can obscure `sidecar_stage_plan` not-ready statuses for resident or unsupported modes. The next gate is defining status/readiness hardening before producing `sidecar_handoff_contract`, synthesizing commands, executing RTL, measuring timing, changing runtime/ABI, or claiming arbitrary RTL/filelist support or automatic allocation.

Native parser-to-sidecar plan-resolution status hardening definition state: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json` defines the future outer status as a direct Verilator option readiness classification: `ready_for_verilator_option_shim`, `not_ready_for_verilator_option_shim`, or `unsupported_for_stage_plan`. It also requires preserving nested `stage_plan_status` so resident workflows stay visible as `planned_not_ready_for_verilator_option_shim`. This is definition-only; it adds no sidecar handoff contract, command synthesis, execution, timing, runtime/ABI, arbitrary RTL/filelist support, or automatic allocation.

Native parser-to-sidecar plan-resolution status hardening review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json` accepts the readiness-classified outer status contract and selects in-place helper hardening next. The next implementation must derive outer status from `sidecar_stage_plan` status plus nested readiness, add `plan_resolution_readiness`, preserve `stage_plan_status`, and keep sidecar handoff contract, command synthesis, execution, timing, runtime/ABI, arbitrary RTL/filelist support, and automatic allocation absent.

Native parser-to-sidecar plan-resolution status hardening implementation state: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json` records the in-place helper change in `src/tools/verilator_native_option_parser_sidecar_plan_resolution.py`. The helper now derives outer status from `sidecar_stage_plan` plus nested readiness, adds `plan_resolution_readiness`, and covers ready template, resident not-ready, persistent-resident not-ready, and unsupported modes in focused contract tests. This remains non-executing fixture evidence only, not sidecar handoff contract, command synthesis, execution, timing, runtime/ABI, arbitrary RTL/filelist support, or automatic allocation.

Native parser-to-sidecar plan-resolution status hardening implementation review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate.json` accepts only the readiness-classified non-executing helper. The accepted weak point is that `ready_for_verilator_option_shim` can still be over-read as execution or correctness evidence, so the next boundary must define handoff-contract inputs and rejections without executing sidecar handoff, synthesizing commands, measuring timing, changing runtime/ABI, expanding arbitrary filelists, or claiming automatic allocation.

Native parser-to-sidecar plan-resolution handoff-contract boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json` defines the ready-only metadata boundary after plan resolution. It requires `status: ready_for_verilator_option_shim`, `plan_resolution_readiness.ready_for_direct_verilator_option: true`, `stage_plan.status: planned`, matching parser/stage shape, and `coverage_output_equivalence` before a future helper may build `sidecar_handoff_contract` metadata. Not-ready and unsupported outputs must not produce handoff metadata. This is definition-only; it adds no command synthesis, operator plan, runtime handoff execution, RTL execution, timing, runtime/ABI change, arbitrary filelist expansion, or automatic allocation.

Native parser-to-sidecar plan-resolution handoff-contract boundary review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json` accepts that ready-only metadata boundary and selects `implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate`. The next helper must validate the reviewed plan-resolution surface, outer ready status, nested readiness, planned stage status, and parser/stage shape match before calling `sidecar_handoff_contract(stage_plan)`. Not-ready and unsupported outputs must fail closed before metadata construction and preserve readiness reasons. This still adds no public CLI, command synthesis, operator plan, runtime handoff execution, RTL execution, compare execution, timing, runtime/ABI change, arbitrary filelist expansion, or automatic allocation.

Native parser-to-sidecar plan-resolution handoff-contract fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate.json` records the thin wrapper `resolve_native_parser_plan_resolution_to_sidecar_handoff_contract` in `src/tools/verilator_native_option_parser_sidecar_plan_resolution.py` and the support module `src/tools/verilator_native_option_parser_sidecar_handoff_contract.py`. Ready plan-resolution outputs are validated before calling `sidecar_handoff_contract(stage_plan)` and return metadata only. Not-ready and unsupported outputs return structured closed results without metadata construction. Malformed ready inputs, including ready inputs that already claim `efficiency_estimate_invoked`, raise before the metadata authority can be called. This still adds no public CLI, command synthesis, operator plan, runtime handoff execution, RTL execution, compare execution, timing, runtime/ABI change, arbitrary filelist expansion, or automatic allocation.

Native parser-to-sidecar plan-resolution handoff-contract fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate.json` accepts only the metadata-only, ready-only helper after the explicit `efficiency_estimate_invoked` guard was added. The accepted implementation keeps the public wrapper thin, leaves validation in `src/tools/verilator_native_option_parser_sidecar_handoff_contract.py`, fail-closes not-ready/unsupported outputs before metadata construction, and treats `coverage_output_equivalence` as a later sidecar policy reference rather than native-parser compare evidence. The next gate is defining the handoff-contract-to-operator-plan boundary without adding native Verilator parser support, sidecar runtime handoff validation, command execution, operator-plan execution, RTL simulation, compare execution, timing, runtime/ABI change, arbitrary filelist expansion, or automatic allocation.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json` defines only the next non-executing metadata boundary. Ready handoff-contract metadata may later feed command argv, estimate-command, efficiency-estimate, and operator-plan metadata only after accepted input preconditions pass; closed, unsupported, malformed, or prepopulated inputs must reject before command synthesis or operator-plan metadata construction. This definition keeps efficiency estimate as planning metadata only and adds no command execution, operator-plan execution, RTL simulation, compare execution, timing evidence, runtime/ABI change, source closure inference, arbitrary filelist expansion, or automatic allocation.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan boundary review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json` accepts only the metadata boundary and selects an importable fixture implementation next. The review permits `command_argv`, `estimate_command`, `efficiency_estimate`, and `operator_plan` metadata only as non-executing planning output; `efficiency_estimate` remains non-timing metadata, and closed, unsupported, malformed, or prepopulated inputs must reject before authority calls. This review adds no public CLI, command execution, operator-plan execution, RTL simulation, compare execution, measurement, timing evidence, runtime/ABI change, source closure inference, arbitrary filelist expansion, or automatic allocation.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_implementation_gate.json` accepts the metadata-only helper for accepted ready handoff-contract fixture metadata. The review records that tested malformed/prepopulated cases fail before authority calls, but also records two hardening gaps: bool values can currently satisfy positive-int checks, and `efficiency_estimate` may include existing-report-derived values that are not new timing evidence from this gate. This still adds no public CLI, command execution, operator-plan execution, RTL simulation, compare execution, measured timing, runtime/ABI change, source closure inference, arbitrary filelist expansion, or automatic allocation. The next gate is defining that hardening.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening definition state: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json` defines the minimum hardening boundary before implementation: reject bool values in handoff-contract, stage-plan, and parser-schedule integer fields before command or operator-plan authorities; scope malformed Mapping handling to accepted ready handoff-contract metadata without claiming complete adversarial schema validation; and keep `efficiency_estimate` as non-executing planning metadata even when existing reports contribute values.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json` accepts that definition and selects in-place helper implementation next. The review tightens the weakest part: `stage_plan.phases` and `stage_plan.limit` bool values must reject before command, estimate, efficiency, or operator-plan authorities, not merely before `efficiency_estimate`.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening implementation state: `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json` records the in-place helper hardening. `_positive_int` now rejects bool, `stage_plan.phases` and optional `stage_plan.limit` are validated before all four operator-plan authorities, `hybrid_sidecar_run` details are strict positive integers before command synthesis, and parser schedule counts are strict positive integers before equality comparison. Counting-stub tests cover all eight bool field paths and confirm command, estimate, efficiency, and operator-plan authorities are not called on rejection. This still adds no public CLI, command execution, operator-plan execution, RTL simulation, compare execution, measured timing, runtime/ABI change, source-closure inference, arbitrary filelist expansion, automatic allocation, or complete adversarial Mapping validation.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan fixture hardening implementation review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_implementation_gate.json` accepts the strict metadata-only hardening and allows only a definition-only execution-boundary gate next. The review explicitly keeps command execution, operator-plan execution, RTL simulation, compare execution, coverage-output equivalence for a native-parser flow, measured timing, speedup, runtime/ABI change, arbitrary filelist support, automatic allocation, and complete adversarial Mapping validation out of scope.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan execution boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate.json` defines the first future execution boundary after accepted metadata hardening. A later run gate must validate ready operator-plan metadata, recover or regenerate a reviewed sidecar stage plan, and only then execute reviewed sidecar build/run/compare stages. Direct Verilator command metadata remains preview/build input rather than sidecar runtime evidence. This definition still adds no public CLI, command execution, operator-plan execution, RTL simulation, compare execution, measured timing, runtime/ABI change, arbitrary filelist support, automatic allocation, or native Verilator support claim.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan execution boundary review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate.json` accepts that definition and permits only `run_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_gate` next. The run must validate ready operator-plan metadata and reviewed or regenerated sidecar stage order before executing anything, keep generated evidence under `reports/` and `artifacts/`, and avoid native Verilator support, arbitrary filelist, automatic allocation, timing, speedup, and runtime/ABI claims.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan sidecar execution run state: `config/scaling_gates/run_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_gate.json` records `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1` completing the reviewed `verilator_build`, `host_probe_build`, `cpu_init_state`, `cpu_reference_output`, `gpu_artifact_build`, `hybrid_sidecar_run`, and `coverage_output_compare` stages. `reports/pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json` passes `coverage_output_equivalence` with mismatch count `0` across `64` state pairs. This is scoped sidecar execution evidence only; it is not native Verilator option support, timing or speedup evidence, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser-to-sidecar plan-resolution handoff-contract-to-operator-plan sidecar execution run review state: `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_run_gate.json` accepts only that scoped `pulp_ita_mha 64x1` sidecar execution result and advances to `define_verilator_native_option_parser_direct_command_path_boundary_gate`. The accepted weak point is that the source command is still `run_hybrid_template.py`, not direct native Verilator option execution; the next boundary must define how a future native command path enters reviewed sidecar planning without claiming timing, arbitrary filelists, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_boundary_gate.json` defines the minimum expanded Verilator-facing spelling, `--sim-accel sidecar-gpu` plus positive `--sim-accel-states` and `--sim-accel-steps`, and requires native parser values to materialize or reference a structured sidecar stage plan before any execution authority. Parser-owned preserved source files and filelists remain build inputs only; source closure, host-probe metadata, state/report paths, compare labels, coverage-output target selection, stage order, and generated evidence policy remain sidecar-owned. The definition advances to review and adds no native option support, direct command execution, timing, arbitrary filelists, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_boundary_gate.json` accepts only that definition-only boundary and advances to `define_verilator_native_option_parser_direct_command_path_fixture_gate`. The accepted weak point is that the direct-looking Verilator spelling can be over-read as implemented native support, so the next gate must define the non-executing fixture contract before implementation. This review adds no native option support, direct command execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path fixture definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_fixture_gate.json` defines the future importable helper contract without implementing it. The contract pins an accepted expanded `sidecar-gpu 64x1` case, required input and output payload fields, explicit sidecar context, a reference-only `sidecar_plan_boundary`, reviewed stage order, and fail-closed cases for missing shape halves, non-positive counts, mixed or compact-only shape spelling, missing sidecar context, and parser-prepopulated sidecar-owned fields. The definition advances to review and adds no native option support, helper implementation, direct command execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path fixture review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_gate.json` accepts that non-executing fixture contract and advances to `implement_verilator_native_option_parser_direct_command_path_fixture_gate`. The accepted weak point is that a direct-looking argv plus `sidecar_plan_boundary` can be over-read as implemented native support or execution authority, so the implementation must preserve ordinary Verilator inputs, require explicit sidecar context, return reference-only sidecar metadata, and keep Verilator execution, sidecar stages, compare, timing, allocation, runtime/ABI changes, arbitrary filelists, and raw full-state equality out of scope.

Native parser direct command-path fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_gate.json` records `src/tools/verilator_native_option_parser_direct_command_path_fixture.py`, an importable non-executing helper. It accepts the expanded `sidecar-gpu 64x1` case, wraps parser-stub errors into the direct fixture rejection layer, distinguishes mixed compact/expanded spelling from compact-only spelling, requires explicit sidecar context, rejects parser payloads that prepopulate sidecar-owned fields, and returns only a reference-style `sidecar_plan_boundary`. This adds no native Verilator option support, direct command execution, sidecar stage materialization, compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality claim.

Native parser direct command-path fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_implementation_gate.json` accepts only the non-executing reference-boundary helper. The review records a required follow-up: the parser-payload entrypoint must strictly reject missing reviewed identity/build-input fields before sidecar-plan materialization. The selected next gate is `define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate`; this review adds no native Verilator option support, sidecar stage materialization, direct command execution, compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path fixture payload validation hardening definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json` defines the exact parser-stub payload keyset and required values before `direct_command_parser_payload_to_sidecar_plan_fixture` may return reference-only sidecar boundary metadata. It requires `schema_version`, `surface`, `accelerator_mode`, `correctness_policy`, strict state/step counts, normalized shape, `mdir`, `top_module`, list-of-string preserved build inputs, parser-stub provenance fields, and explicit sidecar context. The selected next gate is `review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate`; this definition adds no helper change, native Verilator option support, sidecar stage materialization, direct command execution, compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path fixture payload validation hardening review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json` accepts exact parser-stub handoff keyset validation as the minimum implementation boundary. The review keeps the weak point explicit: the rule is rigid by design, and the helper is already at the 250-line guard, so implementation must split reusable validation or shrink the helper cleanly. The selected next gate is `implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate`; this review adds no helper change, native Verilator option support, sidecar stage materialization, direct command execution, compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path fixture payload validation hardening implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json` records `src/tools/verilator_native_option_parser_direct_command_payload_validation.py` and the direct fixture wiring. Hand-built parser payloads now must match parser-stub `HANDOFF_FIELDS`, required values, strict positive counts, normalized shape, non-empty `mdir`/`top_module`, list-of-string preserved build inputs, and parser-stub provenance fields before boundary metadata is returned. The selected next gate is `review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_implementation_gate`; this implementation adds no public CLI, native Verilator option support, sidecar stage materialization, direct command execution, compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path fixture payload validation hardening implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_implementation_gate.json` accepts only the stricter non-executing validation helper. The review records the remaining gap: the direct fixture still returns reference-only `sidecar_plan_boundary` metadata, so the next gate is `define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate`. This review adds no public CLI, native Verilator option support, direct command execution, sidecar stage execution, compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path sidecar stage-plan materialization boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate.json` defines that a validated direct fixture result must bridge through the reviewed adapter payload and existing plan-resolution helper before any `sidecar_stage_plan` materialization or reference. It pins explicit sidecar context normalization and ready/not-ready/unsupported status mapping while keeping execution, compare, timing, arbitrary filelists, automatic allocation, runtime/ABI changes, and native Verilator support claims out of scope.

Native parser direct command-path sidecar stage-plan materialization boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate.json` accepts only the non-executing adapter-and-plan-resolution route. The review keeps the weakest point explicit: the direct fixture result itself is not stage-plan authority, and `template_or_target_registry_entry` must be normalized into explicit plan-resolution context before any sidecar plan metadata is exposed. The selected next gate is `implement_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_gate`; this review adds no public CLI, native Verilator option support, direct command execution, sidecar stage execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path sidecar stage-plan materialization fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_gate.json` adds `src/tools/verilator_native_option_parser_direct_stage_plan_materialization.py` as a non-executing bridge. The helper requires the reviewed direct fixture surface/status/keyset, revalidates `parser_payload`, cross-checks duplicated direct top-level schedule/build-input fields, normalizes `template_or_target_registry_entry`, and then routes through `build_native_parser_sidecar_handoff` plus `resolve_native_parser_adapter_payload_to_sidecar_plan`. The selected next gate is `review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_implementation_gate`; this implementation adds no public CLI, native Verilator option support, direct command execution, sidecar stage execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path sidecar stage-plan materialization fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_implementation_gate.json` accepts the bridge as metadata-only stage-plan materialization. The review accepts parser payload revalidation, direct field cross-checks, explicit sidecar context normalization, and the route through reviewed adapter payload plus existing plan resolution, while keeping execution, compare, timing, arbitrary filelists, automatic allocation, runtime/ABI change, and raw full-state equality out of scope. The selected next gate is `define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate`.

Native parser direct command-path sidecar stage-plan execution boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate.json` defines the future run boundary from reviewed direct materialization metadata to scoped sidecar build/run/compare stages. It requires ready materialization metadata, the reviewed seven-stage order, generated evidence under `reports/` and `artifacts/`, and future `coverage_output_equivalence` only after a reviewed run executes compare. The selected next gate is `review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate`; this definition adds no public CLI, native Verilator option support, direct command execution, sidecar stage execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path sidecar stage-plan execution boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate.json` accepts only ready materialized stage-plan metadata plus the reviewed seven-stage sidecar order as future run inputs. The review explicitly keeps `shape` in `stage_plan` while requiring `state_count` and `step_count` to be validated through `parser_schedule_constraints`. It advances to `run_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_gate`; this review adds no public CLI, native Verilator option support, direct command execution, sidecar stage execution by this gate, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path sidecar stage-plan execution run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_gate.json` records `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1` after validating the ready materialization metadata, parser schedule constraints, and reviewed seven-stage order. The generated compare report passes `coverage_output_equivalence` with mismatch count `0` across `64` state pairs and `1856` compared words. Raw full-state match remains false, so the selected next gate is `review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_run_gate` before any native option, direct command execution, timing, arbitrary filelist, automatic allocation, runtime/ABI, or raw-state claim.

Native parser direct command-path sidecar stage-plan execution run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_run_gate.json` accepts only that scoped `pulp_ita_mha 64x1` sidecar build/run/compare result. The review records the weakest point explicitly: the command is still the existing template runner after direct materialization metadata validation, not a real native Verilator option invocation. The selected next gate is `define_verilator_native_option_parser_direct_command_path_native_invocation_boundary_gate`, which must define what counts as native runtime authority before any direct command execution, timing, arbitrary filelist, automatic allocation, runtime/ABI, or raw-state claim.

Native parser direct command-path native invocation boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_boundary_gate.json` defines the minimum future native invocation as a real Verilator-facing command with expanded `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` values, while requiring explicit reviewed sidecar context such as target, mode, template or registry entry, and source gate or manifest before any sidecar stage execution. The definition keeps wrapper execution, direct fixture metadata, materialized stage-plan metadata, and generated command text out of runtime authority. It advances to `review_verilator_native_option_parser_direct_command_path_native_invocation_boundary_gate`; this definition adds no native option support, direct Verilator command execution, new sidecar execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path native invocation boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_boundary_gate.json` accepts that boundary only for a later non-executing fixture. The review explicitly denies runtime authority to the native command alone, wrapper execution, direct fixture metadata, materialized stage-plan metadata, and generated command text, and selects `implement_verilator_native_option_parser_direct_command_path_native_invocation_fixture_gate`. This review adds no native option support, direct Verilator command execution, new sidecar execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

Native parser direct command-path native invocation fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_fixture_gate.json` adds `src/tools/verilator_native_option_parser_direct_native_invocation_fixture.py` as a non-executing helper. It requires a Verilator-facing argv plus explicit sidecar context, or a reviewed parser payload plus explicit sidecar context, and keeps `verilator_process_invoked`, wrapper execution, generated command authority, materialized stage-plan authority, timing, source closure inference, filelist expansion, automatic allocation, runtime/ABI change, and raw full-state equality claims false. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_fixture_implementation_gate`.

Native parser direct command-path native invocation fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_fixture_implementation_gate.json` accepts only the importable helper's metadata validation boundary. The review keeps native command-alone execution authority, fixture metadata runtime authority, generated command text authority, sidecar stage-plan metadata authority, sidecar execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, and raw full-state equality out of scope. The selected next gate is `define_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate`.

Native parser direct command-path native invocation execution boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate.json` defines the first real native-invocation execution boundary after the accepted metadata-only fixture. The future run must validate fixture metadata, require a built or reviewed Verilator process parse result for expanded `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`, require explicit sidecar context and reviewed stage authority before any stage execution, and keep generated evidence under `reports/` and `artifacts/`. This definition adds no native Verilator option support, direct Verilator command execution, sidecar execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate`.

Native parser direct command-path native invocation execution boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_execution_boundary_gate.json` accepts that definition only as a future scoped run boundary. The review requires real Verilator process parse evidence, explicit sidecar context, reviewed stage authority, and generated evidence under `reports/` and `artifacts/` before any later execution claim. It still does not claim native option support, direct Verilator command execution by the review gate, sidecar execution, compare execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality. The selected next gate is `run_verilator_native_option_parser_direct_command_path_native_invocation_execution_gate`.

Native parser direct command-path native invocation execution run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_execution_gate.json` records the first scoped real-process parse attempt after validating native-invocation fixture metadata. The local PATH Verilator reports `Verilator 5.044 2026-01-01 rev vUNKNOWN-built20260114`, its help text does not mention `--sim-accel`, and an isolated smoke RTL parse probe exits with `%Error: Invalid option: --sim-accel`. This is accepted only as process-parse failure evidence; no sidecar stage, compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or native option support is claimed. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_execution_run_gate`.

Native parser direct command-path native invocation execution run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_execution_run_gate.json` accepts the run only as local PATH Verilator process-parse failure evidence. The review explicitly keeps `--timing` as ordinary parser/build input, not timing evidence, and preserves all sidecar execution, compare, coverage-output equivalence, automatic allocation, runtime/ABI, raw full-state equality, and native option support claims as false. The selected next gate is `define_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_selection_gate`.

Native parser direct command-path patched-binary selection definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_selection_gate.json` selects `artifacts/verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_v1/verilator-v5.048-clean/bin/verilator_bin` as the candidate for the next parser-only native-invocation retry. The source of truth is the provenance chain to the v5.048 overlay patch build, parser behavior, and parser integer-hardening gates; the artifact path is generated evidence and must exist or be rebuilt before use. This definition does not execute the binary, does not claim native option support, and does not permit sidecar execution, compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_selection_gate`.

Native parser direct command-path patched-binary selection review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_selection_gate.json` accepts the rebuilt parser-hardening `verilator_bin` only as the candidate for the next parser-only retry. The weakest point is preserved: the binary path is a generated artifact without digest authority, so the next run must record either exact artifact presence or an equivalent rebuild before invoking it. This review does not execute the binary, does not claim native option support, and does not permit sidecar execution, compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality. The selected next gate is `run_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_gate`.

Native parser direct command-path patched-binary retry run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_gate.json` records a direct invocation of the reviewed patched `verilator_bin` with `VERILATOR_ROOT` set to the generated checkout root. The isolated smoke RTL parser-only command using `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1` exits `0`, so the expanded native option spelling is accepted by that patched binary in parser-only smoke mode. The run records that the artifact is generated evidence, not source of truth; it does not claim sidecar execution, compare, coverage-output equivalence, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_run_gate`.

Native parser direct command-path patched-binary retry review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_patched_binary_retry_run_gate.json` accepts only the parser-only smoke success for the reviewed patched binary. The review keeps the weakest point explicit: the binary is generated artifact evidence without digest authority or an equivalent rebuild inside this gate. It does not claim native parser integration completion, sidecar execution, compare, coverage-output equivalence, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `define_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate`.

Native parser direct command-path sidecar authority boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json` defines what must exist after patched-binary parser-only success and before any native sidecar handoff. The boundary requires explicit sidecar context, reviewed stage authority, non-canonical artifact provenance, separated process/authority/stage/compare failure classes, and explicit coverage-output compare policy. This definition does not execute sidecar stages, does not compare outputs, and does not claim timing, speedup, arbitrary RTL/filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate`.

Native parser direct command-path sidecar authority boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_sidecar_authority_boundary_gate.json` accepts only the non-executing authority boundary definition. It keeps the weakest point explicit: parser-only success plus generated patched-binary evidence is not sidecar execution authority. This review does not execute sidecar stages, does not compare outputs, and does not claim coverage-output equivalence evidence, timing, speedup, arbitrary RTL/filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `define_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate`.

Native parser direct command-path first scoped sidecar execution boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate.json` selects only `pulp_ita_mha` / `config/slice_launch_templates/pulp_ita_mha.json` / `64x1` for a future native sidecar execution attempt. The future run must use the reviewed patched binary or equivalent rebuild, explicit sidecar context, the seven reviewed sidecar stages, generated evidence only under `reports/` and `artifacts/`, and `coverage_output_equivalence` with explicit output-word authority. This definition does not execute sidecar stages, does not compare outputs, and does not claim timing, speedup, arbitrary RTL/filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate`.

Native parser direct command-path first scoped sidecar execution boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_boundary_gate.json` accepts only the narrow future-run boundary for `pulp_ita_mha` / `64x1`. The weakest point remains that `execution_boundary` can look like execution evidence, so the review explicitly does not execute sidecar stages, compare outputs, record coverage-output equivalence, measure timing, infer arbitrary filelists, allocate GPUs automatically, change runtime/ABI, or claim raw full-state equality or production throughput. The selected next gate is `run_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_gate`.

Native parser direct command-path first scoped sidecar execution run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_gate.json` records two separated facts: the reviewed patched `verilator_bin` parses the expanded native option spelling for `64x1`, and the reviewed `pulp_ita_mha 64x1` sidecar stage path executes build/run/compare with `coverage_output_equivalence` mismatch count `0` over `64` state pairs / `1856` words. The run explicitly does not claim direct Verilator sidecar execution, broad native option support, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_run_gate`.

Native parser direct command-path first scoped sidecar execution run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_first_scoped_sidecar_execution_run_gate.json` accepts only the separated patched-parser success plus reviewed `pulp_ita_mha 64x1` sidecar build/run/compare evidence. The weakest point is still direct launch authority: the accepted run does not prove that a Verilator process itself launched sidecar stages. The selected next gate is `define_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate`.

Native parser direct command-path direct sidecar launch boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate.json` defines the missing authority chain for a future run: one Verilator-facing process parse, explicit `pulp_ita_mha 64x1` sidecar context, reviewed stage authority, sidecar launch, and compare in one record. This is definition-only; it still does not claim direct Verilator sidecar execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate`.

Native parser direct command-path direct sidecar launch boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_boundary_gate.json` accepts only the future-run authority chain. The review keeps parser success, wrapper execution, generated command text, and stage-plan metadata non-authoritative by themselves, and selects a scoped direct-launch run gate next. This review still does not claim direct Verilator sidecar execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput.

Native parser direct command-path direct sidecar launch run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_gate.json` records a real patched-Verilator process parse of the expanded `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1` spelling, explicit `pulp_ita_mha 64x1` sidecar context, and the separate reviewed sidecar build/run/compare path still passing `coverage_output_equivalence` with mismatch count `0`. The direct native path does not reach sidecar launch, so the recorded failure class is `direct_launch_handoff_failure`; direct Verilator sidecar execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, and production throughput remain non-claims.

Native parser direct command-path direct sidecar launch run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_sidecar_launch_run_gate.json` accepts the run as honest failure evidence. It accepts patched-parser success and the separate reviewed `pulp_ita_mha 64x1` sidecar compare only as prerequisites, not direct-launch authority. The selected next task is defining a minimal direct-launch handoff implementation boundary before any runtime behavior change or direct Verilator sidecar execution claim.

Native parser direct command-path direct-launch handoff implementation boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json` defines the smallest allowed future implementation surface: validated native parser payload, explicit `pulp_ita_mha 64x1` sidecar context, reviewed stage authority, and the existing sidecar stage launcher. This is definition-only; it still does not claim direct Verilator sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput. The selected next gate is `review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate`.

Native parser direct command-path direct-launch handoff implementation boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_implementation_boundary_gate.json` accepts only the narrow implementation boundary. The next task is a non-executing fixture that represents parser-payload to sidecar-launcher handoff readiness; it still does not claim direct Verilator sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw full-state equality, or production throughput.

Native parser direct command-path direct-launch handoff fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_gate.json` adds `define_direct_launch_handoff_fixture` as a metadata-only readiness layer. The fixture preserves the `pulp_ita_mha 64x1` scope and the existing sidecar launcher reference while recording that sidecar launch and coverage-output compare remain unreached from the native path.

Native parser direct command-path direct-launch handoff fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_fixture_implementation_gate.json` accepts the fixture only as non-executing metadata readiness. The selected next task is defining a real handoff run boundary; direct Verilator sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production throughput remain non-claims.

Native parser direct command-path direct-launch handoff run boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate.json` defines the first future run boundary that may prove native parser metadata enters the existing sidecar launcher and reaches coverage-output compare. This is definition-only; direct Verilator sidecar execution, native-path compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production throughput remain non-claims. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate`.

Native parser direct command-path direct-launch handoff run boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_boundary_gate.json` accepts the boundary only as a future-run definition. The selected next task is `run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_gate`; direct Verilator sidecar execution, native-path compare result, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production throughput remain non-claims until that run is recorded and reviewed.

Native parser direct command-path direct-launch handoff run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_gate.json` records patched Verilator parser success, reviewed handoff fixture readiness, and a separate `pulp_ita_mha 64x1` sidecar launcher run with `coverage_output_equivalence` mismatch count `0`. The native path still does not enter the sidecar launcher from the Verilator-facing process, so the failure class remains `direct_launch_handoff_failure`; direct Verilator sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production throughput remain non-claims.

Native parser direct command-path direct-launch handoff run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_run_gate.json` accepts that scoped run as honest `direct_launch_handoff_failure` evidence after patched parser success, fixture readiness, and separate `pulp_ita_mha 64x1` sidecar coverage-output equivalence. The selected next task is defining the native-process to sidecar-launcher bridge boundary; direct Verilator sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production throughput remain non-claims.

Native parser direct command-path sidecar-launcher bridge boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate.json` defines the next implementation boundary from validated native parser payload and reviewed handoff fixture metadata into the existing `src/tools/run_hybrid_template.py` launcher. This is definition-only; direct Verilator sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production throughput remain non-claims pending review.

Native parser direct command-path sidecar-launcher bridge boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_boundary_gate.json` accepts that boundary only as implementation-ready for a non-executing bridge fixture. The selected next task is `implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_gate`; direct Verilator sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production throughput remain non-claims.

Native parser direct command-path sidecar-launcher bridge fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_gate.json` records `define_sidecar_launcher_bridge_fixture` in `src/tools/verilator_native_option_parser_direct_native_invocation_fixture.py`. The helper validates the reviewed handoff metadata, preserves `sidecar_launcher_bridge_failure`, keeps the `pulp_ita_mha 64x1` scope, and marks the existing launcher entrypoint as reference-only. It does not invoke the launcher, execute sidecar stages, run native-path compare, measure timing, broaden filelist/RTL support, change runtime/ABI behavior, or claim direct Verilator sidecar execution.

Native parser direct command-path sidecar-launcher bridge fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_bridge_fixture_implementation_gate.json` accepts the bridge fixture only as metadata. The selected next task is defining a scoped sidecar-launcher run boundary; the review still adds no launcher invocation, sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, or production-throughput evidence.

Native parser direct command-path sidecar-launcher run boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json` defines the first future run boundary that may prove reviewed bridge metadata invokes the existing `src/tools/run_hybrid_template.py` launcher and reaches `coverage_output_equivalence` compare for `pulp_ita_mha 64x1`. This is definition-only; launcher invocation, sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production-throughput evidence remain non-claims pending review and a later run gate.

Native parser direct command-path sidecar-launcher run boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_boundary_gate.json` accepts that boundary only as a future run definition. The selected next task is `run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_gate`; launcher invocation, sidecar execution, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production-throughput evidence remain non-claims until that run is recorded and reviewed.

Native parser direct command-path sidecar-launcher run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_gate.json` records patched Verilator parser success, reviewed bridge fixture readiness, and separate `pulp_ita_mha 64x1` sidecar coverage-output equivalence with mismatch count `0`. The native path is still classified as `sidecar_launcher_bridge_failure` because the bridge fixture does not invoke `src/tools/run_hybrid_template.py` from the native process; launcher invocation, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production-throughput evidence remain non-claims pending review.

Native parser direct command-path sidecar-launcher run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_run_gate.json` accepts that `sidecar_launcher_bridge_failure` classification as honest evidence. The selected next task is `define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate`; direct Verilator sidecar execution, native-path launcher invocation, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, and production-throughput evidence remain non-claims.

Native parser direct command-path sidecar-launcher invocation boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate.json` defines the minimal implementation boundary from reviewed parser payload and bridge metadata to the existing `src/tools/run_hybrid_template.py` launcher. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate`; this definition still adds no direct Verilator sidecar execution, native-path launcher invocation, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, or production-throughput evidence.

Native parser direct command-path sidecar-launcher invocation boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_boundary_gate.json` accepts the boundary only for a scoped fixture implementation. This review still adds no direct Verilator sidecar execution, native-path launcher invocation evidence, native-path compare, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, raw-state equality, or production-throughput evidence.

Native parser direct command-path sidecar-launcher invocation fixture review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_fixture_implementation_gate.json` accepts `define_sidecar_launcher_invocation_fixture` only as metadata. It validates reviewed parser payload, reviewed bridge metadata, and the exact sidecar-launcher run review gate before materializing `run_hybrid_template.py` argv for `pulp_ita_mha 64x1`. The selected next task is `define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate`; this review still does not invoke the launcher, execute sidecar stages, reach native-path compare, measure timing, broaden filelist/RTL support, change runtime/ABI behavior, or claim direct Verilator sidecar execution.

Native parser direct command-path sidecar-launcher invocation run boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate.json` defines the future scoped run preconditions from reviewed invocation fixture metadata and structured argv to `src/tools/run_hybrid_template.py` plus `coverage_output_equivalence` compare for `pulp_ita_mha 64x1`. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate`; this definition still does not invoke the launcher, execute sidecar stages, reach native-path compare, measure timing, broaden filelist/RTL support, change runtime/ABI behavior, or claim direct Verilator sidecar execution.

Native parser direct command-path sidecar-launcher invocation run boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_boundary_gate.json` accepts that boundary only for a scoped future run. The selected next task is `run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_gate`; this review still does not invoke the launcher, execute sidecar stages, reach native-path compare, measure timing, broaden filelist/RTL support, change runtime/ABI behavior, or claim direct Verilator sidecar execution.

Native parser direct command-path sidecar-launcher invocation run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_gate.json` records the reviewed structured launcher argv `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1` starting the existing launcher and reaching `coverage_output_equivalence` compare with mismatch count `0`. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_gate`; direct Verilator sidecar execution, broad native option support, timing, automatic allocation, runtime/ABI change, arbitrary filelist support, raw-state equality, and production-throughput evidence remain non-claims until reviewed.

Native parser direct command-path sidecar-launcher invocation run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_gate.json` accepts only the scoped structured launcher invocation evidence for `pulp_ita_mha 64x1`. The reviewed run starts `src/tools/run_hybrid_template.py` from materialized argv, executes the existing sidecar stages, and passes `coverage_output_equivalence` with mismatch count `0` over `64` state pairs / `1856` words. The selected next task is `define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate`; the remaining gap is that a full native Verilator process-to-launcher CLI path still does not exist, so direct Verilator sidecar execution, broad native option support, timing, automatic allocation, runtime/ABI change, arbitrary filelist support, raw-state equality, and production-throughput evidence remain non-claims.

Native parser direct command-path process-to-launcher CLI boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate.json` defines the missing authority chain from a Verilator-facing process parse result to the existing `src/tools/run_hybrid_template.py` launcher CLI. It requires parser schedule, explicit sidecar context, source or template authority, structured launcher argv without shell-string guessing, and separate failure classes for parse, context, authority, process-to-launcher bridge, launcher invocation, sidecar stage, compare, and timing-without-measurement. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate`; this definition still adds no process-to-launcher implementation, direct Verilator sidecar execution, broad native option support, timing, automatic allocation, runtime/ABI change, arbitrary filelist support, raw-state equality, or production-throughput evidence.

Native parser direct command-path process-to-launcher CLI boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate.json` accepts the boundary only for a scoped non-executing fixture implementation. The accepted boundary may connect a Verilator-facing parser payload, explicit `pulp_ita_mha 64x1` sidecar context, reviewed source or template authority, and the existing `src/tools/run_hybrid_template.py` launcher argv, while keeping launcher execution, sidecar stages, compare, timing, runtime/ABI change, public CLI change, broad native option support, arbitrary filelist support, raw-state equality, and production-throughput evidence out of scope. The selected next task is `implement_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_gate`.

Native parser direct command-path process-to-launcher CLI fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_gate.json` records `src/tools/verilator_native_option_parser_process_to_launcher_cli_fixture.py::define_process_to_launcher_cli_fixture`. The helper requires the current process-to-launcher boundary review gate, rejects predecessor structured-invocation review evidence as current authority, rejects generated command text or payload-only authority fields, and materializes the exact `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1` argv without starting the launcher. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_implementation_gate`; launcher execution, sidecar stages, compare, timing, runtime/ABI change, broad native option support, arbitrary filelist support, raw-state equality, and production-throughput evidence remain non-claims.

Native parser direct command-path process-to-launcher CLI fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_implementation_gate.json` accepts the non-executing fixture only after separating the predecessor structured launcher invocation run review gate from the older reused sidecar launcher fixture source gate. The selected next task is `define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate`; the next boundary must define when the exact materialized `run_hybrid_template.py` argv may be used to start a launcher process, while still keeping sidecar stage execution, compare, timing, runtime/ABI change, broad native option support, arbitrary filelist support, raw-state equality, and production-throughput evidence out of scope.

Native parser direct command-path process-to-launcher CLI execution boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate.json` defines only the future boundary for turning reviewed process-to-launcher CLI fixture metadata into a scoped `src/tools/run_hybrid_template.py` launcher process start. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate`; this definition still adds no launcher execution, sidecar stage execution, compare, timing, runtime/ABI change, broad native option support, arbitrary filelist support, raw-state equality, or production-throughput evidence.

Native parser direct command-path process-to-launcher CLI execution boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate.json` accepts the definition only for a scoped future run. The selected next task is `run_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_gate`; this review still adds no launcher execution, sidecar stage execution, compare, timing, runtime/ABI change, broad native option support, arbitrary filelist support, raw-state equality, or production-throughput evidence.

Native parser direct command-path process-to-launcher CLI execution run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_gate.json` records the scoped `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1` run from reviewed process-to-launcher CLI fixture metadata. The launcher started, all sidecar stages reached, and `coverage_output_equivalence` compare passed with mismatch count `0` over `64` state pairs / `1856` words.

Native parser direct command-path process-to-launcher CLI execution run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_run_gate.json` accepts that run only as process-to-launcher CLI execution from reviewed fixture metadata. It selected `define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_boundary_gate`; direct Verilator sidecar execution, broad native option support, timing, automatic allocation, runtime/ABI change, arbitrary filelist support, raw-state equality, and production-throughput evidence remain non-claims.

Native parser direct command-path Verilator process launcher bridge fixture implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_fixture_gate.json` records `src/tools/verilator_native_option_parser_verilator_process_launcher_bridge_fixture.py::define_verilator_process_launcher_bridge_fixture`. The helper requires the reviewed bridge boundary gate, builds or validates reviewed process-to-launcher CLI metadata, rejects unreviewed sidecar context authority when prebuilt metadata is supplied, preserves explicit sidecar context, and materializes the exact `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1` argv without starting Verilator or the launcher. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_fixture_implementation_gate`; launcher execution, sidecar stages, compare, timing, runtime/ABI change, broad native option support, arbitrary filelist support, raw-state equality, direct Verilator sidecar execution, and production-throughput evidence remain non-claims.

Native parser direct command-path Verilator process launcher bridge fixture implementation review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_fixture_implementation_gate.json` accepts the bridge fixture only as metadata. The selected next task is `define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_boundary_gate`; the next boundary must define when reviewed Verilator-process-to-launcher bridge metadata may drive a wrapper-mediated Verilator-facing process and launcher start. This review still adds no Verilator process execution, launcher execution, sidecar stage execution, native-path compare, timing, broad native option support, arbitrary filelist support, automatic GPU allocation, runtime/ABI change, raw-state equality, or production-throughput evidence.

Native parser direct command-path Verilator process launcher bridge execution boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_boundary_gate.json` defines only the future boundary for turning reviewed bridge fixture metadata into a wrapper-mediated Verilator-facing process plus structured launcher start. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_boundary_gate`; this definition still adds no Verilator process execution, launcher execution, sidecar stage execution, native-path compare, timing, broad native option support, arbitrary filelist support, automatic GPU allocation, runtime/ABI change, raw-state equality, or production-throughput evidence.

Native parser direct command-path Verilator process launcher bridge execution boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_boundary_gate.json` accepts the definition only for a scoped future run. The selected next task is `run_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_gate`; that run must record expanded option parse acceptance, reviewed bridge metadata validation, explicit sidecar context authority, unreviewed context-ref rejection, exact structured launcher argv, and observable wrapper-mediated bridge trace before launcher start. This review still adds no Verilator process execution, launcher execution, sidecar stage execution, native-path compare, timing, broad native option support, arbitrary filelist support, automatic GPU allocation, runtime/ABI change, raw-state equality, direct Verilator sidecar execution, or production-throughput evidence.

Native parser direct command-path Verilator process launcher bridge execution run state: `config/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_gate.json` records the first scoped bridge execution attempt as `process_to_launcher_bridge_failure`. Reviewed bridge fixture metadata is ready, process-to-launcher CLI metadata matches, explicit sidecar context authority is validated, and unreviewed context refs are rejected, but there is still no callable path that emits observable wrapper-mediated bridge trace before launcher start. The accepted process-to-launcher CLI run remains prerequisite evidence only; bridge-path launcher start, bridge-path sidecar stages, bridge-path compare, direct Verilator sidecar execution, broad native option support, timing, automatic allocation, runtime/ABI change, arbitrary filelist support, raw-state equality, and production-throughput evidence remain non-claims. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_run_gate`.

Native parser direct command-path Verilator process launcher bridge execution run review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_execution_run_gate.json` accepts `process_to_launcher_bridge_failure` as the honest failure classification. The review accepts bridge metadata readiness and the separate process-to-launcher CLI run only as prerequisite evidence, not bridge-path authority. The selected next task is `define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_implementation_boundary_gate`; it must define the minimal callable implementation boundary for observable wrapper-mediated bridge ordering before launcher start. This still does not prove direct Verilator sidecar execution, bridge-path launcher start, bridge-path compare, broad native option support, timing, automatic allocation, runtime/ABI change, arbitrary filelist support, raw-state equality, or production-throughput evidence.

Native parser direct command-path Verilator process launcher bridge observable-ordering implementation boundary definition state: `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_implementation_boundary_gate.json` defines the minimal future implementation boundary for a callable wrapper-mediated ordering helper. The future helper must validate reviewed bridge metadata, reviewed process-to-launcher metadata, explicit sidecar context, and unreviewed context-ref rejection before emitting an observable bridge trace ahead of launcher start. The selected next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_implementation_boundary_gate`. This definition still adds no implementation code, launcher start, bridge-path compare, timing, broad native option support, automatic allocation, runtime/ABI change, arbitrary filelist support, direct Verilator sidecar execution, raw-state equality, or production-throughput evidence.

Native parser direct command-path Verilator process launcher bridge observable-ordering implementation boundary review state: `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_implementation_boundary_gate.json` accepts the definition only as an implementation-boundary review. The next task is `implement_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_helper_gate`; it may add an importable helper in `src/tools/verilator_native_option_parser_verilator_process_launcher_bridge_fixture.py` that emits an observable ordering trace before launcher-start-allowed status. This review still does not allow launcher process execution, sidecar stages, bridge-path compare, timing, public CLI changes, runtime/ABI changes, arbitrary filelist support, automatic allocation, direct Verilator sidecar execution, raw-state equality, or production-throughput claims.

Native parser direct command-path Verilator process launcher bridge observable-ordering helper implementation state: `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_helper_gate.json` adds `run_verilator_process_launcher_bridge_with_observable_ordering` in `src/tools/verilator_native_option_parser_verilator_process_launcher_bridge_fixture.py`. The helper validates reviewed bridge metadata, reviewed process-to-launcher metadata, explicit `pulp_ita_mha 64x1` sidecar context, unreviewed context-ref rejection, and the exact structured launcher argv before returning a monotonic ordering trace and launcher-start-allowed status. It still does not start the launcher, execute sidecar stages, run bridge-path compare, measure timing, add a public CLI, change runtime/ABI behavior, infer arbitrary filelists, allocate GPUs automatically, prove direct Verilator sidecar execution, prove raw-state equality, or claim production throughput. The next task is `review_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_observable_ordering_helper_implementation_gate`.

The full ITA/MHA plus larger paged KV-cache goal is complete and held for review. Full MHA was retried through the current hybrid path; the fresh 1x1 run wrote `reports/pulp_ita_mha_hybrid_1x1.txt` and passed coverage-output equivalence in `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`.

Full MHA scale-up state: `64x1` and `1x64` were measured in `reports/pulp_ita_mha_64x1_1x64_scaling_summary.json`; `64x1` is GPU-favorable while `1x64` remains a weak repeated-step shape for this single run.

Prefill/decode split state: `64x1` is recorded as prefill-like and `1x64` as decode-like in `reports/pulp_ita_mha_prefill_decode_split_summary.json`; the serving implication is that hybrid favors batched/state-parallel MHA-style work more than serial single-state decode-style work.

Resident decode state: `1x64` resident mode is recorded in `reports/pulp_ita_mha_resident_decode_1x64_summary.json`; it preserves coverage-output equivalence and improves hybrid wall by about 1.91x for this single run.

Resident decode batch-parallel state: `8x64`, `16x64`, and `32x64` resident modes are recorded in `reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json`; all pass coverage-output equivalence, and `32x64` improves per-state-step wall cost by about 26.06x over `1x64` resident for this single run.

Long-goal audit state: `config/scaling_gates/modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json` now maps correctness, speed, reproducibility, and non-claims to the current MHA, paged-attention, paged-KV, prefill/decode, resident, resident batch-parallel, persistent resident ABI, and MobileViT limit-128 CPU-kick plus hybrid control-boundary evidence.

Public results state: `config/scaling_gates/public_results_packaging_gate.json` now refreshes `docs/results.md` after the persistent resident ABI measurement, MobileViT limit-128 evidence, and wrapper summary schema publication. The public benchmark pack presents the conclusion, reproduction commands, result tables, wrapper summary reports, source evidence, and non-claims for external readers.

Public results MHA refresh state: `config/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json` defines the source-of-truth refresh after the fresh `pulp_ita_mha` generic-host-probe chain. `docs/results.md` now includes the `1x1`, `32x1`, and `1x32` compare reports, single-run timing table, and gate chain references while keeping reports/artifacts generated-only. This is not a new workload measurement, not repeat-median evidence, and not a production LLM-serving throughput claim; the next_task returns to `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`.

Filelist broader shape timing public refresh definition state: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json` closes the accepted four-command single-run timing review into a packaging-only refresh definition. It pins the timing definition/result/review gates plus eight timing reports and four compare reports as generated evidence only, preserves `coverage_output_equivalence` mismatch count `0`, and makes the next task the public-pack archive dry-run. It does not add measurement/execution evidence or claim repeat-median timing, broad speedup, GEM comparison, native Verilator option support, arbitrary RTL support, automatic allocation, runtime/ABI change, production-serving throughput, or raw full-state equality.

Filelist broader shape timing public refresh review state: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` and including the timing definition/result/review, public-refresh definition, source-of-truth docs, compact selection pointers, and twelve generated timing/compare reports as evidence-only paths. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json` accepts this packaging-only refresh and selects public benchmark-pack externalization completion next.

Filelist broader shape timing public-pack externalization completion state: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json` closes the publication boundary for the scoped four-command single-run `64x1` / `1x64` timing refresh. The closed claim remains `coverage_output_equivalence` mismatch count `0`, raw full-state equality false and non-required, and single-run timing ranges only; repeat-median timing, broad speedup, GEM comparison, native Verilator option support, arbitrary RTL/dependency inference, runtime/ABI changes, production-serving throughput, and automatic optimal allocation remain non-claims. It selects next-measurement selection after this public-pack refresh.

Next measured workstream after broader shape timing public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate`. The selected scope is repeat-median timing for the same two reviewed filelist-derived targets at `64x1` and `1x64`; this is selection-only and does not add measurement, execution, repeat-median evidence, broad speedup, GEM comparison, native Verilator support, arbitrary RTL/dependency inference, runtime/ABI changes, production-serving throughput, automatic optimal allocation, or raw full-state equality.

Filelist broader shape repeat-median timing definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_timing_gate.json` fixes the same two reviewed filelist-derived targets at `64x1` and `1x64`, repeat count `3`, and `coverage_output_equivalence` for every repeat sample. It records the workflow gap that the existing `--filelist-shape-breadth-repeat-median` public CLI is scoped to `32x1` / `1x32`, so the next task is adding a distinct public workflow for the broader-shape set. This remains definition-only and adds no measurement, execution, repeat-median evidence, broad speedup, GEM comparison, native Verilator support, arbitrary RTL/dependency inference, runtime/ABI changes, production-serving throughput, automatic optimal allocation, or raw full-state equality.

Filelist broader shape repeat-median workflow: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --filelist-broader-shape-repeat-median 3 --dry-run` for the same `64x1` / `1x64` target/shape set. The workflow gate itself is public and tested but remains workflow-only; the measurement gate below records the non-dry-run repeat-count-3 evidence.

Filelist broader shape repeat-median measurement: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --filelist-broader-shape-repeat-median 3` exiting `0`. All 12 samples pass `coverage_output_equivalence` with mismatch count `0`; median CPU-to-hybrid wall ratios are `129.02924528301887x` for `filelist_paged_attention_kv_score 64x1`, `2.204404109589041x` for `filelist_paged_attention_kv_score 1x64`, `121.47241379310344x` for `filelist_known_template_pulp_ita_mha 64x1`, and `1.7360211463550361x` for `filelist_known_template_pulp_ita_mha 1x64`. This is scoped repeat-count-3 evidence for these exact filelist-derived templates; review is required before public-pack refresh or broader claims.

Filelist broader shape repeat-median review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json` accepts only the scoped repeat-count-3 result for the two reviewed filelist-derived targets at `64x1` and `1x64`. The review records that the evidence is narrow, repeat-count `3` is not paper-grade statistics, `1x64` remains a modest-ratio repeated-step case, and generated reports are not source of truth. It selects `define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate` next and keeps broad speedup, native Verilator option, arbitrary RTL/dependency inference, automatic GPU allocation, runtime/ABI, GEM comparison, production-serving, and raw full-state equality as non-claims.

Filelist broader shape repeat-median public refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json` defines the documentation and archive dry-run boundary for the reviewed broader-shape repeat-count-3 evidence. It pins the boundary, workflow, measurement, review, and refresh definition gates plus `reports/filelist_broader_shape_repeat_median_summary.json` and four median report paths as generated evidence only.

Filelist broader shape repeat-median public refresh review: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_result_gate.json` records the public-pack archive dry-run exiting `0`; `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_review_gate.json` accepts that packaging-only result.

Filelist broader shape repeat-median public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_gate.json` closes the publication boundary for the scoped repeat-count-3 `64x1` / `1x64` refresh.

Next measured workstream after broader shape repeat-median public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_repeat_median_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate`. That follow-up defined a conservative broader scoped allocation policy from the earlier `32x1` / `1x32` evidence plus the latest `64x1` / `1x64` repeat-median evidence; automatic optimal allocation, native Verilator option support, arbitrary dependency inference, GEM comparison, runtime/ABI change, and production serving remain non-claims.

Filelist broader shape GPU allocation policy boundary: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json` defines the scoped broader policy from the earlier `32x1` / `1x32` evidence and the latest `64x1` / `1x64` repeat-median evidence. It recommends `64x1` with high confidence only for the two reviewed filelist-derived targets, keeps `32x1` as a reviewed fallback, and selects a distinct broader-policy workflow gate next. This is definition-only; no execution, measurement, native Verilator option, arbitrary RTL/dependency inference, runtime/ABI, GEM comparison, automatic optimal allocation, or production-serving claim is added.

Filelist broader shape GPU allocation policy public-pack externalization: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_gate.json` closes the publication boundary for the distinct `python3 src/tools/run_results_reproduction.py --filelist-broader-shape-gpu-allocation-policy --dry-run` payload. It keeps `64x1` high-confidence recommendations and `32x1` medium-confidence fallbacks scoped to two reviewed filelist-derived targets; this adds no execution, measurement, native Verilator option, arbitrary RTL/dependency inference, runtime/ABI, GEM comparison, automatic optimal allocation, or production-serving claim.

Next measured workstream after broader shape GPU allocation policy public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate`. This is selection-only; it adds no execution, measurement, timing, native Verilator option, arbitrary RTL/dependency inference, runtime/ABI, GEM comparison, automatic optimal allocation, production-serving, or raw full-state equality claim.

Filelist broader shape GPU allocation policy non-dry-run execution definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json` selects both policy-recommended `64x1` build/run/compare commands for `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha`. The `32x1` fallback remains recorded as reviewed but is not selected for this execution gate. This definition adds no execution, measurement, timing, native Verilator option, arbitrary RTL/dependency inference, runtime/ABI, GEM comparison, automatic optimal allocation, production-serving, or raw full-state equality claim.

Filelist broader shape GPU allocation policy non-dry-run execution accepted: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json` records the two policy-recommended `64x1` build/run/compare commands exiting `0`, writing `reports/filelist_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json` and `reports/filelist_known_template_pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json`, and passing `coverage_output_equivalence` with mismatch count `0` over `64` state pairs, `1856` words, and `7424` bytes per report. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json` accepts this scoped result and selects public results packaging refresh next; raw full-state equality remains false and non-required.

Filelist broader shape GPU allocation policy non-dry-run public refresh defined: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json` pins the accepted execution definition, result, review, the two `64x1` compare reports, and the prior broader policy input evidence into the next public-pack archive dry-run boundary. It is packaging-only and adds no new execution, measurement, timing, speedup, repeat-median, native Verilator option, arbitrary RTL/dependency inference, automatic allocation, runtime/ABI, GEM, production-serving, or raw full-state equality claim.

Filelist broader shape GPU allocation policy non-dry-run public refresh accepted: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_result_gate.json` records the public-pack archive dry-run exiting `0`, creating no archive, and including the accepted execution result/review gates plus the two `64x1` compare reports. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_review_gate.json` accepts this packaging-only refresh and selects the public benchmark-pack externalization completion definition next.

Filelist broader shape GPU allocation policy non-dry-run public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_gate.json` closes the publication boundary for the scoped two-command `64x1` policy-selected execution result and public refresh. The closed claim remains `coverage_output_equivalence` mismatch count `0`, with `32x1` only as a reviewed fallback and raw full-state equality false/non-required. The next task is selecting the next measured workstream; no new measurement, execution, timing/speedup, repeat-median, runtime/ABI, native Verilator option, arbitrary RTL/dependency inference, automatic optimal allocation, GEM, production-serving, or raw full-state equality claim is added.

Next measured workstream after broader policy non-dry-run public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_non_dry_run_execution_public_pack_refresh_gate.json` selects policy-selected `64x1` repeat-median timing before native option work, broader automatic allocation, dependency inference, resident execution optimization, GEM comparison, runtime/ABI changes, or production-serving claims.

Filelist broader shape GPU allocation policy repeat-median timing definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_timing_gate.json` defines repeat count `3`, total sample count `6`, `coverage_output_equivalence`, and the exact two `64x1` filelist-derived commands selected by the broader policy. It records the workflow gap that the existing broader-shape repeat-median CLI includes non-selected `1x64`, so a distinct policy-selected workflow is required next.

Filelist broader shape GPU allocation policy repeat-median workflow added: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --filelist-broader-policy-repeat-median 3 --dry-run`, reusing the existing repeat-median core with a two-workload `64x1` policy-selected workload set. The next task is the dry-run result gate; no new measurement, timing/speedup, runtime/ABI, native Verilator option, arbitrary RTL/dependency inference, automatic allocation, GEM, production-serving, or raw full-state equality claim is added.

Filelist broader shape GPU allocation policy repeat-median dry-run accepted: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_result_gate.json` records `python3 src/tools/run_results_reproduction.py --filelist-broader-policy-repeat-median 3 --dry-run` exiting `0`, planning exactly two `64x1` targets, six compare commands, no `1x64` commands, no generated writes, and no local absolute paths. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_dry_run_review_gate.json` accepts only that plan and selects the non-dry-run timing gate next.

Filelist broader shape GPU allocation policy repeat-median measured and reviewed: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --filelist-broader-policy-repeat-median 3` for exactly the two policy-selected `64x1` filelist workloads. All six samples pass `coverage_output_equivalence` with mismatch count `0`; median CPU-to-hybrid-wall ratios are `145.7001090512541` for `filelist_paged_attention_kv_score` and `139.77687626774846` for `filelist_known_template_pulp_ita_mha`. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json` accepts only that scoped result and selects public results packaging refresh definition next; per-sample stdout reports may contain local paths and must stay out of public-pack evidence.

Filelist broader shape GPU allocation policy repeat-median public refresh accepted: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json` defines the packaging-only refresh for the accepted aggregate and median JSON reports. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_result_gate.json` records the public archive dry-run exiting `0` with `include_count=535`, `exclude_count=2`, no archive creation, and no per-sample stdout/local absolute paths in the manifest. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_review_gate.json` accepts the refresh and selects public benchmark-pack externalization completion next.

Filelist broader shape GPU allocation policy repeat-median public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_gate.json` closes the publication boundary for the scoped two-target `64x1` policy-selected repeat-median result. The closed claim remains `coverage_output_equivalence` mismatch count `0`, with `32x1` only as fallback and per-sample stdout excluded from public-pack evidence. The next task is selecting the next measured workstream; no new measurement, execution, native Verilator option, arbitrary RTL/dependency inference, automatic optimal allocation, GEM, runtime/ABI, production-serving, or raw full-state equality claim is added.

Next measured workstream after policy-selected repeat-median public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_policy_repeat_median_public_pack_refresh_gate.json` selects `define_verilator_native_option_prototype_boundary_gate`. Native option work is selected because the scoped sidecar/filelist/policy evidence is now closed; the selection remains definition-only and does not claim native Verilator support, arbitrary RTL support, dependency inference, automatic optimal allocation, runtime/ABI change, GEM comparison, or production-serving throughput.

Verilator native option prototype boundary: `config/scaling_gates/define_verilator_native_option_prototype_boundary_gate.json` defines the future primary spelling as expanded `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1` on a normal `verilator --cc --timing` command. It keeps `--sim-accel-shape` as wrapper/shim compatibility, records that current `filelist_*` targets are not yet registered in the `run_hybrid_benchmark.py` sidecar registry, and selects a dry-run gate next. This remains definition-only, not native Verilator support or arbitrary filelist execution.

Verilator native option prototype boundary dry-run: `config/scaling_gates/verilator_native_option_prototype_boundary_dry_run_result_gate.json` records four plan-only commands exiting `0`: registered shim previews for `paged_attention_kv_score` and `pulp_ita_mha`, plus `64x1` filelist-template dry-runs for `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha`. `config/scaling_gates/verilator_native_option_prototype_boundary_dry_run_review_gate.json` accepts that dry-run and selects `define_verilator_native_option_prototype_filelist_target_resolution_gate` next. The remaining weak point is direct `filelist_*` target support in the shim registry; no native parser, execution, timing, dependency inference, automatic allocation, runtime/ABI, or production-serving claim is added.

Verilator native option prototype filelist registry support: `config/scaling_gates/define_verilator_native_option_prototype_filelist_target_resolution_gate.json` selects static registry entries for exactly two tracked templates, not a new planner. `config/scaling_gates/verilator_native_option_prototype_filelist_registry_result_gate.json` records preview/operator-plan commands exiting `0` for `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha`; `config/scaling_gates/verilator_native_option_prototype_filelist_registry_review_gate.json` accepts this tracked-template-only support and selects public results packaging refresh next. This adds no native parser, arbitrary filelist support, dependency inference, automatic allocation, runtime/ABI change, or new measurement evidence.

Verilator native option prototype filelist registry public refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_gate.json` defines the packaging-only refresh for that accepted tracked-template registry support. It selects the public-pack archive dry-run next and keeps the boundary as two static `filelist_*` targets only; no native parser, arbitrary filelist support, dependency inference, automatic allocation, runtime/ABI change, execution, or measurement claim is added.

Verilator native option prototype filelist registry public refresh accepted: `config/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0`, with `include_count=546`, `exclude_count=2`, no archive creation, and generated-output exclusions preserved. `config/scaling_gates/public_results_packaging_refresh_after_verilator_native_option_prototype_filelist_registry_review_gate.json` accepts only this packaging result and selects public benchmark-pack externalization completion next.

Verilator native option prototype filelist registry public-pack externalization complete: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_verilator_native_option_prototype_filelist_registry_gate.json` closes the public-pack boundary for exactly two static tracked `filelist_*` registry targets and advances to next-measurement/workstream selection. This is completion-only and adds no native parser, arbitrary filelist support, dependency inference, automatic allocation, runtime/ABI change, execution, or measurement claim.

Next workstream selection after Verilator native option prototype filelist registry public-pack refresh: `config/scaling_gates/next_measurement_selection_after_verilator_native_option_prototype_filelist_registry_public_pack_refresh_gate.json` selects `define_commit_split_and_public_pack_cleanup_gate`. The weak point is now operational hygiene: the tracked registry/public-pack chain is closed, but the staged set was observed above the documented `100`-file commit guard, so the next gate must pin commit groups before any native parser, planner, dependency inference, allocation broadening, resident optimization, or GEM work is added.

Commit split and public-pack cleanup boundary definition: `config/scaling_gates/define_commit_split_and_public_pack_cleanup_gate.json` defines eight review-sized groups with estimated file counts `15`, `26`, `71`, `30`, `24`, `59`, `28`, and `25`. It also records per-file line guard risks for `src/tools/results_reproduction_gpu_allocation_policy.py`, `tests/contract/test_hybrid_verilator_like_cli.py`, and `tests/contract/test_public_pack_repeat_median_refresh_gates.py`, so the review must decide between hunk staging, refactoring, or explicit reviewed overrides before any index rewrite or commit execution.

Commit split and public-pack cleanup review: `config/scaling_gates/review_commit_split_and_public_pack_cleanup_gate.json` accepts the eight file-count groups as the operational split boundary. The weak point is now narrower: ordinary hook-clean commits are still blocked by line guard risks in `src/tools/results_reproduction_gpu_allocation_policy.py`, `tests/contract/test_hybrid_verilator_like_cli.py`, and `tests/contract/test_public_pack_repeat_median_refresh_gates.py`, so the next gate must resolve those before any index rewrite or commit execution.

Commit split line guard resolution: `config/scaling_gates/resolve_commit_split_line_guard_risks_gate.json` records the line guard cleanup. `src/tools/results_reproduction_gpu_allocation_policy.py` now keeps payload construction separate from static evidence data, filelist assertions moved out of `tests/contract/test_hybrid_verilator_like_cli.py` into focused contract tests, and `tests/contract/test_public_pack_repeat_median_refresh_gates.py` is back under the added-line guard. `python3 src/tools/check_staged_large_files.py --max-files 999` exits `0`; the remaining blocker is the staged file-count guard.

Commit split index rewrite completion: `config/scaling_gates/execute_commit_split_index_rewrite_gate.json` records the accepted split as executed. The payload landed as eight hook-sized commits after the staged-only hook prerequisite; the largest payload commit touched `76` files, below the documented `100`-file guard. The worktree was clean after the split and `make simple && make check` passed with `221` contract tests. The next selected boundary is `define_verilator_native_option_parser_boundary_gate`; this completion adds no native parser implementation, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser boundary definition: `config/scaling_gates/define_verilator_native_option_parser_boundary_gate.json` defines the minimal native parser surface as `--sim-accel sidecar-gpu` plus paired positive `--sim-accel-states <N>` and `--sim-accel-steps <S>`, preserving normal Verilator inputs and handing off structured fields to the existing sidecar plan contract. `--sim-accel-shape <NxS>`, target-first registry lookup, terminal print modes, JSON operator plans, resident modes, and dataset-backed flows remain wrapper/shim compatibility. The next task is review; this definition adds no Verilator source patch, parser implementation, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser boundary review: `config/scaling_gates/review_verilator_native_option_parser_boundary_gate.json` accepts the parser-only/no-execution definition and advances to `run_verilator_native_option_parser_boundary_dry_run_gate`. The review records the weakest point explicitly: this repository still has no Verilator source tree or parser patch, and the parser boundary does not infer coverage manifests, host-probe metadata, source closure, state paths, or report paths. Those remain sidecar handoff-contract fields, not parser discoveries.

Verilator native option parser boundary dry-run result: `config/scaling_gates/verilator_native_option_parser_boundary_dry_run_result_gate.json` records 12 non-executing preview/rejection commands and advances to `review_verilator_native_option_parser_boundary_dry_run_gate`. Ready previews for `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` expose `64x1`, the expanded future Verilator spelling, generated report paths as non-canonical handoff fields, and `coverage_output_equivalence`. Missing shape halves, mixed shape spelling, and non-positive counts reject through the shared mapper; unknown accelerator names currently reject at argparse choices. Resident and dataset-backed flows remain not-ready for direct native-parser handoff.

Verilator native option parser boundary dry-run review: `config/scaling_gates/review_verilator_native_option_parser_boundary_dry_run_gate.json` accepts the 12-command non-executing result and advances to `define_verilator_native_option_parser_stub_boundary_gate`. The caveat is now part of the next task: unknown accelerator validation must be assigned to the native parser, shared mapper, or compatibility wrapper layer before any native parser support claim.

Verilator native option parser stub boundary definition: `config/scaling_gates/define_verilator_native_option_parser_stub_boundary_gate.json` assigns canonical unknown-accelerator validation to the parser-stub validation contract and treats current argparse choices as wrapper compatibility only. It defines the structured handoff fields for a future non-executing parser-stub fixture while keeping target registry lookup, source closure metadata, coverage manifest selection, host-probe metadata, state materialization, execution, and comparison on the sidecar side. The next task is review; this definition adds no Verilator source patch, parser implementation, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser stub boundary review: `config/scaling_gates/review_verilator_native_option_parser_stub_boundary_gate.json` accepts the boundary narrowly and advances to `define_verilator_native_option_parser_stub_fixture_gate`. The review keeps the weak point explicit: this remains contract-only, the repository has no Verilator source tree or parser patch, and current unknown-accelerator rejection is still observable through wrapper argparse choices. The next gate must define a non-executing fixture that makes the parser-stub validation and handoff contract testable before any native parser support claim.

Verilator native option parser stub fixture definition: `config/scaling_gates/define_verilator_native_option_parser_stub_fixture_gate.json` defines the non-executing importable fixture contract and advances to `review_verilator_native_option_parser_stub_fixture_gate`. The fixture must accept `sidecar-gpu` `64x1`, reject unknown accelerators through parser-stub validation rather than wrapper argparse choices, reject missing/non-positive shape inputs, reject compact `--sim-accel-shape` as wrapper compatibility outside the native minimum, preserve ordinary Verilator build arguments, and serialize parser-only handoff fields. This definition adds no helper implementation, Verilator source patch, parser implementation, execution, measurement, runtime/ABI change, arbitrary filelist support, dependency inference, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser stub fixture review: `config/scaling_gates/review_verilator_native_option_parser_stub_fixture_gate.json` accepts the fixture contract and advances to `implement_verilator_native_option_parser_stub_fixture_gate`. The implementation must be an importable non-executing helper rather than a public CLI, must reject unknown accelerators through parser-stub validation with the unsupported value preserved, and must keep target registry lookup, source closure inference, coverage manifest selection, host-probe metadata, execution, compare, and allocation out of scope.

Verilator native option parser stub fixture implementation: `config/scaling_gates/implement_verilator_native_option_parser_stub_fixture_gate.json` records `src/tools/verilator_native_option_parser_stub_fixture.py` and `parse_verilator_native_option_stub`. The helper accepts the expanded native minimum `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1`, rejects unknown accelerators through parser-stub validation while preserving the unsupported value, rejects compact and mixed compact shape spelling outside the native parser-stub minimum, preserves ordinary Verilator build arguments, and serializes the 18 parser-only handoff fields with `coverage_output_equivalence`. The next task is review; this implementation adds no public CLI, Verilator source patch, native parser, execution, measurement, runtime/ABI change, source-closure inference, arbitrary RTL/filelist support, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser stub fixture implementation review: `config/scaling_gates/review_verilator_native_option_parser_stub_fixture_implementation_gate.json` accepts the helper narrowly and advances to `define_verilator_native_option_parser_source_patch_boundary_gate`. The review keeps the weak point explicit: the helper is still a Python fixture rather than real Verilator parser integration, and shallow source/filelist classification is acceptable only because ordinary Verilator args are preserved and `source_boundary_status` remains `preserved_only_not_resolved`. The next gate must define the smallest real source/overlay patch boundary before any native parser implementation claim.

Verilator native option parser source-patch boundary definition: `config/scaling_gates/define_verilator_native_option_parser_source_patch_boundary_gate.json` defines the first source-patch representation as a future repo-owned overlay patch descriptor under `overlays/verilator/patches/`, not vendored Verilator source or a new Verilator submodule. The native minimum remains expanded-only `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`, validation errors map to the accepted parser-stub contract, and the parser-only handoff preserves ordinary Verilator inputs while leaving source closure inference, filelist expansion, coverage manifest selection, execution, comparison, and automatic allocation to later sidecar layers. The next task is review; this definition adds no patch file, native parser implementation, execution, measurement, runtime/ABI change, arbitrary RTL/filelist support, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser source-patch boundary review: `config/scaling_gates/review_verilator_native_option_parser_source_patch_boundary_gate.json` accepts the overlay descriptor boundary narrowly and advances to `define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate`. The weak point is explicit: no descriptor schema, no patch file, no pinned upstream Verilator ref, no touched-file allowlist, and no reproducible `git apply --check` command exist yet. The next gate must define those before any native parser source patch implementation claim; this review adds no execution, measurement, runtime/ABI change, arbitrary RTL/filelist support, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser overlay patch descriptor/apply-check definition: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json` defines the future descriptor path as `overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json`, the future patch file as `overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch`, and pins upstream Verilator `v5.048` at `d0aa828c217410fffc73d92077b6f4f54830357c`. The apply-check command is defined as `git -C "$VERILATOR_CHECKOUT" apply --check "$REPO_ROOT/overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch"` with expected exit code `0`. The first source touch candidates are `src/V3Options.h` and `src/V3Options.cpp`; shared option-parser mechanics, `src/VlcMain.cpp`, upstream docs/tests, compact shape spelling, and estimate-efficiency remain deferred unless review expands scope. This definition adds no descriptor file, patch file, native parser implementation, execution, measurement, runtime/ABI change, arbitrary RTL/filelist support, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser overlay patch descriptor/apply-check review: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json` accepts the boundary narrowly and advances to `implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate`. The accepted implementation payload is limited to `overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.json` and `overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch` plus source-of-truth/test/doc alignment. The pinned Verilator commit is treated as the peeled commit for release tag `v5.048`; HEAD remains informational only. This review adds no descriptor file, patch file, native parser implementation, execution, measurement, runtime/ABI change, arbitrary RTL/filelist support, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser overlay patch descriptor/apply-check implementation: `config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_descriptor_apply_check_gate.json` adds the accepted descriptor and patch under `overlays/verilator/patches/`. The descriptor validates with `python3 -m json.tool`, and the patch applies with `git apply --check` against Verilator `v5.048` peeled commit `d0aa828c217410fffc73d92077b6f4f54830357c`. The patch touches only upstream `src/V3Options.h` and `src/V3Options.cpp`; the new options are undocumented parse/store/validate-only registrations, leaving docs, upstream `test_regress`, `V3OptionParser.*`, `VlcMain.cpp`, compact shape, estimate-efficiency, execution, and runtime handoff out of scope. This implementation adds no native parser support claim, Verilator build/regression result, execution, measurement, runtime/ABI change, arbitrary RTL/filelist support, automatic allocation, GEM comparison, production-serving claim, or raw full-state equality claim.

Verilator native option parser overlay patch build-only validation run: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_build_only_validation_gate.json` records the external checkout/apply/build attempt. Descriptor validation and `git apply --check` passed, the patch was applied, `autoconf` and `configure` were reached with a checkout-local `VERILATOR_INSTALL` default, and `make verilator_bin` was reached but failed with exit code `2`. The failure is classified as `patch_compile_link_failure` because the current patch inserts `m_simAccel*` fields and accessors after `#endif  // guard` in `V3Options.h`. The next task is to define the smallest compile-fix gate; this run still adds no parser behavior, upstream regression, execution, measurement, runtime/ABI, arbitrary RTL/filelist, automatic allocation, GEM, production-serving, or raw full-state equality claim.

Verilator native option parser overlay patch compile-fix definition: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_compile_fix_gate.json` keeps the existing descriptor/patch path and defines an in-place contextual patch repair. The definition requires fields/accessors to stay inside the `V3Options` class, places count fields after `m_verilateJobs`, the accelerator string after `m_protectKey`, count accessors after `verilateJobs()`, and the string accessor after `protectKeyDefaulted()`. It also requires `V3Options.cpp` notify/parser/registration hunks to land inside `notify()` and `parseOptsList()` rather than after `optimize()`. The next task is review; this definition still changes no patch, runs no build, and adds no parser behavior, upstream regression, execution, measurement, runtime/ABI, arbitrary RTL/filelist, automatic allocation, GEM, production-serving, or raw full-state equality claim.

Verilator native option parser overlay patch compile-fix review: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_gate.json` accepts the in-place contextual patch repair boundary and advances to implementation. The review keeps the caveat explicit: the `V3Options.cpp` helper anchor may use `};` only with the recorded `callStrSetter` prior context and `parseOptsList()` bounds; a bare `};` anchor is not accepted. The next gate may update the existing patch/descriptor plus source-of-truth/test/doc alignment and must run or record descriptor validation, clean-checkout apply-check, patch apply, and post-apply location sanity before any build-success or parser-behavior claim.

Verilator native option parser overlay patch compile-fix implementation: `config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_compile_fix_gate.json` updates the existing descriptor and patch in place. The descriptor validates, the contextual patch passes clean-checkout `git apply --check` against Verilator `v5.048` peeled commit `d0aa828c217410fffc73d92077b6f4f54830357c`, actual apply succeeds, and post-apply sanity confirms the `V3Options.h` fields/accessors are inside the class before the header guard end while the `V3Options.cpp` additions are inside `notify()` and `parseOptsList()`. `make verilator_bin` is deferred to the next fail-fast build-only rerun gate, so this implementation still adds no build-success, parser-behavior, upstream regression, execution, measurement, runtime/ABI, arbitrary RTL/filelist, automatic allocation, GEM, production-serving, or raw full-state equality claim.

Verilator native option parser overlay patch compile-fix build-only validation: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json` records descriptor validation, clean-checkout `git apply --check`, actual patch apply, `autoconf`, `configure`, and `make -j 28 verilator_bin` all reaching exit code `0` with a checkout-local generated `VERILATOR_INSTALL` default. This is compile/link compatibility evidence for the repaired patch only; parser behavior, upstream regression, sidecar execution, measurement, runtime/ABI, arbitrary RTL/filelist, automatic allocation, GEM, production-serving, and raw full-state equality remain non-claims.

Verilator native option parser overlay patch compile-fix build-only validation review: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_compile_fix_build_only_validation_gate.json` accepts the build-only result as compile/link compatibility for the repaired patch against pinned Verilator `v5.048`. That review selected defining parser-behavior checks through the built binary or a reproduced equivalent build. This review still adds no parser behavior validation, sidecar execution, measurement, runtime/ABI, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, or upstream landing claim.

Verilator native option parser overlay patch parser-behavior definition: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json` defines the smallest built-binary lint-only smoke boundary: accept expanded `64x1` and `1x64` spellings, reject unknown accelerator, missing accelerator/shape halves, and zero counts, and reuse or regenerate the prior build artifact only as generated evidence. This definition explicitly defers strict `std::atoi` suffix hardening and still adds no parser execution, sidecar execution, measurement, runtime/ABI, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, or upstream landing claim.

Verilator native option parser overlay patch parser-behavior review: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json` accepts that definition as a narrow parser-only built-binary smoke boundary and advances to the run gate. The review permits reusing the generated `verilator_bin` only with recorded provenance, or regenerating it from the build-run gate commands; it still adds no parser behavior result, native parser support, sidecar execution, measurement, runtime/ABI, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, or upstream landing claim.

Verilator native option parser overlay patch parser-behavior run: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_behavior_gate.json` records the reused generated `verilator_bin`, `VERILATOR_ROOT` set to the generated checkout root, a generated trivial RTL input, two positive expanded option cases exiting `0`, and six required rejection cases exiting `1` with expected diagnostics. This is a scoped parser-only smoke result; strict `std::atoi` suffix handling, negative counts, sidecar handoff, RTL simulation, timing, coverage-output equivalence, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, and upstream landing remain non-claims.

Verilator native option parser overlay patch parser-behavior run review: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_run_gate.json` accepts only the scoped parser-only smoke result and the recorded `VERILATOR_ROOT` mechanical adjustment for a reused generated build artifact. The next gate is defining parser integer hardening for negative counts and `std::atoi` suffix inputs; sidecar handoff, RTL simulation, timing, coverage-output equivalence, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, and upstream landing remain non-claims.

Verilator native option parser overlay patch parser-integer hardening definition: `config/scaling_gates/define_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` selects separate-token negative count cases and non-numeric suffix cases as the next strict-integer boundary. The definition records that dash-prefixed negative values may expose tokenizer behavior, while suffix cases such as `64abc` and `1abc` require replacing the current `std::atoi`-style prefix parsing before any strict integer claim. This adds no patch change, hardening result, sidecar handoff, RTL simulation, timing, coverage-output equivalence, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, or upstream landing claim.

Verilator native option parser overlay patch parser-integer hardening review: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` accepts the hardening boundary and selects an in-place update of `overlays/verilator/patches/verilator_native_option_parser_sidecar_gpu_v5_048.patch`. The next implementation may touch the existing descriptor/patch and likely upstream `src/V3Options.cpp` patch hunk only; it still adds no hardening result through a built Verilator binary, sidecar handoff, RTL simulation, timing, coverage-output equivalence, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, or upstream landing claim.

Verilator native option parser overlay patch parser-integer hardening implementation: `config/scaling_gates/implement_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` records the in-place descriptor/patch update. The `parsePositiveSimAccelCount` helper now uses manual full-token decimal digit validation and no longer uses `std::atoi` for sim-accel count parsing; descriptor JSON validation, clean-checkout `git apply --check`, actual patch apply, and diff/location sanity all exit `0`.

Verilator native option parser overlay patch parser-integer hardening run: `config/scaling_gates/run_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json` records a clean-checkout rebuild of the updated overlay patch, `make -j 28 verilator_bin` exiting `0`, two positive expanded parser cases exiting `0`, and four hardening rejection cases exiting `1` with expected diagnostics. The suffix cases prove `std::atoi` prefix behavior is rejected, and the separate-token negative cases reached strict value validation in this run. This permits only scoped parser-only hardening evidence for `--sim-accel-states` and `--sim-accel-steps`; sidecar handoff, RTL simulation, timing, coverage-output equivalence, arbitrary RTL/filelist support, automatic allocation, GEM, production-serving, and upstream landing remain non-claims. The next gate is reviewing this run.

Verilator native option parser overlay patch parser-integer hardening run review: `config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_run_gate.json` accepts only the scoped strict count-token result for the listed parser-only smoke cases. It accepts the observed separate-token negative cases as helper value-validation evidence for this run, but still rejects broad parser, sidecar handoff, RTL simulation, timing, arbitrary RTL/filelist, automatic allocation, upstream regression, or upstream landing claims. The selected next gate defined the native parser-to-sidecar adapter handoff boundary.

Public benchmark pack externalization readiness state: `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json` records the minimum review surfaces, smoke commands, release checks, and evidence policy for handing the refreshed pack to an external reader. The status is `ready_for_external_review`; this is a packaging/readiness audit only, not a new measurement result or stronger performance claim.

Next measurement goal selection state: `config/scaling_gates/next_measurement_goal_selection_after_public_pack_readiness_gate.json` selects `persistent_resident_state_abi_repeat_median` after public-pack readiness. The first required gate is `persistent_resident_state_abi_repeat_median_measurement_gate`, which should reuse the existing persistent resident ABI entrypoint without changing runtime ABI or adding a new workload. Paged attention/KV-cache scale-up, additional prefill/decode work, and publish-only work remain deferred; this selection does not claim production paged attention, production KV-cache memory hierarchy, model-level Transformer inference, or a new timing result yet.

Persistent resident state ABI repeat-median state: `config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3`. The generated summary is `reports/persistent_resident_state_abi_repeat_median_summary.json`; all three samples pass coverage-output equivalence with mismatch count `0`. Median hybrid wall is `4.965 ms`, median GPU kernel total is `4.934624 ms`, and median hybrid wall per final state-step is `0.001212158203125 ms`. The gate reuses the existing persistent resident ABI measurement path and forbids runtime/ABI changes or new workload claims.

Next goal after persistent resident repeat-median: `config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json` selects `public_pack_refresh_after_persistent_resident_repeat_median`. The selected first gate is `public_results_packaging_refresh_after_persistent_resident_repeat_median_gate`; paged attention/KV-cache scale-up remains the strongest later measurement candidate, but it is deferred until the new repeat-median evidence is closed into the public pack. This is selection-only packaging/review work, not a new measurement, runtime/ABI change, or production serving claim.

Public results repeat-median refresh state: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json` defines the source-of-truth refresh after the persistent resident state ABI repeat-median result. It keeps `docs/results.md`, README, status, roadmap, and selection aligned around `reports/persistent_resident_state_abi_repeat_median_summary.json` as generated evidence only. The next_task returns to `select_next_measurement_after_config_generation_validation_shape_breadth_public_pack_refresh`.

Public benchmark pack externalization completion state: `config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json` closes the externalization boundary after the repeat-median refresh. It is completion-only packaging work: no new measurement, no runtime/ABI change, and no stronger production-serving claim. The next_task is `select_next_measurement_after_public_benchmark_pack_externalization`.

Next measurement after public benchmark pack externalization: `config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json` selects `paged_attention_kv_cache_scale_up`. The first required gate is `define_paged_attention_kv_cache_scale_up_measurement_gate`, which should start from tracked paged-attention KV-score and paged KV-cache evidence, preserve `coverage_output_equivalence`, and avoid importing unreviewed candidate overlays or changing runtime/ABI behavior.

Paged-attention/KV-cache scale-up measurement result: `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json` records that all four planned measurement commands exited with code `0` and passed `coverage_output_equivalence` with mismatch count `0`. The measured set is limited to tracked `pulp_paged_kv_cache_large` and `pulp_paged_attention_kv_score` templates at `256x1`, `1x64`, `64x1`, and `1x64`; the generated compare reports are `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`, and `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`. This is correctness evidence only: raw full-state equality is not required or claimed, reports/artifacts remain generated evidence rather than source of truth, and timing/speedup claims require a separate timing summary gate.

Paged-attention/KV-cache scale-up measurement review: `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json` closes the correctness review and selects `define_paged_attention_kv_cache_timing_summary_gate` next. The reason is that coverage-output equivalence is complete for the four planned shapes, while compare reports alone do not provide timing fields or justify a speedup claim. The next gate should summarize or regenerate timing for the same tracked measurement set without importing untracked candidate overlays, changing runtime/ABI behavior, or broadening production LLM-serving claims.

Paged-attention/KV-cache timing summary: `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` records single-run timing for the same four reviewed shapes. `pulp_paged_kv_cache_large 256x1` records CPU `599.228 ms`, hybrid wall `1.266 ms`, and CPU/hybrid wall ratio `473.32385466034754`; `pulp_paged_kv_cache_large 1x64` records CPU `2.93242 ms`, hybrid wall `1.907 ms`, and ratio `1.5377136864184584`; `pulp_paged_attention_kv_score 64x1` records CPU `137.923 ms`, hybrid wall `1.666 ms`, and ratio `82.78691476590637`; `pulp_paged_attention_kv_score 1x64` records CPU `2.69249 ms`, hybrid wall `1.404 ms`, and ratio `1.9177279202279203`. This preserves the trend that state-parallel shapes are much more favorable than single-state repeated-step shapes, but it is single-run generated evidence only, not repeat-median or production LLM-serving throughput. The next_task is `review_paged_attention_kv_cache_timing_summary`.

Paged-attention/KV-cache timing summary review: `config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json` closes the single-run timing review and selects `define_public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate` next. Repeat-median timing, resident optimization, and new paged-attention or quantized KV workloads remain deferred because they would widen the current boundary. The selected next step is publication-only packaging around the reviewed correctness and timing summary evidence.

Paged-attention/KV-cache public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json` defines the source-of-truth refresh after the reviewed four-shape correctness and single-run timing summary. It keeps `docs/results.md`, README, status, roadmap, and selection aligned while keeping reports and artifacts generated evidence only. This is documentation refresh only: no new measurement, no runtime or ABI change, no new workload, no repeat-median timing claim, and no production LLM-serving throughput claim. The next_task returns to `select_next_measurement_after_config_generation_validation_shape_breadth_public_pack_refresh`.

Public benchmark pack externalization completion after paged-attention/KV-cache timing refresh: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json` closes the publication boundary after the paged-attention/KV-cache timing summary refresh. It is completion-only packaging work: no new measurement, no runtime/ABI change, and no stronger production-serving claim. The next_task is `select_next_measurement_after_paged_attention_kv_cache_timing_summary_public_pack_refresh`.

Next measurement after paged-attention/KV-cache timing refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json` selects `paged_attention_kv_cache_repeat_median_timing` next. The reason is that correctness and single-run timing are now reviewed and public-packaged for the four existing paged-attention/KV-cache shapes, while the weakest remaining evidence gap is timing stability. The first required gate is `define_paged_attention_kv_cache_repeat_median_timing_gate`; it should reuse the existing four-shape set, preserve `coverage_output_equivalence`, and avoid runtime/ABI changes, new workloads, unreviewed candidate overlays, and production serving claims.

Paged-attention/KV-cache repeat-median timing boundary: `config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json` defines the repeat-median measurement boundary for the same four reviewed shapes and requires repeat count `3`, coverage-output equivalence, and median CPU, hybrid wall, and GPU-kernel timing fields. The gate also records a workflow gap: the existing `python3 src/tools/run_results_reproduction.py --repeat-median 3` representative flow includes only `pulp_paged_attention_kv_score 64x1` from this set, so the next task is `add_paged_attention_kv_cache_repeat_median_workflow`. This is definition-only and does not run a new measurement or change runtime, ABI, workloads, or overlays.

Paged-attention/KV-cache repeat-median workflow: `config/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json` adds the public dry-run command `python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3 --dry-run`. It expands all four reviewed shapes with three uniquely named samples per shape, preserves `coverage_output_equivalence`, and does not write generated evidence in dry-run mode. The next task is `run_paged_attention_kv_cache_repeat_median_timing_gate`.

Paged-attention/KV-cache repeat-median measurement: `config/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3`. The generated summary is `reports/paged_attention_kv_cache_repeat_median_summary.json`; all four workloads pass coverage-output equivalence with mismatch count `0`. Median results are: `pulp_paged_kv_cache_large 256x1` CPU `613.931 ms`, hybrid wall `1.259 ms`, ratio `487.6338363780779x`; `pulp_paged_kv_cache_large 1x64` CPU `3.60037 ms`, hybrid wall `1.823 ms`, ratio `1.9749698299506309x`; `pulp_paged_attention_kv_score 64x1` CPU `145.936 ms`, hybrid wall `1.068 ms`, ratio `136.6441947565543x`; `pulp_paged_attention_kv_score 1x64` CPU `3.16693 ms`, hybrid wall `1.601 ms`, ratio `1.978094940662086x`. The gate forbids runtime/ABI changes, new workload claims, and treating reports/artifacts as source of truth. The next task is `review_paged_attention_kv_cache_repeat_median_timing`.

Paged-attention/KV-cache repeat-median review: `config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json` accepts the scoped repeat-count `3` result for public-pack use. The reviewed trend is unchanged: state-parallel shapes have median CPU/hybrid wall ratios from `136.6441947565543x` to `487.6338363780779x`, while single-state repeated-step shapes remain around `1.9749698299506309x` to `1.978094940662086x`. The weak points are explicit: repeat-count `3` is not paper-grade statistics, these are scoped RTL harnesses rather than production paged attention or full LLM serving, and generated reports remain evidence rather than source of truth. The next task is `define_public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median`.

Paged-attention/KV-cache repeat-median public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json` defines the source-of-truth refresh after the reviewed repeat-median result. It keeps `docs/results.md`, README, status, roadmap, and selection aligned around `reports/paged_attention_kv_cache_repeat_median_summary.json` as generated evidence only. This is documentation refresh only: no new measurement, no runtime or ABI change, no new workload, no raw full-state equality claim, and no production LLM-serving throughput claim. The next task returns to `select_next_measurement_after_config_generation_validation_shape_breadth_public_pack_refresh`.

Public benchmark pack externalization completion after paged-attention/KV-cache repeat-median refresh: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json` closes the publication boundary after the repeat-median refresh. It is completion-only packaging work: no new measurement, no runtime/ABI change, and no stronger production-serving claim. The next task is `select_next_measurement_after_paged_attention_kv_cache_repeat_median_public_pack_refresh`.

Next measurement after paged-attention/KV-cache repeat-median public-pack refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate.json` selects `config_generation_validation_breadth`. The reason is that repeat-median evidence is already closed into the public pack, while the remaining weakest point is validation breadth for generated config and generic host-probe metadata. The next task is `define_config_generation_validation_breadth_gate`; this is selection-only, not a new measurement, runtime/ABI change, workload promotion, or production LLM-serving claim.

Config-generation validation breadth state: `config/scaling_gates/config_generation_validation_breadth_gate.json` defines the tracked target set for validating generated config and generic host-probe metadata breadth. The selected templates are `nvdla_cmac_core_mac`, `pulp_ita_dotp`, `pulp_ita_softmax_top`, `pulp_ita_mha`, `pulp_paged_attention_kv_score`, and `pulp_paged_kv_cache_large`; MobileViT, Ibex, quantized KV-cache, and untracked candidate overlays remain deferred. This is definition-only and does not run a new measurement or change runtime/ABI behavior. The next task is `run_config_generation_validation_breadth_dry_run_gate`.

Config-generation validation breadth dry-run state: `config/scaling_gates/config_generation_validation_breadth_dry_run_gate.json` records that the six tracked `1x1 --dry-run` command plans exited with code `0`, emitted `src/tools/build_host_probe.py`, and preserved `coverage_output_equivalence` compare plans without Makefile host-probe targets. This is dry-run-only command-plan evidence, not a fresh build/run/compare measurement. The next task is `review_config_generation_validation_breadth_dry_run_gate`.

Config-generation validation breadth dry-run review: `config/scaling_gates/config_generation_validation_breadth_dry_run_review_gate.json` accepts the six-template dry-run command-plan boundary and explicitly records the remaining gap: no fresh Verilator build, generic host-probe compile, hybrid run, or CPU-vs-hybrid compare evidence has been produced by this gate. The next task is `define_config_generation_validation_breadth_execution_gate`.

Config-generation validation breadth execution boundary: `config/scaling_gates/config_generation_validation_breadth_execution_gate.json` defines the next real execution set as all six tracked `1x1` build/run/compare commands from the dry-run plan. This is definition-only: it does not claim fresh build success, CPU-vs-hybrid equivalence, timing, runtime/ABI changes, or workload promotion. The next task is `run_config_generation_validation_breadth_execution_gate`.

Config-generation validation breadth execution result: `config/scaling_gates/config_generation_validation_breadth_execution_result_gate.json` records the completed non-dry-run `1x1` execution for all six tracked templates: `nvdla_cmac_core_mac`, `pulp_ita_dotp`, `pulp_ita_softmax_top`, `pulp_ita_mha`, `pulp_paged_attention_kv_score`, and `pulp_paged_kv_cache_large`. All six commands completed Verilator build, generic host-probe build through `src/tools/build_host_probe.py`, GPU cubin build, CPU run, hybrid run, and CPU-vs-hybrid compare. The selected policy is `coverage_output_equivalence`; every report passed with mismatch count `0` over `29` words / `116` bytes. Raw full-state equality remains false with `32` Verilator-internal-only mismatch bytes per report, so this is scoped output-equivalence evidence, not raw state equality, timing, speedup, or production LLM-serving evidence.

Config-generation validation breadth execution review: `config/scaling_gates/config_generation_validation_breadth_execution_review_gate.json` accepts the six-template execution boundary and selects `define_public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate` next. The next step is packaging/source-of-truth alignment, not another measurement or runtime/ABI change.

Config-generation validation breadth public refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate.json` keeps the six-template execution result in the public/source-of-truth pack without adding timing, speedup, raw-state, runtime/ABI, or production-serving claims. `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate.json` closes that packaging boundary, and `config/scaling_gates/next_measurement_selection_after_config_generation_validation_breadth_public_pack_refresh_gate.json` selects `define_config_generation_validation_shape_breadth_gate` next. The reason is that `1x1` breadth now passes, while the next empirical gap is shape breadth for the same generated-config path.

Config-generation validation shape breadth definition: `config/scaling_gates/config_generation_validation_shape_breadth_gate.json` defines the next dry-run boundary as all six tracked templates at `32x1` and `1x32`. This is definition-only; it does not run Verilator, build host probes, produce compare reports, or claim correctness for those shapes. The next task is `run_config_generation_validation_shape_breadth_dry_run_gate`.

Config-generation validation shape breadth dry-run: `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_gate.json` records that all 12 `--dry-run` command plans exited with code `0`, emitted `src/tools/build_host_probe.py`, avoided Makefile host-probe targets, and preserved `coverage_output_equivalence` compare plans. `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_review_gate.json` accepts the command-plan boundary and selects `define_config_generation_validation_shape_breadth_execution_gate` next. This is still dry-run-only evidence, not Verilator build success, host-probe compile success, hybrid execution, or CPU-vs-hybrid coverage-output equivalence.

Config-generation validation shape breadth execution boundary: `config/scaling_gates/config_generation_validation_shape_breadth_execution_gate.json` defines the next real execution set as all 12 reviewed `32x1` / `1x32` build/run/compare commands across the six tracked templates. This is definition-only: it does not claim fresh build success, CPU-vs-hybrid equivalence, timing, runtime/ABI changes, or workload promotion. The next task is `run_config_generation_validation_shape_breadth_execution_gate`.

Config-generation validation shape breadth execution result: `config/scaling_gates/config_generation_validation_shape_breadth_execution_result_gate.json` records the completed non-dry-run `32x1` / `1x32` execution for all six tracked templates. All 12 commands completed Verilator build, generic host-probe build through `src/tools/build_host_probe.py`, GPU cubin build, CPU run, hybrid run, and CPU-vs-hybrid compare. The selected policy is `coverage_output_equivalence`; every report passed with mismatch count `0` over `29` words / `116` bytes per state. Raw full-state equality remains false for all 12 reports, and some `32x1` reports include raw mismatch bytes classified as `other`, so this is scoped coverage-output evidence, not raw state equality, timing, speedup, or production LLM-serving evidence.

Config-generation validation shape breadth execution review: `config/scaling_gates/config_generation_validation_shape_breadth_execution_review_gate.json` accepts the 12-command execution boundary and selects `define_public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate` next. The next step is packaging/source-of-truth alignment, not another measurement or runtime/ABI change.

Config-generation validation shape breadth public refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate.json` keeps the 12-command shape-breadth execution result in the public/source-of-truth pack without adding timing, speedup, raw-state, runtime/ABI, or production-serving claims. The next task is `public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution`.

Config-generation validation shape breadth public-pack completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution_gate.json` closes the publication boundary for the 12-command shape-breadth execution. `config/scaling_gates/next_measurement_selection_after_config_generation_validation_shape_breadth_public_pack_refresh_gate.json` selects `define_config_generation_validation_additional_targets_gate` next because the six-template path now passes both shape checks and the narrower remaining validation gap is additional tracked target breadth, not timing, runtime tuning, or workload import.

Config-generation validation additional targets definition: `config/scaling_gates/config_generation_validation_additional_targets_gate.json` selects `nvdla_cmac_a2cacc`, `prim_count`, and `prim_secded_inv_39_32_enc` as the first additional tracked target set at `1x1`.

Config-generation validation additional targets dry-run review: `config/scaling_gates/config_generation_validation_additional_targets_dry_run_gate.json` records that all three `1x1 --dry-run` command plans exited zero, use `src/tools/build_host_probe.py`, avoid Makefile host-probe targets, and preserve `coverage_output_equivalence` compare plans. `config/scaling_gates/config_generation_validation_additional_targets_dry_run_review_gate.json` accepts the command-plan boundary and selects `define_config_generation_validation_additional_targets_execution_gate` next. This is command-plan evidence only; it does not run Verilator, build host probes, produce compare reports, or claim correctness for those targets in the generated-config path.

Config-generation validation additional targets execution definition: `config/scaling_gates/config_generation_validation_additional_targets_execution_gate.json` fixes the next real build/run/compare boundary as all three reviewed `1x1` commands and selects `run_config_generation_validation_additional_targets_execution_gate`. This definition does not itself run Verilator, build host probes, produce compare reports, or claim correctness.

Config-generation validation additional targets execution review: `config/scaling_gates/config_generation_validation_additional_targets_execution_result_gate.json` records that `nvdla_cmac_a2cacc`, `prim_count`, and `prim_secded_inv_39_32_enc` all completed `1x1` non-dry-run build/run/compare through the generated-config path. All three selected `coverage_output_equivalence` policies passed with mismatch count `0` over `29` words / `116` bytes per state. Raw full-state equality remains false for all three reports, so the accepted claim remains scoped output equivalence, not raw byte equality. `config/scaling_gates/config_generation_validation_additional_targets_execution_review_gate.json` accepts this result and selects `define_public_results_packaging_refresh_after_config_generation_validation_additional_targets_execution_gate` next.

Config-generation validation additional targets public refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_additional_targets_execution_gate.json` admits the three-command additional-target result into the public/source-of-truth pack without adding a new measurement, runtime/ABI change, workload import, timing claim, speedup claim, raw-state claim, or production-serving claim. The generated compare reports remain evidence under `reports/`, not source of truth.

Config-generation validation additional targets public-pack completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_additional_targets_execution_gate.json` closes the publication boundary for the three-command additional-target execution. `config/scaling_gates/next_measurement_selection_after_config_generation_validation_additional_targets_public_pack_refresh_gate.json` selects `define_config_generation_validation_followup_gate` next, keeping the next step focused on deciding whether the generated-config validation track needs another scoped target set or should hand off to metadata-invariant review.

Config-generation validation follow-up: `config/scaling_gates/config_generation_validation_followup_gate.json` selects `define_tlul_template_schema_metadata_invariant_review_gate` next. The reason is that generated-config correctness now has six-template breadth, 32x1/1x32 shape breadth, and three additional tracked targets all passing `coverage_output_equivalence`; adding more targets would mostly increase evidence volume while the sharper remaining risk is whether template metadata invariants are explicit enough for Verilator-like GPU-backed operation.

TL-UL/template schema metadata invariant review definition: `config/scaling_gates/tlul_template_schema_metadata_invariant_review_gate.json` fixes the representative metadata review set and required invariants for producing a generic host-probe plus `coverage_output_equivalence` plan from tracked templates. The selected dry-run set covers legacy-normalized TL-UL templates, target-specific clock/reset overrides, explicit primitive metadata, non-default NVDLA clock/reset metadata, full ITA/MHA metadata, and paged KV-cache metadata. This is definition-only, not a build/run/compare result or proof that future templates pass execution.

TL-UL/template schema metadata invariant dry-run review: `config/scaling_gates/tlul_template_schema_metadata_invariant_review_dry_run_gate.json` records that all six representative `1x1 --dry-run` plans exited zero, use `src/tools/build_host_probe.py`, avoid Makefile host-probe targets, and include `coverage_output_equivalence` with coverage-output gate and target arguments. `config/scaling_gates/tlul_template_schema_metadata_invariant_review_dry_run_review_gate.json` accepts this command-plan boundary and selects the execution definition boundary. This is still dry-run-only evidence, not build/run/compare success or new correctness evidence.

TL-UL/template schema metadata invariant execution definition: `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_gate.json` fixes the six representative non-dry-run `1x1` commands for legacy TL-UL, primitive, NVDLA, full ITA/MHA, and paged KV-cache template metadata forms. The next task is to run all six through Verilator build, generic host-probe build, GPU cubin build, CPU/hybrid execution, and `coverage_output_equivalence` compare. This definition is not yet execution evidence, timing evidence, raw full-state equality, or a universal template guarantee.

TL-UL/template schema metadata invariant execution review: `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_result_gate.json` records that all six representative non-dry-run `1x1` commands completed Verilator build, generic host-probe build, GPU cubin build, CPU/hybrid runs, and compare. All six selected `coverage_output_equivalence` and passed with mismatch count `0` over `29` words / `116` bytes per state; normalized final-state equivalence also passed. Raw strict final-state equality remains false for all six reports, so `config/scaling_gates/tlul_template_schema_metadata_invariant_execution_review_gate.json` accepts only scoped coverage-output equivalence and selects public-results packaging refresh next.

TL-UL/template schema metadata invariant public-pack completion: `config/scaling_gates/public_results_packaging_refresh_after_tlul_template_schema_metadata_invariant_execution_gate.json` admits the six-command result into the public/source-of-truth pack without adding a new measurement, timing claim, runtime/ABI change, raw-state claim, or Verilator-native option claim. `config/scaling_gates/public_benchmark_pack_externalization_completion_after_tlul_template_schema_metadata_invariant_execution_gate.json` closes that publication boundary. `config/scaling_gates/next_measurement_selection_after_tlul_template_schema_metadata_invariant_public_pack_refresh_gate.json` selects `define_verilator_like_hybrid_entrypoint_option_surface_gate` next because the sharper remaining gap is usability: defining a small Verilator-like hybrid entrypoint surface, not adding more correctness evidence.

Verilator-like hybrid entrypoint surface definition: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_gate.json` selects `python3 src/tools/run_hybrid_benchmark.py <target> --sim-accel-shape <NxS>` as the first operator-facing bridge toward a future Verilator option. The reproducible input contract remains tracked slice-launch templates, and target names must resolve to those templates before execution. Raw filelist input is deferred until top module, clock/reset, overlay, coverage manifest, acceptance policy, and output report inference are defined without hidden local assumptions. This is definition-only, not Verilator native-option support, arbitrary RTL support, automatic optimal GPU assignment, timing evidence, or a runtime/ABI change.

Verilator-like hybrid entrypoint dry-run review: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_dry_run_gate.json` records six non-executing preview/operator-plan commands for `paged_attention_kv_score --sim-accel-shape 64x1`, including `run_hybrid_benchmark.py` and `verilator_sidecar_shim.py` views. All six exited `0` and preserved the tracked-template handoff, generated compare-report path, synthesized Verilator command preview, and `coverage_output_equivalence` policy. `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_dry_run_review_gate.json` accepts this only as option-surface evidence and selects execution-gate definition next; it does not claim build/run/compare success, timing, speedup, optimal GPU allocation, raw filelist ingestion, or Verilator-native option support.

Verilator-like hybrid entrypoint execution definition: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_gate.json` selects exactly one non-dry-run operator command: `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_sim_accel_64x1.json`. The accepted output is the generated compare report `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json` passing `coverage_output_equivalence` with mismatch count `0`. This is definition-only until executed; it does not add raw filelist ingestion, native Verilator option support, timing/speedup evidence, or optimal GPU allocation.

Verilator-like hybrid entrypoint execution review: `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_result_gate.json` records that the selected non-dry-run operator command exited `0`, resolved through the tracked paged-attention template, and passed `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes per state. Raw strict final-state equality remains false, while normalized final-state equivalence passes. `config/scaling_gates/verilator_like_hybrid_entrypoint_option_surface_execution_review_gate.json` accepts this as scoped operator-surface integration evidence only and selects public-results packaging refresh next.

Verilator-like hybrid entrypoint public-pack completion: `config/scaling_gates/public_results_packaging_refresh_after_verilator_like_hybrid_entrypoint_option_surface_execution_gate.json` admits the one-command operator-surface execution result into the public/source-of-truth pack as scoped integration evidence. `config/scaling_gates/public_benchmark_pack_externalization_completion_after_verilator_like_hybrid_entrypoint_option_surface_execution_gate.json` closes that publication boundary. `config/scaling_gates/next_measurement_selection_after_verilator_like_hybrid_entrypoint_option_surface_public_pack_refresh_gate.json` selects `define_filelist_to_verilator_like_hybrid_plan_boundary_gate` next because the sharper remaining usability gap is a filelist-facing plan contract, not more timing, native Verilator implementation, or runtime tuning.

Filelist-facing hybrid plan boundary definition: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_gate.json` defines the first filelist-facing contract as repeatable `--source` RTL paths plus explicit `--target`, `--top-module`, optional coverage overlay, and explicit/defaulted clock/reset metadata through `src/tools/gen_hybrid_config.py --dry-run`. The next gate must validate that this produces coverage manifest, slice-template, scaling-gate, host-probe metadata, and `coverage_output_equivalence` planning without writing source-of-truth files. This is plan-only and does not claim arbitrary RTL execution, automatic top/clock/reset inference, optimal GPU allocation, timing, or native Verilator support.

Filelist-facing hybrid plan dry-run review: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_dry_run_gate.json` records one accepted plan-only command using `third_party/ITA/src/ita.sv` plus `overlays/ITA/src/pulp_paged_attention_kv_score_gpu_cov_tb.sv`, and one refusal command with no source or overlay. The accepted command printed coverage manifest, slice-template, and scaling-gate drafts; the refusal command exited `1` with `error: at least one --source or --overlay is required`. `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_dry_run_review_gate.json` accepts this as plan evidence only and selects a materialization-definition gate next.

Filelist-facing hybrid plan materialization definition: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_gate.json` allows exactly three reviewed dry-run payloads to be written as source: `overlays/generated/tests/filelist_paged_attention_kv_score_coverage_regions.json`, `config/slice_launch_templates/filelist_paged_attention_kv_score.json`, and `records/scaling_gates/filelist_paged_attention_kv_score_first_hybrid_benchmark_gate.json`. Existing file overwrite is forbidden. The next gate validates only file creation, JSON validity, host-probe metadata, planned source/overlay paths, and `coverage_output_equivalence`; it still does not claim Verilator build/run/compare success.

Filelist-facing hybrid plan materialization review: `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_result_gate.json` records that the materialization command exited `0` and wrote exactly the three allowed JSON files: the generated coverage manifest, generated slice launch template, and generated scaling gate for `filelist_paged_attention_kv_score`. `config/scaling_gates/filelist_to_verilator_like_hybrid_plan_boundary_materialization_review_gate.json` accepts this as source materialization evidence only and selects `define_filelist_materialized_template_dry_run_gate` next. No Verilator build, host-probe compile, CPU/hybrid run, or compare evidence is claimed.

Filelist materialized template dry-run review: `config/scaling_gates/filelist_materialized_template_dry_run_result_gate.json` records that `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/filelist_paged_attention_kv_score.json --shape 1x1 --dry-run` exited `0` and emitted the expected seven-stage command plan. `config/scaling_gates/filelist_materialized_template_dry_run_review_gate.json` accepts this as command-plan evidence only and selects `define_filelist_materialized_template_execution_gate` next. This is still not Verilator build, host-probe compile, CPU/hybrid run, compare correctness, timing, native Verilator option, arbitrary RTL, or optimal GPU-allocation evidence.

Filelist materialized template execution definition: `config/scaling_gates/filelist_materialized_template_execution_gate.json` selects the matching non-dry-run command, `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/filelist_paged_attention_kv_score.json --shape 1x1`, as the next build/run/compare boundary. Later acceptance requires exit `0` and `coverage_output_equivalence` mismatch count `0` over `29` words / `116` bytes, while raw full-state equality remains non-required and generated reports/artifacts remain non-canonical.

Filelist materialized template execution review: `config/scaling_gates/filelist_materialized_template_execution_result_gate.json` records that the first non-dry-run attempt failed because the generated source list was not compile-complete for `third_party/ITA/src/ita.sv`; the template was repaired by adding the existing PULP ITA/common_cells source closure. The repaired command completed build/run/compare and `reports/filelist_paged_attention_kv_score_cpu_vs_hybrid_1x1_coverage_output_compare.json` passed `coverage_output_equivalence` with mismatch count `0` over `29` words / `116` bytes. Raw strict final-state equality remains false with Verilator-internal-only mismatches. `config/scaling_gates/filelist_materialized_template_execution_review_gate.json` accepts this only as scoped materialized-template execution evidence and selects public-pack refresh next.

Filelist materialized template public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_result_gate.json` records that `docs/results.md`, `src/tools/results_reproduction_manifest.py`, and `src/tools/results_reproduction_manifest_sources.py` now include the scoped filelist plan/materialization/dry-run/execution gate chain, the generated filelist template and coverage manifest, the generator helper sources, and the optional compare report. `config/scaling_gates/public_results_packaging_refresh_after_filelist_materialized_template_execution_review_gate.json` accepts this refresh and selects the public benchmark pack completion boundary next; no new measurement, timing, speedup, arbitrary RTL, native Verilator option, or optimal GPU-allocation claim is added.

Filelist materialized template public-pack completion and next selection: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_materialized_template_execution_gate.json` closes the externalization boundary after the scoped filelist materialized-template execution result. `config/scaling_gates/next_measurement_selection_after_filelist_materialized_template_public_pack_refresh_gate.json` selects `define_filelist_source_closure_dependency_policy_gate` next because the first non-dry-run attempt exposed an incomplete generated source list before the template was repaired.

Filelist source-closure dependency policy definition: `config/scaling_gates/filelist_source_closure_dependency_policy_gate.json` defines the next policy boundary after that failure. It requires explicit complete source closure for non-dry-run execution, allows copying a known tracked template source closure, requires dry-run output to expose source-closure status, and keeps arbitrary RTL dependency inference, native Verilator option support, timing, speedup, and optimal GPU allocation outside the claim.

Filelist source-closure dependency policy dry-run review: `config/scaling_gates/filelist_source_closure_dependency_policy_dry_run_result_gate.json` records two dry-run cases. The previously failing `third_party/ITA/src/ita.sv` plus overlay case is marked `source_closure.status=incomplete` with missing `ita_package` and `common_cells` sources; the explicit 29-file ITA/common_cells closure is marked `complete`. `config/scaling_gates/filelist_source_closure_dependency_policy_dry_run_review_gate.json` accepts this metadata-only boundary and selects `define_filelist_source_closure_non_dry_run_refusal_gate` next. This is not arbitrary RTL dependency inference, build/run/compare evidence, timing evidence, native Verilator support, or optimal GPU allocation.

Filelist source-closure non-dry-run refusal review: `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_gate.json`, `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_result_gate.json`, and `config/scaling_gates/filelist_source_closure_non_dry_run_refusal_review_gate.json` define, implement, and accept the minimal guard. `run_hybrid_template.py` now refuses templates that explicitly declare `source_closure.status` as `incomplete` or `refused` before the first non-dry-run subprocess; dry-run still prints a plan, and missing/unknown source-closure metadata remains risk metadata rather than complete evidence. The next task is public-pack refresh definition for this guard.

Filelist source-closure refusal public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_gate.json`, `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_result_gate.json`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_source_closure_refusal_review_gate.json` add the source-closure policy/dry-run/refusal gate chain plus `tests/contract/test_hybrid_config_template_cli.py` and `tests/contract/test_hybrid_verilator_like_config_generation.py` to the public-pack manifest. This is packaging evidence only; it adds no new execution, timing, speedup, arbitrary RTL dependency inference, native Verilator option, or automatic GPU allocation claim.

Filelist source-closure refusal public-pack completion and next selection: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_source_closure_refusal_gate.json` closes the externalization boundary. `config/scaling_gates/next_measurement_selection_after_filelist_source_closure_refusal_public_pack_refresh_gate.json` selects `define_filelist_known_template_source_closure_copy_gate` because the operator still has to provide long complete source lists manually. The next workstream must remain a reviewed known-template copy boundary, not arbitrary RTL dependency inference.

Filelist known-template source-closure copy dry-run: `config/scaling_gates/filelist_known_template_source_closure_copy_gate.json`, `config/scaling_gates/filelist_known_template_source_closure_copy_dry_run_result_gate.json`, and `config/scaling_gates/filelist_known_template_source_closure_copy_dry_run_review_gate.json` define and accept `gen_hybrid_config.py --source-closure-from-template`. The boundary requires a tracked `config/slice_launch_templates/*.json` reference with `source_closure.status=complete`, copies `source_files` and `source_closure`, records `reference_template` and `source_files_sha256`, and refuses requested `--source` entries absent from the copied closure. This remains dry-run/operator-surface evidence only; materialization and any build/run/compare evidence are separate gates.

Filelist known-template source-closure copy materialization definition: `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_gate.json` defines the next write boundary. It permits only the generated coverage manifest, launch template, and scaling gate paths; requires complete copied source-closure metadata, `reference_template`, and `source_files_sha256`; and keeps default writes from overwriting existing source-of-truth files. The next task is materialization result capture, not execution or timing.

Filelist known-template source-closure copy materialization review: `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_result_gate.json` records the actual materialization of exactly three JSON payloads for `filelist_known_template_paged_attention_kv_score`. `config/scaling_gates/filelist_known_template_source_closure_copy_materialization_review_gate.json` accepts only materialized source evidence: JSON validity, no local absolute paths, complete copied closure, recorded `reference_template`, and recorded `source_files_sha256`. It selects the generated-template dry-run boundary next.

Filelist known-template source-closure copy materialized-template dry-run review: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_gate.json`, `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_result_gate.json`, and `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_dry_run_review_gate.json` define, run, and accept the first command-plan check for `config/slice_launch_templates/filelist_known_template_paged_attention_kv_score.json --shape 1x1 --dry-run`. The plan preserves generic host-probe generation and `coverage_output_equivalence`; it remains command-plan evidence only.

Filelist known-template source-closure copy materialized-template execution review: `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_gate.json`, `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_result_gate.json`, and `config/scaling_gates/filelist_known_template_source_closure_copy_materialized_template_execution_review_gate.json` define, run, and accept the first non-dry-run `1x1` build/run/compare for the materialized copied-closure template. The selected `coverage_output_equivalence` policy passed with mismatch count `0` over `29` words / `116` bytes. Raw strict final-state equality remains false and timing/speedup remain out of scope.

Filelist known-template source-closure copy execution public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_gate.json`, `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_result_gate.json`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_known_template_source_closure_copy_execution_review_gate.json` define, dry-run, and accept the packaging refresh. The public archive dry-run includes the known-template copy gate chain, materialized template, materialized coverage manifest, first benchmark gate, execution gates, and optional compare report. This adds no new execution, timing, speedup, arbitrary dependency inference, native Verilator, raw full-state, or optimal GPU allocation claim.

Filelist known-template source-closure copy execution externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_known_template_source_closure_copy_execution_gate.json` closes the externalized public-pack boundary for the selected copied-closure execution. `config/scaling_gates/next_measurement_selection_after_filelist_known_template_source_closure_copy_execution_public_pack_refresh_gate.json` selects source-closure reference inventory next because the current complete-reference set is narrow and should not be presented as a general solution before inventory/breadth is explicit.

Known-template source-closure reference inventory: `config/scaling_gates/known_template_source_closure_reference_inventory_gate.json`, `config/scaling_gates/known_template_source_closure_reference_inventory_result_gate.json`, and `config/scaling_gates/known_template_source_closure_reference_inventory_review_gate.json` define, run, and accept the tracked template inventory. There are 137 tracked launch templates and only two complete source-closure templates: one legacy paged-attention filelist template without reference/hash metadata and one copied derivative. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_reference_inventory_gate.json` selects independent reference promotion next; breadth validation remains deferred.

Known-template independent source-closure reference promotion definition: `config/scaling_gates/known_template_source_closure_independent_reference_promotion_gate.json` selects `PULP_ITA.pulp_ita_mha` as the first non-paged-attention-copied-lineage promotion candidate. The weak point is explicit: this closure is larger and still in the ITA family, so it must not be treated as arbitrary dependency inference or as proof for every ITA/filelist target. It is still the best first independent reference for the long-term goal because it is not a copied derivative, has an explicit 29-file ITA/common_cells/overlay source list, and already has scoped `1x1`, `32x1`, and `1x32` coverage-output equivalence evidence. This definition does not change the template, run a new measurement, infer arbitrary RTL dependencies, or claim speedup/native Verilator support.

Known-template independent source-closure reference promotion result: `config/scaling_gates/known_template_source_closure_independent_reference_promotion_result_gate.json` records that `config/slice_launch_templates/pulp_ita_mha.json` now declares `source_closure.status=complete` with `provenance=independent_tracked_template_promotion`, `source_file_count=29`, and source-file hash `073d53d91f23bf47eb907188096c21672b36801ed6fd7f8d218130c913322b89`. A `1x1 --dry-run` command plan still exits `0`, so the metadata addition preserves the operator plan. This is not a fresh measurement, timing result, speedup claim, raw full-state equality claim, arbitrary dependency inference, or native Verilator option support.

Known-template independent source-closure reference promotion review: `config/scaling_gates/known_template_source_closure_independent_reference_promotion_review_gate.json` accepts `PULP_ITA.pulp_ita_mha` as the first promoted independent complete source-closure reference. The review keeps the weak points explicit: the closure is specific to the tracked MHA harness, the promotion is metadata-only, and the hash fixes ordered source files without proving dependency inference. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_independent_reference_promotion_review_gate.json` selects `define_known_template_source_closure_copy_breadth_validation_gate` next.

Known-template source-closure copy breadth validation definition: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_gate.json` defines a dry-run-first breadth matrix over two reviewed complete references: the existing paged-attention copied lineage and the independent `PULP_ITA.pulp_ita_mha` reference. It also requires one requested-source-absent refusal case. This definition is intentionally narrow and adds no materialization, execution, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation claim.

Known-template source-closure copy breadth validation dry-run result: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_dry_run_result_gate.json` records that both accepted `gen_hybrid_config.py --dry-run` cases exited `0`, emitted complete copied source-closure metadata with the expected `reference_template` and `source_files_sha256`, preserved `src/tools/build_host_probe.py`, and planned `coverage_output_equivalence`. The requested-source-absent refusal exited `1` with a policy error. This result is dry-run evidence only, not materialization, execution, timing, speedup, arbitrary dependency inference, native Verilator option support, or automatic GPU allocation.

Known-template source-closure copy breadth validation dry-run review: `config/scaling_gates/known_template_source_closure_copy_breadth_validation_dry_run_review_gate.json` accepts the two accepted dry-runs plus one refusal as dry-run policy/breadth evidence only. The review records the remaining weak points: only two reference families are covered, dry-run success does not prove materialized build/run/compare, and the copied closures are not arbitrary target closures. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_validation_dry_run_review_gate.json` selects `define_known_template_source_closure_copy_breadth_materialization_gate` next.

Known-template source-closure copy breadth materialization definition: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_gate.json` permits exactly three new tracked source files for `filelist_known_template_pulp_ita_mha`: generated coverage manifest, launch template, and first benchmark gate. It also requires the already materialized paged-attention copied-lineage outputs to refuse overwrite. The accepted materialized template must preserve complete copied source-closure metadata, `reference_template=config/slice_launch_templates/pulp_ita_mha.json`, source-file hash `073d53d91f23bf47eb907188096c21672b36801ed6fd7f8d218130c913322b89`, and `src/tools/build_host_probe.py`. This definition is not execution, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation evidence.

Known-template source-closure copy breadth materialization result: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_result_gate.json` records that the existing paged-attention copied-lineage materialization refused overwrite with exit `1`, while the MHA-copy materialization wrote exactly three new source files: generated coverage manifest, launch template, and first benchmark gate. The generated MHA-copy template preserves complete copied source-closure metadata, `reference_template=config/slice_launch_templates/pulp_ita_mha.json`, source-file hash `073d53d91f23bf47eb907188096c21672b36801ed6fd7f8d218130c913322b89`, and `src/tools/build_host_probe.py`. No reports or artifacts were required. This is materialized source evidence only, not Verilator build/run/compare, timing, speedup, arbitrary dependency inference, native Verilator option, or optimal GPU allocation evidence.

Known-template source-closure copy breadth materialization review: `config/scaling_gates/known_template_source_closure_copy_breadth_materialization_review_gate.json` accepts the MHA-copy materialized source boundary: exactly three JSON source files, complete copied source-closure metadata, expected reference/hash, no local absolute paths, and paged-attention overwrite refusal. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_materialization_review_gate.json` selects `define_known_template_source_closure_copy_breadth_materialized_template_dry_run_gate` next. This still makes no Verilator build/run/compare, timing, speedup, arbitrary dependency inference, or native option claim.

Known-template source-closure copy breadth materialized-template dry-run definition: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_gate.json` fixes `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json --shape 1x1 --dry-run` as the next command-plan boundary. The accepted plan must use the materialized copied MHA source list, `src/tools/build_host_probe.py`, CPU reference, GPU cubin build, hybrid run, and final `coverage_output_equivalence` compare. This definition remains command-plan scope only and does not run Verilator or claim correctness/timing/speedup.

Known-template source-closure copy breadth materialized-template dry-run result: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_result_gate.json` records exit `0` for the materialized MHA-copy template `1x1 --dry-run`. The observed plan has seven stages, uses the copied MHA source closure and `src/tools/build_host_probe.py`, plans GPU cubin build and hybrid run, and ends with `coverage_output_equivalence`. This remains dry-run command-plan evidence only.

Known-template source-closure copy breadth materialized-template dry-run review: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_dry_run_review_gate.json` accepts the dry-run result, and `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_materialized_template_dry_run_review_gate.json` selects the matching non-dry-run execution-definition gate next. Timing, speedup, arbitrary dependency inference, native Verilator option, and automatic GPU allocation remain non-claims.

Known-template source-closure copy breadth materialized-template execution definition: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_gate.json` selects `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json --shape 1x1` as the next non-dry-run build/run/compare command. Later acceptance requires exit `0` and `coverage_output_equivalence` mismatch count `0` over `29` words / `116` bytes. This definition adds no execution result, timing, speedup, shape breadth, native Verilator option, arbitrary dependency inference, or automatic GPU allocation claim.

Known-template source-closure copy breadth materialized-template execution result: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_result_gate.json` records exit `0` for the materialized MHA-copy template `1x1` build/run/compare. `coverage_output_equivalence` passed with mismatch count `0` over `29` words / `116` bytes. Raw strict final-state equality remains false with Verilator-internal-only mismatches, and timing/speedup remain out of scope. The copied template now inherits the reference MHA Verilator args so the copied source closure includes the warning suppressions and ITA shape defines needed by the reference.

Known-template source-closure copy breadth materialized-template execution review: `config/scaling_gates/known_template_source_closure_copy_breadth_materialized_template_execution_review_gate.json` accepts the scoped `1x1` result and the copied-template Verilator-args repair. `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_execution_review_gate.json` selects public results packaging refresh next, deferring shape breadth and timing claims.

Known-template source-closure copy breadth execution public-pack refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_gate.json` pins the accepted MHA-copy execution records, materialized template, coverage manifest, first benchmark gate, generator helpers, and optional compare report for public-pack dry-run verification. This remains packaging-only and adds no new execution, timing, speedup, shape breadth, arbitrary dependency inference, native Verilator option, or automatic GPU allocation claim.

Known-template source-closure copy breadth execution public-pack refresh result: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0`. The dry-run include list contains the accepted execution records, materialized MHA-copy template, generated coverage manifest, first benchmark gate, generator helper, and optional compare report. No archive is created and reports/artifacts remain non-canonical.

Known-template source-closure copy breadth execution public-pack refresh review: `config/scaling_gates/public_results_packaging_refresh_after_known_template_source_closure_copy_breadth_execution_review_gate.json` accepts the dry-run include evidence as packaging-only. It selects `define_public_benchmark_pack_externalization_completion_after_known_template_source_closure_copy_breadth_execution_gate` next, without adding execution, timing, speedup, shape breadth, arbitrary dependency inference, native Verilator option, or automatic GPU allocation claims.

Known-template source-closure copy breadth execution public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_known_template_source_closure_copy_breadth_execution_gate.json` closes the packaging boundary, and `config/scaling_gates/next_measurement_selection_after_known_template_source_closure_copy_breadth_execution_public_pack_refresh_gate.json` selects `define_verilator_compatible_gpu_hybrid_minimal_bench_suite_gate` next.

Verilator-compatible GPU hybrid minimal bench suite: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_gate.json` defines `python3 src/tools/run_hybrid_benchmark.py --minimal-bench-suite`, with reusable logic in `src/tools/hybrid_benchmark_minimal_suite.py`. `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_result_gate.json` records the descriptor command exiting `0` with five benchmark entries: operator-plan preview, state-parallel high estimate, single-state repeated-step low estimate, resident decode-like dry-run, and filelist-derived MHA-copy execution evidence.

Verilator-compatible GPU hybrid minimal bench suite run: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_run_result_gate.json` records `python3 src/tools/run_hybrid_benchmark.py --run-minimal-bench-suite` exiting `0`. The run validates the Verilator-compatible operator plan, distinguishes high and low shape classes, confirms the resident decode-like dry-run path, and validates the filelist MHA-copy execution evidence. Existing reports provide scoped observed speedups of `157.725x` for state-parallel `64x1` and `2.164x` for single-state repeated-step `1x64`; these are not broad speedup claims.

Verilator-compatible GPU hybrid minimal bench suite completion: `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_run_review_gate.json` accepts the run result, and `config/scaling_gates/verilator_compatible_gpu_hybrid_minimal_bench_suite_completion_audit.json` closes the objective that selected the first follow-up measured benchmark.

Next measured benchmark selection after the minimal suite: `config/scaling_gates/next_measured_benchmark_selection_after_verilator_compatible_gpu_hybrid_minimal_bench_suite_completion_gate.json` selects the persistent resident decode-like follow-up. The weak point is that resident/persistent resident is still `pulp_ita_mha` ABI/workflow specific and not direct Verilator option support. `config/scaling_gates/define_persistent_resident_decode_like_followup_measurement_gate.json` defines the command as `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3`.

Persistent resident decode-like follow-up measurement: `config/scaling_gates/persistent_resident_decode_like_followup_measurement_result_gate.json` records the selected command exiting `0`. All three repeat samples pass coverage-output equivalence with mismatch count `0`; median hybrid wall is `5.692 ms`, median GPU kernel total is `5.705824 ms`, and median hybrid wall per final state-step is `0.0013896484375 ms`. `config/scaling_gates/persistent_resident_decode_like_followup_measurement_review_gate.json` accepts the result and selects public results packaging refresh next. This is still scoped to the selected `pulp_ita_mha` persistent resident ABI path, not direct Verilator option support, arbitrary RTL support, automatic GPU allocation, or production LLM-serving throughput.

Persistent resident decode-like public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_gate.json` defines the packaging boundary for the scoped follow-up evidence. `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0`, and `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_decode_like_followup_measurement_review_gate.json` accepts the refresh. The next open task is defining public benchmark pack externalization completion for this refresh; it remains packaging-only and does not add measurement, runtime/ABI, direct Verilator option, arbitrary RTL, automatic GPU allocation, or production serving claims.

Persistent resident decode-like public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_persistent_resident_decode_like_followup_measurement_gate.json` closes the externalization boundary after the accepted refresh.

Next measured benchmark selection after persistent resident decode-like refresh: `config/scaling_gates/next_measurement_selection_after_persistent_resident_decode_like_followup_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_timing_measurement_gate`. The next workstream is filelist-derived shape breadth and timing, because current filelist evidence is still mostly correctness-scoped and narrow. Native Verilator option support, arbitrary RTL dependency inference, automatic optimal GPU allocation, runtime/ABI change, and production LLM-serving throughput remain non-claims.

Filelist shape-breadth timing measurement definition: `config/scaling_gates/define_filelist_shape_breadth_timing_measurement_gate.json` fixes four single-run commands: `filelist_paged_attention_kv_score` at `32x1` and `1x32`, and `filelist_known_template_pulp_ita_mha` at `32x1` and `1x32`. The result gate must record CPU elapsed, hybrid wall, GPU kernel total, per-state-step timing, speedup ratios, and `coverage_output_equivalence` mismatch count while keeping raw full-state equality diagnostic only.

Filelist shape-breadth timing measurement result: `config/scaling_gates/filelist_shape_breadth_timing_measurement_result_gate.json` records all four defined commands exiting `0` and passing `coverage_output_equivalence` with maximum mismatch count `0`. For the two `32x1` state-parallel shapes, observed CPU-to-hybrid wall speedup is `87.13301x` and `87.73713x`; for `1x32` single-state repeated-step shapes, observed wall speedup is `2.346763x` and `3.327072x`. This remains single-run scoped timing, not repeat-median, native Verilator option support, arbitrary RTL dependency inference, automatic optimal GPU allocation, or production LLM-serving throughput.

Filelist shape-breadth timing measurement review: `config/scaling_gates/filelist_shape_breadth_timing_measurement_review_gate.json` accepts the scoped four-command result because all commands exited `0`, all selected `coverage_output_equivalence` checks passed, and maximum mismatch count is `0`. The next task is defining public results packaging refresh for this accepted evidence; new measurement, runtime/ABI change, native Verilator option support, arbitrary RTL dependency inference, automatic GPU allocation, production LLM-serving throughput, and raw full-state equality remain non-claims.

Filelist shape-breadth public-pack refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_gate.json` defines the packaging boundary for the accepted four-command result. The next task is running `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` and checking that the filelist timing definition, result, review, and refresh definition gates are included while reports and artifacts remain generated evidence only.

Filelist shape-breadth public-pack refresh review: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_result_gate.json` records the public-pack archive dry-run exiting `0` and including the filelist timing definition, result, review, refresh definition, source-of-truth docs, compact selection pointers, and optional generated report snapshots. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_timing_measurement_review_gate.json` accepts this packaging-only refresh. The next task is defining public benchmark pack externalization completion for this scoped evidence without adding measurement, runtime/ABI, native Verilator option, arbitrary RTL, dependency inference, or automatic GPU allocation claims.

Filelist shape-breadth public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_timing_measurement_gate.json` closes the public benchmark pack boundary for the accepted four-command result. The next task is selecting the next measured benchmark after this public-pack refresh while keeping the completed scope limited to the exact filelist-derived target/shape pairs and single-run timing evidence.

Next measured benchmark selection after filelist shape-breadth public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_timing_measurement_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_repeat_median_timing_gate`. The selected workstream is repeat-median timing for the same `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` target/shape pairs, because automatic GPU allocation policy should be derived from repeat-median-backed filelist timing rather than the current single-run result. This selection does not add measurement, native Verilator option support, arbitrary RTL dependency inference, runtime/ABI changes, automatic optimal GPU allocation, or production LLM-serving throughput.

Filelist shape-breadth repeat-median timing definition: `config/scaling_gates/define_filelist_shape_breadth_repeat_median_timing_gate.json` fixes the same four filelist-derived target/shape pairs, repeat count `3`, `coverage_output_equivalence`, and median timing fields. It also records the workflow gap: prior public repeat-median flows did not cover this exact filelist-derived four-shape set, and `run_hybrid_template.py` has no repeat/sample-preserving summary option.

Filelist shape-breadth repeat-median workflow: `config/scaling_gates/filelist_shape_breadth_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-repeat-median 3 --dry-run`. The dry-run expands `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` at `32x1` and `1x32` into three samples per shape, emits the aggregate `reports/filelist_shape_breadth_repeat_median_summary.json` write plan, and does not write generated evidence. This workflow gate itself adds no timing evidence, runtime/ABI change, native Verilator option support, arbitrary dependency inference, automatic GPU allocation, or production serving claim.

Filelist shape-breadth repeat-median measurement: `config/scaling_gates/filelist_shape_breadth_repeat_median_measurement_gate.json` records `python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-repeat-median 3` exiting `0`. All four workloads and 12 total samples pass `coverage_output_equivalence` with mismatch count `0`. Median CPU-to-hybrid wall ratios are `68.83243486073675x` for `filelist_paged_attention_kv_score 32x1`, `2.67586493987049x` for `filelist_paged_attention_kv_score 1x32`, `76.07629547960308x` for `filelist_known_template_pulp_ita_mha 32x1`, and `6.705723524656427x` for `filelist_known_template_pulp_ita_mha 1x32`; this preserves the scoped state-parallel-over-repeated-step trend. This measurement adds no runtime/ABI change, native Verilator option support, arbitrary dependency inference, automatic GPU allocation, broad speedup claim, or production serving claim.

Filelist shape-breadth repeat-median review: `config/scaling_gates/filelist_shape_breadth_repeat_median_review_gate.json` accepts the repeat-count-3 measurement for scoped public-pack refresh. The review keeps the weakest point explicit: sample variability remains visible, especially in the `filelist_known_template_pulp_ita_mha 1x32` CPU samples, so the accepted claim is a scoped trend rather than paper-grade statistics or broad speedup evidence. The public results packaging refresh definition now precedes any automatic GPU allocation policy work.

Filelist shape-breadth repeat-median public-pack refresh definition: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_gate.json` defines the documentation and archive dry-run boundary for the reviewed repeat-count-3 evidence. That refresh check verifies that the boundary, workflow, measurement, review, refresh definition gate, aggregate summary, and four median report paths are included while keeping generated reports non-canonical.

Filelist shape-breadth repeat-median public-pack refresh result/review: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0`, and `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_repeat_median_review_gate.json` accepts the packaging-only result. This led into the public benchmark pack externalization completion boundary for the scoped repeat-count-3 evidence; it added no new measurement, runtime/ABI change, native Verilator option support, arbitrary dependency inference, automatic GPU allocation, or production serving claim.

Filelist shape-breadth repeat-median public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_repeat_median_gate.json` closes the public benchmark pack boundary for the scoped repeat-count-3 evidence. The next task is selecting the next measured benchmark after this refresh. Candidate directions are scoped automatic GPU allocation policy, broader filelist shape sweep, native Verilator option boundary, filelist dependency inference policy, and resident execution optimization; no candidate is selected by the completion gate itself.

Next measured workstream selection after filelist shape-breadth repeat-median public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_repeat_median_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_gate`. The selection is deliberately scoped: it converts the accepted `32x1` versus `1x32` repeat-median evidence into conservative policy-definition requirements and fallbacks, while broad speedup, native Verilator option support, arbitrary RTL/dependency inference, automatic optimal allocation, runtime/ABI changes, and production serving claims remain out of scope.

Filelist shape-breadth GPU allocation policy definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_gate.json` defines the first policy boundary. It recommends `32x1` only for the two reviewed filelist-derived targets with complete source closure and repeat-median evidence, marks missing timing as low confidence, refuses unknown targets or incomplete source closure, and keeps `1xN` repeated-step workloads as low-confidence or resident-mitigation candidates. This remains scoped policy work, not implementation of automatic optimal GPU allocation for arbitrary RTL.

Filelist shape-breadth GPU allocation policy dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_result_gate.json` records `python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-gpu-allocation-policy --dry-run` exiting `0`, JSON-only stdout, two `32x1` high-confidence recommendations, and refused/low-confidence cases for unknown targets, incomplete source closure, missing repeat-median evidence, and `1xN` repeated-step requests. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_dry_run_review_gate.json` accepts that dry-run scope and advances to defining policy execution/application, not arbitrary RTL optimal allocation.

Filelist shape-breadth GPU allocation policy execution definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_execution_gate.json` defines execution/application as applying the accepted `32x1` recommendation to existing tracked template command plans first. The next dry-run validates `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha` at `32x1`; later non-dry-run build/run/compare still requires a separate gate and `coverage_output_equivalence`.

Filelist shape-breadth GPU allocation policy execution dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_result_gate.json` records both selected `32x1 --dry-run` tracked-template command plans exiting `0`, each with seven planned stages and `coverage_output_equivalence` compare output. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_execution_dry_run_review_gate.json` accepts only command-plan evidence and advances to defining a non-dry-run execution boundary; it is still not build/run/compare evidence or arbitrary optimal allocation.

Filelist shape-breadth GPU allocation policy non-dry-run execution definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json` selects both reviewed `32x1` commands for non-dry-run build/run/compare. Later acceptance requires each command to exit `0`, write the expected compare report, and pass `coverage_output_equivalence` with mismatch count `0`; raw full-state equality, timing/speedup claims, native Verilator support, arbitrary RTL support, and automatic optimal allocation remain non-claims.

Filelist shape-breadth GPU allocation policy non-dry-run execution result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json` records both reviewed policy-selected `32x1` tracked-template commands exiting `0`, writing their expected compare reports, and passing `coverage_output_equivalence` with mismatch count `0`. Each report compares `32` state pairs over `29` words / `116` bytes per state (`928` words / `3712` bytes per report). `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json` accepts only this scoped two-command execution and selects `define_public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate` next; raw full-state equality remains false and timing/speedup, native Verilator, arbitrary RTL/dependency inference, runtime/ABI, production-serving, and automatic optimal allocation claims remain out of scope.

Filelist shape-breadth GPU allocation policy non-dry-run public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json` defines the packaging-only refresh for the accepted two-command execution result. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` and including the execution definition/result/review, source-of-truth docs, selection pointers, and the two generated compare reports as evidence-only paths. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_review_gate.json` accepts that refresh and selects `define_public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate` next.

Filelist shape-breadth GPU allocation policy non-dry-run public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_gate.json` closes the public benchmark-pack boundary for the scoped two-command `32x1` execution result and refresh. It records the closed scope as two reviewed filelist-derived targets, `coverage_output_equivalence` mismatch count `0`, `29` words / `116` bytes per state, raw full-state equality not required and not met, and generated compare reports as non-canonical evidence. The next task is `select_next_measurement_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_public_pack_refresh`.

Next measured workstream selection after filelist GPU allocation policy non-dry-run public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_non_dry_run_execution_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate`. The selected work is a broader explicit shape sweep for the same two reviewed filelist-derived targets; it is not a new measurement result, native Verilator support, arbitrary RTL dependency inference, runtime/ABI work, or automatic optimal GPU allocation.

Filelist shape-breadth GPU allocation policy broader shape sweep definition: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_gate.json` keeps the same two reviewed filelist-derived targets, treats `32x1` as the accepted state-parallel baseline and `1x32` as the existing repeated-step control, and selects four dry-run command plans at `64x1` and `1x64`. GEM comparison remains a deferred design-study candidate rather than benchmark evidence.

Filelist shape-breadth GPU allocation policy broader shape sweep dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_result_gate.json` records all four selected `64x1` / `1x64` dry-run command plans exiting `0`, with no generated reports or artifacts retained. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_dry_run_review_gate.json` accepts only command-plan evidence and led to the non-dry-run definition gate; correctness, timing/speedup, GEM comparison, native Verilator support, arbitrary RTL, runtime/ABI, and automatic optimal allocation remain non-claims.

Filelist shape-breadth GPU allocation policy broader shape sweep non-dry-run boundary: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json` selects all four accepted `64x1` / `1x64` build/run/compare commands for the same two reviewed filelist-derived targets. Later acceptance requires command exit `0` and `coverage_output_equivalence` mismatch count `0`; this definition-only gate does not add execution, timing/speedup, GEM comparison, native Verilator, arbitrary RTL, runtime/ABI, automatic optimal allocation, or production-serving evidence.

Filelist shape-breadth GPU allocation policy broader shape sweep non-dry-run result/review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json` records all four selected `64x1` / `1x64` commands exiting `0`, writing the expected reports, and passing `coverage_output_equivalence` with mismatch count `0`. `64x1` reports compare `64` state pairs over `1856` words / `7424` bytes; `1x64` reports compare `1` state pair over `29` words / `116` bytes. `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_review_gate.json` accepts the result and selects public results packaging refresh next; raw full-state equality remains false and non-required.

Filelist shape-breadth GPU allocation policy broader shape sweep public-pack refresh: `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json` defines the packaging-only refresh for the accepted four-command `64x1` / `1x64` result. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_result_gate.json` records `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` exiting `0` and including the execution definition/result/review, source-of-truth docs, selection pointers, and four generated compare reports as evidence-only paths. `config/scaling_gates/public_results_packaging_refresh_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_review_gate.json` accepts that refresh and selects public benchmark-pack externalization completion next.

Filelist shape-breadth GPU allocation policy broader shape sweep public-pack externalization completion: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_gate.json` closes the public benchmark-pack boundary for the scoped four-command `64x1` / `1x64` result. The closed claim remains `coverage_output_equivalence` mismatch count `0` over `29` words / `116` bytes per state, with raw full-state equality false and non-required. It selects the next measurement-selection task and adds no new measurement, execution, timing/speedup, repeat-median, GEM comparison, native Verilator, arbitrary RTL/dependency inference, runtime/ABI, production-serving, or automatic optimal-allocation claim.

Next measured workstream selection after broader shape-sweep public-pack refresh: `config/scaling_gates/next_measurement_selection_after_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_non_dry_run_execution_public_pack_refresh_gate.json` selects `define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate`. The selected scope is single-run timing for the same two reviewed filelist-derived targets at `64x1` and `1x64`; this is selection-only and does not add timing evidence, repeat-median evidence, native Verilator option support, arbitrary RTL dependency inference, runtime/ABI changes, GEM comparison evidence, production-serving, or automatic optimal allocation claims.

Filelist shape-breadth GPU allocation policy broader shape sweep timing boundary: `config/scaling_gates/define_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate.json` defines four existing `run_hybrid_template.py` commands for the same two reviewed filelist-derived targets at `64x1` and `1x64`. It records single-run timing fields to capture next, keeps `coverage_output_equivalence` as the correctness policy, and selects `run_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate` next. It is not timing evidence, repeat-median evidence, native Verilator support, arbitrary RTL/dependency inference, runtime/ABI work, GEM comparison, production-serving, or automatic optimal allocation.

Filelist shape-breadth GPU allocation policy broader shape sweep timing result: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_result_gate.json` records all four defined `64x1` / `1x64` timing commands exiting `0` and passing `coverage_output_equivalence` with mismatch count `0`. Single-run wall ratios are `127.407767x` / `8.297071x` for `filelist_paged_attention_kv_score` and `214.308914x` / `1.945839x` for `filelist_known_template_pulp_ita_mha`; raw full-state equality remains false and non-required. This selects `review_filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_gate` next and does not claim repeat-median timing, broad speedup, GEM comparison, native Verilator support, arbitrary RTL/dependency inference, runtime/ABI changes, production-serving throughput, automatic optimal allocation, or raw full-state equality.

Filelist shape-breadth GPU allocation policy broader shape sweep timing review: `config/scaling_gates/filelist_shape_breadth_gpu_allocation_policy_broader_shape_sweep_timing_measurement_review_gate.json` accepts the scoped single-run timing result and selects public results packaging refresh next. The accepted claim is limited to the two reviewed filelist-derived targets at `64x1` and `1x64`; repeat-median timing, broad speedup, GEM comparison, native Verilator support, arbitrary RTL/dependency inference, runtime/ABI changes, production-serving throughput, automatic optimal allocation, and raw full-state equality remain non-claims.

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

Public benchmark pack externalization state: `config/scaling_gates/public_results_packaging_gate.json` defines the reader-facing pack boundary, while later local candidate publication records are not current source of truth unless they are tracked and selected by `config/selection.json` or the public-pack manifest. `docs/results.md` carries the MobileViT `limit 128` evidence and archive dry-run policy with explicit non-claims.

Paged-attention/KV-cache follow-up and subsequent candidate publication records remain historical/local evidence unless tracked and selected by the current state. Treat `config/selection.json` as authoritative for the current open pointer.

Public reproduction smoke state: `docs/results.md` now records the first dry-run command set for external readers. This smoke validates public CLI parsing and command expansion only; it is not correctness or timing evidence.

Public archive dry-run state: `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` now prints the public pack include/exclude plan and the non-executed archive command without creating an archive. Archive files remain generated outputs and are not source of truth.

Generic benchmark CLI state: `config/scaling_gates/generic_hybrid_benchmark_cli_gate.json` adds `src/tools/run_hybrid_benchmark.py` as a target-oriented wrapper over existing proven flows. Initial supported dry-run targets are `pulp_ita_mha --shape`, `paged_attention_kv_score --shape`, and `mobile_vit --limit 128`; `pulp_ita_mha` also supports `--mode resident-state-reuse` and `--mode persistent-resident-state-abi`. The reusable dispatch lives in `src/tools/hybrid_benchmark.py`. `--summary-out` adds a unified generated summary schema for the wrapper, including target, shape or limit, mode, commands, expected reports, and collected coverage-output evidence when the benchmark is actually executed; dry-run summaries are marked as non-evidence. Fresh wrapper smokes for `pulp_ita_mha 1x1`, `paged_attention_kv_score 1x1`, `pulp_ita_mha 1x1 resident-state-reuse phases=2`, and `pulp_ita_mha 1x1 persistent-resident-state-abi phases=2` wrote matching `reports/hybrid_benchmark_*.json` summaries; all passed coverage-output equivalence with mismatch count `0`. `mobile_vit --limit 128 --summary-from-existing` writes `reports/hybrid_benchmark_mobile_vit_template_limit128.json` from the already generated MobileViT limit-128 reports without rerunning inference or hybrid commands. The lower-level `run_hybrid_template.py` and target-oriented `run_hybrid_benchmark.py` now both have `--estimate-efficiency` for short operator-facing high/medium/low speedup-class output and `--estimate-efficiency-json` for machine-readable estimate inspection; both keep performance estimates separate from CPU-vs-hybrid equivalence claims. The benchmark wrapper estimate also includes a `next_action` line so the operator can decide whether to scale state-parallel shapes, avoid single-state repeated launches, or separate dataset host preprocessing from RTL timing. `--list-targets` now includes a `sidecar_gpu` discovery block so operators can see template-shape shim readiness or the not-ready reason before running a target. `run_hybrid_benchmark.py --help` now lists the shortest Verilator-like examples for target discovery, terminal command preview, terminal operator plan, and debug JSON operator-plan inspection. `run_hybrid_benchmark.py --sidecar-gpu` is a short compatibility alias for the existing hybrid sidecar GPU flow plus the human-readable efficiency estimate; it does not change `coverage_output_equivalence` or create a new speedup claim. The wrapper now also accepts tested Verilator-style compatibility spelling, `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`, mapped through `src/tools/verilator_sidecar_options.py`. Template-target preflight now includes `sidecar_stage_plan` from `src/tools/hybrid_benchmark_sidecar_plan.py`, naming the direct-Verilator migration stages through `gpu_artifact_build`, `hybrid_sidecar_run`, and final `coverage_output_equivalence` compare; each stage also carries structured `details` for build inputs, state files, launch shape, and compare policy. The stage plan now reports `verilator_option_readiness`, where `ready_for_verilator_option_shim` means the wrapper has the minimum structured inputs for a future option shim while remaining non-executed planning evidence. `src/tools/verilator_sidecar_shim.py` exposes the same non-executing handoff as debug JSON, with exit code `0` for ready, `2` for not-ready target/mode, and `1` for input/planning errors. It can also select one planned stage with `--stage <name> --emit-command` and expose that stage command at top level without executing it. `--emit-verilator-command` additionally synthesizes future direct Verilator command previews as machine-readable `verilator_command_argv` plus shell-quoted `verilator_command` fields from structured stage details, again without executing them. `--print-verilator-command` prints only the shell-quoted preview for terminal use when the shim is ready, while not-ready targets keep JSON status output and exit code `2`. `--print-efficiency-estimate` prints the matching human-readable speedup class, reason, next action, and non-claims without executing commands. `--print-operator-plan` combines the shell-quoted command preview and the same efficiency estimate in one non-executing terminal view. The primary wrapper now exposes these terminal previews with compact `run_hybrid_benchmark.py <target> --sim-accel-shape <NxS> --print-verilator-command`, `--print-efficiency-estimate`, or `--print-operator-plan`, giving operators a short target-first path from discovery to the direct-option preview without execution. `--operator-plan-json` provides the same wrapper-first operator plan as debug JSON, declares `schema_role: target_first_operator_plan`, adds `json_flow_role: debug_inspection`, `runtime_abi: false`, and `execution_authority: false`, and returns not-ready targets as JSON with exit code `2`. `--list-targets`, wrapper debug JSON, and shim debug JSON now share the same readiness vocabulary for `ready_for_template_shape`, `ready_for_verilator_option_shim`, and `not_ready_for_verilator_option_shim`. Wrapper `--operator-plan-json` emits the operator-plan fields at top level for inspection, while shim JSON nests the same synthesized command/handoff shape under `operator_plan` when the command can be synthesized; both forms keep command argv, shell-quoted command, estimate command, efficiency estimate, and `coverage_output_equivalence` as the correctness policy. The intended end state is a direct Verilator option, recorded in `docs/verilator_sidecar_option.md`, with target spelling `verilator --sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`.

Sidecar operator surface update: `--list-targets` now reports ready template stage names, not-ready resident fallback stage names, and dataset-backed stage names or inspect commands inside the `sidecar_gpu` discovery block. `--list-targets sidecar_gpu` now emits the focused sidecar discovery view referenced by terminal operator plans and debug JSON discovery hints. Ready slice-template targets include terminal operator-plan templates, estimate-command preview templates, debug JSON operator-plan templates, and concrete example commands using the recommended `64x1` starting shape; the example commands use compact `--sim-accel-shape` and are contract-tested as non-executing previews. The ready discovery block now separates `recommended_entrypoint` (`--sim-accel-shape <NxS>`) from `compatibility_entrypoint` (`--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`) so tooling can choose the short wrapper-first path without losing the expanded future-Verilator form. Ready operator-plan debug JSON includes top-level `requested_compatibility_entrypoint`, plain `command`, `estimate_command` with `--sim-accel-estimate-efficiency`, and `handoff_contract`, which records state authority, init/reference/candidate dumps, generated compare report path, and `coverage_output_equivalence` without executing anything; it also includes `discovery_hint` so debug tooling can inspect the same recommended starting shape, entrypoint split, concrete requested-shape compatibility spelling, estimate-command example, and both terminal and JSON operator-plan examples as discovery, while keeping `requested_shape` and `recommended_shape_matches_request` explicit. Summary JSON and preflight JSON now carry the same discovery hint and `verilator_option_preview` with both `command` and `estimate_command` whenever a direct-option preview can be synthesized. Wrapper dry-run treats `--sim-accel-*` shape spellings as sidecar-compatible entrypoints even when the explicit `--sim-accel sidecar-gpu` selector is omitted; entrypoint metadata now separates raw `sim_accel` from `effective_sim_accel` so this implicit sidecar path is visible. `run_hybrid_benchmark.py --help` now uses compact `--sim-accel-shape 64x1 --print-verilator-command`, `--print-verilator-estimate-command`, `--print-efficiency-estimate`, `--print-operator-plan`, and `--operator-plan-json` as the shortest wrapper-first examples while retaining expanded Verilator-style compatibility. `mobile_vit --limit 128` remains not-ready for the direct Verilator option, but its not-ready plan exposes `host_preprocess` and `rtl_sidecar_proxy_eval` stages. Resident modes also remain not-ready for the direct option, but expose `resident_state_reuse_workflow` and `persistent_resident_state_abi_workflow` fallback commands. `verilator_sidecar_shim.py --help` now carries executable examples for ready command previews, estimate-command previews, plus not-ready MobileViT and resident stage-command inspection; the examples are contract-tested.
Shortest operator path state: the documented terminal path is `python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu`, then `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan`. The focused sidecar discovery JSON exposes that sequence as `shortest_operator_path` and exposes the optional JSON inspection sequence as `debug_json_path`. Both are non-executing and keep `coverage_output_equivalence` separate from the efficiency estimate; the JSON path is debug output, not the runtime ABI.

The active conclusion is:

- CPU vs hybrid coverage-output equivalence passes on the selected MHA and paged KV evidence.
- Many independent states per launch are the favorable shape.
- Single-state repeated launches remain the weak shape.
- Current evidence is scoped to coverage-output equivalence, not raw Verilator internal state equivalence.

## Source Of Truth

Canonical current state:

- `config/selection.json`
- `docs/status.md`
- `docs/roadmap.md`
- `README.md`

`config/README.md` is explanatory documentation for the config directory; it is
not a canonical current-state file.

Generated evidence paths are listed here only so readers can regenerate or
inspect them from documented commands. They are not source of truth, and current
decisions must not depend on local report snapshots:

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
- `public_benchmark_pack_externalization_completion_gate.json`
- `next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`
- `paged_attention_kv_cache_scale_up_measurement_gate.json`
- `persistent_resident_device_handle_storage_gate.json`
- `persistent_resident_device_handle_storage_review_gate.json`

## Active Harness Surface

- `overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv`
- `pulp_paged_kv_cache_large_host_probe`
- `tc_sram`

## RTLMeter Vortex/VeeR Hybrid Matrix

`src/tools/rtlmeter_vortex_veer_hybrid_measurement_matrix.py` now produces the
single review table for the active `Vortex:mini:hello` plus VeeR EH1/EH2/EL2
hybrid-measurement objective. The generated report is
`reports/rtlmeter_vortex_veer_hybrid_measurement_matrix.json`. Its Markdown
view now exposes Vortex runner evidence as table columns, including
`cycles=40897`, `proxy_handoff=true`, `fake_authority=true`,
`runtime_stub_rebuilt=true`,
`runtime_bridge_stub_rebuilt=true`,
`materialized_runtime_args_probe_executed=true`,
`real_cuda_materialized_smoke=true`,
`real_cuda_materialized_args_call=true`,
`real_vortex_kernel_artifact=true`,
`kernel_build_landingpad_block=false`,
`cuda_memory_transport=true`, `cuda_runtime_sequence_preflight=true`,
`preflight_authority=true:memory_post_condition`,
`dpi_memory_helper=true`, `probe_marker_block=true`, and `gpu=False`. The same Markdown view now also surfaces EH1/EH2 root-header probe
evidence as `root_probe=True`, `offset_probe=True`, `marker_groups=5`,
`offset_groups=5`, `offsets_reviewed=True`,
`root_variant=mailbox_public_flat`, and `offset_review_ready=True`.
The matrix also folds each EH bridge preflight's `missing_build_context` into
row-level missing prerequisites, so the remaining `executed_bridge_comparison`
and `timing_report` blockers are not hidden behind the presence of a bridge
report.
`reports/rtlmeter_vortex_observable_authority_audit.json` keeps
`real_runtime_observable_authority_ready=false`, so proxy/fake-driver evidence
and the rebuilt generated-main stubs are not confused with Vortex kernel
execution or timing. The bridge stub compiles against `vortex_lowered_tb_runtime_sequence.h`
types, and the invocation probe executes an expected-fail
`vortex_lowered_tb_invoke_runtime_sequence(NULL, ...)` boundary before proxy
handoff. The materialized runtime-args probe now also consumes the prepared
Vortex buffers (`37224` host-to-device bytes, `88` device-to-host initial bytes)
and `9` DCR writes through real CUDA Driver API callbacks before proxy handoff;
`reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.json`
records `timed_out=true` from the generated `Vsim` when run from `obj_dir` with
the root-storage-backed real CUDA callback. It still does not export real Vortex
runtime authority.
`reports/rtlmeter_vortex_real_kernel_artifact_preflight.json` now finds the
generated Vortex `vl_batch_gpu.ptx` plus `vl_batch_gpu.meta.json`, and
`reports/rtlmeter_vortex_kernel_artifact_build_attempt.json` now passes the
`src/tools/build_vl_gpu.py ... --emit-ptx-module` attempt without the previous
landingpad/personality verifier failure. A syms-state-image rebuild now clears
the artifact prelaunch rejection in generated hierarchy metadata
(`prelaunch_rejection_required=false`, `root_offset_in_state=192`,
`storage_size=80768`). The generated `Vsim__main.cpp` now invokes
`rtlmeter_vortex_real_cuda_launch_root_storage_kernel`. The full PTX still
times out under bounded `ptxas`, but
`reports/rtlmeter_vortex_ptx_entry_slice.json` writes a `vl_eval_batch_gpu`
single-entry slice and
`reports/rtlmeter_vortex_ptx_entry_slice_module_load_diagnostic.json` proves it
precompiles to `artifacts/rtlmeter_vortex_ptx_entry_slice/vl_eval_batch_gpu.cubin`.
With the canonical std::ref-fix CUBIN selected, the real-CUDA smoke reaches
`after_cuCtxSynchronize`, relocates 65 pointers in the host `rootp - 192` syms
image, and exports `memory_post_condition` authority. `reports/rtlmeter_vortex_timing.json`
then measures the first CPU-vs-hybrid gate; the hybrid median is
`0.4504947270033881s` versus CPU `0.22s`, so no speedup/usefulness claim is made.
`reports/rtlmeter_vortex_cuda_memory_transport_preflight.json` now separately
proves the real CUDA Driver API buffer transport for those materialized inputs:
`7` buffers, `37224` H2D bytes, and `88` D2H-init bytes. The D2H total changed
from `68` to `88` because `post_compare_result_initial` now matches the full
`VortexPostCompareResult` ABI size instead of only its first field.
`reports/rtlmeter_vortex_cuda_runtime_sequence_preflight.json` now also passes
on the real CUDA Driver API path for upload, `9` DCR callbacks, a no-op kernel
callback, observable export, and release, with preflight authority source
`memory_post_condition`. The generated DPI `mem_access` wrapper now contains a
compile-safe shadow call to `vortex_mem_access_device_helper`, so the
memory-helper prerequisite is no longer the first blocker. The
observable-authority audit still records that probe or marker boundaries block
the real generated lowered-TB runtime call. This is still not Vortex kernel
execution, runtime observable authority, CPU-vs-hybrid timing, or a
speedup/usefulness claim.
`reports/rtlmeter_hybrid_measurement_difficulty.json` is now the generated
difficulty table layered on top of that matrix, not a new measurement. It scores
the current blockers as Vortex `1` measured/low with a measured negative
CPU-vs-hybrid timing result, EH1 `6` high difficulty, EH2 `25` high difficulty,
and EL2 `1` measured/low difficulty while keeping both measured rows as
no-speedup evidence. The EH2 score now includes
`entry_pruned_cpp_verilator_runtime_residue_in_gpu_ptx` from the entry-pruned
PTX slice: `reports/rtlmeter_veer_eh2_sidecar_bridge.json` records `1456`
runtime-residue pattern hits and `134` suspicious function definitions before
the first eval launch fault. The expanded host-cleanup pass now removes the
remaining `VlDelayScheduler`, `VlCoroutineHandle`, `std::multimap`, and
`_Rb_tree` call sites from the entry path, but direct no-patch eval-only still
fails at `before_first_step_sync` with CUDA 700. A return-before-eval probe and
a prologue-only return-before-eval-call probe both pass. The latest staged
probes narrow the first fault further: `_eval` returning before
`eval_phase__act` passes, one `eval_phase__act` call fails, `eval_phase__act`
returning after `eval_triggers__act` passes, and returning after
`trigger_orInto__act` fails. A `trigger_orInto__act` entry-only return before
the first `VlUnpacked<uint64_t,1>::operator[]` still fails, including with a
64KiB stack override. Inline probes then narrow the boundary further: no-op,
destination load, source load, and before-store variants pass, but the store to
`__VnbaTriggered` at `root+472408` faults in `eval_phase__act` context.
Adjacent `__VactTriggered` store, root-base store, and the same
`__VnbaTriggered` store from entry context pass; padded 2MiB state and
`ptxas --maxrregcount=228` do not clear it. The follow-up probes refine this:
an `eval_phase__act` store to `__VnbaTriggered` passes before triggers, after
triggers when the root pointer is recomputed directly, and in a minimal
`eval_phase__act` skeleton; the adjacent `root+472416` store after triggers
also passes. The `std::reference_wrapper::get()`-derived path with explicit
`cvta.global` still faults, so `vlgpugen` now canonicalizes those get calls
back to the stored original root pointer. That canonicalized full eval-only
CUBIN still fails at `before_first_step_sync` with CUDA 700. Follow-up
canonical probes show `_eval` passes when returning before `eval_phase__act`,
but faults after one `eval_phase__act` call; ret0 `eval_phase__act` probes
still fault by the `trigger_orInto__act` return boundary. The latest
`trigger_orInto__act` probes pass entry, destination load, source load, and
before-store, then the after-store probe faults with CUDA 700. `vlgpugen` now
canonicalizes single-element `VlUnpacked<T,1>` index calls as well; the EH2
probe rewrites `57` such calls and directizes `trigger_orInto__act` to
base-pointer load/store, but full eval-only still fails at
`before_first_step_sync` with CUDA 700. The current EH2 boundary is therefore
post-`VlUnpacked<T,1>` canonical eval localization, not a plain operator[] call
ABI, raw-address size, trigger load, stack limit, or simple register-count
issue.
`reports/rtlmeter_vsim_main_vortex_probe_marker_strip.json` now records that the
generated-main runtime marker and expected-fail invocation probe were stripped
from `Vsim__main.cpp`, preserving the materialized runtime-args probe, and the
Vortex obj_dir rebuild passes, and the canonical `vlgpugen` std::ref
pointer-return fix CUBIN reaches `after_cuCtxSynchronize`. The audit therefore advances
`next_required_boundary` to
`measure_or_unblock_veer_eh1_eh2_hybrid_timing`.

Current state: `VeeR-EL2:default:hello` is hybrid-measured and correctness
passes, with the best current timing row from
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json`
(`sidecar_wall_s_median=0.641226`,
`sidecar_vs_cpu_parallel_ratio=3.460382`, no speedup claim). `Vortex:mini:hello`
now has a measured negative first gate. The reviewed authority-registry source closure is present,
the stdout/cycles runner contract and runner argv handoff are ready, and the
wrapper now strips sidecar-only `--sim-accel*` options before invoking real
Verilator. The direct-native runner observes RTLMeter stdout/cycles
(`cycle_count=40897`, `TEST PASSED`) and records
`hybrid_candidate_proxy_handoff_observed_timing_missing`. A reviewed Vsim
sidecar proxy target is exercised through the patched `Vsim__main.cpp` source
path, so `rtlmeter_proxy_handoff_observed=true`; GPU execution claim, timing,
and speedup remain false. The generated PTX/meta artifact is ready, prelaunch
rejection is clear, and the root-storage callback is wired. The real-CUDA materialized runtime smoke now uses
`artifacts/rtlmeter_vortex_vlgpugen_std_ref_fix_probe/vl_eval_batch_gpu.cubin`,
reaches `after_cuCtxSynchronize`, and exports `memory_post_condition` authority.
The earlier return-before-eval slice
`artifacts/rtlmeter_vortex_ptx_entry_return_probe/vl_eval_batch_gpu_return_before_eval.cubin`
uses the same 65-pointer relocated syms image and reaches `after_cuCtxSynchronize`.
An `_eval` skeleton probe that skips both `eval_phase__act` and
`eval_phase__nba` still fails unless `_eval` locally bypasses the null
`std::ref<Vsim___024root>` lowering and uses the root argument directly; that
root-direct plus phase-skip probe reaches `after_cuCtxSynchronize`. Root-direct
with phases enabled still fails with CUDA 700, but the all-`std::ref`
returns-argument CUBIN reaches `after_cuCtxSynchronize` with phases enabled.
The canonical `vlgpugen` std::ref pointer-return fix now rebuilds a
`vl_eval_batch_gpu` CUBIN that also reaches `after_cuCtxSynchronize`. The next
next active blocker is EH1/EH2 measurement; Vortex already exports
observable authority before CPU-vs-hybrid timing can exist.
`reports/rtlmeter_veer_family_surface_audit.json` now classifies
`VeeR-EH1:default:hello` and `VeeR-EH2:default:hello` as
`sidecar_bridge_preflight_surface_missing`: descriptor/testbench evidence is
present enough to start a design-specific port, and fail-closed EH1/EH2 authority
registry entries now exist under `config/rtlmeter_sidecar_authorities/`.
Fail-closed EH1/EH2 state-layout preflight reports also exist under `reports/`,
with `state_layout_ready=false` because generated root-layout offsets are not yet
reviewed. The regenerated state-layout reports now prefer the
mailbox-public-flat CPU-reference `Vsim___024root.h` headers when present and
set `root_layout_probe_performed=true` plus
`root_offset_probe_performed=true` for both EH1/EH2, so `root_layout_probe` is
no longer listed as missing. The root-offset review now records
`root_obj_dir_variant=mailbox_public_flat`, complete marker groups for control
scalars, PC candidates, cycle counters, mailbox observables, and GPR
observables, no missing marker groups, and a selected root-offset ABI for both
EH1/EH2. This is still not sidecar bridge execution or timing.
Fail-closed EH1/EH2 preload
state-image materializer reports now also
exist under `reports/`, with `state_image_materialized=true` but
`gpu_execution_claimed=false`, `timing_measured=false`, and
`speedup_claimed=false`. Fail-closed EH1/EH2 sidecar bridge preflight reports now
also exist under `reports/`, with `sidecar_bridge_preflight_ready=true` but
`sidecar_bridge_invoked=false`, `sidecar_observables_ready=false`,
`sidecar_execution_claimed=false`, `gpu_execution_claimed=false`,
`timing_measured=false`, and `speedup_claimed=false`. EH1/EH2 CPU reference
observables now pass: `reports/rtlmeter_veer_eh1_cpu_reference_summary.json`
records `1044` RTLMeter cycles, `TEST_PASSED`, and `execute_elapsed_s=0.03`;
`reports/rtlmeter_veer_eh2_cpu_reference_summary.json` records `2325` RTLMeter
cycles, `TEST_PASSED`, and `execute_elapsed_s=0.06`. The bridge preflight
reports therefore no longer list `cpu_reference_observables`,
`complete_root_field_offset_abi_review`, or
`design_specific_sidecar_executable_implementation` as missing. The new
fail-closed EH executable boundary `src/tools/veer_eh_sidecar_executable.py`
now checks generated GPU artifact metadata as well as the state image,
root-offset ABI, and CPU reference. EH1 has a generated PTX module artifact
ready for bridge execution (`storage_size=1355200`,
`gpu_artifact_prelaunch_rejection_required=false`). EH2 also has a generated
PTX module artifact. It has now been rebuilt as a syms-state image
(`storage_size=623168`, `root_offset_in_state=192`,
`unsafe_syms_gep_covered_by_state_image=true`,
`gpu_artifact_prelaunch_rejection_required=false`). The EH2 bridge now invokes
`run_vl_hybrid`, materializes `542` imem and `542` lmem program bytes, offsets
the clock/reset patch by `192`, and still times out after `60s` at
`before_cuModuleLoad` on the `44377841` byte PTX before stdout/cycles
comparison. The eval+patch entry-pruned EH2 CUBIN now builds with `ptxas -O0`,
loads, resolves kernels, uploads the init state, launches the step-0 patch+eval
pair, and with `RUN_VL_HYBRID_SYNC_EACH_STEP=1` fails at
`before_first_step_sync` with `CUDA error 700`; a no-patch eval-only probe
reproduces the same first eval launch fault, and 2MiB padded storage, a 64KiB
stack limit, plus zero-init storage do not clear it. The entry-pruned EH2 PTX
slice is now statically counted in the bridge preflight: `VlDelayScheduler`
(`31`), `VlCoroutineHandle` (`228`), `_Rb_tree` (`98`), `basic_string` (`171`),
`new_allocator` (`14`), `VL_WRITEF` (`13`), `VL_FINISH` (`13`),
`runFlushCallbacks` (`7`), `std::ref` root wrappers (`114`), and other
`std::ref` module wrappers (`767`), for `1456` total residue-pattern hits and
`134` suspicious PTX function definitions. The expanded
`vl-stub-host-io-calls` / `vl-stub-timing-scheduler-context` cleanup path now
erases the remaining scheduler/container calls, including `VlDelayScheduler`,
`VlCoroutineHandle`, `std::multimap`, and `_Rb_tree`; the cleaned entry slice
still has `1331` static residue-pattern hits and direct no-patch eval-only still
fails at `before_first_step_sync` with CUDA 700. Return-before-eval and
prologue-only return-before-eval-call probes both pass, so module load, init
upload, kernel launch/sync, and syms pointer setup are no longer the first EH2
blocker. Staged `_eval` / `eval_phase__act` probes first placed the CUDA 700 at
`trigger_orInto__act`, then inline probes narrowed it to the store into
`__VnbaTriggered` at `root+472408`: loads and OR pass, `__VactTriggered`
(`root+472400`) and root-base stores pass, entry-context `__VnbaTriggered`
store passes, but eval-phase `__VnbaTriggered` stores fail for both u32 and u8.
Padded 2MiB state and maxr128 CUBIN still fail. After `VlUnpacked<T,1>`
index-call canonicalization, `eval_phase__act` can return before
`trigger_orInto__act`, but an immediate-return `trigger_orInto__act` helper call
still faults with CUDA 700. A targeted vlgpugen rewrite now replaces the EH2
`VlUnpacked<T,1>` `trigger_orInto__act` helper call with inlined load/or/store
and removes the call from the eval entry slice; the rewritten eval-only CUBIN
still fails with CUDA 700 at first-step sync. Store-value probes show skip,
zero, and dst-value stores all still fault in full eval-only, while skip-store
return probes pass before `trigger_anySet__act`, after `trigger_anySet__act`,
and after `timing_resume`; returning after `eval_act` still faults. The
new `eval_act` return probes pass after callseq `950` and `951`, then fault
after callseq `952`. Deeper probes show `dec_cam[0]` still faults even when its
body is replaced with a minimal `ret`; skipping only callseq `952`, or callseq
`952` and `953`, still faults, while skipping callseq `952`, `953`, and `954`
passes. A follow-up vlgpugen pass canonicalizes `VlWide<N>` pointer conversions
(`cvPj` and `cvPKj`) to their first pointer argument; the latest EH2 lowering
reports `VlWide pointer conversions canonicalized: 16394`. The regenerated
entry-pruned CUBIN builds with `ptxas -O0`, but eval-only execution still fails
at first-step sync with CUDA 700. Current post-`VlWide` probes now show kernel
relocation and `_eval` prologue pass, `eval_phase__act` passes through
`eval_triggers__act` and the trigger-merge loads, and a nonzero trigger store
passes when `_eval` returns immediately. With normal `_eval` continuation, NBA
`trigger_anySet` passes before `eval_nba`, then CUDA 700 appears after crossing
`eval_nba`. The generated matrix therefore moves EH2's next action to
`localize_eh2_post_vlwide_eval_phase_nba_eval_nba_cuda700_before_bridge_timing`.
EH1 bounded bridge execution now invokes the
root-image path, materializes `349` imem and `349` lmem program bytes, writes a
clock/reset patch, and calls `run_vl_hybrid` for `19` logical steps. Stage
tracing shows CUDA init, device lookup, and context creation pass, then the
runtime times out after `20s` at `before_cuModuleLoad` before emitting a GPU
dump. EH1 therefore now blocks on the PTX module load/JIT portion of
`successful_gpu_launch_without_timeout`, not on bridge invocation. The bounded
offline cubin probe `reports/rtlmeter_veer_eh1_ptxas_o0_probe.json` also times
out: `ptxas --opt-level 0` on the `17,684,220` byte / `630,613` line PTX exits
through the `180s` timeout, reaches `6,674,492` KB max RSS, and produces no
cubin. The entry-pruned probe
`reports/rtlmeter_veer_eh1_entry_pruned_module_probe.json` narrows the module to
`vl_eval_batch_gpu` plus `vl_apply_patch_schedule_gpu`; `ptxas -O0` then passes
in `17.98s` and emits an `11,701,952` byte cubin. That cubin loads and resolves
both kernels, but sync-each-step execution fails at the first `vl_eval_batch_gpu`
launch with CUDA illegal memory access. The follow-up eval-only single-entry
cubin also fails at the first synced `vl_eval_batch_gpu` launch, so the fault is
not caused by the patch-schedule helper. Explicit
`RUN_VL_HYBRID_ORDERING_AWARE_REGION_COUNTER_GLOBAL_INIT=1`, accepted CUDA
stack-limit overrides through `262144` bytes, and a `2097152` byte padded
storage/init-state probe also do not clear the fault. Static PTX review showed
that `vl_eval_batch_gpu` calls `Vsim___024root___eval`, which reaches
`Vsim___024root___eval_nba`; that path still contained `std::string`,
`VL_WRITEF_NX`, `VL_FINISH_MT`, and `Verilated::runFlushCallbacks` calls, with
`std::new_allocator<char>::allocate` lowered to a null-returning device stub.
The LLVM pass boundary has now moved: `src/passes/VlGpuPasses.cpp` marks the
GPU cleanup passes required for O0 `optnone` Verilator IR, stubs `VL_FINISH_MT`
and `Verilated::runFlushCallbacks`, and handles `CallBase`/`InvokeInst` call
sites. Running the updated pass over the EH1 `vl_batch_gpu.ll` writes
`vl_batch_gpu.host_io_stub_probe.ll`;
`reports/rtlmeter_veer_eh1_host_io_stub_probe.opt.stderr` records `47` erased
host-I/O call sites, and the probe IR contains zero matching calls to
`VL_FINISH_MT`, `VL_WRITEF_NX`, `Verilated::runFlushCallbacks`,
`std::basic_string`, or `std::new_allocator<char>::allocate`. This is still not
a passing cubin or bridge measurement. The next boundary is regenerating the
entry-pruned EH1 cubin from this host-I/O-stubbed IR and rerunning the eval-only
bridge to see whether the first-launch CUDA fault clears.
Both still lack a passing sidecar stdout/cycles comparison and CPU-vs-hybrid
timing reports. The
measured EL2 executable is not directly reusable for EH1/EH2 because the
authority target name, root-symbol/state-layout paths, and `hello`
`program.hex` SHA are EL2-specific. The objective is therefore not complete.

| Case | Measurement state | Quantitative evidence | Remaining gate |
|---|---|---|---|
| `Vortex:mini:hello` | Measured; correctness passed; no speedup claim | CPU reference passes (`0.22s`, `40897` clocks, `TEST PASSED`); canonical real-CUDA materialized runtime relocates 65 pointers, reaches `after_cuCtxSynchronize`, exports `memory_post_condition` authority, and `reports/rtlmeter_vortex_timing.json` records hybrid wall median `0.4504947270033881s` over `3` repeats with `hybrid_vs_cpu_ratio=2.047703304560855` and `cpu_vs_hybrid_speedup=0.48835199795434103` | Treat as measured negative first gate; continue EH1/EH2 unblock and timing |
| `VeeR-EH1:default:hello` | Not measured; entry-pruned module loads but eval-only launch faults | CPU reference passes (`0.03s`, `1044` RTLMeter cycles, `TEST_PASSED`); mailbox-public-flat CPU reference rebuild passes; root-offset ABI review ready; full PTX times out at module load and offline `ptxas -O0` times out after `180s`; entry-pruned eval+patch cubin builds in `17.98s`, loads, resolves kernels, uploads init state, then fails at first synced `vl_eval_batch_gpu` launch; eval-only single-entry cubin fails the same way; `2097152` byte padded storage, region-counter global init, and stack-limit overrides do not clear it; updated host-I/O stub pass erases `47` EH1 host-I/O call sites and leaves zero matching calls in `vl_batch_gpu.host_io_stub_probe.ll`; regenerated host-I/O-stubbed single-entry eval CUBIN builds (`6735488` bytes, `ptxas -O0` `15.29s`) but the bridge still exits with `CUDA error 700` at first eval launch; runtime trace records `NUM_REGS=255`, `LOCAL_SIZE_BYTES=1776`, last stage `before_final_sync`, and padded 2MiB init-state still faults; compute-sanitizer is blocked before the first instrumented CUDA API | Continue EH1 by isolating remaining scheduler/container/ABI device fault, then bridge stdout/cycles comparison and timing |
| `VeeR-EH2:default:hello` | Not measured; entry-pruned CUBIN loads but first eval launch faults | CPU reference passes (`0.06s`, `2325` RTLMeter cycles, `TEST_PASSED`); mailbox-public-flat CPU reference rebuild passes; root-offset ABI review ready; syms-state image artifact exists (`storage_size=623168`, `root_offset_in_state=192`, `unsafe_syms_gep_covered_by_state_image=true`, prelaunch rejection false); full PTX bridge still times out after `60s` at `before_cuModuleLoad` on the `44377841` byte PTX, but the eval+patch entry-pruned CUBIN builds with `ptxas -O0`, loads, resolves kernels, uploads init state, launches step-0 patch+eval, then fails at `before_first_step_sync` with `CUDA error 700`; `VlWide<N>` pointer conversions are canonicalized (`16394` rewrites), and current post-`VlWide` probes show nonzero trigger store can pass if `_eval` returns immediately; NBA `trigger_anySet` passes before `eval_nba`, then CUDA 700 appears after crossing `eval_nba` | Localize/fix post-`VlWide` `eval_phase__nba` / `eval_nba` CUDA700, then rerun bridge comparison and timing |
| `VeeR-EL2:default:hello` | Measured; correctness passed | Best sidecar row `0.641226s`; `sidecar_vs_cpu_parallel_ratio=3.460382`; serial CPU still faster | Keep as measured negative/portability baseline; no speedup claim |

RTLMeter/GPU usefulness is therefore split by workload shape rather than by a
single global "GPU on/off" decision:

| Workload / scope | Current classification | Evidence | Hybrid decision |
|---|---|---|---|
| `NVDLA.nvdla_cmac_a2cacc` scoped hot SS | GPU-favorable measured case | `reports/rtlmeter_non_veer_hybrid_measurement_summary.json` records `10/10` measured shapes as GPU-favorable with coverage-output equivalence. Best wall ratio is `11764.742765273311x` at `1024x64`; repeat-median audit records best planned-shape ratio `2553.8327316486166x` at `2048x64`. | Prefer GPU for reviewed hot-SS candidates with state batching and/or repeated-step batching. Do not generalize to full NVDLA or arbitrary RTLMeter. |
| `Vortex:mini:hello` RTLMeter first gate | Measured negative | CPU reference and proxy stdout/cycles pass at `40897` cycles. Canonical real-CUDA materialized runtime reaches `after_cuCtxSynchronize`, exports `memory_post_condition` authority, and the timing report records hybrid median `0.4504947270033881s` versus CPU `0.22s` (`2.047703304560855x` slower). | Keep as a measured negative first gate; do not claim speedup. |
| VeeR full-program RTLMeter (`EL2/EH1/EH2`) | Unfavorable or blocked | EL2 is correctness-measured but the best `hello` sidecar row has `sidecar_vs_cpu_parallel_ratio=3.460382` and serial CPU is faster. EH1 reaches entry-pruned module load but faults at first eval launch even after host-I/O residue cleanup and regenerated eval-only CUBIN. EH2 clears prelaunch and can pass module load with an entry-pruned CUBIN, but now faults with CUDA error 700 at the first step sync before stdout/cycles comparison. | Use CPU-parallel full-program control as the default. Keep GPU work for bounded probes, portability, and root-cause isolation rather than claiming speedup. |
| gateGPT `tb_exp` data-backed vector sequence | Narrow GPU-favorable evidence | Resident 103-state probe passes 7/7 with `wall_time_ms_median=0.93`, CPU Verilator median `28.96515399334021 ms`, and observed GPU wall ratio `31.145326874559363x`. | Good GPU candidate when many independent vector states share one small regular datapath. Broaden before making a general gateGPT usefulness claim. |
| CIRCT `dense_matmul_tile` scientific lane | Scoped GPU-favorable at batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the same 2x2 tile with `inner_repeat=1000` records `64x1` end-to-end speedup `0.425926x` CPU-favorable, `256x1` `1.29699x` GPU-favorable, and `1024x1` `4.83185x` GPU-favorable. Kernel-only speedups are `2.51925x`, `7.76652x`, and `30.1806x`. | Useful when many independent scientific tiles/states amortize transfer and launch overhead; not evidence for full-design Verilator/RTLMeter speedup. |
| CIRCT `batched_reduction` scientific lane | Scoped GPU-favorable at batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the 8-input reduction with `inner_repeat=1000` records `64x1` end-to-end speedup `0.178523x` CPU-favorable, `256x1` `1.22712x` GPU-favorable, and `1024x1` `3.5003x` GPU-favorable. Kernel-only speedups are `4.24892x`, `7.92091x`, and `28.0256x`. | Confirms the current useful region is many independent low-observable scientific states; 64-state batches are still too small end-to-end. |
| CIRCT `stencil_2d_tile` scientific lane | Scoped GPU-favorable only at larger batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the 5-point tile with `inner_repeat=1000` records `64x1` end-to-end speedup `0.127491x` CPU-favorable, `256x1` `0.777396x` CPU-favorable, and `1024x1` `1.78392x` GPU-favorable. Kernel-only speedups are `2.27716x`, `7.28139x`, and `29.1859x`. | Neighbor-style/lightweight kernels need a larger batch to amortize transfer and launch overhead; this argues for candidate-specific thresholds, not one global `256x1` rule. |
| CIRCT `softmax_exp_pipeline` scientific lane | Scoped GPU-favorable at batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the exp/softmax-style polynomial pipeline with `inner_repeat=1000` records `64x1` end-to-end speedup `0.601074x` CPU-favorable, `256x1` `1.86415x` GPU-favorable, and `1024x1` `5.75945x` GPU-favorable. Kernel-only speedups are `2.60554x`, `6.37916x`, and `26.7024x`. | Supports treating microGPT-style matmul/reduction/softmax arithmetic as GPU candidates when batched; token/control state remains a separate CPU or new-mapping bucket. |
| CIRCT `microgpt_math_block` scientific lane | Scoped GPU-favorable at batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the composite dense-dot, softmax/exp-like, and reduction block with `inner_repeat=1000` records `64x1` end-to-end speedup `0.239753x` CPU-favorable, `256x1` `1.2195x` GPU-favorable, and `1024x1` `4.23625x` GPU-favorable. Kernel-only speedups are `2.01551x`, `7.56732x`, and `29.6779x`. | This is the first measured direct microGPT-style composite math block; still not full microGPT execution, but stronger than a partition-only claim. |
| CIRCT `microgpt_attention_head` scientific lane | Scoped GPU-favorable at batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the source-derived two-token attention-head slice with `inner_repeat=1000` records `64x1` end-to-end speedup `0.602488x` CPU-favorable, `256x1` `1.8243x` GPU-favorable, and `1024x1` `6.41385x` GPU-favorable. Kernel-only speedups are `2.57215x`, `5.84249x`, and `28.8371x`. | This is the first measured attention-head slice derived from actual `third_party/microgpt.py`; still not full block-size microGPT inference. |
| CIRCT `attention_head4_hls_friendly` source variant | Scoped direct-callsite improvement | `reports/scientific_circt_hls_attention_head4.json` materializes four explicit independent attention heads, lowers FIRRTL to SystemVerilog, builds Verilator and a separate CUDA shared library, and compares the Verilator CPU output buffer against the GPU output buffer with zero mismatches. The scoped bridge-wall speedup is `13.301119215779238x` versus the direct-callsite baseline `6.126758590128443x`; GPU end-to-end speedup is `14.585880739265654x`. | HLS-style source/IR reshaping is a stronger lever than small late LLVM/Verilator tweaks for this measured arithmetic class. This is not full microGPT, automatic HLS rewrite, PCIe framing, or RTLMeter evidence. |
| CIRCT `microgpt_mlp_slice` scientific lane | Scoped GPU-favorable only at larger batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the reduced-width source-derived MLP slice with `inner_repeat=1000` records `64x1` end-to-end speedup `0.339622x` CPU-favorable, `256x1` `0.333924x` CPU-favorable, and `1024x1` `2.28894x` GPU-favorable. Kernel-only speedups are `1.36729x`, `5.59061x`, and `24.0632x`. | The `mlp_fc1 -> ReLU -> mlp_fc2` shape is GPU-useful when enough independent states are batched, but this light slice needs `1024x1`; still not full hidden-width microGPT MLP inference. |
| CIRCT `mlp4_hls_friendly` source variant | Scoped direct-callsite improvement | `reports/scientific_circt_hls_mlp_block_variants.json` materializes four explicit independent MLP slices per state, lowers FIRRTL to SystemVerilog, builds a Verilator CPU callsite and CUDA shared library, and matches CPU/GPU output plus checksum with zero mismatches. Bridge-wall speedup improves from the baseline MLP slice `2.28894x` to `9.922827450510521x`; GPU end-to-end speedup is `11.464384891502785x`. | Positive evidence that explicit independent-unit reshaping helps light MLP arithmetic once it raises arithmetic density enough. Not full microGPT or automatic HLS rewriting. |
| CIRCT `microgpt_block_slice` scientific lane | Scoped GPU-favorable at batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the source-derived one-token/two-key block-level slice with `inner_repeat=1000` records `64x1` end-to-end speedup `0.52329x` CPU-favorable, `256x1` `1.70084x` GPU-favorable, and `1024x1` `5.75973x` GPU-favorable. Kernel-only speedups are `2.6523x`, `7.66483x`, and `32.0863x`. | This combines attention-style aggregation, residual-style addition, and MLP-style arithmetic from the microGPT block structure; still not full `block_size` microGPT inference. |
| CIRCT `block2_hls_friendly` source variant | Scoped direct-callsite non-improvement | The two-independent-block variant lowers and matches CPU/GPU output plus checksum with zero mismatches, but bridge-wall speedup is `5.56609843788867x` versus the baseline block slice `5.75973x`. GPU end-to-end speedup is `7.076745304097536x`. | The block slice was already GPU-favorable; duplicating two independent blocks did not improve the direct-callsite bridge ratio. Do not promote this reshaping without more batch or arithmetic density. |
| CIRCT `microgpt_inference_slice` scientific lane | Scoped GPU-favorable at batch scale | CIRCT-generated SystemVerilog passes Verilator CPU reference. CUDA timing for the source-derived two-token inference slice with `inner_repeat=1000` records `64x1` end-to-end speedup `0.249726x` CPU-favorable, `256x1` `1.24281x` GPU-favorable, and `1024x1` `3.62419x` GPU-favorable. Kernel-only speedups are `2.3037x`, `4.15142x`, and `14.944x`. | This adds token/position embedding-style arithmetic, KV-cache-style reuse, token1 attention over token0 and itself, residual/MLP-style arithmetic, and logit-style outputs; still not full `block_size` microGPT execution or training/autograd. |
| CIRCT `inference2_hls_friendly` source variant | Scoped direct-callsite improvement | The two-independent-inference variant lowers and matches CPU/GPU output plus checksum with zero mismatches. Bridge-wall speedup improves from the baseline inference slice `3.62419x` to `9.799333107174757x`; GPU end-to-end speedup is `12.486420847688292x`. | Positive evidence that source/IR reshaping still helps a fuller two-token inference-style slice, not only isolated attention or MLP arithmetic. Still not full microGPT execution. |
| gateGPT `tb_core` token sequence | GPU-correct but CPU-negative | Ordering-aware token-loop path validates `16/16` states with `9` launches over `30618` logical launches, but GPU wall is `363.628 ms` versus CPU oracle `81.95496001280844 ms` (`4.436924866331091x` slower). Guarded bitmap remains slower (`354.541 ms`, `4.326046891421703x` slower). | Do not treat more launch fusion as the main lever. Next useful work is structural partitioning or larger state-scale testing, not a small LLVM peephole pass. |
| Generic Verilator/RTLMeter full design | Not proven useful | `reports/rtlmeter_hybrid_advantage_summary.json` counts `gpu_sidecar_favorable=0`, `gpu_sidecar_unfavorable=4`, `launch_feasibility_blocked=1`, and recommends CPU-parallel control with bounded GPU probes. | Hybrid selection should be compile-time candidate selection plus runtime shape/timing confirmation; unsupported cases fail closed. |

Scientific-compute CIRCT candidate search has moved past the initial plan-only
blocker for the first candidate. The repo-local CIRCT package can be enabled
with `source artifacts/toolchains/circt-firtool-1.149.0/env.sh`, and
`reports/scientific_circt_gpu_candidate_plan.json` now records CIRCT tools as
available in that environment. `dense_matmul_tile` has a reproducible
materializer at `src/tools/scientific_circt_dense_matmul_tile.py`; it emits
FIRRTL, lowers it through `firtool` to SystemVerilog, builds with Verilator, and
passes the CPU reference observable `TEST PASSED dense_matmul_tile_cpu_reference
cases=4`. The generated artifacts remain under
`artifacts/scientific_circt/dense_matmul_tile/` and are not source of truth.
Lowered LLVM IR suitability has been run on the eval datapath entry; the
entry-scoped report recommends `gpu_state_parallel`, while whole-generated-code
analysis remains polluted by Verilator support code and is not used as a
speedup claim. The first CUDA timing gate now measures the same 2x2 tile as a
batched state-parallel workload. With `inner_repeat=1000`, `64x1` remains
CPU-favorable end-to-end (`0.425926x`), while `256x1` (`1.29699x`) and `1024x1`
(`4.83185x`) are GPU-favorable end-to-end. Kernel-only speedups are positive at
all measured shapes. This is scoped evidence for the dense scientific tile
only; it is not a general RTL, Verilator, RTLMeter, or automatic partitioning
claim.
`reports/scientific_circt_dense_matmul_tile_hybrid_advantage.json` now folds
those three timing reports into a common scientific hybrid summary:
`gpu_end_to_end_favorable=2`, `cpu_end_to_end_favorable=1`,
`gpu_kernel_favorable=3`, and the first end-to-end GPU-favorable shape is
`256x1`.
`reports/scientific_circt_testbench_hybrid_advantage.json` now aggregates
`dense_matmul_tile`, `batched_reduction`, `stencil_2d_tile`,
`softmax_exp_pipeline`, `microgpt_math_block`, and
`microgpt_attention_head`, `microgpt_mlp_slice`, `microgpt_block_slice`, and
`microgpt_inference_slice`: twenty-seven measured reports, sixteen end-to-end
GPU-favorable rows, eleven CPU-favorable rows, and twenty-seven kernel-favorable
rows. Dense matmul, reduction, softmax/exp, the composite microGPT-style math
block, the source-derived microGPT attention-head slice, and the block-level
slice plus the two-token inference slice first become end-to-end GPU-favorable
at `256x1`; stencil and the reduced-width microGPT MLP slice first become
end-to-end GPU-favorable at `1024x1`.
`reports/scientific_circt_gpu_selection_policy.json` converts this into a
compile-time policy: measured candidates use GPU state-parallel execution only
for `steps=1` and at or above their candidate-specific measured boundary; below
that boundary, CPU remains the end-to-end default. The policy is currently ready
for `dense_matmul_tile`, `batched_reduction`, `stencil_2d_tile`,
`softmax_exp_pipeline`, `microgpt_math_block`, and
`microgpt_attention_head`, `microgpt_mlp_slice`, `microgpt_block_slice`, and
`microgpt_inference_slice`.
The next scientific lane should move from these
source-derived slices toward a fuller microGPT IR lowering: keep matmul,
attention-head arithmetic, MLP arithmetic, block-level arithmetic, reductions,
two-token inference arithmetic, and softmax-like arithmetic structurally visible for CIRCT/GPU selection, while keeping
token/control state in CPU or a separately measured mapping.
`reports/scientific_circt_microgpt_ir_partition_probe.json` now performs that
projection without claiming microGPT execution. At `nstates=256,steps=1`, it
classifies 8 of 10 microGPT-style nodes as GPU state-parallel candidates
(`attention`, `mlp`, and `normalization`) and leaves token-loop control plus
KV-cache state update in the CPU/new-mapping bucket. This records the current
interpretation of the gateGPT question: gateGPT appears to be FPGA-oriented and
is still valuable as a representative external RTL testbench, but direct
microGPT IR/CIRCT is the cleaner next surface for preserving regular arithmetic
before RTL/control lowering hides the GPU-friendly structure.
`reports/scientific_circt_gategpt_microgpt_compare.json` makes the comparison
explicit and now scans the actual `third_party/microgpt.py` source. The scan
finds `linear`, `softmax`, `rmsnorm`, and `gpt`, plus attention, MLP, and
autograd-training structure with `n_layer=1`, `n_embd=16`, `block_size=16`, and
`n_head=4`; no local license file is present next to that source. Direct
microGPT/CIRCT is preferred for GPU partition discovery because the regular
arithmetic remains visible and `microgpt_math_block` plus
`microgpt_attention_head` plus `microgpt_mlp_slice` plus
`microgpt_block_slice` plus `microgpt_inference_slice` have generated
SystemVerilog, Verilator CPU reference, and GPU-favorable end-to-end timing
with candidate-specific thresholds. gateGPT remains preferred as the external
RTL integration lane: it has
six CPU Verilator testbenches and GPU kernel-launch smoke coverage, `tb_exp` is
a narrow regular-datapath positive case (`31.145326874559363x` observed wall
speedup), but `tb_core` remains a stateful token/control negative case
(`0.08117848829459036x` wall speedup versus CPU in the distinct-state
pair-cycle-loop comparison) and broad GPU stdout/PASS/finish authority is not
claimed.
`reports/scientific_circt_evidence_audit.json` now checks the scientific CIRCT
lane end-to-end evidence and records `status=evidence_ready`,
`candidate_count=9`, `ready_candidate_count=9`, and dispatch-matrix measured
speedup evidence attached to all 27 candidate/shape rows.
`reports/scientific_circt_hybrid_protocol.json` now converts the measured
policy into a compile-time CPU/GPU handoff protocol. It records
`status=protocol_ready`, `ready_candidate_count=9`,
`source_variant_ready_count=3`, dispatch key
`candidate,source_variant,nstates,steps`, `required_steps=1`, one GPU launch
per candidate batch, and CPU fallback when a candidate or source variant is
unmeasured or below its measured threshold. For the microGPT-style lane, CPU
keeps token-loop control, sampler/observable authority, and full KV-cache state
authority; GPU owns only the measured arithmetic batch. For
`microgpt_inference_slice`, the baseline threshold handoff is `nstates=256`
with logical payload estimate `1024` input bytes, `6144` output bytes, and
`7168` roundtrip bytes. For `inference2_hls_friendly`, the promoted
source-variant threshold is `1024x1` with `8192` input bytes, `49152` output
bytes, and `57344` roundtrip bytes. These are logical payload bytes only;
allocator/alignment/PCIe framing, runtime ABI authority, and automatic HLS
rewriting remain non-claims. The same tool now emits single dispatch
decisions: `microgpt_inference_slice,nstates=256,steps=1` selects
`select_gpu_state_parallel`; `microgpt_inference_slice,inference2_hls_friendly,
nstates=1024,steps=1` selects `promote_to_hls_gpu`; `block2_hls_friendly`
selects `keep_baseline_gpu_or_cpu`; `64x1`, unknown candidates/variants, and
step mismatches select CPU with fail-closed reasons.
`reports/scientific_circt_hybrid_dispatch_matrix.json` expands the same
protocol into the current measured shape matrix: 27 candidate/shape decisions,
16 GPU selections, 11 CPU selections, and measured speedup evidence attached to
all 27 rows. `64x1` is all CPU, `256x1` selects GPU for seven of nine
candidates, and `1024x1` selects GPU for all nine. This remains compile-time
dispatch evidence over measured timing reports only; it is not runtime ABI
authority, PCIe framing evidence, RTLMeter evidence, full microGPT execution,
or automatic partitioning.
The matrix also ranks the 16 GPU-selected rows for runtime integration; the
current top row is `microgpt_attention_head` at `1024x1` with measured
end-to-end speedup `6.41385x`. The next required evidence is broader hybrid
runtime entrypoint wiring plus amortized integration timing.
The same matrix now expands HLS-friendly `source_variants` over the same shape
points. It records 12 variant decisions: three `promote_to_hls_gpu` rows at
`1024x1`, three `keep_baseline_gpu_or_cpu` rows for `block2_hls_friendly`, and
six CPU fallbacks below the promoted variant threshold. The promoted runtime
handoff candidate queue ranks `attention_head4_hls_friendly`
(`13.301119215779238x`), `mlp4_hls_friendly` (`9.922827450510521x`), and
`inference2_hls_friendly` (`9.799333107174757x`). The selected next runtime
boundary is `inference2_hls_friendly`, because attention already has the scoped
runtime evidence lane and inference is the fuller token/cache slice despite
MLP being slightly faster.
`reports/scientific_circt_source_variant_runtime_handoff.json` now re-runs that
selected boundary as an executable runtime handoff measurement. It records
`status=runtime_handoff_boundary_measured` for
`inference2_hls_friendly,1024x1`, uses the generated direct-callsite binary and
GPU shared library from the HLS variant report, and keeps token-loop,
sampler/output, and KV-cache authority on CPU while GPU owns the
HLS-friendly batched arithmetic source variant. CPU/GPU output equality and
control-checksum equality hold. The observed per-integration-batch timing is:
CPU `1.5594159200000002 ms`, GPU end-to-end `0.1436130933333333 ms`, GPU kernel
`0.04580693379044533 ms`, bridge wall `0.16406808 ms`, CPU-to-bridge-wall
speedup `9.504688053885925x`, GPU end-to-end speedup
`10.858452274825085x`, and kernel speedup `34.0432286328947x`. Logical payload
is `8192` input bytes and `49152` output bytes. This closes the selected
source-variant runtime-boundary measurement but is still not full microGPT
execution, PCIe framing evidence, RTLMeter evidence, automatic HLS rewriting,
or a production runtime boundary. The next runtime step is to factor this
source-variant boundary into the broader `src/hybrid` or direct Verilator
callsite path rather than relying only on the generated direct binary.
`reports/scientific_circt_source_variant_verilator_entrypoint.json` now closes
that next step for the selected source variant. The checked-in bridge
`src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` compiles
against the generated `inference2_hls_friendly` Verilator `obj_dir`, loads
`libinference2_hls_friendly_gpu.so`, compares Verilator CPU outputs with GPU
outputs, and times the GPU-only handoff path. The report records
`status=src_hybrid_verilator_runtime_handoff_measured`,
`verilator_callsite_used=true`, CPU/GPU output equality, and control-checksum
equality. Per integration batch, CPU is `1.51916184 ms`, GPU end-to-end is
`0.13439465333333334 ms`, GPU kernel is `0.045233493745326994 ms`, bridge wall
is `0.15218008 ms`, CPU-to-bridge-wall speedup is `9.982658965614949x`, GPU
end-to-end speedup is `11.3037371824018x`, and kernel speedup is
`33.58488841373086x`. This replaces the direct-binary-only boundary with a
checked-in `src/hybrid` Verilator-callsite bridge for the selected
`inference2_hls_friendly` slice. It is still scoped: no full microGPT
execution, PCIe framing evidence, RTLMeter evidence, automatic HLS rewriting,
or production runtime claim.
`reports/scientific_circt_source_variant_runtime_dispatcher.json` now routes
that same selected boundary through a reusable runtime dispatcher. The
dispatcher reads the HLS dispatch matrix, preserves the selected
candidate/source_variant/shape policy, rejects non-selected source variants,
and invokes the registered `src_hybrid_verilator_callsite_bridge` for
`inference2_hls_friendly,1024x1`. The report records
`status=runtime_dispatch_measured`, nested
`runtime_handoff_status=src_hybrid_verilator_runtime_handoff_measured`,
`verilator_callsite_used=true`, CPU/GPU output equality, and control-checksum
equality. Per integration batch, CPU is `1.5616191466666665 ms`, GPU end-to-end
is `0.12166281333333333 ms`, GPU kernel is `0.045206187069416044 ms`, bridge
wall is `0.14075793333333333 ms`, CPU-to-bridge-wall speedup is
`11.09435972584612x`, GPU end-to-end speedup is `12.83563238331603x`, and
kernel speedup is `34.54436766075257x`. This generalizes the first
source-variant bridge into a policy-checked dispatch surface, but still makes
no full microGPT execution, PCIe framing, RTLMeter, automatic HLS rewrite, or
production runtime-dispatcher claim.
`reports/scientific_circt_source_variant_runtime_dispatcher_soak_summary.json`
now records the selected one-hour dispatcher soak over the same
`inference2_hls_friendly,1024x1` boundary. It ran for `3600` seconds and
produced `2574` per-iteration reports under
`reports/one_hour_runtime_dispatcher/`. All `2574` reports passed
`status=runtime_dispatch_measured`, nested
`runtime_handoff_status=src_hybrid_verilator_runtime_handoff_measured`,
CPU/GPU output equality, and control-checksum equality. CPU-to-bridge-wall
speedup distribution was min `1.2956713528049701x`, p10
`8.363504353854227x`, median `10.731542472816859x`, p90
`11.829942667042333x`, max `12.793946412262754x`, and mean
`10.28419894271687x`; bridge wall per integration batch had median
`0.14407087333333335 ms`, p90 `0.18502854666666665 ms`, and max
`1.2186646533333334 ms`. The soak has `75` reports below `5x` bridge speedup
and `40` reports above `0.5 ms` bridge wall, so this is correctness/dispatch
stability evidence, not a new reviewed production speedup claim.
`reports/scientific_circt_source_variant_metadata.json` now records the
metadata surface needed before broadening bridge generation. It is
`source_variant_metadata_ready` with four complete rows for
`attention_head4_hls_friendly`, `mlp4_hls_friendly`,
`inference2_hls_friendly`, and `block2_hls_friendly`, including GPU symbols,
input/output layout, artifact paths, Verilator `obj_dir`, entrypoint kind,
runtime boundary kind, and fallback policy. The extracted input/output bytes
per state are `80/128`, `16/64`, `8/48`, and `24/32`.
`reports/scientific_circt_source_variant_runtime_dispatcher_multi.json` now
extends dispatch across that metadata-described source-variant set. It records
`status=multi_source_variant_dispatch_ready`: three promoted variants dispatch
to measured GPU boundaries, and one non-improving variant falls back to
CPU/baseline. `attention_head4_hls_friendly` uses the direct-callsite HLS
source-variant boundary with output/checksum equality and CPU-to-bridge-wall
speedup `11.31933596913315x`. `mlp4_hls_friendly` uses the same
direct-callsite boundary class with equality and speedup
`9.466548203869824x`. `inference2_hls_friendly` keeps the checked-in
`src_hybrid_verilator_callsite_bridge` with equality and speedup
`11.420283475548267x` in this run. `block2_hls_friendly` is not dispatched to
a new GPU boundary; it is recorded as `runtime_dispatch_fallback_baseline`
because its HLS-friendly speedup `5.56609843788867x` does not improve over the
baseline `5.75973x`. This is now a metadata-driven four-row source-variant
selection table with CPU/baseline fail-closed behavior, not broad full-design
acceleration evidence.
`reports/heavy_rtl_candidate_matrix.json` now records the PULP/NoC heavy RTL
candidate matrix generated by `src/tools/heavy_rtl_candidate_matrix.py`. It has
six rows: two PULP candidates and four NoC/TLUL-style candidates. The common
schema records source closure, template presence, build/run/compare evidence,
CPU/hybrid timing evidence, state-parallel shape, single-state repeated-step
shape, and the promote/fallback/resident-required policy. The current policy
counts are five `promote_state_parallel_measurement` and one
`resident_or_shape_sweep_required`. `pulp_paged_attention_kv_score 64x1`,
`tlul_socket_1n 32x1`, `tlul_socket_m1 32x1`, and BlackParrot
`bsg_wormhole_router` at `32x1`, `64x1`, `128x1`, and `256x1` have repeat-count-3
median reports in addition to the prior `pulp_ita_mha` row. All measured
reports pass coverage-output equivalence in every sample with mismatch count
`0`; median CPU-to-hybrid wall speedups are `159.01406799531068x`,
`75.23948126801153x`, `77.24226694915255x`, and BlackParrot
`32.76216804527645x` at `32x1`, `158.28447339847992x` at `64x1`, and
`259.4919886899152x` at `128x1`, and `651.817697228145x` at `256x1`. BlackParrot now
has `config/slice_launch_templates/blackparrot_bsg_wormhole_router.json`, the
coverage overlay `overlays/rtlmeter/designs/BlackParrot/src/bsg_wormhole_router_gpu_cov_tb.sv`,
the coverage gate `config/scaling_gates/blackparrot_bsg_wormhole_router_source_gate.json`,
and repeat-count-3 packet-pattern coverage-output-equivalent timing through
`256x1`. This is shape-extension repeat-median-backed promote evidence rather
than a `32x1`-only candidate. The resident/multi-step definition gate now lives
at `config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json`.
It defines a `256x4` resident packet-pattern timing target and records the
resolved pre-execution blocker
`template_runner_has_no_resident_schedule_surface` plus the remaining blocker
`blackparrot_packet_pattern_patch_script_not_materialized`.
`run_hybrid_template.py` now has a dry-run resident command-plan surface with
`--resident-steps`, explicit `--patch-script`, resident-specific candidate dump
paths, and resident-specific compare-report paths. The next stabilizing work is
materializing the BlackParrot packet-pattern patch script, or recording that
patch-script source as the named FC-071 blocker. Source-closure statuses are normalized at the
row top level: complete for `pulp_ita_mha`,
template-present but not recorded for `pulp_paged_attention_kv_score`,
source-backed overlay statuses for the two TLUL sockets,
`broad_structural_spread` for `tlul_fifo_sync`, and
`source_backed_template_defined` for BlackParrot. `tlul_fifo_sync` has favorable
frozen execution-profile timing (`3.5951481185001524x`) but needs resident or
shape-sweep evidence before a broader policy claim. This is scoped
candidate evidence and triage only, not broad RTL speedup, native Verilator
option support, arbitrary dependency inference, or automatic optimal GPU
allocation.
`reports/scientific_circt_runtime_handoff_abi.json` now converts that top row
into the first runtime handoff ABI definition. It records
`status=handoff_abi_ready`, array-of-structs input/output layout, 20 input
bytes/state, 32 output bytes/state, and 53,248 logical roundtrip bytes for
1,024 states. CPU retains sequence/KV-cache authority and GPU owns only the
  measured attention-head arithmetic batch. The adapter and entrypoint evidence
  below closes the first CPU-vs-GPU equality, warmed fused adapter timing, and
  broader `src/hybrid` C-bridge runtime boundary timing gates. Direct Verilator
  generated-callsite wiring remains open. This is not PCIe framing evidence,
  full microGPT execution, RTLMeter evidence, or automatic partitioning.
`reports/scientific_circt_runtime_handoff_adapter.json` now runs the first
ABI-backed adapter correctness gate for the same candidate/shape. It records
`status=adapter_correctness_passed`, observed input bytes `20480`, observed
output bytes `32768`, ABI byte-count matches, CPU-vs-GPU output equality, and
`mismatch_count=0` for the 1,024-state batch. The same adapter report now
records an adapter-local integration loop with `inner_repeat=1000` and
`integration_batches=15`: CPU `0.7769709466666667 ms`, GPU end-to-end
`0.12586719999999998 ms`, GPU kernel `0.027211092884341877 ms`, CPU-to-GPU
end-to-end speedup `6.17294216973657x`, and CPU-to-GPU kernel speedup
`28.553463470545143x` per integration batch. It also builds
`libmicrogpt_attention_head_handoff_adapter.so` for in-process entrypoint
timing and exports a GPU output-buffer symbol for Verilator callsite comparison.
This is scoped positive
runtime-adapter evidence: the warmed fused attention-head handoff preserves the
measured `microgpt_attention_head` GPU-favorable region after adapter-local
amortization. It is not a broad runtime speedup claim, PCIe framing, full
microGPT, RTLMeter, automatic partitioning, or direct Verilator runtime evidence.
`reports/scientific_circt_runtime_entrypoint.json` now measures the first
subprocess-free in-process adapter-library entrypoint. It records
`status=in_process_entrypoint_timing_measured`, `subprocess_used=false`,
CPU-vs-GPU output equality, matching correctness checksums, and matching timed
GPU checksum. The correctness warmup is excluded from the timed hybrid path. The
timed GPU-only library call records wall `8.331281000209856 ms`, or
`0.11108374666946474 ms` per integration batch, versus CPU baseline
`0.78472712 ms` per integration batch. The resulting
`cpu_to_in_process_wall_speedup=7.0642838716540135x` is CPU-favorable; adapter
GPU end-to-end is `0.09972410666666667 ms` per integration batch and kernel is
`0.026255359500646593 ms`. This is the first positive subprocess-free runtime
entrypoint evidence for `microgpt_attention_head,1024x1`. It is not a direct
Verilator entrypoint, PCIe framing evidence, full microGPT execution, RTLMeter
evidence, automatic partitioning, or production runtime evidence.
`reports/scientific_circt_broader_runtime_entrypoint.json` now measures the same
adapter shared library from a `src/hybrid` C bridge. The bridge is compiled from
`src/hybrid/scientific_circt_adapter_bridge.c`, loads
`libmicrogpt_attention_head_handoff_adapter.so` with `dlopen`/`dlsym`, runs the
CPU+GPU correctness call as warmup, then times the GPU-only adapter symbol inside
the C process. The report records `status=broader_hybrid_entrypoint_timing_measured`,
`subprocess_used_for_adapter=false`, CPU-vs-GPU output equality, matching
correctness checksums, and matching timed GPU checksum. The bridge-internal timed
hybrid path records wall `8.079087 ms`, or `0.10772116 ms` per integration batch,
versus CPU baseline `0.7869408533333333 ms` per integration batch. The resulting
`cpu_to_bridge_hybrid_wall_speedup=7.305350715990556x` is CPU-favorable; adapter
GPU end-to-end is `0.09732182666666667 ms` per integration batch and kernel is
`0.026241706187526383 ms`. This closes the broader `src/hybrid`
runtime-boundary evidence for the scoped adapter.
`reports/scientific_circt_verilator_callsite_entrypoint.json` now measures the
same GPU adapter from a direct Verilator-generated CPU callsite. The bridge is
compiled from `src/hybrid/scientific_circt_verilator_callsite_bridge.cpp` against
`artifacts/scientific_circt/microgpt_attention_head/obj_dir`, calls `Vsim::eval()`
for the CPU path, compares the 1,024-state Verilator output buffer with the GPU
adapter output buffer, and then times the GPU-only adapter symbol. The report
records `status=direct_verilator_callsite_entrypoint_timing_measured`,
`verilator_callsite_used=true`, `subprocess_used_for_adapter=false`,
`mismatch_count=0`, and matching Verilator/GPU control checksums. The timed hybrid
path records bridge wall `10.028488 ms`, or `0.13371317333333332 ms` per
integration batch, versus Verilator CPU callsite baseline `0.8192283333333333 ms`
per integration batch. The resulting
`cpu_to_bridge_hybrid_wall_speedup=6.126758590128443x` is CPU-favorable; adapter
GPU end-to-end is `0.10795985333333334 ms` per integration batch and kernel is
`0.026105172832806906 ms`. This satisfies the scoped direct Verilator callsite
entrypoint goal for `microgpt_attention_head,1024x1`, but it is still not full
microGPT execution, PCIe framing evidence, RTLMeter evidence, automatic
partitioning, or production runtime evidence.
`reports/scientific_circt_hls_attention_head4.json` now tests the next HLS-style
source variant for the same direction. It uses four explicit independent
attention heads per state, lowers through FIRRTL/SystemVerilog, builds the
Verilator CPU callsite, builds the GPU arithmetic as a separate CUDA shared
library, and compares the output buffer/checksum before timing. The result is
`status=hls_variant_improved`, `mismatch_count=0`, CPU/GPU output and checksum
equality true, Verilator CPU `3.4998690533333336 ms` per integration batch,
GPU end-to-end `0.2399491066666667 ms`, GPU kernel
`0.12229589293400446 ms`, and bridge wall
`0.26312590666666663 ms` per integration batch. The scoped bridge-wall speedup
is `13.301119215779238x`, improving over the prior direct-callsite baseline
`6.126758590128443x` by `7.174360625650795x`. The interpretation is that
source/IR-level arithmetic shaping can materially improve this class; it is
still not full microGPT execution, automatic HLS rewriting, PCIe framing,
RTLMeter evidence, or production runtime evidence.
`reports/scientific_circt_hls_mlp_block_variants.json` extends the same HLS-style
source-variant measurement to MLP, block, and inference slices. `mlp4_hls_friendly`
records `status=hls_variant_improved`, output/checksum equality,
`mismatch_count=0`, baseline speedup `2.28894x`, bridge-wall speedup
`9.922827450510521x`, and positive delta `7.633887450510521x`.
`block2_hls_friendly` records output/checksum equality and `mismatch_count=0`,
but `status=hls_variant_measured_no_speedup_improvement`: its bridge-wall
speedup `5.56609843788867x` is below the baseline block-slice speedup
`5.75973x`. `inference2_hls_friendly` records output/checksum equality and
improves from baseline `3.62419x` to `9.799333107174757x`. The refreshed
`reports/scientific_circt_gpu_selection_policy.json` now integrates these HLS
reports as `source_variants`: `attention_head4_hls_friendly`,
`mlp4_hls_friendly`, and `inference2_hls_friendly` select
`promote_to_hls_gpu`, while `block2_hls_friendly` selects
`keep_baseline_gpu_or_cpu`. Together, the rule is now measurable: explicit
independent-unit source/IR reshaping should be promoted when equality holds and
direct-callsite speedup improves; otherwise keep the baseline GPU/CPU decision.

Vortex progress update: `reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json`
now validates the real `Vortex:mini:hello` materialized runtime inputs. The
buffer artifacts are present, H2D bytes are `37224`, initial D2H bytes are `88`,
the materialized DCR table matches the `9` write schedule, and
`src/hybrid/vortex_lowered_tb_runtime_sequence.h` exposes the runtime sequence
call and authority fields. This advances the first-gate preparation, but it is
still not generated lowered-TB integration, GPU execution, observable
authority, CPU-vs-hybrid timing, or a speedup/usefulness claim.
`reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json` now
compiles and runs generated lowered-TB-shaped C harness code that consumes those
real materialized artifacts and calls
`vortex_lowered_tb_invoke_runtime_sequence`. The separate generated `Vsim`
real-CUDA materialized smoke now uses the root-storage callback and the
single-entry cubin; it reaches `after_cuMemcpyHtoDRootStorage` and
`after_cuCtxSynchronize` and exports `memory_post_condition` authority before
observable authority, CPU-vs-hybrid timing, and speedup/usefulness evidence.
`reports/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json` now
compiles and runs generated lowered-TB-shaped C code that consumes the real
materialized memory artifacts through `vortex_memory_model_device.h`. It records
`block_count=576`, `initial_post_mismatches=48`,
`post_replay_mismatches=0`, and `stdout_chars=12`. This advances the bridge
from generic helper availability to generated memory-access smoke, but still
does not prove real Verilator generated lowered-TB integration, GPU execution,
observable authority, CPU-vs-hybrid timing, or speedup/usefulness.
`reports/rtlmeter_vortex_cpu_reference_summary.json` now records the native
RTLMeter CPU reference as passed: stdout contains `TEST PASSED`, Verilog
`$finish` is observed, post hook passed, `9` DCR writes were printed, and the
execute metrics are `0.22s`, `40897` clocks, and
`185.89545454545453 kHz`. `reports/rtlmeter_vortex_hybrid_candidate_summary.json`
records the current hybrid candidate attempt as
`hybrid_candidate_proxy_handoff_observed_timing_missing`: the
PATH-selected wrapper captures the requested sidecar mode and `1x1` shape, the
handoff metadata is ready, the stdout/cycles plan targets `Vortex:mini:hello`,
the reviewed authority registry source closure is present, and direct-native
RTLMeter stdout/cycles observation reaches `40897` cycles with `TEST PASSED`.
The reviewed proxy handoff is observed through source patch metadata, but GPU
execution, timing, and speedup claims remain false. It still fails closed for
hybrid measurement because Vortex observable authority and CPU-vs-hybrid timing
are not present.

## MobileViT CPU-Kick State

MobileViT remains CPU-kick evidence:

- `mobile_vit_cpu_kick_imagenet_accuracy`
- `mobile_vit_cpu_kick_rtl_hybrid_boundary`
- `apple/mobilevit-small`
- `complete_full_imagenet_validation_cpu_kick_accuracy_measured`
- `top-1 0.77022`
- `mobile_vit_cpu_kick_rtl_proxy_host_probe`
- `mobile_vit_hybrid_imagenet_eval_gate`

The historical MobileViT gate is `records/scaling_gates/mobile_vit_hybrid_imagenet_eval_gate.json`. It defines `src/tools/mobile_vit_hybrid_imagenet_eval.py`, which splits an ImageNet manifest into `mobile_vit_cpu_kick_rtl_proxy` hybrid control-boundary batches while computing top-1/top-5 from CPU-kick predictions. A two-image scoped ImageNet run from the local HF parquet cache executed through hybrid and passed coverage-output equivalence; the follow-up `limit 128` scale-up also executed as one `cfg_batch_length=128` hybrid batch and passed coverage-output equivalence. The retained 128 summary is `reports/mobile_vit_hybrid_128_summary.json`: `evaluated_count=128`, `top1_accuracy=0.7734375`, `top5_accuracy=0.953125`, `coverage_output_equivalence_complete=true`. The completion audit is `records/scaling_gates/mobile_vit_hybrid_imagenet_limit_128_scaleup_completion_audit.json`. This is still not a claim that MobileViT numerical logits are produced by RTL or that the full 50k validation set was rerun through hybrid.
