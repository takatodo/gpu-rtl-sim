#!/usr/bin/env python3
"""Build a PULP/NoC heavy RTL candidate evidence matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from results_reproduction_io import display_path, parse_hybrid_report, sanitize_local_absolute_paths

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT = Path("reports/heavy_rtl_candidate_matrix.json")

DEFAULT_CANDIDATES = [
    {
        "name": "pulp_ita_mha",
        "family": "PULP_ITA",
        "class": "attention_mha",
        "template": "config/slice_launch_templates/pulp_ita_mha.json",
        "source_parallel_shape": "64x1",
        "single_state_shape": "1x64",
        "cpu_report": "reports/pulp_ita_mha_cpu_repeat_64x1.json",
        "hybrid_report": "reports/pulp_ita_mha_hybrid_64x1.txt",
        "compare_report": "reports/pulp_ita_mha_cpu_vs_hybrid_64x1_coverage_output_compare.json",
        "next_measure_command": "python3 src/tools/hybrid_template_repeat_median.py config/slice_launch_templates/pulp_ita_mha.json --shape 64x1 --repeat 3 --write-report --report-out reports/pulp_ita_mha_64x1_median.json",
    },
    {
        "name": "pulp_paged_attention_kv_score",
        "family": "PULP_ITA",
        "class": "paged_attention_score",
        "template": "config/slice_launch_templates/pulp_paged_attention_kv_score.json",
        "source_parallel_shape": "64x1",
        "single_state_shape": "1x64",
        "repeat_report": "reports/pulp_paged_attention_kv_score_64x1_median.json",
        "next_measure_command": "python3 src/tools/hybrid_template_repeat_median.py config/slice_launch_templates/pulp_paged_attention_kv_score.json --shape 64x1 --repeat 3 --write-report --report-out reports/pulp_paged_attention_kv_score_64x1_median.json",
    },
    {
        "name": "tlul_socket_1n",
        "family": "OpenTitan_TLUL",
        "class": "fanout_socket",
        "template": "config/slice_launch_templates/tlul_socket_1n.json",
        "source_parallel_shape": "32x1",
        "single_state_shape": "1x56",
        "repeat_report": "reports/tlul_socket_1n_32x1_median.json",
        "next_measure_command": "python3 src/tools/hybrid_template_repeat_median.py config/slice_launch_templates/tlul_socket_1n.json --shape 32x1 --repeat 3 --write-report --report-out reports/tlul_socket_1n_32x1_median.json",
    },
    {
        "name": "tlul_socket_m1",
        "family": "OpenTitan_TLUL",
        "class": "arbiter_socket",
        "template": "config/slice_launch_templates/tlul_socket_m1.json",
        "source_parallel_shape": "32x1",
        "single_state_shape": "1x56",
        "repeat_report": "reports/tlul_socket_m1_32x1_median.json",
        "next_measure_command": "python3 src/tools/hybrid_template_repeat_median.py config/slice_launch_templates/tlul_socket_m1.json --shape 32x1 --repeat 3 --write-report --report-out reports/tlul_socket_m1_32x1_median.json",
    },
    {
        "name": "tlul_fifo_sync",
        "family": "OpenTitan_TLUL",
        "class": "protocol_fifo",
        "template": "config/slice_launch_templates/tlul_fifo_sync.json",
        "source_parallel_shape": "32x1",
        "single_state_shape": "1x56",
        "next_measure_command": "python3 src/tools/hybrid_template_repeat_median.py config/slice_launch_templates/tlul_fifo_sync.json --shape 32x1 --repeat 3 --write-report --report-out reports/tlul_fifo_sync_32x1_median.json",
    },
    {
        "name": "blackparrot_bsg_wormhole_router",
        "family": "BlackParrot_BaseJump_NoC",
        "class": "wormhole_router",
        "source": "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_wormhole_router.sv",
        "template": "config/slice_launch_templates/blackparrot_bsg_wormhole_router.json",
        "source_parallel_shape": "packet_batch",
        "single_state_shape": "single_packet_stream",
        "repeat_report": "reports/blackparrot_bsg_wormhole_router_256x1_median.json",
        "shape_sweep_reports": [
            "reports/blackparrot_bsg_wormhole_router_32x1_median.json",
            "reports/blackparrot_bsg_wormhole_router_64x1_median.json",
            "reports/blackparrot_bsg_wormhole_router_128x1_median.json",
            "reports/blackparrot_bsg_wormhole_router_256x1_median.json",
        ],
        "source_closure_plan": {
            "status": "source_backed_shape_sweep_promote_256x1_resident_template_surface_defined_patch_script_next",
            "required_source_files": [
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_defines.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_noc_links.svh",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_wormhole_router.svh",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_wormhole_router_pkg.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_wormhole_router.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_wormhole_router_decoder_dor.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_wormhole_router_input_control.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_wormhole_router_output_control.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_two_fifo.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_concentrate_static.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_unconcentrate_static.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_array_concentrate_static.sv",
                "third_party/rtlmeter/designs/BlackParrot/src/basejump_stl/bsg_transpose.sv",
            ],
            "coverage_overlay": "overlays/rtlmeter/designs/BlackParrot/src/bsg_wormhole_router_gpu_cov_tb.sv",
            "coverage_manifest": "overlays/rtlmeter/designs/BlackParrot/tests/bsg_wormhole_router_coverage_regions.json",
            "coverage_gate": "config/scaling_gates/blackparrot_bsg_wormhole_router_source_gate.json",
            "resident_multistep_definition_gate": "config/scaling_gates/blackparrot_bsg_wormhole_router_resident_multistep_definition.json",
            "minimum_smoke": "32x1, 64x1, 128x1, and 256x1 packet-pattern coverage_output_equivalence passed across repeat-count-3 median samples; the resident/multi-step definition gate now has a template command surface and is blocked only on materializing the packet-pattern patch script before execution",
        },
        "next_measure_command": "materialize_blackparrot_bsg_wormhole_router_packet_pattern_patch_script_or_record_named_blocker",
    },
]


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _repo_path(raw: str | None) -> Path | None:
    if raw is None:
        return None
    return REPO_ROOT / raw


def _display(raw: str | None) -> str | None:
    path = _repo_path(raw)
    if path is None:
        return None
    return display_path(path, repo_root=REPO_ROOT)


def _template_summary(template_path: str | None) -> dict[str, Any]:
    path = _repo_path(template_path)
    if path is None or not path.exists():
        return {"present": False, "path": template_path}
    template = _load_json(path)
    assert template is not None
    runner = template.get("runner_args_template") if isinstance(template.get("runner_args_template"), dict) else {}
    static = template.get("static_features") if isinstance(template.get("static_features"), dict) else {}
    source_files = template.get("source_files")
    source_files_list = source_files if isinstance(source_files, list) else []
    closure = template.get("source_closure") if isinstance(template.get("source_closure"), dict) else {}
    return {
        "present": True,
        "path": display_path(path, repo_root=REPO_ROOT),
        "target": template.get("target"),
        "status": template.get("status"),
        "top_module": template.get("top_module") or runner.get("top_module"),
        "source_gate": template.get("source_gate"),
        "source_files_count": len(source_files_list),
        "source_closure_status": closure.get("status") or ("implicit_template" if source_files_list else None),
        "coverage_tb_path": runner.get("coverage_tb_path") or static.get("coverage_tb_path"),
        "coverage_manifest_path": runner.get("coverage_manifest_path") or static.get("coverage_manifest_path"),
        "rtl_path": runner.get("rtl_path") or static.get("rtl_path"),
        "first_pass_result": template.get("first_pass_result") if isinstance(template.get("first_pass_result"), dict) else None,
        "depth_result": template.get("depth_result") if isinstance(template.get("depth_result"), dict) else None,
        "execution_profiles": template.get("execution_profiles") if isinstance(template.get("execution_profiles"), dict) else {},
        "static_features": {
            "region_count": static.get("region_count"),
            "required_output_count": static.get("required_output_count"),
            "tb_output_count": static.get("tb_output_count"),
            "search_prior_class": static.get("search_prior_class"),
            "structural_connectivity_class": (
                static.get("structural_connectivity", {}).get("structural_connectivity_class")
                if isinstance(static.get("structural_connectivity"), dict)
                else None
            ),
        },
    }


def _coverage_summary(compare_report: str | None) -> dict[str, Any] | None:
    path = _repo_path(compare_report)
    if path is None or not path.exists():
        return None
    payload = _load_json(path)
    assert payload is not None
    coverage = payload.get("coverage_output_policy") if isinstance(payload.get("coverage_output_policy"), dict) else {}
    selected = payload.get("selected_acceptance_policy") if isinstance(payload.get("selected_acceptance_policy"), dict) else {}
    return {
        "report": display_path(path, repo_root=REPO_ROOT),
        "match": payload.get("match"),
        "mismatch_count": payload.get("mismatch_count"),
        "coverage_output_equivalence_passed": (
            payload.get("coverage_output_equivalence_passed")
            if payload.get("coverage_output_equivalence_passed") is not None
            else coverage.get("passed")
        ),
        "coverage_output_mismatch_count": (
            payload.get("coverage_output_mismatch_count")
            if payload.get("coverage_output_mismatch_count") is not None
            else coverage.get("mismatch_count")
        ),
        "coverage_output_compared_word_count": (
            payload.get("coverage_output_compared_word_count")
            if payload.get("coverage_output_compared_word_count") is not None
            else coverage.get("compared_word_count")
        ),
        "coverage_output_compared_byte_count": (
            payload.get("coverage_output_compared_byte_count")
            if payload.get("coverage_output_compared_byte_count") is not None
            else coverage.get("compared_byte_count")
        ),
        "selected_acceptance_policy": selected.get("name") or coverage.get("acceptance_policy"),
        "selected_acceptance_passed": selected.get("passed") if selected else coverage.get("passed"),
    }


def _timing_summary(cpu_report: str | None, hybrid_report: str | None) -> dict[str, Any] | None:
    cpu_path = _repo_path(cpu_report)
    hybrid_path = _repo_path(hybrid_report)
    if cpu_path is None or hybrid_path is None or not cpu_path.exists() or not hybrid_path.exists():
        return None
    cpu = _load_json(cpu_path)
    assert cpu is not None
    hybrid = parse_hybrid_report(hybrid_path, repo_root=REPO_ROOT)
    cpu_ms = cpu.get("elapsed_ms")
    if not isinstance(cpu_ms, int | float):
        return None
    wall_ms = hybrid["hybrid_wall_ms"]
    kernel_ms = hybrid["gpu_kernel_total_ms"]
    return {
        "cpu_report": display_path(cpu_path, repo_root=REPO_ROOT),
        "hybrid_report": display_path(hybrid_path, repo_root=REPO_ROOT),
        "cpu_elapsed_ms": float(cpu_ms),
        "hybrid_wall_ms": wall_ms,
        "gpu_kernel_total_ms": kernel_ms,
        "cpu_to_hybrid_wall_speedup": float(cpu_ms) / wall_ms if wall_ms else None,
        "cpu_to_gpu_kernel_speedup": float(cpu_ms) / kernel_ms if kernel_ms else None,
    }


def _repeat_summary(repeat_report: str | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    path = _repo_path(repeat_report)
    if path is None or not path.exists():
        return None, None
    payload = _load_json(path)
    assert payload is not None
    median = payload.get("median") if isinstance(payload.get("median"), dict) else {}
    last_sample = payload.get("last_sample") if isinstance(payload.get("last_sample"), dict) else {}
    coverage = last_sample.get("coverage_output") if isinstance(last_sample.get("coverage_output"), dict) else None
    timing = {
        "source": "repeat_median_report",
        "repeat_report": display_path(path, repo_root=REPO_ROOT),
        "status": payload.get("status"),
        "shape": payload.get("shape"),
        "repeat_count": payload.get("repeat_count"),
        "coverage_output_equivalence_all_passed": payload.get("coverage_output_equivalence_all_passed"),
        "cpu_elapsed_ms": median.get("cpu_elapsed_ms"),
        "hybrid_wall_ms": median.get("hybrid_wall_ms"),
        "gpu_kernel_total_ms": median.get("gpu_kernel_total_ms"),
        "cpu_to_hybrid_wall_speedup": median.get("cpu_to_hybrid_wall_speedup"),
        "cpu_to_gpu_kernel_speedup": median.get("cpu_to_gpu_kernel_speedup"),
    }
    return timing, coverage


def _shape_sweep_summary(repeat_reports: list[str] | None) -> list[dict[str, Any]]:
    if not isinstance(repeat_reports, list):
        return []
    summaries: list[dict[str, Any]] = []
    for report in repeat_reports:
        timing, coverage = _repeat_summary(report)
        if timing is None:
            summaries.append({"repeat_report": report, "present": False})
            continue
        summaries.append(
            {
                "present": True,
                "repeat_report": timing["repeat_report"],
                "shape": timing.get("shape"),
                "repeat_count": timing.get("repeat_count"),
                "coverage_output_equivalence_all_passed": timing.get(
                    "coverage_output_equivalence_all_passed"
                ),
                "coverage_output_mismatch_count": (
                    coverage.get("coverage_output_mismatch_count")
                    if isinstance(coverage, dict)
                    else None
                ),
                "cpu_to_hybrid_wall_speedup": timing.get("cpu_to_hybrid_wall_speedup"),
                "cpu_to_gpu_kernel_speedup": timing.get("cpu_to_gpu_kernel_speedup"),
                "hybrid_wall_ms": timing.get("hybrid_wall_ms"),
                "gpu_kernel_total_ms": timing.get("gpu_kernel_total_ms"),
            }
        )
    return summaries


def _profile_timing(template: dict[str, Any]) -> dict[str, Any] | None:
    profiles = template.get("execution_profiles")
    if not isinstance(profiles, dict):
        return None
    profile = profiles.get("multi_step") or profiles.get("campaign") or profiles.get("single_step")
    if not isinstance(profile, dict):
        return None
    cpu = profile.get("median_cpu_ms_per_rep")
    gpu = profile.get("median_gpu_ms_per_rep")
    if not isinstance(cpu, int | float) or not isinstance(gpu, int | float):
        return None
    return {
        "source": "template_execution_profile",
        "status": profile.get("status"),
        "scenario": profile.get("scenario"),
        "nstates": profile.get("nstates"),
        "sequential_steps": profile.get("sequential_steps"),
        "cpu_elapsed_ms": float(cpu),
        "hybrid_wall_ms": float(gpu),
        "cpu_to_hybrid_wall_speedup": float(cpu) / float(gpu) if gpu else None,
        "compact_match": profile.get("compact_match"),
    }


def _source_closure_summary(candidate: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    source_path = _display(candidate.get("source"))
    source_present = _repo_path(candidate.get("source")).exists() if candidate.get("source") else None
    static = template.get("static_features") if isinstance(template.get("static_features"), dict) else {}
    if template.get("present") is not True:
        return {
            "status": "source_present_template_missing" if source_present else "template_missing_source_unchecked",
            "source": source_path,
            "source_present": source_present,
            "template_present": False,
            "source_files_count": 0,
        }
    status = template.get("source_closure_status") or static.get("structural_connectivity_class")
    if status is None and template.get("rtl_path"):
        status = "source_backed_template_closure_not_recorded"
    if status is None:
        status = "template_present_source_closure_not_recorded"
    return {
        "status": status,
        "source": source_path or template.get("rtl_path"),
        "source_present": source_present,
        "template_present": True,
        "source_files_count": template.get("source_files_count", 0),
        "source_gate": template.get("source_gate"),
        "rtl_path": template.get("rtl_path"),
    }


def _policy(row: dict[str, Any]) -> dict[str, Any]:
    template = row["template"]
    timing = row.get("timing_evidence")
    coverage = row.get("compare_evidence")
    first_pass = template.get("first_pass_result") if isinstance(template.get("first_pass_result"), dict) else None
    template_present = template.get("present") is True
    coverage_pass = (
        isinstance(coverage, dict)
        and coverage.get("coverage_output_equivalence_passed") is True
        and coverage.get("coverage_output_mismatch_count") == 0
    )
    first_pass_ok = (
        isinstance(first_pass, dict)
        and first_pass.get("status") == "passed"
        and first_pass.get("mismatch_count", 0) == 0
    )
    speedup = timing.get("cpu_to_hybrid_wall_speedup") if isinstance(timing, dict) else None
    if not template_present:
        return {
            "decision": "template_required_before_measurement",
            "reason": "source candidate exists but no slice launch template is present",
        }
    if isinstance(speedup, int | float) and speedup >= 2.0 and (coverage_pass or first_pass_ok):
        return {
            "decision": "promote_state_parallel_measurement",
            "reason": "state-parallel timing is GPU/hybrid favorable and coverage-output evidence is available",
        }
    if first_pass_ok and timing is None:
        return {
            "decision": "measure_repeat_median_next",
            "reason": "correctness/depth evidence exists but timing evidence is missing",
        }
    if timing is not None:
        return {
            "decision": "resident_or_shape_sweep_required",
            "reason": "timing exists but does not yet prove a strong state-parallel promotion",
        }
    return {
        "decision": "build_run_compare_required",
        "reason": "template exists but current evidence is not enough for promote/fallback classification",
    }


def candidate_row(candidate: dict[str, Any]) -> dict[str, Any]:
    template = _template_summary(candidate.get("template"))
    source_closure = _source_closure_summary(candidate, template)
    repeat_timing, repeat_coverage = _repeat_summary(candidate.get("repeat_report"))
    shape_sweep = _shape_sweep_summary(candidate.get("shape_sweep_reports"))
    timing = repeat_timing or _timing_summary(candidate.get("cpu_report"), candidate.get("hybrid_report"))
    if timing is None:
        timing = _profile_timing(template)
    row: dict[str, Any] = {
        "name": candidate["name"],
        "family": candidate["family"],
        "candidate_class": candidate["class"],
        "source": _display(candidate.get("source")),
        "source_closure": source_closure,
        "source_closure_status": source_closure["status"],
        "template": template,
        "source_parallel_shape": candidate.get("source_parallel_shape"),
        "single_state_repeated_step_shape": candidate.get("single_state_shape"),
        "timing_evidence": timing,
        "shape_sweep_evidence": shape_sweep,
        "compare_evidence": repeat_coverage or _coverage_summary(candidate.get("compare_report")),
        "next_measure_command": sanitize_local_absolute_paths(str(candidate.get("next_measure_command"))),
        "source_closure_plan": candidate.get("source_closure_plan"),
        "non_claims": [
            "not broad arbitrary RTL acceleration evidence",
            "coverage-output equivalence is separate from raw full-state equality",
            "policy is a scoped next-action classifier, not automatic optimal GPU allocation",
        ],
    }
    row["policy"] = _policy(row)
    return row


def build_matrix(candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = [candidate_row(candidate) for candidate in (candidates or DEFAULT_CANDIDATES)]
    status_counts: dict[str, int] = {}
    for row in rows:
        decision = str(row.get("policy", {}).get("decision"))
        status_counts[decision] = status_counts.get(decision, 0) + 1
    next_commands = [
        {
            "name": row["name"],
            "policy": row["policy"]["decision"],
            "command": row["next_measure_command"],
        }
        for row in rows
        if row["policy"]["decision"] in {
            "measure_repeat_median_next",
            "build_run_compare_required",
            "template_required_before_measurement",
        }
    ]
    return {
        "schema_version": 1,
        "surface": "heavy_rtl_candidate_matrix",
        "status": "heavy_rtl_candidate_matrix_ready",
        "row_count": len(rows),
        "pulp_row_count": sum(1 for row in rows if str(row.get("family")).startswith("PULP")),
        "noc_tlul_row_count": sum(
            1
            for row in rows
            if "TLUL" in str(row.get("family")) or "NoC" in str(row.get("family")) or row.get("candidate_class") == "wormhole_router"
        ),
        "policy_counts": status_counts,
        "rows": rows,
        "next_minimal_measurements": next_commands[:5],
        "non_claims": [
            "not a new timing run",
            "not broad speedup evidence",
            "not native Verilator option support",
            "not automatic dependency inference for arbitrary RTL",
            "not automatic optimal GPU allocation",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    try:
        report = build_matrix()
    except Exception as exc:
        print(str(exc))
        return 2
    if args.write_report:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "heavy_rtl_candidate_matrix_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
