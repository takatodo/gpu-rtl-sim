# Candidate Contract Tests

This directory holds exploratory NN, LLM, and MobileViT contract tests that are
not part of the active contract suite yet.

Active contract tests live under `tests/contract/` and are expected to pass with:

```bash
python3 -m unittest discover -s tests/contract -q
```

Before moving a candidate test into `tests/contract/`, make its required tools,
templates, overlays, third-party dependencies, and documentation part of the same
review boundary. Generated reports remain evidence only and must not become the
source of truth.
