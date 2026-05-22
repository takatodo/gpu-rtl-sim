"""Phase execution helpers for persistent resident state ABI probes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from results_reproduction_persistent_probe_summary import report_path, summarize_phase
from results_reproduction_persistent_paths import state_abi_multiphase_command
from results_reproduction_types import MedianWorkload, ReproductionCommand


REPO_ROOT = Path(__file__).resolve().parents[2]
RunCommand = Callable[[ReproductionCommand], None]
CpuRepeatCommandFactory = Callable[..., ReproductionCommand]
CompareCommandFactory = Callable[..., ReproductionCommand]


def run_cpu_phases(
    *,
    workload: MedianWorkload,
    nstates: int,
    steps: int,
    phase_paths: list[dict[str, Path]],
    run_command: RunCommand,
    cpu_repeat_command: CpuRepeatCommandFactory,
) -> None:
    for phase, paths in enumerate(phase_paths, start=1):
        cumulative_steps = steps * phase
        phase_cpu_command = cpu_repeat_command(
            workload,
            state_out=paths["cpu_state"],
            report=paths["cpu_report"],
            nstates=nstates,
            steps=cumulative_steps,
        )
        run_command(phase_cpu_command)


def run_compare_phases(
    *,
    workload: MedianWorkload,
    nstates: int,
    steps: int,
    phase_paths: list[dict[str, Path]],
    hybrid_report: Path,
    dry_run: bool,
    run_command: RunCommand,
    compare_command: CompareCommandFactory,
) -> list[dict[str, object]]:
    phase_summaries: list[dict[str, object]] = []
    for phase, paths in enumerate(phase_paths, start=1):
        cumulative_steps = steps * phase
        phase_compare_command = compare_command(
            workload,
            phase=phase,
            cumulative_steps=cumulative_steps,
            cpu_state=paths["cpu_state"],
            gpu_state=paths["gpu_state"],
            report=paths["compare_report"],
        )
        run_command(phase_compare_command)
        if not dry_run:
            phase_summaries.append(
                summarize_phase(
                    paths=paths,
                    hybrid_report=hybrid_report,
                    nstates=nstates,
                    steps=steps,
                    phase=phase,
                )
            )
    return phase_summaries


def run_hybrid_multiphase(
    *,
    workload: MedianWorkload,
    phases: int,
    init_state: Path,
    phase_paths: list[dict[str, Path]],
    sample_tag: str | None,
    run_command: RunCommand,
) -> Path:
    tag = f"_{sample_tag}" if sample_tag else ""
    hybrid_report = report_path(
        f"pulp_ita_mha_{workload.nstates}x{workload.steps}_persistent_resident_state_abi{tag}_multiphase_hybrid.txt"
    )
    hybrid_command = state_abi_multiphase_command(
        REPO_ROOT,
        workload,
        phases=phases,
        cpu_init_state=init_state,
        gpu_states=[paths["gpu_state"] for paths in phase_paths],
        report_path_out=hybrid_report,
    )
    run_command(hybrid_command)
    return hybrid_report
