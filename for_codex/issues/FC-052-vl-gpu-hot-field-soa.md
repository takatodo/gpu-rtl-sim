# FC-052: vl-gpu-hot-field-soa

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/26
Target file: `src/passes/`, `src/hybrid/`, `src/tools/build_vl_gpu_*`, `tests/contract/`

## Objective

Evaluate a later ABI-changing optimization that splits hot top-level fields
from the AoS state image into SoA buffers for better memory coalescing.

This should not be implemented before the metadata, state-access
canonicalization, inline policy, and resident-step work have clear correctness
and measurement gates.

## Rationale

Current layout:

```text
state0 | state1 | state2 | ...
```

Warp threads reading the same field use:

```text
base + tid * storage_size + field_offset
```

Large `storage_size` can make this a strided access. A future SoA layout could
separate selected hot fields:

```text
cfg_valid_i[state0..N]
done_o[state0..N]
toggle_bitmap[state0..N]
state_image[state0..N]
```

## Risks

- This changes host/GPU ABI.
- Verilator helpers currently expect an AoS root pointer.
- Field access rewrites must be complete and proven safe.
- Partial SoA can create two sources of truth for state if not carefully
  synchronized.

## Acceptance

- A design note or prototype gate identifies candidate hot fields and required
  ABI changes.
- No default runtime behavior changes.
- No helper field is split unless all reads/writes are accounted for.
- Unknown or dynamic field accesses fail closed.

## Validation

```sh
git diff --check
```

Further validation must be defined by the implementation gate.

## Non-Goals

- No first-pass implementation.
- No silent ABI change.
- No broad coalescing/speedup claim without measurement.
