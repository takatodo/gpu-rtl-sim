# GPU Toggle Coverage Minimal

Minimal extraction of the GPU-toggle coverage hybrid-runtime project.

The repository keeps the active implementation surface small while preserving a reproducible path from configuration to build, run, comparison, and status reporting. Generated outputs are not source of truth.

## Goal

Large goal:

`modern_llm_serving_rtl_hybrid_conditions`

Current priority:

`run_resident_execution_optimization_followup_measurement_gate`

Current gate (authorizing artifact):

`config/scaling_gates/run_resident_execution_optimization_followup_measurement_dry_run_gate.json`

The larger project question is: identify the conditions where a hybrid CPU/GPU RTL coverage runtime can run modern LLM-serving-like RTL workloads correctly and quickly.

External-facing result synthesis:

- `docs/results.md`
- `python3 src/tools/run_results_reproduction.py --dry-run`
- `python3 src/tools/run_results_reproduction.py --repeat-median 3 --dry-run`
- `python3 src/tools/run_results_reproduction.py --paged-kv-continuation-repeat-median 3 --dry-run`
- `python3 src/tools/run_results_reproduction.py --paged-kv-next-shapes-repeat-median 3 --dry-run`
- `python3 src/tools/run_results_reproduction.py --resident-batch-sweep 1,8,16,32 --resident-batch-sweep-repeat 3 --dry-run`
- `python3 src/tools/run_results_reproduction.py --resident-state-reuse 16x64 --resident-state-reuse-phases 4 --dry-run`
- `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --dry-run`
- `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi-shape-phase-sweep --dry-run`
- `python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run`
- `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/nvdla_cmac_a2cacc.json --shape 1x1 --dry-run`
- `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/prim_count.json --shape 1x1 --dry-run`
- `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/prim_secded_inv_39_32_enc.json --shape 1x1 --dry-run`
- `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/tlul_fifo_sync.json --shape 1x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 1x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode resident-state-reuse --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode persistent-resident-state-abi --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json`
- `python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --summary-from-existing --summary-out reports/hybrid_benchmark_mobile_vit_template_limit128.json`

How to read the public benchmark pack:

- Start at `docs/results.md`.
- Use `docs/tool_surface.md` to distinguish routine CLI entrypoints from helper modules.
- Treat `config/selection.json` (compact pointer and core fields), `config/selection_extensions.json` (linked `completed_goal_evidence` and MobileViT accuracy block), and `config/selection_verification_commands.json` (linked scripted verification checklist), together with `docs/status.md`, `docs/roadmap.md`, and this README, as the current source of truth. Merge programmatically via `src/tools/selection_state.py` (`load_selection`) when tooling needs the historical maps and full verification command list.
- Treat `reports/` and `artifacts/` as generated evidence/output only.
- Review `reports/hybrid_benchmark_*.json` for the compact wrapper summary schema: target, shape or limit, execution mode, commands, expected reports, and collected evidence.
- Prefer `--dry-run` first when reproducing measurements.
- External pack boundary: a review bundle may include generated `reports/*.json` as evidence, but a clean checkout can regenerate them from the documented commands.

## Commit Guard

Enable the versioned pre-commit hook once per checkout:

```sh
git config core.hooksPath .githooks
```

The hook runs `python3 src/tools/check_staged_large_files.py`, rejects staged files larger than `5 MiB`, rejects commits with more than `100` staged non-submodule file changes including deletions and type changes, rejects guarded script deltas above `250` added lines per script, rejects guarded scripts above `1800` total lines per script, rejects more than `3` new guarded scripts in one commit, and rejects growing `tests/contract/test_*.py` files above `1200` total lines or `250` added lines. Existing oversized contract tests may still shrink. Guarded scripts are Python tools under `src/tools/` and shell hooks under `.githooks/`. Override local thresholds with `GPU_TOGGLE_MAX_COMMIT_FILE_BYTES=<bytes>`, `GPU_TOGGLE_MAX_COMMIT_FILE_COUNT=<count>`, `GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES=<lines>`, `GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES=<lines>`, `GPU_TOGGLE_MAX_NEW_SCRIPT_FILES=<count>`, `GPU_TOGGLE_MAX_CONTRACT_TEST_ADDED_LINES=<lines>`, or `GPU_TOGGLE_MAX_CONTRACT_TEST_TOTAL_LINES=<lines>` only when a reviewed change genuinely needs a different limit.

Commit cadence: keep commits small enough to review by one gate or one workflow boundary. Prefer committing source/doc/test changes separately from generated `reports/` refreshes; keep `artifacts/` as local generated output and do not commit bulky generated outputs as source of truth.
- Public pack manifest: `docs/results.md` lists the minimum source-of-truth files, `records/scaling_gates` gate/audit records, tools, templates, contract tests, and optional generated evidence snapshots to include for review.
- Public reproduction smoke: `docs/results.md` lists the first dry-run commands to run before attempting full measurements.
- Public release checklist: `docs/results.md` lists the final source-of-truth, path hygiene, smoke, evidence, non-claim, and contract-test checks before handoff.
- Externalization readiness audit: `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json` records the minimum review surfaces, smoke commands, release checks, and evidence policy for externalization.
- Public archive dry-run: `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run` prints the include/exclude plan without creating an archive.

## Source Of Truth

Canonical project state lives in:

- `config/README.md`
- `config/selection.json`
- `config/targets.json`
- `docs/status.md`
- `docs/roadmap.md`
- `README.md`

`docs/results.md` is the external-facing result pack and reader guide. It summarizes current evidence, reproduction commands, and non-claims, but canonical project-state decisions stay in the files above.

Historical gate details live under `records/scaling_gates/`, with `config/scaling_gates` kept as a compatibility link. Generated outputs are reproducible under `reports/` and `artifacts/`; they may be present in a local working tree as evidence, but they are never source of truth.

The config minimization audit is `records/scaling_gates/config_minimal_surface_completion_audit.json`.

## Operator shortcuts

`Makefile` targets are thin wrappers that call **existing** tools directly (no shared “do everything” Python script):

```bash
make simple          # status + validate + smoke (まずはこれ)
make status          # jq on config/selection.json (current_priority)
make validate        # jq empty on canonical config/*.json
make test            # python3 -m unittest discover -s tests/contract
make check           # validate, then test
make smoke           # python3 src/tools/run_results_reproduction.py --dry-run
make mobile-vit-venv # venv + pip install -r requirements/mobile_vit.txt
make clean-mobile-vit-venv
make hooks           # print git hooksPath setup command
```

Equivalent direct commands (same behavior without `make`):

```bash
jq empty config/selection.json config/selection_extensions.json \
  config/selection_verification_commands.json config/targets.json
python3 -m unittest discover -s tests/contract -q
python3 src/tools/run_results_reproduction.py --dry-run
```

Merged selection state for tooling: `src/tools/selection_state.py` (`load_selection`).

Upstream RTL source is provided through submodules. Initialize the active upstream source before running target templates:

```bash
git submodule update --init third_party/rtlmeter
```

## Active Scope

**Target names** live in `config/targets.json` (`active_targets`). **`load_selection()`** injects `active_scope.targets` from that registry when you need the combined machine-readable view.

The compact `config/selection.json` still records scope metadata:

- `active_target_count`
- `active_tlul_target_count`
- `active_primitive_target_count`
- `latest_primitive`
- `coverage_output_equivalence_gate`
- `coverage_output_equivalence_report`
- strict output word and byte counts

Candidate targets are empty until the next gate is selected.

## What This Repo Can Do

- Build Verilator-derived CPU and hybrid host/GPU probes.
- Compare CPU vs hybrid by coverage-output equivalence rather than raw internal state.
- Preserve host-only Verilator internal handling before launch.
- Run slice launch templates such as TL-UL, OpenTitan primitive, NVDLA, ITA, MHA, paged KV-cache, and paged-attention KV-score seeds.
- Generate Verilator-like hybrid config from a target/top/overlay description.

## Minimal CPU/GPU Repro Flow

Existing template runner:

```bash
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 32x1
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x32
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1 --dry-run --estimate-efficiency
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1 --dry-run --estimate-efficiency-json
```

`--estimate-efficiency` prints a short human-readable `high` / `medium` / `low` estimate. `--estimate-efficiency-json` keeps the same data machine-readable for tests and wrappers. Existing CPU and hybrid reports can add an observed `cpu_to_hybrid_wall_speedup`, but this remains scoped evidence for that target/shape and is not a broad speedup claim.

Verilator-like benchmark runner:

```bash
python3 src/tools/run_hybrid_benchmark.py --list-targets
python3 src/tools/run_hybrid_benchmark.py --help
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --estimate-efficiency
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --estimate-efficiency-json
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run --sidecar-gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-verilator-command
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-efficiency-estimate
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-operator-plan
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --operator-plan-json
python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1
python3 src/tools/run_hybrid_benchmark.py pulp_paged_kv_cache_large --shape 256x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode resident-state-reuse --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 1x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_paged_kv_cache_large --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_paged_kv_cache_large_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode resident-state-reuse --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode persistent-resident-state-abi --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --summary-from-existing --summary-out reports/hybrid_benchmark_mobile_vit_template_limit128.json
```

Use `--list-targets` to inspect supported target names, aliases, required `--shape` or `--limit` arguments, supported modes, and the current `sidecar_gpu` option-shim discovery status before running a measurement.

Use `--help` for the shortest Verilator-like entrypoint examples: target discovery, terminal operator plan, and JSON operator plan.

The `--list-targets` sidecar discovery block also reports ready template stage names, not-ready resident fallback stage names, and dataset-backed stage names. This keeps the first discovery command tied to the shim commands that can inspect or emit stage commands.

`run_hybrid_benchmark.py --estimate-efficiency` is the operator-facing form: it prints the target, shape or limit, speedup class, reason, next action, and non-claims after the command plan. `--estimate-efficiency-json` keeps the same estimate machine-readable. `--preflight` already emits JSON and cannot be combined with the extra efficiency output flags.

`--sidecar-gpu` is a short Verilator-like alias for the existing hybrid sidecar GPU benchmark flow. It does not change the CPU/GPU comparison policy; it adds the human-readable efficiency estimate so the operator can see the command plan, speedup class, and equivalence non-claims in one terminal view.

The wrapper also accepts `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` and compact `--sim-accel-shape <NxS>` as tested compatibility spellings for the planned Verilator option. These names map to the same internal `NxS` shape and reject mixed shape spellings.

`--print-verilator-command` on the wrapper prints only the synthesized future Verilator command without executing commands. `--print-efficiency-estimate` prints only the matching human-readable estimate. `--print-operator-plan` prints that command plus the same efficiency estimate. These are the shortest terminal paths from target discovery to the direct-option preview, while the JSON shim remains the structured automation boundary.

`--operator-plan-json` prints the same wrapper operator plan as machine-readable JSON without executing commands. It exits `0` with a `planned` report when ready, and exits `2` with a `not_ready_for_verilator_option_shim` JSON report when the target cannot synthesize the direct-option preview. The ready report includes `handoff_contract` metadata for state authority, init/reference/candidate dumps, generated compare report path, and `coverage_output_equivalence`. Its `schema_role` is `target_first_operator_plan`; use `verilator_sidecar_shim.py` when automation needs the fuller readiness or stage-detail boundary.

Readiness status strings are shared across discovery and JSON entrypoints: `ready_for_template_shape`, `ready_for_verilator_option_shim`, and `not_ready_for_verilator_option_shim`.

`--preflight` includes a `sidecar_stage_plan` for template targets. It names the direct-Verilator migration stages, including `gpu_artifact_build`, `hybrid_sidecar_run`, and the final `coverage_output_compare` using `coverage_output_equivalence`. Each stage also carries structured `details` so `mdir`, `top_module`, source files, state files, shape, and compare policy are available without scraping command strings.

`sidecar_stage_plan.verilator_option_readiness` reports whether the wrapper has the minimum structured inputs for a future Verilator option shim. `ready_for_verilator_option_shim` is a planning/readiness claim only; it is not execution evidence and does not mean Verilator itself already implements `--sim-accel`.

Wrapper `--preflight` and summary JSON also include `verilator_option_preview`. Ready previews include the synthesized direct-option command and handoff contract; not-ready previews keep the missing input list without pretending Verilator already implements `--sim-accel`.

When `--dry-run` is used with `--sidecar-gpu` or explicit `--sim-accel sidecar-gpu`, the wrapper prints a compact `# verilator_option_preview` block before the existing wrapper command plan. This keeps the future Verilator command visible while leaving the current dry-run and `coverage_output_equivalence` flow unchanged.

Dataset-backed targets stay not-ready for the direct Verilator option until they have a direct RTL sidecar handoff. `mobile_vit --limit 128` still exposes non-executing `host_preprocess` and `rtl_sidecar_proxy_eval` stages so automation can inspect the host preprocessing boundary and the current RTL proxy eval command without treating either as shim readiness.

Resident modes also stay not-ready for the direct Verilator option. Their not-ready plan exposes a `resident_state_reuse_workflow` or `persistent_resident_state_abi_workflow` fallback command so low-efficiency `1xN` shapes can move to the supported resident workflow without implying Verilator owns that flow yet.

`src/tools/verilator_sidecar_shim.py` emits the future option handoff as JSON without executing commands. It exits `0` when ready for the shim, `2` when the target or mode is not ready for the shim, and `1` for input/planning errors with JSON on stderr.

To inspect the exact command for one planned stage without running it:

```bash
python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --stage hybrid_sidecar_run --emit-command
```

The emitted command is still planning output; it is not execution evidence.

To preview the future direct Verilator command shape without running it:

```bash
python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --emit-verilator-command
```

This synthesized command is a handoff preview for automation. It does not mean Verilator itself already implements `--sim-accel`.

For a one-line human-readable preview:

```bash
python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-verilator-command
```

For the matching human-readable efficiency estimate:

```bash
python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-efficiency-estimate
```

To see both the command preview and efficiency estimate in one terminal view:

```bash
python3 src/tools/verilator_sidecar_shim.py --target paged_attention_kv_score --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-operator-plan
```

The target end state is a direct Verilator option, documented in `docs/verilator_sidecar_option.md`. The wrapper spelling above is the current compatibility surface while that option is not implemented in Verilator itself.

`--summary-from-existing` writes a wrapper summary from already generated reports without rerunning benchmark commands.

Generate a new hybrid config:

```bash
python3 src/tools/gen_hybrid_config.py \
  --target PULP_ITA.my_target \
  --top-module my_target_gpu_cov_tb \
  --overlay overlays/my/src/my_target_gpu_cov_tb.sv
```

The generated config covers the scaling gate, coverage manifest, slice launch template, and generic host-probe build metadata. New generated templates use `src/tools/build_host_probe.py`, so they do not require adding a matching target to `src/hybrid/Makefile`.

## Coverage Output Equivalence

Acceptance policy:

```text
coverage_output_equivalence
```

The comparison target is the declared output word set, not raw Verilator state. This keeps CPU vs hybrid comparison stable when host-only internal fields differ.

Representative evidence:

- `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`
- `reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json`
- `reports/pulp_ita_mha_first_hybrid_benchmark_summary.json`
- `reports/pulp_ita_mha_64x1_1x64_scaling_summary.json`
- `reports/pulp_ita_mha_prefill_decode_split_summary.json`
- `reports/pulp_ita_mha_resident_decode_1x64_summary.json`
- `reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json`
- `reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json`
- `reports/results_reproduction_median_summary.json`
- `reports/resident_batch_sweep_summary.json`
- `reports/resident_state_reuse_experiment_summary.json`
- `reports/persistent_resident_state_abi_probe_summary.json`

## Completed NN Gates

Current goal evidence includes:

- `neural_network_rtl_paged_kv_cache_large_scaleup_gate.json`
- `neural_network_rtl_paged_kv_cache_large_review_gate.json`
- `neural_network_rtl_full_ita_mha_dependency_audit_gate.json`
- `neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json`
- `neural_network_rtl_full_ita_mha_larger_paged_kv_goal_review_gate.json`
- `neural_network_rtl_paged_attention_kv_score_harness_gate.json`
- `full_ita_mha_larger_paged_attention_kv_goal_completion_audit.json`
- `hybrid_verilator_like_config_and_probe_generation_gate.json`
- `full_mha_hybrid_try_completion_audit.json`
- `full_mha_scaleup_64x1_1x64_gate.json`
- `prefill_decode_split_mha_benchmark_gate.json`
- `resident_decode_optimization_probe_gate.json`
- `resident_decode_batch_parallel_probe_gate.json`
- `modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json`
- `public_results_packaging_gate.json`
- `public_benchmark_pack_externalization_readiness_audit.json`
- `public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json`
- `public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`
- `public_benchmark_pack_externalization_completion_gate.json`
- `next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`
- `paged_attention_kv_cache_scale_up_measurement_gate.json`
- `pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json`
- `pulp_ita_mha_shape_expansion_gate.json`
- `pulp_ita_mha_shape_expansion_review_gate.json`
- `public_benchmark_pack_goal_completion_audit.json`
- `one_command_reproduction_flow_gate.json`
- `repeat_median_results_reproduction_gate.json`
- `resident_execution_optimization_next_gate.json`
- `resident_batch_sweep_measurement_gate.json`
- `resident_batch_sweep_review_gate.json`
- `resident_state_reuse_experiment_gate.json`
- `resident_state_reuse_measurement_gate.json`
- `resident_state_reuse_review_gate.json`
- `persistent_resident_state_abi_probe_gate.json`
- `persistent_resident_state_abi_probe_implementation_gate.json`
- `persistent_resident_device_handle_storage_gate.json`
- `persistent_resident_device_handle_storage_review_gate.json`

Relevant RTL/harness surface:

- `overlays/ITA/src/pulp_paged_kv_cache_large_gpu_cov_tb.sv`
- `pulp_paged_kv_cache_large_host_probe`
- `tc_sram`

## MobileViT CPU-Kick Evidence

MobileViT is kept as CPU-kick evidence, not as RTL equivalence proof:

- `mobile_vit_cpu_kick_imagenet_accuracy`
- `mobile_vit_cpu_kick_rtl_hybrid_boundary`
- `apple/mobilevit-small`
- `complete_full_imagenet_validation_cpu_kick_accuracy_measured`
- `top-1 0.77022`
- `mobile_vit_cpu_kick_rtl_proxy_host_probe`
- `mobile_vit_hybrid_imagenet_eval_gate`
- `mobile_vit_hybrid_imagenet_eval_completion_audit`
- `mobile_vit_hybrid_imagenet_limit_128_scaleup_completion_audit`

Hybrid ImageNet evaluation entrypoint:

```bash
python3 -m venv artifacts/mobile_vit/venv
artifacts/mobile_vit/venv/bin/python -m pip install -U pip
artifacts/mobile_vit/venv/bin/python -m pip install -r requirements/mobile_vit.txt

python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128
```

This regenerates the `limit 128` manifest, runs CPU-kick MobileViT inference, runs the `mobile_vit_cpu_kick_rtl_proxy` hybrid control-boundary batch, and computes accuracy from CPU-kick predictions. It is not a claim that MobileViT logits are produced by RTL.

Current retained evidence includes both the real cached two-image smoke and a `limit 128` local-cache ImageNet scale-up:

- manifest: `artifacts/mobile_vit/apple_mobilevit_small/imagenet_manifest_128.json`
- summary: `reports/mobile_vit_hybrid_128_summary.json`
- compare: `reports/mobile_vit_cpu_kick_rtl_proxy_imagenet_batch1_128_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- result: `evaluated_count=128`, `top1_accuracy=0.7734375`, `top5_accuracy=0.953125`, `coverage_output_equivalence_complete=true`

Full 50k ImageNet hybrid scale-up remains optional follow-up work.

## Artifact Policy

Ignored generated outputs:

- `artifacts/`
- `reports/`
- `work/`

Do not put canonical decisions in generated outputs. If a generated result matters, record the regeneration command in docs and reference the generated path from the relevant gate. `reports/` and `artifacts/` are allowed to be empty except for `.gitignore`.

### Local disk hygiene (optional)

These paths are **regenerable**; remove them when reclaiming disk, then follow the matching commands in this README, `docs/results.md`, or the relevant gate JSON.

- **`artifacts/mobile_vit/venv`**: GPU-oriented PyTorch / Hugging Face stack used by `src/tools/results_reproduction_mobile_vit.py` (`MOBILE_VIT_PYTHON`). Recreate with the **MobileViT CPU-Kick Evidence** `venv` + `pip install` block above.
- **Verilator `artifacts/*_obj_dir/**`**: per-target `--Mdir` trees. Delete DUTs you no longer build; recreate via the template / `run_hybrid_template.py` / gate-documented `verilator --cc ... --Mdir ...` flows.

## Next Direction

The paged-attention/KV-cache repeat-median public-pack boundary is complete. The selected next workstream is `config_generation_validation_breadth`:

- use `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate.json` as the source selection gate for the config-generation validation breadth workstream
- use `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json` as the source completion gate
- use `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json` as the source refresh gate
- use `config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json` as the source selection gate
- use `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json` as the externalization readiness audit
- use `config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json` as the source completion gate
- use `config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json` as the current next-goal selection gate after the repeat-median result
- use `docs/results.md` as the external-facing benchmark pack
- use `config/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json` for the fresh MHA `1x1`, `32x1`, and `1x32` generic-host-probe chain
- use `reports/persistent_resident_state_abi_repeat_median_summary.json` as the newest persistent resident ABI timing evidence
- keep `coverage_output_equivalence` as the correctness policy
- run `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3 --dry-run` to inspect the persistent resident repeat-median flow
- run `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3` to regenerate the report; the current median hybrid wall is `4.965 ms`, median GPU kernel total is `4.934624 ms`, and all samples pass coverage-output equivalence with mismatch count `0`
- current selected goal is complete: the public benchmark pack externalization boundary is closed without changing runtime or ABI behavior
- dry-run completed: all four paged-attention/KV-cache scale-up dry-run commands exited with code `0`
- measurement completed: all four paged-attention/KV-cache scale-up measurement commands exited with code `0` and passed `coverage_output_equivalence` with mismatch count `0`
- generated compare evidence: `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json`, `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json`, `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`, and `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`
- review completed: `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json` selects a timing summary gate because the compare reports prove correctness but do not contain timing fields
- timing summary defined: `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` records single-run CPU, hybrid wall, and GPU-kernel timing for the same four shapes without changing runtime, ABI, or workload scope
- timing summary reviewed: `config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json` selects a public-results packaging refresh next, while preserving the single-run and non-production boundaries
- public results refresh defined: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json` keeps the reviewed four-shape correctness and single-run timing evidence in the public pack without adding a measurement, workload, runtime change, repeat-median claim, or production serving claim
- public benchmark pack externalization completed after timing refresh: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json` closes the publication boundary before selecting another measurement
- next measurement selected: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json` selects repeat-median timing for the existing four-shape paged-attention/KV-cache set, because the remaining evidence gap is timing stability rather than another single-run shape expansion
- repeat-median timing boundary defined: `config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json` fixes the existing four-shape set and records that the existing `--repeat-median` workflow does not cover all four required paged-attention/KV-cache shapes
- repeat-median workflow added: `config/scaling_gates/paged_attention_kv_cache_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --paged-kv-repeat-median 3 --dry-run` for all four reviewed paged-attention/KV-cache shapes
- repeat-median measurement recorded: `config/scaling_gates/paged_attention_kv_cache_repeat_median_measurement_gate.json` records `reports/paged_attention_kv_cache_repeat_median_summary.json`; all four shapes pass `coverage_output_equivalence` with mismatch count `0`
- repeat-median review completed: `config/scaling_gates/paged_attention_kv_cache_repeat_median_review_gate.json` accepts the scoped repeat-count `3` measurement for the public pack and keeps production serving, raw full-state equality, runtime/ABI, and new-workload claims out of scope
- repeat-median public results refresh defined: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_repeat_median_gate.json` keeps the reviewed repeat-median evidence in the public pack without adding a measurement, workload, runtime change, or production serving claim
- public benchmark pack externalization completed after repeat-median refresh: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_repeat_median_gate.json` closes the publication boundary before selecting another measurement
- next measurement selected after repeat-median refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_repeat_median_refresh_gate.json` selects `config_generation_validation_breadth`
- config-generation validation breadth defined: `config/scaling_gates/config_generation_validation_breadth_gate.json` fixes the tracked template set for generic host-probe metadata validation
- config-generation validation breadth dry-run passed: `config/scaling_gates/config_generation_validation_breadth_dry_run_gate.json` records six tracked `1x1 --dry-run` command plans using `src/tools/build_host_probe.py`
- config-generation validation breadth dry-run reviewed: `config/scaling_gates/config_generation_validation_breadth_dry_run_review_gate.json` accepts command-plan evidence and keeps build/run/compare claims out of scope
- config-generation validation breadth execution defined: `config/scaling_gates/config_generation_validation_breadth_execution_gate.json` fixes the six tracked `1x1` build/run/compare commands for the next execution gate
- config-generation validation breadth execution passed: `config/scaling_gates/config_generation_validation_breadth_execution_result_gate.json` records that all six tracked `1x1` build/run/compare commands passed `coverage_output_equivalence` with mismatch count `0`
- config-generation validation breadth execution reviewed: `config/scaling_gates/config_generation_validation_breadth_execution_review_gate.json` accepts the six-template correctness result and selects a public-results packaging refresh next
- config-generation validation breadth public results refresh defined: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_breadth_execution_gate.json` keeps the reviewed six-template correctness result in the public pack without adding timing, speedup, runtime/ABI, new-workload, raw full-state equality, or production serving claims
- public benchmark pack externalization completed after config-generation validation breadth: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_breadth_execution_gate.json` closes the publication boundary before selecting another measurement
- next measurement selected after config-generation validation breadth public refresh: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_breadth_public_pack_refresh_gate.json` selects shape-breadth definition work
- config-generation validation shape breadth defined: `config/scaling_gates/config_generation_validation_shape_breadth_gate.json` fixes the non-`1x1` tracked-template dry-run set
- config-generation validation shape breadth dry-run passed: `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_gate.json` records 12 dry-run command plans with exit code `0`
- config-generation validation shape breadth dry-run reviewed: `config/scaling_gates/config_generation_validation_shape_breadth_dry_run_review_gate.json` accepts the dry-run command-plan boundary
- config-generation validation shape breadth execution defined: `config/scaling_gates/config_generation_validation_shape_breadth_execution_gate.json` fixes 12 non-dry-run build/run/compare commands using `src/tools/build_host_probe.py` and `coverage_output_equivalence`; this is not fresh build/run/compare evidence, and reports and artifacts are generated evidence, not source of truth
- config-generation validation shape breadth execution passed: `config/scaling_gates/config_generation_validation_shape_breadth_execution_result_gate.json` records 12 non-`1x1` build/run/compare commands; all passed `coverage_output_equivalence` with mismatch count `0`
- config-generation validation shape breadth execution reviewed: `config/scaling_gates/config_generation_validation_shape_breadth_execution_review_gate.json` accepts the 12-command correctness result and selects a public-results packaging refresh next
- Shape-breadth public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_config_generation_validation_shape_breadth_execution_gate.json` keeps the reviewed 12-command non-`1x1` correctness result in the public pack without adding timing, speedup, runtime/ABI, new-workload, raw full-state equality, or production serving claims
- public benchmark pack externalization completed after config-generation validation shape breadth: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_config_generation_validation_shape_breadth_execution_gate.json` closes the publication boundary before selecting another measurement
- next measurement selected after config-generation validation shape breadth public refresh: `config/scaling_gates/next_measurement_selection_after_config_generation_validation_shape_breadth_public_pack_refresh_gate.json` selects resident execution overhead breakdown
- resident execution overhead breakdown defined: `config/scaling_gates/resident_execution_overhead_breakdown_gate.json` fixes the existing-evidence analysis boundary
- resident execution overhead breakdown analysis recorded: `config/scaling_gates/resident_execution_overhead_breakdown_analysis_gate.json` records existing-evidence-only wall-minus-kernel residuals for resident batch sweep, file-boundary state reuse, and persistent resident ABI repeat-median evidence; the next task is to review the runtime boundary choice without claiming a new measurement or speedup
- resident execution overhead runtime-boundary review: `config/scaling_gates/resident_execution_overhead_runtime_boundary_review_gate.json` selects a persistent resident ABI shape/phase sweep next; runtime/ABI optimization and paged-attention/KV-cache scale-up remain deferred until the existing ABI path has broader shape and phase evidence
- persistent resident ABI shape/phase sweep workflow implemented: `config/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi-shape-phase-sweep --dry-run`, distinct per-case reports, and the aggregate summary path `reports/persistent_resident_state_abi_shape_phase_sweep_summary.json`
- persistent resident ABI shape/phase sweep measurement recorded: `config/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_measurement_gate.json` records all four repeat-count `3` cases passing `coverage_output_equivalence` with mismatch count `0`; median hybrid wall is `3.036 ms` for `16x64_p2_r3`, `5.646 ms` for `16x64_p4_r3`, `8.367 ms` for `16x128_p4_r3`, and `5.244 ms` for `32x64_p4_r3`; the measurement review gate accepts this result and selects the public results refresh next
- persistent resident ABI shape/phase sweep public results refresh defined: `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_state_abi_shape_phase_sweep_gate.json` keeps the reviewed four-case sweep evidence in the public pack without adding a measurement, runtime/ABI change, new workload, raw full-state equality claim, or production serving claim
- public benchmark pack externalization completed after persistent resident ABI shape/phase sweep: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_persistent_resident_state_abi_shape_phase_sweep_gate.json` closes the publication boundary and sets `select_next_measurement_after_persistent_resident_state_abi_shape_phase_sweep_public_pack_refresh` as the next selection task
- next measurement selected after persistent resident ABI shape/phase sweep public refresh: `config/scaling_gates/next_measurement_selection_after_persistent_resident_state_abi_shape_phase_sweep_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_continuation_gate` next
- paged-attention/KV-cache scale-up continuation defined: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_gate.json` fixes tracked `pulp_paged_kv_cache_large` `512x1` and `1x128`, plus tracked `pulp_paged_attention_kv_score` `128x1` and `1x128`; next task is `run_paged_attention_kv_cache_scale_up_continuation_dry_run_gate`
- paged-attention/KV-cache scale-up continuation dry-run passed: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_dry_run_gate.json` records 4 dry-run command plans exiting with code `0`; next task is `review_paged_attention_kv_cache_scale_up_continuation_dry_run_gate`
- paged-attention/KV-cache scale-up continuation dry-run reviewed: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_dry_run_review_gate.json` accepts the dry-run command plan and selects `run_paged_attention_kv_cache_scale_up_continuation_measurement_gate`
- paged-attention/KV-cache scale-up continuation measurement recorded: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_measurement_gate.json` records all 4 non-dry-run build/run/compare commands passing `coverage_output_equivalence` with mismatch count `0`; raw full-state equality remains out of scope and the next task is `review_paged_attention_kv_cache_scale_up_continuation_measurement_gate`
- paged-attention/KV-cache scale-up continuation measurement reviewed: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_measurement_review_gate.json` accepts the measurement result and selects `define_public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_gate`
- paged-attention/KV-cache scale-up continuation public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_gate.json` keeps the reviewed four-report correctness evidence in the public pack and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh`
- public benchmark pack externalization completed after paged-attention/KV-cache scale-up continuation: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_continuation_gate.json` closes the publication boundary and sets `select_next_measurement_after_paged_attention_kv_cache_scale_up_continuation_public_pack_refresh` as the next selection task
- next measurement selected after paged-attention/KV-cache scale-up continuation public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_continuation_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_continuation_repeat_median_gate` next
- paged-attention/KV-cache scale-up continuation repeat-median boundary defined: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_gate.json` fixes the same four continuation shapes, requires repeat count `3`, and selects `add_paged_attention_kv_cache_scale_up_continuation_repeat_median_workflow` next
- paged-attention/KV-cache scale-up continuation repeat-median workflow added: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --paged-kv-continuation-repeat-median 3 --dry-run` for the reviewed four continuation shapes
- paged-attention/KV-cache scale-up continuation repeat-median measurement recorded: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_measurement_gate.json` records `reports/paged_attention_kv_cache_scale_up_continuation_repeat_median_summary.json`; all four shapes pass `coverage_output_equivalence` with mismatch count `0`
- paged-attention/KV-cache scale-up continuation repeat-median review completed: `config/scaling_gates/paged_attention_kv_cache_scale_up_continuation_repeat_median_review_gate.json` accepts the scoped repeat-count `3` result for public-pack use and keeps production serving, raw full-state equality, runtime/ABI, and new-workload claims out of scope
- paged-attention/KV-cache scale-up continuation repeat-median public results refresh defined: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_gate.json` keeps the reviewed repeat-count `3` timing evidence in the public pack and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh`
- public benchmark pack externalization completed after paged-attention/KV-cache scale-up continuation repeat-median: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_gate.json` closes the publication boundary and sets `select_next_measurement_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_public_pack_refresh` as the next selection task
- next measurement selected after paged-attention/KV-cache scale-up continuation repeat-median public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_continuation_repeat_median_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_next_shapes_gate` next
- paged-attention/KV-cache scale-up next-shapes measurement passed: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_measurement_gate.json` records 4 non-dry-run build/run/compare commands for `1024x1`, `1x256`, `256x1`, and `1x256`; all passed `coverage_output_equivalence` with mismatch count `0`
- paged-attention/KV-cache scale-up next-shapes measurement reviewed: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_measurement_review_gate.json` accepts the four-report correctness evidence and selects the public results refresh next
- paged-attention/KV-cache scale-up next-shapes public results refresh: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_next_shapes_gate.json` keeps the reviewed four-report correctness evidence in the public pack and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh`
- public benchmark pack externalization completed after paged-attention/KV-cache scale-up next-shapes: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_next_shapes_gate.json` closes the publication boundary and sets `select_next_measurement_after_paged_attention_kv_cache_scale_up_next_shapes_public_pack_refresh` as the next selection task
- next measurement selected after paged-attention/KV-cache scale-up next-shapes public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_next_shapes_public_pack_refresh_gate.json` selects `define_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate` next, keeping the same four next-shapes and requiring repeat count `3` before timing-stability claims
- paged-attention/KV-cache scale-up next-shapes repeat-median boundary defined: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json` fixes the same four next-shapes, requires repeat count `3`, records the workflow gap, plans `python3 src/tools/run_results_reproduction.py --paged-kv-next-shapes-repeat-median 3`, plans `reports/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json`, and selects `add_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_workflow` next
- paged-attention/KV-cache scale-up next-shapes repeat-median workflow added: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_workflow_gate.json` adds `python3 src/tools/run_results_reproduction.py --paged-kv-next-shapes-repeat-median 3 --dry-run` for the reviewed four next-shapes and selects `run_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_timing_gate` next
- paged-attention/KV-cache scale-up next-shapes repeat-median measurement recorded: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_measurement_gate.json` records `reports/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json`; all four shapes pass `coverage_output_equivalence` with mismatch count `0`, with state-parallel wall ratios from `387.388` to `1088.195` and single-state repeated wall ratios from `0.907` to `0.996`
- paged-attention/KV-cache scale-up next-shapes repeat-median review completed: `config/scaling_gates/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_review_gate.json` accepts the scoped repeat-count `3` result for public-pack use and keeps production serving, raw full-state equality, runtime/ABI, and new-workload claims out of scope
- paged-attention/KV-cache scale-up next-shapes repeat-median public results refresh defined: `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json` keeps the reviewed repeat-count `3` timing evidence in the public pack, includes the generated summary plus four median reports as evidence snapshots, and selects `select_next_measurement_after_config_generation_validation_additional_targets_public_pack_refresh`
- public benchmark pack externalization completed after paged-attention/KV-cache scale-up next-shapes repeat-median: `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_gate.json` closes the publication boundary and sets `select_next_measurement_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_public_pack_refresh` as the next selection task
- next measurement selected after paged-attention/KV-cache scale-up next-shapes repeat-median public refresh: `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_scale_up_next_shapes_repeat_median_public_pack_refresh_gate.json` selects `define_config_generation_validation_additional_targets_gate` next, because generated-config validation breadth is the current weakest point
- previous paged-attention/KV-cache dry-run commands: `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_kv_cache_large.json --shape 256x1 --dry-run`, `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_kv_cache_large.json --shape 1x64 --dry-run`, `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run`, and `python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 1x64 --dry-run`
- do not import unreviewed candidate overlays or change runtime/ABI behavior for this selection boundary
- keep the long-term goal: make hybrid execution close to Verilator usage while preserving reproducible correctness and speed evidence for LLM-serving-like RTL workloads
- keep config current-state-only and historical evidence in gates; regenerate reports/artifacts only when needed
- keep public CLIs thin and tested
