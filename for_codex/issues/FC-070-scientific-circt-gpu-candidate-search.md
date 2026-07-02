# FC-070: Scientific CIRCT GPU Candidate Search

Status: open
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/71
Parent: FC-043 / https://github.com/takatodo/gpu-rtl-sim/issues/10
Related: FC-063 / https://github.com/takatodo/gpu-rtl-sim/issues/64, FC-065 / https://github.com/takatodo/gpu-rtl-sim/issues/65, FC-037 / https://github.com/takatodo/gpu-rtl-sim/issues/2, FC-071 / https://github.com/takatodo/gpu-rtl-sim/issues/70
Target file: `src/tools/scientific_circt_gpu_candidate_plan.py`, `src/tools/scientific_circt_dense_matmul_tile.py`, `src/tools/scientific_circt_batched_reduction.py`, `src/tools/scientific_circt_stencil_2d_tile.py`, `src/tools/scientific_circt_softmax_exp_pipeline.py`, `src/tools/scientific_circt_microgpt_ir_partition_probe.py`, `src/tools/scientific_circt_microgpt_math_block.py`, `src/tools/scientific_circt_microgpt_attention_head.py`, `src/tools/scientific_circt_microgpt_mlp_slice.py`, `src/tools/scientific_circt_microgpt_block_slice.py`, `src/tools/scientific_circt_microgpt_inference_slice.py`, `src/tools/scientific_circt_hybrid_protocol.py`, `src/tools/scientific_circt_hybrid_dispatch_matrix.py`, `src/tools/scientific_circt_runtime_handoff_abi.py`, `src/tools/scientific_circt_runtime_handoff_adapter.py`, `src/tools/scientific_circt_runtime_entrypoint.py`, `src/tools/scientific_circt_broader_runtime_entrypoint.py`, `src/tools/scientific_circt_verilator_callsite_entrypoint.py`, `src/tools/scientific_circt_hls_attention_head_variant.py`, `src/tools/scientific_circt_hls_mlp_block_variants.py`, `src/tools/scientific_circt_source_variant_metadata.py`, `src/tools/scientific_circt_source_variant_runtime_handoff.py`, `src/tools/scientific_circt_source_variant_runtime_dispatcher.py`, `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp`, `src/hybrid/scientific_circt_adapter_bridge.c`, `src/hybrid/scientific_circt_verilator_callsite_bridge.cpp`, `src/tools/scientific_circt_gategpt_microgpt_compare.py`, `src/tools/scientific_circt_evidence_audit.py`, `src/tools/scientific_circt_hybrid_advantage.py`, `src/tools/llvm_rtl_gpu_suitability.py`, `src/tools/heavy_rtl_candidate_matrix.py`, `config/slice_launch_templates/blackparrot_bsg_wormhole_router.json`, `overlays/rtlmeter/designs/BlackParrot/src/bsg_wormhole_router_gpu_cov_tb.sv`, `overlays/rtlmeter/designs/BlackParrot/tests/bsg_wormhole_router_coverage_regions.json`, `config/scaling_gates/blackparrot_bsg_wormhole_router_source_gate.json`, `tests/contract/test_scientific_circt_gpu_candidate_plan.py`, `tests/contract/test_scientific_circt_dense_matmul_tile.py`, `tests/contract/test_scientific_circt_batched_reduction.py`, `tests/contract/test_scientific_circt_stencil_2d_tile.py`, `tests/contract/test_scientific_circt_softmax_exp_pipeline.py`, `tests/contract/test_scientific_circt_microgpt_ir_partition_probe.py`, `tests/contract/test_scientific_circt_microgpt_math_block.py`, `tests/contract/test_scientific_circt_microgpt_attention_head.py`, `tests/contract/test_scientific_circt_microgpt_mlp_slice.py`, `tests/contract/test_scientific_circt_microgpt_block_slice.py`, `tests/contract/test_scientific_circt_microgpt_inference_slice.py`, `tests/contract/test_scientific_circt_hybrid_protocol.py`, `tests/contract/test_scientific_circt_hybrid_dispatch_matrix.py`, `tests/contract/test_scientific_circt_runtime_handoff_abi.py`, `tests/contract/test_scientific_circt_runtime_handoff_adapter.py`, `tests/contract/test_scientific_circt_runtime_entrypoint.py`, `tests/contract/test_scientific_circt_broader_runtime_entrypoint.py`, `tests/contract/test_scientific_circt_verilator_callsite_entrypoint.py`, `tests/contract/test_scientific_circt_hls_attention_head_variant.py`, `tests/contract/test_scientific_circt_hls_mlp_block_variants.py`, `tests/contract/test_scientific_circt_source_variant_metadata.py`, `tests/contract/test_scientific_circt_source_variant_runtime_handoff.py`, `tests/contract/test_scientific_circt_source_variant_runtime_dispatcher.py`, `tests/contract/test_scientific_circt_gategpt_microgpt_compare.py`, `tests/contract/test_scientific_circt_evidence_audit.py`, `tests/contract/test_scientific_circt_hybrid_advantage.py`, `tests/contract/test_heavy_rtl_candidate_matrix.py`, `config/selection.json`, `README.md`, `docs/roadmap.md`, `docs/status.md`

## Objective

Create a reproducible path for scientific-compute kernels to enter the sidecar
project through CIRCT-generated SystemVerilog, then Verilator, then the existing
GPU suitability and CPU/hybrid measurement gates.

The intended operator question is:

```text
Given a scientific computation lowered through CIRCT to SystemVerilog and then
Verilator LLVM IR, which sub-systems are likely GPU-useful, which should stay
CPU-parallel, and which require a new specialized mapping?
```

This issue started with candidate selection and planning. The measured
testbenches now have CIRCT lowering, Verilator CPU reference evidence, and
scoped CUDA timing evidence at the planned shapes. It still does not claim
broad RTL, RTLMeter, automatic partitioning, or arbitrary-design speedup.

Current next direction: make `microgpt_inference_slice,inference2_hls_friendly,
1024x1` the primary reusable runtime boundary. CPU keeps token-loop, sampler,
full KV-cache, unknown variants, unsupported shapes, and step-mismatched
requests; GPU owns only the measured batched arithmetic behind metadata-gated
candidate/source-variant/shape dispatch. Use gateGPT `exp_unit` as the
comparison slice for Verilator-lowered RTL: signed 16-bit `z` input, signed
16-bit `e` output one cycle later, `tb_exp.v` plus `test_exp_z.hex` and
`test_exp_e.hex` as the 103-case CPU oracle, and resident/state-indexed GPU
hybrid timing with wall/kernel/launch/handoff/state-count/mismatch accounting
before any broader usefulness claim.

2026-06-23 progress: GitHub mirror is #71. The dispatcher now accepts requested
`--shape` and `--steps` gates. Unsupported
`inference2_hls_friendly --shape 256x1` returns
`runtime_dispatch_cpu_fallback_unsupported_shape`, and `--steps 2` returns
`runtime_dispatch_cpu_fallback_unsupported_steps`; both avoid invoking runtime
handoff. The dispatcher now also passes the selected metadata row into
`build_runtime_handoff_report`. The `src-hybrid-verilator` handoff validates
candidate/source_variant/shape/entrypoint/runtime-boundary/layout/symbols and
returns `src_hybrid_verilator_metadata_gate_rejected` before compile/run on
mismatch; the C++ bridge checks compact metadata argv and returns
`failed_metadata_gate` before `dlopen`. Next is executing the metadata-gated
bridge path in an environment with Verilator inputs, then refreshing the gateGPT
`exp_unit` comparison lane.

2026-06-24 progress: the metadata-gated execute path now runs. The direct
handoff report `reports/scientific_circt_source_variant_verilator_entrypoint.json`
records `src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`,
CPU/GPU output equality, control-checksum equality, all metadata-gate checks
true, and `cpu_to_bridge_hybrid_wall_speedup=6.2165001599863245x`. The
dispatcher report `reports/scientific_circt_source_variant_runtime_dispatcher.json`
records `runtime_dispatch_measured` with nested
`src_hybrid_verilator_runtime_handoff_measured`, mismatch `0`, output/checksum
equality, all metadata-gate checks true, and
`cpu_to_bridge_hybrid_wall_speedup=15.461002763357895x`. The gateGPT `exp_unit`
comparison lane was refreshed with
`python3 src/tools/gategpt_testbench_probe.py --repo-dir artifacts/external_gateGPT --run-gpu-smoke --gpu-jobs 2 --write-report --report-out reports/gategpt_testbench_probe.json`.
The report records `tb_exp` vector, distinct-state, and resident patch paths all
passing `103/103` with mismatch `0`; resident repeat median is `1.422 ms` wall
and `1.348608 ms` kernel versus CPU Verilator process-wall median
`14.788301952648908 ms`. This remains narrow `tb_exp` comparison evidence:
`speedup_claimed=false`, `usefulness_claimed=false`, no broad gateGPT
PASS/FAIL, and no arbitrary RTL usefulness claim. FC-070 / #71 is now
closure-ready around this scoped metadata-gated runtime boundary. The next
substantive implementation slice is FC-072 / #72: generate or otherwise reuse
source-variant bridge code from the metadata surface while preserving the same
fail-closed candidate/source_variant/shape/layout/symbol gates. FC-072 now has
a measured generated-header bridge gate for the scoped
`inference2_hls_friendly,1024x1` row; that remains a child-task result, not a
new broad FC-070 claim.

## Tasks

- Add a plan surface for scientific candidates such as dense matmul tiles,
  stencil tiles, batched reductions, softmax/exp pipelines, and branch-heavy
  sparse solver control.
- For each candidate, define the intended pipeline:
  MLIR/CIRCT input -> CIRCT SystemVerilog -> Verilator build -> lowered LLVM IR
  -> static suitability -> repeat-median CPU/hybrid measurement.
- Prefer regular-memory, low-observable, many-independent-state candidates
  before branch-heavy control candidates.
- Reuse FC-063/FC-065 suitability JSON only as review/debug metadata, not as
  execution authority.
- Fail closed when the CIRCT toolchain is missing.
- Materialize `dense_matmul_tile` first, prove CIRCT-generated SystemVerilog and
  Verilator CPU reference, then measure at `64x1`, `256x1`, and `1024x1` before
  broadening.
- Record CPU-vs-GPU end-to-end and kernel-only timing separately so PCIe/launch
  overhead and compute-side benefit do not get conflated.
- Repeat the flow per testbench and aggregate the per-testbench favorable
  boundary before converting it into a compile-time policy.

## Acceptance

- `src/tools/scientific_circt_gpu_candidate_plan.py` emits a JSON plan with
  candidate order, CIRCT/Verilator/suitability/measurement stages, expected
  GPU buckets, planned shapes, and non-claims.
- The plan reports `blocked_circt_toolchain_missing` when no CIRCT executable is
  on `PATH`.
- Tests cover candidate filtering, unknown-candidate fail-closed behavior,
  absence of local absolute paths, and non-claims.
- README documents the command and the fact that it is plan-only.
- `src/tools/scientific_circt_dense_matmul_tile.py` materializes the first
  candidate reproducibly, writes generated artifacts under
  `artifacts/scientific_circt/dense_matmul_tile/`, and reports a Verilator CPU
  reference observable before any GPU claim.
- Entry-scoped LLVM IR suitability is recorded separately from whole
  Verilator-generated support analysis.
- `src/tools/scientific_circt_dense_matmul_tile_gpu_timing.py` records scoped
  CUDA timing for `64x1`, `256x1`, and `1024x1`; `64x1` is CPU-favorable
  end-to-end, while `256x1` and `1024x1` are GPU-favorable end-to-end.
- `src/tools/scientific_circt_hybrid_advantage.py` folds the scientific timing
  reports into a common hybrid summary and records `256x1` as the first
  end-to-end GPU-favorable measured shape.
- `src/tools/scientific_circt_batched_reduction.py` proves the same path for a
  second testbench. `64x1` is CPU-favorable end-to-end, while `256x1` and
  `1024x1` are GPU-favorable end-to-end.
- `src/tools/scientific_circt_stencil_2d_tile.py` proves the same path for a
  neighbor-style third testbench. `64x1` and `256x1` are CPU-favorable
  end-to-end, while `1024x1` is GPU-favorable.
- `src/tools/scientific_circt_softmax_exp_pipeline.py` proves the same path for
  an exp/softmax-style fourth testbench. `64x1` is CPU-favorable end-to-end,
  while `256x1` and `1024x1` are GPU-favorable end-to-end.
- `src/tools/scientific_circt_gpu_selection_policy.py` converts the repeated
  measured boundaries into a candidate-specific compile-time selection policy.
- `src/tools/scientific_circt_hybrid_protocol.py` converts the measured policy
  and hybrid summary into a compile-time CPU/GPU handoff protocol. It records
  candidate dispatch by `(candidate,nstates,steps)`, CPU fallback below measured
  thresholds, CPU ownership of token-loop/sampler/full-KV authority for the
  microGPT lane, GPU ownership of measured arithmetic batches, and logical
  payload byte estimates. It can also emit a single-candidate dispatch decision:
  measured candidates at or above threshold select GPU, while below-threshold,
  unknown, unsupported, or step-mismatched requests select CPU with fail-closed
  reasons. This is not runtime ABI authority or PCIe framing evidence.
- `src/tools/scientific_circt_hybrid_dispatch_matrix.py` expands the protocol
  into an all-candidate measured-shape dispatch matrix. For the current
  `64x1`, `256x1`, and `1024x1` points it records 27 candidate/shape decisions:
  16 select GPU and 11 select CPU, with measured speedup evidence attached to
  all 27 rows. `64x1` stays CPU for all candidates, `256x1` selects GPU for
  seven candidates, and `1024x1` selects GPU for all nine. This is compile-time
  dispatch evidence over measured timing reports only, not runtime ABI
  authority, PCIe framing evidence, RTLMeter evidence, full microGPT execution,
  or automatic partitioning.
- The dispatch matrix ranks GPU-selected rows for runtime integration. The
  current top row is `microgpt_attention_head` at `1024x1` with measured
  end-to-end speedup `6.41385x`; the next required evidence is broader hybrid
  runtime entrypoint wiring plus amortized integration timing.
- `src/tools/scientific_circt_runtime_handoff_abi.py` converts that top row
  into the first runtime handoff ABI definition. The current report is
  `handoff_abi_ready` for `microgpt_attention_head,1024x1`, with 20 input
  bytes/state, 32 output bytes/state, and 53,248 logical roundtrip bytes. CPU
  retains sequence/KV-cache authority, and GPU owns only the measured
  attention-head arithmetic batch. The adapter gate below now records
  CPU-vs-GPU equality plus warmed fused timing, so the next evidence is broader
  hybrid runtime entrypoint wiring and amortized integration timing. This is not
  PCIe framing evidence, full microGPT execution, RTLMeter evidence, or
  automatic partitioning.
- `src/tools/scientific_circt_runtime_handoff_adapter.py` runs the first
  ABI-backed adapter correctness gate for `microgpt_attention_head,1024x1`.
  The current report is `adapter_correctness_passed`, observes 20,480 input
  bytes and 32,768 output bytes matching the ABI, and records CPU-vs-GPU output
  equality with `mismatch_count=0` for the 1,024-state batch. It also records
  an adapter-local integration loop with `inner_repeat=1000` and
  `integration_batches=15`: CPU `0.7769709466666667 ms`, GPU end-to-end
  `0.12586719999999998 ms`, GPU kernel `0.027211092884341877 ms`, CPU-to-GPU
  end-to-end speedup `6.17294216973657x`, and CPU-to-GPU kernel speedup
  `28.553463470545143x` per integration batch. It now builds both the CLI
  binary and `libmicrogpt_attention_head_handoff_adapter.so`, including a GPU
  output-buffer symbol for Verilator callsite comparison. This is scoped
  positive runtime-adapter evidence: the warmed fused handoff preserves the
  measured GPU-favorable candidate region after adapter-local amortization.
- `src/tools/scientific_circt_runtime_entrypoint.py` measures the first
  subprocess-free in-process runtime entrypoint over that generated adapter
  shared library. The current report is
  `in_process_entrypoint_timing_measured`: a CPU+GPU correctness warmup preserves
  output/checksum equality, the timed GPU-only library call matches the
  correctness checksum, and `subprocess_used=false`. Timed hybrid wall is
  `8.331281000209856 ms`, or `0.11108374666946474 ms` per integration batch,
  against CPU baseline `0.78472712 ms` per integration batch, so
  `cpu_to_in_process_wall_speedup=7.0642838716540135x`. This is the first positive
  subprocess-free runtime entrypoint evidence for `microgpt_attention_head,1024x1`.
  It is not broad runtime speedup evidence, PCIe framing evidence, full microGPT
  execution, RTLMeter evidence, automatic partitioning, direct Verilator runtime
  evidence, or production runtime evidence.
- `src/tools/scientific_circt_broader_runtime_entrypoint.py` measures the same
  adapter shared library through `src/hybrid/scientific_circt_adapter_bridge.c`.
  The bridge uses `dlopen`/`dlsym`, runs the CPU+GPU correctness call as warmup,
  then times the GPU-only adapter symbol from C. The current report is
  `broader_hybrid_entrypoint_timing_measured`: output/checksum equality holds,
  the timed GPU checksum matches the correctness checksum, and
  `subprocess_used_for_adapter=false`. Bridge-internal timed hybrid wall is
  `8.079087 ms`, or `0.10772116 ms` per integration batch, against CPU baseline
  `0.7869408533333333 ms`; `cpu_to_bridge_hybrid_wall_speedup` is
  `7.305350715990556x`. This closes the broader `src/hybrid` C-bridge boundary.
- `src/tools/scientific_circt_verilator_callsite_entrypoint.py` measures the same
  GPU adapter against the Verilator-generated `Vsim` model through
  `src/hybrid/scientific_circt_verilator_callsite_bridge.cpp`. The bridge calls
  `Vsim::eval()` for the CPU path, compares the 1,024-state Verilator output
  buffer against the GPU adapter output buffer, then times the GPU-only adapter
  symbol. The current report is
  `direct_verilator_callsite_entrypoint_timing_measured`: `verilator_callsite_used`
  is true, output/checksum equality holds, and `subprocess_used_for_adapter=false`.
  Bridge-internal timed hybrid wall is `10.028488 ms`, or
  `0.13371317333333332 ms` per integration batch, against Verilator CPU callsite
  baseline `0.8192283333333333 ms`; `cpu_to_bridge_hybrid_wall_speedup` is
  `6.126758590128443x`. This closes the scoped direct Verilator-generated callsite
  boundary. The next required evidence is replacing the remaining handwritten GPU
  adapter kernel with a lowered or generated GPU kernel.
- `src/tools/scientific_circt_hls_attention_head_variant.py` tests the HLS-style
  source-variant question for `microgpt_attention_head,1024x1`. It materializes
  four explicit independent attention heads per state, lowers FIRRTL to
  SystemVerilog, builds Verilator, builds a separate CUDA shared library, and
  compares the Verilator CPU output buffer/checksum with the GPU result before
  timing. The current report is `hls_variant_improved`: output/checksum equality
  holds, `mismatch_count=0`, and bridge-wall speedup improves from the
  direct-callsite baseline `6.126758590128443x` to `13.301119215779238x`.
  This supports source/IR-level arithmetic reshaping as the next useful lever;
  it is not full microGPT execution or automatic HLS rewriting.
- `src/tools/scientific_circt_hls_mlp_block_variants.py` extends the same
  direct-callsite measurement to `microgpt_mlp_slice` and
  `microgpt_block_slice`, and now `microgpt_inference_slice`.
  `mlp4_hls_friendly` improves from the baseline MLP speedup `2.28894x` to
  `9.922827450510521x`. `inference2_hls_friendly` improves from the baseline
  inference speedup `3.62419x` to `9.799333107174757x`. `block2_hls_friendly`
  lowers and matches output/checksum, but does not improve over the block
  baseline (`5.56609843788867x` versus `5.75973x`). This gives positive and
  negative rule samples for source/IR reshaping: promote explicit independent
  units only when equality holds and the measured direct-callsite ratio improves.
- `src/tools/scientific_circt_gpu_selection_policy.py` now accepts
  `--hls-variant-report` and adds `source_variants` decisions keyed by
  `(candidate,source_variant,shape)`. The current policy promotes
  `attention_head4_hls_friendly`, `mlp4_hls_friendly`, and
  `inference2_hls_friendly` to HLS GPU, while `block2_hls_friendly` keeps the
  baseline GPU/CPU decision.
- `src/tools/scientific_circt_hybrid_protocol.py` now carries those
  `source_variants` through the compile-time handoff protocol. The dispatch key
  is `(candidate,source_variant,nstates,steps)`, and the source-variant decision
  CLI returns `promote_to_hls_gpu` for promoted equality-checked variants at
  their measured shape, `keep_baseline_gpu_or_cpu` for non-improving
  equality-checked variants, and `select_cpu` for unknown/below-threshold/step
  mismatch cases.
- `src/tools/scientific_circt_hybrid_dispatch_matrix.py` now expands the same
  source variants over `64x1`/`256x1`/`1024x1`: 12 variant decisions, 3
  promoted rows, 3 baseline-keep rows, and 6 CPU fallback rows. It also ranks
  promoted runtime-handoff candidates as attention (`13.301119215779238x`), MLP
  (`9.922827450510521x`), and inference (`9.799333107174757x`), then selects
  `inference2_hls_friendly` as the next runtime boundary because attention
  already has the scoped runtime evidence lane and inference is the fuller
  token/cache slice.
- `src/tools/scientific_circt_source_variant_runtime_handoff.py` now executes
  the selected source-variant boundary as a scoped runtime handoff report. The
  current report is `runtime_handoff_boundary_measured` for
  `inference2_hls_friendly,1024x1`: CPU/GPU output and checksum equality hold,
  logical payload is 8,192 input bytes plus 49,152 output bytes, and observed
  per-integration-batch timing is CPU `1.5594159200000002 ms`, GPU end-to-end
  `0.1436130933333333 ms`, GPU kernel `0.04580693379044533 ms`, bridge wall
  `0.16406808 ms`, and CPU-to-bridge-wall speedup `9.504688053885925x`.
  CPU retains token-loop/sampler/KV-cache authority while GPU owns only the
  HLS-friendly batched arithmetic source variant. The next gate is integrating
  this selected boundary into the broader `src/hybrid` or direct Verilator
  callsite path, not choosing another boundary.
- `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` now closes
  that next gate for the selected source variant. The bridge builds against
  the generated `inference2_hls_friendly` Verilator `obj_dir`, uses
  `Vsim::eval()` as the CPU callsite, loads the GPU shared library with
  `dlopen`/`dlsym`, and records output/checksum equality. The current
  `reports/scientific_circt_source_variant_verilator_entrypoint.json` report
  is `src_hybrid_verilator_runtime_handoff_measured`, with CPU-to-bridge-wall
  speedup `9.982658965614949x` and bridge wall `0.15218008 ms` per
  integration batch. Next gate: generalize the bridge pattern into a reusable
  runtime-boundary dispatcher or generator while preserving
  candidate/source_variant/shape policy checks.
- `src/tools/scientific_circt_source_variant_runtime_dispatcher.py` now closes
  that generalization gate for the first source variant. It reads the dispatch
  matrix, rejects non-selected source variants, verifies the registered
  candidate/source_variant/shape tuple, and invokes the checked-in
  `src_hybrid_verilator_callsite_bridge` for `inference2_hls_friendly,1024x1`.
  The current `reports/scientific_circt_source_variant_runtime_dispatcher.json`
  report is `runtime_dispatch_measured`, with nested
  `runtime_handoff_status=src_hybrid_verilator_runtime_handoff_measured`,
  output/checksum equality, bridge wall `0.14075793333333333 ms` per
  integration batch, and CPU-to-bridge-wall speedup `11.09435972584612x`.
  Next gate: broaden the dispatcher registry or generator beyond this first
  inference slice while retaining CPU-fail-closed behavior for unsupported
  source variants.
- The selected one-hour test case now passes:
  `reports/scientific_circt_source_variant_runtime_dispatcher_soak_summary.json`
  records `source_variant_runtime_dispatcher_soak` over the same
  `inference2_hls_friendly,1024x1` boundary for `3600` seconds. It produced
  `2574` per-iteration reports under `reports/one_hour_runtime_dispatcher/`;
  all `2574` passed `status=runtime_dispatch_measured`, nested
  `runtime_handoff_status=src_hybrid_verilator_runtime_handoff_measured`,
  output equality, and control-checksum equality. CPU-to-bridge-wall speedup
  median is `10.731542472816859x`, with p10 `8.363504353854227x`, p90
  `11.829942667042333x`, min `1.2956713528049701x`, and max
  `12.793946412262754x`. The soak also records `75` reports below `5x` bridge
  speedup and `40` reports above `0.5 ms` bridge wall, so it is
  correctness/dispatch stability evidence, not a new reviewed production
  speedup claim.
- `src/tools/scientific_circt_source_variant_metadata.py` now generates the
  source-variant bridge metadata surface from the dispatch matrix, HLS variant
  reports, and artifact GPU sources. The current
  `reports/scientific_circt_source_variant_metadata.json` report is
  `source_variant_metadata_ready` with four complete rows for
  `attention_head4_hls_friendly`, `mlp4_hls_friendly`,
  `inference2_hls_friendly`, and `block2_hls_friendly`. It extracts GPU
  symbols, input/output layout, artifact paths, Verilator `obj_dir`,
  entrypoint kind, runtime boundary kind, and fallback policy; input/output
  bytes per state are `80/128`, `16/64`, `8/48`, and `24/32`.
- `src/tools/scientific_circt_source_variant_runtime_dispatcher.py` now reads
  that generated metadata instead of a fixed in-code source-variant registry.
  The current `reports/scientific_circt_source_variant_runtime_dispatcher_multi.json`
  report is still `multi_source_variant_dispatch_ready`: `attention_head4_hls_friendly`,
  `mlp4_hls_friendly`, and `inference2_hls_friendly` dispatch to measured
  equality-checked GPU boundaries, while `block2_hls_friendly` is recorded as
  `runtime_dispatch_fallback_baseline` because its HLS-friendly speedup
  `5.56609843788867x` does not improve over the baseline `5.75973x`. The
  measured CPU-to-bridge-wall speedups for the promoted rows are
  `11.31933596913315x`, `9.466548203869824x`, and `11.420283475548267x`.
  Next gate: emit reusable bridge source from the metadata surface before
  broadening beyond this source-variant set.
- `src/tools/heavy_rtl_candidate_matrix.py` now generates the PULP/NoC heavy
  RTL candidate matrix at `reports/heavy_rtl_candidate_matrix.json`. The matrix
  uses a common row-level schema for source closure, template availability,
  build/run/compare evidence, CPU/hybrid timing, state-parallel shape,
  single-state repeated-step shape, and promote/fallback/resident-required
  policy. It currently contains two PULP rows and four NoC/TLUL-style rows.
  `pulp_ita_mha`, `pulp_paged_attention_kv_score`, `tlul_socket_1n`,
  `tlul_socket_m1`, and `blackparrot_bsg_wormhole_router` are now promoted
  rows. The next-stage repeat-median reports
  are `reports/pulp_paged_attention_kv_score_64x1_median.json`,
  `reports/tlul_socket_1n_32x1_median.json`, and
  `reports/tlul_socket_m1_32x1_median.json`, plus the BlackParrot
  `reports/blackparrot_bsg_wormhole_router_32x1_median.json`,
  `reports/blackparrot_bsg_wormhole_router_64x1_median.json`, and
  `reports/blackparrot_bsg_wormhole_router_128x1_median.json`, and
  `reports/blackparrot_bsg_wormhole_router_256x1_median.json` shape sweep; all
  pass coverage-output equivalence across three samples. BlackParrot now has a
  source-backed BaseJump closure template, coverage overlay, coverage manifest,
  and coverage gate. Packet-pattern repeat-median wall speedups are
  `32.76216804527645x` at `32x1`, `158.28447339847992x` at `64x1`, and
  `259.4919886899152x` at `128x1`, and `651.817697228145x` at `256x1`, so it is shape-extension repeat-median-backed
  promote evidence rather than a `32x1`-only candidate. The resident/multi-step
  definition gate is now
  `config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json`;
  it defines a `256x4` resident packet-pattern timing target. The template
  runner now has a dry-run resident command-plan surface with `--resident-steps`
  and explicit `--patch-script`; execution is blocked until the BlackParrot
  packet-pattern patch script is materialized or recorded as the named FC-071
  blocker.
- `src/tools/scientific_circt_evidence_audit.py` includes the dispatch matrix
  in the readiness audit. The current audit is `evidence_ready` for 9/9
  candidates and verifies dispatch-matrix measured speedup evidence for all 27
  candidate/shape rows.
- The next follow-up is a microGPT IR partition probe: keep matmul, reduction,
  and softmax-like arithmetic visible for CIRCT/GPU selection instead of relying
  only on late Verilator LLVM tweaks over gateGPT root-state control.
- `src/tools/scientific_circt_microgpt_ir_partition_probe.py` maps the measured
  scientific policy onto a microGPT-style graph. At `nstates=256,steps=1`, it
  selects GPU state-parallel for 8/10 nodes and keeps token-loop control plus
  KV-cache state update in the CPU/new-mapping bucket. This is not microGPT
  execution; it is a partition target for the next CIRCT experiment.
- `src/tools/scientific_circt_microgpt_math_block.py` materializes the first
  composite microGPT-style math block through CIRCT/SystemVerilog and Verilator
  CPU reference, then measures CUDA timing at `64x1`, `256x1`, and `1024x1`.
  `64x1` is CPU-favorable end-to-end, while `256x1` and `1024x1` are
  GPU-favorable end-to-end.
- `src/tools/scientific_circt_microgpt_attention_head.py` materializes a
  source-derived two-token attention-head slice from actual `third_party/microgpt.py`
  structure through CIRCT/SystemVerilog and Verilator CPU reference, then
  measures CUDA timing at `64x1`, `256x1`, and `1024x1`. `64x1` is
  CPU-favorable end-to-end, while `256x1` and `1024x1` are GPU-favorable
  end-to-end. This is not full block-size microGPT inference.
- `src/tools/scientific_circt_microgpt_mlp_slice.py` materializes a
  reduced-width source-derived MLP slice from actual `third_party/microgpt.py`
  `mlp_fc1 -> ReLU -> mlp_fc2` structure through CIRCT/SystemVerilog and
  Verilator CPU reference, then measures CUDA timing at `64x1`, `256x1`, and
  `1024x1`. `64x1` and `256x1` are CPU-favorable end-to-end, while `1024x1`
  is GPU-favorable end-to-end. This is not full hidden-width microGPT MLP
  inference.
- `src/tools/scientific_circt_microgpt_block_slice.py` materializes a
  source-derived one-token/two-key block-level slice from actual
  `third_party/microgpt.py` attention/residual/MLP structure through
  CIRCT/SystemVerilog and Verilator CPU reference, then measures CUDA timing at
  `64x1`, `256x1`, and `1024x1`. `64x1` is CPU-favorable end-to-end, while
  `256x1` and `1024x1` are GPU-favorable end-to-end. This is not full
  `block_size` microGPT inference.
- `src/tools/scientific_circt_microgpt_inference_slice.py` materializes a
  source-derived two-token inference slice from actual `third_party/microgpt.py`
  token/position, KV-cache, attention, residual, MLP, and logits structure
  through CIRCT/SystemVerilog and Verilator CPU reference, then measures CUDA
  timing at `64x1`, `256x1`, and `1024x1`. `64x1` is CPU-favorable
  end-to-end, while `256x1` and `1024x1` are GPU-favorable end-to-end. This is
  not full `block_size` microGPT execution or training/autograd.
- gateGPT remains the external RTL testbench lane, but its FPGA-oriented RTL
  optimization makes it a noisier surface for first-pass GPU partition
  discovery than direct microGPT IR/CIRCT.
- `src/tools/scientific_circt_gategpt_microgpt_compare.py` scans the actual
  `third_party/microgpt.py` source and compares it with gateGPT evidence. The
  source exposes `linear`, `softmax`, `rmsnorm`, `gpt`, attention, MLP, and
  autograd-training structure. The current decision is to use direct
  microGPT/CIRCT for GPU partition discovery and gateGPT RTL for integration and
  negative/control evidence. The comparison records `microgpt_math_block`,
  `microgpt_attention_head`, `microgpt_mlp_slice`, `microgpt_block_slice`, and
  `microgpt_inference_slice` as measured
  source-derived CIRCT slices.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_gpu_candidate_plan -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_dense_matmul_tile -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_dense_matmul_tile_gpu_timing -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_batched_reduction -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_stencil_2d_tile -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_softmax_exp_pipeline -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_microgpt_ir_partition_probe -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_microgpt_math_block -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_microgpt_attention_head -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_microgpt_mlp_slice -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_microgpt_block_slice -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_microgpt_inference_slice -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_hybrid_protocol -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_hybrid_dispatch_matrix -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_runtime_handoff_abi -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_runtime_handoff_adapter -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_runtime_entrypoint -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_broader_runtime_entrypoint -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_verilator_callsite_entrypoint -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_hls_attention_head_variant -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_hls_mlp_block_variants -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_source_variant_metadata -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_source_variant_runtime_handoff -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_source_variant_runtime_dispatcher -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_gategpt_microgpt_compare -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_evidence_audit -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_hybrid_advantage -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_scientific_circt_gpu_selection_policy -q
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.contract.test_heavy_rtl_candidate_matrix -q
python3 -m py_compile \
  src/tools/scientific_circt_gpu_candidate_plan.py \
  src/tools/scientific_circt_dense_matmul_tile.py \
  src/tools/scientific_circt_dense_matmul_tile_gpu_timing.py \
  src/tools/scientific_circt_batched_reduction.py \
  src/tools/scientific_circt_stencil_2d_tile.py \
  src/tools/scientific_circt_softmax_exp_pipeline.py \
  src/tools/scientific_circt_microgpt_ir_partition_probe.py \
  src/tools/scientific_circt_microgpt_math_block.py \
  src/tools/scientific_circt_microgpt_attention_head.py \
  src/tools/scientific_circt_microgpt_mlp_slice.py \
  src/tools/scientific_circt_microgpt_block_slice.py \
  src/tools/scientific_circt_microgpt_inference_slice.py \
  src/tools/scientific_circt_hybrid_protocol.py \
  src/tools/scientific_circt_hybrid_dispatch_matrix.py \
  src/tools/scientific_circt_runtime_handoff_abi.py \
  src/tools/scientific_circt_runtime_handoff_adapter.py \
  src/tools/scientific_circt_runtime_entrypoint.py \
  src/tools/scientific_circt_broader_runtime_entrypoint.py \
  src/tools/scientific_circt_verilator_callsite_entrypoint.py \
  src/tools/scientific_circt_hls_attention_head_variant.py \
  src/tools/scientific_circt_hls_mlp_block_variants.py \
  src/tools/scientific_circt_source_variant_metadata.py \
  src/tools/scientific_circt_source_variant_runtime_handoff.py \
  src/tools/scientific_circt_source_variant_runtime_dispatcher.py \
  src/tools/scientific_circt_gategpt_microgpt_compare.py \
  src/tools/scientific_circt_evidence_audit.py \
  src/tools/scientific_circt_hybrid_advantage.py \
  src/tools/scientific_circt_gpu_selection_policy.py \
  src/tools/heavy_rtl_candidate_matrix.py \
  tests/contract/test_scientific_circt_gpu_candidate_plan.py \
  tests/contract/test_scientific_circt_dense_matmul_tile.py \
  tests/contract/test_scientific_circt_dense_matmul_tile_gpu_timing.py \
  tests/contract/test_scientific_circt_batched_reduction.py \
  tests/contract/test_scientific_circt_stencil_2d_tile.py \
  tests/contract/test_scientific_circt_softmax_exp_pipeline.py \
  tests/contract/test_scientific_circt_microgpt_ir_partition_probe.py \
  tests/contract/test_scientific_circt_microgpt_math_block.py \
  tests/contract/test_scientific_circt_microgpt_attention_head.py \
  tests/contract/test_scientific_circt_microgpt_mlp_slice.py \
  tests/contract/test_scientific_circt_microgpt_block_slice.py \
  tests/contract/test_scientific_circt_microgpt_inference_slice.py \
  tests/contract/test_scientific_circt_hybrid_protocol.py \
  tests/contract/test_scientific_circt_hybrid_dispatch_matrix.py \
  tests/contract/test_scientific_circt_runtime_handoff_abi.py \
  tests/contract/test_scientific_circt_runtime_handoff_adapter.py \
  tests/contract/test_scientific_circt_runtime_entrypoint.py \
  tests/contract/test_scientific_circt_broader_runtime_entrypoint.py \
  tests/contract/test_scientific_circt_verilator_callsite_entrypoint.py \
  tests/contract/test_scientific_circt_hls_attention_head_variant.py \
  tests/contract/test_scientific_circt_hls_mlp_block_variants.py \
  tests/contract/test_scientific_circt_source_variant_metadata.py \
  tests/contract/test_scientific_circt_gategpt_microgpt_compare.py \
  tests/contract/test_scientific_circt_evidence_audit.py \
  tests/contract/test_scientific_circt_hybrid_advantage.py \
  tests/contract/test_scientific_circt_gpu_selection_policy.py \
  tests/contract/test_heavy_rtl_candidate_matrix.py
git diff --check -- \
  src/tools/scientific_circt_gpu_candidate_plan.py \
  src/tools/scientific_circt_dense_matmul_tile.py \
  src/tools/scientific_circt_dense_matmul_tile_gpu_timing.py \
  src/tools/scientific_circt_batched_reduction.py \
  src/tools/scientific_circt_stencil_2d_tile.py \
  src/tools/scientific_circt_softmax_exp_pipeline.py \
  src/tools/scientific_circt_microgpt_ir_partition_probe.py \
  src/tools/scientific_circt_microgpt_math_block.py \
  src/tools/scientific_circt_microgpt_attention_head.py \
  src/tools/scientific_circt_microgpt_mlp_slice.py \
  src/tools/scientific_circt_microgpt_block_slice.py \
  src/tools/scientific_circt_microgpt_inference_slice.py \
  src/tools/scientific_circt_hybrid_protocol.py \
  src/tools/scientific_circt_hybrid_dispatch_matrix.py \
  src/tools/scientific_circt_runtime_handoff_abi.py \
  src/tools/scientific_circt_runtime_handoff_adapter.py \
  src/tools/scientific_circt_runtime_entrypoint.py \
  src/tools/scientific_circt_broader_runtime_entrypoint.py \
  src/tools/scientific_circt_verilator_callsite_entrypoint.py \
  src/tools/scientific_circt_hls_attention_head_variant.py \
  src/tools/scientific_circt_hls_mlp_block_variants.py \
  src/tools/scientific_circt_source_variant_metadata.py \
  src/tools/scientific_circt_source_variant_runtime_handoff.py \
  src/tools/scientific_circt_source_variant_runtime_dispatcher.py \
  src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp \
  src/hybrid/scientific_circt_adapter_bridge.c \
  src/hybrid/scientific_circt_verilator_callsite_bridge.cpp \
  src/tools/scientific_circt_gategpt_microgpt_compare.py \
  src/tools/scientific_circt_evidence_audit.py \
  src/tools/scientific_circt_hybrid_advantage.py \
  src/tools/scientific_circt_gpu_selection_policy.py \
  src/tools/heavy_rtl_candidate_matrix.py \
  tests/contract/test_scientific_circt_gpu_candidate_plan.py \
  tests/contract/test_scientific_circt_dense_matmul_tile.py \
  tests/contract/test_scientific_circt_dense_matmul_tile_gpu_timing.py \
  tests/contract/test_scientific_circt_batched_reduction.py \
  tests/contract/test_scientific_circt_stencil_2d_tile.py \
  tests/contract/test_scientific_circt_softmax_exp_pipeline.py \
  tests/contract/test_scientific_circt_microgpt_ir_partition_probe.py \
  tests/contract/test_scientific_circt_microgpt_math_block.py \
  tests/contract/test_scientific_circt_microgpt_attention_head.py \
  tests/contract/test_scientific_circt_microgpt_mlp_slice.py \
  tests/contract/test_scientific_circt_microgpt_block_slice.py \
  tests/contract/test_scientific_circt_microgpt_inference_slice.py \
  tests/contract/test_scientific_circt_hybrid_protocol.py \
  tests/contract/test_scientific_circt_hybrid_dispatch_matrix.py \
  tests/contract/test_scientific_circt_runtime_handoff_abi.py \
  tests/contract/test_scientific_circt_runtime_handoff_adapter.py \
  tests/contract/test_scientific_circt_runtime_entrypoint.py \
  tests/contract/test_scientific_circt_broader_runtime_entrypoint.py \
  tests/contract/test_scientific_circt_verilator_callsite_entrypoint.py \
  tests/contract/test_scientific_circt_hls_attention_head_variant.py \
  tests/contract/test_scientific_circt_hls_mlp_block_variants.py \
  tests/contract/test_scientific_circt_source_variant_metadata.py \
  tests/contract/test_scientific_circt_source_variant_runtime_handoff.py \
  tests/contract/test_scientific_circt_source_variant_runtime_dispatcher.py \
  tests/contract/test_scientific_circt_gategpt_microgpt_compare.py \
  tests/contract/test_scientific_circt_evidence_audit.py \
  tests/contract/test_scientific_circt_hybrid_advantage.py \
  tests/contract/test_scientific_circt_gpu_selection_policy.py \
  tests/contract/test_heavy_rtl_candidate_matrix.py \
  config/selection.json \
  README.md \
  docs/roadmap.md \
  docs/status.md \
  for_codex/issues.md \
  for_codex/issues/FC-070-scientific-circt-gpu-candidate-search.md
```

## Non-Goals

- No CIRCT execution by the plan alone; only the materializer command provides
  first-candidate CIRCT evidence.
- No generated SystemVerilog committed as source of truth.
- No Verilator build or GPU launch by the plan alone.
- No broad correctness equivalence, timing, speedup, or usefulness claim beyond
  the scoped measured evidence for named scientific testbenches.
- No automatic hybrid partition claim.
