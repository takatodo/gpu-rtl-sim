#!/usr/bin/env python3
"""Summarize the Vortex mini:hello RTLMeter hybrid candidate attempt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_WORK_ROOT = Path("artifacts/rtlmeter_vortex_mini_hello_hybrid_candidate")
DEFAULT_RUNNER_REPORT = Path("reports/rtlmeter_vortex_proxy_handoff_runner_observed.json")
DEFAULT_OBSERVABLE_AUTHORITY_AUDIT_REPORT = Path("reports/rtlmeter_vortex_observable_authority_audit.json")
CASE = "Vortex:mini:hello"


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _status(path: Path) -> str | None:
    return path.read_text(encoding="utf-8").strip() if path.is_file() else None


def _strip_rtlmeter_log_prefix(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if " | " not in line:
            lines.append(line)
            continue
        prefix, payload = line.split(" | ", 1)
        try:
            float(prefix.strip())
        except ValueError:
            lines.append(line)
        else:
            lines.append(payload)
    return "\n".join(lines)


def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    normalized = _strip_rtlmeter_log_prefix(text)
    decoder = json.JSONDecoder()
    start = normalized.find("{")
    while start != -1:
        try:
            payload, _ = decoder.raw_decode(normalized[start:])
        except json.JSONDecodeError:
            start = normalized.find("{", start + 1)
            continue
        return payload if isinstance(payload, dict) else None
    return None


def _wrapper_missing_prerequisites(wrapper_payload: dict[str, Any] | None) -> list[str]:
    if wrapper_payload is None:
        return [
            "path_selected_sidecar_capable_verilator_or_wrapper",
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "hybrid_observable_authority",
            "cpu_vs_hybrid_timing_report",
        ]
    if (
        wrapper_payload.get("status")
        == "rtlmeter_sidecar_execution_handoff_blocked_missing_authority_registry_source_closure"
    ):
        return [
            "reviewed_vortex_authority_registry_source_closure",
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "hybrid_observable_authority",
            "cpu_vs_hybrid_timing_report",
        ]
    if wrapper_payload.get("status") == "rtlmeter_sidecar_execution_handoff_blocked_sidecar_verilate_execution":
        return [
            "direct_sidecar_verilate_execution_or_vsim_proxy_for_vortex",
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "hybrid_observable_authority",
            "cpu_vs_hybrid_timing_report",
        ]
    return [
        "reviewed_vortex_sidecar_context_for_wrapper_handoff",
        "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
        "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
        "hybrid_observable_authority",
        "cpu_vs_hybrid_timing_report",
    ]


def _runner_missing_prerequisites(runner_report: dict[str, Any] | None) -> list[str] | None:
    if runner_report is None:
        return None
    if (
        runner_report.get("status") == "rtlmeter_stdout_cycles_sidecar_runner_observables_ready"
        and runner_report.get("rtlmeter_proxy_handoff_observed") is not True
    ):
        return [
            "reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export",
            "sidecar_proxy_marker_valid",
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "hybrid_observable_authority",
            "cpu_vs_hybrid_timing_report",
        ]
    if (
        runner_report.get("status") == "rtlmeter_stdout_cycles_sidecar_runner_observables_ready"
        and runner_report.get("rtlmeter_proxy_handoff_observed") is True
    ):
        return [
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper",
            "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence",
            "hybrid_observable_authority",
            "cpu_vs_hybrid_timing_report",
        ]
    return None


def build_summary(
    repo_root: Path,
    *,
    work_root: Path = DEFAULT_WORK_ROOT,
    runner_report_path: Path | None = DEFAULT_RUNNER_REPORT,
    observable_authority_audit_path: Path | None = DEFAULT_OBSERVABLE_AUTHORITY_AUDIT_REPORT,
) -> dict[str, Any]:
    root = repo_root.resolve()
    work = _resolve(work_root, repo_root=root)
    compile_dir = work / "Vortex" / "mini" / "compile-0"
    execute_dir = work / "Vortex" / "mini" / "execute-0" / "hello"
    verilate_stdout = _read_optional(compile_dir / "_verilate" / "stdout.log")
    verilate_cmd = _read_optional(compile_dir / "_verilate" / "cmd").strip()
    invalid_sim_accel = "Invalid option: --sim-accel" in verilate_stdout
    invalid_use_gpu = "Invalid option: --use-gpu" in verilate_stdout
    verilate_status = _status(compile_dir / "_verilate" / "status")
    execute_status = _status(execute_dir / "_execute" / "status")
    runner_report = (
        _read_json_optional(_resolve(runner_report_path, repo_root=root))
        if runner_report_path is not None
        else None
    )
    observable_authority_audit = (
        _read_json_optional(_resolve(observable_authority_audit_path, repo_root=root))
        if observable_authority_audit_path is not None
        else None
    )
    runner_observables_ready = (
        isinstance(runner_report, dict)
        and runner_report.get("status") == "rtlmeter_stdout_cycles_sidecar_runner_observables_ready"
        and runner_report.get("observables_ready") is True
    )
    runner_proxy_handoff_observed = (
        isinstance(runner_report, dict) and runner_report.get("rtlmeter_proxy_handoff_observed") is True
    )
    runner_execution_performed = (
        isinstance(runner_report, dict) and runner_report.get("execution_performed") is True
    )
    runner_cycle_count = runner_report.get("cycle_count") if isinstance(runner_report, dict) else None
    ordinary_vsim_execute_success = execute_status == "success" or runner_observables_ready
    hybrid_candidate_executed = False
    wrapper_payload = _extract_first_json_object(verilate_stdout)
    wrapper_inspection = wrapper_payload.get("wrapper_inspection", {}) if isinstance(wrapper_payload, dict) else {}
    if not isinstance(wrapper_inspection, dict):
        wrapper_inspection = {}
    handoff_metadata = wrapper_payload.get("handoff_metadata", {}) if isinstance(wrapper_payload, dict) else {}
    if not isinstance(handoff_metadata, dict):
        handoff_metadata = {}
    launcher_invocation = wrapper_payload.get("launcher_invocation", {}) if isinstance(wrapper_payload, dict) else {}
    if not isinstance(launcher_invocation, dict):
        launcher_invocation = {}
    sidecar_authority_registry = (
        wrapper_payload.get("sidecar_authority_registry", {}) if isinstance(wrapper_payload, dict) else {}
    )
    if not isinstance(sidecar_authority_registry, dict):
        sidecar_authority_registry = {}
    wrapper_captured_sidecar_planning = (
        isinstance(wrapper_payload, dict)
        and wrapper_payload.get("surface") == "rtlmeter_verilator_wrapper_runtime"
        and wrapper_inspection.get("status") == "ready_for_rtlmeter_sidecar_planning"
    )
    blocked_missing_reviewed_source_closure = (
        isinstance(wrapper_payload, dict)
        and wrapper_payload.get("status")
        == "rtlmeter_sidecar_execution_handoff_blocked_missing_reviewed_source_closure"
    )
    blocked_missing_authority_registry_source_closure = (
        isinstance(wrapper_payload, dict)
        and wrapper_payload.get("status")
        == "rtlmeter_sidecar_execution_handoff_blocked_missing_authority_registry_source_closure"
    )
    blocked_sidecar_verilate_execution = (
        isinstance(wrapper_payload, dict)
        and wrapper_payload.get("status") == "rtlmeter_sidecar_execution_handoff_blocked_sidecar_verilate_execution"
    )
    sidecar_execution_invoked = (
        wrapper_payload.get("sidecar_execution_invoked") if isinstance(wrapper_payload, dict) else False
    )
    cpu_as_gpu_fallback = wrapper_payload.get("cpu_as_gpu_fallback") if isinstance(wrapper_payload, dict) else False
    stdout_cycles_plan = wrapper_payload.get("stdout_cycles_execution_plan", {}) if isinstance(wrapper_payload, dict) else {}
    if not isinstance(stdout_cycles_plan, dict):
        stdout_cycles_plan = {}
    gpu_candidate = stdout_cycles_plan.get("gpu_candidate", {})
    if not isinstance(gpu_candidate, dict):
        gpu_candidate = {}
    runner_contract = wrapper_payload.get("stdout_cycles_runner_contract", {}) if isinstance(wrapper_payload, dict) else {}
    if not isinstance(runner_contract, dict):
        runner_contract = {}
    adapter_implementation = (
        wrapper_payload.get("stdout_cycles_runner_adapter_implementation", {}) if isinstance(wrapper_payload, dict) else {}
    )
    if not isinstance(adapter_implementation, dict):
        adapter_implementation = {}
    reentry_guard = wrapper_payload.get("reentry_guard", {}) if isinstance(wrapper_payload, dict) else {}
    if not isinstance(reentry_guard, dict):
        reentry_guard = {}

    if runner_observables_ready and runner_proxy_handoff_observed:
        status = "hybrid_candidate_proxy_handoff_observed_timing_missing"
    elif runner_observables_ready:
        status = "hybrid_candidate_stdout_cycles_observed_proxy_handoff_blocked"
    elif blocked_sidecar_verilate_execution:
        status = "hybrid_candidate_blocked_sidecar_verilate_execution"
    elif blocked_missing_authority_registry_source_closure:
        status = "hybrid_candidate_blocked_missing_vortex_authority_registry_source_closure"
    elif blocked_missing_reviewed_source_closure:
        status = "hybrid_candidate_blocked_missing_reviewed_vortex_sidecar_context"
    elif invalid_sim_accel or invalid_use_gpu:
        status = "hybrid_candidate_blocked_invalid_verilator_option"
    elif verilate_status == "success":
        status = "hybrid_candidate_compile_passed_execution_missing"
    else:
        status = "hybrid_candidate_incomplete"
    still_missing = (
        _runner_missing_prerequisites(runner_report)
        or _wrapper_missing_prerequisites(wrapper_payload if wrapper_captured_sidecar_planning else None)
    )
    real_runtime_observable_authority_ready = (
        isinstance(observable_authority_audit, dict)
        and observable_authority_audit.get("real_runtime_observable_authority_ready") is True
    )
    if isinstance(observable_authority_audit, dict):
        audit_missing = observable_authority_audit.get("missing_prerequisites")
        if isinstance(audit_missing, list):
            still_missing = list(dict.fromkeys(str(item) for item in audit_missing if item))

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_hybrid_candidate_summary",
        "status": status,
        "case": CASE,
        "work_root": _display_path(work, repo_root=root),
        "compile_dir": _display_path(compile_dir, repo_root=root),
        "execute_dir": _display_path(execute_dir, repo_root=root),
        "verilate_status": verilate_status,
        "execute_status": execute_status,
        "ordinary_vsim_execute_success": ordinary_vsim_execute_success,
        "verilate_command": verilate_cmd,
        "invalid_sim_accel_option": invalid_sim_accel,
        "invalid_use_gpu_option": invalid_use_gpu,
        "wrapper_runtime_status": wrapper_payload.get("status") if isinstance(wrapper_payload, dict) else None,
        "wrapper_inspection_status": wrapper_inspection.get("status") if isinstance(wrapper_inspection, dict) else None,
        "wrapper_sidecar_accel": wrapper_inspection.get("sidecar_accel") if isinstance(wrapper_inspection, dict) else None,
        "wrapper_sidecar_states": wrapper_inspection.get("sidecar_states") if isinstance(wrapper_inspection, dict) else None,
        "wrapper_sidecar_steps": wrapper_inspection.get("sidecar_steps") if isinstance(wrapper_inspection, dict) else None,
        "wrapper_captured_sidecar_planning": wrapper_captured_sidecar_planning,
        "handoff_status": handoff_metadata.get("status") if isinstance(handoff_metadata, dict) else None,
        "launcher_invocation_status": launcher_invocation.get("status") if isinstance(launcher_invocation, dict) else None,
        "sidecar_authority_registry_target": sidecar_authority_registry.get("target")
        if isinstance(sidecar_authority_registry, dict)
        else None,
        "blocked_missing_reviewed_source_closure": blocked_missing_reviewed_source_closure,
        "blocked_missing_authority_registry_source_closure": blocked_missing_authority_registry_source_closure,
        "blocked_sidecar_verilate_execution": blocked_sidecar_verilate_execution,
        "handoff_metadata_ready": handoff_metadata.get("status") == "rtlmeter_sidecar_handoff_metadata_ready",
        "stdout_cycles_plan_seed": stdout_cycles_plan.get("seed"),
        "stdout_cycles_plan_authority_registry": stdout_cycles_plan.get("authority_registry"),
        "stdout_cycles_plan_gpu_work_root": gpu_candidate.get("work_root"),
        "stdout_cycles_plan_gpu_observable_execute_dir": gpu_candidate.get("observable_execute_dir"),
        "runner_contract_status": runner_contract.get("status"),
        "runner_contract_missing_context": runner_contract.get("missing_runner_context")
        if isinstance(runner_contract.get("missing_runner_context"), list)
        else None,
        "runner_command_ready": isinstance(adapter_implementation.get("runner_command_argv"), list),
        "adapter_implementation_status": adapter_implementation.get("status"),
        "reentry_guard_status": reentry_guard.get("status"),
        "direct_sidecar_verilate_phase_allowed": reentry_guard.get("direct_sidecar_verilate_phase_allowed"),
        "runner_report_path": _display_path(_resolve(runner_report_path, repo_root=root), repo_root=root)
        if runner_report_path is not None
        else None,
        "runner_report_status": runner_report.get("status") if isinstance(runner_report, dict) else None,
        "runner_observables_ready": runner_observables_ready,
        "runner_execution_performed": runner_execution_performed,
        "runner_cycle_count": runner_cycle_count,
        "runner_proxy_handoff_observed": runner_proxy_handoff_observed,
        "runner_gpu_execution_claimed": runner_report.get("gpu_execution_claimed")
        if isinstance(runner_report, dict)
        else None,
        "runner_timing_measured": runner_report.get("timing_measured") if isinstance(runner_report, dict) else None,
        "runner_speedup_claimed": runner_report.get("speedup_claimed") if isinstance(runner_report, dict) else None,
        "observable_authority_audit_report": _display_path(
            _resolve(observable_authority_audit_path, repo_root=root), repo_root=root
        )
        if observable_authority_audit_path is not None
        else None,
        "observable_authority_audit_status": observable_authority_audit.get("status")
        if isinstance(observable_authority_audit, dict)
        else None,
        "proxy_handoff_observable_evidence_ready": observable_authority_audit.get("proxy_handoff_observed")
        if isinstance(observable_authority_audit, dict)
        else None,
        "generated_fake_driver_authority_passed": observable_authority_audit.get(
            "generated_fake_driver_authority_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_lowered_tb_runtime_call_observed": observable_authority_audit.get(
            "real_verilator_lowered_tb_runtime_call_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "fake_driver_materialized_runtime_args_call_observed": observable_authority_audit.get(
            "fake_driver_materialized_runtime_args_call_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_args_call_observed": observable_authority_audit.get(
            "real_cuda_materialized_runtime_args_call_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_memory_helper_call_observed": observable_authority_audit.get(
            "real_verilator_memory_helper_call_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_dpi_memory_helper_call_observed": observable_authority_audit.get(
            "real_verilator_dpi_memory_helper_call_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_sequence_marker_observed": observable_authority_audit.get(
            "real_verilator_runtime_sequence_marker_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_stub_observed": observable_authority_audit.get(
            "real_verilator_runtime_stub_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_stub_rebuilt": observable_authority_audit.get(
            "real_verilator_runtime_stub_rebuilt"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_bridge_stub_observed": observable_authority_audit.get(
            "real_verilator_runtime_bridge_stub_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_bridge_stub_rebuilt": observable_authority_audit.get(
            "real_verilator_runtime_bridge_stub_rebuilt"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_invocation_probe_observed": observable_authority_audit.get(
            "real_verilator_runtime_invocation_probe_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_invocation_probe_rebuilt": observable_authority_audit.get(
            "real_verilator_runtime_invocation_probe_rebuilt"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_runtime_invocation_probe_executed": observable_authority_audit.get(
            "real_verilator_runtime_invocation_probe_executed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_materialized_runtime_args_probe_observed": observable_authority_audit.get(
            "real_verilator_materialized_runtime_args_probe_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_materialized_runtime_args_probe_rebuilt": observable_authority_audit.get(
            "real_verilator_materialized_runtime_args_probe_rebuilt"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_verilator_materialized_runtime_args_probe_executed": observable_authority_audit.get(
            "real_verilator_materialized_runtime_args_probe_executed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_smoke_passed": observable_authority_audit.get(
            "real_cuda_materialized_runtime_smoke_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_authority_ready": observable_authority_audit.get(
            "real_cuda_materialized_runtime_authority_ready"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_authority_source": observable_authority_audit.get(
            "real_cuda_materialized_runtime_authority_source"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_smoke_returncode": observable_authority_audit.get(
            "real_cuda_materialized_runtime_smoke_returncode"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_smoke_probe_status": observable_authority_audit.get(
            "real_cuda_materialized_runtime_smoke_probe_status"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_smoke_timed_out": observable_authority_audit.get(
            "real_cuda_materialized_runtime_smoke_timed_out"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_smoke_module": observable_authority_audit.get(
            "real_cuda_materialized_runtime_smoke_module"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_return_before_eval_smoke_passed": observable_authority_audit.get(
            "real_cuda_return_before_eval_smoke_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_return_before_eval_smoke_module": observable_authority_audit.get(
            "real_cuda_return_before_eval_smoke_module"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_return_before_eval_root_storage_relocation_count": observable_authority_audit.get(
            "real_cuda_return_before_eval_root_storage_relocation_count"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_all_std_ref_returns_arg_smoke_passed": observable_authority_audit.get(
            "real_cuda_all_std_ref_returns_arg_smoke_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_all_std_ref_returns_arg_smoke_module": observable_authority_audit.get(
            "real_cuda_all_std_ref_returns_arg_smoke_module"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_all_std_ref_returns_arg_root_storage_relocation_count": observable_authority_audit.get(
            "real_cuda_all_std_ref_returns_arg_root_storage_relocation_count"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_canonical_std_ref_fix_smoke_passed": observable_authority_audit.get(
            "real_cuda_canonical_std_ref_fix_smoke_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_canonical_std_ref_fix_authority_ready": observable_authority_audit.get(
            "real_cuda_canonical_std_ref_fix_authority_ready"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_canonical_std_ref_fix_authority_source": observable_authority_audit.get(
            "real_cuda_canonical_std_ref_fix_authority_source"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_canonical_std_ref_fix_smoke_module": observable_authority_audit.get(
            "real_cuda_canonical_std_ref_fix_smoke_module"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_canonical_std_ref_fix_root_storage_relocation_count": observable_authority_audit.get(
            "real_cuda_canonical_std_ref_fix_root_storage_relocation_count"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_root_storage_kernel_stage_trace": observable_authority_audit.get(
            "real_cuda_root_storage_kernel_stage_trace"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_root_storage_kernel_last_stage": observable_authority_audit.get(
            "real_cuda_root_storage_kernel_last_stage"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_root_storage_relocation_count": observable_authority_audit.get(
            "real_cuda_root_storage_relocation_count"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_smoke_failed_stage": observable_authority_audit.get(
            "real_cuda_materialized_runtime_smoke_failed_stage"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_materialized_runtime_smoke_failed_result": observable_authority_audit.get(
            "real_cuda_materialized_runtime_smoke_failed_result"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_root_storage_kernel_failed_stage": observable_authority_audit.get(
            "real_cuda_root_storage_kernel_failed_stage"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_root_storage_kernel_failed_result": observable_authority_audit.get(
            "real_cuda_root_storage_kernel_failed_result"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_vortex_kernel_artifact_ready": observable_authority_audit.get(
            "real_vortex_kernel_artifact_ready"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_vortex_kernel_artifact_status": observable_authority_audit.get(
            "real_vortex_kernel_artifact_status"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_vortex_kernel_artifact_count": observable_authority_audit.get(
            "real_vortex_kernel_artifact_count"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_artifact_build_attempt_status": observable_authority_audit.get(
            "kernel_artifact_build_attempt_status"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_artifact_build_landingpad_blocked": observable_authority_audit.get(
            "kernel_artifact_build_landingpad_blocked"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_artifact_build_attempt_next_required_boundary": observable_authority_audit.get(
            "kernel_artifact_build_attempt_next_required_boundary"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_callback_preflight_status": observable_authority_audit.get(
            "kernel_callback_preflight_status"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_callback_wiring_ready": observable_authority_audit.get(
            "kernel_callback_wiring_ready"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_callback_prelaunch_rejection_required": observable_authority_audit.get(
            "kernel_callback_prelaunch_rejection_required"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_callback_unsafe_syms_gep_count": observable_authority_audit.get(
            "kernel_callback_unsafe_syms_gep_count"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "kernel_callback_next_required_boundary": observable_authority_audit.get(
            "kernel_callback_next_required_boundary"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_memory_transport_passed": observable_authority_audit.get(
            "real_cuda_memory_transport_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_memory_transport_h2d_bytes": observable_authority_audit.get(
            "real_cuda_memory_transport_h2d_bytes"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_memory_transport_d2h_initial_bytes": observable_authority_audit.get(
            "real_cuda_memory_transport_d2h_initial_bytes"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_runtime_sequence_preflight_passed": observable_authority_audit.get(
            "real_cuda_runtime_sequence_preflight_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_runtime_sequence_preflight_h2d_bytes": observable_authority_audit.get(
            "real_cuda_runtime_sequence_preflight_h2d_bytes"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_runtime_sequence_preflight_d2h_initial_bytes": observable_authority_audit.get(
            "real_cuda_runtime_sequence_preflight_d2h_initial_bytes"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_runtime_sequence_preflight_dcr_applied_count": observable_authority_audit.get(
            "real_cuda_runtime_sequence_preflight_dcr_applied_count"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_preflight_authority_report_ready": observable_authority_audit.get(
            "real_cuda_preflight_authority_report_ready"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_preflight_authority_passed": observable_authority_audit.get(
            "real_cuda_preflight_authority_passed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_cuda_preflight_authority_source": observable_authority_audit.get(
            "real_cuda_preflight_authority_source"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "probe_or_marker_boundary_observed": observable_authority_audit.get(
            "probe_or_marker_boundary_observed"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "generated_lowered_tb_runtime_call_blocked_by_probe_markers": observable_authority_audit.get(
            "generated_lowered_tb_runtime_call_blocked_by_probe_markers"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "generated_lowered_tb_memory_helper_call_blocked_by_probe_markers": observable_authority_audit.get(
            "generated_lowered_tb_memory_helper_call_blocked_by_probe_markers"
        )
        if isinstance(observable_authority_audit, dict)
        else None,
        "next_required_boundary": observable_authority_audit.get("next_required_boundary")
        if isinstance(observable_authority_audit, dict)
        else None,
        "real_runtime_observable_authority_ready": real_runtime_observable_authority_ready,
        "sidecar_execution_invoked": sidecar_execution_invoked is True,
        "hybrid_candidate_executed": hybrid_candidate_executed,
        "hybrid_observable_authority_ready": real_runtime_observable_authority_ready,
        "cpu_as_gpu_fallback": cpu_as_gpu_fallback is True,
        "measurement_ready": False,
        "readiness_delta": {
            "hybrid_candidate_attempted": work.exists(),
            "blocked_on_verilator_gpu_option_surface": invalid_sim_accel or invalid_use_gpu,
            "wrapper_captured_sidecar_planning": wrapper_captured_sidecar_planning,
            "blocked_missing_reviewed_source_closure": blocked_missing_reviewed_source_closure,
            "blocked_missing_authority_registry_source_closure": blocked_missing_authority_registry_source_closure,
            "blocked_sidecar_verilate_execution": blocked_sidecar_verilate_execution,
            "runner_observables_ready": runner_observables_ready,
            "runner_proxy_handoff_observed": runner_proxy_handoff_observed,
            "still_missing_for_measurement": still_missing,
        },
        "non_claims": [
            "not_hybrid_execution",
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--work-root", default=DEFAULT_WORK_ROOT.as_posix())
    parser.add_argument("--runner-report", default=DEFAULT_RUNNER_REPORT.as_posix())
    parser.add_argument("--observable-authority-audit", default=DEFAULT_OBSERVABLE_AUTHORITY_AUDIT_REPORT.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_summary(
            Path(args.repo_root),
            work_root=Path(args.work_root),
            runner_report_path=Path(args.runner_report) if args.runner_report else None,
            observable_authority_audit_path=Path(args.observable_authority_audit)
            if args.observable_authority_audit
            else None,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        report_path = Path(args.report_out)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
