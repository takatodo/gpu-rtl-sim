# FC-047: vl-gpu-abi-metadata

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/21
Target file: `src/passes/vlgpugen.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/`

## Objective

Emit GPU ABI metadata into generated LLVM IR so later optimization passes can
read state layout and kernel ABI facts without scraping command-line arguments
or generated JSON.

The metadata should describe the existing ABI, not change it.

## Proposed Metadata

```llvm
!vl.gpu.abi = !{!0}
!0 = !{
  !"abi_version", i32 1,
  !"storage_size", i64 2112,
  !"storage_stride", i64 2112,
  !"state_root_offset", i64 0,
  !"state_base_align", i64 8,
  !"kernel", !"vl_eval_batch_gpu",
  !"layout", !"aos",
  !"syms_state_image", i1 false
}
```

`vlSymsp` offsets may be included when available, but metadata consumers must
handle their absence.

## Tasks

- Add metadata emission in `vlgpugen` after the selected storage/root/syms
  values are known.
- Keep metadata descriptive; do not make it execution authority.
- Add a small parser/helper or test assertion that verifies the metadata exists
  in generated IR.
- Keep build metadata JSON as debug/review output, not the runtime ABI.

## Acceptance

- Generated IR contains `!vl.gpu.abi` for `vl_eval_batch_gpu`.
- Metadata values match the CLI inputs used by `vlgpugen`.
- Existing build/run paths continue to work without changing host/runtime ABI.
- Missing metadata causes later optimization passes to fail closed, not guess.

## Validation

```sh
git diff --check
make -C src/passes --no-print-directory
```

Add or extend a focused contract test that inspects generated IR metadata.

## Non-Goals

- No optimization by this issue alone.
- No SoA conversion.
- No resident step kernel.
- No broad `verilator --use-gpu` claim.
