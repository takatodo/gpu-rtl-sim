"""Assess the first Vortex RTLMeter CPU-vs-hybrid measurement gate."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any

import yaml


DESCRIPTOR = Path("third_party/rtlmeter/designs/Vortex/descriptor.yaml")
EXPECTED_FIRST_CASE = "Vortex:mini:hello"
BRIDGE_REVIEW_REPORT = Path("reports/rtlmeter_vortex_dpi_memory_bridge_review.json")
SOURCE_CLOSURE_REPORT = Path("reports/rtlmeter_vortex_source_closure.json")
CPU_REFERENCE_REPORT = Path("reports/rtlmeter_vortex_cpu_reference_summary.json")
HYBRID_CANDIDATE_REPORT = Path("reports/rtlmeter_vortex_hybrid_candidate_summary.json")
OBSERVABLE_AUTHORITY_AUDIT_REPORT = Path("reports/rtlmeter_vortex_observable_authority_audit.json")


def _load_yaml(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected YAML object")
    return payload


def _load_json_if_exists(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_files(root: Path, rel_paths: object) -> list[dict[str, Any]]:
    if not isinstance(rel_paths, list):
        return []
    files = []
    for item in rel_paths:
        if not isinstance(item, str):
            continue
        path = root / item
        files.append({"path": item, "exists": path.is_file(), "size_bytes": path.stat().st_size if path.is_file() else None})
    return files


def _configuration_tests(descriptor: Mapping[str, Any]) -> dict[str, list[str]]:
    configs = _mapping(descriptor.get("configurations"))
    result: dict[str, list[str]] = {}
    for name, value in configs.items():
        tests = _mapping(_mapping(value).get("execute")).get("tests")
        if isinstance(tests, Mapping):
            result[str(name)] = sorted(str(test_name) for test_name in tests)
    return result


def _first_case_inputs(design_root: Path, descriptor: Mapping[str, Any]) -> dict[str, Any]:
    tests = _mapping(_mapping(descriptor.get("execute")).get("tests"))
    hello = _mapping(tests.get("hello"))
    return {
        "case": EXPECTED_FIRST_CASE,
        "files": _list_files(design_root, hello.get("files")),
        "args": _mapping(_mapping(_mapping(descriptor.get("configurations")).get("mini")).get("execute"))
        .get("tests", {})
        .get("hello", {})
        if isinstance(_mapping(_mapping(_mapping(descriptor.get("configurations")).get("mini")).get("execute")).get("tests"), Mapping)
        else {},
        "authority": {
            "stdout_must_contain": "TEST PASSED",
            "post_hook": _mapping(_mapping(descriptor.get("execute")).get("common")).get("postHook"),
            "memory_init": "init.bin",
            "memory_expected": "post.bin",
            "dcr_program": "dcrs.bin",
        },
    }


def build_readiness(repo_root: Path) -> dict[str, Any]:
    descriptor_path = repo_root / DESCRIPTOR
    descriptor = _load_yaml(descriptor_path)
    design_root = descriptor_path.parent
    compile_section = _mapping(descriptor.get("compile"))
    source_files = compile_section.get("verilogSourceFiles", [])
    include_files = compile_section.get("verilogIncludeFiles", [])
    cpp_files = compile_section.get("cppSourceFiles", [])
    first_case = _first_case_inputs(design_root, descriptor)
    first_case_files_exist = all(item.get("exists") is True for item in first_case["files"])
    template_path = repo_root / "config/slice_launch_templates/vortex_mini_hello.json"
    authority_path = repo_root / "config/rtlmeter_sidecar_authorities/rtlmeter_vortex_mini_hello.json"
    bridge_review = _load_json_if_exists(repo_root / BRIDGE_REVIEW_REPORT)
    source_closure_report = _load_json_if_exists(repo_root / SOURCE_CLOSURE_REPORT)
    cpu_reference_report = _load_json_if_exists(repo_root / CPU_REFERENCE_REPORT)
    hybrid_candidate_report = _load_json_if_exists(repo_root / HYBRID_CANDIDATE_REPORT)
    observable_authority_audit = _load_json_if_exists(repo_root / OBSERVABLE_AUTHORITY_AUDIT_REPORT)
    cpu_reference_ready = (
        isinstance(cpu_reference_report, Mapping)
        and cpu_reference_report.get("status") == "cpu_reference_passed"
        and cpu_reference_report.get("cpu_reference_ready_for_hybrid_compare") is True
    )
    template = _load_json_if_exists(template_path)
    authority = _load_json_if_exists(authority_path)
    template_summary = None
    if template is not None:
        source_closure = _mapping(template.get("source_closure"))
        acceptance = _mapping(template.get("acceptance"))
        template_summary = {
            "path": _display_path(template_path, repo_root=repo_root),
            "status": template.get("status"),
            "runtime_launchable": template.get("runtime_launchable"),
            "source_closure_status": source_closure.get("status"),
            "non_dry_run_must_fail_until_source_closure_complete": acceptance.get(
                "non_dry_run_must_fail_until_source_closure_complete"
            ),
            "speedup_claim_allowed_by_template_alone": acceptance.get("speedup_claim_allowed_by_template_alone"),
        }
    authority_summary = None
    if authority is not None:
        authority_summary = {
            "path": _display_path(authority_path, repo_root=repo_root),
            "schema_role": authority.get("schema_role"),
            "status": authority.get("status"),
            "runtime_launchable": authority.get("runtime_launchable"),
            "coverage_output_target": authority.get("coverage_output_target"),
        }
    existing_reports = sorted(
        _display_path(path, repo_root=repo_root)
        for path in (repo_root / "reports").glob("*vortex*")
        if path.is_file() and ("cpu_vs_hybrid" in path.name or "timing" in path.name)
    )

    missing = []
    if template is None:
        missing.append("slice_launch_template.vortex_mini_hello")
    if authority is None:
        missing.append("rtlmeter_sidecar_authority.vortex_mini_hello")
    if not cpu_reference_ready:
        missing.append("cpu_reference_report.vortex")
    if not existing_reports:
        missing.append("cpu_vs_hybrid_timing_report.vortex")
    if (
        isinstance(hybrid_candidate_report, Mapping)
        and hybrid_candidate_report.get("status") == "hybrid_candidate_blocked_invalid_verilator_option"
    ):
        missing.append("path_selected_sidecar_capable_verilator_or_wrapper")
    if (
        isinstance(hybrid_candidate_report, Mapping)
        and hybrid_candidate_report.get("status")
        == "hybrid_candidate_blocked_missing_reviewed_vortex_sidecar_context"
    ):
        missing.append("reviewed_vortex_sidecar_context_for_wrapper_handoff")
    if (
        isinstance(hybrid_candidate_report, Mapping)
        and hybrid_candidate_report.get("status")
        == "hybrid_candidate_blocked_missing_vortex_authority_registry_source_closure"
    ):
        missing.append("reviewed_vortex_authority_registry_source_closure")
    if (
        isinstance(hybrid_candidate_report, Mapping)
        and hybrid_candidate_report.get("status") == "hybrid_candidate_blocked_sidecar_verilate_execution"
    ):
        missing.append("direct_sidecar_verilate_execution_or_vsim_proxy_for_vortex")
    if (
        isinstance(hybrid_candidate_report, Mapping)
        and hybrid_candidate_report.get("status")
        == "hybrid_candidate_stdout_cycles_observed_proxy_handoff_blocked"
    ):
        missing.append("reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export")
    if (
        isinstance(hybrid_candidate_report, Mapping)
        and hybrid_candidate_report.get("status")
        == "hybrid_candidate_proxy_handoff_observed_timing_missing"
    ):
        if (
            isinstance(observable_authority_audit, Mapping)
            and observable_authority_audit.get("status")
            == "observable_authority_audit_proxy_and_fake_ready_real_runtime_missing"
        ):
            missing.append("real_runtime_observable_authority")
        else:
            missing.append("hybrid_observable_authority")
    if isinstance(observable_authority_audit, Mapping):
        for item in observable_authority_audit.get("missing_prerequisites", []):
            if item and item != "cpu_vs_hybrid_timing_report.vortex":
                missing.append(str(item))
    if bridge_review is None and cpp_files:
        missing.append("dpi_memory_bridge_review_for_gpu_sidecar")
    elif bridge_review is not None:
        missing.extend(str(item) for item in bridge_review.get("missing_prerequisites", []) if item)
    if "stdout_TEST_PASSED_or_memory_post_condition_gpu_observable" not in missing:
        missing.append("stdout_TEST_PASSED_or_memory_post_condition_gpu_observable")
    source_closure_complete = (
        isinstance(source_closure_report, Mapping)
        and source_closure_report.get("status") == "descriptor_source_closure_complete"
        and source_closure_report.get("all_sources_exist") is True
    )
    if template_summary is not None and authority_summary is not None:
        recommended_sequence = []
        if not source_closure_complete:
            recommended_sequence.append("complete_vortex_descriptor_dpi_source_closure")
        bridge_mapping = _mapping(bridge_review)
        if bridge_mapping.get("generated_lowered_tb_invocation_smoke_passed") is True:
            runtime_step = "connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence"
            needs_helper_integration = False
        elif bridge_mapping.get("materialized_runtime_invocation_smoke_ready") is True:
            runtime_step = "generate_lowered_tb_call_to_vortex_lowered_tb_invoke_runtime_sequence"
            needs_helper_integration = False
        elif bridge_mapping.get("lowered_tb_invocation_smoke_ready") is True:
            runtime_step = "generate_lowered_tb_call_to_vortex_lowered_tb_invoke_runtime_sequence"
            needs_helper_integration = True
        elif bridge_mapping.get("runtime_sequence_helper_ready") is True:
            runtime_step = "invoke_vortex_runtime_sequence_helper_from_lowered_tb_or_launch_template"
            needs_helper_integration = True
        else:
            runtime_step = "invoke_vortex_runtime_upload_buffers"
            needs_helper_integration = True
        bridge_missing = bridge_mapping.get("missing_prerequisites")
        if (
            isinstance(bridge_missing, list)
            and "lowered_tb_mem_access_device_helper_integration" in bridge_missing
        ):
            needs_helper_integration = True
        if needs_helper_integration:
            recommended_sequence.append("integrate_lowered_tb_mem_access_with_vortex_device_helper")
        if (
            isinstance(hybrid_candidate_report, Mapping)
            and hybrid_candidate_report.get("status") == "hybrid_candidate_blocked_invalid_verilator_option"
        ):
            recommended_sequence.append("install_or_select_sidecar_capable_verilator_wrapper_for_vortex")
        if (
            isinstance(hybrid_candidate_report, Mapping)
            and hybrid_candidate_report.get("status")
            == "hybrid_candidate_blocked_missing_reviewed_vortex_sidecar_context"
        ):
            recommended_sequence.append("provide_reviewed_vortex_sidecar_context_for_wrapper_handoff")
        if (
            isinstance(hybrid_candidate_report, Mapping)
            and hybrid_candidate_report.get("status")
            == "hybrid_candidate_blocked_missing_vortex_authority_registry_source_closure"
        ):
            recommended_sequence.append("review_vortex_authority_registry_source_closure_for_wrapper_handoff")
        if (
            isinstance(hybrid_candidate_report, Mapping)
            and hybrid_candidate_report.get("status") == "hybrid_candidate_blocked_sidecar_verilate_execution"
        ):
            recommended_sequence.append("enable_direct_sidecar_verilate_or_vsim_proxy_for_vortex")
        if (
            isinstance(hybrid_candidate_report, Mapping)
            and hybrid_candidate_report.get("status")
            == "hybrid_candidate_stdout_cycles_observed_proxy_handoff_blocked"
        ):
            recommended_sequence.append("provide_reviewed_vsim_sidecar_proxy_target_or_vortex_observable_export")
        if (
            isinstance(hybrid_candidate_report, Mapping)
            and hybrid_candidate_report.get("status")
            == "hybrid_candidate_proxy_handoff_observed_timing_missing"
        ):
            if (
                isinstance(observable_authority_audit, Mapping)
                and observable_authority_audit.get("status")
                == "observable_authority_audit_proxy_and_fake_ready_real_runtime_missing"
            ):
                recommended_sequence.append("connect_real_verilator_generated_lowered_tb_to_vortex_runtime_sequence")
            else:
                recommended_sequence.append("invoke_vortex_observable_export_and_report_authority")
        recommended_sequence.extend(
            [
                runtime_step,
                "invoke_vortex_observable_export_and_report_authority",
                "run_cpu_vs_hybrid_timing_for_Vortex_mini_hello",
                "only_then_try_Vortex_mini_saxpy_or_sgemm",
            ]
        )
    else:
        recommended_sequence = [
            "define_vortex_mini_hello_authority_and_template",
            "run_cpu_reference_for_Vortex_mini_hello",
            "run_hybrid_candidate_or_fail_closed_on_dpi_memory_bridge",
            "compare_stdout_TEST_PASSED_and_memory_post_condition",
            "only_then_try_Vortex_mini_saxpy_or_sgemm",
        ]
    missing = list(dict.fromkeys(missing))
    recommended_sequence = list(dict.fromkeys(recommended_sequence))

    return {
        "schema_version": 1,
        "surface": "rtlmeter_vortex_first_gate_readiness",
        "status": "blocked_missing_first_gate" if missing else "ready_for_first_measurement",
        "descriptor": _display_path(descriptor_path, repo_root=repo_root),
        "top_module": compile_section.get("topModule"),
        "main_clock": compile_section.get("mainClock"),
        "verilog_source_count": len(source_files) if isinstance(source_files, list) else 0,
        "include_file_count": len(include_files) if isinstance(include_files, list) else 0,
        "cpp_source_files": list(cpp_files) if isinstance(cpp_files, list) else [],
        "configuration_tests": _configuration_tests(descriptor),
        "first_measurement_candidate": first_case,
        "first_case_files_exist": first_case_files_exist,
        "slice_launch_template": template_summary,
        "sidecar_authority": authority_summary,
        "descriptor_source_closure": {
            "report": _display_path(repo_root / SOURCE_CLOSURE_REPORT, repo_root=repo_root),
            "status": source_closure_report.get("status"),
            "all_sources_exist": source_closure_report.get("all_sources_exist"),
            "source_counts": source_closure_report.get("source_counts"),
            "runtime_launchable": _mapping(source_closure_report.get("execution_authority")).get("runtime_launchable"),
        }
        if source_closure_report is not None
        else None,
        "cpu_reference": {
            "report": _display_path(repo_root / CPU_REFERENCE_REPORT, repo_root=repo_root),
            "status": cpu_reference_report.get("status"),
            "cpu_reference_ready_for_hybrid_compare": cpu_reference_report.get(
                "cpu_reference_ready_for_hybrid_compare"
            ),
            "stdout_test_passed": cpu_reference_report.get("stdout_test_passed"),
            "finish_observed": cpu_reference_report.get("finish_observed"),
            "dcr_write_count": cpu_reference_report.get("dcr_write_count"),
            "metrics": cpu_reference_report.get("metrics"),
        }
        if cpu_reference_report is not None
        else None,
        "hybrid_candidate": {
            "report": _display_path(repo_root / HYBRID_CANDIDATE_REPORT, repo_root=repo_root),
            "status": hybrid_candidate_report.get("status"),
            "invalid_sim_accel_option": hybrid_candidate_report.get("invalid_sim_accel_option"),
            "wrapper_captured_sidecar_planning": hybrid_candidate_report.get("wrapper_captured_sidecar_planning"),
            "wrapper_runtime_status": hybrid_candidate_report.get("wrapper_runtime_status"),
            "wrapper_inspection_status": hybrid_candidate_report.get("wrapper_inspection_status"),
            "wrapper_sidecar_accel": hybrid_candidate_report.get("wrapper_sidecar_accel"),
            "wrapper_sidecar_states": hybrid_candidate_report.get("wrapper_sidecar_states"),
            "wrapper_sidecar_steps": hybrid_candidate_report.get("wrapper_sidecar_steps"),
            "blocked_missing_reviewed_source_closure": hybrid_candidate_report.get(
                "blocked_missing_reviewed_source_closure"
            ),
            "blocked_missing_authority_registry_source_closure": hybrid_candidate_report.get(
                "blocked_missing_authority_registry_source_closure"
            ),
            "blocked_sidecar_verilate_execution": hybrid_candidate_report.get("blocked_sidecar_verilate_execution"),
            "handoff_metadata_ready": hybrid_candidate_report.get("handoff_metadata_ready"),
            "stdout_cycles_plan_seed": hybrid_candidate_report.get("stdout_cycles_plan_seed"),
            "stdout_cycles_plan_authority_registry": hybrid_candidate_report.get(
                "stdout_cycles_plan_authority_registry"
            ),
            "runner_contract_status": hybrid_candidate_report.get("runner_contract_status"),
            "runner_command_ready": hybrid_candidate_report.get("runner_command_ready"),
            "adapter_implementation_status": hybrid_candidate_report.get("adapter_implementation_status"),
            "reentry_guard_status": hybrid_candidate_report.get("reentry_guard_status"),
            "sidecar_execution_invoked": hybrid_candidate_report.get("sidecar_execution_invoked"),
            "hybrid_candidate_executed": hybrid_candidate_report.get("hybrid_candidate_executed"),
            "measurement_ready": hybrid_candidate_report.get("measurement_ready"),
        }
        if hybrid_candidate_report is not None
        else None,
        "observable_authority_audit": {
            "report": _display_path(repo_root / OBSERVABLE_AUTHORITY_AUDIT_REPORT, repo_root=repo_root),
            "status": observable_authority_audit.get("status"),
            "proxy_handoff_observed": observable_authority_audit.get("proxy_handoff_observed"),
            "generated_fake_driver_authority_passed": observable_authority_audit.get(
                "generated_fake_driver_authority_passed"
            ),
            "real_verilator_lowered_tb_runtime_call_observed": observable_authority_audit.get(
                "real_verilator_lowered_tb_runtime_call_observed"
            ),
            "real_verilator_memory_helper_call_observed": observable_authority_audit.get(
                "real_verilator_memory_helper_call_observed"
            ),
            "real_verilator_runtime_sequence_marker_observed": observable_authority_audit.get(
                "real_verilator_runtime_sequence_marker_observed"
            ),
            "real_verilator_runtime_stub_observed": observable_authority_audit.get(
                "real_verilator_runtime_stub_observed"
            ),
            "real_verilator_runtime_stub_rebuilt": observable_authority_audit.get(
                "real_verilator_runtime_stub_rebuilt"
            ),
            "real_verilator_runtime_bridge_stub_observed": observable_authority_audit.get(
                "real_verilator_runtime_bridge_stub_observed"
            ),
            "real_verilator_runtime_bridge_stub_rebuilt": observable_authority_audit.get(
                "real_verilator_runtime_bridge_stub_rebuilt"
            ),
            "real_verilator_runtime_invocation_probe_observed": observable_authority_audit.get(
                "real_verilator_runtime_invocation_probe_observed"
            ),
            "real_verilator_runtime_invocation_probe_rebuilt": observable_authority_audit.get(
                "real_verilator_runtime_invocation_probe_rebuilt"
            ),
            "real_verilator_runtime_invocation_probe_executed": observable_authority_audit.get(
                "real_verilator_runtime_invocation_probe_executed"
            ),
            "real_verilator_materialized_runtime_args_probe_observed": observable_authority_audit.get(
                "real_verilator_materialized_runtime_args_probe_observed"
            ),
            "real_verilator_materialized_runtime_args_probe_rebuilt": observable_authority_audit.get(
                "real_verilator_materialized_runtime_args_probe_rebuilt"
            ),
            "real_verilator_materialized_runtime_args_probe_executed": observable_authority_audit.get(
                "real_verilator_materialized_runtime_args_probe_executed"
            ),
            "real_cuda_memory_transport_passed": observable_authority_audit.get(
                "real_cuda_memory_transport_passed"
            ),
            "real_cuda_memory_transport_h2d_bytes": observable_authority_audit.get(
                "real_cuda_memory_transport_h2d_bytes"
            ),
            "real_cuda_memory_transport_d2h_initial_bytes": observable_authority_audit.get(
                "real_cuda_memory_transport_d2h_initial_bytes"
            ),
            "real_cuda_runtime_sequence_preflight_passed": observable_authority_audit.get(
                "real_cuda_runtime_sequence_preflight_passed"
            ),
            "real_cuda_runtime_sequence_preflight_h2d_bytes": observable_authority_audit.get(
                "real_cuda_runtime_sequence_preflight_h2d_bytes"
            ),
            "real_cuda_runtime_sequence_preflight_d2h_initial_bytes": observable_authority_audit.get(
                "real_cuda_runtime_sequence_preflight_d2h_initial_bytes"
            ),
            "real_cuda_runtime_sequence_preflight_dcr_applied_count": observable_authority_audit.get(
                "real_cuda_runtime_sequence_preflight_dcr_applied_count"
            ),
            "real_runtime_observable_authority_ready": observable_authority_audit.get(
                "real_runtime_observable_authority_ready"
            ),
        }
        if observable_authority_audit is not None
        else None,
        "dpi_memory_bridge_review": {
            "report": _display_path(repo_root / BRIDGE_REVIEW_REPORT, repo_root=repo_root),
            "status": bridge_review.get("status"),
            "reviewed_bridge_boundary": bridge_review.get("reviewed_bridge_boundary"),
            "implementation_ready": bridge_review.get("implementation_ready"),
            "gpu_observable_ready": bridge_review.get("gpu_observable_ready"),
            "device_helper_ready_for_integration": bridge_review.get("device_helper_ready_for_integration"),
            "device_helper_header": bridge_review.get("device_helper_header"),
            "device_buffers_materialized_for_upload": bridge_review.get("device_buffers_materialized_for_upload"),
            "device_buffer_materialization": bridge_review.get("device_buffer_materialization"),
            "dcr_schedule_materialized": bridge_review.get("dcr_schedule_materialized"),
            "dcr_schedule": bridge_review.get("dcr_schedule"),
            "runtime_upload_helper_ready": bridge_review.get("runtime_upload_helper_ready"),
            "runtime_upload_header": bridge_review.get("runtime_upload_header"),
            "observable_export_helper_ready": bridge_review.get("observable_export_helper_ready"),
            "observable_export_header": bridge_review.get("observable_export_header"),
            "runtime_sequence_helper_ready": bridge_review.get("runtime_sequence_helper_ready"),
            "runtime_sequence_header": bridge_review.get("runtime_sequence_header"),
            "runtime_sequence": bridge_review.get("runtime_sequence"),
            "runtime_invocation_plan_ready": bridge_review.get("runtime_invocation_plan_ready"),
            "runtime_invocation_plan": bridge_review.get("runtime_invocation_plan"),
            "lowered_tb_invocation_smoke_ready": bridge_review.get("lowered_tb_invocation_smoke_ready"),
            "lowered_tb_invocation_smoke": bridge_review.get("lowered_tb_invocation_smoke"),
            "materialized_runtime_invocation_smoke_ready": bridge_review.get(
                "materialized_runtime_invocation_smoke_ready"
            ),
            "materialized_runtime_invocation_smoke": bridge_review.get("materialized_runtime_invocation_smoke"),
            "generated_lowered_tb_invocation_smoke_passed": bridge_review.get(
                "generated_lowered_tb_invocation_smoke_passed"
            ),
            "generated_lowered_tb_invocation_smoke": bridge_review.get("generated_lowered_tb_invocation_smoke"),
            "lowered_tb_memory_helper_integration_smoke_passed": bridge_review.get(
                "lowered_tb_memory_helper_integration_smoke_passed"
            ),
            "lowered_tb_memory_helper_integration_smoke": bridge_review.get(
                "lowered_tb_memory_helper_integration_smoke"
            ),
            "binary_input_summary": bridge_review.get("binary_input_summary"),
            "gpu_memory_model_plan": bridge_review.get("gpu_memory_model_plan"),
            "memory_model_reference": bridge_review.get("memory_model_reference"),
        }
        if bridge_review is not None
        else None,
        "existing_vortex_reports": existing_reports,
        "missing_prerequisites": missing,
        "recommended_sequence": recommended_sequence,
        "non_claims": [
            "not_vortex_gpu_measurement",
            "not_vortex_speedup_claim",
            "not_cpu_vs_hybrid_timing_evidence",
            "descriptor_and_readiness_only",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", help="Output JSON path when --write-report is used")
    args = parser.parse_args(argv)

    try:
        summary = build_readiness(Path(args.repo_root))
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
