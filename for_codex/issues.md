# Agent Issue Index

This is the Codex-facing issue index. Each issue has its own file under `for_codex/issues/`, so agents can claim and edit one issue without touching a shared table.

Status values: `open`, `claimed`, `blocked`, `review`, `done`.

## Issues

| ID | Issue File | Target File |
|---|---|---|
| FC-001 | [README goal and user path](issues/FC-001-readme-goal.md) | `README.md` |
| FC-002 | [Tool surface JSON wording](issues/FC-002-tool-surface-json-wording.md) | `docs/tool_surface.md` |
| FC-003 | [Verilator sidecar option scope](issues/FC-003-verilator-sidecar-option-scope.md) | `docs/verilator_sidecar_option.md` |
| FC-004 | [Results debug JSON wording](issues/FC-004-results-debug-json-wording.md) | `docs/results.md` |
| FC-005 | [Status goal frame](issues/FC-005-status-goal-frame.md) | `docs/status.md` |
| FC-006 | [Roadmap sidecar goal](issues/FC-006-roadmap-sidecar-goal.md) | `docs/roadmap.md` |
| FC-007 | [Sidecar command path split](issues/FC-007-sidecar-command-path-split.md) | `src/tools/hybrid_benchmark_sidecar_commands.py` |
| FC-008 | [Discovery payload debug role](issues/FC-008-discovery-payload-debug-role.md) | `src/tools/hybrid_benchmark_catalog.py` |
| FC-009 | [Operator JSON debug markers](issues/FC-009-operator-json-debug-markers.md) | `src/tools/hybrid_benchmark_operator_core.py` |
| FC-010 | [Sidecar operator non-claims](issues/FC-010-sidecar-operator-non-claims.md) | `src/tools/hybrid_benchmark_sidecar_operator.py` |
| FC-011 | [Shim debug JSON role](issues/FC-011-shim-debug-json-role.md) | `src/tools/verilator_sidecar_shim.py` |
| FC-012 | [Benchmark CLI help JSON wording](issues/FC-012-benchmark-cli-help-json-wording.md) | `src/tools/run_hybrid_benchmark_args.py` |
| FC-013 | [Minimal suite debug naming](issues/FC-013-minimal-suite-debug-naming.md) | `src/tools/hybrid_benchmark_minimal_suite.py` |
| FC-014 | [Discovery CLI contract](issues/FC-014-discovery-cli-contract.md) | `tests/contract/test_hybrid_benchmark_discovery_cli.py` |
| FC-015 | [Benchmark/config JSON contract](issues/FC-015-benchmark-config-json-contract.md) | `tests/contract/test_hybrid_benchmark_and_config_cli.py` |
| FC-016 | [Discovery example contract](issues/FC-016-discovery-example-contract.md) | `tests/contract/test_hybrid_benchmark_discovery_examples_cli.py` |
| FC-017 | [Shim example contract](issues/FC-017-shim-example-contract.md) | `tests/contract/test_hybrid_verilator_sidecar_shim_examples_cli.py` |
| FC-018 | [Codex README index](issues/FC-018-for-codex-readme-index.md) | `for_codex/README.md` |
| FC-019 | [Project memory archive warning](issues/FC-019-project-memory-archive-warning.md) | `for_codex/project_memory.md` |
| FC-020 | [Results memory archive warning](issues/FC-020-results-memory-archive-warning.md) | `for_codex/results_memory.md` |
| FC-021 | [Status memory authority warning](issues/FC-021-status-memory-authority-warning.md) | `for_codex/status.md` |
| FC-022 | [Roadmap memory authority warning](issues/FC-022-roadmap-memory-authority-warning.md) | `for_codex/roadmap.md` |
| FC-023 | [Selection goal decision gate](issues/FC-023-selection-goal-decision-gate.md) | `config/selection.json` |
| FC-024 | [RTLMeter user path goal](issues/FC-024-rtlmeter-user-path-goal.md) | `README.md`, `docs/tool_surface.md` |
| FC-025 | [RTLMeter Verilator command capture](issues/FC-025-rtlmeter-verilator-command-capture.md) | `src/tools/rtlmeter_*` |
| FC-026 | [RTLMeter PATH wrapper prototype](issues/FC-026-rtlmeter-path-wrapper-prototype.md) | `src/tools/rtlmeter_*`, `src/tools/verilator_sidecar_shim.py` |
| FC-027 | [RTLMeter compileArgs pass-through smoke](issues/FC-027-rtlmeter-compileargs-pass-through-smoke.md) | `tests/contract/test_rtlmeter_*` |
| FC-028 | [RTLMeter sidecar contract mapping](issues/FC-028-rtlmeter-sidecar-contract-mapping.md) | `src/tools/rtlmeter_*` |
| FC-029 | [RTLMeter first seed selection](issues/FC-029-rtlmeter-first-seed-selection.md) | `config/selection.json`, `config/targets.json` |
| FC-030 | [RTLMeter CPU/GPU compare integration](issues/FC-030-rtlmeter-cpu-gpu-compare-integration.md) | `src/tools/rtlmeter_*`, `reports/` |
| FC-031 | [RTLMeter overlays audit](issues/FC-031-rtlmeter-overlays-audit.md) | `src/tools/rtlmeter_overlay_audit.py`, `tests/contract/test_rtlmeter_overlays_audit.py` |
| FC-032 | [RTLMeter public contract tests](issues/FC-032-rtlmeter-public-contract-tests.md) | `tests/contract/test_rtlmeter_*` |
| FC-033 | [RTLMeter docs and troubleshooting](issues/FC-033-rtlmeter-docs-troubleshooting.md) | `README.md`, `docs/verilator_sidecar_option.md` |
| FC-034 | [RTLMeter first seed execution integration](issues/FC-034-rtlmeter-first-seed-execution-integration.md) | `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*` |

## Parallel Split

- Agent A: FC-001 through FC-006, public docs only.
- Agent B: FC-007 through FC-013, CLI and JSON/debug implementation.
- Agent C: FC-014 through FC-017, contract tests.
- Agent D: FC-018 through FC-023, Codex memory and source-of-truth alignment.
- Agent E: FC-024 through FC-034, RTLMeter user-path exploration. Keep this separate from current sidecar cleanup unless a file is explicitly owned. FC-034 is the first executing issue; keep it isolated from non-executing FC-024 through FC-033.

## Guardrails

- Do not move canonical decisions into `for_codex/`.
- Do not promote JSON from debug output into runtime ABI.
- Do not claim CIRCT execution support yet.
- Do not claim general `verilator --use-gpu -f filelist.f --top-module top` support yet.
- Do not claim RTLMeter acceleration just because RTLMeter compiles.
- Keep RTLMeter's native user path intact; avoid requiring users to select repo-specific harness JSON manually.
- Do not update `config/selection.json` without a reviewed goal/priority change.
