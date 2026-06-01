# FC-015: Benchmark/Config JSON Contract

Status: done
Owner: Codex
Target file: `tests/contract/test_hybrid_benchmark_and_config_cli.py`

## Objective

Pin JSON debug marker fields and avoid brittle non-claim index checks.

## Tasks

- Check `json_flow_role`, `runtime_abi`, and `execution_authority`.
- Prefer membership checks over fixed list indexes for non-claims.
- Keep not-ready JSON behavior covered.

## Acceptance

- Tests catch ABI/execution overclaim regressions.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_and_config_cli -q
```

## Resolution

- Benchmark/config contract tests check `json_flow_role`, `runtime_abi`, and `execution_authority`.
- Not-ready JSON behavior remains covered.
- Non-claims are checked by membership rather than relying on brittle list positions.
