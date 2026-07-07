# FC-055: Native sidecar runtime handoff and coverage gate

Status: completed
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/55
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Predecessor: FC-054 / https://github.com/takatodo/gpu-rtl-sim/issues/54

## Closure Boundary

FC-055 is complete as a temporary reviewed endpoint: the native make driver can
delegate the recognized `pulp_ita_mha 64x1` closure to the existing
`run_hybrid_template.py` seven-stage flow, reaching real GPU kernel launch and
`coverage_output_equivalence` mismatch count 0. This does not prove direct
`obj_dir/V<top>` GPU runtime integration.

The preferred owner-goal endpoint moved to FC-057 / #57: the generated
make-built `obj_dir/V<top>` executable must invoke the GPU sidecar runtime
directly, with no template-runner delegation or user-facing repo-root plumbing.

## Objective

Close the next native-path gap after FC-054 milestone 3: the recognized
`pulp_ita_mha 64x1` native command must not stop at CUBIN generation. The
native path must produce a runnable `obj_dir` binary or equivalent make-built
native artifact that invokes the GPU sidecar runtime directly and reaches
`coverage_output_equivalence` with mismatch count 0.

The owner goal remains: `verilator --sim-accel sidecar-gpu ... -f filelist
--top-module top` followed by the normal build/run path, with no PATH wrapper,
proxy env, review manifest, repo-specific JSON selection, or user-facing
intermediate operation.

## Current Boundary From FC-054

FC-054 proves:

- native `--sim-accel sidecar-gpu` parser path reaches generated Makefile hook;
- `make` invokes the repo-side driver;
- the tracked `pulp_ita_mha` closure is recognized;
- `build_vl_gpu` is driven from that native path;
- a real SM89 CUBIN with GPU kernels is produced.

FC-054 does not prove:

- the `obj_dir` binary invokes the GPU sidecar runtime;
- native-path host-probe/state-init inputs match the working template flow;
- CPU-vs-hybrid coverage output equivalence;
- timing or speedup.

## Scope

- Add the missing native-path host-probe/state-init/runtime handoff needed to
  execute the generated CUBIN correctly.
- Decide and implement the minimal integration shape:
  - preferred endpoint: make-built `obj_dir/V<top>` invokes the hybrid sidecar
    runtime directly; or
  - temporary reviewed endpoint: generated Makefile target drives the existing
    runner as a build/run target while clearly not claiming `obj_dir` binary
    integration yet.
- Reuse existing `src/hybrid/`, `run_vl_hybrid*`, and `build_vl_gpu*` pieces
  instead of adding a parallel runtime.
- Keep all generated build outputs under `obj_dir`, `artifacts/`, or `reports/`
  according to the existing generated-output policy.

## Acceptance

- The recognized `pulp_ita_mha 64x1` native command runs through:
  `verilator --sim-accel sidecar-gpu ... -f <tracked filelist>
  --top-module pulp_ita_mha_gpu_cov_tb` -> `make` -> native GPU sidecar run.
- The run loads the native-path GPU artifact and launches GPU kernels; CPU
  fallback is not used.
- Native-path state image / host-probe metadata are compatible with the runtime
  and do not reproduce the FC-054 `storage_size 5760 vs 6144` mismatch.
- CPU vs hybrid `coverage_output_equivalence` reaches mismatch count 0 for the
  recognized closure.
- Unrecognized filelist/top remains fail-closed.
- GPU initialization or runtime failure remains fail-closed; no CPU-as-GPU
  fallback.
- The resulting issue comment records exact commands and evidence boundaries.

## Non-claims

- No arbitrary RTL or arbitrary filelist support.
- No dependency inference, automatic allocation, or broad native Verilator
  support.
- No speedup or timing claim unless a separate measurement gate records it.
- No raw full-state equality claim.
- Compile-only success and CUBIN generation alone are not GPU execution
  evidence.

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

Plus one real recognized native run through Verilator -> make -> GPU sidecar
execution -> coverage compare, and one real unrecognized filelist/top
fail-closed run.
