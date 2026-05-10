#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class HostProbeBuildPlan:
    template_path: Path
    top_module: str
    mdir: Path
    output: Path
    clock_field: str
    clock_report_name: str
    reset_field: str
    reset_report_name: str
    reset_asserted_value: str
    reset_deasserted_value: str
    host_clock_control: bool
    host_reset_control: bool
    probe_syms_state: bool
    cxx: str
    verilator_root: Path


def _repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _quote_define(raw: str) -> str:
    return f'"{raw}"'


def default_verilator_root() -> Path:
    env = os.environ.get("VERILATOR_ROOT")
    if env:
        return Path(env)
    try:
        completed = subprocess.run(
            ["verilator", "--getenv", "VERILATOR_ROOT"],
            check=True,
            text=True,
            capture_output=True,
        )
        value = completed.stdout.strip()
        if value:
            return Path(value)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return Path("/usr/local/share/verilator")


def load_host_probe_build_plan(template_path: Path) -> HostProbeBuildPlan:
    import json

    template_path = _repo_path(template_path)
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    top_module = str(payload["top_module"])
    build = payload["build"]
    mdir = _repo_path(str(build["mdir"]))
    host_probe = build.get("host_probe") or {}
    return HostProbeBuildPlan(
        template_path=template_path,
        top_module=top_module,
        mdir=mdir,
        output=mdir / str(host_probe.get("output", "tlul_slice_host_probe")),
        clock_field=str(host_probe.get("clock_field", f"{top_module}__DOT__clk_i")),
        clock_report_name=str(host_probe.get("clock_report_name", "clk_i")),
        reset_field=str(host_probe.get("reset_field", f"{top_module}__DOT__reset_like_w")),
        reset_report_name=str(host_probe.get("reset_report_name", "reset_like_w")),
        reset_asserted_value=str(host_probe.get("reset_asserted_value", "1U")),
        reset_deasserted_value=str(host_probe.get("reset_deasserted_value", "0U")),
        host_clock_control=bool(host_probe.get("host_clock_control", True)),
        host_reset_control=bool(host_probe.get("host_reset_control", False)),
        probe_syms_state=bool(host_probe.get("probe_syms_state", False)),
        cxx=str(host_probe.get("cxx", os.environ.get("CXX", "g++"))),
        verilator_root=Path(str(host_probe.get("verilator_root", default_verilator_root()))),
    )


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
    expanded: list[str] = []
    for arg in command:
        if arg.endswith("/*.cpp"):
            glob_dir = Path(arg[:-6])
            if not glob_dir.is_absolute():
                glob_dir = REPO_ROOT / glob_dir
            matches = sorted(glob_dir.glob("*.cpp"))
            if not matches:
                raise FileNotFoundError(f"no Verilator C++ files matched {arg}")
            expanded.extend(_display_path(path) for path in matches)
        else:
            expanded.append(arg)
    plan.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(expanded, cwd=REPO_ROOT, check=True)
