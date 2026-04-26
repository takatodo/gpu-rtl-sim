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
  decide_second_seed_or_larger_workload_after_exact_cpu_loop_baseline: next
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
```
