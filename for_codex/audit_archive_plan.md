# Audit Archive Plan

Goal: remove gate-history bulk from the main user path while preserving reviewability.

Recommended final state:

- `records/scaling_gates/*.json` is exported as an audit archive or release artifact.
- The main branch keeps only a small audit index with archive name, source commit, record count, and checksum.
- `config/scaling_gates` compatibility references are removed or replaced with explicit archive references after tooling no longer depends on live files.
- User-facing docs describe supported commands, not gate-by-gate history.
- Contract tests assert public behavior and claim boundaries, not every historical gate transition.

Phased migration:

1. Keep `README.md` user-facing and move Codex-only memory into `for_codex/`.
2. Remove local generated outputs and logs from the checkout.
3. Add an audit index and archive checksum workflow.
4. Update tools/tests that read `records/scaling_gates` to either read the compact index or skip archive-only history.
5. Remove tracked `records/scaling_gates/*.json` from main once the index and archive are reproducible.

Do not claim completion until a clean checkout can run the documented user commands without the tracked gate-history files.
