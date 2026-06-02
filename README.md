# GPU Toggle Coverage Minimal

Minimal extraction of the GPU-toggle coverage hybrid-runtime project.

## Goal

This repository is an experimental GPU sidecar runtime for RTL compiler frontends. Verilator is the current compatibility frontend because its generated C++ build path is the shortest route to a usable sidecar; CIRCT is a planned frontend target through the same sidecar contract idea.

The contract is the boundary between frontend-owned RTL/build information and sidecar-owned GPU build, run, and compare work. It should be represented in importable code and runtime metadata first. JSON output is useful for debug and review; automation may inspect it, but it should not become execution authority or the required runtime ABI.

Current pointer, mirrored from `config/selection.json`:

- `current_priority`: `package_verilator_use_gpu_first_scoped_wrapper_gate`
- `current_priority_source_artifact`: `config/scaling_gates/sync_verilator_use_gpu_first_path_completion_to_wrapper_task_gate.json`

The long-term shorthand Verilator-facing UX target remains:

```sh
verilator --use-gpu -f filelist.f --top-module top
```

That endpoint is not yet a general Verilator replacement. The current canonical preview and parser-minimum spelling is `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`. The current implementation is a scoped hybrid sidecar path with Verilator-like option plumbing. Supported paths should reach the GPU sidecar flow and compare CPU vs hybrid output. Unsupported paths should fail clearly instead of silently falling back or claiming GPU optimization.

The first scoped executable `--use-gpu` adapter path is complete. The current `--use-gpu` work is packaging that proven path as a Verilator-facing wrapper. It still selects one reviewed filelist/template/top path, requires an explicit `64x1` schedule unless a later reviewed gate changes that wrapper rule, and must keep unsupported paths fail-closed without adding arbitrary filelist support, dependency inference, automatic GPU allocation, timing/speedup, CIRCT execution, raw-state equality, or a JSON runtime ABI.

The frontend-neutral research target is:

```sh
gpu-sidecar --frontend verilator -f filelist.f --top-module top
gpu-sidecar --frontend circt -f filelist.f --top-module top
```

Those commands are a direction, not current user-facing support.

For RTLMeter, the target is to keep the RTLMeter workflow intact. A user should
be able to start from RTLMeter's own case selection and add GPU intent through
the existing Verilator command path, for example:

```sh
./rtlmeter run --cases OpenTitan:default:<test> --compileArgs "--use-gpu"
PATH=/path/to/gpu-verilator-wrapper:$PATH ./rtlmeter run --cases OpenTitan:default:<test>
```

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
The helper's default GPU candidate uses the current native-minimum schedule
spelling, `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1`;
`--compile-args` can override it for compatibility checks. Missing RTLMeter or
sidecar prerequisites produce `cannot_execute` or `gpu_execution_failed`, not a
CPU-as-GPU fallback.
Expanded-schedule failures include metadata for the captured schedule, preserved
parser inputs, and missing sidecar-owned context. That metadata is diagnostic
only and does not launch a repo-owned template as RTLMeter GPU evidence. A
complete RTLMeter sidecar context can be validated as metadata-ready, but the
actual launcher handoff remains a separate step and is still not execution-ready.
The compare helper now builds an RTLMeter sidecar context candidate from the
selected seed and passes it to the wrapper through `RTLMETER_SIDECAR_CONTEXT_JSON`.
That narrows the missing context list, but the env payload is still diagnostic
handoff metadata, not a runtime ABI.
For `Example:kind:hello`, the RTLMeter compile closure is known from the
descriptor, but it is kept separate from the hybrid execution closure because
the existing host-probe/template flow is not yet valid for stdout/cycles RTLMeter
evidence.

## Quickstart

Use the repo tools directly while the native GPU UX is still being hardened:

```sh
python3 src/tools/run_hybrid_benchmark.py pulp_ita_mha --shape 64x1 --dry-run
python3 src/tools/run_hybrid_benchmark.py paged_attention_kv_score --shape 64x1 --dry-run
python3 src/tools/verilator_sidecar_shim.py --target pulp_ita_mha --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --print-verilator-command
python3 src/tools/verilator_use_gpu_first_path.py --cc -f config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json --top-module pulp_ita_mha_gpu_cov_tb --use-gpu --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --first-use-gpu-dry-run
python3 -c 'from src.tools.verilator_use_gpu_wrapper_runtime import write_verilator_use_gpu_wrapper; write_verilator_use_gpu_wrapper("artifacts/use-gpu-wrapper/verilator")'
PATH="$PWD/artifacts/use-gpu-wrapper:$PATH" verilator --cc -f config/slice_launch_templates/filelist_known_template_pulp_ita_mha.json --top-module pulp_ita_mha_gpu_cov_tb --use-gpu --sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1 --first-use-gpu-dry-run
```

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

## What Is Supported

- Scoped template-based hybrid runs through `src/tools/run_hybrid_template.py`.
- Target-oriented runs through `src/tools/run_hybrid_benchmark.py`.
- A Verilator-sidecar option preview using `--sim-accel sidecar-gpu --sim-accel-states N --sim-accel-steps S`.
- A frontend contract shape where Verilator currently supplies the build-side metadata and future CIRCT work should supply equivalent sidecar metadata.
- Optional JSON plans for debug and review inspection.
- CPU-vs-hybrid correctness checking with `coverage_output_equivalence`.
- Non-executing RTLMeter command-shape inspection for preserving the future RTLMeter user path.
- An opt-in RTLMeter first-seed CPU reference run with a fail-closed generated Verilator wrapper boundary.

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
- If CPU-vs-hybrid compare reports raw state mismatch, check whether `coverage_output_equivalence` still passes; raw full-state equality is not the supported correctness policy.
- If `verilator --use-gpu` style commands are needed before the #33 wrapper lands, use `src/tools/verilator_sidecar_shim.py` or `src/tools/verilator_use_gpu_first_path.py` as the scoped preview path.
- If an RTLMeter command with `--compileArgs "--use-gpu"` only reports wrapper metadata, that is expected for the current public surface. It proves GPU intent reached the Verilator command path, not GPU execution or speedup.
- If `third_party/rtlmeter/rtlmeter` fails from the repo root with `No module named 'src.rtlmeter'`, use the documented compare helper; it prepends `third_party/rtlmeter` to `PYTHONPATH` for RTLMeter execution.
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
