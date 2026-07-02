# FC-042: Verilator --use-gpu First Real Path

Status: done
Owner: unassigned
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/9
Target file: `src/tools/verilator_*`, `src/tools/hybrid_benchmark_*`, `tests/contract/test_hybrid_*`, `README.md`, `docs/verilator_sidecar_option.md`

Completion note: GitHub #9 is closed/completed after #33 packaged the scoped
PATH-selected wrapper and #35 synced the canonical pointer to
`external_user_readiness_audit_gate`. The completed path remains narrow:
`filelist_known_template_pulp_ita_mha` / `pulp_ita_mha_gpu_cov_tb`, explicit
`64x1`, coverage-output equivalence mismatch count `0`, and no CPU-as-GPU
fallback.

## Objective

Turn the current Verilator-like preview and native-minimum plumbing into one
reviewed, executing first path for the long-term shorthand:

```sh
verilator --use-gpu -f filelist.f --top-module top
```

The first path must be narrow. It should prove that one known supported target
can enter the sidecar build/run/compare path from a Verilator-facing
filelist/top command, while unsupported paths fail closed. This is not broad
arbitrary RTL support.

Depends on FC-039 goal framing, the current launcher-invocation run review, and
the clean-sim hardening chain FC-035, FC-036, and FC-038. It is separate from
RTLMeter FC-034, FC-037, and FC-040.

## Tasks

- Define exactly how `--use-gpu` expands to the current native-minimum schedule
  or how the schedule is provided when `--use-gpu` is present.
- Select exactly one existing reviewed target/filelist/top pair for the first
  real path; do not infer arbitrary filelists.
- Preserve ordinary Verilator build inputs while passing only reviewed schedule
  and sidecar metadata across the sidecar boundary.
- Route the selected command into the sidecar launcher and reach CPU-vs-hybrid
  compare with the declared `coverage_output_equivalence` policy.
- Fail closed for unknown filelists, missing top, missing sidecar context,
  unavailable GPU runtime, and unsupported schedules; never report a CPU run as
  GPU execution.
- Add focused contract tests for the successful supported path, unsupported
  path rejection, and `--use-gpu` shorthand expansion or diagnostic.
- Update public docs so the first real path is presented as scoped support, not
  as a general Verilator replacement.

## Acceptance

- One documented `verilator --use-gpu -f <known-filelist> --top-module <known-top>`
  style command reaches sidecar build/run/compare and records
  `coverage_output_equivalence` mismatch count `0`.
- Unsupported or unknown inputs fail closed with a clear diagnostic and no
  CPU-as-GPU fallback.
- The implementation does not make JSON the runtime ABI and does not move
  sidecar-owned metadata into parser-owned fields.
- No arbitrary RTL, dependency inference, automatic allocation, timing,
  production throughput, CIRCT, or raw full-state equality claim is added.
- The docs and tests make the narrow scope visible to an external user.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_hybrid_benchmark_and_config_cli -q
python3 -m unittest tests.contract.test_hybrid_verilator_sidecar_shim_examples_cli -q
```

Add or extend a focused contract test for the first real `--use-gpu` path. The
test may skip or fail closed when GPU driver access is unavailable, but it must
not classify blocked GPU access as success.

## Non-Goals

- No general `verilator --use-gpu` support for arbitrary RTL.
- No automatic dependency inference from arbitrary `-f filelist.f`.
- No automatic GPU allocation or timing/speedup claim.
- No CIRCT execution support.
- No mandatory JSON runtime ABI.
