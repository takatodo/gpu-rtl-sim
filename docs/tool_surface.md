# Tool Surface

This page defines the small operator-facing tool surface. The repository may keep many helper modules under `src/tools/`, but routine work should start from the entrypoints below.

The tool surface is frontend-oriented, not Verilator-only. Verilator is the current compatibility frontend; CIRCT is a planned frontend target. The common object should be sidecar plan metadata: frontend-owned RTL/build inputs flow into sidecar-owned GPU build, run, and compare stages. JSON output is allowed for debug and review inspection, but it should not become execution authority or the required runtime ABI.

For RTLMeter, the user-facing goal is not to make users select this repository's
template JSON by hand. The target workflow keeps RTLMeter's own case selection
and adds GPU intent through the Verilator command path:

```bash
python3 -c 'from src.tools.rtlmeter_verilator_wrapper_runtime import write_rtlmeter_verilator_wrapper; write_rtlmeter_verilator_wrapper("artifacts/rtlmeter-wrapper/verilator")'
PYTHONPATH="$PWD/third_party/rtlmeter:$PYTHONPATH" PATH="$PWD/artifacts/rtlmeter-wrapper:$PATH" third_party/rtlmeter/rtlmeter run --cases <design>:<config>:<test> --compileArgs "--use-gpu"
```

These commands remain the target workflow for broad RTLMeter support. The scoped
`Example:kind:hello` seed now has a first-seed stdout/cycles handoff proof, but
compile-only success, copied RTLMeter-derived harnesses, and repo-specific
launch-template selection still do not prove RTLMeter acceleration. Unsupported
RTLMeter cases should fail closed, and any RTLMeter JSON capture remains
debug/inspection metadata.

## Three Layers

1. Current execution support: use the primary repo entrypoints for scoped template and benchmark targets, with CPU-vs-hybrid comparison based on `coverage_output_equivalence`.
2. Preview UX: use `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` and the wrapper/shim print modes to inspect the future Verilator-compatible surface; print modes and JSON plans are not execution authority.
3. Long-term goal: keep the tool surface compatible with a frontend-neutral sidecar fed by Verilator or CIRCT, and use the benchmark pack to identify LLM-serving-like RTL workloads that benefit from hybrid execution.

## Primary Entrypoints

| Entrypoint | Use |
| --- | --- |
| `src/tools/run_hybrid_benchmark.py` | Verilator-like target/shape wrapper for supported benchmark workloads. Start here for routine dry-runs, summaries, and supported target discovery. |
| `src/tools/run_hybrid_template.py` | Lower-level slice-template runner. Use when working directly from `config/slice_launch_templates/*.json`. |
| `src/tools/run_results_reproduction.py` | Public-pack reproduction, aggregate measurement workflows, and developer/audit-only policy dry-runs. Policy dry-runs do not imply arbitrary filelist support or automatic optimal GPU allocation. |
| `src/tools/gen_hybrid_config.py` | Generate a new slice template, coverage-region file, and scaling-gate draft from a target/top/overlay description. |

## Reproduction And Public Pack Boundary

`src/tools/run_results_reproduction.py --dry-run` is a preview surface. It
prints commands and expected generated outputs; it does not run measurements,
create archives, or promote generated evidence to source of truth. The public
pack preview is explicit:

```bash
python3 src/tools/run_results_reproduction.py --public-pack-archive --dry-run
```

That command prints include/exclude lines and refuses non-dry archive creation.
`reports/` entries are generated evidence snapshots, `artifacts/` entries are
rebuildable local outputs, and canonical project decisions stay in
`config/selection.json`, `docs/status.md`, `docs/roadmap.md`, and `README.md`.
Clean-checkout checks can use Python dry-runs; non-dry Verilator or CUDA runs
need the corresponding local toolchain and GPU runtime.

## Routine Operator Path

The normal sidecar path starts with `src/tools/run_hybrid_benchmark.py`, not the
JSON shim. Discover a ready target, dry-run it, then print the operator plan:

```bash
python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
```

The operator plan is terminal output for humans. JSON inspection is available
for debugging, but it is not the runtime ABI and should not become the required
operator path.

## Lower-Level Template Path

`run_hybrid_template.py` defaults to a concise seven-stage terminal summary for
non-dry runs and writes detailed generated logs under `reports/`. Dry-runs still
print full commands, and `--verbose` restores command/log streaming for local
debugging. The generated logs are evidence only, not source of truth.

RTLMeter helpers under `src/tools/rtlmeter_*` are not routine entrypoints yet.
They exist to capture RTLMeter's Verilator command shape and preserve the future
RTLMeter user path while the sidecar contract is hardened.
gateGPT helpers such as `src/tools/gategpt_testbench_probe.py` and
`src/tools/gategpt_entry_sliced_cubin_chain.py` are FC-069 diagnostic
entrypoints, not routine benchmark entrypoints. The entry-sliced CUBIN-chain
helper regenerates generated PTX/CUBIN artifacts under `artifacts/` and writes
evidence under `reports/`; it does not execute kernels or claim speedup,
usefulness, or broad gateGPT PASS/FAIL authority.
`src/tools/gategpt_stage112_store_source_summary.py` is an FC-073 evidence audit
helper. It joins Stage112 runtime events with the LLVM metadata source map, but
static metadata rows remain non-authoritative unless a runtime event names the
same source id.
`src/tools/rtlmeter_vortex_ptx_entry_slice.py --stub-func` is a ptxas-surface
diagnostic only: it can replace a selected reachable `.func` body with a
ret-only stub to prove that a large callee body is driving compile cost. A stub
slice or CUBIN is not runtime correctness evidence and must not be used for
semantic classification.
`src/tools/rtlmeter_cpu_gpu_compare_integration.py` is an opt-in
RTLMeter reference-vs-sidecar-candidate compare helper. It writes generated
evidence under `reports/` and fails closed when RTLMeter or the sidecar
Verilator wrapper is unavailable.
When no `RTLMETER_SIDECAR_VERILATOR_WRAPPER` is supplied, it creates an ignored
`artifacts/.../wrapper/verilator` shim backed by
`src/tools/rtlmeter_verilator_wrapper_runtime.py`. That shim is an explicit
execution boundary: no-GPU argv delegates to the real Verilator after excluding
itself from PATH lookup. Broad GPU intent still fails closed; the current
exception is the scoped first-seed stdout/cycles proxy/marker handoff. The older
`src/tools/rtlmeter_verilator_path_wrapper.py` remains
inspect-only metadata and is not promoted to execution authority.
`RTLMETER_SIDECAR_VERILATOR_WRAPPER` names the wrapper command RTLMeter invokes.
`RTLMETER_REAL_VERILATOR` names the non-wrapper Verilator binary behind that
wrapper, or the wrapper resolves one from filtered PATH. If that real binary
rejects the expanded sidecar argv with `Invalid option: --sim-accel`, the
compare report names
`real_verilator_not_sidecar_capable_for_expanded_rtlmeter_argv` rather than
falling back to CPU or claiming GPU execution.
The compare report also carries `real_verilator_preflight`: missing means no
non-wrapper real Verilator was selected after excluding the wrapper itself;
selected means the binary was found but sidecar capability is still proven only
by the later RTLMeter Verilate invocation.
The compare helper defaults the GPU candidate to the expanded native-minimum
schedule spelling, `--sim-accel sidecar-gpu --sim-accel-states 64
--sim-accel-steps 1`, rather than `--use-gpu` alone. That keeps the failure at
the sidecar handoff boundary instead of failing earlier because no schedule was
selected.
At that boundary, `src/tools/rtlmeter_sidecar_handoff.py` records captured
schedule, preserved parser inputs, and sidecar-owned context. It does not call
`run_hybrid_template.py`; launching an unrelated template would not be RTLMeter
GPU evidence.
When RTLMeter's Verilator argv omits `-Mdir`, the handoff records Verilator's
default output directory as `obj_dir` with `parser_payload_mdir_source:
verilator_default_obj_dir`. The first-seed runner path now uses that metadata,
the reviewed authority registry, a PATH-selected wrapper, and a marker-backed
`Vsim__main.cpp` proxy handoff to run the opt-in
`Example:kind:hello` stdout/cycles compare. The latest real opt-in evidence is
`status=passed`, `comparison.status=passed`,
`stdout_cycles_sidecar_runner.execution_authority=true`, and
`sidecar_execution_invoked=true`.
For RTLMeter, `RTLMETER_SIDECAR_CONTEXT_JSON` is a wrapper-to-handoff diagnostic
channel used by the compare helper to pass the current context candidate. It is
not the stable sidecar ABI.
The first-seed proof is not `run_hybrid_template.py` evidence and does not use
the RTLMeter launcher materializer as execution authority.
The native-Verilator bridge work has accepted metadata and failure-classification
evidence for a scoped wrapper-mediated process-to-launcher path. That evidence
is a technical prerequisite, not the current public task: the active task is the
external user readiness audit after the scoped `--use-gpu` wrapper completion.
Launcher start, bridge-path compare, timing, and broad native-option claims
remain out of scope.
RTLMeter context candidates distinguish compile source closure from hybrid
execution source closure. `Example:kind:hello` now has reviewed stdout/cycles
source-closure authority for this first-seed lane.
`config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json` records
that distinction as metadata-only config. It is not a `run_hybrid_template.py`
input; launcher argv still requires a separate reviewed runtime launch template.
The wrapper may load that registry for diagnostics, but the registry is not
execution authority. Reviewed RTLMeter source closure requires more than
`status: complete`: it must bind target/mode/case, source/include/filelist
entries, stdout/cycles observables, runner strategy, reviewed host-probe status,
`cpu_as_gpu_fallback_allowed: false`, and review evidence. A thin
`status`/`authority` payload remains blocked, and a metadata-only registry only
feeds explicit `authority_registry.source_closure.*` missing-context diagnostics.
Registry and source-closure targets must also match the requested sidecar
context target. For the first seed only, valid wrapper proxy-marker evidence
plus current-run stdout/cycles observables can set `execution_authority=true`
and `sidecar_execution_invoked=true`.
Public docs should still describe this as a scoped first-seed handoff proof:
CPU reference output remains owned by RTLMeter, candidate execution remains
bounded to the reviewed sidecar proxy lane, comparison is limited to
`normalized_stdout` and `rtlmeter_cycles`, CPU-as-GPU fallback is forbidden,
`gpu_execution_claimed=false`, `speedup_claimed=false`, and `runtime_abi=false`.
Generated stdout/cycles reports remain generated evidence, not source of truth.

## Runtime Building Blocks

The near-term target end state is a direct Verilator option, described in `docs/verilator_sidecar_option.md`.
The current active work is the external user readiness audit, not additional
native direct-command implementation. Observable-ordering helper work remains a
technical follow-up lane and must not be presented as current public support.
The separate process-to-launcher CLI run started the exact `run_hybrid_template.py`
launcher argv for `pulp_ita_mha 64x1`, reached sidecar stages, and reached
`coverage_output_equivalence` compare from reviewed fixture metadata, but it
remains prerequisite evidence rather than bridge-path authority. Timing,
broad filelist support, runtime/ABI change, production-throughput claims, broad
native option support, and direct Verilator sidecar execution remain out of
scope until later reviewed evidence proves them.
Until that exists in Verilator itself, use this compatibility spelling:

```bash
python3 src/tools/run_hybrid_benchmark.py <target> --shape <NxS> --sidecar-gpu
```

`--sidecar-gpu` uses the same benchmark plan as the target wrapper and adds the short efficiency estimate. It is a migration surface toward the direct Verilator option, and it does not replace the documented CPU/GPU compare policy.

Use `python3 src/tools/run_hybrid_benchmark.py --list-targets` before choosing a target. Its `sidecar_gpu` block shows whether a target is ready for the template-shape option shim, the ready template stage names, not-ready resident fallback stage names, and dataset-backed stage names or inspect commands. Use `python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu` for the focused sidecar discovery view referenced by terminal operator plans and debug JSON discovery hints. Ready slice-template targets also include parameterized and concrete `64x1` commands for terminal operator plans, estimate-command previews, and JSON debug plans, with `recommended_entrypoint` separating compact `--sim-accel-shape <NxS>` use from the expanded compatibility spelling.

The shortest sidecar operator path is:

```bash
python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --print-operator-plan
```

The focused sidecar discovery JSON exposes the terminal sequence as `shortest_operator_path` and keeps the JSON inspection sequence in `debug_json_path`.

Use `python3 src/tools/run_hybrid_benchmark.py --help` for the shortest supported examples: target discovery, `--sidecar-gpu --dry-run`, `--sidecar-gpu --preflight`, terminal command preview, terminal estimate-command preview, terminal operator plan, and debug JSON inspection.

The wrapper also accepts the planned Verilator shape spelling so the option semantics have one tested mapping before they move into Verilator itself:

```bash
python3 src/tools/run_hybrid_benchmark.py <target> \
  --sim-accel sidecar-gpu \
  --sim-accel-states <N> \
  --sim-accel-steps <S> \
  --dry-run
```

`--sim-accel-shape <NxS>` remains a compact compatibility spelling. On the wrapper, any `--sim-accel-*` shape spelling is treated as a sidecar-compatible entrypoint for dry-run preview and efficiency output. The implementation for these mappings lives in `src/tools/verilator_sidecar_options.py`; keep that module shared rather than duplicating shape parsing in each entrypoint.

`--preflight` includes a `sidecar_stage_plan` for template targets. That stage plan names the intended direct-Verilator execution boundary: `verilator_build`, `host_probe_build`, `cpu_init_state`, `cpu_reference_output`, `gpu_artifact_build`, `hybrid_sidecar_run`, and `coverage_output_compare`. Each stage keeps the printable command plus structured `details`; the `verilator_build` details include `mdir`, `top_module`, source files, defines, and Verilator args, and the compare stage keeps `coverage_output_equivalence` as the policy.

The stage plan also includes `verilator_option_readiness`. `ready_for_verilator_option_shim` means the wrapper plan has the required structured inputs for a future option shim; it is not execution evidence and does not mean Verilator itself already implements `--sim-accel`.

Wrapper preflight and summary JSON also include `verilator_option_preview`. Ready targets include the synthesized command, matching `estimate_command` with `--sim-accel-estimate-efficiency`, concrete `requested_compatibility_entrypoint`, and the handoff contract; not-ready targets keep the not-ready status and missing input list. Ready preflight and summary reports also carry the same `discovery_hint` as operator-plan JSON. This lets operators inspect the future direct-option surface from the same target-first dry-run or summary path without treating the preview as execution evidence.

When `--dry-run` is invoked with `--sidecar-gpu` or explicit `--sim-accel sidecar-gpu`, the wrapper prints a short `# verilator_option_preview` block before the existing command plan. Ready targets show the synthesized command, matching estimate command, and concrete requested compatibility entrypoint; not-ready targets show the missing input list but keep dry-run non-fatal.

`--sidecar-gpu --preflight` stays JSON-only: it accepts the short sidecar spelling, includes the normal `efficiency_estimate` object and `verilator_option_preview`, and does not print the terminal `# efficiency_estimate` block. Explicit human/JSON estimate output flags remain rejected with `--preflight`.

Preflight and summary JSON include `operator_entrypoint` so debug tooling can distinguish the short `--sidecar-gpu` alias, explicit `--sim-accel` compatibility spelling, and ordinary target/shape runs without scraping the terminal output.

## Shim Preview And Debug Path

For debug inspection, `src/tools/verilator_sidecar_shim.py` emits the same readiness surface as JSON. It is a non-executing preview for the planned `verilator --sim-accel sidecar-gpu` handoff, not the first routine operator entrypoint. Exit code `0` means ready for the option shim, `2` means the target or mode is not ready for the shim, and `1` means input or planning error with a JSON error object on stderr. The shim accepts both expanded `--sim-accel-states <N> --sim-accel-steps <S>` and compact `--sim-accel-shape <NxS>` shape spellings. When a synthesized Verilator command is emitted, shim JSON carries the same `discovery_hint` as wrapper operator-plan JSON at the top level and inside `operator_plan`.

The shim accepts `--stage <name> --emit-command` to expose one stage command as top-level JSON for debug inspection. This remains non-executing output; unknown stages and `--emit-command` without `--stage` are JSON errors.

For the closest preview of the future direct Verilator surface, use `--emit-verilator-command`. It synthesizes top-level `verilator_command_argv` and shell-quoted `verilator_command` fields from structured stage details and appends `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` without running the command.

For a terminal-only preview, `--print-verilator-command` prints just the shell-quoted command when the shim is ready. `--print-verilator-estimate-command` prints just the matching command with `--sim-accel-estimate-efficiency` appended. Not-ready targets keep the JSON status output and exit code `2`.

For the matching terminal estimate, `--print-efficiency-estimate` prints the human-readable speedup class, reason, next action, and non-claims without executing commands. The shim also accepts the Verilator-compatible alias `--sim-accel-estimate-efficiency` for the same estimate-only mode. It cannot be combined with `--print-verilator-command`.

For an operator-oriented terminal view, `--print-operator-plan` prints the synthesized command, the matching future Verilator command with `--sim-accel-estimate-efficiency`, and the same efficiency estimate. The terminal print-only modes are mutually exclusive; use the JSON output only when inspecting structured command fields and stage details.

The same command-only, estimate-command-only, estimate-only, and operator views are also available from the primary wrapper as `python3 src/tools/run_hybrid_benchmark.py <target> --sim-accel-shape <NxS> --print-verilator-command`, `--print-verilator-estimate-command`, `--print-efficiency-estimate`, or `--print-operator-plan`. That path keeps the usual target/shape entrypoint while still avoiding execution. The operator view prints the synthesized command plus `requested_compatibility_entrypoint`, making the concrete future-Verilator suffix visible without requiring JSON. The expanded `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` spelling remains the explicit future-Verilator form.

On the primary wrapper, `--sim-accel-estimate-efficiency` is not a print-only preview selector. It follows the normal execution or `--dry-run` command path and then prints the estimate, matching the intended future Verilator flag behavior. Use `--print-efficiency-estimate` for a non-executing estimate-only preview.

```bash
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --sim-accel-shape 64x1 --sim-accel-estimate-efficiency --dry-run
```

## Debug JSON Inspection Path

For debug inspection from the primary wrapper, use the same compact command with `--operator-plan-json` instead of `--print-operator-plan`, for example `python3 src/tools/run_hybrid_benchmark.py <target> --sim-accel-shape <NxS> --operator-plan-json`. It emits the synthesized command, `estimate_command` with `--sim-accel-estimate-efficiency`, concrete `requested_compatibility_entrypoint`, efficiency estimate, `correctness_policy`, discovery hint, and non-claims as JSON when ready; not-ready targets return JSON with exit code `2` instead of a plain text error. The discovery hint carries the requested shape, whether it matches the recommended starting shape, the same recommended/compatibility entrypoints exposed by sidecar discovery, and the concrete compatibility spelling for the requested shape. Summary JSON carries the same discovery hint when a direct-option preview can be synthesized. The wrapper JSON keeps `schema_role: target_first_operator_plan` for compatibility and adds `json_flow_role: debug_inspection`, `runtime_abi: false`, and `execution_authority: false`; the shim remains the fuller readiness/stage-detail debug boundary.

`operator_entrypoint.effective_sim_accel` records the selected sidecar path after compatibility normalization. This keeps raw `sim_accel: null` from looking like no accelerator was selected when the operator used compact `--sim-accel-shape`.

The readiness vocabulary is shared across `--list-targets`, wrapper debug JSON, and shim debug JSON: template-shape discovery uses `ready_for_template_shape`, executable shim readiness uses `ready_for_verilator_option_shim`, and not-ready paths use `not_ready_for_verilator_option_shim`.

Wrapper `--operator-plan-json` emits the operator-plan fields at top level for debug inspection. Shim JSON nests the same command/handoff shape under `operator_plan` when a command can be synthesized. In both forms, the plan groups `command_argv`, shell-quoted `command`, `estimate_command_argv`, shell-quoted `estimate_command`, concrete `requested_compatibility_entrypoint`, `efficiency_estimate`, `handoff_contract`, and `correctness_policy: coverage_output_equivalence`. The plain command remains command-only; the estimate command is the future Verilator spelling with `--sim-accel-estimate-efficiency`. The handoff contract records state authority, init/reference/candidate dumps, generated compare report path, and the compare policy without executing anything. Generated compare reports may still record raw final-state `match: false`; the operator contract is the selected `coverage_output_equivalence` policy, not raw state equality. JSON is only the serialized inspection view of this metadata.

Dataset-backed and resident modes are intentionally still not-ready for the direct Verilator option. Their stage plans expose non-executing fallback stages such as `host_preprocess`, `rtl_sidecar_proxy_eval`, `resident_state_reuse_workflow`, and `persistent_resident_state_abi_workflow` so operators can inspect the next supported command while keeping shim readiness separate from higher-level orchestration.

These are still public enough to appear in generated command plans, but they are not the first place an operator should start:

| Tool | Role |
| --- | --- |
| `src/tools/build_host_probe.py` | Build the generic Verilator host probe used by template plans. |
| `src/tools/build_vl_gpu.py` | Build GPU artifacts from a Verilator object directory; missing local pass tools are rebuilt under `artifacts/tool_bins/passes/` on demand after clean. |
| `src/tools/run_vl_hybrid.py` | Launch the hybrid host/GPU runtime for an existing object directory and state dump; the local runtime binary is rebuilt under `artifacts/tool_bins/hybrid/` on demand after clean. |
| `src/tools/compare_vl_hybrid_modes.py` | Compare CPU and hybrid dumps, normally with `coverage_output_equivalence`. |

## Helper Modules

Files with prefixes such as `build_vl_gpu_*`, `compare_vl_hybrid_*`, `hybrid_benchmark_*`, `hybrid_template_*`, `results_reproduction_*`, `mobile_vit_*`, and `check_staged_large_files_*` are implementation helpers. They should remain importable and tested, but should not become new routine entrypoints without a matching contract test and documentation mention.

`scientific_circt_*` files under `src/tools/` and `src/hybrid/` are the scoped scientific-CIRCT GPU candidate lane (FC-070/FC-072/FC-074), not part of the primary Verilator sidecar entrypoints above. `src/tools/scientific_circt_source_variant_bridge_emit.py` is its thin CLI: `--source-variant <name> --emit-header --no-execute` renders one source-variant's bridge gate header, `--all-promoted --emit-header --no-execute` renders headers for every promoted (`policy: promote_to_hls_gpu`) row, and `--source-variant <name> --run` compiles and runs the shared `src/hybrid/scientific_circt_source_variant_verilator_bridge.cpp` against that row's own Verilator object directory, exiting 0 only when CPU/GPU output and control-checksum both match. Non-promoted or unknown rows (for example the `block2_hls_friendly` fallback-baseline row) fail closed with a non-zero exit and no header written. The header/port-map derivation itself lives in `src/tools/scientific_circt_bridge_spec.py`'s `BridgeSpec` helper: it turns one `reports/scientific_circt_source_variant_metadata.json` row into a fail-closed `BridgeSpec` (port names sourced from the HLS generator modules, never from artifact `*_bridge.cpp` files or JSON) and renders the generated gate header from it. As with the rest of this lane, the header is compile-time specialization and an argv gate only; correctness authority stays CPU-vs-GPU mismatch==0 at runtime.

## Output Policy

Generated evidence belongs under `reports/`; generated build and state material belongs under `artifacts/`. Neither directory is a source of truth. CPU/GPU correctness claims should continue to name the compared output words and the selected policy, usually `coverage_output_equivalence`, instead of claiming raw full-state equality.
