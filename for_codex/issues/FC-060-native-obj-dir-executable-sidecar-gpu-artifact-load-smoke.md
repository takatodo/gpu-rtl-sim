# FC-060: Native obj_dir executable sidecar GPU artifact load smoke

Status: open
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/60
Parent task: FC-057 / https://github.com/takatodo/gpu-rtl-sim/issues/57
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Predecessor: FC-059 / https://github.com/takatodo/gpu-rtl-sim/issues/59

## Objective

Advance from FC-059's direct `obj_dir/V<top>` shim-entry smoke to the next
narrow direct-executable state: the make-built native executable for the
recognized `pulp_ita_mha 64x1` closure must directly locate and load the
expected sidecar GPU artifact from the native path, without delegating runtime
execution to `run_hybrid_template.py`.

This is still a smoke slice under FC-057. It proves artifact-load reachability
from the direct executable path only; it does not complete FC-057 unless kernel
launch and coverage equivalence are also implemented and verified.

## Current Boundary

FC-059 proves the final make-built `obj_dir/V<top>` can link and enter
repo-owned sidecar shim code directly. Its runtime evidence intentionally
records:

- `direct_executable_shim_reached: true`
- `template_flow_invoked: false`
- `gpu_artifact_loaded: false`
- `gpu_kernel_launched: false`
- `coverage_equivalence_passed: false`

The next weakest point is that the direct executable still does not load a
reviewed GPU artifact itself.

## Scope

- Extend the direct executable shim/runtime path so it resolves the expected
  native-path GPU artifact for the recognized `pulp_ita_mha 64x1` closure.
- Load or open/validate that artifact from the direct executable path and record
  machine-readable evidence under generated `obj_dir` output.
- Preserve FC-059's guarantee that the runtime path does not call or exec
  `run_hybrid_template.py`.
- Keep unrecognized filelist/top fail-closed.
- Missing artifact, mismatched artifact metadata, unsupported shape, or loader
  failure must fail nonzero and must not fall back to CPU.
- Keep generated evidence under `obj_dir`, `artifacts/`, or `reports/`; do not
  make generated evidence source of truth.

## Acceptance

For the recognized closure, the normal command sequence reaches artifact-load
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
- `gpu_artifact_path` or equivalent generated-path evidence
- `gpu_kernel_launched: false` unless a real launch is also implemented and
  verified
- `coverage_equivalence_passed: false` unless a real compare is also implemented
  and verified
- `gpu_execution_claimed: false` unless a real kernel launch is verified
- missing artifact path fails nonzero and records a fail-closed blocker

## Non-claims

- Does not complete FC-057 by itself.
- No GPU kernel-launch claim unless a real kernel launch is recorded.
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
obj_dir/V<prefix>` that records direct artifact-load evidence, and one real
missing-artifact or unrecognized filelist/top fail-closed run.
