# FC-045: GPU Sidecar Eligibility and Shape Policy

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/19
Target file: `src/tools/*policy*`, `src/tools/hybrid_benchmark_*`, `docs/results.md`, `README.md`, `tests/contract/`

## Objective

Develop the current GPU sidecar algorithm from measured shape evidence into an
explicit eligibility and shape-selection policy. The policy should decide when a
known RTL slice is likely to benefit from GPU sidecar execution, and which shape
class to prefer, without claiming arbitrary RTL support or automatic optimal GPU
allocation.

The evidence base is narrow and must be treated by measurement region. Earlier
repeat-median evidence (#16) is useful for shape intuition, but FC-056 records a
more direct `pulp_ita_mha` eval-only comparison: the current `64x1` headline
shape is not faster on GPU, `256x1` is also slower, crossover is around 1024
independent states, and large batches (`4K` to `256K` states) show scoped
kernel-only benefit. Because FC-056 is gated behind direct native correctness
(FC-057) and RTLMeter direct-native correctness (FC-058), those numbers are
policy input only, not closure evidence or a broad acceleration claim.

Depends on measurement evidence issue #16, filelist-derived boundary issue #17,
first real Verilator path FC-042 / #9, direct native runtime integration FC-057 /
#57, RTLMeter direct-native correctness FC-058 / #58, and timing policy evidence
FC-056 / #56. It can start as a dry-run policy helper before broad execution
support exists.

## Algorithm Direction

Prefer GPU sidecar when all of these are true:

- Many independent states can be batched into one launch.
- The per-state RTL work is compute-heavy enough to amortize launch overhead.
- State transfer and compared output words are small relative to compute.
- The measurement region is explicit (kernel-only, transfer-inclusive wall time,
  or full tool flow) and comparable to the decision being made.
- Correctness can be checked with a declared observable policy such as
  `coverage_output_equivalence`.
- The source closure, top, schedule, and sidecar context are explicit and
  reviewed.

Prefer CPU or require a resident/persistent mitigation when these are true:

- The workload is primarily one state advanced across many dependent steps.
- Each step requires CPU/GPU synchronization.
- The observable set requires returning large raw internal state every time.
- The testbench depends on stdout, `$display`, `$finish`, DPI, or external
  side effects rather than a sidecar-compatible observable policy.
- The filelist/top/source closure is unknown or inferred weakly.
- The only available shape is a small independent-state batch such as `64x1`
  without resident execution or another launch-overhead mitigation.

## Tasks

- Define a small eligibility record with at least:
  `target`, `shape`, `independent_state_count`, `steps_per_state`,
  `observable_policy`, `source_closure_status`, `state_bytes_estimate`,
  `output_words_estimate`, `measurement_region`, `evidence_status`, and
  `recommended_action`.
- Encode conservative rules for:
  - high-confidence state-parallel recommendation,
  - low-confidence single-state repeated-step recommendation,
  - resident/persistent-resident mitigation recommendation,
  - fail-closed unsupported/unknown source closure.
- Use existing reviewed evidence for `filelist_paged_attention_kv_score`,
  `filelist_known_template_pulp_ita_mha`, and FC-056. Keep older evidence
  region-scoped; do not mix state-generation time with eval-only or kernel-only
  timing.
- Add a dry-run/inspection path that prints the recommendation without launching
  GPU work.
- Add contract tests that prove unsupported targets do not produce a high
  confidence GPU recommendation.
- Update docs only after the policy wording preserves non-claims.

## Acceptance

- The policy treats `64x1` `pulp_ita_mha` as correctness/UX smoke evidence, not
  as speedup evidence.
- The policy only gives a favorable performance recommendation for
  `pulp_ita_mha` when the requested shape is in the measured large independent
  batch region, and the output states kernel-only caveats.
- The policy does not recommend broad GPU execution for unknown targets,
  incomplete source closures, missing repeat-median evidence, or arbitrary
  filelists.
- `1xN` repeated-step shapes are marked weaker or routed toward
  resident/persistent mitigation rather than presented as optimal GPU use.
- JSON output, if any, is debug/inspection only and not runtime ABI.
- Docs keep this as a scoped policy, not automatic optimal allocation.

## Current State

- `src/tools/gpu_sidecar_eligibility_policy.py` adds the first importable
  conservative policy helper.
- `src/tools/gpu_sidecar_eligibility_policy_cli.py` adds a thin dry-run/report
  CLI for that helper.
- The helper consumes FC-063 / FC-065 suitability JSON as debug/review metadata
  and emits `recommended_action`, not runtime authority.
- `64x1` state-parallel `pulp_ita_mha` suitability maps to
  `gpu_correctness_smoke_only_require_larger_batch_evidence`, preserving the
  no-speedup boundary.
- Large independent-state batches can map to
  `prefer_gpu_state_parallel_large_batch_with_caveats` only with reviewed source
  closure and region-scoped caveats.
- VeeR/design-CPU-like poor suitability maps to
  `prefer_cpu_parallel_or_new_mapping`.
- Missing/unreviewed source closure fails closed, and `1xN` repeated-step shapes
  route toward resident or CPU-parallel mitigation.

## Validation

```sh
git diff --check
python3 -m unittest discover -s tests/contract -p '*policy*' -q
python3 -m unittest tests.contract.test_gpu_sidecar_eligibility_policy -q
python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-gpu-allocation-policy --dry-run
```

Add a focused test if no existing policy test covers the new eligibility record.

## Non-Goals

- No arbitrary RTL support.
- No automatic optimal GPU allocation claim.
- No new measurement beyond citing existing issue evidence.
- No broad speedup claim.
- No runtime/ABI change.
- No CIRCT execution support.
- No RTLMeter acceleration claim.
