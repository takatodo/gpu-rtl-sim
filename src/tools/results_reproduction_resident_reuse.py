"""Resident state-reuse experiment helpers for results reproduction."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from results_reproduction_io import write_json
from results_reproduction_resident_reuse_commands import (
    _report,
    resident_state_reuse_compare_command,
    resident_state_reuse_paths,
    resident_state_reuse_phase_commands,
)
from results_reproduction_resident_reuse_summary import (
    resident_state_reuse_experiment_summary,
    resident_state_reuse_phase_summary,
)
from results_reproduction_types import MedianWorkload, ReproductionCommand

WorkloadFactory = Callable[..., MedianWorkload]
InitStateRunner = Callable[[MedianWorkload, str], Path]
RunCommands = Callable[[list[ReproductionCommand]], None]
CpuRepeatCommandFactory = Callable[..., ReproductionCommand]
HybridCommandFactory = Callable[..., ReproductionCommand]


def run_resident_state_reuse_phase(
    *,
    workload: MedianWorkload,
    nstates: int,
    steps: int,
    phase: int,
    previous_gpu_state: Path,
    dry_run: bool,
    run_commands: RunCommands,
    cpu_repeat_command: CpuRepeatCommandFactory,
    hybrid_command: HybridCommandFactory,
) -> tuple[Path, dict[str, object] | None]:
    cumulative_steps = steps * phase
    paths = resident_state_reuse_paths(nstates=nstates, steps=steps, phase=phase)
    run_commands(
        resident_state_reuse_phase_commands(
            workload=workload,
            nstates=nstates,
            cumulative_steps=cumulative_steps,
            phase=phase,
            previous_gpu_state=previous_gpu_state,
            paths=paths,
            cpu_repeat_command=cpu_repeat_command,
            hybrid_command=hybrid_command,
        )
    )
    if dry_run:
        return paths["gpu_state"], None
    return paths["gpu_state"], resident_state_reuse_phase_summary(
        phase=phase,
        nstates=nstates,
        steps=steps,
        cumulative_steps=cumulative_steps,
        paths=paths,
    )


def run_resident_state_reuse_experiment(
    *,
    nstates: int,
    steps: int,
    phases: int,
    dry_run: bool,
    workload_factory: WorkloadFactory,
    run_init_state: InitStateRunner,
    run_commands: RunCommands,
    cpu_repeat_command: CpuRepeatCommandFactory,
    hybrid_command: HybridCommandFactory,
) -> dict[str, object] | None:
    if phases <= 0:
        raise ValueError("--resident-state-reuse-phases must be positive")
    workload = workload_factory(nstates=nstates, steps=steps)
    init_state = run_init_state(workload, "resident_state_reuse")
    phase_summaries: list[dict[str, object]] = []
    previous_gpu_state = init_state
    for phase in range(1, phases + 1):
        previous_gpu_state, phase_summary = run_resident_state_reuse_phase(
            workload=workload,
            nstates=nstates,
            steps=steps,
            phase=phase,
            previous_gpu_state=previous_gpu_state,
            dry_run=dry_run,
            run_commands=run_commands,
            cpu_repeat_command=cpu_repeat_command,
            hybrid_command=hybrid_command,
        )
        if phase_summary is not None:
            phase_summaries.append(phase_summary)
    if dry_run:
        return None

    summary = resident_state_reuse_experiment_summary(
        workload=workload,
        nstates=nstates,
        steps=steps,
        phases=phases,
        phase_summaries=phase_summaries,
    )
    write_json(_report("resident_state_reuse_experiment_summary.json"), summary)
    return summary
