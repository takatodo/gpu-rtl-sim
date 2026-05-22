"""Shared stage environment for build_vl_gpu stage wrappers."""

from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
PASSES_DIR = SCRIPT_DIR.parent / "passes"
PASSES_SO = PASSES_DIR / "VlGpuPasses.so"
VLGPUGEN = PASSES_DIR / "vlgpugen"


def run(cmd: list, **kwargs):
    print(" ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)
