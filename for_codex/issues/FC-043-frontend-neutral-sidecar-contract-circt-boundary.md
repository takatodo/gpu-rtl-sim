# FC-043: Frontend-Neutral Sidecar Contract and CIRCT Boundary

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/10
Target file: `src/tools/*sidecar*`, `src/hybrid/`, `docs/roadmap.md`, `docs/status.md`, `README.md`, `tests/contract/`

## Objective

Extract the sidecar boundary so it is not accidentally Verilator-only. The goal
is a reviewed importable contract shape that Verilator can feed today and CIRCT
can feed later with equivalent metadata. This issue defines the boundary and a
non-executing CIRCT placeholder check; it does not claim CIRCT execution.

The weakest point to address is architectural: current implementation evidence
is still Verilator/template-centered even though the stated goal is
frontend-neutral.

## Tasks

- Inventory the metadata currently required by the sidecar launcher:
  source/build closure, top/module identity, schedule shape, host-probe or
  observable policy, state/report paths, compare policy, and failure classes.
- Separate frontend-owned fields from sidecar-owned fields in importable code,
  not in JSON-first documents.
- Add a small contract helper or dataclass-like shape that can be constructed
  from the current Verilator path without changing runtime behavior.
- Add a non-executing CIRCT adapter placeholder that validates which required
  fields are missing or present, without pretending to compile CIRCT output.
- Keep JSON as optional debug/review output only.
- Add tests that reject parser/frontend payloads trying to smuggle sidecar-owned
  paths, compare labels, or execution authority.
- Update docs to state what the frontend-neutral contract proves and what it
  still does not prove.

## Acceptance

- There is one importable contract boundary used or referenced by the Verilator
  path and suitable for a future CIRCT adapter.
- The contract explicitly identifies frontend-owned vs sidecar-owned fields.
- A CIRCT placeholder can report readiness/missing-context diagnostics without
  compiling, executing, or claiming support.
- Tests prove JSON debug output is not required as the runtime ABI.
- Docs preserve the non-claim: no CIRCT execution support yet.

## Validation

```sh
git diff --check
python3 -m unittest discover -s tests/contract -p '*sidecar*' -q
python3 -m unittest discover -s tests/contract -p '*verilator*' -q
```

Add a focused contract test for the frontend-neutral boundary if no existing
sidecar test is narrow enough.

## Non-Goals

- No CIRCT compile or execution support.
- No replacement of the current Verilator path.
- No stable external ABI promise.
- No JSON-first contract authority.
- No timing, speedup, or production-throughput claim.
