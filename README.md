# GPU Toggle Coverage Minimal

Minimal extraction of the GPU-toggle coverage hybrid-runtime project.

The repository keeps the active implementation surface small while preserving a reproducible path from configuration to build, run, comparison, and status reporting. Generated outputs are not source of truth.

## Goal

Large goal:

`modern_llm_serving_rtl_hybrid_conditions`

Current priority:

`public_benchmark_pack_externalization_ready`

Current gate:

`config/scaling_gates/public_results_packaging_gate.json`

The larger project question is: identify the conditions where a hybrid CPU/GPU RTL coverage runtime can run modern LLM-serving-like RTL workloads correctly and quickly.

External-facing result synthesis:

- `docs/results.md`
- `python3 src/tools/run_results_reproduction.py --dry-run`
- `python3 src/tools/run_results_reproduction.py --repeat-median 3 --dry-run`
- `python3 src/tools/run_results_reproduction.py --resident-batch-sweep 1,8,16,32 --resident-batch-sweep-repeat 3 --dry-run`
- `python3 src/tools/run_results_reproduction.py --resident-state-reuse 16x64 --resident-state-reuse-phases 4 --dry-run`
- `python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --dry-run`
- `python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run`
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
- Treat `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, and this README as the current source of truth.
- Treat `reports/` and `artifacts/` as generated evidence/output only.
- Review `reports/hybrid_benchmark_*.json` for the compact wrapper summary schema: target, shape or limit, execution mode, commands, expected reports, and collected evidence.
- Prefer `--dry-run` first when reproducing measurements.
- External pack boundary: a review bundle may include generated `reports/*.json` as evidence, but a clean checkout can regenerate them from the documented commands.
- Public pack manifest: `docs/results.md` lists the minimum source-of-truth files, `records/scaling_gates` gate/audit records, tools, templates, contract tests, and optional generated evidence snapshots to include for review.
- Public reproduction smoke: `docs/results.md` lists the first dry-run commands to run before attempting full measurements.
- Public release checklist: `docs/results.md` lists the final source-of-truth, path hygiene, smoke, evidence, non-claim, and contract-test checks before handoff.
- Externalization readiness audit: `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json` records the minimum review surfaces, smoke commands, release checks, and evidence policy for external review.
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

Upstream RTL source is provided through submodules. Initialize the active upstream source before running target templates:

```bash
git submodule update --init third_party/rtlmeter
```

## Active Scope

`active_targets:` are recorded in `config/selection.json`.

The current compact selection records:

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
```

Verilator-like benchmark runner:

```bash
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode resident-state-reuse --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --summary-out reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 1x1 --summary-out reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode resident-state-reuse --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 1x1 --mode persistent-resident-state-abi --phases 2 --summary-out reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --summary-from-existing --summary-out reports/hybrid_benchmark_mobile_vit_template_limit128.json
```

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
python3 -m pip install -r requirements/mobile_vit.txt

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

## Next Direction

The next useful goal is review of the refreshed public benchmark pack:

- use `config/scaling_gates/public_results_packaging_gate.json` as the current gate
- use `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json` as the external review readiness audit
- use `docs/results.md` as the external-facing benchmark pack
- use `config/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json` for the fresh MHA `1x1`, `32x1`, and `1x32` generic-host-probe chain
- use `reports/persistent_resident_state_abi_probe_summary.json` as the newest persistent resident ABI evidence
- keep `coverage_output_equivalence` as the correctness policy
- keep the long-term goal: make hybrid execution close to Verilator usage while preserving reproducible correctness and speed evidence for LLM-serving-like RTL workloads
- keep config current-state-only and historical evidence in gates; regenerate reports/artifacts only when needed
- keep public CLIs thin and tested
