# Status

## weakest_point

The copied runtime core and first `tlul_fifo_sync` repro flow work, generated outputs are ignored, the initial source boundary is committed, and clean-checkout reproduction passes after fixing the README Verilator command to include `prim_pkg.sv`. The `tlul_fifo_sync` repeated-step comparison and second-seed `tlul_sink` CPU/GPU repeated-step comparison both pass with GPU wins. The minimal two-seed package boundary is now documented, with claims limited to OpenTitan TL-UL repeated-step gates.

## goal

```text
generalize_verilator_llvm_hybrid_runtime_for_high_throughput_regression_and_coverage
```

## current_state

```text
repo:
  status: runtime_core_source_local_dependency_closure_ok
  active_seed_target: tlul_fifo_sync
  active_second_seed_target: tlul_sink
  generated_history_carried: false

current_priority:
  define_larger_resident_schedule_envelope_gate

dependency_closure:
  repo_local_missing_headers: 0
  deferred_external_headers:
    - cuda.h
    - verilated.h
    - llvm/*
  deferred_generated_headers:
    - Vtlul_fifo_sync_gpu_cov_cpu_replay_tb.h
    - Vtlul_fifo_sync_gpu_cov_cpu_replay_tb___024root.h
    - MODEL_HEADER
    - ROOT_HEADER
    - EXTRA_WATCH_FIELDS_HEADER

selected_now:
  - src/tools/build_vl_gpu.py
  - src/tools/gen_vl_gpu_kernel.py
  - src/tools/llvm_ir_parse.py
  - src/tools/llvm_stub_gen.py
  - src/tools/vl_runtime_filter.py
  - src/tools/run_vl_hybrid.py
  - src/tools/compare_vl_hybrid_modes.py

tool_copy:
  copied_file_count: 7
  py_compile: pass
  import_validation: pass

seed_config:
  launch_template_path: config/slice_launch_templates/tlul_fifo_sync.json
  target_registry: config/targets.json
  index_json_copied: false

rtl_test_asset_selection:
  selected_asset_count: 22
  copied_asset_count: 22
  copy_full_third_party_tree: false

verilator_surface:
  lint_only: pass_with_warnings
  cc_obj_dir: artifacts/tlul_fifo_sync_obj_dir
  cc_result: pass_with_warnings
  top_module: tlul_fifo_sync_gpu_cov_tb

gpu_kernel_build_attempt:
  reached: storage_size_probe
  blocked_by: missing src/passes/vlgpugen

pass_build_surface:
  makefile: src/passes/Makefile
  make: pass
  outputs:
    - src/passes/vlgpugen
    - src/passes/VlGpuPasses.so

gpu_kernel:
  cubin: artifacts/tlul_fifo_sync_obj_dir/vl_batch_gpu.cubin
  meta: artifacts/tlul_fifo_sync_obj_dir/vl_batch_gpu.meta.json
  storage_size: 6016
  kernel: vl_eval_batch_gpu

host_runtime:
  makefile: src/hybrid/Makefile
  binary: src/hybrid/run_vl_hybrid
  make: pass

first_hybrid_smoke:
  nstates: 1
  steps: 1
  result: pass
  state_dump: artifacts/tlul_fifo_sync_obj_dir/minimal_smoke_state.bin

compare_surface:
  mode: compare_existing_state_dumps
  report: reports/minimal_smoke_self_compare.json
  validation: gpu_smoke_self_compare
  result: pass
  non_claim: not_yet_cpu_gpu_correctness

cpu_reference:
  build: make -C src/hybrid tlul_slice_host_probe
  probe_report: reports/minimal_cpu_reference_probe.json
  state_dump: artifacts/tlul_fifo_sync_obj_dir/minimal_cpu_reference_state.bin
  result: dump_generated

cpu_gpu_compare:
  report: reports/minimal_cpu_vs_gpu_smoke_compare.json
  result: fail_expected_contract_gap
  first_non_internal_mismatch: cfg_valid_i

cpu_gpu_aligned_compare:
  gpu_run_report: reports/minimal_gpu_from_cpu_init_run.json
  compare_report: reports/minimal_cpu_vs_gpu_from_cpu_init_compare.json
  result: normalized_final_state_equivalence_pass
  design_state_mismatch_bytes: 0
  top_level_io_mismatch_bytes: 0
  raw_mismatch_bytes: 156

repro_documentation:
  file: README.md
  status: documented
  covers:
    - prerequisites
    - Verilator obj_dir generation
    - GPU cubin build
    - host runtime build
    - CPU reference dump generation
    - GPU run from CPU init-state
    - normalized final-state compare
    - generated artifact policy

promotion_policy:
  status: accepted
  mainline_surface: true
  scope: tlul_fifo_sync normalized CPU/GPU repro flow
  old_repo_role: historical campaign archive and migration reference

generated_artifact_policy:
  status: frozen
  artifacts: generated build/runtime outputs only
  reports: generated summaries only
  canonical_state:
    - config/selection.json
    - docs/status.md
    - docs/roadmap.md
    - README.md

operator_status_report:
  status: emitted
  completed_capability: tlul_fifo_sync CPU/GPU normalized final-state equivalence repro
  correctness_claim:
    policy: normalized_final_state_equivalence
    design_state_mismatch_bytes: 0
    top_level_io_mismatch_bytes: 0
    other_mismatch_bytes: 0
  non_claims:
    - raw byte equality is not required because Verilator internal bytes may differ
    - throughput scaling is not claimed
    - only one seed target is active
  repo_split:
    minimal_repo: mainline implementation surface
    old_repo: historical campaign archive and migration reference
  next_recommended_work: commit if explicitly requested

commit_boundary:
  status: summarized_in_old_repo
  include: hand-authored minimal repo source/docs/config plus old repo minimal status artifacts
  exclude: generated artifacts and unrelated old repo dirty files

git_ownership:
  selected_mode: new_repository
  reason: keep the minimal source boundary independent from the old repo's unrelated dirty state and campaign history
  initialized: true
  branch: main
  generated_outputs_ignored:
    - artifacts/**
    - reports/**
    - src/hybrid/run_vl_hybrid
    - src/hybrid/*_host_probe
    - src/passes/VlGpuPasses.so
    - src/passes/vlgpugen

source_boundary_review:
  status: pass
  tracked_candidate_count: 48
  initial_commit: f8349b9
  next_action: reproduce_from_clean_checkout_after_initial_commit
  weakest_point: third_party seed provenance should be reviewed before publishing beyond local development

clean_checkout_reproduction:
  status: pass
  source_commit: 8419685
  readme_fix_required: add prim_pkg.sv to the Verilator command
  readme_fix_commit: c041911
  selected_acceptance_policy: normalized_final_state_equivalence
  selected_acceptance_policy_passed: true
  design_state_mismatch_bytes: 0
  top_level_io_mismatch_bytes: 0
  other_mismatch_bytes: 0
  next_action: select_next_minimal_runtime_validation_axis

next_axis_candidates:
  - increase_nstates_or_steps_on_tlul_fifo_sync: selected
  - add_second_small_seed_target
  - package_remote_or_release_boundary

selected_next_axis:
  axis: increase_nstates_or_steps_on_tlul_fifo_sync
  reason: reuse the proven seed to measure batching/state scaling before increasing target breadth
  gate: config/scaling_gates/tlul_fifo_sync.json
  runner: src/tools/run_tlul_fifo_sync_scaling_validation.py
  report: reports/tlul_fifo_sync_scaling_validation.json
  status: pass
  next_action: decide_post_tlul_scaling_validation_next_axis
  gate_shape:
    build: reuse documented clean-checkout build
    runs:
      - nstates: 1
        steps: 1
      - nstates: 8
        steps: 1
      - nstates: 32
        steps: 1
    acceptance:
      - each run exits successfully
      - generated state dumps have expected storage_size * nstates bytes
      - normalized final-state equivalence remains the correctness policy for CPU/GPU aligned single-state comparison
      - scaling gate reports runtime and throughput without claiming speedup until CPU baseline is measured

tlul_fifo_sync_scaling_validation:
  status: pass
  report: reports/tlul_fifo_sync_scaling_validation.json
  storage_size: 6016
  runs:
    - name: single_state_smoke
      nstates: 1
      steps: 1
      passed: true
    - name: small_batch
      nstates: 8
      steps: 1
      passed: true
    - name: medium_batch
      nstates: 32
      steps: 1
      passed: true
  non_claims:
    - CPU speedup is not claimed yet
    - target breadth is not claimed because only tlul_fifo_sync was exercised

tlul_fifo_sync_cpu_baseline:
  gate: config/scaling_gates/tlul_fifo_sync_cpu_baseline.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py
  report: reports/tlul_fifo_sync_cpu_baseline.json
  status: pass
  reps: 5
  median_elapsed_ms: 18.653276027180254
  root_size: 6016
  next_action: define_tlul_cpu_multistate_baseline_gate
  accepted_claim: CPU single-state host probe timing surface
  non_claim: exact nstates>1 CPU-vs-GPU speedup until matching CPU loop exists

tlul_fifo_sync_cpu_multistate_baseline:
  gate: config/scaling_gates/tlul_fifo_sync_cpu_multistate_baseline.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --multi-state
  report: reports/tlul_fifo_sync_cpu_multistate_baseline.json
  status: pass
  claim_scope: conservative_process_per_state_cpu_baseline
  latest_metrics: read reports/tlul_fifo_sync_cpu_multistate_baseline.json
  next_action: decide_exact_cpu_loop_or_second_seed_after_conservative_multistate_baseline
  weakest_point: process-per-state CPU timing includes host probe process overhead, so it is not an exact single-process CPU speedup claim

tlul_fifo_sync_cpu_exact_loop_baseline:
  gate: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_baseline.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --exact-loop
  report: reports/tlul_fifo_sync_cpu_exact_loop_baseline.json
  status: pass
  claim_scope: single_process_cpu_loop_baseline
  latest_metrics: read reports/tlul_fifo_sync_cpu_exact_loop_baseline.json
  latest_observation: GPU is still slower than CPU for nstates <= 32 under this small seed/workload
  next_action: decide_second_seed_or_larger_workload_after_exact_cpu_loop_baseline
  weakest_point: exact loop removes process overhead, but the current workload is too small to demonstrate a GPU win

tlul_fifo_sync_large_workload:
  gpu_gate: config/scaling_gates/tlul_fifo_sync_large_workload.json
  cpu_gate: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_large_workload.json
  gpu_report: reports/tlul_fifo_sync_large_workload_scaling.json
  cpu_report: reports/tlul_fifo_sync_cpu_exact_loop_large_workload.json
  status: pass
  accepted_claim: GPU beats single-process CPU exact loop at nstates=512 for tlul_fifo_sync steps=1
  latest_metrics:
    nstates_32_gpu_over_cpu: 0.1296
    nstates_128_gpu_over_cpu: 0.7455
    nstates_512_gpu_over_cpu: 2.8779
  next_action: decide_repeated_steps_or_second_seed_after_large_workload
  weakest_point: steps remain fixed at 1 because CPU exact-loop timing does not yet model repeated eval steps

tlul_fifo_sync_repeated_steps:
  gpu_gate: config/scaling_gates/tlul_fifo_sync_repeated_steps.json
  cpu_gate: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_repeated_steps.json
  gpu_report: reports/tlul_fifo_sync_repeated_steps_scaling.json
  cpu_report: reports/tlul_fifo_sync_cpu_exact_loop_repeated_steps.json
  status: pass
  accepted_claim: GPU beats CPU repeated-eval loop for nstates=512 and steps in [1, 8, 32] on tlul_fifo_sync
  latest_metrics:
    steps_1_gpu_over_cpu: 2.5619
    steps_8_gpu_over_cpu: 5.2985
    steps_32_gpu_over_cpu: 2.7165
  next_action: decide_second_seed_after_repeated_steps
  weakest_point: CPU repeated steps are modeled as repeated eval_step calls after initialization, not full timed clock cycles

tlul_sink_second_seed:
  selection_status: selected
  reason: second OpenTitan TL-UL seed with source-backed frozen multi-step GPU-win evidence in the exploration repository
  launch_template: config/slice_launch_templates/tlul_sink.json
  gpu_gate: config/scaling_gates/tlul_sink_repeated_steps.json
  gpu_report: reports/tlul_sink_repeated_steps_scaling.json
  cpu_gate: config/scaling_gates/tlul_sink_cpu_exact_loop_repeated_steps.json
  cpu_report: reports/tlul_sink_cpu_exact_loop_repeated_steps.json
  build_surface:
    verilator_obj_dir: pass_with_warnings
    gpu_cubin: pass
    gpu_repeated_steps: pass
    cpu_exact_loop_repeated_steps: pass
  observed_gpu_state_steps_per_second:
    steps_1: 1047.6424
    steps_8: 9412.8866
    steps_32: 32658.0798
  gpu_over_cpu:
    steps_1: 5.2200
    steps_8: 2.7046
    steps_32: 6.0901
  next_action: decide_package_boundary_after_second_seed_speedup
  weakest_point: target breadth is still limited to two OpenTitan TL-UL seeds

package_boundary:
  status: documented
  documented_in: README.md
  included:
    - minimal Verilator to LLVM to CUDA build path
    - tlul_fifo_sync repeated-step CPU/GPU comparison
    - tlul_sink repeated-step CPU/GPU comparison
  excluded:
    - non-TL-UL target breadth
    - full RTL application throughput claim
    - raw byte equality claim
  next_action: decide_non_tlul_seed_or_release_after_package_boundary
  weakest_point: package is useful as two-seed TL-UL evidence, not as broad RTL generality

release_readiness_audit:
  status: pass_lightweight
  checks:
    jq_configs: pass
    python_syntax: pass
    diff_whitespace: pass
    generated_outputs_tracked: artifacts/.gitignore and reports/.gitignore only
    first_seed_gpu_gate: status_ok
    first_seed_cpu_gate: status_ok
    second_seed_gpu_gate: status_ok
    second_seed_cpu_gate: status_ok
  next_action: prepare_minimal_two_seed_release_boundary
  weakest_point: this is a local lightweight audit, not an independent clean-clone rerun

release_boundary:
  status: documented
  documented_in: README.md
  boundary_name: minimal-two-tlul-seed-boundary
  boundary_base_commit: 1da48dc
  next_action: select_smallest_non_tlul_breadth_seed_candidate
  weakest_point: release boundary is local and TL-UL only; no broad non-TL-UL claim

non_tlul_breadth_seed_selection:
  status: selected
  selected_candidate: XuanTie-E902
  selected_template_source: old repo config/slice_launch_templates/xuantie_e902.json
  reason:
    - old repo campaign_non_opentitan_entry selected xuantie_single_surface_e902
    - selected profile describes it as the smallest ready stock-Verilator bootstrap candidate
    - the existing template is a single-surface non-OpenTitan candidate
  do_not_do_yet:
    - copy XuanTie-E902 assets
    - claim non-TL-UL runtime support
    - broaden beyond one candidate before gate shape is fixed
  next_action: define_xuantie_e902_minimal_gate_before_asset_copy
  weakest_point: candidate evidence is inherited from old repo metadata; minimal repo has not built or run it

xuantie_e902_minimal_gate:
  status: defined_before_asset_copy
  target: XuanTie.xuantie_e902
  top_module: xuantie_e902_gpu_cov_tb
  old_template: old repo config/slice_launch_templates/xuantie_e902.json
  planned_mdir: artifacts/xuantie_e902_obj_dir
  initial_gate_shape:
    gpu_nstates: 8
    gpu_sequential_steps: 56
    first_acceptance: stock Verilator object directory can be generated from copied source boundary
    followup_acceptance: GPU cubin builds and runs without broad performance claim
  required_asset_boundary:
    - third_party/rtlmeter/designs/XuanTie-E902/descriptor.yaml
    - third_party/rtlmeter/designs/XuanTie-E902/LICENSE-XuanTie-E902
    - third_party/rtlmeter/designs/XuanTie-E902/src/**
    - third_party/rtlmeter/designs/XuanTie-E902/tests/hello/case.pat
    - third_party/rtlmeter/designs/XuanTie-E902/tests/post.bash
    - third_party/rtlmeter/designs/XuanTie-E902/tests/xuantie_e902_gpu_cov_coverage_regions.json
  generated_outputs:
    - artifacts/xuantie_e902_obj_dir/**
    - reports/xuantie_e902_*.json
  non_claims:
    - not a GPU speedup claim
    - not a supported non-TL-UL target claim
    - not a claim that all XuanTie family targets work
  next_action: materialize_xuantie_e902_asset_boundary
  weakest_point: gate definition still relies on old repo template and has not been validated in minimal repo

xuantie_e902_asset_boundary:
  status: materialized
  copied_scope:
    - third_party/rtlmeter/designs/XuanTie-E902/descriptor.yaml
    - third_party/rtlmeter/designs/XuanTie-E902/LICENSE-XuanTie-E902
    - third_party/rtlmeter/designs/XuanTie-E902/src/**
    - third_party/rtlmeter/designs/XuanTie-E902/tests/hello/case.pat
    - third_party/rtlmeter/designs/XuanTie-E902/tests/post.bash
    - third_party/rtlmeter/designs/XuanTie-E902/tests/xuantie_e902_gpu_cov_coverage_regions.json
  launch_template: config/slice_launch_templates/xuantie_e902.json
  target_registry: config/targets.json
  non_claims:
    - copied source boundary is not a build pass claim
    - copied source boundary is not a GPU runtime claim
    - copied source boundary is not a supported non-TL-UL target claim
  next_action: validate_xuantie_e902_asset_boundary
  weakest_point: source boundary is copied but not yet validated by syntax/config checks

xuantie_e902_asset_boundary_validation:
  status: blocked
  config_json: pass
  python_syntax: pass
  diff_check: pass
  copied_file_count: 130
  copied_families:
    - OpenTitan
    - XuanTie-E902
  source_discovery:
    descriptor_source_count: 125
    missing_source_count: 0
  verilator_lint_only:
    status: blocked
    blocker: tb.v includes missing __rtlmeter_top_include.vh
  next_action: define_xuantie_e902_rtlmeter_include_strategy
  weakest_point: XuanTie-E902 depends on an RTLMeter generated include seam that is not yet represented in the minimal repo

xuantie_e902_rtlmeter_include_strategy:
  status: resolved_for_lint
  support_rtl:
    - third_party/rtlmeter/rtl/__rtlmeter_utils.sv
    - third_party/rtlmeter/rtl/__rtlmeter_top_include.vh
  verilator_define:
    __RTLMETER_MAIN_CLOCK: xuantie_e902_gpu_cov_tb.dut.clk
  lint_only:
    status: pass_with_warnings
    source_count: 126
    warning_policy: accepted_for_lint_only
  non_claims:
    - not a Verilator obj_dir build claim
    - not a GPU cubin build claim
    - not a runtime support claim
  next_action: generate_xuantie_e902_verilator_obj_dir
  weakest_point: lint passes only with accepted source warnings; full obj_dir generation is still unproven

xuantie_e902_obj_dir_generation:
  status: pass_with_warnings
  source_count: 126
  mdir: artifacts/xuantie_e902_obj_dir
  runtime_input_staged: artifacts/xuantie_e902_obj_dir/case.pat
  top_module: xuantie_e902_gpu_cov_tb
  warning_policy: accepted_for_build_surface_only
  next_action: build_xuantie_e902_gpu_cubin
  weakest_point: Verilator C++ obj_dir exists, but the GPU cubin and runtime execution path are still unproven for this non-TL-UL seed.

xuantie_e902_gpu_cubin_and_smoke:
  status: pass
  mdir: artifacts/xuantie_e902_obj_dir
  cubin: artifacts/xuantie_e902_obj_dir/vl_batch_gpu.cubin
  meta: artifacts/xuantie_e902_obj_dir/vl_batch_gpu.meta.json
  storage_size: 1318784
  smoke:
    nstates: 1
    steps: 1
    state_dump: artifacts/xuantie_e902_obj_dir/xuantie_gpu_smoke_state.bin
    result: pass
  runtime_observation:
    gpu_kernel_time_ms_total: 0.229376
    wall_time_ms: 2.312
  non_claims:
    - not a CPU/GPU correctness claim
    - not a throughput or speedup claim
    - not a full non-TL-UL support claim
  next_action: define_xuantie_e902_cpu_reference_contract
  weakest_point: The GPU kernel launches, but there is no CPU reference dump or normalized final-state equivalence contract for XuanTie-E902 yet.

xuantie_e902_cpu_reference_contract:
  status: pass
  host_probe: artifacts/xuantie_e902_obj_dir/xuantie_e902_host_probe
  source: src/hybrid/tlul_slice_host_probe.cpp
  make_target: make -C src/hybrid xuantie_e902_host_probe
  cpu_reference:
    command_workdir: artifacts/xuantie_e902_obj_dir
    state_dump: artifacts/xuantie_e902_obj_dir/xuantie_cpu_reference_state.bin
    probe_stdout: artifacts/xuantie_e902_obj_dir/xuantie_cpu_reference_probe.json
    note: stock tb emits a banner before JSON, so this probe output is operator-readable but not strict JSON
  gpu_from_cpu_init:
    state_dump: artifacts/xuantie_e902_obj_dir/xuantie_gpu_from_cpu_reference_state.bin
    sanitize_host_only_internals: true
  compare:
    report: reports/xuantie_e902_cpu_vs_gpu_from_cpu_init_compare.json
    selected_acceptance_policy: normalized_final_state_equivalence
    result: pass
    raw_mismatch_bytes: 39
    design_state_mismatch_bytes: 0
    top_level_io_mismatch_bytes: 0
    other_mismatch_bytes: 0
  non_claims:
    - not a throughput or speedup claim
    - not a repeated-step claim
    - not a full non-TL-UL family support claim
  next_action: define_xuantie_e902_scaling_gate
  weakest_point: XuanTie-E902 has a one-state correctness smoke, but no scaling gate or CPU/GPU repeated-step comparison yet.

xuantie_e902_scaling_gate:
  status: pass
  gate: config/scaling_gates/xuantie_e902_scaling.json
  runner: src/tools/run_tlul_fifo_sync_scaling_validation.py
  report: reports/xuantie_e902_scaling.json
  mdir: artifacts/xuantie_e902_obj_dir
  storage_size: 1318784
  runs:
    - name: single_state_smoke
      nstates: 1
      steps: 1
      passed: true
    - name: small_batch
      nstates: 8
      steps: 1
      passed: true
    - name: small_repeated_steps
      nstates: 8
      steps: 8
      passed: true
  non_claims:
    - no XuanTie CPU speedup claim yet
    - no repeated-step CPU/GPU correctness claim yet
    - no broad non-TL-UL generality claim
  next_action: define_xuantie_e902_cpu_repeated_steps_baseline
  weakest_point: GPU launch/scaling passes for a conservative E902 shape, but the matching CPU repeated-step baseline is not defined.

xuantie_e902_cpu_repeated_steps_baseline:
  status: pass_cpu_favorable
  gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_repeated_steps.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --exact-loop
  probe: artifacts/xuantie_e902_obj_dir/xuantie_e902_host_probe
  report: reports/xuantie_e902_cpu_exact_loop_repeated_steps.json
  source_gpu_report: reports/xuantie_e902_scaling.json
  runs:
    - shape: nstates=1 steps=1
      passed: true
      gpu_over_cpu_throughput_ratio: 0.0115
    - shape: nstates=8 steps=1
      passed: true
      gpu_over_cpu_throughput_ratio: 0.1003
    - shape: nstates=8 steps=8
      passed: true
      gpu_over_cpu_throughput_ratio: 0.0590
  observation: CPU is faster than GPU for the conservative XuanTie-E902 gate shapes.
  non_claims:
    - no XuanTie speedup claim
    - no broad non-TL-UL throughput claim
    - no larger-nstates or longer-run conclusion yet
  next_action: decide_xuantie_e902_next_scaling_or_boundary
  weakest_point: The first non-TL-UL correctness path works, but the conservative performance gate is CPU-favorable; the next decision is whether to scale workload or package the correctness boundary.
```

## next

```text
decide_xuantie_e902_next_scaling_or_boundary:
  decision: increase XuanTie-E902 nstates/steps beyond the conservative gate
  reason: the project goal is throughput evidence, and the conservative gate is CPU-favorable
  selected_gate: config/scaling_gates/xuantie_e902_large_workload.json

xuantie_e902_large_workload_scaling_gate:
  gate: config/scaling_gates/xuantie_e902_large_workload.json
  runner: src/tools/run_tlul_fifo_sync_scaling_validation.py
  report: reports/xuantie_e902_large_workload_scaling.json
  mdir: artifacts/xuantie_e902_obj_dir
  runs:
    - shape: nstates=32 steps=8
    - shape: nstates=64 steps=8
    - shape: nstates=64 steps=32
  status: pass
  observation: GPU large-workload gate runs, but speedup is not claimed until the matching CPU exact-loop baseline is run.
  non_claims:
    - no XuanTie speedup claim until matching large-workload CPU exact-loop baseline exists
    - no full non-TL-UL generality claim from one E902 wrapper
  next_action: run_xuantie_e902_cpu_exact_loop_large_workload_baseline

xuantie_e902_cpu_exact_loop_large_workload_baseline:
  gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_large_workload.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --exact-loop
  probe: artifacts/xuantie_e902_obj_dir/xuantie_e902_host_probe
  report: reports/xuantie_e902_cpu_exact_loop_large_workload.json
  source_gpu_report: reports/xuantie_e902_large_workload_scaling.json
  status: pass_cpu_favorable_but_gap_narrowed
  runs:
    - shape: nstates=32 steps=8
      passed: true
      gpu_over_cpu_throughput_ratio: 0.5008
    - shape: nstates=64 steps=8
      passed: true
      gpu_over_cpu_throughput_ratio: 0.5632
    - shape: nstates=64 steps=32
      passed: true
      gpu_over_cpu_throughput_ratio: 0.8625
  observation: GPU does not beat CPU yet, but increasing repeated steps narrows the gap.
  next_action: decide_xuantie_e902_larger_memory_resident_workload_or_boundary

decide_xuantie_e902_larger_memory_resident_workload_or_boundary:
  if the goal remains throughput evidence:
    reduce host/device communication further and define a larger memory-resident XuanTie workload
  else:
    package the first non-TL-UL correctness plus CPU-favorable performance boundary
  keep_current_observation:
    conservative_gate: CPU-favorable
    large_workload_gate: CPU-favorable_but_gap_narrowed
  do_not_claim: XuanTie speedup

define_xuantie_e902_memory_resident_workload_gate:
  goal: reduce host/device communication enough to test whether XuanTie-E902 crosses from CPU-favorable to GPU-favorable
  first_task: define a GPU gate that keeps more work resident per transfer instead of only increasing small launch shapes
  selected_gate: config/scaling_gates/xuantie_e902_memory_resident_workload.json
  acceptance:
    - gate config exists under config/scaling_gates
    - README command is documented
    - status and roadmap point to the same gate
    - no speedup claim is made until a matching CPU exact-loop baseline exists
  status: done
  next_action: run_xuantie_e902_memory_resident_workload_gate

xuantie_e902_memory_resident_workload_gate:
  gate: config/scaling_gates/xuantie_e902_memory_resident_workload.json
  runner: src/tools/run_tlul_fifo_sync_scaling_validation.py
  report: reports/xuantie_e902_memory_resident_workload_scaling.json
  mdir: artifacts/xuantie_e902_obj_dir
  runs:
    - shape: nstates=64 steps=64
    - shape: nstates=64 steps=128
    - shape: nstates=128 steps=64
  status: pass
  non_claims:
    - communication-reduction proxy only; not proof of fully resident GPU runtime
    - no speedup claim until matching CPU exact-loop baseline exists
  next_action: run_xuantie_e902_cpu_exact_loop_memory_resident_workload_baseline

xuantie_e902_cpu_exact_loop_memory_resident_workload_baseline:
  gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_memory_resident_workload.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --exact-loop
  probe: artifacts/xuantie_e902_obj_dir/xuantie_e902_host_probe
  report: reports/xuantie_e902_cpu_exact_loop_memory_resident_workload.json
  source_gpu_report: reports/xuantie_e902_memory_resident_workload_scaling.json
  status: pass_gpu_win_at_largest_shape
  runs:
    - shape: nstates=64 steps=64
      passed: true
      gpu_over_cpu_throughput_ratio: 0.8634
    - shape: nstates=64 steps=128
      passed: true
      gpu_over_cpu_throughput_ratio: 0.5997
    - shape: nstates=128 steps=64
      passed: true
      gpu_over_cpu_throughput_ratio: 1.2076
  observation: GPU beats the CPU exact-loop baseline at the largest resident shape after explicit resident mode was implemented.
  next_action: decide_true_resident_runtime_or_package_xuantie_boundary

decide_true_resident_runtime_or_package_xuantie_boundary:
  if the goal is implementation depth:
    implement a true resident GPU runtime path that avoids per-step host/device transfers
  else:
    package XuanTie-E902 as a first non-TL-UL proxy-throughput boundary with clear non-claims
  allowed_claim:
    XuanTie-E902 communication-reduction proxy gate has a GPU win at nstates=128 steps=64
  non_claim:
    not a fully resident GPU runtime proof

define_true_resident_gpu_runtime_interface:
  decision: pursue implementation depth before packaging XuanTie-E902
  reason: the top-level goal is high-throughput regression/coverage, and the proxy gate indicates communication reduction can cross CPU throughput
  first_task: define the host/runtime interface for keeping batched state resident across repeated eval steps
  selected_interface:
    cli_flag: src/tools/run_vl_hybrid.py --resident-steps
    runtime_env: RUN_VL_HYBRID_RESIDENT_STEPS=1
    c_runtime: src/hybrid/run_vl_hybrid.c
    validation_runner: src/tools/run_tlul_fifo_sync_scaling_validation.py
  expected_scope:
    - runtime flag or entrypoint for resident execution
    - explicit ownership of device state allocation and final dump
    - no per-step host/device state transfer in the resident path
    - existing non-resident runner remains available for comparison
    - resident mode refuses per-step patch inputs until script semantics are defined
  acceptance:
    - interface is documented in README/status
    - implementation task names exact files or modules before editing runtime code
    - no true-resident speedup claim until a resident GPU run and matching CPU baseline pass
  status: done
  next_action: implement_true_resident_gpu_runtime_flag

implement_true_resident_gpu_runtime_flag:
  goal: make resident execution explicit rather than relying on proxy gate wording
  edit_scope:
    - src/tools/run_vl_hybrid.py
    - src/hybrid/run_vl_hybrid.c
    - src/tools/run_tlul_fifo_sync_scaling_validation.py
  behavior:
    - --resident-steps forwards RUN_VL_HYBRID_RESIDENT_STEPS=1
    - resident mode reports resident_mode=true in stdout/report
    - resident mode initially rejected --patch and --patch-script before schedule semantics existed
    - final dump remains allowed
  status: done
  result:
    resident_gpu_gate: pass
    cpu_exact_loop_baseline: pass
    best_gpu_over_cpu_ratio: 1.2076
  next_action: package_xuantie_true_resident_runtime_boundary

package_xuantie_true_resident_runtime_boundary:
  goal: document the first non-TL-UL true resident runtime boundary without overclaiming broad generality
  include:
    - XuanTie-E902 resident flag semantics
    - resident GPU gate command and matching CPU exact-loop command
    - accepted claim limited to nstates=128 steps=64 on XuanTie-E902
    - non-claims for full RTL generality and patch-script resident semantics
  status: done
  accepted_claim: XuanTie-E902 resident mode beats CPU exact-loop baseline at nstates=128 steps=64
  best_gpu_over_cpu_ratio: 1.2076
  next_action: define_resident_runtime_regression_contract

define_resident_runtime_regression_contract:
  goal: prevent resident-mode regressions before broadening to another non-TL-UL target
  include:
    - run_vl_hybrid.py --resident-steps guards host patch behavior
    - resident gate report records resident_steps=true
    - stdout tail includes resident_mode: true
    - README boundary remains limited to XuanTie-E902 nstates=128 steps=64
  test: tests/contract/test_resident_runtime_contract.py
  command: python3 -m unittest tests.contract.test_resident_runtime_contract
  status: pass
  next_action: select_next_resident_runtime_breadth_or_patch_semantics

select_next_resident_runtime_breadth_or_patch_semantics:
  if prioritizing target breadth:
    select the next non-TL-UL resident runtime candidate and define a matching gate
  else:
    define resident --patch / --patch-script semantics before more breadth
  current_bias: target breadth, because patch semantics are explicitly out of the packaged XuanTie boundary
  decision: prioritize target breadth
  next_action: select_next_non_tlul_resident_candidate

select_next_non_tlul_resident_candidate:
  goal: choose the next non-TL-UL target to test the resident runtime beyond XuanTie-E902
  weakest_point: the minimal repo currently carries only one non-TL-UL source asset, so broadening requires selecting and importing a bounded source/test boundary from the old repo.
  selected_candidate: veer_el2
  selection_reason:
    - old repo evidence records VeeR-EL2 gpu_cov_gate dhry reaching TEST_PASSED
    - old repo design scope packet ranks VeeR family candidates at candidate_score 14
    - old repo already has a bounded launch template for VeeR-EL2
  candidate_policy:
    - prefer a target with existing old-repo campaign evidence and small source boundary
    - define gate shape before copying assets
    - do not import broad historical work/output artifacts
    - keep resident patch/script semantics out of scope unless the candidate requires them
  source_evidence:
    - old_repo:output/family_readiness/veer_el2_gpu_toggle_readiness.md
    - old_repo:output/design_scope_expansion_packet.json
    - old_repo:config/slice_launch_templates/veer_el2.json
  status: done_selected_before_asset_copy
  next_action: define_veer_el2_resident_gate_before_asset_copy

define_veer_el2_resident_gate_before_asset_copy:
  goal: define the VeeR-EL2 resident runtime gate shape before importing its source/test boundary
  weakest_point: VeeR-EL2 is selected from old-repo evidence, but the minimal repo has not copied its RTL/test assets and has no resident-mode result for it yet.
  selected_candidate: veer_el2
  planned_gate:
    name: veer_el2_resident_workload
    target: VeeR.veer_el2
    source_template: config/slice_launch_templates/veer_el2.json
    gpu_gate: config/scaling_gates/veer_el2_resident_workload.json
    cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_resident_workload.json
    initial_workload_shapes:
      - nstates=64 steps=64 resident_steps=true
      - nstates=128 steps=64 resident_steps=true
  acceptance:
    - gate config names only the bounded VeeR-EL2 source/test boundary to be copied
    - asset copy excludes old repo work/output history
    - resident mode must report resident_mode=true before any speedup claim
    - matching CPU exact-loop baseline must be defined before comparing throughput
  status: done_gate_defined_before_asset_copy
  non_claims:
    - VeeR-EL2 resident runtime is not proven yet
    - broad VeeR family support is not proven yet
    - resident patch/script semantics remain out of scope
  next_action: materialize_veer_el2_asset_boundary

materialize_veer_el2_asset_boundary:
  goal: copy only the bounded VeeR-EL2 source/test boundary required by the defined launch template and resident gates
  weakest_point: gate config now exists, but the minimal repo still lacks VeeR-EL2 RTL/test assets and therefore cannot build or run the gate.
  copy_policy:
    - copy descriptor, license, required src tree, and dhry program input from old repo
    - exclude old repo work/output history and transient /tmp evidence
    - preserve config/ as the operational source of truth
  expected_paths:
    - third_party/rtlmeter/designs/VeeR-EL2/descriptor.yaml
    - third_party/rtlmeter/designs/VeeR-EL2/LICENSE-VeeR-EL2
    - third_party/rtlmeter/designs/VeeR-EL2/src/
    - third_party/rtlmeter/designs/VeeR-EL2/tests/dhry/program.hex
    - third_party/rtlmeter/designs/VeeR-EL2/tests/hello/program.hex
    - third_party/rtlmeter/designs/VeeR-EL2/tests/cmark/program.hex
    - third_party/rtlmeter/designs/VeeR-EL2/tests/cmark_iccm/program.hex
    - third_party/rtlmeter/designs/VeeR-EL2/tests/veer_el2_coverage_regions.json
    - third_party/rtlmeter/designs/VeeR-EL2/tests/veer_el2_program_hex_target_config.json
  status: done_asset_boundary_materialized
  copied_size: about_1_8MiB
  next_action: validate_veer_el2_asset_boundary

validate_veer_el2_asset_boundary:
  goal: prove the copied VeeR-EL2 asset boundary is internally consistent before attempting Verilator obj_dir generation
  weakest_point: the assets are present, but no Verilator build or resident runtime result exists for VeeR-EL2 in the minimal repo yet.
  checks:
    - descriptor exists
    - license exists
    - launch template coverage_tb_path exists
    - launch template dhry program input exists
    - resident GPU and CPU gate configs are registered
    - no old repo work/output history is copied under the VeeR-EL2 boundary
    - descriptor-referenced src/tests files exist
  status: pass_contract
  test: tests/contract/test_resident_runtime_contract.py
  next_action: generate_veer_el2_verilator_obj_dir

generate_veer_el2_verilator_obj_dir:
  goal: run stock Verilator against the copied VeeR-EL2 gpu_cov_gate boundary and produce artifacts/veer_el2_obj_dir
  weakest_point: boundary validation passed, but build behavior in the minimal repo is not proven and may expose include/order differences.
  planned_mdir: artifacts/veer_el2_obj_dir
  top_module: veer_el2_gpu_cov_tb
  support_rtl:
    - third_party/rtlmeter/rtl/__rtlmeter_utils.sv
    - third_party/rtlmeter/rtl/__rtlmeter_top_include.vh
  verilator_define:
    __RTLMETER_MAIN_CLOCK: veer_el2_gpu_cov_tb.dut.core_clk
  status: pass_with_warnings
  next_action: build_veer_el2_gpu_cubin

build_veer_el2_gpu_cubin:
  goal: build the VeeR-EL2 GPU cubin from artifacts/veer_el2_obj_dir
  weakest_point: Verilator obj_dir exists, but GPU kernel generation may expose VeeR-specific lowering/classifier gaps.
  mdir: artifacts/veer_el2_obj_dir
  storage_size: 431808
  cubin: artifacts/veer_el2_obj_dir/vl_batch_gpu.cubin
  cubin_bytes: 5220896
  status: pass
  next_action: run_veer_el2_gpu_smoke

run_veer_el2_gpu_smoke:
  goal: run one small VeeR-EL2 GPU smoke from the generated cubin before making resident throughput claims
  weakest_point: cubin builds, but no VeeR-EL2 runtime execution result exists yet.
  mdir: artifacts/veer_el2_obj_dir
  smoke_shape: nstates=1 steps=1
  state_dump: artifacts/veer_el2_obj_dir/veer_el2_gpu_smoke_state.bin
  dump_bytes: 431808
  status: pass
  next_action: define_veer_el2_cpu_reference_contract

define_veer_el2_cpu_reference_contract:
  goal: define how to obtain a CPU reference state and normalized compare for VeeR-EL2 before resident throughput gates
  weakest_point: the CPU/GPU one-state correctness contract now passes, but VeeR-EL2 resident throughput is still unmeasured and the CPU reference probe stdout contains Verilog readmem warnings before JSON.
  host_probe:
    build: make -C src/hybrid veer_el2_host_probe
    binary: artifacts/veer_el2_obj_dir/veer_el2_host_probe
    source: src/hybrid/tlul_slice_host_probe.cpp
    non_tlul_mode: PROBE_TLUL_SIGNALS=0
  cpu_reference:
    state_dump: artifacts/veer_el2_obj_dir/veer_el2_cpu_reference_state.bin
    probe_stdout: artifacts/veer_el2_obj_dir/veer_el2_cpu_reference_probe.json
    note: probe stdout is not strict JSON because VeeR emits readmem warnings before the JSON object
  gpu_from_cpu_reference:
    state_dump: artifacts/veer_el2_obj_dir/veer_el2_gpu_from_cpu_reference_state.bin
  compare:
    report: reports/veer_el2_cpu_vs_gpu_from_cpu_init_compare.json
    acceptance_policy: normalized_final_state_equivalence
    result: pass
    included_member_count: 6494
    included_byte_count: 431346
    functional_non_internal_mismatch_bytes: 0
  status: pass_normalized_final_state_equivalence
  next_action: run_veer_el2_resident_workload_gate

run_veer_el2_resident_workload_gate:
  goal: run the predefined VeeR-EL2 resident workload gate after CPU/GPU correctness has a normalized baseline
  weakest_point: resident mode now runs, but the matching CPU exact-loop baseline is still faster at the current 64/128-state shapes.
  gpu_gate: config/scaling_gates/veer_el2_resident_workload.json
  cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_resident_workload.json
  gpu_report: reports/veer_el2_resident_workload_scaling.json
  cpu_report: reports/veer_el2_cpu_exact_loop_resident_workload.json
  result:
    resident_gpu_gate: pass
    cpu_exact_loop_gate: pass
    resident_mode_observed: true
    nstates_64_steps_64_gpu_over_cpu_ratio: 0.6021517508485191
    nstates_128_steps_64_gpu_over_cpu_ratio: 0.8295362109911266
  status: pass_cpu_favorable
  next_action: define_veer_el2_larger_resident_workload_gate

define_veer_el2_larger_resident_workload_gate:
  goal: increase the VeeR-EL2 resident workload shape before deciding whether to package or abandon this candidate for speedup claims
  weakest_point: current VeeR-EL2 resident shapes pass functionally but do not beat CPU, so packaging now would overstate the project benefit.
  gpu_gate: config/scaling_gates/veer_el2_larger_resident_workload.json
  cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_larger_resident_workload.json
  shapes:
    - nstates=256 steps=64 resident_steps=true
    - nstates=512 steps=64 resident_steps=true
  acceptance:
    - define matching GPU and CPU exact-loop gate configs before running
    - require resident_mode=true for GPU
    - compare only same nstates/steps shapes
    - if still CPU-favorable, record VeeR-EL2 as correctness/breadth win but not throughput win
  status: done_defined_before_run
  next_action: run_veer_el2_larger_resident_workload_gate

run_veer_el2_larger_resident_workload_gate:
  goal: run the larger VeeR-EL2 resident GPU gate and then the matching CPU exact-loop baseline
  weakest_point: the larger gate proves a bounded GPU win, but the claim is limited to the measured VeeR-EL2 shapes and does not imply broad VeeR family support.
  gpu_gate: config/scaling_gates/veer_el2_larger_resident_workload.json
  cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_larger_resident_workload.json
  gpu_report: reports/veer_el2_larger_resident_workload_scaling.json
  cpu_report: reports/veer_el2_cpu_exact_loop_larger_resident_workload.json
  result:
    resident_gpu_gate: pass
    cpu_exact_loop_gate: pass
    resident_mode_observed: true
    nstates_256_steps_64_gpu_over_cpu_ratio: 2.3705374232694565
    nstates_512_steps_64_gpu_over_cpu_ratio: 2.45997554488639
  status: pass_gpu_win
  next_action: package_veer_el2_larger_resident_boundary

package_veer_el2_larger_resident_boundary:
  goal: document the bounded VeeR-EL2 larger resident workload win without overstating target generality
  weakest_point: the result is strong at larger resident shapes, but it is still one VeeR-EL2 wrapper and does not prove full CPU application throughput or broad VeeR family support.
  accepted_claim:
    - VeeR-EL2 larger resident GPU gate beats the matching single-process CPU repeated-eval loop at nstates=256/512, steps=64
  non_claims:
    - not broad VeeR family support
    - not full RTL application throughput
    - not resident patch/script semantics
  status: done_packaged_boundary
  next_action: commit_veer_el2_larger_resident_boundary

commit_veer_el2_larger_resident_boundary:
  goal: create a source commit for the VeeR-EL2 host-probe, larger resident gate, docs, and contract updates
  weakest_point: the generated reports and artifacts prove the result locally, but the next operational axis was not yet selected in the minimal repo canonical state.
  include:
    - src/hybrid/Makefile
    - src/hybrid/tlul_slice_host_probe.cpp
    - config/scaling_gates/veer_el2_larger_resident_workload.json
    - config/scaling_gates/veer_el2_cpu_exact_loop_larger_resident_workload.json
    - config/selection.json
    - config/targets.json
    - docs/status.md
    - docs/roadmap.md
    - README.md
    - tests/contract/test_resident_runtime_contract.py
  exclude:
    - artifacts/**
    - reports/**
  status: done_620cf74
  next_action: define_resident_patch_script_semantics

define_resident_patch_script_semantics:
  goal: define how resident mode should handle per-step input changes without falling back to host-device copies on every step
  weakest_point: resident mode initially rejected --patch and --patch-script, so workloads needing changing inputs needed a device-resident schedule path.
  reason_for_priority:
    - XuanTie-E902 and VeeR-EL2 already provide bounded non-TL-UL resident breadth
    - the remaining practical gap is communication reduction with changing inputs
    - defining semantics before implementation avoids ambiguous host/GPU ownership
  proposed_semantics:
    - --resident-steps keeps the full state array device-resident across eval steps
    - static init-state upload remains a one-time pre-run transfer
    - per-step patches must be represented as a compact device-side patch schedule before the resident loop begins
    - host must not perform per-step cuMemcpyHtoD during resident mode
    - final DtoH remains optional and occurs only at the boundary when --dump-state is requested
  contract:
    file: config/resident_patch_script_semantics.json
    status: runtime_schedule_upload_smoke_passed
    next_action: define_resident_patch_schedule_validation_gate
  first_contract:
    - reject direct --patch until it is deliberately mapped to a one-step schedule shorthand
    - describe the resident patch buffer ABI before claiming changing-input throughput
  status: done_runtime_schedule_upload_implemented_contract_pending
  next_action: define_resident_patch_schedule_validation_gate

implement_resident_patch_schedule_upload:
  goal: implement the resident patch schedule upload path without reintroducing per-step host-device copies
  weakest_point: runtime schedule upload has a regenerated-cubin smoke pass, but no accepted changing-input throughput gate exists yet.
  source_contract: config/resident_patch_script_semantics.json
  implementation_scope:
    - preserve existing non-resident --patch and --patch-script behavior
    - upload resident patch schedule once before the resident launch loop
    - keep per-step cuMemcpyHtoD out of resident mode
    - retain final DtoH only at --dump-state boundary
  status: done_smoke_pass
  next_action: validate_resident_patch_schedule_upload

validate_resident_patch_schedule_upload:
  goal: regenerate a cubin with vl_apply_patch_schedule_gpu and prove resident --patch-script changes inputs without per-step HtoD patches
  weakest_point: smoke proves runtime wiring, but throughput/correctness cannot be claimed until a gate defines workload shape and CPU baseline.
  source_contract: config/resident_patch_script_semantics.json
  smoke:
    target: tlul_fifo_sync
    cubin: artifacts/tlul_fifo_sync_obj_dir/vl_batch_gpu.cubin
    patch_kernel: vl_apply_patch_schedule_gpu
    result: pass
    resident_patch_schedule:
      logical_steps: 6
      records: 3
      blocks: 3
  status: done_smoke_pass
  next_action: define_resident_patch_schedule_validation_gate

define_resident_patch_schedule_validation_gate:
  goal: define the first accepted changing-input resident patch schedule gate and matching CPU comparison surface
  weakest_point: a one-state smoke can hide overhead shape; gate must include enough steps/states to test communication reduction rather than just function resolution.
  gate: config/scaling_gates/tlul_fifo_sync_resident_patch_schedule.json
  runner: src/tools/run_tlul_fifo_sync_scaling_validation.py
  report: reports/tlul_fifo_sync_resident_patch_schedule.json
  status: done
  next_action: run_resident_patch_schedule_validation_gate

run_resident_patch_schedule_validation_gate:
  goal: run resident changing-input schedule validation on tlul_fifo_sync using a regenerated cubin
  weakest_point: this gate can validate resident schedule mechanics, but CPU changing-input baseline is still a follow-up.
  gate: config/scaling_gates/tlul_fifo_sync_resident_patch_schedule.json
  report: reports/tlul_fifo_sync_resident_patch_schedule.json
  result:
    status: pass
    runs:
      - resident_patch_schedule_smoke_1x6
      - resident_patch_schedule_batch_512x32
  status: done
  next_action: define_matching_cpu_changing_input_patch_baseline

define_matching_cpu_changing_input_patch_baseline:
  goal: define how CPU exact-loop baseline should model per-step changing inputs before speedup claims
  weakest_point: the existing CPU exact-loop probe repeats eval steps, but it does not consume the same patch script semantics as the resident GPU path.
  gate: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_resident_patch_schedule.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --exact-loop
  report: reports/tlul_fifo_sync_cpu_exact_loop_resident_patch_schedule.json
  status: done
  next_action: run_matching_cpu_changing_input_patch_baseline

run_matching_cpu_changing_input_patch_baseline:
  goal: run CPU exact-loop baseline with the same patch script shapes as the resident GPU validation gate
  weakest_point: CPU byte patches assume root storage offsets match the GPU storage layout; this is acceptable for the current copied root image contract but must remain a bounded claim.
  gate: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_resident_patch_schedule.json
  source_gpu_report: reports/tlul_fifo_sync_resident_patch_schedule.json
  report: reports/tlul_fifo_sync_cpu_exact_loop_resident_patch_schedule.json
  result:
    status: pass
    gpu_over_cpu_throughput_ratio:
      resident_patch_schedule_smoke_1x6: 0.005627988093961567
      resident_patch_schedule_batch_512x32: 3.1160088024052413
  status: done
  next_action: package_resident_patch_schedule_boundary

package_resident_patch_schedule_boundary:
  goal: document the bounded resident changing-input claim and non-claims after GPU and CPU gates pass
  weakest_point: the positive result is shape-specific; small smoke is CPU-favorable and broad RTL coverage is not proven.
  accepted_claim:
    target: tlul_fifo_sync
    shape: nstates=512 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 3.1160088024052413
  non_claims:
    - no broad target-breadth claim
    - no full RTL application throughput claim
    - CPU patch baseline relies on matching root storage byte offsets
  status: done
  next_action: select_next_resident_patch_schedule_breadth_or_commit

select_next_resident_patch_schedule_breadth_or_commit:
  goal: decide whether to commit the bounded tlul_fifo_sync resident patch schedule boundary or broaden it to a second seed first
  weakest_point: broadening before committing risks mixing the validated boundary with the next experiment; committing now preserves a clean checkpoint.
  options:
    - commit_current_boundary
    - port_patch_schedule_gate_to_tlul_sink
    - port_patch_schedule_gate_to_non_tlul_resident_target
  recommended_next: commit_current_boundary
  status: done_committed
  next_action: port_patch_schedule_gate_to_tlul_sink

port_patch_schedule_gate_to_tlul_sink:
  goal: broaden resident changing-input patch schedule validation from tlul_fifo_sync to the second TL-UL seed
  weakest_point: this improves TL-UL breadth, but still does not prove non-TL-UL target breadth.
  gpu_gate: config/scaling_gates/tlul_sink_resident_patch_schedule.json
  cpu_gate: config/scaling_gates/tlul_sink_cpu_exact_loop_resident_patch_schedule.json
  gpu_report: reports/tlul_sink_resident_patch_schedule.json
  cpu_report: reports/tlul_sink_cpu_exact_loop_resident_patch_schedule.json
  result:
    status: pass
    gpu_over_cpu_throughput_ratio:
      tlul_sink_resident_patch_schedule_smoke_1x6: 0.008255714084067339
      tlul_sink_resident_patch_schedule_batch_512x32: 2.002480966457029
  status: done
  next_action: package_two_seed_resident_patch_schedule_boundary

package_two_seed_resident_patch_schedule_boundary:
  goal: document the two-seed TL-UL resident changing-input patch schedule claim and remaining non-claims
  weakest_point: both TL-UL seeds pass at 512x32, but this still is not non-TL-UL resident patch schedule breadth.
  accepted_claims:
    - target: tlul_fifo_sync
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 3.1160088024052413
    - target: tlul_sink
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 2.002480966457029
  non_claims:
    - no non-TL-UL resident patch schedule breadth
    - no full RTL application throughput claim
    - small 1x6 smoke remains CPU-favorable on both seeds
  status: done
  next_action: commit_two_seed_resident_patch_schedule_boundary

commit_two_seed_resident_patch_schedule_boundary:
  goal: commit the two-seed TL-UL resident patch schedule boundary before starting non-TL-UL breadth work
  weakest_point: without a commit boundary, the next breadth experiment can blur the validated TL-UL claim.
  commit: 9bddec4
  status: done
  next_action: select_non_tlul_resident_patch_schedule_breadth_candidate

select_non_tlul_resident_patch_schedule_breadth_candidate:
  goal: choose the first non-TL-UL resident changing-input patch schedule target after two TL-UL seeds passed
  weakest_point: tlul_fifo_sync and tlul_sink prove the mechanism on small OpenTitan TL-UL seeds, not non-TL-UL breadth or full RTL application throughput.
  candidate_order:
    - veer_el2
    - xuantie_e902
  recommended_next: define_veer_el2_resident_patch_schedule_gate
  selected: veer_el2
  status: done
  next_action: define_veer_el2_resident_patch_schedule_gate

define_veer_el2_resident_patch_schedule_gate:
  goal: define VeeR-EL2 GPU and matching CPU exact-loop resident patch schedule gates without adding new runner logic
  weakest_point: the gate is defined with byte-offset patch stimuli; it does not yet prove runtime pass, speedup, or VeeR program semantics.
  gpu_gate: config/scaling_gates/veer_el2_resident_patch_schedule.json
  cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_resident_patch_schedule.json
  gpu_report: reports/veer_el2_resident_patch_schedule.json
  cpu_report: reports/veer_el2_cpu_exact_loop_resident_patch_schedule.json
  status: done
  next_action: run_veer_el2_resident_patch_schedule_gate

run_veer_el2_resident_patch_schedule_gate:
  goal: run the first non-TL-UL resident changing-input patch schedule GPU gate on VeeR-EL2
  weakest_point: until the VeeR-EL2 gate runs, non-TL-UL patch schedule breadth is only planned, not measured.
  gate: config/scaling_gates/veer_el2_resident_patch_schedule.json
  report: reports/veer_el2_resident_patch_schedule.json
  status: done
  next_action: run_veer_el2_cpu_exact_loop_resident_patch_schedule_gate

run_veer_el2_cpu_exact_loop_resident_patch_schedule_gate:
  goal: run the matching VeeR-EL2 CPU exact-loop patch schedule baseline and compare against the GPU report
  weakest_point: the CPU baseline applies byte patches directly to root storage, so the claim is bounded to matching root-storage offsets rather than VeeR program semantics.
  gate: config/scaling_gates/veer_el2_cpu_exact_loop_resident_patch_schedule.json
  report: reports/veer_el2_cpu_exact_loop_resident_patch_schedule.json
  accepted_claim:
    veer_el2_resident_patch_schedule_batch_512x32: 2.8489279680483475
  non_claims:
    - veer_el2_resident_patch_schedule_smoke_1x6 remains CPU-favorable with ratio 0.005922418043868761
    - not broad VeeR family support
    - not full RTL application throughput
    - byte patch offsets are validation stimuli, not VeeR ISA/program semantics
  status: done
  next_action: package_veer_el2_resident_patch_schedule_boundary

package_veer_el2_resident_patch_schedule_boundary:
  goal: package the first non-TL-UL resident patch schedule boundary before broadening further
  weakest_point: the measured VeeR-EL2 win proves one non-TL-UL generated design shape, not broad target coverage.
  accepted_claims:
    - target: tlul_fifo_sync
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 3.1160088024052413
    - target: tlul_sink
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 2.002480966457029
    - target: veer_el2
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 2.8489279680483475
  non_claims:
    - no broad non-TL-UL resident patch schedule breadth
    - no broad VeeR family support
    - no full RTL application throughput claim
    - byte patch offsets are validation stimuli, not target program semantics
    - small 1x6 smoke remains CPU-favorable on all measured patch-schedule seeds
  status: done
  next_action: commit_veer_el2_resident_patch_schedule_boundary

commit_veer_el2_resident_patch_schedule_boundary:
  goal: commit the packaged VeeR-EL2 resident patch schedule boundary before the next breadth experiment
  weakest_point: without a commit boundary, the first non-TL-UL patch schedule claim can be mixed with later target-breadth attempts.
  commit: 5697daa
  status: done
  next_action: select_next_patch_schedule_breadth_after_veer_el2

select_next_patch_schedule_breadth_after_veer_el2:
  goal: choose the next resident patch schedule breadth axis after TL-UL two-seed and VeeR-EL2 pass at the bounded 512x32 shape
  weakest_point: adding another design-family seed improves breadth, but it still may not prove application-like input semantics or full RTL application throughput.
  candidates:
    - target: xuantie_e902
      reason: existing non-TL-UL resident workload artifacts and host probe are already present in the minimal repo
      next_action: define_xuantie_e902_resident_patch_schedule_gate
    - target: application_like_patch_semantics
      reason: move beyond arbitrary root byte patches toward meaningful input/ROM/program-driven state changes
      next_action: define_application_like_patch_schedule_semantics
  recommended_next: define_xuantie_e902_resident_patch_schedule_gate
  selected: xuantie_e902
  status: done
  next_action: define_xuantie_e902_resident_patch_schedule_gate

define_xuantie_e902_resident_patch_schedule_gate:
  goal: define XuanTie-E902 GPU and matching CPU exact-loop resident patch schedule gates without adding new runner logic
  weakest_point: the gate uses byte-offset patch stimuli; it has not yet run and does not prove XuanTie program semantics.
  gpu_gate: config/scaling_gates/xuantie_e902_resident_patch_schedule.json
  cpu_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_resident_patch_schedule.json
  gpu_report: reports/xuantie_e902_resident_patch_schedule.json
  cpu_report: reports/xuantie_e902_cpu_exact_loop_resident_patch_schedule.json
  status: done
  next_action: run_xuantie_e902_resident_patch_schedule_gate

run_xuantie_e902_resident_patch_schedule_gate:
  goal: run the second non-TL-UL resident changing-input patch schedule GPU gate on XuanTie-E902
  weakest_point: until the XuanTie-E902 gate runs, the third design-family patch schedule breadth point is only defined, not measured.
  gate: config/scaling_gates/xuantie_e902_resident_patch_schedule.json
  report: reports/xuantie_e902_resident_patch_schedule.json
  status: done
  next_action: run_xuantie_e902_cpu_exact_loop_resident_patch_schedule_gate

run_xuantie_e902_cpu_exact_loop_resident_patch_schedule_gate:
  goal: run the matching XuanTie-E902 CPU exact-loop patch schedule baseline and compare against the GPU report
  weakest_point: the win is modest and bounded to 128x32; byte patches are validation stimuli, not XuanTie program semantics.
  gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_resident_patch_schedule.json
  report: reports/xuantie_e902_cpu_exact_loop_resident_patch_schedule.json
  accepted_claim:
    xuantie_e902_resident_patch_schedule_batch_128x32: 1.1724144754038845
  non_claims:
    - xuantie_e902_resident_patch_schedule_smoke_1x6 remains CPU-favorable with ratio 0.01038989322830183
    - not broad XuanTie family support
    - not full RTL application throughput
    - byte patch offsets are validation stimuli, not XuanTie ISA/program semantics
  status: done
  next_action: package_xuantie_e902_resident_patch_schedule_boundary

package_xuantie_e902_resident_patch_schedule_boundary:
  goal: package the second non-TL-UL resident patch schedule boundary before moving toward application-like patch semantics
  weakest_point: XuanTie-E902 adds breadth but still relies on arbitrary root byte patches rather than application-level input or ROM semantics.
  accepted_claims:
    - target: tlul_fifo_sync
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 3.1160088024052413
    - target: tlul_sink
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 2.002480966457029
    - target: veer_el2
      shape: nstates=512 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 2.8489279680483475
    - target: xuantie_e902
      shape: nstates=128 logical_patch_steps=32
      gpu_over_cpu_throughput_ratio: 1.1724144754038845
  non_claims:
    - no broad non-TL-UL resident patch schedule breadth
    - no broad XuanTie family support
    - no full RTL application throughput claim
    - byte patch offsets are validation stimuli, not target program semantics
    - application-like input, ROM, or program-delta semantics are not defined yet
  status: next
  next_action: commit_xuantie_e902_resident_patch_schedule_boundary

commit_xuantie_e902_resident_patch_schedule_boundary:
  goal: commit the packaged XuanTie-E902 resident patch schedule boundary before defining application-like patch semantics
  weakest_point: without a commit boundary, the measured XuanTie-E902 byte-patch claim can be mixed with the next semantic broadening step.
  commit: 30e17bd
  status: done
  next_action: define_application_like_patch_schedule_semantics

define_application_like_patch_schedule_semantics:
  goal: define the first application-like resident patch schedule semantics after multi-seed byte-patch throughput wins
  weakest_point: byte patches prove communication reduction mechanics, but not meaningful RTL stimulus semantics; the next gate must map patches to input, ROM, or program-delta changes.
  source_contract: config/resident_patch_script_semantics.json
  candidate_semantics:
    - input_stream_delta
    - rom_or_memory_init_delta
    - program_image_delta
  selected_semantic: rom_or_memory_init_delta
  selection_reason: ROM or memory init deltas are closer to design-level stimuli than arbitrary root byte offsets while still fitting the one-time schedule upload model.
  acceptance:
    - selected semantic can be described without clone-local paths
    - selected semantic reuses one-time schedule upload and forbids per-step host-device patch copies
    - selected semantic has a matching CPU exact-loop baseline plan
    - selected semantic does not claim ISA/program correctness from arbitrary byte offsets
  status: done
  next_action: define_rom_or_memory_init_delta_patch_gate

define_rom_or_memory_init_delta_patch_gate:
  goal: define the first ROM or memory initialization delta resident patch schedule gate
  weakest_point: selecting ROM/memory delta improves semantic clarity, but the gate still needs target-specific mapping from memory image bytes to the generated root storage layout.
  source_contract: config/resident_patch_script_semantics.json
  selected_target: xuantie_e902
  gpu_gate: config/scaling_gates/xuantie_e902_rom_memory_delta_patch_schedule.json
  cpu_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule.json
  gpu_report: reports/xuantie_e902_rom_memory_delta_patch_schedule.json
  cpu_report: reports/xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule.json
  acceptance:
    - gate identifies a target with existing generated artifacts and CPU host probe
    - gate explains how memory-image deltas map to resident patch schedule records
    - gate preserves one-time schedule upload and no per-step host-device copies
    - matching CPU exact-loop baseline is defined with the same delta sequence
  status: done
  next_action: run_xuantie_e902_rom_memory_delta_patch_schedule_gate

run_xuantie_e902_rom_memory_delta_patch_schedule_gate:
  goal: run the first ROM or memory initialization delta resident patch schedule GPU gate on XuanTie-E902
  weakest_point: this first gate still uses explicit root-storage offsets as a proxy mapping; named ROM/memory symbol mapping remains a later precision step.
  gate: config/scaling_gates/xuantie_e902_rom_memory_delta_patch_schedule.json
  report: reports/xuantie_e902_rom_memory_delta_patch_schedule.json
  status: done
  next_action: run_xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule_gate

run_xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule_gate:
  goal: run the matching XuanTie-E902 CPU exact-loop ROM/memory delta baseline and compare against the GPU report
  weakest_point: the win is bounded to a proxy root-storage mapping; named ROM or memory symbol mapping is not proven.
  gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule.json
  report: reports/xuantie_e902_cpu_exact_loop_rom_memory_delta_patch_schedule.json
  accepted_claim:
    xuantie_e902_rom_memory_delta_batch_128x32: 1.442536802751107
  non_claims:
    - xuantie_e902_rom_memory_delta_smoke_1x6 remains CPU-favorable with ratio 0.024056822624438708
    - not broad XuanTie family support
    - not full RTL application throughput
    - not named-symbol ROM/memory mapping
    - not ISA/program correctness
  status: done
  next_action: package_rom_memory_delta_patch_schedule_boundary

package_rom_memory_delta_patch_schedule_boundary:
  goal: package the first ROM/memory delta proxy resident patch schedule boundary
  weakest_point: the result proves the selected communication-reduction semantics as a proxy mapping, not a named ROM symbol or program correctness claim.
  accepted_claim:
    target: xuantie_e902
    semantic: rom_or_memory_init_delta
    shape: nstates=128 logical_patch_steps=32
    gpu_over_cpu_throughput_ratio: 1.442536802751107
  non_claims:
    - not named-symbol ROM/memory mapping
    - not ISA/program correctness
    - not full software boot correctness
    - not full RTL application throughput
    - small 1x6 smoke remains CPU-favorable with ratio 0.024056822624438708
  status: done
  next_action: commit_rom_memory_delta_patch_schedule_boundary

commit_rom_memory_delta_patch_schedule_boundary:
  goal: commit the packaged ROM/memory delta proxy boundary before increasing semantic precision
  weakest_point: without a commit boundary, the proxy mapping claim can be mixed with later named-symbol ROM mapping work.
  commit: 010fb86
  status: done
  next_action: define_named_rom_memory_symbol_mapping_gate

define_named_rom_memory_symbol_mapping_gate:
  goal: define a gate that maps ROM or memory init deltas to named generated symbols or documented memory image regions instead of raw root offsets
  weakest_point: the existing ROM/memory delta result is still a root-storage proxy; named mapping may require target-specific symbol discovery in generated Verilator root storage.
  source_contract: config/resident_patch_script_semantics.json
  candidate_target: xuantie_e902
  candidate_fields:
    - xuantie_e902_gpu_cov_tb.dut.x_soc.x_cpu_sub_system_ahb.x_iahb_mem_ctrl.ram0..3.mem
    - xuantie_e902_gpu_cov_tb.dut.x_soc.x_smem_ctrl.ram0..3.mem
    - xuantie_e902_gpu_cov_tb.dut.x_soc.x_dmem_ctrl.ram0..3.mem
  acceptance:
    - identify candidate ROM/memory storage fields or document why only proxy offsets are currently available
    - define GPU gate and CPU exact-loop baseline using the same named mapping or a documented unresolved mapping fallback
    - preserve one-time schedule upload and no per-step host-device copies
    - keep non-claims for ISA/program correctness and full software boot
  status: done_candidate_fields_inspected
  next_action: define_xuantie_e902_named_rom_memory_mapping_contract

define_xuantie_e902_named_rom_memory_mapping_contract:
  goal: turn the inspected XuanTie-E902 RAM field candidates into an explicit mapping contract before adding or running another throughput gate
  weakest_point: the candidate field names are generated Verilator storage names; without an address/byte-lane contract, a patch against them can still be a renamed proxy rather than a defensible ROM/memory-image delta.
  source_contract: config/resident_patch_script_semantics.json
  candidate_target: xuantie_e902
  selected_family: iahb_instruction_memory
  source_rtl:
    - third_party/rtlmeter/designs/XuanTie-E902/src/tb.v
    - third_party/rtlmeter/designs/XuanTie-E902/src/mem_ctrl.v
  mapping_contract:
    memory_image_source: case.pat loaded through mem_inst_temp
    word_index_mapping: case.pat word index i maps to x_iahb_mem_ctrl.ram0..3.mem[i]
    testbench_initialization_lanes:
      ram0: word[31:24]
      ram1: word[23:16]
      ram2: word[15:8]
      ram3: word[7:0]
    ahb_readback_lanes: mem_ctrl readback assembles {ram3, ram2, ram1, ram0}
    required_gate_note: the named gate must state whether its deltas follow testbench image order or AHB readback order
  unselected_families:
    - x_smem_ctrl.ram0..3.mem
    - x_dmem_ctrl.ram0..3.mem
  acceptance:
    - document which candidate family is instruction memory, scratch/shared memory, or data memory for this target
    - define byte-lane mapping from memory-image deltas to ram0..3.mem indices
    - define unresolved fallback if a named family cannot be tied to a memory-image region
    - keep GPU and CPU baselines on the same named mapping
  status: done_contract_defined
  next_action: define_xuantie_e902_named_rom_memory_mapping_gate

define_xuantie_e902_named_rom_memory_mapping_gate:
  goal: define GPU and CPU exact-loop gates that apply XuanTie-E902 case.pat deltas through the named IAHB instruction-memory mapping instead of raw root offsets
  weakest_point: even with named IAHB mapping, this still validates bounded memory-image delta communication reduction, not ISA correctness or full software boot.
  source_contract: config/resident_patch_script_semantics.json
  selected_target: xuantie_e902
  selected_family: iahb_instruction_memory
  gpu_gate: config/scaling_gates/xuantie_e902_named_rom_memory_mapping.json
  cpu_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json
  runtime_support_status: named_mapping_lowering_required
  acceptance:
    - define GPU gate patch records from named case.pat word/lane deltas
    - define matching CPU exact-loop baseline with the same named mapping
    - keep one-time schedule upload and no per-step host-device copies
    - preserve non-claims for ISA correctness, full software boot, and broad XuanTie family support
  status: done_gates_defined
  next_action: implement_xuantie_e902_named_rom_memory_mapping_lowering

implement_xuantie_e902_named_rom_memory_mapping_lowering:
  goal: lower XuanTie-E902 named case.pat word/lane deltas to resident patch records using generated root field offsets for x_iahb_mem_ctrl.ram0..3.mem
  weakest_point: the lowering proves generated-symbol patch schedule execution, but it is still a bounded memory-image delta throughput claim rather than ISA/program correctness.
  source_gpu_gate: config/scaling_gates/xuantie_e902_named_rom_memory_mapping.json
  source_cpu_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json
  gpu_report: reports/xuantie_e902_named_rom_memory_mapping.json
  cpu_report: reports/xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json
  resolved_lane_offsets:
    ram0: 269904
    ram1: 400976
    ram2: 532048
    ram3: 663120
  accepted_claim:
    xuantie_e902_named_rom_memory_mapping_batch_128x32: 2.0903639153360194
  non_claims:
    - smoke 1x6 remains CPU-favorable with ratio 0.009975536442199584
    - not ISA/program correctness
    - not full software boot correctness
    - not broad XuanTie family support
    - not full RTL application throughput
  acceptance:
    - derive global storage offsets from generated root fields rather than hard-coded raw offsets
    - preserve the named_patch_deltas as source of truth
    - generate patch_script_lines or equivalent resident records for both GPU and CPU runners
    - keep artifacts generated-only under reports/ or work/
  status: done_gpu_cpu_pass
  next_action: package_xuantie_e902_named_rom_memory_mapping_boundary

package_xuantie_e902_named_rom_memory_mapping_boundary:
  goal: package the named XuanTie-E902 ROM/memory delta boundary and decide the next semantic axis
  weakest_point: the result is still one target and one instruction-memory family, so it should not be generalized to all XuanTie memory regions.
  source_gpu_report: reports/xuantie_e902_named_rom_memory_mapping.json
  source_cpu_report: reports/xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json
  packaged_claim:
    xuantie_e902_named_rom_memory_mapping_batch_128x32: 2.0903639153360194
  selected_next_axis: program_image_delta
  selection_reason: program-image deltas are the smallest semantic step after case.pat IAHB instruction-memory mapping; input-stream deltas would require a different target IO contract first.
  acceptance:
    - summarize the named mapping win and non-claims
    - keep the generated reports as artifacts, not source of truth
    - choose whether the next axis is input_stream_delta, program_image_delta, or broader target/memory-family coverage
  status: done
  next_action: define_xuantie_e902_program_image_delta_gate

define_xuantie_e902_program_image_delta_gate:
  goal: define the next application-like resident schedule gate as a bounded XuanTie-E902 program-image delta workload
  weakest_point: a program-image delta can still be only a memory-image mutation unless the gate states how bytes map to an executable program image and keeps ISA/program-correctness as a non-claim.
  source_mapping_boundary: package_xuantie_e902_named_rom_memory_mapping_boundary
  source_gpu_report: reports/xuantie_e902_named_rom_memory_mapping.json
  source_cpu_report: reports/xuantie_e902_cpu_exact_loop_named_rom_memory_mapping.json
  gpu_gate: config/scaling_gates/xuantie_e902_program_image_delta.json
  cpu_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_program_image_delta.json
  acceptance:
    - define GPU and CPU gate configs from program-image deltas, not raw root byte offsets
    - preserve generated root field offsets as lowering output, not hand-authored source
    - keep one-time schedule upload and no per-step host-device patch copies
    - state non-claims for ISA correctness, full software boot, and broad XuanTie coverage
  status: done_gates_defined
  next_action: run_xuantie_e902_program_image_delta_gate

run_xuantie_e902_program_image_delta_gate:
  goal: run the bounded XuanTie-E902 program-image delta GPU gate and matching CPU exact-loop baseline
  weakest_point: the gate still mutates a bounded loaded program image; passing throughput does not prove the mutated program is semantically meaningful.
  source_gpu_gate: config/scaling_gates/xuantie_e902_program_image_delta.json
  source_cpu_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_program_image_delta.json
  gpu_report: reports/xuantie_e902_program_image_delta.json
  cpu_report: reports/xuantie_e902_cpu_exact_loop_program_image_delta.json
  accepted_claim:
    xuantie_e902_program_image_delta_batch_128x32: 1.3826459191531113
  non_claims:
    - smoke 1x6 remains CPU-favorable with ratio 0.016034347357067786
    - not ISA/program correctness
    - not full software boot correctness
    - not broad XuanTie family support
    - not full RTL application throughput
  acceptance:
    - run GPU resident schedule gate
    - run matching CPU exact-loop baseline
    - compare 128x32 throughput and record non-claims
    - keep generated reports under reports/
  status: done_gpu_cpu_pass
  next_action: package_xuantie_e902_program_image_delta_boundary

package_xuantie_e902_program_image_delta_boundary:
  goal: package the bounded XuanTie-E902 program-image delta result and choose the next responsibility expansion
  weakest_point: the result uses a small mutation to a loaded image and still does not prove executable program behavior; packaging must avoid upgrading it to ISA correctness.
  source_gpu_report: reports/xuantie_e902_program_image_delta.json
  source_cpu_report: reports/xuantie_e902_cpu_exact_loop_program_image_delta.json
  packaged_claim:
    xuantie_e902_program_image_delta_batch_128x32: 1.3826459191531113
  selected_next_axis: broader_memory_family_coverage
  selection_reason: x_smem/x_dmem candidate families are already identified, so broadening named memory-family coverage is a smaller responsibility expansion than introducing a new input-stream IO contract.
  acceptance:
    - summarize the program-image delta win and non-claims
    - keep reports generated-only
    - choose next axis: input_stream_delta, broader memory-family coverage, or target breadth
  status: done
  next_action: define_xuantie_e902_broader_memory_family_delta_gate

define_xuantie_e902_broader_memory_family_delta_gate:
  goal: define a bounded XuanTie-E902 gate that extends named memory-family coverage beyond IAHB instruction memory
  weakest_point: x_smem/x_dmem were candidate fields, but their program/data semantics are not yet tied to a defensible memory-image source; the gate must avoid pretending they are equivalent to case.pat instruction memory.
  source_program_image_boundary: package_xuantie_e902_program_image_delta_boundary
  candidate_families:
    - x_smem_ctrl.ram0..3.mem
    - x_dmem_ctrl.ram0..3.mem
  source_contract_findings:
    x_smem_ctrl: AHB slave1 SYS MEM at 0x60000000..0x600fffff exists, but tb.v does not load a source image into x_smem_ctrl.ram0..3.mem.
    x_dmem_ctrl: AHB slave5 DMEM at 0x20000000..0x207fffff exists and tb.v zero-fills x_dmem_ctrl.ram0..3.mem, but no external data-image source is present.
    decision: do not define a broader memory-family throughput gate until a defensible source image or runtime write contract exists.
  acceptance:
    - choose one non-IAHB memory family or explicitly document why neither is source-defensible yet
    - define GPU and CPU gate configs only if a memory-image/source contract exists
    - preserve generated field offsets as lowering output, not hand-authored source
    - keep non-claims for ISA correctness, full boot, and broad XuanTie support
  status: blocked_source_contract_gap
  next_action: document_xuantie_e902_non_iahb_memory_family_contract_gap

document_xuantie_e902_non_iahb_memory_family_contract_gap:
  goal: package the non-IAHB memory-family source-contract gap and select a safer next responsibility expansion
  weakest_point: without a source image or observed runtime-write contract, x_smem/x_dmem byte mutations would regress to arbitrary root-storage patch semantics.
  source_files:
    - third_party/rtlmeter/designs/XuanTie-E902/src/tb.v
    - third_party/rtlmeter/designs/XuanTie-E902/src/ahb.v
    - third_party/rtlmeter/designs/XuanTie-E902/src/soc.v
  acceptance:
    - record why x_smem/x_dmem are not source-defensible for a throughput gate yet
    - avoid adding GPU/CPU gate configs for unsupported semantics
    - choose next axis between input_stream_delta and target_breadth
  status: done
  next_action: select_post_xuantie_memory_gap_responsibility_axis

select_post_xuantie_memory_gap_responsibility_axis:
  goal: choose the next responsibility-expansion axis after blocking broader non-IAHB memory-family coverage
  weakest_point: choosing target breadth too early may dodge input semantics, while choosing input_stream_delta without a defensible source contract may recreate arbitrary byte-patch claims.
  candidate_axes:
    input_stream_delta: reuse the existing XuanTie-E902 program-image source contract if an externally meaningful input/stimulus delta can be represented without inventing a new unsupported memory image.
    target_breadth: move to another target only if its memory/input contract is clearer than XuanTie-E902 x_smem/x_dmem.
  selected_axis: input_stream_delta
  deferred_axis: target_breadth
  selection_reason: input_stream_delta can be scoped against the existing XuanTie-E902 case.pat / IAHB program-image contract before adding another target; target_breadth is deferred until a clearer source-backed memory/input contract is selected.
  acceptance:
    - select exactly one next axis
    - record why the rejected axis is deferred
    - do not add new GPU/CPU gate configs until the selected axis has a source-backed contract
  status: done_input_stream_delta_selected
  next_action: define_xuantie_e902_input_stream_delta_contract

define_xuantie_e902_input_stream_delta_contract:
  goal: define the source-backed contract for the next XuanTie-E902 input/stimulus delta before adding GPU/CPU gates
  weakest_point: an input-stream delta that is only another arbitrary instruction-memory byte mutation would not expand responsibility beyond the existing program-image delta claim.
  source_boundary:
    reusable_contract: case.pat loaded through mem_inst_temp into x_iahb_mem_ctrl.ram0..3.mem
    forbidden_shortcut: hand-written generated root byte offsets without a program-image or stimulus-level source meaning
  finding:
    exposed_source_backed_input: case.pat program image only
    rejection_reason: no distinct input/stimulus source was found beyond the existing program-image contract; adding another input_stream_delta gate would collapse into a renamed program-image byte mutation.
  acceptance:
    - define what input/stimulus source is being varied
    - prove the delta lowers through the existing named program-image mapping or explicitly reject the axis
    - only then add matching GPU and CPU exact-loop gate configs
  status: rejected_no_distinct_source_contract
  next_action: select_next_target_breadth_source_backed_contract

select_next_target_breadth_source_backed_contract:
  goal: select the next target only if it has a clearer source-backed input or memory contract than the blocked XuanTie-E902 followups
  weakest_point: target breadth can become another target-count exercise unless the selected target has a source contract strong enough to support a meaningful GPU/CPU gate.
  candidate_policy:
    required: source-backed input/memory image or stimulus contract visible from checked-in RTL/test assets
    reject: targets that only offer arbitrary generated root storage mutation
  inventory:
    checked_in_minimal_targets:
      - tlul_fifo_sync
      - tlul_sink
      - xuantie_e902
      - veer_el2
    finding: all checked-in minimal targets have already been used as seeds or breadth candidates.
  acceptance:
    - name one next target candidate
    - cite the source artifact that defines its input/memory/stimulus contract
    - defer gate config creation until that contract is documented
  status: blocked_checked_in_minimal_targets_exhausted
  next_action: decide_next_source_backed_target_import_or_close_breadth

decide_next_source_backed_target_import_or_close_breadth:
  goal: decide whether to import a new source-backed target boundary or close target-breadth expansion for the current minimal repository
  weakest_point: importing a target without a source-backed input/memory contract repeats the current failure mode, while closing breadth too early may stop before proving another family.
  options:
    import_next_target:
      requirement: target has checked-in RTL/test assets plus an explicit input/memory/stimulus source contract
    close_current_minimal_breadth:
      requirement: record that current minimal repo breadth is exhausted and move back to runtime responsibility depth
  decision: close_current_minimal_breadth
  decision_reason: no unused checked-in minimal target remains with a clearer source-backed input or memory contract; importing a new target is deferred to avoid expanding repository scope without a contract.
  acceptance:
    - choose import or close
    - if import, name the source repo/path and required asset boundary
    - if close, select the next runtime-depth axis without adding target configs
  status: done_close_current_minimal_breadth
  next_action: select_next_runtime_depth_after_breadth_closure

select_next_runtime_depth_after_breadth_closure:
  goal: choose the next runtime-depth axis after closing current minimal target breadth
  weakest_point: repeating target-breadth paperwork will not improve runtime capability; the next task should reduce communication, increase resident scalability, or move more state construction onto GPU.
  candidate_axes:
    resident_schedule_scalability_envelope: measure and document where resident patch/program-image schedules remain GPU-favorable across larger nstates/steps.
    gpu_owned_state_construction: reduce host-device transfer by constructing or deriving more per-state initial data on GPU before resident eval.
  selected_axis: resident_schedule_scalability_envelope
  deferred_axis: gpu_owned_state_construction
  selection_reason: resident patch/program-image schedule reports already exist across TL-UL, VeeR-EL2, and XuanTie-E902; define the scalability envelope before designing heavier GPU-owned state construction.
  acceptance:
    - select one runtime-depth axis
    - define the first gate or documentation packet for that axis
    - avoid adding new target assets
  status: done_resident_schedule_scalability_selected
  next_action: define_resident_schedule_scalability_envelope

define_resident_schedule_scalability_envelope:
  goal: define the bounded resident schedule scalability envelope using existing GPU/CPU reports before adding new runtime mechanisms
  weakest_point: existing wins are shape-specific; without an envelope, it is unclear which nstates/steps regimes justify further GPU-resident optimization.
  source_reports:
    - reports/tlul_fifo_sync_resident_patch_schedule.json
    - reports/tlul_sink_resident_patch_schedule.json
    - reports/veer_el2_resident_patch_schedule.json
    - reports/xuantie_e902_resident_patch_schedule.json
    - reports/xuantie_e902_program_image_delta.json
  acceptance:
    - list included gate families and measured shapes
    - state where GPU wins and where CPU-favorable smoke remains
    - choose whether the next implementation axis is larger envelope measurement or gpu_owned_state_construction
  envelope:
    cpu_favorable_smoke_shapes:
      - tlul_fifo_sync resident_patch_schedule 1x6 ratio 0.005627988093961567
      - tlul_sink resident_patch_schedule 1x6 ratio 0.008255714084067339
      - veer_el2 resident_patch_schedule 1x6 ratio 0.005922418043868761
      - xuantie_e902 resident_patch_schedule 1x6 ratio 0.01038989322830183
      - xuantie_e902 program_image_delta 1x6 ratio 0.016034347357067786
    gpu_favorable_batch_shapes:
      - tlul_fifo_sync resident_patch_schedule 512x32 ratio 3.1160088024052413
      - tlul_sink resident_patch_schedule 512x32 ratio 2.002480966457029
      - veer_el2 resident_patch_schedule 512x32 ratio 2.8489279680483475
      - xuantie_e902 resident_patch_schedule 128x32 ratio 1.1724144754038845
      - xuantie_e902 program_image_delta 128x32 ratio 1.3826459191531113
    decision: extend larger envelope measurement before starting gpu_owned_state_construction
  status: done_from_existing_reports
  next_action: define_larger_resident_schedule_envelope_gate

define_larger_resident_schedule_envelope_gate:
  goal: define a larger resident schedule envelope gate using existing targets and runners, without importing new assets
  weakest_point: current accepted batch shapes prove GPU-favorable regimes, but do not show whether throughput improves, saturates, or regresses at larger resident schedule sizes.
  candidate_scope:
    - extend TL-UL resident patch schedule beyond 512x32 if memory budget remains safe
    - extend XuanTie-E902 program-image delta beyond 128x32 only if state memory footprint remains practical
  acceptance:
    - define GPU and CPU exact-loop gate configs or explicitly choose a documentation-only envelope
    - keep source-backed semantics unchanged
    - do not add target assets
  status: next
  next_action: define_larger_resident_schedule_envelope_gate
```

## source_of_truth

```text
- config/selection.json
- docs/status.md
- docs/roadmap.md
```
