#!/usr/bin/env python3
"""Compatibility facade for the frozen gateGPT testbench probe."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
for _path in (REPO_ROOT, TOOLS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Keep the frozen implementation's historical active-tool dependency closure
# visible to the tracked-surface guard without executing these imports here.
if False:  # pragma: no cover
    import compare_vl_hybrid_root_layout
    import gategpt_entry_sliced_cubin_chain
    import gategpt_schedule_planner

from src.diagnostics.frozen.gategpt import testbench_probe as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl


if __name__ == "__main__":
    raise SystemExit(_impl.main())
