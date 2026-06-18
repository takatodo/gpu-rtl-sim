# Agent Issue Index

This is the Codex-facing issue index. Each issue has its own file under `for_codex/issues/`, so agents can claim and edit one issue without touching a shared table.

Status values: `open`, `claimed`, `blocked`, `review`, `done`.

## GitHub Issue Coordination

Use GitHub Issues through `gh` for live coordination when the repository has an
accessible remote issue tracker. The local FC files are useful for design
context and file-scoped acceptance criteria, but they should not become a
private task queue that other agents cannot see.

Recommended flow:

```sh
gh issue list
gh issue create --title "FC-XXX: <short title>" --body-file for_codex/issues/FC-XXX-<slug>.md
gh issue comment <number> --body "<validation, blocker, or handoff note>"
```

Rules:

- Prefer one GitHub issue per actionable FC issue.
- Keep the GitHub title prefixed with `FC-XXX` when mirroring an FC file.
- Add the matching GitHub issue URL or number to the FC file when useful, but do
  not make GitHub-only metadata the source of truth for design decisions.
- Use `gh issue edit` or `gh issue comment` to record status transitions instead
  of relying only on local unpushed markdown edits.
- Close issues only after acceptance criteria and validation are recorded, or
  after a replacement issue is linked.
- Never claim success from a blocked environment; record the blocker explicitly.

Current GitHub mirror:

| Local FC | GitHub Issue | Notes |
|---|---|---|
| FC-034 | https://github.com/takatodo/gpu-rtl-sim/issues/8 | Historical first RTLMeter executing correctness issue for the proxy/marker lane; local first-seed stdout/cycles compare passes with marker-backed execution authority, but #49 closure is frozen in favor of FC-058 direct-native correctness. |
| FC-035 | https://github.com/takatodo/gpu-rtl-sim/issues/7 | Clean sim GPU runtime preflight; classify blocked CUDA driver access without reporting success. |
| FC-036 | https://github.com/takatodo/gpu-rtl-sim/issues/6 | Move generated helper binaries out of `src/`; clean-sim hardening, not RTLMeter execution. |
| FC-037 | https://github.com/takatodo/gpu-rtl-sim/issues/2 | Active RTLMeter VeeR-EL2 timing/usefulness issue after FC-064 / #63 passed direct sidecar stdout/cycles equivalence. The timing gate now records repeated `hello` sidecar gates with matching CPU-parallel duplicate-`hello` baselines. The latest non-fusion representative is `reports/rtlmeter_veer_el2_timing_nstates16.json`: serial CPU `0.04s`, sixteen-worker CPU-parallel wall `2.218887s`, sidecar wall median `0.768573s`, GPU kernel total median `268.161011ms`, and `speedup_claimed=false`. Patch/eval fusion passed correctness but did not improve that median. `posedge_only` reduced work but failed correctness with VeeR counters stuck at zero. The true fused pair-cycle path (`VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle` plus `VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1`) passes `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json` with 21/21 correctness samples, `sidecar_wall_s_median=0.641226`, `gpu_kernel_ms_total_median=262.026245`, `pair_cycle_fusion_launched_median=727.0`, and fallback median `0.0`; this remains the best total-latency sidecar result but is still about `16.030650x` slower than serial CPU. The 32-state scale point now passes after raising the runtime patch-script limit to 256: `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json` records `sidecar_wall_s_median=0.950341`, `gpu_kernel_ms_total_median=357.866486`, `gpu_kernel_timed_launch_count_median=733.0`, and `sidecar_vs_cpu_parallel_ratio=4.468648`. Compared with 16-state fused, total wall worsens by `1.482069x`, but per-state wall/states-s improve by `1.349465x`. The state-local compression probe `reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json` passes correctness and cuts patch records by `32x`, but regresses wall to `2.452390s` and GPU kernel total to `1675.526123ms`, so it is rejected as a performance path. The cmark mismatch probe now fails closed in `reports/veer_el2_cmark_state_image_materialize_after_fix.json`; reviewed matching preload materialization now exists for `cmark`, `cmark_iccm`, and `dhry` in `reports/veer_el2_cmark_state_image_materialize.json`, `reports/veer_el2_cmark_iccm_state_image_materialize.json`, and `reports/veer_el2_dhry_state_image_materialize.json`. The launch-count feasibility gate now blocks full `cmark`/`cmark_iccm` timing before bridge execution in `reports/rtlmeter_veer_el2_timing_cmark_launch_feasibility.json` and `reports/rtlmeter_veer_el2_timing_cmark_iccm_launch_feasibility.json` with estimated actual timed launches `5276412` and `6024133` versus threshold `100000`. Bounded one-cycle non-`hello` smoke reaches GPU launch, and 500-cycle bounded progress now reaches `mcycle=499` with `minstret=321` for `dhry`, `342` for `cmark`, and `418` for `cmark_iccm` in `reports/rtlmeter_veer_el2_dhry_bounded_progress_500.json`, `reports/rtlmeter_veer_el2_cmark_bounded_progress_500.json`, and `reports/rtlmeter_veer_el2_cmark_iccm_bounded_progress_500.json`; the aggregate summary is `reports/rtlmeter_veer_el2_non_hello_bounded_progress_summary.json`. This is bounded progress evidence only, not full correctness or usefulness. Serial CPU is still much faster than all measured sidecar paths, so no broad speedup/usefulness claim is allowed. The first opt-in pair-cycle loop fusion surface is implemented, built, and exercised in `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_no_trace_500.json` and `reports/rtlmeter_veer_el2_hello_pair_cycle_loop_no_trace_full_event.json`: bounded `dhry` and full `hello` cycles each collapse to one loop kernel and seven actual timed launches, and `hello` reaches `finish_marker_observed=true`, `mcycle=726`, `minstret=330`, and `cycles=2229`. This is launch-count-collapse and full-program-event evidence only because stdout trace is disabled; next blocker is stdout-safe device-side trace before full timing or usefulness claims. |
| FC-038 | https://github.com/takatodo/gpu-rtl-sim/issues/3 | Dedicated clean-sim operator log hygiene issue. |
| FC-039 | https://github.com/takatodo/gpu-rtl-sim/issues/1 | Existing public goal-framing issue; do not create a duplicate. |
| FC-040 | https://github.com/takatodo/gpu-rtl-sim/issues/4 | Second RTLMeter seed broadening; bounded to one seed and gated on FC-064 VeeR stdout/cycles correctness plus FC-037 timing/usefulness evidence. FC-058 remains related native-path context, not the current VeeR correctness gate. |
| FC-041 | https://github.com/takatodo/gpu-rtl-sim/issues/5 | Installable PATH `verilator` wrapper; delegates for non-GPU, fails closed for unsupported GPU argv. |
| FC-042 | https://github.com/takatodo/gpu-rtl-sim/issues/9 | Closed/completed after #35; first real scoped `verilator --use-gpu` path remains one reviewed wrapper route, not arbitrary RTL support. |
| FC-043 | https://github.com/takatodo/gpu-rtl-sim/issues/10 | Frontend-neutral sidecar contract and CIRCT placeholder boundary; not CIRCT execution. |
| FC-044 | https://github.com/takatodo/gpu-rtl-sim/issues/11 | External-user readiness audit; remove or demote misleading surface area. |
| FC-045 | https://github.com/takatodo/gpu-rtl-sim/issues/19 | GPU sidecar eligibility and shape policy; consume FC-056 scoped timing evidence without broad speedup claims. The first importable helper and thin dry-run CLI now consume FC-063/FC-065 suitability JSON as debug/review metadata and emit conservative `recommended_action` values. Treat `64x1` as correctness/UX smoke, route VeeR/design-CPU-like poor suitability to CPU-parallel or new-mapping work, fail closed for unreviewed source closure, and only recommend GPU performance for reviewed large independent-state regions with caveats. |
| FC-046 | https://github.com/takatodo/gpu-rtl-sim/issues/20 | LLVM GPU optimization pass roadmap; umbrella only, not implementation evidence. |
| FC-047 | https://github.com/takatodo/gpu-rtl-sim/issues/21 | Emit GPU ABI metadata in generated IR. |
| FC-048 | https://github.com/takatodo/gpu-rtl-sim/issues/22 | Canonicalize safe constant-offset state accesses. |
| FC-049 | https://github.com/takatodo/gpu-rtl-sim/issues/24 | Conservative NVPTX inline/noinline policy. |
| FC-050 | https://github.com/takatodo/gpu-rtl-sim/issues/25 | Trigger guard factoring for proven-safe adjacent wrappers only. |
| FC-051 | https://github.com/takatodo/gpu-rtl-sim/issues/23 | Opt-in resident step kernel; separate correctness gate required. |
| FC-052 | https://github.com/takatodo/gpu-rtl-sim/issues/26 | Hot-field SoA exploration; ABI-changing and last in order. |
| FC-054 | https://github.com/takatodo/gpu-rtl-sim/issues/54 | First native-path slice under FC-053 / #46. M2 (recognition) + M3 (verilator option → make → build_vl_gpu → real SM89 CUBIN with GPU kernels) proven end-to-end on `pulp_ita_mha`. M4 (obj_dir binary alone runs GPU) and M5 (coverage equivalence) NOT done: the `make` exe is the plain CPU `--main` binary, and the native CUBIN (storage 5760) hits CUDA 700 vs the working 7-stage template CUBIN (storage 6144) because the native path omits host-probe/state-init stages. No GPU-execution or speedup claim. |
| FC-055 | https://github.com/takatodo/gpu-rtl-sim/issues/55 | Satisfied (temporary reviewed endpoint, commit b3da44d): the native make driver delegates the recognized `pulp_ita_mha 64x1` closure to the reviewed `run_hybrid_template` 7-stage flow, reaching real GPU sidecar execution (storage 6144) and `coverage_output_equivalence` mismatch=0; unrecognized fail-closed. Preferred endpoint (obj_dir binary direct GPU execution / in-process runtime ABI) remains a later issue. No timing/speedup claim. |
| FC-056 | https://github.com/takatodo/gpu-rtl-sim/issues/56 | Honest apples-to-apples CPU-vs-GPU timing for `pulp_ita_mha`; gated behind FC-057 direct `obj_dir` GPU execution and FC-058 RTLMeter direct-native correctness. Existing timing notes are pre-gate exploratory evidence only and do not permit broad speedup claims. |
| FC-057 | https://github.com/takatodo/gpu-rtl-sim/issues/57 | Replace the FC-055 temporary runner-delegation endpoint with direct `obj_dir/V<top>` GPU sidecar runtime integration for the recognized native path. Also removes user-facing `GPU_RTL_SIM_REPO_ROOT`-style repo-root plumbing from the normal make/run path. |
| FC-058 | https://github.com/takatodo/gpu-rtl-sim/issues/58 | After FC-057, run the first RTLMeter seed through the direct native sidecar executable path without proxy/env/review-manifest handoff, then close or supersede #49/#51/#53. 2026-06-14 probe reached RTLMeter/Verilator build but failed closed because `Example:kind:hello` `top` plus generated `filelist` is not a native sidecar known closure. Keeps timing and second seed gated. |
| FC-059 | https://github.com/takatodo/gpu-rtl-sim/issues/59 | First child slice under FC-057: prove `obj_dir/V<top>` can link and enter a minimal in-process sidecar shim directly, without `run_hybrid_template.py` runtime delegation. Smoke only: no kernel-launch, coverage, timing, or full FC-057 claim unless separately verified. |
| FC-060 | https://github.com/takatodo/gpu-rtl-sim/issues/60 | Next child slice under FC-057 after FC-059: direct `obj_dir/V<top>` executable loads or validates the expected native-path GPU artifact and records artifact-load evidence. Smoke only: no kernel-launch, coverage, timing, or full FC-057 claim unless separately verified. |
| FC-061 | https://github.com/takatodo/gpu-rtl-sim/issues/61 | Next child slice under FC-057 after FC-060: direct `obj_dir/V<top>` executable loads the adjacent CUDA module and launches the expected GPU kernel. Smoke only: no coverage equivalence, timing, or full FC-057 claim unless separately verified. |
| FC-062 | https://github.com/takatodo/gpu-rtl-sim/issues/62 | Next child slice under FC-057 after FC-061: direct `obj_dir/V<top>` executable records accepted coverage-output equivalence evidence with mismatch count 0. This is the FC-057 correctness closure candidate only when prior shim/artifact/kernel evidence is also in place; no timing, speedup, RTLMeter, or arbitrary RTL claim. |
| FC-063 | https://github.com/takatodo/gpu-rtl-sim/issues/64 | LLVM RTL GPU suitability analysis pass under FC-046 / #20. Adds a static LLVM IR review/debug JSON surface that classifies state-parallel GPU candidates versus CPU-parallel or new-implementation/GEM-like candidates from branch density, memory regularity, state independence, and observable pressure. This is not GPU execution, runtime ABI, correctness equivalence, timing, speedup, or RTLMeter usefulness evidence. |
| FC-064 | https://github.com/takatodo/gpu-rtl-sim/issues/63 | Scoped RTLMeter VeeR-EL2 design-CPU known-closure and state-layout task. Source closure, `tb_top`/filelist recognition, program identity, PC/GPR schema, ICCM/DCCM 4-bank ECC preload schema, GPU state-image initialization schema, extracted state-image materialization, RTLMeter stdout/cycles compare binding, and the direct sidecar observable-bridge command now inspect cleanly for `hello`. A real VeeR build records automatic root-image to syms-state-image rebuild, produces `vl_batch_gpu.cubin` (`storage_size=433472`), and the bridge/build report maps 52 required root fields from the generated layout, including reset/nmi vectors. The reviewed executable `src/tools/veer_el2_sidecar_executable.py` consumes the extracted state image, materializes a syms-state init image, writes reset/nmi vectors, drives a clock/reset patch, launches the generated artifact, dumps GPU state, and writes sidecar stdout/cycles without copying CPU observables. The bridge reaches `sidecar_observables_ready=true`; GPU final state reaches `mcycle=726`, `minstret=330`, and `finish_marker_observed=true`, matching the architectural counters printed by CPU stdout. GPU stdout stream reconstruction reaches normalized stdout match, and `_rtlmeter_cycles.txt` is aligned to RTLMeter's `tb_top.core_clk` count. The bridge now passes stdout/cycles equivalence with `cpu_cycles=2229` and `gpu_cycles=2229`. No speedup, usefulness, arbitrary RTLMeter, or arbitrary CPU-core claim until timing is measured. |
| FC-065 | https://github.com/takatodo/gpu-rtl-sim/issues/65 | Real lowered IR suitability corpus gate under FC-063 / #64. The contract test now runs the public analyzer CLI with `--write-report` on compact lowered-IR-style state-parallel and VeeR/design-CPU-like samples, plus one temporary C++ sample regenerated through the existing `build_vl_gpu_compile.compile_ll` clang emit-LLVM helper. FC-063 metrics now include defined callees reachable from `--entry` plus reachable external/intrinsic call evidence, preserving helper-level pressure, required metrics, dotted/quoted entry coverage, generated-report path hygiene, and review/debug-only JSON non-claims. No GPU execution, runtime ABI, correctness equivalence, timing, speedup, RTLMeter usefulness, or large generated IR source-of-truth claim. |
| FC-068 | https://github.com/takatodo/gpu-rtl-sim/issues/68 | gateGPT `tb_core` padded-start schedule lowering gate under #67. Promote the planner/artifact-backed padded-start shape into LLVM pass or build-metadata lowering, then rerun the 16-state lower-launch CPU compare. Latest local evidence: standard path `393.999 ms` wall with 35 launches, padded-start `366.21 ms` wall with 26 launches, CPU oracle `84.66219899128191 ms`; `gategpt_schedule_planner` now generates the schedule-lowered `run_vl_hybrid` argv, `run_vl_hybrid.py --schedule-lowering-plan` consumes the plan artifact, and generated build metadata exposes `schedule_lowering_capabilities.padded_start_pair_cycle_loop=available` with no missing runtime entrypoints. The 7-repeat CPU comparison claims only the lower-launch gate; usefulness and speedup remain unclaimed. |
| FC-069 | https://github.com/takatodo/gpu-rtl-sim/issues/69 | gateGPT `tb_core` ordering-aware phase-resident token-loop prototype under #67 after #68. Current build metadata reports `vl_tb_core_ordering_aware_phase_resident_token_loop_gpu` as available and the diagnostic schedule-owned token-loop path still passes the 16/16 CPU-token oracle. Post-capture compare validates reached CFG-clone liveout capture points: outline_call_count=3434752, liveout_frame_store_count=82434048, compare_count=150480, mismatch_count=0, actual_store_slots_per_outline_call=24, and compare_slots_per_outline_call=0.043811023328612954. A baseline-isolation entrypoint builds `obj_tb_core_nondiagnostic` with `build_vl_gpu.py --disable-cfg-clone-diagnostics` plus `RUN_VL_HYBRID_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI=1`. Replacement same-CPU-oracle timing remains CPU-negative: non-diagnostic GPU wall `404.986 ms` / kernel `404.90036 ms` versus CPU oracle `107.71662899060175 ms` (`3.759735184762744x` slower). The LLVM Pass emits a partition-local eval continuation guard static shape: target/guarded/successor-PHI-defined regions `8/8/8`, successor PHI incoming `1344`, blocked runtime-noop selects `832`, authority `static_control_flow_guard_shape_no_runtime_skip_or_noop_authority`. Successor-PHI continuation user classification is complete for `168` successor PHIs / direct users / direct load users / load-consumed PHIs, with `0` direct non-load users, `168` load-result direct users, `0` unsupported load-result users, and `1` candidate cluster under `classification_only_no_runtime_skip_or_select_elision_authority`. Existing pass evidence has also reached compact cluster outline frame-call ABI stub materialization: `1` outline callee, `63` outline call sites, `175` explicit live-ins, `48` explicit live-outs, `242` lowered live-in frame stores, `48` lowered live-out frame stores, and `0` unsupported live-in/live-out frame values, with `outline_frame_call_abi_stub_materialized_no_semantic_outline_authority`. The analyzer now records `blocked_partition_local_eval_continuation_guard_runtime_execution_summary_missing`; runtime noop/skip authority and semantic guard authority are false, so existing CPU-token/CFG-clone oracle checks do not validate this guard path. Guarded/liveout oracle validation still requires the diagnostic artifact and remains validation-only: GPU wall `19232.031 ms` / kernel `19231.960938 ms` versus the same CPU oracle (`178.5428227769548x` slower). Speedup/usefulness and broad gateGPT PASS/FAIL authority remain unclaimed. Next required evidence is `clone_compact_cluster_body_into_outline_callee_and_rewire_control_flow`; the follow-on minimal runtime hook is a diagnostic `partition_local_eval_continuation_guard_runtime:` stdout/counter summary. |
| FC-070 | unmirrored | Scientific CIRCT GPU candidate search. Adds a plan-only surface for lowering scientific-compute kernels through CIRCT-generated SystemVerilog, Verilator, lowered LLVM IR suitability, and repeat-median CPU/hybrid measurement gates. The current environment has Verilator and clang++ but no CIRCT executable on `PATH`, so the first status is expected to fail closed as `blocked_circt_toolchain_missing`. No CIRCT execution, SystemVerilog generation, Verilator build, GPU execution, speedup, usefulness, or automatic partition claim is made by the plan alone. |

FC-001 through FC-033 remain local planning issues unless they are promoted to
GitHub. When promoting more issues, check existing GitHub titles first and keep
duplicates linked instead of creating parallel trackers.

External testbench candidate note: `gateGPT`
(`https://github.com/fguzman82/gateGPT` at
`f1a604e998022b528a962e0af8af3d89e5f369b5`) is recorded only as an external
checkout candidate, not a vendored source dependency. GitHub #66 tracks the
bounded testcase execution gate. The accepted local gate keeps
`sim/tb_mathops.v` as the raw-checkout Verilator lint-only smoke, then runs
`tb_mathops`, `tb_exp`, `tb_matvec`, `tb_norm`, `tb_attn`, and `tb_core` in an
evaluation-only normalized copy under `artifacts/gategpt_local_eval/gateGPT`,
recorded in `reports/gategpt_testbench_probe.json` with
`status=gategpt_gpu_smoke_and_tb_mathops_sequence_compare_passed_without_pass_fail_export`.
All six normalized obj_dirs also pass PTX build plus one zero-init GPU kernel
launch smoke. The result shows the current LLVM pass/runtime path can emit and
launch gateGPT kernels, and `tb_mathops` DUT outputs can be driven and compared
through a full byte-level clocked patch sequence. It still does not prove full
gateGPT PASS/FAIL equivalence because initial blocks, `$readmemh` setup,
`$display` checks, `$finish`, and PASS/FAIL authority are not represented as GPU
execution authority. No speedup, usefulness, arbitrary RTL support, or
vendored-source claim is made; vendoring remains blocked by the missing license
file.

GitHub #67 tracks the gateGPT semantic-equivalence lane. The first selected
candidate was `tb_mathops` because it has six division cases and seven
square-root cases, with CPU PASS authority reducible to `errors == 0`; that
candidate now has a reviewed init/input contract, observable manifest, and
manifest-consuming semantic compare rather than only basic PTX emission.
Generated C++ still routes the original stdout/finish path through
coroutine/timing scheduler code plus `VL_WRITEF_NX` and `VL_FINISH_MT`; current
GPU IR emission does not export those events as device observables. A generated field-offset
manifest for the relevant drive/observe fields, including
`tb_mathops__DOT__errors`, `tb_mathops__DOT__d_quo`, and
`tb_mathops__DOT__s_root`, is now recorded in
`reports/gategpt_testbench_probe.json`. The report also consumes that manifest
for the full six-divider plus seven-sqrt `tb_mathops` sequence; all 13 observed
DUT results match CPU reference values. The selected `tb_mathops` PASS policy is
now accepted as that manifest-consuming DUT-output compare plus final
`errors == 0`, while stdout PASS/FAIL export and `$finish` export remain
unclaimed. The probe now also extracts a CPU Verilator stdout/finish authority
manifest for all six normalized benches: all six have PASS plus `$finish`,
`tb_core` has structured token/cycle stdout lines before PASS, and the
data-backed benches need readmem/init-state contracts. `tb_exp`, `tb_matvec`,
`tb_norm`, and `tb_attn` now have those contracts. The generated GPU-output
mapping plan is
`covered_by_bench_specific_gpu_output_manifests_without_stdout_finish_export`: `tb_mathops` is covered by
the selected DUT-output policy, `tb_exp` is covered by a bench-specific
vector-sequence DUT-output compare, and `tb_matvec`/`tb_norm`/`tb_attn` are
covered by bench-specific vmem output sequence compares. `tb_core` is covered by
a bench-specific structured root-state sequence compare. The first data-backed contract is
now defined for `tb_exp`:
`generated/test_exp_z.hex` and `generated/test_exp_e.hex` are 103-entry signed
16-bit preloads for `tb_exp__DOT__zs` and `tb_exp__DOT__es`, with a seven-field
offset manifest for the GPU vector-sequence compare. That vector sequence now
runs and passes: 103/103 cases match, zero mismatch, and
`semantic_equivalence_claimed=true`. The comparison reconstructs `eo` from
`pos_r`, `big_r`, and `interp` because `eo` is not a root field. `tb_norm` now
also passes a GPU DUT-output contract: `generated/test_norm_in.hex` is preloaded
into `tb_norm__DOT__u_vmem__DOT__mem[0..23]`, one explicit reset/start/clock
sequence runs, `n_done` is observed, and final
`tb_norm__DOT__u_vmem__DOT__mem[64..87]` matches
`generated/test_norm_out.hex` for 24/24 outputs. `tb_matvec` now passes the same
vmem-contract pattern: `generated/test_in.hex` is preloaded into
`tb_matvec__DOT__u_vmem__DOT__mem[0..23]`, one explicit reset/start/clock
sequence runs, `mv_done` is observed, and final
`tb_matvec__DOT__u_vmem__DOT__mem[64..87]` matches `generated/test_wq.hex` for
24/24 outputs. `tb_attn` now passes the larger vmem-contract pattern:
`generated/test_attn_q.hex`, `generated/test_attn_k.hex`, and
`generated/test_attn_v.hex` are preloaded into `vmem[0..23]`, `vmem[32..415]`,
and `vmem[448..831]`; `a_done` is observed; and final `vmem[864..887]` matches
`generated/test_attn_out.hex` for 24/24 outputs. `tb_core` now maps structured
stdout authority to root-state fields: the GPU multi-launch sequence matches
greedy tokens `1 12 1 25 1`, sampled tokens `18 15 19 16 8 15 4`, and cycle
summary `CYCLES_PER_TOKEN=1157`, `AVG_CYCLES=1322 over 12 tokens (last=1489)`.
It uses 14 launches and 47,656 logical steps, so it is correctness evidence
only. The current next artifact should close the remaining stdout/finish
observable export gap or measure whether batching the bench-specific scenarios
as states can be useful.
The first `tb_exp` replicated-state batching probe is now recorded, but it is
only same-scenario launch-amortization evidence. It copies the same 103-case
vector sequence across `nstates=1,32,256`, with per-state kernel time
`16.966656 ms`, `0.56204803125 ms`, and `0.084064 ms`; best is `nstates=256`
with `201.83022459078796x` per-state kernel improvement versus `nstates=1`.
It does not claim mixed-scenario batching, semantic equivalence, speedup, or
usefulness. The distinct-state gate now has a minimal runtime ABI:
`@state:local_offset:byte` patch tokens drive different per-state values. The
first distinct `tb_exp` probe runs 103 different `z` inputs across 103 GPU states
in one 2-step clock sequence, matches 103/103 reconstructed outputs, and records
nonresident `gpu_kernel_total_ms=3.639296`, `wall_time_ms=13.266`. The first
resident version now also passes: `--resident-steps` uploads `412` patch records
once as a device-resident schedule, matches 103/103 outputs, and now has a 7/7
repeat-median gate: `gpu_kernel_total_ms_median=0.887808`,
`wall_time_ms_median=0.93`. A matching CPU Verilator process-wall baseline
passes 7/7 samples with `median=28.96515399334021 ms`; the resident
repeat-median observed GPU wall ratio is `31.145326874559363x`. This is still a
narrow two-step timing result for `tb_exp`, so speedup/usefulness claims remain
disabled. The broader resident gate now has a passing `tb_core` full persistent
resident feedback result for the reviewed token/cycle contract. The resident
multi-step shape improves from `4367.203339 ms` / `4373.235 ms` to
`816.12083 ms` / `816.915 ms`; the full feedback path now has a 7/7
repeat-median of `767.118103 ms` kernel / `767.173 ms` wall, sets
`resident_multitoken_claimed=true` only for that bench-specific contract, and
records observed wall ratios of `5.700454786599632x` versus nonresident GPU and
`1.064838048262908x` versus resident multi-step. A new CPU `tb_core`
process-wall baseline passes 7/7 with median `22.265211009653285 ms`; full
feedback GPU wall is only `0.029022412167338116x` of CPU, about `34.5x` slower.
The slowdown breakdown records `47,642` logical GPU launches and `95,311` actual
timed launches for one scenario; the `27` feedback helper launches are only
`0.000283283146751162` of actual launches. Pair-cycle-loop is now tried on this
shape and passes the same token/cycle contract 7/7 with `69` actual timed
launches, `14` loop kernels, `23,814` looped low/high cycles, and `432.609 ms`
median wall (`1.7733634760256953x` GPU-wall improvement), but it is still
`19.429818105583568x` slower than CPU. The `nstates=1,8,32` replicated-state
follow-up now preserves pair-cycle-loop eligibility by replicating the state0
resident patch schedule across state strides: all three runs keep actual timed
launches at `69`, and `nstates=32` reaches `18.3382225 ms/state` kernel
time, a `23.557655274386597x` per-state improvement versus `nstates=1`. All
replicated state phase dumps now pass the same token/cycle contract (`8/8` for
`nstates=8`, `32/32` for `nstates=32`, zero mismatches). This is still
same-scenario replicated correctness, not mixed-scenario batching, speedup, or
usefulness. A distinct-state `tb_core` full-sequence phase-set probe now passes
two scenarios in one GPU batch: state0 greedy observes
`[1, 12, 1, 25, 1, 0]`, and state1 sampled seed `2` observes
`[18, 15, 19, 16, 8, 15, 4, 0]`, with 2/2 states passing and zero mismatches.
It uses `8` state-indexed phase-set launches, `7` combined feedback launches,
`76` phase-set records, `27,224` logical launches, and `54,463` actual launches
without loop collapse (`gpu_kernel_total_ms=471.468170`,
`wall_time_ms=471.533`). The pair-cycle-loop follow-up keeps the same 2/2 token
result and now passes a 7/7 repeat median: `286.213837 ms` kernel /
`286.254 ms` wall, `47.0` actual launches, `27,224.0` logical launches,
`8.0` loop kernels, `13,600.0` looped low/high cycles, and `8.0`
phase-boundary fallbacks. The CPU process-wall median is
`23.23766698827967 ms`, so the observed GPU wall ratio is
`0.08117848829459036x` and GPU wall remains `12.31853439264696x` slower. The
many-independent seed matrix now has CPU token oracles for all `16` target
states with zero validation mismatches; `greedy` and `sampled_seed2` keep
reviewed golden provenance, while `sampled_seed3` through `sampled_seed16` are
generated by the CPU Verilator oracle bench. The 16-state GPU batch now passes
7/7 repeat-median samples with 16/16 token streams matched and
`trim_final_low=true`: median GPU time is `393.967987 ms` kernel /
`393.999 ms` wall, with `35.0` actual launches over `30,618.0` logical
launches. Compared with CPU oracle wall `84.66219899128191 ms`, GPU remains
`4.653777065731213x` slower. Launch-structure analysis accounts for all `35`
actual launches (`9` phase-set, `8` combined-feedback, `9` pair-cycle-fusion,
and `9` pair-cycle-loop kernels), leaving `0` residual launches and `0.0`
residual launches per fallback. This is token sequence mixed batching plus
repeat-median launch-collapse evidence only, not cycle summary authority,
stdout/PASS/finish authority, speedup, or usefulness. This makes the unsupported
point more concrete: helper-kernel LLVM tweaks and oracle generation are
insufficient. A hold-start diagnostic reaches `26` actual launches by removing
the `9` pair-cycle-fusion launches, but all `16` token streams mismatch. The
padded-start diagnostic is the useful positive path: it preserves the one-cycle
start pulse, passes `7/7` repeats with `16/16` token streams matched, drops
actual launches to `26`, removes pair-cycle-fusion launches and loop fallbacks,
and records `366.163605 ms` kernel / `366.21 ms` wall. This is a
`1.0758826902596872x` wall improvement over the standard 35-launch path but still
`4.325543210113294x` slower than the CPU oracle wall, so speedup/usefulness
remain false. The 7-repeat CPU comparison claims only the lower-launch gate, and
`tb_core_padded_start_cpu_negative_gap_decision` reports
`mapping_structure_change_recommended`, so the next structural work is a
materially different runtime/mapping structure, not holding `start` high and
not first adding a new
phase-start-pulse-plus-loop C kernel. The generated
`tb_core_runtime_mapping_structure_candidate_plan` is
`ready_for_runtime_mapping_design` and ranks
`ordering_aware_phase_resident_token_loop` first; GitHub #69 tracks that
prototype. Its prototype contract now validates as planning evidence and targets
`phase_set=0`, `combined_feedback=0`, `pair_cycle_loop=0`, and one
`ordering_aware_token_loop` launch before any speedup/usefulness claim. Current
build metadata now reports `vl_tb_core_ordering_aware_phase_resident_token_loop_gpu`
as available, and the generated kernel body now consumes `current_phase`,
phase-control records, feedback copy/increment records, and terminal-mask
records around the pair-cycle loop. The latest ordering-aware run consumes the
#69 lowering plan through the schedule-owned token-loop path with
`runtime_supported=true`, passes the source CPU-token-oracle comparison for
`16/16` states, uses `9` actual ordering-aware launches over `30,618` logical
launches, and suppresses the separate helper launch classes:
`feedback_phase_sets=0`, `feedback_combined=0`, `pair_cycle_loop_fusion=0`, and
`resident_pair_cycle=0`. Runtime reporting records `entrypoint_available=true`,
`phase_control_records=672`,
`feedback_copy_records=5`, `feedback_increment_records=1`,
`pair_cycle_loop_records=1701`, `terminal_mask_records=16`,
`terminal_mask_device_records=16`, `terminal_mask_parse_errors=0`, and
`launch_probe_count=9`, `device_table_launches=9`, blocking at
`ordering_aware_token_loop_schedule_integrated_cpu_comparison_pending`. The
ordering-aware lowering plan artifact now records the ABI-probe env and
terminal mask at
`artifacts/gategpt_local_eval/gateGPT/obj_tb_core/tb_core_ordering_aware_token_loop_lowering_plan.json`.
The wrapper now consumes this shape by default, and
`--allow-ordering-aware-token-loop-probe-plan` remains only as a debug
compatibility path. The C runtime parses, validates, canonicalizes, and uploads
terminal masks as device-side `state:terminal_step` records. The generated kernel
uses a direct state-indexed terminal-mask fast path with an order-tolerant fallback
before gating active phases and final feedback. CPU comparison remains negative:
GPU wall is `363.628 ms` / GPU kernel is `363.59198 ms` versus CPU oracle wall `81.95496001280844 ms`, so the
ordering-aware path with normal eval select-mux transform is
`4.436924866331091x` slower than CPU. The guarded bitmap trial now uses
`mode=phase_state_partition_bitmap` with `active_bitmap_partition_count=13`,
keeps 16/16 source states matched, and records `353.39 ms` GPU wall /
`353.358521 ms` GPU kernel, so it is still `4.288906799987675x` slower than
CPU and not a speedup. `speedup_claimed=false`
and `usefulness_claimed=false`; at that stage the next task was replacing the synthetic
CFG-clone component chain under `isolate_entry_dispatch_cfg_clone_memory_reads_before_wiring`,
but cold partition skip safety now records `13` inspected continuations, `0`
skip-safe candidates, and `13` rejected continuations
(`successor_phi_depends_on_continuation_edge=11` and
`terminator_not_unconditional_branch=2`), so simple LLVM guard insertion is insufficient
until `outline_partition_region_before_phi_join_or_split_successor_phi_edges`
handles the PHI-edge cases and
`outline_multi_successor_partition_region_or_normalize_continuation_terminator`
handles the remaining terminator cases.
The pass-level shape breakdown is `select_only_phi_edge_region=8`,
`effectful_memory_phi_edge_region=3`, and `multi_successor_continuation=2`; this
was the earlier PHI-edge outline slice that led into the current compact CFG
clone path. It is not the active open pointer anymore.
The select-only outline preflight records `8` regions with `832` selects,
`1344` successor-PHI edges, `832` local live-out values, and `512`
external-or-constant incoming values; this is the sizing contract for the first
outline slice, not speedup, usefulness, or skip-safety evidence.
The pass now inserts `8` select-only PHI repair blocks, moving `832` selects and
retargeting `1344` successor-PHI edges; this is CFG repair evidence only, not
partition-aware skip authority.
Post-repair static safety classification now records `8` inspected repaired
select-only continuations, `8` candidates, and `0` rejected; this narrows the
next guarded-skip prototype but still grants no skip authority.
The generated
`tb_core_ordering_aware_cpu_negative_gap_decision` now records
`status=ordering_aware_cpu_negative_gap_measured`: helper launches are already
suppressed, launches fell by `17` versus padded-start (`0.6538461538461539`),
but wall improved only `1.0604264497337874x` versus padded-start. The requested `decompose_ordering_aware_kernel_body_cost_and_state_scale` follow-up is now represented by stage timing, the state-scale sweep, and opt-in device-side diagnostic region counters: `before_final_sync=360.61 ms` dominates the measured wall path, so more helper-launch removal is not the next lever. The standard CPU comparison remains bound to the 16-scenario oracle; the 32-state sweep row uses a separately generated 32-scenario CPU oracle. The 4/8/16/32-state ordering-aware sweep records
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
The phase/state/partition predicate table is authoritative through `RUN_VL_HYBRID_EVAL_PARTITION_PREDICATES` and the `eval_partition_predicates:` stdout contract with `active_mask_authority=true`; direct eval callee and call-site predicate-pointer markers are present through `vlgpu.direct_eval_predicate_pointer_abi` and `vlgpu.eval_predicate_pointer`. The no-skip predicate-read validation still passes and the CPU token oracle still matches 16/16 states. Post-capture compare validates reached CFG-clone liveout capture points: `outline_call_count=3434752`, `liveout_frame_store_count=82434048`, `compare_count=150480`, `mismatch_count=0`, `actual_store_slots_per_outline_call=24`, and `compare_slots_per_outline_call=0.043811023328612954`. The non-diagnostic isolation path builds and runs to same-CPU-oracle timing with CFG-clone counter/shadow diagnostic ABI disabled: GPU wall `404.986 ms` / kernel `404.90036 ms` versus CPU oracle `107.71662899060175 ms`, still `3.759735184762744x` slower. The Pass emits partition-local eval continuation guard static shape for `8` guarded regions with `1344` successor-PHI incoming values. Runtime-noop derivation is blocked by successor PHI live-out for all `832` inspected selects (`0` elision-safe, authority `no_runtime_noop_derivation_authority`). Successor-PHI continuation user classification is complete for `168` successor PHIs / direct users / direct load users / load-consumed PHIs, with `0` direct non-load users, `168` load-result direct users, `0` unsupported load-result users, and `1` candidate cluster under `classification_only_no_runtime_skip_or_select_elision_authority`. Existing pass evidence has also reached compact cluster outline frame-call ABI stub materialization: `1` outline callee, `63` outline call sites, `175` explicit live-ins, `48` explicit live-outs, `242` lowered live-in frame stores, `48` lowered live-out frame stores, and `0` unsupported live-in/live-out frame values, with `outline_frame_call_abi_stub_materialized_no_semantic_outline_authority`, so the analyzer now records CPU-oracle validation as blocked because runtime guard execution summary is missing and runtime skip/no-op authority is false. Guarded/liveout CPU-oracle validation still uses the diagnostic artifact and remains validation-only: GPU wall `19232.031 ms` / kernel `19231.960938 ms` versus the same CPU oracle, `178.5428227769548x` slower. The next contract is `clone_compact_cluster_body_into_outline_callee_and_rewire_control_flow`; speedup/usefulness remain forbidden.
The first
promotion step is now in place:
the rule is factored into `src/tools/gategpt_schedule_planner.py`, which now
validates the plan and generates the schedule-lowered `run_vl_hybrid` argv, and
`run_vl_hybrid.py --schedule-lowering-plan` consumes the generated lowering-plan
artifact as the runtime env source:
`artifacts/gategpt_local_eval/gateGPT/obj_tb_core/tb_core_many_independent_padded_start_lowering_plan.json`.
The generated `vl_batch_gpu.meta.json` also exposes
`schedule_lowering_capabilities.padded_start_pair_cycle_loop=available` with no
missing runtime entrypoints; this is build-artifact capability metadata, not
execution authority.
The
`tb_core_persistent_resident_multitoken_abi_gap` report now defines the next
gate as optimizing this persistent resident multi-token shape after the CPU
`tb_core` baseline proved the current single-scenario GPU path negative:
feedback copies `next_token -> token_in`, four
`rng_out -> rng_in` byte lanes, and device-side `pos_in` advancement between
token transactions. The LLVM pass emits `vl_apply_feedback_edges_gpu`,
`vl_apply_feedback_increments_gpu`, `vl_apply_feedback_sets_gpu`, and
`vl_apply_feedback_combined_gpu`. Runtime upload/launch orchestration is
smoke-tested for 5 byte-copy feedback edges, one `pos_in` increment, phase-set
`start/smode/inv_temp` controls, one combined edge+increment launch, zero
separate edge/increment launches, and two phase-set launches. Full feedback uses
13 combined edge+increment launches and 14 phase-set launches; phase-set writes
remain separate to preserve per-phase ordering. Remaining claims disabled:
stdout/PASS/finish authority, speedup, usefulness, and arbitrary RTL support.

Current FC-037 handoff: `hello` sidecar timing and launch-count collapse are
measured, but the active blocker is non-`hello` `dhry` finish/stdout/timing
evidence. The old same-cycle and trace mismatch thread was resolved as flat
`lmem` initialization, not divider lowering or a simple observation offset.
`$readmemh` writes outside the `0x80000000` 64 KiB program window polluted the
unmapped default byte, and the missing `@10000000` control window made GPU
reads return `0x0a0a0a0a...` instead of the Dhrystone iteration value `1000`.
The fixed flat-memory layout separates unmapped writes from default reads and
materializes the 16-byte control window. The current machine-checkable
same-window evidence is
`reports/rtlmeter_veer_el2_dhry_lmem_control_trace_equivalence_875_50000.json`,
which summarizes
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_50000.json` as
`status=passed`: GPU steps `875..49999`, 49125 aligned rows, 62 compared fields,
zero mismatched field observations, and `speedup_claimed=false` /
`usefulness_claimed=false`. This supersedes the earlier 50k raw PC/minstret gap
for the traced fields, but it is still bounded trace-equivalence evidence only:
full `dhry` finish, stdout correctness, fair timing, and GPU usefulness are not
proven. The first stdout-safe longer-progress gate remains bounded-only:
`reports/rtlmeter_veer_el2_dhry_lmem_control_stdout_safe_progress_100000_loopfix.json`
reaches `mcycle=99999`, `minstret=95864`, and no finish marker with
`step_trace_disabled=true` and `final_observable_stdout_requested=true`, while
keeping timing/speed/usefulness claims disabled. Non-`hello` final-observable
stdout remains reviewed-blocked. Bounded phase-aware loop diagnostics now launch
`vl_patch_eval_pair_cycle_loop_batch_gpu` while preserving the VeeR
`vl_ico_batch_gpu` plus `vl_eval_loop_batch_gpu` phase sequence. The 10/100/1000
cycle loop outputs match resident fallback byte-for-byte; the 1000-cycle case
reduces actual timed launches from `6009` to `10` and GPU kernel total from
`272.929400ms` to `238.399490ms`. Wrapper wall is not yet a robust win, and
full `dhry` finish/stdout remains unproven. The 100000-cycle phase-aware loop
summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_progress.json`
passes bounded progress with one loop kernel, `10` actual timed launches,
`mcycle=99999`, `minstret=95864`, `22404.386719ms` GPU kernel time, and no
finish marker. The generated bounded projection report
`reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_negative_projection.json`
projects that measured window to CPU RTLMeter cycles `5984259` as about
`1340.75s` GPU-kernel time versus `37.240654s` CPU serial wall, about `36.00x`
slower by GPU-kernel time alone, and records `negative_usefulness_decision=true`.

Task order:
1. Treat the current bounded non-`hello` `dhry` GPU path as negative for
   usefulness by generated bounded projection.
2. Do not create a new GitHub issue yet: FC-037 / #2 still owns this timing and
   usefulness measurement lane.
3. Use the phase-aware loop-collapse evidence as bounded progress plus a
   negative usefulness decision for the current path; full non-`hello`
   finish/stdout remains future correctness work.
4. Mixed GPU state preload now reaches 100000 bounded cycles:
   `reports/rtlmeter_veer_el2_mixed_state_dhry_cmark_cmark_iccm_100000_projection.json`
   uses `state0=dhry`, `state1=cmark`, and `state2=cmark_iccm` as distinct
   syms init images with the same GPU kernels, then pairs the run with
   `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json`. It records
   `mixed_state_negative_projection_decision=true`: projection to the CPU mixed
   baseline max cycle count is about `1369.99s` GPU-kernel time versus
   `37.079953s` CPU mixed parallel wall, about `36.95x` slower. This is not a
   full-program finish/stdout proof and not a positive speedup/usefulness
   claim.
   Next gate: stop this current GPU path unless a materially different
   implementation is defined first. That definition must name the launch-count
   reduction mechanism, the per-state finish/stdout observability contract, and
   the CPU mixed parallel baseline comparison. Keep FC-037 / GitHub #2 as owner;
   do not add a new issue for the same RTLMeter timing/usefulness lane.
5. The old `fetch_stall` / `dec_i0_decode_d` split was narrowed through
   `misc2ff`, `exu_div_wren`, and divider traces to an apparent
   `dw_shortq_raw` split at `gpu_step=890` / CPU `post_reset_posedges=893`.
5. The actual root cause was flat `lmem` initialization: `$readmemh`
   out-of-window writes polluted the unmapped default byte, and the missing
   `@10000000` control window made the GPU read `0x0a0a0a0a...` instead of the
   Dhrystone iteration value `1000`. The fix separates unmapped writes from
   default reads and materializes a 16-byte `0x10000000` control window.
5. Current focused evidence starts with
   `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_1000.json`:
   `status=match`, 125 aligned rows, 62 compared fields, CPU rows mapped as
   `post_reset_posedges=gpu_step+3`, and the previous `gpu_step=890` divider
   split resolved. The follow-up
   `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_2000.json`:
   `status=match`, 1125 aligned rows, 62 compared fields, zero mismatched field
   observations, and CPU rows still mapped as `post_reset_posedges=gpu_step+3`.
   The latest extension is
   `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_5000.json`:
   `status=match`, 4125 aligned rows, 62 compared fields, zero mismatches, and
   coverage through GPU step `4999`. The newest long-window extension is
   `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_50000.json`:
   `status=match`, 49125 aligned rows, 62 compared fields, zero mismatches, and
   coverage through GPU step `49999`.
6. The old loop-fusion eligibility question is no longer the next gate. The
   current mixed-state GPU path has a 100000-cycle negative projection against
   CPU mixed parallel, so the next technical step is a stop/different-path
   decision: either stop this implementation as a performance path, or define a
   materially different GPU implementation with explicit launch-count reduction,
   per-state finish/stdout observability, and CPU mixed parallel comparison
   before writing more code. The definition must cover resident execution over
   many design-CPU cycles per device operation, per-state finish/stdout/cycle
   reporting, superstep entry/exit and unsupported-side-effect checks, a named
   GEM-like/data-parallel lowering candidate if LLVM pass work is proposed, and
   `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json` or an equivalent
   regenerated mixed-program CPU-parallel report as the comparison floor. Keep
   speedup/usefulness wording disabled. The mixed-state GPU/CPU summary now
   exposes this handoff as `recommended_action` plus
   `materially_different_definition_gate`, and the sidecar report records the
   current per-state observability gap instead of letting state-0 stdout stand
   in for mixed non-state0 programs.

## GitHub Roadmap Task Overlay

These GitHub-only `T*` issues organize the current open work around the FC
issues. They are coordination tasks, not a new source of truth for canonical
project state.

| GitHub Issue | Role | Dependency / Scope |
|---|---|---|
| https://github.com/takatodo/gpu-rtl-sim/issues/12 | T0: document current algorithm readiness and claim boundary | First docs task; gates T1/T2 and later docs wording. |
| https://github.com/takatodo/gpu-rtl-sim/issues/13 | T1: shorten operator-facing quickstart | Gated on T0. |
| https://github.com/takatodo/gpu-rtl-sim/issues/14 | T2: harden public-pack reproducibility boundaries | Gated on T0/T1. |
| https://github.com/takatodo/gpu-rtl-sim/issues/15 | T3: advance Verilator native option handoff | Gated on T0/T1/T2; keep sidecar-owned metadata out of parser-owned fields. |
| https://github.com/takatodo/gpu-rtl-sim/issues/16 | T4: repeat-median evidence for policy-selected workloads | Scoped sidecar measurement evidence only; not production throughput. |
| https://github.com/takatodo/gpu-rtl-sim/issues/17 | T5: expand filelist-derived target boundary | Gated on T0/T3; not arbitrary filelist inference. |
| https://github.com/takatodo/gpu-rtl-sim/issues/18 | T6: prepare RTLMeter sidecar handoff | Gated on T0/T1/T3; do not claim acceleration from compile-only evidence. |
| https://github.com/takatodo/gpu-rtl-sim/issues/41 | T11: run RTLMeter first-seed stdout/cycles compare | Current-run stdout/cycles evidence exists for `Example:kind:hello`; compare only normalized stdout and RTLMeter cycle count. |
| https://github.com/takatodo/gpu-rtl-sim/issues/44 | T14: implement RTLMeter sidecar Verilate execution for stdout/cycles | Closed; the blocker narrowed past sidecar Verilate execution to the #49 Vsim proxy/marker boundary. |
| https://github.com/takatodo/gpu-rtl-sim/issues/49 | T18: implement RTLMeter Vsim sidecar proxy marker and runtime handoff | Marker/proxy implementation is committed and pushed on `simple-core-surface-cleanup`; #44/#45 closed on that evidence; closure is gated on review sufficiency of the marker-backed opt-in pass. |
| https://github.com/takatodo/gpu-rtl-sim/issues/50 | T19: clear stale RTLMeter stdout/cycles observables before sidecar runner execution | Safety layer after #44 base; prevents stale `_execute/stdout.log` and `_rtlmeter_cycles.txt` from becoming current evidence. |
| https://github.com/takatodo/gpu-rtl-sim/issues/51 | T20: record marker-backed first-seed opt-in pass evidence | Frozen per the owner native-path goal. End-to-end trial done (forgeability shown); evidence recording not pursued. Closes with #49 (interim-complete or superseded). |
| https://github.com/takatodo/gpu-rtl-sim/issues/52 | T21: harden RTLMeter sidecar proxy-target review | Descoped: allow-list/manifest hardening frozen. Remaining scope is naming separation only (demote `execution_authority`/`sidecar_execution_invoked` to handoff-observed wording). |
| https://github.com/takatodo/gpu-rtl-sim/issues/53 | T22: decide a tracked evidence sink for RTLMeter compare | Frozen per the owner native-path goal; native-path correctness evidence is owned by the #46 milestone-5 gate. Closes as superseded when the native path runs RTLMeter. |

Current GitHub lane map:

- Parent/goal framing: FC-039 / #1. Treat as umbrella coordination, not a
  standalone implementation proof.
- Docs/readiness: #12 -> #13 -> #14 -> FC-044 / #11 remains a cleanup lane,
  not the current implementation blocker.
- Verilator/sidecar: FC-042 / #9 is completed; FC-053 / #46 is the active
  native-path umbrella, and FC-059 / #59 is the related native-path side task.
  The global current priority is FC-069 / #69 for gateGPT `tb_core`
  ordering-aware token-loop schedule integration. FC-037 / #2 remains the
  VeeR-EL2 timing/usefulness lane, but is not the active implementation blocker.
- Algorithm policy: #16 -> FC-045 / #19, using repeat-median evidence to
  recommend scoped shapes without claiming automatic optimal allocation.
- LLVM optimization pass lane: FC-046 / #20 umbrella, then FC-047 / #21 ->
  FC-048 / #22 -> FC-049 / #24 -> FC-050 / #25 -> FC-051 / #23 ->
  FC-052 / #26. Keep correctness patches separate from optimization passes.
- Owner goal (2026-06-12, recorded on FC-039 / #1): the maximal goal is that
  `verilator` with the sidecar options alone builds an `obj_dir/Vsim` that
  executes on GPU, with no wrapper, proxy env, review manifest, repo-specific
  JSON selection, or intermediate files in the user path. FC-053 / #46 is the
  native-path umbrella (milestones recorded there); first target is
  `pulp_ita_mha 64x1`-class, recognized-closure-only, fail-closed.
- RTLMeter proxy interim lane (#49 / #51 / #52 / #53) is frozen per that goal.
  The #51 end-to-end trial showed the proxy review gate is self-attested and a
  CPU-delegate proxy obtains `execution_authority=true`; proxy-lane outputs are
  therefore not GPU-claim evidence. Only the #52 naming separation (demote
  `execution_authority` / `sidecar_execution_invoked` to handoff-observed
  wording) remains active; the rest closes as superseded once the native path
  runs RTLMeter directly. FC-037 / #2 timing and FC-040 / #4 second seed are
  re-evaluated after the #46 milestone-5 correctness gate.
- Measurement evidence: #16, scoped only and separate from production timing
  claims.

## Current PR Queue

Agent coordination snapshot. This section is not source of truth for project
state; prefer live GitHub issues plus `config/selection.json`, `docs/status.md`,
`docs/roadmap.md`, and `README.md` for the current external-reader position.

Treat local staged and unstaged work as pre-PR material until it is split,
pushed, and linked to the issues below.

0. PR-0: RTLMeter VeeR-EL2 timing/usefulness measurement.
   - Primary issues: FC-037 / #2, using FC-064 / #63 as the passing correctness
     prerequisite.
   - Scope: measure serial CPU, CPU-parallel baseline, sidecar wall time, and
     GPU/kernel timing as separate fields for the VeeR-EL2 direct sidecar path.
   - Current result: `reports/rtlmeter_veer_el2_timing_nstates16.json` records
     repeated timing methodology, preserves stdout/cycles equivalence, consumes
     `reports/rtlmeter_cpu_parallel_hello16_baseline.json`, shows improved
     per-state GPU throughput versus eight-state, and still states
     `sidecar_slower_than_serial_cpu` honestly. Remaining gap: `run_vl_hybrid`
     launch, device-trace, and resident-patch overhead reduction.
   - Advantage aggregation: `src/tools/rtlmeter_hybrid_advantage.py` writes
     `reports/rtlmeter_hybrid_advantage_summary.json` from the current
     CPU-parallel, GPU timing, launch-feasibility, and bounded-progress reports.
     Current counts are `cpu_parallel_favorable=1`,
     `gpu_sidecar_unfavorable=4`, `gpu_sidecar_favorable=0`,
     `launch_feasibility_blocked=1`, and `gpu_bounded_progress=1`; the hybrid
     action is `prefer_cpu_parallel_control_with_gpu_bounded_batch_probes`.
   - Non-VeeR candidate aggregation:
     `src/tools/rtlmeter_non_veer_usefulness_candidates.py` writes
     `reports/rtlmeter_non_veer_usefulness_candidates.json`. Current NVDLA
     evidence has `measured_shape_count=10`, `gpu_favorable_shape_count=10`,
     and best wall ratio `11764.742765273311x` at `1024x64` for
     `nvdla_cmac_a2cacc`; Vortex is a fail-closed first-gate candidate with
     `mini` `hello`, `sgemm`, and `saxpy` and now has a measured Vortex `mini:hello` CPU-vs-hybrid timing gate. The
     non-VeeR lane now has a companion split index:
     `src/tools/rtlmeter_non_veer_hybrid_measurement_summary.py` writes
     `reports/rtlmeter_non_veer_hybrid_measurement_summary.json` with
     `measured_design_count=1`, `measured_shape_count=10`,
     `gpu_favorable_shape_count=10`, `unmeasured_first_gate_candidate_count=1`,
     NVDLA `favorable_ratio=1.0`, and Vortex
     `cpu_vs_hybrid_timing_present=false`. Its recommendation is to extend
     NVDLA hot-SS measurement before claiming broader RTLMeter GPU usefulness,
     while keeping Vortex gated on first CPU-vs-hybrid timing.
     `src/tools/rtlmeter_non_veer_hybrid_next_queue.py` writes
     `reports/rtlmeter_non_veer_hybrid_next_queue.json`; the current top
     priority is `nvdla_hot_ss_measurement_extension`, targeting the best
     observed bucket `state_batch_and_repeated_step` and preferred measured
     shape `1024x64` on `nvdla_cmac_a2cacc`. The second queue item is
     `vortex_mini_hello_first_cpu_vs_hybrid_gate`, whose first blocker has
     moved past memory-helper integration, real Vortex kernel artifact
     generation, and PTX/meta prelaunch rejection to wiring a root-storage-backed
     real kernel callback.
     `src/tools/rtlmeter_nvdla_hot_ss_measurement_plan.py` writes
     `reports/rtlmeter_nvdla_hot_ss_measurement_plan.json` from that queue. The
     current plan is non-executing `planned_not_run` for
     `NVDLA.nvdla_cmac_a2cacc`: confirm `1024x64`, check `512x64`, probe
     `2048x64`, and separate state-batch from repeated-step effect with
     `1024x1`. Keep `NVDLA.nvdla_cmac_core_mac` deferred unless the compile-cost
     issue is explicitly reopened.
     `src/tools/rtlmeter_nvdla_hot_ss_plan_dry_run.py` writes
     `reports/rtlmeter_nvdla_hot_ss_plan_dry_run.json`; the current report has
     `all_dry_runs_passed=true` for all four planned shapes. The first plan item
     now has `reports/nvdla_cmac_a2cacc_repeat_median_1024x64.json` with
     `repeat_count=3`, `coverage_output_equivalence_all_passed=true`,
     coverage-output mismatch count `0` in all samples, median CPU
     `2142.1 ms`, median hybrid wall `1.755 ms`, and median CPU/hybrid wall
     speedup `1430.950752393981x`. This required updating
     `hybrid_template_repeat_median.py` to read compare schema v2
     `coverage_output_policy`; raw final-state `match=false` is expected and is
     not the accepted policy.
     `reports/nvdla_cmac_a2cacc_repeat_median_512x64.json` now covers the
     lower-neighbor plan item with `coverage_output_equivalence_all_passed=true`,
     median CPU `1056.75 ms`, median hybrid wall `1.602 ms`, and median
     CPU/hybrid wall speedup `663.2209737827715x`.
     `reports/nvdla_cmac_a2cacc_repeat_median_2048x64.json` now covers the
     larger-state plan item with `coverage_output_equivalence_all_passed=true`,
     median CPU `4244.47 ms`, median hybrid wall `1.662 ms`, and median
     CPU/hybrid wall speedup `2553.8327316486166x`.
     `reports/nvdla_cmac_a2cacc_repeat_median_1024x1.json` now covers the
     state-batch-only plan item with `coverage_output_equivalence_all_passed=true`,
     median CPU `2090.2 ms`, median hybrid wall `2.628 ms`, and median
     CPU/hybrid wall speedup `791.3432267884323x`.
     `src/tools/rtlmeter_nvdla_hot_ss_repeat_summary.py` writes
     `reports/rtlmeter_nvdla_hot_ss_repeat_summary.json`; current counts are
     `planned_measurement_count=4`, `measured_count=4`,
     `coverage_passed_count=4`, and `gpu_favorable_count=4`. The best measured
     shape in this plan is `2048x64`; state batching alone is favorable and
     repeated-step batching improves the best observed wall ratio further.
     `src/tools/rtlmeter_gpu_favorable_conditions_audit.py` writes
     `reports/rtlmeter_gpu_favorable_conditions_audit.json`; it records
     `status=goal_satisfied_by_nvdla_hot_ss` and
     `completion_decision.achieved=true` for the current "find GPU-favorable
     conditions beyond VeeR portability" goal. Vortex remains the
     architecture-diverse follow-up once its first CPU-vs-hybrid timing gate
     exists.
     Current hybrid split table:

     | Target / slice | Measurement state | Decision | Evidence | Next action |
     |---|---|---|---|---|
     | `NVDLA.nvdla_cmac_a2cacc` hot SS | Measured; repeat-median plan complete | GPU-favorable for measured hot-SS shapes | Four repeat-median rows pass coverage-output equivalence and are GPU-favorable; best repeat-median row is `2048x64`, CPU `4244.47 ms`, hybrid wall `1.662 ms`, wall speedup `2553.8327316486166x`; broad-shape index still has prior `1024x64` wall best `11764.742765273311x` | Extend reviewed hot-SS measurements only |
     | `NVDLA.nvdla_cmac_core_mac` full/core slice | Deferred | Not a current GPU path | `32x1` refresh spent more than ten minutes in `ptxas` and about 36 GiB RSS before being stopped | Reopen only with compile-cost mitigation |
     | `Vortex:mini:hello` | CPU reference/preflights ready; hybrid measured | Measured negative; no speedup claim | CPU `0.22s` / `40897` clocks / `TEST PASSED`; canonical real-CUDA materialized runtime reaches `after_cuCtxSynchronize`, exports `memory_post_condition`, and timing records hybrid median `0.4504947270033881s`, `hybrid_vs_cpu_ratio=2.047703304560855`, `cpu_vs_hybrid_speedup=0.48835199795434103` | Continue EH1/EH2 unblock and timing |
     | `VeeR-EL2:default:hello` | Correctness/timing measured | Negative portability baseline, not speedup | Best sidecar row `0.641226s`, `sidecar_vs_cpu_parallel_ratio=3.460382`; serial CPU remains faster | Preserve as baseline |
     | `VeeR-EH1/EH2:default:hello` | Not measured | Blocked before timing | EH1 eval-only launch faults at first `vl_eval_batch_gpu`; 2MiB padded storage, region-counter global init, and stack-limit overrides do not clear it; the required host-I/O stub pass now erases `47` EH1 host-I/O call sites and leaves zero matching calls in the probe IR; regenerated host-I/O-stubbed single-entry eval CUBIN builds (`6735488` bytes, `ptxas -O0` `15.29s`) but the bridge still exits with `CUDA error 700` at first eval launch; runtime trace records `NUM_REGS=255`, `LOCAL_SIZE_BYTES=1776`, and padded 2MiB init-state still faults; EH2 prelaunch is cleared by syms-state image, full PTX still times out at module load, and the entry-pruned eval+patch CUBIN now loads but fails at `before_first_step_sync` with `CUDA error 700` after the step-0 patch+eval launches; no-patch eval-only reproduces the same EH2 fault, and padded2m, stack64k, plus zero-init probes do not clear it; static EH2 PTX audit counts `1456` C++/Verilator runtime-residue hits and `134` suspicious function definitions; expanded EH2 host-cleanup removes scheduler/container call sites, but direct no-patch eval-only still fails with CUDA 700; return-before-eval and prologue-only return-before-eval-call probes pass; staged and inline EH2 probes narrow the fault to eval-phase-context stores into `__VnbaTriggered` at `root+472408`; adjacent, root-base, and entry-context stores pass, while padded2m and maxr128 do not clear the fault | Isolate remaining EH1 scheduler/container/ABI device fault; fix EH2 eval-phase `__VnbaTriggered` store-context CUDA 700 |

     Vortex readiness writes `reports/rtlmeter_vortex_first_gate_readiness.json`;
     it selects
     `Vortex:mini:hello` first because `dcrs.bin`, `init.bin`, and `post.bin`
     exist. `config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json`
     now records a fail-closed `runtime_launchable=false` authority for stdout
     `TEST PASSED` plus memory post-condition, but does not grant reviewed
     execution authority. The fail-closed
     `config/slice_launch_templates/vortex_mini_hello.json` launch template now
     exists with `runtime_launchable=false`, `source_closure.status=incomplete`,
     and non-dry-run source-closure refusal until the DPI/runtime bridge is
     complete. `reports/rtlmeter_vortex_source_closure.json` now validates that
     the descriptor-owned source closure exists locally: `126` Verilog sources,
     `8` include files, and `1` CPP DPI source. This still grants no runtime
     launch authority. The gate still blocks on CPU-vs-hybrid timing evidence
     and GPU bridge implementation. The DPI review
     `reports/rtlmeter_vortex_dpi_memory_bridge_review.json` captures the
     boundary: 64-byte block memory access with byte enables, MMIO stdout at
     `IO_COUT_ADDR=0x40`, `mem_check(post.bin)`, and the DCR schedule that must
     be applied while reset is asserted.
     `src/hybrid/vortex_memory_model_device.h` now provides a host-compilable
     helper for 64-byte block initialization, byte-enable writes, IO_COUT
     capture, and post compare semantics.
     `reports/rtlmeter_vortex_device_buffer_materialize.json` now materializes
     the runtime upload inputs into
     `artifacts/rtlmeter_vortex_mini_hello_device_buffers`: `37224`
     host-to-device bytes and `88` initial device-to-host bytes across `7`
     buffers. `reports/rtlmeter_vortex_dcr_schedule.json` now materializes the
     ordered `9` DCR writes into a `72` byte little-endian runtime table and
     records the `tb.sv` reset/valid timing protocol. This is schedule
     materialization only, not lowered Vortex runtime execution.
     `src/hybrid/vortex_runtime_upload.h` now provides a
     fake-driver-tested upload helper for `cuMemAlloc`, `cuMemcpyHtoD`,
     `cuMemsetD8`, cleanup, and the same `37224` H2D / `88` D2H byte
     accounting. `src/hybrid/vortex_observable_export.h` now provides a
     fake-driver-tested export helper for `cuMemcpyDtoH` of
     `post_compare_result`, memory post-condition PASS/FAIL, and optional raw
     stdout bytes, `TEST PASSED` detection, and host-side authority-source
     selection. `src/hybrid/vortex_runtime_sequence.h` now provides a
     fake-driver-tested host/runtime sequence helper for buffer upload, ordered
     DCR application while reset is asserted, a kernel-launch callback,
     observable export, and buffer release.
     `reports/rtlmeter_vortex_runtime_invocation_plan.json` now validates that
     the fail-closed launch template names `vortex_run_runtime_sequence`, the
     expected upload/DCR/launch/export/release order, and the runtime-sequence
     header. This is a template plan only, not lowered Vortex runtime execution.
     `src/hybrid/vortex_lowered_tb_runtime_sequence.h` now provides a
     fake-driver-tested lowered-TB-side call boundary, and
     `reports/rtlmeter_vortex_lowered_tb_invocation_smoke.json` records it as
     ready but not integrated.
     Remaining blockers are
     generated lowered-TB integration calling
     `vortex_lowered_tb_invoke_runtime_sequence`, reporting that authority, and
     final GPU observable.
     `reports/rtlmeter_vortex_binary_input_summary.json` parses the
     concrete `hello` inputs: `init.bin` has `9` segments and `36864` payload
     bytes over `0x10000..0x80008000`, `post.bin` has `1` segment and `48`
     payload bytes, and `dcrs.bin` has `9` DCR writes.
     `reports/rtlmeter_vortex_gpu_memory_model_plan.json` converts that to an
     ABI plan with `7` device buffers, `576` init 64-byte blocks, and `37224`
     minimum static input bytes.
     `reports/rtlmeter_vortex_memory_model_reference.json` now validates the
     Python reference semantics: loaded initial memory mismatches `post.bin` on
     all `48` checked bytes, byte-enabled post replay matches, and IO_COUT
     capture does not mutate RAM. The remaining Vortex blocker is now real
     artifact execution latency: `build_vl_gpu.py --emit-ptx-module` generates
     PTX/meta, syms-state-image metadata clears prelaunch rejection, and the
     materialized real-CUDA path is wired to the root-storage callback, but the
     smoke times out before proxy handoff. Reporting exported authority, final GPU observable authority,
     and launch-template/timing evidence must follow that callback boundary, not DPI-format
     ambiguity. Do not move to Vortex `mini:saxpy` or
     `mini:sgemm` until `mini:hello` has a CPU-vs-hybrid gate. The
     `hybrid_template_repeat_median.py` repeat workflow is documented in
     README; a 2026-06-17 `NVDLA.nvdla_cmac_core_mac` `32x1` refresh reached
     CPU reference capture but full-core GPU artifact generation remained in
     `ptxas` for more than ten minutes and reached about 36 GiB RSS before
     being stopped, so keep NVDLA focused on smaller hot SS boundaries.
   - Latest overhead trial: true fused pair-cycle resident mode preserves
     low/high eval semantics and passes
     `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json` with
     `pair_cycle_fusion_available_counts={"true": 21}`,
     `pair_cycle_fusion_launched_median=727.0`, fallback median `0.0`, and
     `sidecar_wall_s_median=0.641226`. This is the current best VeeR 16-state
     sidecar result, but serial CPU remains about `16.030650x` faster.
   - Reporting correction: the runtime now distinguishes logical steps from
     actual timed GPU launches. The smoke report
     `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_actual_launch_smoke.json`
     records `1457` logical steps, `733` actual timed launches, and
     `0.373625ms` per actual launch for the fused pair-cycle path.
   - Latest scale trial: 32-state fused pair-cycle now passes after raising the
     runtime patch-script limit from 64 to 256. The full report
     `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json` records
     21/21 correctness samples, `sidecar_wall_s_median=0.950341`,
     `gpu_kernel_ms_total_median=357.866486`,
     `gpu_kernel_timed_launch_count_median=733.0`,
     `resident_patch_records_median=139872.0`, and
     `sidecar_vs_cpu_parallel_ratio=4.468648`. Per-state throughput improves
     versus 16-state, but total wall and serial CPU gap worsen.

1. PR-1: Native obj_dir executable sidecar shim smoke.
   - Primary issues: FC-059 / #59 under FC-053 / #46 and FC-057 / #57.
   - Priority note: related native-path side track, not the active FC-037 timing
     task.
   - Scope: make the final make-built `obj_dir/V<top>` link and enter a minimal
     in-process sidecar shim directly for the recognized closure. Do not route
     runtime execution through `run_hybrid_template.py`.
   - Completion condition: generated shim evidence records direct executable
     shim entry and `template_flow_invoked=false`; unrecognized filelist/top
     remains fail-closed; no GPU kernel, coverage, timing, arbitrary filelist,
     or CPU-as-GPU claim is added.

1. Later technical split: full direct `obj_dir/V<top>` sidecar runtime.
   - Primary issues: FC-057 / #57 after FC-059 / #59.
   - Scope: load the expected native-path GPU artifact, launch GPU kernels, and
     reach accepted coverage-output equivalence from the generated executable
     path. This is not part of the FC-059 shim-entry smoke unless separately
     implemented and verified.
   - Also include the PR-0 source-of-truth and contract expectation updates:
     `config/selection.json`, `config/selection_extensions.json`,
     `records/scaling_gates/config_minimal_surface_completion_audit.json`,
     `tests/contract/test_resident_runtime_contract.py`, and
     `tests/contract/test_tracked_tool_dependency_boundary.py`.
   - The self-contained PR-0 staged set is therefore 16 files, not 11 files.
     The canonical pointer should advance only to
     `define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_boundary_gate`
     with the current record count taken from `config/selection.json`.
   - Exclude `*verilator_process_launcher_bridge*`, `*observable_ordering*`,
     RTLMeter runner work, Makefile/build-path work, and source-of-truth pointer
     updates that already advance to the observable-ordering helper.
   - Keep the process-to-launcher contract test focused and under the staged
     contract-test growth limit; put bridge/gate-chain detail tests in later
     small files if they are still needed.
   - Completion condition: the process-to-launcher fixture materializes exact
     structured `run_hybrid_template.py` argv without starting the launcher, and
     the PR states that argv materialization is not execution authority.

2. Later technical split: Verilator process-to-launcher observable ordering helper.
   - Primary issues: #15 and FC-042 / #9.
   - Prerequisite: PR-0 must be merged or included in the same review stack.
   - Scope: review the implemented non-executing observable-ordering helper and
     its focused contract test.
   - Include only the matching source, tests, records, and source-of-truth
     pointer/docs updates needed for the current priority.
   - Do not include RTLMeter runner work, stdout/cycles work, or broad wrapper
     packaging changes.
   - Completion condition: contract tests pass and the PR description states
     that launcher-start-allowed metadata is not launcher execution, sidecar
     stage execution, timing, arbitrary filelist support, or production
     throughput.

3. Later docs split: Operator/docs readiness cleanup.
   - Primary issues: #12, #13, #14, and FC-044 / #11.
   - Scope: make public docs and reproduction wording match the supported
     preview surface after PR-1.
   - Keep JSON as debug/review inspection wording, not runtime ABI wording.
   - Completion condition: an external reader can distinguish supported
     template/benchmark flows, preview `--sim-accel` plumbing, and unsupported
     broad `verilator --use-gpu` claims.

4. PR-3: RTLMeter fail-closed handoff preparation.
   - Primary issues: #18, FC-034 / #8, and FC-041 / #5.
   - Scope: keep RTLMeter wrapper/context handoff metadata honest and
     fail-closed until a reviewed stdout/cycles sidecar execution source
     closure exists.
   - Do not close FC-037 / #2 or FC-040 / #4 from this PR.
   - Completion condition: RTLMeter GPU intent reaches the wrapper/context
     boundary without claiming acceleration or CPU-as-GPU fallback.

5. PR-4: Measurement evidence hardening.
   - Primary issue: #16.
   - Scope: repeat-median evidence for already policy-selected workloads only.
   - Completion condition: timing fields remain scoped evidence and do not
     become production throughput, automatic allocation, or arbitrary RTL
     claims.

6. PR-5: Filelist-derived boundary expansion.
   - Primary issues: #17 and FC-042 / #9.
   - Scope: expand from one known target/filelist/top only after PR-1 proves the
     first reviewed bridge path.
   - Completion condition: unknown or unsupported filelists fail closed, and no
     arbitrary dependency inference is claimed.

## Current Issue Correctness Snapshot

- FC-035, FC-036, and FC-038 are the correct clean-sim hardening chain. Treat
  them as prerequisite quality work, not as Verilator native-option completion
  or GPU speed evidence.
- FC-039 is complete as public goal-framing cleanup. It keeps current support,
  preview UX, long-term frontend-neutral goals, and non-claims visually
  separated while preserving the `config/selection.json` current pointer.
- FC-041 is complete as RTLMeter wrapper packaging. It materializes a generated
  PATH-selected `verilator` wrapper, delegates no-GPU argv to the real Verilator,
  fails closed for GPU intent, and does not claim RTLMeter acceleration.
- FC-034 remains historical first RTLMeter executing correctness work for the
  proxy/marker lane, but that lane is now frozen by the native-path goal.
  FC-064 is the passing VeeR-EL2 direct sidecar correctness gate. FC-037 timing
  is now actionable, while FC-040 second-seed broadening remains gated on
  FC-037 timing evidence.
- FC-042 / #9 is closed/completed after #35. It proved one scoped
  PATH-selected `verilator --use-gpu` wrapper path and must not be used to
  claim arbitrary RTL support, dependency inference, automatic allocation, or
  timing/speedup.
- FC-043 is architecture cleanup for the frontend-neutral contract. It may add a
  CIRCT placeholder diagnostic, but it must not claim CIRCT execution.
- FC-044 is an external-user readiness audit. It may remove or demote misleading
  surface area, but it must not introduce a new source of truth.
- FC-046 through FC-052 are the LLVM/NVPTX optimization-pass lane. Do not start
  with trigger factoring, resident step kernels, or SoA; metadata, state-access
  canonicalization, and conservative inline policy are the safer first split.
- The active `Vortex:mini:hello` plus VeeR EH1/EH2/EL2 hybrid-measurement
  objective is not complete. Use
  `reports/rtlmeter_vortex_veer_hybrid_measurement_matrix.json` as the generated
  review table: EL2 is measured, Vortex is blocked before first timing, and
  EH1/EH2 are descriptor/testbench-ready for design-specific porting and now
  have fail-closed authority registries, fail-closed state-layout preflight
  reports, fail-closed preload state-image materializer reports, and fail-closed
  sidecar bridge preflight reports. EH1/EH2 CPU reference observables now pass
  (`1044` RTLMeter cycles / `0.03s` for EH1, `2325` RTLMeter cycles / `0.06s`
  for EH2), and their generated CPU-reference `Vsim___024root.h` headers are
  now marker/offset-probed so `root_layout_probe` is no longer missing. After
  applying the mailbox public-flat overlay and rebuilding the EH1/EH2
  CPU-reference workRoots, both root-offset reviews use
  `root_obj_dir_variant=mailbox_public_flat`, complete all five marker groups,
  have no missing marker groups, and select the root-offset ABI.
  The fail-closed EH executable boundary now preflights both targets as ready
  for bridge execution without claiming GPU execution, stdout/cycles
  observables, timing, or speedup. Both still lack executed bridge comparison
  and timing. The generated matrix
  now folds EH bridge
  preflight `missing_build_context` into row-level missing prerequisites, so
  those blockers are visible even though the bridge preflight report exists.
  `reports/rtlmeter_veer_family_surface_audit.json` records them as
  `sidecar_bridge_preflight_surface_missing` and records why the measured EL2
  executable is not directly reusable: EL2-specific authority target,
  root-symbol/state-layout paths, root-offset review helper, sidecar environment
  contract, and `hello` program SHA. The
  matrix Markdown table now raises Vortex runner observations (`cycles=40897`,
  `proxy_handoff=true`, `fake_authority=true`, `runtime_marker=true`,
  `runtime_stub_rebuilt=true`, `runtime_bridge_stub_rebuilt=true`,
  `runtime_invocation_probe_executed=true`,
  `materialized_runtime_args_probe_executed=true`,
  `cuda_memory_transport=true`, `gpu=False`) while
  `reports/rtlmeter_vortex_observable_authority_audit.json` keeps
  `real_runtime_observable_authority_ready=false`, so proxy/fake-driver evidence
  and the rebuilt generated-main no-op/typed bridge/materialized-args probes
  stay separate from Vortex kernel execution, timing, and speedup claims.
  Vortex now has
  `reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json`, proving
  the real materialized buffer artifacts and DCR schedule are ready for the
  lowered-TB runtime-sequence boundary. It also has
  `reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json`, proving
  a generated lowered-TB-shaped C harness can consume those artifacts and call
  `vortex_lowered_tb_invoke_runtime_sequence`. It also has
  `reports/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json`,
  proving generated lowered-TB-shaped memory accesses can consume the same real
  artifacts through `vortex_memory_model_device.h`, replay the post condition to
  zero mismatches, and capture `TEST PASSED` bytes through IO_COUT.
  `reports/rtlmeter_vortex_cuda_memory_transport_preflight.json` proves real
  CUDA Driver API memory transport for the materialized Vortex inputs (`7`
  buffers, `37224` H2D bytes, `88` D2H-init bytes). It also has
  `reports/rtlmeter_vortex_cuda_runtime_sequence_preflight.json`, proving real
  CUDA Driver API upload, `9` DCR callbacks, a no-op kernel callback,
  observable export, and release across the same buffers. These are still not
  Vortex kernel execution, observable authority, timing, or speedup evidence.
  `reports/rtlmeter_vortex_cpu_reference_summary.json` proves the native CPU
  reference passes (`0.22s`, `40897` clocks, `TEST PASSED`), while
  `reports/rtlmeter_vortex_hybrid_candidate_summary.json` proves the current
  hybrid candidate is still fail-closed after the PATH-selected wrapper captures
  sidecar planning and Vortex context makes the handoff metadata ready. The
  Vortex authority-registry source-closure review, stdout/cycles runner
  contract, runner argv handoff, and direct-native stdout/cycles observation are
  now ready: the latest runner observes `40897` cycles, `TEST PASSED`, and
  reviewed proxy handoff while keeping GPU execution/timing/speedup claims
  false. The CUDA runtime-sequence preflight now also reports
  `preflight_authority_source=memory_post_condition`, and the generated DPI
  memory wrapper now has a compile-safe `vortex_mem_access_device_helper`
  shadow call. `reports/rtlmeter_vsim_main_vortex_probe_marker_strip.json`
  records that the generated-main runtime marker and expected-fail invocation
  probe were stripped from `Vsim__main.cpp`, preserving the materialized
  runtime-args probe, and the obj_dir rebuild passes. The generated Vsim path
  now has a real CUDA Driver API materialized runtime-args callback table and
  `reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.json`
  records proxy handoff with `returncode=0` when run from `obj_dir`; the next
  `reports/rtlmeter_vortex_real_kernel_artifact_preflight.json` now finds the
  Vortex PTX/meta artifact, and
  `reports/rtlmeter_vortex_kernel_artifact_build_attempt.json` passes without
  the previous lowered-IR landingpad/personality verifier errors. Syms-state-image
  metadata now clears artifact prelaunch rejection. The full PTX still times
  out under bounded `ptxas`, but `reports/rtlmeter_vortex_ptx_entry_slice.json`
  writes a `vl_eval_batch_gpu` single-entry slice and
  `reports/rtlmeter_vortex_ptx_entry_slice_module_load_diagnostic.json` proves
  that slice precompiles to cubin. With that cubin selected, the canonical real-CUDA smoke reaches `after_cuCtxSynchronize`, exports `memory_post_condition` authority, and `reports/rtlmeter_vortex_timing.json` records the first Vortex CPU-vs-hybrid timing gate as a negative result. The next action is `measure_or_unblock_veer_eh1_eh2_hybrid_timing`: continue EH1/EH2 bridge/timing work,
  not input parsing,
  wrapper selection, or sidecar context selection.
  `reports/rtlmeter_hybrid_measurement_difficulty.json` now adds the generated
  difficulty triage on top of the matrix: Vortex is score `1` measured/low with
  a measured negative CPU-vs-hybrid result (`hybrid_vs_cpu_ratio=2.047703304560855`);
  EH1 is score `6` high difficulty; EH2 is score `11` high difficulty because
  the generated syms-state image artifact clears prelaunch rejection and the
  entry-pruned CUBIN clears module load, but first eval faults with CUDA 700 and
  the entry-pruned PTX still contains `1456` C++/Verilator runtime-residue hits
  across `134` suspicious function definitions. Expanded host-cleanup removes
  scheduler/container call sites, but the same first eval CUDA 700 remains;
  return-before-eval and prologue-only return-before-eval-call probes pass.
  Staged `_eval` / `eval_phase__act` probes first place the fault in the
  `trigger_orInto__act` region, and inline probes narrow it to the
  eval-phase-context `__VnbaTriggered` store at `root+472408`: loads and OR pass,
  adjacent `__VactTriggered`, root-base, and entry-context `__VnbaTriggered`
  stores pass, while padded 2MiB state and maxr128 do not clear it. EL2 is score `1`
  measured/low but remains a serial-CPU-negative no-speedup baseline.

| Case | Hybrid measurement status | Current evidence | Required next step |
|---|---|---|---|
| `Vortex:mini:hello` | Hybrid measured; correctness passed; no speedup | CPU `0.22s` / `40897` clocks / `TEST PASSED`; canonical real-CUDA materialized runtime relocates `65` root-storage pointers, reaches `after_cuCtxSynchronize`, exports `memory_post_condition` authority, and `reports/rtlmeter_vortex_timing.json` records hybrid median `0.4504947270033881s`, `hybrid_vs_cpu_ratio=2.047703304560855`, `cpu_vs_hybrid_speedup=0.48835199795434103` | Continue EH1/EH2 unblock and timing |
| `VeeR-EH1:default:hello` | Not measured; entry-pruned module loads but eval-only launch faults | CPU reference passes (`1044` cycles, `0.03s`, `TEST_PASSED`); mailbox-public-flat rebuild passes; root-offset ABI review ready; generated PTX artifact ready; full `19`-step bridge reaches `run_vl_hybrid` but full PTX times out after `20s` at `before_cuModuleLoad`; bounded `ptxas -O0` on the full `17,684,220` byte / `630,613` line PTX also times out after `180s` with no cubin; entry-pruned eval+patch cubin builds in `17.98s`, loads, resolves kernels, uploads init state, and fails at the first synced `vl_eval_batch_gpu` launch; eval-only single-entry cubin fails the same way, and `2097152` byte padded storage, region-counter global init, plus accepted stack-limit overrides do not clear it; updated required host-I/O stub pass erases `47` EH1 host-I/O call sites and leaves zero matching calls in `vl_batch_gpu.host_io_stub_probe.ll`; regenerated host-I/O-stubbed single-entry eval CUBIN builds (`6735488` bytes, `ptxas -O0` `15.29s`) but the bridge still exits with `CUDA error 700` at first eval launch; runtime trace records `NUM_REGS=255`, `LOCAL_SIZE_BYTES=1776`, and padded 2MiB init-state still faults; compute-sanitizer is blocked before first instrumented CUDA API; EL2 direct reuse blocked | Isolate remaining scheduler/container/ABI device fault, then bridge comparison/timing |
| `VeeR-EH2:default:hello` | Not measured; entry-pruned CUBIN loads but first eval launch faults | CPU reference passes (`2325` cycles, `0.06s`, `TEST_PASSED`); mailbox-public-flat rebuild passes; root-offset ABI review ready; syms-state image artifact exists (`storage_size=623168`, `root_offset_in_state=192`, `unsafe_syms_gep_covered_by_state_image=true`, prelaunch rejection false); full PTX bridge still times out after `60s` at `before_cuModuleLoad` on the `44377841` byte PTX, but the eval+patch entry-pruned CUBIN builds with `ptxas -O0`, loads, resolves kernels, uploads init state, launches step-0 patch+eval, and with sync-each-step fails at `before_first_step_sync` with `CUDA error 700`; no-patch eval-only reproduces the same fault, and padded2m, stack64k, plus zero-init probes do not clear it; static PTX audit counts `1456` C++/Verilator runtime-residue hits and `134` suspicious function definitions; expanded host-cleanup removes scheduler/container call sites, but direct no-patch eval-only still fails with CUDA 700; return-before-eval and prologue-only return-before-eval-call probes pass; staged `_eval` / `eval_phase__act` plus inline probes narrow the first fault to eval-phase-context stores into `__VnbaTriggered` (`root+472408`): loads pass, adjacent `__VactTriggered`, root-base, and entry-context `__VnbaTriggered` stores pass, padded2m and maxr128 still fail; EL2 direct reuse blocked | Fix EH2 eval-phase `__VnbaTriggered` store-context CUDA 700, then bridge comparison/timing |
| `VeeR-EL2:default:hello` | Measured correctness pass | Best row `sidecar_wall_s_median=0.641226`, `sidecar_vs_cpu_parallel_ratio=3.460382` | Keep as no-speedup measured baseline |

## Issues

| ID | Issue File | Target File |
|---|---|---|
| FC-001 | [README goal and user path](issues/FC-001-readme-goal.md) | `README.md` |
| FC-002 | [Tool surface JSON wording](issues/FC-002-tool-surface-json-wording.md) | `docs/tool_surface.md` |
| FC-003 | [Verilator sidecar option scope](issues/FC-003-verilator-sidecar-option-scope.md) | `docs/verilator_sidecar_option.md` |
| FC-004 | [Results debug JSON wording](issues/FC-004-results-debug-json-wording.md) | `docs/results.md` |
| FC-005 | [Status goal frame](issues/FC-005-status-goal-frame.md) | `docs/status.md` |
| FC-006 | [Roadmap sidecar goal](issues/FC-006-roadmap-sidecar-goal.md) | `docs/roadmap.md` |
| FC-007 | [Sidecar command path split](issues/FC-007-sidecar-command-path-split.md) | `src/tools/hybrid_benchmark_sidecar_commands.py` |
| FC-008 | [Discovery payload debug role](issues/FC-008-discovery-payload-debug-role.md) | `src/tools/hybrid_benchmark_catalog.py` |
| FC-009 | [Operator JSON debug markers](issues/FC-009-operator-json-debug-markers.md) | `src/tools/hybrid_benchmark_operator_core.py` |
| FC-010 | [Sidecar operator non-claims](issues/FC-010-sidecar-operator-non-claims.md) | `src/tools/hybrid_benchmark_sidecar_operator.py` |
| FC-011 | [Shim debug JSON role](issues/FC-011-shim-debug-json-role.md) | `src/tools/verilator_sidecar_shim.py` |
| FC-012 | [Benchmark CLI help JSON wording](issues/FC-012-benchmark-cli-help-json-wording.md) | `src/tools/run_hybrid_benchmark_args.py` |
| FC-013 | [Minimal suite debug naming](issues/FC-013-minimal-suite-debug-naming.md) | `src/tools/hybrid_benchmark_minimal_suite.py` |
| FC-014 | [Discovery CLI contract](issues/FC-014-discovery-cli-contract.md) | `tests/contract/test_hybrid_benchmark_discovery_cli.py` |
| FC-015 | [Benchmark/config JSON contract](issues/FC-015-benchmark-config-json-contract.md) | `tests/contract/test_hybrid_benchmark_and_config_cli.py` |
| FC-016 | [Discovery example contract](issues/FC-016-discovery-example-contract.md) | `tests/contract/test_hybrid_benchmark_discovery_examples_cli.py` |
| FC-017 | [Shim example contract](issues/FC-017-shim-example-contract.md) | `tests/contract/test_hybrid_verilator_sidecar_shim_examples_cli.py` |
| FC-018 | [Codex README index](issues/FC-018-for-codex-readme-index.md) | `for_codex/README.md` |
| FC-019 | [Project memory archive warning](issues/FC-019-project-memory-archive-warning.md) | `for_codex/project_memory.md` |
| FC-020 | [Results memory archive warning](issues/FC-020-results-memory-archive-warning.md) | `for_codex/results_memory.md` |
| FC-021 | [Status memory authority warning](issues/FC-021-status-memory-authority-warning.md) | `for_codex/status.md` |
| FC-022 | [Roadmap memory authority warning](issues/FC-022-roadmap-memory-authority-warning.md) | `for_codex/roadmap.md` |
| FC-023 | [Selection goal decision gate](issues/FC-023-selection-goal-decision-gate.md) | `config/selection.json` |
| FC-024 | [RTLMeter user path goal](issues/FC-024-rtlmeter-user-path-goal.md) | `README.md`, `docs/tool_surface.md` |
| FC-025 | [RTLMeter Verilator command capture](issues/FC-025-rtlmeter-verilator-command-capture.md) | `src/tools/rtlmeter_*` |
| FC-026 | [RTLMeter PATH wrapper prototype](issues/FC-026-rtlmeter-path-wrapper-prototype.md) | `src/tools/rtlmeter_*`, `src/tools/verilator_sidecar_shim.py` |
| FC-027 | [RTLMeter compileArgs pass-through smoke](issues/FC-027-rtlmeter-compileargs-pass-through-smoke.md) | `tests/contract/test_rtlmeter_*` |
| FC-028 | [RTLMeter sidecar contract mapping](issues/FC-028-rtlmeter-sidecar-contract-mapping.md) | `src/tools/rtlmeter_*` |
| FC-029 | [RTLMeter first seed selection](issues/FC-029-rtlmeter-first-seed-selection.md) | `config/selection.json`, `config/targets.json` |
| FC-030 | [RTLMeter CPU/GPU compare integration](issues/FC-030-rtlmeter-cpu-gpu-compare-integration.md) | `src/tools/rtlmeter_*`, `reports/` |
| FC-031 | [RTLMeter overlays audit](issues/FC-031-rtlmeter-overlays-audit.md) | `src/tools/rtlmeter_overlay_audit.py`, `tests/contract/test_rtlmeter_overlays_audit.py` |
| FC-032 | [RTLMeter public contract tests](issues/FC-032-rtlmeter-public-contract-tests.md) | `tests/contract/test_rtlmeter_*` |
| FC-033 | [RTLMeter docs and troubleshooting](issues/FC-033-rtlmeter-docs-troubleshooting.md) | `README.md`, `docs/verilator_sidecar_option.md` |
| FC-034 | [RTLMeter first seed execution integration](issues/FC-034-rtlmeter-first-seed-execution-integration.md) | `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*` |
| FC-035 | [Clean sim GPU runtime preflight](issues/FC-035-clean-sim-gpu-runtime-preflight.md) | `src/tools/run_vl_hybrid.py`, `src/tools/run_vl_hybrid_launch.py`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md` |
| FC-036 | [Move generated tool binaries out of src](issues/FC-036-move-generated-tool-binaries-out-of-src.md) | `src/passes/Makefile`, `src/hybrid/Makefile`, `src/tools/build_vl_gpu_*`, `src/tools/run_vl_hybrid_*`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md` |
| FC-037 | [RTLMeter first seed timing and acceleration measurement](issues/FC-037-rtlmeter-first-seed-timing-acceleration.md) | `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*` |
| FC-038 | [Clean sim operator log hygiene](issues/FC-038-clean-sim-operator-log-hygiene.md) | `src/tools/run_hybrid_template.py`, `src/tools/hybrid_template_commands.py`, `src/tools/run_vl_hybrid.py`, `src/tools/run_vl_hybrid_state_sanitize.py`, `reports/`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md` |
| FC-039 | [Three-layer goal framing](issues/FC-039-three-layer-goal-framing.md) | `README.md`, `docs/roadmap.md`, `docs/status.md`, `docs/tool_surface.md` |
| FC-040 | [RTLMeter second seed broadening](issues/FC-040-rtlmeter-second-seed-broadening.md) | `src/tools/rtlmeter_*`, `tests/contract/test_rtlmeter_*` |
| FC-041 | [GPU Verilator wrapper packaging](issues/FC-041-gpu-verilator-wrapper-packaging.md) | `src/tools/rtlmeter_*`, `tests/contract/test_rtlmeter_*`, `README.md`, `docs/verilator_sidecar_option.md` |
| FC-042 | [Verilator --use-gpu first real path](issues/FC-042-verilator-use-gpu-first-real-path.md) | `src/tools/verilator_*`, `src/tools/hybrid_benchmark_*`, `tests/contract/test_hybrid_*`, `README.md`, `docs/verilator_sidecar_option.md` |
| FC-043 | [Frontend-neutral sidecar contract and CIRCT boundary](issues/FC-043-frontend-neutral-sidecar-contract-circt-boundary.md) | `src/tools/*sidecar*`, `src/hybrid/`, `docs/roadmap.md`, `docs/status.md`, `README.md`, `tests/contract/` |
| FC-044 | [External user readiness audit](issues/FC-044-external-user-readiness-audit.md) | `README.md`, `docs/`, `Makefile`, `tests/contract/`, `for_codex/issues.md` |
| FC-045 | [GPU sidecar eligibility and shape policy](issues/FC-045-gpu-sidecar-eligibility-policy.md) | `src/tools/*policy*`, `src/tools/hybrid_benchmark_*`, `docs/results.md`, `README.md`, `tests/contract/` |
| FC-046 | [LLVM GPU optimization pass roadmap](issues/FC-046-llvm-gpu-optimization-pass-roadmap.md) | `src/passes/`, `src/tools/build_vl_gpu_*`, `docs/results.md`, `README.md`, `tests/contract/` |
| FC-047 | [vl-gpu-abi-metadata](issues/FC-047-vl-gpu-abi-metadata.md) | `src/passes/vlgpugen.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/` |
| FC-048 | [vl-gpu-state-access-canon](issues/FC-048-vl-gpu-state-access-canon.md) | `src/passes/VlGpuPasses.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/` |
| FC-049 | [vl-gpu-inline-policy](issues/FC-049-vl-gpu-inline-policy.md) | `src/passes/VlGpuPasses.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/` |
| FC-050 | [vl-gpu-trigger-guard-factor](issues/FC-050-vl-gpu-trigger-guard-factor.md) | `src/passes/VlGpuPasses.cpp`, `src/passes/vlgpugen.cpp`, `tests/contract/` |
| FC-051 | [vl-gpu-resident-step-kernel](issues/FC-051-vl-gpu-resident-step-kernel.md) | `src/passes/vlgpugen.cpp`, `src/hybrid/`, `src/tools/run_vl_hybrid*`, `tests/contract/` |
| FC-052 | [vl-gpu-hot-field-soa](issues/FC-052-vl-gpu-hot-field-soa.md) | `src/passes/`, `src/hybrid/`, `src/tools/build_vl_gpu_*`, `tests/contract/` |

## Parallel Split

- Agent A: FC-001 through FC-006, public docs only.
- Agent B: FC-007 through FC-013, CLI and JSON/debug implementation.
- Agent C: FC-014 through FC-017, contract tests.
- Agent D: FC-018 through FC-023, Codex memory and source-of-truth alignment.
- Agent E: FC-024 through FC-034, FC-037, FC-040, FC-041, FC-058, and FC-064, RTLMeter user-path exploration. Keep this separate from current sidecar cleanup unless a file is explicitly owned. FC-034 is historical proxy/marker executing work and remains isolated from non-executing FC-024 through FC-033. FC-064 is the current VeeR-EL2 stdout/cycles correctness gate for FC-037 timing, while FC-058 remains related direct-native path context. FC-040 broadens to exactly one second seed only after FC-064 plus FC-037 evidence is reviewed. FC-041 packages the PATH wrapper and must fail closed without faking GPU execution.
- Agent F: FC-035 through FC-036 and FC-038, clean sim hardening. Keep it separate from RTLMeter execution integration, do not turn blocked GPU access into a success claim, do not normalize generated binaries under `src/` as acceptable public UX, and keep default operator logs concise enough for external users.
- Agent G: FC-039, public goal framing. Keep long-term UX, current preview support, frontend-neutral contract, and non-claims visually separated.
- Agent H: FC-042, first real Verilator `--use-gpu` path. Treat this lane as
  completed evidence after #9/#35; do not reopen it except to fix scoped-support
  wording.
- Agent I: FC-043, frontend-neutral contract/CIRCT boundary. Keep this as
  contract extraction and placeholder diagnostics only; no CIRCT execution claim.
- Agent J: FC-044, external-user readiness audit. This is the current active
  lane after #35; prefer deleting, moving, or demoting misleading files over
  documenting around them.
- Agent K: FC-045, GPU sidecar eligibility and shape policy. Use existing
  repeat-median evidence to produce conservative recommendations; do not claim
  automatic optimal allocation.
- Agent L: FC-046 through FC-052, LLVM/NVPTX optimization pass lane. Keep the
  first PR to ABI metadata, state-access canonicalization, or conservative
  inline policy; do not start with resident kernels or SoA.

## Guardrails

- Do not move canonical decisions into `for_codex/`.
- Do not promote JSON from debug output into runtime ABI.
- Do not claim CIRCT execution support yet.
- Do not claim general `verilator --use-gpu -f filelist.f --top-module top` support yet.
- Do not claim RTLMeter acceleration just because RTLMeter compiles.
- Keep RTLMeter's native user path intact; avoid requiring users to select repo-specific harness JSON manually.
- Do not update `config/selection.json` without a reviewed goal/priority change.
