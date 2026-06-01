# FC-009: Operator JSON Debug Markers

Status: done
Owner: Codex
Target file: `src/tools/hybrid_benchmark_operator_core.py`

## Objective

Ensure wrapper JSON reports cannot be mistaken for runtime ABI or execution authority.

## Tasks

- Add or preserve `json_flow_role: debug_inspection`.
- Add or preserve `runtime_abi: false`.
- Add or preserve `execution_authority: false`.
- Apply markers to ready and not-ready paths.

## Acceptance

- JSON output remains backward-compatible where required but semantically debug-only.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_and_config_cli -q
```

## Resolution

- Wrapper operator JSON includes `json_flow_role: debug_inspection`, `runtime_abi: false`, and `execution_authority: false`.
- Both ready and not-ready operator-plan JSON paths carry debug-only non-claims.
- Existing config/benchmark contract tests cover the markers.
