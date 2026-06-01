# FC-007: Sidecar Command Path Split

Status: done
Owner: Codex
Target file: `src/tools/hybrid_benchmark_sidecar_commands.py`

## Objective

Maintain a hard split between terminal operator path and debug JSON path.

## Tasks

- Keep `shortest_operator_path()` terminal-only.
- Keep `debug_json_path()` for JSON inspection.
- Do not re-add `--operator-plan-json` to the normal operator path.

## Acceptance

- Discovery payloads expose both paths separately.
- JSON role is marked `debug_inspection`.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_benchmark_discovery_cli -q
```

## Resolution

- `shortest_operator_path()` remains terminal-oriented and does not include `--operator-plan-json`.
- `debug_json_path()` holds the JSON inspection path separately.
- Discovery payloads expose the terminal and debug JSON paths as distinct fields.
