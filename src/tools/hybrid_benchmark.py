#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from hybrid_benchmark_catalog import (
    MODE_TEMPLATE,
    benchmark_plan,
    default_summary_path,
    format_report_command as _format_report_command,
    operator_discovery_hint,
    repo_path as _repo_path,
    sidecar_target_list_report,
    target_list_report,
)
from hybrid_benchmark_evidence import (
    evidence_summary as _evidence_summary,
    expected_reports as _expected_reports,
)
from hybrid_benchmark_efficiency import (
    efficiency_estimate as _efficiency_estimate,
    format_efficiency_estimate as _format_efficiency_estimate,
)
from hybrid_benchmark_sidecar_plan import (
    sidecar_stage_plan as _sidecar_stage_plan,
)
from hybrid_benchmark_operator_core import (
    format_verilator_option_preview,
    operator_plan_json_report,
    operator_plan_report,
    verilator_option_preview,
)
from hybrid_benchmark_operator_prints import (
    print_operator_plan,
    print_operator_plan_json,
    print_verilator_command,
    print_verilator_efficiency_estimate,
    print_verilator_estimate_command,
    print_verilator_option_preview,
)
from hybrid_benchmark_execution import run_benchmark_commands
from results_reproduction import (
    format_command,
)

def benchmark_summary(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    execution_mode: str,
    operator_entrypoint: dict[str, object] | None = None,
) -> dict[str, object]:
    commands = benchmark_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    preview = verilator_option_preview(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    discovery_hint = operator_discovery_hint_for_preview(
        preview=preview,
        target=target,
        requested_shape=shape,
    )
    return {
        "schema_version": 1,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "target": target,
        "shape": shape,
        "limit": limit,
        "mode": mode,
        "phases": phases,
        "execution_mode": execution_mode,
        "operator_entrypoint": operator_entrypoint,
        "command_count": len(commands),
        "commands": [_format_report_command(command) for command in commands],
        "expected_reports": _expected_reports(target=target, shape=shape, limit=limit, mode=mode, phases=phases),
        "efficiency_estimate": _efficiency_estimate(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
        "verilator_option_preview": preview,
        "discovery_hint": discovery_hint,
        "sidecar_stage_plan": _sidecar_stage_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases),
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


def operator_discovery_hint_for_preview(
    *,
    preview: dict[str, object],
    target: str,
    requested_shape: str | None,
) -> dict[str, object] | None:
    if preview["status"] != "planned":
        return None
    return operator_discovery_hint(target=target, requested_shape=requested_shape)


def write_summary(
    *,
    path: Path | None,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    execution_mode: str,
    operator_entrypoint: dict[str, object] | None = None,
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
                operator_entrypoint=operator_entrypoint,
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
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    operator_entrypoint: dict[str, object] | None = None,
) -> dict[str, object]:
    commands = benchmark_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    preview = verilator_option_preview(
        target=target,
        shape=shape,
        limit=limit,
        mode=mode,
        phases=phases,
    )
    return {
        "schema_version": 1,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "target": target,
        "shape": shape,
        "limit": limit,
        "mode": mode,
        "phases": phases,
        "operator_entrypoint": operator_entrypoint,
        "command_count": len(commands),
        "commands": [format_command(command) for command in commands],
        "efficiency_estimate": _efficiency_estimate(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
        "verilator_option_preview": preview,
        "discovery_hint": operator_discovery_hint_for_preview(
            preview=preview,
            target=target,
            requested_shape=shape,
        ),
        "sidecar_stage_plan": _sidecar_stage_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases),
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
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    dry_run: bool,
) -> None:
    commands = benchmark_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    run_benchmark_commands(commands, dry_run=dry_run)


def print_preflight(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    operator_entrypoint: dict[str, object] | None = None,
) -> None:
    print(
        json.dumps(
            preflight_report(
                target=target,
                shape=shape,
                limit=limit,
                mode=mode,
                phases=phases,
                operator_entrypoint=operator_entrypoint,
            ),
            indent=2,
        )
    )


def print_efficiency_estimate(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    as_json: bool = False,
) -> None:
    estimate = _efficiency_estimate(
        target=target,
        shape=shape,
        limit=limit,
        mode=mode,
        phases=phases,
    )
    if as_json:
        print("# efficiency_estimate_json")
        print(json.dumps(estimate, indent=2))
        return
    print(_format_efficiency_estimate(estimate))


def print_target_list(view: str | None = None) -> None:
    if view is None:
        report = target_list_report()
    elif view == "sidecar_gpu":
        report = sidecar_target_list_report()
    else:
        raise ValueError(f"unsupported --list-targets view: {view}; supported: sidecar_gpu")
    print(json.dumps(report, indent=2))
