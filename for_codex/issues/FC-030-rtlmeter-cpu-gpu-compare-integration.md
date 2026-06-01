# FC-030: RTLMeter CPU/GPU Compare Integration

Status: done
Owner: Codex
Target file: `src/tools/rtlmeter_cpu_gpu_compare_policy.py`, `tests/contract/test_rtlmeter_cpu_gpu_compare_policy.py`

## Objective

Define how RTLMeter CPU execution and GPU sidecar execution produce a comparable result while preserving RTLMeter's own metrics and post-hook behavior.

## Tasks

- Identify the first seed's observable output for CPU/GPU comparison.
- Keep RTLMeter's execute metrics intact when GPU sidecar evidence is added.
- Write generated compare reports under `reports/` only.
- Do not make reports the source of truth.

## Acceptance

- CPU/GPU comparison has an explicit policy for the first seed.
- RTLMeter timing and sidecar timing are not conflated.
- Generated reports can be regenerated from documented commands.

## Validation

```sh
python3 -m unittest tests.contract.test_rtlmeter_cpu_gpu_compare_policy -q
```

Result: passed on 2026-06-01.

## Resolution

- Added `src/tools/rtlmeter_cpu_gpu_compare_policy.py` as policy-only metadata, not execution integration.
- The helper is parameterized by RTLMeter seed and compile args, defaulting to the FC-029 seed.
- The policy preserves RTLMeter as CPU execution owner and sidecar as GPU candidate owner.
- Generated report paths are constrained under `reports/` and are not source of truth.
- The regeneration command is planned documentation only; no RTLMeter run, sidecar run, compare report, timing, or speedup is claimed.
