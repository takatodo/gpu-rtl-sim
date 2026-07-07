#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from hybrid_host_probe_execution import run_compile_command
from hybrid_host_probe_plan import HostProbeBuildPlan, default_verilator_root, load_host_probe_build_plan, repo_path


REPO_ROOT = Path(__file__).resolve().parents[2]


_repo_path = repo_path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _quote_define(raw: str) -> str:
    return f'"{raw}"'


def host_probe_compile_command(plan: HostProbeBuildPlan) -> list[str]:
    model = f"V{plan.top_module}"
    root = f"{model}___024root"
    command = [
        plan.cxx,
        "-std=c++20",
        "-fcoroutines",
        "-O2",
        "-w",
        f"-I{_display_path(plan.mdir)}",
        f"-I{plan.verilator_root / 'include'}",
        f"-I{plan.verilator_root / 'include' / 'vltstd'}",
        f"-DMODEL_HEADER={_quote_define(model + '.h')}",
        f"-DROOT_HEADER={_quote_define(root + '.h')}",
        f"-DMODEL_CLASS={model}",
        f"-DROOT_CLASS={root}",
        # The GPU sidecar kernel vl_eval_batch_gpu wraps this same generated root
        # ___eval; defining it here lets the CPU eval-only baseline call the
        # identical function for an apples-to-apples timing comparison.
        f"-DROOT_EVAL_FN={root}___eval",
        f"-DROOT_CLK_FIELD={plan.clock_field}",
        f"-DROOT_CLK_REPORT_NAME={_quote_define(plan.clock_report_name)}",
        f"-DROOT_RST_FIELD={plan.reset_field}",
        f"-DROOT_RST_REPORT_NAME={_quote_define(plan.reset_report_name)}",
        f"-DROOT_RST_ASSERTED_VALUE={plan.reset_asserted_value}",
        f"-DROOT_RST_DEASSERTED_VALUE={plan.reset_deasserted_value}",
        f"-DHOST_CLOCK_CONTROL={1 if plan.host_clock_control else 0}",
        f"-DHOST_RESET_CONTROL={1 if plan.host_reset_control else 0}",
        f"-DTARGET_NAME={_quote_define(plan.top_module)}",
    ]
    if plan.probe_syms_state:
        command.extend(
            [
                f"-DSYMS_HEADER={_quote_define(model + '__Syms.h')}",
                f"-DSYMS_CLASS={model}__Syms",
                "-DPROBE_SYMS_STATE=1",
            ]
        )
    command.extend(
        [
            "src/hybrid/tlul_slice_host_probe.cpp",
            f"{_display_path(plan.mdir)}/*.cpp",
            str(plan.verilator_root / "include" / "verilated.cpp"),
            str(plan.verilator_root / "include" / "verilated_timing.cpp"),
            str(plan.verilator_root / "include" / "verilated_threads.cpp"),
            "-pthread",
            "-o",
            _display_path(plan.output),
        ]
    )
    return command


def run_host_probe_build(plan: HostProbeBuildPlan, *, dry_run: bool = False) -> None:
    command = host_probe_compile_command(plan)
    print("+ " + " ".join(command))
    if dry_run:
        return
    plan.output.parent.mkdir(parents=True, exist_ok=True)
    run_compile_command(command)
