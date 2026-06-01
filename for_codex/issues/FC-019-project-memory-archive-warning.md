# FC-019: Project Memory Archive Warning

Status: done
Owner: Codex
Target file: `for_codex/project_memory.md`

## Objective

Prevent archived project memory from being mistaken for current external goal.

## Tasks

- Keep archive warning near the top.
- Do not update this file as canonical state.
- Prefer updating `README.md`, `docs/status.md`, or `docs/roadmap.md` for current state.

## Acceptance

- The file clearly says it is an archive.

## Validation

Manual review.

Result: passed on 2026-06-01.

## Resolution

- `for_codex/project_memory.md` starts with an archived pre-cleanup README warning.
- The warning points current external goal authority back to `README.md`, `docs/status.md`, and `docs/roadmap.md`.
- No canonical project state was moved into this file.
