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
  select_next_minimal_runtime_validation_axis: next
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
```
