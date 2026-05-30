# Verilator Sidecar Option Target

The long-term usability target is a direct Verilator option, not a project-specific wrapper.

## Target Spelling

Canonical option prefix: `verilator --sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`.

Use `python3 src/tools/run_hybrid_benchmark.py --list-targets` to inspect which targets currently expose a `sidecar_gpu` option-shim discovery block. Use `python3 src/tools/run_hybrid_benchmark.py --list-targets sidecar_gpu` for the focused sidecar discovery view referenced by operator-plan JSON discovery hints. Slice-template targets are marked `ready_for_template_shape` and list their ready stage names; dataset-backed targets remain not-ready for the direct Verilator option, but `mobile_vit --limit 128` now exposes non-executing `host_preprocess` and `rtl_sidecar_proxy_eval` stage names so the host/RTL boundary is visible from discovery.

The sidecar registry includes two tracked filelist-derived template targets, `filelist_paged_attention_kv_score` and `filelist_known_template_pulp_ita_mha`. They are static registry entries backed by reviewed launch templates and explicit source closure metadata. This is not arbitrary filelist parsing, not dependency inference for unknown RTL, and not native Verilator parser support.

```bash
verilator --cc --timing \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --sim-accel-estimate-efficiency \
  -Mdir artifacts/<target>_obj_dir \
  <rtl files> \
  --top-module <top>
```

The option should keep normal Verilator build semantics visible: source files, `--top-module`, `-Mdir`, defines, warnings, and timing flags still belong to the Verilator command line.

## Semantics

`--sim-accel sidecar-gpu` means:

- build or reuse the normal Verilator `--cc` object directory
- build the sidecar GPU artifacts from that object directory
- run the hybrid host/GPU path for the requested state/step schedule
- compare CPU and hybrid outputs with the documented policy, normally `coverage_output_equivalence`
- keep raw full-state equality out of the default claim

`--sim-accel-states <N>` and `--sim-accel-steps <S>` map to the existing state/step shape vocabulary:

- `N` independent states
- `S` eval steps per state
- state-parallel shapes such as `64x1` are expected to amortize launch and transfer overhead better than single-state repeated-step shapes such as `1x64`

`--sim-accel-shape <NxS>` may remain as a compact compatibility spelling, but it should not be the primary Verilator-facing form because `states` and `steps` are easier to read in a standard command-line help page.

`--sim-accel-estimate-efficiency` prints the short operator-facing estimate:

- `speedup_class`
- reason
- next action
- scoped observed speedup when matching reports already exist
- non-claims that separate performance estimates from CPU/GPU equivalence

## Current Compatibility Entrypoint

Until this is implemented inside Verilator, use the repository wrapper as the compatibility spelling:

```bash
python3 src/tools/run_hybrid_benchmark.py <target> --shape <NxS> --sidecar-gpu
```

This wrapper intentionally remains a migration surface. It should expose the same concepts as the target Verilator option while keeping reusable behavior in importable modules.

The wrapper accepts the planned option names as a stricter compatibility check:

```bash
python3 src/tools/run_hybrid_benchmark.py <target> \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --dry-run
```

## Source Patch Descriptor Boundary

The current native-parser path is still overlay-only. The first repo-owned source-patch descriptor and patch file live under `overlays/verilator/patches/`, pinned to upstream Verilator `v5.048` at peeled commit `d0aa828c217410fffc73d92077b6f4f54830357c`. The patch touches only upstream `src/V3Options.h` and `src/V3Options.cpp`, adding undocumented parse/store/validate-only `--sim-accel`, `--sim-accel-states`, and `--sim-accel-steps` handling. The descriptor validates as JSON, the patch applies and builds `verilator_bin` in the scoped build-only gate, the parser-only smoke has been reviewed for two positive expanded spellings plus six rejection cases, and integer hardening has been defined and reviewed for negative counts and `std::atoi` suffix inputs. This still does not claim broad native parser support, strict integer parsing implementation, execution, measurement, runtime handoff, or arbitrary RTL/filelist support.

`src/tools/verilator_sidecar_options.py` is the current shared mapping authority for `--sim-accel-states`, `--sim-accel-steps`, and compact `--sim-accel-shape`. On the wrapper, those `--sim-accel-*` shape spellings are enough to enter the sidecar preview path even if the explicit `--sim-accel sidecar-gpu` selector is omitted. The mapper rejects mixed shape spellings so the eventual Verilator implementation does not inherit ambiguous behavior.

`run_hybrid_benchmark.py --list-targets` exposes the same spellings under `sidecar_gpu.shape_spellings` for ready slice-template targets. The older `sidecar_gpu.requires` field remains the minimum expanded option pair for compatibility, while `sidecar_gpu.recommended_entrypoint` names the compact operator path (`--sim-accel-shape <NxS>`) and `sidecar_gpu.compatibility_entrypoint` names the expanded future-Verilator form. The focused `--list-targets sidecar_gpu` view also exposes `shortest_operator_path`, matching the documented three-command flow. `sidecar_gpu.operator_plan_command_template`, `sidecar_gpu.verilator_estimate_command_template`, and `sidecar_gpu.operator_plan_json_command_template` give the parameterized target-first preview commands; `sidecar_gpu.operator_plan_example_command`, `sidecar_gpu.verilator_estimate_example_command`, and `sidecar_gpu.operator_plan_json_example_command` give concrete non-executing `64x1` preview commands operators can try immediately. Those preview commands use the compact `--sim-accel-shape` entrypoint. Wrapper operator-plan JSON repeats the same recommended and compatibility entrypoints in `discovery_hint` and adds `requested_compatibility_entrypoint`, the concrete expanded spelling for the requested shape, so automation does not need to re-run discovery to preserve that distinction. The example shape is a starting point, not timing evidence by itself.

`--preflight` on the wrapper emits `sidecar_stage_plan` for template targets. This is the current implementation boundary for moving into Verilator: the stages are `verilator_build`, `host_probe_build`, `cpu_init_state`, `cpu_reference_output`, `gpu_artifact_build`, `hybrid_sidecar_run`, and `coverage_output_compare`. The printable command is kept for operators, while structured `details` keep the Verilator build inputs (`mdir`, `top_module`, source files, defines, and Verilator args), sidecar launch shape, state files, and compare policy machine-readable. The final stage must continue to use `coverage_output_equivalence`.

The same preflight block includes `verilator_option_readiness`. `ready_for_verilator_option_shim` means the wrapper plan has the minimum structured inputs for a future option shim: Verilator build directory, top module, source files, sidecar state/step shape, state I/O, and `coverage_output_equivalence` compare details. It does not mean Verilator itself already implements `--sim-accel`.

Wrapper preflight and summary JSON also include `verilator_option_preview`. Ready template targets include the synthesized direct-option command, matching `estimate_command` with `--sim-accel-estimate-efficiency`, concrete `requested_compatibility_entrypoint`, and handoff contract; not-ready targets keep a stable not-ready status and missing input list. Ready preflight and summary reports also carry the same `discovery_hint` as operator-plan JSON. The preview is non-executing metadata so the direct-option surface stays visible during normal dry-run and summary workflows.

For terminal dry-runs with `--sidecar-gpu` or explicit `--sim-accel sidecar-gpu`, the wrapper prints a compact `# verilator_option_preview` block before the existing command plan, including the plain command, estimate command, and concrete requested compatibility entrypoint. This keeps the Verilator-facing command visible in the shortest dry-run path while preserving the current wrapper execution plan and CPU/GPU comparison policy.

For JSON planning, `--sidecar-gpu --preflight` is accepted and remains JSON-only. The preflight report includes `efficiency_estimate` and `verilator_option_preview`; explicit terminal estimate flags such as `--estimate-efficiency` remain invalid with `--preflight`.

Preflight, summary, and operator-plan JSON include `operator_entrypoint` to record whether the invocation used `--sidecar-gpu`, explicit `--sim-accel`, or the ordinary target/shape surface. It also records `shape_source` as `shape`, `sim_accel_shape`, or `sim_accel_states_steps` so compact and expanded Verilator-style spellings stay auditable after normalization. `sim_accel` records the raw selector when present, while `effective_sim_accel` records the sidecar path selected by compatibility shape spellings or aliases. This is wrapper invocation metadata only, not execution or correctness evidence.

`src/tools/verilator_sidecar_shim.py` is the non-executing JSON boundary intended to match the future Verilator option handoff. It returns exit code `0` when `verilator_option_readiness.status` is `ready_for_verilator_option_shim`, exit code `2` when the target or mode is not ready for the shim, and exit code `1` for input/planning errors with a JSON error object on stderr. The shim accepts both expanded `--sim-accel-states <N> --sim-accel-steps <S>` and compact `--sim-accel-shape <NxS>` shape spellings through the shared mapper. The shim also includes the same efficiency estimate so performance expectations stay separate from correctness.

The shim can also select one planned stage and emit that stage command without executing it:

```bash
python3 src/tools/verilator_sidecar_shim.py \
  --target paged_attention_kv_score \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --stage hybrid_sidecar_run \
  --emit-command
```

`--emit-command` requires `--stage`. Unknown stages are JSON errors. Emitted commands are planning output only.

The recommended direct-option preview is `--emit-verilator-command`:

```bash
python3 src/tools/verilator_sidecar_shim.py \
  --target paged_attention_kv_score \
  --sim-accel-shape 64x1 \
  --emit-verilator-command
```

This adds top-level `verilator_command_argv` and `verilator_command` fields synthesized from the structured `verilator_build` and `hybrid_sidecar_run` stage details. `verilator_command_argv` is the machine-readable form; `verilator_command` is shell-quoted for human inspection. It is a future handoff preview only; it is not executed and is not a claim that Verilator already accepts the option.

When the shim can synthesize the command, the JSON report also includes `operator_plan`. This groups `command_argv`, shell-quoted `command`, concrete `requested_compatibility_entrypoint`, `efficiency_estimate`, `handoff_contract`, `discovery_hint`, and `correctness_policy: coverage_output_equivalence` in one machine-readable object for automation that wants the same information as the terminal operator view. The same `discovery_hint` is also repeated at the shim report top level, matching wrapper operator-plan JSON so automation can preserve the compact entrypoint and expanded future-Verilator spelling from either entrypoint. The handoff contract is non-executing metadata for the future Verilator-owned boundary: state authority, init/reference/candidate dumps, generated compare report path, and compare policy.

For terminal use, `--print-verilator-command` prints only the shell-quoted command when the shim is ready:

```bash
python3 src/tools/verilator_sidecar_shim.py \
  --target paged_attention_kv_score \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --print-verilator-command
```

If the target or mode is not ready, the shim keeps the JSON status output and exit code `2` instead of printing a fake command.

For the matching terminal efficiency view, use the Verilator-compatible estimate flag:

```bash
python3 src/tools/verilator_sidecar_shim.py \
  --target paged_attention_kv_score \
  --sim-accel-shape 64x1 \
  --sim-accel-estimate-efficiency
```

This is the current shim alias for `--print-efficiency-estimate`. It prints the same non-executing estimate carried in the JSON report. It is separate from the command-only mode and remains separate from correctness evidence. Not-ready targets still print the human estimate, but return exit code `2` so scripts can distinguish an estimate for a not-ready direct-option handoff from a ready operator path.

For a single operator view, use `--print-operator-plan`:

```bash
python3 src/tools/verilator_sidecar_shim.py \
  --target paged_attention_kv_score \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --print-operator-plan
```

This prints the synthesized command, the matching future Verilator command with `--sim-accel-estimate-efficiency`, and the same human-readable efficiency estimate. It still does not execute either command, and it does not replace the JSON form for automation.

The primary benchmark wrapper exposes the same terminal operator view with the target-first spelling:

```bash
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score \
  --sim-accel-shape 64x1 \
  --print-operator-plan
```

For a command-only target-first preview, replace `--print-operator-plan` with `--print-verilator-command`. For the matching estimate-command-only preview, use `--print-verilator-estimate-command`; it prints the same future Verilator command with `--sim-accel-estimate-efficiency` appended and nothing else. For the matching estimate-only target-first preview, use `--print-efficiency-estimate`. Use these compact wrapper paths when starting from `run_hybrid_benchmark.py --list-targets`; not-ready command and operator-plan previews return JSON with exit code `2`, while ready terminal output stays concise. The operator-plan terminal view prints `requested_compatibility_entrypoint` next to the synthesized command so the concrete future-Verilator suffix is visible without JSON. The expanded `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` spelling remains the explicit future-Verilator form and is still accepted by the wrapper for compatibility. The command-only preview stays command-only even when the short `--sidecar-gpu` alias is used.

The machine-readable operator plan keeps both command forms separate: `command` is the plain future Verilator sidecar command, while `estimate_command` appends `--sim-accel-estimate-efficiency`. This keeps command-only previews clean while still giving automation the exact future Verilator spelling for an estimate-annotated run.

On `run_hybrid_benchmark.py`, `--sim-accel-estimate-efficiency` follows the normal execution or `--dry-run` path and then prints the estimate. It is the wrapper-side compatibility spelling for the future Verilator option flag, not the non-executing preview selector. Use `--print-efficiency-estimate` for estimate-only preview output.

```bash
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score \
  --sim-accel-shape 64x1 \
  --sim-accel-estimate-efficiency \
  --dry-run
```

The same wrapper path can emit machine-readable JSON:

```bash
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score \
  --sim-accel-shape 64x1 \
  --operator-plan-json
```

This is still a non-executing operator plan. It carries the synthesized command, concrete `requested_compatibility_entrypoint`, efficiency estimate, handoff contract, `coverage_output_equivalence`, discovery hint, and non-claims without turning the estimate into correctness or timing evidence. The discovery hint records the requested shape separately from the recommended starting shape. The wrapper JSON declares `schema_role: target_first_operator_plan`; use the shim JSON for readiness/stage-detail handoff fields. If the target is not ready for the direct-option preview, the wrapper returns `status: not_ready_for_verilator_option_shim` JSON with exit code `2`, plus top-level `missing` and `fallback_command` fields for quick automation handling.

Readiness status strings are shared across discovery and JSON entrypoints: `ready_for_template_shape`, `ready_for_verilator_option_shim`, and `not_ready_for_verilator_option_shim`.

Resident modes are not direct Verilator option handoffs yet. Their not-ready stage plan exposes a `resident_state_reuse_workflow` or `persistent_resident_state_abi_workflow` fallback command, preserving the efficiency guidance for low-parallelism `1xN` shapes while keeping shim readiness separate from higher-level orchestration.

## Non-Claims

- This is not a new correctness policy.
- This is not raw full-state equality.
- This is not a broad speedup claim for arbitrary RTL.
- Dataset-backed flows still need a direct RTL sidecar handoff before they are ready for the Verilator option shim.
