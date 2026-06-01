# FC-011: Shim Debug JSON Role

Status: done
Owner: Codex
Target file: `src/tools/verilator_sidecar_shim.py`

## Objective

Keep shim JSON as debug output while preserving command-only terminal modes.

## Tasks

- Preserve `schema_role: verilator_sidecar_debug_plan`.
- Preserve `json_flow_role: debug_inspection`.
- Preserve `runtime_abi: false` and `execution_authority: false`.
- Do not make any shim mode execute benchmark commands.

## Acceptance

- Ready JSON and not-ready JSON are debug-only.
- Terminal print modes remain concise and script-friendly.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_verilator_sidecar_shim_examples_cli -q
```

## Resolution

- Shim ready JSON preserves `schema_role: verilator_sidecar_debug_plan`, `json_flow_role: debug_inspection`, `runtime_abi: false`, and `execution_authority: false`.
- Shim error/not-ready JSON is also debug-only and non-executing.
- Terminal print modes remain concise command/estimate views instead of normal JSON output.
