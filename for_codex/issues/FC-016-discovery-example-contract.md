# FC-016: Discovery Example Contract

Status: done
Owner: Codex
Target file: `tests/contract/test_hybrid_benchmark_discovery_examples_cli.py`

## Objective

Keep help examples executable while checking JSON examples are debug-only.

## Tasks

- Preserve example command order unless intentionally changed with docs.
- Check JSON debug markers.
- Keep terminal examples non-JSON where expected.

## Acceptance

- Tests catch JSON role regressions.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_discovery_examples_cli -q
```

## Resolution

- Discovery example tests preserve the documented help-example command order.
- JSON examples are checked for debug-only markers.
- Terminal command examples are asserted to stay non-JSON where expected.
