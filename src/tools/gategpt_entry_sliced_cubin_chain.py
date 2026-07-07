#!/usr/bin/env python3
"""Compatibility wrapper for the frozen gateGPT entry-sliced CUBIN helper."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.diagnostics.frozen.gategpt_fc069_073.entry_sliced_cubin_chain import (  # noqa: E402
    DEFAULT_GPU_NAME,
    DEFAULT_OUT_DIR,
    DEFAULT_PTXAS_TIMEOUT_SECONDS,
    DEFAULT_REPORT,
    DEFAULT_SOURCE_PTX,
    SLICE_SPECS,
    main,
    parse_args,
    regenerate_chain,
)


__all__ = [
    "DEFAULT_GPU_NAME",
    "DEFAULT_OUT_DIR",
    "DEFAULT_PTXAS_TIMEOUT_SECONDS",
    "DEFAULT_REPORT",
    "DEFAULT_SOURCE_PTX",
    "SLICE_SPECS",
    "main",
    "parse_args",
    "regenerate_chain",
]


if __name__ == "__main__":
    raise SystemExit(main())
