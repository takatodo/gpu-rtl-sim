# Results

## Conclusion

The hybrid runtime is useful for scoped modern-LLM-serving-like RTL harnesses when the workload has many independent states per launch and correctness is checked with coverage-output equivalence.

The strongest measured condition is state-parallel execution. The weakest baseline condition is a single state advanced across many repeated launches. Resident execution only slightly changes the `1x64` median in the latest run, while resident batch-parallel decode restores much of the throughput shape by amortizing one resident launch across many states.

The persistent resident ABI probe adds a stronger decode-like condition: one process can keep the same GPU `d_storage` allocation authoritative across four cumulative `16x64` phases, with phase dumps used only as compare evidence rather than as the next phase input.

The current result is a scoped RTL-harness conclusion. It is not a production LLM serving benchmark.

## How To Read This Pack

Read this benchmark pack in this order:

1. Start with the conclusion and non-claims in this document.
2. Use `config/selection.json`, `docs/status.md`, and `docs/roadmap.md` as the canonical current project state.
3. Treat `reports/*.json` as generated evidence from documented commands, not as hand-authored decisions.
4. Use wrapper summaries named `reports/hybrid_benchmark_*.json` as the compact review surface for target, shape or limit, execution mode, commands, expected reports, and collected evidence.
5. Use `--dry-run` commands before running measurements to inspect the exact command sequence and expected generated outputs.

Evidence status terms:

| Term | Meaning |
| --- | --- |
| `executed` | The wrapper command executed benchmark commands and collected evidence from the resulting reports. |
| `existing_evidence` | The wrapper summary was built from already generated reports without rerunning the benchmark commands. |
| `coverage_output_equivalence` | CPU and hybrid agree on the declared output word set; this is not raw full-state equality. |
| `reports/` | Generated summaries and comparisons; useful evidence, but not source of truth. |
| `artifacts/` | Generated build outputs, binaries, state dumps, and raw runtime material. |

External pack boundary:

- A published review bundle may include generated `reports/*.json` files as evidence snapshots.
- A clean checkout should treat those reports as reproducible outputs and regenerate them from the documented commands when needed.
- Canonical decisions remain in `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, and `README.md`.

Prerequisites by path:

| Path | Needs |
| --- | --- |
| `python3 src/tools/run_results_reproduction.py --dry-run` | Python only; prints commands and expected outputs. |
| `python3 src/tools/run_hybrid_benchmark.py ... --dry-run` | Python only; prints target-oriented wrapper commands. |
| Wrapper summary generation with `--summary-out` | Existing tool inputs plus generated `reports/` evidence when collecting results. |
| Persistent resident ABI measurements | Verilator object directories, CUDA-capable runtime, and the hybrid host/GPU build outputs under `artifacts/`. |
| MobileViT `limit 128` | Python MobileViT dependencies, local Hugging Face ImageNet parquet cache, and generated CPU-kick/hybrid proxy reports. |

Public pack manifest:

| Group | Include | Reason |
| --- | --- | --- |
| Current source of truth and reader pack | `README.md`, `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, `docs/results.md` | Current objective, status, roadmap, result narrative, and reader guide. Canonical project-state decisions remain in `README.md`, `config/selection.json`, `docs/status.md`, and `docs/roadmap.md`; this document is the external-facing result pack. |
| Gate and audit evidence | `records/scaling_gates/public_results_packaging_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`, `records/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json`, `records/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json`, `records/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_gate.json`, `records/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json`, `records/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json`, `records/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json`, `records/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json`, `records/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json`, `records/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json`, `records/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json`, `records/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json`, `records/scaling_gates/public_benchmark_pack_goal_completion_audit.json`, `records/scaling_gates/generic_hybrid_benchmark_cli_gate.json`, `records/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json`, `records/scaling_gates/pulp_ita_mha_shape_expansion_gate.json`, `records/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json` | Machine-readable benchmark-pack scope, externalization readiness, completion audit, wrapper summary schema, the fresh full ITA/MHA generic-host-probe chain, the persistent resident repeat-median selection/measurement/refresh/completion chain, the paged-attention/KV-cache scale-up selection, measurement, timing summary, timing-summary public-results refresh/completion, next repeat-median timing selection, and the repeat-median timing boundary definition; these are also available through the `config/scaling_gates` compatibility symlink. |
| Reproduction tools | `src/tools/run_results_reproduction.py`, `src/tools/results_reproduction.py`, `src/tools/run_hybrid_benchmark.py`, `src/tools/hybrid_benchmark.py`, `src/tools/run_hybrid_template.py` | Public CLI entrypoints and shared logic needed to regenerate evidence. |
| Target templates | `config/slice_launch_templates/pulp_ita_mha.json`, `config/slice_launch_templates/pulp_paged_kv_cache_large.json`, `config/slice_launch_templates/pulp_paged_attention_kv_score.json`, `config/slice_launch_templates/mobile_vit_cpu_kick_rtl_proxy.json` | Supported representative workload templates. |
| Contract tests | `tests/contract/test_full_ita_mha_larger_paged_kv_next.py`, `tests/contract/test_hybrid_verilator_like_cli.py` | Public pack, wrapper summary, CLI, and local-path policy checks. |
| Generated review evidence | `reports/results_reproduction_median_summary.json`, `reports/persistent_resident_state_abi_probe_summary.json`, `reports/persistent_resident_state_abi_repeat_median_summary.json`, `reports/mobile_vit_hybrid_128_summary.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`, `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`, `reports/hybrid_benchmark_*.json` | Optional evidence snapshots for review; regenerate from documented commands when absent. |
| Non-pack outputs | `artifacts/` raw dumps and build trees | Reproducible local outputs; do not treat as canonical pack content. |

Public archive dry-run:

This section is the scoped `public_pack_archive_ready` task inside the current public benchmark pack externalization objective.

Use this command to print the archive include/exclude plan without creating an archive file:

```bash
python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run
```

The archive dry-run is intentionally non-writing. It lists the same source-of-truth files, gate/audit records, tools, templates, tests, and optional generated evidence snapshots as the public pack manifest. It also prints the non-executed command `tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>`. Archive files, if created outside this workflow, are generated outputs and must not become source of truth.

Public reproduction smoke:

Run these commands first when checking the public pack from a fresh checkout. They are dry-run commands, so they validate the public CLI surface and command expansion without requiring Verilator/CUDA execution, generated object directories, or ImageNet data.

```bash
python3 src/tools/run_results_reproduction.py --dry-run
python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 16x64 --mode persistent-resident-state-abi --dry-run
python3 src/tools/run_hybrid_benchmark.py mobile_vit --limit 128 --dry-run
```

Passing this smoke set means the public commands are parseable and expand to the expected workflow. It does not prove correctness or timing; those claims require the generated evidence reports listed below.

## Public Release Checklist

This section is the scoped `public_release_checklist_ready` task inside the current public benchmark pack externalization objective.

Before publishing or handing off the benchmark pack, verify:

| Check | How to verify | Required result |
| --- | --- | --- |
| Source-of-truth alignment | Inspect `README.md`, `config/selection.json`, `docs/status.md`, and `docs/roadmap.md`. | All point at `add_paged_attention_kv_cache_repeat_median_workflow` and `config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json`. |
| Reader guide and boundaries | Inspect `docs/results.md`. | It includes `How To Read This Pack`, `External pack boundary`, `Prerequisites by path`, `Public pack manifest`, and `Public reproduction smoke`. |
| Local path hygiene | Search public docs, gates, and wrapper summaries for local absolute paths. | No machine-local absolute path prefixes are exposed. |
| Smoke commands | Run the public reproduction smoke commands above. | All commands exit successfully and do not write benchmark evidence. |
| Archive dry-run | Run `python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run`. | The command prints include/exclude paths and does not create an archive. |
| Evidence claims | Inspect `docs/results.md` and `reports/hybrid_benchmark_*.json`. | Correctness claims are scoped to `coverage_output_equivalence`; `existing_evidence` is not presented as fresh execution. |
| Non-claims | Inspect `docs/results.md:Non-Claims`. | Production serving, raw full-state equality, RTL logits/ImageNet accuracy, and paper-grade confidence are not claimed. |
| Contract tests | Run `python3 -m unittest discover -s tests/contract -q`. | All contract tests pass, with expected skips only. |

Externalization readiness audit:

`config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`

The audit records the minimum review surfaces, smoke commands, release checks, evidence policy, and persistent resident repeat-median refresh for handing this pack to an external reader. Its `ready_for_external_review` status means the pack is organized for review; it is not a new measurement result and does not strengthen the timing or correctness claims beyond the referenced evidence.

## Correctness Condition

The accepted correctness policy is:

```text
coverage_output_equivalence
```

The comparison target is the declared output word set, not raw Verilator state. Raw state may differ because host-only Verilator internals, scheduler state, and pointer-like fields are not stable CPU-vs-GPU comparison targets.

For GPU execution initialized from a CPU state image, host-only internals must be sanitized before upload.

Representative compare evidence:

| Workload | Shape | Compare report | Result |
| --- | --- | --- | --- |
| Full ITA/MHA | `1x1` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA fresh generic-host-probe | `32x1` | `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA fresh generic-host-probe | `1x32` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA | `64x1` | `reports/pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA | `1x64` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x64_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA resident | `1x64` | `reports/pulp_ita_mha_cpu_vs_hybrid_1x64_resident_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA resident batch | `32x64` | `reports/pulp_ita_mha_cpu_vs_hybrid_32x64_resident_coverage_output_compare.json` | pass, mismatch `0` |
| Full ITA/MHA persistent resident ABI | `16x64..16x256` | `reports/persistent_resident_state_abi_probe_summary.json` | pass, mismatch `0` |
| Paged KV-cache large | `256x1` | `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json` | pass, mismatch `0` |
| Paged KV-cache large | `1x64` | `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json` | pass, mismatch `0` |
| Paged-attention KV score | `64x1` | `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json` | pass, mismatch `0` |
| Paged-attention KV score | `1x64` | `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json` | pass, mismatch `0` |
| MobileViT CPU-kick RTL proxy | `cfg_batch_length=128` | `reports/mobile_vit_cpu_kick_rtl_proxy_imagenet_batch1_128_cpu_vs_hybrid_1x1_coverage_output_compare.json` | pass, mismatch `0` |

For the paged KV-cache and paged-attention KV-score scale-up rows, correctness is based on `selected_acceptance_policy.passed` and `coverage_output_policy.mismatch_count == 0`. Top-level raw/full-state `match` is not the acceptance target and may be false; raw/full-state mismatch is diagnostic information only. These four rows are correctness evidence, not timing or speedup evidence.

## Performance Summary

Paged-attention/KV-cache scale-up single-run timing:

| Workload | Shape | Interpretation | CPU elapsed ms | Hybrid wall ms | GPU kernel total ms | CPU / hybrid wall | Evidence |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Paged KV-cache large | `256x1` | state-parallel | `599.228` | `1.266` | `1.233920` | `473.32385466034754x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |
| Paged KV-cache large | `1x64` | single-state repeated | `2.93242` | `1.907` | `1.878016` | `1.5377136864184584x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |
| Paged-attention KV score | `64x1` | state-parallel attention-score proxy | `137.923` | `1.666` | `1.635328` | `82.78691476590637x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |
| Paged-attention KV score | `1x64` | single-state repeated attention-score proxy | `2.69249` | `1.404` | `1.300480` | `1.9177279202279203x` | `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json` |

This is single-run timing from generated reports for the already reviewed four-shape measurement set. It is not repeat-median timing or production LLM-serving throughput evidence.

Repeat-median timing highlights, generated with `python3 src/tools/run_results_reproduction.py --repeat-median 3`:

| Workload | Shape | Interpretation | CPU elapsed ms | Hybrid wall ms | Ratio / improvement | Evidence |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Full ITA/MHA | `64x1` | state-parallel, prefill-like | `177.257` | `1.286` | CPU / hybrid wall `137.84x` | `reports/pulp_ita_mha_64x1_median.json` |
| Full ITA/MHA | `1x64` | single-state repeated, decode-like baseline | `3.03036` | `1.622` | CPU / hybrid wall `1.87x` | `reports/pulp_ita_mha_1x64_median.json` |
| Full ITA/MHA resident | `1x64` | resident decode-like | `3.21449` | `2.020` | wall `0.80x` vs non-resident `1x64` | `reports/pulp_ita_mha_1x64_resident_median.json` |
| Full ITA/MHA resident batch | `32x64` | resident batch decode-like | `72.5432` | `1.918` | wall per-state-step `33.70x` over resident `1x64` | `reports/pulp_ita_mha_32x64_resident_median.json` |
| Paged-attention KV score | `64x1` | state-parallel attention-score proxy | `145.323` | `1.199` | CPU / hybrid wall `121.20x` | `reports/pulp_paged_attention_kv_score_64x1_median.json` |

All five repeat-median workloads passed coverage-output equivalence with mismatch count `0`. The aggregate report is `reports/results_reproduction_median_summary.json`.

Fresh full ITA/MHA generic-host-probe chain:

| Workload | Shape | Interpretation | CPU elapsed ms | Hybrid wall ms | Result | Gate |
| --- | --- | --- | ---: | ---: | --- | --- |
| Full ITA/MHA fresh generic-host-probe | `1x1` | minimal smoke | `2.91612` | `0.891` | pass, mismatch `0` | `config/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json` |
| Full ITA/MHA fresh generic-host-probe | `32x1` | state-parallel | `72.0539` | `0.877` | pass, mismatch `0` | `config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json` |
| Full ITA/MHA fresh generic-host-probe | `1x32` | single-state repeated-step | `2.93625` | `1.453` | pass, mismatch `0` | `config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json` |

This fresh chain is single-run evidence for the generic host-probe path. It is separate from the repeat-median table above and is not a paper-ready statistical benchmark.

Persistent resident ABI probe:

| Workload | Shape | Interpretation | Hybrid wall ms | GPU kernel total ms | Result | Evidence |
| --- | --- | --- | ---: | ---: | --- | --- |
| Full ITA/MHA persistent resident ABI | `16x64..16x256` | one process, same `d_storage` across four cumulative phases | `4.517` | `4.486688` | all phases pass, mismatch `0` | `reports/persistent_resident_state_abi_probe_summary.json` |

Persistent resident ABI repeat-median:

| Workload | Shape | Interpretation | Hybrid wall ms median | GPU kernel total ms median | Per final state-step wall ms median | Result | Evidence |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| Full ITA/MHA persistent resident ABI | `16x64..16x256`, repeat `3` | same existing persistent resident ABI path, no runtime/ABI change | `4.965` | `4.934624` | `0.001212158203125` | all samples pass, mismatch `0` | `reports/persistent_resident_state_abi_repeat_median_summary.json` |

## MobileViT ImageNet Evidence

MobileViT is included as CPU-kick ImageNet evidence plus a hybrid RTL control-boundary check. The model logits and accuracy are produced by CPU-kick MobileViT inference records; the hybrid RTL proxy verifies the CPU-visible `LOAD_MODEL` / `LOAD_IMAGE` / `KICK_INFER` / `POLL_DONE` boundary with coverage-output equivalence.

| Scope | Images | Accuracy source | Top-1 | Top-5 | CPU-kick events | Hybrid batch | Compare result | Evidence |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| smoke | `2` | CPU-kick predictions | `1.0` | `1.0` | `2` kick / `2` done | `cfg_batch_length=2`, `1` batch | pass, mismatch `0` | `reports/mobile_vit_hybrid_smoke_summary.json` |
| scale-up | `128` | CPU-kick predictions | `0.7734375` | `0.953125` | `128` kick / `128` done | `cfg_batch_length=128`, `1` batch | pass, mismatch `0` | `reports/mobile_vit_hybrid_128_summary.json` |

The `limit 128` run uses the local Hugging Face ImageNet parquet cache:

```bash
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128
```

## Reproduction

The public one-command entrypoint for the representative result set is:

```bash
python3 src/tools/run_results_reproduction.py --dry-run
```

Inspect the command sequence first. For a full run, remove `--dry-run`:

```bash
python3 src/tools/run_results_reproduction.py
```

The command expands into the representative MHA, resident decode, resident batch-decode, and paged-attention KV-score runs used by this document.

For repeat-median timing evidence, use:

```bash
python3 src/tools/run_results_reproduction.py --repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --repeat-median 3
```

For persistent resident ABI repeat-median timing evidence, use:

```bash
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3 --dry-run
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --persistent-resident-state-abi-repeat-median 3
```

The lower-level template runner remains available for individual slice templates:

```bash
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x1 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 32x1 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x32 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 1x64 --dry-run
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1 --dry-run
```

The target-oriented benchmark runner provides a shorter Verilator-like interface for supported workloads:

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

`--summary-out` writes a generated unified wrapper summary under `reports/` by default. The schema records target, shape or limit, mode, command list, expected reports, and collected evidence when commands actually execute; dry-run summaries explicitly remain non-evidence.

`--summary-from-existing` writes the same wrapper schema from already generated reports without rerunning benchmark commands. It is useful for publishing the current benchmark pack, but it is not fresh execution evidence by itself.

Wrapper summary schema fields:

```text
schema_version
tool
target
shape
limit
mode
phases
execution_mode
command_count
commands
expected_reports
evidence
non_claims
```

Wrapper summary reports currently published in this benchmark pack:

| Target | Mode | Shape / limit | Execution mode | Summary report | Evidence status |
| --- | --- | --- | --- | --- | --- |
| `pulp_ita_mha` | `template` | `1x1` | `executed` | `reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json` | pass, mismatch `0` |
| `paged_attention_kv_score` | `template` | `1x1` | `executed` | `reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json` | pass, mismatch `0` |
| `pulp_ita_mha` | `resident-state-reuse` | `1x1`, `2` phases | `executed` | `reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json` | pass, mismatch `0` |
| `pulp_ita_mha` | `persistent-resident-state-abi` | `1x1`, `2` phases | `executed` | `reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json` | pass, mismatch `0` |
| `mobile_vit` | `template` | `limit=128` | `existing_evidence` | `reports/hybrid_benchmark_mobile_vit_template_limit128.json` | collected from existing MobileViT limit-128 evidence |

Generated binaries and raw state dumps go under `artifacts/`; generated summaries and comparisons go under `reports/`.

The resident decode batch-parallel measurements were produced from the existing `pulp_ita_mha` Verilator object directory with `run_vl_hybrid.py --resident-steps`, CPU repeat-state dumps, and `compare_vl_hybrid_modes.py --acceptance-policy coverage_output_equivalence`.

The persistent resident ABI probe is reproduced with:

```bash
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4 --dry-run
python3 src/tools/run_results_reproduction.py --persistent-resident-state-abi 16x64 --persistent-resident-state-abi-phases 4
```

The MobileViT ImageNet `limit 128` evidence is reproduced with:

```bash
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128 --dry-run
python3 src/tools/run_results_reproduction.py --mobile-vit-imagenet-128
```

## Non-Claims

This repository does not claim:

- not production LLM serving throughput
- not cross-process persistent CUDA state
- not model-level Transformer inference
- not production KV-cache memory hierarchy
- not production paged attention
- not MobileViT numerical inference in RTL
- not ImageNet accuracy from RTL logits
- not full 50k ImageNet hybrid execution
- not quantized model accuracy
- not broad speedup for arbitrary RTL
- not raw full-state equality
- paper-grade statistical confidence beyond repeat-count 3 representative medians

## Source Evidence

Canonical state and completion audit:

- `README.md`
- `config/selection.json`
- `docs/results.md`
- `docs/status.md`
- `docs/roadmap.md`
- `config/scaling_gates/public_results_packaging_gate.json`
- `config/scaling_gates/public_benchmark_pack_goal_completion_audit.json`
- `config/scaling_gates/generic_hybrid_benchmark_cli_gate.json`
- `config/scaling_gates/one_command_reproduction_flow_gate.json`
- `config/scaling_gates/repeat_median_results_reproduction_gate.json`
- `config/scaling_gates/modern_llm_serving_rtl_hybrid_conditions_goal_completion_audit.json`
- `config/scaling_gates/public_benchmark_pack_externalization_readiness_audit.json`
- `config/scaling_gates/public_results_packaging_refresh_after_pulp_ita_mha_shape_expansion_gate.json`
- `config/scaling_gates/next_goal_selection_after_persistent_resident_repeat_median_gate.json`
- `config/scaling_gates/persistent_resident_state_abi_repeat_median_measurement_gate.json`
- `config/scaling_gates/public_results_packaging_refresh_after_persistent_resident_repeat_median_gate.json`
- `config/scaling_gates/public_benchmark_pack_externalization_completion_gate.json`
- `config/scaling_gates/next_measurement_selection_after_public_benchmark_pack_externalization_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_scale_up_measurement_review_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_timing_summary_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_timing_summary_review_gate.json`
- `config/scaling_gates/public_results_packaging_refresh_after_paged_attention_kv_cache_timing_summary_gate.json`
- `config/scaling_gates/public_benchmark_pack_externalization_completion_after_paged_attention_kv_cache_timing_summary_gate.json`
- `config/scaling_gates/next_measurement_selection_after_paged_attention_kv_cache_timing_refresh_gate.json`
- `config/scaling_gates/paged_attention_kv_cache_repeat_median_timing_gate.json`
- `config/scaling_gates/pulp_ita_mha_first_generic_host_probe_build_run_compare_gate.json`
- `config/scaling_gates/pulp_ita_mha_shape_expansion_gate.json`
- `config/scaling_gates/pulp_ita_mha_shape_expansion_review_gate.json`
- `config/scaling_gates/mobile_vit_hybrid_imagenet_eval_gate.json`
- `config/scaling_gates/mobile_vit_hybrid_imagenet_limit_128_scaleup_completion_audit.json`

Result summaries:

- `reports/pulp_ita_mha_first_hybrid_benchmark_summary.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_32x1_coverage_output_compare.json`
- `reports/pulp_ita_mha_cpu_vs_hybrid_1x32_coverage_output_compare.json`
- `reports/pulp_ita_mha_64x1_1x64_scaling_summary.json`
- `reports/pulp_ita_mha_prefill_decode_split_summary.json`
- `reports/pulp_ita_mha_resident_decode_1x64_summary.json`
- `reports/pulp_ita_mha_resident_decode_batch_parallel_summary.json`
- `reports/pulp_paged_kv_cache_large_first_hybrid_benchmark_summary.json`
- `reports/pulp_paged_attention_kv_score_first_hybrid_benchmark_summary.json`
- `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_256x1_coverage_output_compare.json`
- `reports/pulp_paged_kv_cache_large_cpu_vs_hybrid_1x64_coverage_output_compare.json`
- `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_64x1_coverage_output_compare.json`
- `reports/pulp_paged_attention_kv_score_cpu_vs_hybrid_1x64_coverage_output_compare.json`
- `reports/results_reproduction_median_summary.json`
- `reports/persistent_resident_state_abi_probe_summary.json`
- `reports/persistent_resident_state_abi_repeat_median_summary.json`
- `reports/pulp_ita_mha_64x1_median.json`
- `reports/pulp_ita_mha_1x64_median.json`
- `reports/pulp_ita_mha_1x64_resident_median.json`
- `reports/pulp_ita_mha_32x64_resident_median.json`
- `reports/pulp_paged_attention_kv_score_64x1_median.json`
- `reports/mobile_vit_hybrid_smoke_summary.json`
- `reports/mobile_vit_hybrid_128_summary.json`
- `reports/mobile_vit_hybrid_128_accuracy.json`
- `reports/mobile_vit_hybrid_128_cpu_kick_predictions.json`
- `reports/mobile_vit_cpu_kick_rtl_proxy_imagenet_batch1_128_cpu_vs_hybrid_1x1_coverage_output_compare.json`
- `reports/hybrid_benchmark_pulp_ita_mha_template_1x1.json`
- `reports/hybrid_benchmark_paged_attention_kv_score_template_1x1.json`
- `reports/hybrid_benchmark_pulp_ita_mha_resident_state_reuse_1x1.json`
- `reports/hybrid_benchmark_pulp_ita_mha_persistent_resident_state_abi_1x1.json`
- `reports/hybrid_benchmark_mobile_vit_template_limit128.json`
