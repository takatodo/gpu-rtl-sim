# FC-002: Tool Surface JSON Wording

Status: done
Owner: Codex
Target file: `docs/tool_surface.md`

## Objective

Ensure the operator-facing tool surface treats JSON as debug/inspection output, not the primary operator flow.

## Tasks

- Keep `shortest_operator_path` terminal-oriented.
- Keep `debug_json_path` optional and explicitly debug-only.
- Avoid wording that makes JSON the runtime contract.

## Acceptance

- Terminal operator flow and debug JSON flow are clearly separated.
- `coverage_output_equivalence` remains the correctness policy.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_discovery_cli tests.contract.test_hybrid_verilator_like_cli -q
```

## Resolution

- `docs/tool_surface.md` separates the terminal `shortest_operator_path` from the optional `debug_json_path`.
- JSON is described as debug/review inspection, not execution authority or the runtime ABI.
- The operator contract continues to name `coverage_output_equivalence` as the correctness policy.
