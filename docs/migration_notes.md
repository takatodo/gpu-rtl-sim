# Migration Notes

## Gap from a minimal verification setup

What “simple” often means here: one small RTL template, Verilator lint or a short CPU-only sim, optional unit tests, no GPU, no long evidence chain.

How this repository diverges:

- **Toolchain and runtime**: Hybrid correctness checks assume **Verilator builds**, **generic host probes**, **CUDA** / GPU hybrid runs, and **`artifacts/`** object dirs—not a single `verilator --lint-only` smoke.
- **Active surface vs one seed**: `AGENTS.md` still speaks one active seed policy for the original extraction goal, but **`config/selection.json`** now tracks a **large TL-UL + OpenTitan primitive inventory** (tens to hundreds of targets) alongside LLM-serving-like ITA paths; mental load and checkout cost are not “one DUT”.
- **Gates and history**: **600+** JSON records under `records/scaling_gates/` power compatibility and audits; “simple” verification rarely needs a parallel legal ledger.
- **Correctness semantics**: Acceptance is **`coverage_output_equivalence`** on declared output words, not bitwise or raw Verilator state—extra reading for anyone expecting dump equality.
- **Reproduction paths**: Public smoke is mostly **`--dry-run`** (`docs/results.md`), but real evidence requires **multi-step** flows (`run_hybrid_template.py`, `run_results_reproduction.py` with many flags, resident/persistent modes, repeat-median batches).
- **Contract tests**: **`tests/contract/test_full_ita_mha_larger_paged_kv_next*.py`** shards encode the packaging gate chain; **`test_resident_runtime_contract.py`** pins selection and surface rules—far beyond a tiny smoke test file.
- **Operator and data dependencies**: **Submodules** (`third_party/ITA`, etc.), optional **ImageNet / HF cache** for MobileViT paths, and **pre-commit** guards (large files, script/test growth) add environment and workflow assumptions.
- **Current pointer**: Canonical **`current_priority`** / **`current_priority_source_artifact`** advance through **define → dry-run → measurement → review** style gates; that is process overhead, not “run one command and done.”

What stays comparatively simple: **dry-run-only** CLI checks, **`run_hybrid_benchmark.py --dry-run`** for supported targets, and reading **`docs/results.md`** + **`README.md`** for the smallest public surface.

## `selection.json` split (schema_version 3)

- **`config/selection.json`**: compact file with the live pointer (`current_priority`, `current_priority_source_artifact`), `active_scope` metadata (not the target-name list), `verification`, `repository_cleanup`, and `selection_extensions` (path). Target names are injected at load time from `config/targets.json`.
- **`config/selection_extensions.json`**: `completed_goal_evidence` and `mobile_vit_cpu_kick_imagenet_accuracy` (historical / bulky).
- **`config/selection_verification_commands.json`**: long `verification.commands` checklist for the TL-UL `tlul_fifo_async` promotion path; referenced from `selection.json` as `verification.commands_artifact`. Injected into a merged view by `load_selection`.
- **Merged read**: use `src/tools/selection_state.py` (`load_selection`) or contract-test helper `read_selection()`; do not assume a flat single-file dump when writing new tooling.

## 整理の順序（推奨）

優先度の目安: **P0** 最優先（読み方の一貫性）、**P1** 重複排除、**P2** 長大フィールドの外部化、**P3** ローカル生成物の掃除。

| 優先度 | 内容 | 状態 |
| --- | --- | --- |
| P0 | `selection` は `load_selection` / `read_selection()` でマージ読み。証跡マップを生 `selection.json` に置かない。 | 完了 |
| P1 | **`active_scope.targets` は `config/targets.json` からのみ注入**（`selection.json` には永続化しない）。 | 完了 |
| P2 | `verification.commands` の外部化（`config/selection_verification_commands.json`）、README / `jq` / 本ドキュメントの同時更新。 | 完了 |
| P3 | `artifacts/mobile_vit/venv` や未使用 `*_obj_dir` の整理（再現手順は README **Artifact Policy → Local disk hygiene** と MobileViT 節）。 | 完了 |
| P4 | 日常操作: 既存 CLI をそのまま呼ぶ薄い `Makefile` のみ（統合 Python オペレータは置かない）。 | 完了 |
| （続き） | `active_scope` の数値・claim と `targets.json` の整合をさらに機械化する場合は P1 の延長で検討。 | 任意 |

作業を並列に広げず、上から順に片付けると依存とテストの整合が取りやすい。

## weakest_point

The exploration repository contains valuable knowledge, but most of its generated artifacts and historical decision logs should not be copied.

## carry

```text
runtime_core:
  - src/hybrid/run_vl_hybrid.c
  - src/hybrid/host_abi.h
  - src/hybrid/tlul_slice_host_probe.cpp
  - src/hybrid/tlul_fifo_sync_cpu_replay_host_probe.cpp
  - src/passes/VlGpuPasses.cpp
  - src/passes/vlgpugen.cpp

first_seed:
  - tlul_fifo_sync source/config only
```

## do_not_carry

```text
- work/
- output/
- obj_dir/
- __pycache__/
- broad MobileViT side branches
- historical campaign decision artifact history
```
