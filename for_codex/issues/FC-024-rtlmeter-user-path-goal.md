# FC-024: RTLMeter User Path Goal

Status: done
Owner: Codex
Target file: `README.md`, `docs/tool_surface.md`

## Objective

Define the RTLMeter goal from the user's point of view: a user wants RTLMeter designs to run faster without abandoning normal RTLMeter commands. Compiling RTLMeter or compiling an extracted harness is not sufficient.

## Tasks

- State the target user path as `./rtlmeter run --cases ... --compileArgs "--use-gpu"` or a `PATH`-selected `verilator` wrapper.
- State that repo-specific `config/slice_launch_templates/*.json` selection is not the desired public RTLMeter UX.
- Separate "RTLMeter design used as research input" from "RTLMeter workflow accelerated".
- Record that JSON remains debug/inspection output only.

## Acceptance

- Public docs do not imply RTLMeter acceleration from compile-only evidence.
- Public docs name the simple RTLMeter-preserving command shape.
- Unsupported RTLMeter cases are described as fail-closed.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_verilator_command_capture -q
```

Result: passed on 2026-06-01.

## Resolution

- README now names the RTLMeter-preserving target commands using `--compileArgs "--use-gpu"` and a `PATH`-selected Verilator wrapper.
- `docs/tool_surface.md` states that repo-specific launch-template selection is not the desired RTLMeter UX.
- Public docs distinguish RTLMeter-derived harness experiments from proven RTLMeter workflow acceleration.
- Docs state that unsupported RTLMeter cases should fail closed and RTLMeter JSON capture remains debug/inspection metadata.
