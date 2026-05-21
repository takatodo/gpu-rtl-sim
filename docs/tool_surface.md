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

For automation, `src/tools/verilator_sidecar_shim.py` emits the same readiness surface as JSON. Exit code `0` means ready for the option shim, `2` means the target or mode is not ready for the shim, and `1` means input or planning error with a JSON error object on stderr.

The shim accepts `--stage <name> --emit-command` to expose one stage command as top-level JSON for automation. This remains non-executing output; unknown stages and `--emit-command` without `--stage` are JSON errors.

For the closest preview of the future direct Verilator surface, use `--emit-verilator-command`. It synthesizes top-level `verilator_command_argv` and shell-quoted `verilator_command` fields from structured stage details and appends `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>` without running the command.

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
