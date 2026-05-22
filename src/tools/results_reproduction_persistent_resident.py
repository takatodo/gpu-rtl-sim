"""Persistent resident state ABI helpers for results reproduction."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_io import display_path, parse_hybrid_report
from results_reproduction_persistent_paths import (
    phase_report_paths as _phase_report_paths_impl,
    report as _report_impl,
    state_abi_multiphase_command as _state_abi_multiphase_command_impl,
    state_abi_paths as _state_abi_paths_impl,
    state_abi_phase_args as _state_abi_phase_args_impl,
    state_abi_phase_command as _state_abi_phase_command_impl,
    state_abi_phase_paths as _state_abi_phase_paths_impl,
)
from results_reproduction_persistent_probe import (
    probe_context,
    run_probe,
)
from results_reproduction_persistent_probe_phases import (
    run_compare_phases,
    run_cpu_phases,
    run_hybrid_multiphase,
)
from results_reproduction_persistent_probe_summary import (
    summarize_phase,
    write_probe_summary,
)
from results_reproduction_persistent_repeat import (
    load_and_annotate_repeat_sample,
    repeat_sample,
    run_repeat_median,
    run_repeat_sample,
    run_repeat_samples,
    write_repeat_median_summary,
)
from results_reproduction_types import MedianWorkload, ReproductionCommand

REPO_ROOT = Path(__file__).resolve().parents[2]


def _display_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def _report(path: str) -> Path:
    return _report_impl(REPO_ROOT, path)


def phase_report_paths(paths: dict[str, Path]) -> dict[str, str]:
    return _phase_report_paths_impl(REPO_ROOT, paths)


def state_abi_paths(
    *,
    nstates: int,
    steps: int,
    phase: int,
    sample_tag: str | None = None,
) -> dict[str, Path]:
    return _state_abi_paths_impl(
        REPO_ROOT,
        nstates=nstates,
        steps=steps,
        phase=phase,
        sample_tag=sample_tag,
    )


def state_abi_phase_args(workload: MedianWorkload, *, phase: int) -> list[str]:
    return _state_abi_phase_args_impl(REPO_ROOT, workload, phase=phase)


def state_abi_phase_command(
    workload: MedianWorkload,
    *,
    phase: int,
    cpu_init_state: Path,
    gpu_state: Path,
    report: Path,
) -> ReproductionCommand:
    return _state_abi_phase_command_impl(
        REPO_ROOT,
        workload,
        phase=phase,
        cpu_init_state=cpu_init_state,
        gpu_state=gpu_state,
        report_path_out=report,
    )


def state_abi_multiphase_command(
    workload: MedianWorkload,
    *,
    phases: int,
    cpu_init_state: Path,
    gpu_states: list[Path],
    report: Path,
) -> ReproductionCommand:
    return _state_abi_multiphase_command_impl(
        REPO_ROOT,
        workload,
        phases=phases,
        cpu_init_state=cpu_init_state,
        gpu_states=gpu_states,
        report_path_out=report,
    )


def state_abi_phase_summary(
    *,
    paths: dict[str, Path],
    hybrid_report: Path,
    nstates: int,
    steps: int,
    phase: int,
) -> dict[str, object]:
    return summarize_phase(
        paths=paths,
        hybrid_report=hybrid_report,
        nstates=nstates,
        steps=steps,
        phase=phase,
    )


def state_abi_phase_paths(
    *,
    nstates: int,
    steps: int,
    phases: int,
    sample_tag: str | None,
) -> list[dict[str, Path]]:
    return _state_abi_phase_paths_impl(
        REPO_ROOT,
        nstates=nstates,
        steps=steps,
        phases=phases,
        sample_tag=sample_tag,
    )
