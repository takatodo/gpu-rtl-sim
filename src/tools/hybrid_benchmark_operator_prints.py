"""Printing helpers for hybrid benchmark operator previews."""

from __future__ import annotations

import json

from hybrid_benchmark_catalog import MODE_TEMPLATE
from hybrid_benchmark_efficiency import format_efficiency_estimate
from hybrid_benchmark_operator_core import (
    format_verilator_option_preview,
    operator_plan_json_report,
    operator_plan_report,
    verilator_option_preview,
)
from hybrid_benchmark_sidecar_plan import format_sidecar_operator_plan


def print_verilator_efficiency_estimate(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> int:
    exit_code, report = operator_plan_json_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    print(format_efficiency_estimate(report["efficiency_estimate"]))
    return exit_code


def print_operator_plan(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    operator_entrypoint: dict[str, object] | None = None,
) -> int:
    exit_code, report = operator_plan_json_report(
        target=target,
        shape=shape,
        limit=limit,
        mode=mode,
        phases=phases,
        operator_entrypoint=operator_entrypoint,
    )
    if exit_code != 0:
        print(json.dumps(report, indent=2))
        return exit_code
    plan = operator_plan_report(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    print(format_sidecar_operator_plan(plan))
    return 0


def print_verilator_command(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    operator_entrypoint: dict[str, object] | None = None,
) -> int:
    exit_code, report = operator_plan_json_report(
        target=target,
        shape=shape,
        limit=limit,
        mode=mode,
        phases=phases,
        operator_entrypoint=operator_entrypoint,
    )
    if exit_code != 0:
        print(json.dumps(report, indent=2))
        return exit_code
    print(report["command"])
    return 0


def print_verilator_estimate_command(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    operator_entrypoint: dict[str, object] | None = None,
) -> int:
    exit_code, report = operator_plan_json_report(
        target=target,
        shape=shape,
        limit=limit,
        mode=mode,
        phases=phases,
        operator_entrypoint=operator_entrypoint,
    )
    if exit_code != 0:
        print(json.dumps(report, indent=2))
        return exit_code
    print(report["estimate_command"])
    return 0


def print_verilator_option_preview(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
) -> int:
    preview = verilator_option_preview(target=target, shape=shape, limit=limit, mode=mode, phases=phases)
    print(format_verilator_option_preview(preview))
    return int(preview["exit_code"])


def print_operator_plan_json(
    *,
    target: str,
    shape: str | None = None,
    limit: int | None = None,
    mode: str = MODE_TEMPLATE,
    phases: int = 4,
    operator_entrypoint: dict[str, object] | None = None,
) -> int:
    exit_code, report = operator_plan_json_report(
        target=target,
        shape=shape,
        limit=limit,
        mode=mode,
        phases=phases,
        operator_entrypoint=operator_entrypoint,
    )
    print(json.dumps(report, indent=2))
    return exit_code
