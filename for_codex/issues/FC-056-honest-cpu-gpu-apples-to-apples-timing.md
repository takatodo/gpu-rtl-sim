# FC-056: Honest apples-to-apples CPU-vs-GPU timing for pulp_ita_mha

Status: open
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Predecessor: FC-055 / https://github.com/takatodo/gpu-rtl-sim/issues/55

## Objective

Answer the owner's recurring question — "is the GPU path actually faster?" —
with a scoped, honest, apples-to-apples CPU-vs-GPU wall-time comparison for the
recognized `pulp_ita_mha 64x1` closure, gated on coverage-output equivalence.
This is scoped measurement evidence only: not a production-throughput,
automatic-allocation, or broad-speedup claim.

## Key finding that blocks using existing numbers

The existing `reports/..._cpu_repeat_64x1.json` `elapsed_ms` is NOT comparable
to the GPU `wall_time_ms`:

- CPU `elapsed_ms` (`tlul_slice_host_probe --repeat-states N`) times
  `run_one_probe_state` x N, where each call runs the full probe pipeline
  (reset + batch + drain + eval) that GENERATES a state. This is CPU reference /
  state-generation time.
- GPU `wall_time_ms` / `gpu_kernel_time_ms` (`run_vl_hybrid`) time evaluation of
  an already-captured init state replicated to N states.

These are different regions. Dividing one by the other (e.g. CPU 144 ms /
GPU-kernel 0.025 ms) is exactly the conflation the project forbids.

## Measurement definition (per Codex design inquiry)

Primary indicator: wall-to-wall steady-state execution from a shared init state.

- Prerequisite (excluded from timing): build / verilate / CUBIN generation;
  `cpu_init_state` captured once and shared by both sides.
- CPU side: from the shared init state, run the SAME `nstates x steps` eval
  loop and dump the same coverage-output target — wall time only.
- GPU side: from the same init state, HtoD upload, patch apply, kernel
  launch/sync, DtoH dump — wall time only.
- Gate: `coverage_output_equivalence` mismatch count 0 is required; timing alone
  is not a pass.

Metrics to report:

- `cpu_execution_wall_ms` (NEW, eval-only-from-init region)
- `hybrid_execution_wall_ms`
- repeat-count >= 3 median for each
- `wall_ms_per_state_step = wall_ms / (nstates * steps)`
- `cpu_to_hybrid_wall_ratio_median`

Allowed but secondary (diagnostic, not the headline): `gpu_kernel_time_ms_total`
(GPU-internal efficiency), existing `hybrid wall_time_ms` only if its start
point (HtoD/init/dump inclusion) is stated.

Forbidden comparisons:

- CPU repeat `elapsed_ms` / `gpu_kernel_time_ms_total`
- full host-probe/reference CPU time / GPU kernel-only
- build/verilate/CUBIN-inclusive CPU time / GPU execution-only
- any timing without mismatch=0 confirmed

## Scope

- Add a CPU eval-only-from-init-state measurement mirroring the GPU's exact
  operation (load init state, replicate to N, run S eval steps, dump, time only
  that region). Reuse `src/hybrid` model; no parallel runtime.
- Produce a scoped timing report under `reports/` (evidence only, not source of
  truth), with `coverage_output_equivalence` required.

## Non-claims

- No production throughput, automatic allocation, or broad speedup claim.
- A favorable or unfavorable ratio at this scale (64x1) is scoped evidence only.
- If the GPU is not faster at this scale, that is a valid recorded result, not a
  failure to hide.
- No arbitrary RTL / filelist support.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 make surface
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/check_staged_large_files.py
```

Plus one real measured run recording cpu/hybrid wall medians with mismatch=0.
