from __future__ import annotations

from pathlib import Path

from results_reproduction_io import report_path
from results_reproduction_types import MedianWorkload


def report(repo_root: Path, path: str) -> Path:
    return report_path(path, repo_root=repo_root)


def sample_paths(repo_root: Path, workload: MedianWorkload, sample_index: int) -> dict[str, Path]:
    shape = f"{workload.nstates}x{workload.steps}"
    suffix = "_resident" if workload.resident else ""
    if workload.report_tag is None:
        stem = f"{workload.target_name}_{shape}{suffix}_median_sample_{sample_index}"
    else:
        stem = f"{workload.report_tag}_median_sample_{sample_index}"
    return {
        "cpu_state": workload.obj_dir / f"{stem}_cpu.bin",
        "gpu_state": workload.obj_dir / f"{stem}_gpu.bin",
        "cpu_report": report(repo_root, f"{stem}_cpu.json"),
        "hybrid_report": report(repo_root, f"{stem}_hybrid.txt"),
        "compare_report": report(repo_root, f"{stem}_compare.json"),
        "compare_stdout_report": report(repo_root, f"{stem}_compare_stdout.txt"),
    }


def init_state_paths(repo_root: Path, workload: MedianWorkload, *, tag: str) -> dict[str, Path]:
    stem = workload.report_tag or workload.target_name
    return {
        "state": workload.obj_dir / f"{stem}_cpu_repeat_1x1.bin",
        "report": report(repo_root, f"{stem}_{tag}_init_1x1_cpu.json"),
    }
