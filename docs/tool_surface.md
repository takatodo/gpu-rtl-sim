# Tool Surface

This page defines the small operator-facing tool surface. The repository may keep many helper modules under `src/tools/`, but routine work should start from the entrypoints below.

## Primary Entrypoints

| Entrypoint | Use |
| --- | --- |
| `src/tools/run_hybrid_benchmark.py` | Verilator-like target/shape wrapper for supported benchmark workloads. Start here for routine dry-runs, summaries, and supported target discovery. |
| `src/tools/verilator_sidecar_shim.py` | Non-executing JSON shim for the planned `verilator --sim-accel sidecar-gpu` option. Use to inspect readiness, stage details, and efficiency estimate with stable exit codes. |
| `src/tools/run_hybrid_template.py` | Lower-level slice-template runner. Use when working directly from `config/slice_launch_templates/*.json`. |
| `src/tools/run_results_reproduction.py` | Public-pack reproduction and aggregate measurement workflows. Use for documented result refreshes and dry-run smoke checks. |
| `src/tools/gen_hybrid_config.py` | Generate a new slice template, coverage-region file, and scaling-gate draft from a target/top/overlay description. |

## Runtime Building Blocks

The target end state is a direct Verilator option, described in `docs/verilator_sidecar_option.md`.
Until that exists in Verilator itself, use this compatibility spelling:

```bash
python3 src/tools/run_hybrid_benchmark.py <target> --shape <NxS> --sidecar-gpu
```

`--sidecar-gpu` uses the same benchmark plan as the target wrapper and adds the short efficiency estimate. It is a migration surface toward the direct Verilator option, and it does not replace the documented CPU/GPU compare policy.

Use `python3 src/tools/run_hybrid_benchmark.py --list-targets` before choosing a target. Its `sidecar_gpu` block shows whether a target is ready for the template-shape option shim, the ready template stage names, not-ready resident fallback stage names, and dataset-backed stage names or inspect commands.

Use `python3 src/tools/run_hybrid_benchmark.py --help` for the shortest supported examples: target discovery, terminal operator plan, and JSON operator plan.

The wrapper also accepts the planned Verilator shape spelling so the option semantics have one tested mapping before they move into Verilator itself:

```bash
python3 src/tools/run_hybrid_benchmark.py <target> \
  --sim-accel sidecar-gpu \
  --sim-accel-states <N> \
  --sim-accel-steps <S> \
  --dry-run
```

`--sim-accel-shape <NxS>` remains a compact compatibility spelling. The implementation for these mappings lives in `src/tools/verilator_sidecar_options.py`; keep that module shared rather than duplicating shape parsing in each entrypoint.

`--preflight` includes a `sidecar_stage_plan` for template targets. That stage plan names the intended direct-Verilator execution boundary: `verilator_build`, `host_probe_build`, `cpu_init_state`, `cpu_reference_output`, `gpu_artifact_build`, `hybrid_sidecar_run`, and `coverage_output_compare`. Each stage keeps the printable command plus structured `details`; the `verilator_build` details include `mdir`, `top_module`, source files, defines, and Verilator args, and the compare stage keeps `coverage_output_equivalence` as the policy.

The stage plan also includes `verilator_option_readiness`. `ready_for_verilator_option_shim` means the wrapper plan has the required structured inputs for a future option shim; it is not execution evidence and does not mean Verilator itself already implements `--sim-accel`.

Wrapper preflight and summary JSON also include `verilator_option_preview`. Ready targets include the synthesized command plus the handoff contract; not-ready targets keep the not-ready status and missing input list. This lets operators inspect the future direct-option surface from the same target-first dry-run or summary path without treating the preview as execution evidence.

When `--dry-run` is invoked with `--sidecar-gpu` or explicit `--sim-accel sidecar-gpu`, the wrapper prints a short `# verilator_option_preview` block before the existing command plan. Ready targets show the synthesized command; not-ready targets show the missing input list but keep dry-run non-fatal.

`--sidecar-gpu --preflight` stays JSON-only: it accepts the short sidecar spelling, includes the normal `efficiency_estimate` object and `verilator_option_preview`, and does not print the terminal `# efficiency_estimate` block. Explicit human/JSON estimate output flags remain rejected with `--preflight`.

Preflight and summary JSON include `operator_entrypoint` so automation can distinguish the short `--sidecar-gpu` alias, explicit `--sim-accel` compatibility spelling, and ordinary target/shape runs without scraping the terminal output.

For automation, `src/tools/verilator_sidecar_shim.py` emits the same readiness surface as JSON. Exit code `0` means ready for the option shim, `2` means the target or mode is not ready for the shim, and `1` means input or planning error with a JSON error object on stderr.

The shim accepts `--stage <name> --emit-command` to expose one stage command as top-level JSON for automation. This remains non-executing output; unknown stages and `--emit-command` without `--stage` are JSON errors.

For the closest preview of the future direct Verilator surface, use `--emit-verilator-command`. It synthesizes top-level `verilator_command_argv` and shell-quoted `verilator_command` fields from structured stage details and appends `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` without running the command.

For a terminal-only preview, `--print-verilator-command` prints just the shell-quoted command when the shim is ready. Not-ready targets keep the JSON status output and exit code `2`.

For the matching terminal estimate, `--print-efficiency-estimate` prints the human-readable speedup class, reason, next action, and non-claims without executing commands. It cannot be combined with `--print-verilator-command`.

For an operator-oriented terminal view, `--print-operator-plan` prints the synthesized command followed by the same efficiency estimate. The three print-only modes are mutually exclusive; use the JSON output for automation that needs both structured command fields and stage details.

The same command-only, estimate-only, and operator views are also available from the primary wrapper as `python3 src/tools/run_hybrid_benchmark.py <target> --sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S> --print-verilator-command`, `--print-efficiency-estimate`, or `--print-operator-plan`. That path keeps the usual target/shape entrypoint while still avoiding execution.

For wrapper-first automation, use the same command with `--operator-plan-json` instead of `--print-operator-plan`. It emits the synthesized command, efficiency estimate, `correctness_policy`, and non-claims as JSON when ready; not-ready targets return JSON with exit code `2` instead of a plain text error. The wrapper JSON declares `schema_role: target_first_operator_plan`; the shim remains the fuller readiness/stage-detail boundary.

The readiness vocabulary is shared across `--list-targets`, wrapper operator-plan JSON, and shim JSON: template-shape discovery uses `ready_for_template_shape`, executable shim readiness uses `ready_for_verilator_option_shim`, and not-ready paths use `not_ready_for_verilator_option_shim`.

When a command can be synthesized, the JSON output also includes `operator_plan`, grouping `command_argv`, shell-quoted `command`, `efficiency_estimate`, `handoff_contract`, and `correctness_policy: coverage_output_equivalence`. The handoff contract records state authority, init/reference/candidate dumps, generated compare report path, and the compare policy without executing anything.

Dataset-backed and resident modes are intentionally still not-ready for the direct Verilator option. Their stage plans expose non-executing fallback stages such as `host_preprocess`, `rtl_sidecar_proxy_eval`, `resident_state_reuse_workflow`, and `persistent_resident_state_abi_workflow` so operators can inspect the next supported command while keeping shim readiness separate from higher-level orchestration.

These are still public enough to appear in generated command plans, but they are not the first place an operator should start:

| Tool | Role |
| --- | --- |
| `src/tools/build_host_probe.py` | Build the generic Verilator host probe used by template plans. |
| `src/tools/build_vl_gpu.py` | Build GPU artifacts from a Verilator object directory. |
| `src/tools/run_vl_hybrid.py` | Launch the hybrid host/GPU runtime for an existing object directory and state dump. |
| `src/tools/compare_vl_hybrid_modes.py` | Compare CPU and hybrid dumps, normally with `coverage_output_equivalence`. |

## Helper Modules

Files with prefixes such as `build_vl_gpu_*`, `compare_vl_hybrid_*`, `hybrid_benchmark_*`, `hybrid_template_*`, `results_reproduction_*`, `mobile_vit_*`, and `check_staged_large_files_*` are implementation helpers. They should remain importable and tested, but should not become new routine entrypoints without a matching contract test and documentation mention.

## Output Policy

Generated evidence belongs under `reports/`; generated build and state material belongs under `artifacts/`. Neither directory is a source of truth. CPU/GPU correctness claims should continue to name the compared output words and the selected policy, usually `coverage_output_equivalence`, instead of claiming raw full-state equality.
