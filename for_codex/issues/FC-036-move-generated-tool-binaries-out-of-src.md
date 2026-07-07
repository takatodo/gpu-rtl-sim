# FC-036: Move Generated Tool Binaries Out of `src/`

Status: done
Owner: Unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/6
Target file: `src/passes/Makefile`, `src/hybrid/Makefile`, `src/tools/build_vl_gpu_*`, `src/tools/run_vl_hybrid_*`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md`

## Objective

Stop writing generated helper binaries into `src/` during normal clean-checkout
sim flows.

The current clean path can rebuild missing prerequisites, but it still produces
ignored binaries at:

- `src/passes/VlGpuPasses.so`
- `src/passes/vlgpugen`
- `src/hybrid/run_vl_hybrid`

That is a weak user-facing design. `src/` should read as source, not as a build
output directory. For a repository intended for other users, generated binaries
belong under `artifacts/` or another clearly ignored build-output location.

This is a clean-sim hardening step for FC-035's prerequisites. It does not
attempt to unblock FC-034's RTLMeter launcher handoff, choose a reviewed
RTLMeter launch template, or resolve RTLMeter source closure.

## Tasks

- Choose one ignored output root for local helper binaries, for example
  `artifacts/tool_bins/` or `artifacts/build_tools/`.
- Update the pass build so `VlGpuPasses.so` and `vlgpugen` are emitted outside
  `src/passes/`.
- Update the hybrid runtime build so `run_vl_hybrid` is emitted outside
  `src/hybrid/`.
- Update Python launch/build helpers to resolve and rebuild the relocated
  binaries without requiring users to know the internal output paths.
- Keep compatibility only if it is cheap and explicit; do not silently prefer
  stale source-tree binaries over freshly generated artifact binaries.
- Update contract tests and docs so `git clean -fdX` followed by a template run
  does not recreate source-tree binaries.
- Preserve the native RTLMeter path and do not require users to manually select
  repository-specific harness JSON.
- Do not update `config/selection.json`; this issue is not a reviewed priority
  or seed-selection change.

## Acceptance

- After `git clean -fdX -e '!.codex' -e '!.agents'`, a template run may create
  ignored generated files, but not `src/passes/VlGpuPasses.so`,
  `src/passes/vlgpugen`, or `src/hybrid/run_vl_hybrid`.
- `build_vl_gpu.py` and `run_vl_hybrid.py` still rebuild missing local helper
  binaries on demand.
- `git status --short --untracked-files=all` shows no extra git-visible files
  from the flow.
- `git clean -ndX -e '!.codex' -e '!.agents'` shows generated outputs only under
  ignored output locations, plus local busy metadata such as `.codex/` and
  `.agents/` if present.
- The non-GPU contract path stays green by mocking, injecting, or skipping real
  GPU runtime access while still failing closed for missing local helper
  binaries.

## Validation

```sh
git clean -fdX -e '!.codex' -e '!.agents'
log="$(mktemp)"
if ! python3 src/tools/run_hybrid_template.py config/slice_launch_templates/tlul_fifo_sync.json --shape 1x1 >"$log" 2>&1; then
  grep -E "gpu_runtime_unavailable|CUDA driver|CUDA error 304|operating system" "$log"
fi
test ! -e src/passes/VlGpuPasses.so
test ! -e src/passes/vlgpugen
test ! -e src/hybrid/run_vl_hybrid
python3 -m unittest tests.contract.test_clean_sim_prerequisites -q
git diff --check
```

In non-GPU environments, the template command may stop at the FC-035
GPU-runtime-unavailable boundary. It must not recreate source-tree binaries
before that failure.

## Current State

- Local helper binaries now build under `artifacts/tool_bins/passes/` and
  `artifacts/tool_bins/hybrid/`.
- `src/passes/Makefile` keeps explicit compatibility targets for `vlgpugen`
  and `VlGpuPasses.so`, so make does not fall back to implicit source-tree
  outputs.
- `src/hybrid/Makefile` keeps an explicit `run_vl_hybrid` compatibility target
  that depends on the artifact runner.
- `build_vl_gpu.py` and `run_vl_hybrid.py` resolve the relocated helper
  binaries without requiring operator-visible paths.
- Contract tests now cover relocated helper paths, artifact runner argv,
  compatibility make dry-runs, and log sanitization for option-value absolute
  paths.
- Verified real `make -C src/passes` and `make -C src/hybrid` builds produce
  only artifact helper binaries; `src/passes/VlGpuPasses.so`,
  `src/passes/vlgpugen`, and `src/hybrid/run_vl_hybrid` remain absent.
- Verified a non-GPU template run stops at the FC-035
  `classified_failure: gpu_runtime_unavailable` boundary without recreating
  source-tree helper binaries.
- `git clean -fdX -e '!.codex' -e '!.agents'` was run in this workspace, then
  the template flow rebuilt helper binaries only under `artifacts/tool_bins/`
  and did not recreate `src/` helper binaries.
- Full contract validation passed after the clean/rebuild check with 530 tests.

## Non-Goals

- No broad `verilator --use-gpu` support claim.
- No CIRCT execution support claim.
- No timing or speedup claim.
- No RTLMeter acceleration claim.
- No RTLMeter native UX regression or manual harness JSON requirement.
- No promotion of debug JSON into a runtime ABI.
- No cleanup of unrelated generated or historical files.
- No promotion of generated outputs to source of truth.
- No canonical decision moved into `for_codex/`, `artifacts/`, or `reports/`.
- No `config/selection.json` update.
- No environment blocker reported as success.
