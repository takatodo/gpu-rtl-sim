# Records Directory

`records/` holds hand-authored historical records that are useful for audit and
compatibility but should not enlarge the active `config/` surface.

Current layout:

- `records/scaling_gates/`: historical and current gate records.

Compatibility:

- `config/scaling_gates` is a symlink to `../records/scaling_gates`.
- Existing commands and tests may continue to reference
  `config/scaling_gates/<gate>.json`.

Policy:

- Keep generated command output reproducible under `reports/`, not here.
- Keep build products and raw dumps reproducible under `artifacts/`, not here.
- Keep current machine-readable project state in `config/selection.json`.
- Keep launch templates in `config/slice_launch_templates/` because they are
  runtime-facing configuration, not historical records.
