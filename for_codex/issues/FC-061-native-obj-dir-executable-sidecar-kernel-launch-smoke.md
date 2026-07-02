# FC-061: Native obj_dir executable sidecar kernel launch smoke

Status: open
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/61
Parent task: FC-057 / https://github.com/takatodo/gpu-rtl-sim/issues/57
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Predecessor: FC-060 / https://github.com/takatodo/gpu-rtl-sim/issues/60

## Objective

Advance from FC-060's direct executable GPU artifact-load smoke to the next
narrow direct-executable state: the make-built native executable for the
recognized `pulp_ita_mha 64x1` closure must initialize the sidecar runtime
enough to load the adjacent GPU artifact as a CUDA module and launch the
expected GPU kernel from the direct `obj_dir/V<top>` path, without delegating
runtime execution to `run_hybrid_template.py`.

This is still a child slice under FC-057. It proves direct executable
kernel-launch reachability only; it does not complete FC-057 unless
coverage-output equivalence is also implemented and verified.

## Current Boundary

FC-060 proves the final make-built `obj_dir/V<top>` executable reaches
repo-owned sidecar shim code directly and validates adjacent generated artifact
files:

- `vl_batch_gpu.meta.json`
- `vl_batch_gpu.cubin`

FC-060 intentionally records `gpu_artifact_loaded: true` as artifact-file
validation only, while keeping:

- `gpu_kernel_launched: false`
- `coverage_equivalence_passed: false`
- `gpu_execution_claimed: false`

The next weakest point is that the direct executable still does not perform CUDA
module load or kernel launch itself.

## Scope

- Extend the direct executable shim/runtime path to initialize the required
  sidecar runtime state for the recognized `pulp_ita_mha 64x1` closure.
- Load the adjacent `vl_batch_gpu.cubin` as a CUDA module or use the existing
  `src/hybrid/` runtime loader path from the direct executable.
- Launch the expected kernel named by `vl_batch_gpu.meta.json`, without calling
  or execing `run_hybrid_template.py`.
- Record generated evidence under `obj_dir/native_sidecar_runtime.json`.
- Missing CUDA driver/device, missing/mismatched artifact metadata, unsupported
  shape, loader failure, or launch failure must fail nonzero and must not fall
  back to CPU.
- Keep unrecognized filelist/top fail-closed.

## Acceptance

For the recognized closure, the normal command sequence reaches kernel-launch
smoke evidence:

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
- `gpu_kernel_name` or equivalent kernel evidence
- `coverage_equivalence_passed: false` unless a real compare is also
  implemented and verified
- `gpu_execution_claimed: true` only if the evidence reflects a real CUDA kernel
  launch
- CUDA init/module/launch failure fails nonzero and records a fail-closed
  blocker

## Non-claims

- Does not complete FC-057 by itself.
- No coverage equivalence claim unless compare actually runs and records
  mismatch count 0.
- No timing or speedup claim.
- No arbitrary RTL, arbitrary filelist support, dependency inference, or
  automatic allocation claim.
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
obj_dir/V<prefix>` that records direct CUDA module-load and kernel-launch
evidence, and one real CUDA/artifact failure path that records fail-closed
evidence without CPU fallback.
