"""Command construction for resident state-reuse reproduction."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_io import display_path, report_path
from results_reproduction_types import MedianWorkload, ReproductionCommand

REPO_ROOT = Path(__file__).resolve().parents[2]


def _display_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def _mha_obj(path: str) -> Path:
    return REPO_ROOT / "artifacts" / "pulp_ita_mha_obj_dir" / path


def _report(path: str) -> Path:
    return report_path(path, repo_root=REPO_ROOT)


def resident_state_reuse_paths(*, nstates: int, steps: int, phase: int) -> dict[str, Path]:
    cumulative_steps = steps * phase
    stem = f"pulp_ita_mha_{nstates}x{steps}_resident_state_reuse_phase_{phase}"
    return {
        "cpu_state": _mha_obj(f"{stem}_cpu_{nstates}x{cumulative_steps}.bin"),
        "gpu_state": _mha_obj(f"{stem}_gpu_{nstates}x{cumulative_steps}.bin"),
        "cpu_report": _report(f"{stem}_cpu_{nstates}x{cumulative_steps}.json"),
        "hybrid_report": _report(f"{stem}_hybrid_{nstates}x{cumulative_steps}.txt"),
        "compare_report": _report(f"{stem}_compare_{nstates}x{cumulative_steps}.json"),
    }


def resident_state_reuse_compare_command(
    workload: MedianWorkload,
    *,
    phase: int,
    cumulative_steps: int,
    cpu_state: Path,
    gpu_state: Path,
    report: Path,
) -> ReproductionCommand:
    stdout = report.with_name(report.stem + "_stdout.txt")
    return ReproductionCommand(
        [
            "python3",
            "src/tools/compare_vl_hybrid_modes.py",
            _display_path(workload.obj_dir),
            "--compare-dumps",
            _display_path(cpu_state),
            _display_path(gpu_state),
            "--reference-label",
            f"cpu_repeat_{workload.nstates}x{cumulative_steps}",
            "--candidate-label",
            f"hybrid_resident_state_reuse_phase_{phase}_{workload.nstates}x{cumulative_steps}",
            "--acceptance-policy",
            "coverage_output_equivalence",
            "--json-out",
            _display_path(report),
            "--coverage-output-gate",
            workload.source_gate,
            "--coverage-output-target",
            workload.coverage_target,
        ],
        stdout=stdout,
    )


def resident_state_reuse_phase_commands(
    *,
    workload: MedianWorkload,
    nstates: int,
    cumulative_steps: int,
    phase: int,
    previous_gpu_state: Path,
    paths: dict[str, Path],
    cpu_repeat_command,
    hybrid_command,
) -> list[ReproductionCommand]:
    return [
        cpu_repeat_command(
            workload,
            state_out=paths["cpu_state"],
            report=paths["cpu_report"],
            nstates=nstates,
            steps=cumulative_steps,
        ),
        hybrid_command(
            workload,
            cpu_init_state=previous_gpu_state,
            gpu_state=paths["gpu_state"],
            report=paths["hybrid_report"],
        ),
        resident_state_reuse_compare_command(
            workload,
            phase=phase,
            cumulative_steps=cumulative_steps,
            cpu_state=paths["cpu_state"],
            gpu_state=paths["gpu_state"],
            report=paths["compare_report"],
        ),
    ]
