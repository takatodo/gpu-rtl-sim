# FC-059: Native obj_dir executable sidecar shim link smoke

Status: open
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/59
Parent task: FC-057 / https://github.com/takatodo/gpu-rtl-sim/issues/57
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Predecessor: FC-055 / https://github.com/takatodo/gpu-rtl-sim/issues/55

## Objective

Split the first executable-level bridge out of FC-057: the generated
`obj_dir/V<top>` binary for the recognized native `pulp_ita_mha 64x1` closure
must link and enter a minimal in-process sidecar shim directly, without
delegating runtime execution to `run_hybrid_template.py`.

This is a smoke slice for the hardest first question in FC-057: can the
make-built Verilator executable call repo-owned sidecar runtime code directly at
all?

## Current Boundary

FC-055 is complete only as a temporary reviewed endpoint. It reaches real GPU
kernel launch and `coverage_output_equivalence` mismatch count 0 by delegating
to the existing `run_hybrid_template.py` seven-stage flow.

FC-055 does not prove that `obj_dir/V<top>` itself links sidecar runtime code,
loads a GPU artifact, launches a kernel, or performs the coverage compare.

## Scope

- Add a tiny C/C++ sidecar shim callable from the Verilator-built executable.
- Wire the generated native sidecar build / Makefile path so `obj_dir/V<top>`
  links that shim for the recognized `pulp_ita_mha 64x1` closure.
- On execution, the shim must emit or record evidence that the native executable
  path was reached directly.
- Do not call or exec `run_hybrid_template.py` from the runtime path.
- It is acceptable for this slice to stop before full GPU artifact ABI/state
  plumbing, kernel launch, or coverage equivalence, as long as the stop is
  fail-closed and explicitly classified.
- Unrecognized filelist/top remains fail-closed.

## Implementation Ownership

Primary owned files:

- `src/tools/verilator_native_sidecar_make_driver.py`
- `tests/contract/test_verilator_native_sidecar_make_driver.py`
- New or existing `src/hybrid/*` minimal C/C++ sidecar shim source.

Conditional owned files, only if the direct shim cannot be linked through the
current driver surface:

- `src/tools/build_vl_gpu_finalize.py` or another existing link/finalize helper.
- `overlays/verilator/patches/verilator_native_sidecar_makefile_build_hook_v5_048.patch`
- `overlays/verilator/patches/verilator_native_sidecar_makefile_build_hook_v5_048.json`
- `tests/contract/test_verilator_native_sidecar_makefile_build_hook_patch.py`

The main implementation decision is inside the current
`run_native_sidecar_build()` boundary. Today that path delegates a recognized
closure to `run_hybrid_template.py`; FC-059 owns replacing or branching that
runtime path with a minimal direct-shim path for the recognized closure.

## Acceptance

- For the recognized closure, the normal command sequence reaches the shim:

```sh
verilator --cc --exe --sim-accel sidecar-gpu \
  --sim-accel-states 64 --sim-accel-steps 1 \
  -f <known pulp_ita_mha filelist> --top-module pulp_ita_mha_gpu_cov_tb
make -C obj_dir -f V<prefix>.mk
obj_dir/V<prefix>
```

- `obj_dir/V<prefix>` directly enters the native sidecar shim.
- Runtime evidence distinguishes at least these states:
  - direct executable shim reached;
  - GPU artifact loaded;
  - GPU kernel launched;
  - coverage equivalence passed.
- This issue only requires the first state unless later states are actually
  implemented and verified.
- Missing GPU/runtime prerequisites fail nonzero; they must not fall back to CPU.
- CPU fallback is impossible and explicitly not used.
- No `run_hybrid_template.py` execution occurs from the runtime path.
- Unrecognized filelist/top remains fail-closed.

## Acceptance Clarifications

- `GPU_RTL_SIM_REPO_ROOT` may remain a make-time locator for this smoke slice,
  because removing user-facing repo-root plumbing belongs to full FC-057. The
  runtime execution path itself must not require an operator-selected template
  runner or invoke `run_hybrid_template.py`.
- The current Makefile hook uses an order-only stamp
  (`| $(VL_SIDECAR_STAMP)`) so the stamp does not enter `$^` link inputs. FC-059
  acceptance requires moving beyond that: a sidecar shim object/library, or an
  equivalent repo-owned main/runtime object, must be present in the final
  `obj_dir/V<top>` link inputs. A pre-link stamp or successful driver run alone
  is not shim-entry evidence.
- The direct-shim evidence should be written under the generated `obj_dir`, for
  example `obj_dir/native_sidecar_runtime.json`. Generated evidence remains an
  evidence snapshot, not source of truth.
- The evidence must include at least:
  - `direct_executable_shim_reached: true`
  - `template_flow_invoked: false`
  - `cpu_as_gpu_fallback: false`
  - `gpu_artifact_loaded: false` unless actually loaded
  - `gpu_kernel_launched: false` unless actually launched
  - `coverage_equivalence_passed: false` unless actually compared
- If the shim is reached and this smoke slice intentionally stops before GPU
  artifact load, exit `0` is allowed only when the evidence clearly classifies
  the result as shim-entry smoke, not GPU execution. Missing prerequisites for
  the shim/link path itself must fail nonzero.
- Contract tests must prove `run_hybrid_template.py` is not invoked on the
  direct-shim runtime path, for example via a fake runner call count of zero or
  required evidence field `template_flow_invoked: false`.

## Non-claims

- Does not complete FC-057 by itself.
- No coverage equivalence claim unless the compare actually runs and records
  mismatch count 0.
- No GPU kernel-launch claim unless a real kernel launch is recorded.
- No timing or speedup claim.
- No arbitrary RTL or arbitrary filelist support.
- No dependency inference or automatic allocation claim.
- No CPU-as-GPU fallback.

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
obj_dir/V<prefix>` that records direct shim entry, and one real unrecognized
filelist/top fail-closed run.
