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


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


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
    from hybrid_template_runner import normalize_template_payload

    template_path = repo_path(template_path)
    payload = normalize_template_payload(json.loads(template_path.read_text(encoding="utf-8")))
    top_module = str(payload["top_module"])
    build = payload["build"]
    mdir = repo_path(str(build["mdir"]))
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
