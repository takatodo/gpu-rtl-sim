# FC-027: RTLMeter CompileArgs Pass-Through Smoke

Status: done
Owner: Codex
Target file: `tests/contract/test_rtlmeter_*`

## Objective

Pin the user-facing RTLMeter pass-through path where the user adds GPU intent through RTLMeter's existing `--compileArgs` mechanism.

## Tasks

- Add a non-executing contract test for `./rtlmeter run --cases ... --compileArgs "--use-gpu"`.
- Verify that the GPU intent reaches the Verilator wrapper or command-capture layer.
- Avoid full RTLMeter benchmark execution in the contract test unless explicitly scoped.
- Include a clear skip or fixture path when the RTLMeter submodule is absent.

## Acceptance

- The test proves command pass-through, not performance.
- The test does not mutate RTLMeter descriptors.
- The test does not claim GPU execution.

## Validation

```sh
python3 -m unittest tests.contract.test_rtlmeter_compileargs_pass_through_smoke -q
```

Result: passed on 2026-06-01.

## Resolution

- Added `tests/contract/test_rtlmeter_compileargs_pass_through_smoke.py`.
- The test uses RTLMeter descriptor capture plus wrapper inspection to prove that `--compileArgs "--use-gpu"` reaches the wrapper-visible Verilator argv.
- The test does not run RTLMeter, run Verilator, mutate RTLMeter descriptors, build GPU artifacts, compare outputs, or claim speedup.
- A second smoke checks RTLMeter-style single-string `compileArgs` splitting for expanded sidecar options.
- When the RTLMeter source tree is absent, the helper returns `rtlmeter_source_unavailable` instead of leaking a local absolute path or pretending pass-through succeeded.
