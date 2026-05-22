"""Shared value types for build_vl_gpu."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildContext:
    mdir: Path
    prefix: str
    all_classes: list[str]
    existing_meta: dict | None
    classifier_report: Path
    incremental_mode: str
    opt_marker: Path
    clang_changed: bool


@dataclass(frozen=True)
class BuildArtifacts:
    gpu_ptx: Path
    storage_size: int
    root_storage_size: int | None
    classifier_report: Path
    launch_sequence: list[str] | None
    gpu_ir_workarounds: list[str]


@dataclass(frozen=True)
class BuildRequest:
    sm: str
    out_cubin: Path | None
    force: bool
    clang_opt: str
    gpu_opt_level: str
    ptxas_opt_level: int | None
    emit_ptx_module: bool
    analyze_phases: bool
    kernel_split_phases: bool
    kernel_probe_act_sequent_chunk_size: int
    reuse_gpu_patched_ll: bool
    reuse_ptx: bool
    syms_state_image: bool
    syms_storage_size: int | None
    state_root_offset: int | None
    jobs: int
