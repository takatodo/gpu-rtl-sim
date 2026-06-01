# FC-005: Status Goal Frame

Status: done
Owner: Codex
Target file: `docs/status.md`

## Objective

Keep the current gate pointer intact while ensuring the external goal frame matches the sidecar direction.

## Tasks

- Do not rewrite the long historical chain casually.
- Keep `Project Goal Frame` aligned with README.
- If editing current priority, update `config/selection.json` in the same reviewed task.

## Acceptance

- Current status remains consistent with selection state.
- JSON is debug/inspection, not runtime ABI.

## Validation

```sh
git diff --check
python3 src/tools/check_staged_large_files.py
```

## Resolution

- `docs/status.md` states the frontend-neutral sidecar goal and near-term Verilator UX target.
- It explicitly says JSON reports and operator plans are debug/review inspection, not JSON-first execution design.
- Current priority remains aligned with `config/selection.json`; no selection-state change was made.
