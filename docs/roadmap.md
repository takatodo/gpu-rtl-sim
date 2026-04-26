# Roadmap

## weakest_point

The project must prove it can run one seed from a clean, small surface before adding more targets or campaign logic.

## plan

```text
phase_1:
  scaffold_minimal_repo: done
  copy_minimal_runtime_core: done
  validate_imports: done
  select_thin_tools: done
  copy_selected_thin_tools: done
  validate_thin_tool_imports: done

phase_2:
  copy_tlul_fifo_sync_seed_config: done
  validate_build_surface_prerequisites: done
  copy_rtl_test_assets: done
  validate_verilator_build_surface: done
  generate_verilator_obj_dir: done
  build_gpu_kernel: blocked_missing_pass_build_surface
  add_pass_build_surface: done
  retry_build_gpu_kernel: done
  compile_host_runtime: done
  run_first_hybrid_smoke: done
  add_cpu_gpu_compare_surface: done
  run_cpu_baseline: done_with_contract_gap
  align_cpu_gpu_initial_state_contract: done
  run_hybrid_validation: done_normalized_final_state_equivalence
  run_compare: done_normalized_final_state_equivalence
  document_minimal_repro_flow: done

phase_3:
  decide_mainline_promotion_policy: done
  freeze_generated_artifact_policy: done
  emit_status_report: done
  summarize_commit_boundary: done
  select_git_ownership_mode: done_new_repository
  add_root_gitignore_policy: done
  initialize_minimal_repo_git_repository: done
  review_minimal_initial_source_boundary: done
  minimal_initial_commit_if_requested: done_f8349b9
  reproduce_from_clean_checkout_after_initial_commit: done_after_readme_fix
  commit_minimal_readme_clean_checkout_fix: done_c041911
  select_next_minimal_runtime_validation_axis: done_scale_tlul_fifo_sync
  define_tlul_fifo_sync_scaling_validation_gate: done
  implement_tlul_fifo_sync_scaling_validation_runner: done
  run_tlul_fifo_sync_scaling_validation_gate: done
  decide_post_tlul_scaling_validation_next_axis: done_cpu_baseline
  define_tlul_scaling_cpu_baseline_gate: done
  implement_tlul_fifo_sync_cpu_baseline_runner: done
  run_tlul_fifo_sync_cpu_baseline_gate: done
  decide_post_cpu_baseline_next_axis: done_conservative_multistate_baseline
  define_tlul_cpu_multistate_baseline_gate: done
  implement_tlul_cpu_multistate_baseline_runner_mode: done
  run_tlul_cpu_multistate_baseline_gate: done
  decide_exact_cpu_loop_or_second_seed_after_conservative_multistate_baseline: done_exact_loop
  define_tlul_cpu_exact_loop_baseline_gate: done
  implement_tlul_cpu_exact_loop_probe_and_runner_mode: done
  run_tlul_cpu_exact_loop_baseline_gate: done
  decide_second_seed_or_larger_workload_after_exact_cpu_loop_baseline: done_large_nstates
  define_tlul_large_workload_scaling_gate: done
  run_tlul_large_workload_scaling_gate: done
  define_tlul_large_workload_exact_cpu_loop_gate: done
  run_tlul_large_workload_exact_cpu_loop_gate: done
  decide_repeated_steps_or_second_seed_after_large_workload: done_repeated_steps
  define_tlul_repeated_steps_scaling_gate: done
  run_tlul_repeated_steps_scaling_gate: done
  define_tlul_repeated_steps_exact_cpu_loop_gate: done
  run_tlul_repeated_steps_exact_cpu_loop_gate: done
  decide_second_seed_after_repeated_steps: done_tlul_sink
  select_second_small_seed_target: done_tlul_sink
  copy_tlul_sink_minimal_assets: done
  generate_tlul_sink_verilator_obj_dir: done
  build_tlul_sink_gpu_cubin: done
  run_tlul_sink_repeated_steps_gpu_gate: done
  generalize_cpu_exact_loop_probe_for_second_seed: done
  build_tlul_sink_host_probe: done
  run_tlul_sink_repeated_steps_exact_cpu_loop_gate: done
  decide_package_boundary_after_second_seed_speedup: done_package_boundary
  document_two_seed_claim_boundary: done
  document_release_checklist: done
  package_minimal_two_seed_boundary: done
  decide_non_tlul_seed_or_release_after_package_boundary: done_release_readiness_first
  run_release_readiness_audit_after_package_boundary: done_lightweight_pass
  prepare_minimal_two_seed_release_boundary: done_local_boundary_documented
  select_smallest_non_tlul_breadth_seed_candidate: done_xuantie_e902
  define_xuantie_e902_minimal_gate_before_asset_copy: done_gate_shape_defined
  materialize_xuantie_e902_asset_boundary: done_source_boundary_copied
  validate_xuantie_e902_asset_boundary: blocked_missing_rtlmeter_top_include
  define_xuantie_e902_rtlmeter_include_strategy: done_lint_pass_with_warnings
  generate_xuantie_e902_verilator_obj_dir: done_pass_with_warnings
  build_xuantie_e902_gpu_cubin: done
  run_xuantie_e902_gpu_smoke: done
  define_xuantie_e902_cpu_reference_contract: done_normalized_final_state_equivalence
  define_xuantie_e902_scaling_gate: done
  run_xuantie_e902_scaling_gate: done
  define_xuantie_e902_cpu_repeated_steps_baseline: done_cpu_favorable
  decide_xuantie_e902_next_scaling_or_boundary: done_scale_workload
  define_xuantie_e902_large_workload_scaling_gate: done
  run_xuantie_e902_large_workload_scaling_gate: done
  define_xuantie_e902_cpu_exact_loop_large_workload_baseline: done
  run_xuantie_e902_cpu_exact_loop_large_workload_baseline: done_cpu_favorable_but_gap_narrowed
  decide_xuantie_e902_larger_memory_resident_workload_or_boundary: done_select_memory_resident_gate
  define_xuantie_e902_memory_resident_workload_gate: done
  run_xuantie_e902_memory_resident_workload_gate: done
  define_xuantie_e902_cpu_exact_loop_memory_resident_workload_baseline: done
  run_xuantie_e902_cpu_exact_loop_memory_resident_workload_baseline: done_gpu_win_at_largest_shape
  decide_true_resident_runtime_or_package_xuantie_boundary: done_select_true_resident_runtime_interface
  define_true_resident_gpu_runtime_interface: done
  implement_true_resident_gpu_runtime_flag: done
  package_xuantie_true_resident_runtime_boundary: done
  define_resident_runtime_regression_contract: done
  run_resident_runtime_regression_contract: done
  select_next_resident_runtime_breadth_or_patch_semantics: done_select_breadth
  select_next_non_tlul_resident_candidate: done_veer_el2
  define_veer_el2_resident_gate_before_asset_copy: done
  materialize_veer_el2_asset_boundary: next
```

## acceptance

```text
first_success_metric:
  build: pass
  run_seed: pass
  compare_seed: pass
  status_report: pass
  generated_artifacts_tracked: 0
  active_targets: 1

next_scaling_gate:
  target: tlul_fifo_sync
  config: config/scaling_gates/tlul_fifo_sync.json
  runner: src/tools/run_tlul_fifo_sync_scaling_validation.py
  report: reports/tlul_fifo_sync_scaling_validation.json
  nstates: [1, 8, 32]
  steps: [1]
  correctness_policy: normalized_final_state_equivalence_for_aligned_single_state
  performance_policy: report_runtime_and_throughput_without_speedup_claim
  status: pass

next_cpu_baseline_gate:
  target: tlul_fifo_sync
  config: config/scaling_gates/tlul_fifo_sync_cpu_baseline.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py
  report: reports/tlul_fifo_sync_cpu_baseline.json
  reps: 5
  accepted_claim: CPU single-state host probe timing surface
  non_claim: exact nstates>1 CPU-vs-GPU speedup until matching CPU loop exists
  status: pass

next_cpu_multistate_baseline_gate:
  target: tlul_fifo_sync
  config: config/scaling_gates/tlul_fifo_sync_cpu_multistate_baseline.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --multi-state
  report: reports/tlul_fifo_sync_cpu_multistate_baseline.json
  nstates: [1, 8, 32]
  steps: [1]
  accepted_claim: conservative CPU process-per-state baseline compared with GPU scaling report
  non_claim: exact single-process CPU-vs-GPU speedup
  status: pass

next_cpu_exact_loop_baseline_gate:
  target: tlul_fifo_sync
  config: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_baseline.json
  runner: src/tools/run_tlul_fifo_sync_cpu_baseline.py --exact-loop
  report: reports/tlul_fifo_sync_cpu_exact_loop_baseline.json
  nstates: [1, 8, 32]
  steps: [1]
  accepted_claim: single-process CPU loop baseline compared with GPU scaling report
  current_observation: GPU is slower than CPU for this small seed/workload
  next_decision: increase workload or add second seed
  status: pass

next_large_workload_gate:
  target: tlul_fifo_sync
  gpu_config: config/scaling_gates/tlul_fifo_sync_large_workload.json
  cpu_config: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_large_workload.json
  gpu_report: reports/tlul_fifo_sync_large_workload_scaling.json
  cpu_report: reports/tlul_fifo_sync_cpu_exact_loop_large_workload.json
  nstates: [32, 128, 512]
  steps: [1]
  accepted_claim: GPU beats exact CPU loop at nstates=512 for this seed and gate shape
  non_claim: repeated-step throughput and target-breadth generality
  status: pass

next_repeated_steps_gate:
  target: tlul_fifo_sync
  gpu_config: config/scaling_gates/tlul_fifo_sync_repeated_steps.json
  cpu_config: config/scaling_gates/tlul_fifo_sync_cpu_exact_loop_repeated_steps.json
  gpu_report: reports/tlul_fifo_sync_repeated_steps_scaling.json
  cpu_report: reports/tlul_fifo_sync_cpu_exact_loop_repeated_steps.json
  nstates: [512]
  steps: [1, 8, 32]
  accepted_claim: GPU beats CPU repeated-eval loop for this seed and gate shape
  non_claim: target-breadth generality and full timed-cycle equivalence
  status: pass

second_seed_gate:
  target: tlul_sink
  gpu_config: config/scaling_gates/tlul_sink_repeated_steps.json
  gpu_report: reports/tlul_sink_repeated_steps_scaling.json
  nstates: [512]
  steps: [1, 8, 32]
  cpu_config: config/scaling_gates/tlul_sink_cpu_exact_loop_repeated_steps.json
  cpu_report: reports/tlul_sink_cpu_exact_loop_repeated_steps.json
  accepted_claim: second seed shows GPU win against single-process CPU repeated-eval loop
  non_claim: generality beyond two OpenTitan TL-UL seeds
  status: pass

package_boundary:
  status: documented
  claim_scope: two OpenTitan TL-UL seeds only
  release_checklist: README.md
  release_readiness_audit: pass_lightweight
  release_boundary: README.md
  next_task: materialize_xuantie_e902_asset_boundary
  next_decision: copy only the defined XuanTie-E902 source/test boundary

non_tlul_breadth_seed_candidate:
  selected: XuanTie-E902
  role: first non-TL-UL breadth candidate
  selection_status: asset_boundary_materialized
  gate_status: defined_before_asset_copy
  gate_top_module: xuantie_e902_gpu_cov_tb
  gate_shape: nstates=8 steps=56
  launch_template: config/slice_launch_templates/xuantie_e902.json
  asset_boundary_status: copied
  lint_only_status: pass_with_warnings
  obj_dir_status: pass_with_warnings
  obj_dir: artifacts/xuantie_e902_obj_dir
  gpu_cubin_status: pass
  gpu_smoke_status: pass
  cpu_reference_contract_status: pass
  normalized_final_state_equivalence: pass
  scaling_gate: config/scaling_gates/xuantie_e902_scaling.json
  scaling_report: reports/xuantie_e902_scaling.json
  scaling_status: pass
  cpu_exact_loop_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_repeated_steps.json
  cpu_exact_loop_report: reports/xuantie_e902_cpu_exact_loop_repeated_steps.json
  cpu_gpu_observation: cpu_favorable_at_conservative_gate
  large_workload_gate: config/scaling_gates/xuantie_e902_large_workload.json
  large_workload_report: reports/xuantie_e902_large_workload_scaling.json
  large_workload_status: pass
  cpu_exact_loop_large_workload_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_large_workload.json
  cpu_exact_loop_large_workload_report: reports/xuantie_e902_cpu_exact_loop_large_workload.json
  cpu_exact_loop_large_workload_status: pass_cpu_favorable_but_gap_narrowed
  best_large_workload_gpu_over_cpu_ratio: 0.8625
  memory_resident_workload_gate: config/scaling_gates/xuantie_e902_memory_resident_workload.json
  memory_resident_workload_report: reports/xuantie_e902_memory_resident_workload_scaling.json
  memory_resident_workload_status: pass
  cpu_exact_loop_memory_resident_workload_gate: config/scaling_gates/xuantie_e902_cpu_exact_loop_memory_resident_workload.json
  cpu_exact_loop_memory_resident_workload_report: reports/xuantie_e902_cpu_exact_loop_memory_resident_workload.json
  cpu_exact_loop_memory_resident_workload_status: pass_gpu_win_at_largest_shape
  best_memory_resident_proxy_gpu_over_cpu_ratio: 1.0955
  best_true_resident_gpu_over_cpu_ratio: 1.2076
  true_resident_runtime_status: packaged_boundary
  true_resident_runtime_accepted_claim: XuanTie-E902 resident mode beats CPU exact-loop at nstates=128 steps=64
  resident_runtime_regression_contract: tests/contract/test_resident_runtime_contract.py
  resident_runtime_regression_status: pass
  next_resident_breadth_policy: select bounded non-TL-UL candidate before copying assets
  next_resident_breadth_candidate: veer_el2
  next_resident_breadth_candidate_status: resident_gate_defined_before_asset_copy
  next_resident_breadth_candidate_evidence:
    - old_repo:output/family_readiness/veer_el2_gpu_toggle_readiness.md
    - old_repo:output/design_scope_expansion_packet.json
    - old_repo:config/slice_launch_templates/veer_el2.json
  next_resident_breadth_candidate_launch_template: config/slice_launch_templates/veer_el2.json
  next_resident_breadth_candidate_gpu_gate: config/scaling_gates/veer_el2_resident_workload.json
  next_resident_breadth_candidate_cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_resident_workload.json
  true_resident_runtime_interface:
    cli_flag: src/tools/run_vl_hybrid.py --resident-steps
    runtime_env: RUN_VL_HYBRID_RESIDENT_STEPS=1
    c_runtime: src/hybrid/run_vl_hybrid.c
  storage_size: 1318784
  support_rtl: third_party/rtlmeter/rtl
  next_task: materialize_veer_el2_asset_boundary

veer_el2_resident_breadth_candidate:
  selected: true
  selection_status: resident_gate_defined_before_asset_copy
  role: next non-TL-UL resident runtime breadth candidate
  old_repo_launch_template: config/slice_launch_templates/veer_el2.json
  old_repo_gate_evidence: output/family_readiness/veer_el2_gpu_toggle_readiness.md
  old_repo_candidate_score_evidence: output/design_scope_expansion_packet.json
  launch_template: config/slice_launch_templates/veer_el2.json
  gpu_gate: config/scaling_gates/veer_el2_resident_workload.json
  cpu_gate: config/scaling_gates/veer_el2_cpu_exact_loop_resident_workload.json
  gate_shapes:
    - nstates=64 steps=64 resident_steps=true
    - nstates=128 steps=64 resident_steps=true
  required_next_step: materialize bounded VeeR-EL2 source/test assets
  non_claim: no VeeR-EL2 resident-mode result exists in the minimal repo yet
```
