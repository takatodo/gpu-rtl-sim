"""Public persistent-resident workflows for results reproduction."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_commands import cpu_repeat_command
from results_reproduction_io import run_command
from results_reproduction_median_core import run_init_state
from results_reproduction_persistent_resident import (
    run_probe as _run_persistent_resident_state_abi_probe_impl,
    run_repeat_median as _run_persistent_resident_state_abi_repeat_median_impl,
)
from results_reproduction_persistent_shape_phase import (
    run_shape_phase_sweep as _run_persistent_resident_state_abi_shape_phase_sweep_impl,
)
from results_reproduction_resident_reuse import resident_state_reuse_compare_command
from results_reproduction_summaries import PERSISTENT_RESIDENT_STATE_ABI_SHAPE_PHASE_SWEEP_CASES
from results_reproduction_workloads import mha_reuse_workload
from results_reproduction_types import MedianWorkload, ReproductionCommand


REPO_ROOT = Path(__file__).resolve().parents[2]


def _cpu_repeat_command(
    workload: MedianWorkload,
    *,
    state_out: Path,
    report: Path,
    nstates: int | None = None,
    steps: int | None = None,
) -> ReproductionCommand:
    return cpu_repeat_command(
        REPO_ROOT,
        workload,
        state_out=state_out,
        report_path_out=report,
        nstates=nstates,
        steps=steps,
    )


def run_persistent_resident_state_abi_probe(
    *,
    nstates: int,
    steps: int,
    phases: int,
    dry_run: bool,
    sample_tag: str | None = None,
    summary_report: Path | None = None,
) -> None:
    _run_persistent_resident_state_abi_probe_impl(
        nstates=nstates,
        steps=steps,
        phases=phases,
        dry_run=dry_run,
        sample_tag=sample_tag,
        summary_report=summary_report,
        workload_factory=mha_reuse_workload,
        run_init_state=lambda workload, tag: run_init_state(workload, tag=tag, dry_run=dry_run),
        run_command=lambda command: run_command(command, repo_root=REPO_ROOT, dry_run=dry_run),
        cpu_repeat_command=_cpu_repeat_command,
        compare_command=resident_state_reuse_compare_command,
    )


def run_persistent_resident_state_abi_repeat_median(
    *,
    nstates: int,
    steps: int,
    phases: int,
    repeat_count: int,
    dry_run: bool,
    summary_report: Path | None = None,
    sample_report_prefix: str = "persistent_resident_state_abi_repeat_median_sample",
    sample_tag_prefix: str = "repeat_median_sample",
    source_gate: str = "config/scaling_gates/persistent_resident_device_handle_storage_gate.json",
) -> dict[str, object] | None:
    return _run_persistent_resident_state_abi_repeat_median_impl(
        nstates=nstates,
        steps=steps,
        phases=phases,
        repeat_count=repeat_count,
        dry_run=dry_run,
        summary_report=summary_report,
        sample_report_prefix=sample_report_prefix,
        sample_tag_prefix=sample_tag_prefix,
        source_gate=source_gate,
        run_probe_fn=run_persistent_resident_state_abi_probe,
    )


def run_persistent_resident_state_abi_shape_phase_sweep(*, dry_run: bool) -> None:
    _run_persistent_resident_state_abi_shape_phase_sweep_impl(
        cases=PERSISTENT_RESIDENT_STATE_ABI_SHAPE_PHASE_SWEEP_CASES,
        dry_run=dry_run,
        run_repeat_median_fn=run_persistent_resident_state_abi_repeat_median,
    )
