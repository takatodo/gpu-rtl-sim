# FC-004: Results Debug JSON Wording

Status: done
Owner: Codex
Target file: `docs/results.md`

## Objective

Separate reproduction/result commands from JSON inspection commands.

## Tasks

- Do not call JSON the shortest operator path.
- Preserve historical evidence and benchmark claims.
- Keep generated reports as evidence only, not source of truth.

## Acceptance

- `--operator-plan-json` is described as debug JSON.
- Result claims remain scoped and non-claims remain explicit.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_hybrid_benchmark_discovery_examples_cli -q
```

## Resolution

- `docs/results.md` keeps generated reports under evidence-only wording.
- The reader path points operators to terminal commands and dry-runs before generated summaries.
- Result claims remain scoped, with reports and artifacts explicitly not treated as source of truth.
