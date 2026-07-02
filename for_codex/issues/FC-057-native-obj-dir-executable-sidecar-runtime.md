# FC-057: Native obj_dir executable sidecar runtime integration

Status: open
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/57
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Predecessor: FC-055 / https://github.com/takatodo/gpu-rtl-sim/issues/55
First child slice: FC-059 / https://github.com/takatodo/gpu-rtl-sim/issues/59

## Objective

Replace the FC-055 temporary reviewed endpoint with the owner-goal endpoint:
the make-built `obj_dir/V<top>` executable for a recognized native
`--sim-accel sidecar-gpu` closure must invoke the GPU sidecar runtime directly,
without delegating execution to the repo template runner.

The target user path remains:

```text
verilator --sim-accel sidecar-gpu --sim-accel-states N --sim-accel-steps M \
  -f filelist --top-module top
make -C obj_dir -f V<top>.mk
obj_dir/V<top>
```

No PATH wrapper, proxy env, review manifest, repo-specific launch-template
selection, or user-facing intermediate operation should be required.

## Current Boundary From FC-055

FC-055 proves the generated Makefile can drive the existing reviewed
`run_hybrid_template.py` seven-stage flow for the recognized `pulp_ita_mha
64x1` closure and reach GPU kernel launch plus `coverage_output_equivalence`
mismatch count 0.

FC-055 does not prove:

- `obj_dir/V<top>` itself loads the sidecar artifact or launches GPU kernels;
- an in-process runtime ABI between Verilator-generated executable and
  `src/hybrid/` exists;
- the user can run the normal make/run flow without a repo-side runner
  delegation step;
- the native path is free of user-supplied repo-root environment plumbing.

FC-059 is the first child slice under this parent. It only proves that the
make-built `obj_dir/V<top>` can link and enter a minimal in-process sidecar shim
directly, without `run_hybrid_template.py` runtime delegation. FC-059 does not
complete this issue unless later states such as GPU artifact load, kernel
launch, and coverage equivalence are also implemented and verified.

## Scope

- Add the minimal bridge from the generated Verilator executable to the hybrid
  sidecar runtime for the recognized `pulp_ita_mha 64x1` closure.
- Reuse existing `src/hybrid/` runtime and generated GPU artifacts; do not add a
  parallel runtime.
- Preserve the FC-055 coverage-equivalence behavior while moving execution from
  runner delegation into the make-built executable path.
- Remove or hide user-facing `GPU_RTL_SIM_REPO_ROOT` style repo-root plumbing
  from the normal command path. If a repo/tool locator is still needed, resolve
  it at install/configure/build time and fail closed when unavailable.
- Keep generated artifacts under `obj_dir`, `artifacts/`, or `reports/` per the
  generated-output policy.

## Acceptance

- For the recognized `pulp_ita_mha 64x1` closure, the normal flow
  `verilator -> make -> obj_dir/V<top>` invokes the GPU sidecar runtime
  directly.
- `obj_dir/V<top>` loads the expected native-path GPU artifact and launches GPU
  kernels; CPU fallback is not used.
- CPU vs hybrid `coverage_output_equivalence` reaches mismatch count 0.
- The normal make/run path does not require the operator to pass
  `GPU_RTL_SIM_REPO_ROOT=<repo>` or select a repo-specific launch template.
- Unrecognized filelist/top remains fail-closed.
- GPU initialization or runtime failure remains fail-closed; no CPU-as-GPU
  fallback.
- Evidence records distinguish direct executable integration from the FC-055
  temporary runner-delegation endpoint.

## Non-claims

- No arbitrary RTL or arbitrary filelist support.
- No dependency inference, automatic allocation, or broad native Verilator
  support.
- No timing or speedup claim unless a later measurement issue records it.
- No raw full-state equality claim.
- No stable external runtime ABI claim beyond the reviewed internal bridge.

## Validation

Required:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_verilator_native_known_closure \
  tests.contract.test_verilator_native_sidecar_make_driver -q
PYTHONDONTWRITEBYTECODE=1 make surface
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/check_staged_large_files.py
```

Plus one real recognized native run through `verilator -> make ->
obj_dir/V<top>` direct GPU execution and coverage compare, and one real
unrecognized filelist/top fail-closed run.
