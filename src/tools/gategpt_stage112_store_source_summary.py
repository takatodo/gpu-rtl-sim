#!/usr/bin/env python3
"""Compatibility wrapper for the frozen gateGPT Stage112 diagnostic helper."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.diagnostics.frozen.gategpt_fc069_073.stage112_store_source_summary import (  # noqa: E402
    STAGE112_EVENT_KEYS,
    STAGE112_ROW_RE,
    decode_stage112_control_word,
    main,
    parse_stage112_metadata,
    parse_stage112_runtime_events,
    summarize_stage112_store_sources,
)


__all__ = [
    "STAGE112_EVENT_KEYS",
    "STAGE112_ROW_RE",
    "decode_stage112_control_word",
    "main",
    "parse_stage112_metadata",
    "parse_stage112_runtime_events",
    "summarize_stage112_store_sources",
]


if __name__ == "__main__":
    raise SystemExit(main())
