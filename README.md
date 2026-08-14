# GPU Toggle Coverage Minimal

Minimal extraction of the GPU-toggle coverage hybrid-runtime project.

## OpenTitan TL-UL regression tracer

`examples/tlul10818/tlul_adapter_sram_10818_tb.sv` is a standalone reproducer
for [OpenTitan issue #10818](https://github.com/lowRISC/opentitan/issues/10818):
an integrity-failed `Get` must return `DataWhenError`, including when the D
channel is backpressured.  OpenTitan and Verilator are external dependencies;
neither is vendored or mutated by this repository.

Run it against a checkout before the fix and one including
[PR #10820](https://github.com/lowRISC/opentitan/pull/10820):

```bash
python3 src/tools/run_tlul10818_cpu_regression.py \
  --verilator /path/to/verilator \
  --bad /path/to/opentitan-before-10820 \
  --fixed /path/to/opentitan-with-10820 \
  --out artifacts/tlul10818_cpu
```

The report separates action observations from the independent oracle: the bad
revision must violate it and the fixed revision must satisfy it.  GPU batching,
coverage-guided seed selection, and performance claims are intentionally not
made by this CPU contract.

The device-clean synchronous wrapper has a stricter GPU gate.  It builds the
same wrapper for CPU and GPU, applies identical resident patch schedules, and
compares only `done`, the oracle bit, response error/integrity bits, and
response data.  It excludes raw generated state because that contains host
pointers and runtime bookkeeping.

```bash
python3 src/tools/run_tlul10818_gpu_equivalence.py \
  --verilator /path/to/verilator \
  --verilator-root /path/to/verilator-source-or-install-root \
  --bad /path/to/opentitan-before-10820 \
  --fixed /path/to/opentitan-with-10820 \
  --out artifacts/tlul10818_gpu_equivalence
```

The gate requires an oracle violation in the bad revision and its absence in
the fixed revision for both immediate-D and D-backpressured actions.  It is a
correctness gate, not an exploration or speed claim.

To reproduce the bounded exploration comparison after the equivalence gate:

```bash
python3 src/tools/summarize_tlul10818_campaign.py \
  --equivalence-report artifacts/tlul10818_gpu_equivalence/tlul10818_gpu_equivalence.json \
  --bad-checkout /path/to/opentitan-before-10820 \
  --fixed-checkout /path/to/opentitan-with-10820 \
  --out artifacts/tlul10818_campaign
```

The domain is the complete Cartesian product of a valid versus malformed `Get`
and immediate versus backpressured D acceptance.  The tool exhausts its 24
permutations for each policy, so its p50/p95/max and tail values are exact for
that finite domain.  `new_coverage_seeds`, `oracle_violation_seeds`, and
`known_regression_seeds` are emitted separately.  Coverage is an explicit
functional action-bin bitmap used to select interesting seeds; only the
independent response oracle labels a bug candidate.  The report records source
revision, checkpoint, action-domain, and GPU-manifest identities.  The
integrity-stratified policy is fixed before feedback, so it is not a bandit,
online-learning, or PPO claim.

The source currently lives on branch `feature/tlul10818-regression`; the
working copy used during development is `/tmp/gpu-tlul10818-regression`, rather
than the home directory.  It must be pushed or checked out there before a
home-directory `find .` can discover it.

## OpenTitan EDN regression tracer

`examples/edn23526/edn_csrng_23526_tb.sv` is a standalone CPU reproducer for
[OpenTitan issue #23526](https://github.com/lowRISC/opentitan/issues/23526):
when EDN has asserted `csrng_req_valid`, an error ACK while
`csrng_req_ready` is low must not drop valid before the ready handshake.  The
direct Verilator build uses `examples/edn23526/prim_generic_aliases.sv` to map
OpenTitan abstract primitive names to the generic primitive implementations
that FuseSoC/primgen normally select.

Run it against a checkout before the fix and one including
[PR #23607](https://github.com/lowRISC/opentitan/pull/23607):

```bash
python3 src/tools/run_edn23526_cpu_regression.py \
  --verilator /path/to/verilator \
  --bad /path/to/opentitan-before-23607 \
  --fixed /path/to/opentitan-with-23607 \
  --out artifacts/edn23526_cpu
```

The expected CPU oracle split is `protocol_violation=1` for the bad revision
and `protocol_violation=0` with `valid_after_error=1` for the fixed revision.
The device-clean GPU gate uses `examples/edn23526/edn_csrng_23526_gpu_tb.sv`.
It drives the four-action domain `success_ack_ready`,
`success_ack_backpressured`, `error_ack_ready`, and
`error_ack_backpressured` with resident patch schedules, then compares only
`done`, `protocol_violation`, `valid_after_error`, valid-observed, and the
action coverage bitmap.

```bash
python3 src/tools/run_edn23526_gpu_equivalence.py \
  --verilator /path/to/verilator \
  --verilator-root /path/to/verilator-source-or-install-root \
  --bad /path/to/opentitan-before-23607 \
  --fixed /path/to/opentitan-with-23607 \
  --out artifacts/edn23526_gpu_equivalence
```

To reproduce the bounded EDN exploration comparison after the equivalence gate:

```bash
python3 src/tools/summarize_edn23526_campaign.py \
  --equivalence-report artifacts/edn23526_gpu_equivalence/edn23526_gpu_equivalence.json \
  --bad-checkout /path/to/opentitan-before-23607 \
  --fixed-checkout /path/to/opentitan-with-23607 \
  --out artifacts/edn23526_campaign
```

The summary emits `new_coverage_seeds`, `oracle_violation_seeds`, and
`known_regression_seeds` separately.  Coverage is the action-bin bitmap; only
the independent valid/ready oracle marks a bug candidate.  The risk-stratified
order is fixed before feedback, so it is not an online-learning or PPO claim.

## OpenTitan entropy_src regression tracer

`examples/entropy10983/entropy_src_main_sm_10983_tb.sv` is a standalone CPU
reproducer for [OpenTitan issue #10983](https://github.com/lowRISC/opentitan/issues/10983):
in firmware-override entropy-insert mode, SHA3 processing must not start before
firmware has explicitly started the insert window.  The local oracle checks
`entropy_src_main_sm` because [PR #11003](https://github.com/lowRISC/opentitan/pull/11003)
adds the missing main-state-machine handshake.

Run it against the PR base and merge commits:

```bash
python3 src/tools/run_entropy10983_cpu_regression.py \
  --verilator /path/to/verilator \
  --bad /path/to/opentitan-before-11003 \
  --fixed /path/to/opentitan-with-11003 \
  --out artifacts/entropy10983_cpu
```

The expected CPU oracle split is `early_sha3_process=1` for the bad revision
and `early_sha3_process=0` for the fixed revision.  GPU equivalence and corpus
generation are the next gates for this third known issue.

## Goal

This repository is an experimental GPU sidecar runtime for RTL compiler frontends. Verilator is the current compatibility frontend because its generated C++ build path is the shortest route to a usable sidecar; CIRCT is a planned frontend target through the same sidecar contract idea.

The contract is the boundary between frontend-owned RTL/build information and sidecar-owned GPU build, run, and compare work. It should be represented in importable code and runtime metadata first. JSON output is useful for debug and review; automation may inspect it, but it should not become execution authority or the required runtime ABI.

### Three Layers

These layers keep current support separate from direction:

1. Current execution support: scoped template and benchmark flows run through the GPU sidecar path and compare CPU vs hybrid outputs with `coverage_output_equivalence`; unsupported paths fail closed.
2. Preview UX: Verilator-like option plumbing uses `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` through repo wrappers and shims, with non-executing previews where noted.
3. Long-term goal: a frontend-neutral sidecar that can be reached from Verilator and CIRCT while finding the conditions where LLM-serving-like RTL workloads run correctly and efficiently on hybrid CPU/GPU execution.

### Current Algorithm Status

The core GPU sidecar algorithm is established for scoped template-backed RTL workloads. Correctness is claimed through `coverage_output_equivalence`, not raw full-state equality. The best observed shape is state-parallel work that evaluates many independent states in one sidecar launch.

This does not claim arbitrary RTL support, arbitrary filelist inference, broad native Verilator support, automatic optimal allocation, stable external runtime ABI, RTLMeter acceleration, or production throughput.

Current pointer, mirrored from `config/selection.json`:

- `current_priority`: `opentitan_temporal_protocol_gpu_resident_regression_discovery`
- `current_next_action`: `add_entropy10983_gpu_equivalence_and_corpus_gate`
- `current_priority_source_artifact`: `artifacts/entropy10983_cpu/entropy10983_cpu_regression.json`

Latest OpenTitan regression-discovery update: TL-UL #10818 and EDN #23526 now form the two-IP seed set. Both targets have fixed revisions/checkpoints/action domains/oracles/semantic-manifest identities, bad-revision oracle violations, fixed-revision non-reproduction, CPU/GPU semantic equivalence, separated corpora, and reproducible random-vs-stratified summaries.

Historical FC-069 update: Stage118 block-source `1760` is clean/raw-clean through candidate `2021`. Extended Stage119 maps dirty `block_source_id=1760`, `source_id=2` to `compact.cfg_clone.entry_phi.producer_selector.counters3969` with `skipped_count=1536`. This remains historical context for the old gateGPT frontier, not the current OpenTitan regression-discovery pointer.

Stage117 update: the previous `1..256` report is not accepted as Stage117 runtime evidence because generated IR lacked Stage117 instrumentation due stale `vlgpugen` pass-tool build order. Pass-tool freshness is now fixed so stale pass tools rebuild before IR generation. With the lightweight saved-address Stage117 probe and a 900s `ptxas` bound, `reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_light_block_body_boundary_range_1_2048_ptxas900_runtime.json` reaches runtime: all three entry slices pass `ptxas`, preflight passes, and classification is `token_loop_stage117_phase1_callee0_nested_body_block_body_boundary_same_saved_addr_changed`. The first `COUNT=1024` run was clean, but `COUNT=2048` finds a dirty Stage117 block-body boundary at `source_id=1760` with `split_result=same_saved_addr_changed`, `before_direct_param_record318=0`, `after_direct_param_record318=38666621`, `after_saved_addr_record318=38666621`, `saved_after_polluted=true`, and `semantic_authority=false`. Current IR mapping evidence points to `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:834516` metadata row and reconstructed block `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ll:327571` / `%19690` in `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`; the patched control-word store is `artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu_patched.ll:333201`, `control_word=72058702139492064`. This is a dirty boundary, not final adjacent-window write-source authority.

Stage119/120/121/122/123/124 implementation update: Stage119 skipped-span boundary diagnostics inspect contiguous spans that Stage118 intentionally skips, including compact CFG-clone/probe spans. Stage120 splits one mapped skipped span into instruction-level boundaries using `VLGPUGEN_STAGE120_BLOCK_SOURCE_ID`, `VLGPUGEN_STAGE120_SKIP_SPAN_SOURCE_ID`, `VLGPUGEN_STAGE120_INSTRUCTION_START`, and `VLGPUGEN_STAGE120_INSTRUCTION_COUNT`; `VLGPUGEN_STAGE120_SPAN_EDGE_PROBE=1` probes the aggregate span entry-to-exit edge with `boundary_kind_id=6`, `VLGPUGEN_STAGE120_AGGREGATE_EDGE_PROBE=1` probes prefix aggregate edges with `boundary_kind_id=7`, and `VLGPUGEN_STAGE120_LOW_PERTURBATION_PROBE=1` removes the before/saved-address observation to distinguish diagnostic perturbation from a stable after-only polluted edge. Stage123 adds `--ordering-aware-stage123-concrete-write-window-bisection-probe` / `VLGPUGEN_STAGE123_CONCRETE_WRITE_WINDOW_BISECTION_PROBE=1` for concrete store/atomic/mem-intrinsic candidates after Stage121 diagnostic suppression. Stage124 adds `--ordering-aware-stage124-record318-transition-probe` / `VLGPUGEN_STAGE124_RECORD318_TRANSITION_PROBE=1` for post-suppression record318 transition scanning. Runtime printing exposes the Stage122 lifecycle probe, Stage123 concrete write-window probe, and Stage124 transition probe. The progress fallback is now 192 counters, with Stage122 slots at `168..175`, Stage123 slots at `176..183`, and Stage124 slots at `184..191`.

Stage121 source611 diagnostic-atomic suppression reproduction command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 611 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-aggregate-edge-probe \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage121_source611_diagnostic_atomic_suppression_ptxas300_runtime.json
```

Stage121 source613 diagnostic-atomic suppression reproduction command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 613 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-aggregate-edge-probe \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-id 613 \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage121_source613_diagnostic_atomic_suppression_ptxas300_runtime.json
```

Historical Stage121 multi-source diagnostic-atomic suppression reproduction command for the superseded source619 frontier:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 619 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-aggregate-edge-probe \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 613,615,618 \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage120_block1760_span2_aggregate_edge_source619_after_source613_615_618_suppression_low_perturbation_ptxas300_runtime.json
```

Stage121 source622 diagnostic marker-read suppression reproduction command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 622 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-aggregate-edge-probe \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage120_block1760_span2_aggregate_edge_source622_after_source611_613_615_618_620_marker_read622_suppression_low_perturbation_ptxas300_runtime.json
```

Stage121 source625 global-suppression reproduction command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 625 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-aggregate-edge-probe \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage120_block1760_span2_aggregate_edge_source625_after_source611_613_615_618_620_624_marker_read622_global_suppression_low_perturbation_ptxas300_runtime.json
```

Stage122 expanded-ABI non-diagnostic lifecycle reproduction command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 1 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --ordering-aware-stage122-non-diagnostic-lifecycle-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage122_record318_write_source_expanded_abi_after_stage121_global_suppression_ptxas300_runtime.json
```

Stage123 concrete write-window wide-range reproduction command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 626 \
  --ordering-aware-stage120-instruction-count 911 \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --ordering-aware-stage123-concrete-write-window-bisection-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage123_concrete_write_window_source626_1536_after_stage121_global_suppression_ptxas300_runtime.json
```

Stage123 source940 confirmation command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 940 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --ordering-aware-stage123-concrete-write-window-bisection-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage123_concrete_write_window_source940_after_stage121_global_suppression_ptxas300_runtime.json
```

Stage123 source941..1536 follow-up scan command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 941 \
  --ordering-aware-stage120-instruction-count 596 \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --ordering-aware-stage123-concrete-write-window-bisection-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage123_concrete_write_window_source941_1536_after_stage121_global_suppression_ptxas300_runtime.json
```

Stage123 source1324 confirmation command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 1324 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --ordering-aware-stage123-concrete-write-window-bisection-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage123_concrete_write_window_source1324_after_stage121_global_suppression_ptxas300_runtime.json
```

Stage123 source1324 suppression/exclusion command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 1324 \
  --ordering-aware-stage120-instruction-count 1 \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624,1324 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --ordering-aware-stage123-concrete-write-window-bisection-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage123_concrete_write_window_source1324_suppressed_after_stage121_global_suppression_ptxas300_runtime.json
```

Stage123 source1325..1536 tail scan command:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir third_party/gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 300 \
  --ordering-aware-stage120-block-source-id 1760 \
  --ordering-aware-stage120-skip-span-source-id 2 \
  --ordering-aware-stage120-instruction-start 1325 \
  --ordering-aware-stage120-instruction-count 212 \
  --ordering-aware-stage120-low-perturbation-probe \
  --ordering-aware-stage121-source611-diagnostic-atomic-suppression-probe \
  --ordering-aware-stage121-diagnostic-atomic-suppression-source-ids 611,613,615,618,620,624 \
  --ordering-aware-stage121-diagnostic-marker-read-source-ids 622 \
  --ordering-aware-stage123-concrete-write-window-bisection-probe \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage123_concrete_write_window_source1325_1536_after_stage121_global_suppression_ptxas300_runtime.json
```

Stage118 ptxas-surface follow-up: `rtlmeter_vortex_ptx_entry_slice.py` now avoids treating semicolon-terminated `.func` declarations as function bodies, with a focused contract test. A dry-run regeneration report, `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_reduced_probe.json`, still produces large Stage118 slices (`762827`, `762985`, and `766310` lines), so this parser fix is correct but not sufficient; the next work remains shrinking retained prefix/global/reachable PTX surface or slice freshness before retrying `ptxas`.

Stage118 slice-freshness and split-surface mitigation: `gategpt_entry_sliced_cubin_chain.py` now writes a `*.cubin.slice.json` manifest after a successful `ptxas` run and only reuses an existing CUBIN when the current slice content hash, CUBIN path, GPU target, and ptxas options match that manifest. The entry-sliced specs now keep `vl_eval_batch_gpu` and `vl_patch_eval_pair_cycle_loop_batch_gpu` out of the helper support/feedback CUBINs because those symbols are already available from the token-loop slice. `reports/gategpt_tb_core_entry_sliced_cubin_chain_stage118_default_split_ptxas1_probe.json` shows the helper slices shrink to `418` and `483` lines and both pass `ptxas` within a 1s bound; the remaining blocker is the token-loop slice at `766310` lines, which still times out. This narrows the ptxas blocker from three huge slices to one huge token-loop slice; it does not identify the final adjacent-window write source.

Stage118 token-loop stub-surface diagnosis: `rtlmeter_vortex_ptx_entry_slice.py --stub-func` can now replace selected reachable `.func` bodies with ret-only diagnostic stubs for ptxas-surface experiments only. `reports/gategpt_tb_core_stage118_token_loop_stub_slice_probe.json` stubs `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` and `__vlgpu_compact_cluster_outline_frame_stub`, reducing the token-loop slice from `766310` to `5066` lines; `ptxas` then produces `artifacts/gategpt_tb_core_ptx_entry_slice_stage118_stub_probe/vl_tb_core_ordering_aware_phase_resident_token_loop_gpu.cubin`. This confirms the remaining ptxas blocker is the reachable high-eval callee/compact-outline body surface, not the token-loop entry body itself. The stub CUBIN is not runtime evidence and must not be used to classify Stage118 instruction range `1281`.

Stage112 source-summary guardrail: `src/tools/gategpt_stage112_store_source_summary.py` joins Stage112 runtime events with the LLVM metadata map without promoting static rows to runtime authority. `reports/gategpt_tb_core_stage112_store_source_static_candidate_summary.json` records static source candidates `1415` and `1533` as `_Z40Vtb_core___024root___nba_sequent__TOP__0` `expected_liveout` zero-clear stores, but the paired runtime report is `clean_no_nested_body_store` with `source_id=0`, so `runtime_authority=false`. These rows are useful suspects for static review, not final adjacent-window write-source authority.

Stage118 opt-in guard surface probe: the earlier `1281,count=64` 120s ptxas-only blocker is now superseded. The same opt-in guard with a 300s `ptxas` bound reaches runtime for `1281..1344` and `1345..1408`; both raw Stage118 events are `clean_no_instruction_boundary`, but their report-level classifier fields remain stale pre-fix Stage112-incomplete results. Classifier-fixed runtime reports now cover `1409..2021` clean, and the later `2049..2112` request is exhausted by metadata.

Stage118/119/120 runtime update: prior Stage118 reports classify `1..1280` clean, `1281..1408` reached runtime with raw clean Stage118 events but stale pre-fix report classifications, and classifier-fixed reports classify `1409..2021` clean. The Stage118 `2049..2112` request is metadata-exhausted and the diagnostic allocation alias scan is clean. Extended Stage119 finds the dirty skipped span at `source_id=2`, mapped to `compact.cfg_clone.entry_phi.producer_selector.counters3969`. Stage120 ranges `1..1536 / 1536` inside that mapped span are clean, and `1537..1792` is metadata-exhausted; the aggregate span-edge probe is dirty. Refreshed aggregate-edge prefix bisection with target metadata converged to regular-probe dirty `source610` after clean `source609`, but low-perturbation probing makes `source610` clean and leaves `source611` dirty as `after_only_polluted`. Stage121 source611 diagnostic-atomic suppression makes the targeted low-perturbation aggregate-edge probe clean (`source_id=0`, `split_result=clean_no_skipped_span_instruction_boundary`, `view_mask=0`), classifying the prior source611 after-only result as diagnostic counter perturbation rather than a proven pair-offset writer.

gateGPT切り出し条件: gateGPTを深掘りする場合は、全体`tb_core`高速化ではなく、計算ブロック型RTLのGPU適用境界を測る。採用条件は、(1)入出力契約が小さく固定できる、(2)状態間独立またはbatch化できる、(3)算術密度が高い、(4)host/device往復がbatchあたり1回以下、(5)CPU oracleとbit/word単位で比較できる、(6)CIRCT/HLSまたはVerilator loweringのどちら由来かを分けて記録できること。除外条件は、逐次token loop、PHI/liveout/valid authorityが主役、stdout/PASS/finish依存、巨大root-state差分、または1シナリオだけの細粒度制御であること。最初の候補は`exp_unit`、matvec/norm/attention系の固定幅サブブロック、比較対象はRTLMeterで得た制御・CPU型RTL境界とする。

現在の実験ゴール: FC-070 / #71 は `microgpt_inference_slice,inference2_hls_friendly,1024x1` の metadata-gated runtime boundary と gateGPT `exp_unit` 比較レーンまで closure-ready。FC-072 / #72 は scoped complete として、`src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` の candidate/source_variant/shape/layout/symbol gate を metadata surface 由来の generated header に切り出した。CPUは token loop/sampler/full KV-cache と未知・非対応形状を持ち、GPUは測定済み batched arithmetic だけを持つ。これは full microGPT、whole `tb_core`、自動partitioning、任意RTL bridge generation、multi-row source emitter、またはJSONだけのruntime ABI authorityを主張しない。

FC-070 / #71 progress: `scientific_circt_source_variant_runtime_dispatcher.py` accepts requested `--shape` and `--steps` gates, passes the selected metadata row into `build_runtime_handoff_report`, and the `src-hybrid-verilator` handoff validates candidate/source_variant/shape/entrypoint/runtime-boundary/layout/symbols before compile/run. The C++ bridge also checks compact metadata argv and returns `failed_metadata_gate` before `dlopen` on mismatch. The metadata-gated execute path now measures `inference2_hls_friendly,1024x1`: `reports/scientific_circt_source_variant_verilator_entrypoint.json` records `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, and `cpu_to_bridge_hybrid_wall_speedup=6.2165001599863245x`; the dispatcher report records `runtime_dispatch_measured` with nested `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, and `cpu_to_bridge_hybrid_wall_speedup=15.461002763357895x`. The gateGPT `exp_unit` comparison lane is refreshed in `reports/gategpt_testbench_probe.json`: `tb_exp` vector, distinct-state, and resident patch paths all pass `103/103` with mismatch `0`; resident repeat median is `1.422 ms` wall / `1.348608 ms` kernel versus CPU process-wall median `14.788301952648908 ms`. This remains narrow `tb_exp` comparison evidence with `speedup_claimed=false` and `usefulness_claimed=false`, not broad gateGPT or arbitrary RTL usefulness. The next implementation issue is FC-072 / #72: generate or otherwise reuse source-variant bridge code from metadata while preserving the same fail-closed gates.

FC-072 / #72 progress: the scoped src-hybrid bridge gate is now derived from the source-variant metadata helper and materialized as `artifacts/scientific_circt/source_variant_verilator_entrypoint/scientific_circt_source_variant_bridge_gate.h` before compiling the Verilator-callsite bridge. `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` consumes generated `SCI_CIRCT_BRIDGE_EXPECTED_*` macros and still returns `failed_metadata_gate` before `dlopen` if argv metadata does not match. The refreshed handoff report records `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum equality, generated header source `source_variant_metadata_row`, and `cpu_to_bridge_hybrid_wall_speedup=16.76826214888755x`; the dispatcher report records `runtime_dispatch_measured` with nested generated-header handoff and `cpu_to_bridge_hybrid_wall_speedup=15.600012129935479x`. This is still scoped to `inference2_hls_friendly,1024x1`, not arbitrary RTL bridge generation.

FC-072 / #72 closure audit: scoped acceptance is met. A broader reusable bridge source emitter for multiple metadata rows remains a possible follow-up only if the project explicitly needs that wider surface.

Current FC-069 evidence boundary: Stage109 proves record `318` changes after high-eval `callee_index=0`; Stage112/113/114/116 remain clean and Stage117/119/120 narrow the dirty area to compact CFG-clone producer-selector diagnostics. Source622 marker-read suppression, source624 diagnostic atomic positioning, and the source625 global-suppression clean run show the active producer-selector dirtiness is diagnostic counter/marker traffic. Stage122 expanded ABI shows the first non-diagnostic lifecycle edge after that suppressed span is still dirty, but the edge has no concrete record318/adjacent-window write target. Stage123 source1324 is excluded as a CFG-clone liveout-counter adjacent event because suppressing it removes the event but leaves record318 polluted and CPU oracle mismatch at 2. Stage124 reaches runtime through `1..896` in narrow windows plus source897,count128, source960,count1, source968,count1, source972,count1, source974,count1, and source975,count1; none finds a transition source. Unsuppressed source976,count1 is incomplete, but adding source976 to diagnostic atomic suppression restores source976 completion and lets source977,count1 through source1005,count1 complete with no transition. Unsuppressed source1006,count1 is incomplete, but adding source1006 to diagnostic atomic suppression restores source1006 completion with no transition. Source1007,count1 through source1019,count1 reach runtime under that suppression frontier with no transition. Unsuppressed source1020,count1 is incomplete; adding source1020 to diagnostic atomic suppression restores source1020 completion with no transition and no semantic authority. Source1021,count1 through source1053,count1 also reach runtime under source976/source1006/source1020 suppression with no transition and no semantic authority. The older source1024,count1 and source1025,count128 attempts without that advanced suppression frontier remain incomplete reachability attempts. The full `1..1536` window is a `ptxas` timeout. No semantic pass, speedup, usefulness, actual-valid authority, final write-source authority, or broad gateGPT PASS/FAIL authority is claimed.

Historical FC-069 notes before root replay:

A root-dispatch-only repair was tried and rejected before accepting this as a
new evidence gate: exposing additional post-lowering CFG-clone component roots
makes the generated `tb_core` LLVM IR fail verifier checks with
`Instruction does not dominate all uses` on shadow-payload loads, selects, and
PHI users. The next repair therefore has to make CFG-clone operands and
materialized liveout values component-local/dominance-safe before dispatching
slots `24..47`.

A follow-up component-local remap experiment narrowed the failure further but is
also not accepted as a source change: the generated `tb_core` PTX build passed
LLVM verification, but static metadata dropped to `24` CFG-clone liveout stores,
`24` unsupported liveouts, `96` unsupported operands, and `240` unsupported PHI
incoming values; the guarded diagnostic then observed `actual_valid_slots=none`
and `checked_slots=none` with `blocking=runtime_outline_call_reached_but_cfg_clone_liveout_counter_zero`.
The next repair must preserve all `48` liveout stores while making PHI/liveout
materialization dominance-safe.

An entry-frame seed / shadow cross-block undef experiment then restored the
LLVM verifier and kept static CFG-clone liveout stores at `48/48` with
unsupported operands, PHI incoming values, and liveouts all at `0`, but it still
did not cover liveout slots `24..47` at runtime: `checked_slots` and
`actual_valid_slots` remained `0..23` (`24/48`) with
`blocking=runtime_checked_slot_coverage_partial`. It also regressed the static
inactive successor-PHI select-to-liveout mapping to `0/832`, so that patch is
not accepted. The next implementation must use edge-local PHI incoming/liveout
rematerialization without losing the existing static select mapping or the
`48/48` liveout stores.

A narrower PHI-incoming-only edge rematerialization experiment also passed the
`tb_core` verifier/PTX build, but it did not move the runtime witness:
`checked_slots` and `actual_valid_slots` stayed `0..23` (`24/48`),
`expected_valid_slots` stayed `0..47`, `compare_count=250480`, and
`mismatch_count=0`; static inactive successor-PHI select mapping again regressed
to `0/832`. That experiment was reverted. The next repair must store
successor-PHI liveout values on the actual cloned branch/switch successor-exit
edges through `storeCfgCloneLiveOut`, not only remap PHI incoming values.

An external-successor-exit edge-store experiment then inserted
`storeCfgCloneLiveOut` on cloned branch/switch edges that leave the cloned
component. It also passed verifier/PTX, but runtime stayed partial at
`checked_slots=0..23` and `actual_valid_slots=0..23` (`24/48`), and static
inactive successor-PHI select mapping again regressed to `0/832`. This shows
edge stores alone do not dispatch the component that writes slots `24..47`.
The next repair must combine post-lowering component-root dispatch for the
missing component with dominance-safe edge/local materialization.

A direct-entry dispatch experiment made that next step more precise. Limiting
direct entry to the expected capture blocks kept the build passing but still
left the generated CFG-clone entry switch with only case `0`, so runtime stayed
at `checked_slots=0..23` and `actual_valid_slots=0..23` (`24/48`). Expanding
direct entry to every compact-cluster block exposed the missing path but failed
LLVM verification with `Instruction does not dominate all uses` on
shadow-payload/PHI/select values. The next repair must first materialize
entry-local PHI/shadow fallback values for the missing store path, then reopen
dispatch for slots `24..47` while preserving `48/48` stores and the `832/832`
static mapping.

The entry-liveout fallback diagnostic now makes that blocker explicit without
claiming runtime validity: `required_phi_liveout_fallback_count=48`,
`decoded_entry_frame_fallback_count=48`, and
`missing_entry_frame_fallback_count=0`, but
`clone_produced_actual_valid_authorized_count=0` and
`clone_produced_actual_valid_blocked_count=48` with authority
`entry_frame_fallback_decoded_no_clone_produced_actual_valid_authority`.
The next sub-action is to materialize the PHI/shadow values from current
state/shadow payloads before authorizing actual-valid slots `24..47`; copying
or reusing stale entry-frame liveout values is not acceptable evidence.
The follow-up PHI selector diagnostic narrows this again: all `48/48` fallback
liveouts are multi-incoming PHIs (`single_incoming_phi_liveout_count=0`,
`multi_incoming_phi_liveout_count=48`) with `816` total incoming edges, but
`entry_edge_selector_authorized_count=0` and
`entry_edge_selector_blocked_count=48` under `no_entry_edge_selector_authority`.
The next gate is to add a runtime predecessor-edge selector or replay the guarded
predecessor path before direct entry can mark slots `24..47` actual-valid.
The selector diagnostic counter ABI is now wired in generated IR/host/parser as
a non-authoritative slots-24..47 predecessor-edge counter:
`selector_group_count=2`, `max_phi_incoming_edge_count=28`,
`runtime_selector_arg_count=2`, `replay_authorized_count=0`, and
`blocked_phi_liveout_count=48` with authority
`entry_phi_selector_diagnostic_counter_abi_wired_no_actual_valid_authority`.
Read-only IR inspection shows the missing slots `24..47` share one recomputable
predecessor-edge selector. A bounded selector-counter smoke now observes the
runtime diagnostic ABI without running the full `--run-gpu-smoke` sweep:
`status=gategpt_gpu_selector_counter_observed`,
`selector_abi_available=true`, `selector_counter_count=48`,
`selector_observed_slots=24..47:3178 each`, `selector_observed_slot_count=24`,
`runtime_selector_argument_count=2`, `replay_authorized_count=0`,
`selected_phi_incoming_slots=24:3..47:3`,
`runtime_selected_phi_incoming_edge_index_count=24`,
`missing_runtime_selected_phi_incoming_edge_index_count=0`,
`runtime_selected_phi_incoming_value_materialized_count=24`,
`missing_runtime_selected_phi_incoming_value_materialized_count=0`,
`selected_phi_incoming_value_materialized_slots=24..47:3178 each`,
`selected_phi_incoming_value_compare_slots=24..47:422072 each`,
`runtime_selected_phi_incoming_value_compare_count=24`,
`selected_phi_incoming_value_mismatch_slots=24..47:206048 each`,
`runtime_selected_phi_incoming_value_mismatch_count=24`,
`selected_phi_incoming_value_store_site_reached_slots=24..47:422072 each`,
`runtime_selected_phi_incoming_value_store_site_reached_count=24`,
`selected_phi_incoming_value_store_site_reached_authority=selected_phi_incoming_value_store_site_reached_unproven_return_compare_proxy_no_actual_valid_authority`,
`selected_phi_incoming_value_store_site_immediate_compare_slots=none`,
`runtime_selected_phi_incoming_value_store_site_immediate_compare_count=0`,
`selected_phi_incoming_value_store_site_immediate_mismatch_slots=none`,
`runtime_selected_phi_incoming_value_store_site_immediate_mismatch_count=0`,
`selector_guarded_actual_valid_candidate_count=24`,
`selector_actual_valid_authority_review=blocked_missing_value_semantic_authority`,
`selector_actual_valid_materialized_slot_count=0`,
`actual_valid_authorized_count=0`, and `authority=false` with
`selected_phi_incoming_value_compare_authority=selected_phi_incoming_value_compare_mismatch_no_actual_valid_authority`.
This proves the selector counter and selected-value materialization path are
live. The return-site clone/CPU-oracle comparison diagnostic still finds a
selected-value mismatch for all 24 target slots. The store-site immediate
comparison remains missing, and the new store-site reached diagnostic survives
optimized GPU lowering only as a return-compare proxy:
`selected_phi_incoming_value_store_site_reached_slots=24..47:422072 each` with
runtime count `24` under
`selected_phi_incoming_value_store_site_reached_unproven_return_compare_proxy_no_actual_valid_authority`.
This does not prove true store-site materialization/compare reachability. The
fail-closed expected-valid missing diagnostic still survives optimization in the
return-compare path:
`selected_phi_incoming_value_store_site_immediate_expected_valid_slots=none`,
`selected_phi_incoming_value_store_site_immediate_expected_valid_missing_slots=24..47:422072 each`,
`runtime_selected_phi_incoming_value_store_site_immediate_expected_valid_count=0`,
`runtime_selected_phi_incoming_value_store_site_immediate_expected_valid_missing_count=24`, and
`selected_phi_incoming_value_store_site_immediate_expected_valid_authority=selected_phi_incoming_value_store_site_immediate_expected_valid_missing_no_actual_valid_authority`.
The return-compare diagnostic now records mismatch-time actual/expected samples
as `slot:encoded_edge:actual:expected`. The current bounded smoke reports all
24 target slots, including `24:4:4232314521:4284088574`,
`25:4:4246995464:4279042099`, and `26:4:4223336341:64356007`; encoded edge
`4` corresponds to the observed selected edge `3`. The previous return-compare
proxy did not prove a nonzero producer-selected encoded value; it wrote the
return-compare `Actual` value and has been removed. With that false-positive
gone, the current bounded smoke reports nonzero producer selector reads for
slots `24..47` as encoded `18`. `VlStripX86AttrsPass` now preserves `optnone`
for the generated compact-cluster outline diagnostic stub, so the
producer-selected encoded-value sample survives optimized GPU IR
(`selected_encoded_value=192`, metadata `1` in both source and optimized IR).
Store-before value samples also survive optimized GPU IR
(`candidate_source_value=96`, `materialized_store=384`,
`materialized_store_reload=96` in both source and optimized IR). The remaining
runtime zero fields are value-debug evidence, not value authority.
The optimized `vl_batch_gpu_opt.ll` still retains volatile mismatch-sample,
expected-valid-missing, `store_site_reached.return_compare_proxy`, and the
stable-return-path store-site compare/mismatch atomics in the executed
return-compare path. The selector-counter report now records
`selected_phi_incoming_store_site_path_elision_summary.status=store_site_compare_moved_to_stable_return_path_return_compare_proxy_retained`
with stable-return-path store-site compare/mismatch counters retained,
`runtime_selected_phi_incoming_value_store_site_immediate_compare_count=24`,
`runtime_selected_phi_incoming_value_store_site_immediate_mismatch_count=24`,
and `optimized_ir_true_store_site_any_counter_present=false`. The active
blocking summary is now
`stable_path_store_site_mismatch_runtime_producer_predecessor_selector_read_out_of_materialization_phi_range_after_nonzero_selector_read`
with historical next action
`split_or_reduce_cfg_clone_diagnostic_ptx_after_nondiagnostic_load_pass`.
This remains diagnostic classification only, not selected-value or actual-valid
authority; the current blocker has since moved to the producer-side selected
encoded value handoff into the materialized store path.
The current runtime still has not authorized actual-valid slots under that
selector. The generated
IR now also emits a fail-closed pass summary:
`prototype_repaired_select_only_compact_cluster_selector_gated_materialization_blocked`,
`required_phi_liveout_count=48`,
`selector_gated_materialization_attempt_count=24`,
`selector_gated_actual_valid_candidate_count=24`,
`selector_gated_materialization_authorized_count=0`, and
`selector_gated_materialization_blocked_count=48` with authority
`selector_gated_materialization_missing_no_actual_valid_authority`. The
authority-review metadata is also fail-closed with
`selector_actual_valid_blocked_expected_frame_fallback_not_value_semantic_authority`.
The selected-PHI-incoming materialization review is now fail-closed but live:
`prototype_repaired_select_only_compact_cluster_selected_phi_incoming_value_materialized_without_actual_valid_authority`,
`reviewed_candidate_count=24`,
`selected_phi_incoming_materialized_count=24`,
`runtime_edge_selector_count=24`,
`missing_runtime_edge_selector_count=0`,
`runtime_selected_phi_incoming_edge_index_count=24`,
`missing_runtime_selected_phi_incoming_edge_index_count=0`,
`runtime_selected_phi_incoming_value_materialized_count=24`,
`missing_runtime_selected_phi_incoming_value_materialized_count=0`,
`expected_frame_shortcut_rejected_count=24`, and `blocked_count=0` with
authority
`selected_phi_incoming_value_materialized_no_actual_valid_authority`. The
runtime failure classification is now clear:
`selected_phi_incoming_value_materialization_failure_slot_count=0`, empty
failure reason counts, and dominant reason `none`. The generated IR also
reports static materialization clear:
`prototype_repaired_select_only_compact_cluster_selected_phi_incoming_materialization_failure_clear`,
`visited_candidate_count=48`, `slot_out_of_range_count=24`, and
`missing_cfg_block_count=0`. The historical next step was
`wire_cfg_clone_runtime_entry_dispatch_before_selected_phi_store_site_compare`:
keep the post-replay selected-PHI value compare and store-site diagnostic
atomics live in optimized GPU IR/runtime before using the materialized value as
selected-value or actual-valid evidence.

The non-diagnostic baseline split is now an explicit workflow entrypoint:
`src/tools/build_vl_gpu.py --disable-cfg-clone-diagnostics` tells `vlgpugen`
to omit compact CFG-clone counter/shadow diagnostic IR, and
`RUN_VL_HYBRID_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI=1` keeps the ordering-aware
token-loop runtime from allocating or passing those diagnostic buffers. This is
only a baseline-isolation mechanism; guarded/liveout CPU-oracle validation still
requires the normal diagnostic build and must not set the runtime disable env.

External testbench candidate smoke:

```sh
git clone --depth 1 https://github.com/fguzman82/gateGPT.git artifacts/external_gateGPT
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir artifacts/external_gateGPT \
  --run-verilator-lint \
  --run-local-normalized-testcases \
  --run-gpu-smoke \
  --write-report \
  --report-out reports/gategpt_testbench_probe.json
```

To rerun only the current selector-counter evidence gate without the full GPU
smoke sweep:

```sh
python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir artifacts/external_gateGPT \
  --run-gpu-selector-counter-smoke \
  --selector-counter-state-count 2 \
  --gpu-jobs 2 \
  --write-report \
  --report-out reports/gategpt_selector_counter_smoke.json
```

To rerun the current FC-069 ordering-aware full-logical-phase gate, use the
narrow CLI path below. It forces `loop_chunk=1701` and avoids the full gateGPT
GPU smoke sweep, but still records non-claims for speedup, usefulness, and broad
gateGPT PASS/FAIL authority.

If the full-phase preflight reports
`ordering_aware_full_phase_preflight_passed`, regenerate the
entry-sliced PTX/CUBIN chain after the full-phase PTX build. The full-phase
probe has an opt-in flag for this because the preflight rebuilds
`obj_tb_core/vl_batch_gpu.ptx` before checking the CUBIN chain:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir artifacts/external_gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 2 \
  --regenerate-ordering-aware-entry-sliced-cubins \
  --ordering-aware-entry-sliced-ptxas-timeout-seconds 600 \
  --gpu-jobs 2 \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state.json
```

The standalone regeneration command below writes the same generated chain and a
separate evidence report. It is useful for diagnosing slice contents, but the
full-phase preflight still needs the opt-in flag above if it rebuilds
`vl_batch_gpu.ptx` first.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/gategpt_entry_sliced_cubin_chain.py \
  --repo-root . \
  --ptx artifacts/gategpt_local_eval/gateGPT/obj_tb_core/vl_batch_gpu.ptx \
  --out-dir artifacts/gategpt_tb_core_ptx_entry_slice \
  --ptxas-timeout-seconds 300 \
  --write-report \
  --report-out reports/gategpt_tb_core_entry_sliced_cubin_chain_regeneration.json
```

The matching 16-state scale command changes only the state count and report
path:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/gategpt_testbench_probe.py \
  --repo-dir artifacts/external_gateGPT \
  --run-gpu-ordering-aware-full-phase-smoke \
  --ordering-aware-state-count 16 \
  --gpu-jobs 2 \
  --write-report \
  --report-out reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_16state.json
```

Historical full-phase pass evidence was narrow: manifest status
`gategpt_gpu_ordering_aware_full_phase_probe_passed`, nested status
`ordering_aware_full_phase_probe_passed`, `ordering_aware_loop_chunk=1701`,
`ordering_aware_full_logical_phase_chunk=true`, `runtime_supported=true`,
the historical runtime-correctness flag set, and
`source_probe_comparison.state_count == passed_count == target_state_count`
with `mismatch_count=0`. The current FC-073 diagnostic attempt is instead recorded at
`reports/gategpt_tb_core_ordering_aware_token_loop_full_phase_2state_stage117_light_block_body_boundary_range_1_2048_ptxas900_runtime.json`; it is a Stage117 boundary probe that finds dirty block-body boundary `source_id=1760` with `same_saved_addr_changed`, after the prior `COUNT=1024` clean result. It is not a runtime-correctness pass or final adjacent-window write-source authority. The older
entry-sliced CUBIN module-load/symbol preflight passes and CPU oracle generation
passes. The runtime command consumes the actual ordering-aware lowering plan,
not the padded-start runtime plan. The first-launch diagnostic is observed with
`low_count=6`, `high_count=6`, `cycle_count=2701`, `phase_control_count=76`,
`feedback_copy_count=5`, `feedback_increment_count=2`,
`terminal_mask_count=2`, `eval_predicate_count=282`,
`cfg_clone_shadow_descriptor_count=268`, and all required device table pointers
present. The first full 1701-cycle ordering-aware token-loop launch now fails
inside the opt-in post-launch sync diagnostic with `cuda_result=700`,
`cuda_error=CUDA_ERROR_ILLEGAL_ADDRESS`. The previous `stage=0` / `cycle=0`
visibility boundary has since been cleared by same-module progress-global
initialization; refreshed progress now reaches `stage=77` / `cycle=27`.
Record `318` still maps to expected pair-offset address `81654729712`, where
host/upload/pair/pre-token authority reads offset `0`. The token-loop load reads
`38666621`, and the stage77 tuple shows that value flows into the storage GEP:
`storage_base=81654710272`, `high_dst_addr=81693376893`,
`high_dst_delta=38666621`, and `loaded_offset_oob_by_kernel=1`. That older
stage77 boundary has since been superseded by the FC-073 Stage95 host-side
event labels: record `318` is clean after schedule upload and at phase 1
`pre_token_loop_launch`, but phase 1 `post_token_loop_sync` already observes
uploaded/pair/pre-token offset `38666621`; phase 2 pre-launch inherits that
polluted value before CUDA700. The active classification is now
`token_loop_stage96_phase1_post_sync_multi_record_offset_table_pollution`, so
correctness or timing stays blocked until the successful phase 1 token-loop
launch write/alias path into the pair-offset table is explained.

The accepted gate keeps `sim/tb_mathops.v` as the raw-checkout Verilator
lint-only smoke, then creates an evaluation-only copy under
`artifacts/gategpt_local_eval/gateGPT`, normalizes upstream absolute
`/home/hermes/microgpt_fpga` include/readmem paths in that copy, adjusts the
`tb_exp` generated-data depth in that copy, and runs `tb_mathops`, `tb_exp`,
`tb_matvec`, `tb_norm`, `tb_attn`, and `tb_core` as Verilator binary
testcases. With `--run-gpu-smoke`, the same generated obj_dirs are lowered
through the current LLVM GPU path and each generated PTX module is launched once
with zero-initialized state. That smoke proves PTX build and kernel launch only;
it does not reproduce the gateGPT testbench initial blocks, `$readmemh` setup,
clock loops, `$display` PASS/FAIL checks, or `$finish` authority on GPU. The
checkout has no license file, so it is not vendored as source. This is local CPU
Verilator testcase evidence plus a GPU kernel-launch smoke, not speedup,
usefulness, arbitrary RTL support, or gateGPT PASS/FAIL equivalence evidence.
The first semantic-equivalence candidate is `tb_mathops`: the CPU authority is
`errors == 0`, while the generated C++ uses coroutine/timing scheduler code plus
`VL_WRITEF_NX` and `VL_FINISH_MT`. The generated report now includes a
`tb_mathops` field-offset manifest for selected drive/observe fields, including
`errors`, `d_quo`, and `s_root`, and uses it for a full `tb_mathops` DUT-output
sequence compare: all six divider cases and seven square-root cases match their
CPU reference values. Current LLVM passes can emit PTX and byte-patched DUT
sequences can run. For this selected testcase only, the accepted PASS policy is
now the manifest-consuming DUT-output compare with final `errors == 0`; it does
not claim stdout PASS/FAIL export or `$finish` export. General gateGPT still
needs GPU output manifests or stdout/finish observables before broader PASS/FAIL
equivalence, batching, speedup, or usefulness can be claimed. The probe now also
extracts a CPU Verilator stdout/finish authority manifest for all six normalized
benches. That manifest records PASS lines and `$finish` lines for all six
benches, preserves `tb_core` structured stdout lines such as tokens and cycle
summaries, and marks the data-backed benches as needing readmem/init-state
contracts. `tb_exp`, `tb_matvec`, `tb_norm`, and `tb_attn` now have those
contracts. It is a CPU authority manifest only; GPU
stdout/finish export and a general GPU output manifest remain unclaimed. The
follow-up mapping plan is now explicit: `tb_mathops` is covered by the selected
DUT-output policy, and `tb_exp` is covered by a bench-specific vector-sequence
DUT-output compare. `tb_matvec`, `tb_norm`, and `tb_attn` are now covered by
bench-specific vmem output sequence compares. `tb_core` is now covered by a
bench-specific structured root-state sequence compare for token and cycle lines.
All six normalized gateGPT benches now have bench-specific GPU output manifests;
general stdout/finish export and throughput usefulness remain unclaimed. A
`tb_exp` replicated-state batching timing probe has also been run with the same
103-case vector scenario copied across `nstates=1,32,256`. Kernel time per state
improves from `16.966656 ms` to `0.56204803125 ms` to `0.084064 ms`, with the
best per-state result at `nstates=256` and a `201.83022459078796x` per-state
kernel improvement versus `nstates=1`. That is launch-amortization evidence for
identical replicated states only; it explicitly does not claim mixed-scenario
batching, semantic equivalence, speedup, or usefulness. A minimal state-indexed
patch ABI is now available as `@state:local_offset:byte`, and the first
distinct-state `tb_exp` probe passes: 103 different `z` inputs are run as 103 GPU
states in one 2-step clock sequence, 103/103 reconstructed outputs match, and
the latest nonresident sample records `gpu_kernel_total_ms=3.639296` and
`wall_time_ms=13.266`. The resident variant now runs the same patch script with
`--resident-steps`, uploads `412` patch records once as a device-resident
schedule, matches 103/103 outputs, and records
single-sample `gpu_kernel_total_ms=0.951296`, `wall_time_ms=0.99`. The resident
repeat-median gate now passes 7/7 samples with `wall_time_ms_median=0.93` and
`gpu_kernel_total_ms_median=0.887808`. The matching CPU Verilator process-wall
baseline now has 7/7 passing samples with `median=28.96515399334021 ms`. The
resident repeat-median observed GPU wall ratio versus CPU is
`31.145326874559363x`, but
speedup/usefulness remain unclaimed until resident coverage is broadened beyond
this narrow two-step `tb_exp` path. The first
concrete data-backed manifest is now `tb_exp`: the probe identifies
`generated/test_exp_z.hex` and `generated/test_exp_e.hex` as 103-entry signed
16-bit arrays, maps them to `tb_exp__DOT__zs` and `tb_exp__DOT__es`, and records
the drive/observe fields needed for a GPU vector-sequence compare. That
sequence now passes as a bench-specific GPU DUT-output compare: all 103 cases
match the CPU reference, with `semantic_equivalence_claimed=true`. The direct
`eo` signal is not available in the root state, so the probe reconstructs it from
`pos_r`, `big_r`, and `interp`. The LLVM pass path now keeps top-level phase
closures for root images and preserves trigger-bearing act phases, which gives
the called `tb_exp` posedge/NBA sequence complete GPU IR definitions. This is
still not general gateGPT PASS/FAIL equivalence because stdout PASS lines and
`$finish` are not exported as GPU execution authority.
The next covered data-backed bench is `tb_norm`: the probe maps
`generated/test_norm_in.hex` into `tb_norm__DOT__u_vmem__DOT__mem[0..23]`, runs
one explicit reset/start/clock sequence, and compares
`tb_norm__DOT__u_vmem__DOT__mem[64..87]` with `generated/test_norm_out.hex`.
That GPU vmem sequence passes 24/24 outputs, observes `n_done`, and still makes
no stdout PASS/FAIL or `$finish` export claim.
`tb_matvec` follows the same vmem contract pattern: the probe maps
`generated/test_in.hex` into `tb_matvec__DOT__u_vmem__DOT__mem[0..23]`, runs one
explicit reset/start/clock sequence, and compares
`tb_matvec__DOT__u_vmem__DOT__mem[64..87]` with `generated/test_wq.hex`. That GPU
vmem sequence passes 24/24 outputs, observes `mv_done`, and still makes no
stdout PASS/FAIL or `$finish` export claim.
`tb_attn` uses the same explicit-init pattern with three vmem input windows:
`generated/test_attn_q.hex` maps to `vmem[0..23]`, `test_attn_k.hex` maps to
`vmem[32..415]`, and `test_attn_v.hex` maps to `vmem[448..831]`. The GPU run
observes `a_done` and compares `tb_attn__DOT__u_vmem__DOT__mem[864..887]` with
`generated/test_attn_out.hex`; 24/24 outputs match, with no stdout PASS/FAIL or
`$finish` export claim.
`tb_core` maps the structured stdout authority to root-state observables:
`next_token`, `rng_out`, `cyc`, `reported`, `tot_cyc`, and `tot_tok`. The probe
runs one GPU launch per generated token, carries the dumped state through
`--init-state`, feeds sampled `rng_out` into the next `rng_in`, and compares the
greedy tokens `1 12 1 25 1`, sampled tokens `18 15 19 16 8 15 4`, and cycle
summary `CYCLES_PER_TOKEN=1157`, `AVG_CYCLES=1322 over 12 tokens (last=1489)`.
That structured sequence passes, but the nonresident path uses 14 launches and
47,656 logical steps with `gpu_kernel_total_ms=4367.203339`,
`wall_time_ms=4373.235`, so it is correctness evidence only. A resident
multi-step variant now passes the same token/cycle comparison with the same 14
token transactions and 47,656 logical steps, reducing the measured kernel total
to `816.12083 ms` and wall time to `816.915 ms`. This proves resident
multi-step scheduling can cover the current `tb_core` token transaction shape,
but it still does not claim speedup or usefulness. The next runtime/LLVM
boundary is recorded as `tb_core_persistent_resident_multitoken_abi_gap`:
persistent resident multi-phase mode now reuses device-resident patch schedules,
`vl_apply_feedback_edges_gpu`, `vl_apply_feedback_increments_gpu`, and
`vl_apply_feedback_sets_gpu` are now generated and annotated as NVVM kernels,
and `vl_apply_feedback_combined_gpu` is available for fused edge+increment
feedback.
The runtime smoke-tests table upload/launch for `next_token -> token_in`,
four `rng_out -> rng_in` byte lanes, `pos_in += 1`, and phase-set
`start/smode/inv_temp` controls with `5` feedback edges, `1` increment,
`8` phase-set records, one combined edge+increment launch, zero separate
edge/increment launches, and two phase-set launches
(`gpu_kernel_total_ms=0.982016`, `wall_time_ms=1.020`). This smoke now includes
`@0:phase:offset:value` state-indexed phase-set records, so parser, C upload,
and GPU set-kernel ABI coverage exists for the one-state case. Phase-set writes
remain separate to preserve per-phase ordering; a fully fused
phase-set/copy/increment attempt is not the accepted path. The full persistent
resident feedback smoke now runs the greedy and sampled `tb_core` token sequence
without host state-dump handoff: observed tokens `[1, 12, 1, 25, 1, 0, 18, 15,
19, 16, 8, 15, 4, 0]` match the expected delimiter-inclusive sequence, the
cycle checkpoint matches `reported=12`, `tot_tok=12`, `tot_cyc=15871`,
`last_cycle=1489`, and the run uses `13` combined feedback launches plus `14`
phase-set launches over `68` phase-set records. The corresponding 7/7
repeat-median gate records `gpu_kernel_total_ms_median=767.118103` and
`wall_time_ms_median=767.173`, which is `5.700454786599632x` observed wall
improvement versus the nonresident structured path and `1.064838048262908x`
versus resident multi-step. A matching CPU Verilator process-wall baseline now
passes 7/7 with `wall_time_ms_median=22.265211009653285`; the full feedback GPU
wall ratio versus that CPU baseline is only `0.029022412167338116x`, so this
single-scenario `tb_core` GPU path is about `34.5x` slower than CPU process-wall.
The slowdown breakdown records `47,642` logical GPU launches and `95,311` actual
timed launches, while feedback helper launches are only `27`, about
`0.000283283146751162` of actual launches. The opt-in pair-cycle-loop follow-up
preserves the same `tb_core` token/cycle contract and collapses actual timed
launches to `69` with `14` loop kernels over `23,814` low/high cycles. Its 7/7
repeat median is `432.562866 ms` kernel / `432.609 ms` wall, a
`1.7733634760256953x` GPU-wall improvement versus full feedback. It is still
`19.429818105583568x` slower than the CPU process-wall baseline. A replicated
`nstates=1,8,32` follow-up now preserves pair-cycle-loop eligibility by
replicating the state0 resident patch schedule across state strides: all three
runs keep actual timed launches at `69`, and the best per-state kernel result is
`nstates=32` at `18.3382225 ms/state`, a `23.557655274386597x` improvement
versus `nstates=1`. The probe now compares all replicated state phase dumps:
`nstates=8` passes `8/8` states and `nstates=32` passes `32/32` states with zero
token/cycle mismatches. This is still same-scenario replicated correctness only;
mixed-scenario batching, speedup, and usefulness remain unclaimed for the
replicated-state gate. A distinct-state `tb_core` full-sequence phase-set probe
now runs greedy and sampled sequences concurrently as two GPU states:
state0 observes `[1, 12, 1, 25, 1, 0]`, and state1 sampled seed `2` observes
`[18, 15, 19, 16, 8, 15, 4, 0]`, with 2/2 states passing and zero mismatches.
It uses `8` state-indexed phase-set launches, `7` combined feedback launches,
`76` phase-set records, `27,224` logical launches, and `54,463` actual launches
without loop collapse (`gpu_kernel_total_ms=471.468170`,
`wall_time_ms=471.533`). The pair-cycle-loop follow-up preserves the same
two-state token contract and now has a 7/7 repeat median: `286.213837 ms` kernel /
`286.254 ms` wall, with `47.0` actual launches, `27,224.0` logical launches,
`8.0` loop kernels, `13,600.0` looped low/high cycles, and `8.0`
phase-boundary fallbacks. Compared with the CPU Verilator process-wall median
`23.23766698827967 ms`, the observed GPU wall ratio is only
`0.08117848829459036x`, so this two-state GPU path is about
`12.31853439264696x` slower than CPU. The many-independent seed matrix now has
CPU token oracles for all `16` target states, with zero validation mismatches:
`greedy` and `sampled_seed2` keep reviewed golden provenance, while
`sampled_seed3` through `sampled_seed16` are generated by the CPU Verilator
oracle bench. The 16-state GPU batch now passes 7/7 repeat-median samples with
`trim_final_low=true`: 16/16 token streams match, median GPU time is
`393.967987 ms` kernel / `393.999 ms` wall, with `35.0` actual launches over
`30,618.0` logical launches. Compared with the CPU oracle executable wall
`84.66219899128191 ms`, GPU wall speedup is only `0.2148792230215861x`, so GPU
remains `4.653777065731213x` slower. Launch-structure analysis accounts for all
`35` actual launches (`9` phase-set, `8` combined-feedback, `9`
pair-cycle-fusion, and `9` pair-cycle-loop kernels), leaving `0` residual
launches and `0.0` residual launches per fallback. This proves many-independent
token-sequence batching for the seed matrix and removes the final-low residual
launch gap, but cycle summary authority, stdout/PASS/$finish, speedup, and
usefulness remain unclaimed. A hold-start diagnostic drops actual launches to
`26` by eliminating the `9` pair-cycle-fusion launches, but all `16` token streams
mismatch, so holding `start` high is rejected. A padded-start diagnostic keeps
the one-cycle start pulse, passes 7/7 repeats with 16/16 token streams matched,
and reduces the structure to `26` actual launches with `0` pair-cycle-fusion
launches and `0` loop fallbacks. Its median is `366.163605 ms` kernel /
`366.21 ms` wall, a `1.0758826902596872x` wall improvement over the standard
35-launch path, but still `4.325543210113294x` slower than CPU. The padded-start
rule is now represented as an importable schedule planner helper in
`src/tools/gategpt_schedule_planner.py`, including the runtime-facing env,
required entrypoints, and expected lower-launch shape. The current generated
plan artifact is
`artifacts/gategpt_local_eval/gateGPT/obj_tb_core/tb_core_many_independent_padded_start_lowering_plan.json`;
`run_vl_hybrid.py --schedule-lowering-plan` now validates and consumes that
artifact as the runtime env source for the padded-start probe, and the planner
now generates the schedule-lowered `run_vl_hybrid` argv. The generated
`vl_batch_gpu.meta.json` now exposes
`schedule_lowering_capabilities.padded_start_pair_cycle_loop` as `available`
with no missing runtime entrypoints. The 7-repeat CPU comparison now claims only
the lower-launch gate. The generated
`tb_core_padded_start_cpu_negative_gap_decision` report is
`mapping_structure_change_recommended`, so the next work is a different
runtime/mapping structure rather than another narrow LLVM helper-kernel tweak.
The generated `tb_core_runtime_mapping_structure_candidate_plan` is
`ready_for_runtime_mapping_design` and ranks
`ordering_aware_phase_resident_token_loop` first; GitHub #69 tracks that
prototype. Its prototype contract now validates as planning evidence and targets
`phase_set=0`, `combined_feedback=0`, `pair_cycle_loop=0`, and one
`ordering_aware_token_loop` launch before any speedup/usefulness claim. Current
build metadata now reports `vl_tb_core_ordering_aware_phase_resident_token_loop_gpu`
as available, and the generated kernel body now consumes `current_phase`,
phase-control records, feedback copy/increment records, and terminal-mask
records around the
pair-cycle loop. The latest ordering-aware run now consumes the #69 lowering
plan through the schedule-owned token-loop path with `runtime_supported=true`.
It passes the source CPU-token-oracle comparison for `16/16` states, uses `9`
actual ordering-aware launches over `30,618` logical launches, and suppresses
the separate helper launch classes: `feedback_phase_sets=0`,
`feedback_combined=0`, `pair_cycle_loop_fusion=0`, and
`resident_pair_cycle=0`. Runtime summary:
`entrypoint_available=true`, `phase_control_records=672`, `feedback_copy_records=5`,
`feedback_increment_records=1`, `pair_cycle_loop_records=1701`,
`terminal_mask_records=16`, `terminal_mask_device_records=16`,
`terminal_mask_parse_errors=0`, `launch_probe_count=9`, and
`device_table_launches=9`, with
`blocking=ordering_aware_token_loop_schedule_integrated_cpu_comparison_pending`.
The
ordering-aware lowering plan artifact now records the ABI-probe env and
per-state terminal mask at
`artifacts/gategpt_local_eval/gateGPT/obj_tb_core/tb_core_ordering_aware_token_loop_lowering_plan.json`.
`run_vl_hybrid.py --schedule-lowering-plan` now consumes this shape; the older
`--allow-ordering-aware-token-loop-probe-plan` remains only as a compatibility
debug flag. The C runtime parses, validates, canonicalizes, and uploads terminal masks as device-side
`state:terminal_step` records, and the generated kernel now uses a direct state-indexed
terminal-mask fast path with an order-tolerant fallback before gating active phases
and final feedback. Earlier ordering-aware normal-eval probe status was
`passed` with source-probe and runtime-correctness flags set, but that is historical timing evidence; the current FC-073 Stage124 probe remains diagnostic-only and claims no runtime correctness. The CPU comparison for the older normal-eval path was still negative:
	GPU wall is `363.628 ms` / GPU kernel is `363.59198 ms` versus CPU oracle wall `81.95496001280844 ms`, so the
	ordering-aware path with the normal eval select-mux transform is
	`4.436924866331091x` slower than CPU. The normal eval reachable closure now has
`normal_eval_transform_present=true`, `normal_eval_rewritten_select_count=2344`,
and `transform_rewritten_select_count=2688`, with
`implementation_stage=normal_select_mux_cluster_transform_measured_cpu_negative`.
The select-mux transform now runs before eval hot-path partitioning, and the
post-select-mux partition stage is measured with
`eval_hot_path_partition_after_select_mux_transform_present=true` and
`eval_hot_path_partition_count=2580`.
The guarded bitmap trial now uses a partition-indexed active bitmap
(`mode=phase_state_partition_bitmap`, `active_bitmap_partition_count=23`,
`active_bitmap_phase_count=20`, `active_bitmap_device_bytes=2080`) and also
	passes the 16/16 CPU token oracle, but records `354.541 ms` GPU wall /
	`354.494232 ms` GPU kernel and is still `4.326046891421703x` slower than CPU,
so it is not a speedup. The previous guarded launch
failure was stale host-runtime ABI, now covered by rebuilding
`artifacts/tool_bins/hybrid/run_vl_hybrid` when `src/hybrid` inputs are newer.
`speedup_claimed=false` and `usefulness_claimed=false`; at that guarded-bitmap
stage the next concrete gate was
`isolate_entry_dispatch_cfg_clone_memory_reads_before_wiring`,
but cold partition skip safety reports `13` inspected continuations, `0`
skip-safe candidates, and `13` rejected continuations
(`successor_phi_depends_on_continuation_edge=11` and
`terminator_not_unconditional_branch=2`), so simple LLVM guard insertion is
insufficient.
The first concrete refactor is
`outline_partition_region_before_phi_join_or_split_successor_phi_edges`,
followed by
`outline_multi_successor_partition_region_or_normalize_continuation_terminator`;
the LLVM pass now reports this first refactor as `8`
`select_only_phi_edge_region` cases before `3`
`effectful_memory_phi_edge_region` cases, with `2`
`multi_successor_continuation` cases for the second refactor.
The select-only outline preflight records `8` regions with `832` selects,
`1344` successor-PHI edges, `832` local live-out values, and `512`
external-or-constant incoming values; this is implementation planning evidence,
not guard authority or timing evidence.
The pass now inserts `8` select-only PHI repair blocks, moving `832` selects and
retargeting `1344` successor-PHI edges; this is CFG repair evidence only, not
partition-aware skip authority.
Post-repair static safety classification now records `8` inspected repaired
select-only continuations, `8` candidates, and `0` rejected; this narrows the
next guarded-skip prototype but still grants no skip authority.
after those partition-local regions exist, apply the repaired select-only current
partition-id context as the guarded-scan partition match instead of remeasuring
the already measured select-mux-after-partition stage. The generated
`tb_core_ordering_aware_cpu_negative_gap_decision` then recorded
`status=ordering_aware_cpu_negative_gap_measured`: helper launches are already
suppressed, launches fell by `17` versus padded-start (`0.6538461538461539`),
but wall improved only `1.0604264497337874x` versus padded-start. The requested `decompose_ordering_aware_kernel_body_cost_and_state_scale` follow-up is now represented by stage timing, the state-scale sweep, and opt-in device-side diagnostic region counters: `before_final_sync=360.61 ms` dominates the measured wall path, so more helper-launch removal is not the next lever. The standard CPU comparison remains bound to the 16-scenario oracle; the 32-state sweep row uses a separately generated 32-scenario CPU oracle. The new 4/8/16/32-state ordering-aware sweep records
`273.035736 ms`, `324.181793 ms`, `359.070801 ms`, and `402.972504 ms` kernel time respectively,
or `68.258934`, `40.522724125`, `22.4732570625`, and `12.59289075 ms/state`. State scaling is
helping by `5.420434065149021x` from 4 to 32 states, but the 16-state wall is
still `4.30538043208457x` slower than CPU and the 32-state wall is still
`2.710562354615603x` slower than its 32-scenario CPU oracle. Static IR
classification of `vl_tb_core_ordering_aware_phase_resident_token_loop_gpu`
now records `24` basic blocks and `137` LLVM instructions with the expected
`terminal.mask`, `phase.set`, `cycle`, `low.patch`, `high.patch`, and `feedback`
regions. Static region breakdown is recorded as a non-timing proxy, and the opt-in timing variant records diagnostic gid0 clock64 counters for the 16-state baseline: cycle_body `4884742382`, high_eval `3629021127`, low_eval `1216414868`, low_patch `21611907`, high_patch `14785139`, phase_set `881773`, terminal_mask `9294`, and feedback `18574`; the 32-state normal row remains CPU-negative at `403.039 ms` wall versus a `148.6920230090618 ms` 32-oracle CPU wall. The direct eval callee has `65` counted LLVM instructions; its largest direct call is `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root` at `11593` counted instructions, `1777` basic blocks, `2670` loads, `556` stores, and `1758` branches. Its refined structural decomposition shows two largest LLVM basic blocks at `694` instructions each, a third at `339`, `select=2149`, `switch=17`, no `phase` keyword hits, and only `start=2`; the analyzer now marks this as `start_only_guard_evidence_present` with `weak_for_phase_guard_partition`. The eval direct-call finding classifies that NBA sequential body as `poor_for_narrow_peephole_pass` and recommends `structural_eval_partition_or_larger_state_scale`; the concrete next experiment is now `measure_memory_vs_select_cluster_partition`; static clusters are `load_store_heavy=3182` instructions and `select_mux_heavy=1352` instructions, with partition gate `ready_for_static_partition_probe`, `memory_select_instruction_count=4534`, and `memory_select_fraction_of_function=0.39109807642542915`, with lane priority `memory_heavy_root_state_lane` -> `select_mux_lane` -> `branch_control_lane`; the memory lane contract targets `isolate_or_instrument_load_store_heavy_basic_blocks` with candidates `measure_memory_cluster_clock64_region`, `prototype_hot_root_state_field_grouping`, and `prototype_memory_cluster_outline_or_split`, so it should not be treated as a small LLVM peephole target. The runtime partition measurement contract has advanced to `runtime_cluster_counters_present`: `memory_cluster`, `select_mux_cluster`, optional `branch_control_cluster`, active-path BB discovery, and select-mux scoped hook counters are emitted through the 16-slot region timing ABI. The companion cluster counters still use `all_threads_atomic_clock64_sum`, while the select-mux scoped hook now uses `representative_thread_non_atomic_clock64_sum`. The current 16-state token-loop run observes `memory_cluster=481050879`, `select_mux_cluster=1405771525`, `branch_control_cluster=0`, `active_eval_basic_blocks=79885598`, `active_memory_candidate_blocks=600894`, `active_select_candidate_blocks=387828`, `select_mux_scoped_cycles=73818337`, and `select_mux_scoped_blocks=20412`; the scoped values are intentionally representative-thread values and no longer match the all-thread select-mux cluster sum. Select-mux is `2.922292810112504x` memory-cluster cycles, and memory+select accounts for `0.4054252889390992` of cycle-body cycles. The prior ABI, zero-signal, scoped-atomic, lowering-candidate-metadata, and normal-vs-diagnostic-kernel-isolation blockers are gone. A clone-only identity select rewrite is applied inside select-mux-heavy region-timing eval clones (`transform_present=true`, `transform_rewritten_select_count=2`), and the normal eval reachable closure now has eval hot-path partition markers (`eval_hot_path_partition_present=true`, `eval_hot_path_partition_count=2580`) plus active-block gate markers (`eval_hot_path_active_block_gate_present=true`, `eval_hot_path_active_block_gate_count=53`). The eval hot-path partition prototype marks 1580 split continuation blocks, active-block gate markers are present (`eval_hot_path_active_block_gate_present=true`, `eval_hot_path_active_block_gate_count=53`), cold partition skip safety classification is now present (`eval_hot_path_cold_partition_skip_present=true`, `eval_hot_path_cold_partition_skip_candidate_count=0`, `eval_hot_path_cold_partition_skip_rejected_count=23`), and the phase/state/partition predicate table is authoritative via `RUN_VL_HYBRID_EVAL_PARTITION_PREDICATES` / `eval_partition_predicates:` with `active_mask_authority=true`; direct eval callee/call-site predicate-pointer markers are present via `vlgpu.direct_eval_predicate_pointer_abi` / `vlgpu.eval_predicate_pointer`. This remains lowering-hook/ABI plumbing evidence, not speedup timing, usefulness evidence, or safe skip authority. The current guarded skip has a partition-indexed active bitmap, so `active_bitmap_index_omits_partition_id` is no longer a blocker; the broad partition-aware skip gaps are that the kernel guard skips whole eval calls rather than partition continuations and the continuations are not skip-safe for simple guard insertion; the active compact-cluster implementation gap is runtime outline wiring after the single-entry CFG clone probe. Direct terminal-mask lookup and patch-record invariant division/base hoisting are now implemented with fallback/hoisted IR evidence; remaining LLVM/lowering candidates are phase/state partitioning for phase-control records. Structural candidates are eval-callee hot-path analysis,
expanding beyond 32 independent states, or a multi-phase resident sequence kernel.
The phase/state/partition predicate table is authoritative through `RUN_VL_HYBRID_EVAL_PARTITION_PREDICATES` and the `eval_partition_predicates:` stdout contract with `active_mask_authority=true`; direct eval callee and call-site predicate-pointer markers are present through `vlgpu.direct_eval_predicate_pointer_abi` and `vlgpu.eval_predicate_pointer`. The diagnostic path still validates 16/16 CPU token oracles and reached CFG-clone liveout capture points with mismatch_count=0. The non-diagnostic `obj_tb_core_nondiagnostic` artifact builds with `--disable-cfg-clone-diagnostics`, and `RUN_VL_HYBRID_DISABLE_CFG_CLONE_DIAGNOSTIC_ABI=1` suppresses matching runtime allocations/arguments. The same-CPU-oracle baseline remains CPU-negative. No broad partition-aware skip, speedup, or usefulness is claimed. This older continuation action, the later stage0/cycle0 progress-visibility gate, the token-loop load-propagation diagnostic action, and the closure-wide Stage110 ptxas-cost gate have been superseded; Stage111 narrows the record `318` write boundary to nested call `_Z40Vtb_core___024root___nba_sequent__TOP__0P18Vtb_core___024root`, Stage112 ranges `1..13134`, Stage113 direct deeper-call boundaries, Stage114 design-origin non-store effects, Stage116 CFG-edge boundaries, Stage117 block-body boundary `source_id=1760`, and Stage118 intrablock candidates through `2021` are narrowed/clean but not final write-source authority. Extended Stage119 maps the dirty residual to `compact.cfg_clone.entry_phi.producer_selector.counters3969`; Stage120 per-instruction ranges are clean/exhausted, Stage121/122/123 classify the producer-selector frontier as diagnostic/lifecycle traffic, and Stage124 has reached source1058 with no transition under source976/source1006/source1020 suppression. Source1058,count1 also reaches runtime under the source976/source1006/source1020 suppression frontier with result=after_only_polluted, transition_complete=true, scan_complete=true, transition_found=false, semantic_authority=false, write_source_authority=none, before/after record318=0/38666621, pair_offsets_base_changed=false, and CPU oracle mismatch_count=2/passed_count=0. The current FC-069 next concrete action is `advance_stage124_source1065_after_sources976_1006_1020_diagnostic_atomic_suppression_cuda700`.

LLVM IR suitability analysis is available as a static review/debug surface:

```sh
python3 src/tools/llvm_rtl_gpu_suitability_cli.py \
  --ir <lowered.ll> \
  --entry <function> \
  --target <target-or-design> \
  --workload <case-label> \
  --shape 64x1
```

The JSON reports whether the IR looks like `good_state_parallel`,
`poor_requires_new_implementation`, or an uncertain definition gate, with
branch density, memory regularity, state independence, and observable pressure
metrics. This is not GPU execution, correctness equivalence, runtime ABI, timing
evidence, or a speedup/usefulness claim.

For the FC-065 lowered-IR corpus gate, use the same CLI with `--write-report`
and keep generated reports under `reports/` or another generated-output path:

```sh
clang++-18 -std=c++20 -S -emit-llvm -O1 \
  <source.cpp> -o artifacts/<case>/<case>.ll

python3 src/tools/llvm_rtl_gpu_suitability_cli.py \
  --ir artifacts/<case>/<case>.ll \
  --entry <function> \
  --target <target-or-design> \
  --workload <case-label> \
  --shape <NxS> \
  --write-report \
  --report-out reports/<case>_llvm_rtl_gpu_suitability.json
```

Those reports are reproducible static suitability evidence only; they are not a
new source of truth and do not authorize sidecar execution.

When `--entry` is supplied, the analyzer includes defined LLVM callees reachable
from that entry before computing metrics. This avoids treating a thin `_eval`
wrapper as suitable when a reachable helper carries branch, observable, or
volatile pressure. The JSON also reports external calls and LLVM intrinsic
calls seen in that reachable region so side-effect pressure is reviewable.

The suitability JSON can be passed to the conservative FC-045 policy helper in
`src/tools/gpu_sidecar_eligibility_policy.py`. That helper emits
`recommended_action` metadata for review: `64x1` state-parallel cases remain
correctness/UX smoke until larger-batch evidence exists, poor design-CPU cases
route to CPU-parallel or new-mapping work, and unreviewed source closures fail
closed. The helper consumes debug JSON only; it does not make the JSON a runtime
ABI or execution authority.

```sh
python3 src/tools/gpu_sidecar_eligibility_policy_cli.py \
  --suitability-report reports/<case>_llvm_rtl_gpu_suitability.json \
  --source-closure-status reviewed \
  --write-report \
  --report-out reports/<case>_gpu_sidecar_eligibility_policy.json
```

The contract gate also exercises the same clang emit-LLVM shape through the
existing `build_vl_gpu_compile.compile_ll` helper, so the regeneration path is
closer to the repository build flow without committing generated `.ll` files.

Scientific-compute candidates can be staged for a future CIRCT-to-SystemVerilog
path with a plan-only helper:

```sh
python3 src/tools/scientific_circt_gpu_candidate_plan.py \
  --write-report \
  --report-out reports/scientific_circt_gpu_candidate_plan.json
```

The plan ranks regular-memory, low-observable candidates such as dense matmul
tiles, stencil tiles, reductions, and exp/softmax pipelines before branch-heavy
sparse/control workloads. Each candidate records the intended path:
CIRCT input, generated SystemVerilog, Verilator build, lowered LLVM IR
suitability, then repeat-median CPU/hybrid measurement. If no CIRCT executable
is on `PATH`, the plan fails closed with `blocked_circt_toolchain_missing`.
This is not CIRCT execution, generated RTL evidence, Verilator success, GPU
execution, correctness equivalence, timing, or a speedup/usefulness claim.

With a CIRCT toolchain on `PATH`, the first candidate can now be materialized
and checked through Verilator CPU reference:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_dense_matmul_tile.py \
  --run-circt \
  --run-verilator-cpu \
  --write-report \
  --report-out reports/scientific_circt_dense_matmul_tile_materialize.json
```

The generated FIRRTL, SystemVerilog, harness, Verilator `obj_dir`, and lowered
LLVM IR remain generated artifacts under `artifacts/scientific_circt/`. The
current CPU reference gate is only a correctness entry point for the scientific
lane; it is not GPU execution, hybrid timing, speedup, or usefulness evidence.

The first scoped CUDA timing gate compares the same 2x2 tile computation as a
batched state-parallel workload:

```sh
python3 src/tools/scientific_circt_dense_matmul_tile_gpu_timing.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_dense_matmul_tile_gpu_timing_1024x1.json
```

Current scoped measurements with `inner_repeat=1000` show the expected boundary:
`64x1` is still CPU-favorable end-to-end because transfer/launch overhead
dominates, while `256x1` and `1024x1` become GPU-favorable end-to-end. Kernel
time alone is faster at all three measured shapes. This is evidence for the
`dense_matmul_tile` candidate only, not a general RTL speedup claim.

The timing reports can be folded into the common scientific hybrid-advantage
summary:

```sh
python3 src/tools/scientific_circt_hybrid_advantage.py \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_64x1.json \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_256x1.json \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_1024x1.json \
  --write-report \
  --report-out reports/scientific_circt_dense_matmul_tile_hybrid_advantage.json
```

A second testbench, `batched_reduction`, uses the same pattern:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_batched_reduction.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_batched_reduction_1024x1.json
```

The testbench-level summary combines dense matmul and batched reduction reports:

```sh
python3 src/tools/scientific_circt_hybrid_advantage.py \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_64x1.json \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_256x1.json \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_1024x1.json \
  --report reports/scientific_circt_batched_reduction_64x1.json \
  --report reports/scientific_circt_batched_reduction_256x1.json \
  --report reports/scientific_circt_batched_reduction_1024x1.json \
  --write-report \
  --report-out reports/scientific_circt_testbench_hybrid_advantage.json
```

Both current testbenches first become end-to-end GPU-favorable at `256x1` with
`inner_repeat=1000`; `64x1` remains CPU-favorable end-to-end for both.

`stencil_2d_tile` follows the same flow but has a higher boundary:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_stencil_2d_tile.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_stencil_2d_tile_1024x1.json
```

For this neighbor-style kernel, `64x1` and `256x1` remain CPU-favorable
end-to-end, while `1024x1` becomes GPU-favorable.

`softmax_exp_pipeline` covers an exp/softmax-style arithmetic pipeline and uses
the same CIRCT/SystemVerilog, Verilator CPU reference, and CUDA timing path:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_softmax_exp_pipeline.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_softmax_exp_pipeline_1024x1.json
```

The measured exp/softmax-style pipeline is CPU-favorable at `64x1`
(`0.601074x`) but GPU-favorable at `256x1` (`1.86415x`) and `1024x1`
(`5.75945x`) end-to-end. This supports a microGPT-style partitioning direction:
regular matmul, reduction, and softmax-like kernels are GPU candidates once
state batching amortizes launch and transfer overhead, while token/control
state machines remain separate CPU or new-mapping candidates.

The combined summary should include all measured scientific candidates:

```sh
python3 src/tools/scientific_circt_hybrid_advantage.py \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_64x1.json \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_256x1.json \
  --report reports/scientific_circt_dense_matmul_tile_gpu_timing_1024x1.json \
  --report reports/scientific_circt_batched_reduction_64x1.json \
  --report reports/scientific_circt_batched_reduction_256x1.json \
  --report reports/scientific_circt_batched_reduction_1024x1.json \
  --report reports/scientific_circt_stencil_2d_tile_64x1.json \
  --report reports/scientific_circt_stencil_2d_tile_256x1.json \
  --report reports/scientific_circt_stencil_2d_tile_1024x1.json \
  --report reports/scientific_circt_softmax_exp_pipeline_64x1.json \
  --report reports/scientific_circt_softmax_exp_pipeline_256x1.json \
  --report reports/scientific_circt_softmax_exp_pipeline_1024x1.json \
  --report reports/scientific_circt_microgpt_math_block_64x1.json \
  --report reports/scientific_circt_microgpt_math_block_256x1.json \
  --report reports/scientific_circt_microgpt_math_block_1024x1.json \
  --report reports/scientific_circt_microgpt_attention_head_64x1.json \
  --report reports/scientific_circt_microgpt_attention_head_256x1.json \
  --report reports/scientific_circt_microgpt_attention_head_1024x1.json \
  --report reports/scientific_circt_microgpt_mlp_slice_64x1.json \
  --report reports/scientific_circt_microgpt_mlp_slice_256x1.json \
  --report reports/scientific_circt_microgpt_mlp_slice_1024x1.json \
  --report reports/scientific_circt_microgpt_block_slice_64x1.json \
  --report reports/scientific_circt_microgpt_block_slice_256x1.json \
  --report reports/scientific_circt_microgpt_block_slice_1024x1.json \
  --report reports/scientific_circt_microgpt_inference_slice_64x1.json \
  --report reports/scientific_circt_microgpt_inference_slice_256x1.json \
  --report reports/scientific_circt_microgpt_inference_slice_1024x1.json \
  --write-report \
  --report-out reports/scientific_circt_testbench_hybrid_advantage.json
```

The measured boundary can be converted into a compile-time selection policy:

```sh
python3 src/tools/scientific_circt_gpu_selection_policy.py \
  --summary reports/scientific_circt_testbench_hybrid_advantage.json \
  --write-report \
  --report-out reports/scientific_circt_gpu_selection_policy.json
```

The current policy selects GPU state-parallel execution for measured candidates
only when `steps=1`, all measured kernel timings are GPU-favorable, and the
state batch is at or above that candidate's measured end-to-end favorable
boundary. The current thresholds are `nstates >= 256` for `dense_matmul_tile`,
`batched_reduction`, `softmax_exp_pipeline`, `microgpt_math_block`, and
`microgpt_attention_head`, `microgpt_block_slice`, and
`microgpt_inference_slice`, and `nstates >= 1024` for `stencil_2d_tile` and
`microgpt_mlp_slice`; below each threshold, CPU is the default end-to-end path.

The measured scientific policy can also be projected onto a microGPT-style IR
partition without claiming microGPT execution:

```sh
python3 src/tools/scientific_circt_microgpt_ir_partition_probe.py \
  --policy reports/scientific_circt_gpu_selection_policy.json \
  --nstates 256 \
  --steps 1 \
  --write-report \
  --report-out reports/scientific_circt_microgpt_ir_partition_probe.json
```

At `256x1`, the current probe classifies 8 of 10 microGPT-style nodes as GPU
state-parallel candidates: attention/MLP dense math, softmax-like arithmetic,
and normalization reductions. Token-loop control and KV-cache state updates
remain CPU or new-mapping candidates. This is the reason to prefer a direct
microGPT IR/CIRCT route for the next experiment: it preserves GPU-friendly
regular arithmetic before FPGA-oriented RTL/control lowering obscures it.
gateGPT remains useful as an external RTL testbench, but not as the cleanest
first surface for GPU partition discovery.

A first composite microGPT-style math block now materializes the regular
arithmetic path directly through CIRCT/SystemVerilog:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_microgpt_math_block.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_microgpt_math_block_1024x1.json
```

This block combines dense dot-product style arithmetic, a softmax/exp-like
pipeline, and a reduction in one generated SystemVerilog module. It passes
Verilator CPU reference and records end-to-end speedups of `0.239753x` at
`64x1`, `1.2195x` at `256x1`, and `4.23625x` at `1024x1`. It is still not full
microGPT execution, but it is stronger evidence than the partition probe alone:
the directly lowered composite math region itself follows the same GPU-favorable
batch boundary.

A source-derived microGPT attention-head slice is also materialized from the
actual `third_party/microgpt.py` attention-loop shape (`n_head=4`,
`head_dim=4`):

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_microgpt_attention_head.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_microgpt_attention_head_1024x1.json
```

This slice computes a two-token head-style dot/weight/value path and passes the
same CIRCT/SystemVerilog, Verilator CPU reference, and CUDA timing flow. Its
end-to-end speedups are `0.602488x` at `64x1`, `1.8243x` at `256x1`, and
`6.41385x` at `1024x1`; kernel-only speedups are positive at all three shapes.
It is still not full block-size microGPT inference.

A reduced-width microGPT MLP slice covers the `mlp_fc1 -> ReLU -> mlp_fc2`
structure:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_microgpt_mlp_slice.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_microgpt_mlp_slice_1024x1.json
```

This slice is intentionally lighter than the full `4 * n_embd` hidden-width MLP.
It passes CIRCT/SystemVerilog, Verilator CPU reference, and CUDA timing. Its
end-to-end speedups are `0.339622x` at `64x1`, `0.333924x` at `256x1`, and
`2.28894x` at `1024x1`; kernel-only speedups are positive at all three shapes.
This records that light MLP-like slices need a larger state batch before the GPU
wins end-to-end.

A source-derived microGPT block-level slice combines attention-style
aggregation, residual-style addition, and MLP-style arithmetic:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_microgpt_block_slice.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_microgpt_block_slice_1024x1.json
```

This slice is still reduced to a one-token/two-key block-level path, not full
`block_size` microGPT inference. It passes CIRCT/SystemVerilog, Verilator CPU
reference, and CUDA timing. Its end-to-end speedups are `0.52329x` at `64x1`,
`1.70084x` at `256x1`, and `5.75973x` at `1024x1`; kernel-only speedups are
`2.6523x`, `7.66483x`, and `32.0863x`.

A source-derived two-token microGPT inference slice adds token/position
embedding-style arithmetic, KV-cache-style reuse, token1 attention over token0
and itself, residual/MLP-style arithmetic, and logit-style outputs:

```sh
source artifacts/toolchains/circt-firtool-1.149.0/env.sh
python3 src/tools/scientific_circt_microgpt_inference_slice.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --write-report \
  --report-out reports/scientific_circt_microgpt_inference_slice_1024x1.json
```

This is closer to the inference path than the isolated block slice, but it is
still a reduced two-token scenario batch, not full `block_size` microGPT
execution and not training/autograd. It passes CIRCT/SystemVerilog, Verilator
CPU reference, and CUDA timing. Its end-to-end speedups are `0.249726x` at
`64x1`, `1.24281x` at `256x1`, and `3.62419x` at `1024x1`; kernel-only
speedups are `2.3037x`, `4.15142x`, and `14.944x`.

The gateGPT versus direct microGPT/CIRCT comparison is generated with:

```sh
python3 src/tools/scientific_circt_gategpt_microgpt_compare.py \
  --microgpt-source third_party/microgpt.py \
  --microgpt-report reports/scientific_circt_microgpt_math_block_64x1.json \
  --microgpt-report reports/scientific_circt_microgpt_math_block_256x1.json \
  --microgpt-report reports/scientific_circt_microgpt_math_block_1024x1.json \
  --microgpt-report reports/scientific_circt_microgpt_attention_head_64x1.json \
  --microgpt-report reports/scientific_circt_microgpt_attention_head_256x1.json \
  --microgpt-report reports/scientific_circt_microgpt_attention_head_1024x1.json \
  --microgpt-report reports/scientific_circt_microgpt_mlp_slice_64x1.json \
  --microgpt-report reports/scientific_circt_microgpt_mlp_slice_256x1.json \
  --microgpt-report reports/scientific_circt_microgpt_mlp_slice_1024x1.json \
  --microgpt-report reports/scientific_circt_microgpt_block_slice_64x1.json \
  --microgpt-report reports/scientific_circt_microgpt_block_slice_256x1.json \
  --microgpt-report reports/scientific_circt_microgpt_block_slice_1024x1.json \
  --microgpt-report reports/scientific_circt_microgpt_inference_slice_64x1.json \
  --microgpt-report reports/scientific_circt_microgpt_inference_slice_256x1.json \
  --microgpt-report reports/scientific_circt_microgpt_inference_slice_1024x1.json \
  --write-report \
  --report-out reports/scientific_circt_gategpt_microgpt_compare.json
```

The current comparison scans [third_party/microgpt.py](third_party/microgpt.py)
and records `linear`, `softmax`, `rmsnorm`, `gpt`, attention, MLP, and autograd
training structure. It keeps gateGPT as the realistic external RTL testbench
lane: six CPU Verilator testbenches and GPU kernel-launch smoke coverage exist,
`tb_exp` is a narrow regular-datapath positive case, and `tb_core` remains a
stateful token/control negative case. For GPU partition discovery, the direct
microGPT/CIRCT route is preferred because regular arithmetic remains explicit
and the composite math block, attention-head slice, MLP slice, and block-level
slice plus a two-token inference slice are already measured through
SystemVerilog.

The scientific CIRCT evidence audit checks that each measured candidate has
SystemVerilog, Verilator CPU reference status, timing reports, summary coverage,
policy coverage, and dispatch-matrix speedup evidence:

```sh
python3 src/tools/scientific_circt_evidence_audit.py \
  --dispatch-matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
  --write-report \
  --report-out reports/scientific_circt_evidence_audit.json
```

The current audit reports `9/9` scientific CIRCT candidates ready and verifies
that the dispatch matrix has measured speedup evidence attached to all 27
candidate/shape rows.

The measured policy can be converted into a compile-time hybrid handoff
protocol:

```sh
python3 src/tools/scientific_circt_hybrid_protocol.py \
  --policy reports/scientific_circt_gpu_selection_policy.json \
  --summary reports/scientific_circt_testbench_hybrid_advantage.json \
  --write-report \
  --report-out reports/scientific_circt_hybrid_protocol.json
```

The current protocol report is `protocol_ready` for all nine measured
candidates and `source_variant_ready_count=3` for HLS-friendly variants. Its
dispatch key is `(candidate, source_variant, nstates, steps)`, with `steps=1`,
CPU fallback below each candidate or variant threshold, and one GPU launch per
candidate batch. For the microGPT-style lane, CPU keeps token-loop control,
sampler/observable authority, and full KV-cache state authority. GPU owns only
the measured arithmetic batch. For `microgpt_inference_slice`, the baseline GPU
boundary starts at `nstates=256`; for `inference2_hls_friendly`, the promoted
HLS source-variant boundary starts at `1024x1` with `8192` logical input bytes
plus `49152` logical output bytes. These are logical payload bytes only;
allocator/alignment/PCIe framing, runtime ABI authority, and automatic HLS
rewriting are not claimed.

The same tool can emit a single compile-time dispatch decision:

```sh
python3 src/tools/scientific_circt_hybrid_protocol.py \
  --protocol reports/scientific_circt_hybrid_protocol.json \
  --candidate microgpt_inference_slice \
  --nstates 256 \
  --steps 1
```

For the current reports this returns `select_gpu_state_parallel` with reason
`measured_candidate_at_or_above_threshold`. The same candidate at `64x1`, an
unknown candidate, or a step mismatch returns `select_cpu` with a fail-closed
reason.

The same decision CLI can select an HLS-friendly source variant:

```sh
python3 src/tools/scientific_circt_hybrid_protocol.py \
  --protocol reports/scientific_circt_hybrid_protocol.json \
  --candidate microgpt_inference_slice \
  --source-variant inference2_hls_friendly \
  --nstates 1024 \
  --steps 1
```

For the current reports this returns `promote_to_hls_gpu`. The non-improving
`block2_hls_friendly` variant returns `keep_baseline_gpu_or_cpu`; below the
variant threshold, unknown variants, and step mismatches fail closed to
`select_cpu`.

The same protocol can be expanded into an all-candidate dispatch matrix:

```sh
python3 src/tools/scientific_circt_hybrid_dispatch_matrix.py \
  --protocol reports/scientific_circt_hybrid_protocol.json \
  --summary reports/scientific_circt_testbench_hybrid_advantage.json \
  --write-report \
  --report-out reports/scientific_circt_hybrid_dispatch_matrix.json
```

For the current `64x1`, `256x1`, and `1024x1` points this matrix records 27
candidate/shape dispatch decisions and attaches measured CPU/GPU timing
evidence to all 27 rows: `64x1` selects CPU for all nine candidates, `256x1`
selects GPU for seven candidates and CPU for stencil plus the reduced MLP
slice, and `1024x1` selects GPU for all nine candidates. This is still a
compile-time report surface over measured timing reports, not runtime ABI, PCIe
framing, RTLMeter, full microGPT execution, or automatic partitioning evidence.
The same report also ranks the GPU-selected rows for runtime integration. The
current top candidate is `microgpt_attention_head` at `1024x1`, with measured
end-to-end speedup `6.41385x`; the next required evidence is broader hybrid
runtime entrypoint wiring plus amortized integration timing.

The matrix also expands the HLS-friendly `source_variants` over the same shape
points. It records 12 source-variant decisions: three `promote_to_hls_gpu`
decisions at `1024x1`, three `keep_baseline_gpu_or_cpu` decisions for
`block2_hls_friendly`, and six CPU fallbacks below the promoted variant
threshold. The promoted runtime-handoff candidates rank as
`attention_head4_hls_friendly` (`13.301119215779238x`),
`mlp4_hls_friendly` (`9.922827450510521x`), and
`inference2_hls_friendly` (`9.799333107174757x`). The selected next runtime
boundary is `inference2_hls_friendly`, because attention already has the
scoped runtime evidence lane and inference is the fuller token/cache slice even
though MLP is slightly faster.

The selected HLS-friendly source variant can then be re-run as a scoped runtime
handoff boundary:

```sh
python3 src/tools/scientific_circt_source_variant_runtime_handoff.py \
  --matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
  --hls-variant-report reports/scientific_circt_hls_mlp_block_variants.json \
  --write-report \
  --report-out reports/scientific_circt_source_variant_runtime_handoff.json
```

The current report is `runtime_handoff_boundary_measured` for
`inference2_hls_friendly,1024x1`. It reuses the generated direct-callsite
binary and GPU shared library, keeps token-loop/sampler/KV-cache authority on
CPU, and treats the HLS-friendly two-inference arithmetic batch as the GPU
handoff scope. CPU/GPU output and control checksums match. The observed bridge
wall speedup is `9.504688053885925x`, with GPU end-to-end speedup
`10.858452274825085x`, kernel speedup `34.0432286328947x`, `8192` logical input
bytes, and `49152` logical output bytes. This is not full microGPT execution,
PCIe framing evidence, RTLMeter evidence, automatic HLS rewriting, or a
production runtime boundary.

The same selected boundary can now be measured from a checked-in `src/hybrid`
Verilator-callsite bridge instead of relying only on the generated direct
binary:

```sh
python3 src/tools/scientific_circt_source_variant_runtime_handoff.py \
  --entrypoint src-hybrid-verilator \
  --matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
  --hls-variant-report reports/scientific_circt_hls_mlp_block_variants.json \
  --write-report \
  --report-out reports/scientific_circt_source_variant_verilator_entrypoint.json
```

This compiles
`src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` against the
generated `inference2_hls_friendly` Verilator `obj_dir`, loads
`libinference2_hls_friendly_gpu.so`, compares the Verilator CPU output buffer
against GPU outputs, then times the GPU-only handoff path. The current report
is `src_hybrid_verilator_runtime_handoff_measured`: output/checksum equality
holds, bridge wall is `0.15218008 ms` per integration batch, and
CPU-to-bridge-wall speedup is `9.982658965614949x`. This is the first
checked-in `src/hybrid` runtime boundary for the selected HLS-friendly
microGPT inference slice; it is still scoped and not full microGPT execution.

The selected boundary can also be routed through the reusable runtime
dispatcher, which preserves the dispatch-matrix candidate/source_variant/shape
policy before invoking the registered `src/hybrid` bridge:

```sh
python3 src/tools/scientific_circt_source_variant_runtime_dispatcher.py \
  --matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
  --hls-variant-report reports/scientific_circt_hls_mlp_block_variants.json \
  --write-report \
  --report-out reports/scientific_circt_source_variant_runtime_dispatcher.json
```

The current dispatcher report is `runtime_dispatch_measured` for
`inference2_hls_friendly,1024x1`. It rejects non-selected source variants,
dispatches only the registered `src_hybrid_verilator_callsite_bridge`, and then
reuses the same checked-in Verilator-callsite bridge. Output/checksum equality
holds. The measured bridge wall is `0.14075793333333333 ms` per integration
batch, with CPU-to-bridge-wall speedup `11.09435972584612x`, GPU end-to-end
speedup `12.83563238331603x`, and kernel speedup `34.54436766075257x`. This is
still scoped evidence: not full microGPT execution, PCIe framing evidence,
RTLMeter evidence, automatic HLS rewriting, or a production runtime dispatcher.

The selected one-hour runtime test case is a dispatcher soak over the same
`inference2_hls_friendly,1024x1` boundary:

```sh
deadline=$((SECONDS+3600))
i=0
mkdir -p reports/one_hour_runtime_dispatcher
while [ $SECONDS -lt $deadline ]; do
  python3 src/tools/scientific_circt_source_variant_runtime_dispatcher.py \
    --matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
    --hls-variant-report reports/scientific_circt_hls_mlp_block_variants.json \
    --write-report \
    --report-out reports/one_hour_runtime_dispatcher/dispatcher_${i}.json || exit 1
  i=$((i+1))
done
printf 'iterations=%s\n' "$i"
```

Then summarize the generated per-iteration reports without treating them as
canonical state:

```sh
python3 - <<'PY'
import glob, json, statistics

rows = [
    json.load(open(path))
    for path in sorted(glob.glob("reports/one_hour_runtime_dispatcher/dispatcher_*.json"))
]
ok = [
    row
    for row in rows
    if row.get("status") == "runtime_dispatch_measured"
    and row.get("runtime_handoff_status") == "src_hybrid_verilator_runtime_handoff_measured"
    and row.get("runtime_handoff", {}).get("cpu_vs_gpu_output_equal") is True
    and row.get("runtime_handoff", {}).get("cpu_vs_gpu_control_checksum_equal") is True
]
speedups = [
    row.get("runtime_handoff", {}).get("average", {}).get("cpu_to_bridge_hybrid_wall_speedup")
    for row in ok
]
speedups = [value for value in speedups if isinstance(value, (int, float))]
print(
    {
        "count": len(rows),
        "ok": len(ok),
        "failed": len(rows) - len(ok),
        "speedup_min": min(speedups) if speedups else None,
        "speedup_median": statistics.median(speedups) if speedups else None,
        "speedup_max": max(speedups) if speedups else None,
    }
)
PY
```

This is the primary hour-long case because it keeps the selected
candidate/source_variant/shape policy unchanged and repeatedly exercises the
checked-in `src_hybrid_verilator_callsite_bridge`. The pass condition is that
every iteration exits 0, reports `runtime_dispatch_measured`, keeps nested
`runtime_handoff_status=src_hybrid_verilator_runtime_handoff_measured`, and
preserves output/checksum equality. The latest single dispatcher measurement
took about `1.5 s`, so a one-hour loop should produce roughly 2400 independent
measurements. A larger `inner_repeat` source-variant run can be used later as
arithmetic-intensity stress, but it changes the workload and should not replace
this dispatcher soak as the stability test.

The current one-hour soak result is recorded in
`reports/scientific_circt_source_variant_runtime_dispatcher_soak_summary.json`.
It ran for `3600` seconds and produced `2574` dispatcher reports. All `2574`
reports passed `runtime_dispatch_measured`, nested
`src_hybrid_verilator_runtime_handoff_measured`, output equality, and control
checksum equality. The CPU-to-bridge-wall speedup distribution was min
`1.2956713528049701x`, p10 `8.363504353854227x`, median
`10.731542472816859x`, p90 `11.829942667042333x`, and max
`12.793946412262754x`; bridge wall per integration batch was median
`0.14407087333333335 ms`. There were `75` reports below `5x` bridge speedup
and `40` reports above `0.5 ms` bridge wall, so the result supports stability
of correctness and dispatch execution, not a new reviewed production speedup
claim.

The source-variant metadata surface is generated from the dispatch matrix, HLS
variant reports, and artifact sources before multi-dispatch:

```sh
python3 src/tools/scientific_circt_source_variant_metadata.py \
  --matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
  --hls-variant-report reports/scientific_circt_hls_mlp_block_variants.json \
  --extra-hls-variant-report reports/scientific_circt_hls_attention_head4.json \
  --write-report \
  --report-out reports/scientific_circt_source_variant_metadata.json
```

The current metadata report is `source_variant_metadata_ready` with four
complete rows. It extracts GPU symbols, input/output layout, artifact paths,
Verilator `obj_dir`, entrypoint kind, runtime boundary kind, and fallback
policy for `attention_head4_hls_friendly`, `mlp4_hls_friendly`,
`inference2_hls_friendly`, and `block2_hls_friendly`. The input/output bytes
per state are `80/128`, `16/64`, `8/48`, and `24/32`, respectively.

The dispatcher can now run that metadata-described source-variant set instead
of only the selected inference boundary:

```sh
python3 src/tools/scientific_circt_source_variant_runtime_dispatcher.py \
  --matrix reports/scientific_circt_hybrid_dispatch_matrix.json \
  --hls-variant-report reports/scientific_circt_hls_mlp_block_variants.json \
  --extra-hls-variant-report reports/scientific_circt_hls_attention_head4.json \
  --metadata-report reports/scientific_circt_source_variant_metadata.json \
  --all-known-source-variants \
  --write-report \
  --report-out reports/scientific_circt_source_variant_runtime_dispatcher_multi.json
```

The current multi-dispatch report is `multi_source_variant_dispatch_ready`.
`attention_head4_hls_friendly`, `mlp4_hls_friendly`, and
`inference2_hls_friendly` all dispatch through measured equality-checked GPU
boundaries. Their CPU-to-bridge-wall speedups are respectively
`11.31933596913315x`, `9.466548203869824x`, and `11.420283475548267x` in the
latest run. `block2_hls_friendly` is deliberately kept as
`runtime_dispatch_fallback_baseline`, because its HLS-friendly variant speedup
`5.56609843788867x` does not improve over the baseline `5.75973x`. This is the
current metadata-driven GPU-vs-CPU/baseline selection table for the
source-variant lane, not a full microGPT, RTLMeter, PCIe, or production runtime
claim.

The PULP/NoC heavy RTL candidate matrix is generated with:

```sh
python3 src/tools/heavy_rtl_candidate_matrix.py \
  --write-report \
  --report-out reports/heavy_rtl_candidate_matrix.json
```

The current matrix has six rows: two PULP candidates and four NoC/TLUL-style
candidates. Five rows now have `promote_state_parallel_measurement` evidence:
`pulp_ita_mha`, `pulp_paged_attention_kv_score`, `tlul_socket_1n`,
`tlul_socket_m1`, and `blackparrot_bsg_wormhole_router`. The repeat-median reports are
`reports/pulp_paged_attention_kv_score_64x1_median.json`,
`reports/tlul_socket_1n_32x1_median.json`, and
`reports/tlul_socket_m1_32x1_median.json`, plus the BlackParrot
`reports/blackparrot_bsg_wormhole_router_32x1_median.json`,
`reports/blackparrot_bsg_wormhole_router_64x1_median.json`, and
`reports/blackparrot_bsg_wormhole_router_128x1_median.json`, and
`reports/blackparrot_bsg_wormhole_router_256x1_median.json` shape sweep; all
pass coverage-output equivalence across three samples. Median CPU-to-hybrid wall
speedups are `159.01406799531068x`, `75.23948126801153x`,
`77.24226694915255x`, plus BlackParrot `32.76216804527645x` at `32x1`,
`158.28447339847992x` at `64x1`, `259.4919886899152x` at `128x1`, and
`651.817697228145x` at `256x1`.
`tlul_fifo_sync` remains favorable but
needs resident or shape-sweep evidence before becoming a broader policy row.
`blackparrot_bsg_wormhole_router` now has
`config/slice_launch_templates/blackparrot_bsg_wormhole_router.json`, a
source-backed coverage overlay and gate, and repeat-count-3 packet-pattern
coverage-output-equivalent timing at `32x1`, `64x1`, `128x1`, and `256x1`.
This is now
shape-extension repeat-median-backed promote evidence rather than a `32x1`-only
candidate. The resident/multi-step definition gate is now
`config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json`.
It defines a `256x4` resident packet-pattern timing target, but records the
current named blocker before execution: the BlackParrot packet-pattern patch
script is not yet materialized. The template runner now has a dry-run resident
command surface via `--resident-steps --patch-script`, with resident-specific
candidate dump and compare report paths. The next implementation task is
therefore to materialize that patch script or record it as the FC-071 blocker.
This is scoped candidate evidence, not a broad RTL speedup claim, native
Verilator option, or automatic GPU allocation policy.

The current top row can be converted into the first runtime handoff ABI
definition:

```sh
python3 src/tools/scientific_circt_runtime_handoff_abi.py \
  --write-report \
  --report-out reports/scientific_circt_runtime_handoff_abi.json
```

The current ABI report is `handoff_abi_ready` for
`microgpt_attention_head,1024x1`. It defines an array-of-structs handoff with
20 input bytes/state, 32 output bytes/state, and 53,248 logical roundtrip bytes
for 1,024 states. CPU retains sequence/KV-cache authority, GPU owns only the
measured attention-head arithmetic batch. The adapter evidence below now closes
the first CPU-vs-GPU equality gate; the remaining evidence is broader hybrid
runtime entrypoint wiring plus amortized integration timing.

The first ABI-backed runtime adapter correctness gate is:

```sh
python3 src/tools/scientific_circt_runtime_handoff_adapter.py \
  --abi reports/scientific_circt_runtime_handoff_abi.json \
  --repeat 5 \
  --inner-repeat 1000 \
  --integration-batches 15 \
  --write-report \
  --report-out reports/scientific_circt_runtime_handoff_adapter.json
```

The current adapter report is `adapter_correctness_passed` for
`microgpt_attention_head,1024x1`: observed input bytes `20480`, observed output
bytes `32768`, both match the ABI, and CPU reference versus GPU adapter
`mismatch_count=0` on the same 1,024-state batch. It now also records an
adapter-local integration loop with 15 warmed fused handoffs. It also builds a
shared library exposing an `extern "C"` JSON entrypoint for in-process timing.
This is scoped positive runtime-adapter evidence: once the measured
attention-head work is fused behind the handoff and amortized inside one
adapter process, the adapter preserves the measured candidate region. It is
still not PCIe framing evidence, full microGPT execution, RTLMeter evidence,
automatic partitioning, or direct Verilator runtime evidence.

The first subprocess-free in-process runtime entrypoint timing gate is:

```sh
python3 src/tools/scientific_circt_runtime_entrypoint.py \
  --adapter-report reports/scientific_circt_runtime_handoff_adapter.json \
  --mode in-process \
  --write-report \
  --report-out reports/scientific_circt_runtime_entrypoint.json
```

This entrypoint loads the generated adapter shared library in the same Python
process, runs a CPU+GPU correctness warmup, then times the GPU-only hybrid
library call without `subprocess`. The current report is
`in_process_entrypoint_timing_measured`: CPU/GPU output and checksum equality
hold, and the timed hybrid path is CPU-favorable. Detailed timing numbers live
in `reports/scientific_circt_runtime_entrypoint.json` and `docs/status.md`.

The first broader hybrid-runtime boundary timing gate is:

```sh
python3 src/tools/scientific_circt_broader_runtime_entrypoint.py \
  --adapter-report reports/scientific_circt_runtime_handoff_adapter.json \
  --write-report \
  --report-out reports/scientific_circt_broader_runtime_entrypoint.json
```

This compiles `src/hybrid/scientific_circt_adapter_bridge.c`, loads the same
adapter shared library with `dlopen`/`dlsym`, runs the CPU+GPU correctness call
as warmup, then times the GPU-only adapter symbol from the C bridge. The current
report is `broader_hybrid_entrypoint_timing_measured`: CPU/GPU output and
checksum equality hold, and the bridge-internal timed hybrid path is
CPU-favorable. This is broader `src/hybrid` bridge evidence, not direct
Verilator callsite evidence.

The first direct Verilator-generated callsite timing gate for the same adapter
boundary is:

```sh
python3 src/tools/scientific_circt_verilator_callsite_entrypoint.py \
  --adapter-report reports/scientific_circt_runtime_handoff_adapter.json \
  --write-report \
  --report-out reports/scientific_circt_verilator_callsite_entrypoint.json
```

This compiles `src/hybrid/scientific_circt_verilator_callsite_bridge.cpp` against
the `microgpt_attention_head` Verilator `obj_dir`, calls `Vsim::eval()` as the
CPU callsite, compares the 1,024-state Verilator output buffer against the GPU
adapter output buffer, then times the GPU-only adapter symbol. The current report
is `direct_verilator_callsite_entrypoint_timing_measured`: output/checksum
equality hold and the timed hybrid path is CPU-favorable. This is still scoped to
the attention-head adapter; it is not full microGPT execution or a production
runtime claim.

The HLS-friendly source-variant check for the same attention-head direction is:

```sh
python3 src/tools/scientific_circt_hls_attention_head_variant.py \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --integration-batches 15 \
  --write-report \
  --report-out reports/scientific_circt_hls_attention_head4.json
```

This materializes a four-independent-head FIRRTL/SystemVerilog variant, builds a
Verilator CPU callsite, builds a separate CUDA shared library, and compares the
same output buffer/checksum before timing the in-process GPU path. The current
report is `hls_variant_improved`: output/checksum equality hold, and the scoped
bridge-wall speedup improves from the direct-callsite baseline `6.126758590128443x`
to `13.301119215779238x`. This is evidence for source/IR-level arithmetic
reshaping, not an automatic HLS rewrite or full microGPT execution.

The same source-variant check now covers MLP and block-level slices:

```sh
python3 src/tools/scientific_circt_hls_mlp_block_variants.py \
  --variant all \
  --shape 1024x1 \
  --repeat 5 \
  --inner-repeat 1000 \
  --integration-batches 15 \
  --write-report \
  --report-out reports/scientific_circt_hls_mlp_block_variants.json
```

The current report is `hls_variant_summary_ready`. `mlp4_hls_friendly` improves
over the baseline MLP slice from `2.28894x` to `9.922827450510521x` bridge-wall
speedup. `block2_hls_friendly` also lowers and matches outputs/checksum, but
does not improve over the baseline block slice (`5.56609843788867x` versus
`5.75973x`). `inference2_hls_friendly` checks the fuller two-token inference
slice and improves from `3.62419x` to `9.799333107174757x`. The current rule is
therefore: explicit independent-unit reshaping is useful for light
MLP/attention/inference arithmetic when it raises arithmetic intensity enough,
but it should not be promoted for a block-level slice unless the added parallel
arithmetic outweighs bridge and output movement cost.

The selection policy can consume those HLS reports:

```sh
python3 src/tools/scientific_circt_gpu_selection_policy.py \
  --summary reports/scientific_circt_testbench_hybrid_advantage.json \
  --hls-variant-report reports/scientific_circt_hls_attention_head4.json \
  --hls-variant-report reports/scientific_circt_hls_mlp_block_variants.json \
  --write-report \
  --report-out reports/scientific_circt_gpu_selection_policy.json
```

The policy keeps the original candidate/shape decisions and adds
`source_variants`: `attention_head4_hls_friendly`, `mlp4_hls_friendly`, and
`inference2_hls_friendly` are `promote_to_hls_gpu`, while
`block2_hls_friendly` is `keep_baseline_gpu_or_cpu`.

The long-term shorthand Verilator-facing UX target remains:

```sh
verilator --use-gpu -f filelist.f --top-module top
```

That endpoint is not yet a general Verilator replacement. The current canonical preview and parser-minimum spelling is `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`. The current implementation is a scoped hybrid sidecar path with Verilator-like option plumbing. Supported paths should reach the GPU sidecar flow and compare CPU vs hybrid output. Unsupported paths should fail clearly instead of silently falling back or claiming GPU optimization.

The first scoped executable `--use-gpu` adapter path and PATH-selected wrapper
path are complete for one reviewed filelist/template/top path with explicit
`64x1` scheduling. FC-064 / #63 now proves that the VeeR-EL2 design CPU can
produce a correct direct sidecar stdout/cycles run. The current RTLMeter
priority is FC-037 / #2: measure whether that run is useful. `program_staging_lmem` and
`program_staging_imem` now build as reviewed `VlGpuFlatByteMem` flat byte
windows, and the VeeR GPU build now auto-promotes the root image into a
`Vsim__Syms` state image when `%vlSymsp` coverage requires it. The reviewed VeeR
sidecar executable now launches the generated GPU artifact from the extracted
state image and emits observables. The clock/reset patch now advances the GPU run to
`mcycle=726`, `minstret=330`, and the `0xff` finish marker, matching the
architectural counters printed by the CPU stdout. The GPU mailbox trace now
reconstructs normalized stdout, and `_rtlmeter_cycles.txt` is aligned to
RTLMeter's injected `tb_top.core_clk` count. The VeeR-EL2 stdout/cycles gate
passes. FC-037 timing now records three-batch stability gates with seven
`hello` sidecar samples per batch and workload-comparable CPU-parallel
duplicate-`hello` baselines. The current representative scaling gate uses
sixteen CPU-parallel workers and `nstates=16`. The GPU sidecar drives
clock/reset patches across all sixteen state strides and validates all final state
observables against state 0 while keeping the stdout trace scoped to state 0.
Serial RTLMeter CPU elapsed is `0.04s`, sixteen-worker CPU-parallel wall is
`2.218887s`, sidecar wall median across all 21 samples is `0.768573s`, GPU
kernel total median is `268.161011ms`, and the preliminary outcome is
`sidecar_slower_than_serial_cpu`. Bridge preflight median is `0.000406s`.
The bridge now invokes the reviewed Python sidecar in-process, and the sidecar
calls the hybrid C runtime directly instead of launching through
`run_vl_hybrid.py`; the report records
`sidecar_executable_invocation_mode_counts={"in_process_veer_el2_sidecar": 21}`
and `run_vl_hybrid_launcher_mode_counts={"direct_hybrid_runtime": 21}`.
Step-trace field reads use a filtered, coalesced device-buffered DtoD trace path
with rising-edge mailbox reconstruction plus final counter fallback,
init-state replication uses the device kernel path, and patch application uses
the device-resident patch schedule. The filter records only clock-high rows
after reset (`727` rows from a `1457`-step patch capacity). The resident patch
schedule still carries `69936` patch records for `1457` logical steps. All
three batch medians beat the comparable CPU-parallel floor (`0.768573s`,
`0.706345s`, `0.884339s`), and per-state wall is `0.048036s`. Compared with the
prior eight-state gate, total wall is `1.258905x` worse while per-state wall and
states/s improve by about `1.589x`. A previous filtered sixteen-state run
reached `0.643080s`, so the latest rerun shows significant wall-time
variability rather than a robust new speedup.
No broad
RTLMeter GPU usefulness or speedup claim is made because serial CPU is still
much faster. The current blocker has moved beyond non-`hello` loop-collapse
eligibility: fixed-flat-memory `dhry` now has same-window trace equivalence and
a phase-aware pair-cycle loop kernel that preserves the `vl_ico_batch_gpu` plus
`vl_eval_loop_batch_gpu` sequence in bounded diagnostics. Patch/eval fusion was implemented as an explicit
experiment and preserves correctness (`patch_eval_fusion_launched_median=1457.0`
in `reports/rtlmeter_veer_el2_timing_nstates16_fusion.json`), but it is not kept
as the default because the repeated 16-state median `0.774456s` is slightly worse
than the non-fusion representative `0.768573s`. The
`VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=posedge_only` diagnostic reduced the patch
script to `730` logical steps and `35040` resident patch records, but
`reports/rtlmeter_veer_el2_timing_posedge_only_smoke.json` failed correctness:
the VeeR state stayed at `mcycle=0`, `minstret=0`, and no stdout was
reconstructed. High-only clock patching is therefore not a valid acceleration
path. The follow-up pair-cycle/resident-step path preserves ordered low-eval
then high-eval semantics inside one runtime operation. That opt-in pair-cycle
path is now implemented as
`VEER_EL2_SIDECAR_CLOCK_PATCH_MODE=resident_pair_cycle` and keeps the same
low/high eval ordering while pairing runtime loop iterations. The repeated
16-state gate in `reports/rtlmeter_veer_el2_timing_pair_cycle_nstates16.json`
passes all 21 correctness samples with
`resident_pair_cycle_launched_median=727.0` and fallback median `0.0`.
Its sidecar wall median is `0.692794s`, improving the latest non-fusion
representative by `1.109382x`, but it is still slower than serial CPU and does
not beat the previous best filtered 16-state observation (`0.643080s`). The
confirmatory report
`reports/rtlmeter_veer_el2_timing_pair_cycle_confirm_nstates16.json` also
passes 21/21 samples and remains faster than the non-fusion representative
(`0.707203s`, `1.086778x`), but its batch medians still vary
(`0.868907s`, `0.673572s`, `0.685787s`). The mode remains opt-in; default
promotion is premature until longer stability is shown or a true fused
pair-cycle kernel reduces launch count further. The true fused pair-cycle
experiment now emits `vl_patch_eval_pair_cycle_batch_gpu` and is selected with
`VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE=1` alongside `resident_pair_cycle`.
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json` passes 21/21
correctness samples with `pair_cycle_fusion_available_counts={"true": 21}`,
`pair_cycle_fusion_launched_median=727.0`, and fallback median `0.0`. Its
sidecar wall median is `0.641226s`, improving the non-fusion representative by
`1.198599x`, the pair-cycle confirm gate by `1.102892x`, and the previous best
filtered observation by `1.002891x`. This is the current best VeeR 16-state
sidecar result, but it is still about `16.030650x` slower than serial CPU, so no
broad RTLMeter GPU speedup/usefulness claim is made.
Runtime timing reports now also distinguish logical steps from actual timed GPU
launches. The actual-launch smoke
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_actual_launch_smoke.json`
records `gpu_kernel_timing_logical_step_count_median=1457.0` and
`gpu_kernel_timed_launch_count_median=733.0`: the fused pair-cycle path accounts
for 727 paired kernels plus six reset/deassert patch/eval launches.
The next scale point was also measured with 32 duplicated `hello` states.
`reports/rtlmeter_cpu_parallel_hello32_baseline.json` passes with CPU-parallel
wall `4.246739s`, speedup vs serial sum `6.845413x`, and efficiency `0.213919`.
After raising the runtime patch-script per-step limit from 64 to 256 so 32-state
clock/reset patch rows can carry 96 patches, the fused pair-cycle 32-state gate
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json` passes 21/21
correctness samples with `sidecar_wall_s_median=0.950341`,
batch medians `[0.840963, 0.906735, 0.956599]`,
`gpu_kernel_ms_total_median=357.866486`, actual timed GPU launch median `733.0`,
and `pair_cycle_fusion_launched_median=727.0`. Doubling from 16 to 32 states
worsens total wall by `1.482069x`, but improves per-state wall by `1.349465x`
(`0.040077s` to `0.029698s`) and improves the CPU-parallel comparison ratio by
`1.291374x`. Serial CPU is still about `23.758525x` faster than the 32-state
sidecar wall, so this remains throughput-scaling evidence, not a speedup claim.
The follow-up state-local resident patch compression probe is recorded in
`reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json`.
It is correctness-safe and reduces patch records from `139872` to `4371`
(`32x`), but it regresses timing: `sidecar_wall_s_median=2.452390`,
`gpu_kernel_ms_total_median=1675.526123`, and wall is `2.580537x` slower than
the expanded 32-state fused path. Keep it as an opt-in diagnostic, not the next
performance path.
To move toward a real design-CPU workload, the non-`hello` preload path was
first made fail-closed: `reports/veer_el2_cmark_state_image_materialize_after_fix.json`
refuses a mismatched `cmark` program instead of writing a false `hello` image.
The reviewed preload path now materializes matching state images for
`cmark`, `cmark_iccm`, and `dhry` in
`reports/veer_el2_cmark_state_image_materialize.json`,
`reports/veer_el2_cmark_iccm_state_image_materialize.json`, and
`reports/veer_el2_dhry_state_image_materialize.json`. This is preload evidence
only, not timing evidence. Full RTLMeter GPU timing is still blocked because the
current pair-cycle path would require millions of GPU launches for full
design-CPU programs such as `cmark`. The explicit feasibility reports
`reports/rtlmeter_veer_el2_timing_cmark_launch_feasibility.json` and
`reports/rtlmeter_veer_el2_timing_cmark_iccm_launch_feasibility.json` block
before bridge execution with estimated actual timed launch counts of `5276412`
and `6024133`, respectively, against a current threshold of `100000`. The next
step is launch-count collapse via resident multi-cycle execution or a bounded
non-`hello` smoke gate.
The bounded smoke gate now confirms that reviewed non-`hello` state images can
enter the sidecar executable and reach the GPU resident pair-cycle fused launch
path for a one-cycle run: `reports/rtlmeter_veer_el2_dhry_bounded_smoke.json`,
`reports/rtlmeter_veer_el2_cmark_bounded_smoke.json`, and
`reports/rtlmeter_veer_el2_cmark_iccm_bounded_smoke.json` all emit sidecar
observables with `gpu_kernel_timed_launch_count=7` and one fused pair-cycle
launch. This is not full RTLMeter correctness or timing evidence; the smoke is
intentionally too short to reach the CPU program's final counters or pass/fail
marker.
Extending that bounded smoke to 500 cycles now shows architectural progress for
the reviewed non-`hello` programs:
`reports/rtlmeter_veer_el2_dhry_bounded_progress_500.json`,
`reports/rtlmeter_veer_el2_cmark_bounded_progress_500.json`, and
`reports/rtlmeter_veer_el2_cmark_iccm_bounded_progress_500.json` all record
`mcycle=499` with `minstret=321`, `342`, and `418` respectively. The runs still
do not finish the RTLMeter programs and do not measure useful end-to-end timing.
`reports/rtlmeter_veer_el2_non_hello_bounded_progress_summary.json` is the
machine-checked summary for those three reports; it passes the bounded progress
threshold and keeps `speedup_claimed=false`.
The first opt-in launch-count-collapse surface is now implemented, rebuilt,
and exercised in a bounded no-trace diagnostic:
`vlgpugen` emits `vl_patch_eval_pair_cycle_loop_batch_gpu`, `run_vl_hybrid`
accepts `RUN_VL_HYBRID_FUSED_PAIR_CYCLE_LOOP`, and the VeeR sidecar forwards
`VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP`. The diagnostic report is
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_no_trace_500.json`: for
`dhry`, 500 design-CPU cycles collapse to
`pair_cycle_loop_fusion.kernel_launches=1`, `cycles=500`, `fallback=0`, and
`gpu_kernel_timed_launch_count=7`, while final observables still match across
the two GPU states with `mcycle=499` and `minstret=321`. This is launch-count
collapse evidence only. The same loop path also reaches a full `hello`
program event in
`reports/rtlmeter_veer_el2_hello_pair_cycle_loop_no_trace_full_event.json`:
727 design-CPU cycles collapse to one loop kernel and seven actual timed
launches, `finish_marker_observed=true`, `mcycle=726`, `minstret=330`, and
`cycles=2229`, matching the prior stdout/cycles gate's final counters. Because
`VEER_EL2_SIDECAR_DISABLE_STEP_TRACE=1` disables stdout reconstruction, these
were initially not full RTLMeter stdout correctness, full timing, speedup, or
usefulness evidence. The same loop-collapse path now has a larger non-`hello`
bounded diagnostic:
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_5000_summary.json`
summarizes `dhry`, `cmark`, and `cmark_iccm` 5000-cycle no-trace runs. All
three pass the bounded progress check with `mcycle=4999`, `minstret=4821`,
`4842`, and `4918`, `pair_cycle_loop_fusion.kernel_launches=5`,
`pair_cycle_loop_fusion.cycles=5000`, fallback `0`, and
`gpu_kernel_timed_launch_count=21`. This proves launch-count collapse now works
for reviewed non-`hello` preloads beyond the tiny `hello` full-event case, but
the programs do not finish and stdout is not reconstructed, so it is still not
full RTLMeter correctness, timing, speedup, or usefulness evidence.
The loop chunk gate has now been widened for this specific path. With
`VEER_EL2_SIDECAR_FUSED_PAIR_CYCLE_LOOP_CHUNK=5000`,
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_5000_summary.json`
passes for the same three non-`hello` 5000-cycle runs with one loop kernel,
seven actual timed GPU launches, and fallback `0`. The `cmark` and `cmark_iccm`
bounded GPU kernel times drop from about `2.75s` to about `1.11s`, so the old
1000-cycle chunk cap was a real bounded-runtime blocker. A follow-up
`dhry` 50000-cycle finish probe at
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk50000_final_stdout_50000.json`
still records `finish_marker_observed=false`, `mcycle=49999`, and
`minstret=49821`; non-`hello` final-observable stdout is also still blocked by
the reviewed-hello-only stdout gate. The next gate is therefore finish
reachability and program-image completeness, not a speedup claim.
The program-image completeness blocker was narrowed further: the sidecar syms
init materializer now writes reviewed DCCM/ICCM ECC bank preload entries into
the GPU init blob. The refreshed bounded summary
`reports/rtlmeter_veer_el2_non_hello_pair_cycle_loop_chunk5000_bank_init_5000_summary.json`
passes for `dhry`, `cmark`, and `cmark_iccm` with one loop kernel and seven
actual timed GPU launches. It records DCCM/ICCM bank word counts of `371/0`,
`0/0`, and `342/7674`, respectively. This changes `dhry` and `cmark_iccm`
PC/minstret versus the pre-bank-init reports, proving the previous sidecar init
state was incomplete for bank-preloaded programs. A longer `dhry` bank-init
probe at
`reports/rtlmeter_veer_el2_dhry_pair_cycle_loop_chunk200000_dccm_init_final_stdout_200000.json`
reaches `mcycle=199999` and `minstret=191985` in one loop kernel but still has
`finish_marker_observed=false`, so FC-037 remains open.
A CPU RTLMeter follow-up now shows why that bounded GPU window is too short for
finish evidence: `reports/rtlmeter_cpu_dhry_serial_baseline.json` finishes
`VeeR-EL2:default:dhry` at `5984259` RTLMeter cycles with a `37.240654s` serial
wall time, so the 200000-cycle GPU probe covers only about `3.34%` of the full
CPU completion window. The bounded CPU snapshot gap is now closed for this
`dhry` point: `src/tools/rtlmeter_veer_el2_cpu_snapshot.py` links a generated
snapshot main against the existing CPU `Vsim` obj_dir and the reports
`reports/rtlmeter_veer_el2_cpu_dhry_snapshot_mcycle4999.json`,
`reports/rtlmeter_veer_el2_cpu_dhry_snapshot_mcycle49999.json`, and
`reports/rtlmeter_veer_el2_cpu_dhry_snapshot_mcycle199999.json` stop at matching
GPU-observed `mcycle` points. The mismatch is present from the first 5k window:
CPU retires `4473`, `47757`, and `192038` instructions while the corresponding
GPU bank-init reports initially exposed raw PC/minstret gaps, but that thread is
now resolved as flat `lmem` initialization. `$readmemh` records outside the
`0x80000000` 64 KiB program window were writing through the unmapped default
byte, and the missing `@10000000` control window made GPU reads return
`0x0a0a0a0a...` instead of the Dhrystone iteration value `1000`. The fixed
flat-memory layout separates unmapped writes from default reads and materializes
the 16-byte control window. Same-window CPU/GPU trace equivalence now reaches
`reports/rtlmeter_veer_el2_dhry_lmem_control_compare_875_50000.json`:
`status=match`, GPU steps `875..49999`, 49125 aligned rows, 62 compared fields,
and zero mismatched field observations. The automatic summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_trace_equivalence_875_50000.json`
passes those thresholds while keeping `timing_measured=false`,
`speedup_claimed=false`, and `usefulness_claimed=false`. This is bounded trace
equivalence only; the next task is stdout-safe longer `dhry` progress or finish
reachability with the fixed flat-memory layout, not a GPU usefulness claim. The
first stdout-safe longer-progress gate remains bounded-only:
`reports/rtlmeter_veer_el2_dhry_lmem_control_stdout_safe_progress_100000_loopfix.json`
reaches `mcycle=99999` / `minstret=95864` with `finish_marker_observed=false`,
`step_trace_disabled=true`, and `final_observable_stdout_requested=true`, while
keeping timing/speed/usefulness claims disabled. Non-`hello` final-observable
stdout is still blocked by policy. Bounded phase-aware loop diagnostics now
launch `vl_patch_eval_pair_cycle_loop_batch_gpu` and match resident fallback
byte-for-byte at 10, 100, and 1000 cycles. The 1000-cycle case reduces actual
timed launches from `6009` to `10` and GPU kernel total from `272.929400ms` to
`238.399490ms`, but wrapper wall is not yet a robust win and full `dhry`
finish/stdout is unproven. The 100000-cycle phase-aware loop summary
`reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_progress.json`
reaches `mcycle=99999` / `minstret=95864` with one loop kernel, `10` actual
timed launches, `22404.386719ms` GPU kernel time, and no finish marker. A
bounded projection report
`reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_negative_projection.json`
now records `negative_usefulness_decision=true`: projecting to CPU RTLMeter
cycles `5984259` gives about `1340.75s` GPU-kernel time versus `37.240654s`
CPU serial wall, or about `36.00x` slower by GPU-kernel time alone. This is a
negative usefulness decision for the current bounded GPU path, not full
`dhry` finish/stdout or a positive speedup/usefulness claim.

Regenerate that bounded projection report with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/rtlmeter_veer_el2_timing.py \
  --case VeeR-EL2:default:dhry \
  --bounded-projection-sidecar-report artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/dhry_lmem_control_loop_notrace_100000_phaseaware_loop/_sidecar/veer_el2_sidecar_executable_report.json \
  --bounded-projection-cpu-baseline-report reports/rtlmeter_cpu_dhry_serial_baseline.json \
  --bounded-projection-min-progress-fraction 0.01 \
  --negative-usefulness-ratio-threshold 10 \
  --write-report \
  --report-out reports/rtlmeter_veer_el2_dhry_lmem_control_phaseaware_loop_100000_negative_projection.json
```
The user's design-CPU
parallel SIM idea is useful on CPU: `reports/rtlmeter_cpu_mixed_program_parallel_baseline.json`
runs `dhry`, `cmark`, and `cmark_iccm` as separate RTLMeter CPU simulations and
preserves stdout/cycle observables while reducing wall time from a `107.522775s`
serial sum to `37.079953s` with three workers (`2.899755x`). This is CPU-side
throughput evidence, not GPU usefulness evidence.
The matching GPU mixed-state path now exists:
`reports/rtlmeter_veer_el2_mixed_state_dhry_cmark_cmark_iccm_100000_projection.json`
summarizes a 100000-cycle sidecar run with `state0=dhry`, `state1=cmark`, and
`state2=cmark_iccm`. The sidecar materializes one syms-state image per program,
concatenates the images into one `storage_size * nstates` init file, and uses
the same generated GPU kernels with host-uploaded mixed init state instead of
device-side same-init replication. All three states reach `mcycle=99999` with
distinct PC/minstret observables. Projecting the measured GPU kernel time to the
CPU mixed baseline max cycle count `6025629` gives about `1369.99s` versus
`37.079953s` CPU mixed parallel wall, about `36.95x` slower. This is a negative
projection for the current mixed GPU path, not full-program finish,
full-program timing, non-state0 stdout correctness, speedup, or GPU usefulness
evidence.

Regenerate the mixed-state GPU/CPU summary with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/rtlmeter_veer_el2_timing.py \
  --mixed-state-sidecar-report artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/mixed_dhry_cmark_cmark_iccm_notrace_100000/_sidecar/veer_el2_sidecar_executable_report.json \
  --mixed-state-cpu-baseline-report reports/rtlmeter_cpu_mixed_program_parallel_baseline.json \
  --write-report \
  --report-out reports/rtlmeter_veer_el2_mixed_state_dhry_cmark_cmark_iccm_100000_projection.json
```
The hello path now has an explicit final-observable stdout
mode, `VEER_EL2_SIDECAR_FINAL_OBSERVABLE_STDOUT=1`, recorded in
`reports/rtlmeter_veer_el2_hello_pair_cycle_loop_final_stdout_bridge.json` and
`reports/rtlmeter_veer_el2_hello_pair_cycle_loop_final_stdout_sidecar.json`.
That mode is reviewed only for the known hello program SHA and passes the CPU
normalized stdout/cycles comparison while keeping
`gpu_kernel_timed_launch_count=7`.
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_smoke.json`
shows the same mode through the timing runner with one sample. The optimized
rebuild follow-up is now captured in
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_final_stdout_nstates16.json`:
21/21 correctness samples pass, `sidecar_wall_s_median=0.751716`,
batch medians are `0.733165`, `0.812418`, and `0.705006`,
`gpu_kernel_ms_total_median=259.037048`,
`pair_cycle_loop_fusion.kernel_launches=1`,
`gpu_kernel_timed_launch_count=7`, and
`step_trace_copy_mode=disabled_final_observable_stdout`. This is faster than
the matching sixteen-worker CPU-parallel `hello` baseline
(`sidecar_vs_cpu_parallel_ratio=2.951762`) but still about `18.8x` slower than
serial CPU and about `1.17x` slower than the current best sixteen-state fused
pair-cycle sidecar result. The next work is sidecar load/host overhead reduction
or a general device-side trace path for non-`hello` stdout, not a broad
usefulness claim. The first opt-in overhead breakdown is
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_stage_timing_smoke.json`,
enabled by `VEER_EL2_SIDECAR_HYBRID_STAGE_TIMING=1`. In that smoke,
`sidecar_wall_s_median=0.931864`, `gpu_kernel_ms_total_median=266.998444`, and
the largest runtime stages are CUDA context/init setup
(`after_cuCtxCreate=346.810ms`, `after_cuInit=157.850ms`) plus final sync
(`after_final_sync=265.491ms`); final state dump is only `8.076ms`. The next
performance path is therefore persistent runtime/context reuse, not optimizing
the dump first.
The first in-process repeat diagnostic is
`reports/rtlmeter_veer_el2_timing_pair_cycle_loop_inprocess_repeats_smoke.json`,
enabled with `VEER_EL2_SIDECAR_HYBRID_TIMING_REPEATS=3`. It reuses one CUDA
context/runtime setup and restores the VeeR init state from a device snapshot
between repeats. Correctness passes, `gpu_kernel_time_repeat_count_median=3.0`,
`gpu_kernel_ms_total_median=253.576187`, and
`gpu_kernel_timed_launch_count_median=7.0`. The report intentionally marks
CPU/serial wall comparison invalid with
`timing_comparison_scope=in_process_hybrid_repeat_diagnostic`, because three
GPU sidecar repeats inside one process are not comparable to one CPU RTLMeter
run. This suggests context reuse alone does not uncover a large hidden kernel
speedup for tiny `hello`; the next path is a less tiny workload/general
non-`hello` trace or deeper kernel/runtime work, not a speedup claim.
FC-059 / #59 remains the native Verilator shim-entry track, but it is not the
current pointer in `config/selection.json`.

The frontend-neutral research target is:

```sh
gpu-sidecar --frontend verilator -f filelist.f --top-module top
gpu-sidecar --frontend circt -f filelist.f --top-module top
```

Those commands are a direction, not current user-facing support.

## Measured Speedup

The reviewed timing evidence is scoped to repo-owned RTL harnesses and
filelist-derived templates, not arbitrary RTL or production serving. The
accepted repeat-median gate is:

```sh
python3 src/tools/run_results_reproduction.py --filelist-shape-breadth-repeat-median 3
```

That gate ran 3 samples for each listed shape, required
`coverage_output_equivalence`, and recorded max coverage-output mismatch count
`0`. The strongest result is state-parallel execution, where many independent
states are evaluated in one sidecar launch:

| Target | Shape | CPU median | Hybrid wall median | CPU / hybrid wall |
|---|---:|---:|---:|---:|
| `filelist_paged_attention_kv_score` | `32x1` | `76.6105 ms` | `1.113 ms` | `68.83x` |
| `filelist_known_template_pulp_ita_mha` | `32x1` | `69.0012 ms` | `0.907 ms` | `76.08x` |

Single-state repeated-step shapes are much weaker because launch overhead is
amortized poorly:

| Target | Shape | CPU median | Hybrid wall median | CPU / hybrid wall |
|---|---:|---:|---:|---:|
| `filelist_paged_attention_kv_score` | `1x32` | `2.89261 ms` | `1.081 ms` | `2.68x` |
| `filelist_known_template_pulp_ita_mha` | `1x32` | `8.29498 ms` | `1.237 ms` | `6.71x` |

Read these as scoped repeat-count-3 evidence for two reviewed templates. They
do not prove general `verilator --use-gpu`, RTLMeter acceleration, automatic GPU
allocation, arbitrary filelist dependency inference, or production throughput.
If CUDA driver access is blocked, the same flows should fail closed rather than
falling back to CPU and reporting a GPU speedup.

For RTLMeter, the target is to keep the RTLMeter workflow intact. A user should
be able to start from RTLMeter's own case selection and add GPU intent through
the existing Verilator command path.

The repo-owned wrapper can be materialized as a generated `verilator` command
for PATH testing:

```sh
python3 -c 'from src.tools.rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper; write_rtlmeter_verilator_wrapper("artifacts/rtlmeter-wrapper/verilator")'
PYTHONPATH="$PWD/third_party/rtlmeter:$PYTHONPATH" PATH="$PWD/artifacts/rtlmeter-wrapper:$PATH" third_party/rtlmeter/rtlmeter run --cases OpenTitan:default:<test> --compileArgs "--use-gpu"
```

If the real Verilator is not later on `PATH`, set
`RTLMETER_REAL_VERILATOR=/path/to/real/verilator`. The wrapper excludes itself
when resolving the real Verilator. No-GPU argv is delegated with the real
process behavior preserved. Broad GPU-intent argv still fails closed; the
current exception is the scoped `Example:kind:hello` first-seed stdout/cycles
handoff proof described below.

Those RTLMeter commands are a usability target, not a current broad support
claim. Compiling RTLMeter, compiling a copied RTLMeter-derived harness, or
selecting a repo-specific `config/slice_launch_templates/*.json` file is not
enough to claim RTLMeter acceleration. Unsupported RTLMeter cases should fail
closed with a clear diagnostic.

The first executing RTLMeter gate is intentionally opt-in and fail-closed:

```sh
python3 src/tools/rtlmeter_cpu_gpu_compare_integration.py --write-report
RTLMETER_CPU_GPU_COMPARE_EXECUTE=1 \
  python3 src/tools/rtlmeter_cpu_gpu_compare_integration.py --execute --write-report
```

The default command emits a non-executing report schema. The opt-in command
writes `reports/rtlmeter_example_kind_hello_cpu_gpu_compare.json`. If
`RTLMETER_SIDECAR_VERILATOR_WRAPPER=/path/to/verilator` is omitted, it
materializes an ignored wrapper under `artifacts/` that delegates non-GPU
Verilator argv to the real Verilator and fails closed for GPU intent. A
sidecar-capable wrapper can be supplied with that env var when available.
Treat `RTLMETER_SIDECAR_VERILATOR_WRAPPER` as the `verilator` command that
RTLMeter sees. Treat `RTLMETER_REAL_VERILATOR` as the non-wrapper Verilator
binary used behind that wrapper; it must be sidecar-capable for the expanded
argv below, or the compare report classifies the blocker as
`real_verilator_not_sidecar_capable_for_expanded_rtlmeter_argv`.
The generated report includes a `real_verilator_preflight` block so operators
can distinguish an absent non-wrapper Verilator from a selected Verilator that
later rejects the expanded sidecar argv.
The helper's default GPU candidate uses the current native-minimum schedule
spelling, `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1`;
`--compile-args` can override it for compatibility checks. Missing RTLMeter or
sidecar prerequisites produce `cannot_execute` or `gpu_execution_failed`, not a
CPU-as-GPU fallback.
Expanded-schedule failures include metadata for the captured schedule, preserved
parser inputs, and sidecar-owned context. That metadata is diagnostic only and
does not launch a repo-owned template as RTLMeter GPU evidence. For
`Example:kind:hello`, the authority registry now carries reviewed stdout/cycles
source-closure authority. The opt-in compare now executes the GPU candidate
through `src/tools/rtlmeter_stdout_cycles_sidecar_runner.py` before observing
stdout/cycles outputs. For the first seed, the latest real opt-in run reaches
`status=passed` and `comparison=passed` with marker-backed
`execution_authority=true`, while keeping `gpu_execution_claimed=false` and
`speedup_claimed=false`. That proxy/marker handoff lane is now frozen under the
native Verilator sidecar goal; it is retained as first-seed handoff evidence, not
as the current GPU execution closure path. The current RTLMeter correctness gate
is FC-064 / GitHub #63 for the `VeeR-EL2:default:hello` direct sidecar bridge.
FC-058 / GitHub #58 remains related native-path context after FC-057, but it is
not the active RTLMeter VeeR blocker. This is not an RTLMeter acceleration
claim, not a broad GPU runtime claim, not a slice `run_hybrid_template.py`
launch template, and not a CPU fallback.
The compare helper now builds an RTLMeter sidecar context candidate from the
selected seed and passes it to the wrapper through `RTLMETER_SIDECAR_CONTEXT_JSON`.
That narrows the missing context list, but the env payload is still diagnostic
handoff metadata, not a runtime ABI or acceleration evidence.

For the current VeeR-EL2 design-CPU investigation, use the native make-driver
inspection path to separate recognized closure evidence from GPU usefulness:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  inspect-veer-el2-state-layout --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --rtlmeter-program-hex artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/VeeR-EL2/default/execute-0/hello/program.hex \
  --summary-out reports/rtlmeter_veer_el2_state_layout_inspection.json
```

This command is expected to fail closed until the VeeR-EL2 GPU state-image
materializer runs and the direct sidecar execution bridge is reviewed.
The `--rtlmeter-program-hex` argument lets the inspection verify that RTLMeter's
observed program preload matches a reviewed VeeR-EL2 preload hash. Reviewed
programs currently cover `hello`, `cmark`, `cmark_iccm`, and `dhry`; arbitrary
or mismatched `program.hex` inputs still fail closed. The inspection also
detects the mailbox stdout/pass-fail source from generated C++ expressions when
`mailbox_data` is optimized away as a root field. It does not claim GPU
execution, timing, or speedup. The same inspection verifies the reviewed VeeR-EL2
PC/GPR schema, the reviewed ICCM/DCCM 4-bank ECC preload schema, and the
reviewed GPU state-image initialization schema against the generated root
header and testbench/generated-C++ markers, and verifies the reviewed
RTLMeter stdout/cycles compare binding without executing it.

To materialize the reviewed extracted state image for the same VeeR-EL2 case:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  materialize-veer-el2-state-image --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --rtlmeter-program-hex artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/VeeR-EL2/default/execute-0/hello/program.hex \
  --state-image-out artifacts/veer_el2_direct_verilator_sidecar_probe/veer_el2_extracted_state_image.json \
  --summary-out reports/rtlmeter_veer_el2_state_image_materializer.json
```

That materializer writes a reproducible extracted state-image artifact with
program staging sections and derived ICCM/DCCM bank sections. For the current
`hello` program, the ICCM/DCCM preload sentinels are absent, so both bank
preloads are inactive and have zero nonzero entries. This still does not claim
GPU execution, timing, or speedup; the direct VeeR-EL2 sidecar execution bridge
and a reviewed GPU run remain required before GPU usefulness can be measured.

To run the direct VeeR-EL2 sidecar observable bridge against the generated GPU
metadata:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/verilator_native_sidecar_make_driver.py \
  run-veer-el2-sidecar-bridge --repo-root . \
  --filelist artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/gpu/VeeR-EL2/default/compile-0/filelist \
  --top-module tb_top \
  --mdir artifacts/veer_el2_direct_verilator_sidecar_probe/obj_dir \
  --state-image artifacts/veer_el2_direct_verilator_sidecar_probe/veer_el2_extracted_state_image.json \
  --cpu-execute-dir artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/VeeR-EL2/default/execute-0/hello \
  --sidecar-execute-dir artifacts/veer_el2_direct_verilator_sidecar_probe/sidecar_execute/hello \
  --sidecar-executable src/tools/veer_el2_sidecar_executable.py \
  --summary-out reports/rtlmeter_veer_el2_sidecar_bridge.json
```

The bridge does not copy CPU observables into the sidecar output. The reviewed
executable consumes `VEER_EL2_SIDECAR_STATE_IMAGE`, materializes a syms-state
init image, launches `vl_batch_gpu.cubin`, dumps GPU state, and emits sidecar
stdout/cycles files. The current VeeR `obj_dir` builds `vl_batch_gpu.cubin` with
`storage_size=433472` using a `verilator_syms_image`; `vl_batch_gpu.meta.json`
reports `prelaunch_rejection_required=false` and
`unsafe_syms_gep_covered_by_state_image=true`. The bridge now reaches
`sidecar_observables_ready=true`, drives a VeeR clock/reset patch, and produces
GPU final-state observables `mcycle=726`, `minstret=330`, and
`finish_marker_observed=true`. The GPU mailbox trace reconstructs normalized
stdout to match the CPU reference, and the sidecar `_rtlmeter_cycles.txt` now
uses RTLMeter's `tb_top.core_clk` count rather than the VeeR architectural
`mcycle`. The bridge reaches
`status=verilator_native_sidecar_veer_el2_stdout_cycles_compare_passed` with
`cpu_cycles=2229` and `gpu_cycles=2229`. Timing and usefulness remain
measured separately by FC-037; correctness alone is not usefulness evidence.

To regenerate the current VeeR-EL2 timing/usefulness report:

```sh
RTLMETER_CPU_PARALLEL_BASELINE_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_cpu_parallel_baseline.py \
    --cases VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
            VeeR-EL2:default:hello VeeR-EL2:default:hello \
    --compile-root artifacts/design_cpu_state_parallel_probe/veer_el2_serial \
    --artifact-root artifacts/rtlmeter_cpu_parallel_hello16_baseline \
    --max-workers 16 --timeout 10 --write-report \
    --report-out reports/rtlmeter_cpu_parallel_hello16_baseline.json

RTLMETER_VEER_EL2_TIMING_EXECUTE=1 PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_el2_timing.py \
    --samples 7 --batches 3 --sidecar-nstates 16 \
    --cpu-parallel-report reports/rtlmeter_cpu_parallel_hello16_baseline.json \
    --write-report --report-out reports/rtlmeter_veer_el2_timing_nstates16.json
```

The report at `reports/rtlmeter_veer_el2_timing_nstates16.json` records 21 passing
sidecar correctness samples across three seven-sample batches, serial CPU
elapsed `0.04s`, comparable CPU-parallel wall `2.218887s`, sidecar wall median
`0.768573s`, GPU kernel total median `268.161011ms`,
`sidecar_vs_cpu_parallel_ratio=2.887022`, bridge preflight median `0.000406s`,
`sidecar_executable_invocation_mode_counts={"in_process_veer_el2_sidecar": 21}`,
`nstates=16` all-state clock/reset patching, all-state final observable
validation, coalesced device-buffered DtoD step-trace copies
(`step_trace_copy_mode_counts={"device_buffered_coalesced_d2d_trace": 21}`)
with high-phase filtering
(`step_trace_filter_counts={"start=4,stride=2": 21}`,
`step_trace_filter_rows_median=727.0`, capacity median `1457.0`,
`resident_patch_records_median=69936.0`), rising-edge
mailbox reconstruction, and final counter fallback,
device-resident patch scheduling, and
`timing_stability_outcome=stable_repeated_batch_outcome`.
`gpu_cpu_parallel_comparison_valid=true`, but `speedup_claimed=false`.

To aggregate RTLMeter favorable/unfavorable evidence across CPU-parallel,
GPU-sidecar timing, launch-feasibility, and bounded-progress reports:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/rtlmeter_hybrid_advantage.py \
  --report reports/rtlmeter_cpu_parallel_hello16_baseline.json \
  --report reports/rtlmeter_veer_el2_timing_nstates16.json \
  --report reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json \
  --report reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json \
  --report reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json \
  --report reports/rtlmeter_veer_el2_timing_cmark_launch_feasibility.json \
  --report reports/rtlmeter_veer_el2_non_hello_bounded_progress_summary.json \
  --write-report --report-out reports/rtlmeter_hybrid_advantage_summary.json
```

The current aggregate classifies one CPU-parallel baseline as favorable, four
GPU-sidecar timing reports as unfavorable against their CPU-parallel comparison,
one launch-feasibility blocker, and one bounded-progress GPU report. The
recommended hybrid action is
`prefer_cpu_parallel_control_with_gpu_bounded_batch_probes`; this is a
measurement index, not a new speedup claim.

To summarize non-VeeR RTLMeter usefulness candidates from descriptors and
existing NVDLA hybrid evidence:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_non_veer_usefulness_candidates.py \
    --write-report \
    --report-out reports/rtlmeter_non_veer_usefulness_candidates.json
```

The current non-VeeR summary records NVDLA as the measured candidate:
`measured_shape_count=20`, `gpu_favorable_shape_count=20`, best observed wall
speedup `11764.742765273311x` at `1024x64` for `nvdla_cmac_a2cacc`. Vortex is
now a fail-closed first-gate candidate: `mini` exposes `hello`, `sgemm`, and
`saxpy`, the `hello` bridge inputs and helper plan are reviewed, but there is no
CPU-vs-hybrid measurement yet. The recommended next step is
`refresh_or_extend_nvdla_cmac_core_mac_repeat_median_before_vortex`.

To quantify the non-VeeR hybrid split from the same evidence:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_non_veer_hybrid_measurement_summary.py \
    --write-report \
    --report-out reports/rtlmeter_non_veer_hybrid_measurement_summary.json
```

The current split report records `measured_design_count=2`,
`measured_shape_count=20`, `gpu_favorable_shape_count=20`, and
`unmeasured_first_gate_candidate_count=2`. NVDLA is classified as the measured
hot-SS path with `favorable_ratio=1.0`; Vortex remains
`fail_closed_first_gate_no_cpu_vs_hybrid_measurement` with no CPU-vs-hybrid
timing present. Its recommendation is
`extend_nvdla_hot_ss_measurement_before_claiming_broader_rtlmeter_gpu_usefulness`.

To turn that split into an ordered next-measurement queue:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_non_veer_hybrid_next_queue.py \
    --summary reports/rtlmeter_non_veer_hybrid_measurement_summary.json \
    --write-report \
    --report-out reports/rtlmeter_non_veer_hybrid_next_queue.json
```

The current queue sets `nvdla_hot_ss_measurement_extension` as top priority:
repeat or extend the best observed NVDLA hot-SS bucket,
`state_batch_and_repeated_step`, with preferred measured shape `1024x64` on
`nvdla_cmac_a2cacc`. Vortex remains priority 2 as
`vortex_mini_hello_first_cpu_vs_hybrid_gate`; its first current blocker is
debugging the generated real Vortex PTX module load/JIT path: the materialized
real-CUDA path now uses the root-storage callback, reaches
`before_cuModuleLoad`, and times out before function lookup, kernel launch,
observable export, or timing.
This queue is a planning index only, not a scheduler, runtime ABI, new
measurement, or speedup claim.

To materialize the concrete NVDLA hot-SS measurement-extension plan from that
queue:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_nvdla_hot_ss_measurement_plan.py \
    --queue reports/rtlmeter_non_veer_hybrid_next_queue.json \
    --write-report \
    --report-out reports/rtlmeter_nvdla_hot_ss_measurement_plan.json
```

The current plan is `planned_not_run` and targets only
`NVDLA.nvdla_cmac_a2cacc`. It proposes four repeat-median measurements:
confirm `1024x64`, check `512x64`, probe `2048x64`, and separate the
state-batch effect with `1024x1`. `NVDLA.nvdla_cmac_core_mac` remains deferred
because the latest local `32x1` refresh hit high `ptxas` compile cost; Vortex
remains deferred until the first-gate runtime authority is wired.

To preflight the plan without running repeat-median measurements:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_nvdla_hot_ss_plan_dry_run.py \
    --plan reports/rtlmeter_nvdla_hot_ss_measurement_plan.json \
    --write-report \
    --report-out reports/rtlmeter_nvdla_hot_ss_plan_dry_run.json
```

The current preflight passes all four dry-runs. The first plan item has also
been measured with:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/hybrid_template_repeat_median.py \
    config/slice_launch_templates/nvdla_cmac_a2cacc.json \
    --shape 1024x64 \
    --repeat 3 \
    --write-report \
    --report-out reports/nvdla_cmac_a2cacc_repeat_median_1024x64.json
```

That repeat-median report records `coverage_output_equivalence_all_passed=true`
with coverage-output mismatch count `0` in all three samples. The median CPU
time is `2142.1 ms`, median hybrid wall time is `1.755 ms`, and median
CPU/hybrid wall speedup is `1430.950752393981x`. Raw final-state byte equality
still fails because Verilator internal fields differ; the accepted policy is
coverage-output equivalence.

The lower-neighbor `512x64` repeat-median report
`reports/nvdla_cmac_a2cacc_repeat_median_512x64.json` also passes
coverage-output equivalence for all three samples, with median CPU `1056.75 ms`,
median hybrid wall `1.602 ms`, and median CPU/hybrid wall speedup
`663.2209737827715x`. The larger-state `2048x64` repeat-median report
`reports/nvdla_cmac_a2cacc_repeat_median_2048x64.json` also passes
coverage-output equivalence for all three samples, with median CPU `4244.47 ms`,
median hybrid wall `1.662 ms`, and median CPU/hybrid wall speedup
`2553.8327316486166x`. The state-batch-only `1024x1` repeat-median report
`reports/nvdla_cmac_a2cacc_repeat_median_1024x1.json` also passes
coverage-output equivalence for all three samples, with median CPU `2090.2 ms`,
median hybrid wall `2.628 ms`, and median CPU/hybrid wall speedup
`791.3432267884323x`. To summarize plan progress:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_nvdla_hot_ss_repeat_summary.py \
    --plan reports/rtlmeter_nvdla_hot_ss_measurement_plan.json \
    --write-report \
    --report-out reports/rtlmeter_nvdla_hot_ss_repeat_summary.json
```

The current summary records `planned_measurement_count=4`, `measured_count=4`,
`coverage_passed_count=4`, and `gpu_favorable_count=4`; `2048x64` is the best
measured shape in this plan. The `1024x1` result shows that state batching alone
is already favorable, while repeated-step batching improves the best observed
wall ratio further.

To audit the goal of finding GPU-favorable RTLMeter conditions beyond VeeR
portability evidence:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_gpu_favorable_conditions_audit.py \
    --write-report \
    --report-out reports/rtlmeter_gpu_favorable_conditions_audit.json
```

The current audit reports `goal_satisfied_by_nvdla_hot_ss`: NVDLA `a2cacc`
has all four planned hot-SS measurements completed, coverage-output-equivalent,
and GPU-favorable by wall time. Vortex remains the architecture-diverse follow-up
because its first CPU-vs-hybrid timing gate is now measured but slower than the CPU reference.

To inspect the first Vortex measurement gate readiness:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_first_gate_readiness.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_first_gate_readiness.json
```

To review the Vortex DPI memory bridge boundary that blocks that gate:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_dpi_memory_bridge_review.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_dpi_memory_bridge_review.json
```

To validate the descriptor-owned Vortex source closure without granting runtime
launch authority:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_source_closure.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_source_closure.json
```

To summarize the concrete `Vortex:mini:hello` binary inputs consumed by that
bridge:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_binary_input_summary.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_binary_input_summary.json
```

To derive the GPU memory-model ABI plan from those parsed inputs:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_gpu_memory_model_plan.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_gpu_memory_model_plan.json
```

To validate the Python reference semantics for the same Vortex DPI memory
contract:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_memory_model_reference.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_memory_model_reference.json
```

To materialize the host-side device-buffer blobs that a Vortex hybrid runtime
would upload:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_device_buffer_materialize.py \
    --artifact-dir artifacts/rtlmeter_vortex_mini_hello_device_buffers \
    --write-report \
    --report-out reports/rtlmeter_vortex_device_buffer_materialize.json
```

To materialize the ordered Vortex DCR schedule and reset/valid timing semantics
from `dcrs.bin`:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_dcr_schedule.py \
    --artifact-dir artifacts/rtlmeter_vortex_mini_hello_dcr_schedule \
    --write-report \
    --report-out reports/rtlmeter_vortex_dcr_schedule.json
```

To review the fail-closed Vortex runtime sequence invocation plan after the
bridge review report exists:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_runtime_invocation_plan.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_runtime_invocation_plan.json
```

To review the lowered-TB-side runtime sequence invocation smoke boundary:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_lowered_tb_invocation_smoke.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_lowered_tb_invocation_smoke.json
```

To validate that the materialized `Vortex:mini:hello` buffers and DCR schedule
are ready for that runtime-sequence boundary:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_materialized_runtime_invocation_smoke.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json
```

To validate that generated lowered-TB-shaped C code can consume the real
materialized `Vortex:mini:hello` buffer artifacts and call the runtime-sequence
boundary:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json
```

To validate that generated lowered-TB-shaped memory accesses consume the real
materialized `Vortex:mini:hello` buffers through the device memory helper:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json
```

To run and summarize the native RTLMeter CPU reference for the same first gate:

```sh
PYTHONPATH="$PWD/third_party/rtlmeter:$PYTHONPATH" \
  third_party/rtlmeter/rtlmeter run \
    --cases Vortex:mini:hello \
    --workRoot artifacts/rtlmeter_vortex_mini_hello_cpu_reference \
    --timeout 5 \
    --verbose

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_cpu_reference_summary.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_cpu_reference_summary.json
```

To record the current fail-closed hybrid candidate attempt:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_sidecar_context.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_sidecar_context.json

python3 -c 'from src.tools.rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper; write_rtlmeter_verilator_wrapper("artifacts/rtlmeter_vortex_wrapper/verilator")'

RTLMETER_SIDECAR_CONTEXT_JSON="$(cat reports/rtlmeter_vortex_sidecar_context.json)" \
  PYTHONPATH="$PWD/third_party/rtlmeter:$PYTHONPATH" \
  PATH="$PWD/artifacts/rtlmeter_vortex_wrapper:$PATH" \
  RTLMETER_REAL_VERILATOR=/usr/local/bin/verilator \
  third_party/rtlmeter/rtlmeter run \
    --cases Vortex:mini:hello \
    --workRoot artifacts/rtlmeter_vortex_mini_hello_hybrid_candidate_context_report \
    --compileArgs "--sim-accel sidecar-gpu --sim-accel-states 1 --sim-accel-steps 1" \
    --timeout 5 \
    --verbose

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_hybrid_candidate_summary.py \
    --work-root artifacts/rtlmeter_vortex_mini_hello_hybrid_candidate_context_report \
    --write-report \
    --report-out reports/rtlmeter_vortex_hybrid_candidate_summary.json
```

The current readiness report selects `Vortex:mini:hello` as the first Vortex
gate because its `dcrs.bin`, `init.bin`, and `post.bin` inputs exist and the
descriptor marks `hello` as the `mini` sanity case. The fail-closed authority
`config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json` now
exists with `runtime_launchable=false`; it defines the intended stdout
`TEST PASSED` plus memory `post.bin` authority without granting execution
authority. The fail-closed launch template
`config/slice_launch_templates/vortex_mini_hello.json` now exists with
`runtime_launchable=false`, `source_closure.status=incomplete`, and
`speedup_claim_allowed_by_template_alone=false`; non-dry-run execution refuses
at the source-closure gate until the DPI/runtime bridge is integrated.
`reports/rtlmeter_vortex_source_closure.json` now validates the descriptor-owned
source closure: all `126` Verilog sources, `8` include files, and `1` CPP DPI
source exist locally, but runtime launch authority remains false. The gate still
blocks before a measurement because CPU-vs-hybrid timing evidence and GPU bridge
implementation are missing. The bridge review confirms
the CPU authority uses `mem_load(init.bin)`, `dcrs.bin` DCR writes, 64-byte
block memory access with byte enables, MMIO stdout at `IO_COUT_ADDR=0x40`, and
`mem_check(post.bin)` before stdout `TEST PASSED`. The host-compilable
`src/hybrid/vortex_memory_model_device.h` helper now covers 64-byte block init,
byte-enable writes, IO_COUT capture, and post compare semantics; remaining work
is generated lowered-TB integration, invoking the lowered-TB runtime sequence
shim, and reporting stdout or memory post-condition authority. The runtime upload helper in `src/hybrid/vortex_runtime_upload.h`
is fake-driver tested for `cuMemAlloc`, `cuMemcpyHtoD`, `cuMemsetD8`, cleanup,
and the `37224` H2D / `88` D2H byte accounting.
`src/hybrid/vortex_observable_export.h` is fake-driver tested for
`cuMemcpyDtoH` export of `post_compare_result`, memory post-condition PASS/FAIL,
optional raw stdout bytes, `TEST PASSED` detection, and host-side authority
source selection. `src/hybrid/vortex_runtime_sequence.h` is fake-driver tested
for the host/runtime sequence boundary: upload the materialized buffers, apply
the ordered DCR writes while reset is asserted, call a kernel-launch callback,
export observables, and release runtime buffers. The remaining Vortex blocker is
now debugging the real kernel artifact after callback wiring: the generated
Vsim path invokes the materialized real-CUDA sequence with
`rtlmeter_vortex_real_cuda_launch_root_storage_kernel`,
`vl_batch_gpu.ptx` plus `vl_batch_gpu.meta.json` exist, and the callback
preflight records the root-storage launch ABI as ready, but the real-CUDA smoke
times out before proxy handoff. `reports/rtlmeter_vortex_runtime_invocation_plan.json`
checks that the fail-closed launch template names `vortex_run_runtime_sequence`,
the required upload/DCR/launch/export/release order, and the runtime-sequence
header; it is a template plan only and does not invoke the lowered Vortex path.
`src/hybrid/vortex_lowered_tb_runtime_sequence.h` is fake-driver tested as the
thin lowered-TB-side call boundary, and
`reports/rtlmeter_vortex_lowered_tb_invocation_smoke.json` records that smoke as
ready but not integrated.
`reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json` now
validates the real materialized `hello` runtime inputs against that boundary:
all `7` buffer artifacts exist, H2D bytes are `37224`, initial D2H bytes are
`88`, the `9` DCR writes match the materialized little-endian schedule, and the
lowered-TB sequence-call header exposes authority fields. This is still not GPU
execution, generated lowered-TB integration, observable authority, timing, or a
speedup claim. The next blocker is building a real Vortex kernel artifact from
lowered IR is now cleared; the current build attempt generates `vl_batch_gpu.ptx`
and `vl_batch_gpu.meta.json`. The remaining blocker is wiring that artifact into
the materialized runtime callback with a root-storage launch ABI.
`reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json` now
compiles and runs generated C harness code against those real materialized
artifacts and records `generated_lowered_tb_invocation_smoke_passed=true`,
`host_to_device_bytes=37224`, `device_to_host_initial_bytes=88`, and
`dcr_write_count=9`. This narrows the gap to real Verilator generated lowered-TB
integration, but still does not prove Vortex GPU execution, observable
authority, CPU-vs-hybrid timing, or speedup.
`reports/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json` now
compiles and runs generated lowered-TB-shaped C code that consumes the same
materialized artifacts through `vortex_memory_model_device.h`: it initializes
`576` memory blocks, observes `48` initial post mismatches, replays the post
condition through byte-enable writes to reach `0` mismatches, and captures
`12` `TEST PASSED\n` stdout bytes through IO_COUT. This removes the generic
helper-integration smoke gap, but it is still not real Verilator generated
lowered-TB integration, GPU execution, observable authority, timing, or speedup.
`reports/rtlmeter_vortex_cpu_reference_summary.json` now records the native
RTLMeter CPU reference for `Vortex:mini:hello`: `TEST PASSED`, Verilog
`$finish`, post hook success, `9` DCR writes, `40897` execute clocks,
`execute_elapsed_s=0.22`, and `execute_speed_khz=185.89545454545453`. This is
the CPU side of the comparison only. `reports/rtlmeter_vortex_hybrid_candidate_summary.json`
records the current hybrid candidate as fail-closed before measurement after
the PATH-selected wrapper captures `--sim-accel sidecar-gpu`,
`--sim-accel-states 1`, and `--sim-accel-steps 1`. With Vortex sidecar context
provided, the wrapper reaches `rtlmeter_sidecar_handoff_metadata_ready`, strips
wrapper-only `--sim-accel*` options before calling real Verilator, and the direct
native runner now reaches RTLMeter stdout/cycles observation for
`Vortex:mini:hello`: `cycle_count=40897` with `TEST PASSED`. A reviewed Vsim
sidecar proxy target is now exercised through the patched `Vsim__main.cpp`
source path, and the current summary status is
`hybrid_candidate_proxy_handoff_observed_timing_missing`. This is still not
GPU execution: `rtlmeter_proxy_handoff_observed=true`, but
`gpu_execution_claimed=false`, `timing_measured=false`, and
`speedup_claimed=false`. The next blocker is wiring the generated Vortex PTX
artifact into the materialized runtime callback, including the root-storage
launch ABI, followed by real kernel launch/export authority and CPU-vs-hybrid
timing.
The parsed `hello`
input has `9` init memory segments totaling `36864` bytes over
`0x10000..0x80008000`, `1` post segment of `48` bytes, and `9` DCR writes. The
ABI plan reduces this to `7` planned device buffers, `576` init 64-byte blocks,
and `37224` bytes of minimum static input tables/payloads. The materialized
buffers have `37224` host-to-device bytes and `88` initial device-to-host bytes under
`artifacts/rtlmeter_vortex_mini_hello_device_buffers`; this is host-side buffer
preparation, not device upload or GPU execution.
`reports/rtlmeter_vortex_dcr_schedule.json` now materializes the `9` DCR writes
as a `72` byte little-endian runtime table and records the `tb.sv` protocol:
reset remains asserted, each write holds `dcr_wr_valid` high for `#10`, the
between-write low interval is only a delta cycle, and the final write is
followed by `#10` with valid low before reset deassert. This is schedule
materialization only; the sequence helper contract covers the call ordering, but
runtime execution still has to invoke it from the Vortex lowered path. The
reference report now
reaches `reference_validated`: the
loaded initial memory does not match `post.bin` (`48` mismatches over `48`
checked bytes), a byte-enabled post replay reproduces `post.bin`, and IO_COUT
writes are captured without mutating RAM. This is still a Python reference
semantics check, not Vortex GPU execution, CPU-vs-hybrid timing, or a speedup
claim.
Try `mini:saxpy` or `mini:sgemm` only after this first `hello` gate exists.

To summarize the active `Vortex:mini:hello` plus VeeR EH1/EH2/EL2 hybrid
measurement objective in one table:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_veer_hybrid_measurement_matrix.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_veer_hybrid_measurement_matrix.json \
    --markdown
```

To summarize why each row is difficult to measure before treating any timing as
evidence:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_hybrid_measurement_difficulty.py \
    --write-report \
    --report-out reports/rtlmeter_hybrid_measurement_difficulty.json \
    --markdown-out reports/rtlmeter_hybrid_measurement_difficulty.md
```

To strip the Vortex generated-main runtime marker and expected-fail invocation
probe after the materialized runtime-args probe has been established:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vsim_main_vortex_probe_marker_strip.py \
    --write-report \
    --report-out reports/rtlmeter_vsim_main_vortex_probe_marker_strip.json

make -C artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir \
  -f Vsim.mk Vsim
```

To replace the materialized runtime-args callback table with real CUDA Driver
API callbacks and verify that the generated `Vsim` reaches the proxy handoff
from its `obj_dir` cwd:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch.py \
    --write-report \
    --report-out reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_patch.json

make -C artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir \
  -f Vsim.mk Vsim

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.py \
    --write-report \
    --report-out reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.json
```

To check whether a real Vortex kernel artifact exists, and to record the
current build-attempt blocker:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_real_kernel_artifact_preflight.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_real_kernel_artifact_preflight.json

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_kernel_artifact_build_attempt.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_kernel_artifact_build_attempt.json

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_vortex_kernel_callback_preflight.py \
    --write-report \
    --report-out reports/rtlmeter_vortex_kernel_callback_preflight.json
```

The current preflight finds `vl_batch_gpu.ptx` and `vl_batch_gpu.meta.json` for
`Vortex:mini:hello`, with `kernel_artifact_format=ptx`. The build attempt runs
`src/tools/build_vl_gpu.py ... --emit-ptx-module` and now passes after preserving
personality on functions that still contain EH pads. A syms-state-image rebuild
now records `state_image_kind=verilator_syms_image`,
`root_offset_in_state=192`, `storage_size=80768`, and
`prelaunch_rejection_required=false` under the generated hierarchy metadata.
The next Vortex boundary is therefore wiring a root-storage-backed
`vl_eval_batch_gpu` callback:
`reports/rtlmeter_vortex_kernel_callback_preflight.json` records
`status=blocked_by_missing_root_storage_launch_callback`. Artifact presence is
still not kernel execution, observable authority, timing, or a speedup claim.

To audit why the measured VeeR-EL2 sidecar path cannot be directly reused for
EH1/EH2:

```sh
PYTHONPATH="$PWD/third_party/rtlmeter:$PYTHONPATH" \
  third_party/rtlmeter/rtlmeter run \
    --cases VeeR-EH1:default:hello \
    --workRoot artifacts/rtlmeter_veer_eh1_cpu_reference_mailbox_public_flat \
    --timeout 5 \
    --verbose

PYTHONPATH="$PWD/third_party/rtlmeter:$PYTHONPATH" \
  third_party/rtlmeter/rtlmeter run \
    --cases VeeR-EH2:default:hello \
    --workRoot artifacts/rtlmeter_veer_eh2_cpu_reference_mailbox_public_flat \
    --timeout 5 \
    --verbose

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_family_cpu_reference_summary.py \
    --design VeeR-EH1 \
    --write-report \
    --report-out reports/rtlmeter_veer_eh1_cpu_reference_summary.json

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_family_cpu_reference_summary.py \
    --design VeeR-EH2 \
    --write-report \
    --report-out reports/rtlmeter_veer_eh2_cpu_reference_summary.json

PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/rtlmeter_veer_family_surface_audit.py \
    --write-authorities \
    --write-state-layout-preflight \
    --write-state-images \
    --write-root-offset-review \
    --write-sidecar-executable-review \
    --write-sidecar-bridge-preflight \
    --write-report \
    --report-out reports/rtlmeter_veer_family_surface_audit.json \
    --markdown
```

The current matrix is intentionally incomplete: `VeeR-EL2:default:hello` is the
only measured VeeR row, with best current timing evidence from
`reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json`
(`sidecar_wall_s_median=0.641226`, `sidecar_vs_cpu_parallel_ratio=3.460382`,
correctness passed, no speedup claim). The Markdown table also surfaces the
current Vortex runner evidence directly: `cycles=40897`,
`proxy_handoff=true`, `fake_authority=true`,
`runtime_stub_rebuilt=true`, `runtime_bridge_stub_rebuilt=true`,
`materialized_runtime_args_probe_executed=true`,
`real_cuda_materialized_smoke=true`,
`real_cuda_materialized_args_call=true`,
`cuda_memory_transport=true`, `cuda_runtime_sequence_preflight=true`,
`preflight_authority=true:memory_post_condition`,
`dpi_memory_helper=true`, `probe_marker_block=true`, and `gpu=False`;
for EH1/EH2 it also surfaces `root_probe=True`, `offset_probe=True`,
`marker_groups=5`, `offset_groups=5`, `offsets_reviewed=True`,
`root_variant=mailbox_public_flat`, and `offset_review_ready=True`. It also
folds each EH bridge preflight's `missing_build_context` into the row-level
missing list, so EH1/EH2 now expose `executed_bridge_comparison` before timing.
The
corresponding audit keeps
`real_runtime_observable_authority=false`, so the review table distinguishes
proxy/fake-driver/generated-main, real CUDA memory-transport, and real CUDA
runtime-sequence preflight evidence from real Vortex kernel execution or timing.
The Vortex first timing gate is now measured:
`reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.json`
uses the canonical `vlgpugen` std::ref pointer-return fix CUBIN at
`artifacts/rtlmeter_vortex_vlgpugen_std_ref_fix_probe/vl_eval_batch_gpu.cubin`,
relocates `65` root-storage pointers, reaches `after_cuCtxSynchronize`, and
exports `memory_post_condition` authority. `reports/rtlmeter_vortex_timing.json`
then records `3` authority-passing repeats: CPU reference `0.22s` / `40897`
clocks versus hybrid wall median `0.4504947270033881s`, so
`hybrid_vs_cpu_ratio=2.047703304560855` and
`cpu_vs_hybrid_speedup=0.48835199795434103`. This is a measured negative
Vortex `mini:hello` gate, not a speedup claim. The generated difficulty view now
shows Vortex measured/low with blocker `measured_hybrid_slower_than_cpu_reference`;
EH1/EH2 remain high-difficulty unmeasured rows, and EL2 remains a measured
negative portability baseline.

To reproduce the Vortex timing gate after rebuilding the patched `Vsim`, run:

```sh
python3 src/tools/rtlmeter_vortex_timing.py \
  --repo-root . \
  --repeats 3 \
  --timeout-seconds 60 \
  --write-report \
  --report-out reports/rtlmeter_vortex_timing.json
```
`Vortex:mini:hello` now has direct-native RTLMeter stdout/cycles observation
(`40897` cycles, `TEST PASSED`), reviewed proxy handoff, canonical real-CUDA
materialized runtime authority, and a CPU-vs-hybrid timing report. The result
is negative for speedup, so the active remaining measurement work is EH1/EH2.
`VeeR-EH1:default:hello` and `VeeR-EH2:default:hello` are now classified by
`reports/rtlmeter_veer_family_surface_audit.json` as
`sidecar_bridge_preflight_surface_missing`: their descriptors, `tb_top`,
`core_clk`, `program.hex` preload, and mailbox/testbench surfaces are present
enough to start a design-specific port. `--write-authorities` materializes
fail-closed EH1/EH2 authority registry entries under
`config/rtlmeter_sidecar_authorities/`, `--write-state-layout-preflight` writes
fail-closed EH1/EH2 state-layout preflight reports under `reports/`, and
`--write-state-images` now writes fail-closed EH1/EH2 preload state-image
materializer reports plus artifacts. `--write-root-offset-review` writes
fail-closed EH1/EH2 root-offset candidate review reports,
`--write-sidecar-executable-review` writes fail-closed EH1/EH2 EL2-reuse review
reports, and
`--write-sidecar-bridge-preflight` writes fail-closed EH1/EH2 sidecar bridge
preflight reports. The materializer reports record
`state_image_materialized=true`, but still keep `state_layout_ready=false`,
`gpu_execution_claimed=false`, `timing_measured=false`, and
`speedup_claimed=false`; the bridge preflight reports record
`sidecar_bridge_preflight_ready=true` while keeping `sidecar_bridge_invoked=false`,
`sidecar_observables_ready=false`, `sidecar_execution_claimed=false`,
`gpu_execution_claimed=false`, `timing_measured=false`, and
`speedup_claimed=false`. EH1/EH2 CPU reference observables now pass:
`reports/rtlmeter_veer_eh1_cpu_reference_summary.json` records `1044` RTLMeter
cycles, `TEST_PASSED`, and `execute_elapsed_s=0.03`;
`reports/rtlmeter_veer_eh2_cpu_reference_summary.json` records `2325` RTLMeter
cycles, `TEST_PASSED`, and `execute_elapsed_s=0.06`. The regenerated
state-layout preflight reports now prefer the mailbox-public-flat
CPU-reference `Vsim___024root.h` headers when present: both EH1/EH2 set
`root_layout_probe_performed=true`, `root_offset_probe_performed=true`, and
`root_obj_dir_variant=mailbox_public_flat`, and therefore no longer list
`root_layout_probe` as missing. The state-layout report remains a preflight
surface, while the root-offset review now carries the selected ABI entries. It
has complete marker groups for control, PC, cycle counter, mailbox observable,
and GPR candidates on both EH1/EH2.
The bridge preflight therefore no longer lists `cpu_reference_observables`,
`complete_root_field_offset_abi_review`, or
`design_specific_sidecar_executable_implementation` as a missing build context.
After the root-offset and executable-boundary reviews, EH1 now has a generated
PTX module artifact ready for bridge execution and a bounded bridge execution
report. That bounded run materializes the root init image, writes `349` imem and
`349` lmem program bytes, writes a clock/reset patch, and invokes
`run_vl_hybrid` for `19` logical steps, and stage tracing shows CUDA init,
device lookup, and context creation pass before the run stops at
`before_cuModuleLoad`; it times out after `20s` before a GPU dump or
stdout/cycles observables are available. The bounded offline cubin probe
`reports/rtlmeter_veer_eh1_ptxas_o0_probe.json` also times out:
`ptxas --opt-level 0` on the `17,684,220` byte / `630,613` line PTX ran for
`180s`, reached `6,674,492` KB max RSS, and produced no cubin. A narrower
entry-pruned module keeps only `vl_eval_batch_gpu` and
`vl_apply_patch_schedule_gpu`: `ptxas -O0` completes in `17.98s` and emits an
`11,701,952` byte cubin, proving unused entry co-packaging caused the module
compile timeout. That cubin loads and launches, but the first synced
`vl_eval_batch_gpu` launch fails with CUDA illegal memory access before any dump
or stdout/cycles observables. EH2 also has a generated PTX
module artifact. It now uses a syms-state image (`storage_size=623168`,
`root_offset_in_state=192`) and clears
`gpu_artifact_prelaunch_rejection_required`, but the bridge times out after
`60s` at `before_cuModuleLoad` on the `44377841` byte PTX before stdout/cycles
observables. The EH sidecar bridge accepts
`VEER_EH_SIDECAR_GPU_MODULE_OVERRIDE=<module>` for bounded module-substitution
probes; using the eval+patch entry-pruned EH2 CUBIN clears module load and
kernel resolution, uploads the init state, launches the step-0 patch+eval pair,
then with `RUN_VL_HYBRID_SYNC_EACH_STEP=1` fails at `before_first_step_sync`
with `CUDA error 700`; a no-patch eval-only probe reproduces the same first
  eval launch fault, and 2MiB padded storage, a 64KiB stack limit, plus zero-init
storage do not clear it before stdout/cycles observables. Staged, inline, and
canonical probes now narrow EH2 through the post-std-ref-get-canonical
`trigger_orInto__act` destination store: entry, dst-load, src-load, and
before-store pass, then the after-store probe faults with CUDA 700.
`VlUnpacked<T,1>` index-call canonicalization rewrites `57` calls and directizes
that helper, but full eval-only still faults with CUDA 700. The matrix carries
those bridge-internal blockers into its row-level missing list. EH1/EH2
still have no passing bridge comparison or CPU-vs-hybrid timing
report. The EL2 executable is not directly reusable because
the authority target name, root-symbol/state-layout paths, and `hello`
`program.hex` SHA are EL2-specific.

| Case | Current status | Best evidence | Next blocker | Speedup claim |
|---|---|---|---|---|
| `Vortex:mini:hello` | Hybrid measured; correctness passed | CPU reference `0.22s` / `40897` clocks; canonical real-CUDA materialized runtime relocates `65` root-storage pointers, reaches `after_cuCtxSynchronize`, and exports `memory_post_condition` authority; `reports/rtlmeter_vortex_timing.json` records hybrid wall median `0.4504947270033881s` over `3` repeats, `hybrid_vs_cpu_ratio=2.047703304560855`, and `cpu_vs_hybrid_speedup=0.48835199795434103` | Treat as measured negative first gate; continue EH1/EH2 unblock/timing | No |
| `VeeR-EH1:default:hello` | Bounded bridge invoked; entry-pruned module loads but first eval launch faults | CPU reference passes (`0.03s`, `1044` RTLMeter cycles, `TEST_PASSED`); mailbox-public-flat rebuild passes; root-offset ABI review ready; full generated PTX times out at `before_cuModuleLoad` and offline `ptxas -O0` times out after `180s`; entry-pruned `vl_eval_batch_gpu` + `vl_apply_patch_schedule_gpu` cubin builds in `17.98s`, loads, resolves kernels, uploads init state, then fails with CUDA illegal memory access at the first synced `vl_eval_batch_gpu` launch; required host-I/O-stubbed probe IR now erases `47` EH1 stdout/finish/string call sites and leaves zero matching calls; regenerated host-I/O-stubbed single-entry eval CUBIN builds (`6735488` bytes, `ptxas -O0` `15.29s`) but the eval-only bridge still exits with `CUDA error 700` at first eval launch; runtime trace records `NUM_REGS=255`, `LOCAL_SIZE_BYTES=1776`, and padded 2MiB init-state still faults | Isolate remaining scheduler/container/ABI device fault, then stdout/cycles comparison and timing report | No |
| `VeeR-EH2:default:hello` | Entry-pruned CUBIN loads; first eval launch faults | CPU reference passes (`0.06s`, `2325` RTLMeter cycles, `TEST_PASSED`); mailbox-public-flat rebuild passes; root-offset ABI review ready; syms-state image PTX exists (`storage_size=623168`, `root_offset_in_state=192`, prelaunch rejection false); full PTX bridge still times out after `60s` at `before_cuModuleLoad`, but the eval+patch entry-pruned CUBIN builds with `ptxas -O0`, loads, resolves kernels, uploads init state, launches step-0 patch+eval, and with sync-each-step fails at `before_first_step_sync` with `CUDA error 700`; no-patch eval-only reproduces the same fault, and padded2m, stack64k, plus zero-init probes do not clear it; static PTX audit counts `1456` C++/Verilator runtime-residue hits and `134` suspicious function definitions; expanded host-cleanup removes scheduler/container call sites, but direct no-patch eval-only still fails with CUDA 700; direct-root/minimal `__VnbaTriggered` stores pass, the reference-wrapper/cvta path faults, and `std::reference_wrapper::get()` canonicalization is now applied; canonical probes pass `trigger_orInto__act` entry, dst-load, src-load, and before-store, then fault after the destination store; `VlUnpacked<T,1>` index-call canonicalization rewrites `57` calls and directizes that helper; skip-store probes pass through `timing_resume`; `eval_act` probes show the first submodule act calls at callseq `952`/`953`/`954` are the current CUDA700 boundary, and skipping all three passes | Fix the `eval_act` submodule act call boundary CUDA700, then bridge comparison and timing report | No |
| `VeeR-EL2:default:hello` | Hybrid measured, correctness passed | Best row: `sidecar_wall_s_median=0.641226`, `sidecar_vs_cpu_parallel_ratio=3.460382`, CPU-parallel favorable, serial CPU still faster | Use as measured portability/negative-usefulness baseline; do not claim broad speedup | No |

For a repeat-median check of a slice-launch template, use:

```sh
PYTHONDONTWRITEBYTECODE=1 \
  python3 src/tools/hybrid_template_repeat_median.py \
    config/slice_launch_templates/nvdla_cmac_core_mac.json \
    --shape 32x1 \
    --repeat 3 \
    --write-report \
    --report-out reports/nvdla_cmac_core_mac_repeat_median_32x1.json
```

The 2026-06-17 local `NVDLA.nvdla_cmac_core_mac` `32x1` refresh reached
Verilator build, host-probe build, CPU init-state capture, and CPU reference
capture, then spent more than ten minutes in `ptxas` for the full core GPU
artifact with about 36 GiB RSS before the run was stopped. Treat this as
compile-cost evidence against broad full-core GPU lowering; the useful non-VeeR
path is still NVDLA, but with smaller hot SS boundaries such as the existing
`nvdla_cmac_a2cacc` and `cmac_core_mac` scoped timing records. Vortex remains
the next generalization candidate once it has a first CPU-vs-hybrid timing gate.

## Quickstart

Start with target discovery, then confirm the routine sidecar path without
dropping into shim JSON or wrapper internals:

```sh
python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
```

For debug and compatibility work below the normal operator path, use the
preview/shim tools deliberately rather than treating them as the first command a
user should run.

The `verilator_use_gpu_first_path.py` adapter is intentionally narrow: it
accepts only the reviewed `filelist_known_template_pulp_ita_mha` `64x1` path
and delegates to the existing hybrid template runner. It is not arbitrary
filelist support or automatic GPU allocation.

The generated `artifacts/use-gpu-wrapper/verilator` wrapper is the current
scoped PATH-selected wrapper for #33. It delegates no-GPU-intent argv to a real
Verilator later on `PATH`, or to `VERILATOR_USE_GPU_REAL_VERILATOR` when that
environment variable is set. GPU-intent argv is never delegated as CPU-only
success; it must pass the same reviewed first-path authority above or fail
closed.

Remove `--first-use-gpu-dry-run` from the wrapper command to execute the same
scoped path through sidecar build, run, and `coverage_output_equivalence`
compare.

After `git clean -fdX`, template and hybrid runs rebuild the local GPU pass
tools and hybrid runtime binary on demand. Generated material remains under
ignored build/report locations.

For a broad smoke of the documented reproduction surface:

```sh
make smoke
```

## Operator shortcuts

The `Makefile` keeps routine checks short:

```sh
make simple
make surface
make check
python3 src/tools/run_results_reproduction.py --dry-run
```

`make simple` validates the compact state and runs the dry-run smoke. `make surface` checks the tracked tool boundary. `make check` runs validation, surface checks, and contract tests.

`python3 src/tools/run_results_reproduction.py --dry-run` is a command preview:
it prints reproduction commands and expected generated outputs without running
measurements or creating archives. For the public pack boundary, use
`python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run`;
it prints the include/exclude plan and still creates no archive. Treat
`reports/` as generated evidence snapshots and `artifacts/` as rebuildable local
outputs. Canonical current state remains in `config/selection.json`,
`docs/status.md`, `docs/roadmap.md`, and `README.md`. A clean checkout can run
the Python dry-runs; non-dry Verilator/CUDA flows require the matching toolchain
and GPU runtime prerequisites.

Verilator-like benchmark runner:

```bash
python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
```

Full command reference:

```bash
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-command
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-verilator-estimate-command
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-efficiency-estimate
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --operator-plan-json
```

`--operator-plan-json` is a debug/inspection view of the same plan. It is not the runtime ABI and should not be the normal operator path.

Lower-level template runs use a concise stage summary by default. Detailed
Verilator/build/pass/compare logs are written under generated `reports/` paths;
use `--verbose` only when debugging the stage commands or sanitized-state
details directly:

```bash
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1 --verbose
```

Local helper binaries rebuilt by this flow are generated under
`artifacts/tool_bins/`, not under `src/`. The source tree should remain source
only after a clean-checkout template run.

## What Is Supported

- Scoped template-based hybrid runs through `src/tools/run_hybrid_template.py`.
- Target-oriented runs through `src/tools/run_hybrid_benchmark.py`.
- A Verilator-sidecar option preview using `--sim-accel sidecar-gpu --sim-accel-states N --sim-accel-steps S`.
- A frontend contract shape where Verilator currently supplies the build-side metadata and future CIRCT work should supply equivalent sidecar metadata.
- Optional JSON plans for debug and review inspection.
- CPU-vs-hybrid correctness checking with `coverage_output_equivalence`.
- Non-executing RTLMeter command-shape inspection for preserving the future RTLMeter user path.
- Historical opt-in RTLMeter first-seed CPU/reference vs sidecar-candidate compare evidence that passes for `Example:kind:hello` with marker-backed execution authority and no GPU runtime or speedup claim; current RTLMeter correctness work is gated on the direct-native path.

## What Is Not Yet Claimed

- General `verilator --use-gpu` support for arbitrary RTL.
- CIRCT execution support.
- Arbitrary `-f filelist.f --top-module top` dependency inference.
- Automatic optimal GPU allocation.
- A mandatory JSON runtime ABI.
- RTLMeter acceleration from compile-only evidence.
- Production timing or throughput claims.
- Raw full-state equality.
- Runtime/ABI stability for external users.

## Troubleshooting

- If a dry-run fails, run `python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu` and pick one of the listed targets.
- If a non-dry-run fails during build, initialize submodules with `git submodule update --init --recursive`.
- If a template run fails, use the reported stage name and generated `reports/*_<stage>.log` path first; rerun with `--verbose` only when the concise stage summary is not enough.
- If helper binaries are missing after `git clean -fdX`, rerun the template command; pass tools and the hybrid runtime are rebuilt under `artifacts/tool_bins/`.
- If GPU driver access is blocked, the hybrid stage fails closed with `classified_failure: gpu_runtime_unavailable`, usually alongside `CUDA error ... (cuInit)`. This is an environment blocker, not a CPU fallback or GPU success; inspect `reports/*_hybrid_sidecar_run.log` for the CUDA driver detail.
- If CPU-vs-hybrid compare reports raw state mismatch, check whether `coverage_output_equivalence` still passes; raw full-state equality is not the supported correctness policy.
- If scoped `verilator --use-gpu` wrapper support is needed, treat it as a debug/compatibility path rather than the first operator command. Use `src/tools/verilator_use_gpu_first_path.py --first-use-gpu-dry-run` only when inspecting the underlying adapter directly.
- If an RTLMeter command with `--compileArgs "--use-gpu"` only reports wrapper metadata, that is expected for the current public surface. It proves GPU intent reached the Verilator command path, not GPU execution or speedup.
- If `third_party/rtlmeter/rtlmeter` fails from the repo root with `No module named 'src.rtlmeter'`, rerun with the documented `PYTHONPATH="$PWD/third_party/rtlmeter:$PYTHONPATH"` prefix. The compare helper is an alternate diagnostic path; it prepends `third_party/rtlmeter` to `PYTHONPATH` for RTLMeter execution.
- If an RTLMeter wrapper request fails closed, check that the captured Verilator argv includes `--cc`, `-f <filelist>`, `--top-module <top>`, and either `--use-gpu` or expanded `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`.
- If RTLMeter speedup is the goal, keep compile success, GPU sidecar execution, CPU/GPU compare, and measured acceleration as separate milestones.

## Setup

Initialize submodules before running nontrivial flows:

```sh
git submodule update --init --recursive
```

Enable the local commit guard if you are contributing:

```sh
git config core.hooksPath .githooks
```

Run contract tests with:

```sh
make test
```

## Commit Guard

Enable the versioned hook once per checkout:

```sh
git config core.hooksPath .githooks
```

The hook runs `python3 src/tools/check_staged_large_files.py` and rejects oversized files, oversized commits, too many new guarded scripts, and large `src/tools/` or `tests/contract/` growth. Reviewed local overrides are `GPU_TOGGLE_MAX_COMMIT_FILE_COUNT`, `GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES`, `GPU_TOGGLE_MAX_NEW_SCRIPT_FILES`, `GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES`, `GPU_TOGGLE_MAX_CONTRACT_TEST_ADDED_LINES`, and `GPU_TOGGLE_MAX_CONTRACT_TEST_TOTAL_LINES`.

Commit cadence: keep commits scoped to one gate or workflow boundary. Keep generated `artifacts/` local and commit generated `reports/` only when they are reviewed evidence snapshots.

## Local disk hygiene

`artifacts/` is generated output, not source of truth. You may delete stale build trees and recreate optional local environments from documented commands:

```sh
python3 -m venv artifacts/mobile_vit/venv
artifacts/mobile_vit/venv/bin/python -m pip install -r requirements/mobile_vit.txt
```

## Repository Map

| Path | Role |
|---|---|
| `src/` | Runtime, passes, public CLIs, and shared helpers. |
| `tests/` | Contract tests for supported behavior and claim boundaries. |
| `docs/` | User and developer documentation. Start with `docs/tool_surface.md` and `docs/verilator_sidecar_option.md` for operator-facing details. |
| `config/` | Current machine-readable project state and launch templates. |
| `overlays/` | Repo-owned patches and source overlays for upstream projects. |
| `third_party/` | Pinned upstream submodules. |
| `records/` | Internal audit history; not normal user input. This is planned to move out of the main user path. |
| `reports/` | Generated reports; not source of truth. |
| `artifacts/` | Generated build outputs; not source of truth. |
| `for_codex/` | Codex-facing instructions and project memory moved out of the user README path. |

## Source Of Truth

For normal users, start here and use the documented commands. Internal project state is intentionally kept out of the primary README path.

- `config/selection.json`
- `docs/status.md`
- `docs/roadmap.md`
- `README.md`

Codex-facing instructions, long gate memory, and prior README content live under `for_codex/`.

The selected correctness policy is `coverage_output_equivalence`; raw final-state match may remain false while the declared coverage-output words pass.
