# FC-051: vl-gpu-resident-step-kernel

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/23
Target file: `src/passes/vlgpugen.cpp`, `src/hybrid/`, `src/tools/run_vl_hybrid*`, `tests/contract/`

## Objective

Add an opt-in resident step kernel that loops over multiple eval steps on the
device, reducing repeated host kernel launches for step-heavy workloads.

This is not a first optimization pass. It needs a separate correctness gate
because host-side patching, scheduling, and observability can change between
steps.

## Proposed ABI

```c
extern "C" __global__
void vl_eval_steps_batch_gpu(uint8_t *storage_base,
                             int32_t nstates,
                             int32_t steps);
```

Each thread still owns one Verilator state image.

## MVP Restrictions

- No host-side patch between steps, or all patches are already represented on
  the device before the loop starts.
- No timing scheduler dependency.
- No host I/O dependency.
- No CPU/GPU sync required between individual steps.
- Correctness must be checked with declared observables such as
  `coverage_output_equivalence`.

## Acceptance

- The kernel is opt-in and absent from default execution unless requested.
- Existing `vl_eval_batch_gpu(storage_base, nstates)` behavior remains
  unchanged.
- Unsupported step schedules fail closed.
- A correctness gate proves at least one reviewed target/shape before any timing
  claim.

## Validation

```sh
git diff --check
make -C src/passes --no-print-directory
python3 -m unittest discover -s tests/contract -p '*resident*' -q
```

## Non-Goals

- No default resident mode change.
- No patch-schedule integration in MVP.
- No runtime/ABI stability promise.
- No speedup claim without a dedicated measurement gate.
