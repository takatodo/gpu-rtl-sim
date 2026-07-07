# FC-058: RTLMeter direct native sidecar path without proxy lane

Status: open
GitHub: https://github.com/takatodo/gpu-rtl-sim/issues/58
Parent umbrella: FC-053 / https://github.com/takatodo/gpu-rtl-sim/issues/46
Goal framing: FC-039 / https://github.com/takatodo/gpu-rtl-sim/issues/1
Prerequisite: FC-057 / https://github.com/takatodo/gpu-rtl-sim/issues/57
Supersedes interim lane: https://github.com/takatodo/gpu-rtl-sim/issues/49

## Objective

After FC-057 proves that a make-built `obj_dir/V<top>` can invoke the GPU
sidecar runtime directly, route the first RTLMeter seed through that native
executable path instead of the interim proxy/marker lane.

The goal is to preserve RTLMeter's normal user workflow while removing the
temporary `RTLMETER_VSIM_SIDECAR_PROXY` / marker / review-manifest mechanism
from the evidence path.

## Current Boundary

The current RTLMeter proxy lane (#49/#51/#53) is frozen because it can only
prove that a reviewed proxy handoff occurred. The #51 trial showed the proxy
review surface was forgeable by a CPU-delegate proxy, and #52 only fixed the
wording/self-attestation risk. Proxy-lane outputs must not become GPU execution
evidence.

FC-057 is the prerequisite because RTLMeter should be able to execute the
generated `obj_dir/Vsim` directly once the native Verilator sidecar executable
path exists.

2026-06-14 direct-native priority probe status:

- CPU baseline for `Example:kind:hello` passed.
- The GPU/direct-native candidate reached the RTLMeter/Verilator build path
  without the frozen `RTLMETER_VSIM_SIDECAR_PROXY` precheck.
- The candidate still failed closed before simulation execute because the
  RTLMeter-generated `top` plus generated `filelist` is not a tracked native
  sidecar known closure.
- The recorded sidecar build status was
  `verilator_native_sidecar_blocked_unrecognized_closure`, with
  `cpu_as_gpu_fallback=false` and `gpu_execution_claimed=false`.
- Therefore RTLMeter GPU usefulness and speed are still not measurable from the
  first seed. The blocker is now concrete: add a real RTLMeter-native known
  closure or choose exactly one RTLMeter seed that maps to a sidecar-supported
  kernel/state layout without faking GPU execution.

## Scope

- Run the selected RTLMeter first seed through RTLMeter's normal compile/execute
  workflow using the native sidecar-capable Verilator path.
- Ensure RTLMeter executes the generated native sidecar `obj_dir/Vsim` (or
  equivalent RTLMeter-named executable) directly, not a proxy script.
- Preserve RTLMeter observables: normalized stdout and RTLMeter cycle count.
- Compare against the CPU reference using the existing stdout/cycles policy.
- Close or supersede #49/#51/#53 after recording why proxy evidence is obsolete.
- Keep timing and second-seed broadening gated on this correctness result.

## Path To A RTLMeter Usefulness Claim

The useful/faster question is answered only after these gates, in order:

1. Keep the current direct-native RTLMeter path intact: no proxy script, no
   marker/review-manifest handoff, no CPU-as-GPU fallback, and fail-closed for
   unsupported filelist/top pairs.
2. Establish the CPU-parallel RTLMeter baseline in FC-037 before making any GPU
   usefulness claim. Run the same RTLMeter seed as independent CPU simulations
   with isolated work roots, sweep worker counts, and record throughput plus
   stdout/cycle equivalence.
3. Make the RTLMeter first seed a genuine native sidecar known closure, or
   record why `Example:kind:hello` is unsuitable and choose exactly one
   replacement RTLMeter seed. This must use RTLMeter-generated compile inputs;
   it must not redirect to `pulp_ita_mha` or another unrelated template flow.
4. Re-run FC-058 direct-native correctness. The candidate must build and execute
   the generated RTLMeter-named executable, record GPU artifact/kernel evidence,
   preserve normalized stdout/cycles, and leave CPU fallback impossible.
5. Only then run FC-037 timing. Compare CPU serial, best CPU-parallel baseline,
   GPU wall time, and GPU kernel diagnostics as separate fields. A negative or
   slower GPU result is a valid outcome and must be reported.
6. Keep FC-040 second-seed broadening blocked until the first seed has both
   direct-native correctness and honest timing evidence.

## Acceptance

- RTLMeter first seed runs CPU reference and native sidecar candidate from the
  RTLMeter workflow.
- Candidate execution invokes the native GPU sidecar runtime through the
  generated executable, not `RTLMETER_VSIM_SIDECAR_PROXY`.
- Normalized stdout and RTLMeter cycle count match the CPU reference.
- `gpu_execution_claimed` is true only if the native executable path records
  GPU artifact load / kernel-launch evidence; otherwise the run remains
  fail-closed.
- CPU-as-GPU fallback is impossible and remains explicitly false.
- #49/#51/#53 are closed or re-labeled as superseded with links to this issue
  and the native-path evidence.
- #2 timing and #4 second seed remain blocked until this correctness gate is
  accepted.

## Non-claims

- No RTLMeter acceleration or speedup claim.
- No second seed or broad RTLMeter support.
- No arbitrary filelist inference or automatic allocation claim.
- No generated report as source of truth.

## Validation

Required:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.contract.test_rtlmeter_verilator_wrapper_runtime \
  tests.contract.test_rtlmeter_stdout_cycles_runner_contract \
  tests.contract.test_rtlmeter_cpu_gpu_compare_integration -q
PYTHONDONTWRITEBYTECODE=1 make surface
git diff --check
PYTHONDONTWRITEBYTECODE=1 python3 src/tools/check_staged_large_files.py
```

Plus one real RTLMeter first-seed run that records CPU reference, native
sidecar candidate execution, stdout/cycles comparison, and fail-closed behavior
for missing native sidecar runtime prerequisites.
