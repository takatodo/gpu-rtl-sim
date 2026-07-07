# FC-050: vl-gpu-trigger-guard-factor

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/25
Target file: `src/passes/VlGpuPasses.cpp`, `src/passes/vlgpugen.cpp`, `tests/contract/`

## Objective

Reduce repeated Verilator trigger-mask checks only when the guard structure is
proven safe. This issue is intentionally narrower than a general CFG optimizer.

The current `vlgpugen` already extracts guarded segments and creates guarded
wrappers for some `eval_nba` paths. This pass should start from those simple
wrapper-generated patterns instead of scanning arbitrary Verilator CFGs.

## Initial Scope

Group adjacent guards only when all are true:

- Same trigger pointer identity and byte offset.
- Same load type, mask, predicate, and execute-on-true polarity.
- Adjacent single-call guarded blocks.
- No store to the trigger word between grouped calls.
- No volatile or atomic memory operations are crossed.
- Callees are proven not to write the trigger word.
- Call order is preserved.

## Non-Scope For First Implementation

- Do not move arbitrary basic block regions.
- Do not group across unknown side-effect calls.
- Do not group across trigger clear wrappers.
- Do not rewrite phase semantics.

## Acceptance

- The pass refuses complex or unsafe guard layouts.
- The pass reduces duplicated guard load/mask/icmp only for the safe adjacent
  case.
- Existing `coverage_output_equivalence` checks still pass on reviewed targets.
- Branch/load-count reduction is reported as diagnostic, not speed evidence.

## Validation

```sh
git diff --check
make -C src/passes --no-print-directory
python3 -m unittest discover -s tests/contract -p '*hybrid*' -q
```

Add focused IR tests for safe grouping and unsafe refusal cases.

## Non-Goals

- No general CFG optimization.
- No grouping across unknown side effects.
- No speedup claim without later measurement.
