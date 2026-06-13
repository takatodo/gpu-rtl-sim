# FC-054: Native sim-accel known-closure Makefile hook for pulp_ita_mha

Status: open
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Backend lane: FC-046 / https://github.com/takatodo/gpu-rtl-sim/issues/20

## Objective

First implementation slice of the owner goal recorded on FC-039 / #1: the patched
Verilator alone, given only command-line options, must produce an `obj_dir`
whose simulation binary executes through the GPU sidecar runtime. No PATH
wrapper, proxy env, review manifest, repo-specific JSON selection, or
user-facing intermediate files.

Design decision (Codex inquiry, 2026-06-12): keep the Verilator patch thin.
When `--sim-accel sidecar-gpu` is active, the patch injects an include/rule
hook into the generated `V<top>.mk`. A repo-side make driver then performs
known-closure recognition and bridges to the existing `build_vl_gpu_*`
pipeline (`src/passes/vlgpugen.cpp` + `VlGpuPasses.cpp` → NVPTX/CUBIN) and
links the `src/hybrid/` runtime so the built binary runs the GPU sidecar path
directly.

## Scope split

- Verilator patch responsibility: hold parsed options; only when `--sim-accel`
  is active, add the hook include/rule to the generated Makefile; fail
  Verilate/build for unsupported modes; never CPU-fallback.
- Repo-side responsibility: known-closure recognition
  (`verilator_native_known_closure.py`), make driver
  (`verilator_native_sidecar_make_driver.py`), existing `build_vl_gpu`
  orchestration reuse, hybrid runtime link glue.

## Owned files

- `overlays/verilator/patches/` (Makefile hook extension of the v5.048 patch)
- `src/tools/verilator_native_known_closure.py`
- `src/tools/verilator_native_sidecar_make_driver.py`
- `src/tools/build_vl_gpu_orchestration.py` (reuse; thin extension only if needed)
- `src/hybrid/Makefile` or a link helper (minimal `Vsim` link change)
- `config/native_known_closures.json` (internal registry; not user-facing input)
- `tests/contract/test_verilator_native_known_closure.py`
- `tests/contract/test_verilator_native_sidecar_make_driver.py`
- `docs/verilator_sidecar_option.md`, `docs/status.md`, `docs/roadmap.md`,
  `for_codex/issues.md`

## Acceptance

- `verilator --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1
  -f <tracked known pulp_ita_mha filelist> --top-module pulp_ita_mha_gpu_cov_tb
  --Mdir obj_dir` succeeds and the generated Makefile contains the sidecar hook.
- `make -C obj_dir -f V<top>.mk` invokes the existing `build_vl_gpu` pipeline;
  NVPTX/CUBIN and hybrid-runtime-linked artifacts are produced under `obj_dir`.
- Running the built `obj_dir` binary alone invokes the GPU sidecar runtime.
- CPU vs hybrid `coverage_output_equivalence` mismatch count is 0 for the
  recognized `pulp_ita_mha 64x1` closure.
- An unrecognized filelist/top fails closed at Verilate or make time with an
  explicit `recognized target only` diagnostic; no dependency inference.
- GPU initialization failure does not fall back to CPU.

## Non-claims

- No arbitrary RTL or arbitrary filelist support.
- No dependency inference, no automatic allocation.
- No speedup or timing claim.
- No raw full-state equality claim.
- Compile-only success is not GPU execution evidence.
- Recognized closure is exactly `pulp_ita_mha 64x1`-class; nothing broader.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_verilator_native_known_closure \
  tests.contract.test_verilator_native_sidecar_make_driver -q
PYTHONDONTWRITEBYTECODE=1 make surface
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/check_staged_large_files.py
```

Plus the real-flow commands above (verilator → make → run) and one
fail-closed run with an unknown filelist/top.
