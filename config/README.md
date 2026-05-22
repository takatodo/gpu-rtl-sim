# Config Directory

`config/` is source-of-truth configuration, not generated output.

Keep this directory small at the top level. Put only current machine-readable
state, target inventories, execution templates, and gate records here. Generated
summaries are reproducible under `reports/`; build products and raw dumps are
reproducible under `artifacts/`. Those directories may contain only `.gitignore`
in a clean minimized tree.

## Top-Level Files

| Path | Role | Policy |
| --- | --- | --- |
| `selection.json` | Current project state and current gate pointer | `schema_version` 3+: keep compact; large maps in `selection_extensions.json`; long `verification.commands` in `selection_verification_commands.json`. |
| `selection_extensions.json` | Historical / bulky selection payloads (`completed_goal_evidence`, MobileViT accuracy block) | Source-of-truth config; referenced by `selection.json` (`selection_extensions`). Load merged view with `src/tools/selection_state.py` (`load_selection`). |
| `selection_verification_commands.json` | Scripted verification steps for the checked-in `tlul_fifo_async` evidence path | Referenced as `verification.commands_artifact` from `selection.json`. `load_selection` injects `verification.commands`. |
| `targets.json` | Active target inventory | Canonical list of `active_targets` names and metadata; `load_selection` builds `active_scope.targets` from this file. Keep counts/metadata in `selection.json` aligned when you change inventory. |
| `archived_targets.json` | Inactive target inventory | Use for removed or parked targets instead of leaving them active. |
| `resident_patch_script_semantics.json` | Legacy resident patch semantics record | Keep only while referenced by historical gates/tests. |

## Subdirectories

| Path | Role | Policy |
| --- | --- | --- |
| `slice_launch_templates/` | Public hybrid launch templates | Runtime-facing. Keep templates reproducible and referenced by CLI docs/tests. |
| `scaling_gates/` | Compatibility link to `../records/scaling_gates` | Evidence ledger lives outside the active config surface. Current gate is selected by `selection.json`. |

## Current Entry Points

- Current machine-readable state: `config/selection.json`
- Operator shortcuts: `Makefile` at repo root (see README **Operator shortcuts**; calls existing tools only)
- Current target inventory: `config/targets.json`
- Current gate pointer: `current_priority_source_artifact` in `config/selection.json` (at time of writing this is `config/scaling_gates/config_generation_validation_breadth_execution_gate.json`; treat `selection.json` as authoritative if they drift)
- Public benchmark pack gate: `config/scaling_gates/public_results_packaging_gate.json`
- Public benchmark pack audit: `config/scaling_gates/public_benchmark_pack_goal_completion_audit.json`
- Gate record storage: `records/scaling_gates/`

## Add/Move Rules

- Add a new public CLI or workflow only with a matching test and README/docs mention.
- Add a new launchable target template under `slice_launch_templates/`.
- Add a new decision/evidence gate under `records/scaling_gates/`; keep
  `config/scaling_gates/...` references for compatibility when needed.
- Do not put generated reports, raw benchmark output, or local absolute paths in `config/`.
- Do not make `scaling_gates/` the operator entry point; link current work through `selection.json`, `README.md`, `docs/status.md`, and `docs/roadmap.md`.
