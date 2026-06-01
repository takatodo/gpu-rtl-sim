# FC-033: RTLMeter Docs And Troubleshooting

Status: done
Owner: Codex
Target file: `README.md`, `docs/verilator_sidecar_option.md`

## Objective

Document the RTLMeter path only after the supported command shape is pinned. The docs should help a RTLMeter user try GPU sidecar without learning this repo's internal template system.

## Tasks

- Add the simplest supported RTLMeter command once FC-025 through FC-028 define it.
- Explain how to use a `PATH` wrapper or `--compileArgs` without patching RTLMeter.
- State unsupported cases and failure diagnostics.
- Avoid claiming speedup until CPU/GPU compare and timing are both measured.

## Acceptance

- Docs start from RTLMeter commands, not repo-specific JSON templates.
- Docs include a fail-closed troubleshooting path.
- Docs distinguish compile success, GPU execution, CPU/GPU compare, and measured acceleration.

## Validation

```sh
git diff --check
python3 -m unittest tests.contract.test_rtlmeter_verilator_command_capture -q
```

Result: passed on 2026-06-01.

## Resolution

- README troubleshooting now distinguishes RTLMeter pass-through metadata, fail-closed wrapper diagnostics, GPU execution, CPU/GPU compare, and measured acceleration.
- `docs/verilator_sidecar_option.md` now includes a RTLMeter user-path section that starts from RTLMeter commands rather than repo-specific launch templates.
- The docs explain `--compileArgs "--use-gpu"` and PATH wrapper usage without requiring RTLMeter source patches.
- The docs explicitly avoid claiming speedup from compile success or wrapper metadata.
