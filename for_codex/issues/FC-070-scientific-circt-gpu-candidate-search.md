# FC-070: Scientific CIRCT GPU Candidate Search

Status: open
Owner: unassigned
GitHub: unmirrored
Parent: FC-043 / https://github.com/takatodo/gpu-rtl-sim/issues/10
Related: FC-063 / https://github.com/takatodo/gpu-rtl-sim/issues/64, FC-065 / https://github.com/takatodo/gpu-rtl-sim/issues/65, FC-037 / https://github.com/takatodo/gpu-rtl-sim/issues/2
Target file: `src/tools/scientific_circt_gpu_candidate_plan.py`, `src/tools/llvm_rtl_gpu_suitability.py`, `tests/contract/test_scientific_circt_gpu_candidate_plan.py`, `README.md`, `docs/roadmap.md`, `docs/status.md`

## Objective

Create a reproducible path for scientific-compute kernels to enter the sidecar
project through CIRCT-generated SystemVerilog, then Verilator, then the existing
GPU suitability and CPU/hybrid measurement gates.

The intended operator question is:

```text
Given a scientific computation lowered through CIRCT to SystemVerilog and then
Verilator LLVM IR, which sub-systems are likely GPU-useful, which should stay
CPU-parallel, and which require a new specialized mapping?
```

This issue starts with candidate selection and planning. It does not claim CIRCT
execution, SystemVerilog generation, Verilator success, GPU execution, or
speedup until those gates produce evidence.

## Tasks

- Add a plan surface for scientific candidates such as dense matmul tiles,
  stencil tiles, batched reductions, softmax/exp pipelines, and branch-heavy
  sparse solver control.
- For each candidate, define the intended pipeline:
  MLIR/CIRCT input -> CIRCT SystemVerilog -> Verilator build -> lowered LLVM IR
  -> static suitability -> repeat-median CPU/hybrid measurement.
- Prefer regular-memory, low-observable, many-independent-state candidates
  before branch-heavy control candidates.
- Reuse FC-063/FC-065 suitability JSON only as review/debug metadata, not as
  execution authority.
- Fail closed when the CIRCT toolchain is missing.
- After CIRCT is available, materialize `dense_matmul_tile` first and measure at
  `64x1`, `256x1`, and `1024x1` before broadening.

## Acceptance

- `src/tools/scientific_circt_gpu_candidate_plan.py` emits a JSON plan with
  candidate order, CIRCT/Verilator/suitability/measurement stages, expected
  GPU buckets, planned shapes, and non-claims.
- The plan reports `blocked_circt_toolchain_missing` when no CIRCT executable is
  on `PATH`.
- Tests cover candidate filtering, unknown-candidate fail-closed behavior,
  absence of local absolute paths, and non-claims.
- README documents the command and the fact that it is plan-only.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_gpu_candidate_plan -q
python3 -m py_compile \
  src/tools/scientific_circt_gpu_candidate_plan.py \
  tests/contract/test_scientific_circt_gpu_candidate_plan.py
git diff --check -- \
  src/tools/scientific_circt_gpu_candidate_plan.py \
  tests/contract/test_scientific_circt_gpu_candidate_plan.py \
  README.md \
  docs/roadmap.md \
  docs/status.md \
  for_codex/issues.md \
  for_codex/issues/FC-070-scientific-circt-gpu-candidate-search.md
```

## Non-Goals

- No CIRCT execution by the plan alone.
- No generated SystemVerilog committed as source of truth.
- No Verilator build or GPU launch by the plan alone.
- No correctness equivalence, timing, speedup, or usefulness claim without
  measured evidence.
- No automatic hybrid partition claim.
