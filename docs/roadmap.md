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

Current weak point: #2 / FC-037 has a refreshed VeeR-EL2 `hello` timing result,
and the current GPU sidecar path is still much slower than serial CPU, while the
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

`modern_llm_serving_rtl_hybrid_conditions` is complete for the scoped RTL-harness condition-finding objective. The first scoped executable Verilator-facing `--use-gpu` adapter and PATH-selected wrapper path are complete. The current work is the gateGPT `tb_core` ordering-aware token-loop schedule-integration gate after the padded-start path remained CPU-negative.

Current priority:

`partition_local_eval_continuation_guard_cpu_oracle_validation`

Next concrete action:

`clone_compact_cluster_body_into_outline_callee_and_rewire_control_flow`

Current source artifact:

`for_codex/issues.md`

GitHub tracking: #69 / FC-069 is the active gateGPT `tb_core`
ordering-aware token-loop task. #2 / FC-037 remains the RTLMeter timing lane,
but it is not the current implementation blocker.
#1 records the owner goal and #46 remains the native-path umbrella; #59/#57/#58
remain related native-path tasks.

Current alignment check: `config/selection.json`, `docs/status.md`, `README.md`, and this roadmap agree on the **current_priority**, **current_next_action**, and **current_priority_source_artifact** strings above. Historical completion gates may still list older `next_task` labels; treat `selection.json` as authoritative for the open pointer.

`gateGPT` is now a candidate external testbench, not a new active seed or
vendored dependency. The accepted local gate keeps the raw-checkout
`sim/tb_mathops.v` Verilator lint-only smoke, then runs `tb_mathops`, `tb_exp`,
`tb_matvec`, `tb_norm`, `tb_attn`, and `tb_core` in an evaluation-only
normalized copy under `artifacts/gategpt_local_eval/gateGPT`, recorded in
`reports/gategpt_testbench_probe.json` with
`status=gategpt_gpu_smoke_and_tb_mathops_sequence_compare_passed_without_pass_fail_export`.
The current LLVM pass path can emit PTX for those normalized obj_dirs and the
runtime can launch each kernel once with zero-initialized state. It also drives
the full `tb_mathops` six-divider plus seven-sqrt sequence through a byte-level
clocked patch script and compares DUT outputs against CPU reference values. The
selected `tb_mathops` PASS policy is now accepted as a manifest-consuming
DUT-output compare with final `errors == 0`, without claiming stdout PASS/FAIL
or `$finish` export. The remaining gate is general PASS/FAIL authority:
gateGPT initial/readmem/display/finish testbench behavior is not represented as
a GPU execution authority. The probe now extracts the CPU Verilator stdout and
finish authority for all six normalized benches into a generated manifest:
all six have PASS plus `$finish`, `tb_core` carries structured token/cycle stdout
lines, and the data-backed benches are marked as needing readmem/init-state
contracts before GPU semantic equivalence can be claimed. `tb_exp`, `tb_matvec`,
`tb_norm`, and `tb_attn` now have those contracts. The generated GPU-output
mapping plan is now bench-complete for structured DUT/root-state outputs:
`tb_mathops` is covered through the selected DUT-output policy, `tb_exp` is now
covered by a bench-specific vector-sequence DUT-output compare, and
`tb_matvec`/`tb_norm`/`tb_attn` are covered by bench-specific vmem output
sequence compares. `tb_core` is covered by a bench-specific structured
root-state sequence compare for token and cycle lines. All six normalized
gateGPT benches now have bench-specific GPU output manifests, while general
stdout/finish export and usefulness remain unclaimed.
`tb_exp` is now the first data-backed bench with that contract defined:
`generated/test_exp_z.hex` and `generated/test_exp_e.hex` are recorded as
103-entry signed 16-bit preload arrays targeting `tb_exp__DOT__zs` and
`tb_exp__DOT__es`, and the field manifest identifies the clock, input, pipeline,
interpolation, and array fields needed for the GPU vector-sequence compare.
That GPU vector-sequence run now compares all 103 cases and passes with zero
mismatches, so the bench-specific `tb_exp` DUT-output semantic claim is accepted.
The direct `eo` signal is absent from root state, so the probe reconstructs it
from `pos_r`, `big_r`, and `interp`. The observed blocker is no longer
readmem/source discovery or missing called helper definitions; `vlgpugen` keeps
top-level phase closures for root images, and the timing-scheduler-context pass
preserves trigger-bearing act phases instead of deleting their bodies.
`tb_norm` is now the next data-backed proof: the probe preloads
`generated/test_norm_in.hex` into `tb_norm__DOT__u_vmem__DOT__mem[0..23]`,
executes an explicit reset/start/clock sequence, observes `n_done`, and compares
`tb_norm__DOT__u_vmem__DOT__mem[64..87]` against
`generated/test_norm_out.hex`. The GPU vmem sequence passes 24/24 outputs with
zero mismatches, while stdout PASS/FAIL and `$finish` export remain unclaimed.
`tb_matvec` follows the same structural pattern: the probe preloads
`generated/test_in.hex` into `tb_matvec__DOT__u_vmem__DOT__mem[0..23]`, executes
an explicit reset/start/clock sequence, observes `mv_done`, and compares
`tb_matvec__DOT__u_vmem__DOT__mem[64..87]` against `generated/test_wq.hex`. That
GPU vmem sequence also passes 24/24 outputs with zero mismatches and no
stdout/finish export claim.
`tb_attn` follows the same structural pattern with three input windows:
`generated/test_attn_q.hex` is preloaded into
`tb_attn__DOT__u_vmem__DOT__mem[0..23]`, `generated/test_attn_k.hex` into
`tb_attn__DOT__u_vmem__DOT__mem[32..415]`, and `generated/test_attn_v.hex` into
`tb_attn__DOT__u_vmem__DOT__mem[448..831]`. The explicit GPU sequence observes
`a_done` and compares `tb_attn__DOT__u_vmem__DOT__mem[864..887]` against
`generated/test_attn_out.hex`; it passes 24/24 outputs with zero mismatches and
no stdout/finish export claim.
`tb_core` maps its structured stdout authority to root-state fields and runs a
multi-launch GPU token sequence: one launch per generated token, with each state
dump fed into the next launch via `--init-state`. The compare observes
`next_token`, `rng_out`, `cyc`, `reported`, `tot_cyc`, and `tot_tok`, matches
greedy tokens `1 12 1 25 1`, sampled tokens `18 15 19 16 8 15 4`, and the cycle
summary `CYCLES_PER_TOKEN=1157`, `AVG_CYCLES=1322 over 12 tokens (last=1489)`.
This passes as a structured correctness proof, but uses 14 GPU launches and
47,656 logical steps, so it is not throughput/usefulness evidence.
`tb_mathops` remains the first selected semantic-equivalence proof because its
CPU PASS authority reduces to `errors == 0` after six division and seven
square-root cases, and that proof is now satisfied by the manifest-consuming
13-case DUT-output compare. The next gate for gateGPT is therefore not another
`tb_mathops` or `tb_exp` source-discovery step; it is either explicitly
exporting the corresponding PASS/finish authority or measuring whether the
bench-specific scenarios can be batched usefully. The immediate
LLVM/runtime gap is not PTX emission, offset discovery, byte-level clock/start
patching, `tb_mathops` DUT-output comparison, the selected `tb_mathops` PASS
policy, the `tb_exp` vector contract, the `tb_matvec`/`tb_norm`/`tb_attn`
vmem output contracts, or the `tb_core` structured token/cycle contract; it is
preserving/exporting
`VL_WRITEF_NX` / `VL_FINISH_MT` PASS/FAIL and finish authority as device-visible
observables, then testing whether batching independent scenarios as states gives
useful throughput.
The first batching data point is only a replicated-state probe for `tb_exp`, not
that independent-scenario gate. It copies the same 103-case vector scenario
across `nstates=1,32,256` and records per-state kernel time of `16.966656 ms`,
`0.56204803125 ms`, and `0.084064 ms`; the best result is `nstates=256`, a
`201.83022459078796x` per-state kernel improvement versus `nstates=1`. Treat
this as launch-amortization evidence only. The next useful gate is a resident
distinct-state path or resident multi-step/token runtime, then repeat-median
comparison against the measured CPU baseline.
The first distinct-state `tb_exp` gate is now correctness-positive: the runtime
accepts `@state:local_offset:byte` patch tokens, and the probe runs 103 different
`z` inputs as 103 GPU states in one 2-step clock sequence with 103/103 matched
outputs, nonresident `gpu_kernel_total_ms=3.639296`, and nonresident
`wall_time_ms=13.266`. The first resident version is now also correctness-
positive: it runs the same patch script through `--resident-steps`, uploads
`412` patch records once as a device-resident schedule, matches 103/103 outputs,
and now has a 7/7 repeat-median gate: `gpu_kernel_total_ms_median=0.887808`,
`wall_time_ms_median=0.93`. The matching CPU Verilator process-wall baseline
now passes 7/7 samples with `median=28.96515399334021 ms`, so the resident
repeat-median observed wall ratio is `31.145326874559363x`. The broader resident
coverage gate has now reached full `tb_core` persistent resident feedback
correctness for the reviewed token/cycle contract. The resident multi-step
sequence reduces measured kernel/wall from `4367.203339 ms` / `4373.235 ms` to
`816.12083 ms` / `816.915 ms`, and the full feedback path now has a 7/7
repeat-median of `767.118103 ms` kernel / `767.173 ms` wall. That is
`5.700454786599632x` observed wall improvement versus nonresident structured GPU
and `1.064838048262908x` versus resident multi-step. The new CPU `tb_core`
process-wall baseline passes 7/7 with median `22.265211009653285 ms`; full
feedback GPU wall is only `0.029022412167338116x` of CPU, about `34.5x` slower.
The slowdown breakdown records `95,311` actual timed GPU launches for one
scenario, while feedback helpers are only `27` launches. The first launch-count
collapse trial now has a 7/7 repeat median with pair-cycle-loop enabled: `69`
actual timed launches, `14` loop kernels, `23,814` looped low/high cycles,
`432.609 ms` wall, and `1.7733634760256953x` GPU-wall improvement versus full
feedback. It remains `19.429818105583568x` slower than CPU. The `nstates=1,8,32`
replicated-state trial now preserves pair-cycle-loop eligibility by replicating
the state0 resident patch schedule across state strides: all three runs keep
actual timed launches at `69`, and `nstates=32` reaches
`18.3382225 ms/state` kernel time, a `23.557655274386597x` per-state
improvement versus `nstates=1`. All replicated state phase dumps now pass the
same token/cycle contract (`8/8` for `nstates=8`, `32/32` for `nstates=32`,
zero mismatches). A distinct-state full-sequence phase-set probe also now
passes: state0 greedy observes `[1, 12, 1, 25, 1, 0]`, and state1 sampled seed
`2` observes `[18, 15, 19, 16, 8, 15, 4, 0]`. This proves the reviewed
token-sequence mixed batching contract. Without loop collapse it costs `54,463`
actual launches and `471.533 ms` wall; the pair-cycle-loop follow-up keeps the
same token result and now has a 7/7 repeat median: `286.213837 ms` kernel /
`286.254 ms` wall, with `47.0` actual launches, `27,224.0` logical launches,
`8.0` loop kernels, `13,600.0` looped low/high cycles, and `8.0`
phase-boundary fallbacks still present. Against the CPU Verilator process-wall
median `23.23766698827967 ms`, the observed GPU wall ratio is only
`0.08117848829459036x`, about `12.31853439264696x` slower than CPU. The
many-independent seed matrix now has CPU token oracles for all `16` target
states with zero validation mismatches, and the 16-state GPU batch passes 7/7
repeat-median samples with 16/16 token streams matched and
`trim_final_low=true`. Median GPU time is `393.967987 ms` kernel /
`393.999 ms` wall, with `35.0` actual launches over `30,618.0` logical
launches. Compared with the CPU oracle executable wall `84.66219899128191 ms`,
GPU wall speedup is only `0.2148792230215861x`, so GPU remains
`4.653777065731213x` slower. Launch-structure analysis accounts for all `35`
actual launches (`9` phase-set, `8` combined-feedback, `9` pair-cycle-fusion,
and `9` pair-cycle-loop kernels), leaving `0` residual launches. It still does
not prove cycle summary authority, stdout/PASS/finish authority, speedup, or
usefulness. A hold-start diagnostic drops actual launches to `26`, but all `16`
token streams mismatch. The padded-start probe preserves one-cycle start
semantics, passes `7/7` repeats with `16/16` token streams matched, reduces
actual launches to `26`, and removes pair-cycle-fusion launches and loop
fallbacks. Its median is `366.163605 ms` kernel / `366.21 ms` wall, still
`4.325543210113294x` slower than CPU. The generated build metadata now exposes
`schedule_lowering_capabilities.padded_start_pair_cycle_loop` as `available`
with no missing runtime entrypoints. The 7-repeat CPU comparison now claims only
the lower-launch gate; it remains CPU-negative before any project-level
usefulness claim. The
`tb_core_persistent_resident_multitoken_abi_gap` report fixes the minimum ABI:
copy `next_token` to `token_in`, copy four `rng_out` bytes to `rng_in`, and
advance `pos_in` on device between token transactions. The LLVM pass now emits
`vl_apply_feedback_edges_gpu`, `vl_apply_feedback_increments_gpu`, and
`vl_apply_feedback_sets_gpu`, plus `vl_apply_feedback_combined_gpu` for fused
edge+increment feedback. The runtime now smoke-tests feedback table
upload/launch for 5 copy edges, one `pos_in` increment, and phase-set
`start/smode/inv_temp` controls, including `@0:phase:offset:value`
state-indexed phase-set records in the one-state smoke. The full feedback smoke uses 14 phases, 13
combined edge+increment feedback launches, 14 phase-set launches, and 68
phase-set records while keeping stdout/PASS/finish and usefulness claims
disabled. The distinct-state full-sequence phase-set probe now passes the
reviewed two-state token contract in one GPU batch: state0 greedy observes
`[1, 12, 1, 25, 1, 0]`, and state1 sampled seed `2` observes
`[18, 15, 19, 16, 8, 15, 4, 0]`. It uses `8` state-indexed phase-set launches,
`7` combined feedback launches, `76` phase-set records, `27,224` logical
launches, and `54,463` actual launches without loop collapse
(`gpu_kernel_total_ms=471.468170`, `wall_time_ms=471.533`). The pair-cycle-loop
follow-up keeps the same reviewed token contract and now passes a 7/7 repeat
median: `286.213837 ms` kernel / `286.254 ms` wall, `47.0` actual launches,
`8.0` loop kernels over `13,600.0` low/high cycles, and `8.0` phase-boundary
fallbacks. The CPU process-wall median is `23.23766698827967 ms`, so the
observed GPU wall ratio is `0.08117848829459036x` and GPU wall remains
`12.31853439264696x` slower. The many-independent-scenario gate is now explicit
and measured: the 16-state seed matrix has CPU token oracles with zero
validation mismatches, and the state-indexed GPU batch passes 7/7 repeat-median
samples with 16/16 token streams matched and `trim_final_low=true`. Median GPU
time is `393.967987 ms` kernel / `393.999 ms` wall, while CPU oracle wall is
`84.66219899128191 ms`; GPU remains `4.653777065731213x` slower.
Launch-structure analysis accounts for all `35` actual launches (`9` phase-set,
`8` combined-feedback, `9` pair-cycle-fusion, and `9` pair-cycle-loop kernels),
leaving `0` residual launches and `0.0` residual launches per fallback. This is
token sequence mixed batching plus repeat-median launch-collapse evidence only;
cycle summary authority, speedup, usefulness, and stdout/PASS/finish remain
unclaimed. The hold-start diagnostic reaches `26` launches but fails all `16`
token streams, so the structural direction is not holding `start` high. The
padded-start schedule-shape lowering probe preserves the one-cycle start pulse,
passes `7/7` repeats with `16/16` token streams matched,
and reduces the structure to `26` actual launches (`9` phase-set, `8`
combined-feedback, `0` pair-cycle-fusion, `9` pair-cycle-loop kernels, `0`
loop fallbacks). Median time improves to `366.163605 ms` kernel /
`366.21 ms` wall, but the result remains CPU-negative at `4.325543210113294x`
slower than the CPU oracle wall. The schedule shape is now factored into
`src/tools/gategpt_schedule_planner.py` with runtime-facing env, required
entrypoints, and expected launch-shape metadata, and the generated plan artifact
is `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/tb_core_many_independent_padded_start_lowering_plan.json`.
`run_vl_hybrid.py --schedule-lowering-plan` now consumes that artifact as the
validated runtime env source for the padded-start probe, and the planner now
generates the schedule-lowered `run_vl_hybrid` argv. The generated build
metadata now exposes
`schedule_lowering_capabilities.padded_start_pair_cycle_loop` as `available`
with no missing runtime entrypoints, and the 7-repeat CPU comparison claims only
the lower-launch gate. The generated
`tb_core_padded_start_cpu_negative_gap_decision` report is
`mapping_structure_change_recommended`, so the next gate is a materially
different runtime/mapping structure rather than another narrow LLVM
helper-kernel tweak. The generated
`tb_core_runtime_mapping_structure_candidate_plan` is
`ready_for_runtime_mapping_design` and ranks
`ordering_aware_phase_resident_token_loop` first; GitHub #69 tracks that
prototype. Its prototype contract now validates as planning evidence and targets
`phase_set=0`, `combined_feedback=0`, `pair_cycle_loop=0`, and one
`ordering_aware_token_loop` launch before any speedup/usefulness claim. Current
build metadata now reports `vl_tb_core_ordering_aware_phase_resident_token_loop_gpu`
as available, and the generated kernel body now consumes `current_phase`,
phase-control records, feedback copy/increment records, and terminal-mask
records around the
pair-cycle loop. The latest ordering-aware run now consumes the #69 lowering
plan through the schedule-owned token-loop path with `runtime_supported=true`.
It passes the source CPU-token-oracle comparison for `16/16` states, uses `9`
actual ordering-aware launches over `30,618` logical launches, and suppresses
the separate helper launch classes: `feedback_phase_sets=0`,
`feedback_combined=0`, `pair_cycle_loop_fusion=0`, and
`resident_pair_cycle=0`. Runtime summary now reports `entrypoint_available=true`,
`phase_control_records=672`, `feedback_copy_records=5`,
`feedback_increment_records=1`, `pair_cycle_loop_records=1701`,
`terminal_mask_records=16`, `terminal_mask_device_records=16`, and
`terminal_mask_parse_errors=0`, with `launch_probe_count=9`,
`device_table_launches=9`, blocking at
`ordering_aware_token_loop_schedule_integrated_cpu_comparison_pending`. The
ordering-aware lowering plan artifact now records the ABI-probe env and
per-state terminal mask at
`artifacts/gategpt_local_eval/gateGPT/obj_tb_core/tb_core_ordering_aware_token_loop_lowering_plan.json`;
the wrapper now consumes this shape by default, and
`--allow-ordering-aware-token-loop-probe-plan` remains only as a debug
compatibility path. The C runtime parses, validates, and uploads terminal masks
as device-side `state:terminal_step` records. The runtime now canonicalizes terminal
steps by state, and the generated kernel uses a direct state-indexed terminal-mask
fast path with an order-tolerant fallback before gating active phases and final feedback.
Latest ordering-aware probe status
is `passed` with `source_probe_correctness_claimed=true` and
`runtime_correctness_claimed=true`, but the CPU comparison is still negative:
GPU wall is `363.628 ms` / GPU kernel is `363.59198 ms` versus CPU oracle wall `81.95496001280844 ms`, so the
ordering-aware path with the normal eval select-mux transform is
`4.436924866331091x` slower than CPU. The normal eval reachable closure now has
`normal_eval_transform_present=true`, `normal_eval_rewritten_select_count=1344`,
and `transform_rewritten_select_count=2688`, with
`implementation_stage=normal_select_mux_cluster_transform_measured_cpu_negative`.
The select-mux transform now runs before eval hot-path partitioning, and the
post-select-mux partition stage is measured with
`eval_hot_path_partition_after_select_mux_transform_present=true` and
`eval_hot_path_partition_count=1580`.
The guarded bitmap run is correctness-positive but performance-negative:
16/16 source states still match with `mode=phase_state_partition_bitmap`,
`active_bitmap_partition_count=13`, and `active_bitmap_device_bytes=2080`.
GPU wall is `354.541 ms` / GPU kernel is `354.494232 ms`, still
`4.326046891421703x` slower than CPU, and no speedup is claimed. The stale
runtime-binary launch failure was fixed by rebuilding the host runtime when
`src/hybrid` inputs are newer. The next concrete gap is partition-local guarded
cold-partition skip: the bitmap is now partition-indexed, but the kernel guard
still skips whole eval calls, cold partition skip safety reports `13` inspected
continuations, `0` skip-safe candidates, and `13` rejected continuations
(`successor_phi_depends_on_continuation_edge=11` and
`terminator_not_unconditional_branch=2`). The select-only repair now exposes
`8/8` partition-match targets, concrete direct eval predicate-context global ABI,
and control-flow guard lowering for all `8` repaired targets. The no-skip bypass
still has no runtime skip authority and now classifies `832` cloned select values
as non-trivially elidable inactive-partition work. Simple LLVM guard insertion is therefore insufficient until
`outline_partition_region_before_phi_join_or_split_successor_phi_edges` handles
the PHI-edge cases and
`outline_multi_successor_partition_region_or_normalize_continuation_terminator`
handles the remaining terminator cases.
The pass now refines that into `8` `select_only_phi_edge_region` cases, `3`
`effectful_memory_phi_edge_region` cases, and `2` `multi_successor_continuation`
cases, so the next implementation slice should start with the select-only
PHI-edge outline.
The select-only outline preflight records `8` regions with `832` selects,
`1344` successor-PHI edges, `832` local live-out values, and `512`
external-or-constant incoming values; this is the sizing contract for the first
outline slice, not a speedup or skip-safety claim.
The pass now inserts `8` select-only PHI repair blocks, moving `832` selects and
retargeting `1344` successor-PHI edges; this is CFG repair evidence only, not
partition-aware skip authority.
Post-repair static safety classification now records `8` inspected repaired
select-only continuations, `8` candidates, and `0` rejected; this narrows the
next guarded-skip prototype but still grants no skip authority.
The generated `tb_core_ordering_aware_cpu_negative_gap_decision` now records
`status=ordering_aware_cpu_negative_gap_measured`: helper launches are already
suppressed, launches fell by `17` versus padded-start (`0.6538461538461539`),
but wall improved only `1.0604264497337874x` versus padded-start. The requested `decompose_ordering_aware_kernel_body_cost_and_state_scale` follow-up is now represented by stage timing, the state-scale sweep, and opt-in device-side diagnostic region counters: `before_final_sync=360.61 ms` dominates the measured wall path, so more helper-launch removal is not the next lever. The standard CPU comparison remains bound to the 16-scenario oracle; the 32-state sweep row uses a separately generated 32-scenario CPU oracle. The new 4/8/16/32-state ordering-aware sweep records
`273.035736 ms`, `324.181793 ms`, `359.070801 ms`, and `402.972504 ms` kernel time respectively,
or `68.258934`, `40.522724125`, `22.4732570625`, and `12.59289075 ms/state`. State scaling is
helping by `5.420434065149021x` from 4 to 32 states, but the 16-state wall is
still `4.30538043208457x` slower than CPU and the 32-state wall is still
`2.710562354615603x` slower than its 32-scenario CPU oracle. Static IR
classification of `vl_tb_core_ordering_aware_phase_resident_token_loop_gpu`
now records `24` basic blocks and `137` LLVM instructions with the expected
`terminal.mask`, `phase.set`, `cycle`, `low.patch`, `high.patch`, and `feedback`
regions. Static region breakdown is recorded as a non-timing proxy, and the opt-in timing variant records diagnostic gid0 clock64 counters for the 16-state baseline: cycle_body `4884742382`, high_eval `3629021127`, low_eval `1216414868`, low_patch `21611907`, high_patch `14785139`, phase_set `881773`, terminal_mask `9294`, and feedback `18574`; the 32-state normal row remains CPU-negative at `403.039 ms` wall versus a `148.6920230090618 ms` 32-oracle CPU wall. The direct eval callee has `65` counted LLVM instructions; its largest direct call is `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` at `11593` counted instructions, `1777` basic blocks, `2670` loads, `556` stores, and `1758` branches. Its refined structural decomposition shows two largest LLVM basic blocks at `694` instructions each, a third at `339`, `select=2149`, `switch=17`, no `phase` keyword hits, and only `start=2`; the analyzer now marks this as `start_only_guard_evidence_present` with `weak_for_phase_guard_partition`. The eval direct-call finding classifies that NBA sequential body as `poor_for_narrow_peephole_pass` and recommends `structural_eval_partition_or_larger_state_scale`; the concrete next experiment is now `measure_memory_vs_select_cluster_partition`; static clusters are `load_store_heavy=3182` instructions and `select_mux_heavy=1352` instructions, with partition gate `ready_for_static_partition_probe`, `memory_select_instruction_count=4534`, and `memory_select_fraction_of_function=0.39109807642542915`, with lane priority `memory_heavy_root_state_lane` -> `select_mux_lane` -> `branch_control_lane`; the memory lane contract targets `isolate_or_instrument_load_store_heavy_basic_blocks` with candidates `measure_memory_cluster_clock64_region`, `prototype_hot_root_state_field_grouping`, and `prototype_memory_cluster_outline_or_split`, so it should not be treated as a small LLVM peephole target. The runtime partition measurement contract has advanced to `runtime_cluster_counters_present`: `memory_cluster`, `select_mux_cluster`, optional `branch_control_cluster`, active-path BB discovery, and select-mux scoped hook counters are emitted through the 16-slot region timing ABI. The companion cluster counters still use `all_threads_atomic_clock64_sum`, while the select-mux scoped hook now uses `representative_thread_non_atomic_clock64_sum`. The current 16-state token-loop run observes `memory_cluster=481050879`, `select_mux_cluster=1405771525`, `branch_control_cluster=0`, `active_eval_basic_blocks=79885598`, `active_memory_candidate_blocks=600894`, `active_select_candidate_blocks=387828`, `select_mux_scoped_cycles=73818337`, and `select_mux_scoped_blocks=20412`; the scoped values are intentionally representative-thread values and no longer match the all-thread select-mux cluster sum. Select-mux is `2.922292810112504x` memory-cluster cycles, and memory+select accounts for `0.4054252889390992` of cycle-body cycles. The prior ABI, zero-signal, scoped-atomic, lowering-candidate-metadata, and normal-vs-diagnostic-kernel-isolation blockers are gone. A clone-only identity select rewrite is applied inside select-mux-heavy region-timing eval clones (`transform_present=true`, `transform_rewritten_select_count=1`), and the normal eval reachable closure now has eval hot-path partition markers (`eval_hot_path_partition_present=true`, `eval_hot_path_partition_count=1580`) plus active-block gate markers (`eval_hot_path_active_block_gate_present=true`, `eval_hot_path_active_block_gate_count=53`). The eval hot-path partition prototype marks 1580 split continuation blocks, active-block gate markers are present (`eval_hot_path_active_block_gate_present=true`, `eval_hot_path_active_block_gate_count=53`), cold partition skip safety classification is now present (`eval_hot_path_cold_partition_skip_present=true`, `eval_hot_path_cold_partition_skip_candidate_count=0`, `eval_hot_path_cold_partition_skip_rejected_count=13`), and the phase/state/partition predicate table is authoritative via `RUN_VL_HYBRID_EVAL_PARTITION_PREDICATES` / `eval_partition_predicates:` with `active_mask_authority=true`; direct eval callee/call-site predicate-pointer markers are present via `vlgpu.direct_eval_predicate_pointer_abi` / `vlgpu.eval_predicate_pointer`. This remains lowering-hook/ABI plumbing evidence, not speedup timing, usefulness evidence, or safe skip authority. The current guarded skip has a partition-indexed active bitmap, so `active_bitmap_index_omits_partition_id` is no longer a blocker; the broad partition-aware skip gap is that the kernel guard skips whole eval calls rather than partition continuations; the active compact-cluster implementation gap is runtime outline wiring after the single-entry CFG clone probe. Direct terminal-mask lookup and patch-record invariant division/base hoisting are now implemented with fallback/hoisted IR evidence; remaining LLVM/lowering candidates are phase/state partitioning for phase-control records. Structural candidates are eval-callee hot-path analysis,
expanding beyond 32 independent states, or a multi-phase resident sequence kernel.
The phase/state/partition predicate table is authoritative through `RUN_VL_HYBRID_EVAL_PARTITION_PREDICATES` and the `eval_partition_predicates:` stdout contract with `active_mask_authority=true`; direct eval callee and call-site predicate-pointer markers are present through `vlgpu.direct_eval_predicate_pointer_abi` and `vlgpu.eval_predicate_pointer`. The diagnostic path still validates 16/16 CPU token oracles and reached CFG-clone liveout capture points with mismatch_count=0. A first non-diagnostic isolation entrypoint exists through `build_vl_gpu.py --disable-cfg-clone-diagnostics` plus `RUN_VL_HYBRID_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI=1`; replacement same-CPU-oracle timing is measured and still CPU-negative: non-diagnostic GPU wall `404.986 ms` / kernel `404.90036 ms` versus CPU oracle `107.71662899060175 ms` (`3.759735184762744x` slower). The LLVM Pass emits a partition-local eval continuation guard static shape: target/guarded/successor-PHI-defined regions `8/8/8`, successor PHI incoming `1344`, blocked runtime-noop selects `832`. Runtime-noop derivation is also blocked by successor PHI live-out: `832` inspected selects, `832` const/global-pointer-arm selects, `832` external-condition selects, `832` successor-PHI-liveout selects, `0` elision-safe selects, `832` blocked selects, authority `no_runtime_noop_derivation_authority`. Successor-PHI continuation user classification is complete for `168` successor PHIs / direct users / direct load users / load-consumed PHIs, with `0` direct non-load users, `168` load-result direct users, `0` unsupported load-result users, and `1` candidate cluster under `classification_only_no_runtime_skip_or_select_elision_authority`. Existing pass evidence has also reached compact cluster outline frame-call ABI stub materialization: `1` outline callee, `63` outline call sites, `175` explicit live-ins, `48` explicit live-outs, `242` lowered live-in frame stores, `48` lowered live-out frame stores, and `0` unsupported live-in/live-out frame values, with `outline_frame_call_abi_stub_materialized_no_semantic_outline_authority`. The analyzer now records this as CPU-oracle-pending because runtime guard execution summary is missing and runtime noop/skip authority is false. Guarded/liveout oracle validation remains on the diagnostic artifact and is also negative: GPU wall `19232.031 ms` / kernel `19231.960938 ms` versus the same CPU oracle (`178.5428227769548x` slower). `claim_speedup` and `claim_usefulness` remain forbidden. The next contract is `clone_compact_cluster_body_into_outline_callee_and_rewire_control_flow`.
Do not create a launch template or add a `third_party/` copy until the missing
license question is resolved. This candidate does not change the FC-037
RTLMeter VeeR timing priority and does not add gateGPT PASS/FAIL equivalence,
speedup, usefulness, or arbitrary RTL support evidence.

Native Verilator sidecar owner-goal tracking is handled by GitHub #46 / FC-053.
The owner endpoint is:

```text
verilator --sim-accel sidecar-gpu ... -f filelist --top-module top
make -C obj_dir -f V<top>.mk
obj_dir/V<top>
```

The VeeR-EL2 task order is #63 / FC-064 first: program staging is now a
device-suitable flat/byte-addressable representation, and automatic
syms-state-image rebuild clears the prelaunch rejection gate in metadata. The
reviewed state-image-consuming VeeR sidecar executable now runs and emits
observables. The GPU clock/reset patch reaches the CPU stdout architectural
counter point (`mcycle=726`, `minstret=330`) and observes the `0xff` finish
marker, and the mailbox step trace now reconstructs normalized stdout to match
the CPU reference. The sidecar `_rtlmeter_cycles.txt` is now aligned with
RTLMeter's injected `tb_top.core_clk` count, so stdout/cycles comparison passes.
FC-037 now records a three-batch timing stability result with a
workload-comparable eight-worker CPU-parallel `hello` baseline: correctness
samples pass, `nstates=8` runs with all-state clock/reset patching and final
observable validation, every batch median is faster than CPU-parallel CPU after
coalesced two-field device-buffered trace plus resident patch scheduling, and the path is
still much slower than serial CPU for `hello`.
FC-037 also records a sixteen-state scaling gate against a matching
sixteen-worker CPU-parallel baseline: after high-phase trace filtering,
states/s improves by about `1.589x` against eight-state, but total wall is
`1.258905x` worse and still much slower
than serial CPU. Current next work is making the fixed-flat-memory non-`hello`
`dhry` path eligible for pair-cycle loop collapse despite the multi-kernel VeeR
launch sequence, without pre-claiming broad speedup. The explicit `posedge_only` clock patch probe
showed that fewer logical eval steps are not legal when they remove the
low-clock phase. The follow-up opt-in pair-cycle mode preserves the VeeR design
CPU's low/high transition semantics and passes
`reports/rtlmeter_veer_el2_timing_pair_cycle_nstates16.json` with 21/21
correctness samples, `sidecar_wall_s_median=0.692794`, and fallback median
`0.0`; it improves the latest non-fusion representative `0.768573s` by
`1.109382x` but remains slower than serial CPU and does not beat the previous
best filtered observation `0.643080s`. A confirmatory report
`reports/rtlmeter_veer_el2_timing_pair_cycle_confirm_nstates16.json` again
passes 21/21 correctness samples and remains faster than non-fusion
(`0.707203s`, `1.086778x`), but the batch medians
`0.868907` / `0.673572` / `0.685787` show enough variability to keep
pair-cycle opt-in.
The true fused pair-cycle follow-up at
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json` passes 21/21
correctness samples with `pair_cycle_fusion_available_counts={"true": 21}`,
`pair_cycle_fusion_launched_median=727.0`, fallback median `0.0`, and
`sidecar_wall_s_median=0.641226`. This improves the latest non-fusion
representative by `1.198599x`, the pair-cycle confirm gate by `1.102892x`, and
the previous best filtered observation by `1.002891x`, while remaining about
`16.030650x` slower than serial CPU.
Runtime reporting now separates logical steps from actual timed GPU launches:
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_actual_launch_smoke.json`
passes and records `1457` logical steps, `733` actual timed launches, and
`0.373625ms` per actual launch. The `733` includes 727 fused pair-cycle kernels
plus six reset/deassert patch/eval launches.
The next scale point,
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json`, also passes
21/21 correctness samples after raising the runtime patch-script limit to 256
patches per step. It uses
`reports/rtlmeter_cpu_parallel_hello32_baseline.json` as the matching CPU floor
and records `sidecar_wall_s_median=0.950341`,
`gpu_kernel_ms_total_median=357.866486`,
`gpu_kernel_timed_launch_count_median=733.0`, and
`sidecar_vs_cpu_parallel_ratio=4.468648`. Compared with the 16-state fused gate,
total wall is `1.482069x` worse, but per-state wall and states/s improve by
`1.349465x`. The direction is throughput-positive but latency-negative, so the
next useful work is overhead reduction or a less tiny per-state workload, not
default promotion. The state-local patch compression follow-up
`reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json`
is correctness-safe and cuts stored patch records by `32x`, but it regresses
wall to `2.452390s` and GPU kernel total to `1675.526123ms`, so it is rejected
as the next performance path.
The first non-`hello` preload check is now fail-closed instead of misleading:
`reports/veer_el2_cmark_state_image_materialize_after_fix.json` records that a
`cmark` `--rtlmeter-program-hex` mismatch refuses materialization with
`state_image_materialized=false`. Reviewed matching preload materialization now
exists for `cmark`, `cmark_iccm`, and `dhry` via
`reports/veer_el2_cmark_state_image_materialize.json`,
`reports/veer_el2_cmark_iccm_state_image_materialize.json`, and
`reports/veer_el2_dhry_state_image_materialize.json`. That clears the
hello-only preload blocker but does not measure GPU usefulness. The next step
toward useful design-CPU timing is launch-count feasibility: collapse the
current pair-cycle path with resident multi-cycle execution or reach a
meaningful bounded non-`hello` program milestone before attempting full
RTLMeter timing. The current explicit
feasibility reports,
`reports/rtlmeter_veer_el2_timing_cmark_launch_feasibility.json` and
`reports/rtlmeter_veer_el2_timing_cmark_iccm_launch_feasibility.json`, stop
before bridge execution with estimated actual timed launch counts `5276412` and
`6024133` versus threshold `100000`.
The first bounded non-`hello` smoke now also passes the launch boundary:
`reports/rtlmeter_veer_el2_dhry_bounded_smoke.json`,
`reports/rtlmeter_veer_el2_cmark_bounded_smoke.json`, and
`reports/rtlmeter_veer_el2_cmark_iccm_bounded_smoke.json` reach
`status=observables_emitted` with one fused pair-cycle launch and seven actual
timed GPU launches. This confirms the reviewed state images can enter the GPU
path, but it is still not full RTLMeter correctness or usefulness evidence.
The follow-up 500-cycle bounded progress reports
`reports/rtlmeter_veer_el2_dhry_bounded_progress_500.json`,
`reports/rtlmeter_veer_el2_cmark_bounded_progress_500.json`, and
`reports/rtlmeter_veer_el2_cmark_iccm_bounded_progress_500.json` show real
architectural progress on the GPU path: all reach `mcycle=499`, with
`minstret=321`, `342`, and `418`. The next frontier is still launch-count
collapse or a bounded correctness gate that reaches a meaningful program
milestone without pretending this is full timing.
The three-report bounded-progress result is now machine-checked in
`reports/rtlmeter_veer_el2_non_hello_bounded_progress_summary.json`; it is a
progress gate, not timing or usefulness evidence.
The first implementation step for launch-count collapse is now exercised in a
bounded no-trace/final-observable diagnostic:
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_no_trace_500.json`.
The opt-in pair-cycle loop kernel `vl_patch_eval_pair_cycle_loop_batch_gpu`
uses `RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP` /
`VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP` with
`VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1`. In that `dhry` 500-cycle run, loop
fusion is available and used with `kernel_launches=1`, `cycles=500`,
`fallback=0`, and `gpu_kernel_timed_launch_count=7`, while final observables
match across the two GPU states. The same no-trace loop path now reaches a full
`hello` program event in
`reports/rtlmeter_veer_el2_hello_pair_cycle_loop_no_trace_full_event.json`:
`kernel_launches=1`, `cycles=727`, `gpu_kernel_timed_launch_count=7`,
`finish_marker_observed=true`, `mcycle=726`, `minstret=330`, and
`cycles=2229`. This is launch-count-collapse and full-program-event evidence
only.
The same launch-count-collapse path now has a larger reviewed non-`hello`
bounded gate:
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_5000_summary.json`
passes for `dhry`, `cmark`, and `cmark_iccm` 5000-cycle no-trace runs. All
three reach `mcycle=4999`, retire thousands of instructions (`4821`, `4842`,
and `4918`), and keep `gpu_kernel_timed_launch_count=11` with
`pair_cycle_loop_fusion.kernel_launches=5`, `cycles=5000`, and fallback `0`.
This proves the loop-collapse strategy is moving the non-`hello` path past the
previous millions-of-launches blocker for bounded windows. It still is not full
RTLMeter correctness or usefulness evidence because the programs do not finish
and stdout is not reconstructed.
The immediate launch-count follow-up widened the loop chunk for this narrow
path. With `VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK=5000`,
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_5000_summary.json`
passes for the same three 5000-cycle non-`hello` preloads using one loop kernel
and seven actual timed GPU launches instead of five loop kernels and 11 timed
launches. This is a real bounded runtime improvement, especially for
`cmark`/`cmark_iccm`, but a `dhry` 50000-cycle finish probe still does not
observe the finish marker. Next work should inspect finish reachability and
program-image completeness before any non-`hello` stdout or usefulness claim.
That completeness issue has been narrowed: the sidecar syms init materializer
now writes reviewed DCCM/ICCM ECC bank preload entries. The refreshed
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_bank_init_5000_summary.json`
passes with bank word counts `371/0` for `dhry`, `0/0` for `cmark`, and
`342/7674` for `cmark_iccm`. A longer bank-init `dhry` probe reaches
`mcycle=199999` and `minstret=191985` without finish. The CPU follow-up
`reports/rtlmeter_cpu_dhry_serial_baseline.json` finishes `dhry` at `5984259`
RTLMeter cycles, so the GPU probe covers only about `3.34%` of the CPU
completion window. The same-cycle CPU snapshot workflow is now implemented for
this `dhry` point in `src/tools/rtlmeter_veer_el2_cpu_snapshot.py`; the report
set now covers `mcycle=4999`, `49999`, and `199999`. CPU retires `4473`,
`47757`, and `192038` instructions, while GPU retires `4421`, `47705`, and
`191985`; raw PC fields differ in all three comparisons. The GPU kernel time at
`mcycle=199999` (`43.9320625s`) is about `35.8x` the bounded CPU run wall
(`1.226972s`). Removing CPU `+iterations=17500` does not fix the mismatch; it
produces a stable CPU-minus-GPU `minstret` delta of `65`. Sampling CPU at
`mcycle-65` makes the long-window PC/minstret close to GPU but does not fully
explain the short-window mismatch. The post-reset cycle-targeted follow-up also
does not explain the gap: CPU snapshots at `post_reset_posedges=N+2` align
`mcycle` with the GPU windows, but `minstret` and PC stay on the CPU-default
path rather than matching GPU.

Historical pre-fix trace-debug context follows; the fixed flat-memory
same-window compare through 50000 cycles supersedes this mismatch thread for
the traced fields, so the current gate is stdout-safe longer progress or finish
reachability. The early reset-release CPU snapshot follow-up
now shows CPU remains at zero state through post-reset posedge `3`, reaches
`mcycle=1` at posedge `4`, and reaches `mcycle=497`, `minstret=360`,
`pc=0x400002d1` at posedge `500`. The existing GPU 1-cycle report also starts
at zero, but the existing GPU 500-cycle report is pre-bank-init and therefore
not a valid current comparison. The regenerated bank-init GPU windows now show
CPU/GPU equivalence through 875 cycles: 500, 750, and 875 cycle windows match
`mcycle`, `minstret`, PC, and mailbox byte. The first observed divergence is at
1000 cycles, where CPU has `minstret=746`, `pc=0x40000194`, `obuf=117`, while
GPU has `minstret=709`, `pc=0x40000270`, `obuf=32`. The progress-only trace
gate first narrowed the mismatch:
`reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_875_1000.json` compares
CPU trace rows with GPU step trace rows carrying `mcycle`, `minstret`, and `pc`.
The mapping is `cpu_post_reset_posedges=gpu_step+3`. Rows match through
`gpu_step=896` / CPU `post_reset_posedges=899`; at `gpu_step=897` / CPU
`post_reset_posedges=900`, only PC differs (`0x4000026e` GPU versus
`0x40000270` CPU) while `mcycle=897`, `minstret=669`, and `obuf=32` still
match. Follow-up traces first added `pc_d`, then decode/fetch-stall debug
fields, and the earliest observed mismatch is now
`reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_debug_875_1000.json`.
Rows match through `gpu_step=894` / CPU `post_reset_posedges=897`; at
`gpu_step=895` / CPU `post_reset_posedges=898`, both sides still match
`mcycle=895`, `minstret=669`, registered PC `0x4000026e`, `pc_d=0x40000270`,
`pc_din=0x4000026e`, `instr_d=0x0334c4b3`, and `obuf=32`, but CPU has
`decode_d=1` / `fetch_stall=0` while GPU has `decode_d=0` / `fetch_stall=1`.
The next gate is auditing or fixing why the GPU eval path leaves
`ifu_pmu_fetch_stall` asserted one sampled cycle longer and delays
`dec_i0_decode_d`, before running longer GPU finish probes or using speedup
wording. A phase-split artifact was also generated to test the eval-ordering
hypothesis. The first phase sequence exposed two generator issues:
`_eval_phase__act` could be over-stubbed to `return false`, and phase kernels
did not use the same syms self-pointer repair as `vl_eval_batch_gpu`. After
fixing those and using `vl_nba_loop_batch_gpu` for reachable `_eval_phase__nba`,
`reports/rtlmeter_veer_el2_dhry_phase_nba_loop_trial_summary.json` shows the
phase sequence now progresses through the 1000-cycle bounded `dhry` trace with
the same final observables as `vl_eval_batch_gpu`. The manifest now uses
`vl_ico_batch_gpu` followed by the combined `vl_eval_loop_batch_gpu`, but it
still reproduces the `gpu_step=895` `fetch_stall=1` / `decode_d=0` divergence.
The follow-up input trace,
`reports/rtlmeter_veer_el2_dhry_fetch_inputs_compare_875_1000.json`, shows
`decode_valid_gate=1` and `fetch_fbwrite=0x038` still match, but GPU has
`decode_misc2ff=4`, `decode_i0_exublock=1`, and `fetch_consume_gate=0` where
CPU has `0`, `0`, and `1`. The AXI input trace
`reports/rtlmeter_veer_el2_dhry_axi_inputs_compare_875_1000.json` shows valid
IFU response inputs match through the divergent window. The next task is the
remaining IFU fetch-buffer consume update fault, not continuing to restructure
phase order. The IFU consume/request trace
`reports/rtlmeter_veer_el2_dhry_ifu_consume_compare_875_1000.json` confirms
that the first divergent row remains `gpu_step=895` / CPU post-reset `898`.
At that row the request/response-side equivalents and miss-state fields still
match, but `ifu_ifc_fetch_req_bf` is `CPU=1` / `GPU=0` and
`ifu_ifc_fb_write_ns` is `CPU=4` / `GPU=8`. The ALN consume trace,
`reports/rtlmeter_veer_el2_dhry_aln_consume_compare_875_1000.json`, shows the
same row has matching `ifu_aln_bundle2=63` and `ifu_ifc_fetch_ready=1`, but GPU
keeps `ifu_aln_sf0val=3` and leaves `ifu_aln_shift_f1_f0` /
`ifu_aln_shift_f2_f1` deasserted while CPU has `ifu_aln_sf0val=0` and both
shifts asserted. The next implementation target is ALN sf/shift next-state or
state-update ordering feeding IFC fetch-buffer consume/request. The trigger/DIN
follow-up in `reports/rtlmeter_veer_el2_dhry_aln_trigger_compare_875_1000.json`
shows the committed ALN flops still match at the first functional mismatch, but
GPU next-state outputs are stale (`bundle1_din=0` vs CPU `8`,
`bundle2_din=63` vs CPU `15`) and post-step `root_act_triggered` /
`root_nba_triggered` are clear on both sides. This makes the immediate fix
target `Vsim___024root___nba_comb__TOP__18` recompute ordering or a phase-local
ALN dependency recompute after active/sequent updates, not a broad phase
rewrite. The focused diagnostic
`reports/rtlmeter_veer_el2_dhry_post_nba_recompute_compare_875_1000.json`
adds an opt-in `--veer-aln-post-nba-recompute` path that reruns
`TOP__16/17/18` after a changed NBA phase, but the first mismatch remains
`gpu_step=895` / CPU post-reset `898`. The default artifact has been rebuilt
without that diagnostic recompute. The next target is therefore not a simple
extra `TOP__18` call; trace or inspect the immediate inputs read by `TOP__18`
and the lowered ordering inside `TOP__18`. That follow-up now exists as
`reports/rtlmeter_veer_el2_dhry_top18_inputs_compare_875_1000.json`, using CPU
trace `reports/rtlmeter_veer_el2_cpu_dhry_top18_inputs_875_1002.json` and GPU
trace
`artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_top18_inputs_trace_1000/_sidecar/`.
The trace grows to 82 fields, below the 96-field runtime cap, and confirms the
first functional mismatch is still `gpu_step=895` / CPU post-reset `898`.
`TOP__18` local inputs mostly still match there (`bundle2`, `aligndata`,
`alignfromf1`, brdata enable, `ic_hit_f`, ECC/error, and freeff inputs), but
`ifu_pmu_instr_aligned` is already stale on GPU (`0` vs CPU `1`). Since that
signal is computed by `TOP__17` from matching `bundle2` and divergent
`dec_i0_decode_d`, the next concrete target is `dec_i0_decode_d` /
`i0_exublock_d` generation or lowered ordering before `TOP__17/18`. The
exublock-input trace now exists as
`reports/rtlmeter_veer_el2_dhry_exublock_inputs_compare_875_1000.json`, with
CPU trace
`reports/rtlmeter_veer_el2_cpu_dhry_exublock_inputs_875_1002.json` and GPU
trace
`artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_exublock_inputs_trace_1000/_sidecar/`.
It reaches the current trace cap exactly (`96` fields without `step`) and still
reproduces `gpu_step=895` / CPU post-reset `898`. The new `i0_exublock_d`
candidate inputs match at the first functional split; the remaining visible
upstream state difference is `decode_misc2ff=4` on GPU versus `0` on CPU,
alongside `decode_i0_exublock=1` versus `0`. Next work should replace lower
value trace columns with `misc2ff` DIN/enable/source fields and inspect the
lowered update order around that flop. In generated Verilator code,
`misc2ff[2]` is driven by `i0_div_decode_d` or by self-holding old
`misc2ff[2]` while `exu_div_wren` and `dec_div_cancel` are clear; the gated
`misc2ff` DIN is root-visible, so the next narrow trace should include that DIN
plus `exu_div_wren`, `dec_div_cancel`, `dec_debug_valid_d`,
`exu_flush_final`, and selected LSU bit-neighbor sources. That follow-up exists
as `reports/rtlmeter_veer_el2_dhry_misc2ff_inputs_compare_875_1000.json` and
keeps the trace width at 96 fields. It moves the first relevant split earlier:
at `gpu_step=894` / CPU post-reset `897`, GPU keeps `decode_misc2ff_din=4`
while CPU drops it to `0` because CPU sees `exu_div_wren=1` and GPU does not.
The divider-input trace
`reports/rtlmeter_veer_el2_dhry_div_inputs_compare_875_1000.json` then moves
the first split earlier again to `gpu_step=890` / CPU post-reset `893`, where
`exu_div_i_misc_ff_din` and `exu_div_shortq` already differ. Next work should
trace or inspect divider `shortq` / `i_misc_ff` update ordering and the
arithmetic inputs feeding those fields before trying longer `dhry` probes. The
deeper divider trace
`reports/rtlmeter_veer_el2_dhry_div_deep_compare_875_1000.json` keeps the
first focused split at `gpu_step=890` / CPU post-reset `893` and narrows it to
`exu_div_dw_shortq_raw`, `exu_div_shortq`, and `exu_div_i_misc_ff_din`: at that
row `exu_div_valid_in`, `exu_div_running_state`, `exu_div_i_misc_ff`,
`exu_div_shortq_enable`, `exu_div_quotient_raw`, `exu_div_quotient_new`, and
`exu_div_i_b_ff` match. Generated C++/IR inspection shows `dw_shortq_raw` is
written by `___nba_sequent__TOP__8`, `shortq` is written by
`___nba_sequent__TOP__9`, and the GPU IR still calls TOP__8 before TOP__9.
That debug gate has now been resolved as flat-memory initialization, not
divider lowering. `$readmemh` records outside the `0x80000000` 64 KiB flat
program window were writing through the unmapped default byte, eventually
making invalid reads return `0x0a0a0a0a...`. The missing `@10000000` control
window then fed bad `tb_lmem_axi_rdata` into `exu_div_a_ff` and caused the
apparent `dw_shortq_raw` split. The flat memory now separates unmapped writes
from default reads and materializes a 16-byte `0x10000000` control window. The
rebuilt artifact uses `syms_storage_size=433536`, and
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_1000.json` reports
`status=match` for 125 aligned rows and 62 compared fields across GPU steps
`875..999` with CPU rows mapped as `post_reset_posedges=gpu_step+3`. The
previous failing row (`gpu_step=890` / CPU `893`) now matches on
`tb_lmem_axi_rdata`, `exu_div_a_ff`, `exu_div_dw_shortq_raw`, `exu_div_shortq`,
and the divider input/result fields. This is bounded correctness evidence only;
the next longer same-window check also passes:
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_2000.json` reports
`status=match` for GPU steps `875..1999`, 1125 aligned rows, and 62 compared
fields with zero mismatched field observations. The next gate is therefore
either an even longer same-window `dhry` compare or a stdout-safe trace using the
fixed flat-memory layout, not a speedup/usefulness claim. The next same-window
extension now also passes:
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_5000.json` reports
`status=match` for GPU steps `875..4999`, 4125 aligned rows, and 62 compared
fields with zero mismatched field observations. This reaches the previous
5000-cycle bounded progress milestone with CPU/GPU trace equivalence, but it is
still not full `dhry` finish/stdout correctness or timing/usefulness evidence.
The latest long-window extension now reaches
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_50000.json` with
`status=match` for GPU steps `875..49999`, 49125 aligned rows, and 62 compared
fields with zero mismatched field observations. This is now captured by the
machine-checkable summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_trace_equivalence_875_50000.json`,
which passes while keeping `timing_measured=false`, `speedup_claimed=false`, and
`usefulness_claimed=false`. The next gate should move from same-window progress
equivalence to stdout-safe longer progress or finish reachability; do not
convert this into a speedup/usefulness claim.
That first stdout-safe longer-progress gate remains bounded-only. The refreshed
summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_stdout_safe_progress_100000_loopfix.json`
still reaches `mcycle=99999` and `minstret=95864` with
`step_trace_disabled=true`, `final_observable_stdout_requested=true`, and
`finish_marker_observed=false`, while keeping timing/speed/usefulness claims
disabled. The phase-aware loop diagnostic now executes for bounded `dhry`: the
10/100/1000-cycle loop outputs match resident fallback byte-for-byte, and the
1000-cycle case reduces actual timed launches from `6009` to `10` and GPU
kernel total from `272.929400ms` to `238.399490ms`. This still does not prove
usefulness because non-`hello` stdout and full finish are unproven and wrapper
wall did not robustly improve in the 1000-cycle sample. The 100000-cycle
phase-aware loop reaches `mcycle=99999` with no finish marker in `22.889812s`
runtime wall and `22404.386719ms` GPU kernel time. The generated bounded
projection report
`reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_negative_projection.json`
projects this to CPU RTLMeter cycles `5984259` as about `1340.75s` GPU-kernel
time versus `37.240654s` CPU serial wall, about `36.00x` slower by GPU-kernel
time alone, and records `negative_usefulness_decision=true`. The next gate is
to publish that decision to FC-037 / #2 and treat full non-`hello`
finish/stdout as future correctness work, not another loop-eligibility probe.
The
CPU-side parallel program idea is
validated by `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json`: three
different VeeR design-CPU programs preserve stdout/cycle equivalence and improve
from `107.522775s` serial-sum to `37.079953s` parallel wall (`2.899755x`), which
is CPU throughput evidence rather than GPU usefulness evidence.
The GPU side now reaches the same mixed-program shape at 100000 bounded cycles:
`reports/rtlmeter_veer_el2_mixed_state_dhry_cmark_cmark_iccm_100000_projection.json`
records `state0=dhry`, `state1=cmark`, and `state2=cmark_iccm` as distinct
per-state syms init images uploaded as one concatenated `storage_size*nstates`
blob while using the same generated GPU kernels. All three states reach
`mcycle=99999` with distinct final observables, but projection to the CPU mixed
baseline is about `36.95x` slower by GPU-kernel time alone. The next gate is
deciding whether to stop this current GPU path or add stronger per-state
finish/stdout observability for a different implementation direction.
Concrete task order for that gate:

1. Treat the current mixed-state GPU path as negative by bounded projection; do
   not spend more work on loop-eligibility for the same implementation.
2. If GPU work continues, first define a materially different implementation
   target with an explicit launch-count reduction mechanism and per-state
   finish/stdout observability contract.
3. Keep `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json` as the
   comparison floor for design-CPU program throughput; serial-only comparison is
   not enough for usefulness.
4. Keep FC-037 / GitHub #2 as the owner unless the next implementation leaves
   the RTLMeter timing/usefulness lane.
5. Use the mixed-state GPU/CPU summary's `recommended_action` and
   `materially_different_definition_gate` fields as the automation-readable
   stop/different-path handoff before starting more GPU performance work.

The minimum definition for a "materially different implementation" is now:

- **Resident execution**: one device operation must advance a bounded region of
  many VeeR design-CPU cycles per state. Repeating the current per-cycle or
  pair-cycle host launch shape with a larger wrapper is not enough.
- **Observable contract**: the design must name how each GPU state reports
  finish, stdout/mailbox bytes, RTLMeter cycle count, and final architectural
  counters without assuming state 0 represents every program. A no-trace
  final-observable-only run is bounded-progress evidence until this contract is
  implemented and compared.
- **Superstep boundary**: each resident region must have explicit entry
  conditions, exit conditions, and unsupported-side-effect checks. Host sync is
  allowed only at superstep boundaries, not at every design-CPU cycle.
- **GEM-like lowering candidate**: any LLVM/pass-based attempt must first
  identify a hot regular subproblem or helper family that can be lowered into a
  data-parallel kernel with stable memory layout. Reordering generic VeeR eval
  control flow without such a candidate is still the current implementation.
- **Usefulness gate**: compare against
  `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json` or a regenerated
  equivalent mixed-program CPU-parallel report. A GPU path that only beats
  serial CPU, or only reports bounded progress without finish/stdout, is not a
  usefulness result.

Until those five items are defined, the next action is to stop the current
mixed-state GPU path as a performance direction and keep full non-`hello`
finish/stdout as future correctness work.
For the known hello program, stdout-safe observability now exists as an
explicit final-observable stdout mode:
`reports/rtlmeter_veer_el2_hello_pair_cycle_loop_final_stdout_bridge.json`
passes normalized stdout/cycles comparison while preserving the loop-collapse
shape, and
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_smoke.json`
shows the same mode through the timing runner with one sample. The optimized
repeated timing gate now exists at
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_nstates16.json`:
it passes 21/21 correctness samples with one loop kernel, seven actual timed
GPU launches, and disabled final-observable stdout reconstruction. Its
`sidecar_wall_s_median=0.751716` is faster than the matching CPU-parallel
sixteen-worker baseline, but it is slower than the current best sixteen-state
fused pair-cycle sidecar result (`0.641226s`) and remains far slower than serial
CPU. The next gate is sidecar load/host overhead reduction or a general
device-side trace path for non-`hello` stdout. The first stage-timing diagnostic,
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_stage_timing_smoke.json`,
adds opt-in `RUN_VL_HYBRID_STAGE_TIMING` reporting and shows that the expensive
host side is CUDA init/context creation (`after_cuInit=157.850ms`,
`after_cuCtxCreate=346.810ms`) plus final sync/kernel time
(`after_final_sync=265.491ms`), while final state dump is only `8.076ms`.
Therefore the next performance gate should prototype persistent CUDA
context/runtime reuse before spending effort on dump compression.
That prototype now has a first smoke:
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_inprocess_repeats_smoke.json`
uses `VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS=3` to keep one CUDA
context/runtime setup, restore `d_storage` from a device snapshot, and repeat
the VeeR `hello` loop in-process. Correctness passes and the per-repeat kernel
median is `253.576187ms` with seven actual timed launches, but the report marks
CPU/serial wall comparison invalid as
`timing_comparison_scope=in_process_hybrid_repeat_diagnostic`. Persistent
context reuse is still valuable for runtime architecture, but this smoke does
not reveal a hidden speedup for tiny `hello`; the next useful gate should move
toward non-`hello` observability or deeper kernel/runtime reduction.
The
native-path #59 / #57 / #58 chain
remains important, but it is not the current pointer.

## 追跡タスク (Tracked tasks)

1. **RTLMeter VeeR-EL2 timing/usefulness gate**: FC-064 / #63 now reaches normalized stdout match and RTLMeter cycle-count match, and FC-037 / #2 now records three-batch timing stability results for eight-state, sixteen-state, and thirty-two-state sidecar gates with matching CPU-parallel `hello` baselines. The 16-state fused pair-cycle gate remains the best total-latency result with `sidecar_wall_s_median=0.641226`, `pair_cycle_fusion_launched_median=727.0`, and fallback median `0.0`. The 32-state fused pair-cycle gate passes 21/21 correctness samples and improves per-state wall and states/s by `1.349465x` versus 16-state, but total wall worsens to `0.950341s` and serial CPU remains about `23.758525x` faster. Patch/eval fusion and `posedge_only` have both been tried; `posedge_only` failed correctness. State-local patch compression also passes correctness and cuts records by `32x`, but regresses timing to `sidecar_wall_s_median=2.452390`, so it is not promoted. The cmark preload probe now fails closed rather than producing a false hello-backed state image, and reviewed matching preload materialization exists for `cmark`, `cmark_iccm`, and `dhry`. The current `dhry` fixed-flat-memory path has bounded same-window trace equivalence, 100k no-finish progress, phase-aware loop-collapse evidence through 100000 cycles, and a generated negative-usefulness projection for the current single-scenario GPU path. The mixed-state GPU init path now also reaches 100000 bounded cycles for `dhry`/`cmark`/`cmark_iccm` using one shared kernel sequence and per-state preloads, but its projection is about `36.95x` slower than the CPU mixed parallel baseline by GPU-kernel time alone. `reports/rtlmeter_hybrid_advantage_summary.json` now quantifies the split: `cpu_parallel_favorable=1`, `gpu_sidecar_unfavorable=4`, `gpu_sidecar_favorable=0`, `launch_feasibility_blocked=1`, and `gpu_bounded_progress=1`, with `prefer_cpu_parallel_control_with_gpu_bounded_batch_probes` as the current hybrid action.
2. **RTLMeter non-VeeR usefulness candidates**: `reports/rtlmeter_non_veer_usefulness_candidates.json` now separates measured NVDLA evidence from fail-closed Vortex first-gate readiness. NVDLA has `measured_shape_count=10` and `gpu_favorable_shape_count=10` across existing `cmac_core_mac` / `cmac_a2cacc` scoped coverage-output-equivalent hybrid gates; the best wall ratio is `11764.742765273311x` at `1024x64` for `nvdla_cmac_a2cacc`. A 2026-06-17 `NVDLA.nvdla_cmac_core_mac` `32x1` repeat-median refresh reached CPU reference capture but full-core GPU artifact generation stayed in `ptxas` for more than ten minutes and reached about 36 GiB RSS before being stopped, so the next useful NVDLA path is smaller hot SS partitioning rather than broad full-core lowering. Vortex readiness now has its own report at `reports/rtlmeter_vortex_first_gate_readiness.json`: `Vortex:mini:hello` is the first gate because its binary inputs exist and it is the descriptor sanity test, `config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json` records a fail-closed `runtime_launchable=false` authority for stdout `TEST PASSED` plus memory post-condition, and `config/slice_launch_templates/vortex_mini_hello.json` records a fail-closed `runtime_launchable=false` / `source_closure.status=incomplete` launch-template marker. `reports/rtlmeter_vortex_source_closure.json` now validates the descriptor-owned source closure: all `126` Verilog sources, `8` include files, and `1` CPP DPI source exist locally, without granting runtime launch authority. `reports/rtlmeter_vortex_dpi_memory_bridge_review.json` reviews the DPI boundary and shows that the gate is no longer blocked on understanding the bridge. `src/hybrid/vortex_memory_model_device.h` provides a host-compilable helper for 64-byte block initialization, byte-enable writes, IO_COUT capture, and post compare semantics. `reports/rtlmeter_vortex_device_buffer_materialize.json` materializes the runtime upload inputs into `artifacts/rtlmeter_vortex_mini_hello_device_buffers`: `37224` host-to-device bytes and `88` initial device-to-host bytes across `7` buffers. `reports/rtlmeter_vortex_dcr_schedule.json` materializes the ordered `9` DCR writes into a `72` byte little-endian runtime table and records the reset/valid timing protocol from `tb.sv`; it is still not runtime DCR application. `src/hybrid/vortex_runtime_upload.h`, `src/hybrid/vortex_observable_export.h`, and `src/hybrid/vortex_runtime_sequence.h` provide fake-driver-tested upload/export/runtime-sequence helpers, and `reports/rtlmeter_vortex_cuda_runtime_sequence_preflight.json` proves the sequence shape against the real CUDA Driver API with a no-op kernel callback. Vortex has now crossed the first CPU-vs-hybrid gate: the canonical `vlgpugen` std::ref pointer-return fix CUBIN reaches `after_cuCtxSynchronize`, exports `memory_post_condition` authority, and `reports/rtlmeter_vortex_timing.json` records hybrid median `0.4504947270033881s` versus CPU `0.22s` (`hybrid_vs_cpu_ratio=2.047703304560855`, no speedup claim). Treat Vortex `mini:hello` as a measured negative first gate; try Vortex `mini:saxpy` or `mini:sgemm` only after the active EH1/EH2 measurement blockers are addressed.
   `reports/rtlmeter_non_veer_hybrid_measurement_summary.json` now adds the comparable hybrid split index: `measured_design_count=1`, `measured_shape_count=10`, `gpu_favorable_shape_count=10`, `unmeasured_first_gate_candidate_count=1`, NVDLA `favorable_ratio=1.0`, and Vortex `cpu_vs_hybrid_timing_present=false`. This makes the current next step explicit: extend NVDLA hot-SS measurement before claiming broader RTLMeter GPU usefulness, while keeping Vortex as the next architecture-diverse first-gate once its lowered-TB invocation and observable authority are wired.
   `reports/rtlmeter_non_veer_hybrid_next_queue.json` now turns that split into an ordered next-measurement queue. Priority 1 is `nvdla_hot_ss_measurement_extension`: repeat or extend the best measured NVDLA hot-SS bucket, `state_batch_and_repeated_step`, with preferred shape `1024x64` on `nvdla_cmac_a2cacc`. Priority 2 is `vortex_mini_hello_first_cpu_vs_hybrid_gate`; its current first blocker has moved past memory-helper integration and kernel artifact generation to real artifact wiring.
   Latest Vortex audit refinement: `reports/rtlmeter_vortex_observable_authority_audit.json` now reports `real_runtime_observable_authority_ready=true`, `real_cuda_materialized_runtime_authority_ready=true`, and authority source `memory_post_condition`. `reports/rtlmeter_vortex_timing.json` measures three authority-passing repeats and records hybrid median `0.4504947270033881s` versus CPU `0.22s`, so this is a measured negative first gate, not a speedup claim.
   This latest audit refinement supersedes the older same-paragraph shorthand that described generated lowered-TB invocation/authority, verifier-clean artifact generation, missing callback wiring, or PTX module-load/JIT timeout as the remaining Vortex blocker. The observed immediate blocker is kernel illegal memory access, not descriptor source ambiguity, DPI-format ambiguity, memory-helper integration, landingpad/personality verification, callback ABI wiring, or `cuModuleLoad`.
   `reports/rtlmeter_nvdla_hot_ss_measurement_plan.json` now materializes priority 1 as a concrete, non-executing NVDLA plan: repeat-median confirm `1024x64`, check `512x64`, probe `2048x64`, and separate the state-batch effect with `1024x1`, all on `NVDLA.nvdla_cmac_a2cacc`. This keeps the next useful measurement on the small hot-SS target and leaves `NVDLA.nvdla_cmac_core_mac` deferred because of the recent high `ptxas` compile-cost observation.
   `reports/rtlmeter_nvdla_hot_ss_plan_dry_run.json` preflights all four planned commands successfully. The first plan item now has repeat-median evidence in `reports/nvdla_cmac_a2cacc_repeat_median_1024x64.json`: `repeat_count=3`, `coverage_output_equivalence_all_passed=true`, coverage-output mismatch count `0` in all samples, median CPU `2142.1 ms`, median hybrid wall `1.755 ms`, and median CPU/hybrid wall speedup `1430.950752393981x`. Treat this as scoped NVDLA hot-SS usefulness evidence only; raw final-state equality still fails on Verilator/internal fields.
   The lower-neighbor `512x64` plan item now also passes repeat-median coverage-output equivalence in `reports/nvdla_cmac_a2cacc_repeat_median_512x64.json`, with median CPU `1056.75 ms`, median hybrid wall `1.602 ms`, and median CPU/hybrid wall speedup `663.2209737827715x`. The larger-state `2048x64` plan item also passes in `reports/nvdla_cmac_a2cacc_repeat_median_2048x64.json`, with median CPU `4244.47 ms`, median hybrid wall `1.662 ms`, and median CPU/hybrid wall speedup `2553.8327316486166x`. The state-batch-only `1024x1` plan item passes in `reports/nvdla_cmac_a2cacc_repeat_median_1024x1.json`, with median CPU `2090.2 ms`, median hybrid wall `2.628 ms`, and median CPU/hybrid wall speedup `791.3432267884323x`. `reports/rtlmeter_nvdla_hot_ss_repeat_summary.json` summarizes the four-shape plan as four measured, four coverage-passed, and four GPU-favorable shapes; `2048x64` is the best measured shape. State batching alone is favorable, and repeated-step batching improves the best observed wall ratio further.
   `reports/rtlmeter_gpu_favorable_conditions_audit.json` now closes the current search question as `goal_satisfied_by_nvdla_hot_ss`: NVDLA `a2cacc` scoped hot-SS has reproducible positive evidence, while Vortex now has a measured architecture-diverse first CPU-vs-hybrid gate, but it is slower than the CPU reference and remains a negative first-gate result.
3. **Docs pointer sync**: Keep `config/selection.json`, `docs/status.md`, this roadmap, README, and `for_codex/issues.md` aligned on `clone_compact_cluster_body_into_outline_callee_and_rewire_control_flow`.
4. **Simple verification doc**: Keep `docs/migration_notes.md` “Gap from a minimal verification setup” accurate when entrypoints or prerequisites change.
5. **Gate chain hygiene**: When advancing `current_priority`, update `completed_goal_evidence` in `config/selection_extensions.json` only with tracked records; keep linked source-of-truth files clone-reproducible.
6. **Native Verilator sidecar track**: Keep #59 as a related native-path side track under #46, not the global current priority while FC-069 integrates the gateGPT ordering-aware token-loop path. Do not treat stamp/build-driver success as shim-entry evidence; the final `obj_dir/V<top>` link inputs must include the sidecar shim object/library or equivalent repo-owned runtime object.
7. **RTLMeter first seed**: Keep `Example:kind:hello` scoped and non-claiming. The reviewed stdout/cycles source-closure authority now exists in the RTLMeter authority registry, runner argv handoff executes through a thin runner CLI before stdout/cycles observation, and the latest real opt-in run reaches `status=passed` / `comparison=passed` with marker-backed `execution_authority=true` and `sidecar_execution_invoked=true`. This is historical first-seed proxy/marker handoff evidence only: `gpu_execution_claimed=false`, `speedup_claimed=false`, `runtime_abi=false`, CPU-as-GPU fallback is forbidden, and metadata-only authority registries, `run_hybrid_template.py` launch templates, and runner metadata must not become RTLMeter acceleration evidence. The proxy lane (#49/#51/#53) is frozen under the native Verilator sidecar goal; current RTLMeter correctness is gated on FC-064 / #63 for VeeR-EL2, with FC-058 / #58 retained as related native-path context.
8. **RTLMeter VeeR-EL2 design CPU**: FC-064 / #63 is the passing fail-closed automatic readiness gate for `VeeR-EL2:default:hello`. The current inspection verifies source closure, program identity, observable expression binding, PC/GPR schema, ICCM/DCCM 4-bank ECC preload schema, GPU state-image initialization schema, and RTLMeter stdout/cycles compare binding. The materializer emits the reviewed extracted state image for `hello` with inactive ICCM/DCCM bank preloads. A real VeeR build records an automatic root-image to syms-state-image rebuild, produces `vl_batch_gpu.cubin` (`storage_size=433472`), and maps 52 required root fields from the generated layout, including reset/nmi vectors. The reviewed executable `src/tools/veer_el2_sidecar_executable.py` consumes the extracted state image, materializes a syms-state init image, writes the reset/nmi vectors, drives a clock/reset patch, launches the generated artifact, dumps GPU state, and writes sidecar stdout/cycles files without copying CPU observables. The bridge reaches `status=verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed` with `cpu_cycles=2229` and `gpu_cycles=2229`. FC-037 timing now records `sidecar_slower_than_serial_cpu` for `hello`; no GPU usefulness or speedup claim is allowed.

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

Use #2 / FC-037 as the current VeeR-EL2 RTLMeter timing/usefulness gate. #63 /
FC-064 already proves the state-image/stdout/cycles safety slice: the reviewed
VeeR sidecar executable launches the generated artifact, emits stdout/cycles
observables, reconstructs normalized stdout, and matches RTLMeter cycles at
`2229`. The latest timing report beats the comparable CPU-parallel floor across
three seven-sample batches and remains slower than serial CPU for `hello`; the
required advance is no longer proving low/high pair-cycle correctness, basic
loop launch-count collapse, or a final-observable stdout/cycles compare for
`hello`. The remaining blocker is making the fixed-flat-memory non-`hello`
`dhry` path eligible for loop collapse despite the multi-kernel VeeR launch
sequence, then measuring finish/timing/usefulness only after that path actually
launches loop kernels.
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

`partition_local_eval_continuation_guard_cpu_oracle_validation`

Acceptance criteria:

- use `for_codex/issues.md` and GitHub #69 as the source artifact/tracker
- verify `README.md`, `docs/status.md`, this roadmap, `for_codex/issues.md`, and `config/selection.json` agree that FC-069 is current
- use the latest schedule-owned ordering-aware result as the baseline: `16/16` source probe passed, the non-diagnostic same-CPU-oracle baseline is GPU wall `404.986 ms` / kernel `404.90036 ms` versus CPU oracle `107.71662899060175 ms` (`3.759735184762744x` slower), and no speedup/usefulness is claimed
- treat the guarded/liveout diagnostic path as validation-only and performance-negative: GPU wall `19232.031 ms` / kernel `19231.960938 ms`, `178.5428227769548x` slower than the same CPU oracle
- use the compact CFG clone materialization result as the new baseline: `65` blocks, `944` cloned instructions, `65` cloned terminators, `48` PHIs, `48` static CFG-clone liveout stores, unsupported terminators `0`, and `outline_call_count=3434752`
- resolve the baseline-isolation blocker: outline entry reaches `compact_cluster.cfg_clone.entry` and the generated IR verifies; post-capture compare validates reached CFG-clone liveout capture points (`liveout_frame_store_count=82434048`, `compare_count=150480`, `mismatch_count=0`, authority=true). The non-diagnostic same-CPU-oracle baseline is measured and still negative (`baseline_gpu_wall_ms=404.986`, `baseline_gpu_kernel_ms=404.90036`, CPU oracle `107.71662899060175 ms`, `3.759735184762744x` slower); the diagnostic guarded/liveout path is GPU wall `19232.031 ms` / kernel `19231.960938 ms` and remains validation-only at `178.5428227769548x` slower. The Pass emits partition-local eval continuation guard static shape for `8` guarded regions with `1344` successor-PHI incoming values. Runtime-noop derivation is blocked by successor PHI live-out for all `832` inspected selects (`0` elision-safe, authority `no_runtime_noop_derivation_authority`). Successor-PHI continuation user classification is complete for `168` successor PHIs / direct users / direct load users / load-consumed PHIs, with `0` direct non-load users, `168` load-result direct users, `0` unsupported load-result users, and `1` candidate cluster under `classification_only_no_runtime_skip_or_select_elision_authority`, so the analyzer keeps CPU-oracle validation blocked until inactive-path noop/skip authority and runtime guard execution observation exist.
- keep the older CFG-clone memory-read isolation, shadow liveout compare, valid-frame, and select-only PHI repair gates as historical preconditions; they are no longer the active next gate after successor-PHI continuation user classification.
- implement the current next action: `clone_compact_cluster_body_into_outline_callee_and_rewire_control_flow`
- do not claim speedup from a single run or from comparison against serial CPU alone
- keep broad `verilator --use-gpu`, arbitrary filelist inference, automatic GPU allocation, RTLMeter speedup/usefulness, CIRCT execution, raw-state equality, JSON runtime ABI, and production-readiness claims out of scope unless later gates prove them

Scientific-compute CIRCT side lane:

- `reports/scientific_circt_gpu_candidate_plan.json` is the current plan-only
  evidence for converting scientific kernels through CIRCT-generated
  SystemVerilog, Verilator, lowered LLVM IR suitability, and repeat-median
  CPU/hybrid measurement.
- The current status is `blocked_circt_toolchain_missing`: Verilator and
  `clang++` are available, but `circt-opt`, `circt-translate`, and `firtool`
  are not on `PATH`.
- The first materialization target should be `dense_matmul_tile`, then shapes
  `64x1`, `256x1`, and `1024x1`, because that candidate best matches the
  known GPU-favorable pattern: regular memory, low observable pressure, high
  arithmetic intensity, and many independent states/tiles.
- The candidate plan deliberately keeps branch-heavy sparse/control kernels in
  the CPU-parallel-or-new-mapping bucket until static suitability and measured
  evidence say otherwise.
- This lane must not claim CIRCT execution, generated RTL, Verilator success,
  GPU execution, timing, speedup, usefulness, or automatic hybrid partitioning
  until the corresponding gates produce evidence.

Deferred technical workstreams:

- native Verilator parser boundary
- arbitrary filelist-to-sidecar planner
- filelist dependency inference
- broader automatic GPU allocation policy
- resident execution optimization
- GEM comparison boundary

## Archive Boundary

Historical gate details remain in `records/scaling_gates/`, with `config/scaling_gates` kept as a compatibility link. Generated summaries are reproducible under `reports/`, and build/raw outputs are reproducible under `artifacts/`; both directories may contain local generated evidence. They should not be copied back into `selection.json`, `README.md`, or this roadmap as canonical decisions.
