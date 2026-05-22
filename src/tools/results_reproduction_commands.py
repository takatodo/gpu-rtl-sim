"""Command and path builders for results reproduction workflows."""

from pathlib import Path

from results_reproduction_io import display_path, report_path
from results_reproduction_legacy_commands import (
    host_probe_repeat_command,
    hybrid_template_command,
    resident_compare_command,
    resident_hybrid_command,
)
from results_reproduction_sample_paths import (
    init_state_paths,
    sample_paths,
)
from results_reproduction_types import MedianWorkload, ReproductionCommand


def median_workload_stem(workload: MedianWorkload) -> str:
    return workload.report_tag or workload.name


def mha_obj(repo_root: Path, path: str) -> Path:
    return repo_root / "artifacts" / "pulp_ita_mha_obj_dir" / path


def report(repo_root: Path, path: str) -> Path:
    return report_path(path, repo_root=repo_root)


def cpu_repeat_command(
    repo_root: Path,
    workload: MedianWorkload,
    *,
    state_out: Path,
    report_path_out: Path,
    nstates: int | None = None,
    steps: int | None = None,
) -> ReproductionCommand:
    return ReproductionCommand(
        [
            display_path(workload.obj_dir / "tlul_slice_host_probe", repo_root=repo_root),
            "--repeat-states",
            str(workload.nstates if nstates is None else nstates),
            "--repeat-eval-steps",
            str(workload.steps if steps is None else steps),
            "--set",
            "cfg_valid_i=1",
            "--set",
            "cfg_batch_length_i=64",
            "--set",
            "cfg_reset_cycles_i=2",
            "--set",
            "cfg_drain_cycles_i=8",
            "--set",
            "cfg_seed_i=1",
            "--repeat-state-out",
            display_path(state_out, repo_root=repo_root),
        ],
        stdout=report_path_out,
    )


def hybrid_command(
    repo_root: Path,
    workload: MedianWorkload,
    *,
    cpu_init_state: Path,
    gpu_state: Path,
    report_path_out: Path,
) -> ReproductionCommand:
    command = [
        "python3",
        "src/tools/run_vl_hybrid.py",
        "--mdir",
        display_path(workload.obj_dir, repo_root=repo_root),
        "--nstates",
        str(workload.nstates),
        "--steps",
        str(workload.steps),
    ]
    if workload.resident:
        command.append("--resident-steps")
    command.extend(
        [
            "--init-state",
            display_path(cpu_init_state, repo_root=repo_root),
            "--sanitize-host-only-internals",
            "--dump-state",
            display_path(gpu_state, repo_root=repo_root),
        ]
    )
    return ReproductionCommand(command, stdout=report_path_out)


def compare_command(
    repo_root: Path,
    workload: MedianWorkload,
    *,
    cpu_state: Path,
    gpu_state: Path,
    report_path_out: Path,
) -> ReproductionCommand:
    shape = f"{workload.nstates}x{workload.steps}"
    suffix = "_resident" if workload.resident else ""
    stdout = report_path_out.with_name(report_path_out.stem + "_stdout.txt")
    return ReproductionCommand(
        [
            "python3",
            "src/tools/compare_vl_hybrid_modes.py",
            display_path(workload.obj_dir, repo_root=repo_root),
            "--compare-dumps",
            display_path(cpu_state, repo_root=repo_root),
            display_path(gpu_state, repo_root=repo_root),
            "--reference-label",
            f"cpu_repeat_{shape}",
            "--candidate-label",
            f"hybrid{suffix}_from_cpu_init_{shape}",
            "--acceptance-policy",
            "coverage_output_equivalence",
            "--json-out",
            display_path(report_path_out, repo_root=repo_root),
            "--coverage-output-gate",
            workload.source_gate,
            "--coverage-output-target",
            workload.coverage_target,
        ],
        stdout=stdout,
    )

