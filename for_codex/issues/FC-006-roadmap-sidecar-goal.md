# FC-006: Roadmap Sidecar Goal

Status: done
Owner: Codex
Target file: `docs/roadmap.md`

## Objective

Keep roadmap aligned with the frontend-neutral sidecar goal.

## Tasks

- Preserve current priority unless changing `config/selection.json`.
- Keep Verilator as near-term frontend, CIRCT as planned frontend.
- Avoid making JSON a milestone for runtime ABI.

## Acceptance

- Roadmap does not conflict with README/status.
- CIRCT and Verilator roles are clear.

## Validation

```sh
python3 -m unittest tests.contract.test_hybrid_verilator_like_cli -q
```

## Resolution

- `docs/roadmap.md` starts with a GPU sidecar goal frame, Verilator as first frontend, and CIRCT as planned second frontend.
- JSON is framed as inspection output and explicitly not execution authority or a mandatory runtime ABI.
- The roadmap keeps current priority unchanged and aligned with README/status/selection state.
