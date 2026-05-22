"""Shared value types for results reproduction workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReproductionCommand:
    argv: list[str]
    stdout: Path | None = None


@dataclass(frozen=True)
class MedianWorkload:
    name: str
    target_name: str
    obj_dir: Path
    nstates: int
    steps: int
    source_gate: str
    coverage_target: str
    resident: bool = False
    report_tag: str | None = None


@dataclass(frozen=True)
class PersistentResidentStateAbiProbeContext:
    workload: MedianWorkload
    init_state: Path
    phase_paths: list[dict[str, Path]]
