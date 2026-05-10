#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hybrid_template_runner import load_template_plan
from results_reproduction import (
    REPO_ROOT,
    ReproductionCommand,
    format_command,
    mobile_vit_imagenet_128_plan,
)


@dataclass(frozen=True)
class BenchmarkSpec:
    target: str
    kind: str
    template: str | None = None


BENCHMARKS: dict[str, BenchmarkSpec] = {
    "pulp_ita_mha": BenchmarkSpec(
        target="pulp_ita_mha",
        kind="slice_template",
        template="config/slice_launch_templates/pulp_ita_mha.json",
    ),
    "paged_attention_kv_score": BenchmarkSpec(
        target="paged_attention_kv_score",
        kind="slice_template",
        template="config/slice_launch_templates/pulp_paged_attention_kv_score.json",
    ),
    "pulp_paged_attention_kv_score": BenchmarkSpec(
        target="paged_attention_kv_score",
        kind="slice_template",
        template="config/slice_launch_templates/pulp_paged_attention_kv_score.json",
    ),
    "mobile_vit": BenchmarkSpec(
        target="mobile_vit",
        kind="mobile_vit_imagenet",
    ),
}


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _shape_tag(*, shape: str | None, limit: int | None) -> str:
    if shape is not None:
        return shape.replace("/", "_")
    if limit is not None:
        return f"limit{limit}"
    return "unshaped"


def _format_report_command(command: ReproductionCommand) -> str:
    rendered = format_command(command)
    rendered = rendered.replace(str(REPO_ROOT), ".")
    return re.sub(r"(?<!\S)/home/\S+", "<local-absolute-path>", rendered)


def default_summary_path(*, target: str, shape: str | None, limit: int | None, mode: str) -> Path:
    mode_tag = mode.replace("-", "_")
    return REPO_ROOT / "reports" / f"hybrid_benchmark_{target}_{mode_tag}_{_shape_tag(shape=shape, limit=limit)}.json"


def benchmark_plan(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = "template",
    phases: int = 4,
) -> list[ReproductionCommand]:
    try:
        spec = BENCHMARKS[target]
    except KeyError as exc:
        supported = ", ".join(sorted(BENCHMARKS))
        raise ValueError(f"unsupported benchmark target: {target}; supported: {supported}") from exc

    if phases <= 0:
        raise ValueError("--phases must be positive")

    if spec.kind == "slice_template":
        if shape is None:
            raise ValueError(f"{target} requires --shape")
        if limit is not None:
            raise ValueError(f"{target} does not accept --limit")
        if mode == "resident-state-reuse":
            if spec.target != "pulp_ita_mha":
                raise ValueError(f"{target} does not support --mode resident-state-reuse")
            return [
                ReproductionCommand(
                    [
                        "python3",
                        "src/tools/run_results_reproduction.py",
                        "--resident-state-reuse",
                        shape,
                        "--resident-state-reuse-phases",
                        str(phases),
                    ]
                )
            ]
        if mode == "persistent-resident-state-abi":
            if spec.target != "pulp_ita_mha":
                raise ValueError(f"{target} does not support --mode persistent-resident-state-abi")
            return [
                ReproductionCommand(
                    [
                        "python3",
                        "src/tools/run_results_reproduction.py",
                        "--persistent-resident-state-abi",
                        shape,
                        "--persistent-resident-state-abi-phases",
                        str(phases),
                    ]
                )
            ]
        if mode != "template":
            raise ValueError(f"unsupported mode for {target}: {mode}")
        assert spec.template is not None
        return [
            ReproductionCommand(
                [
                    "python3",
                    "src/tools/run_hybrid_template.py",
                    spec.template,
                    "--shape",
                    shape,
                ]
            )
        ]

    if spec.kind == "mobile_vit_imagenet":
        if mode != "template":
            raise ValueError("mobile_vit only supports --mode template")
        if shape is not None:
            raise ValueError("mobile_vit does not accept --shape")
        if limit != 128:
            raise ValueError("mobile_vit currently supports --limit 128 only")
        return mobile_vit_imagenet_128_plan()

    raise ValueError(f"unsupported benchmark kind: {spec.kind}")


def _expected_reports(
    *,
    target: str,
    shape: str | None,
    limit: int | None,
    mode: str,
    phases: int,
) -> dict[str, object]:
    spec = BENCHMARKS[target]
    if spec.kind == "slice_template" and mode == "template":
        assert spec.template is not None
        assert shape is not None
        plan = load_template_plan(Path(spec.template), shape=shape)
        return {
            "cpu_report": _display_path(plan.cpu_report),
            "hybrid_report": _display_path(plan.hybrid_report),
            "compare_report": _display_path(plan.compare_report),
        }
    if spec.kind == "slice_template" and mode == "resident-state-reuse":
        return {
            "aggregate_summary": "reports/resident_state_reuse_experiment_summary.json",
            "phase_count": phases,
        }
    if spec.kind == "slice_template" and mode == "persistent-resident-state-abi":
        return {
            "aggregate_summary": "reports/persistent_resident_state_abi_probe_summary.json",
            "phase_count": phases,
        }
    if spec.kind == "mobile_vit_imagenet":
        assert limit is not None
        return {
            "aggregate_summary": f"reports/mobile_vit_hybrid_{limit}_summary.json",
            "accuracy_report": f"reports/mobile_vit_hybrid_{limit}_accuracy.json",
        }
    return {}


def _coverage_from_compare(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    coverage = payload.get("coverage_output_policy") or {}
    return {
        "compare_report": _display_path(path),
        "acceptance_policy": coverage.get("acceptance_policy"),
        "coverage_output_passed": coverage.get("passed"),
        "coverage_output_mismatch_count": coverage.get("mismatch_count"),
        "compared_word_count": coverage.get("compared_word_count"),
        "compared_byte_count": coverage.get("compared_byte_count"),
    }


def _evidence_summary(
    *,
    target: str,
    shape: str | None,
    limit: int | None,
    mode: str,
    phases: int,
    execution_mode: str,
) -> dict[str, object]:
    if execution_mode not in ("executed", "existing_evidence"):
        return {
            "status": "not_collected",
            "reason": f"{execution_mode} does not execute benchmark commands",
        }

    spec = BENCHMARKS[target]
    if spec.kind == "slice_template" and mode == "template":
        assert spec.template is not None
        assert shape is not None
        plan = load_template_plan(Path(spec.template), shape=shape)
        if not plan.compare_report.exists():
            return {"status": "missing", "missing_report": _display_path(plan.compare_report)}
        evidence = _coverage_from_compare(plan.compare_report)
        evidence["status"] = "collected"
        return evidence

    reports = _expected_reports(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    aggregate = reports.get("aggregate_summary")
    if not isinstance(aggregate, str):
        return {"status": "not_available"}
    aggregate_path = _repo_path(aggregate)
    if not aggregate_path.exists():
        return {"status": "missing", "missing_report": aggregate}
    payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
    if spec.kind == "mobile_vit_imagenet":
        hybrid_control = payload.get("hybrid_control") or {}
        return {
            "status": "collected",
            "aggregate_summary": aggregate,
            "evaluated_count": payload.get("evaluated_count"),
            "top1_accuracy": payload.get("top1_accuracy"),
            "top5_accuracy": payload.get("top5_accuracy"),
            "coverage_output_passed": hybrid_control.get("coverage_output_equivalence_complete"),
            "hybrid_batch_count": hybrid_control.get("batch_count"),
        }
    actual_shape = payload.get("shape")
    actual_phases = payload.get("phases")
    if actual_shape != shape or actual_phases != phases:
        return {
            "status": "mismatched_summary",
            "aggregate_summary": aggregate,
            "expected_shape": shape,
            "actual_shape": actual_shape,
            "expected_phases": phases,
            "actual_phases": actual_phases,
            "coverage_output_passed": payload.get("all_coverage_output_passed"),
            "coverage_output_mismatch_count": payload.get("max_coverage_output_mismatch_count"),
        }
    return {
        "status": "collected",
        "aggregate_summary": aggregate,
        "acceptance_policy": payload.get("acceptance_policy"),
        "coverage_output_passed": payload.get("all_coverage_output_passed"),
        "coverage_output_mismatch_count": payload.get("max_coverage_output_mismatch_count"),
        "phase_count": len(payload.get("phase_reports") or []),
    }


def benchmark_summary(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = "template",
    phases: int = 4,
    execution_mode: str,
) -> dict[str, object]:
    commands = benchmark_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    return {
        "schema_version": 1,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "target": target,
        "shape": shape,
        "limit": limit,
        "mode": mode,
        "phases": phases,
        "execution_mode": execution_mode,
        "command_count": len(commands),
        "commands": [_format_report_command(command) for command in commands],
        "expected_reports": _expected_reports(target=target, shape=shape, limit=limit, mode=mode, phases=phases),
        "evidence": _evidence_summary(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
            execution_mode=execution_mode,
        ),
        "non_claims": [
            "summary records benchmark wrapper evidence only",
            "dry-run summaries are not correctness or timing evidence",
            "existing_evidence summaries do not rerun benchmark commands",
            "coverage-output equivalence is not raw full-state equality",
        ],
    }


def write_summary(
    *,
    path: Path | None,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = "template",
    phases: int = 4,
    execution_mode: str,
) -> Path:
    out = path or default_summary_path(target=target, shape=shape, limit=limit, mode=mode)
    out = _repo_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            benchmark_summary(
                target=target,
                shape=shape,
                limit=limit,
                mode=mode,
                phases=phases,
                execution_mode=execution_mode,
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return out


def preflight_report(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = "template",
    phases: int = 4,
) -> dict[str, object]:
    commands = benchmark_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    return {
        "schema_version": 1,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "target": target,
        "shape": shape,
        "limit": limit,
        "mode": mode,
        "phases": phases,
        "command_count": len(commands),
        "commands": [format_command(command) for command in commands],
        "execution_mode": "preflight",
        "non_claims": [
            "preflight does not execute benchmark commands",
            "preflight is not correctness evidence",
            "preflight is not timing evidence",
        ],
    }


def run_benchmark(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = "template",
    phases: int = 4,
    dry_run: bool,
) -> None:
    for command in benchmark_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases):
        print("+ " + format_command(command))
        if dry_run:
            continue
        if command.stdout is None:
            subprocess.run(command.argv, cwd=REPO_ROOT, check=True)
            continue
        command.stdout.parent.mkdir(parents=True, exist_ok=True)
        with command.stdout.open("w", encoding="utf-8") as out:
            subprocess.run(command.argv, cwd=REPO_ROOT, check=True, stdout=out)


def print_preflight(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = "template",
    phases: int = 4,
) -> None:
    print(json.dumps(preflight_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases), indent=2))
