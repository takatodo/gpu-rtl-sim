# FC-012: Benchmark CLI Help JSON Wording

Status: done
Owner: Codex
Target file: `src/tools/run_hybrid_benchmark_args.py`

## Objective

Make CLI help clear that `--operator-plan-json` is debug/inspection output.

## Tasks

- Keep examples executable.
- Keep terminal preview examples before JSON inspection examples.
- Do not describe JSON as the runtime ABI.

## Acceptance

- Help text says `--operator-plan-json` is debug/inspection.
- Existing example tests still pass.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_discovery_examples_cli -q
```

## Resolution

- `run_hybrid_benchmark.py --help` lists terminal preview examples before debug JSON inspection.
- The help text says `--operator-plan-json` is for debug/inspection and not the runtime ABI.
- Help examples remain executable under the discovery example contract tests.
