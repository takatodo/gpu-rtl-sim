"""Shared stage environment for build_vl_gpu stage wrappers."""

from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PASSES_DIR = SCRIPT_DIR.parent / "passes"
PASS_TOOL_DIR = REPO_ROOT / "artifacts" / "tool_bins" / "passes"
PASSES_SO = PASS_TOOL_DIR / "VlGpuPasses.so"
VLGPUGEN = PASS_TOOL_DIR / "vlgpugen"
PASS_TOOL_OUTPUTS = (PASSES_SO, VLGPUGEN)
PASS_TOOL_SOURCE_GLOBS = ("*.cpp", "*.h", "Makefile")


def run(cmd: list, **kwargs):
    print(" ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def _latest_pass_tool_source_mtime() -> float | None:
    mtimes: list[float] = []
    for pattern in PASS_TOOL_SOURCE_GLOBS:
        for path in PASSES_DIR.glob(pattern):
            if path.is_file():
                mtimes.append(path.stat().st_mtime)
    return max(mtimes) if mtimes else None


def ensure_pass_tools_built(*, run_command=run) -> None:
    missing = [path for path in PASS_TOOL_OUTPUTS if not path.is_file()]
    latest_source_mtime = _latest_pass_tool_source_mtime()
    stale = []
    if latest_source_mtime is not None:
        stale = [
            path
            for path in PASS_TOOL_OUTPUTS
            if path.is_file() and path.stat().st_mtime < latest_source_mtime
        ]
    if not missing and not stale:
        return
    names = ", ".join(path.name for path in [*missing, *stale])
    reason = "missing/stale" if missing and stale else "missing" if missing else "stale"
    print(f"  [make] building {reason} GPU pass tools: {names}", flush=True)
    run_command(["make", "-C", str(PASSES_DIR), "--no-print-directory"])
