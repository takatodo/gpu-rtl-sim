# FC-025: RTLMeter Verilator Command Capture

Status: done
Owner: Codex
Target file: `src/tools/rtlmeter_*`

## Objective

Capture the Verilator command shape that RTLMeter emits for a selected case without requiring a full GPU execution path. The sidecar needs to understand RTLMeter's `--top-module`, `-f filelist`, include dirs, defines, and extra args.

## Tasks

- Inspect RTLMeter descriptors through RTLMeter's existing Python modules or command output.
- Produce an importable helper that normalizes a selected RTLMeter case into frontend-owned build metadata.
- Preserve RTLMeter-owned compile and execute semantics; do not rewrite RTLMeter descriptors in place.
- Keep any JSON output as optional debug capture.

## Acceptance

- A selected RTLMeter case can be inspected into a stable command/metadata object.
- The helper does not call GPU build/run/compare.
- The helper does not require copying RTLMeter source files into this repo's template registry.

## Validation

```sh
python3 -m unittest tests.contract.test_rtlmeter_verilator_command_capture -q
```

Add this test with the implementation.

Result: passed on 2026-06-01.

## Resolution

- Added `src/tools/rtlmeter_verilator_command_capture.py`.
- The helper captures RTLMeter descriptor-derived Verilator metadata for a selected case without compiling RTLMeter, running Verilator, building GPU artifacts, comparing outputs, or measuring timing.
- The capture preserves frontend-owned fields such as top module, main clock, filelist entries, source/include files, defines, Verilator args, and extra args.
- The command capture mirrors RTLMeter's trace define injection for `--trace`, `--trace-vcd`, and `--trace-fst`.
- The returned structure marks JSON as `debug_inspection` with `runtime_abi: false` and `execution_authority: false`.
- Added `tests/contract/test_rtlmeter_verilator_command_capture.py`.
