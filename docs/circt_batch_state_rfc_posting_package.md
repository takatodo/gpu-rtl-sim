# CIRCT Batch-State RFC Posting Package

Status: posting-ready local package, not yet posted publicly.

Source draft: `docs/circt_batch_state_rfc_draft.md`.

Recommended first route: LLVM Discourse CIRCT category. CIRCT's public project
site and README list the LLVM Discourse forum as a community entry point, with
Discord and the weekly video chat as follow-up venues. This package should be
posted as a design question first; if maintainers show interest or ask for live
discussion, the next step is to request a weekly video chat/Open Design Meeting
slot.

Do not claim public posting until it has actually happened.

## Paste Instructions

Discourse category:
`https://discourse.llvm.org/c/projects-that-want-to-become-official-llvm-projects/circt/40`

Title:
`Measured boundary for independent-state batch execution in arcilator/arc`

Body to paste: copy from `## Short Summary` through `## Explicit Non-Claims`.
Do not paste the local `Status`, `Source draft`, `Recommended first route`,
`Paste Instructions`, or `Recommended Posting Decision` sections.

## Suggested Title

Measured boundary for independent-state batch execution in arcilator/arc

## Short Summary

I would like feedback on whether independent-state batch execution belongs in
arcilator/arc, or should remain an external runner around arcilator output.

The workload is not single-design simulation latency. The workload is many
short, independent simulations of the same or similar block: generated RTL
screening, variant search, fuzzing, or block-level arithmetic-kernel comparison.
In that setting, one important useful axis is across independent states:

```text
for each independent state i:
  eval(block, state[i], input[i]) -> output[i]
```

We first tried to recover this axis from Verilator-generated C++ and LLVM IR.
That path works as a CPU oracle and compatibility frontend, but it is less
direct for this experiment: state is hidden in generated C++ root objects,
host/runtime residue enters the IR, scheduling scaffolding obscures the block
eval, and CPU/GPU helper code can drift.

For the measured local test blocks, arcilator exposes a cleaner discussion
point: a state file, a state buffer, and an eval function over one state
pointer. The local question is whether the batch axis should become a
first-class experiment around that representation:

```text
single state:
  eval(uint8_t *state)

batch state:
  parallel_for i in 0..N:
    eval(states + i * align_up(numStateBytes, 16))
```

Local evidence suggests the fair CPU baseline is a local CPU state-index batch
runner around arcilator output, not native Verilator `--threads` and not
one-Verilated-model-per-thread host batching. In these local measurements, the
CUDA sidecar bridge has lower wall time on the same blocks, but the margin
narrows substantially once compared against that local arcilator-output CPU
state-index runner. That boundary is why I am asking about the representation,
not claiming a general GPU RTL simulator.

## Compact Evidence

Timed regions differ. Treat this table as a boundary map, not one global speedup
claim.

| Block | Current CUDA bridge wall | Local arcilator-output CPU state-index P16 | Verilator native `--threads` | Warm-thread Verilator-model CPU batch | Classification |
|---|---:|---:|---:|---:|---|
| `attention_head4_hls_friendly` | `0.263 ms` | `1.081 ms` | best `5.738 ms` | best `3.035 ms` | Local CUDA sidecar bridge is `4.11x` lower wall time than the local arcilator-output CPU P16 runner; this is motivation only, not arcilator GPU evidence. |
| `mlp4_hls_friendly` | `0.139 ms` | `0.263 ms` | best `3.778 ms` | best `3.152 ms` | Local CUDA sidecar bridge is `1.90x` lower wall time than the local arcilator-output CPU P16 runner; the local CPU state-index batch runner scales `12.09x` from P1 to P16. |
| `inference2_hls_friendly` | `0.157 ms` | `0.202 ms` | best `3.834 ms` | best `3.068 ms` | Local CUDA sidecar bridge is `1.29x` lower wall time than the local arcilator-output CPU P16 runner; the local CPU state-index batch runner scales `11.75x` from P1 to P16. |

Arcilator B1 structure for the same promoted-block family:

| Block | LLVM IR size | Eval shape | State layout | C++ residue classification |
|---|---:|---|---|---|
| `attention_head4_hls_friendly` | 303 LLVM IR lines, 3 functions | direct eval over one state pointer | `numStateBytes=231`, aligned stride `240` used in local batch wrapper | no landingpad/personality/exception/iostream/libc++/malloc tokens, only `exit` declare |
| `mlp4_hls_friendly` | 199 LLVM IR lines, 3 functions | direct eval over one state pointer | `numStateBytes=102` | no landingpad/personality/exception/iostream/libc++/malloc tokens, only `exit` declare |
| `inference2_hls_friendly` | 295 LLVM IR lines, 5 functions | direct eval over one state pointer | `numStateBytes=80`, 14 state entries | no C++ frontend residue reported in the local B1 summary |

Repro packet status:

- Local repo snapshot used for this posting package: `4527646` with a dirty
  working tree; the package is not externally reproducible from a clean public
  commit yet.
- Local arcilator/arc test material: `arc-tests` snapshot `8dad869`; arcilator
  and `firtool` binaries are not on `PATH` in the current shell.
- Hardware/toolchain for the recorded CUDA/Verilator rows: NVIDIA GeForce RTX
  4070 Ti SUPER, driver `591.86`, CUDA compiler build
  `cuda_12.0.r12.0/compiler.32267302_0`, Verilator `5.044`.
- Evidence paths: `reports/scientific_circt_hls_attention_head4.json`,
  `reports/scientific_circt_hls_mlp_block_variants.json`,
  `for_codex/issues/FC-079-baselines-and-arcilator-confirmation-shot.md`, and
  `for_codex/issues/FC-080-rfc-draft-breadth-baselines-for-multi-block-batch-state-lowering.md`.
- Shapes: `state_count=1024`, `steps=1`, `inner_repeat=1000`; table medians are
  local wall-time rows with different timed regions, so they are not a single
  speedup claim.

## Proposed Small Experiment

Start CPU-only and make the batch axis explicit before discussing any GPU
backend:

1. Pick one small combinational/feed-forward `steps=1` block with a clean
   arcilator state file and direct eval function.
2. Allocate 1024 independent state slots using
   `stride=align_up(numStateBytes, 16)`.
3. Zero each state slot, then initialize deterministic inputs and selected
   output bytes for each slot.
4. Run the eval function over all state slots with a CPU thread pool.
5. Compare output bytes against a scalar/formula oracle.
6. Report P1/P2/P4/P8/P16 medians for pure eval and eval-plus-inner-repeat.
7. Only after that baseline is reviewed as the right comparison point,
   separately discuss whether an MLIR `gpu`/NVVM prototype is useful.

First-reproducer exclusions: no arbitrary SystemVerilog testbench, no DPI or
black boxes, no memories that require external initialization beyond the state
file and deterministic slot fill, and no multi-cycle protocol beyond `steps=1`.

## Input/Test-Vector Contract

The reproducer needs one more explicit piece: a small contract for input vectors
and output comparison. In this proposal, one state slot is one independent test
case, not one lane of a single testbench.

The local runner shape is:

```text
module: MicrogptInferenceHls2
state_count: 1024
steps: 1
slot_stride: align_up(numStateBytes, 16)
inputs:
  - name: i0_tok0
    width: 8
  - name: i1_pos1
    width: 8
outputs:
  - name: i0_y0
    width: 64
  - name: i1_y2
    width: 64
stimulus:
  input[state_index][port_index] =
    (state_index * A + port_index * B + C) & mask
oracle:
  scalar reference function or formula
comparison:
  exact selected output bytes; checksum diagnostic only
```

A minimal runner would consume the arcilator state file to map named input and
output state entries, fill each slot deterministically, run `eval` for each
slot, then compare selected outputs against the oracle. This is not a proposal
for arbitrary SystemVerilog testbench execution; it is just enough structure to
make many-independent-vector runs reproducible across CPU state-index and any
future GPU lowering.

In the local harness this boundary is now represented by an importable
`BatchStimulusSpec` helper derived from the same promoted metadata rows as the
existing bridge contract. It records the shape, slot-stride convention,
generator-owned fill/mix formulas, selected I/O entries, oracle kind, exact
selected-output comparison, and checksum-as-diagnostic policy. It does not add a
new runtime ABI or an arcilator GPU backend. Port order follows the
generator-owned FIRRTL port order used by the existing bridge metadata.

Current local promoted-row examples:

| Source variant | Inputs | Outputs | Fill formula | Inner-repeat mix |
|---|---:|---:|---|---|
| `attention_head4_hls_friendly` | `80 x uint8_t` | `16 x uint64_t` | `(i * 17 + j * 11 + 1) & 0x7f` | `(r + j) & 31` |
| `mlp4_hls_friendly` | `16 x uint8_t` | `8 x uint64_t` | `(i * 31 + j * 17 + 3) & 0xff` | `(r + j * 3) & 255` |
| `inference2_hls_friendly` | `8 x uint8_t` | `6 x uint64_t` | `(i * 17 + j * 23 + 7) & 0x3f` | `(r + j * 3) & 255` |

Here `i` is the state/test index, `j` is the input or output element index, and
`r` is the inner-repeat index. Checksums are diagnostic; exact selected-output
equality is the correctness authority.

## Primary Question For CIRCT Maintainers

Should this begin as an external CPU state-index runner around arcilator output,
or is there an in-tree arcilator/arc representation you would prefer?

Follow-up questions:

- Should arcilator emit an explicit recommended state slot stride instead of
  relying on consumers to infer `align_up(numStateBytes, 16)`?
- Which existing CIRCT tests or arcilator examples would be the smallest
  credible reproducer?
- Later, separately: if the CPU state-index baseline is the right comparison
  point, is an MLIR `gpu`/NVVM prototype for the same state-index loop useful?

## Explicit Non-Claims

This is not claiming:

- an implemented arcilator GPU backend
- CIRCT upstream endorsement
- arbitrary RTL support
- broad GPU RTL speedup
- superiority over GEM-style intra-design emulation
- production-serving readiness
- a stable external runtime ABI
- that Verilator should change its C++ output contract
- that kernel-only, bridge-wall, and CPU state-index timings are
  interchangeable
- that the thread has already been posted publicly

## Private Pre-Review Message Template

Subject:
`Question about independent-state batch execution around arcilator/arc`

Body:

```text
Hi <name>,

I have a small CIRCT/arcilator design question and would appreciate a quick
pre-review before I post it publicly.

The question is not about a GPU backend claim. It is whether a CPU
state-index runner around arcilator output is the right first representation
for many short independent simulations of the same block:

  eval(states + i * align_up(numStateBytes, 16))

The feedback I need is:

1. Should this begin as an external runner around arcilator output, or is
   there an in-tree arcilator/arc representation you would prefer?
2. Should arcilator expose a recommended state slot stride?
3. Which existing CIRCT test or arcilator example would be the smallest
   credible reproducer?

Non-claims: no arcilator GPU backend, no CIRCT endorsement, no arbitrary
SystemVerilog testbench support, no stable runtime ABI, no GEM replacement
claim, and no broad GPU RTL speedup claim.

Draft/package:
<link or pasted docs/circt_batch_state_discourse_body.md>
```

## Recommended Posting Decision

Post first to the LLVM Discourse CIRCT category as a design-question thread.
Do not start with a pull request: the proposal is still about scope and
representation. Do not start with a live meeting: the evidence table and
non-claims need asynchronous review first. If the Discourse thread receives
maintainer interest, ask whether a weekly video chat/Open Design Meeting slot is
useful and prepare a smaller live agenda from the same material.

Private pre-review is optional if a known CIRCT/arcilator maintainer is already
available. Without a named reviewer, private review should not block the public
Discourse question.
