# FC-063: LLVM RTL GPU Suitability Analysis Pass

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/64
Parent: FC-046 / https://github.com/takatodo/gpu-rtl-sim/issues/20
Related: FC-037 / https://github.com/takatodo/gpu-rtl-sim/issues/2, FC-045 / https://github.com/takatodo/gpu-rtl-sim/issues/19
Target file: `src/tools/llvm_ir_parse.py`, `src/tools/llvm_rtl_gpu_suitability.py`, `src/tools/llvm_rtl_gpu_suitability_cli.py`, `tests/contract/test_llvm_rtl_gpu_suitability_cli.py`, `README.md`, `docs/verilator_sidecar_option.md`

## Objective

Add a static LLVM IR suitability analyzer for lowered RTL functions. The
analyzer should make the current decision reproducible before more GPU work is
attempted:

```text
GPU state-parallel path
CPU-parallel path
requires new implementation / GEM-like mapping path
```

This issue is deliberately analysis-only. It consumes lowered LLVM IR and emits
debug/review JSON. It does not execute RTL, launch GPU kernels, change the host
runtime ABI, or claim speedup.

## Inputs and Output

Inputs:

- LLVM IR text from Verilator/CIRCT-style lowering.
- Optional entry function.
- Target/workload label.
- Optional shape in `NxS` form, such as `64x1` or `3x100000`.

Output:

- A suitability JSON record with `verdict`, `recommended_path`, positive and
  negative reasons, non-claims, and metrics.
- Required metrics include `branch_density`, `memory_regularity_score`,
  `state_independence_score`, and `observable_pressure`.

## Acceptance

- A synthetic ITA/MHA-style `64x1` lowered IR fixture is classified as
  `good_state_parallel` with `recommended_path=gpu_state_parallel`.
- A synthetic VeeR mixed design-CPU workload fixture is classified as
  `poor_requires_new_implementation` with
  `recommended_path=cpu_parallel_or_gem_like_mapping`.
- The VeeR-style result reports high branch/observable pressure and the
  observable-heavy RTL CPU-core reason.
- Unsupported atomic/fence and volatile/inline-asm hints fail closed through
  explicit negative reasons.
- Dotted and quoted LLVM function names can be selected by entry name without
  weakening the missing-entry fail-closed behavior.
- When an entry function is selected, defined callees reachable from that entry
  are included in metrics so helper-level branch, observable, volatile, or
  memory pressure is not hidden by a thin wrapper.
- Reachable-region side-effect evidence includes `external_call_count`,
  `external_calls`, `llvm_intrinsic_call_count`, and `llvm_intrinsic_calls`.
- The CLI prints JSON without local absolute paths.
- Missing entry functions fail closed with a non-zero exit status.
- Documentation states that this JSON is debug/review analysis only, not
  execution authority, runtime ABI, correctness equivalence, or speedup
  evidence.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_llvm_rtl_gpu_suitability_cli -q
python3 -m py_compile \
  src/tools/llvm_ir_parse.py \
  src/tools/llvm_rtl_gpu_suitability.py \
  src/tools/llvm_rtl_gpu_suitability_cli.py \
  tests/contract/test_llvm_rtl_gpu_suitability_cli.py
git diff --check -- \
  src/tools/llvm_ir_parse.py \
  src/tools/llvm_rtl_gpu_suitability.py \
  src/tools/llvm_rtl_gpu_suitability_cli.py \
  tests/contract/test_llvm_rtl_gpu_suitability_cli.py \
  README.md \
  docs/verilator_sidecar_option.md \
  for_codex/issues.md \
  for_codex/issues/FC-063-llvm-rtl-gpu-suitability-analysis-pass.md
```

## Non-Goals

- No GPU execution by this issue alone.
- No runtime ABI change.
- No correctness equivalence claim.
- No RTLMeter speedup or usefulness claim.
- No arbitrary RTL support claim.
- No replacement for measured FC-037 / #2 timing evidence.
