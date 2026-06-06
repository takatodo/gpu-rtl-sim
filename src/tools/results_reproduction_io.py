"""I/O helpers for results reproduction workflows."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from results_reproduction_types import ReproductionCommand

LOCAL_ABSOLUTE_PATH_TOKEN_RE = re.compile(
    r"/(?:home|tmp|Users|var|mnt|workspace|root)/[^\s'\",;)]+"
)
GPU_TOTAL_RE = re.compile(r"gpu_kernel_time_ms:\s+total=([0-9.]+)\s+per_launch=([0-9.]+)")
GPU_PER_STATE_RE = re.compile(r"gpu_kernel_time:\s+per_state=([0-9.]+)\s+us")
WALL_RE = re.compile(r"wall_time_ms:\s+([0-9.]+)")


def display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root))
    except ValueError:
        return str(path)


def sanitize_local_absolute_paths(text: str) -> str:
    return LOCAL_ABSOLUTE_PATH_TOKEN_RE.sub("<local-absolute-path>", text)


def report_path(path: str, *, repo_root: Path) -> Path:
    return repo_root / "reports" / path


def json_report(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_hybrid_report(path: Path, *, repo_root: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    total_match = GPU_TOTAL_RE.search(text)
    per_state_match = GPU_PER_STATE_RE.search(text)
    wall_match = WALL_RE.search(text)
    if total_match is None or per_state_match is None or wall_match is None:
        raise ValueError(f"failed to parse hybrid timing report: {display_path(path, repo_root=repo_root)}")
    return {
        "gpu_kernel_total_ms": float(total_match.group(1)),
        "gpu_kernel_per_launch_ms": float(total_match.group(2)),
        "gpu_kernel_per_state_us": float(per_state_match.group(1)),
        "hybrid_wall_ms": float(wall_match.group(1)),
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def format_command(command: ReproductionCommand, *, repo_root: Path) -> str:
    rendered = " ".join(command.argv)
    if command.stdout is not None:
        rendered = f"{rendered} > {display_path(command.stdout, repo_root=repo_root)}"
    return sanitize_local_absolute_paths(rendered)


def run_command(command: ReproductionCommand, *, repo_root: Path, dry_run: bool) -> None:
    print("+ " + format_command(command, repo_root=repo_root))
    if dry_run:
        return
    if command.stdout is None:
        subprocess.run(command.argv, cwd=repo_root, check=True)
        return
    command.stdout.parent.mkdir(parents=True, exist_ok=True)
    with command.stdout.open("w", encoding="utf-8") as out:
        subprocess.run(command.argv, cwd=repo_root, check=True, stdout=out)


def run_commands(commands: list[ReproductionCommand], *, repo_root: Path, dry_run: bool) -> None:
    for command in commands:
        run_command(command, repo_root=repo_root, dry_run=dry_run)
