# FC-032: RTLMeter Public Contract Tests

Status: done
Owner: Codex
Target file: `tests/contract/test_rtlmeter_*`

## Objective

Create the minimal public contract tests for RTLMeter sidecar support so the repo cannot claim an easy RTLMeter path without preserving RTLMeter's normal UX.

## Tasks

- Test command capture for one RTLMeter case.
- Test `--compileArgs "--use-gpu"` or wrapper pass-through.
- Test fail-closed behavior for unsupported RTLMeter cases.
- Test that debug JSON is optional and not required for execution authority.

## Acceptance

- Tests are focused and do not run a full benchmark by default.
- Tests fail if the implementation bypasses RTLMeter and requires manual repo template selection.
- Tests have a README/docs mention when the public workflow is added.

## Validation

```sh
python3 -m unittest tests.contract.test_rtlmeter_public_contract -q
```

Result: passed on 2026-06-01.

## Resolution

- Added `tests/contract/test_rtlmeter_public_contract.py`.
- The aggregate public contract verifies RTLMeter user-path preservation through command capture, `--compileArgs "--use-gpu"` pass-through, and sidecar contract mapping.
- The contract fails closed for malformed GPU-intent wrapper requests.
- The contract verifies RTLMeter debug JSON metadata is optional inspection output with `runtime_abi: false` and `execution_authority: false`.
