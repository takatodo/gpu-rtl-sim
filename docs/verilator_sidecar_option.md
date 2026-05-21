# Verilator Sidecar Option Target

The long-term usability target is a direct Verilator option, not a project-specific wrapper.

## Target Spelling

Canonical option prefix: `verilator --sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`.

Use `python3 src/tools/run_hybrid_benchmark.py --list-targets` to inspect which targets currently expose a `sidecar_gpu` option-shim discovery block. Slice-template targets are marked `ready_for_template_shape`; dataset-backed targets remain not-ready for the direct Verilator option, but `mobile_vit --limit 128` now exposes non-executing `host_preprocess` and `rtl_sidecar_proxy_eval` stages so the host/RTL boundary is visible.

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

`src/tools/verilator_sidecar_options.py` is the current shared mapping authority for `--sim-accel-states`, `--sim-accel-steps`, and compact `--sim-accel-shape`. It rejects mixed shape spellings so the eventual Verilator implementation does not inherit ambiguous behavior.

`--preflight` on the wrapper emits `sidecar_stage_plan` for template targets. This is the current implementation boundary for moving into Verilator: the stages are `verilator_build`, `host_probe_build`, `cpu_init_state`, `cpu_reference_output`, `gpu_artifact_build`, `hybrid_sidecar_run`, and `coverage_output_compare`. The printable command is kept for operators, while structured `details` keep the Verilator build inputs (`mdir`, `top_module`, source files, defines, and Verilator args), sidecar launch shape, state files, and compare policy machine-readable. The final stage must continue to use `coverage_output_equivalence`.

The same preflight block includes `verilator_option_readiness`. `ready_for_verilator_option_shim` means the wrapper plan has the minimum structured inputs for a future option shim: Verilator build directory, top module, source files, sidecar state/step shape, state I/O, and `coverage_output_equivalence` compare details. It does not mean Verilator itself already implements `--sim-accel`.

`src/tools/verilator_sidecar_shim.py` is the non-executing JSON boundary intended to match the future Verilator option handoff. It returns exit code `0` when `verilator_option_readiness.status` is `ready_for_verilator_option_shim`, exit code `2` when the target or mode is not ready for the shim, and exit code `1` for input/planning errors with a JSON error object on stderr. The shim also includes the same efficiency estimate so performance expectations stay separate from correctness.

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
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --emit-verilator-command
```

This adds top-level `verilator_command_argv` and `verilator_command` fields synthesized from the structured `verilator_build` and `hybrid_sidecar_run` stage details. `verilator_command_argv` is the machine-readable form; `verilator_command` is shell-quoted for human inspection. It is a future handoff preview only; it is not executed and is not a claim that Verilator already accepts the option.

When the shim can synthesize the command, the JSON report also includes `operator_plan`. This groups `command_argv`, shell-quoted `command`, `efficiency_estimate`, `handoff_contract`, and `correctness_policy: coverage_output_equivalence` in one machine-readable object for automation that wants the same information as the terminal operator view. The handoff contract is non-executing metadata for the future Verilator-owned boundary: state authority, init/reference/candidate dumps, generated compare report path, and compare policy.

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

For the matching terminal efficiency view, use `--print-efficiency-estimate`:

```bash
python3 src/tools/verilator_sidecar_shim.py \
  --target paged_attention_kv_score \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --print-efficiency-estimate
```

This prints the same non-executing estimate carried in the JSON report. It is separate from the command-only mode and remains separate from correctness evidence.

For a single operator view, use `--print-operator-plan`:

```bash
python3 src/tools/verilator_sidecar_shim.py \
  --target paged_attention_kv_score \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --print-operator-plan
```

This prints the synthesized command followed by the same human-readable efficiency estimate. It still does not execute the command, and it does not replace the JSON form for automation.

The primary benchmark wrapper exposes the same terminal operator view with the target-first spelling:

```bash
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --print-operator-plan
```

Use this when starting from `run_hybrid_benchmark.py --list-targets`; use the shim JSON when automation needs structured stage details or stable not-ready exit codes.

The same wrapper path can emit machine-readable JSON:

```bash
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score \
  --sim-accel sidecar-gpu \
  --sim-accel-states 64 \
  --sim-accel-steps 1 \
  --operator-plan-json
```

This is still a non-executing operator plan. It carries the synthesized command, efficiency estimate, handoff contract, `coverage_output_equivalence`, and non-claims without turning the estimate into correctness or timing evidence. The wrapper JSON declares `schema_role: target_first_operator_plan`; use the shim JSON for readiness/stage-detail handoff fields. If the target is not ready for the direct-option preview, the wrapper returns `status: not_ready_for_verilator_option_shim` JSON with exit code `2`.

Readiness status strings are shared across discovery and JSON entrypoints: `ready_for_template_shape`, `ready_for_verilator_option_shim`, and `not_ready_for_verilator_option_shim`.

Resident modes are not direct Verilator option handoffs yet. Their not-ready stage plan exposes a `resident_state_reuse_workflow` or `persistent_resident_state_abi_workflow` fallback command, preserving the efficiency guidance for low-parallelism `1xN` shapes while keeping shim readiness separate from higher-level orchestration.

## Non-Claims

- This is not a new correctness policy.
- This is not raw full-state equality.
- This is not a broad speedup claim for arbitrary RTL.
- Dataset-backed flows still need a direct RTL sidecar handoff before they are ready for the Verilator option shim.
