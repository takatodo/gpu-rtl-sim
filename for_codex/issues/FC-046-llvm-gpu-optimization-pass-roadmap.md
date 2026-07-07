# FC-046: LLVM GPU Optimization Pass Roadmap

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/20
Target file: `src/passes/`, `src/tools/build_vl_gpu_*`, `docs/results.md`, `README.md`, `tests/contract/`

## Objective

Define the first LLVM/NVPTX optimization pass layer for the GPU sidecar path.
The optimization layer must run after the existing correctness patch passes and
must preserve the current CUDA distribution model:

```text
1 CUDA thread = 1 Verilator state
state images are independent
Verilator phase semantics are unchanged
host I/O, convergence, and timing-scheduler correctness patches stay owned by
the existing VlGpuPasses correctness layer
```

This is an umbrella issue. It coordinates FC-047 through FC-052 and should not
be closed by a single implementation unless all child acceptance criteria are
explicitly handled or replaced.

## Recommended Order

1. FC-047: emit GPU ABI metadata from `vlgpugen`.
2. FC-048: canonicalize state-image accesses.
3. FC-049: add conservative NVPTX inline/noinline policy.
4. FC-050: factor trigger guards only for proven-safe simple wrappers.
5. FC-051: add resident step kernel only after a separate correctness gate.
6. FC-052: evaluate hot-field SoA as a later ABI-changing design.

## Acceptance

- The roadmap keeps optimization separate from correctness patching.
- The pipeline position is explicit: after correctness patches and before `-O3`
  for the first optimization passes.
- The first implementation PR is limited to metadata, state-access
  canonicalization, or conservative inline policy.
- Trigger factoring, resident step kernels, and SoA are not treated as safe
  first-pass changes.
- No broad `verilator --use-gpu`, arbitrary RTL, automatic allocation,
  production throughput, CIRCT execution, or RTLMeter acceleration claim is
  added by this roadmap.

## Validation

```sh
git diff --check
python3 -m unittest discover -s tests/contract -q
```

Child issues should add focused tests and may use smaller validation commands.

## Non-Goals

- No new speedup claim by roadmap alone.
- No runtime/ABI change unless a child issue explicitly owns it.
- No change to correctness patch semantics.
- No JSON runtime ABI.
