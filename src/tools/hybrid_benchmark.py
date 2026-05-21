#!/usr/bin/env python3
from __future__ import annotations

import json
import shlex
from pathlib import Path

from hybrid_benchmark_catalog import (
    MODE_TEMPLATE,
    benchmark_plan,
    default_summary_path,
    format_report_command as _format_report_command,
    repo_path as _repo_path,
    target_list_report,
)
from hybrid_benchmark_specs import (
    CORRECTNESS_POLICY_COVERAGE_OUTPUT,
    SCHEMA_ROLE_TARGET_FIRST_OPERATOR_PLAN,
    STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
    STATUS_READY_FOR_VERILATOR_OPTION_SHIM,
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
    format_sidecar_operator_plan as _format_sidecar_operator_plan,
    sidecar_handoff_contract as _sidecar_handoff_contract,
    sidecar_operator_plan as _sidecar_operator_plan,
    sidecar_stage_plan as _sidecar_stage_plan,
    synthesized_verilator_command_argv as _synthesized_verilator_command_argv,
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
        "efficiency_estimate": _efficiency_estimate(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
        "verilator_option_preview": verilator_option_preview(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
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


def write_summary(
    *,
    path: Path | None,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
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
    mode: str = MODE_TEMPLATE,
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
        "efficiency_estimate": _efficiency_estimate(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
        "verilator_option_preview": verilator_option_preview(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
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
) -> None:
    print(json.dumps(preflight_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases), indent=2))


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


def print_verilator_efficiency_estimate(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> int:
    exit_code, report = operator_plan_json_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    print(_format_efficiency_estimate(report["efficiency_estimate"]))
    return exit_code


def verilator_option_preview(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> dict[str, object]:
    exit_code, report = operator_plan_json_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    preview: dict[str, object] = {
        "schema_version": 1,
        "status": report["status"],
        "exit_code": exit_code,
        "command_emitted": exit_code == 0,
        "non_claims": [
            "preview does not execute commands",
            "preview does not mean Verilator itself implements --sim-accel",
            "coverage-output equivalence remains the correctness policy",
        ],
    }
    if exit_code == 0:
        preview.update(
            {
                "command_argv": report["command_argv"],
                "command": report["command"],
                "correctness_policy": report["correctness_policy"],
                "handoff_contract": report["handoff_contract"],
            }
        )
    else:
        plan = report.get("sidecar_stage_plan")
        readiness = plan.get("verilator_option_readiness") if isinstance(plan, dict) else None
        if isinstance(readiness, dict):
            preview["missing"] = readiness.get("missing", [])
    return preview


def operator_plan_report(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> dict[str, object]:
    plan = _sidecar_stage_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    readiness = plan.get("verilator_option_readiness")
    ready = isinstance(readiness, dict) and readiness.get("status") == STATUS_READY_FOR_VERILATOR_OPTION_SHIM
    if not ready:
        raise ValueError(f"{target} is not ready for the Verilator sidecar option shim")
    estimate = _efficiency_estimate(
        target=target,
        shape=shape,
        limit=limit,
        mode=mode,
        phases=phases,
    )
    command_argv = _synthesized_verilator_command_argv(plan)
    return _sidecar_operator_plan(
        command_argv=command_argv,
        command=shlex.join(command_argv),
        efficiency_estimate=estimate,
        handoff_contract=_sidecar_handoff_contract(plan),
    )


def operator_plan_json_report(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> tuple[int, dict[str, object]]:
    plan = _sidecar_stage_plan(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    readiness = plan.get("verilator_option_readiness")
    ready = isinstance(readiness, dict) and readiness.get("status") == STATUS_READY_FOR_VERILATOR_OPTION_SHIM
    if ready:
        report = operator_plan_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
        report["schema_role"] = SCHEMA_ROLE_TARGET_FIRST_OPERATOR_PLAN
        report["tool"] = "src/tools/run_hybrid_benchmark.py"
        report["use_when"] = [
            "automation starts from run_hybrid_benchmark.py --list-targets",
            "automation needs the synthesized Verilator command and efficiency estimate",
            "full sidecar stage details are not required",
        ]
        report["shim_boundary"] = {
            "tool": "src/tools/verilator_sidecar_shim.py",
            "use_when": "need readiness/stage details, stage command emission, or stable shim handoff fields",
        }
        report["exit_code"] = 0
        return 0, report
    return 2, {
        "schema_version": 1,
        "schema_role": SCHEMA_ROLE_TARGET_FIRST_OPERATOR_PLAN,
        "tool": "src/tools/run_hybrid_benchmark.py",
        "status": STATUS_NOT_READY_FOR_VERILATOR_OPTION_SHIM,
        "target": target,
        "shape": shape,
        "limit": limit,
        "mode": mode,
        "phases": phases,
        "exit_code": 2,
        "efficiency_estimate": _efficiency_estimate(
            target=target,
            shape=shape,
            limit=limit,
            mode=mode,
            phases=phases,
        ),
        "sidecar_stage_plan": plan,
        "use_when": [
            "automation starts from run_hybrid_benchmark.py --list-targets",
            "automation needs a stable not-ready JSON result without parsing stderr",
        ],
        "shim_boundary": {
            "tool": "src/tools/verilator_sidecar_shim.py",
            "use_when": "need readiness/stage details, stage command emission, or stable shim handoff fields",
        },
        "non_claims": [
            "operator plan JSON does not execute commands",
            "not-ready status is not correctness or timing evidence",
            "coverage-output equivalence remains separate from performance estimates",
        ],
    }


def print_operator_plan(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> None:
    plan = operator_plan_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    print(_format_sidecar_operator_plan(plan))


def print_verilator_command(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> int:
    exit_code, report = operator_plan_json_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    if exit_code != 0:
        print(json.dumps(report, indent=2))
        return exit_code
    print(report["command"])
    return 0


def print_operator_plan_json(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> int:
    exit_code, report = operator_plan_json_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    print(json.dumps(report, indent=2))
    return exit_code


def print_target_list() -> None:
    print(json.dumps(target_list_report(), indent=2))
