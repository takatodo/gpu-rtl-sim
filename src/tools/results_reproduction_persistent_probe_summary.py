"""Summary helpers for persistent resident state ABI probe runs."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_io import display_path, json_report, write_json
from results_reproduction_persistent_paths import phase_report_paths, report
from results_reproduction_summaries import persistent_resident_state_abi_probe_summary
from results_reproduction_types import MedianWorkload


REPO_ROOT = Path(__file__).resolve().parents[2]


def display_repo_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def report_path(path: str) -> Path:
    return report(REPO_ROOT, path)


def summarize_phase(
    *,
    paths: dict[str, Path],
    hybrid_report: Path,
    nstates: int,
    steps: int,
    phase: int,
) -> dict[str, object]:
    cumulative_steps = steps * phase
    cpu = json_report(paths["cpu_report"])
    compare = json_report(paths["compare_report"])
    coverage = compare["coverage_output_policy"]
    return {
        "phase": phase,
        "shape": f"{nstates}x{cumulative_steps}",
        "phase_step_count": steps,
        "cumulative_step_count": cumulative_steps,
        "state_step_count": nstates * cumulative_steps,
        "cpu_elapsed_ms": cpu["elapsed_ms"],
        "coverage_output_passed": coverage["passed"],
        "coverage_output_mismatch_count": coverage["mismatch_count"],
        "reports": {
            **phase_report_paths(REPO_ROOT, paths),
            "hybrid_report": display_repo_path(hybrid_report),
        },
    }


def write_probe_summary(
    *,
    workload: MedianWorkload,
    nstates: int,
    steps: int,
    phases: int,
    hybrid_report: Path,
    phase_summaries: list[dict[str, object]],
    summary_report: Path | None,
    dry_run: bool,
) -> None:
    output = summary_report or report_path("persistent_resident_state_abi_probe_summary.json")
    if dry_run:
        print(f"+ write {display_repo_path(output)}")
        return

    summary = persistent_resident_state_abi_probe_summary(
        workload=workload,
        nstates=nstates,
        steps=steps,
        phases=phases,
        hybrid_report=display_repo_path(hybrid_report),
        phase_summaries=phase_summaries,
    )
    write_json(output, summary)
