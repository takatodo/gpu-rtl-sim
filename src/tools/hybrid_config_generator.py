#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from hybrid_config_benchmark import benchmark_gate
from hybrid_config_spec import HybridConfigSpec, default_gate_name, default_paths


REPO_ROOT = Path(__file__).resolve().parents[2]


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
