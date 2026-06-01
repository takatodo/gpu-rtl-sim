# FC-030: RTLMeter CPU/GPU Compare Integration

Status: open
Owner: unassigned
Target file: `src/tools/rtlmeter_*`, `reports/`

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

Future validation command after the compare-policy helper/test is staged:

```sh
python3 -m unittest tests.contract.test_rtlmeter_cpu_gpu_compare_integration -q
```
