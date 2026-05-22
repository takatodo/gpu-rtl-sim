"""Public resident execution workflows for results reproduction."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_commands import cpu_repeat_command, hybrid_command
from results_reproduction_io import run_commands
from results_reproduction_median_core import run_init_state, run_workload_sample
from results_reproduction_resident_batch import run_resident_batch_sweep as _run_resident_batch_sweep_impl
from results_reproduction_resident_reuse import run_resident_state_reuse_experiment as _run_resident_state_reuse_impl
from results_reproduction_types import MedianWorkload, ReproductionCommand
from results_reproduction_workloads import mha_reuse_workload


REPO_ROOT = Path(__file__).resolve().parents[2]


def _cpu_repeat_command(
    workload: MedianWorkload,
    *,
    state_out: Path,
    report: Path,
    nstates: int | None = None,
    steps: int | None = None,
) -> ReproductionCommand:
    return cpu_repeat_command(
        REPO_ROOT,
        workload,
        state_out=state_out,
        report_path_out=report,
        nstates=nstates,
        steps=steps,
    )


def _hybrid_command(workload: MedianWorkload, *, cpu_init_state: Path, gpu_state: Path, report: Path) -> ReproductionCommand:
    return hybrid_command(
        REPO_ROOT,
        workload,
        cpu_init_state=cpu_init_state,
        gpu_state=gpu_state,
        report_path_out=report,
    )


def run_resident_batch_sweep(*, repeat_count: int, batch_states: list[int], dry_run: bool) -> list[dict[str, object]]:
    return _run_resident_batch_sweep_impl(
        repeat_count=repeat_count,
        batch_states=batch_states,
        dry_run=dry_run,
        run_init_state=lambda workload, tag, dry: run_init_state(workload, tag=tag, dry_run=dry),
        run_workload_sample=run_workload_sample,
    )


def run_resident_state_reuse_experiment(
    *,
    nstates: int,
    steps: int,
    phases: int,
    dry_run: bool,
) -> dict[str, object] | None:
    return _run_resident_state_reuse_impl(
        nstates=nstates,
        steps=steps,
        phases=phases,
        dry_run=dry_run,
        workload_factory=mha_reuse_workload,
        run_init_state=lambda workload, tag: run_init_state(workload, tag=tag, dry_run=dry_run),
        run_commands=lambda commands: run_commands(commands, repo_root=REPO_ROOT, dry_run=dry_run),
        cpu_repeat_command=_cpu_repeat_command,
        hybrid_command=_hybrid_command,
    )
