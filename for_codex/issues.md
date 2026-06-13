# Agent Issue Index

This is the Codex-facing issue index. Each issue has its own file under `for_codex/issues/`, so agents can claim and edit one issue without touching a shared table.

Status values: `open`, `claimed`, `blocked`, `review`, `done`.

## GitHub Issue Coordination

Use GitHub Issues through `gh` for live coordination when the repository has an
accessible remote issue tracker. The local FC files are useful for design
context and file-scoped acceptance criteria, but they should not become a
private task queue that other agents cannot see.

Recommended flow:

```sh
gh issue list
gh issue create --title "FC-XXX: <short title>" --body-file for_codex/issues/FC-XXX-<slug>.md
gh issue comment <number> --body "<validation, blocker, or handoff note>"
```

Rules:

- Prefer one GitHub issue per actionable FC issue.
- Keep the GitHub title prefixed with `FC-XXX` when mirroring an FC file.
- Add the matching GitHub issue URL or number to the FC file when useful, but do
  not make GitHub-only metadata the source of truth for design decisions.
- Use `gh issue edit` or `gh issue comment` to record status transitions instead
  of relying only on local unpushed markdown edits.
- Close issues only after acceptance criteria and validation are recorded, or
  after a replacement issue is linked.
- Never claim success from a blocked environment; record the blocker explicitly.

Current GitHub mirror:

| Local FC | GitHub Issue | Notes |
|---|---|---|
| FC-034 | https://github.com/takatodo/gpu-rtl-sim/issues/8 | First RTLMeter executing correctness issue; local first-seed stdout/cycles compare now passes with marker-backed execution authority, pending #49 closure review. |
| FC-035 | https://github.com/takatodo/gpu-rtl-sim/issues/7 | Clean sim GPU runtime preflight; classify blocked CUDA driver access without reporting success. |
| FC-036 | https://github.com/takatodo/gpu-rtl-sim/issues/6 | Move generated helper binaries out of `src/`; clean-sim hardening, not RTLMeter execution. |
| FC-037 | https://github.com/takatodo/gpu-rtl-sim/issues/2 | Dedicated RTLMeter timing issue. Depends on FC-034 correctness compare and pending #49 closure sufficiency review. |
| FC-038 | https://github.com/takatodo/gpu-rtl-sim/issues/3 | Dedicated clean-sim operator log hygiene issue. |
| FC-039 | https://github.com/takatodo/gpu-rtl-sim/issues/1 | Existing public goal-framing issue; do not create a duplicate. |
| FC-040 | https://github.com/takatodo/gpu-rtl-sim/issues/4 | Second RTLMeter seed broadening; bounded to one seed and gated on FC-034 evidence, FC-037 timing, and pending #49 closure sufficiency review. |
| FC-041 | https://github.com/takatodo/gpu-rtl-sim/issues/5 | Installable PATH `verilator` wrapper; delegates for non-GPU, fails closed for unsupported GPU argv. |
| FC-042 | https://github.com/takatodo/gpu-rtl-sim/issues/9 | Closed/completed after #35; first real scoped `verilator --use-gpu` path remains one reviewed wrapper route, not arbitrary RTL support. |
| FC-043 | https://github.com/takatodo/gpu-rtl-sim/issues/10 | Frontend-neutral sidecar contract and CIRCT placeholder boundary; not CIRCT execution. |
| FC-044 | https://github.com/takatodo/gpu-rtl-sim/issues/11 | External-user readiness audit; remove or demote misleading surface area. |
| FC-045 | https://github.com/takatodo/gpu-rtl-sim/issues/19 | GPU sidecar eligibility and shape policy; scoped recommendation, not automatic optimal allocation. |
| FC-046 | https://github.com/takatodo/gpu-rtl-sim/issues/20 | LLVM GPU optimization pass roadmap; umbrella only, not implementation evidence. |
| FC-047 | https://github.com/takatodo/gpu-rtl-sim/issues/21 | Emit GPU ABI metadata in generated IR. |
| FC-048 | https://github.com/takatodo/gpu-rtl-sim/issues/22 | Canonicalize safe constant-offset state accesses. |
| FC-049 | https://github.com/takatodo/gpu-rtl-sim/issues/24 | Conservative NVPTX inline/noinline policy. |
| FC-050 | https://github.com/takatodo/gpu-rtl-sim/issues/25 | Trigger guard factoring for proven-safe adjacent wrappers only. |
| FC-051 | https://github.com/takatodo/gpu-rtl-sim/issues/23 | Opt-in resident step kernel; separate correctness gate required. |
| FC-052 | https://github.com/takatodo/gpu-rtl-sim/issues/26 | Hot-field SoA exploration; ABI-changing and last in order. |
| FC-054 | https://github.com/takatodo/gpu-rtl-sim/issues/54 | First native-path slice under FC-053 / #46. M2 (recognition) + M3 (verilator option → make → build_vl_gpu → real SM89 CUBIN with GPU kernels) proven end-to-end on `pulp_ita_mha`. M4 (obj_dir binary alone runs GPU) and M5 (coverage equivalence) NOT done: the `make` exe is the plain CPU `--main` binary, and the native CUBIN (storage 5760) hits CUDA 700 vs the working 7-stage template CUBIN (storage 6144) because the native path omits host-probe/state-init stages. No GPU-execution or speedup claim. |

FC-001 through FC-033 remain local planning issues unless they are promoted to
GitHub. When promoting more issues, check existing GitHub titles first and keep
duplicates linked instead of creating parallel trackers.

## GitHub Roadmap Task Overlay

These GitHub-only `T*` issues organize the current open work around the FC
issues. They are coordination tasks, not a new source of truth for canonical
project state.

| GitHub Issue | Role | Dependency / Scope |
|---|---|---|
| https://github.com/takatodo/gpu-rtl-sim/issues/12 | T0: document current algorithm readiness and claim boundary | First docs task; gates T1/T2 and later docs wording. |
| https://github.com/takatodo/gpu-rtl-sim/issues/13 | T1: shorten operator-facing quickstart | Gated on T0. |
| https://github.com/takatodo/gpu-rtl-sim/issues/14 | T2: harden public-pack reproducibility boundaries | Gated on T0/T1. |
| https://github.com/takatodo/gpu-rtl-sim/issues/15 | T3: advance Verilator native option handoff | Gated on T0/T1/T2; keep sidecar-owned metadata out of parser-owned fields. |
| https://github.com/takatodo/gpu-rtl-sim/issues/16 | T4: repeat-median evidence for policy-selected workloads | Scoped sidecar measurement evidence only; not production throughput. |
| https://github.com/takatodo/gpu-rtl-sim/issues/17 | T5: expand filelist-derived target boundary | Gated on T0/T3; not arbitrary filelist inference. |
| https://github.com/takatodo/gpu-rtl-sim/issues/18 | T6: prepare RTLMeter sidecar handoff | Gated on T0/T1/T3; do not claim acceleration from compile-only evidence. |
| https://github.com/takatodo/gpu-rtl-sim/issues/41 | T11: run RTLMeter first-seed stdout/cycles compare | Current-run stdout/cycles evidence exists for `Example:kind:hello`; compare only normalized stdout and RTLMeter cycle count. |
| https://github.com/takatodo/gpu-rtl-sim/issues/44 | T14: implement RTLMeter sidecar Verilate execution for stdout/cycles | Closed; the blocker narrowed past sidecar Verilate execution to the #49 Vsim proxy/marker boundary. |
| https://github.com/takatodo/gpu-rtl-sim/issues/49 | T18: implement RTLMeter Vsim sidecar proxy marker and runtime handoff | Marker/proxy implementation is committed and pushed on `simple-core-surface-cleanup`; #44/#45 closed on that evidence; closure is gated on review sufficiency of the marker-backed opt-in pass. |
| https://github.com/takatodo/gpu-rtl-sim/issues/50 | T19: clear stale RTLMeter stdout/cycles observables before sidecar runner execution | Safety layer after #44 base; prevents stale `_execute/stdout.log` and `_rtlmeter_cycles.txt` from becoming current evidence. |
| https://github.com/takatodo/gpu-rtl-sim/issues/51 | T20: record marker-backed first-seed opt-in pass evidence | Frozen per the owner native-path goal. End-to-end trial done (forgeability shown); evidence recording not pursued. Closes with #49 (interim-complete or superseded). |
| https://github.com/takatodo/gpu-rtl-sim/issues/52 | T21: harden RTLMeter sidecar proxy-target review | Descoped: allow-list/manifest hardening frozen. Remaining scope is naming separation only (demote `execution_authority`/`sidecar_execution_invoked` to handoff-observed wording). |
| https://github.com/takatodo/gpu-rtl-sim/issues/53 | T22: decide a tracked evidence sink for RTLMeter compare | Frozen per the owner native-path goal; native-path correctness evidence is owned by the #46 milestone-5 gate. Closes as superseded when the native path runs RTLMeter. |

Current GitHub lane map:

- Parent/goal framing: FC-039 / #1. Treat as umbrella coordination, not a
  standalone implementation proof.
- Docs/readiness: #12 -> #13 -> #14 -> FC-044 / #11.
- Verilator/sidecar: FC-042 / #9 is completed; remaining architecture work is FC-043 / #10, while current external readiness work is FC-044 / #11.
- Algorithm policy: #16 -> FC-045 / #19, using repeat-median evidence to
  recommend scoped shapes without claiming automatic optimal allocation.
- LLVM optimization pass lane: FC-046 / #20 umbrella, then FC-047 / #21 ->
  FC-048 / #22 -> FC-049 / #24 -> FC-050 / #25 -> FC-051 / #23 ->
  FC-052 / #26. Keep correctness patches separate from optimization passes.
- Owner goal (2026-06-12, recorded on FC-039 / #1): the maximal goal is that
  `verilator` with the sidecar options alone builds an `obj_dir/Vsim` that
  executes on GPU, with no wrapper, proxy env, review manifest, repo-specific
  JSON selection, or intermediate files in the user path. FC-053 / #46 is the
  native-path umbrella (milestones recorded there); first target is
  `pulp_ita_mha 64x1`-class, recognized-closure-only, fail-closed.
- RTLMeter proxy interim lane (#49 / #51 / #52 / #53) is frozen per that goal.
  The #51 end-to-end trial showed the proxy review gate is self-attested and a
  CPU-delegate proxy obtains `execution_authority=true`; proxy-lane outputs are
  therefore not GPU-claim evidence. Only the #52 naming separation (demote
  `execution_authority` / `sidecar_execution_invoked` to handoff-observed
  wording) remains active; the rest closes as superseded once the native path
  runs RTLMeter directly. FC-037 / #2 timing and FC-040 / #4 second seed are
  re-evaluated after the #46 milestone-5 correctness gate.
- Measurement evidence: #16, scoped only and separate from production timing
  claims.

## Current PR Queue

Agent coordination snapshot. This section is not source of truth for project
state; prefer live GitHub issues plus `config/selection.json`, `docs/status.md`,
`docs/roadmap.md`, and `README.md` for the current external-reader position.

Treat local staged and unstaged work as pre-PR material until it is split,
pushed, and linked to the issues below.

0. PR-0: External user readiness cleanup.
   - Primary issues: FC-044 / #11.
   - Scope: align public docs, tool-surface wording, for_codex issue state, and
     GitHub dependency notes after #9/#35 completion.
   - Completion condition: an external reader can tell that the scoped
     `--use-gpu` wrapper path is complete, #11 is current, and broad Verilator,
     arbitrary filelist, automatic allocation, timing/speedup, CIRCT, JSON ABI,
     and production-readiness claims remain non-claims.

1. Later technical split: Verilator process-to-launcher CLI prerequisite.
   - Primary issues: #15 and FC-042 / #9.
   - Scope: land the non-executing process-to-launcher CLI fixture and its
     gate chain before any observable-ordering helper depends on it.
   - Include exactly this source/test pair:
     `src/tools/verilator_native_option_parser_process_to_launcher_cli_fixture.py`
     and
     `tests/contract/test_verilator_native_option_parser_process_to_launcher_cli_fixture.py`.
   - Include only these new process-to-launcher gate records:
     `records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_direct_launch_handoff_sidecar_launcher_invocation_run_gate.json`,
     `records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate.json`,
     `records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_boundary_gate.json`,
     `records/scaling_gates/implement_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_gate.json`,
     `records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_fixture_implementation_gate.json`,
     `records/scaling_gates/define_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate.json`,
     `records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_boundary_gate.json`,
     `records/scaling_gates/run_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_gate.json`,
     and
     `records/scaling_gates/review_verilator_native_option_parser_direct_command_path_native_invocation_process_to_launcher_cli_execution_run_gate.json`.
   - Also include the PR-0 source-of-truth and contract expectation updates:
     `config/selection.json`, `config/selection_extensions.json`,
     `records/scaling_gates/config_minimal_surface_completion_audit.json`,
     `tests/contract/test_resident_runtime_contract.py`, and
     `tests/contract/test_tracked_tool_dependency_boundary.py`.
   - The self-contained PR-0 staged set is therefore 16 files, not 11 files.
     The canonical pointer should advance only to
     `define_verilator_native_option_parser_direct_command_path_native_invocation_verilator_process_launcher_bridge_boundary_gate`
     with the current record count taken from `config/selection.json`.
   - Exclude `*verilator_process_launcher_bridge*`, `*observable_ordering*`,
     RTLMeter runner work, Makefile/build-path work, and source-of-truth pointer
     updates that already advance to the observable-ordering helper.
   - Keep the process-to-launcher contract test focused and under the staged
     contract-test growth limit; put bridge/gate-chain detail tests in later
     small files if they are still needed.
   - Completion condition: the process-to-launcher fixture materializes exact
     structured `run_hybrid_template.py` argv without starting the launcher, and
     the PR states that argv materialization is not execution authority.

2. Later technical split: Verilator process-to-launcher observable ordering helper.
   - Primary issues: #15 and FC-042 / #9.
   - Prerequisite: PR-0 must be merged or included in the same review stack.
   - Scope: review the implemented non-executing observable-ordering helper and
     its focused contract test.
   - Include only the matching source, tests, records, and source-of-truth
     pointer/docs updates needed for the current priority.
   - Do not include RTLMeter runner work, stdout/cycles work, or broad wrapper
     packaging changes.
   - Completion condition: contract tests pass and the PR description states
     that launcher-start-allowed metadata is not launcher execution, sidecar
     stage execution, timing, arbitrary filelist support, or production
     throughput.

3. Later docs split: Operator/docs readiness cleanup.
   - Primary issues: #12, #13, #14, and FC-044 / #11.
   - Scope: make public docs and reproduction wording match the supported
     preview surface after PR-1.
   - Keep JSON as debug/review inspection wording, not runtime ABI wording.
   - Completion condition: an external reader can distinguish supported
     template/benchmark flows, preview `--sim-accel` plumbing, and unsupported
     broad `verilator --use-gpu` claims.

4. PR-3: RTLMeter fail-closed handoff preparation.
   - Primary issues: #18, FC-034 / #8, and FC-041 / #5.
   - Scope: keep RTLMeter wrapper/context handoff metadata honest and
     fail-closed until a reviewed stdout/cycles sidecar execution source
     closure exists.
   - Do not close FC-037 / #2 or FC-040 / #4 from this PR.
   - Completion condition: RTLMeter GPU intent reaches the wrapper/context
     boundary without claiming acceleration or CPU-as-GPU fallback.

5. PR-4: Measurement evidence hardening.
   - Primary issue: #16.
   - Scope: repeat-median evidence for already policy-selected workloads only.
   - Completion condition: timing fields remain scoped evidence and do not
     become production throughput, automatic allocation, or arbitrary RTL
     claims.

6. PR-5: Filelist-derived boundary expansion.
   - Primary issues: #17 and FC-042 / #9.
   - Scope: expand from one known target/filelist/top only after PR-1 proves the
     first reviewed bridge path.
   - Completion condition: unknown or unsupported filelists fail closed, and no
     arbitrary dependency inference is claimed.

## Current Issue Correctness Snapshot

- FC-035, FC-036, and FC-038 are the correct clean-sim hardening chain. Treat
  them as prerequisite quality work, not as Verilator native-option completion
  or GPU speed evidence.
- FC-039 is complete as public goal-framing cleanup. It keeps current support,
  preview UX, long-term frontend-neutral goals, and non-claims visually
  separated while preserving the `config/selection.json` current pointer.
- FC-041 is complete as RTLMeter wrapper packaging. It materializes a generated
  PATH-selected `verilator` wrapper, delegates no-GPU argv to the real Verilator,
  fails closed for GPU intent, and does not claim RTLMeter acceleration.
- FC-034 remains the first RTLMeter executing correctness issue. FC-037 timing
  and FC-040 second-seed broadening are valid issues, but they must not produce
  timing, acceleration, or broadening claims until #49 closure accepts the
  current first-seed proxy/marker handoff evidence as sufficient.
- FC-037 and FC-040 should be treated as open-but-dependency-gated, not as
  immediately actionable measurement work.
- FC-042 / #9 is closed/completed after #35. It proved one scoped
  PATH-selected `verilator --use-gpu` wrapper path and must not be used to
  claim arbitrary RTL support, dependency inference, automatic allocation, or
  timing/speedup.
- FC-043 is architecture cleanup for the frontend-neutral contract. It may add a
  CIRCT placeholder diagnostic, but it must not claim CIRCT execution.
- FC-044 is an external-user readiness audit. It may remove or demote misleading
  surface area, but it must not introduce a new source of truth.
- FC-046 through FC-052 are the LLVM/NVPTX optimization-pass lane. Do not start
  with trigger factoring, resident step kernels, or SoA; metadata, state-access
  canonicalization, and conservative inline policy are the safer first split.

## Issues

| ID | Issue File | Target File |
|---|---|---|
| FC-001 | [README goal and user path](issues/FC-001-readme-goal.md) | `README.md` |
| FC-002 | [Tool surface JSON wording](issues/FC-002-tool-surface-json-wording.md) | `docs/tool_surface.md` |
| FC-003 | [Verilator sidecar option scope](issues/FC-003-verilator-sidecar-option-scope.md) | `docs/verilator_sidecar_option.md` |
| FC-004 | [Results debug JSON wording](issues/FC-004-results-debug-json-wording.md) | `docs/results.md` |
| FC-005 | [Status goal frame](issues/FC-005-status-goal-frame.md) | `docs/status.md` |
| FC-006 | [Roadmap sidecar goal](issues/FC-006-roadmap-sidecar-goal.md) | `docs/roadmap.md` |
| FC-007 | [Sidecar command path split](issues/FC-007-sidecar-command-path-split.md) | `src/tools/hybrid_benchmark_sidecar_commands.py` |
| FC-008 | [Discovery payload debug role](issues/FC-008-discovery-payload-debug-role.md) | `src/tools/hybrid_benchmark_catalog.py` |
| FC-009 | [Operator JSON debug markers](issues/FC-009-operator-json-debug-markers.md) | `src/tools/hybrid_benchmark_operator_core.py` |
| FC-010 | [Sidecar operator non-claims](issues/FC-010-sidecar-operator-non-claims.md) | `src/tools/hybrid_benchmark_sidecar_operator.py` |
| FC-011 | [Shim debug JSON role](issues/FC-011-shim-debug-json-role.md) | `src/tools/verilator_sidecar_shim.py` |
| FC-012 | [Benchmark CLI help JSON wording](issues/FC-012-benchmark-cli-help-json-wording.md) | `src/tools/run_hybrid_benchmark_args.py` |
| FC-013 | [Minimal suite debug naming](issues/FC-013-minimal-suite-debug-naming.md) | `src/tools/hybrid_benchmark_minimal_suite.py` |
| FC-014 | [Discovery CLI contract](issues/FC-014-discovery-cli-contract.md) | `tests/contract/test_hybrid_benchmark_discovery_cli.py` |
| FC-015 | [Benchmark/config JSON contract](issues/FC-015-benchmark-config-json-contract.md) | `tests/contract/test_hybrid_benchmark_and_config_cli.py` |
| FC-016 | [Discovery example contract](issues/FC-016-discovery-example-contract.md) | `tests/contract/test_hybrid_benchmark_discovery_examples_cli.py` |
| FC-017 | [Shim example contract](issues/FC-017-shim-example-contract.md) | `tests/contract/test_hybrid_verilator_sidecar_shim_examples_cli.py` |
| FC-018 | [Codex README index](issues/FC-018-for-codex-readme-index.md) | `for_codex/README.md` |
| FC-019 | [Project memory archive warning](issues/FC-019-project-memory-archive-warning.md) | `for_codex/project_memory.md` |
| FC-020 | [Results memory archive warning](issues/FC-020-results-memory-archive-warning.md) | `for_codex/results_memory.md` |
| FC-021 | [Status memory authority warning](issues/FC-021-status-memory-authority-warning.md) | `for_codex/status.md` |
| FC-022 | [Roadmap memory authority warning](issues/FC-022-roadmap-memory-authority-warning.md) | `for_codex/roadmap.md` |
| FC-023 | [Selection goal decision gate](issues/FC-023-selection-goal-decision-gate.md) | `config/selection.json` |
| FC-024 | [RTLMeter user path goal](issues/FC-024-rtlmeter-user-path-goal.md) | `README.md`, `docs/tool_surface.md` |
| FC-025 | [RTLMeter Verilator command capture](issues/FC-025-rtlmeter-verilator-command-capture.md) | `src/tools/rtlmeter_*` |
| FC-026 | [RTLMeter PATH wrapper prototype](issues/FC-026-rtlmeter-path-wrapper-prototype.md) | `src/tools/rtlmeter_*`, `src/tools/verilator_sidecar_shim.py` |
| FC-027 | [RTLMeter compileArgs pass-through smoke](issues/FC-027-rtlmeter-compileargs-pass-through-smoke.md) | `tests/contract/test_rtlmeter_*` |
| FC-028 | [RTLMeter sidecar contract mapping](issues/FC-028-rtlmeter-sidecar-contract-mapping.md) | `src/tools/rtlmeter_*` |
| FC-029 | [RTLMeter first seed selection](issues/FC-029-rtlmeter-first-seed-selection.md) | `config/selection.json`, `config/targets.json` |
| FC-030 | [RTLMeter CPU/GPU compare integration](issues/FC-030-rtlmeter-cpu-gpu-compare-integration.md) | `src/tools/rtlmeter_*`, `reports/` |
| FC-031 | [RTLMeter overlays audit](issues/FC-031-rtlmeter-overlays-audit.md) | `src/tools/rtlmeter_overlay_audit.py`, `tests/contract/test_rtlmeter_overlays_audit.py` |
| FC-032 | [RTLMeter public contract tests](issues/FC-032-rtlmeter-public-contract-tests.md) | `tests/contract/test_rtlmeter_*` |
| FC-033 | [RTLMeter docs and troubleshooting](issues/FC-033-rtlmeter-docs-troubleshooting.md) | `README.md`, `docs/verilator_sidecar_option.md` |
| FC-034 | [RTLMeter first seed execution integration](issues/FC-034-rtlmeter-first-seed-execution-integration.md) | `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*` |
| FC-035 | [Clean sim GPU runtime preflight](issues/FC-035-clean-sim-gpu-runtime-preflight.md) | `src/tools/run_vl_hybrid.py`, `src/tools/run_vl_hybrid_launch.py`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md` |
| FC-036 | [Move generated tool binaries out of src](issues/FC-036-move-generated-tool-binaries-out-of-src.md) | `src/passes/Makefile`, `src/hybrid/Makefile`, `src/tools/build_vl_gpu_*`, `src/tools/run_vl_hybrid_*`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md` |
| FC-037 | [RTLMeter first seed timing and acceleration measurement](issues/FC-037-rtlmeter-first-seed-timing-acceleration.md) | `src/tools/rtlmeter_*`, `reports/`, `tests/contract/test_rtlmeter_*` |
| FC-038 | [Clean sim operator log hygiene](issues/FC-038-clean-sim-operator-log-hygiene.md) | `src/tools/run_hybrid_template.py`, `src/tools/hybrid_template_commands.py`, `src/tools/run_vl_hybrid.py`, `src/tools/run_vl_hybrid_state_sanitize.py`, `reports/`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md` |
| FC-039 | [Three-layer goal framing](issues/FC-039-three-layer-goal-framing.md) | `README.md`, `docs/roadmap.md`, `docs/status.md`, `docs/tool_surface.md` |
| FC-040 | [RTLMeter second seed broadening](issues/FC-040-rtlmeter-second-seed-broadening.md) | `src/tools/rtlmeter_*`, `tests/contract/test_rtlmeter_*` |
| FC-041 | [GPU Verilator wrapper packaging](issues/FC-041-gpu-verilator-wrapper-packaging.md) | `src/tools/rtlmeter_*`, `tests/contract/test_rtlmeter_*`, `README.md`, `docs/verilator_sidecar_option.md` |
| FC-042 | [Verilator --use-gpu first real path](issues/FC-042-verilator-use-gpu-first-real-path.md) | `src/tools/verilator_*`, `src/tools/hybrid_benchmark_*`, `tests/contract/test_hybrid_*`, `README.md`, `docs/verilator_sidecar_option.md` |
| FC-043 | [Frontend-neutral sidecar contract and CIRCT boundary](issues/FC-043-frontend-neutral-sidecar-contract-circt-boundary.md) | `src/tools/*sidecar*`, `src/hybrid/`, `docs/roadmap.md`, `docs/status.md`, `README.md`, `tests/contract/` |
| FC-044 | [External user readiness audit](issues/FC-044-external-user-readiness-audit.md) | `README.md`, `docs/`, `Makefile`, `tests/contract/`, `for_codex/issues.md` |
| FC-045 | [GPU sidecar eligibility and shape policy](issues/FC-045-gpu-sidecar-eligibility-policy.md) | `src/tools/*policy*`, `src/tools/hybrid_benchmark_*`, `docs/results.md`, `README.md`, `tests/contract/` |
| FC-046 | [LLVM GPU optimization pass roadmap](issues/FC-046-llvm-gpu-optimization-pass-roadmap.md) | `src/passes/`, `src/tools/build_vl_gpu_*`, `docs/results.md`, `README.md`, `tests/contract/` |
| FC-047 | [vl-gpu-abi-metadata](issues/FC-047-vl-gpu-abi-metadata.md) | `src/passes/vlgpugen.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/` |
| FC-048 | [vl-gpu-state-access-canon](issues/FC-048-vl-gpu-state-access-canon.md) | `src/passes/VlGpuPasses.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/` |
| FC-049 | [vl-gpu-inline-policy](issues/FC-049-vl-gpu-inline-policy.md) | `src/passes/VlGpuPasses.cpp`, `src/tools/build_vl_gpu_*`, `tests/contract/` |
| FC-050 | [vl-gpu-trigger-guard-factor](issues/FC-050-vl-gpu-trigger-guard-factor.md) | `src/passes/VlGpuPasses.cpp`, `src/passes/vlgpugen.cpp`, `tests/contract/` |
| FC-051 | [vl-gpu-resident-step-kernel](issues/FC-051-vl-gpu-resident-step-kernel.md) | `src/passes/vlgpugen.cpp`, `src/hybrid/`, `src/tools/run_vl_hybrid*`, `tests/contract/` |
| FC-052 | [vl-gpu-hot-field-soa](issues/FC-052-vl-gpu-hot-field-soa.md) | `src/passes/`, `src/hybrid/`, `src/tools/build_vl_gpu_*`, `tests/contract/` |

## Parallel Split

- Agent A: FC-001 through FC-006, public docs only.
- Agent B: FC-007 through FC-013, CLI and JSON/debug implementation.
- Agent C: FC-014 through FC-017, contract tests.
- Agent D: FC-018 through FC-023, Codex memory and source-of-truth alignment.
- Agent E: FC-024 through FC-034, FC-037, FC-040, and FC-041, RTLMeter user-path exploration. Keep this separate from current sidecar cleanup unless a file is explicitly owned. FC-034 is the first executing issue; keep it isolated from non-executing FC-024 through FC-033. FC-037 measures timing only and depends on a passing FC-034 correctness compare. FC-040 broadens to exactly one second seed and is gated on FC-034 evidence. FC-041 packages the PATH wrapper and must fail closed without faking GPU execution.
- Agent F: FC-035 through FC-036 and FC-038, clean sim hardening. Keep it separate from RTLMeter execution integration, do not turn blocked GPU access into a success claim, do not normalize generated binaries under `src/` as acceptable public UX, and keep default operator logs concise enough for external users.
- Agent G: FC-039, public goal framing. Keep long-term UX, current preview support, frontend-neutral contract, and non-claims visually separated.
- Agent H: FC-042, first real Verilator `--use-gpu` path. Treat this lane as
  completed evidence after #9/#35; do not reopen it except to fix scoped-support
  wording.
- Agent I: FC-043, frontend-neutral contract/CIRCT boundary. Keep this as
  contract extraction and placeholder diagnostics only; no CIRCT execution claim.
- Agent J: FC-044, external-user readiness audit. This is the current active
  lane after #35; prefer deleting, moving, or demoting misleading files over
  documenting around them.
- Agent K: FC-045, GPU sidecar eligibility and shape policy. Use existing
  repeat-median evidence to produce conservative recommendations; do not claim
  automatic optimal allocation.
- Agent L: FC-046 through FC-052, LLVM/NVPTX optimization pass lane. Keep the
  first PR to ABI metadata, state-access canonicalization, or conservative
  inline policy; do not start with resident kernels or SoA.

## Guardrails

- Do not move canonical decisions into `for_codex/`.
- Do not promote JSON from debug output into runtime ABI.
- Do not claim CIRCT execution support yet.
- Do not claim general `verilator --use-gpu -f filelist.f --top-module top` support yet.
- Do not claim RTLMeter acceleration just because RTLMeter compiles.
- Keep RTLMeter's native user path intact; avoid requiring users to select repo-specific harness JSON manually.
- Do not update `config/selection.json` without a reviewed goal/priority change.
