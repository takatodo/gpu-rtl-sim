"""Benchmark gate payloads for generated hybrid config."""

from __future__ import annotations

from hybrid_config_spec import HybridConfigSpec


def _benchmark_target_scope(spec: HybridConfigSpec, *, manifest_path: str, template_path: str) -> list[dict[str, object]]:
    return [
        {
            "target": spec.target_name,
            "status": "candidate",
            "launch_template": template_path,
            "coverage_manifest": manifest_path,
            "mdir": spec.resolved_mdir,
            "cpu_reference_state": f"{spec.resolved_mdir}/{spec.target_name}_cpu_repeat_1x1.bin",
            "gpu_candidate_state": f"{spec.resolved_mdir}/{spec.target_name}_gpu_from_cpu_init_1x1.bin",
        }
    ]


def _benchmark_coverage_output_contract() -> dict:
    return {
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
    }


def _benchmark_acceptance_policy() -> dict:
    return {
        "overlay_and_manifest_exist": True,
        "cpu_reference_built": False,
        "gpu_cubin_built": False,
        "cpu_vs_hybrid_compared": False,
        "coverage_output_equivalence_required": True,
        "host_probe_glue_generated_from_template": True,
        "makefile_target_required": False,
        "speedup_claim_allowed_by_gate_alone": False,
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
        "target_scope": _benchmark_target_scope(
            spec,
            manifest_path=manifest_path,
            template_path=template_path,
        ),
        "coverage_output_contract": _benchmark_coverage_output_contract(),
        "planned_shapes": [
            {"name": "minimum_overhead_probe", "nstates": 1, "steps": 1},
            {"name": "state_parallel_probe", "nstates": 64, "steps": 1},
            {"name": "single_state_repeated_probe", "nstates": 1, "steps": 64},
        ],
        "acceptance_policy": _benchmark_acceptance_policy(),
        "non_claims": [
            "not raw full-state equality",
            "not broad speedup",
            "not correctness equivalence beyond scoped output words",
        ],
        "next_task": f"run_{spec.target_name}_first_cpu_vs_hybrid_compare",
    }
