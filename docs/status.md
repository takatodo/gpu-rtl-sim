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
  generate_xuantie_e902_verilator_obj_dir

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
```

## next

```text
generate_xuantie_e902_verilator_obj_dir:
  generate artifacts/xuantie_e902_obj_dir from descriptor source order
  pass __RTLMETER_MAIN_CLOCK from descriptor mainClock
  stage tests/hello/case.pat as generated runtime input if needed
  do not claim GPU runtime until obj_dir and cubin build pass
```

## source_of_truth

```text
- config/selection.json
- docs/status.md
- docs/roadmap.md
```
