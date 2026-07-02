"""Repeat a slice-launch hybrid template and summarize median timing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Callable

from hybrid_template_runner import load_template_plan, run_plan, validate_source_closure_for_execution
from hybrid_template_types import HybridTemplatePlan
from results_reproduction_io import display_path, parse_hybrid_report


REPO_ROOT = Path(__file__).resolve().parents[2]


def _plan_repo_root(plan: HybridTemplatePlan) -> Path:
    parts = plan.template_path.resolve().parts
    for index, part in enumerate(parts):
        if part == "config":
            return Path(*parts[:index]) if index else Path("/")
    return REPO_ROOT


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _coverage_summary(path: Path, *, repo_root: Path) -> dict[str, Any]:
    payload = _load_json(path)
    coverage_policy = payload.get("coverage_output_policy")
    coverage = coverage_policy if isinstance(coverage_policy, dict) else {}
    selected_policy = payload.get("selected_acceptance_policy")
    selected = selected_policy if isinstance(selected_policy, dict) else {}
    return {
        "report": display_path(path, repo_root=repo_root),
        "match": payload.get("match"),
        "mismatch_count": payload.get("mismatch_count"),
        "coverage_output_equivalence_passed": (
            payload.get("coverage_output_equivalence_passed")
            if payload.get("coverage_output_equivalence_passed") is not None
            else coverage.get("passed")
        ),
        "coverage_output_mismatch_count": (
            payload.get("coverage_output_mismatch_count")
            if payload.get("coverage_output_mismatch_count") is not None
            else coverage.get("mismatch_count")
        ),
        "coverage_output_compared_word_count": (
            payload.get("coverage_output_compared_word_count")
            if payload.get("coverage_output_compared_word_count") is not None
            else coverage.get("compared_word_count")
        ),
        "coverage_output_compared_byte_count": (
            payload.get("coverage_output_compared_byte_count")
            if payload.get("coverage_output_compared_byte_count") is not None
            else coverage.get("compared_byte_count")
        ),
        "selected_acceptance_policy": selected.get("name"),
        "selected_acceptance_passed": selected.get("passed"),
    }


def sample_from_existing_reports(plan: HybridTemplatePlan, *, sample_index: int) -> dict[str, Any]:
    repo_root = _plan_repo_root(plan)
    cpu = _load_json(plan.cpu_report)
    hybrid = parse_hybrid_report(plan.hybrid_report, repo_root=repo_root)
    coverage = _coverage_summary(plan.compare_report, repo_root=repo_root)
    cpu_elapsed_ms = float(cpu["elapsed_ms"])
    hybrid_wall_ms = float(hybrid["hybrid_wall_ms"])
    gpu_kernel_total_ms = float(hybrid["gpu_kernel_total_ms"])
    return {
        "sample_index": sample_index,
        "cpu_elapsed_ms": cpu_elapsed_ms,
        "hybrid_wall_ms": hybrid_wall_ms,
        "gpu_kernel_total_ms": gpu_kernel_total_ms,
        "cpu_to_hybrid_wall_speedup": cpu_elapsed_ms / hybrid_wall_ms if hybrid_wall_ms else None,
        "cpu_to_gpu_kernel_speedup": cpu_elapsed_ms / gpu_kernel_total_ms if gpu_kernel_total_ms else None,
        "coverage_output": coverage,
        "reports": {
            "cpu_report": display_path(plan.cpu_report, repo_root=repo_root),
            "hybrid_report": display_path(plan.hybrid_report, repo_root=repo_root),
            "compare_report": display_path(plan.compare_report, repo_root=repo_root),
        },
    }


def _median(values: list[float | None]) -> float | None:
    numeric = [value for value in values if isinstance(value, int | float)]
    return float(statistics.median(numeric)) if numeric else None


def _all_coverage_passed(samples: list[dict[str, Any]]) -> bool:
    for sample in samples:
        coverage = sample.get("coverage_output")
        if not isinstance(coverage, dict):
            return False
        passed = coverage.get("coverage_output_equivalence_passed")
        mismatch = coverage.get("coverage_output_mismatch_count")
        if passed is not True and mismatch != 0:
            return False
    return bool(samples)


def summarize_samples(plan: HybridTemplatePlan, samples: list[dict[str, Any]]) -> dict[str, Any]:
    repo_root = _plan_repo_root(plan)
    speedups = [sample.get("cpu_to_hybrid_wall_speedup") for sample in samples]
    kernel_speedups = [sample.get("cpu_to_gpu_kernel_speedup") for sample in samples]
    return {
        "schema_version": 1,
        "surface": "hybrid_template_repeat_median",
        "status": "measured" if samples else "no_samples",
        "target": plan.target_name,
        "template": display_path(plan.template_path, repo_root=repo_root),
        "shape": f"{plan.nstates}x{plan.steps}",
        "repeat_count": len(samples),
        "coverage_output_equivalence_all_passed": _all_coverage_passed(samples),
        "median": {
            "cpu_elapsed_ms": _median([sample.get("cpu_elapsed_ms") for sample in samples]),
            "hybrid_wall_ms": _median([sample.get("hybrid_wall_ms") for sample in samples]),
            "gpu_kernel_total_ms": _median([sample.get("gpu_kernel_total_ms") for sample in samples]),
            "cpu_to_hybrid_wall_speedup": _median(speedups),
            "cpu_to_gpu_kernel_speedup": _median(kernel_speedups),
        },
        "samples": samples,
        "last_sample": samples[-1] if samples else None,
        "non_claims": [
            "scoped repeat-median evidence only",
            "not a broad speedup claim for arbitrary RTL",
            "coverage-output equivalence remains separate from raw full-state equality",
        ],
    }


def run_repeat_median(
    plan: HybridTemplatePlan,
    *,
    repeat_count: int,
    runner: Callable[[HybridTemplatePlan], None] | None = None,
) -> dict[str, Any]:
    if repeat_count <= 0:
        raise ValueError("repeat count must be positive")
    validate_source_closure_for_execution(plan)
    run_once = runner or (lambda current_plan: run_plan(current_plan, dry_run=False, verbose=False))
    samples: list[dict[str, Any]] = []
    for index in range(1, repeat_count + 1):
        run_once(plan)
        samples.append(sample_from_existing_reports(plan, sample_index=index))
    return summarize_samples(plan, samples)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="config/slice_launch_templates/<target>.json")
    parser.add_argument("--shape", default="1x1", help="State/step shape, for example 32x1")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--cfg-batch-length", type=int, default=64)
    parser.add_argument("--cfg-reset-cycles", type=int, default=2)
    parser.add_argument("--cfg-drain-cycles", type=int, default=8)
    parser.add_argument("--cfg-seed", type=int, default=1)
    parser.add_argument("--from-existing", action="store_true", help="Summarize current reports without executing")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        plan = load_template_plan(
            args.template,
            shape=args.shape,
            cfg_batch_length=args.cfg_batch_length,
            cfg_reset_cycles=args.cfg_reset_cycles,
            cfg_drain_cycles=args.cfg_drain_cycles,
            cfg_seed=args.cfg_seed,
        )
        if args.from_existing:
            summary = summarize_samples(plan, [sample_from_existing_reports(plan, sample_index=1)])
            summary["status"] = "summarized_from_existing_reports"
        else:
            summary = run_repeat_median(plan, repeat_count=args.repeat)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
