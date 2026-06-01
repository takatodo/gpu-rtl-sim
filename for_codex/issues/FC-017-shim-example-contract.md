# FC-017: Shim Example Contract

Status: done
Owner: Codex
Target file: `tests/contract/test_hybrid_verilator_sidecar_shim_examples_cli.py`

## Objective

Assert shim JSON reports are debug-only while preserving terminal command-only behavior.

## Tasks

- Check debug markers on ready JSON.
- Check debug markers on not-ready JSON.
- Ensure terminal print modes do not emit JSON unless not-ready.

## Acceptance

- Tests catch shim JSON ABI/execution overclaims.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_verilator_sidecar_shim_examples_cli -q
```

## Resolution

- Shim example tests check ready JSON debug markers.
- Not-ready JSON keeps structured status with non-execution semantics.
- Terminal print modes are asserted not to emit JSON unless reporting not-ready status.
