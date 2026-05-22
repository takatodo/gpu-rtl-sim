from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from results_reproduction_io import display_path, report_path, write_json
from results_reproduction_summaries import persistent_resident_state_abi_shape_phase_aggregate

REPO_ROOT = Path(__file__).resolve().parents[2]


def _display_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def _report(path: str) -> Path:
    return report_path(path, repo_root=REPO_ROOT)


def shape_phase_case_summary(
    *,
    case_id: str,
    summary: dict[str, object],
    case_summary_report: Path,
) -> dict[str, object]:
    samples = summary["samples"]
    if not isinstance(samples, list) or not samples:
        raise ValueError(f"shape-phase case summary has no samples: {case_id}")
    first_sample = samples[0]
    if not isinstance(first_sample, dict):
        raise ValueError(f"shape-phase first sample is not an object: {case_id}")
    return {
        "case_id": case_id,
        "shape": summary["shape"],
        "phases": summary["phases"],
        "repeat_count": summary["repeat_count"],
        "acceptance_policy": summary["acceptance_policy"],
        "state_authority": summary["state_authority"],
        "all_coverage_output_passed": summary["all_coverage_output_passed"],
        "max_coverage_output_mismatch_count": summary["max_coverage_output_mismatch_count"],
        "final_state_step_count": first_sample["final_state_step_count"],
        "phase_shapes": first_sample["phase_shapes"],
        "metrics": summary["metrics"],
        "case_summary_report": _display_path(case_summary_report),
        "sample_reports": summary["sample_reports"],
    }


def run_shape_phase_case(
    *,
    case: dict[str, object],
    source_gate: str,
    dry_run: bool,
    run_repeat_median_fn: Callable[..., dict[str, object] | None],
) -> dict[str, object] | None:
    case_id = str(case["case_id"])
    nstates = int(case["nstates"])
    steps = int(case["steps"])
    phases = int(case["phases"])
    repeat_count = int(case["repeat_count"])
    per_case_summary_report = _report(f"persistent_resident_state_abi_shape_phase_sweep_{case_id}.json")
    if dry_run:
        print(f"# persistent_resident_state_abi_shape_phase_sweep {case_id}")
    summary = run_repeat_median_fn(
        nstates=nstates,
        steps=steps,
        phases=phases,
        repeat_count=repeat_count,
        dry_run=dry_run,
        summary_report=per_case_summary_report,
        sample_report_prefix=f"persistent_resident_state_abi_shape_phase_sweep_{case_id}_sample",
        sample_tag_prefix=f"shape_phase_sweep_{case_id}_sample",
        source_gate=source_gate,
    )
    if summary is None:
        return None
    return shape_phase_case_summary(
        case_id=case_id,
        summary=summary,
        case_summary_report=per_case_summary_report,
    )


def run_shape_phase_sweep(
    *,
    cases: tuple[dict[str, object], ...],
    dry_run: bool,
    run_repeat_median_fn: Callable[..., dict[str, object] | None],
) -> None:
    case_summaries: list[dict[str, object]] = []
    source_gate = "config/scaling_gates/persistent_resident_state_abi_shape_phase_sweep_gate.json"
    aggregate_summary_report = _report("persistent_resident_state_abi_shape_phase_sweep_summary.json")

    for case in cases:
        case_summary = run_shape_phase_case(
            case=case,
            source_gate=source_gate,
            dry_run=dry_run,
            run_repeat_median_fn=run_repeat_median_fn,
        )
        if case_summary is not None:
            case_summaries.append(case_summary)

    if dry_run:
        print(f"+ write {_display_path(aggregate_summary_report)}")
        return

    aggregate = persistent_resident_state_abi_shape_phase_aggregate(
        source_gate=source_gate,
        case_summaries=case_summaries,
    )
    write_json(aggregate_summary_report, aggregate)
