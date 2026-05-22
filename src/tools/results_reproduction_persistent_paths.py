"""Path and command builders for persistent resident reproduction flows."""

from pathlib import Path

from results_reproduction_io import display_path, report_path
from results_reproduction_types import MedianWorkload, ReproductionCommand


def mha_obj(repo_root: Path, path: str) -> Path:
    return repo_root / "artifacts" / "pulp_ita_mha_obj_dir" / path


def report(repo_root: Path, path: str) -> Path:
    return report_path(path, repo_root=repo_root)


def phase_report_paths(repo_root: Path, paths: dict[str, Path]) -> dict[str, str]:
    return {
        "cpu_report": display_path(paths["cpu_report"], repo_root=repo_root),
        "hybrid_report": display_path(paths["hybrid_report"], repo_root=repo_root),
        "compare_report": display_path(paths["compare_report"], repo_root=repo_root),
        "compare_stdout_report": display_path(
            paths["compare_report"].with_name(paths["compare_report"].stem + "_stdout.txt"),
            repo_root=repo_root,
        ),
    }


def state_abi_paths(
    repo_root: Path,
    *,
    nstates: int,
    steps: int,
    phase: int,
    sample_tag: str | None = None,
) -> dict[str, Path]:
    cumulative_steps = steps * phase
    tag = f"_{sample_tag}" if sample_tag else ""
    stem = f"pulp_ita_mha_{nstates}x{steps}_persistent_resident_state_abi{tag}_phase_{phase}"
    return {
        "cpu_state": mha_obj(repo_root, f"{stem}_cpu_{nstates}x{cumulative_steps}.bin"),
        "gpu_state": mha_obj(repo_root, f"{stem}_gpu_dump_{nstates}x{cumulative_steps}.bin"),
        "cpu_report": report(repo_root, f"{stem}_cpu_{nstates}x{cumulative_steps}.json"),
        "hybrid_report": report(repo_root, f"{stem}_hybrid_{nstates}x{cumulative_steps}.txt"),
        "compare_report": report(repo_root, f"{stem}_compare_{nstates}x{cumulative_steps}.json"),
    }


def state_abi_phase_args(repo_root: Path, workload: MedianWorkload, *, phase: int) -> list[str]:
    return [
        "python3",
        "src/tools/run_vl_hybrid.py",
        "--mdir",
        display_path(workload.obj_dir, repo_root=repo_root),
        "--nstates",
        str(workload.nstates),
        "--steps",
        str(workload.steps),
        "--resident-steps",
        "--persistent-resident-state-abi-handle",
        f"pulp_ita_mha_{workload.nstates}x{workload.steps}",
        "--persistent-resident-state-abi-phase",
        str(phase),
    ]


def state_abi_phase_command(
    repo_root: Path,
    workload: MedianWorkload,
    *,
    phase: int,
    cpu_init_state: Path,
    gpu_state: Path,
    report_path_out: Path,
) -> ReproductionCommand:
    command = state_abi_phase_args(repo_root, workload, phase=phase)
    if phase == 1:
        command.extend(
            [
                "--init-state",
                display_path(cpu_init_state, repo_root=repo_root),
                "--sanitize-host-only-internals",
            ]
        )
    command.extend(
        [
            "--dump-state",
            display_path(gpu_state, repo_root=repo_root),
        ]
    )
    return ReproductionCommand(command, stdout=report_path_out)


def state_abi_multiphase_command(
    repo_root: Path,
    workload: MedianWorkload,
    *,
    phases: int,
    cpu_init_state: Path,
    gpu_states: list[Path],
    report_path_out: Path,
) -> ReproductionCommand:
    return ReproductionCommand(
        [
            *state_abi_phase_args(repo_root, workload, phase=1),
            "--persistent-resident-state-abi-phases",
            str(phases),
            "--persistent-resident-state-abi-phase-dumps",
            ",".join(display_path(path, repo_root=repo_root) for path in gpu_states),
            "--init-state",
            display_path(cpu_init_state, repo_root=repo_root),
            "--sanitize-host-only-internals",
        ],
        stdout=report_path_out,
    )


def state_abi_phase_paths(
    repo_root: Path,
    *,
    nstates: int,
    steps: int,
    phases: int,
    sample_tag: str | None,
) -> list[dict[str, Path]]:
    return [
        state_abi_paths(
            repo_root,
            nstates=nstates,
            steps=steps,
            phase=phase,
            sample_tag=sample_tag,
        )
        for phase in range(1, phases + 1)
    ]
