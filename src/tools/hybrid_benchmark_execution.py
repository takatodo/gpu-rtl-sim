from __future__ import annotations

import subprocess

from results_reproduction import REPO_ROOT, ReproductionCommand, format_command


def run_benchmark_command(command: ReproductionCommand, *, dry_run: bool) -> None:
    print("+ " + format_command(command))
    if dry_run:
        return
    if command.stdout is None:
        subprocess.run(command.argv, cwd=REPO_ROOT, check=True)
        return
    command.stdout.parent.mkdir(parents=True, exist_ok=True)
    with command.stdout.open("w", encoding="utf-8") as out:
        subprocess.run(command.argv, cwd=REPO_ROOT, check=True, stdout=out)


def run_benchmark_commands(commands: list[ReproductionCommand], *, dry_run: bool) -> None:
    for command in commands:
        run_benchmark_command(command, dry_run=dry_run)
