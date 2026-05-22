"""Core repeat-median execution for results reproduction workflows."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_commands import (
    compare_command,
    cpu_repeat_command,
    hybrid_command,
    init_state_paths as init_state_paths_impl,
    median_workload_stem,
    report as report_impl,
    sample_paths as sample_paths_impl,
)
from results_reproduction_io import (
    display_path,
    json_report,
    parse_hybrid_report,
    run_command,
    write_json,
)
from results_reproduction_summaries import build_repeat_median_summary
from results_reproduction_types import MedianWorkload


REPO_ROOT = Path(__file__).resolve().parents[2]


def report(path: str) -> Path:
    return report_impl(REPO_ROOT, path)


def median_report_path(workload: MedianWorkload) -> Path:
    return report(f"{median_workload_stem(workload)}_median.json")


def sample_paths(workload: MedianWorkload, sample_index: int) -> dict[str, Path]:
    return sample_paths_impl(REPO_ROOT, workload, sample_index)


def init_state_paths(workload: MedianWorkload, *, tag: str) -> dict[str, Path]:
    return init_state_paths_impl(REPO_ROOT, workload, tag=tag)


def run_init_state(workload: MedianWorkload, *, tag: str, dry_run: bool) -> Path:
    paths = init_state_paths(workload, tag=tag)
    run_command(
        cpu_repeat_command(REPO_ROOT, workload, state_out=paths["state"], report_path_out=paths["report"], nstates=1, steps=1),
        repo_root=REPO_ROOT,
        dry_run=dry_run,
    )
    return paths["state"]


def run_workload_sample(
    workload: MedianWorkload,
    *,
    sample_index: int,
    cpu_init_state: Path,
    dry_run: bool,
) -> dict[str, object] | None:
    paths = sample_paths(workload, sample_index)
    commands = [
        cpu_repeat_command(REPO_ROOT, workload, state_out=paths["cpu_state"], report_path_out=paths["cpu_report"]),
        hybrid_command(REPO_ROOT, workload, cpu_init_state=cpu_init_state, gpu_state=paths["gpu_state"], report_path_out=paths["hybrid_report"]),
        compare_command(REPO_ROOT, workload, cpu_state=paths["cpu_state"], gpu_state=paths["gpu_state"], report_path_out=paths["compare_report"]),
    ]
    for command in commands:
        run_command(command, repo_root=REPO_ROOT, dry_run=dry_run)
    if dry_run:
        return None

    cpu = json_report(paths["cpu_report"])
    compare = json_report(paths["compare_report"])
    coverage = compare["coverage_output_policy"]
    hybrid = parse_hybrid_report(paths["hybrid_report"], repo_root=REPO_ROOT)
    state_step_count = workload.nstates * workload.steps
    return {
        "sample_index": sample_index,
        "state_step_count": state_step_count,
        "cpu_elapsed_ms": cpu["elapsed_ms"],
        "cpu_state_steps_per_second": cpu.get("state_steps_per_second"),
        **hybrid,
        "gpu_kernel_total_ms_per_state_step": hybrid["gpu_kernel_total_ms"] / state_step_count,
        "hybrid_wall_ms_per_state_step": hybrid["hybrid_wall_ms"] / state_step_count,
        "coverage_output_passed": coverage["passed"],
        "coverage_output_mismatch_count": coverage["mismatch_count"],
        "compared_state_pair_count": coverage["compared_state_pair_count"],
        "reports": {key: display_path(value, repo_root=REPO_ROOT) for key, value in paths.items() if key.endswith("_report")},
    }


def run_median_workload_set(
    *,
    repeat_count: int,
    dry_run: bool,
    workloads: list[MedianWorkload],
    aggregate_status: str,
    aggregate_report: str,
) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for workload in workloads:
        cpu_init_state = run_init_state(workload, tag="median", dry_run=dry_run)
        samples = []
        for sample_index in range(1, repeat_count + 1):
            sample = run_workload_sample(
                workload,
                sample_index=sample_index,
                cpu_init_state=cpu_init_state,
                dry_run=dry_run,
            )
            if sample is not None:
                samples.append(sample)
        if dry_run:
            continue
        summary = build_repeat_median_summary(workload=workload, repeat_count=repeat_count, samples=samples)
        path = median_report_path(workload)
        write_json(path, summary)
        summaries.append({**summary, "report": display_path(path, repo_root=REPO_ROOT)})
    if dry_run:
        print(f"+ write {display_path(report(aggregate_report), repo_root=REPO_ROOT)}")
    else:
        aggregate = {
            "schema_version": 1,
            "status": aggregate_status,
            "repeat_count": repeat_count,
            "reports": [entry["report"] for entry in summaries],
            "workloads": summaries,
        }
        write_json(report(aggregate_report), aggregate)
    return summaries
