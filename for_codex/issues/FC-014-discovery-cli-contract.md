# FC-014: Discovery CLI Contract

Status: done
Owner: Codex
Target file: `tests/contract/test_hybrid_benchmark_discovery_cli.py`

## Objective

Pin discovery semantics for terminal path vs debug JSON path.

## Tasks

- Assert terminal path lives in `shortest_operator_path`.
- Assert JSON path lives in `debug_json_path`.
- Assert JSON examples carry debug role.

## Acceptance

- Tests fail if JSON returns to normal operator path.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_discovery_cli -q
```

## Resolution

- Discovery CLI tests assert `shortest_operator_path` as the terminal path.
- They assert `debug_json_path` separately and check debug-role metadata.
- The test suite now fails if JSON returns to the normal operator path.
