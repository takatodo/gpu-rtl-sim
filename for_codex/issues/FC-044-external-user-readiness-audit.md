# FC-044: External User Readiness Audit

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/11
Target file: `README.md`, `docs/`, `Makefile`, `tests/contract/`, `for_codex/issues.md`

## Objective

Make the repository honest and usable for someone outside the current agent
loop. The audit should verify that the documented commands, issue dependencies,
generated-output policy, and non-claims match the actual implementation after
the current cleanup and wrapper work.

This is a readiness audit, not a feature implementation. It should delete or
demote misleading surface area if the files imply unsupported capabilities.

## Tasks

- Run the documented quickstart/smoke commands that do not require special GPU
  access, and record any blocked GPU-runtime cases as blockers rather than
  success.
- Check that `README.md`, `docs/status.md`, `docs/roadmap.md`, and
  `config/selection.json` agree on the current pointer and non-claims.
- Check that GitHub issues and `for_codex/issues.md` agree on open dependencies,
  especially FC-034 -> FC-037 -> FC-040 and FC-042/FC-043.
- Identify files that are obsolete, generated, misleading, or agent-only; move
  agent-only notes under `for_codex/` and do not keep generated outputs as
  source of truth.
- Verify that public commands do not require users to manually select
  repo-specific template JSON unless the docs explicitly call that a low-level
  developer path.
- Add or update a concise readiness checklist in docs only if it prevents future
  drift; avoid adding a new operational note as a second source of truth.

## Acceptance

- A fresh external reader can tell what is supported, what is preview-only, and
  what is not claimed.
- All documented non-GPU-required commands either pass or have an accurate
  documented blocker.
- Issue dependencies are visible in both GitHub and `for_codex/issues.md`.
- No generated output is treated as canonical state.
- Obsolete or misleading files are removed, moved, or explicitly marked as
  archival/agent-only.

## Validation

```sh
git diff --check
make simple
make surface
python3 -m unittest discover -s tests/contract -q
```

If `make` targets or tests cannot run in the local environment, record the exact
blocked prerequisite and do not close the issue as passed.

## Non-Goals

- No new sidecar execution feature.
- No timing or speedup claim.
- No broad `verilator --use-gpu` support claim.
- No CIRCT execution claim.
- No new source-of-truth file outside `config/selection.json`, `docs/status.md`,
  `docs/roadmap.md`, and `README.md`.
