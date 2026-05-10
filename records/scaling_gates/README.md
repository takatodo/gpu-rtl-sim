# Scaling Gates

`records/scaling_gates/` is an evidence ledger. It intentionally contains many
historical JSON records, but it is not the main operator entry point.

For compatibility, `config/scaling_gates` is a symlink to this directory.

Use these files through current pointers:

- `config/selection.json` selects the current gate with `current_priority_source_artifact`.
- `docs/status.md` explains the current state in human-readable form.
- `docs/roadmap.md` explains the next gate and residual risks.
- `docs/results.md` is the public benchmark pack.

## Current Pack Records

- `public_results_packaging_gate.json`
- `public_benchmark_pack_goal_completion_audit.json`
- `modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json`
- `persistent_resident_device_handle_storage_gate.json`
- `persistent_resident_device_handle_storage_review_gate.json`

## File Classes

| Pattern | Meaning |
| --- | --- |
| `*_source_gate.json` | Target promotion or source-equivalence boundary |
| `*_repeated_steps.json` | GPU repeated-step scaling gate |
| `*_cpu_exact_loop_repeated_steps.json` | CPU comparison gate |
| `*_coverage_output_depth.json` | Coverage-output depth check |
| `*_goal_completion_audit.json` | Goal-level completion audit |
| `*_review_gate.json` | Review or next-workstream decision |

## Policy

- Keep hand-authored decisions here, not in generated `reports/`.
- Keep generated measurements in `reports/` and reference them from gates.
- Prefer updating the current gate pointer over moving historical files.
- If a gate becomes irrelevant to the active project, archive the target in
  `config/archived_targets.json` before removing or relocating the gate.
