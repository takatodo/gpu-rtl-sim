# FC-031: RTLMeter Overlays Audit

Status: done
Owner: Codex
Target file: `src/tools/rtlmeter_overlay_audit.py`, `tests/contract/test_rtlmeter_overlays_audit.py`

## Objective

Audit the existing RTLMeter overlays and templates against the user-path goal. Keep overlays that help the first RTLMeter-preserving seed; archive or de-emphasize overlays that only support repo-specific harness experiments.

## Tasks

- Classify overlays as first-seed required, useful later, generated/bulk, or delete/archive candidate.
- Flag `overlays/generated` if generated files are being tracked as source of truth.
- Identify templates that force users into repo-specific JSON selection instead of RTLMeter commands.
- Do not delete files in this issue unless a cleanup branch and recovery path are explicit.

## Acceptance

- The audit names the minimal overlay set needed for the first RTLMeter user path.
- Broad overlay inventory is not presented as current public support.
- Cleanup recommendations are concrete and file-scoped.

## Validation

```sh
python3 -m unittest tests.contract.test_rtlmeter_overlays_audit -q
```

## Resolution

- Added a dynamic audit helper that reads tracked paths from `git ls-files`, with injectable tracked paths used by contract tests.
- Reused `rtlmeter_seed_selection.SELECTED_SEED` and recorded that this audit does not change canonical project state.
- Classified tracked `overlays/rtlmeter/`, tracked `overlays/generated/`, and legacy `config/slice_launch_templates/{prim,tlul,nvdla}_*.json` paths by count plus bounded examples.
- Kept deletion/archive candidates empty; this issue records audit metadata only and makes no broad RTLMeter acceleration support claim.
