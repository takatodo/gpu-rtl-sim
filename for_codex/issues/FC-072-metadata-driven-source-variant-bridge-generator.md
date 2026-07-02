# FC-072: Metadata-driven Source-Variant Bridge Generator

Status: done
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/72
Parent: FC-070 / https://github.com/takatodo/gpu-rtl-sim/issues/71
Related: FC-043 / https://github.com/takatodo/gpu-rtl-sim/issues/10, FC-063 / https://github.com/takatodo/gpu-rtl-sim/issues/64, FC-065 / https://github.com/takatodo/gpu-rtl-sim/issues/65

## Objective

Turn the measured FC-070 source-variant runtime boundary into a reusable
metadata-driven bridge-generation path instead of maintaining
`src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` by hand for
one selected source variant.

The immediate target remains scoped:

- candidate: `microgpt_inference_slice`
- source variant: `inference2_hls_friendly`
- shape: `1024x1`
- entrypoint: `src-hybrid-verilator`
- runtime boundary: `src_hybrid_verilator_callsite_bridge`

CPU retains token-loop, sampler, KV-cache, unknown variant, unsupported shape,
and step-mismatch authority. GPU authority remains limited to measured batched
arithmetic selected by metadata.

## Current Evidence

- FC-070 / #71 measured the metadata-gated `src-hybrid-verilator` execute path.
- `reports/scientific_circt_source_variant_verilator_entrypoint.json` records
  `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, CPU/GPU output
  equality, control-checksum equality, and all metadata-gate checks true.
- `reports/scientific_circt_source_variant_runtime_dispatcher.json` records
  `runtime_dispatch_measured` with nested
  `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum
  equality, and all metadata-gate checks true.
- `reports/gategpt_testbench_probe.json` refreshes the gateGPT `tb_exp`
  comparison lane with `103/103` mismatch-zero resident/state-indexed evidence,
  while keeping `speedup_claimed=false` and `usefulness_claimed=false`.
- 2026-06-24 progress: the scoped bridge gate is now derived by
  `src/tools/scientific_circt_source_variant_metadata.py:
  src_hybrid_verilator_bridge_gate`, materialized by
  `src/tools/scientific_circt_source_variant_runtime_handoff.py:
  _write_src_hybrid_bridge_gate_header`, and compiled into the bridge with
  `-include artifacts/scientific_circt/source_variant_verilator_entrypoint/scientific_circt_source_variant_bridge_gate.h`.
  The C++ bridge consumes generated `SCI_CIRCT_BRIDGE_EXPECTED_*` macros and
  still checks compact argv metadata before `dlopen`. The refreshed handoff and
  dispatcher reports both pass with mismatch `0`, output/checksum equality, and
  generated header source `source_variant_metadata_row`.
- 2026-06-24 closure audit: the generated-header gate satisfies the scoped
  FC-072 acceptance. The remaining hand-maintained C++ eval/data path is not a
  blocker for this issue because FC-072 scoped only the bridge gate fields, not
  a generic multi-row bridge source emitter.

## Tasks

- Add a generator or reusable emitter that consumes
  `reports/scientific_circt_source_variant_metadata.json` or the metadata model
  behind it and emits the compact bridge gate fields currently hand-maintained
  in `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp`.
- Keep runtime execution fail-closed for unknown variants, unsupported shapes,
  unsupported entrypoints, layout mismatches, and symbol mismatches.
- Preserve CPU ownership for token loop, sampler, KV-cache, unknown variants,
  unsupported shapes, and `steps != 1`.
- Keep GPU ownership limited to measured batched arithmetic selected by
  metadata.
- Add or preserve contract tests proving the generated or metadata-driven bridge
  behavior is equivalent to the current hand-maintained path for the scoped
  `inference2_hls_friendly,1024x1` row.
- Update `config/selection.json`, README, `docs/status.md`, `docs/roadmap.md`,
  `for_codex/issues.md`, FC-070, and this file with the result.

## Acceptance

- The bridge gate fields for the scoped `inference2_hls_friendly,1024x1` row are
  derived from generated metadata or a shared metadata model rather than copied
  as a one-off hand-maintained bridge constant set.
- Existing metadata mismatch behavior remains fail-closed before `dlopen`.
- The dispatcher still rejects unsupported shape and `steps != 1` without
  invoking runtime handoff.
- Output/checksum equality and mismatch `0` remain the correctness gate before
  timing interpretation.
- The result does not broaden into arbitrary RTL bridge generation or automatic
  partitioning.

Acceptance result: complete for the scoped generated-header bridge gate. A
broader source emitter for multiple metadata rows should be opened as a new
follow-up only if that scope is needed later.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_scientific_circt_source_variant_metadata \
  tests.contract.test_scientific_circt_source_variant_runtime_dispatcher \
  tests.contract.test_scientific_circt_source_variant_runtime_handoff -q

python3 src/tools/scientific_circt_source_variant_runtime_dispatcher.py \
  --matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
  --metadata-report reports/scientific_circt_source_variant_metadata.json \
  --source-variant inference2_hls_friendly \
  --write-report \
  --report-out reports/scientific_circt_source_variant_runtime_dispatcher.json

python3 -m json.tool config/selection.json >/dev/null
git diff --check -- README.md config/selection.json docs/status.md docs/roadmap.md for_codex/issues.md for_codex/issues/FC-070-scientific-circt-gpu-candidate-search.md for_codex/issues/FC-072-metadata-driven-source-variant-bridge-generator.md
```

## Non-claims

- No full microGPT execution claim.
- No whole gateGPT `tb_core` speedup claim.
- No arbitrary RTL bridge-generation claim.
- No automatic partitioning claim.
- No runtime ABI authority from JSON alone.
- No usefulness claim without repeated CPU/GPU measurement and scoped
  correctness evidence.
