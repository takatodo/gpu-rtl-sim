# FC-048: vl-gpu-state-access-canon

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/22
Target file: `src/passes/VlGpuPasses.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/`

## Objective

Canonicalize provable state-image loads and stores into byte-offset GEPs from
the root/state argument. This should make LLVM and NVPTX optimization more
effective without changing the current AoS state-image ABI.

Depends on FC-047 metadata or an equivalent reviewed source for storage/root
layout facts.

## Safe Transform

Only rewrite pointer expressions when they are proven constant-offset accesses
from the function's state/root pointer argument.

Before:

```llvm
%p = getelementptr inbounds %struct.Root, ptr %state, i32 0, i32 12
%v = load i32, ptr %p, align 4
```

After:

```llvm
%p = getelementptr i8, ptr %state, i64 196
%v = load i32, ptr %p, align 4
```

## Safety Rules

- Do not rewrite non-constant GEPs.
- Do not rewrite pointers through `ptrtoint` / `inttoptr`.
- Do not strengthen alignment unless `!vl.gpu.abi` or argument attributes prove
  it.
- Do not rewrite unknown base pointers.
- Do not delete or move `vlSymsp` rebinding stores.
- Do not change aliasing assumptions beyond what LLVM can prove.

## Acceptance

- A named pass such as `vl-gpu-state-access-canon` exists.
- It rewrites only proven constant-offset state accesses.
- It rejects or leaves unchanged unsafe pointer expressions.
- Existing correctness tests still pass.
- Generated PTX/cubin can be produced for at least one reviewed template.

## Validation

```sh
git diff --check
make -C src/passes --no-print-directory
python3 -m unittest discover -s tests/contract -p '*hybrid*' -q
```

Add focused IR-level tests where possible.

## Non-Goals

- No SoA layout change.
- No trigger guard factoring.
- No resident step loop.
- No speedup claim without a later measurement gate.
