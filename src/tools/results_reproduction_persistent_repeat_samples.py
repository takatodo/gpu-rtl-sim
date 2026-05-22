"""Sample annotation helpers for persistent resident repeat-median runs."""

from __future__ import annotations

from pathlib import Path

from results_reproduction_io import display_path, json_report, parse_hybrid_report, write_json


REPO_ROOT = Path(__file__).resolve().parents[2]


def _display_path(path: Path) -> str:
    return display_path(path, repo_root=REPO_ROOT)


def repeat_sample(
    *,
    sample_index: int,
    nstates: int,
    steps: int,
    phases: int,
    base_summary: object,
    base_summary_path: Path,
) -> dict[str, object]:
    if not isinstance(base_summary, dict):
        raise ValueError(f"persistent resident sample summary is not a JSON object: {_display_path(base_summary_path)}")
    hybrid_report = REPO_ROOT / str(base_summary["hybrid_report"])
    hybrid = parse_hybrid_report(hybrid_report, repo_root=REPO_ROOT)
    final_state_step_count = nstates * steps * phases
    wall_minus_kernel_residual_ms = hybrid["hybrid_wall_ms"] - hybrid["gpu_kernel_total_ms"]
    return {
        "sample_index": sample_index,
        "state_authority": base_summary["state_authority"],
        "phase_shapes": [phase["shape"] for phase in base_summary["phase_reports"]],
        "all_coverage_output_passed": base_summary["all_coverage_output_passed"],
        "max_coverage_output_mismatch_count": base_summary["max_coverage_output_mismatch_count"],
        "final_state_step_count": final_state_step_count,
        **hybrid,
        "wall_minus_kernel_residual_ms": wall_minus_kernel_residual_ms,
        "gpu_kernel_total_ms_per_final_state_step": hybrid["gpu_kernel_total_ms"] / final_state_step_count,
        "hybrid_wall_ms_per_final_state_step": hybrid["hybrid_wall_ms"] / final_state_step_count,
        "wall_minus_kernel_residual_ms_per_final_state_step": wall_minus_kernel_residual_ms / final_state_step_count,
        "source_summary_report": _display_path(base_summary_path),
        "hybrid_report": base_summary["hybrid_report"],
    }


def load_and_annotate_repeat_sample(
    *,
    sample_index: int,
    nstates: int,
    steps: int,
    phases: int,
    base_summary_path: Path,
) -> dict[str, object]:
    base_summary = json_report(base_summary_path)
    sample = repeat_sample(
        sample_index=sample_index,
        nstates=nstates,
        steps=steps,
        phases=phases,
        base_summary=base_summary,
        base_summary_path=base_summary_path,
    )
    base_summary["repeat_median_sample"] = sample
    write_json(base_summary_path, base_summary)
    return {**sample, "sample_report": _display_path(base_summary_path)}
