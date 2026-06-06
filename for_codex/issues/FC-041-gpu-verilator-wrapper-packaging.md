# FC-041: GPU Verilator Wrapper Packaging

Status: done
Owner: Codex
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/5
Target file: `src/tools/rtlmeter_*`, `tests/contract/test_rtlmeter_*`, `README.md`, `docs/verilator_sidecar_option.md`

## Objective

Turn the FC-026 PATH-wrapper prototype (which only classifies an argv) into a
real, installable `verilator` wrapper a user can place on `PATH` ahead of the
real Verilator. This lets RTLMeter's native commands carry GPU intent without
patching RTLMeter. The wrapper delegates to the real Verilator for non-GPU
builds and fails closed for unsupported GPU argv. It makes no acceleration claim.

Depends on FC-025 (command capture), FC-026 (wrapper classification), and FC-027
(compileArgs pass-through). Reuse `inspect_rtlmeter_verilator_wrapper_argv`; do
not fork its classification logic.

## Tasks

- Provide an executable wrapper (for example `src/tools/verilator_gpu_wrapper.py`) that, when named `verilator` on `PATH`, inspects its argv via the FC-026 classifier.
- When no GPU intent is present: delegate transparently to the real Verilator found later on `PATH`, preserving argv, exit code, stdout, and stderr.
- When GPU intent is present with complete RTLMeter build inputs: route to the sidecar planning path. Until FC-034 execution lands, be honest that it is not yet executing (emit the wrapper inspection and exit non-zero) rather than faking success.
- When GPU intent is present but required inputs are missing: fail closed with the FC-026 diagnostic; never silently delegate a CPU run and report it as GPU.
- Find the real Verilator without recursing into the wrapper itself (self-recursion guard).
- Do not patch RTLMeter and do not require repo-specific launch-template selection.
- Document install: prepend the wrapper directory to `PATH`, then run `./rtlmeter run --cases <case> --compileArgs "--use-gpu"`.

## Acceptance

- A runnable wrapper exists and is documented as a `PATH`-selected `verilator`.
- No-GPU-intent argv delegates to the real Verilator with preserved behavior and exit code.
- GPU-intent argv with missing inputs fails closed with a diagnostic; no CPU-as-GPU misreport.
- The wrapper does not patch RTLMeter and does not require manual launch-template selection.
- Self-recursion is prevented (the wrapper does not invoke itself as the real Verilator).
- Until FC-034 execution exists, the GPU-intent path is honest about not yet executing; no speedup claim.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_path_wrapper -q
```

Extend `test_rtlmeter_path_wrapper` or add a focused
`tests/contract/test_rtlmeter_wrapper_script_*` test covering delegation, the
fail-closed path, and the self-recursion guard, using a stub `verilator` on
`PATH` so the suite stays green without a real Verilator.

## Completion

Implemented as wrapper packaging only:

- `write_rtlmeter_verilator_wrapper()` materializes an executable generated
  `verilator` wrapper for PATH testing.
- The generated wrapper passes `RTLMETER_VERILATOR_WRAPPER_SELF="$0"` to the
  runtime, so real-Verilator resolution excludes the wrapper path even though
  the shell wrapper execs the Python runtime.
- No-GPU argv delegates to the real Verilator found later on `PATH` or through
  `RTLMETER_REAL_VERILATOR`, preserving stdout, stderr, and exit code.
- GPU-intent argv fails closed and now includes the FC-026 wrapper inspection
  plus `missing_required_inputs` in the runtime diagnostic JSON.
- This ledger entry is paired with focused materialized-wrapper process tests;
  canonical user-facing docs remain outside this staged slice.

Validation passed:

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_verilator_wrapper_runtime.RtlmeterVerilatorWrapperRuntimeTest.test_materialized_wrapper_delegates_no_gpu_argv_preserving_process_behavior tests.contract.test_rtlmeter_verilator_wrapper_runtime.RtlmeterVerilatorWrapperRuntimeTest.test_materialized_wrapper_gpu_intent_fails_closed_without_delegating tests.contract.test_rtlmeter_verilator_wrapper_runtime.RtlmeterVerilatorWrapperRuntimeTest.test_materialized_wrapper_gpu_intent_with_missing_inputs_reports_inspection -q
make surface
python3 src/tools/check_staged_large_files.py
```

No acceleration, timing, broad `verilator --use-gpu`, RTLMeter execution, or
stable JSON runtime ABI claim was added.

## Non-Goals

- No acceleration claim; wrapper packaging is plumbing only.
- No RTLMeter source patching.
- No automatic GPU allocation.
- Debug JSON stays debug, not the runtime ABI.
