# Codex Project Memory

This directory holds Codex-facing instructions and internal project memory that should not dominate the external user path.

Moved or mirrored here:

| File | Purpose |
|---|---|
| `AGENTS.md` | Full Codex operating instructions previously kept at repository root. |
| `project_memory.md` | Archived previous long `README.md` content, including gate history and current-priority memory. Do not treat it as the current external goal. |
| `status.md` | Pointer to the authoritative current status files; do not mirror `docs/status.md` here. |
| `roadmap.md` | Pointer to the authoritative current roadmap files; do not mirror `docs/roadmap.md` here. |
| `results_memory.md` | Historical snapshot of `docs/results.md` with detailed evidence and non-claim history. |
| `audit_archive_plan.md` | Plan for moving gate-history records out of the main user path. |
| `issues.md` | Issue index for splitting cleanup and sidecar tasks across agents. |
| `issues/` | One-file-per-issue work queue. Agents should claim and edit individual issue files here. |
| `next_progress_workflow.md` | Operational protocol for turning "continue / check GitHub / use goal" requests into concrete forward progress. |

Root-level user documentation should stay concise. New Codex-only instructions, long-running project memory, and agent handoff notes belong here instead of in `README.md`.

## GitHub Issue Workflow

When `gh` is available, organize active work through GitHub Issues instead of
letting local FC files become the only task queue.

- Use `gh issue list` to inspect the current GitHub queue before creating new
  local-only issue files.
- Create or update one GitHub issue per actionable work item when work should be
  shared across agents or reviewed outside the local checkout.
- Link GitHub issues back to the matching `for_codex/issues/FC-*.md` file when
  an FC file exists; keep the FC file as design context, not as the only live
  tracker.
- Use `gh issue comment` for validation results, blockers, and handoff notes.
- Do not close a GitHub issue until the FC acceptance criteria are satisfied or
  the issue is explicitly superseded.
- Do not paste large generated logs into GitHub issues. Summarize the result and
  point to regenerable commands or generated `reports/` paths.
