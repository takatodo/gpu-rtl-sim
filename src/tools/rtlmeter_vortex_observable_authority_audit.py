#!/usr/bin/env python3
"""Audit Vortex observable-authority evidence after proxy handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RUNNER_REPORT = Path("reports/rtlmeter_vortex_proxy_handoff_runner_observed.json")
DEFAULT_GENERATED_SMOKE_REPORT = Path("reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json")
DEFAULT_MEMORY_HELPER_SMOKE_REPORT = Path("reports/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json")
DEFAULT_MATERIALIZED_SMOKE_REPORT = Path("reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json")
DEFAULT_RUNTIME_STUB_REBUILD_REPORT = Path("reports/rtlmeter_vortex_vsim_main_runtime_stub_rebuild.json")
DEFAULT_RUNTIME_BRIDGE_STUB_REBUILD_REPORT = Path(
    "reports/rtlmeter_vortex_vsim_main_runtime_bridge_stub_rebuild.json"
)
DEFAULT_RUNTIME_INVOCATION_PROBE_REBUILD_REPORT = Path(
    "reports/rtlmeter_vortex_vsim_main_runtime_invocation_probe_rebuild.json"
)
DEFAULT_RUNTIME_INVOCATION_PROBE_EXECUTION_REPORT = Path(
    "reports/rtlmeter_vortex_vsim_main_runtime_invocation_probe_execution.json"
)
DEFAULT_MATERIALIZED_RUNTIME_ARGS_PROBE_REBUILD_REPORT = Path(
    "reports/rtlmeter_vortex_vsim_main_materialized_runtime_args_probe_rebuild.json"
)
DEFAULT_MATERIALIZED_RUNTIME_ARGS_PROBE_EXECUTION_REPORT = Path(
    "reports/rtlmeter_vortex_vsim_main_materialized_runtime_args_probe_execution.json"
)
DEFAULT_REAL_CUDA_MATERIALIZED_RUNTIME_SMOKE_REPORT = Path(
    "reports/rtlmeter_vsim_main_vortex_real_cuda_materialized_runtime_smoke.json"
)
DEFAULT_REAL_CUDA_RETURN_BEFORE_EVAL_SMOKE_REPORT = Path(
    "reports/rtlmeter_vsim_main_vortex_return_before_eval_smoke.json"
)
DEFAULT_REAL_CUDA_ALL_STD_REF_RETURNS_ARG_SMOKE_REPORT = Path(
    "reports/rtlmeter_vsim_main_vortex_all_std_ref_returns_arg_smoke.json"
)
DEFAULT_REAL_CUDA_CANONICAL_STD_REF_FIX_SMOKE_REPORT = Path(
    "reports/rtlmeter_vsim_main_vortex_canonical_std_ref_fix_smoke.json"
)
DEFAULT_REAL_KERNEL_ARTIFACT_PREFLIGHT_REPORT = Path(
    "reports/rtlmeter_vortex_real_kernel_artifact_preflight.json"
)
DEFAULT_KERNEL_ARTIFACT_BUILD_ATTEMPT_REPORT = Path(
    "reports/rtlmeter_vortex_kernel_artifact_build_attempt.json"
)
DEFAULT_KERNEL_CALLBACK_PREFLIGHT_REPORT = Path(
    "reports/rtlmeter_vortex_kernel_callback_preflight.json"
)
DEFAULT_CUDA_MEMORY_TRANSPORT_PREFLIGHT_REPORT = Path(
    "reports/rtlmeter_vortex_cuda_memory_transport_preflight.json"
)
DEFAULT_CUDA_RUNTIME_SEQUENCE_PREFLIGHT_REPORT = Path(
    "reports/rtlmeter_vortex_cuda_runtime_sequence_preflight.json"
)
DEFAULT_DPI_MEMORY_HELPER_PATCH_REPORT = Path("reports/rtlmeter_vortex_generated_dpi_memory_helper_patch.json")
DEFAULT_VSIM_MAIN = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/Vsim__main.cpp"
)
DEFAULT_VSIM_ROOT = Path(
    "artifacts/rtlmeter_vortex_mini_hello_cpu_gpu_compare/gpu/Vortex/mini/compile-0/obj_dir/Vsim___024root__0.cpp"
)
RUNTIME_MARKER_BEGIN = "RTLMETER_VORTEX_RUNTIME_SEQUENCE_MARKER_BEGIN"
RUNTIME_STUB_PATCH_BEGIN = "RTLMETER_VORTEX_RUNTIME_STUB_PATCH_BEGIN"
RUNTIME_STUB_CALL_BEGIN = "RTLMETER_VORTEX_RUNTIME_STUB_CALL_BEGIN"
RUNTIME_BRIDGE_STUB_PATCH_BEGIN = "RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_PATCH_BEGIN"
RUNTIME_BRIDGE_STUB_CALL_BEGIN = "RTLMETER_VORTEX_RUNTIME_BRIDGE_STUB_CALL_BEGIN"
RUNTIME_INVOCATION_PROBE_PATCH_BEGIN = "RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_PATCH_BEGIN"
RUNTIME_INVOCATION_PROBE_CALL_BEGIN = "RTLMETER_VORTEX_RUNTIME_INVOCATION_PROBE_CALL_BEGIN"
MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN = "RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN"
MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN = "RTLMETER_VORTEX_MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN"
REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN = "RTLMETER_VORTEX_REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN"


def _resolve(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _text_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _generated_smoke_authority_passed(report: dict[str, Any] | None) -> bool:
    if not isinstance(report, dict):
        return False
    run = report.get("run")
    stdout = run.get("stdout") if isinstance(run, dict) else ""
    return (
        report.get("status") == "generated_lowered_tb_invocation_smoke_passed"
        and report.get("generated_lowered_tb_invocation_smoke_passed") is True
        and isinstance(stdout, str)
        and "authority_passed=1" in stdout
    )


def build_audit(
    repo_root: Path,
    *,
    runner_report: Path = DEFAULT_RUNNER_REPORT,
    generated_smoke_report: Path = DEFAULT_GENERATED_SMOKE_REPORT,
    memory_helper_smoke_report: Path = DEFAULT_MEMORY_HELPER_SMOKE_REPORT,
    materialized_smoke_report: Path = DEFAULT_MATERIALIZED_SMOKE_REPORT,
    runtime_stub_rebuild_report: Path = DEFAULT_RUNTIME_STUB_REBUILD_REPORT,
    runtime_bridge_stub_rebuild_report: Path = DEFAULT_RUNTIME_BRIDGE_STUB_REBUILD_REPORT,
    runtime_invocation_probe_rebuild_report: Path = DEFAULT_RUNTIME_INVOCATION_PROBE_REBUILD_REPORT,
    runtime_invocation_probe_execution_report: Path = DEFAULT_RUNTIME_INVOCATION_PROBE_EXECUTION_REPORT,
    materialized_runtime_args_probe_rebuild_report: Path = DEFAULT_MATERIALIZED_RUNTIME_ARGS_PROBE_REBUILD_REPORT,
    materialized_runtime_args_probe_execution_report: Path = DEFAULT_MATERIALIZED_RUNTIME_ARGS_PROBE_EXECUTION_REPORT,
    real_cuda_materialized_runtime_smoke_report: Path = DEFAULT_REAL_CUDA_MATERIALIZED_RUNTIME_SMOKE_REPORT,
    real_cuda_return_before_eval_smoke_report: Path = DEFAULT_REAL_CUDA_RETURN_BEFORE_EVAL_SMOKE_REPORT,
    real_cuda_all_std_ref_returns_arg_smoke_report: Path = (
        DEFAULT_REAL_CUDA_ALL_STD_REF_RETURNS_ARG_SMOKE_REPORT
    ),
    real_cuda_canonical_std_ref_fix_smoke_report: Path = (
        DEFAULT_REAL_CUDA_CANONICAL_STD_REF_FIX_SMOKE_REPORT
    ),
    real_kernel_artifact_preflight_report: Path = DEFAULT_REAL_KERNEL_ARTIFACT_PREFLIGHT_REPORT,
    kernel_artifact_build_attempt_report: Path = DEFAULT_KERNEL_ARTIFACT_BUILD_ATTEMPT_REPORT,
    kernel_callback_preflight_report: Path = DEFAULT_KERNEL_CALLBACK_PREFLIGHT_REPORT,
    cuda_memory_transport_preflight_report: Path = DEFAULT_CUDA_MEMORY_TRANSPORT_PREFLIGHT_REPORT,
    cuda_runtime_sequence_preflight_report: Path = DEFAULT_CUDA_RUNTIME_SEQUENCE_PREFLIGHT_REPORT,
    dpi_memory_helper_patch_report: Path = DEFAULT_DPI_MEMORY_HELPER_PATCH_REPORT,
    vsim_main: Path = DEFAULT_VSIM_MAIN,
    vsim_root: Path = DEFAULT_VSIM_ROOT,
) -> dict[str, Any]:
    root = repo_root.resolve()
    runner_path = _resolve(runner_report, repo_root=root)
    generated_path = _resolve(generated_smoke_report, repo_root=root)
    memory_helper_path = _resolve(memory_helper_smoke_report, repo_root=root)
    materialized_path = _resolve(materialized_smoke_report, repo_root=root)
    runtime_stub_rebuild_path = _resolve(runtime_stub_rebuild_report, repo_root=root)
    runtime_bridge_stub_rebuild_path = _resolve(runtime_bridge_stub_rebuild_report, repo_root=root)
    runtime_invocation_probe_rebuild_path = _resolve(runtime_invocation_probe_rebuild_report, repo_root=root)
    runtime_invocation_probe_execution_path = _resolve(runtime_invocation_probe_execution_report, repo_root=root)
    materialized_runtime_args_probe_rebuild_path = _resolve(
        materialized_runtime_args_probe_rebuild_report, repo_root=root
    )
    materialized_runtime_args_probe_execution_path = _resolve(
        materialized_runtime_args_probe_execution_report, repo_root=root
    )
    real_cuda_materialized_runtime_smoke_path = _resolve(
        real_cuda_materialized_runtime_smoke_report, repo_root=root
    )
    real_cuda_return_before_eval_smoke_path = _resolve(
        real_cuda_return_before_eval_smoke_report, repo_root=root
    )
    real_cuda_all_std_ref_returns_arg_smoke_path = _resolve(
        real_cuda_all_std_ref_returns_arg_smoke_report, repo_root=root
    )
    real_cuda_canonical_std_ref_fix_smoke_path = _resolve(
        real_cuda_canonical_std_ref_fix_smoke_report, repo_root=root
    )
    real_kernel_artifact_preflight_path = _resolve(real_kernel_artifact_preflight_report, repo_root=root)
    kernel_artifact_build_attempt_path = _resolve(kernel_artifact_build_attempt_report, repo_root=root)
    kernel_callback_preflight_path = _resolve(kernel_callback_preflight_report, repo_root=root)
    cuda_memory_transport_preflight_path = _resolve(cuda_memory_transport_preflight_report, repo_root=root)
    cuda_runtime_sequence_preflight_path = _resolve(cuda_runtime_sequence_preflight_report, repo_root=root)
    dpi_memory_helper_patch_path = _resolve(dpi_memory_helper_patch_report, repo_root=root)
    vsim_main_path = _resolve(vsim_main, repo_root=root)
    vsim_root_path = _resolve(vsim_root, repo_root=root)

    runner = _load_json_if_exists(runner_path)
    generated_smoke = _load_json_if_exists(generated_path)
    memory_helper_smoke = _load_json_if_exists(memory_helper_path)
    materialized_smoke = _load_json_if_exists(materialized_path)
    runtime_stub_rebuild = _load_json_if_exists(runtime_stub_rebuild_path)
    runtime_bridge_stub_rebuild = _load_json_if_exists(runtime_bridge_stub_rebuild_path)
    runtime_invocation_probe_rebuild = _load_json_if_exists(runtime_invocation_probe_rebuild_path)
    runtime_invocation_probe_execution = _load_json_if_exists(runtime_invocation_probe_execution_path)
    materialized_runtime_args_probe_rebuild = _load_json_if_exists(materialized_runtime_args_probe_rebuild_path)
    materialized_runtime_args_probe_execution = _load_json_if_exists(materialized_runtime_args_probe_execution_path)
    real_cuda_materialized_runtime_smoke = _load_json_if_exists(real_cuda_materialized_runtime_smoke_path)
    real_cuda_return_before_eval_smoke = _load_json_if_exists(real_cuda_return_before_eval_smoke_path)
    real_cuda_all_std_ref_returns_arg_smoke = _load_json_if_exists(real_cuda_all_std_ref_returns_arg_smoke_path)
    real_cuda_canonical_std_ref_fix_smoke = _load_json_if_exists(real_cuda_canonical_std_ref_fix_smoke_path)
    real_kernel_artifact_preflight = _load_json_if_exists(real_kernel_artifact_preflight_path)
    kernel_artifact_build_attempt = _load_json_if_exists(kernel_artifact_build_attempt_path)
    kernel_callback_preflight = _load_json_if_exists(kernel_callback_preflight_path)
    cuda_memory_transport_preflight = _load_json_if_exists(cuda_memory_transport_preflight_path)
    cuda_runtime_sequence_preflight = _load_json_if_exists(cuda_runtime_sequence_preflight_path)
    dpi_memory_helper_patch = _load_json_if_exists(dpi_memory_helper_patch_path)
    vsim_main_text = _text_if_exists(vsim_main_path)
    vsim_root_text = _text_if_exists(vsim_root_path)

    proxy_handoff_observed = (
        isinstance(runner, dict)
        and runner.get("status") == "rtlmeter_stdout_cycles_sidecar_runner_observables_ready"
        and runner.get("observables_ready") is True
        and runner.get("rtlmeter_proxy_handoff_observed") is True
    )
    generated_fake_authority_passed = _generated_smoke_authority_passed(generated_smoke)
    memory_helper_fake_passed = (
        isinstance(memory_helper_smoke, dict)
        and memory_helper_smoke.get("status") == "lowered_tb_memory_helper_integration_smoke_passed"
    )
    materialized_args_ready = (
        isinstance(materialized_smoke, dict)
        and materialized_smoke.get("status") == "materialized_runtime_invocation_smoke_ready_not_integrated"
        and materialized_smoke.get("smoke_ready") is True
    )
    real_verilator_runtime_sequence_marker_observed = RUNTIME_MARKER_BEGIN in vsim_main_text
    real_verilator_runtime_stub_observed = (
        RUNTIME_STUB_PATCH_BEGIN in vsim_main_text
        and RUNTIME_STUB_CALL_BEGIN in vsim_main_text
        and "rtlmeter_vortex_runtime_sequence_hook_stub" in vsim_main_text
    )
    real_verilator_runtime_stub_rebuilt = (
        isinstance(runtime_stub_rebuild, dict)
        and runtime_stub_rebuild.get("status") == "passed"
        and runtime_stub_rebuild.get("returncode") == 0
    )
    real_verilator_runtime_bridge_stub_observed = (
        RUNTIME_BRIDGE_STUB_PATCH_BEGIN in vsim_main_text
        and RUNTIME_BRIDGE_STUB_CALL_BEGIN in vsim_main_text
        and "rtlmeter_vortex_runtime_bridge_typed_stub" in vsim_main_text
        and "VortexLoweredTbRuntimeSummary" in vsim_main_text
        and "vortex_lowered_tb_runtime_summary_clear" in vsim_main_text
    )
    real_verilator_runtime_bridge_stub_rebuilt = (
        isinstance(runtime_bridge_stub_rebuild, dict)
        and runtime_bridge_stub_rebuild.get("status") == "passed"
        and runtime_bridge_stub_rebuild.get("returncode") == 0
    )
    real_verilator_runtime_invocation_probe_observed = (
        RUNTIME_INVOCATION_PROBE_PATCH_BEGIN in vsim_main_text
        and RUNTIME_INVOCATION_PROBE_CALL_BEGIN in vsim_main_text
        and "rtlmeter_vortex_runtime_invocation_expected_fail_probe" in vsim_main_text
        and "vortex_lowered_tb_invoke_runtime_sequence(0, &sequence_summary, &tb_summary)" in vsim_main_text
    )
    real_verilator_runtime_invocation_probe_rebuilt = (
        real_verilator_runtime_invocation_probe_observed
        and
        isinstance(runtime_invocation_probe_rebuild, dict)
        and runtime_invocation_probe_rebuild.get("status") == "passed"
        and runtime_invocation_probe_rebuild.get("returncode") == 0
    )
    real_verilator_runtime_invocation_probe_executed = (
        real_verilator_runtime_invocation_probe_observed
        and
        isinstance(runtime_invocation_probe_execution, dict)
        and runtime_invocation_probe_execution.get("status") == "passed"
        and runtime_invocation_probe_execution.get("returncode") == 0
        and runtime_invocation_probe_execution.get("expected_fail_probe_executed_without_aborting_before_proxy") is True
        and runtime_invocation_probe_execution.get("runtime_authority") is False
    )
    real_verilator_materialized_runtime_args_probe_observed = (
        MATERIALIZED_RUNTIME_ARGS_PROBE_PATCH_BEGIN in vsim_main_text
        and MATERIALIZED_RUNTIME_ARGS_PROBE_CALL_BEGIN in vsim_main_text
        and "rtlmeter_vortex_materialized_runtime_args_probe" in vsim_main_text
        and "vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary)" in vsim_main_text
    )
    real_verilator_materialized_runtime_args_probe_rebuilt = (
        isinstance(materialized_runtime_args_probe_rebuild, dict)
        and materialized_runtime_args_probe_rebuild.get("status") == "passed"
        and materialized_runtime_args_probe_rebuild.get("returncode") == 0
    )
    legacy_materialized_runtime_args_probe_executed = (
        isinstance(materialized_runtime_args_probe_execution, dict)
        and materialized_runtime_args_probe_execution.get("status") == "passed"
        and materialized_runtime_args_probe_execution.get("returncode") == 0
        and materialized_runtime_args_probe_execution.get(
            "materialized_runtime_args_probe_executed_without_aborting_before_proxy"
        )
        is True
        and materialized_runtime_args_probe_execution.get("runtime_authority") is False
    )
    real_cuda_materialized_runtime_smoke_passed = (
        isinstance(real_cuda_materialized_runtime_smoke, dict)
        and real_cuda_materialized_runtime_smoke.get("status") == "passed"
        and real_cuda_materialized_runtime_smoke.get("returncode") == 0
        and real_cuda_materialized_runtime_smoke.get("materialized_runtime_args_probe_passed") is True
        and real_cuda_materialized_runtime_smoke.get("proxy_handoff_reached") is True
    )
    real_cuda_materialized_runtime_authority_ready = (
        real_cuda_materialized_runtime_smoke_passed
        and real_cuda_materialized_runtime_smoke.get("runtime_authority") is True
        and real_cuda_materialized_runtime_smoke.get("authority_report_ready") == 1
        and real_cuda_materialized_runtime_smoke.get("authority_passed") == 1
        and real_cuda_materialized_runtime_smoke.get("observable_export_invoked") == 1
        and real_cuda_materialized_runtime_smoke.get("kernel_launch_invoked") == 1
        and real_cuda_materialized_runtime_smoke.get("dcr_applied_count") == 9
    )
    real_cuda_materialized_runtime_smoke_failure = (
        real_cuda_materialized_runtime_smoke.get("runtime_sequence_failure")
        if isinstance(real_cuda_materialized_runtime_smoke, dict)
        else None
    )
    real_cuda_materialized_runtime_smoke_failure = (
        real_cuda_materialized_runtime_smoke_failure
        if isinstance(real_cuda_materialized_runtime_smoke_failure, dict)
        else None
    )
    real_cuda_materialized_runtime_smoke_timed_out = (
        isinstance(real_cuda_materialized_runtime_smoke, dict)
        and real_cuda_materialized_runtime_smoke.get("timed_out") is True
    )
    real_cuda_root_storage_kernel_stage_trace = (
        real_cuda_materialized_runtime_smoke.get("root_storage_kernel_stage_trace")
        if isinstance(real_cuda_materialized_runtime_smoke, dict)
        and isinstance(real_cuda_materialized_runtime_smoke.get("root_storage_kernel_stage_trace"), list)
        else []
    )
    real_cuda_root_storage_kernel_last_stage = (
        real_cuda_materialized_runtime_smoke.get("root_storage_kernel_last_stage")
        if isinstance(real_cuda_materialized_runtime_smoke, dict)
        else None
    )
    real_cuda_root_storage_relocation_count = (
        real_cuda_materialized_runtime_smoke.get("root_storage_relocation_count")
        if isinstance(real_cuda_materialized_runtime_smoke, dict)
        else None
    )
    real_cuda_materialized_runtime_smoke_module = (
        real_cuda_materialized_runtime_smoke.get("module")
        if isinstance(real_cuda_materialized_runtime_smoke, dict)
        else None
    )
    real_cuda_return_before_eval_smoke_passed = (
        isinstance(real_cuda_return_before_eval_smoke, dict)
        and real_cuda_return_before_eval_smoke.get("status") == "passed"
        and real_cuda_return_before_eval_smoke.get("returncode") == 0
        and real_cuda_return_before_eval_smoke.get("root_storage_kernel_last_stage") == "after_cuCtxSynchronize"
        and real_cuda_return_before_eval_smoke.get("root_storage_kernel_failed_stage") is None
    )
    real_cuda_return_before_eval_smoke_module = (
        real_cuda_return_before_eval_smoke.get("module")
        if isinstance(real_cuda_return_before_eval_smoke, dict)
        else None
    )
    real_cuda_return_before_eval_root_storage_relocation_count = (
        real_cuda_return_before_eval_smoke.get("root_storage_relocation_count")
        if isinstance(real_cuda_return_before_eval_smoke, dict)
        else None
    )
    real_cuda_all_std_ref_returns_arg_smoke_passed = (
        isinstance(real_cuda_all_std_ref_returns_arg_smoke, dict)
        and real_cuda_all_std_ref_returns_arg_smoke.get("status") == "passed"
        and real_cuda_all_std_ref_returns_arg_smoke.get("returncode") == 0
        and real_cuda_all_std_ref_returns_arg_smoke.get("root_storage_kernel_last_stage")
        == "after_cuCtxSynchronize"
        and real_cuda_all_std_ref_returns_arg_smoke.get("root_storage_kernel_failed_stage") is None
        and real_cuda_all_std_ref_returns_arg_smoke.get("runtime_authority") is False
    )
    real_cuda_all_std_ref_returns_arg_smoke_module = (
        real_cuda_all_std_ref_returns_arg_smoke.get("module")
        if isinstance(real_cuda_all_std_ref_returns_arg_smoke, dict)
        else None
    )
    real_cuda_all_std_ref_returns_arg_root_storage_relocation_count = (
        real_cuda_all_std_ref_returns_arg_smoke.get("root_storage_relocation_count")
        if isinstance(real_cuda_all_std_ref_returns_arg_smoke, dict)
        else None
    )
    real_cuda_canonical_std_ref_fix_smoke_passed = (
        isinstance(real_cuda_canonical_std_ref_fix_smoke, dict)
        and real_cuda_canonical_std_ref_fix_smoke.get("status") == "passed"
        and real_cuda_canonical_std_ref_fix_smoke.get("returncode") == 0
        and real_cuda_canonical_std_ref_fix_smoke.get("root_storage_kernel_last_stage")
        == "after_cuCtxSynchronize"
        and real_cuda_canonical_std_ref_fix_smoke.get("root_storage_kernel_failed_stage") is None
    )
    real_cuda_canonical_std_ref_fix_authority_ready = (
        real_cuda_canonical_std_ref_fix_smoke_passed
        and real_cuda_canonical_std_ref_fix_smoke.get("runtime_authority") is True
        and real_cuda_canonical_std_ref_fix_smoke.get("authority_report_ready") == 1
        and real_cuda_canonical_std_ref_fix_smoke.get("authority_passed") == 1
        and real_cuda_canonical_std_ref_fix_smoke.get("observable_export_invoked") == 1
        and real_cuda_canonical_std_ref_fix_smoke.get("kernel_launch_invoked") == 1
        and real_cuda_canonical_std_ref_fix_smoke.get("dcr_applied_count") == 9
    )
    real_cuda_canonical_std_ref_fix_smoke_module = (
        real_cuda_canonical_std_ref_fix_smoke.get("module")
        if isinstance(real_cuda_canonical_std_ref_fix_smoke, dict)
        else None
    )
    real_cuda_canonical_std_ref_fix_root_storage_relocation_count = (
        real_cuda_canonical_std_ref_fix_smoke.get("root_storage_relocation_count")
        if isinstance(real_cuda_canonical_std_ref_fix_smoke, dict)
        else None
    )
    real_cuda_root_storage_kernel_failure = (
        real_cuda_materialized_runtime_smoke.get("root_storage_kernel_failure")
        if isinstance(real_cuda_materialized_runtime_smoke, dict)
        else None
    )
    real_cuda_root_storage_kernel_failure = (
        real_cuda_root_storage_kernel_failure
        if isinstance(real_cuda_root_storage_kernel_failure, dict)
        else None
    )
    real_vortex_kernel_artifact_ready = (
        isinstance(real_kernel_artifact_preflight, dict)
        and real_kernel_artifact_preflight.get("status") == "real_vortex_kernel_artifact_ready"
        and real_kernel_artifact_preflight.get("kernel_artifact_ready") is True
    )
    kernel_artifact_build_landingpad_blocked = (
        isinstance(kernel_artifact_build_attempt, dict)
        and kernel_artifact_build_attempt.get("status") == "failed_broken_module_landingpad_personality"
        and kernel_artifact_build_attempt.get("landingpad_personality_error_observed") is True
    )
    kernel_callback_preflight_status = (
        kernel_callback_preflight.get("status") if isinstance(kernel_callback_preflight, dict) else None
    )
    kernel_callback_wiring_ready = (
        isinstance(kernel_callback_preflight, dict)
        and kernel_callback_preflight.get("callback_wiring_ready") is True
    )
    kernel_callback_prelaunch_rejection_required = (
        isinstance(kernel_callback_preflight, dict)
        and kernel_callback_preflight.get("prelaunch_rejection_required") is True
    )
    kernel_callback_next_required_boundary = (
        kernel_callback_preflight.get("next_required_boundary")
        if isinstance(kernel_callback_preflight, dict)
        else None
    )
    real_verilator_materialized_runtime_args_probe_executed = (
        real_verilator_materialized_runtime_args_probe_observed
        and (legacy_materialized_runtime_args_probe_executed or real_cuda_materialized_runtime_smoke_passed)
    )
    real_cuda_memory_transport_passed = (
        isinstance(cuda_memory_transport_preflight, dict)
        and cuda_memory_transport_preflight.get("status") == "passed"
        and cuda_memory_transport_preflight.get("real_cuda_driver_api_invoked") is True
        and cuda_memory_transport_preflight.get("real_cuda_memory_transport_passed") is True
        and cuda_memory_transport_preflight.get("runtime_authority") is False
    )
    real_cuda_runtime_sequence_preflight_passed = (
        isinstance(cuda_runtime_sequence_preflight, dict)
        and cuda_runtime_sequence_preflight.get("status") == "passed"
        and cuda_runtime_sequence_preflight.get("real_cuda_driver_api_invoked") is True
        and cuda_runtime_sequence_preflight.get("real_cuda_runtime_sequence_preflight_passed") is True
        and cuda_runtime_sequence_preflight.get("runtime_sequence_called") is True
        and cuda_runtime_sequence_preflight.get("runtime_sequence_passed") is True
        and cuda_runtime_sequence_preflight.get("kernel_callback_invoked") is True
        and cuda_runtime_sequence_preflight.get("observable_export_invoked") is True
        and cuda_runtime_sequence_preflight.get("runtime_authority") is False
    )
    real_cuda_preflight_authority_report_ready = (
        real_cuda_runtime_sequence_preflight_passed
        and isinstance(cuda_runtime_sequence_preflight, dict)
        and cuda_runtime_sequence_preflight.get("preflight_authority_report_ready") is True
    )
    real_cuda_preflight_authority_passed = (
        real_cuda_runtime_sequence_preflight_passed
        and isinstance(cuda_runtime_sequence_preflight, dict)
        and cuda_runtime_sequence_preflight.get("preflight_authority_passed") is True
    )
    real_cuda_preflight_authority_source = (
        cuda_runtime_sequence_preflight.get("preflight_authority_source")
        if isinstance(cuda_runtime_sequence_preflight, dict)
        else None
    )
    real_verilator_lowered_tb_runtime_symbol_observed = (
        "vortex_lowered_tb_invoke_runtime_sequence" in vsim_main_text
        or "vortex_run_runtime_sequence" in vsim_main_text
    )
    fake_driver_materialized_runtime_args_call_observed = (
        "vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary)" in vsim_main_text
        and "rtlmeter_vortex_runtime_args_probe_alloc," in vsim_main_text
        and "rtlmeter_vortex_runtime_args_probe_h2d," in vsim_main_text
        and "rtlmeter_vortex_runtime_args_probe_kernel, 0" in vsim_main_text
    )
    real_cuda_materialized_runtime_args_call_observed = (
        REAL_CUDA_MATERIALIZED_RUNTIME_PATCH_BEGIN in vsim_main_text
        and "vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary)" in vsim_main_text
        and "rtlmeter_vortex_real_cuda_alloc," in vsim_main_text
        and "rtlmeter_vortex_real_cuda_h2d," in vsim_main_text
        and "rtlmeter_vortex_real_cuda_d2h" in vsim_main_text
        and "rtlmeter_vortex_real_cuda_dcr, 0" in vsim_main_text
        and (
            "rtlmeter_vortex_real_cuda_launch_root_storage_kernel, 0" in vsim_main_text
            or "rtlmeter_vortex_real_cuda_launch_root_storage_kernel, &root_image" in vsim_main_text
        )
    )
    fake_driver_materialized_runtime_args_symbols_observed = (
        "vortex_lowered_tb_invoke_runtime_sequence(&args, &sequence_summary, &tb_summary)" in vsim_main_text
        and "rtlmeter_vortex_runtime_args_probe_alloc" in vsim_main_text
        and "rtlmeter_vortex_runtime_args_probe_h2d" in vsim_main_text
        and "rtlmeter_vortex_runtime_args_probe_kernel" in vsim_main_text
        and "rtlmeter_vortex_runtime_args_probe_dtoh" in vsim_main_text
    )
    real_verilator_memory_helper_symbol_observed = "vortex_mem_access_device_helper" in vsim_main_text
    real_verilator_dpi_memory_helper_call_observed = (
        "Vsim___024root____Vdpiimwrap_tb__DOT__mem_access_TOP" in vsim_root_text
        and "RTLMETER_VORTEX_DPI_MEMORY_HELPER_SHADOW_CALL_BEGIN" in vsim_root_text
        and "vortex_mem_access_device_helper(" in vsim_root_text
        and isinstance(dpi_memory_helper_patch, dict)
        and dpi_memory_helper_patch.get("generated_dpi_wrapper_calls_vortex_mem_access_device_helper") is True
        and dpi_memory_helper_patch.get("runtime_authority") is False
    )
    real_verilator_memory_helper_symbol_observed = (
        real_verilator_memory_helper_symbol_observed
        or "vortex_mem_access_device_helper" in vsim_root_text
    )
    real_verilator_lowered_tb_runtime_call_observed = (
        real_verilator_lowered_tb_runtime_symbol_observed
        and not real_verilator_runtime_sequence_marker_observed
        and not real_verilator_runtime_invocation_probe_observed
        and not real_verilator_materialized_runtime_args_probe_observed
        and not fake_driver_materialized_runtime_args_call_observed
    )
    real_verilator_memory_helper_call_observed = (
        real_verilator_dpi_memory_helper_call_observed
        or (real_verilator_memory_helper_symbol_observed and not real_verilator_runtime_sequence_marker_observed)
    )
    probe_or_marker_boundary_observed = (
        real_verilator_runtime_sequence_marker_observed
        or real_verilator_runtime_invocation_probe_observed
        or real_verilator_materialized_runtime_args_probe_observed
    )
    runtime_marker_or_invocation_probe_boundary_observed = (
        real_verilator_runtime_sequence_marker_observed
        or real_verilator_runtime_invocation_probe_observed
    )
    generated_lowered_tb_runtime_call_blocked_by_probe_markers = (
        real_verilator_lowered_tb_runtime_symbol_observed
        and not real_verilator_lowered_tb_runtime_call_observed
        and probe_or_marker_boundary_observed
    )
    generated_lowered_tb_memory_helper_call_blocked_by_probe_markers = (
        real_verilator_memory_helper_symbol_observed
        and not real_verilator_memory_helper_call_observed
        and probe_or_marker_boundary_observed
    )
    real_cuda_materialized_or_canonical_authority_ready = (
        real_cuda_materialized_runtime_authority_ready
        or real_cuda_canonical_std_ref_fix_authority_ready
    )
    real_runtime_observable_authority_ready = (
        proxy_handoff_observed
        and real_verilator_lowered_tb_runtime_call_observed
        and real_verilator_memory_helper_call_observed
        and not real_verilator_runtime_sequence_marker_observed
        and isinstance(runner, dict)
        and runner.get("gpu_execution_claimed") is True
    ) or real_cuda_materialized_or_canonical_authority_ready

    missing: list[str] = []
    if not proxy_handoff_observed:
        missing.append("reviewed_proxy_handoff_or_real_vortex_runtime_execution")
    if not materialized_args_ready:
        missing.append("materialized_vortex_runtime_args")
    if not memory_helper_fake_passed:
        missing.append("lowered_tb_memory_helper_integration_smoke")
    if not generated_fake_authority_passed:
        missing.append("generated_lowered_tb_fake_driver_authority_path")
    if not real_verilator_memory_helper_call_observed and not real_cuda_materialized_or_canonical_authority_ready:
        missing.append("real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper")
    if not real_verilator_lowered_tb_runtime_call_observed and not real_cuda_materialized_or_canonical_authority_ready:
        missing.append("real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence")
    if not real_runtime_observable_authority_ready:
        missing.append("real_runtime_execution_reports_vortex_observable_authority")
    if real_cuda_materialized_runtime_args_call_observed and not real_vortex_kernel_artifact_ready:
        missing.append("real_vortex_kernel_artifact_for_materialized_runtime_callback")
    if kernel_artifact_build_landingpad_blocked:
        missing.append("vortex_lowered_ir_landingpad_personality_fix")
    if real_vortex_kernel_artifact_ready and isinstance(kernel_callback_preflight, dict) and not kernel_callback_wiring_ready:
        missing.append("real_vortex_kernel_artifact_materialized_callback_wiring")
    if kernel_callback_prelaunch_rejection_required:
        missing.append("safe_root_or_syms_storage_launch_abi")
    missing.append("cpu_vs_hybrid_timing_report.vortex")
    missing = list(dict.fromkeys(missing))

    if real_runtime_observable_authority_ready:
        status = "observable_authority_audit_real_runtime_ready"
    elif proxy_handoff_observed and generated_fake_authority_passed:
        status = "observable_authority_audit_proxy_and_fake_ready_real_runtime_missing"
    else:
        status = "observable_authority_audit_incomplete"
    if real_cuda_materialized_or_canonical_authority_ready:
        next_required_boundary = "run_cpu_vs_hybrid_timing_for_Vortex_mini_hello"
    elif (
        fake_driver_materialized_runtime_args_call_observed
        and not real_verilator_lowered_tb_runtime_call_observed
        and real_verilator_memory_helper_call_observed
        and not runtime_marker_or_invocation_probe_boundary_observed
    ):
        next_required_boundary = "replace_fake_driver_materialized_runtime_args_call_with_real_generated_lowered_tb_runtime_call"
    elif (
        kernel_callback_wiring_ready
        and real_cuda_materialized_runtime_smoke_timed_out
    ):
        next_required_boundary = (
            "debug_real_vortex_ptx_cuModuleLoad_jit_timeout"
            if real_cuda_root_storage_kernel_last_stage == "before_cuModuleLoad"
            else "debug_real_vortex_ptx_module_load_or_jit_timeout"
        )
    elif (
        kernel_callback_wiring_ready
        and isinstance(real_cuda_materialized_runtime_smoke_failure, dict)
        and real_cuda_materialized_runtime_smoke_failure.get("stage") == "kernel_launch"
    ):
        if (
            isinstance(real_cuda_root_storage_kernel_failure, dict)
            and real_cuda_root_storage_kernel_failure.get("stage") == "cuModuleLoad"
        ):
            next_required_boundary = "debug_real_vortex_ptx_module_load_failure"
        elif (
            isinstance(real_cuda_root_storage_kernel_failure, dict)
            and real_cuda_root_storage_kernel_failure.get("stage") == "cuLaunchOrSync"
            and real_cuda_root_storage_kernel_failure.get("result") == 700
        ):
            next_required_boundary = (
                "execute_real_vortex_gpu_runtime_and_export_authority"
                if real_cuda_canonical_std_ref_fix_smoke_passed
                else "promote_vortex_std_ref_device_lowering_fix_and_run_observable_authority"
                if real_cuda_all_std_ref_returns_arg_smoke_passed
                else "debug_real_vortex_eval_internal_kernel_illegal_memory_access"
                if real_cuda_return_before_eval_smoke_passed
                else "debug_real_vortex_relocated_syms_image_kernel_illegal_memory_access"
                if isinstance(real_cuda_root_storage_relocation_count, int)
                and real_cuda_root_storage_relocation_count > 0
                else "debug_real_vortex_root_storage_kernel_illegal_memory_access"
            )
        else:
            next_required_boundary = "debug_real_vortex_root_storage_kernel_launch_failure"
    elif (
        real_cuda_materialized_runtime_args_call_observed
        and not real_verilator_lowered_tb_runtime_call_observed
        and real_verilator_memory_helper_call_observed
        and not runtime_marker_or_invocation_probe_boundary_observed
        and kernel_artifact_build_landingpad_blocked
    ):
        next_required_boundary = "fix_vortex_lowered_ir_landingpad_personality_before_kernel_artifact"
    elif (
        real_cuda_materialized_runtime_args_call_observed
        and not real_verilator_lowered_tb_runtime_call_observed
        and real_verilator_memory_helper_call_observed
        and not runtime_marker_or_invocation_probe_boundary_observed
        and not real_vortex_kernel_artifact_ready
    ):
        next_required_boundary = "build_real_vortex_kernel_artifact_for_materialized_runtime_callback"
    elif (
        real_cuda_materialized_runtime_args_call_observed
        and isinstance(kernel_callback_next_required_boundary, str)
        and kernel_callback_next_required_boundary
        and not kernel_callback_wiring_ready
    ):
        next_required_boundary = kernel_callback_next_required_boundary
    elif (
        real_cuda_materialized_runtime_args_call_observed
        and not real_verilator_lowered_tb_runtime_call_observed
        and real_verilator_memory_helper_call_observed
        and not runtime_marker_or_invocation_probe_boundary_observed
    ):
        next_required_boundary = (
            str(kernel_callback_next_required_boundary)
            if isinstance(kernel_callback_next_required_boundary, str) and kernel_callback_next_required_boundary
            else "wire_real_vortex_kernel_artifact_into_materialized_runtime_callback"
        )
    elif not real_verilator_lowered_tb_runtime_call_observed and real_verilator_memory_helper_call_observed:
        next_required_boundary = "replace_probe_markers_with_real_generated_lowered_tb_runtime_call"
    elif not real_verilator_lowered_tb_runtime_call_observed or not real_verilator_memory_helper_call_observed:
        next_required_boundary = "replace_probe_markers_with_real_generated_lowered_tb_runtime_and_memory_calls"
    elif not real_runtime_observable_authority_ready:
        next_required_boundary = "execute_real_vortex_gpu_runtime_and_export_authority"
    else:
        next_required_boundary = "run_cpu_vs_hybrid_timing_for_Vortex_mini_hello"

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_observable_authority_audit",
        "status": status,
        "case": "Vortex:mini:hello",
        "runner_report": _display_path(runner_path, repo_root=root),
        "generated_smoke_report": _display_path(generated_path, repo_root=root),
        "memory_helper_smoke_report": _display_path(memory_helper_path, repo_root=root),
        "materialized_smoke_report": _display_path(materialized_path, repo_root=root),
        "runtime_stub_rebuild_report": _display_path(runtime_stub_rebuild_path, repo_root=root),
        "runtime_bridge_stub_rebuild_report": _display_path(runtime_bridge_stub_rebuild_path, repo_root=root),
        "runtime_invocation_probe_rebuild_report": _display_path(
            runtime_invocation_probe_rebuild_path, repo_root=root
        ),
        "runtime_invocation_probe_execution_report": _display_path(
            runtime_invocation_probe_execution_path, repo_root=root
        ),
        "materialized_runtime_args_probe_rebuild_report": _display_path(
            materialized_runtime_args_probe_rebuild_path, repo_root=root
        ),
        "materialized_runtime_args_probe_execution_report": _display_path(
            materialized_runtime_args_probe_execution_path, repo_root=root
        ),
        "real_cuda_materialized_runtime_smoke_report": _display_path(
            real_cuda_materialized_runtime_smoke_path, repo_root=root
        ),
        "real_cuda_return_before_eval_smoke_report": _display_path(
            real_cuda_return_before_eval_smoke_path, repo_root=root
        ),
        "real_cuda_all_std_ref_returns_arg_smoke_report": _display_path(
            real_cuda_all_std_ref_returns_arg_smoke_path, repo_root=root
        ),
        "real_cuda_canonical_std_ref_fix_smoke_report": _display_path(
            real_cuda_canonical_std_ref_fix_smoke_path, repo_root=root
        ),
        "real_kernel_artifact_preflight_report": _display_path(
            real_kernel_artifact_preflight_path, repo_root=root
        ),
        "kernel_artifact_build_attempt_report": _display_path(
            kernel_artifact_build_attempt_path, repo_root=root
        ),
        "kernel_callback_preflight_report": _display_path(kernel_callback_preflight_path, repo_root=root),
        "cuda_memory_transport_preflight_report": _display_path(
            cuda_memory_transport_preflight_path, repo_root=root
        ),
        "cuda_runtime_sequence_preflight_report": _display_path(
            cuda_runtime_sequence_preflight_path, repo_root=root
        ),
        "dpi_memory_helper_patch_report": _display_path(dpi_memory_helper_patch_path, repo_root=root),
        "vsim_main": _display_path(vsim_main_path, repo_root=root),
        "vsim_root": _display_path(vsim_root_path, repo_root=root),
        "runner_observables_ready": runner.get("observables_ready") if isinstance(runner, dict) else None,
        "runner_cycle_count": runner.get("cycle_count") if isinstance(runner, dict) else None,
        "proxy_handoff_observed": proxy_handoff_observed,
        "runner_gpu_execution_claimed": runner.get("gpu_execution_claimed") if isinstance(runner, dict) else None,
        "generated_fake_driver_authority_passed": generated_fake_authority_passed,
        "materialized_runtime_args_ready": materialized_args_ready,
        "memory_helper_fake_integration_passed": memory_helper_fake_passed,
        "real_verilator_lowered_tb_runtime_call_observed": real_verilator_lowered_tb_runtime_call_observed,
        "real_verilator_memory_helper_call_observed": real_verilator_memory_helper_call_observed,
        "real_verilator_runtime_sequence_marker_observed": real_verilator_runtime_sequence_marker_observed,
        "real_verilator_runtime_stub_observed": real_verilator_runtime_stub_observed,
        "real_verilator_runtime_stub_rebuilt": real_verilator_runtime_stub_rebuilt,
        "real_verilator_runtime_bridge_stub_observed": real_verilator_runtime_bridge_stub_observed,
        "real_verilator_runtime_bridge_stub_rebuilt": real_verilator_runtime_bridge_stub_rebuilt,
        "real_verilator_runtime_invocation_probe_observed": real_verilator_runtime_invocation_probe_observed,
        "real_verilator_runtime_invocation_probe_rebuilt": real_verilator_runtime_invocation_probe_rebuilt,
        "real_verilator_runtime_invocation_probe_executed": real_verilator_runtime_invocation_probe_executed,
        "real_verilator_materialized_runtime_args_probe_observed": (
            real_verilator_materialized_runtime_args_probe_observed
        ),
        "real_verilator_materialized_runtime_args_probe_rebuilt": (
            real_verilator_materialized_runtime_args_probe_rebuilt
        ),
        "real_verilator_materialized_runtime_args_probe_executed": (
            real_verilator_materialized_runtime_args_probe_executed
        ),
        "real_cuda_materialized_runtime_smoke_passed": real_cuda_materialized_runtime_smoke_passed,
        "real_cuda_materialized_runtime_authority_ready": (
            real_cuda_materialized_runtime_authority_ready
        ),
        "real_cuda_materialized_runtime_authority_source": (
            real_cuda_materialized_runtime_smoke.get("authority_source")
            if isinstance(real_cuda_materialized_runtime_smoke, dict)
            else None
        ),
        "real_cuda_materialized_runtime_smoke_returncode": (
            real_cuda_materialized_runtime_smoke.get("returncode")
            if isinstance(real_cuda_materialized_runtime_smoke, dict)
            else None
        ),
        "real_cuda_materialized_runtime_smoke_probe_status": (
            real_cuda_materialized_runtime_smoke.get("materialized_runtime_args_probe_status")
            if isinstance(real_cuda_materialized_runtime_smoke, dict)
            else None
        ),
        "real_cuda_materialized_runtime_smoke_timed_out": real_cuda_materialized_runtime_smoke_timed_out,
        "real_cuda_materialized_runtime_smoke_module": real_cuda_materialized_runtime_smoke_module,
        "real_cuda_return_before_eval_smoke_passed": real_cuda_return_before_eval_smoke_passed,
        "real_cuda_return_before_eval_smoke_module": real_cuda_return_before_eval_smoke_module,
        "real_cuda_return_before_eval_root_storage_relocation_count": (
            real_cuda_return_before_eval_root_storage_relocation_count
        ),
        "real_cuda_all_std_ref_returns_arg_smoke_passed": real_cuda_all_std_ref_returns_arg_smoke_passed,
        "real_cuda_all_std_ref_returns_arg_smoke_module": real_cuda_all_std_ref_returns_arg_smoke_module,
        "real_cuda_all_std_ref_returns_arg_root_storage_relocation_count": (
            real_cuda_all_std_ref_returns_arg_root_storage_relocation_count
        ),
        "real_cuda_canonical_std_ref_fix_smoke_passed": real_cuda_canonical_std_ref_fix_smoke_passed,
        "real_cuda_canonical_std_ref_fix_authority_ready": (
            real_cuda_canonical_std_ref_fix_authority_ready
        ),
        "real_cuda_canonical_std_ref_fix_authority_source": (
            real_cuda_canonical_std_ref_fix_smoke.get("authority_source")
            if isinstance(real_cuda_canonical_std_ref_fix_smoke, dict)
            else None
        ),
        "real_cuda_canonical_std_ref_fix_smoke_module": real_cuda_canonical_std_ref_fix_smoke_module,
        "real_cuda_canonical_std_ref_fix_root_storage_relocation_count": (
            real_cuda_canonical_std_ref_fix_root_storage_relocation_count
        ),
        "real_cuda_root_storage_kernel_stage_trace": real_cuda_root_storage_kernel_stage_trace,
        "real_cuda_root_storage_kernel_last_stage": real_cuda_root_storage_kernel_last_stage,
        "real_cuda_root_storage_relocation_count": real_cuda_root_storage_relocation_count,
        "real_cuda_materialized_runtime_smoke_failed_stage": (
            real_cuda_materialized_runtime_smoke_failure.get("stage")
            if isinstance(real_cuda_materialized_runtime_smoke_failure, dict)
            else None
        ),
        "real_cuda_materialized_runtime_smoke_failed_result": (
            real_cuda_materialized_runtime_smoke_failure.get("result")
            if isinstance(real_cuda_materialized_runtime_smoke_failure, dict)
            else None
        ),
        "real_cuda_root_storage_kernel_failed_stage": (
            real_cuda_root_storage_kernel_failure.get("stage")
            if isinstance(real_cuda_root_storage_kernel_failure, dict)
            else None
        ),
        "real_cuda_root_storage_kernel_failed_result": (
            real_cuda_root_storage_kernel_failure.get("result")
            if isinstance(real_cuda_root_storage_kernel_failure, dict)
            else None
        ),
        "real_vortex_kernel_artifact_ready": real_vortex_kernel_artifact_ready,
        "real_vortex_kernel_artifact_status": (
            real_kernel_artifact_preflight.get("status")
            if isinstance(real_kernel_artifact_preflight, dict)
            else None
        ),
        "real_vortex_kernel_artifact_count": (
            int(real_kernel_artifact_preflight.get("cubin_count") or 0)
            + int(real_kernel_artifact_preflight.get("ptx_count") or 0)
            if isinstance(real_kernel_artifact_preflight, dict)
            else None
        ),
        "real_vortex_kernel_artifact_format": (
            real_kernel_artifact_preflight.get("kernel_artifact_format")
            if isinstance(real_kernel_artifact_preflight, dict)
            else None
        ),
        "kernel_artifact_build_attempt_status": (
            kernel_artifact_build_attempt.get("status")
            if isinstance(kernel_artifact_build_attempt, dict)
            else None
        ),
        "kernel_artifact_build_landingpad_blocked": kernel_artifact_build_landingpad_blocked,
        "kernel_artifact_build_attempt_next_required_boundary": (
            kernel_artifact_build_attempt.get("next_required_boundary")
            if isinstance(kernel_artifact_build_attempt, dict)
            else None
        ),
        "kernel_callback_preflight_status": kernel_callback_preflight_status,
        "kernel_callback_wiring_ready": kernel_callback_wiring_ready,
        "kernel_callback_prelaunch_rejection_required": kernel_callback_prelaunch_rejection_required,
        "kernel_callback_unsafe_syms_gep_count": (
            kernel_callback_preflight.get("unsafe_syms_gep_count")
            if isinstance(kernel_callback_preflight, dict)
            else None
        ),
        "kernel_callback_next_required_boundary": kernel_callback_next_required_boundary,
        "real_cuda_memory_transport_passed": real_cuda_memory_transport_passed,
        "real_cuda_memory_transport_h2d_bytes": (
            cuda_memory_transport_preflight.get("host_to_device_bytes")
            if isinstance(cuda_memory_transport_preflight, dict)
            else None
        ),
        "real_cuda_memory_transport_d2h_initial_bytes": (
            cuda_memory_transport_preflight.get("device_to_host_initial_bytes")
            if isinstance(cuda_memory_transport_preflight, dict)
            else None
        ),
        "real_cuda_runtime_sequence_preflight_passed": real_cuda_runtime_sequence_preflight_passed,
        "real_cuda_runtime_sequence_preflight_h2d_bytes": (
            cuda_runtime_sequence_preflight.get("host_to_device_bytes")
            if isinstance(cuda_runtime_sequence_preflight, dict)
            else None
        ),
        "real_cuda_runtime_sequence_preflight_d2h_initial_bytes": (
            cuda_runtime_sequence_preflight.get("device_to_host_initial_bytes")
            if isinstance(cuda_runtime_sequence_preflight, dict)
            else None
        ),
        "real_cuda_runtime_sequence_preflight_dcr_applied_count": (
            cuda_runtime_sequence_preflight.get("dcr_applied_count")
            if isinstance(cuda_runtime_sequence_preflight, dict)
            else None
        ),
        "real_cuda_preflight_authority_report_ready": real_cuda_preflight_authority_report_ready,
        "real_cuda_preflight_authority_passed": real_cuda_preflight_authority_passed,
        "real_cuda_preflight_authority_source": real_cuda_preflight_authority_source,
        "real_verilator_lowered_tb_runtime_symbol_observed": real_verilator_lowered_tb_runtime_symbol_observed,
        "fake_driver_materialized_runtime_args_call_observed": fake_driver_materialized_runtime_args_call_observed,
        "fake_driver_materialized_runtime_args_symbols_observed": fake_driver_materialized_runtime_args_symbols_observed,
        "real_cuda_materialized_runtime_args_call_observed": real_cuda_materialized_runtime_args_call_observed,
        "real_verilator_memory_helper_symbol_observed": real_verilator_memory_helper_symbol_observed,
        "real_verilator_dpi_memory_helper_call_observed": real_verilator_dpi_memory_helper_call_observed,
        "probe_or_marker_boundary_observed": probe_or_marker_boundary_observed,
        "runtime_marker_or_invocation_probe_boundary_observed": runtime_marker_or_invocation_probe_boundary_observed,
        "generated_lowered_tb_runtime_call_blocked_by_probe_markers": (
            generated_lowered_tb_runtime_call_blocked_by_probe_markers
        ),
        "generated_lowered_tb_memory_helper_call_blocked_by_probe_markers": (
            generated_lowered_tb_memory_helper_call_blocked_by_probe_markers
        ),
        "real_runtime_observable_authority_ready": real_runtime_observable_authority_ready,
        "measurement_ready": real_runtime_observable_authority_ready and "cpu_vs_hybrid_timing_report.vortex" not in missing,
        "missing_prerequisites": missing,
        "next_required_boundary": next_required_boundary,
        "recommended_next": (
            "run_cpu_vs_hybrid_timing_for_Vortex_mini_hello"
            if real_runtime_observable_authority_ready
            else "connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence"
        ),
        "non_claims": [
            "proxy_handoff_is_not_gpu_execution",
            "fake_driver_authority_is_not_real_runtime_authority",
            "cuda_runtime_sequence_preflight_is_not_vortex_kernel_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--runner-report", default=DEFAULT_RUNNER_REPORT.as_posix())
    parser.add_argument("--generated-smoke-report", default=DEFAULT_GENERATED_SMOKE_REPORT.as_posix())
    parser.add_argument("--memory-helper-smoke-report", default=DEFAULT_MEMORY_HELPER_SMOKE_REPORT.as_posix())
    parser.add_argument("--materialized-smoke-report", default=DEFAULT_MATERIALIZED_SMOKE_REPORT.as_posix())
    parser.add_argument("--runtime-stub-rebuild-report", default=DEFAULT_RUNTIME_STUB_REBUILD_REPORT.as_posix())
    parser.add_argument(
        "--runtime-bridge-stub-rebuild-report",
        default=DEFAULT_RUNTIME_BRIDGE_STUB_REBUILD_REPORT.as_posix(),
    )
    parser.add_argument(
        "--runtime-invocation-probe-rebuild-report",
        default=DEFAULT_RUNTIME_INVOCATION_PROBE_REBUILD_REPORT.as_posix(),
    )
    parser.add_argument(
        "--runtime-invocation-probe-execution-report",
        default=DEFAULT_RUNTIME_INVOCATION_PROBE_EXECUTION_REPORT.as_posix(),
    )
    parser.add_argument(
        "--materialized-runtime-args-probe-rebuild-report",
        default=DEFAULT_MATERIALIZED_RUNTIME_ARGS_PROBE_REBUILD_REPORT.as_posix(),
    )
    parser.add_argument(
        "--materialized-runtime-args-probe-execution-report",
        default=DEFAULT_MATERIALIZED_RUNTIME_ARGS_PROBE_EXECUTION_REPORT.as_posix(),
    )
    parser.add_argument(
        "--real-cuda-materialized-runtime-smoke-report",
        default=DEFAULT_REAL_CUDA_MATERIALIZED_RUNTIME_SMOKE_REPORT.as_posix(),
    )
    parser.add_argument(
        "--real-cuda-return-before-eval-smoke-report",
        default=DEFAULT_REAL_CUDA_RETURN_BEFORE_EVAL_SMOKE_REPORT.as_posix(),
    )
    parser.add_argument(
        "--real-cuda-all-std-ref-returns-arg-smoke-report",
        default=DEFAULT_REAL_CUDA_ALL_STD_REF_RETURNS_ARG_SMOKE_REPORT.as_posix(),
    )
    parser.add_argument(
        "--real-cuda-canonical-std-ref-fix-smoke-report",
        default=DEFAULT_REAL_CUDA_CANONICAL_STD_REF_FIX_SMOKE_REPORT.as_posix(),
    )
    parser.add_argument(
        "--real-kernel-artifact-preflight-report",
        default=DEFAULT_REAL_KERNEL_ARTIFACT_PREFLIGHT_REPORT.as_posix(),
    )
    parser.add_argument(
        "--kernel-artifact-build-attempt-report",
        default=DEFAULT_KERNEL_ARTIFACT_BUILD_ATTEMPT_REPORT.as_posix(),
    )
    parser.add_argument(
        "--cuda-memory-transport-preflight-report",
        default=DEFAULT_CUDA_MEMORY_TRANSPORT_PREFLIGHT_REPORT.as_posix(),
    )
    parser.add_argument(
        "--cuda-runtime-sequence-preflight-report",
        default=DEFAULT_CUDA_RUNTIME_SEQUENCE_PREFLIGHT_REPORT.as_posix(),
    )
    parser.add_argument(
        "--dpi-memory-helper-patch-report",
        default=DEFAULT_DPI_MEMORY_HELPER_PATCH_REPORT.as_posix(),
    )
    parser.add_argument("--vsim-main", default=DEFAULT_VSIM_MAIN.as_posix())
    parser.add_argument("--vsim-root", default=DEFAULT_VSIM_ROOT.as_posix())
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default="reports/rtlmeter_vortex_observable_authority_audit.json")
    args = parser.parse_args(argv)

    report = build_audit(
        Path(args.repo_root),
        runner_report=Path(args.runner_report),
        generated_smoke_report=Path(args.generated_smoke_report),
        memory_helper_smoke_report=Path(args.memory_helper_smoke_report),
        materialized_smoke_report=Path(args.materialized_smoke_report),
        runtime_stub_rebuild_report=Path(args.runtime_stub_rebuild_report),
        runtime_bridge_stub_rebuild_report=Path(args.runtime_bridge_stub_rebuild_report),
        runtime_invocation_probe_rebuild_report=Path(args.runtime_invocation_probe_rebuild_report),
        runtime_invocation_probe_execution_report=Path(args.runtime_invocation_probe_execution_report),
        materialized_runtime_args_probe_rebuild_report=Path(args.materialized_runtime_args_probe_rebuild_report),
        materialized_runtime_args_probe_execution_report=Path(args.materialized_runtime_args_probe_execution_report),
        real_cuda_materialized_runtime_smoke_report=Path(args.real_cuda_materialized_runtime_smoke_report),
        real_cuda_return_before_eval_smoke_report=Path(args.real_cuda_return_before_eval_smoke_report),
        real_cuda_all_std_ref_returns_arg_smoke_report=Path(
            args.real_cuda_all_std_ref_returns_arg_smoke_report
        ),
        real_cuda_canonical_std_ref_fix_smoke_report=Path(
            args.real_cuda_canonical_std_ref_fix_smoke_report
        ),
        real_kernel_artifact_preflight_report=Path(args.real_kernel_artifact_preflight_report),
        kernel_artifact_build_attempt_report=Path(args.kernel_artifact_build_attempt_report),
        cuda_memory_transport_preflight_report=Path(args.cuda_memory_transport_preflight_report),
        cuda_runtime_sequence_preflight_report=Path(args.cuda_runtime_sequence_preflight_report),
        dpi_memory_helper_patch_report=Path(args.dpi_memory_helper_patch_report),
        vsim_main=Path(args.vsim_main),
        vsim_root=Path(args.vsim_root),
    )
    if args.write_report:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
