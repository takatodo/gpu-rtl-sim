from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from results_reproduction_io import display_path, report_path, write_json
from results_reproduction_summaries import build_repeat_median_summary
from results_reproduction_types import MedianWorkload
from results_reproduction_workloads import resident_batch_sweep_workloads

REPO_ROOT = Path(__file__).resolve().parents[2]
InitStateRunner = Callable[[MedianWorkload, str, bool], Path]
WorkloadSampleRunner = Callable[..., dict[str, object] | None]


def _display_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def _report(path: str) -> Path:
    return report_path(path, repo_root=REPO_ROOT)


def parse_resident_batch_states(text: str) -> list[int]:
    values = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if value <= 0:
            raise ValueError("--resident-batch-sweep values must be positive")
        values.append(value)
    if not values:
        raise ValueError("--resident-batch-sweep requires at least one positive state count")
    return values


def parse_shape(text: str) -> tuple[int, int]:
    parts = text.lower().split("x")
    if len(parts) != 2:
        raise ValueError("shape must be formatted as NSTATESxSTEPS, for example 16x64")
    try:
        nstates = int(parts[0])
        steps = int(parts[1])
    except ValueError as exc:
        raise ValueError("shape must contain positive integer NSTATES and STEPS") from exc
    if nstates <= 0 or steps <= 0:
        raise ValueError("shape must contain positive integer NSTATES and STEPS")
    return nstates, steps


def run_resident_batch_sweep(
    *,
    repeat_count: int,
    batch_states: list[int],
    dry_run: bool,
    run_init_state: InitStateRunner,
    run_workload_sample: WorkloadSampleRunner,
) -> list[dict[str, object]]:
    if repeat_count <= 0:
        raise ValueError("--resident-batch-sweep-repeat must be positive")
    summaries: list[dict[str, object]] = []
    for workload in resident_batch_sweep_workloads(batch_states):
        cpu_init_state = run_init_state(workload, "resident_batch_sweep", dry_run)
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
        summary = build_repeat_median_summary(
            workload=workload,
            repeat_count=repeat_count,
            samples=samples,
            resident_mode=True,
        )
        path = _report(f"{workload.name}.json")
        write_json(path, summary)
        summaries.append({**summary, "report": _display_path(path)})
    if not dry_run:
        aggregate = {
            "schema_version": 1,
            "status": "measured_resident_batch_sweep",
            "repeat_count": repeat_count,
            "batch_states": batch_states,
            "reports": [entry["report"] for entry in summaries],
            "workloads": summaries,
        }
        write_json(_report("resident_batch_sweep_summary.json"), aggregate)
    return summaries
