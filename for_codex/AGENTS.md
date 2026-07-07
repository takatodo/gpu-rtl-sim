# AGENTS.md

## Role

This repository is a minimal extraction of the GPU-toggle coverage hybrid-runtime project.

The goal is to keep the active implementation surface small while preserving a reproducible path from configuration to build, run, comparison, and status reporting.

Destructive cleanup is allowed on dedicated cleanup branches when the affected work is recoverable through git history.

## Core Invariants

- Keep the active surface small.
- Keep CLI entrypoints thin.
- Put reusable behavior in shared importable modules.
- Do not add generated outputs as source of truth.
- Do not create one-off scripts for individual turns or local experiments.
- Add a test and documentation mention for any new public CLI or workflow.
- Keep only one active seed target until the first success metric is met.
- Prefer reproducible commands over hand-maintained operational notes.

## Repository Layout

```text
config/
  selection.json                      # compact current machine-readable project state
  selection_extensions.json           # bulky selection payloads linked from selection.json
  selection_verification_commands.json # long verification checklist linked from selection.json
  targets.json                        # target inventory and metadata

docs/
  status.md             # current human-readable project state
  roadmap.md            # next gate, blocker, and immediate direction
  migration_notes.md    # migration context and compatibility notes

src/hybrid/
  C/C++ hybrid runtime and host/GPU ABI glue

src/passes/
  LLVM / Verilator lowering passes

src/tools/
  thin CLI entrypoints and shared helpers

src/diagnostics/frozen/
  frozen historical diagnostics kept for reproduction behind thin src/tools
  compatibility facades; do not treat these as active operator entrypoints

third_party/
  upstream submodules only

overlays/
  repo-specific source overlays for upstream submodules

tests/contract/
  minimal contract tests for build/run/compare flows

artifacts/
  generated outputs only; never source of truth

reports/
  generated command summaries and compare reports only; never source of truth
```

## Source of Truth

Canonical state lives only in:

```text
config/selection.json   # compact current machine-readable state (see selection_extensions.json for linked evidence maps)
docs/status.md          # current human-readable state
docs/roadmap.md         # next gate and blocker
README.md               # operator reproduction commands
```

Do not move canonical decisions into generated files, local notes, reports, or artifacts.

## Generated Output Policy

### `artifacts/`

Allowed:

* Verilator `obj_dir` outputs
* CUBIN / PTX / LLVM IR build outputs
* Generated host-probe binaries
* Raw state dumps

Forbidden:

* Hand-authored source
* Operational decisions
* Unique non-regenerable notes
* Canonical roadmap or status information

### `reports/`

Allowed:

* Generated command summaries
* Generated compare summaries
* Generated probe output captured as JSON

Forbidden:

* Hand-authored status decisions
* Canonical roadmap state
* Local absolute paths
* Unique information that cannot be regenerated from documented commands

## File Growth Gate

Before adding files, apply this gate:

```text
if adding_new_cli:
  require matching test
  require doc mention
  keep heavy logic in shared modules
  keep CLI entrypoint thin

if adding_new_artifact:
  write under artifacts/
  ensure it is reproducible
  do not make it the only source of truth

if adding_new_report:
  write under reports/
  ensure it is reproducible from documented commands
  do not put hand-authored decisions in reports/
  do not include local absolute paths

if adding_second_related_file_in_same_dir:
  reconsider shared module or subdirectory boundary
```

## CLI and Workflow Rules

For any new public CLI or public workflow:

* Add or update a minimal contract test.
* Add or update a documentation mention.
* Keep parsing, printing, and process exit behavior in the CLI layer.
* Move reusable logic into importable helpers.
* Avoid embedding one-off paths, local machine assumptions, or temporary experiment logic.

## Target Selection Rule

Keep only one active seed target until the first success metric is met.

Target state should be reflected in:

```text
config/selection.json
docs/status.md
docs/roadmap.md
```

Do not introduce a second active seed target unless the roadmap explicitly records that the first success metric has been reached.

## Review Stance

Review strictly. Start from the weakest point in a claim, implementation, test,
or document change before accepting it as done. Do not soften review because a
change matches the user's preferred direction.

In reviews:

* Treat compile success as insufficient unless the requested user value is also
  demonstrated.
* Call out unsupported paths, hidden local assumptions, and overbroad speedup or
  runtime claims.
* Keep JSON debug surfaces separate from execution authority and runtime ABI
  claims.
* Prefer "not proven yet" over a convenient interpretation of partial evidence.

## Review Checklist

Before committing changes, verify:

* No generated output is treated as canonical state.
* No hand-authored decision is stored only in `artifacts/` or `reports/`.
* New CLI or workflow changes have a test and doc mention.
* New reusable behavior is importable and not trapped inside a CLI script.
* Local absolute paths are not written into reports.
* The active seed target policy is still respected.
* `config/selection.json`, `docs/status.md`, and `docs/roadmap.md` agree.
