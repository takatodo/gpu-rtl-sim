# FC-018: Codex README Index

Status: done
Owner: Codex
Target file: `for_codex/README.md`

## Objective

Keep the Codex memory index accurate without making it user-facing source of truth.

## Tasks

- Link coordination docs such as `issues.md`.
- Make authority boundaries clear: docs under `docs/` remain authoritative.
- Keep root README concise.

## Acceptance

- Other agents can find issue files quickly.

## Validation

```sh
python3 -m unittest tests.contract.test_tracked_tool_dependency_boundary -q
```

Result: passed on 2026-06-01.

## Resolution

- `for_codex/README.md` links `issues.md` as the issue index and `issues/` as the one-file-per-issue work queue.
- The README states that root-level user docs should stay concise and Codex-only instructions belong under `for_codex/`.
- `for_codex/issues.md` no longer has duplicated RTLMeter issue rows or duplicated Agent E ownership lines.
