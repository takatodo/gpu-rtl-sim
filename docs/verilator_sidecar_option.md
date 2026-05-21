# Verilator Sidecar Option Target

The long-term usability target is a direct Verilator option, not a project-specific wrapper.

## Target Spelling

Canonical option prefix: `verilator --sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`.

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

## Non-Claims

- This is not a new correctness policy.
- This is not raw full-state equality.
- This is not a broad speedup claim for arbitrary RTL.
- Dataset-backed flows still need host preprocessing separated from RTL sidecar timing.
