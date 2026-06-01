# FC-003: Verilator Sidecar Option Scope

Status: done
Owner: Codex
Target file: `docs/verilator_sidecar_option.md`

## Objective

Keep this document Verilator-specific without implying the whole project is Verilator-only.

## Tasks

- State that Verilator is one frontend of the broader GPU sidecar experiment.
- Keep CIRCT as planned, not implemented.
- Keep JSON described as debug output, not runtime ABI.

## Acceptance

- Direct Verilator support remains a target, not a broad support claim.
- CIRCT is not overclaimed.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_hybrid_verilator_sidecar_shim_examples_cli -q
```

## Resolution

- `docs/verilator_sidecar_option.md` keeps Verilator as the near-term frontend while framing the sidecar as frontend-neutral.
- CIRCT remains planned rather than implemented.
- Sidecar JSON is described as debug/inspection metadata, not a runtime ABI.
