# FC-062: Native obj_dir executable sidecar coverage equivalence smoke

Status: open
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/62
Parent task: FC-057 / https://github.com/takatodo/gpu-rtl-sim/issues/57
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Predecessor: FC-061 / https://github.com/takatodo/gpu-rtl-sim/issues/61

## Objective

Advance from FC-061's direct executable CUDA module-load/kernel-launch smoke to
the remaining correctness slice under FC-057: the make-built native executable
for the recognized `pulp_ita_mha 64x1` closure must collect or expose the direct
sidecar result needed for the existing coverage compare and record accepted
`coverage_output_equivalence` evidence with mismatch count 0, without
delegating runtime execution to `run_hybrid_template.py`.

This is the first child slice that may satisfy the core FC-057 correctness
acceptance if FC-059, FC-060, and FC-061 are already in place. It still makes no
timing, speedup, arbitrary RTL, or RTLMeter claim.

## Current Boundary

FC-061 is intended to prove that `obj_dir/V<top>` directly loads the adjacent
CUDA module and launches the expected kernel. Kernel launch alone is not enough
for the parent objective because FC-057 also requires the direct executable path
to preserve the accepted CPU-vs-hybrid coverage-output equivalence behavior
from FC-055.

The next weakest point is moving the coverage result capture and comparison
from the temporary reviewed runner endpoint into the direct executable path
while keeping the evidence fail-closed and non-ambiguous.

## Scope

- Reuse the existing `src/hybrid/` runtime and coverage compare policy; do not
  add a parallel comparison definition.
- Capture or expose the sidecar output state/coverage-output words needed for
  the accepted `coverage_output_equivalence` comparison for the recognized
  `pulp_ita_mha 64x1` closure.
- Run or record the accepted comparison from the direct `obj_dir/V<top>`
  execution path without calling or execing `run_hybrid_template.py`.
- Record generated evidence under `obj_dir/`, `artifacts/`, or `reports/`
  according to generated-output policy.
- Missing state capture, missing CPU reference, compare prerequisites, CUDA
  failure, unsupported shape, or mismatched metadata must fail nonzero and must
  not fall back to CPU-as-GPU.
- Keep unrecognized filelist/top fail-closed.

## Acceptance

For the recognized closure, the normal command sequence reaches direct
executable coverage-equivalence evidence:

```sh
verilator --cc --exe --sim-accel sidecar-gpu \
  --sim-accel-states 64 --sim-accel-steps 1 \
  -f <known pulp_ita_mha filelist> --top-module pulp_ita_mha_gpu_cov_tb
make -C obj_dir -f V<prefix>.mk
obj_dir/V<prefix>
```

Required evidence:

- `direct_executable_shim_reached: true`
- `template_flow_invoked: false`
- `run_hybrid_template_invoked: false`
- `cpu_as_gpu_fallback: false`
- `gpu_artifact_loaded: true`
- `cuda_module_loaded: true` or equivalent module-load evidence
- `gpu_kernel_launched: true`
- `coverage_collected: true` or equivalent direct sidecar result-capture
  evidence
- `coverage_equivalence_passed: true`
- `coverage_output_mismatch_count: 0`
- `gpu_execution_claimed: true` only when backed by the direct CUDA
  kernel-launch evidence
- compare prerequisite failure fails nonzero and records a fail-closed blocker

## Non-claims

- No timing or speedup claim.
- No arbitrary RTL, arbitrary filelist support, dependency inference, or
  automatic allocation claim.
- No RTLMeter correctness claim; FC-058 remains a separate follow-up after
  FC-057.
- No raw full-state equality claim beyond the accepted coverage-output
  comparison.
- No CPU-as-GPU fallback.
- No stable external runtime ABI claim.

## Validation

Required:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_verilator_native_known_closure \
  tests.contract.test_verilator_native_sidecar_make_driver \
  tests.contract.test_verilator_native_sidecar_makefile_build_hook_patch -q
PYTHONDONTWRITEBYTECODE=1 make surface
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/check_staged_large_files.py
```

Plus one real recognized native run through `verilator -> make ->
obj_dir/V<prefix>` that records direct CUDA module-load, kernel-launch,
result-capture, and `coverage_output_equivalence` mismatch count 0 evidence;
and one real compare-prerequisite failure path that records fail-closed evidence
without CPU fallback.
