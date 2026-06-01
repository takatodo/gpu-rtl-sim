# FC-010: Sidecar Operator Non-Claims

Status: done
Owner: Codex
Target file: `src/tools/hybrid_benchmark_sidecar_operator.py`

## Objective

Keep serialized sidecar metadata from being read as runtime authority.

## Tasks

- Preserve non-claims on handoff contract and operator plan.
- Preserve debug markers in operator plan JSON.
- Keep terminal formatting unchanged unless tests are updated.

## Acceptance

- Handoff contract remains metadata only.
- JSON serialization is explicitly debug output.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_and_config_cli -q
```

## Resolution

- `sidecar_handoff_contract()` keeps contract data as metadata and marks JSON serialization as debug output.
- `sidecar_operator_plan()` marks JSON as debug-only and not command execution.
- Terminal operator-plan formatting remains script-friendly and non-JSON.
