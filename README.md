# GPU Toggle Coverage Minimal

Minimal extraction of the Verilator LLVM hybrid-runtime work.

## Goal

Build a small, reproducible baseline for:

```text
generalize_verilator_llvm_hybrid_runtime_for_high_throughput_regression_and_coverage
```

The first seed target is `tlul_fifo_sync`. This repository intentionally does not carry historical `work/`, `output/`, `obj_dir/`, or broad campaign artifacts from the exploration repository.

## First Success Metric

```text
from_clean_checkout:
  build: pass
  run_seed: pass
  compare_seed: pass
  status_report: pass

surface_limits:
  repo_root_python_file_count: 0
  generated_artifacts_tracked: 0
  active_targets: 1
  active_docs_max: 3
```

## Current State

See:

- `docs/status.md`
- `docs/roadmap.md`
- `config/selection.json`

## Two-Seed Claim Boundary

weakest_point:
  resident patch schedule evidence now includes one non-TL-UL seed, but it does
  not prove broad target-breadth, full RTL application throughput, or raw byte
  equality.

| Seed | Status | Accepted claim | Key ratio | Non-claim |
| --- | --- | --- | --- | --- |
| `tlul_fifo_sync` | CPU/GPU repeated-step comparison passes | GPU beats a single-process CPU repeated-`eval_step` loop for `nstates=512`, `steps=[1,8,32]` | `2.56x`, `5.30x`, `2.72x` | Not full timed-cycle equivalence or non-TL-UL generality |
| `tlul_sink` | CPU/GPU repeated-step comparison passes | GPU beats a single-process CPU repeated-`eval_step` loop for `nstates=512`, `steps=[1,8,32]` | `5.22x`, `2.70x`, `6.09x` | Not full timed-cycle equivalence or non-TL-UL generality |

Resident changing-input patch schedule boundary:

| Seed | Status | Accepted claim | Key ratio | Non-claim |
| --- | --- | --- | --- | --- |
| `tlul_fifo_sync` | Patch schedule GPU/CPU gate passes | GPU resident patch schedule beats a single-process CPU changing-input loop for `nstates=512`, `logical_patch_steps=32` | `3.116x` | Not non-TL-UL breadth |
| `tlul_sink` | Patch schedule GPU/CPU gate passes | GPU resident patch schedule beats a single-process CPU changing-input loop for `nstates=512`, `logical_patch_steps=32` | `2.002x` | Not non-TL-UL breadth |
| `veer_el2` | Patch schedule GPU/CPU gate passes | GPU resident patch schedule beats a single-process CPU changing-input loop for `nstates=512`, `logical_patch_steps=32` | `2.849x` | Not broad VeeR family support or full RTL application throughput |

## XuanTie-E902 Resident Runtime Boundary

weakest_point:
  this is one non-TL-UL wrapper with explicit resident mode. It does not prove
  broad non-TL-UL generality, timed-cycle equivalence, or resident patch-script
  semantics.

| Target | Status | Accepted claim | Key ratio | Non-claim |
| --- | --- | --- | --- | --- |
| `xuantie_e902` | Explicit resident mode passes | GPU resident mode beats a single-process CPU repeated-`eval_step` loop for `nstates=128`, `steps=64` | `1.2076x` | Not broad XuanTie family support or resident patch-script semantics |
| `veer_el2` | Larger resident gate passes | GPU resident mode beats a single-process CPU repeated-`eval_step` loop for `nstates=[256,512]`, `steps=64` | `2.37x`, `2.46x` | Not broad VeeR family support, full RTL application throughput, or resident patch-script semantics |

Next resident breadth candidate:

```text
weakest_point:
  VeeR-EL2 has a bounded larger-resident GPU win, but the claim is limited to
  one wrapper and two measured shapes.

selected:
  target: veer_el2
  launch_template: config/slice_launch_templates/veer_el2.json
  gpu_gate: config/scaling_gates/veer_el2_resident_workload.json
  cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_resident_workload.json
  asset_boundary: third_party/rtlmeter/designs/VeeR-EL2
  old_repo_evidence:
    - output/family_readiness/veer_el2_gpu_toggle_readiness.md
    - output/design_scope_expansion_packet.json

next:
  define_resident_patch_script_semantics
```

Resident boundary:

```text
included:
  - XuanTie-E902 source/test boundary copied into the minimal repo
  - normalized one-state CPU/GPU final-state equivalence
  - conservative and large-workload CPU/GPU baselines
  - explicit --resident-steps / RUN_VL_HYBRID_RESIDENT_STEPS=1 runtime path
  - matching CPU exact-loop comparison for the resident gate

excluded:
  - broad non-TL-UL target generality
  - XuanTie family support beyond E902
  - resident --patch / --patch-script semantics
  - full timed-cycle CPU/GPU equivalence
```

Package boundary:

```text
included:
  - minimal Verilator -> LLVM -> CUDA build path
  - two TL-UL seed GPU repeated-step gates
  - two TL-UL seed single-process CPU repeated-eval comparison gates
  - generated artifacts ignored under artifacts/ and reports/

excluded:
  - broad historical campaign artifacts
  - non-TL-UL target breadth
  - full RTL application throughput claims
  - raw byte equality claims
```

## Minimal CPU/GPU Repro Flow

weakest_point:
  raw byte equality is not the acceptance criterion. Verilator runtime/internal
  fields can differ between host C++ execution and GPU storage execution, so the
  supported correctness claim is normalized final-state equivalence for
  comparable design state / top-level IO fields.

prerequisites:
  - Verilator 5.x with timing coroutine support
  - LLVM/Clang 18 tools available as `llvm-config-18`, `clang++-18`, and `opt-18`
  - CUDA Driver API headers and `libcuda.so`
  - an NVIDIA GPU visible to the CUDA driver

from_clean_checkout:
  1. Build the LLVM pass binaries.

```bash
make -C src/passes
```

  2. Generate the Verilator object directory for the first seed.

```bash
verilator --cc --timing -Wno-fatal \
  -Ithird_party/rtlmeter/designs/OpenTitan/src \
  --Mdir artifacts/tlul_fifo_sync_obj_dir \
  --top-module tlul_fifo_sync_gpu_cov_tb \
  third_party/rtlmeter/designs/OpenTitan/src/prim_assert_dummy_macros.svh \
  third_party/rtlmeter/designs/OpenTitan/src/prim_assert.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_mubi_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_secded_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_util_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/top_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_count_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_generic_flop.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_flop.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_count.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_fifo_sync_cnt.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_fifo_sync.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_fifo_sync.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_fifo_sync_gpu_cov_tb.sv
```

  3. Build the GPU cubin.

```bash
PYTHONPATH=src/tools python3 src/tools/build_vl_gpu.py \
  artifacts/tlul_fifo_sync_obj_dir \
  --sm sm_89 \
  --ptxas-opt-level 0
```

  4. Build host-side runtimes.

```bash
make -C src/hybrid run_vl_hybrid
make -C src/hybrid tlul_slice_host_probe
```

  5. Produce the CPU reference state dump.

```bash
./artifacts/tlul_fifo_sync_obj_dir/tlul_slice_host_probe \
  --reset-cycles 4 \
  --post-reset-cycles 2 \
  --state-out artifacts/tlul_fifo_sync_obj_dir/minimal_cpu_reference_state.bin \
  > reports/minimal_cpu_reference_probe.json
```

  6. Run the GPU from the CPU reference init-state.

```bash
PYTHONPATH=src/tools python3 src/tools/run_vl_hybrid.py \
  --mdir artifacts/tlul_fifo_sync_obj_dir \
  --nstates 1 \
  --steps 1 \
  --init-state artifacts/tlul_fifo_sync_obj_dir/minimal_cpu_reference_state.bin \
  --sanitize-host-only-internals \
  --dump-state artifacts/tlul_fifo_sync_obj_dir/minimal_gpu_from_cpu_init_state.bin
```

  7. Compare CPU and GPU final state with the normalized policy.

```bash
PYTHONPATH=src/tools python3 src/tools/compare_vl_hybrid_modes.py \
  artifacts/tlul_fifo_sync_obj_dir \
  --compare-dumps \
  artifacts/tlul_fifo_sync_obj_dir/minimal_cpu_reference_state.bin \
  artifacts/tlul_fifo_sync_obj_dir/minimal_gpu_from_cpu_init_state.bin \
  --reference-label cpu_reference \
  --candidate-label gpu_from_cpu_init \
  --acceptance-policy normalized_final_state_equivalence \
  --json-out reports/minimal_cpu_vs_gpu_from_cpu_init_compare.json
```

expected_result:

```text
selected_acceptance_policy.passed: true
acceptance_candidates.design_state_mismatch_bytes: 0
acceptance_candidates.top_level_io_mismatch_bytes: 0
acceptance_candidates.other_mismatch_bytes: 0
raw match: false, because Verilator internal bytes may differ
```

artifact_policy:
  generated outputs under `artifacts/` and `reports/` are reproducible and are
  not tracked as source. Keep hand-authored decisions in `config/` or `docs/`.

## Generated Artifact Policy

```text
artifacts/:
  purpose: generated build/runtime outputs
  examples:
    - Verilator obj_dir files
    - cubin / ptx / LLVM IR outputs
    - generated host-probe binaries
    - raw state dumps
  do_not_store:
    - hand-authored source
    - operational decisions
    - unique notes that cannot be regenerated

reports/:
  purpose: generated summaries from documented commands
  examples:
    - CPU probe JSON output
    - GPU run summary
    - CPU/GPU compare JSON
  do_not_store:
    - canonical roadmap state
    - hand-authored status decisions
    - clone-local absolute paths

canonical_state:
  - config/selection.json
  - docs/status.md
  - docs/roadmap.md
  - README.md
```

Both `artifacts/` and `reports/` keep only their `.gitignore` files in source.

## Scaling Gate

Run the selected `tlul_fifo_sync` scaling gate after the repro flow has produced
`artifacts/tlul_fifo_sync_obj_dir/vl_batch_gpu.meta.json` and the hybrid host
runtime.

```bash
PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py
```

The command reads `config/scaling_gates/tlul_fifo_sync.json` and writes the
generated report to `reports/tlul_fifo_sync_scaling_validation.json`.

Run the CPU baseline timing gate for the same seed:

```bash
PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py
```

The CPU baseline report is generated at
`reports/tlul_fifo_sync_cpu_baseline.json`. It is timing context only; it is not
an exact `nstates > 1` CPU/GPU speedup claim.

Run the conservative CPU process-per-state multi-state baseline:

```bash
PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py --multi-state
```

The multi-state CPU baseline report is generated at
`reports/tlul_fifo_sync_cpu_multistate_baseline.json`. It compares the same
`nstates` shapes as the GPU scaling gate when
`reports/tlul_fifo_sync_scaling_validation.json` is present. Treat the ratio as
a conservative process-per-state comparison, not an exact single-process CPU
speedup claim.

Run the single-process CPU loop baseline:

```bash
make -C src/hybrid tlul_slice_host_probe
PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py --exact-loop
```

The exact-loop CPU baseline report is generated at
`reports/tlul_fifo_sync_cpu_exact_loop_baseline.json`. This removes one process
launch per state from the CPU side, but it is still scoped to the small
`tlul_fifo_sync` workload and should not be generalized to full RTL workloads.

Run the larger `nstates` workload gate:

```bash
PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py \
  --gate config/scaling_gates/tlul_fifo_sync_large_workload.json \
  --json-out reports/tlul_fifo_sync_large_workload_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py \
  --exact-loop \
  --gate config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_large_workload.json \
  --json-out reports/tlul_fifo_sync_cpu_exact_loop_large_workload.json \
  --gpu-scaling-report reports/tlul_fifo_sync_large_workload_scaling.json
```

This gate keeps `steps=1` and increases only `nstates`. The current accepted
claim is limited to this seed and gate shape.

Run the repeated-step workload gate:

```bash
PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py \
  --gate config/scaling_gates/tlul_fifo_sync_repeated_steps.json \
  --json-out reports/tlul_fifo_sync_repeated_steps_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py \
  --exact-loop \
  --gate config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_repeated_steps.json \
  --json-out reports/tlul_fifo_sync_cpu_exact_loop_repeated_steps.json \
  --gpu-scaling-report reports/tlul_fifo_sync_repeated_steps_scaling.json
```

This gate compares GPU repeated kernel launches with CPU repeated `eval_step`
calls after initialization. It is still scoped to `tlul_fifo_sync`.

## Second Seed

The second active seed is `tlul_sink`. Its repeated-step gate validates both GPU
execution and a single-process CPU repeated-`eval_step` comparison. Claims remain
limited to two OpenTitan TL-UL seeds.

```bash
verilator --cc --timing -Wno-fatal \
  -Ithird_party/rtlmeter/designs/OpenTitan/src \
  --Mdir artifacts/tlul_sink_obj_dir \
  --top-module tlul_sink_gpu_cov_tb \
  third_party/rtlmeter/designs/OpenTitan/src/prim_assert_dummy_macros.svh \
  third_party/rtlmeter/designs/OpenTitan/src/prim_assert.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_mubi_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_secded_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_util_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/top_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_pkg.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_secded_inv_64_57_enc.sv \
  third_party/rtlmeter/designs/OpenTitan/src/prim_secded_inv_39_32_enc.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_data_integ_enc.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_rsp_intg_gen.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_err.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_sink.sv \
  third_party/rtlmeter/designs/OpenTitan/src/tlul_sink_gpu_cov_tb.sv

PYTHONPATH=src/tools python3 src/tools/build_vl_gpu.py \
  artifacts/tlul_sink_obj_dir \
  --sm sm_89 \
  --ptxas-opt-level 0

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py \
  --gate config/scaling_gates/tlul_sink_repeated_steps.json \
  --mdir artifacts/tlul_sink_obj_dir \
  --json-out reports/tlul_sink_repeated_steps_scaling.json

make -C src/hybrid tlul_sink_host_probe

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py \
  --exact-loop \
  --mdir artifacts/tlul_sink_obj_dir \
  --gate config/scaling_gates/tlul_sink_cpu_exact_loop_repeated_steps.json \
  --json-out reports/tlul_sink_cpu_exact_loop_repeated_steps.json \
  --gpu-scaling-report reports/tlul_sink_repeated_steps_scaling.json
```

## XuanTie-E902 Breadth Smoke

weakest_point:
  this is a first non-TL-UL E902 smoke, not a throughput claim or full
  XuanTie family support claim.

```text
status:
  verilator_obj_dir: pass_with_warnings
  gpu_cubin: pass
  one_state_gpu_smoke: pass
  cpu_reference_dump: pass
  normalized_final_state_equivalence: pass
  conservative_gpu_scaling_gate: pass
  conservative_cpu_gpu_baseline: pass_cpu_favorable
  large_workload_gpu_gate: pass
  large_workload_cpu_baseline_gate: pass_cpu_favorable_but_gap_narrowed
  best_large_workload_gpu_over_cpu_ratio: 0.8625
  memory_resident_workload_gpu_gate: pass
  memory_resident_workload_cpu_baseline_gate: pass_gpu_win_at_largest_shape
  best_memory_resident_proxy_gpu_over_cpu_ratio: 1.0955
  best_true_resident_gpu_over_cpu_ratio: 1.2076
  true_resident_runtime_status: packaged_boundary
  resident_runtime_regression_contract: pass
  next_task: select_next_non_tlul_resident_candidate
```

The `memory_resident_workload_*` gates now use explicit resident mode:
`--resident-steps` in `src/tools/run_vl_hybrid.py` forwards
`RUN_VL_HYBRID_RESIDENT_STEPS=1` into `src/hybrid/run_vl_hybrid.c`. This keeps
batched state on device across repeated eval steps, preserves the existing
non-resident path for comparison, and only dumps final state at the boundary.
The resident mode still rejects direct argv `--patch`, but `--patch-script`
is now the intended changing-input path: the runtime uploads a compact patch
schedule once and applies step records on the GPU with
`vl_apply_patch_schedule_gpu`.

Next resident communication-reduction task:

```text
weakest_point:
  resident --patch-script GPU and CPU gates pass on two TL-UL seeds, but this
  is still not non-TL-UL breadth or full RTL application throughput.

next:
  implement_xuantie_e902_program_image_initialization_construction

latest_larger_envelope:
  tlul_sink_1024x64_gpu_over_cpu_ratio: 5.557127971950416
  tlul_sink_2048x64_gpu_over_cpu_ratio: 6.685046741041471

selected_gpu_owned_state_construction_boundary:
  device_side_init_state_replication

latest_init_state_replication_gate:
  shape: tlul_fifo_sync 64x1
  strict_match: true
  normalized_final_state_equivalence: true
  upload_reduction_ratio: 64.0

next_gpu_owned_state_construction_step:
  boundary: source_backed_program_image_initialization
  target: xuantie_e902
  gate: config/scaling_gates/xuantie_e902_program_image_initialization_construction.json
  source: case.pat loaded through mem_inst_temp
  selected_family: iahb_instruction_memory
  status: packaged_bounded_case_pat_iahb_byte_record_construction
  next: implement_program_image_word_packed_kernel_generation
  task_ladder:
    - extract_xuantie_e902_program_image_initialization_inputs: done_contract_defined
    - define_program_image_initialization_record_format: done_format_defined
    - implement_program_image_initialization_kernel_and_host_flag: planned_subtasks_defined
    - implement_program_image_initialization_kernel_generation: done_kernel_generation_implemented
    - add_program_image_initialization_host_flag_and_env: done_host_flag_env_wired
    - upload_program_image_initialization_records_once: done_records_uploaded_once
    - launch_program_image_initialization_before_resident_eval: done_launch_before_resident_eval_wired
    - validate_program_image_initialization_against_cpu_constructed_state: done_normalized_final_state_equivalence_pass
    - measure_program_image_initialization_upload_reduction: done_positive_but_small_1_0989x
  input_record_fields:
    - word_index
    - lane
    - byte_value
    - target_root_offset
  device_upload_layout: structure_of_arrays_offsets_and_values
  apply_scope: apply every record to every GPU state before the first resident eval step
  required_kernel: vl_apply_program_image_init_gpu
  kernel_generation: implemented_in_generators
  required_host_flag: --program-image-init-records
  host_flag_env: wired_to_runtime_env
  required_env: RUN_VL_HYBRID_PROGRAM_IMAGE_INIT_RECORDS
  record_upload: offset_value_soa_uploaded_once
  launch: before_resident_eval_wired
  validation: normalized_final_state_equivalence_pass
  validation_report: reports/xuantie_e902_program_image_initialization_construction.json
  full_state_upload_bytes: 1318784
  record_upload_bytes: 1200096
  upload_reduction_ratio: 1.0988987547662854
  next_axis: source_backed_program_image_word_packed_initialization
  word_packed_boundary: defined
  word_packed_required_kernel: vl_apply_program_image_words_gpu
  word_packed_kernel_generation: implemented_in_generators
  word_packed_planned_host_flag: --program-image-words
  word_packed_planned_env: RUN_VL_HYBRID_PROGRAM_IMAGE_WORDS
  word_packed_host_flag_env: wired_to_runtime_env
  word_packed_upload: uint32_words_uploaded_once
  word_packed_launch: before_resident_eval_wired
  word_packed_validation: normalized_final_state_equivalence_pass
  word_packed_upload_bytes: 133376
  word_packed_reduction_ratio_vs_full_state: 9.887715930902111
  word_packed_boundary: packaged_source_backed_case_pat_word_packed_iahb_construction
  next_gpu_owned_state_construction_axis: xuantie_e902_non_iahb_source_backed_memory_initialization
  non_iahb_source_backed_boundary: blocked_source_contract_gap
  next_gpu_owned_state_construction_axis_after_non_iahb_gap: xuantie_e902_dmem_zero_fill_device_initialization
  dmem_zero_fill_boundary: defined_boundary
  dmem_zero_fill_selected_family: x_dmem_ctrl.ram0..3.mem
  dmem_zero_fill_source_policy: tb.v zero-fills x_dmem_ctrl.ram0..3.mem
  dmem_zero_fill_required_kernel: vl_zero_dmem_words_gpu
  dmem_zero_fill_planned_host_flag: --dmem-zero-fill
  dmem_zero_fill_planned_env: RUN_VL_HYBRID_DMEM_ZERO_FILL
  dmem_zero_fill_next_action: implement_xuantie_e902_dmem_zero_fill_kernel_generation
  word_packed_input_layout: uint32 program_words[word_count] plus size_t lane_base_offsets[4]
  expected_next_axis_upload_bytes: 166688
  expected_next_axis_reduction_ratio_vs_full_state: 7.911700901080822
  non_claim: not source-backed x_dmem data-image initialization, not x_smem coverage, not ISA correctness, and not full software boot correctness

policy:
  - upload init-state once
  - keep state device-resident across repeated eval steps
  - represent per-step changes as a compact device-side patch schedule
  - do not reintroduce per-step host-device patch copies

source_of_truth:
  - config/resident_patch_script_semantics.json
  - config/scaling_gates/tlul_fifo_sync_resident_patch_schedule.json
  - config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_resident_patch_schedule.json
  - config/scaling_gates/tlul_sink_resident_patch_schedule.json
  - config/scaling_gates/tlul_sink_cpu_exact_loop_resident_patch_schedule.json
  - config/scaling_gates/veer_el2_resident_patch_schedule.json
  - config/scaling_gates/veer_el2_cpu_exact_loop_resident_patch_schedule.json
  - config/scaling_gates/xuantie_e902_resident_patch_schedule.json
  - config/scaling_gates/xuantie_e902_cpu_exact_loop_resident_patch_schedule.json
  - config/scaling_gates/xuantie_e902_rom_memory_delta_patch_schedule.json
  - config/scaling_gates/xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule.json
  - config/scaling_gates/xuantie_e902_named_rom_memory_mapping.json
  - config/scaling_gates/xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json
  - config/scaling_gates/xuantie_e902_program_image_delta.json
  - config/scaling_gates/xuantie_e902_cpu_exact_loop_program_image_delta.json
  - config/scaling_gates/xuantie_e902_program_image_initialization_construction.json
```

Current bounded resident changing-input result:

```text
accepted_claim:
  tlul_fifo_sync:
    shape: nstates=512 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 3.1160088024052413
  tlul_sink:
    shape: nstates=512 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 2.002480966457029
  veer_el2:
    shape: nstates=512 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 2.8489279680483475
  xuantie_e902:
    shape: nstates=128 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 1.1724144754038845
  xuantie_e902_rom_memory_delta:
    shape: nstates=128 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 1.442536802751107
  xuantie_e902_named_rom_memory_mapping:
    shape: nstates=128 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 2.0903639153360194
  xuantie_e902_program_image_delta:
    shape: nstates=128 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 1.3826459191531113
  boundary_status: blocked_broader_memory_family_source_contract_gap

next_candidate_order:
  - input_stream_delta
  - target_breadth
selected_next_axis:
  runtime_depth

non_claims:
  - not broad non-TL-UL resident patch schedule breadth
  - not broad VeeR family support
  - not broad XuanTie family support
  - not broad target-breadth evidence
  - not full RTL application throughput
  - not application-like input, ROM, or program-delta semantics
  - not named-symbol ROM/memory mapping
  - not ISA/program correctness
  - small 1x6 smoke remains CPU-favorable on all measured patch-schedule seeds
```

The host probe reuses `src/hybrid/tlul_slice_host_probe.cpp` with XuanTie
model-specific macros. Run it from the generated obj_dir so the stock testbench
can read `case.pat`.

```bash
make -C src/hybrid xuantie_e902_host_probe

(
  cd artifacts/xuantie_e902_obj_dir
  ./xuantie_e902_host_probe \
    --reset-cycles 120 \
    --post-reset-cycles 120 \
    --state-out xuantie_cpu_reference_state.bin \
    > xuantie_cpu_reference_probe.json
)

PYTHONPATH=src/tools python3 src/tools/run_vl_hybrid.py \
  --mdir artifacts/xuantie_e902_obj_dir \
  --nstates 1 \
  --steps 1 \
  --init-state artifacts/xuantie_e902_obj_dir/xuantie_cpu_reference_state.bin \
  --sanitize-host-only-internals \
  --dump-state artifacts/xuantie_e902_obj_dir/xuantie_gpu_from_cpu_reference_state.bin

PYTHONPATH=src/tools python3 src/tools/compare_vl_hybrid_modes.py \
  artifacts/xuantie_e902_obj_dir \
  --compare-dumps \
    artifacts/xuantie_e902_obj_dir/xuantie_cpu_reference_state.bin \
    artifacts/xuantie_e902_obj_dir/xuantie_gpu_from_cpu_reference_state.bin \
  --json-out reports/xuantie_e902_cpu_vs_gpu_from_cpu_init_compare.json \
  --acceptance-policy normalized_final_state_equivalence

make -C src/hybrid veer_el2_host_probe

(
  cd artifacts/veer_el2_obj_dir
  ./veer_el2_host_probe \
    --reset-cycles 120 \
    --post-reset-cycles 120 \
    --state-out veer_el2_cpu_reference_state.bin \
    > veer_el2_cpu_reference_probe.json
)

PYTHONPATH=src/tools python3 src/tools/run_vl_hybrid.py \
  --mdir artifacts/veer_el2_obj_dir \
  --nstates 1 \
  --steps 1 \
  --init-state artifacts/veer_el2_obj_dir/veer_el2_cpu_reference_state.bin \
  --sanitize-host-only-internals \
  --dump-state artifacts/veer_el2_obj_dir/veer_el2_gpu_from_cpu_reference_state.bin

PYTHONPATH=src/tools python3 src/tools/compare_vl_hybrid_modes.py \
  artifacts/veer_el2_obj_dir \
  --compare-dumps \
    artifacts/veer_el2_obj_dir/veer_el2_cpu_reference_state.bin \
    artifacts/veer_el2_obj_dir/veer_el2_gpu_from_cpu_reference_state.bin \
  --json-out reports/veer_el2_cpu_vs_gpu_from_cpu_init_compare.json \
  --acceptance-policy normalized_final_state_equivalence

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py \
  --gate config/scaling_gates/veer_el2_larger_resident_workload.json \
  --mdir artifacts/veer_el2_obj_dir \
  --json-out reports/veer_el2_larger_resident_workload_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py \
  --exact-loop \
  --mdir artifacts/veer_el2_obj_dir \
  --probe artifacts/veer_el2_obj_dir/veer_el2_host_probe \
  --gate config/scaling_gates/veer_el2_cpu_exact_loop_larger_resident_workload.json \
  --json-out reports/veer_el2_cpu_exact_loop_larger_resident_workload.json \
  --gpu-scaling-report reports/veer_el2_larger_resident_workload_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py \
  --gate config/scaling_gates/xuantie_e902_scaling.json \
  --mdir artifacts/xuantie_e902_obj_dir \
  --json-out reports/xuantie_e902_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py \
  --exact-loop \
  --mdir artifacts/xuantie_e902_obj_dir \
  --probe artifacts/xuantie_e902_obj_dir/xuantie_e902_host_probe \
  --gate config/scaling_gates/xuantie_e902_cpu_exact_loop_repeated_steps.json \
  --json-out reports/xuantie_e902_cpu_exact_loop_repeated_steps.json \
  --gpu-scaling-report reports/xuantie_e902_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py \
  --gate config/scaling_gates/xuantie_e902_large_workload.json \
  --mdir artifacts/xuantie_e902_obj_dir \
  --json-out reports/xuantie_e902_large_workload_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py \
  --exact-loop \
  --mdir artifacts/xuantie_e902_obj_dir \
  --probe artifacts/xuantie_e902_obj_dir/xuantie_e902_host_probe \
  --gate config/scaling_gates/xuantie_e902_cpu_exact_loop_large_workload.json \
  --json-out reports/xuantie_e902_cpu_exact_loop_large_workload.json \
  --gpu-scaling-report reports/xuantie_e902_large_workload_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_scaling_validation.py \
  --gate config/scaling_gates/xuantie_e902_memory_resident_workload.json \
  --mdir artifacts/xuantie_e902_obj_dir \
  --json-out reports/xuantie_e902_memory_resident_workload_scaling.json

PYTHONPATH=src/tools python3 src/tools/run_tlul_fifo_sync_cpu_baseline.py \
  --exact-loop \
  --mdir artifacts/xuantie_e902_obj_dir \
  --probe artifacts/xuantie_e902_obj_dir/xuantie_e902_host_probe \
  --gate config/scaling_gates/xuantie_e902_cpu_exact_loop_memory_resident_workload.json \
  --json-out reports/xuantie_e902_cpu_exact_loop_memory_resident_workload.json \
  --gpu-scaling-report reports/xuantie_e902_memory_resident_workload_scaling.json
```

## Release Checklist

```text
before_publishing:
  jq_configs: jq empty config/selection.json config/targets.json config/scaling_gates/*.json
  python_syntax: python3 -m py_compile src/tools/*.py
  resident_contract: python3 -m unittest tests.contract.test_resident_runtime_contract
  first_seed_gpu_gate: reports/tlul_fifo_sync_repeated_steps_scaling.json
  first_seed_cpu_gate: reports/tlul_fifo_sync_cpu_exact_loop_repeated_steps.json
  second_seed_gpu_gate: reports/tlul_sink_repeated_steps_scaling.json
  second_seed_cpu_gate: reports/tlul_sink_cpu_exact_loop_repeated_steps.json
  generated_outputs_tracked: 0
  claim_boundary_documented: true
```

## Release Boundary

weakest_point:
  this boundary is a local source boundary, not a published remote release tag
  or a broad non-TL-UL generality claim.

```text
boundary_name: minimal-two-tlul-seed-boundary
boundary_base_commit: 1da48dc
scope:
  included:
    - minimal Verilator -> LLVM -> CUDA build path
    - tlul_fifo_sync repeated-step GPU/CPU comparison
    - tlul_sink repeated-step GPU/CPU comparison
    - generated artifact policy for artifacts/ and reports/
  excluded:
    - non-TL-UL target breadth
    - full RTL application throughput
    - raw byte equality
    - historical campaign work/output artifacts
next_axis:
  select the smallest non-TL-UL breadth seed candidate before copying assets
```
