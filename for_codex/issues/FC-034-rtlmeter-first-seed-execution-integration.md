# FC-034: RTLMeter First Seed Execution Integration

Status: review
Owner: Codex
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/8
Target file: `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*`

## Objective

Move from FC-030's non-executing compare policy to a real CPU vs GPU-sidecar
comparison run for the selected first seed `Example:kind:hello`, producing
regenerable evidence under `reports/` without claiming speedup and without
breaking RTLMeter's native UX.

Depends on FC-025 (command capture), FC-026 (PATH wrapper), FC-027 (compileArgs
pass-through), FC-028 (sidecar contract mapping), FC-029 (seed = `Example:kind:hello`),
and FC-030 (compare policy). This issue is the first one allowed to actually
execute; all prior RTLMeter issues are non-executing by design.

## Tasks

- Run RTLMeter's normal CPU execute for `Example:kind:hello` as the CPU reference, or document the exact RTLMeter command used.
- Run the GPU sidecar candidate launched from the RTLMeter-preserving Verilator argv (`--compileArgs "--use-gpu"` or a PATH-selected `verilator` wrapper).
- Compare per FC-030's policy: normalized stdout transcript and reported RTLMeter cycle count must match. Keep RTLMeter execute metrics/postHook intact; do not conflate RTLMeter timing with sidecar timing.
- Write the regenerable compare report to `reports/rtlmeter_example_kind_hello_cpu_gpu_compare.json` only. Reports are not source of truth.
- Gate execution behind explicit opt-in (env var or flag). Fail closed when real Verilator, the GPU sidecar build, or the wrapper prerequisites are missing; never silently fall back to a CPU run and report it as GPU.
- If the environment cannot execute (no real Verilator or no GPU sidecar), record an honest "cannot execute here" first state and mark the issue `blocked` with the missing prerequisite rather than faking a result.

## Acceptance

- A documented, regenerable command runs the CPU/GPU compare for `Example:kind:hello` and writes a report under `reports/`.
- The compare uses FC-030's declared observable outputs; RTLMeter metrics/postHook are preserved and not overwritten.
- No speedup or acceleration claim is made; timing stays diagnostic-only until separately measured.
- Fail-closed behavior when real Verilator or the GPU sidecar is unavailable; no CPU-as-GPU misreport.
- `config/selection.json` records only the first-seed result and non-claims; `config/targets.json` is not broadened to other RTLMeter designs.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_cpu_gpu_compare_integration -q
python3 -m unittest tests.contract.test_rtlmeter_verilator_wrapper_runtime -q
python3 -m unittest tests.contract.test_rtlmeter_stdout_cycles_runner_contract -q
python3 -m unittest tests.contract.test_rtlmeter_sidecar_authority_registry -q
python3 -m unittest discover -s tests/contract -p 'test_rtlmeter*.py' -q
```

Add or extend an executing-path contract test that is skipped or fail-closed when
real Verilator or the GPU sidecar is unavailable, so the suite stays green in a
non-GPU environment.

## Current State

- Latest local real opt-in first-seed evidence reaches `status=passed` and
  `comparison.status=passed` for `Example:kind:hello`.
- The runner observes current-run stdout/cycles outputs and a valid wrapper
  proxy marker with `execution_authority=true` and
  `sidecar_execution_invoked=true`.
- This remains first-seed handoff evidence only:
  `gpu_execution_claimed=false`, `speedup_claimed=false`, `runtime_abi=false`,
  and CPU-as-GPU fallback is forbidden.
- Current review point: decide whether the #49 reviewed first-seed proxy target
  is sufficient closure evidence, or whether #49 requires a stronger
  non-generated sidecar runtime target before closing.

- Added `src/tools/rtlmeter_cpu_gpu_compare_integration.py` as the first opt-in executing helper.
- Added `src/tools/rtlmeter_verilator_wrapper_runtime.py` as the explicit execution-authority boundary for a PATH-selected wrapper named `verilator`; the prior path-wrapper helper remains inspect-only.
- Added `tests/contract/test_rtlmeter_cpu_gpu_compare_integration.py` for non-executing default behavior, fail-closed prerequisite handling, observable compare logic, report schema safety, and CLI JSON output.
- Created the local ignored RTLMeter venv and verified RTLMeter's normal CPU reference command for `Example:kind:hello`.
- CPU reference evidence: `Example:kind:hello` completes with RTLMeter cycle count `1000000` and the expected `Hello World!` transcript under `artifacts/rtlmeter_example_kind_hello_cpu_gpu_compare/cpu/`.
- The compare integration now prepends `third_party/rtlmeter` to `PYTHONPATH` for repo-root launches and can materialize an ignored fail-closed wrapper under `artifacts/.../wrapper/verilator`.
- Ran `python3 src/tools/rtlmeter_cpu_gpu_compare_integration.py --execute --write-report`; the generated report status is `gpu_execution_failed` after a successful CPU reference run.
- The GPU Verilate log records wrapper runtime status `use_gpu_requires_explicit_sidecar_schedule`, with `cpu_as_gpu_fallback: false` and `sidecar_execution_invoked: false`.
- Updated the compare helper's default GPU candidate from `--use-gpu` alone to the expanded native-minimum schedule `--sim-accel sidecar-gpu --sim-accel-states 64 --sim-accel-steps 1`.
- GPU failures now copy the sanitized Verilate diagnostic log into the generated compare report so the fail-closed wrapper status is visible without treating the report as source of truth.
- Added metadata-only RTLMeter sidecar handoff diagnostics for expanded schedules. They preserve schedule/parser inputs and list missing sidecar-owned context, but still do not execute a sidecar launcher.
- The handoff now accepts optional sidecar context and can mark complete context as `sidecar_context_metadata_ready` while keeping `sidecar_context_ready`, `sidecar_launcher_invoked`, `sidecar_execution_invoked`, and `coverage_output_compare_reached` false.
- The compare helper now builds an RTLMeter sidecar context candidate from the selected seed and passes it to the wrapper through `RTLMETER_SIDECAR_CONTEXT_JSON`. The candidate fills known metadata such as target, host-probe candidate, coverage-output policy, path rules, and compare labels, but it deliberately keeps template/source-closure unresolved.
- Added a non-executing RTLMeter launcher invocation materializer. It can build `run_hybrid_template.py` argv only from metadata-ready handoff plus a reviewed template path, and otherwise reports the missing invocation context.
- The context candidate now separates `compile_source_closure` from hybrid execution `source_closure`: `Example:kind:hello` compile inputs are known from the RTLMeter descriptor, but hybrid execution closure remains blocked by the host-probe/template contract mismatch.
- The generated wrapper fail-closed report now includes `launcher_invocation` for expanded RTLMeter sidecar schedules, so the wrapper boundary exposes why no sidecar launcher argv was materialized.
- Re-ran `python3 src/tools/rtlmeter_cpu_gpu_compare_integration.py --execute --write-report` after refreshing the generated GPU workRoot. The generated report still has status `gpu_execution_failed`, but its sanitized Verilate diagnostic log now includes `launcher_invocation.missing_invocation_context`.
- Strengthened wrapper-runtime tests so blocked launcher diagnostics must keep `launcher_command_argv: null`, `launcher_command_role: not_materialized`, `execution_performed: false`, and `measurement_performed: false`.
- Tightened the RTLMeter source-closure contract: `source_closure.status=complete` is no longer enough for handoff readiness unless it also carries `authority: reviewed_hybrid_execution_source_closure`.
- The RTLMeter context candidate now records that required authority on its unresolved `source_closure`, preserving the distinction between descriptor compile inputs and a reviewed hybrid execution closure.
- Tightened launcher invocation materialization so the referenced template file must also carry reviewed hybrid execution source-closure authority. A context-only forged authority is no longer enough to produce `launcher_command_argv`.
- Missing template authority is reported as `template_source_closure.status` or `template_source_closure.authority`, separate from `sidecar_context.source_closure`.
- Split RTLMeter authority registries from runtime launch templates. A metadata-only registry may carry `schema_role: rtlmeter_sidecar_authority`, `runtime_launchable: false`, and reviewed source-closure authority, but it cannot materialize `run_hybrid_template.py` argv by itself.
- Runtime argv materialization now requires a separate `config/slice_launch_templates/*.json` path with `template_execution_role: runnable_hybrid_template`; missing or `metadata_only` roles remain blocked as `template_execution_role`.
- Added `config/rtlmeter_sidecar_authorities/rtlmeter_example_kind_hello.json` as the first metadata-only RTLMeter authority registry. It records the known RTLMeter compile inputs and the selected stdout/cycles compare policy, while keeping hybrid execution `source_closure` incomplete and `runtime_launch_template` null.
- Added a registry contract test proving that the tracked authority registry does not materialize `run_hybrid_template.py` argv even if a handoff context is otherwise metadata-ready.
- Added `src/tools/rtlmeter_stdout_cycles_plan.py` as a shared importable helper rather than adding a new public CLI. The plan is non-executing, keeps CPU reference owner as RTLMeter, GPU candidate owner as sidecar, limits observables to `normalized_stdout` and `rtlmeter_cycles`, and marks fallback policy as forbidden.
- The default compare report now includes that stdout/cycles plan, and the wrapper runtime also includes it in expanded-schedule fail-closed diagnostics. This makes the next execution boundary visible without claiming execution, measurement, timing, speedup, or `run_hybrid_template.py` compatibility.
- Added `src/tools/rtlmeter_stdout_cycles_runner_contract.py` as a non-executing contract validator. It validates the stdout/cycles plan shape, requires handoff metadata and authority-registry context, names the missing RTLMeter-specific sidecar runner implementation, rejects `run_hybrid_template.py` as stdout/cycles evidence, and keeps `sidecar_runner_invoked`, `sidecar_execution_invoked`, `execution_performed`, and `measurement_performed` false.
- Added `src/tools/rtlmeter_stdout_cycles_runner_implementation.py` as the next metadata-only boundary. It records that the only acceptable next step is a reviewed RTLMeter stdout/cycles adapter; it still does not materialize `runner_command_argv`, execute RTLMeter, provide runtime ABI authority, or call `run_hybrid_template.py`.
- Added `src/tools/rtlmeter_stdout_cycles_runner_adapter.py` as non-executing adapter entrypoint metadata. It names the required blocked runner-contract state, wrapper environment, stdout log, cycle-count file, and stdout/cycles acceptance policy without invoking RTLMeter or materializing a command.
- Extended the adapter helper with a separate non-executing implementation boundary. It checks the declared source file `src/tools/rtlmeter_stdout_cycles_sidecar_runner.py`, keeps execution disabled, and records that source presence alone does not authorize execution, measurement, runtime ABI, or CPU-as-GPU fallback.
- Added `src/tools/rtlmeter_stdout_cycles_sidecar_runner.py` as the scoped runner source boundary. It can emit a non-executing JSON plan for the future RTLMeter stdout/cycles sidecar command, and its `--execute` path is guarded by wrapper, command, stale-output, and stdout/cycle-output checks.
- The adapter implementation boundary can now materialize `python3 src/tools/rtlmeter_stdout_cycles_sidecar_runner.py ... -- <rtlmeter command>` only when the declared source exists and the runner contract's sole missing context is `rtlmeter_stdout_cycles_runner_implementation`; the materialized argv is still not invoked.
- The runner now has a scoped execution boundary: `--execute` may invoke only a RTLMeter command carrying `--sim-accel sidecar-gpu`, only when `RTLMETER_SIDECAR_VERILATOR_WRAPPER` points to an executable named `verilator`, and never through `run_hybrid_template.py`.
- The runner clears stale stdout/cycle outputs before invoking the candidate command and reports `rtlmeter_stdout_cycles_sidecar_runner_observables_ready` only after `_execute/stdout.log` and integer `_rtlmeter_cycles.txt` exist from that run. This is still not a speedup or GPU-correctness claim by itself.
- The compare integration now routes the GPU candidate through the stdout/cycles runner boundary and can compare CPU reference stdout/cycles against runner-produced sidecar observables in contract tests.
- The compare integration deletes generated CPU/GPU RTLMeter work roots before a fresh execute run, so stale RTLMeter "Failed on earlier run" state cannot be mistaken for the current blocker.
- The runner and compare report now sanitize local absolute paths, including JSON-quoted paths embedded in wrapper diagnostic logs, before writing generated `reports/` evidence.
- The RTLMeter handoff now records Verilator's default `obj_dir` when `-Mdir` is omitted by the frontend command. The latest fresh run therefore no longer blocks on `mdir`; the wrapper diagnostic reports `parser_payload_mdir: "obj_dir"` and `parser_payload_mdir_source: "verilator_default_obj_dir"`.
- Re-ran `python3 src/tools/rtlmeter_cpu_gpu_compare_integration.py --execute --write-report`; the generated report still has status `gpu_execution_failed`, but it contains no `/home/` or `/tmp/` paths, `stdout_cycles_sidecar_runner.status` is `rtlmeter_stdout_cycles_sidecar_runner_execution_failed`, `sidecar_candidate_command_executed: true`, `observables_ready: false`, `gpu_execution_claimed: false`, and `cpu_as_gpu_fallback: false`.
- The generated compare report remains generated evidence only; no CPU command is reported as GPU execution.
- Added `src/tools/rtlmeter_source_closure_authority.py` as the shared strict source-closure gate. A reviewed closure now requires target/mode/case binding, source/include/filelist lists, declared stdout/cycles observables, runner strategy, reviewed host-probe contract status, `cpu_as_gpu_fallback_allowed: false`, and review evidence; a thin `status=complete` plus `authority` payload is rejected.
- The wrapper runtime now loads `config/rtlmeter_sidecar_authorities/*.json` from `template_or_target_registry_entry` for diagnostics and passes it into the stdout/cycles runner contract. Loading the registry does not authorize execution; it only turns a generic missing `authority_registry` blocker into explicit `authority_registry.source_closure.*` blockers.
- Re-ran `python3 src/tools/rtlmeter_cpu_gpu_compare_integration.py --execute --write-report` after the strict gate. The generated report still has status `gpu_execution_failed`, `cpu_as_gpu_fallback: false`, `sidecar_execution_invoked: false`, and no `/home/` or `/tmp/` paths. The wrapper diagnostic now lists missing `sidecar_context.source_closure.*` and `authority_registry.source_closure.*` reviewed-closure fields.
- Incorporated the multi-agent review finding that source-closure authority must be target-bound, not just present. The runner contract now blocks when the authority registry target or its reviewed source-closure target does not match the requested sidecar context target.
- Wrapper fail-closed diagnostics now report `execution_authority: false`; they are diagnostic boundaries, not permission to run sidecar execution.

## Blocker

- No current correctness blocker remains for the first-seed stdout/cycles
  compare itself; it has passed in the local real opt-in path.
- Remaining blocker is closure policy: #49 should close only if marker-gated
  `Vsim__main.cpp` proxy handoff plus current-run stdout/cycles comparison is
  accepted as the intended first-seed handoff slice.
- If #49 requires a stronger non-generated sidecar runtime target, keep #49
  open and do not promote this evidence into RTLMeter acceleration, GPU runtime,
  timing, speedup, second-seed, arbitrary filelist, or production claims.

## Non-Goals

- No broad RTLMeter acceleration claim.
- No automatic GPU allocation.
- No promotion of debug JSON into the runtime ABI.
- No requirement that RTLMeter users select repo-specific launch templates.
