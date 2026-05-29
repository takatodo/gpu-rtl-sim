#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from hybrid_config_generator import (
    HybridConfigSpec,
    default_gate_name,
    generated_payloads,
    write_payloads,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the config needed by run_hybrid_template.py: scaling gate, "
            "coverage manifest, and slice launch template."
        )
    )
    parser.add_argument("--target", required=True, help="Logical target, for example PULP_ITA.my_target")
    parser.add_argument("--top-module", required=True)
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="RTL source file. Repeat for multiple sources.",
    )
    parser.add_argument(
        "--copy-source-closure-from-template",
        "--source-closure-from-template",
        dest="copy_source_closure_from_template",
        help=(
            "Copy source_files/source_closure from a tracked config/slice_launch_templates/*.json "
            "template that already declares source_closure.status=complete."
        ),
    )
    parser.add_argument(
        "--overlay",
        help="Coverage top overlay path. Added to source_files when not already listed.",
    )
    parser.add_argument("--gate-name", help="Gate basename without .json")
    parser.add_argument("--host-probe-target")
    parser.add_argument(
        "--clock-field",
        help="Root clock field for generated host-probe build metadata. Defaults to <top>__DOT__clk_i.",
    )
    parser.add_argument("--clock-report-name", default="clk_i")
    parser.add_argument(
        "--reset-field",
        help="Root reset field for generated host-probe build metadata. Defaults to <top>__DOT__reset_like_w.",
    )
    parser.add_argument("--reset-report-name", default="reset_like_w")
    parser.add_argument("--reset-asserted-value", default="1U")
    parser.add_argument("--reset-deasserted-value", default="0U")
    parser.add_argument("--host-reset-control", action="store_true")
    parser.add_argument("--probe-syms-state", action="store_true")
    parser.add_argument("--mdir")
    parser.add_argument("--work-dir")
    parser.add_argument(
        "--verilator-arg",
        action="append",
        default=["--flatten"],
        help="Extra Verilator arg. Defaults to --flatten; repeat for multiple args.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def spec_from_args(args: argparse.Namespace) -> HybridConfigSpec:
    return HybridConfigSpec(
        target=args.target,
        top_module=args.top_module,
        source_files=args.source,
        overlay=args.overlay,
        gate_name=args.gate_name or default_gate_name(args.target),
        host_probe_target=args.host_probe_target,
        mdir=args.mdir,
        work_dir=args.work_dir,
        verilator_args=args.verilator_arg,
        clock_field=args.clock_field,
        clock_report_name=args.clock_report_name,
        reset_field=args.reset_field,
        reset_report_name=args.reset_report_name,
        reset_asserted_value=args.reset_asserted_value,
        reset_deasserted_value=args.reset_deasserted_value,
        host_reset_control=args.host_reset_control,
        probe_syms_state=args.probe_syms_state,
        copy_source_closure_from_template=args.copy_source_closure_from_template,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.source and not args.overlay and not args.copy_source_closure_from_template:
        print(
            "error: at least one --source, --overlay, or --copy-source-closure-from-template is required",
            file=sys.stderr,
        )
        return 1

    try:
        spec = spec_from_args(args)
        write_payloads(generated_payloads(spec), dry_run=args.dry_run)
    except (FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
