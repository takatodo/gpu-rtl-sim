"""Legacy representative command builders for results reproduction."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_io import display_path, report_path
from results_reproduction_types import ReproductionCommand


def report(repo_root: Path, path: str) -> Path:
    return report_path(path, repo_root=repo_root)


def host_probe_repeat_command(
    repo_root: Path,
    *,
    nstates: int,
    steps: int,
    state_out: Path,
) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "artifacts/pulp_ita_mha_obj_dir/tlul_slice_host_probe",
            "--repeat-states",
            str(nstates),
            "--repeat-eval-steps",
            str(steps),
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
        stdout=report(repo_root, f"pulp_ita_mha_cpu_repeat_{nstates}x{steps}.json"),
    )


def resident_hybrid_command(
    repo_root: Path,
    *,
    nstates: int,
    steps: int,
    state_out: Path,
) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "python3",
            "src/tools/run_vl_hybrid.py",
            "--mdir",
            "artifacts/pulp_ita_mha_obj_dir",
            "--nstates",
            str(nstates),
            "--steps",
            str(steps),
            "--resident-steps",
            "--init-state",
            "artifacts/pulp_ita_mha_obj_dir/pulp_ita_mha_cpu_repeat_1x1.bin",
            "--sanitize-host-only-internals",
            "--dump-state",
            display_path(state_out, repo_root=repo_root),
        ],
        stdout=report(repo_root, f"pulp_ita_mha_hybrid_{nstates}x{steps}_resident.txt"),
    )


def resident_compare_command(
    repo_root: Path,
    *,
    nstates: int,
    steps: int,
    cpu_state: Path,
    gpu_state: Path,
) -> ReproductionCommand:
    shape = f"{nstates}x{steps}"
    return ReproductionCommand(
        [
            "python3",
            "src/tools/compare_vl_hybrid_modes.py",
            "artifacts/pulp_ita_mha_obj_dir",
            "--compare-dumps",
            display_path(cpu_state, repo_root=repo_root),
            display_path(gpu_state, repo_root=repo_root),
            "--reference-label",
            f"cpu_repeat_{shape}",
            "--candidate-label",
            f"hybrid_resident_from_cpu_init_{shape}",
            "--acceptance-policy",
            "coverage_output_equivalence",
            "--json-out",
            f"reports/pulp_ita_mha_cpu_vs_hybrid_{shape}_resident_coverage_output_compare.json",
            "--coverage-output-gate",
            "config/scaling_gates/neural_network_rtl_full_ita_mha_first_hybrid_benchmark_gate.json",
            "--coverage-output-target",
            "pulp_ita_mha",
        ]
    )


def hybrid_template_command(*, template: str, shape: str) -> ReproductionCommand:
    return ReproductionCommand(
        [
            "python3",
            "src/tools/run_hybrid_template.py",
            template,
            "--shape",
            shape,
        ]
    )
