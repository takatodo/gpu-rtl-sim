"""Persistent resident state ABI probe orchestration."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from results_reproduction_persistent_probe_summary import (
    write_probe_summary,
)
from results_reproduction_persistent_paths import state_abi_phase_paths
from results_reproduction_persistent_probe_phases import (
    run_compare_phases,
    run_cpu_phases,
    run_hybrid_multiphase,
)
from results_reproduction_types import MedianWorkload, ReproductionCommand


REPO_ROOT = Path(__file__).resolve().parents[2]
ProbeContextParts = tuple[MedianWorkload, Path, list[dict[str, Path]]]
RunCommand = Callable[[ReproductionCommand], None]
CpuRepeatCommandFactory = Callable[..., ReproductionCommand]
CompareCommandFactory = Callable[..., ReproductionCommand]
InitStateRunner = Callable[[MedianWorkload, str], Path]
WorkloadFactory = Callable[..., MedianWorkload]


def probe_context(
    *,
    nstates: int,
    steps: int,
    phases: int,
    sample_tag: str | None,
    workload_factory: WorkloadFactory,
    run_init_state: InitStateRunner,
) -> ProbeContextParts:
    if phases <= 0:
        raise ValueError("--persistent-resident-state-abi-phases must be positive")

    workload = workload_factory(nstates=nstates, steps=steps)
    init_tag = "persistent_resident_state_abi" + (f"_{sample_tag}" if sample_tag else "")
    init_state = run_init_state(workload, init_tag)
    phase_paths = state_abi_phase_paths(
        REPO_ROOT,
        nstates=nstates,
        steps=steps,
        phases=phases,
        sample_tag=sample_tag,
    )
    return workload, init_state, phase_paths


def run_probe(
    *,
    nstates: int,
    steps: int,
    phases: int,
    dry_run: bool,
    sample_tag: str | None,
    summary_report: Path | None,
    workload_factory: WorkloadFactory,
    run_init_state: InitStateRunner,
    run_command: RunCommand,
    cpu_repeat_command: CpuRepeatCommandFactory,
    compare_command: CompareCommandFactory,
) -> None:
    workload, init_state, phase_paths = probe_context(
        nstates=nstates,
        steps=steps,
        phases=phases,
        sample_tag=sample_tag,
        workload_factory=workload_factory,
        run_init_state=run_init_state,
    )
    run_cpu_phases(
        workload=workload,
        nstates=nstates,
        steps=steps,
        phase_paths=phase_paths,
        run_command=run_command,
        cpu_repeat_command=cpu_repeat_command,
    )
    hybrid_report = run_hybrid_multiphase(
        workload=workload,
        phases=phases,
        init_state=init_state,
        phase_paths=phase_paths,
        sample_tag=sample_tag,
        run_command=run_command,
    )
    phase_summaries = run_compare_phases(
        workload=workload,
        nstates=nstates,
        steps=steps,
        phase_paths=phase_paths,
        hybrid_report=hybrid_report,
        dry_run=dry_run,
        run_command=run_command,
        compare_command=compare_command,
    )
    write_probe_summary(
        workload=workload,
        nstates=nstates,
        steps=steps,
        phases=phases,
        hybrid_report=hybrid_report,
        phase_summaries=phase_summaries,
        summary_report=summary_report,
        dry_run=dry_run,
    )
