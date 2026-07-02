# FC-037: RTLMeter First Seed Timing And Acceleration Measurement

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/2
Target file: `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*`

## Objective

After FC-064 proves the VeeR-EL2 RTLMeter seed can pass direct sidecar
stdout/cycles equivalence without the frozen proxy/marker lane, measure CPU vs
sidecar timing honestly. Keep CPU reference timing, CPU-parallel baseline timing,
GPU sidecar wall time, GPU kernel time, and RTLMeter's own metrics as separate
evidence. Do not claim acceleration from a single run; timing without repeated
measurement and a CPU-parallel baseline comparison is not usefulness evidence.

Depends on FC-030 (compare policy), FC-057/FC-058 native-path context, and
FC-064 / #63 (VeeR-EL2 direct sidecar stdout/cycles correctness). This issue
measures timing and CPU-parallel usefulness baselines only; correctness is owned
by FC-064.

## Tasks

- Measure timing only after FC-064 reports a passing CPU/direct-sidecar
  stdout/cycles compare for the VeeR-EL2 RTLMeter seed.
- Capture CPU reference timing (RTLMeter's own execute timing) and GPU sidecar timing (wall + kernel) as separate fields; never conflate RTLMeter timing with sidecar timing.
- Use repeated runs (e.g., median or central tendency of N runs) instead of a single run; record N and the methodology in the report.
- Establish a CPU-parallel baseline by running independent CPU-only RTLMeter
  simulations with isolated work roots, sweeping worker counts such as 1, 2, 4,
  and up to a documented local-core bound.
- For the CPU-parallel baseline, record wall time, completed simulations per
  second, worker count, per-run normalized stdout hash, and RTLMeter cycle
  count.
- Compare the GPU candidate against both serial CPU and the best valid
  CPU-parallel baseline; do not call the GPU useful merely because it beats only
  a serial CPU run.
- Write timing evidence to `reports/` only (for example `reports/rtlmeter_example_kind_hello_timing.json`); it is not source of truth.
- Report slowdown or no-change outcomes explicitly; do not suppress non-favorable results.
- Gate behind explicit opt-in. Fail closed or mark `blocked` when real Verilator or the GPU sidecar is unavailable; do not emit timing for a CPU-only fallback.

## 2026-06-14 Design-CPU Preload Parallel Probe

The "design CPU program preload as independent states/work roots" direction is
promising enough to keep pursuing.

Probe:

- Design: `VeeR-EL2:default`.
- Programs: `cmark/program.hex` and `cmark_iccm/program.hex`.
- One RTLMeter/Verilator compile artifact was reused.
- The two programs were run as separate RTLMeter processes with isolated
  execute roots.
- Generated report:
  `reports/design_cpu_preload_state_parallel_probe.json`.

Result:

- Serial CPU execution sum: `68.8s`.
- Parallel wall time for two different design-CPU programs: `38.626s`.
- Throughput improvement vs serial sum: `1.781x`.
- Effective two-worker parallel efficiency: `0.891`.
- Both runs passed and preserved RTLMeter cycle counts:
  `5277908` for `cmark`, `6025629` for `cmark_iccm`.

Interpretation:

- This is not GPU evidence.
- It does show that RTLMeter CPU-core designs with preloaded program memory can
  be treated as independent simulations and run concurrently with useful
  throughput gain.
- RTLMeter's internal computation graph is sequential, so the CPU-parallel
  baseline should be implemented as process-level orchestration with isolated
  work roots.
- This baseline is the right comparison floor for any later GPU usefulness
  claim on design-CPU workloads.

Next concrete task:

- Use the opt-in CPU-parallel RTLMeter baseline runner/report for existing
  compiled CPU-core cases. The first implementation lives at
  `src/tools/rtlmeter_cpu_parallel_baseline.py`; it accepts a case list, compile
  root, isolated execute roots under an artifact root, and worker count, then
  reports wall time, per-program pass/fail, normalized stdout hash, RTLMeter
  cycle count, and completed programs per second.
- Latest runner-generated report:
  `reports/rtlmeter_cpu_parallel_baseline_try.json`.
- Latest runner result: `status=passed`, all serial/parallel observables match,
  serial sum `70.459551s`, parallel wall `37.578359s`, speedup vs serial sum
  `1.875003x`, two-worker efficiency `0.937502`.
- An earlier workload-comparable duplicate-`hello` CPU-parallel report exists at
  `reports/rtlmeter_cpu_parallel_hello_baseline.json`. It runs two independent
  `VeeR-EL2:default:hello` execute/work roots, preserves stdout/cycles
  observables, and records serial sum `1.717726s`, parallel wall `0.954305s`,
  speedup vs serial sum `1.799976x`, and two-worker efficiency `0.899988`.
- An earlier representative duplicate-`hello` CPU-parallel report exists at
  `reports/rtlmeter_cpu_parallel_hello4_baseline.json`. It runs four
  independent `VeeR-EL2:default:hello` execute/work roots, preserves
  stdout/cycles observables, and records serial sum `3.892378s`, parallel wall
  `1.155366s`, speedup vs serial sum `3.368957x`, and four-worker efficiency
  `0.842239`.
- The eight-worker duplicate-`hello` CPU-parallel report is
  `reports/rtlmeter_cpu_parallel_hello8_baseline.json`. It runs eight
  independent `VeeR-EL2:default:hello` execute/work roots, preserves
  stdout/cycles observables, and records serial sum `7.070026s`, parallel wall
  `1.509886s`, speedup vs serial sum `4.682489x`, and eight-worker efficiency
  `0.585311`.
- The current representative duplicate-`hello` CPU-parallel report is
  `reports/rtlmeter_cpu_parallel_hello16_baseline.json`. It runs sixteen
  independent `VeeR-EL2:default:hello` execute/work roots, preserves
  stdout/cycles observables, and records serial sum `14.409478s`, parallel wall
  `2.218887s`, speedup vs serial sum `6.494012x`, and sixteen-worker efficiency
  `0.405876`.

## 2026-06-14 VeeR-EL2 GPU-Side Probe

The GPU side was tried for the same design-CPU direction and advanced through
the direct sidecar stdout/cycles correctness gate.

Reports:

- Wrapper/direct-native integration probe:
  `reports/rtlmeter_veer_el2_direct_native_probe.json`.
- Direct patched-Verilator known-closure diagnostic:
  `artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir/native_sidecar_build.json`.
- Direct sidecar bridge:
  `reports/rtlmeter_veer_el2_sidecar_bridge.json`.

Result:

- RTLMeter CPU baseline for `VeeR-EL2:default:hello` passed.
- FC-064 / #63 recognized the exact VeeR-EL2 filelist/top/program closure,
  materialized the extracted state image, launched the generated sidecar GPU
  artifact, reconstructed normalized stdout from the mailbox trace, and aligned
  `_rtlmeter_cycles.txt` to RTLMeter's injected `tb_top.core_clk` count.
- The bridge report now reaches
  `status=verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed` with
  `normalized_stdout_match=true`, `cycle_count_match=true`,
  `cpu_cycles=2229`, and `gpu_cycles=2229`.
- `cpu_as_gpu_fallback=false`, `timing_measured=false`, and
  `speedup_claimed=false` throughout.

Interpretation:

- The design-CPU preload/state-parallel direction has a useful CPU-parallel
  baseline, and VeeR-EL2 now has a direct sidecar correctness gate.
- The next GPU-side blocker is timing/usefulness, not correctness.
- Do not broaden to arbitrary RTLMeter CPU cores until this VeeR-EL2 timing
  gate records honest results.

## 2026-06-14 VeeR-EL2 Timing Stability Result

The FC-037 timing runner now records the current repeated sidecar timing
stability result for `VeeR-EL2:default:hello`.

Command:

```sh
RTLMETER_CPU_PARALLEL_BASELINE_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_cpu_parallel_baseline.py \
    --cases VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
    --compile-root artifacts/design_cpu_state_parallel_probe/veer_el2_serial \
    --artifact-root artifacts/rtlmeter_cpu_parallel_hello8_baseline \
    --max-workers 8 --timeout 10 --write-report \
    --report-out reports/rtlmeter_cpu_parallel_hello8_baseline.json

RTLMETER_VEER_EL2_TIMING_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_el2_timing.py \
    --samples 7 --batches 3 --sidecar-nstates 8 \
    --cpu-parallel-report reports/rtlmeter_cpu_parallel_hello8_baseline.json \
    --write-report
```

Report:

- `reports/rtlmeter_veer_el2_timing.json`
- `status=passed`
- `timing_measured=true`

## 2026-06-14 VeeR-EL2 Phase-Split Ordering Trial

The current phase-split GPU ordering trial is recorded in
`reports/rtlmeter_veer_el2_dhry_phase_nba_loop_trial_summary.json`.

What was fixed:

- `src/passes/VlGpuPasses.cpp` no longer replaces `_eval_phase__act` with
  `return false` unless it directly calls host scheduler/context APIs.
- `src/passes/vlgpugen.cpp` now passes syms self-pointer repair offsets into
  phase/probe kernels, matching `vl_eval_batch_gpu`.
- `src/passes/vlgpugen.cpp` now uses `vl_nba_loop_batch_gpu` around reachable
  `_eval_phase__nba` instead of the legacy unguarded
  `vl_nba_comb_batch_gpu` / `vl_nba_sequent_batch_gpu` sequence.

Result:

- Generated launch sequence:
  `vl_ico_batch_gpu`, `vl_act_loop_batch_gpu`, `vl_nba_loop_batch_gpu`.
- The phase sequence now progresses through the bounded 1000-cycle `dhry`
  trace and reaches the same final observables as the single eval kernel:
  `mcycle=999`, `minstret=709`, `pc=0x40000270`, `pc_d=0x40000274`, `obuf=32`.
- The original divergence remains at `gpu_step=895`: phase-split still has
  `fetch_stall=1` and `decode_d=0`.

Interpretation:

- The phase-split execution path is now a valid progress probe, but phase
  ordering alone does not explain the `fetch_stall` / `decode_d` mismatch.
- Next task: add or compare the input dependency signals for
  `ifu_pmu_fetch_stall` around `gpu_step=895` / CPU post-reset `898`, then
  rerun the bounded trace compare.
- `sample_count=7`
- `batch_count=3`
- `total_sample_count=21`
- `cpu_reference_elapsed_s=0.04`
- `cpu_parallel_report=reports/rtlmeter_cpu_parallel_hello8_baseline.json`
- `cpu_parallel_wall_s=1.509886`
- `cpu_parallel_speedup_vs_serial_sum=4.682489`
- `sidecar_parallel_state_count=8`
- `parallel_state_validation_complete=true`
- `sidecar_executable_invocation_mode_counts={"in_process_veer_el2_sidecar": 21}`
- `run_vl_hybrid_launcher_mode_counts={"direct_hybrid_runtime": 21}`
- `init_replication_mode_counts={"device_kernel": 21}`
- `patch_drive_scope_counts={"all_states": 21}`
- `sidecar_wall_s_median=0.610509`
- `sidecar_wall_s_batch_medians=[0.797720, 0.592994, 0.610509]`
- `sidecar_wall_s_median_of_batch_medians=0.610509`
- `gpu_kernel_ms_total_median=224.068604`
- `sidecar_vs_serial_cpu_ratio=0.065519`
- `sidecar_vs_cpu_parallel_ratio=2.473159`
- `sidecar_parallel_states_per_s_median=13.103820`
- `sidecar_wall_s_per_parallel_state_median=0.076314`
- `bridge_preflight_s_median=0.000401`
- `sidecar_executable_wall_s_median=0.609780`
- `sidecar_run_vl_hybrid_wall_s_median=0.602956`
- `sidecar_host_overhead_estimate_s_median=0.383020`
- `patch_apply_mode=device_resident_patch_schedule`
- `step_trace_copy_mode=device_buffered_coalesced_d2d_trace`
- `step_trace_copy_mode_counts={"device_buffered_coalesced_d2d_trace": 21}`
- `step_trace_field_mode=mailbox_rising_edge_trace_final_counter_fallback`
- `mapped_fields_cache_status_counts={"hit": 21}`
- `cpu_parallel_wall_time_outcome=sidecar_faster_than_comparable_cpu_parallel_baseline`
- `timing_stability_outcome=stable_repeated_batch_outcome`
- `cpu_parallel_faster_batch_count=3`
- `cpu_parallel_slower_batch_count=0`
- `preliminary_outcome=sidecar_slower_than_serial_cpu`
- `cpu_parallel_comparison_valid=true`
- `gpu_cpu_parallel_comparison_valid=true`
- `speedup_claimed=false`

Interpretation:

- Correctness samples pass, so this is timing evidence for the current direct
  sidecar path.
- The GPU sidecar now actually launches `nstates=8`, calls the hybrid C runtime
  directly instead of launching through `run_vl_hybrid.py`, and the bridge now
  invokes the reviewed Python sidecar in-process instead of spawning it as a
  separate Python executable. It drives clock/reset patches across all eight state
  strides, uses device-kernel init-state replication, and validates final
  observables for all eight states. The stdout stream remains traced and compared
  from state 0 only.
- The current GPU sidecar path is still much slower than serial RTLMeter CPU
  execution, but all three seven-sample batch medians are faster than the
  comparable eight-worker CPU-parallel `hello` baseline. Per-state wall is
  `0.076314s`, so increasing design-CPU state parallelism is currently useful
  for throughput even though total wall remains slower than serial CPU.
- The mapped-field cache, safe-metadata preflight skip, two-field
  coalesced device-buffered DtoD trace path, rising-edge mailbox reconstruction,
  final counter fallback, and device-resident patch schedule reduced the measured GPU
  event time versus the previous device-buffered trace paths while preserving
  stdout/cycles correctness.
- The added multi-batch stability gate removes the immediate single-median
  ambiguity for the CPU-parallel floor in this run. This is still not a broad
  RTLMeter GPU usefulness claim because serial CPU remains much faster and the
  evidence is scoped to one seed.
- Current next work has moved beyond generic trace/resident-patch overhead:
  make the fixed-flat-memory non-`hello` `dhry` path eligible for pair-cycle
  loop collapse despite the multi-kernel VeeR launch sequence before claiming
  usefulness.

## 2026-06-14 VeeR-EL2 Sixteen-State Scaling Result

The next FC-037 scaling gate increases the GPU sidecar to `nstates=16` and
compares it with a matching sixteen-worker duplicate-`hello` CPU-parallel
baseline. This keeps the same correctness policy: state-0 stdout/cycles are
compared against CPU, and final observables must match state 0 across every
launched GPU state.

Reports:

- CPU-parallel baseline:
  `reports/rtlmeter_cpu_parallel_hello16_baseline.json`
- Sidecar timing:
  `reports/rtlmeter_veer_el2_timing_nstates16.json`

Result:

- CPU-parallel `status=passed`
- CPU-parallel case count: `16`
- CPU-parallel wall: `2.218887s`
- CPU-parallel speedup vs serial sum: `6.494012x`
- CPU-parallel efficiency: `0.405876`
- Sidecar `status=passed`
- Sidecar correctness samples: `21/21`
- `sidecar_parallel_state_count=16`
- `parallel_state_validation_complete=true`
- `sidecar_wall_s_median=0.768573`
- `sidecar_wall_s_batch_medians=[0.768573, 0.706345, 0.884339]`
- `gpu_kernel_ms_total_median=268.161011`
- `sidecar_vs_cpu_parallel_ratio=2.887022`
- `sidecar_vs_serial_cpu_ratio=0.052045`
- `sidecar_parallel_states_per_s_median=20.817801`
- `sidecar_wall_s_per_parallel_state_median=0.048036`
- `sidecar_run_vl_hybrid_wall_s_median=0.759191`
- `sidecar_host_overhead_estimate_s_median=0.494926`
- `step_trace_copy_mode_counts={"device_buffered_coalesced_d2d_trace": 21}`
- `step_trace_filter_counts={"start=4,stride=2": 21}`
- `step_trace_filter_rows_median=727.0`
- `step_trace_filter_capacity_median=1457.0`
- `resident_patch_records_median=69936.0`
- `resident_patch_logical_steps_median=1457.0`
- `cpu_parallel_wall_time_outcome=sidecar_faster_than_comparable_cpu_parallel_baseline`
- `serial_cpu_wall_time_outcome=sidecar_slower_than_serial_cpu`
- `speedup_claimed=false`

Scaling interpretation:

- Compared with the eight-state gate, total sidecar wall is `1.258905x` worse
  (`0.768573s` vs `0.610509s`), so simply increasing state count does not yet
  improve total latency for `hello`.
- Per-state wall improves by `1.588683x` (`0.076314s` to `0.048036s`), and
  states/s improves by `1.588682x` (`13.103820` to `20.817801`), so GPU
  state-parallel throughput scales in the useful direction.
- The CPU-parallel comparison ratio improves by `1.167342x`
  (`2.473159` to `2.887022`) because the sixteen-worker CPU baseline loses
  efficiency while the GPU sidecar amortizes more work.
- A previous filtered sixteen-state run reached `0.643080s`, so the latest
  rerun shows significant wall-time variability rather than a robust new
  speedup. The rejected delta patch-script experiment reduced patch records but
  was not retained because it worsened timing in the full gate.
- This still is not a broad RTLMeter GPU usefulness claim because serial CPU
  remains much faster. The next blocker is reducing `run_vl_hybrid` launch,
  device-trace, and resident-patch overhead enough that total wall moves toward
  the serial CPU baseline.

## 2026-06-14 Patch/Eval Fusion Smoke

The next overhead-reduction trial fuses the VeeR-style state-grouped resident
patch application with root eval into a generated `vl_patch_eval_batch_gpu`
kernel. This is deliberately scoped to state-grouped patch records where each
GPU state owns its own patch slice; general RTLMeter/RTL cases still require
fallback.

Implementation status:

- `src/passes/vlgpugen.cpp` now emits `vl_patch_eval_batch_gpu`.
- `src/hybrid/run_vl_hybrid.c` enables the path only when
  `RUN_VL_HYBRID_FUSED_PATCH_EVAL=1`, the fused symbol is present, the kernel
  chain is single-eval, no legacy host patch array is active, and per-step patch
  records are divisible by `nstates`.
- `src/tools/veer_el2_sidecar_executable.py` can request the fused path for the
  VeeR direct sidecar path when `VEER_EL2_SIDECAR_FUSED_PATCH_EVAL=1`, and
  records `patch_eval_fusion` in the run report when the runtime prints it.
- `src/tools/rtlmeter_veer_el2_timing.py` summarizes fusion availability,
  launched-step count, and fallback count.

Smoke evidence:

- New VeeR CUBIN contains `vl_patch_eval_batch_gpu`.
- `reports/rtlmeter_veer_el2_timing_fusion_smoke_cached.json` records
  `status=passed`, stdout/cycles equivalence preserved, all 16 final-state
  observables matched state 0, and
  `patch_eval_fusion_available_counts={"true": 1}`.
- The same smoke records `patch_eval_fusion_launched_median=1457.0` and
  `patch_eval_fusion_fallback_median=0.0`.
- Cached single-sample timing was variable; the latest summary records
  `sidecar_wall_s_median=1.063368`, `run_vl_hybrid_wall_s=1.030664`, and
  `gpu_kernel_ms_total_median=273.930237`. An immediately prior cache-hit smoke
  recorded `sidecar_wall_s=0.710882` and `run_vl_hybrid_wall_s=0.676035`.
- A full repeated fusion gate at
  `reports/rtlmeter_veer_el2_timing_nstates16_fusion.json` records
  `status=passed`, `total_sample_count=21`,
  `patch_eval_fusion_available_counts={"true": 21}`,
  `patch_eval_fusion_launched_median=1457.0`, and
  `patch_eval_fusion_fallback_median=0.0`.
- The full fusion gate did not improve the existing representative 16-state
  timing: `sidecar_wall_s_median=0.774456` versus the current non-fusion
  representative `0.768573`; `run_vl_hybrid_wall_s=0.764437` versus `0.759191`;
  `gpu_kernel_ms_total_median=267.921417` versus `268.161011`.
- After that result, the VeeR sidecar default was returned to the non-fusion
  path. `reports/rtlmeter_veer_el2_timing_post_fusion_default_smoke.json`
  records `status=passed` and `patch_eval_fusion_available_counts={}`.

Interpretation:

- Fusion is correctness-safe for the current VeeR state-grouped patch schedule
  in smoke and repeated testing, and it removes the separate resident patch
  kernel launch from the logical path.
- It is not a useful timing optimization for the current VeeR `hello` gate. The
  full repeated result is slightly worse than the current representative
  non-fusion run.
- Keep fusion as an explicit experiment only. The next overhead target should
  shift away from patch/eval fusion toward trace/output reduction, fewer logical
  eval steps, or a more substantial resident-step kernel that avoids per-step
  host launch structure.

## 2026-06-14 Fewer Logical Eval Steps Diagnostic

The next concrete FC-037 probe is now the opt-in VeeR sidecar clock patch mode:

```sh
VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=posedge_only \
RTLMETER_VEER_EL2_TIMING_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_el2_timing.py \
    --samples 1 --batches 1 --sidecar-nstates 16 \
    --cpu-parallel-report reports/rtlmeter_cpu_parallel_hello16_baseline.json \
    --write-report \
    --report-out reports/rtlmeter_veer_el2_timing_posedge_only_smoke.json
```

Implementation status:

- `src/tools/veer_el2_sidecar_executable.py` accepts
  `VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=posedge_only`.
- The default remains `full_clock_reset_fields`.
- The experimental mode writes reset drives and a reset-release low drive, then
  repeats only clock-high drives. For the default VeeR `hello` timing case this
  reduces the patch script from `1457` logical eval steps to `730`.
- The step trace filter changes from `start=4,stride=2` to `start=3,stride=1`
  for the default `reset_launches=2` setup, and the report keeps the distinct
  `patch_script_mode=experimental_posedge_only_clock_high_fields` marker.

Correctness risk:

- This mode is expected to be risky because repeated high drives do not create
  repeated posedges if the design clock never returns low.
- Passing Verilator/GPU launch is not enough. The mode must pass RTLMeter
  stdout/cycles comparison and all-state final observable validation before any
  timing number is meaningful.
- If this diagnostic fails, the next viable direction is not another high-only
  claim; it is a pair-cycle or resident-step kernel that preserves ordered
  low-eval then high-eval semantics inside one runtime operation.

Measured smoke result:

- `reports/rtlmeter_veer_el2_timing_posedge_only_smoke.json` records
  `status=failed` and `timing_measured=false`.
- The mode marker is recorded as
  `clock_patch_mode_counts={"experimental_posedge_only_clock_high_fields": 1}`.
- Work was reduced: `resident_patch_logical_steps_median=730.0`,
  `resident_patch_records_median=35040.0`, `step_trace_filter_counts={"start=3,stride=1": 1}`,
  and `gpu_kernel_ms_total_median=18.813951`.
- Correctness failed: `normalized_stdout_match=false`, stdout was not
  reconstructed, `finish_marker_observed=false`, and final VeeR counters stayed
  at `mcycle=0`, `minstret=0`, `pc=0`.
- Conclusion: high-only patching is not valid for the VeeR design CPU. The next
  implementation should preserve low/high eval ordering while reducing host or
  launch overhead.

## 2026-06-14 Pair-Cycle Resident-Step Probe

The follow-up probe keeps the validated low-eval then high-eval clock
semantics, but pairs the two logical clock phases inside the resident runtime
loop. This is explicitly opt-in and does not change the default clock patch
mode.

Command:

```sh
VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle \
RTLMETER_VEER_EL2_TIMING_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_el2_timing.py \
    --samples 7 --batches 3 --sidecar-nstates 16 \
    --cpu-parallel-report reports/rtlmeter_cpu_parallel_hello16_baseline.json \
    --write-report \
    --report-out reports/rtlmeter_veer_el2_timing_pair_cycle_nstates16.json
```

Implementation status:

- `src/tools/veer_el2_sidecar_executable.py` accepts
  `VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle`.
- The sidecar sets `RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE=1` and
  `RUN_VL_HYBRID_RESIDENT_PAIR_CYCLE_START=3` for the default VeeR reset
  setup.
- The patch script still emits the same low/high logical clock sequence as the
  full mode, and the state-0 trace filter remains high-phase only
  (`start=4,stride=2`).
- `src/hybrid/run_vl_hybrid.c` reports the runtime mode as
  `resident_pair_cycle: requested=true ... mode=low_eval_high_eval`.
- The pair-cycle path is rejected when patch/eval fusion is also requested,
  because the current fused kernel is single-logical-step only.

Result:

- `reports/rtlmeter_veer_el2_timing_pair_cycle_smoke.json` passed one-sample
  correctness and timing smoke.
- `reports/rtlmeter_veer_el2_timing_pair_cycle_nstates16.json` records
  `status=passed`, `timing_measured=true`, and `total_sample_count=21`.
- All 21 samples pass stdout/cycles comparison and all-state final-observable
  validation.
- `clock_patch_mode_counts={"resident_pair_cycle_low_high_eval": 21}`
- `resident_pair_cycle_mode_counts={"low_eval_high_eval": 21}`
- `resident_pair_cycle_launched_median=727.0`
- `resident_pair_cycle_fallback_median=0.0`
- `sidecar_wall_s_median=0.692794`
- `sidecar_wall_s_batch_medians=[0.699068, 0.704572, 0.664298]`
- `gpu_kernel_ms_total_median=267.055115`
- `sidecar_run_vl_hybrid_wall_s_median=0.682324`
- `sidecar_host_overhead_estimate_s_median=0.419148`
- `sidecar_vs_cpu_parallel_ratio=3.202809`
- `sidecar_vs_serial_cpu_ratio=0.057737`
- `speedup_claimed=false`

Interpretation:

- Pair-cycle is correctness-safe for the current VeeR `hello` gate and improves
  the latest non-fusion representative wall time by `1.109382x`
  (`0.768573s` to `0.692794s`).
- A confirmatory repeated gate at
  `reports/rtlmeter_veer_el2_timing_pair_cycle_confirm_nstates16.json` also
  passed 21/21 correctness samples and kept `resident_pair_cycle_fallback_median=0.0`.
  Its sidecar median was `0.707203s`, still `1.086778x` faster than the
  non-fusion representative, with batch medians `0.868907`, `0.673572`, and
  `0.685787`.
- The improvement is mostly host-loop/runtime overhead: the current pair-cycle
  still launches low-step and high-step patch/eval work separately rather than
  using one true fused pair kernel.
- The result is still much slower than serial CPU (`0.04s`) and does not beat
  the previous best filtered 16-state observation (`0.643080s`), so this is not
  broad RTLMeter GPU usefulness evidence.
- Keep the mode opt-in. The non-fused pair-cycle result motivated the fused
  pair-cycle follow-up below.

Completed follow-up direction:

- Implement a true fused pair-cycle resident kernel that performs low
  patch/eval then high patch/eval in one runtime operation. This is measured in
  the following section.

## 2026-06-14 Fused Pair-Cycle Resident Kernel

The true fused pair-cycle follow-up keeps the same validated low/high clock
semantics but emits a generated kernel that performs low patch/eval then high
patch/eval inside one GPU launch for each pair.

Command:

```sh
VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle \
VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1 \
RTLMETER_VEER_EL2_TIMING_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_el2_timing.py \
    --samples 7 --batches 3 --sidecar-nstates 16 \
    --cpu-parallel-report reports/rtlmeter_cpu_parallel_hello16_baseline.json \
    --write-report \
    --report-out reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json
```

Implementation status:

- `src/passes/vlgpugen.cpp` emits `vl_patch_eval_pair_cycle_batch_gpu`.
- `src/hybrid/run_vl_hybrid.c` resolves the symbol optionally and uses it only
  when `RUN_VL_HYBRID_FUSED_PAIR_CYCLE=1`.
- `src/tools/veer_el2_sidecar_executable.py` exposes that as
  `VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1` and records `pair_cycle_fusion`.
- `src/tools/rtlmeter_veer_el2_timing.py` records the opt-in env in the
  reproducibility command and summarizes `pair_cycle_fusion_*` fields.
- The VeeR CUBIN was rebuilt in syms-state-image mode with `storage_size=433472`;
  the generated PTX contains both `vl_patch_eval_batch_gpu` and
  `vl_patch_eval_pair_cycle_batch_gpu`.

Smoke:

- `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_smoke.json` passed but was
  dominated by a mapped-field cache miss after the CUBIN rebuild.
- `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_smoke_cached.json` passed
  with cache hit, `sidecar_wall_s_median=0.675046`,
  `gpu_kernel_ms_total_median=265.409546`,
  `pair_cycle_fusion_available_counts={"true": 1}`,
  `pair_cycle_fusion_launched_median=727.0`, and fallback median `0.0`.

Full repeated result:

- `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json`
- `status=passed`
- `timing_measured=true`
- `total_sample_count=21`
- all 21 samples passed stdout/cycles and all-state final-observable validation
- `pair_cycle_fusion_available_counts={"true": 21}`
- `pair_cycle_fusion_launched_median=727.0`
- `pair_cycle_fusion_fallback_median=0.0`
- `resident_pair_cycle_launched_median=727.0`
- `resident_pair_cycle_fallback_median=0.0`
- `sidecar_wall_s_median=0.641226`
- `sidecar_wall_s_batch_medians=[0.620763, 0.649879, 0.641226]`
- `gpu_kernel_ms_total_median=262.026245`
- `sidecar_run_vl_hybrid_wall_s_median=0.631477`
- `sidecar_host_overhead_estimate_s_median=0.374121`
- `sidecar_vs_cpu_parallel_ratio=3.460382`
- `sidecar_vs_serial_cpu_ratio=0.062381`
- `speedup_claimed=false`
- Actual launch reporting smoke:
  `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_actual_launch_smoke.json`
  passed with `gpu_kernel_timing_logical_step_count_median=1457.0`,
  `gpu_kernel_timed_launch_count_median=733.0`, and
  `gpu_kernel_time_ms_per_actual_launch_median=0.373625`. The actual count is
  not the same as `pair_cycle_fusion_launched_median=727.0`: it includes the
  727 fused pair-cycle kernels plus six reset/deassert patch/eval launches.

Interpretation:

- This is the current best VeeR 16-state sidecar result.
- It improves the latest non-fusion representative by `1.198599x`
  (`0.768573s` to `0.641226s`).
- It improves the pair-cycle confirm gate by `1.102892x`
  (`0.707203s` to `0.641226s`).
- It narrowly improves the previous best filtered 16-state observation by
  `1.002891x` (`0.643080s` to `0.641226s`).
- It still does not prove broad RTLMeter GPU usefulness: serial CPU remains
  about `16.030650x` faster for this `hello` seed.
- The old `gpu_kernel_time_ms_per_launch` field is retained for compatibility,
  but usefulness analysis should prefer the explicit
  `gpu_kernel_timed_launch_count` and
  `gpu_kernel_time_ms_per_actual_launch` fields when pair-cycle/fused paths are
  enabled.

Next concrete task:

- Do not spend the next step merely promoting pair-cycle/fused-pair defaults.
  The remaining blocker is the serial CPU gap.
- Either increase useful parallel work per run beyond `hello`/16-state, or
  reduce remaining step trace/output/runtime overhead enough to move total wall
  toward the `0.04s` serial CPU baseline.

## 2026-06-14 Fused Pair-Cycle Thirty-Two-State Scaling Gate

The next scale point doubles the duplicate-`hello` comparison from 16 to 32
states.

CPU-parallel baseline:

```sh
RTLMETER_CPU_PARALLEL_BASELINE_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_cpu_parallel_baseline.py \
    --cases $(printf 'VeeR-EL2:default:hello %.0s' {1..32}) \
    --compile-root artifacts/design_cpu_state_parallel_probe/veer_el2_serial \
    --artifact-root artifacts/rtlmeter_cpu_parallel_hello32_baseline \
    --max-workers 32 --timeout 10 --write-report \
    --report-out reports/rtlmeter_cpu_parallel_hello32_baseline.json
```

CPU result:

- `reports/rtlmeter_cpu_parallel_hello32_baseline.json`
- `status=passed`
- `case_count=32`
- `parallel_wall_s=4.246739`
- `serial_sum_case_wall_s=29.070679`
- `parallel_speedup_vs_serial_sum=6.845413`
- `parallel_efficiency=0.213919`
- all serial/parallel stdout hashes and RTLMeter cycle counts match

Initial GPU attempt:

- `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json` initially
  failed closed before timing.
- Direct sidecar stderr showed:
  `veer_el2_clock_reset_patch.txt line 1 exceeds max patches per step (64)`.
- Cause: a 32-state clock/reset patch row has 3 fields x 32 states = 96
  patches.
- Fix: `src/hybrid/run_vl_hybrid.c` raises `MAX_PATCHES` to 256, and
  `tests/contract/test_verilator_native_sidecar_make_driver.py` now covers
  32-state patch script expansion.

Full GPU gate:

```sh
VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle \
VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1 \
RTLMETER_VEER_EL2_TIMING_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_el2_timing.py \
    --samples 7 --batches 3 --sidecar-nstates 32 \
    --cpu-parallel-report reports/rtlmeter_cpu_parallel_hello32_baseline.json \
    --write-report \
    --report-out reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json
```

GPU result:

- `reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json`
- `status=passed`
- `timing_measured=true`
- `total_sample_count=21`
- all 21 stdout/cycles and all-state final-observable validations passed
- `sidecar_wall_s_median=0.950341`
- `sidecar_wall_s_batch_medians=[0.840963, 0.906735, 0.956599]`
- `gpu_kernel_ms_total_median=357.866486`
- `gpu_kernel_timing_logical_step_count_median=1457.0`
- `gpu_kernel_timed_launch_count_median=733.0`
- `gpu_kernel_time_ms_per_actual_launch_median=0.488222`
- `pair_cycle_fusion_available_counts={"true": 21}`
- `pair_cycle_fusion_launched_median=727.0`
- `pair_cycle_fusion_fallback_median=0.0`
- `resident_patch_records_median=139872.0`
- `sidecar_vs_cpu_parallel_ratio=4.468648`
- `sidecar_vs_serial_cpu_ratio=0.04209`
- `speedup_claimed=false`

Scaling interpretation:

- Doubling from 16 to 32 states worsens total wall by `1.482069x`
  (`0.641226s` to `0.950341s`).
- Per-state wall improves by `1.349465x` (`0.040077s` to `0.029698s`).
- States/s improves by `1.349465x` (`24.952201` to `33.672124`).
- The CPU-parallel comparison ratio improves by `1.291374x`
  (`3.460382` to `4.468648`) because the 32-worker CPU baseline loses
  efficiency.
- Serial CPU remains about `23.758525x` faster than the 32-state sidecar wall,
  so this is throughput-scaling evidence, not a latency speedup or broad
  RTLMeter usefulness claim.

Next concrete task:

- Do not continue by only increasing duplicate `hello` states. The patch record
  count doubled from `69936` to `139872`, and total wall worsened.
- Prefer either reducing per-state patch/trace/runtime overhead for 32+ states,
  or moving to a workload with more useful design-CPU work per GPU state.

## 2026-06-14 VeeR-EL2 State-Local Patch Compression Probe

The doubled 32-state patch record count was tested directly with an opt-in
state-local resident patch schedule and a new fused pair-cycle kernel symbol:
`vl_patch_eval_pair_cycle_batch_gpu_state_local`.

Command:

```sh
VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle \
VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1 \
VEER_EL2_SIDECAR_STATE_LOCAL_PATCHES=1 \
RTLMETER_VEER_EL2_TIMING_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_el2_timing.py \
    --samples 7 --batches 3 --sidecar-nstates 32 \
    --cpu-parallel-report reports/rtlmeter_cpu_parallel_hello32_baseline.json \
    --write-report \
    --report-out reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json
```

Reports:

- Smoke:
  `reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32_smoke.json`
- Full gate:
  `reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json`

Result:

- `status=passed`
- `total_sample_count=21`
- all 21 stdout/cycles and all-state final-observable validations passed
- `pair_cycle_state_local_fusion_available_counts={"true": 21}`
- `pair_cycle_state_local_fusion_launched_median=727.0`
- `pair_cycle_state_local_fusion_fallback_median=0.0`
- expanded resident patch records: `139872.0`
- state-local patch records: `4371.0`
- record reduction vs expanded schedule: `32.0x`
- `sidecar_wall_s_median=2.452390`
- `sidecar_wall_s_batch_medians=[2.385776, 2.434931, 2.470700]`
- `gpu_kernel_ms_total_median=1675.526123`
- `gpu_kernel_time_ms_per_actual_launch_median=2.285847`
- `sidecar_vs_cpu_parallel_ratio=1.731674`
- `sidecar_vs_serial_cpu_ratio=0.016311`
- `speedup_claimed=false`

Interpretation:

- The implementation is correctness-safe and proves the repeated clock/reset
  patch schedule can be compressed from global per-state records to local
  per-state records.
- It is not useful for performance on this seed. Compared with the expanded
  32-state fused path, total wall is `2.580537x` slower and GPU kernel total is
  `4.681987x` slower.
- The likely weak point is not just record storage size; the state-local fused
  kernel still executes the per-state patch loop per GPU thread and introduces a
  worse code path for the tiny `hello` workload.
- Keep `VEER_EL2_SIDECAR_STATE_LOCAL_PATCHES=1` as opt-in diagnostic evidence.
  Do not promote it to the default path.

Next concrete task:

- Avoid spending the next step on this state-local patch-loop form.
- Prefer reducing trace/host overhead, reducing eval/kernel launch overhead, or
  moving to a design-CPU workload with more useful work per state.

## 2026-06-14 Non-Hello Program Preload Fail-Closed Fix

The next useful direction is a design-CPU workload with more work per state, such
as `cmark`, rather than more duplicate `hello` lanes. A probe exposed a safety
gap before timing could be trusted:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/verilator_native_sidecar_make_driver.py \
    materialize-veer-el2-state-image \
    --repo-root . \
    --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
    --top-module tb_top \
    --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
    --rtlmeter-program-hex third_party/rtlmeter/designs/VeeR-EL2/tests/cmark/program.hex \
    --state-image-out artifacts/veer_el2_direct_verilator_sidecar_probe/veer_el2_cmark_state_image_probe_after_fix.json \
    --summary-out reports/veer_el2_cmark_state_image_materialize_after_fix.json
```

Result after the fix:

- exit code: `1`
- `status=verilator_native_sidecar_blocked_veer_el2_state_image_materializer`
- `state_image_materialized=false`
- `rtlmeter_program_hex=third_party/rtlmeter/designs/VeeR-EL2/tests/cmark/program.hex`
- `accepted_program_preload=third_party/rtlmeter/designs/VeeR-EL2/tests/hello/program.hex`
- `detected_layout.rtlmeter_program_identity_verified=false`
- diagnostic: requested RTLMeter program does not match the reviewed accepted
  preload

Interpretation:

- Before this fix, a mismatched `--rtlmeter-program-hex` could be detected but
  still materialize the reviewed `hello` state image. That would make a later
  cmark GPU timing run a false positive.
- The materializer now refuses to write a state image when the requested program
  does not match the reviewed authority. This is required before any non-`hello`
  design-CPU GPU timing can be trusted.

Next concrete task:

- Reduce/evaluate pair-cycle launch-count feasibility for reviewed non-`hello`
  programs, or define a bounded non-`hello` correctness/timing smoke before any
  full `cmark`-class RTLMeter timing run.

## 2026-06-14 Reviewed Non-Hello Preload Materialization

Implemented a reviewed allowlist for VeeR-EL2 RTLMeter `program.hex` preload
identity. The materializer now accepts matching reviewed non-`hello` programs
without reopening arbitrary program support:

- `cmark`: `reports/veer_el2_cmark_state_image_materialize.json`
- `cmark_iccm`: `reports/veer_el2_cmark_iccm_state_image_materialize.json`
- `dhry`: `reports/veer_el2_dhry_state_image_materialize.json`

All three reports have `reviewed_rtlmeter_program_preload_supported=true`,
`detected_layout.rtlmeter_program_identity_verified=true`, and
`state_image_materialized=true`. The previous mismatch gate remains as
`reports/veer_el2_cmark_state_image_materialize_after_fix.json`, which refuses
an unaccepted program/image pairing rather than writing a false `hello` image.

Interpretation:

- This clears the hello-only preload/materialization blocker for the reviewed
  non-`hello` programs.
- It is not GPU timing, speedup, or usefulness evidence.
- Full `cmark`/`cmark_iccm` RTLMeter GPU timing was not run because the current
  pair-cycle execution model would require millions of GPU launches for a full
  design-CPU program. The next blocker is launch-count collapse with resident
  multi-cycle execution, or a deliberately bounded non-`hello` smoke gate.

## 2026-06-14 Non-Hello Launch-Count Feasibility Gate

Added a pre-run launch-count feasibility gate to the VeeR-EL2 timing reporter.
It estimates the current resident pair-cycle fused runtime launch count from the
CPU RTLMeter cycle count and blocks before bridge execution when the estimate
exceeds the configured threshold.

Reports:

- `reports/rtlmeter_veer_el2_timing_cmark_launch_feasibility.json`
- `reports/rtlmeter_veer_el2_timing_cmark_iccm_launch_feasibility.json`

Results:

- `cmark`: estimated actual timed GPU launches `5276412`, threshold `100000`
- `cmark_iccm`: estimated actual timed GPU launches `6024133`, threshold
  `100000`
- `status=blocked_launch_count_feasibility`
- `timing_measured=false`
- `gpu_execution_claimed=false`
- `speedup_claimed=false`
- bridge execution was not invoked for these full non-`hello` timing attempts

Interpretation:

- This is a fail-closed feasibility result, not a failed GPU timing result.
- It prevents a misleading full `cmark`-scale run under the current per-pair
  launch model.
- FC-037 remains open; the next useful work is resident multi-cycle launch-count
  collapse or a bounded non-`hello` correctness/timing smoke below the threshold.

## 2026-06-14 Bounded Non-Hello GPU Launch Smoke

Ran a deliberately short one-cycle, two-state smoke through the reviewed VeeR-EL2
sidecar executable for the reviewed non-`hello` state images.

Reports:

- `reports/rtlmeter_veer_el2_dhry_bounded_smoke.json`
- `reports/rtlmeter_veer_el2_cmark_bounded_smoke.json`
- `reports/rtlmeter_veer_el2_cmark_iccm_bounded_smoke.json`

Results:

- all three reports reach `status=observables_emitted`
- `steps=5`
- `sidecar_state_count=2`
- `gpu_kernel_timed_launch_count=7`
- `pair_cycle_fusion.launched=1`
- final observables match across the two GPU states
- `finish_marker_observed=false`, `mcycle=0`, and `minstret=0` for the one-cycle
  smoke

Implementation note:

- The syms-state materializer now skips `program_staging_*` entries outside the
  reviewed flat program-memory window instead of crashing on out-of-range writes.
  The smoke reports record the skipped counts.

Interpretation:

- This proves the reviewed non-`hello` state images can be consumed by the
  sidecar executable and reach the GPU resident pair-cycle fused launch path.
- It is not full RTLMeter correctness, full timing, speedup, or usefulness
  evidence. The run is intentionally too short to reach the CPU program's final
  counters or pass/fail marker.
- The next step remains launch-count collapse or a bounded non-`hello`
  correctness smoke that runs enough cycles to show architectural progress
  without crossing the feasibility threshold.

## 2026-06-14 500-Cycle Non-Hello Bounded Progress

Extended the bounded non-`hello` smoke to 500 sidecar clock cycles for the
reviewed `dhry`, `cmark`, and `cmark_iccm` state images.

Reports:

- `reports/rtlmeter_veer_el2_dhry_bounded_progress_500.json`
- `reports/rtlmeter_veer_el2_cmark_bounded_progress_500.json`
- `reports/rtlmeter_veer_el2_cmark_iccm_bounded_progress_500.json`
- `reports/rtlmeter_veer_el2_non_hello_bounded_progress_summary.json`

Results:

- all three reports reach `status=observables_emitted`
- `gpu_kernel_timed_launch_count=506`
- all three reach `mcycle=499`
- `minstret=321` for `dhry`
- `minstret=342` for `cmark`
- `minstret=418` for `cmark_iccm`
- final observables still match across the two GPU states
- none reaches `finish_marker_observed=true`

Interpretation:

- This proves reviewed non-`hello` program images can execute instructions on
  the GPU sidecar path.
- It is bounded progress evidence only. It is not full RTLMeter correctness,
  full timing, speedup, or usefulness evidence.
- The summary report is generated by the timing tool's bounded-progress mode
  and passes only because all three reports advance `mcycle` and `minstret`,
  match final observables across the two GPU states, and stay below the
  configured launch threshold.
- The next useful step is either resident multi-cycle launch-count collapse or a
  bounded correctness milestone that reaches a reviewed program event below the
  feasibility threshold.

## 2026-06-14 Pair-Cycle Loop Fusion Surface

Implemented and rebuilt the first opt-in launch-count-collapse surface.

Code surfaces:

- `src/passes/vlgpugen.cpp` now emits
  `vl_patch_eval_pair_cycle_loop_batch_gpu`.
- `src/hybrid/run_vl_hybrid.c` accepts
  `RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP` and reports
  `pair_cycle_loop_fusion`.
- `src/tools/veer_el2_sidecar_executable.py` forwards
  `VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP`.
- `src/tools/veer_el2_sidecar_executable.py` also accepts
  `VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1` for bounded
  final-observable-only diagnostics.
- `src/tools/rtlmeter_veer_el2_timing.py` summarizes the new report field.

Validation:

- `make -C src/hybrid --no-print-directory run_vl_hybrid`
- `make -C src/passes --no-print-directory vlgpugen`
- `python3 -m py_compile src/tools/veer_el2_sidecar_executable.py src/tools/rtlmeter_veer_el2_timing.py`
- `python3 -m unittest tests.contract.test_verilator_native_sidecar_make_driver tests.contract.test_rtlmeter_veer_el2_timing -q`

Bounded no-trace diagnostic:

- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_no_trace_500.json`
- `status=observables_emitted`
- `VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1`
- `step_trace_copy_mode=disabled_final_observable_only`
- `pair_cycle_loop_fusion.requested=true`
- `pair_cycle_loop_fusion.available=true`
- `pair_cycle_loop_fusion.kernel_launches=1`
- `pair_cycle_loop_fusion.cycles=500`
- `pair_cycle_loop_fusion.fallback=0`
- `gpu_kernel_timed_launch_count=7`
- final observables match across both GPU states
- `mcycle=499`, `minstret=321`

Full-program event diagnostic:

- `reports/rtlmeter_veer_el2_hello_pair_cycle_loop_no_trace_full_event.json`
- `status=observables_emitted`
- `VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1`
- `step_trace_copy_mode=disabled_final_observable_only`
- `pair_cycle_loop_fusion.kernel_launches=1`
- `pair_cycle_loop_fusion.cycles=727`
- `pair_cycle_loop_fusion.fallback=0`
- `gpu_kernel_timed_launch_count=7`
- `finish_marker_observed=true`
- `cycles=2229`
- `mcycle=726`, `minstret=330`
- final observables match across both GPU states

Non-`hello` 5000-cycle loop-collapse bounded diagnostic:

- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_no_trace_5000.json`
- `reports/rtlmeter_veer_el2_cmark_pair_cycle_loop_no_trace_5000.json`
- `reports/rtlmeter_veer_el2_cmark_iccm_pair_cycle_loop_no_trace_5000.json`
- summary: `reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_5000_summary.json`
- `status=passed` in the summary
- `VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1`
- `clock_cycles=5000`
- all three reports reach `mcycle=4999`
- `minstret`: `dhry=4821`, `cmark=4842`, `cmark_iccm=4918`
- `pair_cycle_loop_fusion.kernel_launches=5`
- `pair_cycle_loop_fusion.cycles=5000`
- `pair_cycle_loop_fusion.fallback=0`
- `gpu_kernel_timed_launch_count=11`
- final observables match across both GPU states
- `speedup_claimed=false`

Interpretation:

- This proves the launch-count collapse path is not limited to tiny `hello`.
- Reviewed non-`hello` preloads can advance 5000 design-CPU cycles with only 11
  actual timed GPU launches instead of thousands of per-step launches.
- This is still bounded progress and timing-diagnostic evidence only: the
  programs do not finish, stdout is not reconstructed, and no speedup/usefulness
  claim is made.

Final-observable stdout compare:

- `reports/rtlmeter_veer_el2_hello_pair_cycle_loop_final_stdout_bridge.json`
- `reports/rtlmeter_veer_el2_hello_pair_cycle_loop_final_stdout_sidecar.json`
- `reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_smoke.json`
- `reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_nstates16.json`
- `VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT=1`
- `normalized_stdout_match=true`
- `cycle_count_match=true`
- `gpu_cycles=2229`
- `step_trace_copy_mode=disabled_final_observable_stdout`
- `stdout_stream_reconstructed=true`
- `pair_cycle_loop_fusion.kernel_launches=1`
- `gpu_kernel_timed_launch_count=7`

Optimized repeated timing:

- `status=passed`
- `total_sample_count=21`
- `sidecar_wall_s_median=0.751716`
- `sidecar_wall_s_batch_medians=[0.733165, 0.812418, 0.705006]`
- `gpu_kernel_ms_total_median=259.037048`
- `pair_cycle_loop_fusion.kernel_launches_median=1.0`
- `pair_cycle_loop_fusion.cycles_median=727.0`
- `pair_cycle_loop_fusion.fallback_median=0.0`
- `step_trace_copy_mode=disabled_final_observable_stdout`
- `sidecar_vs_cpu_parallel_ratio=2.951762`
- `serial_cpu_wall_time_outcome=sidecar_slower_than_serial_cpu`
- `speedup_claimed=false`

Stage-timing smoke:

- `reports/rtlmeter_veer_el2_timing_pair_cycle_loop_stage_timing_smoke.json`
- `VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING=1`
- `status=passed`
- `sidecar_wall_s_median=0.931864`
- `gpu_kernel_ms_total_median=266.998444`
- top `run_vl_hybrid` stages: `after_cuCtxCreate=346.810ms`,
  `after_final_sync=265.491ms`, `after_cuInit=157.850ms`,
  `after_dump_state=8.076ms`, `after_kernel_resolution=7.763ms`,
  `after_cuModuleLoad=5.486ms`

In-process repeat smoke:

- `reports/rtlmeter_veer_el2_timing_pair_cycle_loop_inprocess_repeats_smoke.json`
- `VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS=3`
- `status=passed`
- `gpu_kernel_time_repeat_count_median=3.0`
- `gpu_kernel_ms_total_median=253.576187`
- `gpu_kernel_timed_launch_count_median=7.0`
- `timing_comparison_scope=in_process_hybrid_repeat_diagnostic`
- `cpu_parallel_comparison_valid=false`
- comparison is blocked because multiple GPU sidecar repeats inside one CUDA
  context are not comparable to one CPU RTLMeter run

Interpretation:

- This proves the opt-in loop kernel is actually used and collapses 500
  design-CPU cycles into one loop launch for a bounded `dhry` run.
- The comparable traced 500-cycle bounded progress shape used
  `gpu_kernel_timed_launch_count=506`, so the launch-count problem is reduced
  for this diagnostic.
- The `hello` full-program event gate reaches the same final architectural
  counters and RTLMeter cycle count as the prior stdout/cycles correctness gate
  while reducing the current pair-cycle actual launch shape from `733` to `7`.
- The final-observable stdout mode restores the hello normalized stdout/cycles
  compare while preserving loop-fusion launch collapse. It is reviewed only for
  the known hello program SHA and is not a general stdout trace mechanism.
- The optimized repeated timing gate proves the loop final-observable stdout path
  is stable enough to measure, but it is not the next performance path: it is
  about `1.17x` slower than the current best sixteen-state fused pair-cycle
  sidecar result (`0.641226s`) and about `18.8x` slower than serial CPU.
- The next gate is sidecar load/host overhead reduction or a general device-side
  trace path before non-`hello` stdout claims.
- The stage-timing smoke narrows the overhead target: final state dump is not
  dominant; repeated CUDA init/context setup is. The next performance prototype
  should reuse a persistent CUDA context/runtime process or equivalent resident
  execution authority.
- The in-process repeat prototype now restores VeeR state from a device
  snapshot between repeats and proves that repeat timing can reuse one context,
  but the per-repeat kernel-loop median remains about `253.6ms`. Context reuse
  alone does not create a hidden speedup for tiny `hello`; next work should
  focus on non-`hello` observability or deeper kernel/runtime reduction.

## 2026-06-14 Non-`hello` Loop Chunk And Finish Probe

The non-`hello` bounded loop-collapse path now has a narrow chunk override.
`VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK` is forwarded by the VeeR sidecar
to `RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP_CHUNK`, and `run_vl_hybrid` accepts
values above the old generic `1000` cap only for this loop chunk env.

Reports:

- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_no_trace_5000.json`
- `reports/rtlmeter_veer_el2_cmark_pair_cycle_loop_chunk5000_no_trace_5000.json`
- `reports/rtlmeter_veer_el2_cmark_iccm_pair_cycle_loop_chunk5000_no_trace_5000.json`
- summary:
  `reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_5000_summary.json`
- finish probe:
  `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk50000_final_stdout_50000.json`

Result:

- The three 5000-cycle non-`hello` runs still pass bounded progress.
- `pair_cycle_loop_fusion.kernel_launches` drops from `5` to `1`.
- `gpu_kernel_timed_launch_count` drops from `11` to `7`.
- `pair_cycle_loop_fusion.cycles=5000`, fallback `0`.
- `mcycle=4999` for all three programs.
- `minstret`: `dhry=4821`, `cmark=4842`, `cmark_iccm=4918`.
- Bounded GPU kernel time for `cmark`/`cmark_iccm` drops from about `2.75s` to
  about `1.11s`.
- The 50000-cycle `dhry` finish probe reaches `mcycle=49999` and
  `minstret=49821`, but `finish_marker_observed=false`.
- Non-`hello` final-observable stdout remains blocked by the reviewed
  hello-only SHA gate.

Interpretation:

- The old 1000-cycle loop chunk cap was a real bounded-runtime blocker.
- Raising the chunk improves the bounded non-`hello` launch shape, but it does
  not prove full RTLMeter correctness or speedup.
- The next blocker is finish reachability and program-image completeness for
  non-`hello` preloads. Do not claim non-`hello` stdout or usefulness until
  finish and stdout correctness have stronger evidence.

## 2026-06-14 Non-`hello` Bank Preload Materialization

The program-image completeness blocker was narrowed. The sidecar syms init
materializer now writes reviewed DCCM/ICCM ECC bank preload entries from the
state image into the GPU init blob.

Reports:

- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_no_trace_5000.json`
- `reports/rtlmeter_veer_el2_cmark_pair_cycle_loop_chunk5000_bank_init_no_trace_5000.json`
- `reports/rtlmeter_veer_el2_cmark_iccm_pair_cycle_loop_chunk5000_bank_init_no_trace_5000.json`
- summary:
  `reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_bank_init_5000_summary.json`
- longer finish probes:
  `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk50000_dccm_init_final_stdout_50000.json`
  and
  `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk200000_dccm_init_final_stdout_200000.json`

Result:

- The 5000-cycle bounded gate still passes for `dhry`, `cmark`, and
  `cmark_iccm`.
- All three use one loop kernel, seven actual timed GPU launches, and fallback
  `0`.
- Materialized DCCM/ICCM bank word counts are:
  - `dhry`: `371/0`
  - `cmark`: `0/0`
  - `cmark_iccm`: `342/7674`
- `minstret` at 5000 cycles is now `4421`, `4842`, and `4703`.
- `dhry` 50000-cycle bank-init probe reaches `mcycle=49999`,
  `minstret=47705`, but `finish_marker_observed=false`.
- `dhry` 200000-cycle bank-init probe reaches `mcycle=199999`,
  `minstret=191985`, but `finish_marker_observed=false`.

Interpretation:

- The prior non-`hello` sidecar init state was incomplete for programs with
  reviewed DCCM/ICCM preload sections.
- Bank preload materialization changes architectural progress for `dhry` and
  `cmark_iccm`, so future non-`hello` evidence should use the bank-init reports.
- Finish is still not reached, and non-`hello` stdout remains unreviewed.
- The next useful gate is either CPU-progress comparison at the same `dhry`
  cycle windows or a longer bounded finish probe, not stdout generalization or
  a speedup/usefulness claim.

## 2026-06-14 CPU Completion and Mixed-Program Parallel Baseline

Reports:

- `reports/rtlmeter_cpu_dhry_serial_baseline.json`
- `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_snapshot_mcycle4999.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_snapshot_mcycle49999.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_snapshot_mcycle199999.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_default_iter_snapshot_mcycle4999.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_default_iter_snapshot_mcycle49999.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_default_iter_snapshot_mcycle199999.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_default_iter_snapshot_mcycle4934.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_default_iter_snapshot_mcycle49934.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_default_iter_snapshot_mcycle199934.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_5000.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_50000.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_200000.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_5002.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_50002.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_200002.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_1.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_2.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_3.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_4.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_500.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_502.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_752.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_877.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_1002.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_snapshot_2002.json`
- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_no_trace_500.json`
- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_no_trace_750.json`
- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_no_trace_875.json`
- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_no_trace_1000.json`
- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_no_trace_2000.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_trace_875_1002.json`
- `reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk5000_bank_init_trace_full_1000.json`
- `reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_875_1000.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_trace_pc_d_875_1002.json`
- `reports/rtlmeter_veer_el2_dhry_full_clock_trace_pc_d_1000.json`
- `reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_pc_d_875_1000.json`
- `reports/rtlmeter_veer_el2_cpu_dhry_post_reset_trace_debug_875_1002.json`
- `reports/rtlmeter_veer_el2_dhry_full_clock_trace_debug_1000.json`
- `reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_debug_875_1000.json`

Result:

- Full CPU RTLMeter `VeeR-EL2:default:dhry` finishes at `5984259` cycles.
- The CPU `dhry` serial wall time is `37.240654s`; the matching one-worker
  parallel path is `36.897222s`, and stdout/cycle observables match.
- The 200000-cycle GPU bank-init `dhry` probe therefore covers only about
  `3.34%` of the full CPU completion window.
- `src/tools/rtlmeter_veer_el2_cpu_snapshot.py` now links a generated bounded
  snapshot main against the existing CPU `Vsim` obj_dir. At `mcycle=4999`,
  `49999`, and `199999`, CPU reports `minstret=4473`, `47757`, and `192038`.
- The matching GPU bank-init reports at those `mcycle` points report
  `minstret=4421`, `47705`, and `191985`; raw PC fields differ in all three
  comparisons. At `mcycle=199999`, CPU run wall is `1.226972s` and GPU kernel
  time is `43.9320625s`.
- Repeating CPU snapshots without `+iterations=17500` does not resolve the
  mismatch: CPU-minus-GPU `minstret` deltas are exactly `65` at all three
  windows.
- Sampling CPU at `mcycle-65` gives `mcycle=199934`, `minstret=191990`,
  `pc=0x40000611`, which is close to the long-window GPU `minstret=191985`,
  `pc=0x40000613`, but the short-window PCs still do not align.
- The post-reset cycle-targeted CPU snapshot mode does not resolve the
  mismatch either. `post_reset_posedges=5000`, `50000`, and `200000` stop at
  CPU `mcycle=N-3`; using `N+2` aligns CPU `mcycle` with the GPU windows
  (`4999`, `49999`, `199999`) but leaves CPU `minstret=4486`, `47770`, and
  `192050`, versus GPU `4421`, `47705`, and `191985`, with raw PC mismatch.
- Early CPU reset-release snapshots now show post-reset posedges `1`, `2`, and
  `3` still at `mcycle=0`, `minstret=0`, `pc=0`; posedge `4` reaches
  `mcycle=1`; posedge `500` reaches `mcycle=497`, `minstret=360`,
  `pc=0x400002d1`.
- The CPU snapshot parser now handles snapshot JSON embedded after program
  stdout on the same line; this was required by the 500-cycle snapshot.
- Regenerated bank-init GPU windows now match CPU through 875 cycles when CPU
  is sampled at `post_reset_posedges=N+2`:
  - `500`: both `mcycle=499`, `minstret=362`, `pc=0x400002ce`, `obuf=116`.
  - `750`: both `mcycle=749`, `minstret=579`, `pc=0x40000194`, `obuf=32`.
  - `875`: both `mcycle=874`, `minstret=657`, `pc=0x400001bb`, `obuf=32`.
- The first observed divergence is at `1000` cycles:
  CPU `mcycle=999`, `minstret=746`, `pc=0x40000194`, `obuf=117`;
  GPU `mcycle=999`, `minstret=709`, `pc=0x40000270`, `obuf=32`.
- The divergence grows at `2000` and `5000` cycles, with CPU-minus-GPU
  `minstret` deltas of `60` and `65`.
- The GPU step trace now includes progress observables plus decode/fetch debug
  fields. Comparing the GPU trace with CPU post-reset trace rows maps
  `cpu_post_reset_posedges=gpu_step+3`.
- The latest debug comparison is
  `reports/rtlmeter_veer_el2_dhry_cpu_gpu_trace_compare_debug_875_1000.json`.
- Rows match through `gpu_step=894` / CPU `post_reset_posedges=897`.
- The first exact mismatch is `gpu_step=895` / CPU
  `post_reset_posedges=898`: both sides still have `mcycle=895`,
  `minstret=669`, registered PC `0x4000026e`, `pc_d=0x40000270`,
  `pc_din=0x4000026e`, `instr_d=0x0334c4b3`, and `obuf=32`, but CPU has
  `decode_d=1` / `fetch_stall=0` while GPU has `decode_d=0` /
  `fetch_stall=1`.
- The prior `pc_d`-only split at `gpu_step=896`, registered-PC mismatch at
  `gpu_step=897`, and `minstret` lag at `gpu_step=898` are downstream of GPU
  fetch stall staying asserted one sampled cycle longer.
- The local instruction context is `0x4000026e: c.li x14,5`,
  `0x40000270: lui x15,0xf0043`, and `0x40000274: sw x14,-472(x15)`.
- Mixed CPU runs for `dhry`, `cmark`, and `cmark_iccm` preserve stdout/cycle
  observables and improve from `107.522775s` serial-sum wall to `37.079953s`
  three-worker wall, with `2.899755x` speedup and `0.966585` efficiency.

Interpretation:

- The previous 200000-cycle GPU non-`hello` probe is too short to be finish
  evidence for `dhry`; lack of finish at that window is not by itself a GPU
  correctness failure.
- The same-cycle CPU snapshot workflow is now implemented for three `dhry`
  windows.
- CPU/GPU bounded progress is close but not equivalent: CPU retires 52-53 more
  instructions and the raw PC fields differ. Because the mismatch is already
  present by `mcycle=4999`, the next debug target is initial state, preload,
  reset/clock, or observation-point alignment rather than long-run drift.
- The missing sidecar `+iterations` patch is not sufficient to explain this
  mismatch.
- A simple post-reset observation-count offset is also not sufficient: aligning
  `mcycle` with `post_reset_posedges=N+2` keeps the CPU on its default
  `minstret`/PC path rather than the GPU path.
- The previous suspicion that the initial syms state or reset-release sequence
  was already divergent is now too broad: the bank-init path agrees through 875
  cycles.
- The 875-to-1000 trace gate is now specific enough to move from broad
  state-sampling to auditing `ifu_pmu_fetch_stall` / `dec_i0_decode_d` eval
  ordering or settle fidelity at the first divergent sampled row.
- The follow-up input-dependency trace is
  `reports/rtlmeter_veer_el2_dhry_fetch_inputs_compare_875_1000.json`. At the
  first divergent row, `decode_valid_gate=1` and `fetch_fbwrite=0x038` still
  match, but GPU has `decode_misc2ff=4`, `decode_i0_exublock=1`, and
  `fetch_consume_gate=0` while CPU has `0`, `0`, and `1`. This narrows the next
  fix target to `misc2ff`/exublock and fetch-consume gate update ordering.
- The combined phase-loop implementation now emits
  `launch_sequence=["vl_ico_batch_gpu","vl_eval_loop_batch_gpu"]`; this
  reproduces the native eval outer-loop structure by running act-settle again
  after NBA changes state. It builds and reaches the same bounded `dhry`
  observables as single `vl_eval_batch_gpu`, but it does not fix the
  `gpu_step=895` divergence.
- The AXI input-dependency trace is
  `reports/rtlmeter_veer_el2_dhry_axi_inputs_compare_875_1000.json`, with CPU
  side evidence in
  `reports/rtlmeter_veer_el2_cpu_dhry_axi_inputs_875_1002.json` and GPU side
  evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_axi_inputs_trace_1000/_sidecar/`.
  It shows valid IFU response inputs (`ifu_axi_rvalid/rid/rresp/rdata`) match
  through the divergent window. The only earlier AXI difference is invalid
  `lmem_axi_rdata` filler, so the next debug target is IFU fetch-buffer consume
  generation rather than external instruction response timing.
- The IFU consume/request trace is now
  `reports/rtlmeter_veer_el2_dhry_ifu_consume_compare_875_1000.json`, with CPU
  evidence in
  `reports/rtlmeter_veer_el2_cpu_dhry_ifu_consume_875_1002.json` and GPU
  evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_ifu_consume_trace_1000/_sidecar/`.
  It confirms the first mismatch is still `gpu_step=895` / CPU
  `post_reset_posedges=898`. At `gpu_step=894` the added IFU fields match. At
  `gpu_step=895`, request/response-side equivalents and miss-state fields still
  match (`tb_ifu_axi_arready`, `ifu_bus_cmd_valid`,
  `ifu_bus_rd_addr_count`, `ifu_fetch_addr_f`, `ifu_pmp_addr`,
  `tb_ifu_axi_rvalid/rid/rdata`, `ifu_ifc_miss_f`, `ifu_mem_miss_f`,
  `ifu_mem_miss_state`), while `ifu_ifc_fetch_req_bf` diverges
  (`CPU=1`, `GPU=0`) and `ifu_ifc_fb_write_ns` diverges (`CPU=4`, `GPU=8`).
  The follow-up ALN consume trace is
  `reports/rtlmeter_veer_el2_dhry_aln_consume_compare_875_1000.json`, with CPU
  evidence in
  `reports/rtlmeter_veer_el2_cpu_dhry_aln_consume_875_1002.json` and GPU
  evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_aln_consume_trace_1000/_sidecar/`.
  It confirms `ifu_aln_bundle2` and `ifu_ifc_fetch_ready` still match at the
  first functional mismatch, but GPU keeps `ifu_aln_sf0val=3` and does not
  assert `ifu_aln_shift_f1_f0` / `ifu_aln_shift_f2_f1`, while CPU has
  `ifu_aln_sf0val=0` and both shifts asserted. The next fix target is ALN
  sf/shift next-state or state-update ordering feeding IFC fetch-buffer
  consume/request, not the IFC `fb_write_ns` table output alone.
  Generated-code audit points:
  - ALN `bundle1ff` / `bundle2ff` `dout` commits in
    `Vsim___024root___act_sequent__TOP__0`.
  - ALN `bundle1ff` / `bundle2ff` `din`, `sf0val`, `sf1val`,
    `shift_f1_f0`, `shift_f2_f0`, and `shift_f2_f1` compute in
    `Vsim___024root___nba_comb__TOP__18`.
  - The next trace should distinguish stale ALN flop state from stale NBA-comb
    recomputation by adding ALN `bundle1ff`/`bundle2ff` DIN, sf next-state
    contributors, `fetch_to_f0/f1/f2`, `ifvalid`, `ic_fetch_val_f`,
    `consume_fb0/1`, `ifu_fb_consume1/2`, `exu_flush_final`, and
    `dec_tlu_flush_noredir_r`.
  The implemented follow-up trace is
  `reports/rtlmeter_veer_el2_dhry_aln_trigger_compare_875_1000.json`, with CPU
  evidence in `reports/rtlmeter_veer_el2_cpu_dhry_aln_trigger_875_1002.json`
  and GPU evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_aln_trigger_trace_1000/_sidecar/`.
  It shows committed ALN flops still match at `gpu_step=895`
  (`bundle1=0`, `bundle2=63`), while GPU next-state outputs are stale:
  `bundle1_din=0` vs CPU `8`, `bundle2_din=63` vs CPU `15`,
  `sf0val=3` vs CPU `0`, and both shift outputs deasserted. Post-step
  `root_act_triggered` and `root_nba_triggered` are `0` on both sides, so
  trigger mask differences are not visible in the post-step trace. The next
  implementation target is `Vsim___024root___nba_comb__TOP__18` recompute
  ordering or a phase-local ALN dependency recompute after active/sequent
  updates.
  The focused post-NBA recompute experiment is
  `reports/rtlmeter_veer_el2_dhry_post_nba_recompute_compare_875_1000.json`.
  It adds the diagnostic vlgpugen flag `--veer-aln-post-nba-recompute`, calls
  `TOP__16`, `TOP__17`, and `TOP__18` after a changed NBA phase, and reruns the
  bounded `dhry` trace. The first mismatch still remains `gpu_step=895` / CPU
  post-reset `898` with the same ALN DIN/sf/shift and downstream IFU consume
  differences. The default artifact was rebuilt without that diagnostic
  recompute. This rejects a simple missing post-NBA `TOP__18` call; next inspect
  the immediate inputs read by `TOP__18` or the lowered ordering inside
  `TOP__18`.
  That direct-input trace is now
  `reports/rtlmeter_veer_el2_dhry_top18_inputs_compare_875_1000.json`, with CPU
  evidence in `reports/rtlmeter_veer_el2_cpu_dhry_top18_inputs_875_1002.json`
  and GPU evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_top18_inputs_trace_1000/_sidecar/`.
  It adds `TOP__18`-adjacent input fields and keeps the trace width at 82
  fields, below `MAX_STEP_TRACE_FIELDS=96`. The first functional mismatch still
  remains `gpu_step=895` / CPU post-reset `898`, but the new split shows
  `bundle2`, `aligndata`, `alignfromf1`, brdata enable, `ic_hit_f`,
  ECC/error, and freeff inputs match at that row. The new upstream mismatch is
  `ifu_pmu_instr_aligned` (`GPU=0`, `CPU=1`). Since `TOP__17` computes it from
  matching `bundle2` and divergent `dec_i0_decode_d`, the next target is
  `dec_i0_decode_d` / `i0_exublock_d` generation or lowered ordering before
  `TOP__17/18`, not another ALN-only recompute.
- The exublock-input trace now exists as
  `reports/rtlmeter_veer_el2_dhry_exublock_inputs_compare_875_1000.json`, with
  CPU evidence in
  `reports/rtlmeter_veer_el2_cpu_dhry_exublock_inputs_875_1002.json` and GPU
  evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_exublock_inputs_trace_1000/_sidecar/`.
  It reaches the current trace cap exactly: 96 fields without `step`. The first
  functional mismatch is unchanged at `gpu_step=895` / CPU post-reset `898`.
  The added `i0_exublock_d` source candidates (`misc1ff`, halt, presync/LSU
  idle, nonblock-load, rs enable, hazard, e1/r_d/wb flops) match at that row and
  do not explain the split. The visible upstream state difference remains
  `decode_misc2ff=4` on GPU versus `0` on CPU, with
  `decode_i0_exublock=1` versus `0`.
  Generated-code inspection narrows `misc2ff[2]` to either `i0_div_decode_d` or
  a self-hold of old `misc2ff[2]` while `exu_div_wren=0` and
  `dec_div_cancel=0`. The gated `misc2ff` DIN is root-visible, so the next trace
  can stay within the current runtime surface by replacing matched low-value
  exublock columns with `misc2ff` DIN, `exu_div_wren`, `dec_div_cancel`,
  `dec_debug_valid_d`, `exu_flush_final`, and selected LSU neighboring-bit
  sources.
- The `misc2ff` DIN trace is now recorded in
  `reports/rtlmeter_veer_el2_dhry_misc2ff_inputs_compare_875_1000.json`, with
  CPU evidence in
  `reports/rtlmeter_veer_el2_cpu_dhry_misc2ff_inputs_875_1002.json` and GPU
  evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_misc2ff_inputs_trace_1000/_sidecar/`.
  It keeps the 96-field runtime cap and moves the first functional split to
  `gpu_step=894` / CPU post-reset `897`: GPU has `decode_misc2ff_din=4` while
  CPU has `0`, because CPU asserts `exu_div_wren=1` and GPU keeps it `0`.
- The direct divider-input trace is now recorded in
  `reports/rtlmeter_veer_el2_dhry_div_inputs_compare_875_1000.json`, with CPU
  evidence in `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_1002.json` and
  GPU evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_div_inputs_trace_1000/_sidecar/`.
  It moves the earliest focused split to `gpu_step=890` / CPU post-reset `893`,
  where `exu_div_i_misc_ff_din` and `exu_div_shortq` already differ. The next
  concrete debug gate is therefore divider `shortq` / `i_misc_ff` update
  ordering and the arithmetic inputs feeding those fields.
- The deeper divider trace is now recorded in
  `reports/rtlmeter_veer_el2_dhry_div_deep_compare_875_1000.json`, with CPU
  evidence in `reports/rtlmeter_veer_el2_cpu_dhry_div_deep_875_1002.json` and
  GPU evidence under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_div_deep_trace_1000/_sidecar/`.
  It keeps the first focused split at `gpu_step=890` / CPU post-reset `893`,
  but narrows it to `exu_div_dw_shortq_raw`, `exu_div_shortq`, and
  `exu_div_i_misc_ff_din`. At that row, `exu_div_valid_in`,
  `exu_div_running_state`, `exu_div_i_misc_ff`, `exu_div_shortq_enable`,
  `exu_div_quotient_raw`, `exu_div_quotient_new`, and `exu_div_i_b_ff` match.
  Generated C++/IR inspection shows `dw_shortq_raw` is assigned in
  `___nba_sequent__TOP__8`, `shortq` is assigned in
  `___nba_sequent__TOP__9`, and the GPU IR still calls TOP__8 before TOP__9.
  The follow-up showed this was not a divider offset/type or TOP__8/TOP__9
  ordering bug. `program.hex` contains a Dhrystone control record at
  `@10000000` with value `1000`, while the generated flat byte memory only
  modeled `0x80000000..0x8000ffff`. Out-of-window `$readmemh` writes reused the
  default byte reference and polluted invalid reads to `0x0a`; the GPU then read
  `0x0a0a0a0a...` instead of `1000`, feeding `tb_lmem_axi_rdata`,
  `exu_div_a_ff`, `exu_div_dw_shortq_raw`, `exu_div_shortq`, and
  `exu_div_i_misc_ff_din`.
- The flat-memory fix separates unmapped writes from default reads and adds a
  16-byte `0x10000000` control window after the 64 KiB program window in the
  syms-state image. The rebuilt GPU artifact records `syms_storage_size=433536`.
  The post-fix GPU trace is under
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_trace_1000/_sidecar/`.
  The compare report
  `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_1000.json` maps CPU
  rows as `cpu_post_reset_posedges=gpu_step+3` and now reports `status=match`
  for GPU steps `875..999`: 125 aligned rows, 62 compared fields, and zero
  mismatched field observations. At the old failing row (`gpu_step=890` / CPU
  post-reset `893`), `tb_lmem_axi_rdata`, `exu_div_a_ff`,
  `exu_div_dw_shortq_raw`, `exu_div_shortq`, `exu_div_i_misc_ff_din`,
  `exu_div_i_b_ff`, `exu_div_q_ff`, and `exu_div_r_ff` match.
  `pc_din` is excluded because the earlier ad-hoc CPU counterpart was invalid.
- The fixed flat-memory layout now also passes a longer same-window `dhry`
  compare. GPU trace:
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_trace_2000/_sidecar/veer_el2_step_trace.csv`.
  CPU report:
  `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_2002.json`.
  Compare report:
  `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_2000.json`.
  Result: `status=match`, GPU steps `875..1999`, 1125 aligned rows, 62
  compared fields, and zero mismatched field observations with CPU rows mapped
  as `cpu_post_reset_posedges=gpu_step+3`.
- The same fixed layout now reaches the previous 5000-cycle bounded progress
  milestone with same-window trace equivalence. GPU trace:
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_trace_5000/_sidecar/veer_el2_step_trace.csv`.
  CPU report:
  `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_5002.json`.
  Compare report:
  `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_5000.json`.
  Result: `status=match`, GPU steps `875..4999`, 4125 aligned rows, 62
  compared fields, and zero mismatched field observations.
- The latest same-window extension reaches 50000 cycles. GPU trace:
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_trace_50000/_sidecar/veer_el2_step_trace.csv`.
  CPU report:
  `reports/rtlmeter_veer_el2_cpu_dhry_div_inputs_875_50002.json`.
  Compare report:
  `reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_50000.json`.
  Result: `status=match`, GPU steps `875..49999`, 49125 aligned rows, 62
  compared fields, and zero mismatched field observations. The earlier 50k
  raw PC/minstret mismatch is therefore superseded for these traced fields by
  the fixed flat-memory run.
- Automatic trace-equivalence summary:
  `reports/rtlmeter_veer_el2_dhry_lmem_control_trace_equivalence_875_50000.json`.
  Result: `status=passed`, `same_window_trace_equivalence_evidence=true`,
  thresholds 49125 aligned rows and 62 compared fields, `timing_measured=false`,
  `speedup_claimed=false`, and `usefulness_claimed=false`.
- First stdout-safe longer-progress gate:
  `reports/rtlmeter_veer_el2_dhry_lmem_control_stdout_safe_progress_100000_loopfix.json`.
  It summarizes
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_loop_notrace_100000_loopfix/_sidecar/veer_el2_sidecar_executable_report.json`.
  Result: `status=passed`, `mcycle=99999`, `minstret=95864`,
  `finish_marker_observed=false`, `step_trace_disabled=true`,
  `final_observable_stdout_requested=true`, `speedup_claimed=false`, and
  `usefulness_claimed=false`.
- Phase-aware pair-cycle loop diagnostic:
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_loop_notrace_10_phaseaware_loop/_sidecar/veer_el2_sidecar_executable_report.json`,
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_loop_notrace_100_phaseaware_loop/_sidecar/veer_el2_sidecar_executable_report.json`,
  and
  `artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_loop_notrace_1000_phaseaware_loop/_sidecar/veer_el2_sidecar_executable_report.json`.
  Result: loop and resident-fallback GPU dumps match byte-for-byte at 10, 100,
  and 1000 cycles. At 1000 cycles the phase-aware loop records
  `pair_cycle_loop_fusion.kernel_launches=1`, `cycles=1000`, `fallback=0`, and
  reduces actual timed launches from `6009` to `10`; GPU kernel total moves from
  `272.482300ms` fallback to `238.399490ms` loop. Wrapper wall is not yet a
  robust win, so this remains bounded progress evidence only.
- 100000-cycle phase-aware bounded-progress summary:
  `reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_progress.json`.
  Result: `status=passed`, one loop kernel, `10` actual timed launches,
  `mcycle=99999`, `minstret=95864`, `finish_marker_observed=false`, and
  `gpu_kernel_time_ms_total=22404.386719`.
- Bounded projection negative-usefulness summary:
  `reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_negative_projection.json`.
  Result: `status=negative_usefulness_projected`,
  `negative_usefulness_decision=true`, CPU RTLMeter cycles `5984259`, projected
  GPU-kernel time `1340.749936s`, CPU serial wall `37.240654s`, and projected
  GPU-kernel/CPU-serial ratio `36.002320`.
- Current blocker: full non-`hello` `dhry` finish/stdout and fair CPU-vs-GPU
  timing remain unproven, but the current bounded GPU path now has a reviewed
  negative usefulness decision. Keep speedup/usefulness claims disabled; full
  finish/stdout is future correctness work unless a different GPU path is
  introduced.
- The design-CPU parallel SIM idea is valid for CPU throughput by running
  different programs as separate RTLMeter processes.
- Mixed GPU state preload now has a 100000-cycle bounded projection:
  `reports/rtlmeter_veer_el2_mixed_state_dhry_cmark_cmark_iccm_100000_projection.json`.
  It uses distinct per-state syms init images for `state0=dhry`,
  `state1=cmark`, and `state2=cmark_iccm`, uploads the concatenated
  `storage_size*nstates` init blob through the existing `run_vl_hybrid` total
  init-file branch, and reuses the same generated GPU kernels. Result:
  `status=mixed_state_gpu_negative_projection`, all three states reach
  `mcycle=99999`, `gpu_actual_timed_launches=10`,
  `gpu_kernel_time_ms_total=22735.765625`, CPU mixed baseline
  `parallel_wall_s=37.079953`, projected GPU-kernel time to CPU max cycles
  `1369.986587s`, projected GPU-kernel/CPU-parallel ratio `36.946826`,
  `speedup_claimed=false`, and `usefulness_claimed=false`.
- This does not prove GPU usefulness. The current bounded `dhry` GPU path is
  now has loop-collapse execution and bounded equivalence evidence, but the
  100000-cycle phase-aware no-trace gate still does not finish and the measured
  projection to CPU RTLMeter cycles is about `36.00x` slower than CPU serial by
  GPU-kernel time alone. The concrete gate is now recording that negative
  decision on FC-037 / #2 and deciding whether to stop this current GPU path or
  require a materially different implementation with stronger per-state
  finish/stdout observability, not another loop-eligibility probe.

Next gate task breakdown:

1. Stop treating the current mixed-state GPU path as a promising optimization:
   the 100000-cycle bounded projection is negative versus CPU mixed parallel.
2. Do not add more loop-eligibility work to this implementation unless a new
   measurement disproves the current projection.
3. If GPU work continues, define the materially different implementation first:
   expected launch-count reduction mechanism, per-state finish/stdout
   observability, and the exact CPU mixed parallel baseline comparison.
4. Keep FC-037 / GitHub #2 as the owner for this RTLMeter timing/usefulness lane;
   create a new issue only if the next implementation direction leaves that
   scope.
5. Use the mixed-state GPU/CPU summary JSON fields `recommended_action` and
   `materially_different_definition_gate` as the machine-readable
   stop/different-path gate before more GPU performance work.

Definition gate before more GPU implementation work:

- Resident execution requirement: the candidate must collapse many design-CPU
  cycles for each state into one bounded device-side operation or a small fixed
  number of device-side operations. Pair-cycle launch reduction alone is not a
  new path unless it removes the per-cycle host launch shape for non-`hello`
  programs.
- Observable contract requirement: the candidate must define per-state
  finish-marker handling, stdout/mailbox extraction, RTLMeter cycle count
  reporting, and final architectural counter comparison for mixed programs.
  State-0-only stdout is insufficient for mixed `dhry` / `cmark` /
  `cmark_iccm` usefulness.
- Superstep requirement: the candidate must define the entry state, device-side
  loop bound, legal exit reasons, unsupported side effects, and host-sync
  points for each resident region. Host interaction at every design-CPU cycle
  keeps the implementation in the current rejected path.
- GEM-like / data-parallel lowering requirement: if the next proposal is an
  LLVM pass, it must name the regular hot helper or memory operation family to
  lower into a data-parallel kernel. Generic eval control-flow reshaping,
  branch scheduling, or more inline policy tuning is not enough after the
  current negative projection.
- Comparison requirement: any usefulness attempt must compare against
  `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json` or a regenerated
  equivalent mixed-program CPU-parallel baseline. Serial-only comparison and
  bounded-progress-only reports cannot support a GPU usefulness claim.

If these requirements are not met, the correct next action is to stop the
current GPU path for performance and leave full non-`hello` finish/stdout as a
future correctness task.

## Acceptance

- Timing is reported only when FC-064 direct sidecar stdout/cycles correctness
  passes for the VeeR-EL2 RTLMeter seed.
- CPU timing, GPU wall time, and GPU kernel time are separate; RTLMeter metrics are preserved.
- Serial CPU, CPU-parallel, GPU wall, and GPU kernel diagnostic fields are
  separate; the headline comparison states which baseline is being used.
- CPU-parallel runs use isolated RTLMeter work roots and preserve normalized
  stdout/cycle equivalence across all passing workers.
- GPU-vs-CPU-parallel comparison is valid only when sidecar state count matches
  the CPU duplicate case count, clock/reset patches drive all GPU states, and
  final observables validate across all launched GPU states.
- Any acceleration statement cites repeated multi-batch measurement methodology
  (batch count, samples per batch, central tendency), not a single run.
- Generated timing evidence is regenerable from documented commands and lives
  under `reports/`; canonical pointers and summarized current state are mirrored
  in `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, and README.
- Slowdown and no-change cases are reported honestly.
- After the mixed-state negative projection, further GPU implementation work is
  accepted only when the definition gate above names resident execution,
  per-state observability, superstep boundaries, any GEM-like lowering
  candidate, and the mixed-program CPU-parallel comparison floor.
- The mixed-state GPU/CPU summary emits a machine-readable recommendation and
  materially-different definition gate so automation does not continue the
  current path from a negative projection by default.
- The RTLMeter hybrid advantage aggregate is regenerable with
  `src/tools/rtlmeter_hybrid_advantage.py` and keeps favorable/unfavorable
  counts separate from timing claims. The current generated summary reports
  `cpu_parallel_favorable=1`, `gpu_sidecar_unfavorable=4`,
  `gpu_sidecar_favorable=0`, `launch_feasibility_blocked=1`, and
  `gpu_bounded_progress=1`, with
  `prefer_cpu_parallel_control_with_gpu_bounded_batch_probes` as the current
  hybrid action.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_hybrid_advantage -q
python3 -m unittest tests.contract.test_rtlmeter_veer_el2_timing -q
python3 -m unittest tests.contract.test_rtlmeter_cpu_gpu_compare_integration -q
python3 -m unittest tests.contract.test_rtlmeter_cpu_parallel_baseline -q
```

Add or extend a timing-methodology contract test that is skipped or fail-closed
when real Verilator or the GPU sidecar is unavailable, so the suite stays green
in a non-GPU environment.

## Non-Goals

- No acceleration claim without FC-064 direct VeeR stdout/cycles correctness and
  repeated multi-batch timing.
- No single-run speedup headline.
- No broad RTLMeter acceleration claim; this is seed-scoped only.
- No automatic GPU allocation; debug JSON stays debug, not the runtime ABI.
