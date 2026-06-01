# FC-028: RTLMeter Sidecar Contract Mapping

Status: done
Owner: Codex
Target file: `src/tools/rtlmeter_*`

## Objective

Map RTLMeter's descriptor-derived Verilator build metadata into the frontend-neutral sidecar contract without making RTLMeter-specific JSON the runtime ABI.

## Tasks

- Define which fields are frontend-owned: top module, filelist/source files, include dirs, defines, C++ sources, and Verilator args.
- Define which fields remain sidecar-owned: source closure status, GPU build artifacts, coverage-output selection, state paths, compare labels, and reports.
- Reuse existing sidecar planning helpers where possible.
- Reject ambiguous or incomplete RTLMeter metadata.

## Acceptance

- Mapping is importable and unit-testable.
- Mapping produces structured Python data first; JSON is optional debug output.
- Mapping does not require RTLMeter-specific launch templates for the public path.

## Validation

```sh
python3 -m unittest tests.contract.test_rtlmeter_sidecar_contract_mapping -q
```

Result: passed on 2026-06-01.

## Resolution

- Added `src/tools/rtlmeter_sidecar_contract_mapping.py`.
- The mapper converts RTLMeter command-capture metadata into structured, non-executing sidecar contract metadata.
- Frontend-owned fields are explicit: top module, main clock, filelist entries, source/include files, defines, C++ inputs, Verilator args, and extra args.
- Sidecar-owned responsibilities remain unresolved: source closure, GPU artifacts, coverage-output selection, state paths, compare labels, generated reports, CPU/GPU execution, timing, and allocation.
- The mapping rejects wrong surfaces and prepopulated sidecar-owned fields.
- Added `tests/contract/test_rtlmeter_sidecar_contract_mapping.py`.
