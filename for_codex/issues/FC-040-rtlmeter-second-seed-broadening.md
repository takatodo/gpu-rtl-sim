# FC-040: RTLMeter Second Seed Broadening

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/4
Target file: `src/tools/rtlmeter_*`, `tests/contract/test_rtlmeter_*`

## Objective

After the first seed `Example:kind:hello` reaches a passing CPU/direct-native
sidecar compare through FC-058 and honest RTLMeter timing evidence exists
(FC-037 / #2), select and integrate exactly one second RTLMeter seed to broaden
coverage. Add representativeness (for example one OpenTitan primitive or one
NVDLA CMAC target) while staying on the RTLMeter-preserving native user path. Do
not claim broad RTLMeter acceleration.

Depends on FC-029 (first seed), FC-030 (compare policy), FC-057 (direct
`obj_dir/V<top>` runtime integration), FC-058 (RTLMeter direct-native
correctness), and FC-037 (timing). Broadening is bounded to one additional seed;
this is not all-design support.

## Tasks

- Gate broadening on a passing FC-058 direct-native compare and FC-037 timing
  evidence for the first seed; do not start before that evidence exists.
- Choose exactly one second seed (candidate: one OpenTitan primitive such as `prim_fifo_sync`, or `NVDLA:default:<cmac_test>`). Prefer the seed reachable through RTLMeter's native case selection with the least repo-specific overlay/template.
- Reuse the FC-025 through FC-028 capture/wrapper/mapping surfaces and the FC-030 compare policy for the second seed; do not fork a parallel path.
- Record the second-seed decision (rationale, candidates compared, why not the others) without editing `config/selection.json` or `config/targets.json` until a reviewed priority change.
- Add a focused contract test for the second seed mirroring the public contract (capture, compileArgs pass-through, fail-closed, debug JSON optional).

## Acceptance

- Exactly one second seed is selected with rationale; broadening stays bounded.
- The second seed reuses the existing non-executing surfaces and the FC-030 compare policy; no new repo-specific launch-template requirement for the public path.
- No broad RTLMeter acceleration claim; the second seed is integration scope only.
- `config/selection.json` and `config/targets.json` are untouched pending a reviewed priority change.
- The decision is recorded and depends on FC-058 direct-native correctness and
  FC-037 timing already existing.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_public_contract -q
```

Extend the public contract for the second seed, or add a focused
`tests/contract/test_rtlmeter_second_seed_*` test that is skipped or fail-closed
when real Verilator or the GPU sidecar is unavailable.

## Non-Goals

- No broad RTLMeter acceleration claim.
- No all-design RTLMeter support.
- No automatic GPU allocation; debug JSON stays debug, not the runtime ABI.
- No edit to `config/selection.json` without a reviewed priority change.
