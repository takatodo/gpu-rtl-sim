from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HybridTemplatePlan:
    template_path: Path
    target: str
    target_name: str
    top_module: str
    mdir: Path
    host_probe_target: str
    source_gate: Path | None
    source_files: list[Path]
    verilator_defines: list[str]
    verilator_args: list[str]
    cpu_init_state: Path
    cpu_reference_state: Path
    gpu_candidate_state: Path
    cpu_init_report: Path
    cpu_report: Path
    hybrid_report: Path
    compare_report: Path
    nstates: int
    steps: int
    cfg_batch_length: int
    cfg_reset_cycles: int
    cfg_drain_cycles: int
    cfg_seed: int


def parse_shape(raw: str) -> tuple[int, int]:
    parts = raw.lower().split("x")
    if len(parts) != 2:
        raise ValueError("shape must be formatted as NxS, for example 64x1")
    nstates, steps = int(parts[0]), int(parts[1])
    if nstates <= 0 or steps <= 0:
        raise ValueError("shape values must be positive")
    return nstates, steps
