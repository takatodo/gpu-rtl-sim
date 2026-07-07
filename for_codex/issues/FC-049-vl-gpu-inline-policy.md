# FC-049: vl-gpu-inline-policy

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/24
Target file: `src/passes/VlGpuPasses.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/`

## Objective

Control inline/noinline attributes for NVPTX so small leaf helpers can avoid
call overhead while large phase/eval functions avoid register-pressure and
spill explosions.

This pass should be conservative by default.

## Proposed Rules

```text
kernel functions:
  leave unchanged

tiny leaf helper:
  alwaysinline when instruction_count <= 20 and call_count == 0

large phase/eval/helper:
  noinline when instruction_count >= 300

functions with loops:
  noinline unless very small and explicitly safe

names containing ___eval_phase__, ___eval_nba, ___ico_sequent, ___nba_sequent:
  prefer noinline
```

## Tasks

- Add a named pass such as `vl-gpu-inline-policy`.
- Expose conservative thresholds through command-line options only if needed.
- Insert the pass before the main `-O3` GPU optimization step.
- Record function attributes in tests or generated inspection output.
- Compare `NUM_REGS` and `LOCAL_SIZE_BYTES` in later measurement work; do not
  claim speedup from attributes alone.

## Acceptance

- Tiny leaf helpers receive `alwaysinline` only when the rule proves they are
  safe.
- Large phase/eval functions receive `noinline`.
- Kernel function attributes are not corrupted.
- The pass does not inline host/runtime stubs in a way that revives host I/O.
- Register-pressure metrics are treated as diagnostics until measured.

## Validation

```sh
git diff --check
make -C src/passes --no-print-directory
python3 -m unittest discover -s tests/contract -p '*hybrid*' -q
```

## Non-Goals

- No aggressive inlining policy in the first implementation.
- No speedup claim by attribute changes alone.
- No correctness patch changes.
