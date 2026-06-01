# FC-001: README Goal And User Path

Status: done
Owner: Codex
Target file: `README.md`

## Objective

Keep the public README concise and oriented around a frontend-neutral GPU sidecar. Verilator is first; CIRCT is planned; JSON is debug/inspection only.

## Tasks

- Keep the normal user path terminal/operator first.
- Keep `verilator --use-gpu -f filelist.f --top-module top` as a future target, not a current broad support claim.
- Mention JSON only as debug/review/inspection output.
- Do not move long Codex memory back into README.

## Acceptance

- README does not describe JSON as runtime ABI or execution authority.
- README still includes the tested sidecar command examples.
- Unsupported paths are described as fail-closed.

## Validation

```sh
git diff --check
python3 src/tools/check_staged_large_files.py
```

## Resolution

- `README.md` frames the project as a frontend-neutral GPU sidecar with Verilator first and CIRCT planned.
- The `verilator --use-gpu -f filelist.f --top-module top` endpoint is documented as a long-term target, not current broad support.
- `--operator-plan-json` is documented as debug/inspection only, and unsupported paths are described as fail-closed.
