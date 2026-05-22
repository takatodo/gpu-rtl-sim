from __future__ import annotations

from pathlib import Path

from results_reproduction_commands import (
    host_probe_repeat_command,
    hybrid_template_command,
    mha_obj,
    resident_compare_command,
    resident_hybrid_command,
)
from results_reproduction_io import run_commands
from results_reproduction_manifest import PUBLIC_PACK_ARCHIVE_PATHS
from results_reproduction_types import ReproductionCommand


def reproduction_plan(repo_root: Path) -> list[ReproductionCommand]:
    commands = [
        hybrid_template_command(template="config/slice_launch_templates/pulp_ita_mha.json", shape="64x1"),
        hybrid_template_command(template="config/slice_launch_templates/pulp_ita_mha.json", shape="1x64"),
    ]
    for nstates in (1, 32):
        steps = 64
        cpu_state = mha_obj(repo_root, f"pulp_ita_mha_cpu_repeat_{nstates}x{steps}.bin")
        gpu_state = mha_obj(repo_root, f"pulp_ita_mha_gpu_from_cpu_init_{nstates}x{steps}_resident.bin")
        if nstates != 1:
            commands.append(
                host_probe_repeat_command(
                    repo_root,
                    nstates=nstates,
                    steps=steps,
                    state_out=cpu_state,
                )
            )
        commands.append(
            resident_hybrid_command(
                repo_root,
                nstates=nstates,
                steps=steps,
                state_out=gpu_state,
            )
        )
        commands.append(
            resident_compare_command(
                repo_root,
                nstates=nstates,
                steps=steps,
                cpu_state=cpu_state,
                gpu_state=gpu_state,
            )
        )
    commands.append(
        hybrid_template_command(
            template="config/slice_launch_templates/pulp_paged_attention_kv_score.json",
            shape="64x1",
        )
    )
    return commands


def run_reproduction_plan(repo_root: Path, *, dry_run: bool) -> None:
    run_commands(reproduction_plan(repo_root), repo_root=repo_root, dry_run=dry_run)


def run_public_pack_archive_plan(*, dry_run: bool) -> None:
    if not dry_run:
        raise ValueError("public pack archive planning is dry-run only; do not create archive outputs as source of truth")
    print("# public_pack_archive_ready")
    print("# dry-run only: no archive is created")
    print("# include:")
    for path in PUBLIC_PACK_ARCHIVE_PATHS:
        print(f"include: {path}")
    print("# exclude:")
    print("exclude: artifacts/")
    print("exclude: reports/* except listed evidence snapshots")
    print("# archive command is intentionally not executed")
    print("tar -czf <generated-output>/public-benchmark-pack.tgz <listed paths>")
