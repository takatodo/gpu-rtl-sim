# CIRCT Batch-State Lowering RFC Draft

Status: local draft for discussion.

This draft is intended for CIRCT/arcilator maintainers. It proposes a small
experiment around independent-state batch lowering. It does not claim that an
arcilator GPU backend exists.

## Problem

Compiled RTL simulation usually optimizes the latency of one design running one
testbench. A different workload is becoming important: many short, independent
simulations of the same or similar block. Examples include AI-generated RTL
screening, variant search, fuzzing, and block-level arithmetic-kernel
comparison.

For this workload, one important useful parallel axis is across independent
states:

```text
for each independent state i:
  eval(block, state[i], input[i]) -> output[i]
```

The question for CIRCT is whether `arc`/arcilator should expose this axis as a
first-class lowering experiment.

## Scope

The proposed scope is narrow:

- one RTL block already lowered into arcilator's state/eval representation
- a machine-readable state layout
- a direct eval function over one state buffer
- N independent state slots with aligned stride
- deterministic input initialization and output comparison
- CPU state-index baseline first, GPU lowering only as a later experiment

This is not a proposal to replace Verilator, to build a general GPU RTL
simulator, or to accelerate arbitrary full-system RTL.

## Distinction From GEM-Style GPU RTL Emulation

GEM-style GPU RTL simulation attacks single-design simulation latency by mapping
one RTL design into a GPU-oriented virtual Boolean machine. That is an
intra-design parallelization strategy.

This draft asks a different question: when the workload already contains many
independent short simulations, can arcilator expose an inter-state batch axis
directly?

In shorthand:

```text
GEM-style direction:        intra-design GPU emulation
this proposed direction:    inter-state batch lowering
```

The two directions should not be compared by headline speedup numbers. They
optimize different workload shapes.

## Why Not Recover This From Verilator C++ Output

The current project first tried to treat Verilator output as a source for
GPU-oriented relowering. That path is useful as an oracle and as a compatibility
frontend, but it is less direct for this experiment and is not the abstraction
level this proposal should standardize around.

Observed obstacles on the Verilator -> C++ -> LLVM path:

| Obstacle | Why it matters for batch lowering |
|---|---|
| State is hidden behind generated C++ root objects. | Batch slots require explicit, indexable state layout. |
| Scheduler, phase, trigger, and host-runtime scaffolding remain in the output. | The useful block eval is harder to isolate. |
| C++ frontend residue appears in LLVM IR. | Exception, iostream, libc++, malloc, and host ABI residue become relowering hazards. |
| CPU and GPU helper code can drift. | Separate implementations caused formula/checksum drift classes in earlier bridge work. |
| Performance evidence can be over-read. | Positive rows only hold for scoped batchable blocks, not broad RTL. |

This is not a criticism of Verilator's design contract. C++ output is a strong
contract for portable CPU simulation and integration. The point is narrower:
for this experiment, arcilator's state/eval representation is the more direct
place to ask about a compiler-native batch-state axis.

## Why Arc/Arcilator Is a Natural Place

For the measured promoted blocks, arcilator exposes the pieces that the
Verilator path had to reconstruct:

- a state buffer rather than a generated C++ object as the main eval operand
- a machine-readable state file with named state entries and `numStateBytes`
- compact eval functions for the measured promoted blocks
- direct LLVM IR generation without C++ frontend residue for those blocks
- a representation where CPU and future GPU lowering can share the same source
  semantics

The key transformation is conceptually small:

```text
single state:
  eval(uint8_t *state)

batch state:
  parallel_for i in 0..N:
    eval(states + i * align_up(numStateBytes, 16))
```

The alignment detail matters. Local state-index wrappers used aligned stride,
not raw `numStateBytes`.

## Evidence Summary

The following rows are local project evidence for a pre-RFC discussion. Timed
regions differ, so the tables should be read as a boundary map, not a single
global speedup claim.

Current CUDA sidecar split rows:

| Block | Verilator CPU reference | CUDA kernel | CUDA E2E | Bridge wall per batch | Checksum | Classification |
|---|---:|---:|---:|---:|---|
| `attention_head4_hls_friendly` | `3.4998690533333336 ms` | `0.12229589293400446 ms` | `0.2399491066666667 ms` | `0.26312590666666663 ms` | `52263887287239` | output/checksum equal |
| `mlp4_hls_friendly` | `1.3747541600000002 ms` | `0.045670400510231655 ms` | `0.11991521333333334 ms` | `0.13854460000000002 ms` | `345966047` | output/checksum equal |
| `inference2_hls_friendly` | `1.5363670133333331 ms` | `0.045451947152614594 ms` | `0.12304302666666667 ms` | `0.15678281333333333 ms` | `11642153127551538743` | output/checksum equal |

Fair CPU baseline and Verilator-threading rows:

| Block | CUDA bridge wall | Arcilator CPU state-index P16 | Verilator native `--threads` | Warm-thread Verilator-model CPU batch | Classification |
|---|---:|---:|---:|---:|---|
| `attention_head4_hls_friendly` | `0.26312590666666663 ms` | `1.081104 ms` | best `5.737604 ms` | best `3.034948 ms` | Local CUDA sidecar bridge remains `4.1086946310063075x` faster than arcilator CPU P16; this is motivation only, not arcilator GPU evidence. |
| `mlp4_hls_friendly` | `0.13854460000000002 ms` | `0.26276548 ms` | best `3.777501 ms` | best `3.15167 ms` | Local CUDA sidecar bridge remains `1.8966129318645402x` faster than arcilator CPU P16; CPU state-index batch scales `12.09239569824773x` from P1 to P16. |
| `inference2_hls_friendly` | `0.15678281333333333 ms` | `0.20220682666666667 ms` | best `3.834104 ms` | best `3.067504 ms` | Local CUDA sidecar bridge remains `1.2897257190860463x` faster than arcilator CPU P16; CPU state-index batch scales `11.750368401673482x` from P1 to P16. |

Arcilator B1 inspection for promoted blocks also produced compact eval/state
evidence:

| Block | LLVM IR size | Public eval shape | State layout | C++ residue classification |
|---|---:|---|---|---|
| `attention_head4_hls_friendly` | 303 LLVM IR lines, 3 functions | direct eval over one state pointer | `numStateBytes=231`, aligned stride `240` used in batch wrapper | no landingpad/personality/exception/iostream/libc++/malloc tokens, only `exit` declare |
| `mlp4_hls_friendly` | 199 LLVM IR lines, 3 functions | direct eval over one state pointer | `numStateBytes=102` | no landingpad/personality/exception/iostream/libc++/malloc tokens, only `exit` declare |
| `inference2_hls_friendly` | 295 LLVM IR lines, 5 functions | direct eval over one state pointer | `numStateBytes=80`, 14 state entries | no C++ frontend residue reported in the local B1 summary |

## Interpretation

The strongest CPU baseline measured for these rows is arcilator state-index
batch, not native Verilator `--threads` and not one-`Vsim`-per-thread host
batching.

This matters for any GPU claim. GPU kernel-only numbers are not sufficient, and
Verilator serial CPU numbers are not a fair final baseline. The fair question is
whether a GPU batch lowering still wins after comparing against a CPU
state-index lowering that uses the same independent-state axis.

On the current promoted rows, the existing CUDA sidecar bridge still wins
against arcilator CPU state-index P16. The margin narrows substantially:

- `attention_head4_hls_friendly`: `4.1086946310063075x`
- `mlp4_hls_friendly`: `1.8966129318645402x`
- `inference2_hls_friendly`: `1.2897257190860463x`

That boundary is the useful result: independent-state batch lowering appears
valuable on the measured promoted blocks on CPU, and any GPU usefulness claim
should be judged against that baseline.

## Proposed Arcilator Experiment

Start with a CPU-only arcilator experiment, then decide whether a GPU lowering is
worth discussing.

1. Select one small combinational or feed-forward block with a clean arcilator
   state file and direct eval function.
2. Materialize a batch state buffer with `stride=align_up(numStateBytes, 16)`;
   use 1024 independent state slots for the first reproducer to match the local
   evidence shape.
3. Initialize N independent state slots and deterministic input values.
4. Run `eval` over each state slot with a CPU thread pool.
5. Compare selected output bytes against a scalar reference or formula oracle.
6. Report P1/P2/P4/P8/P16 medians for pure eval and eval-plus-inner-repeat.
7. Only after the CPU state-index baseline is stable, prototype an MLIR
   `gpu`/NVVM lowering for the same state-index loop.

The first maintainable target is not a broad simulator. It is a small,
reproducible state-index runner that makes the batch axis explicit.

## Input/Test-Vector Contract

The reproducer also needs a small stimulus contract. Without this, "batch
state" can mean either many copies of one test or many independent tests, and
timing numbers become hard to interpret.

The proposed minimum is a `BatchStimulusSpec`-like sidecar description consumed
by a runner, not a new RTL dialect:

```yaml
version: 0
module: ExampleBlock
steps: 1
state_count: 1024
slot_stride: align_up(numStateBytes, 16)
ports:
  inputs:
    - { name: x0, width: 8, state_entry: x0 }
    - { name: x1, width: 8, state_entry: x1 }
  outputs:
    - { name: y0, width: 32, state_entry: y0 }
stimulus:
  kind: affine_index
  expression: "(state_index * A + port_index * B + C) & mask"
  A: 31
  B: 17
  C: 3
  mask: 255
oracle:
  kind: reference_function
  symbol: example_block_ref
comparison:
  mode: exact
  checksum: true
```

For the first experiment, each state slot is one independent test case. The
runner should:

1. Read the arcilator state file for `numStateBytes` and named state entries.
2. Allocate `state_count` slots using the agreed stride.
3. Fill input state entries deterministically from `state_index` and
   `port_index`.
4. Run `eval` for each slot and step.
5. Read selected output state entries and compare them against the oracle.
6. Report both mismatch details and a checksum so CPU and future GPU lowerings
   can be compared with the same stimulus.

This is intentionally narrower than a full testbench language. It is enough to
make many-independent-vector runs reproducible while leaving arbitrary
SystemVerilog testbench execution out of scope.

The current local promoted-row stimulus examples are:

| Source variant | Inputs | Outputs | Fill formula | Inner-repeat mix |
|---|---:|---:|---|---|
| `attention_head4_hls_friendly` | `80 x uint8_t` | `16 x uint64_t` | `(i * 17 + j * 11 + 1) & 0x7f` | `(r + j) & 31` |
| `mlp4_hls_friendly` | `16 x uint8_t` | `8 x uint64_t` | `(i * 31 + j * 17 + 3) & 0xff` | `(r + j * 3) & 255` |
| `inference2_hls_friendly` | `8 x uint8_t` | `6 x uint64_t` | `(i * 17 + j * 23 + 7) & 0x3f` | `(r + j * 3) & 255` |

Here `i` is the state/test index, `j` is the input or output element index, and
`r` is the inner-repeat index. Port order follows the generator-owned FIRRTL
port order, which is also the order used by the current bridge metadata.
Checksums are diagnostic; exact selected-output equality is the correctness
authority.

## Open Questions For CIRCT Maintainers

- Is independent-state batch execution in scope for arcilator, or should it live
  as an external runner around arcilator output?
- Should the batch axis be represented in `arc`, in a later lowering pass, or in
  a runtime harness that consumes the arcilator state file?
- Is `align_up(numStateBytes, 16)` the right default slot stride contract, or
  should arcilator emit an explicit recommended stride?
- What is the right verifier boundary for state-file entries, input/output
  byte ranges, deterministic initialization, and oracle binding?
- Should a small `BatchStimulusSpec` live in an external runner first, or is
  there an existing CIRCT/arcilator test-vector shape it should reuse?
- Would an MLIR `gpu` dialect experiment be acceptable if the first patch is
  CPU-only and only defines the state-index abstraction?
- Which existing CIRCT tests would make the smallest credible upstream-facing
  reproducer?

## Non-Claims

This draft does not claim:

- an implemented arcilator GPU backend
- CIRCT upstream endorsement
- arbitrary RTL support
- broad GPU RTL speedup
- superiority over GEM-style intra-design emulation
- production-serving readiness
- a stable external runtime ABI
- that Verilator should change its C++ output contract
- raw generated artifacts as the source of truth
- interchangeability of kernel-only, bridge-wall, and CPU state-index timing
  regions

## Proposed First Discussion Prompt

> We measured a narrow workload where many independent short RTL block
> simulations are available. Native Verilator threading and one-model-per-thread
> batching do not expose the same parallel axis, while arcilator's state/eval
> representation makes a CPU state-index runner straightforward. Is an
> independent-state batch lowering experiment in scope for arcilator or CIRCT,
> and where should that axis live?
