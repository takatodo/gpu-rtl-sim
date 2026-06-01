# FC-035: Clean Sim GPU Runtime Preflight

Status: open
Owner: Unassigned
Target file: `src/tools/run_vl_hybrid.py`, `src/tools/run_vl_hybrid_launch.py`, `tests/contract/test_clean_sim_prerequisites.py`, `README.md`

## Objective

Finish the clean-checkout sim path by making GPU runtime availability fail
closed with an explicit diagnostic before anyone can mistake an environment
blocker for a sidecar success or a build prerequisite bug.

FC-035 starts after the local prerequisite cleanup fix: missing
`src/passes/vlgpugen`, `src/passes/VlGpuPasses.so`, and
`src/hybrid/run_vl_hybrid` should be rebuilt on demand after `git clean -fdX`.
The remaining observed blocker is runtime GPU access: the current environment
reaches `cuInit` and fails with CUDA error 304 while `nvidia-smi` reports GPU
access blocked by the operating system.

## Tasks

- Add a deterministic GPU runtime preflight or launch-time classification that
  reports CUDA driver initialization failure as `gpu_runtime_unavailable` or an
  equally explicit status.
- Preserve fail-closed behavior: never fall back to CPU and report it as GPU.
- Keep generated Verilator, LLVM, CUBIN, state, and report material under
  ignored `artifacts/` and `reports/` locations.
- Keep the normal non-GPU test suite green by mocking or injecting the runtime
  availability check in contract tests.
- Document the expected clean path and the blocked-GPU diagnostic in README
  troubleshooting or the relevant tool surface.

## Acceptance

- After `git clean -fdX`, the template path no longer fails because
  `vlgpugen`, `VlGpuPasses.so`, or `run_vl_hybrid` is missing.
- On a machine where CUDA driver access is blocked, the command exits nonzero
  with a concise GPU-runtime-unavailable diagnostic and no Python traceback.
- On a CUDA-capable machine, the same path can proceed to the existing
  CPU-vs-hybrid compare policy without changing correctness semantics.
- `git status --short --untracked-files=all` shows no extra git-visible output
  after the generated ignored files are cleaned.

## Validation

```sh
git clean -fdX -e .codex -e .agents
python3 src/tools/run_hybrid_template.py config/slice_launch_templates/tlul_fifo_sync.json --shape 1x1
python3 -m unittest tests.contract.test_clean_sim_prerequisites -q
git diff --check
```

For non-GPU environments, the template command is allowed to exit nonzero only
with the explicit GPU-runtime-unavailable diagnostic. It must not fail earlier
with missing local build tools.

## Non-Goals

- No broad `verilator --use-gpu` support claim.
- No RTLMeter acceleration claim.
- No timing or speedup claim.
- No automatic GPU allocation.
- No promotion of debug JSON into the runtime ABI.
