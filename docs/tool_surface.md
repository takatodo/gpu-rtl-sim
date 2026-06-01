# Tool Surface

This page defines the small operator-facing tool surface. The repository may keep many helper modules under `src/tools/`, but routine work should start from the entrypoints below.

The tool surface is frontend-oriented, not Verilator-only. Verilator is the current compatibility frontend; CIRCT is a planned frontend target. The common object should be sidecar plan metadata: frontend-owned RTL/build inputs flow into sidecar-owned GPU build, run, and compare stages. JSON output is allowed for debug and review inspection, but it should not become execution authority or the required runtime ABI.

For RTLMeter, the user-facing goal is not to make users select this repository's
template JSON by hand. The target workflow keeps RTLMeter's own case selection
and adds GPU intent through the Verilator command path:

```bash
./rtlmeter run --cases <design>:<config>:<test> --compileArgs "--use-gpu"
PATH=/path/to/gpu-verilator-wrapper:$PATH ./rtlmeter run --cases <design>:<config>:<test>
```

These commands are a target workflow until a scoped seed is proven. Compile-only
success, copied RTLMeter-derived harnesses, and repo-specific launch-template
selection do not prove RTLMeter acceleration. Unsupported RTLMeter cases should
fail closed, and any RTLMeter JSON capture remains debug/inspection metadata.

## Primary Entrypoints

| Entrypoint | Use |
| --- | --- |
| `src/tools/run_hybrid_benchmark.py` | Verilator-like target/shape wrapper for supported benchmark workloads. Start here for routine dry-runs, summaries, and supported target discovery. |
| `src/tools/verilator_sidecar_shim.py` | Non-executing JSON shim for the planned `verilator --sim-accel sidecar-gpu` option. Use to inspect readiness, stage details, and efficiency estimate with stable exit codes. |
| `src/tools/run_hybrid_template.py` | Lower-level slice-template runner. Use when working directly from `config/slice_launch_templates/*.json`. |
| `src/tools/run_results_reproduction.py` | Public-pack reproduction, aggregate measurement workflows, and scoped policy dry-runs such as `--filelist-shape-breadth-gpu-allocation-policy --dry-run` and `--filelist-broader-shape-gpu-allocation-policy --dry-run`. |
| `src/tools/gen_hybrid_config.py` | Generate a new slice template, coverage-region file, and scaling-gate draft from a target/top/overlay description. |

RTLMeter helpers under `src/tools/rtlmeter_*` are not routine entrypoints yet.
They exist to capture RTLMeter's Verilator command shape and preserve the future
RTLMeter user path while the sidecar contract is hardened.
`src/tools/rtlmeter_cpu_gpu_compare_integration.py` is the first executing
RTLMeter gate: it is opt-in, writes generated evidence under `reports/`, and
fails closed when RTLMeter or the sidecar Verilator wrapper is unavailable.
When no `RTLMETER_SIDECAR_VERILATOR_WRAPPER` is supplied, it creates an ignored
`artifacts/.../wrapper/verilator` shim backed by
`src/tools/rtlmeter_verilator_wrapper_runtime.py`. That shim is an explicit
execution boundary: no-GPU argv delegates to the real Verilator after excluding
itself from PATH lookup, while GPU intent fails closed until a sidecar execution
path is wired. The older `src/tools/rtlmeter_verilator_path_wrapper.py` remains
inspect-only metadata and is not promoted to execution authority.
The compare helper defaults the GPU candidate to the expanded native-minimum
schedule spelling, `--sim-accel sidecar-gpu --sim-accel-states 64
--sim-accel-steps 1`, rather than `--use-gpu` alone. That keeps the failure at
the sidecar handoff boundary instead of failing earlier because no schedule was
selected.
At that boundary, `src/tools/rtlmeter_sidecar_handoff.py` records metadata only:
captured schedule, preserved parser inputs, and the missing sidecar-owned
context such as template/source-closure/host-probe/coverage metadata. It does
not call `run_hybrid_template.py`; launching an unrelated template would not be
RTLMeter GPU evidence.
The handoff can validate an explicitly supplied RTLMeter sidecar context and
mark it metadata-ready, but `sidecar_context_ready` remains false until a real
launcher boundary exists. The actual launcher handoff remains a separate
execution boundary.

## Runtime Building Blocks

The near-term target end state is a direct Verilator option, described in `docs/verilator_sidecar_option.md`.
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

For debug inspection, `src/tools/verilator_sidecar_shim.py` emits the same readiness surface as JSON. Exit code `0` means ready for the option shim, `2` means the target or mode is not ready for the shim, and `1` means input or planning error with a JSON error object on stderr. The shim accepts both expanded `--sim-accel-states <N> --sim-accel-steps <S>` and compact `--sim-accel-shape <NxS>` shape spellings. When a synthesized Verilator command is emitted, shim JSON carries the same `discovery_hint` as wrapper operator-plan JSON at the top level and inside `operator_plan`.

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

For debug inspection, use the same compact command with `--operator-plan-json` instead of `--print-operator-plan`, for example `python3 src/tools/run_hybrid_benchmark.py <target> --sim-accel-shape <NxS> --operator-plan-json`. It emits the synthesized command, `estimate_command` with `--sim-accel-estimate-efficiency`, concrete `requested_compatibility_entrypoint`, efficiency estimate, `correctness_policy`, discovery hint, and non-claims as JSON when ready; not-ready targets return JSON with exit code `2` instead of a plain text error. The discovery hint carries the requested shape, whether it matches the recommended starting shape, the same recommended/compatibility entrypoints exposed by sidecar discovery, and the concrete compatibility spelling for the requested shape. Summary JSON carries the same discovery hint when a direct-option preview can be synthesized. The wrapper JSON keeps `schema_role: target_first_operator_plan` for compatibility and adds `json_flow_role: debug_inspection`, `runtime_abi: false`, and `execution_authority: false`; the shim remains the fuller readiness/stage-detail debug boundary.

`operator_entrypoint.effective_sim_accel` records the selected sidecar path after compatibility normalization. This keeps raw `sim_accel: null` from looking like no accelerator was selected when the operator used compact `--sim-accel-shape`.

The readiness vocabulary is shared across `--list-targets`, wrapper debug JSON, and shim debug JSON: template-shape discovery uses `ready_for_template_shape`, executable shim readiness uses `ready_for_verilator_option_shim`, and not-ready paths use `not_ready_for_verilator_option_shim`.

Wrapper `--operator-plan-json` emits the operator-plan fields at top level for debug inspection. Shim JSON nests the same command/handoff shape under `operator_plan` when a command can be synthesized. In both forms, the plan groups `command_argv`, shell-quoted `command`, `estimate_command_argv`, shell-quoted `estimate_command`, concrete `requested_compatibility_entrypoint`, `efficiency_estimate`, `handoff_contract`, and `correctness_policy: coverage_output_equivalence`. The plain command remains command-only; the estimate command is the future Verilator spelling with `--sim-accel-estimate-efficiency`. The handoff contract records state authority, init/reference/candidate dumps, generated compare report path, and the compare policy without executing anything. Generated compare reports may still record raw final-state `match: false`; the operator contract is the selected `coverage_output_equivalence` policy, not raw state equality. JSON is only the serialized inspection view of this metadata.

Dataset-backed and resident modes are intentionally still not-ready for the direct Verilator option. Their stage plans expose non-executing fallback stages such as `host_preprocess`, `rtl_sidecar_proxy_eval`, `resident_state_reuse_workflow`, and `persistent_resident_state_abi_workflow` so operators can inspect the next supported command while keeping shim readiness separate from higher-level orchestration.

These are still public enough to appear in generated command plans, but they are not the first place an operator should start:

| Tool | Role |
| --- | --- |
| `src/tools/build_host_probe.py` | Build the generic Verilator host probe used by template plans. |
| `src/tools/build_vl_gpu.py` | Build GPU artifacts from a Verilator object directory; missing local pass tools are rebuilt on demand after clean. |
| `src/tools/run_vl_hybrid.py` | Launch the hybrid host/GPU runtime for an existing object directory and state dump; the local runtime binary is rebuilt on demand after clean. |
| `src/tools/compare_vl_hybrid_modes.py` | Compare CPU and hybrid dumps, normally with `coverage_output_equivalence`. |

## Helper Modules

Files with prefixes such as `build_vl_gpu_*`, `compare_vl_hybrid_*`, `hybrid_benchmark_*`, `hybrid_template_*`, `results_reproduction_*`, `mobile_vit_*`, and `check_staged_large_files_*` are implementation helpers. They should remain importable and tested, but should not become new routine entrypoints without a matching contract test and documentation mention.

## Output Policy

Generated evidence belongs under `reports/`; generated build and state material belongs under `artifacts/`. Neither directory is a source of truth. CPU/GPU correctness claims should continue to name the compared output words and the selected policy, usually `coverage_output_equivalence`, instead of claiming raw full-state equality.
