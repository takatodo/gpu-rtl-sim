"""Review the Vortex DPI memory bridge boundary for first GPU usefulness gating."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


TB_PATH = Path("third_party/rtlmeter/designs/Vortex/src/tb.sv")
MEMORY_CPP_PATH = Path("third_party/rtlmeter/designs/Vortex/src/dpi/memory.cpp")
DEVICE_HELPER_HEADER_PATH = Path("src/hybrid/vortex_memory_model_device.h")
RUNTIME_UPLOAD_HEADER_PATH = Path("src/hybrid/vortex_runtime_upload.h")
OBSERVABLE_EXPORT_HEADER_PATH = Path("src/hybrid/vortex_observable_export.h")
RUNTIME_SEQUENCE_HEADER_PATH = Path("src/hybrid/vortex_runtime_sequence.h")
BINARY_INPUT_REPORT = Path("reports/rtlmeter_vortex_binary_input_summary.json")
GPU_MEMORY_MODEL_PLAN_REPORT = Path("reports/rtlmeter_vortex_gpu_memory_model_plan.json")
MEMORY_MODEL_REFERENCE_REPORT = Path("reports/rtlmeter_vortex_memory_model_reference.json")
DEVICE_BUFFER_MATERIALIZE_REPORT = Path("reports/rtlmeter_vortex_device_buffer_materialize.json")
DCR_SCHEDULE_REPORT = Path("reports/rtlmeter_vortex_dcr_schedule.json")
RUNTIME_INVOCATION_PLAN_REPORT = Path("reports/rtlmeter_vortex_runtime_invocation_plan.json")
LOWERED_TB_INVOCATION_SMOKE_REPORT = Path("reports/rtlmeter_vortex_lowered_tb_invocation_smoke.json")
MATERIALIZED_RUNTIME_INVOCATION_SMOKE_REPORT = Path(
    "reports/rtlmeter_vortex_materialized_runtime_invocation_smoke.json"
)
GENERATED_LOWERED_TB_INVOCATION_SMOKE_REPORT = Path(
    "reports/rtlmeter_vortex_generated_lowered_tb_invocation_smoke.json"
)
LOWERED_TB_MEMORY_HELPER_INTEGRATION_SMOKE_REPORT = Path(
    "reports/rtlmeter_vortex_lowered_tb_memory_helper_integration_smoke.json"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _contains_all(text: str, patterns: list[str]) -> dict[str, bool]:
    return {pattern: pattern in text for pattern in patterns}


def _macro_int(text: str, name: str) -> int | None:
    match = re.search(rf"^\s*#define\s+{re.escape(name)}\s+([0-9A-Fa-fx]+)\s*$", text, re.MULTILINE)
    if not match:
        return None
    return int(match.group(1), 0)


def build_review(repo_root: Path) -> dict[str, Any]:
    tb_path = repo_root / TB_PATH
    memory_cpp_path = repo_root / MEMORY_CPP_PATH
    device_helper_header_path = repo_root / DEVICE_HELPER_HEADER_PATH
    runtime_upload_header_path = repo_root / RUNTIME_UPLOAD_HEADER_PATH
    observable_export_header_path = repo_root / OBSERVABLE_EXPORT_HEADER_PATH
    runtime_sequence_header_path = repo_root / RUNTIME_SEQUENCE_HEADER_PATH
    binary_input_summary = _load_json_if_exists(repo_root / BINARY_INPUT_REPORT)
    gpu_memory_model_plan = _load_json_if_exists(repo_root / GPU_MEMORY_MODEL_PLAN_REPORT)
    memory_model_reference = _load_json_if_exists(repo_root / MEMORY_MODEL_REFERENCE_REPORT)
    device_buffer_materialization = _load_json_if_exists(repo_root / DEVICE_BUFFER_MATERIALIZE_REPORT)
    dcr_schedule = _load_json_if_exists(repo_root / DCR_SCHEDULE_REPORT)
    runtime_invocation_plan = _load_json_if_exists(repo_root / RUNTIME_INVOCATION_PLAN_REPORT)
    lowered_tb_invocation_smoke = _load_json_if_exists(repo_root / LOWERED_TB_INVOCATION_SMOKE_REPORT)
    materialized_runtime_invocation_smoke = _load_json_if_exists(
        repo_root / MATERIALIZED_RUNTIME_INVOCATION_SMOKE_REPORT
    )
    generated_lowered_tb_invocation_smoke = _load_json_if_exists(
        repo_root / GENERATED_LOWERED_TB_INVOCATION_SMOKE_REPORT
    )
    lowered_tb_memory_helper_integration_smoke = _load_json_if_exists(
        repo_root / LOWERED_TB_MEMORY_HELPER_INTEGRATION_SMOKE_REPORT
    )
    tb = _read(tb_path)
    memory_cpp = _read(memory_cpp_path)
    device_helper_header = _read(device_helper_header_path) if device_helper_header_path.is_file() else ""
    runtime_upload_header = _read(runtime_upload_header_path) if runtime_upload_header_path.is_file() else ""
    observable_export_header = _read(observable_export_header_path) if observable_export_header_path.is_file() else ""
    runtime_sequence_header = _read(runtime_sequence_header_path) if runtime_sequence_header_path.is_file() else ""

    tb_features = _contains_all(
        tb,
        [
            'import "DPI-C" function void mem_load',
            'import "DPI-C" function bit mem_check',
            'import "DPI-C" function void mem_access',
            'mem_load("init.bin")',
            'mem_check("post.bin", 1\'b0)',
            'mem_check("post.bin", 1\'b1)',
            '$display("TEST PASSED")',
            '$display("TEST FAILED")',
            '$fopen("dcrs.bin", "r")',
            "mem_req_valid",
            "mem_rsp_ready",
            "busy",
        ],
    )
    memory_features = _contains_all(
        memory_cpp,
        [
            "class Ram final",
            "std::unordered_map<uint64_t, std::unique_ptr<uint8_t[]>>",
            "void mem_load",
            "svBit mem_check",
            "void mem_access",
            's_ram.dump("check.bin")',
            "IO_COUT_ADDR",
            "s_print_bufs",
            "printf",
            "block_addr * MEM_BLOCK_SIZE",
        ],
    )
    mem_block_size = _macro_int(memory_cpp, "MEM_BLOCK_SIZE")
    io_cout_addr = _macro_int(memory_cpp, "IO_COUT_ADDR")
    io_cout_size = _macro_int(memory_cpp, "IO_COUT_SIZE")
    device_helper_features = _contains_all(
        device_helper_header,
        [
            "VortexMemSegment",
            "VortexMemBlock",
            "VortexIoCoutCapture",
            "vortex_init_blocks_from_segments",
            "vortex_mem_access_device_helper",
            "vortex_post_compare_device_helper",
            "VORTEX_MEM_BLOCK_SIZE 64u",
            "VORTEX_IO_COUT_ADDR 0x40ull",
            "u64_payload_offset_u64_size_bytes",
        ],
    )
    device_helper_ready = bool(device_helper_header) and all(device_helper_features.values())
    runtime_upload_features = _contains_all(
        runtime_upload_header,
        [
            "VortexCudaUploadDriver",
            "VortexRuntimeBuffer",
            "VortexRuntimeUploadSummary",
            "vortex_upload_runtime_buffers",
            "vortex_release_runtime_buffers",
            "VORTEX_BUFFER_HOST_TO_DEVICE",
            "VORTEX_BUFFER_DEVICE_TO_HOST",
            "cuMemcpyHtoD",
            "cuMemsetD8",
        ],
    )
    runtime_upload_helper_ready = bool(runtime_upload_header) and all(runtime_upload_features.values())
    observable_export_features = _contains_all(
        observable_export_header,
        [
            "VortexObservableExportDriver",
            "VortexObservableDeviceBuffers",
            "VortexObservableExportSummary",
            "vortex_export_observables",
            "vortex_stdout_contains_test_passed",
            "vortex_observable_authority_update",
            "cuMemcpyDtoH",
            "memory_post_condition_passed",
            "stdout_test_passed_observed",
            "authority_passed",
            "authority_source",
            "post_compare_exported",
            "stdout_exported",
        ],
    )
    observable_export_helper_ready = bool(observable_export_header) and all(observable_export_features.values())
    runtime_sequence_features = _contains_all(
        runtime_sequence_header,
        [
            "VortexRuntimeSequenceArgs",
            "VortexRuntimeSequenceSummary",
            "VortexDcrWrite",
            "VortexDcrApplyFn",
            "VortexKernelLaunchFn",
            "vortex_run_runtime_sequence",
            "vortex_upload_runtime_buffers",
            "vortex_export_observables",
            "vortex_release_runtime_buffers",
            "vortex_observable_buffers_from_runtime_buffers",
            "dcr_reset_asserted",
            "kernel_launch_invoked",
            "observable_export_invoked",
        ],
    )
    runtime_sequence_helper_ready = bool(runtime_sequence_header) and all(runtime_sequence_features.values())
    device_buffers_materialized = (
        isinstance(device_buffer_materialization, dict)
        and device_buffer_materialization.get("status") == "device_buffers_materialized"
    )
    dcr_schedule_materialized = (
        isinstance(dcr_schedule, dict) and dcr_schedule.get("status") == "dcr_schedule_materialized"
    )
    runtime_invocation_plan_ready = (
        isinstance(runtime_invocation_plan, dict)
        and runtime_invocation_plan.get("status") == "runtime_sequence_invocation_plan_ready_not_invoked"
    )
    lowered_tb_invocation_smoke_ready = (
        isinstance(lowered_tb_invocation_smoke, dict)
        and lowered_tb_invocation_smoke.get("status") == "lowered_tb_invocation_smoke_ready_not_integrated"
    )
    materialized_runtime_invocation_smoke_ready = (
        isinstance(materialized_runtime_invocation_smoke, dict)
        and materialized_runtime_invocation_smoke.get("status")
        == "materialized_runtime_invocation_smoke_ready_not_integrated"
    )
    generated_lowered_tb_invocation_smoke_passed = (
        isinstance(generated_lowered_tb_invocation_smoke, dict)
        and generated_lowered_tb_invocation_smoke.get("status")
        == "generated_lowered_tb_invocation_smoke_passed"
    )
    lowered_tb_memory_helper_integration_smoke_passed = (
        isinstance(lowered_tb_memory_helper_integration_smoke, dict)
        and lowered_tb_memory_helper_integration_smoke.get("status")
        == "lowered_tb_memory_helper_integration_smoke_passed"
    )

    reviewed = all(tb_features.values()) and all(memory_features.values()) and mem_block_size == 64
    gpu_observable_ready = False
    implementation_ready = False
    if generated_lowered_tb_invocation_smoke_passed:
        runtime_invocation_missing = "real_verilator_generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence"
    elif materialized_runtime_invocation_smoke_ready:
        runtime_invocation_missing = "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence"
    elif lowered_tb_invocation_smoke_ready:
        runtime_invocation_missing = "generated_lowered_tb_calls_vortex_lowered_tb_invoke_runtime_sequence"
    elif runtime_invocation_plan_ready:
        runtime_invocation_missing = "lowered_tb_invokes_vortex_run_runtime_sequence"
    elif runtime_sequence_helper_ready:
        runtime_invocation_missing = "runtime_execution_invokes_vortex_runtime_sequence_helper"
    elif runtime_upload_helper_ready:
        runtime_invocation_missing = "runtime_execution_invokes_vortex_upload_runtime_buffers"
    else:
        runtime_invocation_missing = "device_memory_buffers_uploaded_to_runtime"
    missing = []
    if not reviewed:
        missing.append("dpi_memory_bridge_source_patterns")
    if not device_helper_ready:
        missing.append("gpu_memory_model_for_64B_block_reads_writes_and_byteen")
        missing.append("gpu_mmio_stdout_capture_for_IO_COUT")
        missing.append("gpu_post_bin_memory_compare_or_export")
    else:
        missing.append(
            "real_verilator_generated_lowered_tb_mem_access_calls_vortex_device_helper"
            if lowered_tb_memory_helper_integration_smoke_passed
            else "lowered_tb_mem_access_device_helper_integration"
        )
        if device_buffers_materialized:
            missing.append(runtime_invocation_missing)
        else:
            missing.append("device_memory_buffers_materialized_for_runtime_upload")
        missing.append(
            runtime_invocation_missing
            if runtime_sequence_helper_ready
            else "runtime_execution_invokes_vortex_export_observables"
            if observable_export_helper_ready
            else "gpu_post_compare_result_export"
        )
        missing.append(
            "runtime_execution_reports_vortex_observable_authority"
            if observable_export_helper_ready
            else "gpu_stdout_or_post_compare_observable_export"
        )
    if not implementation_ready:
        if runtime_sequence_helper_ready:
            missing.append(runtime_invocation_missing)
        else:
            missing.append(
                "runtime_execution_applies_vortex_dcr_schedule_while_reset_asserted"
                if dcr_schedule_materialized
                else "dcrs_bin_gpu_schedule_or_host_phase_bridge"
            )
    if not gpu_observable_ready:
        missing.append("stdout_TEST_PASSED_or_memory_post_condition_gpu_observable")
    missing = list(dict.fromkeys(missing))

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_dpi_memory_bridge_review",
        "status": "reviewed_blocked_on_gpu_bridge_implementation" if reviewed else "blocked_missing_review_evidence",
        "tb": _display_path(tb_path, repo_root=repo_root),
        "memory_cpp": _display_path(memory_cpp_path, repo_root=repo_root),
        "device_helper_header": _display_path(device_helper_header_path, repo_root=repo_root)
        if device_helper_header_path.is_file()
        else None,
        "runtime_upload_header": _display_path(runtime_upload_header_path, repo_root=repo_root)
        if runtime_upload_header_path.is_file()
        else None,
        "observable_export_header": _display_path(observable_export_header_path, repo_root=repo_root)
        if observable_export_header_path.is_file()
        else None,
        "runtime_sequence_header": _display_path(runtime_sequence_header_path, repo_root=repo_root)
        if runtime_sequence_header_path.is_file()
        else None,
        "reviewed_bridge_boundary": reviewed,
        "runtime_launchable": False,
        "implementation_ready": implementation_ready,
        "gpu_observable_ready": gpu_observable_ready,
        "device_helper_ready_for_integration": device_helper_ready,
        "device_buffers_materialized_for_upload": device_buffers_materialized,
        "dcr_schedule_materialized": dcr_schedule_materialized,
        "runtime_upload_helper_ready": runtime_upload_helper_ready,
        "observable_export_helper_ready": observable_export_helper_ready,
        "runtime_sequence_helper_ready": runtime_sequence_helper_ready,
        "runtime_invocation_plan_ready": runtime_invocation_plan_ready,
        "lowered_tb_invocation_smoke_ready": lowered_tb_invocation_smoke_ready,
        "materialized_runtime_invocation_smoke_ready": materialized_runtime_invocation_smoke_ready,
        "generated_lowered_tb_invocation_smoke_passed": generated_lowered_tb_invocation_smoke_passed,
        "lowered_tb_memory_helper_integration_smoke_passed": lowered_tb_memory_helper_integration_smoke_passed,
        "memory_model": {
            "block_size_bytes": mem_block_size,
            "io_cout_addr": io_cout_addr,
            "io_cout_size": io_cout_size,
            "byte_enable_write_granularity": "byte",
            "sparse_page_ram": True,
            "init_file": "init.bin",
            "expected_file": "post.bin",
            "dcr_file": "dcrs.bin",
            "dump_file": "check.bin",
        },
        "binary_input_summary": {
            "report": _display_path(repo_root / BINARY_INPUT_REPORT, repo_root=repo_root),
            "status": binary_input_summary.get("status"),
            "init_segment_count": binary_input_summary.get("init_memory", {}).get("segment_count")
            if isinstance(binary_input_summary.get("init_memory"), dict)
            else None,
            "init_total_payload_bytes": binary_input_summary.get("init_memory", {}).get("total_payload_bytes")
            if isinstance(binary_input_summary.get("init_memory"), dict)
            else None,
            "post_segment_count": binary_input_summary.get("post_memory", {}).get("segment_count")
            if isinstance(binary_input_summary.get("post_memory"), dict)
            else None,
            "post_total_payload_bytes": binary_input_summary.get("post_memory", {}).get("total_payload_bytes")
            if isinstance(binary_input_summary.get("post_memory"), dict)
            else None,
            "dcr_write_count": binary_input_summary.get("dcr_writes", {}).get("write_count")
            if isinstance(binary_input_summary.get("dcr_writes"), dict)
            else None,
        }
        if binary_input_summary is not None
        else None,
        "gpu_memory_model_plan": {
            "report": _display_path(repo_root / GPU_MEMORY_MODEL_PLAN_REPORT, repo_root=repo_root),
            "status": gpu_memory_model_plan.get("status"),
            "minimum_static_input_bytes": gpu_memory_model_plan.get("memory_model_abi", {}).get("minimum_static_input_bytes")
            if isinstance(gpu_memory_model_plan.get("memory_model_abi"), dict)
            else None,
            "init_block_count": gpu_memory_model_plan.get("memory_model_abi", {}).get("init_block_count")
            if isinstance(gpu_memory_model_plan.get("memory_model_abi"), dict)
            else None,
            "device_buffer_count": len(gpu_memory_model_plan.get("device_buffers", []))
            if isinstance(gpu_memory_model_plan.get("device_buffers"), list)
            else None,
            "runtime_launchable": gpu_memory_model_plan.get("runtime_launchable"),
        }
        if gpu_memory_model_plan is not None
        else None,
        "memory_model_reference": {
            "report": _display_path(repo_root / MEMORY_MODEL_REFERENCE_REPORT, repo_root=repo_root),
            "status": memory_model_reference.get("status"),
            "initial_post_match": memory_model_reference.get("initial_post_compare", {}).get("match")
            if isinstance(memory_model_reference.get("initial_post_compare"), dict)
            else None,
            "post_replay_status": memory_model_reference.get("post_replay_self_check", {}).get("status")
            if isinstance(memory_model_reference.get("post_replay_self_check"), dict)
            else None,
            "io_cout_status": memory_model_reference.get("io_cout_self_check", {}).get("status")
            if isinstance(memory_model_reference.get("io_cout_self_check"), dict)
            else None,
            "reference_semantics_ready": memory_model_reference.get("gpu_bridge_implication", {}).get(
                "reference_semantics_ready"
            )
            if isinstance(memory_model_reference.get("gpu_bridge_implication"), dict)
            else None,
        }
        if memory_model_reference is not None
        else None,
        "device_buffer_materialization": {
            "report": _display_path(repo_root / DEVICE_BUFFER_MATERIALIZE_REPORT, repo_root=repo_root),
            "status": device_buffer_materialization.get("status"),
            "host_to_device_bytes": device_buffer_materialization.get("totals", {}).get("host_to_device_bytes")
            if isinstance(device_buffer_materialization.get("totals"), dict)
            else None,
            "device_to_host_initial_bytes": device_buffer_materialization.get("totals", {}).get(
                "device_to_host_initial_bytes"
            )
            if isinstance(device_buffer_materialization.get("totals"), dict)
            else None,
            "buffer_count": len(device_buffer_materialization.get("device_buffers", []))
            if isinstance(device_buffer_materialization.get("device_buffers"), list)
            else None,
            "device_buffers_materialized": device_buffers_materialized,
        }
        if device_buffer_materialization is not None
        else None,
        "dcr_schedule": {
            "report": _display_path(repo_root / DCR_SCHEDULE_REPORT, repo_root=repo_root),
            "status": dcr_schedule.get("status"),
            "write_count": dcr_schedule.get("write_count"),
            "device_schedule_bytes": dcr_schedule.get("device_schedule", {}).get("bytes")
            if isinstance(dcr_schedule.get("device_schedule"), dict)
            else None,
            "reset_asserted_during_all_dcr_writes": dcr_schedule.get("schedule_semantics", {}).get(
                "reset_asserted_during_all_dcr_writes"
            )
            if isinstance(dcr_schedule.get("schedule_semantics"), dict)
            else None,
            "dcr_schedule_materialized": dcr_schedule_materialized,
            "runtime_launchable": False,
        }
        if dcr_schedule is not None
        else None,
        "runtime_sequence": {
            "header": _display_path(runtime_sequence_header_path, repo_root=repo_root),
            "helper_ready": runtime_sequence_helper_ready,
            "invokes_upload_helper": runtime_sequence_features.get("vortex_upload_runtime_buffers"),
            "invokes_observable_export_helper": runtime_sequence_features.get("vortex_export_observables"),
            "applies_dcr_with_reset_asserted_summary": runtime_sequence_features.get("dcr_reset_asserted"),
            "launch_callback_boundary": runtime_sequence_features.get("VortexKernelLaunchFn"),
            "runtime_launchable": False,
        }
        if runtime_sequence_header_path.is_file()
        else None,
        "runtime_invocation_plan": {
            "report": _display_path(repo_root / RUNTIME_INVOCATION_PLAN_REPORT, repo_root=repo_root),
            "status": runtime_invocation_plan.get("status"),
            "plan_ready": runtime_invocation_plan.get("plan_ready"),
            "entrypoint": runtime_invocation_plan.get("entrypoint"),
            "required_order": runtime_invocation_plan.get("required_order"),
            "runtime_launchable": runtime_invocation_plan.get("runtime_launchable"),
        }
        if runtime_invocation_plan is not None
        else None,
        "lowered_tb_invocation_smoke": {
            "report": _display_path(repo_root / LOWERED_TB_INVOCATION_SMOKE_REPORT, repo_root=repo_root),
            "status": lowered_tb_invocation_smoke.get("status"),
            "smoke_ready": lowered_tb_invocation_smoke.get("smoke_ready"),
            "runtime_launchable": lowered_tb_invocation_smoke.get("runtime_launchable"),
        }
        if lowered_tb_invocation_smoke is not None
        else None,
        "materialized_runtime_invocation_smoke": {
            "report": _display_path(
                repo_root / MATERIALIZED_RUNTIME_INVOCATION_SMOKE_REPORT,
                repo_root=repo_root,
            ),
            "status": materialized_runtime_invocation_smoke.get("status"),
            "smoke_ready": materialized_runtime_invocation_smoke.get("smoke_ready"),
            "host_to_device_bytes": materialized_runtime_invocation_smoke.get("host_to_device_bytes"),
            "device_to_host_initial_bytes": materialized_runtime_invocation_smoke.get(
                "device_to_host_initial_bytes"
            ),
            "dcr_write_count": materialized_runtime_invocation_smoke.get("dcr_write_count"),
            "runtime_launchable": materialized_runtime_invocation_smoke.get("runtime_launchable"),
        }
        if materialized_runtime_invocation_smoke is not None
        else None,
        "generated_lowered_tb_invocation_smoke": {
            "report": _display_path(
                repo_root / GENERATED_LOWERED_TB_INVOCATION_SMOKE_REPORT,
                repo_root=repo_root,
            ),
            "status": generated_lowered_tb_invocation_smoke.get("status"),
            "generated_lowered_tb_invocation_smoke_passed": generated_lowered_tb_invocation_smoke.get(
                "generated_lowered_tb_invocation_smoke_passed"
            ),
            "host_to_device_bytes": generated_lowered_tb_invocation_smoke.get("host_to_device_bytes"),
            "device_to_host_initial_bytes": generated_lowered_tb_invocation_smoke.get(
                "device_to_host_initial_bytes"
            ),
            "dcr_write_count": generated_lowered_tb_invocation_smoke.get("dcr_write_count"),
            "runtime_launchable": generated_lowered_tb_invocation_smoke.get("runtime_launchable"),
        }
        if generated_lowered_tb_invocation_smoke is not None
        else None,
        "lowered_tb_memory_helper_integration_smoke": {
            "report": _display_path(
                repo_root / LOWERED_TB_MEMORY_HELPER_INTEGRATION_SMOKE_REPORT,
                repo_root=repo_root,
            ),
            "status": lowered_tb_memory_helper_integration_smoke.get("status"),
            "lowered_tb_memory_helper_integration_smoke_passed": lowered_tb_memory_helper_integration_smoke.get(
                "lowered_tb_memory_helper_integration_smoke_passed"
            ),
            "host_to_device_bytes": lowered_tb_memory_helper_integration_smoke.get("host_to_device_bytes"),
            "device_to_host_initial_bytes": lowered_tb_memory_helper_integration_smoke.get(
                "device_to_host_initial_bytes"
            ),
            "init_segment_count": lowered_tb_memory_helper_integration_smoke.get("init_segment_count"),
            "post_segment_count": lowered_tb_memory_helper_integration_smoke.get("post_segment_count"),
            "runtime_launchable": lowered_tb_memory_helper_integration_smoke.get("runtime_launchable"),
        }
        if lowered_tb_memory_helper_integration_smoke is not None
        else None,
        "tb_features": tb_features,
        "memory_cpp_features": memory_features,
        "device_helper_features": device_helper_features,
        "runtime_upload_features": runtime_upload_features,
        "observable_export_features": observable_export_features,
        "runtime_sequence_features": runtime_sequence_features,
        "bridge_classification": {
            "cpu_authority": [
                "mem_load(init.bin)",
                "DCR writes from dcrs.bin",
                "DUT busy low-to-high completion",
                "mem_check(post.bin, verbose=1)",
                "stdout TEST PASSED",
            ],
            "gpu_bridge_requirement": [
                "device-visible 64B block memory read/write model",
                "byte-enable write handling",
                "MMIO stdout capture for IO_COUT",
                "post.bin-equivalent memory comparison or export",
                "runtime application of the materialized DCR write schedule while reset is asserted",
            ],
            "why_not_template_only": [
                "Vortex correctness is not a fixed coverage-word compare on root state",
                "DPI memory state is outside Verilator root fields",
                "stdout TEST PASSED is produced after post.bin memory comparison",
            ],
        },
        "missing_prerequisites": missing,
        "recommended_next": "connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence"
        if generated_lowered_tb_invocation_smoke_passed and lowered_tb_memory_helper_integration_smoke_passed
        else "run_lowered_tb_memory_helper_integration_smoke"
        if generated_lowered_tb_invocation_smoke_passed and not lowered_tb_memory_helper_integration_smoke_passed
        else "generate_lowered_tb_call_to_vortex_lowered_tb_invoke_runtime_sequence"
        if materialized_runtime_invocation_smoke_ready
        else "integrate_vortex_device_memory_helper_with_lowered_tb_and_observable_export"
        if device_helper_ready
        else (
            "implement_vortex_device_memory_helper_from_reference_model_before_launch_template_timing"
            if memory_model_reference is not None
            else "run_vortex_memory_model_reference_before_launch_template_timing"
        ),
        "non_claims": [
            "not_vortex_gpu_execution",
            "not_cpu_vs_hybrid_timing_evidence",
            "not_speedup_or_usefulness_claim",
            "reviewed_boundary_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_review(Path(args.repo_root))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.write_report:
        if not args.report_out:
            print("--write-report requires --report-out", file=sys.stderr)
            return 2
        Path(args.report_out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
