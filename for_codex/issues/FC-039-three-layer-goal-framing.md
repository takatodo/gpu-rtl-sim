# FC-039: Three-Layer Goal Framing

Status: done
Owner: Codex
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/1
Target file: `README.md`, `docs/roadmap.md`, `docs/status.md`, `docs/tool_surface.md`

## Current Owner Goal

Owner instruction, 2026-06-12:

```text
最大の目標はverilatorにオプションを付けるだけで実行できるようにする。中間ファイルもなしでよい
```

Current concrete endpoint:

```text
verilator --sim-accel sidecar-gpu --sim-accel-states N --sim-accel-steps M \
  -f filelist --top-module top
make -C obj_dir -f V<top>.mk
obj_dir/V<top>
```

The generated `obj_dir/V<top>` executable must invoke the GPU sidecar runtime
directly for a recognized closure. PATH wrappers, proxy env, review manifests,
repo-specific template selection, and generated reports must not be required in
the user path.

Active native-path issue chain:

1. FC-059 / #59: direct executable sidecar shim link smoke.
2. FC-057 / #57: direct `obj_dir/V<top>` sidecar runtime integration.
3. FC-058 / #58: RTLMeter direct-native first seed without proxy lane.
4. FC-056 / #56: honest timing only after direct-native correctness.
5. FC-045 / #19: conservative eligibility/shape policy.

FC-053 / #46 is the active native-path umbrella. The proxy/marker lane
(#49/#51/#53) is frozen and should be closed or superseded from FC-058 once
direct-native RTLMeter correctness is recorded.

## Objective

Make the public goal framing easy to read without blurring long-term direction
into current support.

The repository goal should be presented as a frontend-neutral GPU sidecar for
RTL simulation/verification flows: frontend-owned RTL/build metadata enters the
sidecar boundary, while the sidecar owns GPU artifact build, hybrid execution,
CPU/GPU comparison, and status reporting. Verilator is the first frontend;
CIRCT is a planned second frontend. JSON is debug/review output, not execution
authority or a mandatory runtime ABI.

## Tasks

- Split the goal explanation into three clearly labeled layers:
  Verilator-compatible near-term UX, frontend-neutral sidecar contract, and
  LLM-serving-like RTL workload condition finding.
- Keep `verilator --use-gpu -f filelist.f --top-module top` and
  `gpu-sidecar --frontend verilator/circt ...` clearly marked as future
  directions, not current support.
- Keep the current preview spelling
  `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`
  separate from the long-term shorthand.
- Keep supported claims and non-claims adjacent: scoped template/benchmark
  flows, `coverage_output_equivalence`, debug JSON, RTLMeter command-shape
  preservation, and fail-closed unsupported paths.
- Ensure `config/selection.json`, `docs/status.md`, `docs/roadmap.md`, and
  `README.md` continue to agree on the current priority and current gate.

## Acceptance

- A new reader can distinguish current execution support, preview UX, and
  long-term frontend-neutral goals within the first README/status/roadmap pass.
- The docs do not imply general arbitrary RTL support, CIRCT execution support,
  automatic GPU allocation, production timing, RTLMeter acceleration, mandatory
  JSON ABI, or raw full-state equality.
- The current priority remains tied to
  `review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_gate`
  unless a reviewed selection update changes it.
- No canonical decision is moved into `for_codex/`; this issue only tracks the
  doc cleanup work.

## Validation

```sh
jq -r '.top_level_goal, .current_priority, .current_priority_source_artifact' config/selection.json
python3 -m unittest tests.contract.test_resident_runtime_contract -q
git diff --check
```

Add or update focused documentation contract tests only if the wording becomes
part of a public CLI/help contract.

## Completion

Implemented as public documentation cleanup only:

- Added explicit `Three Layers` framing to `README.md`, `docs/status.md`,
  `docs/roadmap.md`, and `docs/tool_surface.md`.
- Added the current `current_priority` and `current_priority_source_artifact`
  pointer to `README.md`, matching `config/selection.json`,
  `docs/status.md`, and `docs/roadmap.md`.
- Reworded Verilator from broad "first supported frontend" language to
  "current compatibility frontend" in the public goal frame.
- Kept `--use-gpu`, `gpu-sidecar --frontend ...`, CIRCT execution, arbitrary
  RTL/filelist support, automatic allocation, production timing, RTLMeter
  acceleration, mandatory JSON ABI, and raw full-state equality as non-claims.

Validation passed:

```sh
jq -r '.top_level_goal, .current_priority, .current_priority_source_artifact' config/selection.json
python3 -m unittest tests.contract.test_resident_runtime_contract -q
git diff --check
```

## Non-Goals

- No new runtime feature.
- No new Verilator native option claim.
- No CIRCT execution claim.
- No RTLMeter acceleration claim.
- No timing, speedup, or production throughput claim.
