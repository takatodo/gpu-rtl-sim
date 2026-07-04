# FC-085: Batch stimulus spec for arcilator state-index runner

Status: done

GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/86

## Objective

Turn the CIRCT/arcilator independent-state batch discussion into a concrete
input/test-vector contract that can be reviewed separately from any GPU backend
claim.

The goal is not to create a general SystemVerilog testbench language. The goal
is a minimal `BatchStimulusSpec`-style runner contract where one state slot is
one independent test case, deterministic inputs are reproducible from the state
index, and selected outputs are compared against a scalar/formula oracle.

## Scope

- Define the minimum fields for a `BatchStimulusSpec`-style sidecar description:
  module, steps, state_count, stride, input/output state entries, stimulus
  generator, oracle binding, comparison mode, and checksum policy.
- Capture the current promoted-row examples from generator-owned metadata:
  `attention_head4_hls_friendly` (`80 x uint8_t` input, `16 x uint64_t` output,
  fill `(i * 17 + j * 11 + 1) & 0x7f`, mix `(r + j) & 31`),
  `mlp4_hls_friendly` (`16 x uint8_t` input, `8 x uint64_t` output, fill
  `(i * 31 + j * 17 + 3) & 0xff`, mix `(r + j * 3) & 255`), and
  `inference2_hls_friendly` (`8 x uint8_t` input, `6 x uint64_t` output, fill
  `(i * 17 + j * 23 + 7) & 0x3f`, mix `(r + j * 3) & 255`).
- Keep the first target CPU-only around arcilator output and its state file.
- Make the verifier boundary explicit: state entries exist, widths fit, output
  byte ranges are selected, stimulus is deterministic, and oracle binding is
  present before timing is accepted.
- Decide whether the spec remains an external runner contract first or can reuse
  an existing CIRCT/arcilator test-vector shape.

## Acceptance

- `docs/circt_batch_state_rfc_draft.md` explains the input/test-vector contract
  well enough that a CIRCT developer can distinguish `64x1` style independent
  vectors from one long testbench.
- The RFC draft contains a concrete promoted-row stimulus table and states that
  checksums are diagnostic while exact selected-output equality is correctness
  authority.
- The posting package/body mention the contract without claiming arbitrary
  SystemVerilog testbench execution.
- A later implementation issue can consume this as the acceptance boundary for
  a CPU state-index runner; this issue itself does not require implementing that
  runner.

## 2026-07-04 Progress

- Added importable `BatchStimulusSpec` support in
  `src/tools/scientific_circt_bridge_spec.py`, derived from the same
  fail-closed promoted metadata rows as `BridgeSpec`.
- The helper fixes the current independent-state vector contract: one state
  slot is one test case, `shape` supplies `state_count x steps`, slot stride is
  recorded as `align_up(numStateBytes, 16)`, input fill and inner-repeat mix
  formulas come from generator-owned constants, exact selected-output equality
  remains correctness authority, and checksum is diagnostic only.
- Added focused contract tests for `attention_head4_hls_friendly`,
  `mlp4_hls_friendly`, and `inference2_hls_friendly`, including fail-closed
  checks for missing `inner_repeat`, malformed `shape`, and invalid override
  counts.
- Still not implemented here: an arcilator state-index runner, arbitrary
  SystemVerilog testbench execution, runtime ABI stabilization, or any arcilator
  GPU backend.

## 2026-07-04 Closure Audit

Acceptance is met in the working tree: the RFC draft, posting package/body, and
importable helper now define the independent-state input-vector contract, and
`python3 -m unittest tests.contract.test_scientific_circt_bridge_spec` passes
17 tests. Do not close GitHub #86 until the relevant local files are committed
and pushed or otherwise synced to GitHub; otherwise the closure would depend on
untracked/local-only evidence. Files that must be included in that sync include
`docs/circt_batch_state_rfc_draft.md`,
`docs/circt_batch_state_rfc_posting_package.md`,
`docs/circt_batch_state_discourse_body.md`, this issue file, the
`BatchStimulusSpec` helper, and its contract tests.

## 2026-07-04 Publish Sync

The scoped evidence bundle is ready to publish as a focused commit containing
the RFC draft, posting package/body, this issue file, the active FC-084 source
artifact, `BatchStimulusSpec`, and the focused contract tests. Once that commit
is pushed, GitHub #86 can be closed without relying on local-only evidence.

## Non-Claims

- No arcilator GPU backend.
- No CIRCT upstream endorsement.
- No arbitrary RTL or arbitrary testbench support.
- No broad speedup or usefulness claim.
- No stable runtime ABI.
