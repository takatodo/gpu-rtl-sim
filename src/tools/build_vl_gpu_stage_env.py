"""Shared stage environment for build_vl_gpu stage wrappers."""

from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
PASSES_DIR = SCRIPT_DIR.parent / "passes"
PASSES_SO = PASSES_DIR / "VlGpuPasses.so"
VLGPUGEN = PASSES_DIR / "vlgpugen"
PASS_TOOL_OUTPUTS = (PASSES_SO, VLGPUGEN)


def run(cmd: list, **kwargs):
    print(" ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def ensure_pass_tools_built(*, run_command=run) -> None:
    missing = [path for path in PASS_TOOL_OUTPUTS if not path.is_file()]
    if not missing:
        return
    names = ", ".join(path.name for path in missing)
    print(f"  [make] building missing GPU pass tools: {names}", flush=True)
    run_command(["make", "-C", str(PASSES_DIR), "--no-print-directory"])
