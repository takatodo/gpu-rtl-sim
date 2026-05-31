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

The current native-parser path is still overlay-only. The first repo-owned source-patch descriptor and patch file live under `overlays/verilator/patches/`, pinned to upstream Verilator `v5.048` at peeled commit `d0aa828c217410fffc73d92077b6f4f54830357c`. The patch touches only upstream `src/V3Options.h` and `src/V3Options.cpp`, adding undocumented parse/store/validate-only `--sim-accel`, `--sim-accel-states`, and `--sim-accel-steps` handling. The descriptor validates as JSON, the patch applies and builds `verilator_bin` in the scoped build-only gate, the parser-only smoke has been reviewed for two positive expanded spellings plus six rejection cases, and the rebuilt-binary hardening smoke review now accepts scoped full-token positive integer validation for `--sim-accel-states` and `--sim-accel-steps` on the listed cases. The parser-to-sidecar boundary is now defined as a native-parser adapter payload before the existing sidecar stage plan. This still does not claim broad native parser support, execution, measurement, runtime handoff, or arbitrary RTL/filelist support.

The adapter payload is intentionally smaller than `sidecar_handoff_contract()`. The parser may own `sidecar-gpu`, positive state/step counts, normalized shape, ordinary Verilator args, `-Mdir`, top module, source files, filelists, defines, include dirs, and warning flags. The sidecar plan remains responsible for source closure status, coverage-output selection, host-probe metadata, state file paths, compare report paths, compare labels, and the final `coverage_output_equivalence` policy. `config/scaling_gates/define_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` is definition-only; it adds no adapter implementation, runtime/ABI integration, RTL simulation, timing, automatic allocation, upstream regression success, or upstream landing claim.

`config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_boundary_gate.json` accepts that boundary narrowly and selects a non-executing fixture implementation next. The review clarifies that `coverage_output_equivalence` is only a later sidecar correctness-policy reference at this layer. The parser adapter must not populate resolved state files, generated reports, compare labels, coverage targets, manifest refs, host-probe metadata, runtime handoff, timing, arbitrary source closure, or automatic allocation.

`src/tools/verilator_native_option_parser_sidecar_handoff.py` is the current importable fixture for that adapter layer. It maps parser-stub values to a flat non-executing adapter payload, preserving ordinary Verilator arguments and classified build inputs without expanding filelists or invoking target registry lookup. Its `correctness_policy_ref` field is reference-only and fixed to `coverage_output_equivalence`; unexpected policy refs are rejected. It also rejects inputs that already contain resolved sidecar outputs such as `state_files`, generated reports, compare labels, coverage targets, manifest refs, or host-probe metadata.

`config/scaling_gates/review_verilator_native_option_parser_sidecar_handoff_fixture_implementation_gate.json` accepts only that fixture implementation. The next native-parser gate is a plan-resolution boundary: deciding how this adapter payload can resolve into the existing sidecar stage-plan surface without moving source closure, coverage-output targets, host-probe metadata, state/report paths, compare labels, execution, timing, or automatic allocation into the parser layer.

`config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` defines that boundary. The adapter payload alone is not enough to resolve a sidecar plan because it lacks target, mode, template identity, source gate, coverage manifest, and host-probe metadata. A later plan-resolution layer may use the parser-owned schedule values and preserved Verilator build inputs only after explicit sidecar context supplies target/mode/template or registry information. Source closure, filelist expansion, coverage-output target selection, host-probe metadata, state/report paths, compare labels, final compare policy, `sidecar_handoff_contract`, execution, timing, and automatic allocation remain sidecar-owned.

`config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_boundary_gate.json` accepts that definition and selects a non-executing plan-resolution fixture next. The fixture may accept `adapter_payload + explicit sidecar context` and reject payload-only resolution, but it still must not run RTL simulation, build GPU artifacts, generate compare evidence, measure timing, change runtime/ABI, or claim arbitrary RTL/filelist support.

`config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_fixture_gate.json` records the first importable plan-resolution fixture in `src/tools/verilator_native_option_parser_sidecar_plan_resolution.py`. It requires reviewed adapter payload plus explicit target, mode, template or registry entry, and source gate/manifest reference, validates the adapter shape and reviewed registry template, and only then calls existing `sidecar_stage_plan` as a non-executing authority. Parser `source_files`, `filelists`, and ordinary Verilator args remain preserved inputs; the fixture does not infer source closure, synthesize a Verilator command, produce `sidecar_handoff_contract`, run compare, measure timing, build GPU artifacts, or change runtime/ABI.

`config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_fixture_implementation_gate.json` accepts only that explicit-context, non-executing template-plan fixture. Its accepted weakness is status/readiness: an outer fixture status of `planned` can hide `sidecar_stage_plan` results such as `unsupported_for_stage_plan` or `planned_not_ready_for_verilator_option_shim`. `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json` therefore defines the future outer status as direct Verilator option readiness: `ready_for_verilator_option_shim`, `not_ready_for_verilator_option_shim`, or `unsupported_for_stage_plan`, while preserving nested `stage_plan_status`. `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json` accepts that definition for in-place helper hardening only, `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_gate.json` records that helper implementation, and `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_status_hardening_implementation_gate.json` accepts only the readiness-classified non-executing result. `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json` defines the ready-only metadata boundary for a later `sidecar_handoff_contract`, `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_boundary_gate.json` accepts it only for fixture implementation, `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_gate.json` records the thin wrapper plus support-module implementation, `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_fixture_implementation_gate.json` accepts it only after the explicit `efficiency_estimate_invoked` guard, `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json` defines only non-executing command argv, estimate-command, efficiency-estimate, and operator-plan metadata from accepted handoff-contract metadata, `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_boundary_gate.json` accepts that boundary for importable fixture implementation, `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_gate.json` records the metadata-only operator-plan fixture, and `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_implementation_gate.json` accepts that fixture only as metadata. The helpers produce metadata only for ready plan-resolution/handoff outputs, return structured closed results for not-ready/unsupported outputs, and still leave command execution, operator-plan execution, RTL simulation, measured timing evidence, runtime/ABI, arbitrary RTL/filelist, and automatic allocation deferred.

`config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json` defines that boundary for review. It covers bool rejection for handoff-contract, stage-plan, and parser-schedule integer fields, scoped malformed Mapping rejection before command/operator-plan authorities, and the rule that `efficiency_estimate` is planning metadata only even when existing reports contribute values. `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json` accepts the boundary for in-place helper implementation and tightens `stage_plan.phases` / `stage_plan.limit` rejection to happen before any authority call. `config/scaling_gates/implement_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_gate.json` records the in-place helper implementation and counting-stub tests for authority ordering. `config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_fixture_hardening_implementation_gate.json` accepts that strict metadata-only implementation and allows only a definition-only execution-boundary gate next. `config/scaling_gates/define_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate.json` then defines that a later run gate must validate ready operator-plan metadata, recover or regenerate a reviewed sidecar stage plan, and execute only reviewed sidecar build/run/compare stages. It still adds no public CLI, command execution, operator-plan execution, RTL simulation, compare execution, timing, runtime/ABI, arbitrary RTL/filelist support, automatic allocation, or complete adversarial Mapping validation.

`config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_execution_boundary_gate.json` accepts that definition and selects `run_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_gate` next. The reviewed weak point is that `handoff_contract` and `command_argv` metadata can look executable, so the next run must treat them only as preview/build inputs until a reviewed or regenerated sidecar stage plan authorizes the scoped build/run/compare sequence. This review still adds no execution, compare result, timing, speedup, native Verilator support, arbitrary filelist support, automatic allocation, or runtime/ABI claim.

`config/scaling_gates/run_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_gate.json` records the first scoped execution at this boundary. It ran `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1`, which uses the existing template runner rather than executing parser `command_argv` as a native Verilator option. The seven stages completed and `reports/pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json` passed `coverage_output_equivalence` with mismatch count `0` over `64` state pairs. Generated reports and artifacts remain evidence only; the run does not claim timing, speedup, native Verilator option support, arbitrary filelists, automatic allocation, runtime/ABI change, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_sidecar_plan_resolution_handoff_contract_operator_plan_sidecar_execution_run_gate.json` accepts that run only as scoped `pulp_ita_mha 64x1` sidecar build/run/compare evidence. The review advances to `define_verilator_native_option_parser_direct_command_path_boundary_gate`, because the remaining usability gap is the real native Verilator command path. The accepted run still does not prove native Verilator option support, direct `command_argv` runtime authority, arbitrary filelists, automatic allocation, timing, speedup, runtime/ABI change, or raw full-state equality.

`config/scaling_gates/define_verilator_native_option_parser_direct_command_path_boundary_gate.json` defines that command path without executing it. The native minimum remains the expanded spelling, `--sim-accel sidecar-gpu --sim-accel-states <N> --sim-accel-steps <S>`, while `--sim-accel-shape <NxS>` stays wrapper compatibility. Parser-owned values must preserve ordinary Verilator build inputs and then materialize or reference a structured sidecar stage plan before any execution authority. Source closure, host-probe metadata, state/report paths, compare labels, coverage-output target selection, stage order, and generated evidence policy remain sidecar-owned. The definition advances to review and still adds no native option support, direct command execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_direct_command_path_boundary_gate.json` accepts that boundary only as non-executing fixture-contract preparation. The accepted minimum is still the expanded spelling plus preserved ordinary Verilator build inputs, and the parser/sidecar authority split stays intact. The next task is defining the direct-command-path fixture contract before implementation, because a direct-looking command can otherwise be mistaken for working native Verilator support. This review still adds no native option support, direct command execution, timing, arbitrary filelist support, automatic allocation, runtime/ABI change, or raw full-state equality.

`config/scaling_gates/define_verilator_native_option_parser_direct_command_path_fixture_gate.json` defines that fixture contract without implementing a helper. It pins an accepted expanded `sidecar-gpu 64x1` case, explicit sidecar context, preserved ordinary Verilator build inputs, a reference-only `sidecar_plan_boundary`, and fail-closed cases for missing or mixed shape inputs, compact-only shape spelling, missing sidecar context, and prepopulated sidecar-owned fields.

`config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_gate.json` accepts that contract and advances to implementing an importable non-executing helper. The accepted weak point is that direct-looking argv and `sidecar_plan_boundary` metadata can be over-read as implemented native support or execution authority, so the helper must keep Verilator execution, sidecar stages, compare, timing, allocation, runtime/ABI changes, arbitrary filelists, and raw full-state equality out of scope.

`config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_gate.json` adds `src/tools/verilator_native_option_parser_direct_command_path_fixture.py` as that importable non-executing helper. It accepts only the reviewed expanded native minimum with explicit sidecar context, preserves ordinary Verilator build inputs, returns reference-only `sidecar_plan_boundary` metadata, and rejects sidecar-owned fields if they appear in the parser payload. The next task is reviewing the helper implementation; this still adds no native Verilator option support, direct command execution, sidecar stage materialization, compare result, timing, allocation, runtime/ABI change, arbitrary filelists, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_implementation_gate.json` accepts that helper only as non-executing reference-boundary metadata. The review deliberately records a hardening gap: hand-built parser payloads must be required to include the reviewed identity and build-input fields before any sidecar boundary metadata is returned. The next task is defining that payload-validation hardening, still before sidecar stage materialization, direct command execution, timing, allocation, runtime/ABI change, arbitrary filelists, or raw full-state equality.

`config/scaling_gates/define_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json` defines that hardening boundary. A hand-built parser payload must match the parser-stub handoff keyset, including `schema_version`, `surface`, schedule fields, preserved Verilator build inputs, `source_boundary_status`, `state_and_report_naming_rules`, `correctness_policy`, and `non_claims`, before the direct fixture can return reference-only boundary metadata. The next task is reviewing this definition; it still adds no helper change, sidecar stage materialization, direct command execution, timing, allocation, runtime/ABI change, arbitrary filelists, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json` accepts the definition and advances to implementation. The implementation must harden hand-built parser payloads before returning boundary metadata, but it still must not add a public CLI, sidecar stage materialization, direct command execution, timing, allocation, runtime/ABI change, arbitrary filelists, or raw full-state equality.

`config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_gate.json` implements that hardening with a split helper, `src/tools/verilator_native_option_parser_direct_command_payload_validation.py`. The direct fixture now rejects malformed hand-built parser payloads before boundary metadata is returned and preserves the non-executing fixture surface. The next task is implementation review; it still adds no public CLI, sidecar stage materialization, direct command execution, timing, allocation, runtime/ABI change, arbitrary filelists, or raw full-state equality.

`config/scaling_gates/review_verilator_native_option_parser_direct_command_path_fixture_payload_validation_hardening_implementation_gate.json` accepts that implementation only as stricter non-executing parser-payload validation. The next task is defining the direct command-path sidecar stage-plan materialization boundary: whether the validated parser payload plus explicit sidecar context may call or reference the reviewed `sidecar_stage_plan` surface before execution. This still adds no public CLI, native option support, direct command execution, sidecar stage execution, timing, allocation, runtime/ABI change, arbitrary filelists, or raw full-state equality.

`config/scaling_gates/define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate.json` defines that boundary, and `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_boundary_gate.json` accepts only the non-executing route through the reviewed parser-to-sidecar adapter payload and existing plan-resolution helper. `config/scaling_gates/implement_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_gate.json` implements that bridge in `src/tools/verilator_native_option_parser_direct_stage_plan_materialization.py`, and `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_materialization_fixture_implementation_gate.json` accepts it as metadata-only stage-plan materialization. `config/scaling_gates/define_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate.json` then defines the future execution boundary from ready materialization metadata to reviewed sidecar build/run/compare stages, and `config/scaling_gates/review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate.json` accepts that boundary only for a scoped run gate. This still adds no public CLI, native option support, direct command execution, sidecar stage execution by the review gate, compare execution by the review gate, timing, allocation, runtime/ABI change, arbitrary filelists, or raw full-state equality.

`config/scaling_gates/run_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_gate.json` records that scoped run for `pulp_ita_mha 64x1` through `python3 src/tools/run_hybrid_template.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1` after validating ready direct materialization metadata, parser schedule constraints, and the reviewed seven-stage order. The generated compare evidence passes `coverage_output_equivalence` with mismatch count `0` across `64` state pairs, while raw full-state match remains false. The next task is reviewing this run before claiming anything broader than scoped sidecar build/run/compare evidence.

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
