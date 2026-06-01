# FC-029: RTLMeter First Seed Selection

Status: open
Owner: unassigned
Target file: `config/selection.json`, `config/targets.json`

## Objective

Choose one RTLMeter seed case for the first honest GPU sidecar integration. Do not broaden to all RTLMeter designs until the first seed reaches CPU/GPU compare evidence.

## Tasks

- Compare candidates such as `Example`, one OpenTitan primitive, one TL-UL target, or one NVDLA CMAC target.
- Prefer the seed that best tests the RTLMeter-preserving UX with the least custom overlay.
- Record non-goals: no broad RTLMeter acceleration claim, no arbitrary descriptor support, no automatic allocation.
- Only edit `config/selection.json` after a reviewed priority change.

## Acceptance

- Exactly one first RTLMeter seed is selected or a clear decision gate is recorded.
- Existing active seed policy is not violated.
- Selection aligns with README, docs/status, and docs/roadmap if source-of-truth files are changed.

## Validation

```sh
python3 -m unittest tests.contract.test_resident_runtime_contract -q
```

Run this only after confirming it will not mutate selection state in the current worktree.
