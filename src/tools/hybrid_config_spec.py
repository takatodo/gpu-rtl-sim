"""Shared specification types for generated hybrid config payloads."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HybridConfigSpec:
    target: str
    top_module: str
    source_files: list[str]
    overlay: str | None
    gate_name: str
    host_probe_target: str | None
    mdir: str | None
    work_dir: str | None
    verilator_args: list[str]
    clock_field: str | None = None
    clock_report_name: str = "clk_i"
    reset_field: str | None = None
    reset_report_name: str = "reset_like_w"
    reset_asserted_value: str = "1U"
    reset_deasserted_value: str = "0U"
    host_clock_control: bool = True
    host_reset_control: bool = False
    probe_syms_state: bool = False
    status: str = "candidate"

    @property
    def target_name(self) -> str:
        return self.target.split(".")[-1]

    @property
    def resolved_host_probe_target(self) -> str:
        return self.host_probe_target or f"{self.target_name}_host_probe"

    @property
    def resolved_mdir(self) -> str:
        return self.mdir or f"artifacts/{self.target_name}_obj_dir"

    @property
    def resolved_work_dir(self) -> str:
        return self.work_dir or f"work/slice_pilots/{self.target_name}"


def default_gate_name(target: str) -> str:
    return f"{target.split('.')[-1]}_first_hybrid_benchmark_gate"


def default_paths(spec: HybridConfigSpec) -> dict[str, str]:
    target_name = spec.target_name
    return {
        "gate": f"config/scaling_gates/{spec.gate_name}.json",
        "manifest": f"overlays/generated/tests/{target_name}_coverage_regions.json",
        "template": f"config/slice_launch_templates/{target_name}.json",
    }
