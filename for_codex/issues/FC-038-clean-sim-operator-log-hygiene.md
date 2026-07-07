# FC-038: Clean Sim Operator Log Hygiene

Status: done
Owner: Unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/3
Target file: `src/tools/run_hybrid_template.py`, `src/tools/hybrid_template_commands.py`, `src/tools/run_vl_hybrid.py`, `src/tools/run_vl_hybrid_state_sanitize.py`, `reports/`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md`

## Objective

Make the clean-checkout sim path readable for a normal operator.

After the clean prerequisite fix, the flow can reach the runtime boundary, but
the terminal output is still too noisy for a public user path. Verilator warnings,
full build commands, repeated pass logs, and a huge sanitized-state field list
all stream to the terminal. That makes real failures hard to see and encourages
users to treat raw logs as the source of truth.

## Tasks

- Define a concise terminal summary for `run_hybrid_template.py` stages:
  Verilator build, host probe, GPU artifact build, hybrid runtime, compare.
- Keep detailed build/pass/sanitize logs available as generated artifacts or
  reports, not as the default terminal surface.
- Replace the default sanitized-state region dump with a compact count and a
  path to detailed debug output. Preserve a verbose/debug mode for developers.
- Keep Verilator warnings visible enough to diagnose source issues, but avoid
  drowning the final failure classification.
- Add contract coverage for default concise output and explicit verbose output.
- Document where detailed logs are written and that they are generated evidence,
  not source of truth.

## Acceptance

- A clean template run that stops at GPU runtime preflight or `cuInit` prints a
  short stage summary plus the final classified failure.
- The default terminal output does not include the full sanitized-state region
  list.
- A verbose or debug flag can still expose detailed command/pass/sanitize logs
  for development.
- Detailed logs, if written, live under ignored `reports/` or `artifacts/`
  paths and are regenerable.
- Existing non-GPU contract tests remain green.

## Validation

```sh
python3 -m unittest tests.contract.test_clean_sim_prerequisites -q
python3 -m unittest discover -s tests/contract -q
git diff --check
```

Add focused tests that assert default output is concise without requiring a real
GPU.

## Current State

- Added `--verbose` to `src/tools/run_hybrid_template.py`; non-dry runs now use
  a concise seven-stage terminal summary by default.
- Default stage details are written as generated `reports/*_<stage>.log` files,
  while dry-runs still print the full command plan.
- `run_vl_hybrid` sanitized init-state reporting is compact by default and
  leaves full region details behind `RUN_VL_HYBRID_VERBOSE_SANITIZE=1`.
- Focused tests cover concise output, verbose output, compact sanitize output,
  and short stage-failure messages without requiring a real GPU.
- Inspected a real `pulp_ita_mha 64x1` template run. The terminal showed only
  the seven-stage summary; stage 3/4/6 now include both log and report paths.
- Generated stage logs sanitize local absolute paths, including temporary
  sanitized init-state paths.
- Inspected a forced `cuInit` failure with `CUDA_VISIBLE_DEVICES=-1` on
  `pulp_ita_mha 1x1`. The terminal stops cleanly at stage 6 with
  `Hybrid sidecar run failed`, `classified_failure: gpu_runtime_unavailable`,
  and log/report paths.
- The generated hybrid sidecar log preserves the CUDA driver error and hint,
  avoids traceback noise, and does not leak local absolute paths.
- Added a regression test that requires the short classified failure to appear
  on the default terminal surface without streaming the full runtime log.
- Full contract validation passed after regenerating the normal `64x1` success
  report so existing efficiency tests do not read a failure transcript; after
  the classified-failure fix, `python3 -m unittest discover -s tests/contract
  -q` passed with 525 tests.

## Non-Goals

- No suppression of real compile/runtime errors.
- No timing or speedup claim.
- No broad `verilator --use-gpu` support claim.
- No promotion of logs or debug JSON into runtime ABI.
- No change to the selected correctness policy.
