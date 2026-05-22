"""Persistent resident repeat-median summary helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from results_reproduction_io import display_path, write_json
from results_reproduction_summaries import persistent_resident_state_abi_repeat_summary
from results_reproduction_persistent_paths import report as _report_impl
from results_reproduction_persistent_repeat_samples import (
    load_and_annotate_repeat_sample,
    repeat_sample,
)
from results_reproduction_persistent_repeat_validation import validate_repeat_median_request

REPO_ROOT = Path(__file__).resolve().parents[2]


def _display_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def _report(path: str) -> Path:
    return _report_impl(REPO_ROOT, path)


def write_repeat_median_summary(
    *,
    nstates: int,
    steps: int,
    phases: int,
    repeat_count: int,
    source_gate: str,
    samples: list[dict[str, object]],
    summary_report: Path | None,
    dry_run: bool,
) -> dict[str, object] | None:
    output = summary_report or _report("persistent_resident_state_abi_repeat_median_summary.json")
    if dry_run:
        print(f"+ write {_display_path(output)}")
        return None

    summary = persistent_resident_state_abi_repeat_summary(
        nstates=nstates,
        steps=steps,
        phases=phases,
        repeat_count=repeat_count,
        source_gate=source_gate,
        samples=samples,
    )
    write_json(output, summary)
    return summary


def run_repeat_sample(
    *,
    sample_index: int,
    nstates: int,
    steps: int,
    phases: int,
    dry_run: bool,
    sample_report_prefix: str,
    sample_tag_prefix: str,
    run_probe_fn: Callable[..., None],
) -> dict[str, object] | None:
    sample_summary_report = _report(f"{sample_report_prefix}_{sample_index}.json")
    run_probe_fn(
        nstates=nstates,
        steps=steps,
        phases=phases,
        dry_run=dry_run,
        sample_tag=f"{sample_tag_prefix}_{sample_index}",
        summary_report=sample_summary_report,
    )
    if dry_run:
        return None

    return load_and_annotate_repeat_sample(
        sample_index=sample_index,
        nstates=nstates,
        steps=steps,
        phases=phases,
        base_summary_path=sample_summary_report,
    )


def run_repeat_samples(
    *,
    nstates: int,
    steps: int,
    phases: int,
    repeat_count: int,
    dry_run: bool,
    sample_report_prefix: str,
    sample_tag_prefix: str,
    run_probe_fn: Callable[..., None],
) -> list[dict[str, object]]:
    samples: list[dict[str, object]] = []
    for sample_index in range(1, repeat_count + 1):
        if dry_run:
            print(f"# persistent_resident_state_abi_repeat_median sample {sample_index}/{repeat_count}")
        sample = run_repeat_sample(
            sample_index=sample_index,
            nstates=nstates,
            steps=steps,
            phases=phases,
            dry_run=dry_run,
            sample_report_prefix=sample_report_prefix,
            sample_tag_prefix=sample_tag_prefix,
            run_probe_fn=run_probe_fn,
        )
        if sample is not None:
            samples.append(sample)
    return samples


def run_repeat_median(
    *,
    nstates: int,
    steps: int,
    phases: int,
    repeat_count: int,
    dry_run: bool,
    summary_report: Path | None,
    sample_report_prefix: str,
    sample_tag_prefix: str,
    source_gate: str,
    run_probe_fn: Callable[..., None],
) -> dict[str, object] | None:
    validate_repeat_median_request(repeat_count=repeat_count, phases=phases)

    samples = run_repeat_samples(
        nstates=nstates,
        steps=steps,
        phases=phases,
        repeat_count=repeat_count,
        dry_run=dry_run,
        sample_report_prefix=sample_report_prefix,
        sample_tag_prefix=sample_tag_prefix,
        run_probe_fn=run_probe_fn,
    )
    return write_repeat_median_summary(
        nstates=nstates,
        steps=steps,
        phases=phases,
        repeat_count=repeat_count,
        source_gate=source_gate,
        samples=samples,
        summary_report=summary_report,
        dry_run=dry_run,
    )
