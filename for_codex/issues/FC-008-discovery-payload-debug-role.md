# FC-008: Discovery Payload Debug Role

Status: done
Owner: Codex
Target file: `src/tools/hybrid_benchmark_catalog.py`

## Objective

Keep discovery payloads explicit about JSON being debug/inspection output.

## Tasks

- Preserve `debug_json_path`.
- Preserve `operator_plan_json_role: debug_inspection`.
- Keep non-claims rejecting runtime ABI interpretation.

## Acceptance

- Ready sidecar targets expose terminal and debug JSON commands distinctly.
- Not-ready targets remain fail-closed.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_discovery_cli tests.contract.test_hybrid_verilator_like_cli -q
```

## Resolution

- Sidecar discovery payloads include `debug_json_path` and `operator_plan_json_role: debug_inspection`.
- Ready targets expose terminal and debug JSON commands distinctly.
- Not-ready targets remain fail-closed and carry non-claims against runtime ABI interpretation.
