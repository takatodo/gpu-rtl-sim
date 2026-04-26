# AGENTS.md

## Role

This repository is the minimal extraction of the GPU toggle coverage hybrid-runtime project.

## Invariants

- Keep the active surface small.
- Do not add generated outputs as source of truth.
- Do not create one-off scripts for each turn.
- Prefer shared importable logic; keep CLI entrypoints thin.
- Add a test and doc mention with any new public CLI or flow.
- Keep only one active seed target until the first success metric is met.

## Layout

```text
config/:
  selection.json
  targets.json

docs/:
  status.md
  roadmap.md
  migration_notes.md

src/hybrid/:
  C/C++ hybrid runtime and host/GPU ABI glue

src/passes/:
  LLVM / Verilator lowering passes

src/tools/:
  thin CLI entrypoints and shared helpers

tests/contract/:
  minimal contract tests for build/run/compare flows

artifacts/:
  generated outputs only, not source of truth

reports/:
  generated command summaries and compare reports only, not source of truth
```

## File Growth Gate

```text
if adding_new_cli:
  require matching test
  require doc mention
  keep heavy logic in shared modules

if adding_new_artifact:
  write under artifacts/
  do not make it the only source of truth

if adding_new_report:
  write under reports/
  keep it reproducible from documented commands
  do not put hand-authored decisions in reports/

if adding_second_related_file_in_same_dir:
  reconsider shared module or subdirectory boundary
```

## Source Of Truth

```text
config/selection.json:
  current machine-readable state

docs/status.md:
  current human-readable state

docs/roadmap.md:
  next gate and blocker
```

## Generated Artifact Policy

```text
artifacts/:
  allowed:
    - Verilator obj_dir outputs
    - cubin/ptx/ll build outputs
    - generated host-probe binaries
    - raw state dumps
  forbidden:
    - hand-authored source
    - operational decisions
    - unique non-regenerable notes

reports/:
  allowed:
    - generated command summaries
    - generated compare summaries
    - generated probe output captured as JSON
  forbidden:
    - hand-authored status decisions
    - canonical roadmap state
    - local absolute paths

canonical_state:
  - config/selection.json
  - docs/status.md
  - docs/roadmap.md
  - README.md for operator repro commands
```
