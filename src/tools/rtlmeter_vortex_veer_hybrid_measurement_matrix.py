#!/usr/bin/env python3
"""Summarize Vortex and VeeR RTLMeter hybrid measurement state."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


TARGETS = [
    {
        "case": "Vortex:mini:hello",
        "design": "Vortex",
        "configuration": "mini",
        "test": "hello",
        "descriptor": Path("third_party/rtlmeter/designs/Vortex/descriptor.yaml"),
        "kind": "vortex_first_gate",
    },
    {
        "case": "VeeR-EH1:default:hello",
        "design": "VeeR-EH1",
        "configuration": "default",
        "test": "hello",
        "descriptor": Path("third_party/rtlmeter/designs/VeeR-EH1/descriptor.yaml"),
        "kind": "veer_unimplemented",
    },
    {
        "case": "VeeR-EH2:default:hello",
        "design": "VeeR-EH2",
        "configuration": "default",
        "test": "hello",
        "descriptor": Path("third_party/rtlmeter/designs/VeeR-EH2/descriptor.yaml"),
        "kind": "veer_unimplemented",
    },
    {
        "case": "VeeR-EL2:default:hello",
        "design": "VeeR-EL2",
        "configuration": "default",
        "test": "hello",
        "descriptor": Path("third_party/rtlmeter/designs/VeeR-EL2/descriptor.yaml"),
        "kind": "veer_el2",
    },
]

EL2_TIMING_REPORTS = [
    Path("reports/rtlmeter_veer_el2_timing_nstates16.json"),
    Path("reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json"),
    Path("reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates32.json"),
    Path("reports/rtlmeter_veer_el2_timing_pair_cycle_state_local_fused_nstates32.json"),
]
EL2_BRIDGE_REPORT = Path("reports/rtlmeter_veer_el2_sidecar_bridge.json")
VEER_FAMILY_SURFACE_AUDIT_REPORT = Path("reports/rtlmeter_veer_family_surface_audit.json")
VORTEX_READINESS_REPORT = Path("reports/rtlmeter_vortex_first_gate_readiness.json")
VORTEX_BRIDGE_REPORT = Path("reports/rtlmeter_vortex_dpi_memory_bridge_review.json")
VORTEX_CPU_REFERENCE_REPORT = Path("reports/rtlmeter_vortex_cpu_reference_summary.json")
VORTEX_HYBRID_CANDIDATE_REPORT = Path("reports/rtlmeter_vortex_hybrid_candidate_summary.json")
VORTEX_PTX_MODULE_LOAD_DIAGNOSTIC_REPORT = Path("reports/rtlmeter_vortex_ptx_module_load_diagnostic.json")
VORTEX_TIMING_REPORT = Path("reports/rtlmeter_vortex_timing.json")


def _veer_stem(design: str) -> str:
    return design.lower().replace("-", "_")


def _veer_state_layout_report_path(design: str) -> Path:
    return Path(f"reports/rtlmeter_{_veer_stem(design)}_state_layout_inspection.json")


def _veer_sidecar_bridge_report_path(design: str) -> Path:
    return Path(f"reports/rtlmeter_{_veer_stem(design)}_sidecar_bridge.json")


def _veer_root_offset_review_report_path(design: str) -> Path:
    return Path(f"reports/rtlmeter_{_veer_stem(design)}_root_offset_review.json")


def _load_json(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, Mapping) else None


def _load_yaml(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, Mapping) else None


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _descriptor_summary(path: Path, *, repo_root: Path, configuration: str, test: str) -> dict[str, Any]:
    descriptor = _load_yaml(path)
    if descriptor is None:
        return {
            "path": _display_path(path, repo_root=repo_root),
            "exists": False,
            "configuration_exists": False,
            "test_exists": False,
            "source_count": None,
            "include_count": None,
            "cpp_source_count": None,
        }
    compile_section = _mapping(descriptor.get("compile"))
    configs = _mapping(descriptor.get("configurations"))
    config = _mapping(configs.get(configuration))
    config_execute = _mapping(config.get("execute"))
    config_tests = _mapping(config_execute.get("tests"))
    base_tests = _mapping(_mapping(descriptor.get("execute")).get("tests"))
    return {
        "path": _display_path(path, repo_root=repo_root),
        "exists": True,
        "configuration_exists": configuration in configs,
        "test_exists": test in base_tests,
        "configuration_test_exists": test in config_tests,
        "top_module": compile_section.get("topModule"),
        "main_clock": compile_section.get("mainClock"),
        "source_count": len(compile_section.get("verilogSourceFiles", [])),
        "include_count": len(compile_section.get("verilogIncludeFiles", [])),
        "cpp_source_count": len(compile_section.get("cppSourceFiles", [])),
    }


def _el2_best_timing(repo_root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for report_path in EL2_TIMING_REPORTS:
        payload = _load_json(repo_root / report_path)
        if payload is None:
            rows.append({"report": report_path.as_posix(), "status": "missing"})
            continue
        summary = _mapping(payload.get("summary"))
        row = {
            "report": report_path.as_posix(),
            "status": payload.get("status"),
            "correctness_passed": summary.get("all_sidecar_samples_passed_correctness"),
            "sidecar_state_count": summary.get("sidecar_parallel_state_count"),
            "sidecar_wall_s_median": _number(summary.get("sidecar_wall_s_median")),
            "gpu_kernel_ms_total_median": _number(summary.get("gpu_kernel_ms_total_median")),
            "cpu_parallel_wall_s": _number(summary.get("cpu_parallel_wall_s")),
            "sidecar_vs_cpu_parallel_ratio": _number(summary.get("sidecar_vs_cpu_parallel_ratio")),
            "serial_cpu_wall_time_outcome": summary.get("serial_cpu_wall_time_outcome"),
            "cpu_parallel_wall_time_outcome": summary.get("cpu_parallel_wall_time_outcome"),
            "speedup_claimed": payload.get("speedup_claimed"),
        }
        rows.append(row)
    valid = [
        row
        for row in rows
        if row.get("status") == "passed"
        and row.get("correctness_passed") is True
        and isinstance(row.get("sidecar_wall_s_median"), float)
    ]
    best = min(valid, key=lambda row: row["sidecar_wall_s_median"]) if valid else None
    return best, rows


def _veer_family_audit_by_design(repo_root: Path) -> dict[str, Mapping[str, Any]]:
    audit = _load_json(repo_root / VEER_FAMILY_SURFACE_AUDIT_REPORT)
    if audit is None:
        return {}
    rows = audit.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, str):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("design"), str):
            result[str(row["design"])] = row
    return result


def _veer_state_layout_probe(repo_root: Path, design: str) -> dict[str, Any] | None:
    report_path = _veer_state_layout_report_path(design)
    report = _load_json(repo_root / report_path)
    if report is None:
        return None
    probe = _mapping(_mapping(report.get("detected_layout")).get("root_header_probe"))
    if not probe:
        return None
    return {
        "state_layout_report": report_path.as_posix(),
        "root_header_observed": probe.get("root_header_observed"),
        "root_layout_probe_performed": probe.get("root_layout_probe_performed"),
        "root_offset_probe_performed": probe.get("root_offset_probe_performed"),
        "root_offset_probe_error": probe.get("root_offset_probe_error"),
        "observed_marker_group_count": probe.get("observed_marker_group_count"),
        "mapped_marker_offset_group_count": probe.get("mapped_marker_offset_group_count"),
        "missing_marker_groups": probe.get("missing_marker_groups"),
        "root_field_offsets_reviewed": probe.get("root_field_offsets_reviewed"),
        "state_layout_ready": report.get("state_layout_ready"),
        "missing_build_context": report.get("missing_build_context"),
    }


def _veer_root_offset_review(repo_root: Path, design: str) -> dict[str, Any] | None:
    report_path = _veer_root_offset_review_report_path(design)
    report = _load_json(repo_root / report_path)
    if report is None:
        return None
    return {
        "root_offset_review_report": report_path.as_posix(),
        "status": report.get("status"),
        "root_offset_review_performed": report.get("root_offset_review_performed"),
        "root_obj_dir_variant": report.get("root_obj_dir_variant"),
        "root_field_offsets_reviewed_for_target": report.get("root_field_offsets_reviewed_for_target"),
        "root_observable_offset_candidates_complete": report.get("root_observable_offset_candidates_complete"),
        "missing_reviewed_root_offset_abi_fields": report.get("missing_reviewed_root_offset_abi_fields"),
        "observed_marker_groups": report.get("observed_marker_groups"),
        "missing_marker_groups": report.get("missing_marker_groups"),
        "missing_build_context": report.get("missing_build_context"),
    }


def _veer_sidecar_bridge_preflight(repo_root: Path, design: str) -> dict[str, Any] | None:
    report_path = _veer_sidecar_bridge_report_path(design)
    report = _load_json(repo_root / report_path)
    if report is None:
        return None
    return {
        "sidecar_bridge_report": report_path.as_posix(),
        "status": report.get("status"),
        "sidecar_bridge_preflight_ready": report.get("sidecar_bridge_preflight_ready"),
        "sidecar_bridge_invoked": report.get("sidecar_bridge_invoked"),
        "sidecar_observables_ready": report.get("sidecar_observables_ready"),
        "run_vl_hybrid_stage_trace": report.get("run_vl_hybrid_stage_trace"),
        "ptxas_probe": report.get("ptxas_probe"),
        "entry_pruned_module_probe": report.get("entry_pruned_module_probe"),
        "cpu_reference_observables_ready": report.get("cpu_reference_observables_ready"),
        "missing_build_context": report.get("missing_build_context"),
        "gpu_execution_claimed": report.get("gpu_execution_claimed"),
        "timing_measured": report.get("timing_measured"),
        "speedup_claimed": report.get("speedup_claimed"),
    }


def _vortex_status(repo_root: Path) -> dict[str, Any]:
    readiness = _load_json(repo_root / VORTEX_READINESS_REPORT)
    bridge = _load_json(repo_root / VORTEX_BRIDGE_REPORT)
    cpu_reference = _load_json(repo_root / VORTEX_CPU_REFERENCE_REPORT)
    hybrid_candidate = _load_json(repo_root / VORTEX_HYBRID_CANDIDATE_REPORT)
    ptx_module_load_diagnostic = _load_json(repo_root / VORTEX_PTX_MODULE_LOAD_DIAGNOSTIC_REPORT)
    vortex_timing = _load_json(repo_root / VORTEX_TIMING_REPORT)
    missing: list[str] = []
    recommended_sequence: list[str] = []
    if readiness is None:
        missing.append("vortex_first_gate_readiness_report")
    else:
        missing.extend(str(item) for item in readiness.get("missing_prerequisites", []) if item)
        raw_sequence = readiness.get("recommended_sequence")
        if isinstance(raw_sequence, Sequence) and not isinstance(raw_sequence, str):
            recommended_sequence = [str(item) for item in raw_sequence if item]
    if bridge is None:
        missing.append("vortex_dpi_memory_bridge_review_report")
    else:
        missing.extend(str(item) for item in bridge.get("missing_prerequisites", []) if item not in missing)
    cpu_reference_ready = (
        isinstance(cpu_reference, Mapping)
        and cpu_reference.get("status") == "cpu_reference_passed"
        and cpu_reference.get("cpu_reference_ready_for_hybrid_compare") is True
    )
    if not cpu_reference_ready and "cpu_reference_report.vortex" not in missing:
        missing.insert(0, "cpu_reference_report.vortex")
    hybrid_candidate_status = hybrid_candidate.get("status") if isinstance(hybrid_candidate, Mapping) else None
    if hybrid_candidate_status == "hybrid_candidate_blocked_invalid_verilator_option":
        if "path_selected_sidecar_capable_verilator_or_wrapper" not in missing:
            missing.insert(1 if cpu_reference_ready else 0, "path_selected_sidecar_capable_verilator_or_wrapper")
    if hybrid_candidate_status == "hybrid_candidate_blocked_missing_reviewed_vortex_sidecar_context":
        if "reviewed_vortex_sidecar_context_for_wrapper_handoff" not in missing:
            missing.insert(1 if cpu_reference_ready else 0, "reviewed_vortex_sidecar_context_for_wrapper_handoff")
    if hybrid_candidate_status == "hybrid_candidate_blocked_missing_vortex_authority_registry_source_closure":
        if "reviewed_vortex_authority_registry_source_closure" not in missing:
            missing.insert(1 if cpu_reference_ready else 0, "reviewed_vortex_authority_registry_source_closure")
    if hybrid_candidate_status == "hybrid_candidate_blocked_sidecar_verilate_execution":
        if "direct_sidecar_verilate_execution_or_vsim_proxy_for_vortex" not in missing:
            missing.insert(1 if cpu_reference_ready else 0, "direct_sidecar_verilate_execution_or_vsim_proxy_for_vortex")
    if hybrid_candidate_status == "hybrid_candidate_stdout_cycles_observed_proxy_handoff_blocked":
        if "reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export" not in missing:
            missing.insert(
                1 if cpu_reference_ready else 0,
                "reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
            )
    if hybrid_candidate_status == "hybrid_candidate_proxy_handoff_observed_timing_missing":
        if (
            isinstance(hybrid_candidate, Mapping)
            and hybrid_candidate.get("observable_authority_audit_status")
            == "observable_authority_audit_proxy_and_fake_ready_real_runtime_missing"
        ):
            if "real_runtime_observable_authority" not in missing:
                missing.insert(1 if cpu_reference_ready else 0, "real_runtime_observable_authority")
        elif "hybrid_observable_authority" not in missing:
            missing.insert(1 if cpu_reference_ready else 0, "hybrid_observable_authority")
    if isinstance(hybrid_candidate, Mapping) and hybrid_candidate.get("real_verilator_memory_helper_call_observed") is True:
        memory_helper_prereqs = {
            "lowered_tb_mem_access_device_helper_integration",
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
        }
        missing = [item for item in missing if item not in memory_helper_prereqs]
    timing_passed = (
        isinstance(vortex_timing, Mapping)
        and vortex_timing.get("status") == "passed"
        and vortex_timing.get("timing_measured") is True
        and vortex_timing.get("correctness_passed") is True
        and vortex_timing.get("runtime_authority") is True
    )
    if timing_passed:
        timing_prereqs = {"cpu_vs_hybrid_timing_report.vortex", "cpu_vs_hybrid_timing_report"}
        missing = [item for item in missing if item not in timing_prereqs]
    next_required_boundary = (
        hybrid_candidate.get("next_required_boundary")
        if isinstance(hybrid_candidate, Mapping)
        else None
    )
    ptx_diagnostic_next = (
        ptx_module_load_diagnostic.get("next_required_boundary")
        if isinstance(ptx_module_load_diagnostic, Mapping)
        and ptx_module_load_diagnostic.get("ptxas_status") == "ptxas_timeout"
        else None
    )
    next_action = str(next_required_boundary) if next_required_boundary else recommended_sequence[0] if recommended_sequence else (
        "integrate_lowered_tb_mem_access_with_vortex_device_helper"
        if "lowered_tb_mem_access_device_helper_integration" in missing
        else "run_cpu_vs_hybrid_timing_for_Vortex_mini_hello"
    )
    if next_required_boundary == "debug_real_vortex_ptx_cuModuleLoad_jit_timeout" and ptx_diagnostic_next:
        next_action = str(ptx_diagnostic_next)
    if timing_passed:
        next_action = "measure_or_unblock_veer_eh1_eh2_hybrid_timing"
        recommended_sequence = ["measure_or_unblock_veer_eh1_eh2_hybrid_timing"]
    return {
        "measurement_status": (
            "hybrid_measured" if timing_passed else "blocked_before_hybrid_measurement" if missing else "ready_for_hybrid_measurement"
        ),
        "correctness_status": "passed" if timing_passed else "not_measured",
        "timing_status": "measured" if timing_passed else "not_measured",
        "readiness_report": VORTEX_READINESS_REPORT.as_posix(),
        "bridge_review_report": VORTEX_BRIDGE_REPORT.as_posix(),
        "cpu_reference_report": VORTEX_CPU_REFERENCE_REPORT.as_posix(),
        "hybrid_candidate_report": VORTEX_HYBRID_CANDIDATE_REPORT.as_posix(),
        "ptx_module_load_diagnostic_report": VORTEX_PTX_MODULE_LOAD_DIAGNOSTIC_REPORT.as_posix(),
        "timing_report": VORTEX_TIMING_REPORT.as_posix() if timing_passed else None,
        "best_timing_report": vortex_timing if timing_passed else None,
        "cpu_reference_ready": cpu_reference_ready,
        "real_cuda_root_storage_kernel_stage_trace": hybrid_candidate.get(
            "real_cuda_root_storage_kernel_stage_trace"
        )
        if isinstance(hybrid_candidate, Mapping)
        else None,
        "real_cuda_root_storage_kernel_last_stage": hybrid_candidate.get(
            "real_cuda_root_storage_kernel_last_stage"
        )
        if isinstance(hybrid_candidate, Mapping)
        else None,
        "real_cuda_root_storage_relocation_count": hybrid_candidate.get(
            "real_cuda_root_storage_relocation_count"
        )
        if isinstance(hybrid_candidate, Mapping)
        else None,
        "real_cuda_root_storage_kernel_failed_stage": hybrid_candidate.get(
            "real_cuda_root_storage_kernel_failed_stage"
        )
        if isinstance(hybrid_candidate, Mapping)
        else None,
        "real_cuda_root_storage_kernel_failed_result": hybrid_candidate.get(
            "real_cuda_root_storage_kernel_failed_result"
        )
        if isinstance(hybrid_candidate, Mapping)
        else None,
        "cpu_reference": {
            "status": cpu_reference.get("status"),
            "execute_elapsed_s": _mapping(cpu_reference.get("metrics")).get("execute_elapsed_s"),
            "execute_speed_khz": _mapping(cpu_reference.get("metrics")).get("execute_speed_khz"),
            "execute_clocks": _mapping(cpu_reference.get("metrics")).get("execute_clocks"),
            "stdout_test_passed": cpu_reference.get("stdout_test_passed"),
        }
        if cpu_reference is not None
        else None,
        "hybrid_candidate": {
            "status": hybrid_candidate_status,
            "invalid_sim_accel_option": hybrid_candidate.get("invalid_sim_accel_option"),
            "wrapper_captured_sidecar_planning": hybrid_candidate.get("wrapper_captured_sidecar_planning"),
            "wrapper_runtime_status": hybrid_candidate.get("wrapper_runtime_status"),
            "wrapper_inspection_status": hybrid_candidate.get("wrapper_inspection_status"),
            "wrapper_sidecar_accel": hybrid_candidate.get("wrapper_sidecar_accel"),
            "wrapper_sidecar_states": hybrid_candidate.get("wrapper_sidecar_states"),
            "wrapper_sidecar_steps": hybrid_candidate.get("wrapper_sidecar_steps"),
            "blocked_missing_reviewed_source_closure": hybrid_candidate.get(
                "blocked_missing_reviewed_source_closure"
            ),
            "blocked_missing_authority_registry_source_closure": hybrid_candidate.get(
                "blocked_missing_authority_registry_source_closure"
            ),
            "blocked_sidecar_verilate_execution": hybrid_candidate.get("blocked_sidecar_verilate_execution"),
            "handoff_metadata_ready": hybrid_candidate.get("handoff_metadata_ready"),
            "stdout_cycles_plan_seed": hybrid_candidate.get("stdout_cycles_plan_seed"),
            "stdout_cycles_plan_authority_registry": hybrid_candidate.get("stdout_cycles_plan_authority_registry"),
            "runner_contract_status": hybrid_candidate.get("runner_contract_status"),
            "runner_command_ready": hybrid_candidate.get("runner_command_ready"),
            "runner_report_status": hybrid_candidate.get("runner_report_status"),
            "runner_observables_ready": hybrid_candidate.get("runner_observables_ready"),
            "runner_cycle_count": hybrid_candidate.get("runner_cycle_count"),
            "runner_proxy_handoff_observed": hybrid_candidate.get("runner_proxy_handoff_observed"),
            "runner_gpu_execution_claimed": hybrid_candidate.get("runner_gpu_execution_claimed"),
            "observable_authority_audit_status": hybrid_candidate.get("observable_authority_audit_status"),
            "generated_fake_driver_authority_passed": hybrid_candidate.get(
                "generated_fake_driver_authority_passed"
            ),
            "real_verilator_lowered_tb_runtime_call_observed": hybrid_candidate.get(
                "real_verilator_lowered_tb_runtime_call_observed"
            ),
            "fake_driver_materialized_runtime_args_call_observed": hybrid_candidate.get(
                "fake_driver_materialized_runtime_args_call_observed"
            ),
            "real_cuda_materialized_runtime_args_call_observed": hybrid_candidate.get(
                "real_cuda_materialized_runtime_args_call_observed"
            ),
            "real_verilator_memory_helper_call_observed": hybrid_candidate.get(
                "real_verilator_memory_helper_call_observed"
            ),
            "real_verilator_dpi_memory_helper_call_observed": hybrid_candidate.get(
                "real_verilator_dpi_memory_helper_call_observed"
            ),
            "real_verilator_runtime_sequence_marker_observed": hybrid_candidate.get(
                "real_verilator_runtime_sequence_marker_observed"
            ),
            "real_verilator_runtime_stub_observed": hybrid_candidate.get("real_verilator_runtime_stub_observed"),
            "real_verilator_runtime_stub_rebuilt": hybrid_candidate.get("real_verilator_runtime_stub_rebuilt"),
            "real_verilator_runtime_bridge_stub_observed": hybrid_candidate.get(
                "real_verilator_runtime_bridge_stub_observed"
            ),
            "real_verilator_runtime_bridge_stub_rebuilt": hybrid_candidate.get(
                "real_verilator_runtime_bridge_stub_rebuilt"
            ),
            "real_verilator_runtime_invocation_probe_observed": hybrid_candidate.get(
                "real_verilator_runtime_invocation_probe_observed"
            ),
            "real_verilator_runtime_invocation_probe_rebuilt": hybrid_candidate.get(
                "real_verilator_runtime_invocation_probe_rebuilt"
            ),
            "real_verilator_runtime_invocation_probe_executed": hybrid_candidate.get(
                "real_verilator_runtime_invocation_probe_executed"
            ),
            "real_verilator_materialized_runtime_args_probe_observed": hybrid_candidate.get(
                "real_verilator_materialized_runtime_args_probe_observed"
            ),
            "real_verilator_materialized_runtime_args_probe_rebuilt": hybrid_candidate.get(
                "real_verilator_materialized_runtime_args_probe_rebuilt"
            ),
            "real_verilator_materialized_runtime_args_probe_executed": hybrid_candidate.get(
                "real_verilator_materialized_runtime_args_probe_executed"
            ),
            "real_cuda_materialized_runtime_smoke_passed": hybrid_candidate.get(
                "real_cuda_materialized_runtime_smoke_passed"
            ),
            "real_cuda_materialized_runtime_authority_ready": hybrid_candidate.get(
                "real_cuda_materialized_runtime_authority_ready"
            ),
            "real_cuda_materialized_runtime_authority_source": hybrid_candidate.get(
                "real_cuda_materialized_runtime_authority_source"
            ),
            "real_cuda_materialized_runtime_smoke_returncode": hybrid_candidate.get(
                "real_cuda_materialized_runtime_smoke_returncode"
            ),
            "real_cuda_materialized_runtime_smoke_probe_status": hybrid_candidate.get(
                "real_cuda_materialized_runtime_smoke_probe_status"
            ),
            "real_cuda_materialized_runtime_smoke_timed_out": hybrid_candidate.get(
                "real_cuda_materialized_runtime_smoke_timed_out"
            ),
            "real_cuda_materialized_runtime_smoke_module": hybrid_candidate.get(
                "real_cuda_materialized_runtime_smoke_module"
            ),
            "real_cuda_return_before_eval_smoke_passed": hybrid_candidate.get(
                "real_cuda_return_before_eval_smoke_passed"
            ),
            "real_cuda_return_before_eval_smoke_module": hybrid_candidate.get(
                "real_cuda_return_before_eval_smoke_module"
            ),
            "real_cuda_return_before_eval_root_storage_relocation_count": hybrid_candidate.get(
                "real_cuda_return_before_eval_root_storage_relocation_count"
            ),
            "real_cuda_all_std_ref_returns_arg_smoke_passed": hybrid_candidate.get(
                "real_cuda_all_std_ref_returns_arg_smoke_passed"
            ),
            "real_cuda_all_std_ref_returns_arg_smoke_module": hybrid_candidate.get(
                "real_cuda_all_std_ref_returns_arg_smoke_module"
            ),
            "real_cuda_all_std_ref_returns_arg_root_storage_relocation_count": hybrid_candidate.get(
                "real_cuda_all_std_ref_returns_arg_root_storage_relocation_count"
            ),
            "real_cuda_canonical_std_ref_fix_smoke_passed": hybrid_candidate.get(
                "real_cuda_canonical_std_ref_fix_smoke_passed"
            ),
            "real_cuda_canonical_std_ref_fix_authority_ready": hybrid_candidate.get(
                "real_cuda_canonical_std_ref_fix_authority_ready"
            ),
            "real_cuda_canonical_std_ref_fix_authority_source": hybrid_candidate.get(
                "real_cuda_canonical_std_ref_fix_authority_source"
            ),
            "real_cuda_canonical_std_ref_fix_smoke_module": hybrid_candidate.get(
                "real_cuda_canonical_std_ref_fix_smoke_module"
            ),
            "real_cuda_canonical_std_ref_fix_root_storage_relocation_count": hybrid_candidate.get(
                "real_cuda_canonical_std_ref_fix_root_storage_relocation_count"
            ),
            "real_cuda_root_storage_kernel_stage_trace": hybrid_candidate.get(
                "real_cuda_root_storage_kernel_stage_trace"
            ),
            "real_cuda_root_storage_kernel_last_stage": hybrid_candidate.get(
                "real_cuda_root_storage_kernel_last_stage"
            ),
            "real_cuda_root_storage_relocation_count": hybrid_candidate.get(
                "real_cuda_root_storage_relocation_count"
            ),
            "real_cuda_materialized_runtime_smoke_failed_stage": hybrid_candidate.get(
                "real_cuda_materialized_runtime_smoke_failed_stage"
            ),
            "real_cuda_materialized_runtime_smoke_failed_result": hybrid_candidate.get(
                "real_cuda_materialized_runtime_smoke_failed_result"
            ),
            "real_cuda_root_storage_kernel_failed_stage": hybrid_candidate.get(
                "real_cuda_root_storage_kernel_failed_stage"
            ),
            "real_cuda_root_storage_kernel_failed_result": hybrid_candidate.get(
                "real_cuda_root_storage_kernel_failed_result"
            ),
            "real_vortex_kernel_artifact_ready": hybrid_candidate.get("real_vortex_kernel_artifact_ready"),
            "real_vortex_kernel_artifact_status": hybrid_candidate.get("real_vortex_kernel_artifact_status"),
            "real_vortex_kernel_artifact_count": hybrid_candidate.get("real_vortex_kernel_artifact_count"),
            "kernel_artifact_build_attempt_status": hybrid_candidate.get("kernel_artifact_build_attempt_status"),
            "kernel_artifact_build_landingpad_blocked": hybrid_candidate.get(
                "kernel_artifact_build_landingpad_blocked"
            ),
            "kernel_artifact_build_attempt_next_required_boundary": hybrid_candidate.get(
                "kernel_artifact_build_attempt_next_required_boundary"
            ),
            "kernel_callback_preflight_status": hybrid_candidate.get("kernel_callback_preflight_status"),
            "kernel_callback_wiring_ready": hybrid_candidate.get("kernel_callback_wiring_ready"),
            "kernel_callback_prelaunch_rejection_required": hybrid_candidate.get(
                "kernel_callback_prelaunch_rejection_required"
            ),
            "kernel_callback_unsafe_syms_gep_count": hybrid_candidate.get(
                "kernel_callback_unsafe_syms_gep_count"
            ),
            "kernel_callback_next_required_boundary": hybrid_candidate.get(
                "kernel_callback_next_required_boundary"
            ),
            "ptx_module_load_diagnostic_status": (
                ptx_module_load_diagnostic.get("status")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "ptx_module_load_ptx_bytes": (
                ptx_module_load_diagnostic.get("ptx_bytes")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "ptx_module_load_ptx_lines": (
                ptx_module_load_diagnostic.get("ptx_lines")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "ptx_module_load_entry_count": (
                ptx_module_load_diagnostic.get("entry_count")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "ptx_module_load_func_count": (
                ptx_module_load_diagnostic.get("func_count")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "ptx_module_load_ptxas_status": (
                ptx_module_load_diagnostic.get("ptxas_status")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "ptx_module_load_ptxas_timed_out": (
                ptx_module_load_diagnostic.get("ptxas_timed_out")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "ptx_module_load_next_required_boundary": (
                ptx_module_load_diagnostic.get("next_required_boundary")
                if isinstance(ptx_module_load_diagnostic, Mapping)
                else None
            ),
            "real_cuda_memory_transport_passed": hybrid_candidate.get("real_cuda_memory_transport_passed"),
            "real_cuda_memory_transport_h2d_bytes": hybrid_candidate.get("real_cuda_memory_transport_h2d_bytes"),
            "real_cuda_memory_transport_d2h_initial_bytes": hybrid_candidate.get(
                "real_cuda_memory_transport_d2h_initial_bytes"
            ),
            "real_cuda_runtime_sequence_preflight_passed": hybrid_candidate.get(
                "real_cuda_runtime_sequence_preflight_passed"
            ),
            "real_cuda_runtime_sequence_preflight_h2d_bytes": hybrid_candidate.get(
                "real_cuda_runtime_sequence_preflight_h2d_bytes"
            ),
            "real_cuda_runtime_sequence_preflight_d2h_initial_bytes": hybrid_candidate.get(
                "real_cuda_runtime_sequence_preflight_d2h_initial_bytes"
            ),
            "real_cuda_runtime_sequence_preflight_dcr_applied_count": hybrid_candidate.get(
                "real_cuda_runtime_sequence_preflight_dcr_applied_count"
            ),
            "real_cuda_preflight_authority_report_ready": hybrid_candidate.get(
                "real_cuda_preflight_authority_report_ready"
            ),
            "real_cuda_preflight_authority_passed": hybrid_candidate.get("real_cuda_preflight_authority_passed"),
            "real_cuda_preflight_authority_source": hybrid_candidate.get("real_cuda_preflight_authority_source"),
            "probe_or_marker_boundary_observed": hybrid_candidate.get("probe_or_marker_boundary_observed"),
            "generated_lowered_tb_runtime_call_blocked_by_probe_markers": hybrid_candidate.get(
                "generated_lowered_tb_runtime_call_blocked_by_probe_markers"
            ),
            "generated_lowered_tb_memory_helper_call_blocked_by_probe_markers": hybrid_candidate.get(
                "generated_lowered_tb_memory_helper_call_blocked_by_probe_markers"
            ),
            "next_required_boundary": (
                "measure_or_unblock_veer_eh1_eh2_hybrid_timing"
                if timing_passed
                else hybrid_candidate.get("next_required_boundary")
            ),
            "real_runtime_observable_authority_ready": hybrid_candidate.get(
                "real_runtime_observable_authority_ready"
            ),
            "adapter_implementation_status": hybrid_candidate.get("adapter_implementation_status"),
            "reentry_guard_status": hybrid_candidate.get("reentry_guard_status"),
            "sidecar_execution_invoked": hybrid_candidate.get("sidecar_execution_invoked"),
            "hybrid_candidate_executed": hybrid_candidate.get("hybrid_candidate_executed"),
            "measurement_ready": hybrid_candidate.get("measurement_ready"),
        }
        if hybrid_candidate is not None
        else None,
        "missing_prerequisites": missing,
        "recommended_sequence": recommended_sequence,
        "next_action": next_action,
        "speedup_claimed": bool(vortex_timing.get("speedup_claimed")) if isinstance(vortex_timing, Mapping) else False,
    }


def build_matrix(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    rows: list[dict[str, Any]] = []
    best_el2, el2_timing_reports = _el2_best_timing(root)
    veer_audit = _veer_family_audit_by_design(root)
    vortex = _vortex_status(root)
    for target in TARGETS:
        descriptor = _descriptor_summary(
            root / target["descriptor"],
            repo_root=root,
            configuration=str(target["configuration"]),
            test=str(target["test"]),
        )
        row: dict[str, Any] = {
            "case": target["case"],
            "design": target["design"],
            "configuration": target["configuration"],
            "test": target["test"],
            "descriptor": descriptor,
        }
        if target["kind"] == "vortex_first_gate":
            row.update(vortex)
        elif target["kind"] == "veer_el2":
            bridge = _load_json(root / EL2_BRIDGE_REPORT)
            row.update(
                {
                    "measurement_status": "hybrid_measured",
                    "correctness_status": "passed" if best_el2 is not None else "missing",
                    "timing_status": "measured" if best_el2 is not None else "missing",
                    "best_timing_report": best_el2,
                    "all_timing_reports": el2_timing_reports,
                    "bridge_report": EL2_BRIDGE_REPORT.as_posix(),
                    "bridge_status": bridge.get("status") if bridge else "missing",
                    "missing_prerequisites": [] if best_el2 is not None else ["veer_el2_timing_report"],
                    "next_action": "do_not_claim_speedup_use_as_negative_portability_measurement",
                    "speedup_claimed": False,
                }
            )
        else:
            rows_for_design = [
                _display_path(path, repo_root=root)
                for path in sorted((root / "reports").glob(f"*{str(target['design']).lower().replace('-', '_')}*"))
            ]
            audit_row = veer_audit.get(str(target["design"]))
            state_layout_probe = _veer_state_layout_probe(root, str(target["design"]))
            root_offset_review = _veer_root_offset_review(root, str(target["design"]))
            sidecar_bridge_preflight = _veer_sidecar_bridge_preflight(root, str(target["design"]))
            missing_prerequisites = [
                "sidecar_authority",
                "state_image_materializer",
                "sidecar_executable_or_lowered_runtime_bridge",
                "cpu_vs_hybrid_timing_report",
            ]
            measurement_status = "design_present_hybrid_surface_missing"
            next_action = "port_el2_state_image_and_observable_bridge_or_record_as_out_of_current_hybrid_scope"
            if audit_row:
                missing_surface = [
                    str(item)
                    for item in audit_row.get("missing_surface", [])
                    if isinstance(item, str) and item
                ]
                if missing_surface:
                    missing_prerequisites = missing_surface
                bridge_missing = _mapping(sidecar_bridge_preflight).get("missing_build_context")
                if isinstance(bridge_missing, Sequence) and not isinstance(bridge_missing, str):
                    missing_prerequisites = list(
                        dict.fromkeys(missing_prerequisites + [str(item) for item in bridge_missing if item])
                    )
                if audit_row.get("ready_to_port_from_descriptor") is True:
                    audit_status = str(audit_row.get("status") or "")
                    if audit_status == "sidecar_bridge_preflight_surface_missing":
                        measurement_status = "sidecar_bridge_preflight_hybrid_surface_missing"
                    elif audit_status == "state_image_materialized_surface_missing":
                        measurement_status = "state_image_materialized_hybrid_surface_missing"
                    elif audit_status == "state_layout_preflight_ready_surface_missing":
                        measurement_status = "state_layout_preflight_ready_hybrid_surface_missing"
                    elif audit_status == "authority_ready_surface_missing":
                        measurement_status = "authority_ready_hybrid_surface_missing"
                    else:
                        measurement_status = "portable_descriptor_ready_hybrid_surface_missing"
                next_action = str(audit_row.get("next_action") or next_action)
                if "gpu_artifact_prelaunch_rejection_required" in missing_prerequisites:
                    if "gpu_artifact_root_offset_in_syms_missing_for_auto_promotion" in missing_prerequisites:
                        next_action = "derive_eh2_root_offset_in_syms_then_rebuild_syms_state_image_before_bridge"
                    elif "gpu_artifact_unsafe_syms_gep_not_covered_by_state_image" in missing_prerequisites:
                        next_action = "rebuild_eh2_with_syms_state_image_to_cover_unsafe_syms_gep_before_bridge"
                    else:
                        next_action = "clear_eh_sidecar_gpu_artifact_prelaunch_rejection_before_bridge"
                elif "successful_gpu_launch_without_timeout" in missing_prerequisites:
                    stage_trace = _mapping(_mapping(sidecar_bridge_preflight).get("run_vl_hybrid_stage_trace"))
                    ptxas_probe = _mapping(_mapping(sidecar_bridge_preflight).get("ptxas_probe"))
                    entry_pruned_probe = _mapping(
                        _mapping(sidecar_bridge_preflight).get("entry_pruned_module_probe")
                    )
                    if (
                        entry_pruned_probe.get("ptxas_status") == "passed"
                        and entry_pruned_probe.get("bridge_status") == "illegal_memory_access_at_first_eval_launch"
                        and entry_pruned_probe.get("eval_only_status")
                        == "illegal_memory_access_at_first_eval_launch"
                        and entry_pruned_probe.get("static_ptx_residue_probe_status")
                        == "reachable_stdout_finish_cpp_runtime_residue_detected"
                    ):
                        next_action = "remove_or_device_stub_eh1_reachable_stdout_finish_cpp_runtime_residue_before_bridge_comparison"
                    elif (
                        entry_pruned_probe.get("ptxas_status") == "passed"
                        and entry_pruned_probe.get("bridge_status") == "illegal_memory_access_at_first_eval_launch"
                        and entry_pruned_probe.get("eval_only_status")
                        == "illegal_memory_access_at_first_eval_launch"
                    ):
                        next_action = "fix_eh1_entry_pruned_eval_only_kernel_illegal_memory_access_before_bridge_comparison"
                    elif (
                        entry_pruned_probe.get("ptxas_status") == "passed"
                        and entry_pruned_probe.get("bridge_status") == "illegal_memory_access_at_first_eval_launch"
                    ):
                        next_action = "fix_eh1_entry_pruned_eval_kernel_illegal_memory_access_before_bridge_comparison"
                    elif (
                        entry_pruned_probe.get("bridge_status")
                        == "illegal_memory_access_at_first_step_sync"
                    ):
                        residue_probe = _mapping(entry_pruned_probe.get("static_ptx_runtime_residue_probe"))
                        host_cleanup_probe = _mapping(entry_pruned_probe.get("host_cleanup_eval_only_probe"))
                        host_cleanup_v2_probe = _mapping(entry_pruned_probe.get("host_cleanup_v2_eval_only_probe"))
                        return_before_eval_probe = _mapping(entry_pruned_probe.get("return_before_eval_probe"))
                        return_before_eval_call_probe = _mapping(
                            entry_pruned_probe.get("return_before_eval_call_probe")
                        )
                        trigger_orinto_entry_probe = _mapping(
                            entry_pruned_probe.get("trigger_orinto_return_before_first_ix_probe")
                        )
                        trigger_orinto_stack64k_probe = _mapping(
                            entry_pruned_probe.get(
                                "trigger_orinto_return_before_first_ix_stack64k_probe"
                            )
                        )
                        inline_noop_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_noop_return_after_probe")
                        )
                        inline_dst_load_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_after_dst_load_probe")
                        )
                        inline_src_load_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_after_src_load_probe")
                        )
                        inline_before_store_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_before_store_probe")
                        )
                        inline_return_after_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_return_after_probe")
                        )
                        inline_store_u32_dst_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_store_u32_dst_probe")
                        )
                        inline_store_u8_dst_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_store_u8_dst_probe")
                        )
                        inline_store_u64_src_probe = _mapping(
                            entry_pruned_probe.get("inline_orinto_store_u64_src_probe")
                        )
                        entry_store_nba_probe = _mapping(
                            entry_pruned_probe.get("entry_store_nba_trigger_return_probe")
                        )
                        std_ref_get_canonical_eval_only_probe = _mapping(
                            entry_pruned_probe.get("std_ref_get_canonical_eval_only_probe")
                        )
                        std_ref_get_canonical_phase_act_orinto_ret0_probe = _mapping(
                            entry_pruned_probe.get(
                                "std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe"
                            )
                        )
                        std_ref_get_canonical_trigger_orinto_after_store_probe = _mapping(
                            entry_pruned_probe.get(
                                "std_ref_get_canonical_trigger_orinto_return_after_store_probe"
                            )
                        )
                        vlunpacked_lm1_canonical_eval_only_probe = _mapping(
                            entry_pruned_probe.get("vlunpacked_lm1_canonical_eval_only_probe")
                        )
                        vlunpacked_lm1_trigger_orinto_return_immediate_probe = _mapping(
                            entry_pruned_probe.get("vlunpacked_lm1_trigger_orinto_return_immediate_probe")
                        )
                        vlunpacked_lm1_orinto_rewrite_eval_only_probe = _mapping(
                            entry_pruned_probe.get("vlunpacked_lm1_orinto_rewrite_eval_only_probe")
                        )
                        skip_store_return_after_eval_act_probe = _mapping(
                            entry_pruned_probe.get("skip_store_return_after_eval_act_probe")
                        )
                        eval_act_callseq_probes = _mapping(
                            entry_pruned_probe.get("eval_act_return_after_callseq_probes")
                        )
                        eval_act_callseq_951_probe = _mapping(eval_act_callseq_probes.get("951"))
                        eval_act_callseq_952_probe = _mapping(eval_act_callseq_probes.get("952"))
                        dec_cam0_minimal_body_ret_probe = _mapping(
                            entry_pruned_probe.get("dec_cam0_minimal_body_ret_probe")
                        )
                        eval_act_skip_first_three_submodule_calls_probe = _mapping(
                            entry_pruned_probe.get(
                                "eval_act_skip_callseq_952_953_954_return_after_954_probe"
                            )
                        )
                        vlwide_pointer_conversion_canonical_probe = _mapping(
                            entry_pruned_probe.get("vlwide_pointer_conversion_canonical_eval_only_probe")
                        )
                        vlwide_phase_act_before_trigger_merge_store_probe = _mapping(
                            entry_pruned_probe.get("vlwide_phase_act_before_trigger_merge_store_probe")
                        )
                        vlwide_phase_act_after_trigger_merge_store_probe = _mapping(
                            entry_pruned_probe.get("vlwide_phase_act_after_trigger_merge_store_probe")
                        )
                        vlwide_phase_act_store_one_nba_before_eval_nba_probe = _mapping(
                            entry_pruned_probe.get("vlwide_phase_act_store_one_nba_before_eval_nba_probe")
                        )
                        vlwide_phase_act_store_one_nba_after_eval_nba_probe = _mapping(
                            entry_pruned_probe.get("vlwide_phase_act_store_one_nba_after_eval_nba_probe")
                        )
                        if (
                            vlwide_phase_act_store_one_nba_before_eval_nba_probe.get("status")
                            == "vlwide_phase_act_store_one_nba_before_eval_nba_passed"
                            and vlwide_phase_act_store_one_nba_after_eval_nba_probe.get("status")
                            == "vlwide_phase_act_store_one_nba_after_eval_nba_still_illegal_memory_access"
                        ):
                            next_action = (
                                "localize_eh2_post_vlwide_eval_phase_nba_eval_nba_cuda700_before_bridge_timing"
                            )
                        elif (
                            vlwide_phase_act_before_trigger_merge_store_probe.get("status")
                            == "vlwide_phase_act_before_trigger_merge_store_passed"
                            and vlwide_phase_act_after_trigger_merge_store_probe.get("status")
                            == "vlwide_phase_act_after_trigger_merge_store_still_illegal_memory_access"
                        ):
                            next_action = (
                                "fix_eh2_post_vlwide_phase_act_trigger_merge_store_cuda700_before_bridge_timing"
                            )
                        elif (
                            vlwide_pointer_conversion_canonical_probe.get("status")
                            == "vlwide_pointer_conversion_canonical_eval_only_still_illegal_memory_access"
                        ):
                            next_action = (
                                "localize_eh2_post_vlwide_pointer_conversion_cuda700_before_bridge_timing"
                            )
                        elif (
                            dec_cam0_minimal_body_ret_probe.get("status")
                            == "dec_cam0_minimal_body_ret_still_illegal_memory_access"
                            and eval_act_skip_first_three_submodule_calls_probe.get("status")
                            == "eval_act_skip_callseq_952_953_954_return_after_954_passed"
                        ):
                            next_action = (
                                "fix_eh2_eval_act_submodule_act_call_boundary_cuda700_before_bridge_timing"
                            )
                        elif (
                            eval_act_callseq_951_probe.get("status")
                            == "eval_act_return_after_callseq_951_passed"
                            and eval_act_callseq_952_probe.get("status")
                            == "eval_act_return_after_callseq_952_still_illegal_memory_access"
                        ):
                            next_action = (
                                "fix_eh2_eval_act_dec_cam0_act_sequent_cuda700_before_bridge_timing"
                            )
                        elif (
                            skip_store_return_after_eval_act_probe.get("status")
                            == "skip_store_return_after_eval_act_still_illegal_memory_access"
                        ):
                            next_action = (
                                "localize_eh2_post_vlunpacked_lm1_eval_act_cuda700_after_timing_resume"
                            )
                        elif (
                            vlunpacked_lm1_orinto_rewrite_eval_only_probe.get("status")
                            == "vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access"
                        ):
                            next_action = (
                                "fix_eh2_post_vlunpacked_lm1_inlined_trigger_orinto_store_cuda700_before_bridge_timing"
                            )
                        elif (
                            vlunpacked_lm1_trigger_orinto_return_immediate_probe.get("status")
                            == "vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access"
                        ):
                            next_action = (
                                "inline_or_eliminate_eh2_post_vlunpacked_lm1_trigger_orinto_helper_call_cuda700_before_bridge_timing"
                            )
                        elif (
                            vlunpacked_lm1_canonical_eval_only_probe.get("status")
                            == "vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access"
                        ):
                            next_action = (
                                "localize_eh2_post_vlunpacked_lm1_canonical_eval_cuda700_before_bridge_timing"
                            )
                        elif (
                            std_ref_get_canonical_trigger_orinto_after_store_probe.get("status")
                            == "std_ref_get_canonical_trigger_orinto_return_after_store_still_illegal_memory_access"
                        ):
                            next_action = (
                                "fix_eh2_post_std_ref_get_canonical_trigger_orinto_dst_store_cuda700_before_bridge_timing"
                            )
                        elif (
                            std_ref_get_canonical_phase_act_orinto_ret0_probe.get("status")
                            == "std_ref_get_canonical_phase_act_return_after_orinto_ret0_still_illegal_memory_access"
                        ):
                            next_action = (
                                "localize_eh2_post_std_ref_get_canonical_trigger_orinto_cuda700_before_bridge_timing"
                            )
                        elif (
                            std_ref_get_canonical_eval_only_probe.get("status")
                            == "std_ref_get_canonical_eval_only_still_illegal_memory_access"
                        ):
                            next_action = (
                                "localize_eh2_post_std_ref_get_canonical_eval_cuda700_before_bridge_timing"
                            )
                        elif (
                            inline_noop_probe.get("status") == "inline_orinto_noop_return_after_passed"
                            and inline_dst_load_probe.get("status") == "inline_orinto_after_dst_load_passed"
                            and inline_src_load_probe.get("status") == "inline_orinto_after_src_load_passed"
                            and inline_before_store_probe.get("status") == "inline_orinto_before_store_passed"
                            and inline_return_after_probe.get("status")
                            == "inline_orinto_return_after_still_illegal_memory_access"
                            and inline_store_u32_dst_probe.get("status")
                            == "inline_orinto_store_u32_dst_still_illegal_memory_access"
                            and inline_store_u8_dst_probe.get("status")
                            == "inline_orinto_store_u8_dst_still_illegal_memory_access"
                            and inline_store_u64_src_probe.get("status") == "inline_orinto_store_u64_src_passed"
                            and entry_store_nba_probe.get("status") == "entry_store_nba_trigger_return_passed"
                        ):
                            next_action = "fix_eh2_eval_phase_vnba_triggered_store_context_cuda700_before_bridge_timing"
                        elif (
                            trigger_orinto_entry_probe.get("status")
                            == "trigger_orinto_return_before_first_ix_still_illegal_memory_access"
                            and trigger_orinto_stack64k_probe.get("status")
                            == "trigger_orinto_return_before_first_ix_stack64k_still_illegal_memory_access"
                        ):
                            next_action = "fix_eh2_trigger_orinto_device_call_abi_cuda700_before_bridge_timing"
                        elif (
                            host_cleanup_v2_probe.get("status")
                            == "host_cleanup_v2_eval_only_still_illegal_memory_access"
                            and return_before_eval_probe.get("status") == "return_before_eval_passed"
                            and return_before_eval_call_probe.get("status")
                            == "prologue_only_return_before_eval_call_passed"
                        ):
                            next_action = "localize_eh2_eval_callee_internal_cuda700_after_prologue_setup"
                        elif host_cleanup_probe.get("status") == "host_cleanup_eval_only_still_illegal_memory_access":
                            next_action = "extend_eh2_host_cleanup_stubs_for_remaining_cpp_runtime_residue_before_bridge_comparison"
                        elif residue_probe.get("runtime_residue_detected") is True:
                            next_action = "remove_or_device_stub_eh2_cpp_verilator_runtime_residue_before_bridge_comparison"
                        else:
                            next_action = "fix_eh2_first_eval_launch_illegal_memory_access_before_bridge_comparison"
                    elif (
                        entry_pruned_probe.get("bridge_status")
                        == "illegal_memory_access_after_entry_pruned_cubin_launch_loop"
                    ):
                        next_action = "fix_eh2_entry_pruned_cubin_launch_loop_illegal_memory_access_before_bridge_comparison"
                    elif (
                        stage_trace.get("last_stage") == "before_cuModuleLoad"
                        and ptxas_probe.get("status") == "ptxas_timeout"
                    ):
                        next_action = "reduce_eh1_generated_ptx_module_compile_cost_before_bridge_comparison"
                    elif stage_trace.get("last_stage") == "before_cuModuleLoad":
                        next_action = "clear_eh_sidecar_ptx_module_load_timeout_before_bridge_comparison"
                    else:
                        next_action = "clear_eh_sidecar_gpu_launch_timeout_before_bridge_comparison"
            row.update(
                {
                    "measurement_status": measurement_status,
                    "correctness_status": "not_measured",
                    "timing_status": "not_measured",
                    "matching_reports": rows_for_design,
                    "state_layout_probe": state_layout_probe,
                    "root_offset_review": root_offset_review,
                    "sidecar_bridge_preflight": sidecar_bridge_preflight,
                    "hybrid_surface_audit_report": VEER_FAMILY_SURFACE_AUDIT_REPORT.as_posix()
                    if audit_row
                    else None,
                    "hybrid_surface_audit": {
                        "status": audit_row.get("status"),
                        "ready_to_port_from_descriptor": audit_row.get("ready_to_port_from_descriptor"),
                        "missing_surface": audit_row.get("missing_surface"),
                        "direct_el2_reuse_blockers": audit_row.get("direct_el2_reuse_blockers"),
                        "program_sha256_matches_el2": _mapping(audit_row.get("testbench_surface")).get(
                            "program_sha256_matches_el2"
                        ),
                    }
                    if audit_row
                    else None,
                    "missing_prerequisites": missing_prerequisites,
                    "next_action": next_action,
                    "speedup_claimed": False,
                }
            )
        rows.append(row)

    measured = [row for row in rows if row.get("measurement_status") == "hybrid_measured"]
    blocked = [row for row in rows if row.get("measurement_status") != "hybrid_measured"]
    vortex_row = next((row for row in rows if row.get("case") == "Vortex:mini:hello"), {})
    vortex_candidate = _mapping(vortex.get("hybrid_candidate"))
    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_veer_hybrid_measurement_matrix",
        "status": "incomplete",
        "objective": "Vortex mini:hello and VeeR EH1/EH2/EL2 hybrid measurement",
        "rows": rows,
        "summary": {
            "target_count": len(rows),
            "hybrid_measured_count": len(measured),
            "blocked_or_missing_count": len(blocked),
            "vortex_measured": vortex_row.get("measurement_status") == "hybrid_measured",
            "vortex_runner_cycle_count": vortex_candidate.get("runner_cycle_count"),
            "vortex_runner_proxy_handoff_observed": vortex_candidate.get("runner_proxy_handoff_observed") is True,
            "vortex_runner_gpu_execution_claimed": vortex_candidate.get("runner_gpu_execution_claimed") is True,
            "vortex_generated_fake_driver_authority_passed": (
                vortex_candidate.get("generated_fake_driver_authority_passed") is True
            ),
            "vortex_real_runtime_observable_authority_ready": (
                vortex_candidate.get("real_runtime_observable_authority_ready") is True
            ),
            "vortex_real_verilator_memory_helper_call_observed": (
                vortex_candidate.get("real_verilator_memory_helper_call_observed") is True
            ),
            "vortex_real_verilator_dpi_memory_helper_call_observed": (
                vortex_candidate.get("real_verilator_dpi_memory_helper_call_observed") is True
            ),
            "vortex_real_verilator_runtime_sequence_marker_observed": (
                vortex_candidate.get("real_verilator_runtime_sequence_marker_observed") is True
            ),
            "vortex_real_verilator_runtime_stub_observed": (
                vortex_candidate.get("real_verilator_runtime_stub_observed") is True
            ),
            "vortex_real_verilator_runtime_stub_rebuilt": (
                vortex_candidate.get("real_verilator_runtime_stub_rebuilt") is True
            ),
            "vortex_real_verilator_runtime_bridge_stub_observed": (
                vortex_candidate.get("real_verilator_runtime_bridge_stub_observed") is True
            ),
            "vortex_real_verilator_runtime_bridge_stub_rebuilt": (
                vortex_candidate.get("real_verilator_runtime_bridge_stub_rebuilt") is True
            ),
            "vortex_real_verilator_runtime_invocation_probe_observed": (
                vortex_candidate.get("real_verilator_runtime_invocation_probe_observed") is True
            ),
            "vortex_real_verilator_runtime_invocation_probe_rebuilt": (
                vortex_candidate.get("real_verilator_runtime_invocation_probe_rebuilt") is True
            ),
            "vortex_real_verilator_runtime_invocation_probe_executed": (
                vortex_candidate.get("real_verilator_runtime_invocation_probe_executed") is True
            ),
            "vortex_real_verilator_materialized_runtime_args_probe_observed": (
                vortex_candidate.get("real_verilator_materialized_runtime_args_probe_observed") is True
            ),
            "vortex_real_verilator_materialized_runtime_args_probe_rebuilt": (
                vortex_candidate.get("real_verilator_materialized_runtime_args_probe_rebuilt") is True
            ),
            "vortex_real_verilator_materialized_runtime_args_probe_executed": (
                vortex_candidate.get("real_verilator_materialized_runtime_args_probe_executed") is True
            ),
            "vortex_real_cuda_materialized_runtime_smoke_passed": (
                vortex_candidate.get("real_cuda_materialized_runtime_smoke_passed") is True
            ),
            "vortex_real_cuda_materialized_runtime_authority_ready": (
                vortex_candidate.get("real_cuda_materialized_runtime_authority_ready") is True
            ),
            "vortex_real_cuda_materialized_runtime_authority_source": vortex_candidate.get(
                "real_cuda_materialized_runtime_authority_source"
            ),
            "vortex_real_cuda_materialized_runtime_smoke_returncode": vortex_candidate.get(
                "real_cuda_materialized_runtime_smoke_returncode"
            ),
            "vortex_real_cuda_materialized_runtime_smoke_probe_status": vortex_candidate.get(
                "real_cuda_materialized_runtime_smoke_probe_status"
            ),
            "vortex_real_cuda_materialized_runtime_smoke_timed_out": vortex_candidate.get(
                "real_cuda_materialized_runtime_smoke_timed_out"
            ),
            "vortex_real_cuda_materialized_runtime_smoke_module": vortex_candidate.get(
                "real_cuda_materialized_runtime_smoke_module"
            ),
            "vortex_real_cuda_return_before_eval_smoke_passed": (
                vortex_candidate.get("real_cuda_return_before_eval_smoke_passed") is True
            ),
            "vortex_real_cuda_return_before_eval_smoke_module": vortex_candidate.get(
                "real_cuda_return_before_eval_smoke_module"
            ),
            "vortex_real_cuda_return_before_eval_root_storage_relocation_count": vortex_candidate.get(
                "real_cuda_return_before_eval_root_storage_relocation_count"
            ),
            "vortex_real_cuda_all_std_ref_returns_arg_smoke_passed": (
                vortex_candidate.get("real_cuda_all_std_ref_returns_arg_smoke_passed") is True
            ),
            "vortex_real_cuda_all_std_ref_returns_arg_smoke_module": vortex_candidate.get(
                "real_cuda_all_std_ref_returns_arg_smoke_module"
            ),
            "vortex_real_cuda_all_std_ref_returns_arg_root_storage_relocation_count": vortex_candidate.get(
                "real_cuda_all_std_ref_returns_arg_root_storage_relocation_count"
            ),
            "vortex_real_cuda_canonical_std_ref_fix_smoke_passed": (
                vortex_candidate.get("real_cuda_canonical_std_ref_fix_smoke_passed") is True
            ),
            "vortex_real_cuda_canonical_std_ref_fix_authority_ready": (
                vortex_candidate.get("real_cuda_canonical_std_ref_fix_authority_ready") is True
            ),
            "vortex_real_cuda_canonical_std_ref_fix_authority_source": vortex_candidate.get(
                "real_cuda_canonical_std_ref_fix_authority_source"
            ),
            "vortex_real_cuda_canonical_std_ref_fix_smoke_module": vortex_candidate.get(
                "real_cuda_canonical_std_ref_fix_smoke_module"
            ),
            "vortex_real_cuda_canonical_std_ref_fix_root_storage_relocation_count": vortex_candidate.get(
                "real_cuda_canonical_std_ref_fix_root_storage_relocation_count"
            ),
            "vortex_real_cuda_root_storage_kernel_stage_trace": vortex_candidate.get(
                "real_cuda_root_storage_kernel_stage_trace"
            ),
            "vortex_real_cuda_root_storage_kernel_last_stage": vortex_candidate.get(
                "real_cuda_root_storage_kernel_last_stage"
            ),
            "vortex_real_cuda_root_storage_relocation_count": vortex_candidate.get(
                "real_cuda_root_storage_relocation_count"
            ),
            "vortex_real_cuda_materialized_runtime_smoke_failed_stage": vortex_candidate.get(
                "real_cuda_materialized_runtime_smoke_failed_stage"
            ),
            "vortex_real_cuda_materialized_runtime_smoke_failed_result": vortex_candidate.get(
                "real_cuda_materialized_runtime_smoke_failed_result"
            ),
            "vortex_real_cuda_root_storage_kernel_failed_stage": vortex_candidate.get(
                "real_cuda_root_storage_kernel_failed_stage"
            ),
            "vortex_real_cuda_root_storage_kernel_failed_result": vortex_candidate.get(
                "real_cuda_root_storage_kernel_failed_result"
            ),
            "vortex_ptx_module_load_diagnostic_status": vortex_candidate.get(
                "ptx_module_load_diagnostic_status"
            ),
            "vortex_ptx_module_load_ptx_bytes": vortex_candidate.get("ptx_module_load_ptx_bytes"),
            "vortex_ptx_module_load_ptx_lines": vortex_candidate.get("ptx_module_load_ptx_lines"),
            "vortex_ptx_module_load_ptxas_status": vortex_candidate.get(
                "ptx_module_load_ptxas_status"
            ),
            "vortex_ptx_module_load_ptxas_timed_out": vortex_candidate.get(
                "ptx_module_load_ptxas_timed_out"
            ),
            "vortex_real_vortex_kernel_artifact_ready": (
                vortex_candidate.get("real_vortex_kernel_artifact_ready") is True
            ),
            "vortex_real_vortex_kernel_artifact_status": vortex_candidate.get(
                "real_vortex_kernel_artifact_status"
            ),
            "vortex_real_vortex_kernel_artifact_count": vortex_candidate.get(
                "real_vortex_kernel_artifact_count"
            ),
            "vortex_kernel_artifact_build_attempt_status": vortex_candidate.get(
                "kernel_artifact_build_attempt_status"
            ),
            "vortex_kernel_artifact_build_landingpad_blocked": (
                vortex_candidate.get("kernel_artifact_build_landingpad_blocked") is True
            ),
            "vortex_fake_driver_materialized_runtime_args_call_observed": (
                vortex_candidate.get("fake_driver_materialized_runtime_args_call_observed") is True
            ),
            "vortex_real_cuda_materialized_runtime_args_call_observed": (
                vortex_candidate.get("real_cuda_materialized_runtime_args_call_observed") is True
            ),
            "vortex_real_cuda_memory_transport_passed": (
                vortex_candidate.get("real_cuda_memory_transport_passed") is True
            ),
            "vortex_real_cuda_runtime_sequence_preflight_passed": (
                vortex_candidate.get("real_cuda_runtime_sequence_preflight_passed") is True
            ),
            "vortex_real_cuda_preflight_authority_report_ready": (
                vortex_candidate.get("real_cuda_preflight_authority_report_ready") is True
            ),
            "vortex_real_cuda_preflight_authority_passed": (
                vortex_candidate.get("real_cuda_preflight_authority_passed") is True
            ),
            "vortex_real_cuda_preflight_authority_source": vortex_candidate.get(
                "real_cuda_preflight_authority_source"
            ),
            "vortex_probe_or_marker_boundary_observed": (
                vortex_candidate.get("probe_or_marker_boundary_observed") is True
            ),
            "vortex_generated_lowered_tb_runtime_call_blocked_by_probe_markers": (
                vortex_candidate.get("generated_lowered_tb_runtime_call_blocked_by_probe_markers") is True
            ),
            "vortex_generated_lowered_tb_memory_helper_call_blocked_by_probe_markers": (
                vortex_candidate.get("generated_lowered_tb_memory_helper_call_blocked_by_probe_markers") is True
            ),
            "vortex_next_required_boundary": vortex_candidate.get("next_required_boundary"),
            "vortex_kernel_callback_preflight_status": vortex_candidate.get(
                "kernel_callback_preflight_status"
            ),
            "vortex_kernel_callback_wiring_ready": vortex_candidate.get("kernel_callback_wiring_ready") is True,
            "vortex_kernel_callback_prelaunch_rejection_required": (
                vortex_candidate.get("kernel_callback_prelaunch_rejection_required") is True
            ),
            "vortex_kernel_callback_unsafe_syms_gep_count": vortex_candidate.get(
                "kernel_callback_unsafe_syms_gep_count"
            ),
            "veer_eh1_measured": False,
            "veer_eh2_measured": False,
            "veer_el2_measured": best_el2 is not None,
            "goal_complete": False,
        },
        "recommended_order": [
            "Vortex: provide reviewed sidecar context/source-closure, connect generated lowered-TB memory/runtime calls, then run first CPU-vs-hybrid timing",
            "VeeR-EH1/EH2: review root offsets, implement design-specific sidecar executable, then execute bridge comparison before timing",
            "VeeR-EL2: keep as measured negative/portability reference; do not treat as GPU speedup evidence",
        ],
        "non_claims": [
            "not_goal_complete",
            "not_vortex_gpu_execution",
            "not_eh1_or_eh2_hybrid_measurement",
            "not_gpu_speedup_claim",
        ],
    }


def _markdown_table(report: Mapping[str, Any]) -> str:
    headers = ["Target", "Hybrid status", "Observed evidence", "GPU/timing claim", "Next blocker"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in report.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        evidence = "none"
        claim = f"timing={row.get('timing_status')}, speedup={row.get('speedup_claimed')}"
        blocker = row.get("next_action")
        hybrid_candidate = _mapping(row.get("hybrid_candidate"))
        if hybrid_candidate:
            observed = []
            if hybrid_candidate.get("runner_observables_ready") is True:
                observed.append("stdout/cycles ready")
            if hybrid_candidate.get("runner_cycle_count") is not None:
                observed.append(f"cycles={hybrid_candidate.get('runner_cycle_count')}")
            if hybrid_candidate.get("runner_proxy_handoff_observed") is True:
                observed.append("proxy_handoff=true")
            if hybrid_candidate.get("generated_fake_driver_authority_passed") is True:
                observed.append("fake_authority=true")
            if hybrid_candidate.get("real_verilator_runtime_sequence_marker_observed") is True:
                observed.append("runtime_marker=true")
            if hybrid_candidate.get("real_verilator_runtime_stub_rebuilt") is True:
                observed.append("runtime_stub_rebuilt=true")
            if hybrid_candidate.get("real_verilator_runtime_bridge_stub_rebuilt") is True:
                observed.append("runtime_bridge_stub_rebuilt=true")
            if hybrid_candidate.get("real_verilator_runtime_invocation_probe_rebuilt") is True:
                observed.append("runtime_invocation_probe_rebuilt=true")
            if hybrid_candidate.get("real_verilator_runtime_invocation_probe_executed") is True:
                observed.append("runtime_invocation_probe_executed=true")
            if hybrid_candidate.get("real_verilator_materialized_runtime_args_probe_executed") is True:
                observed.append("materialized_runtime_args_probe_executed=true")
            if hybrid_candidate.get("real_cuda_materialized_runtime_smoke_passed") is True:
                observed.append("real_cuda_materialized_smoke=true")
            if hybrid_candidate.get("real_vortex_kernel_artifact_ready") is False:
                observed.append("real_vortex_kernel_artifact=false")
            if hybrid_candidate.get("kernel_artifact_build_landingpad_blocked") is True:
                observed.append("kernel_build_landingpad_block=true")
            if hybrid_candidate.get("fake_driver_materialized_runtime_args_call_observed") is True:
                observed.append("fake_driver_materialized_args_call=true")
            if hybrid_candidate.get("real_cuda_materialized_runtime_args_call_observed") is True:
                observed.append("real_cuda_materialized_args_call=true")
            if hybrid_candidate.get("real_cuda_memory_transport_passed") is True:
                observed.append("cuda_memory_transport=true")
            if hybrid_candidate.get("real_cuda_runtime_sequence_preflight_passed") is True:
                observed.append("cuda_runtime_sequence_preflight=true")
            if hybrid_candidate.get("real_verilator_dpi_memory_helper_call_observed") is True:
                observed.append("dpi_memory_helper=true")
            if hybrid_candidate.get("real_cuda_preflight_authority_passed") is True:
                source = hybrid_candidate.get("real_cuda_preflight_authority_source")
                suffix = f":{source}" if source else ""
                observed.append(f"preflight_authority=true{suffix}")
            if (
                hybrid_candidate.get("generated_lowered_tb_runtime_call_blocked_by_probe_markers") is True
                or hybrid_candidate.get("generated_lowered_tb_memory_helper_call_blocked_by_probe_markers") is True
            ):
                observed.append("probe_marker_block=true")
            if hybrid_candidate.get("runner_gpu_execution_claimed") is False:
                observed.append("gpu_claim=false")
            if observed:
                evidence = ", ".join(observed)
            claim = (
                f"gpu={hybrid_candidate.get('runner_gpu_execution_claimed')}, "
                f"timing={row.get('timing_status')}, speedup={row.get('speedup_claimed')}"
            )
        best = _mapping(row.get("best_timing_report"))
        if best:
            evidence = (
                f"{best.get('report')}: wall={best.get('sidecar_wall_s_median')}s, "
                f"cpu_parallel_ratio={best.get('sidecar_vs_cpu_parallel_ratio')}"
            )
            claim = f"gpu_sidecar_timing=measured, speedup={row.get('speedup_claimed')}"
        state_layout_probe = _mapping(row.get("state_layout_probe"))
        root_offset_review = _mapping(row.get("root_offset_review"))
        if state_layout_probe:
            offsets_reviewed = (
                root_offset_review.get("root_field_offsets_reviewed_for_target")
                if root_offset_review
                else state_layout_probe.get("root_field_offsets_reviewed")
            )
            evidence = (
                f"root_probe={state_layout_probe.get('root_layout_probe_performed')}, "
                f"offset_probe={state_layout_probe.get('root_offset_probe_performed')}, "
                f"marker_groups={state_layout_probe.get('observed_marker_group_count')}, "
                f"offset_groups={state_layout_probe.get('mapped_marker_offset_group_count')}, "
                f"offsets_reviewed={offsets_reviewed}"
            )
            missing_groups = state_layout_probe.get("missing_marker_groups")
            if isinstance(missing_groups, Sequence) and not isinstance(missing_groups, (str, bytes)) and missing_groups:
                evidence += f", missing_markers={','.join(str(item) for item in missing_groups[:2])}"
        if root_offset_review:
            missing_groups = root_offset_review.get("missing_marker_groups")
            if isinstance(missing_groups, Sequence) and not isinstance(missing_groups, (str, bytes)) and missing_groups:
                evidence += f", offset_review_missing={','.join(str(item) for item in missing_groups[:2])}"
            variant = root_offset_review.get("root_obj_dir_variant")
            if variant:
                evidence += f", root_variant={variant}"
            evidence += (
                f", offset_review_ready={root_offset_review.get('root_field_offsets_reviewed_for_target')}"
            )
        if evidence == "none":
            descriptor = _mapping(row.get("descriptor"))
            if descriptor.get("exists") is True:
                evidence = "descriptor/test present"
        missing = row.get("missing_prerequisites")
        if isinstance(missing, Sequence) and not isinstance(missing, (str, bytes)) and missing:
            blocker = f"{blocker}; missing={', '.join(str(item) for item in missing[:5])}"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("case")),
                    str(row.get("measurement_status")),
                    str(evidence),
                    str(claim),
                    str(blocker),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_veer_hybrid_measurement_matrix.json")
    parser.add_argument("--markdown", action="store_true", help="Print a compact Markdown table")
    args = parser.parse_args(argv)

    report = build_matrix(Path(args.repo_root))
    if args.write_report:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown:
        print(_markdown_table(report))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
