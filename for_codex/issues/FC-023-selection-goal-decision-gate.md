# FC-023: Selection Goal Decision Gate

Status: done
Owner: Codex
Target file: `config/selection.json`

## Objective

Decide whether `top_level_goal` should eventually change from `modern_llm_serving_rtl_hybrid_conditions` to a sidecar-focused goal.

## Tasks

- Do not edit `config/selection.json` casually.
- Define a reviewed gate before changing the goal string.
- Update `docs/status.md`, `docs/roadmap.md`, and README in the same reviewed task if the goal changes.

## Acceptance

- Current source-of-truth files stay consistent.
- No generated evidence becomes canonical.

## Validation

```sh
python3 -m unittest tests.contract.test_resident_runtime_contract -q
```

Run this only after confirming it will not mutate selection state in the current worktree.

Result: not run; this issue deliberately did not edit `config/selection.json`.

## Resolution

- Decision: do not change `config/selection.json.top_level_goal` in this cleanup pass.
- A sidecar-focused goal string may be introduced only through a reviewed gate that updates `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, and README together.
- Current source-of-truth files are not rewritten from `for_codex/` memory.
- Generated evidence remains non-canonical.
