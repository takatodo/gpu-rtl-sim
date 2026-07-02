# FC-074: Metadata-row Bridge Source Emitter

Status: in progress
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/74
Parent: FC-072 / https://github.com/takatodo/gpu-rtl-sim/issues/72
Related: FC-070 / https://github.com/takatodo/gpu-rtl-sim/issues/71, FC-075 / https://github.com/takatodo/gpu-rtl-sim/issues/75, FC-076 / https://github.com/takatodo/gpu-rtl-sim/issues/76

## Objective

Generalize the FC-072 generated-header approach into a small reusable
interface: metadata rows -> `BridgeSpec` -> generated bridge source/header.
FC-072 scoped the generated header to one hand-picked row
(`microgpt_inference_slice,inference2_hls_friendly,1024x1`); FC-074 lifts that
scope so any promoted row can emit its own header and run through the same
shared bridge binary. The dispatcher and runtime may read metadata, but JSON
never becomes runtime ABI authority; correctness authority stays
mismatch==0 (CPU==GPU) at runtime, never the header.

## Target rows (4)

- `attention_head4_hls_friendly` — promoted GPU dispatch row (direct-binary
  entrypoint upstream of this emitter; also runnable through the shared
  `src-hybrid-verilator` bridge against its own Verilator object directory).
- `mlp4_hls_friendly` — promoted GPU dispatch row (same as above).
- `inference2_hls_friendly` — promoted GPU dispatch row, `src-hybrid-verilator`
  entrypoint; this is the row FC-072 scoped its generated header to.
- `block2_hls_friendly` — fail-closed fallback row (`policy:
  fallback_baseline_no_speedup_improvement`), never GPU-dispatched.

## Current Evidence

- M1: `src/tools/scientific_circt_bridge_spec.py` derives a frozen `BridgeSpec`
  from one source-variant metadata row. Port maps come from new public
  `input_port_names`/`output_port_names` helpers on
  `scientific_circt_hls_mlp_block_variants.py` and
  `scientific_circt_hls_attention_head_variant.py` (never from artifact
  `*_bridge.cpp` files or JSON). `render_bridge_gate_header` emits the 9
  `SCI_CIRCT_BRIDGE_EXPECTED_*` gate macros byte-compatible with the
  pre-FC-074 hand-maintained header, plus new
  `SCI_CIRCT_BRIDGE_APPLY_INPUTS`/`READ_OUTPUTS` macros. Extraction is
  fail-closed on incomplete metadata, unsupported/mismatched entrypoint or
  runtime-boundary kind, non-promoted policy, malformed symbols, unsupported
  element types, and port-count/element-count mismatches.
  `tests/contract/test_scientific_circt_bridge_spec.py` covers all of this,
  including block2 raising before any header render and the generated output
  being verified byte-identical to the pre-refactor logic.
- M2: `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` is
  generalized: its `BridgeIn`/`BridgeOut` structs are sized from the new
  `SCI_CIRCT_BRIDGE_{INPUT,OUTPUT}_ELEMENT_{TYPE,COUNT}` macros, and the
  hand-maintained `inference2`-only port assignments/reads are replaced by
  `SCI_CIRCT_BRIDGE_APPLY_INPUTS`/`READ_OUTPUTS`. Verified against real
  toolchains (not only mocked contract tests): rebuilt the
  `inference2_hls_friendly` object directory/GPU library, compiled the
  generalized bridge with a freshly generated header, and ran it end-to-end —
  mismatch count 0, `cpu_vs_gpu_output_equal`/`cpu_vs_gpu_control_checksum_equal`
  both true, `status: src_hybrid_verilator_callsite_passed`.
- M3: `scientific_circt_source_variant_metadata.src_hybrid_verilator_bridge_gate`
  no longer compares against a single hardcoded `inference2` constant; it
  derives expected values from the metadata row itself (checked for internal
  consistency via `BridgeSpec` and agreement with the dispatch-matrix
  `selected` boundary). `attention_head4_hls_friendly` and
  `mlp4_hls_friendly` now pass gate acceptance at `--no-execute`
  (previously rejected under the old hardcoded gate); `block2_hls_friendly`
  is rejected before dlopen with `entrypoint_kind`/`policy` failed checks.
- M4: `src/tools/scientific_circt_source_variant_bridge_emit.py` is the thin
  CLI: `--source-variant X --emit-header --no-execute` emits one header,
  `--all-promoted --emit-header --no-execute` emits headers for all 3
  promoted rows (exit 0), `--source-variant block2_hls_friendly --emit-header
  --no-execute` fails closed with exit 1 and no header written, and
  `--source-variant X --run` reuses `build_runtime_handoff_report` with
  entrypoint `src-hybrid-verilator` against that row's own Verilator object
  directory, exiting 0 only when both `cpu_vs_gpu_output_equal` and
  `cpu_vs_gpu_control_checksum_equal` are true.
- M5 (GPU acceptance run across all 3 promoted rows through
  `--source-variant X --run`, plus `config/selection.json`/`docs/status.md`/
  `docs/roadmap.md` updates) is pending and out of scope for this pass.

## Tasks

- [x] `BridgeSpec` dataclass and fail-closed extraction from a metadata row.
- [x] Public port-naming helpers on both HLS generators, refactored
      behind-the-scenes without changing generated FIRRTL/bridge output.
- [x] Generated bridge gate header carries struct-sizing and port-assignment
      macros, not just the compact argv-gate constants.
- [x] Shared bridge C++ generalized to any promoted row's element types/counts
      and port names.
- [x] Runtime metadata gate generalized off the single hardcoded constant.
- [x] Thin CLI: emit one header, emit all promoted headers, run one row
      end-to-end.
- [ ] M5: GPU acceptance run for `attention_head4_hls_friendly` and
      `mlp4_hls_friendly` through `--source-variant X --run` (only
      `inference2_hls_friendly` has measured `src-hybrid-verilator` runtime
      evidence so far); refresh `config/selection.json`, `docs/status.md`,
      `docs/roadmap.md` with the result.

## Acceptance

- The 3 promoted rows pass with mismatch 0 and output/checksum equality
  through the generated bridge. (`inference2_hls_friendly` measured; M5
  covers `attention_head4_hls_friendly`/`mlp4_hls_friendly`.)
- `block2_hls_friendly` stays a fail-closed CPU fallback: the emitter and the
  runtime metadata gate both reject it before dlopen, with no header emitted.
- Unsupported shape/steps/source_variant falls back to CPU before any runtime
  dispatch (unchanged from FC-070/FC-072; not touched by this issue).

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/contract/test_scientific_circt_bridge_spec.py \
  tests/contract/test_scientific_circt_source_variant_metadata.py \
  tests/contract/test_scientific_circt_source_variant_runtime_handoff.py \
  tests/contract/test_scientific_circt_hls_mlp_block_variants.py \
  tests/contract/test_scientific_circt_hls_attention_head_variant.py -q

python3 src/tools/scientific_circt_source_variant_bridge_emit.py \
  --all-promoted --emit-header --no-execute

python3 src/tools/scientific_circt_source_variant_bridge_emit.py \
  --source-variant block2_hls_friendly --emit-header --no-execute
# exits non-zero, no header written

python3 -m pytest tests/contract -q -k "scientific_circt"
```

## Non-claims

- No arbitrary RTL bridge generation.
- No automatic partitioning.
- No JSON-only runtime ABI authority — correctness stays mismatch==0
  CPU-vs-GPU at runtime, never the generated header.
- No full-microGPT execution claim.
- No `config/selection.json`/`docs/status.md`/`docs/roadmap.md` promotion
  claim before M5's GPU acceptance run.
