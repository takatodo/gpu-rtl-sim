#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


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


def coverage_manifest(spec: HybridConfigSpec) -> dict:
    return {
        "schema_version": 1,
        "target": spec.target,
        "coverage_domain": "toggle_real_subset_bitmap",
        "top_module": spec.top_module,
        "regions": [
            {
                "name": f"{spec.target_name}_counts",
                "words": [f"real_toggle_subset_word{idx}_o" for idx in range(8)],
            },
            {
                "name": f"{spec.target_name}_signatures",
                "words": [f"real_toggle_subset_word{idx}_o" for idx in range(8, 14)],
            },
            {
                "name": f"{spec.target_name}_samples",
                "words": [f"real_toggle_subset_word{idx}_o" for idx in range(14, 18)],
            },
        ],
        "non_claims": [
            "not correctness equivalence beyond scoped output words",
            "not raw full-state equality",
        ],
    }


def launch_template(spec: HybridConfigSpec, *, gate_path: str, manifest_path: str) -> dict:
    source_files = list(spec.source_files)
    planned_overlay_status = "not_applicable"
    if spec.overlay:
        planned_overlay_status = "implemented"
        if spec.overlay not in source_files:
            source_files.append(spec.overlay)
    return {
        "schema_version": 1,
        "status": spec.status,
        "target": spec.target,
        "source_gate": gate_path,
        "top_module": spec.top_module,
        "build": {
            "mdir": spec.resolved_mdir,
            "work_dir": spec.resolved_work_dir,
            "host_probe_target": spec.resolved_host_probe_target,
            "host_probe_builder": "src/tools/build_host_probe.py",
            "host_probe": {
                "output": "tlul_slice_host_probe",
                "clock_field": spec.clock_field or f"{spec.top_module}__DOT__clk_i",
                "clock_report_name": spec.clock_report_name,
                "reset_field": spec.reset_field or f"{spec.top_module}__DOT__reset_like_w",
                "reset_report_name": spec.reset_report_name,
                "reset_asserted_value": spec.reset_asserted_value,
                "reset_deasserted_value": spec.reset_deasserted_value,
                "host_clock_control": spec.host_clock_control,
                "host_reset_control": spec.host_reset_control,
                "probe_syms_state": spec.probe_syms_state,
            },
            "verilator_mode": "flattened" if "--flatten" in spec.verilator_args else "default",
        },
        "source_files": source_files,
        "verilator_args": list(spec.verilator_args),
        "planned_overlay": {
            "coverage_tb_path": spec.overlay,
            "coverage_manifest_path": manifest_path,
            "launch_template_path": f"config/slice_launch_templates/{spec.target_name}.json",
            "host_probe_target": spec.resolved_host_probe_target,
            "host_probe_builder": "src/tools/build_host_probe.py",
            "makefile": "not_required_for_generated_template",
            "status": planned_overlay_status,
        },
        "acceptance": {
            "candidate_only_until_first_cpu_vs_hybrid_benchmark": True,
            "next_gate_must_build_cpu_reference": True,
            "next_gate_must_build_gpu_cubin": True,
            "next_gate_must_compare_cpu_vs_hybrid": True,
            "speedup_claim_allowed_by_template_alone": False,
        },
        "non_claims": [
            "not raw full-state equality",
            "not broad speedup",
        ],
    }


def benchmark_gate(spec: HybridConfigSpec, *, manifest_path: str, template_path: str) -> dict:
    return {
        "schema_version": 1,
        "gate": spec.gate_name,
        "target": spec.target_name,
        "status": "defined_from_generated_hybrid_config",
        "objective": "Generated first CPU-vs-hybrid coverage-output benchmark gate.",
        "overlay": {
            "coverage_tb": spec.overlay,
            "coverage_manifest": manifest_path,
            "launch_template": template_path,
            "host_probe_target": spec.resolved_host_probe_target,
            "host_probe_builder": "src/tools/build_host_probe.py",
            "makefile": "not_required_for_generated_template",
        },
        "coverage_domain": "toggle_real_subset_bitmap",
        "target_scope": [
            {
                "target": spec.target_name,
                "status": "candidate",
                "launch_template": template_path,
                "coverage_manifest": manifest_path,
                "mdir": spec.resolved_mdir,
                "cpu_reference_state": f"{spec.resolved_mdir}/{spec.target_name}_cpu_repeat_1x1.bin",
                "gpu_candidate_state": f"{spec.resolved_mdir}/{spec.target_name}_gpu_from_cpu_init_1x1.bin",
            }
        ],
        "coverage_output_contract": {
            "strict_output_words": [
                {"prefix": "real_toggle_subset_word", "count": 18},
                {"prefix": "toggle_bitmap_word", "count": 3},
                {"prefix": "focused_wave_word", "count": 8},
            ],
            "manifest_region_words": {
                "prefix": "real_toggle_subset_word",
                "count": 18,
            },
            "total_words_per_state": 29,
            "total_bytes_per_state": 116,
            "acceptance_policy": "coverage_output_equivalence",
        },
        "planned_shapes": [
            {"name": "minimum_overhead_probe", "nstates": 1, "steps": 1},
            {"name": "state_parallel_probe", "nstates": 64, "steps": 1},
            {"name": "single_state_repeated_probe", "nstates": 1, "steps": 64},
        ],
        "acceptance_policy": {
            "overlay_and_manifest_exist": True,
            "cpu_reference_built": False,
            "gpu_cubin_built": False,
            "cpu_vs_hybrid_compared": False,
            "coverage_output_equivalence_required": True,
            "host_probe_glue_generated_from_template": True,
            "makefile_target_required": False,
            "speedup_claim_allowed_by_gate_alone": False,
        },
        "non_claims": [
            "not raw full-state equality",
            "not broad speedup",
            "not correctness equivalence beyond scoped output words",
        ],
        "next_task": f"run_{spec.target_name}_first_cpu_vs_hybrid_compare",
    }


def generated_payloads(spec: HybridConfigSpec) -> dict[str, dict]:
    paths = default_paths(spec)
    return {
        paths["manifest"]: coverage_manifest(spec),
        paths["template"]: launch_template(spec, gate_path=paths["gate"], manifest_path=paths["manifest"]),
        paths["gate"]: benchmark_gate(spec, manifest_path=paths["manifest"], template_path=paths["template"]),
    }


def write_payloads(payloads: dict[str, dict], *, dry_run: bool = False) -> None:
    for raw_path, payload in payloads.items():
        path = REPO_ROOT / raw_path
        print(f"write: {raw_path}")
        if dry_run:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
