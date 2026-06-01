# FC-031: RTLMeter Overlays Audit

Status: open
Owner: unassigned
Target file: `overlays/rtlmeter/`, `config/slice_launch_templates/`

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
python3 -m unittest tests.contract.test_filelist_public_pack_manifest_paths -q
```

Use a narrower test if this audit changes only documentation.
