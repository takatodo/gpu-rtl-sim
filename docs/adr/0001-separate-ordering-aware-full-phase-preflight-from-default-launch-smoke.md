# Separate Ordering-Aware Full-Phase Preflight From Default Launch Smoke

FC-069's next question is whether the ordering-aware token-loop can run one
full logical `tb_core` phase with `loop_chunk=1701`, not whether the generic
zero-initialized `tb_core` launch path is healthy. We will therefore use a
narrow Ordering-Aware Full-Phase Preflight that checks module load,
ordering-aware entrypoint presence, and lowering-plan validation, and we will
not require the Default Launch Smoke before attempting the full-phase rerun.

This trades away one broad runtime-health check from the gate path so that an
unrelated generic launch timeout cannot block the specific ordering-aware
runtime question. Generic launch-smoke failures should still be recorded as
separate runtime health evidence, but they must not be interpreted as a
full-phase token-loop semantic failure.

The preflight should use the existing `run_vl_hybrid.py` / C runtime path with
an opt-in module-load-and-symbol-check mode, rather than a separate Python CUDA
probe, so the checked module format, runtime environment, timeout behavior, and
symbol lookup semantics match the path used for the real rerun.

The module-load-and-symbol-check mode should stop after CUDA initialization,
device/context creation, module load, and `cuModuleGetFunction` for the required
symbol. It must not launch the kernel; kernel-body behavior belongs to the
full-phase rerun itself, not to preflight.

`run_vl_hybrid.py` should remain a thin runtime CLI: it returns an exit status
and trace output for the module-load-and-symbol-check mode. The gateGPT probe
helper owns the structured manifest fields that classify the result into the
Ordering-Aware Full-Phase Preflight status vocabulary.
