# FC-026: RTLMeter PATH Wrapper Prototype

Status: done
Owner: Codex
Target file: `src/tools/rtlmeter_*`, `src/tools/verilator_sidecar_shim.py`

## Objective

Prototype the simplest RTLMeter-preserving integration boundary: a future repo wrapper named `verilator` would sit earlier in `PATH`, let RTLMeter invoke it normally, and decide whether the command can enter the sidecar path.

## Tasks

- Define a wrapper strategy that accepts normal Verilator argv from RTLMeter.
- Detect `--use-gpu` or sidecar options without changing RTLMeter's command model.
- Fail closed for unsupported argv instead of silently running CPU-only while claiming GPU.
- Keep wrapper logic thin and route reusable parsing/planning into importable helpers.

## Acceptance

- The proposed wrapper does not require RTLMeter source patches.
- Unsupported commands produce a clear diagnostic.
- The issue outcome identifies the minimal supported argv surface for the first run.

## Validation

```sh
python3 -m unittest tests.contract.test_rtlmeter_path_wrapper -q
```

Add this test with the implementation.

Result: passed on 2026-06-01.

## Resolution

- Added `src/tools/rtlmeter_verilator_path_wrapper.py`.
- The prototype classifies a Verilator argv as a PATH-selected wrapper named `verilator` would see it.
- It detects `--use-gpu` and expanded `--sim-accel sidecar-gpu --sim-accel-states N --sim-accel-steps S`.
- It records the minimal first-run argv surface as `verilator --cc -f <filelist> --top-module <top> --use-gpu` or expanded sidecar options.
- It fails closed for GPU-intent argv missing `--top-module` or `-f`.
- It is an inspection prototype only; it does not delegate no-GPU-intent argv to a real Verilator yet.
- It does not patch RTLMeter, run Verilator, build GPU artifacts, run sidecar stages, compare outputs, or measure timing.
