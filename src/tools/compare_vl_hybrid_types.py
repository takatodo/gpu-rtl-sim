"""Shared value types for compare_vl_hybrid_modes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FreshRunArtifacts:
    single_path: Path
    split_path: Path
    single_dump: Path
    split_dump: Path
    storage_size: int
    layout: list[dict[str, int | str]]
