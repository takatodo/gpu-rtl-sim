# FC-013: Minimal Suite Debug Naming

Status: done
Owner: Codex
Target file: `src/tools/hybrid_benchmark_minimal_suite.py`

## Objective

Keep the minimal suite aligned with debug JSON semantics.

## Tasks

- First benchmark validates debug JSON inspection, not runtime execution.
- Preserve high/low shape-class distinction.
- Keep filelist execution evidence separate.

## Acceptance

- Minimal suite output uses debug-oriented naming.
- Summary still passes existing contract tests.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_and_config_cli -q
```

## Resolution

- The minimal suite names the first check `operator_plan_debug_json`.
- Its purpose and validation wording make clear that the check verifies debug inspection, not runtime execution.
- Shape-fit and filelist evidence remain separate checks.
