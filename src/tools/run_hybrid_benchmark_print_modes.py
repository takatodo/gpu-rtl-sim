from __future__ import annotations

import argparse

from hybrid_benchmark import (
    print_operator_plan,
    print_operator_plan_json,
    print_verilator_efficiency_estimate,
    print_verilator_estimate_command,
    print_verilator_command,
)


def reject_summary_or_execution_options(args: argparse.Namespace, option_name: str) -> None:
    if args.preflight or args.dry_run or args.summary_from_existing or args.summary_out is not None:
        raise ValueError(f"{option_name} cannot be combined with execution, preflight, or summary options")


def run_print_only_mode(
    args: argparse.Namespace,
    explicit_estimate_output: bool,
    *,
    operator_entrypoint: dict[str, object],
) -> bool:
    print_only_modes = [
        args.print_verilator_command,
        args.print_verilator_estimate_command,
        args.print_efficiency_estimate,
        args.print_operator_plan,
        args.operator_plan_json,
    ]
    if sum(1 for enabled in print_only_modes if enabled) > 1:
        raise ValueError(
            "--print-verilator-command, --print-verilator-estimate-command, "
            "--print-efficiency-estimate, --print-operator-plan, and --operator-plan-json are mutually exclusive"
        )
    if args.print_verilator_command:
        reject_summary_or_execution_options(args, "--print-verilator-command")
        if explicit_estimate_output:
            raise ValueError(
                "--print-verilator-command cannot be combined with estimate output flags; "
                "use --print-verilator-estimate-command"
            )
        exit_code = print_verilator_command(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint,
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return True
    if args.print_verilator_estimate_command:
        reject_summary_or_execution_options(args, "--print-verilator-estimate-command")
        if explicit_estimate_output:
            raise ValueError("--print-verilator-estimate-command already includes --sim-accel-estimate-efficiency")
        exit_code = print_verilator_estimate_command(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint,
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return True
    if args.print_efficiency_estimate:
        reject_summary_or_execution_options(args, "--print-efficiency-estimate")
        if explicit_estimate_output:
            raise ValueError(
                "--print-efficiency-estimate cannot be combined with --estimate-efficiency, "
                "--estimate-efficiency-json, or --sim-accel-estimate-efficiency"
            )
        exit_code = print_verilator_efficiency_estimate(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return True
    if args.operator_plan_json:
        reject_summary_or_execution_options(args, "--operator-plan-json")
        exit_code = print_operator_plan_json(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint,
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return True
    if args.print_operator_plan:
        reject_summary_or_execution_options(args, "--print-operator-plan")
        exit_code = print_operator_plan(
            target=args.target,
            shape=args.shape,
            limit=args.limit,
            mode=args.mode,
            phases=args.phases,
            operator_entrypoint=operator_entrypoint,
        )
        if exit_code != 0:
            raise SystemExit(exit_code)
        return True
    return False
