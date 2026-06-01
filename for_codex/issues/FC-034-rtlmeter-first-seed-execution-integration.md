# FC-034: RTLMeter First Seed Execution Integration

Status: open
Owner: unassigned
Target file: `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*`

## Objective

Move from FC-030's non-executing compare policy to a real CPU vs GPU-sidecar
comparison run for the selected first seed `Example:kind:hello`, producing
regenerable evidence under `reports/` without claiming speedup and without
breaking RTLMeter's native UX.

Depends on FC-025 (command capture), FC-026 (PATH wrapper), FC-027 (compileArgs
pass-through), FC-028 (sidecar contract mapping), FC-029 (seed = `Example:kind:hello`),
and FC-030 (compare policy). This issue is the first one allowed to actually
execute; all prior RTLMeter issues are non-executing by design.

## Tasks

- Run RTLMeter's normal CPU execute for `Example:kind:hello` as the CPU reference, or document the exact RTLMeter command used.
- Run the GPU sidecar candidate launched from the RTLMeter-preserving Verilator argv (`--compileArgs "--use-gpu"` or a PATH-selected `verilator` wrapper).
- Compare per FC-030's policy: normalized stdout transcript and reported RTLMeter cycle count must match. Keep RTLMeter execute metrics/postHook intact; do not conflate RTLMeter timing with sidecar timing.
- Write the regenerable compare report to `reports/rtlmeter_example_kind_hello_cpu_gpu_compare.json` only. Reports are not source of truth.
- Gate execution behind explicit opt-in (env var or flag). Fail closed when real Verilator, the GPU sidecar build, or the wrapper prerequisites are missing; never silently fall back to a CPU run and report it as GPU.
- If the environment cannot execute (no real Verilator or no GPU sidecar), record an honest "cannot execute here" first state and mark the issue `blocked` with the missing prerequisite rather than faking a result.

## Acceptance

- A documented, regenerable command runs the CPU/GPU compare for `Example:kind:hello` and writes a report under `reports/`.
- The compare uses FC-030's declared observable outputs; RTLMeter metrics/postHook are preserved and not overwritten.
- No speedup or acceleration claim is made; timing stays diagnostic-only until separately measured.
- Fail-closed behavior when real Verilator or the GPU sidecar is unavailable; no CPU-as-GPU misreport.
- `config/selection.json` and `config/targets.json` are not edited; broadening to other RTLMeter designs stays gated.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_cpu_gpu_compare_integration -q
```

Add or extend an executing-path contract test that is skipped or fail-closed when
real Verilator or the GPU sidecar is unavailable, so the suite stays green in a
non-GPU environment.

## Non-Goals

- No broad RTLMeter acceleration claim.
- No automatic GPU allocation.
- No promotion of debug JSON into the runtime ABI.
- No requirement that RTLMeter users select repo-specific launch templates.
