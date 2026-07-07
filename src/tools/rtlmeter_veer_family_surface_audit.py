#!/usr/bin/env python3
"""Audit VeeR EH1/EH2/EL2 hybrid-surface portability for RTLMeter."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


SURFACE = "rtlmeter_veer_family_surface_audit"
DEFAULT_REPORT = "reports/rtlmeter_veer_family_surface_audit.json"
EL2_AUTHORITY = Path("config/rtlmeter_sidecar_authorities/rtlmeter_veer_el2_default_hello.json")
EL2_STATE_LAYOUT_REPORT = Path("reports/rtlmeter_veer_el2_state_layout_inspection.json")
EL2_STATE_IMAGE_REPORT = Path("reports/rtlmeter_veer_el2_state_image_materializer.json")
EL2_BRIDGE_REPORT = Path("reports/rtlmeter_veer_el2_sidecar_bridge.json")
EL2_TIMING_REPORT = Path("reports/rtlmeter_veer_el2_timing_pair_cycle_fused_nstates16.json")
EL2_PROGRAM_SHA256 = "d0219135d529505962c1c5ed44360e91466ae046cb8ec40b5980761861c63d76"
RTLMETER_UTILS_SOURCE = "third_party/rtlmeter/rtl/__rtlmeter_utils.sv"
RTLMETER_TOP_INCLUDE = "third_party/rtlmeter/rtl/__rtlmeter_top_include.vh"
EH_MAILBOX_OBSERVABLE_PATCH_DESCRIPTOR = Path(
    "overlays/rtlmeter/patches/rtlmeter_veer_eh_mailbox_observable_public_flat.json"
)
EH_MAILBOX_OBSERVABLE_PATCH = Path(
    "overlays/rtlmeter/patches/rtlmeter_veer_eh_mailbox_observable_public_flat.patch"
)
EH_SIDECAR_EXECUTABLE = Path("src/tools/veer_eh_sidecar_executable.py")

TARGETS = [
    {
        "design": "VeeR-EH1",
        "case": "VeeR-EH1:default:hello",
        "configuration": "default",
        "test": "hello",
        "expected_wrapper_instance": "rvtop",
        "expected_core_symbol_fragment": "__DOT__rvtop__DOT__veer",
        "expected_source_prefix": "",
        "el2_direct_reuse": False,
    },
    {
        "design": "VeeR-EH2",
        "case": "VeeR-EH2:default:hello",
        "configuration": "default",
        "test": "hello",
        "expected_wrapper_instance": "rvtop",
        "expected_core_symbol_fragment": "__DOT__rvtop__DOT__veer",
        "expected_source_prefix": "eh2_",
        "el2_direct_reuse": False,
    },
    {
        "design": "VeeR-EL2",
        "case": "VeeR-EL2:default:hello",
        "configuration": "default",
        "test": "hello",
        "expected_wrapper_instance": "rvtop_wrapper",
        "expected_core_symbol_fragment": "__DOT__rvtop_wrapper__DOT__rvtop__DOT__veer",
        "expected_source_prefix": "el2_",
        "el2_direct_reuse": True,
    },
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_yaml(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, Mapping) else None


def _load_json(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, Mapping) else None


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _descriptor_paths(
    descriptor: Mapping[str, Any] | None,
    *,
    configuration: str,
    test: str,
) -> dict[str, Any]:
    if descriptor is None:
        return {
            "configuration_exists": False,
            "test_exists": False,
            "configuration_test_exists": False,
            "verilog_sources": [],
            "base_includes": [],
            "configuration_includes": [],
            "program_files": [],
            "top_module": None,
            "main_clock": None,
        }
    compile_section = _mapping(descriptor.get("compile"))
    configs = _mapping(descriptor.get("configurations"))
    config = _mapping(configs.get(configuration))
    config_compile = _mapping(config.get("compile"))
    execute_tests = _mapping(_mapping(descriptor.get("execute")).get("tests"))
    config_tests = _mapping(_mapping(config.get("execute")).get("tests"))
    test_entry = _mapping(execute_tests.get(test))
    return {
        "configuration_exists": configuration in configs,
        "test_exists": test in execute_tests,
        "configuration_test_exists": test in config_tests,
        "verilog_sources": _as_list(compile_section.get("verilogSourceFiles")),
        "base_includes": _as_list(compile_section.get("verilogIncludeFiles")),
        "configuration_includes": _as_list(config_compile.get("verilogIncludeFiles")),
        "program_files": _as_list(test_entry.get("files")),
        "top_module": compile_section.get("topModule"),
        "main_clock": compile_section.get("mainClock"),
    }


def _authority_target_name(design: str, configuration: str, test: str) -> str:
    return f"rtlmeter_{design.lower().replace('-', '_')}_{configuration}_{test}"


def _authority_path_for(design: str, configuration: str, test: str) -> Path:
    return Path("config/rtlmeter_sidecar_authorities") / f"{_authority_target_name(design, configuration, test)}.json"


def _state_layout_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_state_layout_inspection.json")


def _root_offset_review_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_root_offset_review.json")


def _cpu_reference_obj_dir_for(design: str, configuration: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"artifacts/rtlmeter_{stem}_cpu_reference/{design}/{configuration}/compile-0/obj_dir")


def _mailbox_public_flat_cpu_reference_obj_dir_for(design: str, configuration: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(
        f"artifacts/rtlmeter_{stem}_cpu_reference_mailbox_public_flat/"
        f"{design}/{configuration}/compile-0/obj_dir"
    )


def _root_obj_dir_candidates_for(design: str, configuration: str) -> list[tuple[str, Path]]:
    candidates = [("default", _cpu_reference_obj_dir_for(design, configuration))]
    if design in {"VeeR-EH1", "VeeR-EH2"}:
        candidates.insert(
            0,
            (
                "mailbox_public_flat",
                _mailbox_public_flat_cpu_reference_obj_dir_for(design, configuration),
            ),
        )
    return candidates


def _state_image_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_state_image_materializer.json")


def _state_image_artifact_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"artifacts/rtlmeter_{stem}_state_image/{stem}_extracted_state_image.json")


def _sidecar_bridge_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_sidecar_bridge.json")


def _sidecar_bridge_bounded_execution_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_sidecar_bridge_bounded8.json")


def _ptxas_probe_report_path_for(design: str) -> Path | None:
    if design != "VeeR-EH1":
        return None
    return Path("reports/rtlmeter_veer_eh1_ptxas_o0_probe.json")


def _entry_pruned_module_probe_report_path_for(design: str) -> Path | None:
    if design == "VeeR-EH1":
        return Path("reports/rtlmeter_veer_eh1_entry_pruned_module_probe.json")
    if design == "VeeR-EH2":
        return Path("reports/rtlmeter_veer_eh2_entry_pruned_module_probe.json")
    return None


def _entry_pruned_eval_only_raw_probe_for(repo_root: Path, design: str) -> dict[str, Any] | None:
    if design != "VeeR-EH2":
        return None
    exit_path = repo_root / "reports/rtlmeter_veer_eh2_entry_pruned_eval_only_probe.exit"
    stderr_path = repo_root / "reports/rtlmeter_veer_eh2_entry_pruned_eval_only_probe.stderr"
    if not exit_path.is_file() or not stderr_path.is_file():
        return None
    exit_text = exit_path.read_text(encoding="utf-8", errors="replace").strip()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    status = "unknown"
    if (
        exit_text != "0"
        and "run_vl_hybrid: launch step=0 kernel_index=0 kernel=vl_eval_batch_gpu" in stderr_text
        and "run_vl_hybrid: stage=before_first_step_sync" in stderr_text
        and "CUDA error 700" in stderr_text
    ):
        status = "illegal_memory_access_at_first_eval_launch"
    return {
        "status": status,
        "exit_code": exit_text,
        "stderr_report": "reports/rtlmeter_veer_eh2_entry_pruned_eval_only_probe.stderr",
        "exit_report": "reports/rtlmeter_veer_eh2_entry_pruned_eval_only_probe.exit",
        "last_stage": "before_first_step_sync" if "run_vl_hybrid: stage=before_first_step_sync" in stderr_text else None,
        "sync_each_step": True,
    }


def _eh2_eval_only_variant_raw_probe(repo_root: Path, name: str) -> dict[str, Any] | None:
    exit_path = repo_root / f"reports/rtlmeter_veer_eh2_entry_pruned_eval_only_{name}_probe.exit"
    stderr_path = repo_root / f"reports/rtlmeter_veer_eh2_entry_pruned_eval_only_{name}_probe.stderr"
    if not exit_path.is_file() or not stderr_path.is_file():
        return None
    exit_text = exit_path.read_text(encoding="utf-8", errors="replace").strip()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    cuda700 = "CUDA error 700" in stderr_text
    first_sync = "run_vl_hybrid: stage=before_first_step_sync" in stderr_text
    status = "unknown"
    if exit_text != "0" and cuda700 and first_sync:
        status = "illegal_memory_access_at_first_eval_launch"
    elif exit_text != "0" and "stack-limit setup failed" in stderr_text:
        status = "stack_limit_setup_failed"
    return {
        "status": status,
        "exit_code": exit_text,
        "stderr_report": f"reports/rtlmeter_veer_eh2_entry_pruned_eval_only_{name}_probe.stderr",
        "exit_report": f"reports/rtlmeter_veer_eh2_entry_pruned_eval_only_{name}_probe.exit",
        "last_stage": "before_first_step_sync" if first_sync else None,
    }


def _eh2_eval_only_variant_raw_probes(repo_root: Path, design: str) -> dict[str, Any]:
    if design != "VeeR-EH2":
        return {}
    return {
        name: probe
        for name in ("padded2m", "stack64k", "zero_init")
        if (probe := _eh2_eval_only_variant_raw_probe(repo_root, name)) is not None
    }


def _eh2_host_cleanup_eval_only_probe(repo_root: Path, design: str) -> dict[str, Any] | None:
    if design != "VeeR-EH2":
        return None
    exit_path = repo_root / "reports/rtlmeter_veer_eh2_host_cleanup_eval_only_direct_probe.exit"
    stderr_path = repo_root / "reports/rtlmeter_veer_eh2_host_cleanup_eval_only_direct_probe.stderr"
    if not exit_path.is_file() or not stderr_path.is_file():
        return None
    exit_text = exit_path.read_text(encoding="utf-8", errors="replace").strip()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    module_probe = _load_json(repo_root / "reports/rtlmeter_veer_eh2_host_cleanup_module_load_diagnostic.json")
    status = "unknown"
    first_sync = "run_vl_hybrid: stage=before_first_step_sync" in stderr_text
    if exit_text != "0" and first_sync and "CUDA error 700" in stderr_text:
        status = "host_cleanup_eval_only_still_illegal_memory_access"
    return {
        "status": status,
        "exit_code": exit_text,
        "stderr_report": "reports/rtlmeter_veer_eh2_host_cleanup_eval_only_direct_probe.stderr",
        "exit_report": "reports/rtlmeter_veer_eh2_host_cleanup_eval_only_direct_probe.exit",
        "last_stage": "before_first_step_sync" if first_sync else None,
        "ptxas_status": _mapping(module_probe).get("ptxas_status"),
        "ptxas_cubin_exists": _mapping(module_probe).get("ptxas_cubin_exists"),
        "cubin": _mapping(module_probe).get("ptxas_cubin_out"),
    }


def _eh2_direct_probe(
    repo_root: Path,
    design: str,
    *,
    name: str,
    success_status: str,
    cuda700_status: str,
) -> dict[str, Any] | None:
    if design != "VeeR-EH2":
        return None
    base = f"reports/rtlmeter_veer_eh2_{name}"
    exit_path = repo_root / f"{base}.exit"
    stderr_path = repo_root / f"{base}.stderr"
    stdout_path = repo_root / f"{base}.stdout"
    if not exit_path.is_file() or not stderr_path.is_file():
        return None
    exit_text = exit_path.read_text(encoding="utf-8", errors="replace").strip()
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    first_sync = "run_vl_hybrid: stage=before_first_step_sync" in stderr_text
    after_first_sync = "run_vl_hybrid: stage=after_first_step_sync" in stderr_text
    status = "unknown"
    if exit_text == "0" and after_first_sync and "ok: steps=1" in stdout_text:
        status = success_status
    elif exit_text != "0" and first_sync and "CUDA error 700" in stderr_text:
        status = cuda700_status
    return {
        "status": status,
        "exit_code": exit_text,
        "stderr_report": f"{base}.stderr",
        "stdout_report": f"{base}.stdout" if stdout_path.is_file() else None,
        "exit_report": f"{base}.exit",
        "last_stage": "after_first_step_sync" if after_first_sync else "before_first_step_sync" if first_sync else None,
    }


PTX_RUNTIME_RESIDUE_PATTERNS = {
    "vl_delay_scheduler": "VlDelayScheduler",
    "rb_tree": "_Rb_tree",
    "coroutine_handle": "VlCoroutineHandle",
    "std_string": "basic_string",
    "new_allocator": "new_allocator",
    "vl_writef": "VL_WRITEF",
    "vl_finish": "VL_FINISH",
    "run_flush_callbacks": "runFlushCallbacks",
    "std_ref_root": "_ZSt3refI14Vsim___024root",
    "std_ref_eh2_modules": "_ZSt3refI",
}


def _entry_pruned_ptx_static_residue_for(repo_root: Path, design: str) -> dict[str, Any] | None:
    if design != "VeeR-EH2":
        return None
    slice_report_path = repo_root / "reports/rtlmeter_veer_eh2_ptx_entry_slice.json"
    slice_report = _load_json(slice_report_path)
    slice_ptx = _mapping(slice_report).get("slice_ptx")
    if not isinstance(slice_ptx, str) or not slice_ptx:
        return None
    ptx_path = repo_root / slice_ptx
    if not ptx_path.is_file():
        return {
            "status": "ptx_slice_missing",
            "slice_report": "reports/rtlmeter_veer_eh2_ptx_entry_slice.json",
            "slice_ptx": slice_ptx,
            "runtime_residue_detected": False,
        }
    text = ptx_path.read_text(encoding="utf-8", errors="replace")
    counts = {
        name: text.count(pattern)
        for name, pattern in PTX_RUNTIME_RESIDUE_PATTERNS.items()
    }
    total = sum(counts.values())
    function_defs = re.findall(r"(?m)^(?:\.visible\s+|\.weak\s+)?\.func\s+[^\n]*", text)
    suspicious_function_defs = [
        line
        for line in function_defs
        if any(pattern in line for pattern in PTX_RUNTIME_RESIDUE_PATTERNS.values())
    ]
    return {
        "status": (
            "cpp_verilator_runtime_residue_detected"
            if total > 0
            else "no_cpp_verilator_runtime_residue_detected"
        ),
        "slice_report": "reports/rtlmeter_veer_eh2_ptx_entry_slice.json",
        "slice_ptx": slice_ptx,
        "ptx_bytes": ptx_path.stat().st_size,
        "runtime_residue_detected": total > 0,
        "residue_pattern_counts": counts,
        "residue_pattern_total": total,
        "suspicious_function_def_count": len(suspicious_function_defs),
        "suspicious_function_def_samples": suspicious_function_defs[:10],
        "next_required_boundary": (
            "stub_or_remove_verilator_cpp_runtime_residue_from_eh2_entry_pruned_eval_kernel"
            if total > 0
            else "continue_eh2_first_eval_fault_debug_without_static_runtime_residue_evidence"
        ),
    }


def _sidecar_executable_review_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_sidecar_executable_review.json")


def _sidecar_executable_preflight_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_sidecar_executable_preflight.json")


def _cpu_reference_report_path_for(design: str) -> Path:
    stem = design.lower().replace("-", "_")
    return Path(f"reports/rtlmeter_{stem}_cpu_reference_summary.json")


def _prefixed_paths(design: str, items: list[str]) -> list[str]:
    return [f"third_party/rtlmeter/designs/{design}/{item}" for item in items]


def _filelist_entries(source_files: list[str], include_files: list[str]) -> list[str]:
    entries: list[str] = []
    for path in source_files:
        if path == RTLMETER_UTILS_SOURCE:
            entries.append("rtl/__rtlmeter_utils.sv")
        else:
            entries.append(f"verilogSourceFiles/{Path(path).name}")
    for path in include_files:
        if path == RTLMETER_TOP_INCLUDE:
            entries.append("rtl/__rtlmeter_top_include.vh")
    return entries


def build_authority_payload(repo_root: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    design = str(target["design"])
    configuration = str(target["configuration"])
    test = str(target["test"])
    case = str(target["case"])
    design_root = repo_root / "third_party" / "rtlmeter" / "designs" / design
    descriptor_path = design_root / "descriptor.yaml"
    descriptor_info = _descriptor_paths(
        _load_yaml(descriptor_path),
        configuration=configuration,
        test=test,
    )
    source_files = _prefixed_paths(design, descriptor_info["verilog_sources"]) + [RTLMETER_UTILS_SOURCE]
    include_files = (
        _prefixed_paths(design, descriptor_info["base_includes"])
        + _prefixed_paths(design, descriptor_info["configuration_includes"])
        + [RTLMETER_TOP_INCLUDE]
    )
    target_name = _authority_target_name(design, configuration, test)
    source_closure = {
        "status": "complete",
        "authority": "reviewed_hybrid_execution_source_closure",
        "authority_scope": "rtlmeter_stdout_cycles_sidecar_runner",
        "target": target_name,
        "mode": "rtlmeter_first_seed",
        "rtlmeter_case": case,
        "source_gate_or_manifest_ref": "reports/rtlmeter_veer_family_surface_audit.json",
        "source_files": source_files,
        "include_files": include_files,
        "filelist_entries": _filelist_entries(source_files, include_files),
        "observables": ["normalized_stdout", "rtlmeter_cycles"],
        "runner_strategy": "rtlmeter_stdout_cycles_direct_wrapper",
        "host_probe_contract_status": "reviewed_for_rtlmeter_sidecar",
        "cpu_as_gpu_fallback_allowed": False,
        "execution_blockers": [
            "state_layout_report",
            "state_image_materializer",
            "sidecar_bridge_report",
            "cpu_vs_hybrid_timing_report",
        ],
        "review_evidence": {
            "reviewed": True,
            "review_ref": "reports/rtlmeter_veer_family_surface_audit.json",
        },
    }
    program_paths = [design_root / item for item in descriptor_info["program_files"]]
    return {
        "schema_version": 1,
        "schema_role": "rtlmeter_sidecar_authority",
        "status": f"blocked_{design.lower().replace('-', '_')}_state_layout_and_native_gpu_execution",
        "runtime_launchable": False,
        "runtime_launch_template": None,
        "target": target_name,
        "mode": "rtlmeter_first_seed",
        "rtlmeter_case": case,
        "coverage_output_target": "rtlmeter_stdout_and_cycles_equivalence",
        "coverage_manifest": {
            "outputs": ["normalized_stdout", "rtlmeter_cycles"],
            "status": "policy_defined_not_observed",
            "raw_state_equality_required": False,
        },
        "compile_source_closure": {
            "status": "complete",
            "provenance": "rtlmeter_descriptor_capture",
            "configuration": configuration,
            "program": test,
            "program_sha256": _sha256(program_paths[0]) if program_paths else None,
            "top_module": descriptor_info["top_module"],
            "main_clock": descriptor_info["main_clock"],
            "source_files": source_files,
            "include_files": include_files,
            "filelist_entries": _filelist_entries(source_files, include_files),
        },
        "source_closure": source_closure,
        "state_and_report_path_rules": {
            "root": f"artifacts/rtlmeter_{design.lower().replace('-', '_')}_{configuration}_{test}_cpu_gpu_compare",
        },
        "compare_labels": {
            "cpu": "rtlmeter_cpu",
            "gpu": "rtlmeter_sidecar_candidate",
        },
        "next_required_boundary": (
            "design-specific state-layout report, state-image materializer, sidecar bridge, and timing"
        ),
        "non_claims": [
            "not_hybrid_execution",
            "not_gpu_speedup_claim",
            "not_state_image_materialization",
            "not_sidecar_bridge_or_timing",
        ],
    }


def build_state_layout_preflight(repo_root: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    design = str(target["design"])
    configuration = str(target["configuration"])
    test = str(target["test"])
    case = str(target["case"])
    design_root = repo_root / "third_party" / "rtlmeter" / "designs" / design
    descriptor_path = design_root / "descriptor.yaml"
    descriptor_info = _descriptor_paths(
        _load_yaml(descriptor_path),
        configuration=configuration,
        test=test,
    )
    tb_top = design_root / "src" / "tb_top.sv"
    tb_text = _read_text(tb_top)
    program_paths = [design_root / item for item in descriptor_info["program_files"]]
    authority_path = _authority_path_for(design, configuration, test)
    authority = _load_json(repo_root / authority_path)
    source_closure = _mapping(_mapping(authority).get("source_closure"))
    expected_wrapper = str(target["expected_wrapper_instance"])
    wrapper_instance_present = expected_wrapper in tb_text
    expected_core_fragment = str(target["expected_core_symbol_fragment"])
    pc_candidates = [
        f"tb_top__DOT__{expected_wrapper}__DOT__veer__DOT__dec_i0_pc_d"
        if expected_wrapper == "rvtop"
        else f"tb_top__DOT__{expected_wrapper}__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d",
        "i0_pc_r_ff",
    ]
    root_header_probe = _root_header_marker_probe(repo_root, design, configuration, pc_candidates)
    detected_layout = {
        "descriptor_source_closure_present": descriptor_path.is_file(),
        "authority_registry_present": authority is not None,
        "authority_source_closure_reviewed": source_closure.get("authority") == "reviewed_hybrid_execution_source_closure",
        "top_module_matches": descriptor_info["top_module"] == "tb_top",
        "main_clock_matches": descriptor_info["main_clock"] == "tb_top.core_clk",
        "program_preload_found": '$readmemh("program.hex"' in tb_text,
        "mailbox_write_found": "mailbox_write" in tb_text,
        "test_passed_mailbox_found": "8'h1" in tb_text,
        "wrapper_instance_present": wrapper_instance_present,
        "expected_core_symbol_fragment": expected_core_fragment,
        "pc_field_candidates": pc_candidates,
        "gpr_schema_candidate": {
            "x0_implicit_zero": True,
            "width_bits": 32,
            "requires_root_layout_probe": True,
        },
        "memory_preload_schema_candidate": {
            "program_hex": _display_path(program_paths[0], repo_root=repo_root) if program_paths else None,
            "program_sha256": _sha256(program_paths[0]) if program_paths else None,
            "program_staging_memories": ["lmem.mem", "imem.mem"],
        },
        "root_header_probe": root_header_probe,
    }
    missing = []
    for key, value in detected_layout.items():
        if isinstance(value, bool) and not value:
            missing.append(key)
    if not program_paths:
        missing.append("program_hex")
    if root_header_probe["root_layout_probe_performed"] is not True:
        missing.append("root_layout_probe")
    missing.append("reviewed_root_field_offsets")
    return {
        "schema_version": 1,
        "surface": "rtlmeter_veer_family_state_layout_preflight",
        "status": f"blocked_{design.lower().replace('-', '_')}_root_layout_offsets_unreviewed",
        "target": _authority_target_name(design, configuration, test),
        "rtlmeter_case": case,
        "mode": "inspect_veer_family_state_layout_preflight",
        "state_layout_inspection_performed": True,
        "state_layout_ready": False,
        "state_layout_target": _authority_target_name(design, configuration, test),
        "descriptor": _display_path(descriptor_path, repo_root=repo_root),
        "testbench_source": _display_path(tb_top, repo_root=repo_root),
        "authority_registry": authority_path.as_posix(),
        "rtlmeter_program_hex": _display_path(program_paths[0], repo_root=repo_root) if program_paths else None,
        "rtlmeter_program_sha256": _sha256(program_paths[0]) if program_paths else None,
        "detected_layout": detected_layout,
        "missing_build_context": list(dict.fromkeys(missing)),
        "next_required_boundary": "probe generated root layout and review EH-specific root field offsets",
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "fail_closed": True,
        "non_claims": [
            "state-layout preflight is descriptor/testbench metadata, not GPU execution",
            "root field offsets are not reviewed yet",
            "no state image materialization, sidecar bridge, timing, or speedup is claimed",
        ],
    }


def _parse_program_hex_bytes(path: Path) -> list[int]:
    if not path.is_file():
        return []
    values: list[int] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        for token in line.replace(",", " ").split():
            if token.startswith("@"):
                continue
            try:
                values.append(int(token, 16) & 0xFF)
            except ValueError:
                continue
    return values


def _byte_entries(values: list[int], *, base_address: int = 0x80000000) -> list[dict[str, str]]:
    return [
        {
            "addr": f"0x{base_address + index:08x}",
            "byte_hex": f"0x{value:02x}",
        }
        for index, value in enumerate(values)
    ]


def build_state_image_payload(repo_root: Path, target: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    design = str(target["design"])
    configuration = str(target["configuration"])
    test = str(target["test"])
    case = str(target["case"])
    design_root = repo_root / "third_party" / "rtlmeter" / "designs" / design
    descriptor_path = design_root / "descriptor.yaml"
    descriptor_info = _descriptor_paths(
        _load_yaml(descriptor_path),
        configuration=configuration,
        test=test,
    )
    program_paths = [design_root / item for item in descriptor_info["program_files"]]
    program_path = program_paths[0] if program_paths else None
    program_bytes = _parse_program_hex_bytes(program_path) if program_path else []
    program_entries = _byte_entries(program_bytes)
    program_sha = _sha256(program_path) if program_path else None
    target_name = _authority_target_name(design, configuration, test)
    artifact_rel = _state_image_artifact_path_for(design)
    program_display = _display_path(program_path, repo_root=repo_root) if program_path else None
    state_image = {
        "schema_version": 1,
        "schema_role": f"{design.lower().replace('-', '_')}_extracted_preload_state_image",
        "target": target_name,
        "rtlmeter_case": case,
        "program_preload": program_display,
        "program_sha256": program_sha,
        "sections": {
            "control_scalars": {
                "tb_top__DOT__core_clk": 0,
                "tb_top__DOT__porst_l": 0,
                "tb_top__DOT__rst_l": 0,
            },
            "dccm_banks": {
                "preload_active": False,
                "start_address_hex": "0x00000000",
                "end_address_hex": "0x00000000",
                "nonzero_entries_by_bank": {"0": [], "1": [], "2": [], "3": []},
            },
            "iccm_banks": {
                "preload_active": False,
                "start_address_hex": "0x00000000",
                "end_address_hex": "0x00000000",
                "nonzero_entries_by_bank": {"0": [], "1": [], "2": [], "3": []},
            },
            "program_staging_lmem": program_entries,
            "program_staging_imem": program_entries,
        },
        "non_claims": [
            "state image materialization is not GPU execution",
            "state image materialization is not RTLMeter stdout/cycles comparison",
            "state image materialization is not speedup evidence",
        ],
    }
    missing_context = ["sidecar_bridge_report", "timing_report"]
    layout_report = _load_json(repo_root / _state_layout_report_path_for(design))
    if layout_report is None:
        missing_context.insert(0, "state_layout_report")
    if not program_bytes:
        missing_context.insert(0, "program_hex_bytes")
    report = {
        "schema_version": 1,
        "surface": "rtlmeter_veer_family_state_image_materializer",
        "status": f"blocked_{design.lower().replace('-', '_')}_sidecar_bridge_missing",
        "target": target_name,
        "rtlmeter_case": case,
        "mode": "materialize_veer_family_preload_state_image",
        "descriptor": _display_path(descriptor_path, repo_root=repo_root),
        "state_layout_report": _state_layout_report_path_for(design).as_posix(),
        "state_image_artifact": artifact_rel.as_posix(),
        "state_image_materialized": True,
        "state_layout_ready": False,
        "program_preload": program_display,
        "program_sha256": program_sha,
        "program_byte_count": len(program_bytes),
        "program_staging_memories": ["lmem.mem", "imem.mem"],
        "missing_build_context": list(dict.fromkeys(missing_context)),
        "next_required_boundary": "create EH-specific sidecar execution bridge and CPU-vs-hybrid timing report",
        "fail_closed": True,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "state image materialization is not GPU execution",
            "state image materialization does not prove root field offsets are reviewed",
            "no sidecar bridge, timing, or speedup is claimed",
        ],
    }
    return report, state_image


def _marker_has_entry(markers: Mapping[str, object], marker: str) -> bool:
    entries = markers.get(marker)
    return isinstance(entries, list) and bool(entries)


def _root_offset_group_complete(group: str, markers: Mapping[str, object]) -> bool:
    if group == "control_scalars":
        return all(
            _marker_has_entry(markers, marker)
            for marker in ["tb_top__DOT__core_clk", "tb_top__DOT__rst_l", "tb_top__DOT__porst_l"]
        )
    if group == "pc_candidates":
        return any(_marker_has_entry(markers, marker) for marker in markers)
    if group == "cycle_counters":
        direct_counters = _marker_has_entry(markers, "mcyclel") and _marker_has_entry(markers, "minstretl")
        exported_arrays = _marker_has_entry(markers, "tb_top__DOT__mcycle") and _marker_has_entry(
            markers,
            "tb_top__DOT__minstret",
        )
        return direct_counters or exported_arrays
    if group == "mailbox_observables":
        return _marker_has_entry(markers, "mailbox_write") and _marker_has_entry(markers, "WriteData")
    if group == "gpr_observables":
        return any(_marker_has_entry(markers, marker) for marker in markers)
    return False


def _candidate_entries(candidates: Mapping[str, object], group: str, marker: str) -> list[Mapping[str, object]]:
    entries = _mapping(_mapping(candidates.get(group)).get(marker))
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, Mapping)]
    return []


def _first_candidate(candidates: Mapping[str, object], group: str, markers: list[str]) -> Mapping[str, object] | None:
    for marker in markers:
        entries = _mapping(candidates.get(group)).get(marker)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, Mapping):
                    return entry
    return None


def _first_sized_candidate(
    candidates: Mapping[str, object],
    group: str,
    markers: list[str],
    *,
    min_size: int,
) -> Mapping[str, object] | None:
    fallback = _first_candidate(candidates, group, markers)
    for marker in markers:
        entries = _mapping(candidates.get(group)).get(marker)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, Mapping) and int(entry.get("size", 0) or 0) >= min_size:
                    return entry
    return fallback


def _reviewed_root_offset_abi(candidates: Mapping[str, object]) -> tuple[dict[str, Any], list[str]]:
    selected: dict[str, Any] = {}
    missing: list[str] = []
    required = {
        "core_clk": ("control_scalars", ["tb_top__DOT__core_clk"]),
        "rst_l": ("control_scalars", ["tb_top__DOT__rst_l"]),
        "porst_l": ("control_scalars", ["tb_top__DOT__porst_l"]),
        "pc": (
            "pc_candidates",
            [
                "tb_top__DOT__rvtop__DOT__veer__DOT__dec_i0_pc_d",
                "dec_i0_pc_d",
                "dec_tlu_i0_pc_e4",
                "ifu_i0_pcdata",
            ],
        ),
        "mailbox_write": ("mailbox_observables", ["mailbox_write"]),
        "mailbox_data": ("mailbox_observables", ["WriteData"]),
    }
    for field, (group, markers) in required.items():
        entry = _first_candidate(candidates, group, markers)
        if entry is None:
            missing.append(field)
            continue
        selected[field] = {
            "name": entry.get("name"),
            "offset": entry.get("offset"),
            "size": entry.get("size"),
            "decl_type": entry.get("decl_type"),
            "source_group": group,
        }
    for field, markers in {
        "mcycle": ["mcyclel", "tb_top__DOT__mcycle"],
        "minstret": ["minstretl", "tb_top__DOT__minstret"],
        "gpr_debug": ["__DOT__gpr", "gpr_banks", "arf"],
    }.items():
        group = "gpr_observables" if field == "gpr_debug" else "cycle_counters"
        entry = _first_sized_candidate(candidates, group, markers, min_size=4)
        if entry is None:
            missing.append(field)
            continue
        selected[field] = {
            "name": entry.get("name"),
            "offset": entry.get("offset"),
            "size": entry.get("size"),
            "decl_type": entry.get("decl_type"),
            "source_group": group,
        }
    return selected, missing


def build_root_offset_review_payload(repo_root: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    design = str(target["design"])
    configuration = str(target["configuration"])
    test = str(target["test"])
    case = str(target["case"])
    stem = design.lower().replace("-", "_")
    target_name = _authority_target_name(design, configuration, test)
    layout_report_path = _state_layout_report_path_for(design)
    layout_report = _load_json(repo_root / layout_report_path)
    probe = _mapping(_mapping(_mapping(layout_report).get("detected_layout")).get("root_header_probe"))
    marker_hits = _mapping(probe.get("root_offset_marker_hits"))
    required_groups = [
        "control_scalars",
        "pc_candidates",
        "cycle_counters",
        "mailbox_observables",
        "gpr_observables",
    ]
    observed_groups = [
        group for group in required_groups if _mapping(marker_hits.get(group)).get("observed") is True
    ]
    complete_groups = [
        group
        for group in required_groups
        if _root_offset_group_complete(group, _mapping(_mapping(marker_hits.get(group)).get("markers")))
    ]
    missing_groups = [group for group in required_groups if group not in complete_groups]
    missing_context: list[str] = []
    if layout_report is None:
        missing_context.append("state_layout_report")
    if probe.get("root_offset_probe_performed") is not True:
        missing_context.append("root_offset_probe")
    missing_context.extend(f"{group}_root_offset_mapping" for group in missing_groups)
    mailbox_patch_available = (
        (repo_root / EH_MAILBOX_OBSERVABLE_PATCH_DESCRIPTOR).is_file()
        and (repo_root / EH_MAILBOX_OBSERVABLE_PATCH).is_file()
    )
    if "mailbox_observables" in missing_groups:
        if mailbox_patch_available:
            missing_context.append("apply_mailbox_observable_patch_and_rebuild_root_layout")
        else:
            missing_context.append("mailbox_observable_export_or_tb_instrumentation")
    missing_context.append("complete_root_field_offset_abi_review")
    resolution_hints = {
        "control_scalars": "review generated root clock/reset scalar offsets",
        "pc_candidates": "review PC root offset candidate used for progress/debug comparison",
        "cycle_counters": "review RTLMeter architectural cycle/minstret root offsets or exported arrays",
        "mailbox_observables": "export or preserve tb_top mailbox_write/WriteData root observables",
        "gpr_observables": "review GPR root offset candidates needed for state image comparison",
    }
    offset_candidates = {
        group: _mapping(marker_hits.get(group)).get("markers")
        for group in required_groups
        if _mapping(marker_hits.get(group)).get("observed") is True
    }
    reviewed_abi, missing_abi_fields = _reviewed_root_offset_abi(offset_candidates)
    if not missing_groups and missing_abi_fields:
        missing_context.extend(f"{field}_root_offset_abi_field" for field in missing_abi_fields)
    abi_review_ready = not missing_groups and not missing_abi_fields
    if abi_review_ready:
        missing_context = [item for item in missing_context if item != "complete_root_field_offset_abi_review"]
    status = (
        f"reviewed_{stem}_root_observable_offset_abi"
        if abi_review_ready
        else f"blocked_{stem}_root_observable_offset_review_incomplete"
    )
    return {
        "schema_version": 1,
        "surface": "rtlmeter_veer_family_root_offset_review",
        "mode": "review_veer_family_root_offset_candidates",
        "status": status,
        "target": target_name,
        "rtlmeter_case": case,
        "state_layout_report": layout_report_path.as_posix(),
        "mailbox_observable_patch_descriptor": EH_MAILBOX_OBSERVABLE_PATCH_DESCRIPTOR.as_posix(),
        "mailbox_observable_patch": EH_MAILBOX_OBSERVABLE_PATCH.as_posix(),
        "mailbox_observable_patch_available": mailbox_patch_available,
        "root_offset_review_performed": True,
        "root_offset_probe_performed": probe.get("root_offset_probe_performed") is True,
        "root_offset_probe_error": probe.get("root_offset_probe_error"),
        "root_header_observed": probe.get("root_header_observed") is True,
        "root_obj_dir_variant": probe.get("root_obj_dir_variant"),
        "root_obj_dir": probe.get("root_obj_dir"),
        "root_obj_dir_candidates": probe.get("root_obj_dir_candidates"),
        "root_layout_entry_count": probe.get("root_layout_entry_count"),
        "required_marker_groups": required_groups,
        "observed_marker_groups": observed_groups,
        "complete_marker_groups": complete_groups,
        "missing_marker_groups": missing_groups,
        "missing_marker_group_resolution_hints": {
            group: resolution_hints[group] for group in missing_groups if group in resolution_hints
        },
        "observed_marker_group_count": len(observed_groups),
        "mapped_marker_offset_group_count": probe.get("mapped_marker_offset_group_count"),
        "offset_candidates": offset_candidates,
        "root_observable_offset_candidates_complete": not missing_groups,
        "reviewed_root_offset_abi": reviewed_abi,
        "missing_reviewed_root_offset_abi_fields": missing_abi_fields,
        "root_field_offsets_reviewed_for_target": abi_review_ready,
        "root_field_offsets_reviewed": abi_review_ready,
        "root_observable_offset_review_ready": abi_review_ready,
        "state_layout_ready": abi_review_ready,
        "missing_build_context": list(dict.fromkeys(missing_context)),
        "next_required_boundary": (
            "implement EH-specific sidecar executable before bridge comparison"
            if abi_review_ready
            else "resolve missing root observable mappings and complete ABI offset review"
        ),
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "fail_closed": True,
        "non_claims": [
            "root offset ABI review is not sidecar bridge execution",
            "root offset ABI review does not claim timing or speedup",
            "no sidecar bridge comparison, timing, or speedup is claimed",
        ],
    }


def build_sidecar_executable_review_payload(repo_root: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    design = str(target["design"])
    configuration = str(target["configuration"])
    test = str(target["test"])
    case = str(target["case"])
    target_name = _authority_target_name(design, configuration, test)
    stem = design.lower().replace("-", "_")
    el2_executable = Path("src/tools/veer_el2_sidecar_executable.py")
    el2_text = _read_text(repo_root / el2_executable)
    eh_executable_text = _read_text(repo_root / EH_SIDECAR_EXECUTABLE)
    state_layout_report_path = _state_layout_report_path_for(design)
    state_layout_report = _load_json(repo_root / state_layout_report_path)
    root_offset_review_path = _root_offset_review_report_path_for(design)
    root_offset_review = _load_json(repo_root / root_offset_review_path)
    state_image_report_path = _state_image_report_path_for(design)
    state_image_report = _load_json(repo_root / state_image_report_path)
    cpu_reference_report_path = _cpu_reference_report_path_for(design)
    cpu_reference_report = _load_json(repo_root / cpu_reference_report_path)
    program_sha = _mapping(state_image_report).get("program_sha256")
    cpu_reference_ready = (
        isinstance(cpu_reference_report, Mapping)
        and cpu_reference_report.get("status") == "cpu_reference_passed"
        and cpu_reference_report.get("cpu_reference_ready_for_hybrid_compare") is True
    )
    el2_markers = {
        "imports_el2_target": "VEER_EL2_RTL_METER_TARGET" in el2_text,
        "uses_el2_sidecar_env": "VEER_EL2_SIDECAR_" in el2_text,
        "expects_rvtop_wrapper_hierarchy": "rvtop_wrapper" in el2_text,
        "checks_el2_program_sha256": "HELLO_PROGRAM_SHA256" in el2_text,
        "rejects_non_el2_state_image_target": (
            "state image target is not the reviewed VeeR-EL2 target" in el2_text
        ),
        "uses_el2_root_offset_review": "_veer_el2_root_state_offset_review" in el2_text,
    }
    reuse_blockers: list[str] = []
    if target_name != "rtlmeter_veer_el2_default_hello":
        reuse_blockers.append("target_name_differs_from_el2")
    if program_sha != EL2_PROGRAM_SHA256:
        reuse_blockers.append("program_sha_differs_from_el2")
    if str(target["expected_wrapper_instance"]) != "rvtop_wrapper":
        reuse_blockers.append("wrapper_hierarchy_differs_from_el2")
    if el2_markers["uses_el2_root_offset_review"]:
        reuse_blockers.append("el2_root_offset_review_function_is_fixed")
    if el2_markers["rejects_non_el2_state_image_target"]:
        reuse_blockers.append("el2_state_image_target_guard_rejects_eh")
    if el2_markers["uses_el2_sidecar_env"]:
        reuse_blockers.append("el2_sidecar_environment_contract_is_fixed")
    eh_executable_markers = {
        "exists": (repo_root / EH_SIDECAR_EXECUTABLE).is_file(),
        "supports_target": target_name in eh_executable_text,
        "checks_root_offset_abi": "REQUIRED_ABI_FIELDS" in eh_executable_text,
        "checks_state_image": "state_image_materialized" in eh_executable_text,
        "checks_cpu_reference": "cpu_reference_ready_for_hybrid_compare" in eh_executable_text,
        "keeps_gpu_execution_false": '"gpu_execution_claimed": False' in eh_executable_text,
    }
    root_offsets_ready = _mapping(root_offset_review).get("root_field_offsets_reviewed_for_target") is True
    design_specific_executable_ready = all(eh_executable_markers.values()) and root_offsets_ready
    missing_context: list[str] = []
    if state_layout_report is None:
        missing_context.append("state_layout_report")
    if (
        _mapping(state_layout_report).get("state_layout_ready") is not True
        and _mapping(root_offset_review).get("root_field_offsets_reviewed_for_target") is not True
    ):
        missing_context.append("reviewed_root_field_offsets")
    if state_image_report is None:
        missing_context.append("state_image_report")
    if not cpu_reference_ready:
        missing_context.append("cpu_reference_observables")
    if not design_specific_executable_ready:
        missing_context.append("design_specific_sidecar_executable_implementation")
    missing_context.extend(["executed_bridge_comparison", "timing_report"])
    status = (
        f"reviewed_{stem}_design_specific_sidecar_executable_boundary"
        if design_specific_executable_ready
        else f"blocked_{stem}_design_specific_sidecar_executable_missing"
    )
    return {
        "schema_version": 1,
        "surface": "rtlmeter_veer_family_sidecar_executable_review",
        "mode": "review_veer_family_sidecar_executable_reuse",
        "status": status,
        "target": target_name,
        "rtlmeter_case": case,
        "el2_sidecar_executable": el2_executable.as_posix(),
        "eh_sidecar_executable": EH_SIDECAR_EXECUTABLE.as_posix(),
        "el2_executable_present": (repo_root / el2_executable).is_file(),
        "el2_executable_reviewed": True,
        "el2_executable_markers": el2_markers,
        "el2_executable_reusable_for_target": False,
        "eh_sidecar_executable_markers": eh_executable_markers,
        "design_specific_sidecar_executable_present": (repo_root / EH_SIDECAR_EXECUTABLE).is_file(),
        "sidecar_executable_review_performed": True,
        "sidecar_executable_reviewed_for_target": design_specific_executable_ready,
        "expected_target": target_name,
        "expected_wrapper_instance": target["expected_wrapper_instance"],
        "expected_core_symbol_fragment": target["expected_core_symbol_fragment"],
        "state_layout_report": state_layout_report_path.as_posix(),
        "root_offset_review_report": root_offset_review_path.as_posix(),
        "root_field_offsets_reviewed_for_target": (
            root_offsets_ready
        ),
        "state_image_report": state_image_report_path.as_posix(),
        "cpu_reference_report": cpu_reference_report_path.as_posix(),
        "cpu_reference_observables_ready": cpu_reference_ready,
        "program_sha256": program_sha,
        "el2_program_sha256": EL2_PROGRAM_SHA256,
        "reuse_blockers": list(dict.fromkeys(reuse_blockers)),
        "missing_build_context": list(dict.fromkeys(missing_context)),
        "next_required_boundary": (
            "execute EH sidecar bridge comparison"
            if design_specific_executable_ready
            else "implement and review an EH-specific sidecar executable before bridge comparison"
        ),
        "sidecar_bridge_invoked": False,
        "sidecar_observables_ready": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "fail_closed": True,
        "non_claims": [
            "EL2 executable review does not review an EH executable",
            "no EH sidecar bridge comparison has run",
            "no timing, speedup, or usefulness claim is made",
        ],
    }


def build_sidecar_bridge_payload(repo_root: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    design = str(target["design"])
    configuration = str(target["configuration"])
    test = str(target["test"])
    case = str(target["case"])
    target_name = _authority_target_name(design, configuration, test)
    state_image_report_path = _state_image_report_path_for(design)
    state_image_report = _load_json(repo_root / state_image_report_path)
    state_image_artifact = _mapping(state_image_report).get("state_image_artifact")
    cpu_reference_report_path = _cpu_reference_report_path_for(design)
    cpu_reference_report = _load_json(repo_root / cpu_reference_report_path)
    cpu_reference_ready = (
        isinstance(cpu_reference_report, Mapping)
        and cpu_reference_report.get("status") == "cpu_reference_passed"
        and cpu_reference_report.get("cpu_reference_ready_for_hybrid_compare") is True
    )
    authority_path = _authority_path_for(design, configuration, test)
    authority = _load_json(repo_root / authority_path)
    layout_report_path = _state_layout_report_path_for(design)
    layout_report = _load_json(repo_root / layout_report_path)
    root_offset_review_path = _root_offset_review_report_path_for(design)
    root_offset_review = _load_json(repo_root / root_offset_review_path)
    sidecar_executable_review_path = _sidecar_executable_review_report_path_for(design)
    sidecar_executable_review = _load_json(repo_root / sidecar_executable_review_path)
    sidecar_executable_preflight_path = _sidecar_executable_preflight_report_path_for(design)
    sidecar_executable_preflight = _load_json(repo_root / sidecar_executable_preflight_path)
    bounded_execution_report_path = _sidecar_bridge_bounded_execution_report_path_for(design)
    bounded_execution_report = _load_json(repo_root / bounded_execution_report_path)
    ptxas_probe_report_path = _ptxas_probe_report_path_for(design)
    ptxas_probe_report = (
        _load_json(repo_root / ptxas_probe_report_path) if ptxas_probe_report_path is not None else None
    )
    entry_pruned_probe_report_path = _entry_pruned_module_probe_report_path_for(design)
    entry_pruned_probe_report = (
        _load_json(repo_root / entry_pruned_probe_report_path)
        if entry_pruned_probe_report_path is not None
        else None
    )
    entry_pruned_eval_only_raw_probe = _entry_pruned_eval_only_raw_probe_for(repo_root, design)
    entry_pruned_eval_only_variant_raw_probes = _eh2_eval_only_variant_raw_probes(repo_root, design)
    eh2_host_cleanup_eval_only_probe = _eh2_host_cleanup_eval_only_probe(repo_root, design)
    eh2_host_cleanup_v2_eval_only_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="host_cleanup_v2_eval_only_direct_probe",
        success_status="host_cleanup_v2_eval_only_passed",
        cuda700_status="host_cleanup_v2_eval_only_still_illegal_memory_access",
    )
    eh2_return_before_eval_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="return_before_eval_direct_probe",
        success_status="return_before_eval_passed",
        cuda700_status="return_before_eval_still_illegal_memory_access",
    )
    eh2_return_before_eval_call_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="return_before_eval_call_direct_probe",
        success_status="prologue_only_return_before_eval_call_passed",
        cuda700_status="prologue_only_return_before_eval_call_still_illegal_memory_access",
    )
    eh2_eval_return_before_phase_act_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_return_before_phase_act_direct_probe",
        success_status="eval_return_before_phase_act_passed",
        cuda700_status="eval_return_before_phase_act_still_illegal_memory_access",
    )
    eh2_eval_return_after_one_phase_act_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_return_after_one_phase_act_direct_probe",
        success_status="eval_return_after_one_phase_act_passed",
        cuda700_status="eval_return_after_one_phase_act_still_illegal_memory_access",
    )
    eh2_eval_phase_act_return_after_triggers_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_return_after_triggers_direct_probe",
        success_status="eval_phase_act_return_after_triggers_passed",
        cuda700_status="eval_phase_act_return_after_triggers_still_illegal_memory_access",
    )
    eh2_eval_phase_act_return_after_orinto_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_return_after_orinto_direct_probe",
        success_status="eval_phase_act_return_after_orinto_passed",
        cuda700_status="eval_phase_act_return_after_orinto_still_illegal_memory_access",
    )
    eh2_trigger_orinto_return_before_first_ix_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="trigger_orinto_return_before_first_ix_direct_probe",
        success_status="trigger_orinto_return_before_first_ix_passed",
        cuda700_status="trigger_orinto_return_before_first_ix_still_illegal_memory_access",
    )
    eh2_trigger_orinto_return_before_first_ix_stack64k_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="trigger_orinto_return_before_first_ix_stack64k_direct_probe",
        success_status="trigger_orinto_return_before_first_ix_stack64k_passed",
        cuda700_status="trigger_orinto_return_before_first_ix_stack64k_still_illegal_memory_access",
    )
    eh2_inline_orinto_return_after_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_return_after_direct_probe",
        success_status="inline_orinto_return_after_passed",
        cuda700_status="inline_orinto_return_after_still_illegal_memory_access",
    )
    eh2_inline_orinto_noop_return_after_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_noop_return_after_direct_probe",
        success_status="inline_orinto_noop_return_after_passed",
        cuda700_status="inline_orinto_noop_return_after_still_illegal_memory_access",
    )
    eh2_inline_orinto_after_dst_load_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_after_dst_load_direct_probe",
        success_status="inline_orinto_after_dst_load_passed",
        cuda700_status="inline_orinto_after_dst_load_still_illegal_memory_access",
    )
    eh2_inline_orinto_after_src_load_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_after_src_load_direct_probe",
        success_status="inline_orinto_after_src_load_passed",
        cuda700_status="inline_orinto_after_src_load_still_illegal_memory_access",
    )
    eh2_inline_orinto_before_store_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_before_store_direct_probe",
        success_status="inline_orinto_before_store_passed",
        cuda700_status="inline_orinto_before_store_still_illegal_memory_access",
    )
    eh2_inline_orinto_store_u64_src_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_store_u64_src_direct_probe",
        success_status="inline_orinto_store_u64_src_passed",
        cuda700_status="inline_orinto_store_u64_src_still_illegal_memory_access",
    )
    eh2_inline_orinto_store_u32_dst_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_store_u32_dst_direct_probe",
        success_status="inline_orinto_store_u32_dst_passed",
        cuda700_status="inline_orinto_store_u32_dst_still_illegal_memory_access",
    )
    eh2_inline_orinto_store_u8_dst_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_store_u8_dst_direct_probe",
        success_status="inline_orinto_store_u8_dst_passed",
        cuda700_status="inline_orinto_store_u8_dst_still_illegal_memory_access",
    )
    eh2_inline_orinto_store_u64_root_base_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_store_u64_root_base_direct_probe",
        success_status="inline_orinto_store_u64_root_base_passed",
        cuda700_status="inline_orinto_store_u64_root_base_still_illegal_memory_access",
    )
    eh2_entry_store_nba_trigger_return_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="entry_store_nba_trigger_return_direct_probe",
        success_status="entry_store_nba_trigger_return_passed",
        cuda700_status="entry_store_nba_trigger_return_still_illegal_memory_access",
    )
    eh2_inline_orinto_return_after_padded2m_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_return_after_padded2m_direct_probe",
        success_status="inline_orinto_return_after_padded2m_passed",
        cuda700_status="inline_orinto_return_after_padded2m_still_illegal_memory_access",
    )
    eh2_inline_orinto_return_after_maxr128_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_return_after_maxr128_direct_probe",
        success_status="inline_orinto_return_after_maxr128_passed",
        cuda700_status="inline_orinto_return_after_maxr128_still_illegal_memory_access",
    )
    eh2_store_vnba_before_triggers_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_store_vnba_before_triggers_return_direct_probe",
        success_status="eval_phase_act_store_vnba_before_triggers_passed",
        cuda700_status="eval_phase_act_store_vnba_before_triggers_still_illegal_memory_access",
    )
    eh2_store_vnba_after_triggers_direct_root_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_store_vnba_after_triggers_direct_root_return_direct_probe",
        success_status="eval_phase_act_store_vnba_after_triggers_direct_root_passed",
        cuda700_status="eval_phase_act_store_vnba_after_triggers_direct_root_still_illegal_memory_access",
    )
    eh2_store_next472416_after_triggers_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_store_next472416_after_triggers_return_direct_probe",
        success_status="eval_phase_act_store_next472416_after_triggers_passed",
        cuda700_status="eval_phase_act_store_next472416_after_triggers_still_illegal_memory_access",
    )
    eh2_inline_orinto_store_vnba_cvta_global_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_inline_orinto_store_vnba_cvta_global_return_direct_probe",
        success_status="inline_orinto_store_vnba_cvta_global_passed",
        cuda700_status="inline_orinto_store_vnba_cvta_global_still_illegal_memory_access",
    )
    eh2_minimal_store_vnba_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_phase_act_minimal_store_vnba_return_direct_probe",
        success_status="eval_phase_act_minimal_store_vnba_passed",
        cuda700_status="eval_phase_act_minimal_store_vnba_still_illegal_memory_access",
    )
    eh2_std_ref_get_canonical_eval_only_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="std_ref_get_canonical_eval_only_direct_probe",
        success_status="std_ref_get_canonical_eval_only_passed",
        cuda700_status="std_ref_get_canonical_eval_only_still_illegal_memory_access",
    )
    eh2_eval_return_before_phase_act_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_eval_return_before_phase_act_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_eval_return_before_phase_act_passed",
        cuda700_status="std_ref_get_canonical_eval_return_before_phase_act_still_illegal_memory_access",
    )
    eh2_eval_return_after_one_phase_act_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_eval_return_after_one_phase_act_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_eval_return_after_one_phase_act_passed",
        cuda700_status="std_ref_get_canonical_eval_return_after_one_phase_act_still_illegal_memory_access",
    )
    eh2_phase_act_return_after_orinto_ret0_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_eval_phase_act_return_after_orinto_ret0_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_phase_act_return_after_orinto_ret0_passed",
        cuda700_status="std_ref_get_canonical_phase_act_return_after_orinto_ret0_still_illegal_memory_access",
    )
    eh2_phase_act_return_after_anyset_ret0_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_eval_phase_act_return_after_anyset_ret0_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_phase_act_return_after_anyset_ret0_passed",
        cuda700_status="std_ref_get_canonical_phase_act_return_after_anyset_ret0_still_illegal_memory_access",
    )
    eh2_phase_act_return_after_timing_resume_ret0_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_eval_phase_act_return_after_timing_resume_ret0_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_phase_act_return_after_timing_resume_ret0_passed",
        cuda700_status="std_ref_get_canonical_phase_act_return_after_timing_resume_ret0_still_illegal_memory_access",
    )
    eh2_trigger_orinto_return_before_loop_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_trigger_orinto_return_before_loop_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_trigger_orinto_return_before_loop_passed",
        cuda700_status="std_ref_get_canonical_trigger_orinto_return_before_loop_still_illegal_memory_access",
    )
    eh2_trigger_orinto_return_after_dst_load_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_trigger_orinto_return_after_dst_load_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_trigger_orinto_return_after_dst_load_passed",
        cuda700_status="std_ref_get_canonical_trigger_orinto_return_after_dst_load_still_illegal_memory_access",
    )
    eh2_trigger_orinto_return_after_src_load_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_trigger_orinto_return_after_src_load_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_trigger_orinto_return_after_src_load_passed",
        cuda700_status="std_ref_get_canonical_trigger_orinto_return_after_src_load_still_illegal_memory_access",
    )
    eh2_trigger_orinto_return_before_store_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_trigger_orinto_return_before_store_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_trigger_orinto_return_before_store_passed",
        cuda700_status="std_ref_get_canonical_trigger_orinto_return_before_store_still_illegal_memory_access",
    )
    eh2_trigger_orinto_return_after_store_std_ref_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_trigger_orinto_return_after_store_std_ref_get_canonical_direct_probe",
        success_status="std_ref_get_canonical_trigger_orinto_return_after_store_passed",
        cuda700_status="std_ref_get_canonical_trigger_orinto_return_after_store_still_illegal_memory_access",
    )
    eh2_vlunpacked_lm1_canonical_eval_only_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlunpacked_lm1_ix0_canonical_eval_only_direct_probe",
        success_status="vlunpacked_lm1_canonical_eval_only_passed",
        cuda700_status="vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access",
    )
    eh2_vlunpacked_lm1_phase_act_return_before_orinto_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_eval_phase_act_return_before_orinto_vlunpacked_lm1_canonical_direct_probe",
        success_status="vlunpacked_lm1_phase_act_return_before_orinto_passed",
        cuda700_status="vlunpacked_lm1_phase_act_return_before_orinto_still_illegal_memory_access",
    )
    eh2_vlunpacked_lm1_trigger_orinto_return_immediate_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vl_trigger_orinto_return_immediate_vlunpacked_lm1_canonical_direct_probe",
        success_status="vlunpacked_lm1_trigger_orinto_return_immediate_passed",
        cuda700_status="vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access",
    )
    eh2_vlunpacked_lm1_orinto_rewrite_eval_only_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlunpacked_lm1_orinto_rewrite_eval_only_direct_probe",
        success_status="vlunpacked_lm1_orinto_rewrite_eval_only_passed",
        cuda700_status="vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access",
    )
    eh2_orinto_store_skip_eval_only_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="orinto_store_skip_eval_only_direct_probe",
        success_status="orinto_store_skip_eval_only_passed",
        cuda700_status="orinto_store_skip_eval_only_still_illegal_memory_access",
    )
    eh2_orinto_store_zero_eval_only_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="orinto_store_zero_eval_only_direct_probe",
        success_status="orinto_store_zero_eval_only_passed",
        cuda700_status="orinto_store_zero_eval_only_still_illegal_memory_access",
    )
    eh2_orinto_store_dst_eval_only_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="orinto_store_dst_eval_only_direct_probe",
        success_status="orinto_store_dst_eval_only_passed",
        cuda700_status="orinto_store_dst_eval_only_still_illegal_memory_access",
    )
    eh2_skip_store_return_before_anyset_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="skip_store_return_before_anyset_eval_only_direct_probe",
        success_status="skip_store_return_before_anyset_passed",
        cuda700_status="skip_store_return_before_anyset_still_illegal_memory_access",
    )
    eh2_skip_store_return_after_anyset_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="skip_store_return_after_anyset_eval_only_direct_probe",
        success_status="skip_store_return_after_anyset_passed",
        cuda700_status="skip_store_return_after_anyset_still_illegal_memory_access",
    )
    eh2_skip_store_return_after_timing_resume_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="skip_store_return_after_timing_resume_eval_only_direct_probe",
        success_status="skip_store_return_after_timing_resume_passed",
        cuda700_status="skip_store_return_after_timing_resume_still_illegal_memory_access",
    )
    eh2_skip_store_return_after_eval_act_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="skip_store_return_after_eval_act_eval_only_direct_probe",
        success_status="skip_store_return_after_eval_act_passed",
        cuda700_status="skip_store_return_after_eval_act_still_illegal_memory_access",
    )
    eh2_eval_act_return_after_callseq_probes = {
        str(callseq): _eh2_direct_probe(
            repo_root,
            design,
            name=f"eval_act_return_after_callseq_{callseq}_eval_only_direct_probe",
            success_status=f"eval_act_return_after_callseq_{callseq}_passed",
            cuda700_status=f"eval_act_return_after_callseq_{callseq}_still_illegal_memory_access",
        )
        for callseq in (950, 951, 952, 953, 954)
    }
    eh2_dec_cam0_return_after_param_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="dec_cam0_return_after_param_eval_only_direct_probe",
        success_status="dec_cam0_return_after_param_passed",
        cuda700_status="dec_cam0_return_after_param_still_illegal_memory_access",
    )
    eh2_dec_cam0_return_after_callseq_15707_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="dec_cam0_return_after_callseq_15707_eval_only_direct_probe",
        success_status="dec_cam0_return_after_callseq_15707_passed",
        cuda700_status="dec_cam0_return_after_callseq_15707_still_illegal_memory_access",
    )
    eh2_dec_cam0_minimal_body_ret_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="dec_cam0_minimal_body_ret_eval_only_direct_probe",
        success_status="dec_cam0_minimal_body_ret_passed",
        cuda700_status="dec_cam0_minimal_body_ret_still_illegal_memory_access",
    )
    eh2_eval_act_skip_callseq_952_return_after_953_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_act_skip_callseq_952_return_after_953_eval_only_direct_probe",
        success_status="eval_act_skip_callseq_952_return_after_953_passed",
        cuda700_status="eval_act_skip_callseq_952_return_after_953_still_illegal_memory_access",
    )
    eh2_eval_act_skip_callseq_952_953_return_after_954_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_act_skip_callseq_952_953_return_after_954_eval_only_direct_probe",
        success_status="eval_act_skip_callseq_952_953_return_after_954_passed",
        cuda700_status="eval_act_skip_callseq_952_953_return_after_954_still_illegal_memory_access",
    )
    eh2_eval_act_skip_callseq_952_953_954_return_after_954_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="eval_act_skip_callseq_952_953_954_return_after_954_eval_only_direct_probe",
        success_status="eval_act_skip_callseq_952_953_954_return_after_954_passed",
        cuda700_status="eval_act_skip_callseq_952_953_954_return_after_954_still_illegal_memory_access",
    )
    eh2_vlwide_pointer_conversion_canonical_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_canonical_entry_slice_const_eval_only_direct_probe",
        success_status="vlwide_pointer_conversion_canonical_eval_only_passed",
        cuda700_status="vlwide_pointer_conversion_canonical_eval_only_still_illegal_memory_access",
    )
    eh2_vlwide_kernel_return_before_eval_call_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_kernel_return_before_eval_call_eval_only_direct_probe",
        success_status="vlwide_kernel_return_before_eval_call_passed",
        cuda700_status="vlwide_kernel_return_before_eval_call_still_illegal_memory_access",
    )
    eh2_vlwide_eval_before_phase_act_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_eval_before_phase_act_ret_eval_only_direct_probe",
        success_status="vlwide_eval_before_phase_act_passed",
        cuda700_status="vlwide_eval_before_phase_act_still_illegal_memory_access",
    )
    eh2_vlwide_phase_act_after_callseq_5472_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_phase_act_after_callseq_5472_ret0_eval_only_direct_probe",
        success_status="vlwide_phase_act_after_callseq_5472_passed",
        cuda700_status="vlwide_phase_act_after_callseq_5472_still_illegal_memory_access",
    )
    eh2_vlwide_phase_act_before_trigger_merge_store_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_phase_act_before_trigger_merge_store_ret0_eval_only_direct_probe",
        success_status="vlwide_phase_act_before_trigger_merge_store_passed",
        cuda700_status="vlwide_phase_act_before_trigger_merge_store_still_illegal_memory_access",
    )
    eh2_vlwide_phase_act_after_trigger_merge_store_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_phase_act_after_trigger_merge_store_ret0_eval_only_direct_probe",
        success_status="vlwide_phase_act_after_trigger_merge_store_passed",
        cuda700_status="vlwide_phase_act_after_trigger_merge_store_still_illegal_memory_access",
    )
    eh2_vlwide_phase_act_skip_trigger_merge_store_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_phase_act_skip_trigger_merge_store_continue_eval_only_direct_probe",
        success_status="vlwide_phase_act_skip_trigger_merge_store_continue_passed",
        cuda700_status="vlwide_phase_act_skip_trigger_merge_store_continue_still_illegal_memory_access",
    )
    eh2_vlwide_phase_act_store_one_eval_return_after_phase_act_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_phase_act_short_store_one_eval_return_after_phase_act_eval_only_direct_probe",
        success_status="vlwide_phase_act_store_one_eval_return_after_phase_act_passed",
        cuda700_status="vlwide_phase_act_store_one_eval_return_after_phase_act_still_illegal_memory_access",
    )
    eh2_vlwide_phase_act_store_one_nba_before_eval_nba_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_phase_act_store_one_nba_before_eval_nba_ret0_eval_only_direct_probe",
        success_status="vlwide_phase_act_store_one_nba_before_eval_nba_passed",
        cuda700_status="vlwide_phase_act_store_one_nba_before_eval_nba_still_illegal_memory_access",
    )
    eh2_vlwide_phase_act_store_one_nba_after_eval_nba_probe = _eh2_direct_probe(
        repo_root,
        design,
        name="vlwide_phase_act_store_one_nba_after_eval_nba_ret0_eval_only_direct_probe",
        success_status="vlwide_phase_act_store_one_nba_after_eval_nba_passed",
        cuda700_status="vlwide_phase_act_store_one_nba_after_eval_nba_still_illegal_memory_access",
    )
    entry_pruned_static_residue_probe = _entry_pruned_ptx_static_residue_for(repo_root, design)
    missing_context: list[str] = []
    if authority is None:
        missing_context.append("authority_registry")
    if layout_report is None:
        missing_context.append("state_layout_report")
    if state_image_report is None:
        missing_context.append("state_image_report")
    status_reasons: list[str] = []
    if _mapping(layout_report).get("state_layout_ready") is not True:
        if root_offset_review is None:
            missing_context.append("reviewed_root_field_offsets")
            status_reasons.append("root_offsets_unreviewed")
        elif root_offset_review.get("root_field_offsets_reviewed_for_target") is not True:
            missing_context.extend(str(item) for item in root_offset_review.get("missing_build_context", []) if item)
            status_reasons.append("root_observable_offset_review_incomplete")
    if sidecar_executable_review is None:
        missing_context.append("sidecar_executable_review")
        status_reasons.append("sidecar_executable_unreviewed")
    elif sidecar_executable_review.get("sidecar_executable_reviewed_for_target") is not True:
        missing_context.append("design_specific_sidecar_executable_implementation")
        status_reasons.append("design_specific_sidecar_executable_missing")
    elif (
        sidecar_executable_preflight is not None
        and sidecar_executable_preflight.get("sidecar_executable_ready_for_bridge") is not True
    ):
        missing_context.extend(
            str(item)
            for item in sidecar_executable_preflight.get("missing_build_context", [])
            if item
        )
        status_reasons.append("sidecar_executable_preflight_blocked")
    elif (
        bounded_execution_report is not None
        and bounded_execution_report.get("sidecar_bridge_invoked") is True
        and bounded_execution_report.get("sidecar_observables_ready") is not True
    ):
        missing_context.extend(
            str(item)
            for item in bounded_execution_report.get("missing_build_context", [])
            if item
        )
        missing_context.append("executed_bridge_comparison")
        status_reasons.append(str(bounded_execution_report.get("status") or "bridge_execution_incomplete"))
        if (
            _mapping(bounded_execution_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
            == "before_cuModuleLoad"
            and _mapping(ptxas_probe_report).get("status") == "ptxas_timeout"
        ):
            missing_context.append("ptxas_cubin_probe_timeout")
        if _mapping(_mapping(entry_pruned_probe_report).get("bridge_probe")).get("status") == (
            "illegal_memory_access_at_first_eval_launch"
        ):
            missing_context.append("entry_pruned_eval_kernel_illegal_memory_access")
            if _mapping(entry_pruned_probe_report.get("eval_only_probe")).get("status") == (
                "illegal_memory_access_at_first_eval_launch"
            ):
                missing_context.append("entry_pruned_eval_only_fault_confirmed")
            if _mapping(entry_pruned_probe_report.get("eval_only_padded_storage_probe")).get(
                "status"
            ) == "padded_storage_did_not_clear_first_eval_fault":
                missing_context.append("padded_storage_did_not_clear_eval_fault")
            if _mapping(entry_pruned_probe_report.get("eval_only_static_ptx_residue_probe")).get(
                "status"
            ) == "reachable_stdout_finish_cpp_runtime_residue_detected":
                missing_context.append("reachable_stdout_finish_cpp_runtime_residue")
            if _mapping(entry_pruned_probe_report.get("eval_only_region_counter_global_init_probe")).get(
                "status"
            ) == "illegal_memory_access_at_first_eval_launch":
                missing_context.append("region_counter_global_init_did_not_clear_eval_fault")
            if _mapping(entry_pruned_probe_report.get("stack_limit_probe")).get("status") == (
                "stack_limit_override_did_not_clear_first_eval_fault"
            ):
                missing_context.append("stack_limit_override_did_not_clear_eval_fault")
            host_io_stub_probe = _mapping(entry_pruned_probe_report.get("host_io_stub_eval_only_probe"))
            if host_io_stub_probe.get("status") == "illegal_memory_access_at_first_eval_launch":
                missing_context.append("host_io_stub_eval_only_fault_confirmed")
                host_io_stub_storage_probe = _mapping(host_io_stub_probe.get("storage2m_padded_init_probe"))
                if host_io_stub_storage_probe.get("status") == "padded_storage_did_not_clear_first_eval_fault":
                    missing_context.append("host_io_stub_padded_storage_did_not_clear_eval_fault")
            if _mapping(host_io_stub_probe.get("compute_sanitizer_probe")).get("status") == (
                "tool_environment_blocked_before_instrumented_cuda_api"
            ):
                missing_context.append("compute_sanitizer_tool_environment_blocked")
        if (
            entry_pruned_probe_report is not None
            and entry_pruned_probe_report.get("schema_role") == "veer_eh_sidecar_bridge_execution"
            and entry_pruned_probe_report.get("status") == "gpu_launch_failed"
            and entry_pruned_probe_report.get("gpu_module_override")
        ):
            missing_context.append("entry_pruned_cubin_gpu_launch_failed")
            stderr_tail = entry_pruned_probe_report.get("run_vl_hybrid_stderr_tail")
            if isinstance(stderr_tail, Sequence) and not isinstance(stderr_tail, str):
                if any("CUDA error 700" in str(line) for line in stderr_tail):
                    missing_context.append("entry_pruned_cubin_gpu_launch_illegal_memory_access")
            if (
                _mapping(entry_pruned_probe_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
                == "after_first_kernel_launch"
            ):
                missing_context.append("entry_pruned_cubin_reaches_launch_loop")
            if (
                entry_pruned_probe_report.get("run_vl_hybrid_sync_each_step") is True
                and _mapping(entry_pruned_probe_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
                == "before_first_step_sync"
            ):
                missing_context.append("entry_pruned_cubin_first_step_sync_illegal_memory_access")
            if _mapping(entry_pruned_eval_only_raw_probe).get("status") == (
                "illegal_memory_access_at_first_eval_launch"
            ):
                missing_context.append("entry_pruned_eval_only_fault_confirmed")
            if _mapping(entry_pruned_eval_only_variant_raw_probes.get("padded2m")).get("status") == (
                "illegal_memory_access_at_first_eval_launch"
            ):
                missing_context.append("entry_pruned_padded_storage_did_not_clear_eval_fault")
            if _mapping(entry_pruned_eval_only_variant_raw_probes.get("stack64k")).get("status") == (
                "illegal_memory_access_at_first_eval_launch"
            ):
                missing_context.append("entry_pruned_stack64k_did_not_clear_eval_fault")
            if _mapping(entry_pruned_eval_only_variant_raw_probes.get("zero_init")).get("status") == (
                "illegal_memory_access_at_first_eval_launch"
            ):
                missing_context.append("entry_pruned_zero_init_eval_only_fault_confirmed")
            if _mapping(entry_pruned_static_residue_probe).get("runtime_residue_detected") is True:
                missing_context.append("entry_pruned_cpp_verilator_runtime_residue_detected")
            if _mapping(eh2_host_cleanup_eval_only_probe).get("status") == (
                "host_cleanup_eval_only_still_illegal_memory_access"
            ):
                missing_context.append("eh2_host_cleanup_eval_only_did_not_clear_eval_fault")
            if _mapping(eh2_host_cleanup_v2_eval_only_probe).get("status") == (
                "host_cleanup_v2_eval_only_still_illegal_memory_access"
            ):
                missing_context.append("eh2_host_cleanup_v2_eval_only_did_not_clear_eval_fault")
            if _mapping(eh2_return_before_eval_probe).get("status") == "return_before_eval_passed":
                missing_context.append("eh2_return_before_eval_launch_infrastructure_passed")
            if _mapping(eh2_return_before_eval_call_probe).get("status") == (
                "prologue_only_return_before_eval_call_passed"
            ):
                missing_context.append("eh2_prologue_pointer_setup_passed_before_eval_call")
            if (
                _mapping(eh2_eval_return_before_phase_act_probe).get("status")
                == "eval_return_before_phase_act_passed"
                and _mapping(eh2_eval_return_after_one_phase_act_probe).get("status")
                == "eval_return_after_one_phase_act_still_illegal_memory_access"
            ):
                missing_context.append("eh2_eval_phase_act_call_boundary_fault")
            if (
                _mapping(eh2_eval_phase_act_return_after_triggers_probe).get("status")
                == "eval_phase_act_return_after_triggers_passed"
                and _mapping(eh2_eval_phase_act_return_after_orinto_probe).get("status")
                == "eval_phase_act_return_after_orinto_still_illegal_memory_access"
            ):
                missing_context.append("eh2_eval_phase_act_trigger_orinto_boundary_fault")
            if _mapping(eh2_trigger_orinto_return_before_first_ix_probe).get("status") == (
                "trigger_orinto_return_before_first_ix_still_illegal_memory_access"
            ):
                missing_context.append("eh2_trigger_orinto_device_call_entry_fault")
            if _mapping(eh2_trigger_orinto_return_before_first_ix_stack64k_probe).get("status") == (
                "trigger_orinto_return_before_first_ix_stack64k_still_illegal_memory_access"
            ):
                missing_context.append("eh2_trigger_orinto_entry_fault_not_stack_limit")
            inline_loads_pass = (
                _mapping(eh2_inline_orinto_noop_return_after_probe).get("status")
                == "inline_orinto_noop_return_after_passed"
                and _mapping(eh2_inline_orinto_after_dst_load_probe).get("status")
                == "inline_orinto_after_dst_load_passed"
                and _mapping(eh2_inline_orinto_after_src_load_probe).get("status")
                == "inline_orinto_after_src_load_passed"
                and _mapping(eh2_inline_orinto_before_store_probe).get("status")
                == "inline_orinto_before_store_passed"
            )
            if inline_loads_pass:
                missing_context.append("eh2_inline_orinto_loads_before_store_pass")
            if _mapping(eh2_inline_orinto_return_after_probe).get("status") == (
                "inline_orinto_return_after_still_illegal_memory_access"
            ):
                missing_context.append("eh2_inline_orinto_store_to_vnba_triggered_fault")
            if _mapping(eh2_inline_orinto_store_u64_src_probe).get("status") == (
                "inline_orinto_store_u64_src_passed"
            ):
                missing_context.append("eh2_adjacent_vact_triggered_store_passes")
            if (
                _mapping(eh2_inline_orinto_store_u32_dst_probe).get("status")
                == "inline_orinto_store_u32_dst_still_illegal_memory_access"
                and _mapping(eh2_inline_orinto_store_u8_dst_probe).get("status")
                == "inline_orinto_store_u8_dst_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vnba_triggered_store_width_independent_fault")
            if _mapping(eh2_inline_orinto_store_u64_root_base_probe).get("status") == (
                "inline_orinto_store_u64_root_base_passed"
            ):
                missing_context.append("eh2_root_base_store_passes")
            if _mapping(eh2_entry_store_nba_trigger_return_probe).get("status") == (
                "entry_store_nba_trigger_return_passed"
            ):
                missing_context.append("eh2_entry_context_vnba_triggered_store_passes")
            if _mapping(eh2_inline_orinto_return_after_padded2m_probe).get("status") == (
                "inline_orinto_return_after_padded2m_still_illegal_memory_access"
            ):
                missing_context.append("eh2_padded2m_does_not_clear_eval_phase_vnba_store_fault")
            if _mapping(eh2_inline_orinto_return_after_maxr128_probe).get("status") == (
                "inline_orinto_return_after_maxr128_still_illegal_memory_access"
            ):
                missing_context.append("eh2_maxr128_does_not_clear_eval_phase_vnba_store_fault")
            if _mapping(eh2_store_vnba_before_triggers_probe).get("status") == (
                "eval_phase_act_store_vnba_before_triggers_passed"
            ):
                missing_context.append("eh2_eval_phase_vnba_store_passes_before_triggers")
            if _mapping(eh2_store_vnba_after_triggers_direct_root_probe).get("status") == (
                "eval_phase_act_store_vnba_after_triggers_direct_root_passed"
            ):
                missing_context.append("eh2_eval_phase_vnba_store_passes_with_direct_root")
            if _mapping(eh2_store_next472416_after_triggers_probe).get("status") == (
                "eval_phase_act_store_next472416_after_triggers_passed"
            ):
                missing_context.append("eh2_eval_phase_adjacent_next_store_passes_after_triggers")
            if _mapping(eh2_inline_orinto_store_vnba_cvta_global_probe).get("status") == (
                "inline_orinto_store_vnba_cvta_global_still_illegal_memory_access"
            ):
                missing_context.append("eh2_reference_wrapper_get_cvta_vnba_store_still_faults")
            if _mapping(eh2_minimal_store_vnba_probe).get("status") == (
                "eval_phase_act_minimal_store_vnba_passed"
            ):
                missing_context.append("eh2_minimal_eval_phase_vnba_store_passes")
            if _mapping(eh2_std_ref_get_canonical_eval_only_probe).get("status") == (
                "std_ref_get_canonical_eval_only_still_illegal_memory_access"
            ):
                missing_context.append("eh2_std_ref_get_canonical_eval_only_still_faults")
            if _mapping(eh2_eval_return_before_phase_act_std_ref_probe).get("status") == (
                "std_ref_get_canonical_eval_return_before_phase_act_passed"
            ):
                missing_context.append("eh2_std_ref_get_canonical_eval_prologue_passes_before_phase_act")
            if _mapping(eh2_eval_return_after_one_phase_act_std_ref_probe).get("status") == (
                "std_ref_get_canonical_eval_return_after_one_phase_act_still_illegal_memory_access"
            ):
                missing_context.append("eh2_std_ref_get_canonical_one_phase_act_still_faults")
            if _mapping(eh2_phase_act_return_after_orinto_ret0_std_ref_probe).get("status") == (
                "std_ref_get_canonical_phase_act_return_after_orinto_ret0_still_illegal_memory_access"
            ):
                missing_context.append("eh2_std_ref_get_canonical_phase_act_orinto_still_faults")
            if _mapping(eh2_phase_act_return_after_anyset_ret0_std_ref_probe).get("status") == (
                "std_ref_get_canonical_phase_act_return_after_anyset_ret0_still_illegal_memory_access"
            ):
                missing_context.append("eh2_std_ref_get_canonical_phase_act_anyset_still_faults")
            if _mapping(eh2_phase_act_return_after_timing_resume_ret0_std_ref_probe).get("status") == (
                "std_ref_get_canonical_phase_act_return_after_timing_resume_ret0_still_illegal_memory_access"
            ):
                missing_context.append("eh2_std_ref_get_canonical_phase_act_timing_resume_still_faults")
            if _mapping(eh2_trigger_orinto_return_before_loop_std_ref_probe).get("status") == (
                "std_ref_get_canonical_trigger_orinto_return_before_loop_passed"
            ):
                missing_context.append("eh2_std_ref_get_canonical_trigger_orinto_entry_call_passes")
            if _mapping(eh2_trigger_orinto_return_after_dst_load_std_ref_probe).get("status") == (
                "std_ref_get_canonical_trigger_orinto_return_after_dst_load_passed"
            ):
                missing_context.append("eh2_std_ref_get_canonical_trigger_orinto_dst_load_passes")
            if _mapping(eh2_trigger_orinto_return_after_src_load_std_ref_probe).get("status") == (
                "std_ref_get_canonical_trigger_orinto_return_after_src_load_passed"
            ):
                missing_context.append("eh2_std_ref_get_canonical_trigger_orinto_src_load_passes")
            if _mapping(eh2_trigger_orinto_return_before_store_std_ref_probe).get("status") == (
                "std_ref_get_canonical_trigger_orinto_return_before_store_passed"
            ):
                missing_context.append("eh2_std_ref_get_canonical_trigger_orinto_before_store_passes")
            if _mapping(eh2_trigger_orinto_return_after_store_std_ref_probe).get("status") == (
                "std_ref_get_canonical_trigger_orinto_return_after_store_still_illegal_memory_access"
            ):
                missing_context.append("eh2_std_ref_get_canonical_trigger_orinto_dst_store_fault")
            if _mapping(eh2_vlunpacked_lm1_canonical_eval_only_probe).get("status") == (
                "vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vlunpacked_lm1_canonicalization_did_not_clear_eval_fault")
            if _mapping(eh2_vlunpacked_lm1_phase_act_return_before_orinto_probe).get("status") == (
                "vlunpacked_lm1_phase_act_return_before_orinto_passed"
            ):
                missing_context.append("eh2_vlunpacked_lm1_phase_act_before_orinto_passes")
            if _mapping(eh2_vlunpacked_lm1_trigger_orinto_return_immediate_probe).get("status") == (
                "vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vlunpacked_lm1_trigger_orinto_helper_call_entry_fault")
            if _mapping(eh2_vlunpacked_lm1_orinto_rewrite_eval_only_probe).get("status") == (
                "vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vlunpacked_lm1_orinto_rewrite_did_not_clear_eval_fault")
            if (
                _mapping(eh2_orinto_store_skip_eval_only_probe).get("status")
                == "orinto_store_skip_eval_only_still_illegal_memory_access"
                and _mapping(eh2_orinto_store_zero_eval_only_probe).get("status")
                == "orinto_store_zero_eval_only_still_illegal_memory_access"
                and _mapping(eh2_orinto_store_dst_eval_only_probe).get("status")
                == "orinto_store_dst_eval_only_still_illegal_memory_access"
            ):
                missing_context.append("eh2_orinto_store_value_or_store_itself_is_not_only_fault")
            if _mapping(eh2_skip_store_return_before_anyset_probe).get("status") == (
                "skip_store_return_before_anyset_passed"
            ):
                missing_context.append("eh2_skip_store_before_anyset_passes")
            if _mapping(eh2_skip_store_return_after_anyset_probe).get("status") == (
                "skip_store_return_after_anyset_passed"
            ):
                missing_context.append("eh2_skip_store_trigger_anyset_passes")
            if _mapping(eh2_skip_store_return_after_timing_resume_probe).get("status") == (
                "skip_store_return_after_timing_resume_passed"
            ):
                missing_context.append("eh2_skip_store_timing_resume_passes")
            if _mapping(eh2_skip_store_return_after_eval_act_probe).get("status") == (
                "skip_store_return_after_eval_act_still_illegal_memory_access"
            ):
                missing_context.append("eh2_skip_store_eval_act_boundary_fault")
            for callseq, probe in eh2_eval_act_return_after_callseq_probes.items():
                status = _mapping(probe).get("status")
                if status == f"eval_act_return_after_callseq_{callseq}_passed":
                    missing_context.append(f"eh2_eval_act_return_after_callseq_{callseq}_passes")
                elif status == f"eval_act_return_after_callseq_{callseq}_still_illegal_memory_access":
                    missing_context.append(f"eh2_eval_act_return_after_callseq_{callseq}_fault")
            if (
                _mapping(eh2_eval_act_return_after_callseq_probes.get("951")).get("status")
                == "eval_act_return_after_callseq_951_passed"
                and _mapping(eh2_eval_act_return_after_callseq_probes.get("952")).get("status")
                == "eval_act_return_after_callseq_952_still_illegal_memory_access"
            ):
                missing_context.append("eh2_eval_act_dec_cam0_act_sequent_boundary_fault")
            if _mapping(eh2_dec_cam0_return_after_param_probe).get("status") == (
                "dec_cam0_return_after_param_still_illegal_memory_access"
            ):
                missing_context.append("eh2_dec_cam0_call_faults_before_param_load_return")
            if _mapping(eh2_dec_cam0_minimal_body_ret_probe).get("status") == (
                "dec_cam0_minimal_body_ret_still_illegal_memory_access"
            ):
                missing_context.append("eh2_dec_cam0_minimal_body_call_boundary_fault")
            if _mapping(eh2_eval_act_skip_callseq_952_return_after_953_probe).get("status") == (
                "eval_act_skip_callseq_952_return_after_953_still_illegal_memory_access"
            ):
                missing_context.append("eh2_eval_act_dec_cam1_call_boundary_fault")
            if _mapping(eh2_eval_act_skip_callseq_952_953_return_after_954_probe).get("status") == (
                "eval_act_skip_callseq_952_953_return_after_954_still_illegal_memory_access"
            ):
                missing_context.append("eh2_eval_act_dec_tlu0_call_boundary_fault")
            if _mapping(eh2_eval_act_skip_callseq_952_953_954_return_after_954_probe).get("status") == (
                "eval_act_skip_callseq_952_953_954_return_after_954_passed"
            ):
                missing_context.append("eh2_eval_act_first_three_submodule_act_calls_skipped_pass")
            if (
                _mapping(eh2_dec_cam0_minimal_body_ret_probe).get("status")
                == "dec_cam0_minimal_body_ret_still_illegal_memory_access"
                and _mapping(eh2_eval_act_skip_callseq_952_953_954_return_after_954_probe).get("status")
                == "eval_act_skip_callseq_952_953_954_return_after_954_passed"
            ):
                missing_context.append("eh2_eval_act_submodule_act_call_boundary_fault")
            if _mapping(eh2_vlwide_pointer_conversion_canonical_probe).get("status") == (
                "vlwide_pointer_conversion_canonical_eval_only_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vlwide_pointer_conversion_canonicalization_did_not_clear_eval_fault")
            if _mapping(eh2_vlwide_kernel_return_before_eval_call_probe).get("status") == (
                "vlwide_kernel_return_before_eval_call_passed"
            ):
                missing_context.append("eh2_vlwide_kernel_relocation_passes_before_eval_call")
            if _mapping(eh2_vlwide_eval_before_phase_act_probe).get("status") == (
                "vlwide_eval_before_phase_act_passed"
            ):
                missing_context.append("eh2_vlwide_eval_prologue_passes_before_phase_act")
            if _mapping(eh2_vlwide_phase_act_after_callseq_5472_probe).get("status") == (
                "vlwide_phase_act_after_callseq_5472_passed"
            ):
                missing_context.append("eh2_vlwide_phase_act_eval_triggers_call_passes")
            if _mapping(eh2_vlwide_phase_act_before_trigger_merge_store_probe).get("status") == (
                "vlwide_phase_act_before_trigger_merge_store_passed"
            ):
                missing_context.append("eh2_vlwide_phase_act_trigger_merge_loads_pass")
            if _mapping(eh2_vlwide_phase_act_after_trigger_merge_store_probe).get("status") == (
                "vlwide_phase_act_after_trigger_merge_store_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vlwide_phase_act_trigger_merge_store_fault")
            if _mapping(eh2_vlwide_phase_act_skip_trigger_merge_store_probe).get("status") == (
                "vlwide_phase_act_skip_trigger_merge_store_continue_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vlwide_phase_act_skip_trigger_merge_store_still_faults_later")
            if _mapping(eh2_vlwide_phase_act_store_one_eval_return_after_phase_act_probe).get("status") == (
                "vlwide_phase_act_store_one_eval_return_after_phase_act_passed"
            ):
                missing_context.append("eh2_vlwide_phase_act_nonzero_trigger_store_passes_when_eval_returns")
            if _mapping(eh2_vlwide_phase_act_store_one_nba_before_eval_nba_probe).get("status") == (
                "vlwide_phase_act_store_one_nba_before_eval_nba_passed"
            ):
                missing_context.append("eh2_vlwide_eval_phase_nba_trigger_anyset_passes_before_eval_nba")
            if _mapping(eh2_vlwide_phase_act_store_one_nba_after_eval_nba_probe).get("status") == (
                "vlwide_phase_act_store_one_nba_after_eval_nba_still_illegal_memory_access"
            ):
                missing_context.append("eh2_vlwide_eval_phase_nba_eval_nba_fault")
    else:
        missing_context.append("executed_bridge_comparison")
        status_reasons.append("bridge_unexecuted")
    if not cpu_reference_ready:
        missing_context.append("cpu_reference_observables")
        status_reasons.append("cpu_reference_observables_missing")
    missing_context.append("timing_report")
    status_reason = "_and_".join(dict.fromkeys(status_reasons)) or "bridge_unexecuted"
    return {
        "schema_version": 1,
        "surface": "rtlmeter_veer_family_sidecar_bridge_preflight",
        "mode": "prepare_veer_family_sidecar_bridge",
        "status": f"blocked_{design.lower().replace('-', '_')}_{status_reason}",
        "target": target_name,
        "rtlmeter_case": case,
        "authority_registry": authority_path.as_posix(),
        "state_layout_report": layout_report_path.as_posix(),
        "root_offset_review_report": root_offset_review_path.as_posix(),
        "state_image_report": state_image_report_path.as_posix(),
        "state_image_path": str(state_image_artifact) if state_image_artifact else None,
        "cpu_reference_report": cpu_reference_report_path.as_posix(),
        "sidecar_executable_review_report": sidecar_executable_review_path.as_posix(),
        "sidecar_executable_preflight_report": sidecar_executable_preflight_path.as_posix(),
        "bounded_bridge_execution_report": (
            bounded_execution_report_path.as_posix() if bounded_execution_report is not None else None
        ),
        "ptxas_probe_report": (
            ptxas_probe_report_path.as_posix()
            if ptxas_probe_report_path is not None and ptxas_probe_report is not None
            else None
        ),
        "entry_pruned_module_probe_report": (
            entry_pruned_probe_report_path.as_posix()
            if entry_pruned_probe_report_path is not None and entry_pruned_probe_report is not None
            else None
        ),
        "root_offset_review_performed": (
            _mapping(root_offset_review).get("root_offset_review_performed") is True
        ),
        "root_field_offsets_reviewed_for_target": (
            _mapping(root_offset_review).get("root_field_offsets_reviewed_for_target") is True
        ),
        "root_offset_missing_marker_groups": _mapping(root_offset_review).get("missing_marker_groups"),
        "sidecar_executable_review_performed": (
            _mapping(sidecar_executable_review).get("sidecar_executable_review_performed") is True
        ),
        "sidecar_executable_reviewed_for_target": (
            _mapping(sidecar_executable_review).get("sidecar_executable_reviewed_for_target") is True
        ),
        "sidecar_executable_ready_for_bridge": (
            _mapping(sidecar_executable_preflight).get("sidecar_executable_ready_for_bridge") is True
        ),
        "gpu_artifact_ready": _mapping(sidecar_executable_preflight).get("gpu_artifact_ready"),
        "gpu_artifact_prelaunch_rejection_required": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_prelaunch_rejection_required")
        ),
        "gpu_artifact_prelaunch_blockers": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_prelaunch_blockers")
        ),
        "gpu_artifact_recommended_prelaunch_boundary": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_recommended_prelaunch_boundary")
        ),
        "gpu_artifact_syms_auto_promotion_possible": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_syms_auto_promotion_possible")
        ),
        "gpu_artifact_unsafe_syms_gep_count": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_unsafe_syms_gep_count")
        ),
        "gpu_artifact_unsafe_syms_gep_covered_by_state_image": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_unsafe_syms_gep_covered_by_state_image")
        ),
        "gpu_artifact_root_offset_in_syms": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_root_offset_in_syms")
        ),
        "gpu_artifact_residual_std_tree_detected": (
            _mapping(sidecar_executable_preflight).get("gpu_artifact_residual_std_tree_detected")
        ),
        "design_specific_sidecar_executable_present": (
            _mapping(sidecar_executable_review).get("design_specific_sidecar_executable_present") is True
        ),
        "cpu_reference_observables_ready": cpu_reference_ready,
        "cpu_reference": {
            "status": cpu_reference_report.get("status"),
            "rtlmeter_cycles": cpu_reference_report.get("rtlmeter_cycles"),
            "stdout_test_passed": cpu_reference_report.get("stdout_test_passed"),
            "execute_elapsed_s": _mapping(cpu_reference_report.get("metrics")).get("execute_elapsed_s"),
        }
        if isinstance(cpu_reference_report, Mapping)
        else None,
        "state_image_loaded": state_image_report is not None and state_image_artifact is not None,
        "state_image_kind": f"{design.lower().replace('-', '_')}_extracted_preload_state_image",
        "sidecar_bridge_preflight_ready": True,
        "sidecar_bridge_invoked": _mapping(bounded_execution_report).get("sidecar_bridge_invoked") is True,
        "sidecar_observables_ready": _mapping(bounded_execution_report).get("sidecar_observables_ready") is True,
        "run_vl_hybrid_stage_trace": _mapping(bounded_execution_report).get("run_vl_hybrid_stage_trace"),
        "ptxas_probe": {
            "status": ptxas_probe_report.get("status"),
            "timeout_s": ptxas_probe_report.get("timeout_s"),
            "elapsed_wall": ptxas_probe_report.get("elapsed_wall"),
            "max_resident_set_kb": ptxas_probe_report.get("max_resident_set_kb"),
            "cubin_exists": ptxas_probe_report.get("cubin_exists"),
            "ptx_bytes": ptxas_probe_report.get("ptx_bytes"),
            "ptx_line_count": ptxas_probe_report.get("ptx_line_count"),
        }
        if isinstance(ptxas_probe_report, Mapping)
        else None,
        "entry_pruned_module_probe": {
            "ptxas_status": _mapping(entry_pruned_probe_report.get("ptxas_probe")).get("status"),
            "bridge_status": (
                "illegal_memory_access_at_first_step_sync"
                if (
                    entry_pruned_probe_report.get("schema_role") == "veer_eh_sidecar_bridge_execution"
                    and entry_pruned_probe_report.get("status") == "gpu_launch_failed"
                    and entry_pruned_probe_report.get("gpu_module_override")
                    and entry_pruned_probe_report.get("run_vl_hybrid_sync_each_step") is True
                    and _mapping(entry_pruned_probe_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
                    == "before_first_step_sync"
                )
                else
                "illegal_memory_access_after_entry_pruned_cubin_launch_loop"
                if (
                    entry_pruned_probe_report.get("schema_role") == "veer_eh_sidecar_bridge_execution"
                    and entry_pruned_probe_report.get("status") == "gpu_launch_failed"
                    and entry_pruned_probe_report.get("gpu_module_override")
                    and any(
                        "CUDA error 700" in str(line)
                        for line in (
                            entry_pruned_probe_report.get("run_vl_hybrid_stderr_tail")
                            if isinstance(entry_pruned_probe_report.get("run_vl_hybrid_stderr_tail"), Sequence)
                            and not isinstance(entry_pruned_probe_report.get("run_vl_hybrid_stderr_tail"), str)
                            else []
                        )
                    )
                )
                else _mapping(entry_pruned_probe_report.get("bridge_probe")).get("status")
            ),
            "eval_only_status": (
                _mapping(entry_pruned_eval_only_raw_probe).get("status")
                or _mapping(entry_pruned_probe_report.get("eval_only_probe")).get("status")
            ),
            "eval_only_last_stage": _mapping(entry_pruned_eval_only_raw_probe).get("last_stage"),
            "eval_only_report": _mapping(entry_pruned_eval_only_raw_probe).get("stderr_report"),
            "eval_only_variant_probes": entry_pruned_eval_only_variant_raw_probes,
            "host_cleanup_eval_only_probe": eh2_host_cleanup_eval_only_probe,
            "host_cleanup_v2_eval_only_probe": eh2_host_cleanup_v2_eval_only_probe,
            "return_before_eval_probe": eh2_return_before_eval_probe,
            "return_before_eval_call_probe": eh2_return_before_eval_call_probe,
            "eval_return_before_phase_act_probe": eh2_eval_return_before_phase_act_probe,
            "eval_return_after_one_phase_act_probe": eh2_eval_return_after_one_phase_act_probe,
            "eval_phase_act_return_after_triggers_probe": eh2_eval_phase_act_return_after_triggers_probe,
            "eval_phase_act_return_after_orinto_probe": eh2_eval_phase_act_return_after_orinto_probe,
            "trigger_orinto_return_before_first_ix_probe": eh2_trigger_orinto_return_before_first_ix_probe,
            "trigger_orinto_return_before_first_ix_stack64k_probe": (
                eh2_trigger_orinto_return_before_first_ix_stack64k_probe
            ),
            "inline_orinto_return_after_probe": eh2_inline_orinto_return_after_probe,
            "inline_orinto_noop_return_after_probe": eh2_inline_orinto_noop_return_after_probe,
            "inline_orinto_after_dst_load_probe": eh2_inline_orinto_after_dst_load_probe,
            "inline_orinto_after_src_load_probe": eh2_inline_orinto_after_src_load_probe,
            "inline_orinto_before_store_probe": eh2_inline_orinto_before_store_probe,
            "inline_orinto_store_u64_src_probe": eh2_inline_orinto_store_u64_src_probe,
            "inline_orinto_store_u32_dst_probe": eh2_inline_orinto_store_u32_dst_probe,
            "inline_orinto_store_u8_dst_probe": eh2_inline_orinto_store_u8_dst_probe,
            "inline_orinto_store_u64_root_base_probe": eh2_inline_orinto_store_u64_root_base_probe,
            "entry_store_nba_trigger_return_probe": eh2_entry_store_nba_trigger_return_probe,
            "inline_orinto_return_after_padded2m_probe": eh2_inline_orinto_return_after_padded2m_probe,
            "inline_orinto_return_after_maxr128_probe": eh2_inline_orinto_return_after_maxr128_probe,
            "store_vnba_before_triggers_probe": eh2_store_vnba_before_triggers_probe,
            "store_vnba_after_triggers_direct_root_probe": (
                eh2_store_vnba_after_triggers_direct_root_probe
            ),
            "store_next472416_after_triggers_probe": eh2_store_next472416_after_triggers_probe,
            "inline_orinto_store_vnba_cvta_global_probe": eh2_inline_orinto_store_vnba_cvta_global_probe,
            "minimal_store_vnba_probe": eh2_minimal_store_vnba_probe,
            "std_ref_get_canonical_eval_only_probe": eh2_std_ref_get_canonical_eval_only_probe,
            "std_ref_get_canonical_eval_return_before_phase_act_probe": (
                eh2_eval_return_before_phase_act_std_ref_probe
            ),
            "std_ref_get_canonical_eval_return_after_one_phase_act_probe": (
                eh2_eval_return_after_one_phase_act_std_ref_probe
            ),
            "std_ref_get_canonical_phase_act_return_after_orinto_ret0_probe": (
                eh2_phase_act_return_after_orinto_ret0_std_ref_probe
            ),
            "std_ref_get_canonical_phase_act_return_after_anyset_ret0_probe": (
                eh2_phase_act_return_after_anyset_ret0_std_ref_probe
            ),
            "std_ref_get_canonical_phase_act_return_after_timing_resume_ret0_probe": (
                eh2_phase_act_return_after_timing_resume_ret0_std_ref_probe
            ),
            "std_ref_get_canonical_trigger_orinto_return_before_loop_probe": (
                eh2_trigger_orinto_return_before_loop_std_ref_probe
            ),
            "std_ref_get_canonical_trigger_orinto_return_after_dst_load_probe": (
                eh2_trigger_orinto_return_after_dst_load_std_ref_probe
            ),
            "std_ref_get_canonical_trigger_orinto_return_after_src_load_probe": (
                eh2_trigger_orinto_return_after_src_load_std_ref_probe
            ),
            "std_ref_get_canonical_trigger_orinto_return_before_store_probe": (
                eh2_trigger_orinto_return_before_store_std_ref_probe
            ),
            "std_ref_get_canonical_trigger_orinto_return_after_store_probe": (
                eh2_trigger_orinto_return_after_store_std_ref_probe
            ),
            "vlunpacked_lm1_canonical_eval_only_probe": eh2_vlunpacked_lm1_canonical_eval_only_probe,
            "vlunpacked_lm1_phase_act_return_before_orinto_probe": (
                eh2_vlunpacked_lm1_phase_act_return_before_orinto_probe
            ),
            "vlunpacked_lm1_trigger_orinto_return_immediate_probe": (
                eh2_vlunpacked_lm1_trigger_orinto_return_immediate_probe
            ),
            "vlunpacked_lm1_orinto_rewrite_eval_only_probe": (
                eh2_vlunpacked_lm1_orinto_rewrite_eval_only_probe
            ),
            "orinto_store_skip_eval_only_probe": eh2_orinto_store_skip_eval_only_probe,
            "orinto_store_zero_eval_only_probe": eh2_orinto_store_zero_eval_only_probe,
            "orinto_store_dst_eval_only_probe": eh2_orinto_store_dst_eval_only_probe,
            "skip_store_return_before_anyset_probe": eh2_skip_store_return_before_anyset_probe,
            "skip_store_return_after_anyset_probe": eh2_skip_store_return_after_anyset_probe,
            "skip_store_return_after_timing_resume_probe": eh2_skip_store_return_after_timing_resume_probe,
            "skip_store_return_after_eval_act_probe": eh2_skip_store_return_after_eval_act_probe,
            "eval_act_return_after_callseq_probes": eh2_eval_act_return_after_callseq_probes,
            "dec_cam0_return_after_param_probe": eh2_dec_cam0_return_after_param_probe,
            "dec_cam0_return_after_callseq_15707_probe": eh2_dec_cam0_return_after_callseq_15707_probe,
            "dec_cam0_minimal_body_ret_probe": eh2_dec_cam0_minimal_body_ret_probe,
            "eval_act_skip_callseq_952_return_after_953_probe": (
                eh2_eval_act_skip_callseq_952_return_after_953_probe
            ),
            "eval_act_skip_callseq_952_953_return_after_954_probe": (
                eh2_eval_act_skip_callseq_952_953_return_after_954_probe
            ),
            "eval_act_skip_callseq_952_953_954_return_after_954_probe": (
                eh2_eval_act_skip_callseq_952_953_954_return_after_954_probe
            ),
            "vlwide_pointer_conversion_canonical_eval_only_probe": (
                eh2_vlwide_pointer_conversion_canonical_probe
            ),
            "vlwide_kernel_return_before_eval_call_probe": (
                eh2_vlwide_kernel_return_before_eval_call_probe
            ),
            "vlwide_eval_before_phase_act_probe": eh2_vlwide_eval_before_phase_act_probe,
            "vlwide_phase_act_after_callseq_5472_probe": (
                eh2_vlwide_phase_act_after_callseq_5472_probe
            ),
            "vlwide_phase_act_before_trigger_merge_store_probe": (
                eh2_vlwide_phase_act_before_trigger_merge_store_probe
            ),
            "vlwide_phase_act_after_trigger_merge_store_probe": (
                eh2_vlwide_phase_act_after_trigger_merge_store_probe
            ),
            "vlwide_phase_act_skip_trigger_merge_store_probe": (
                eh2_vlwide_phase_act_skip_trigger_merge_store_probe
            ),
            "vlwide_phase_act_store_one_eval_return_after_phase_act_probe": (
                eh2_vlwide_phase_act_store_one_eval_return_after_phase_act_probe
            ),
            "vlwide_phase_act_store_one_nba_before_eval_nba_probe": (
                eh2_vlwide_phase_act_store_one_nba_before_eval_nba_probe
            ),
            "vlwide_phase_act_store_one_nba_after_eval_nba_probe": (
                eh2_vlwide_phase_act_store_one_nba_after_eval_nba_probe
            ),
            "static_ptx_runtime_residue_probe": entry_pruned_static_residue_probe,
            "padded_storage_probe_status": _mapping(
                entry_pruned_probe_report.get("eval_only_padded_storage_probe")
            ).get("status"),
            "padded_storage_bytes": _mapping(
                entry_pruned_probe_report.get("eval_only_padded_storage_probe")
            ).get("padded_storage_bytes"),
            "static_ptx_residue_probe_status": _mapping(
                entry_pruned_probe_report.get("eval_only_static_ptx_residue_probe")
            ).get("status"),
            "static_ptx_residue_symbol_count": _mapping(
                entry_pruned_probe_report.get("eval_only_static_ptx_residue_probe")
            ).get("residual_symbol_count"),
            "static_ptx_residue_unsupported_runtime": _mapping(
                entry_pruned_probe_report.get("eval_only_static_ptx_residue_probe")
            ).get("unsupported_device_runtime_residue"),
            "std_allocator_allocate_returns_null": _mapping(
                entry_pruned_probe_report.get("eval_only_static_ptx_residue_probe")
            ).get("std_allocator_allocate_returns_null"),
            "region_counter_global_init_status": _mapping(
                entry_pruned_probe_report.get("eval_only_region_counter_global_init_probe")
            ).get("status"),
            "stack_limit_probe_status": _mapping(entry_pruned_probe_report.get("stack_limit_probe")).get(
                "status"
            ),
            "bridge_last_stage": _mapping(_mapping(entry_pruned_probe_report.get("bridge_probe")).get("stage_trace")).get(
                "last_stage"
            ),
            "entry_pruned_sidecar_status": entry_pruned_probe_report.get("status"),
            "entry_pruned_sidecar_last_stage": _mapping(
                entry_pruned_probe_report.get("run_vl_hybrid_stage_trace")
            ).get("last_stage"),
            "entry_pruned_sidecar_returncode": entry_pruned_probe_report.get("run_vl_hybrid_returncode"),
            "entry_pruned_sidecar_module_override": entry_pruned_probe_report.get("gpu_module_override"),
            "entry_pruned_sidecar_sync_each_step": entry_pruned_probe_report.get("run_vl_hybrid_sync_each_step"),
            "entry_pruned_cubin_exists": entry_pruned_probe_report.get("entry_pruned_cubin_exists"),
            "entry_pruned_cubin_bytes": entry_pruned_probe_report.get("entry_pruned_cubin_bytes"),
            "entry_pruned_kept_entries": entry_pruned_probe_report.get("entry_pruned_kept_entries"),
            "host_io_stub_eval_only_status": _mapping(
                entry_pruned_probe_report.get("host_io_stub_eval_only_probe")
            ).get("status"),
            "host_io_stub_cubin_bytes": _mapping(
                entry_pruned_probe_report.get("host_io_stub_eval_only_probe")
            ).get("cubin_bytes"),
            "host_io_stub_ptxas_o0_elapsed_wall_s": _mapping(
                entry_pruned_probe_report.get("host_io_stub_eval_only_probe")
            ).get("ptxas_o0_elapsed_wall_s"),
            "host_io_stub_last_stage": _mapping(
                entry_pruned_probe_report.get("host_io_stub_eval_only_probe")
            ).get("stage_trace_last_stage"),
            "host_io_stub_num_regs": _mapping(
                _mapping(entry_pruned_probe_report.get("host_io_stub_eval_only_probe")).get("kernel_attrs")
            ).get("num_regs"),
            "host_io_stub_local_size_bytes": _mapping(
                _mapping(entry_pruned_probe_report.get("host_io_stub_eval_only_probe")).get("kernel_attrs")
            ).get("local_size_bytes"),
            "host_io_stub_padded_storage_probe_status": _mapping(
                _mapping(entry_pruned_probe_report.get("host_io_stub_eval_only_probe")).get(
                    "storage2m_padded_init_probe"
                )
            ).get("status"),
            "host_io_stub_padded_storage_bytes": _mapping(
                _mapping(entry_pruned_probe_report.get("host_io_stub_eval_only_probe")).get(
                    "storage2m_padded_init_probe"
                )
            ).get("padded_storage_bytes"),
            "host_io_stub_compute_sanitizer_status": _mapping(
                _mapping(entry_pruned_probe_report.get("host_io_stub_eval_only_probe")).get(
                    "compute_sanitizer_probe"
                )
            ).get("status"),
        }
        if isinstance(entry_pruned_probe_report, Mapping)
        else None,
        "sidecar_execution_claimed": False,
        "comparison": {
            "status": "not_run",
            "normalized_stdout_match": None,
            "cycle_count_match": None,
            "cpu_cycles": None,
            "gpu_cycles": None,
        },
        "missing_build_context": list(dict.fromkeys(missing_context)),
        "next_required_boundary": (
            "fix EH2 entry-pruned CUBIN launch-loop illegal memory access before bridge comparison"
            if (
                entry_pruned_probe_report is not None
                and entry_pruned_probe_report.get("schema_role") == "veer_eh_sidecar_bridge_execution"
                and entry_pruned_probe_report.get("status") == "gpu_launch_failed"
                and entry_pruned_probe_report.get("gpu_module_override")
                and not (
                    entry_pruned_probe_report.get("run_vl_hybrid_sync_each_step") is True
                    and _mapping(entry_pruned_probe_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
                    == "before_first_step_sync"
                )
            )
            else
            "localize EH2 post-VlWide eval_phase__nba eval_nba CUDA700 before bridge comparison"
            if (
                _mapping(eh2_vlwide_phase_act_store_one_nba_before_eval_nba_probe).get("status")
                == "vlwide_phase_act_store_one_nba_before_eval_nba_passed"
                and _mapping(eh2_vlwide_phase_act_store_one_nba_after_eval_nba_probe).get("status")
                == "vlwide_phase_act_store_one_nba_after_eval_nba_still_illegal_memory_access"
            )
            else
            "fix EH2 post-VlWide phase_act trigger merge store CUDA700 before bridge comparison"
            if (
                _mapping(eh2_vlwide_phase_act_before_trigger_merge_store_probe).get("status")
                == "vlwide_phase_act_before_trigger_merge_store_passed"
                and _mapping(eh2_vlwide_phase_act_after_trigger_merge_store_probe).get("status")
                == "vlwide_phase_act_after_trigger_merge_store_still_illegal_memory_access"
            )
            else
            "fix EH2 eval_act submodule act call boundary CUDA700 before bridge comparison"
            if (
                _mapping(eh2_dec_cam0_minimal_body_ret_probe).get("status")
                == "dec_cam0_minimal_body_ret_still_illegal_memory_access"
                and _mapping(eh2_eval_act_skip_callseq_952_953_954_return_after_954_probe).get("status")
                == "eval_act_skip_callseq_952_953_954_return_after_954_passed"
            )
            else
            "fix EH2 eval_act dec_cam[0] act_sequent CUDA700 before bridge comparison"
            if (
                _mapping(eh2_eval_act_return_after_callseq_probes.get("951")).get("status")
                == "eval_act_return_after_callseq_951_passed"
                and _mapping(eh2_eval_act_return_after_callseq_probes.get("952")).get("status")
                == "eval_act_return_after_callseq_952_still_illegal_memory_access"
            )
            else
            "localize EH2 post-VlUnpacked-Lm1 eval_act CUDA700 after timing_resume"
            if (
                _mapping(eh2_skip_store_return_after_eval_act_probe).get("status")
                == "skip_store_return_after_eval_act_still_illegal_memory_access"
            )
            else
            "fix EH2 post-VlUnpacked-Lm1 inlined trigger_orInto store CUDA700 before bridge comparison"
            if (
                _mapping(eh2_vlunpacked_lm1_orinto_rewrite_eval_only_probe).get("status")
                == "vlunpacked_lm1_orinto_rewrite_eval_only_still_illegal_memory_access"
            )
            else
            "inline or eliminate EH2 post-VlUnpacked-Lm1 trigger_orInto helper call CUDA700 before bridge comparison"
            if (
                _mapping(eh2_vlunpacked_lm1_trigger_orinto_return_immediate_probe).get("status")
                == "vlunpacked_lm1_trigger_orinto_return_immediate_still_illegal_memory_access"
            )
            else
            "localize EH2 post-VlUnpacked-Lm1 canonical eval CUDA700 before bridge comparison"
            if (
                _mapping(eh2_vlunpacked_lm1_canonical_eval_only_probe).get("status")
                == "vlunpacked_lm1_canonical_eval_only_still_illegal_memory_access"
            )
            else
            "fix EH2 post-std-ref-get-canonical trigger_orInto dst-store CUDA700 before bridge comparison"
            if (
                _mapping(eh2_trigger_orinto_return_after_store_std_ref_probe).get("status")
                == "std_ref_get_canonical_trigger_orinto_return_after_store_still_illegal_memory_access"
            )
            else
            "localize EH2 post-std-ref-get-canonical trigger_orInto CUDA700 before bridge comparison"
            if (
                _mapping(eh2_phase_act_return_after_orinto_ret0_std_ref_probe).get("status")
                == "std_ref_get_canonical_phase_act_return_after_orinto_ret0_still_illegal_memory_access"
            )
            else
            "localize EH2 post-std-ref-get-canonical eval CUDA700 before bridge comparison"
            if (
                _mapping(eh2_std_ref_get_canonical_eval_only_probe).get("status")
                == "std_ref_get_canonical_eval_only_still_illegal_memory_access"
            )
            else
            "fix EH2 first eval launch illegal memory access before bridge comparison"
            if (
                entry_pruned_probe_report is not None
                and entry_pruned_probe_report.get("schema_role") == "veer_eh_sidecar_bridge_execution"
                and entry_pruned_probe_report.get("status") == "gpu_launch_failed"
                and entry_pruned_probe_report.get("gpu_module_override")
                and entry_pruned_probe_report.get("run_vl_hybrid_sync_each_step") is True
                and _mapping(entry_pruned_probe_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
                == "before_first_step_sync"
            )
            else
            "fix EH1 eval-only kernel illegal memory access after entry-pruned module load"
            if (
                _mapping(_mapping(entry_pruned_probe_report).get("ptxas_probe")).get("status") == "passed"
                and _mapping(_mapping(entry_pruned_probe_report).get("bridge_probe")).get("status")
                == "illegal_memory_access_at_first_eval_launch"
                and _mapping(_mapping(entry_pruned_probe_report).get("eval_only_probe")).get("status")
                == "illegal_memory_access_at_first_eval_launch"
            )
            else
            "fix EH1 eval kernel illegal memory access after entry-pruned module load"
            if (
                _mapping(_mapping(entry_pruned_probe_report).get("ptxas_probe")).get("status") == "passed"
                and _mapping(_mapping(entry_pruned_probe_report).get("bridge_probe")).get("status")
                == "illegal_memory_access_at_first_eval_launch"
            )
            else
            "reduce EH1 generated PTX/module compile cost before bridge comparison"
            if (
                bounded_execution_report is not None
                and bounded_execution_report.get("status") == "gpu_launch_timeout"
                and _mapping(bounded_execution_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
                == "before_cuModuleLoad"
                and _mapping(ptxas_probe_report).get("status") == "ptxas_timeout"
            )
            else
            "clear EH sidecar PTX module load/JIT timeout before stdout/cycles comparison"
            if (
                bounded_execution_report is not None
                and bounded_execution_report.get("status") == "gpu_launch_timeout"
                and _mapping(bounded_execution_report.get("run_vl_hybrid_stage_trace")).get("last_stage")
                == "before_cuModuleLoad"
            )
            else
            "clear EH sidecar GPU launch timeout before stdout/cycles comparison"
            if (
                bounded_execution_report is not None
                and bounded_execution_report.get("status") == "gpu_launch_timeout"
            )
            else
            "clear EH sidecar executable preflight blockers before bridge timing"
            if (
                _mapping(sidecar_executable_review).get("sidecar_executable_reviewed_for_target") is True
                and sidecar_executable_preflight is not None
                and sidecar_executable_preflight.get("sidecar_executable_ready_for_bridge") is not True
            )
            else "execute EH sidecar bridge comparison before timing"
            if (
                _mapping(sidecar_executable_review).get("sidecar_executable_reviewed_for_target") is True
            )
            else "review EH-specific sidecar executable and run stdout/cycles bridge before timing"
        ),
        "fail_closed": True,
        "cpu_as_gpu_fallback": False,
        "gpu_execution_claimed": False,
        "timing_measured": False,
        "speedup_claimed": False,
        "non_claims": [
            "bridge preflight is not sidecar execution",
            "no stdout/cycles comparison has run for this EH target",
            "no timing, speedup, or usefulness claim is made",
        ],
    }


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _layout_entry_summary(entry: Mapping[str, object]) -> dict[str, object]:
    return {
        "name": entry.get("name"),
        "offset": entry.get("offset"),
        "size": entry.get("size"),
        "decl_type": entry.get("decl_type"),
    }


def _matching_layout_entries(layout: list[Mapping[str, object]], marker: str) -> list[dict[str, object]]:
    exact = [entry for entry in layout if entry.get("name") == marker]
    substring = [entry for entry in layout if marker in str(entry.get("name", ""))]
    preferred = exact or [
        entry
        for entry in substring
        if "__Vtrigprevexpr" not in str(entry.get("name", ""))
    ] or substring
    return [_layout_entry_summary(entry) for entry in preferred[:5]]


def _probe_root_offsets(root_header_path: Path, marker_groups: Mapping[str, list[str]]) -> dict[str, Any]:
    if not root_header_path.is_file():
        return {
            "root_offset_probe_performed": False,
            "root_offset_probe_error": "root_header_missing",
            "root_offset_marker_hits": {},
            "mapped_marker_offset_group_count": 0,
        }
    try:
        from compare_vl_hybrid_root_layout import probe_root_layout

        layout = probe_root_layout(root_header_path.parent)
    except Exception as exc:  # pragma: no cover - exercised by fixture headers without Verilator includes.
        return {
            "root_offset_probe_performed": False,
            "root_offset_probe_error": type(exc).__name__,
            "root_offset_marker_hits": {},
            "mapped_marker_offset_group_count": 0,
        }
    offset_hits: dict[str, dict[str, object]] = {}
    for group, markers in marker_groups.items():
        group_hits = {
            marker: _matching_layout_entries(layout, marker)
            for marker in markers
        }
        offset_hits[group] = {
            "markers": group_hits,
            "observed": any(bool(entries) for entries in group_hits.values()),
        }
    return {
        "root_offset_probe_performed": True,
        "root_offset_probe_error": None,
        "root_layout_entry_count": len(layout),
        "root_offset_marker_hits": offset_hits,
        "mapped_marker_offset_group_count": sum(
            1 for hit in offset_hits.values() if hit.get("observed") is True
        ),
    }


def _root_header_marker_probe(repo_root: Path, design: str, configuration: str, pc_candidates: list[str]) -> dict[str, Any]:
    root_obj_dir_candidates = _root_obj_dir_candidates_for(design, configuration)
    selected_variant, obj_dir = root_obj_dir_candidates[-1]
    for variant, candidate in root_obj_dir_candidates:
        if (repo_root / candidate / "Vsim___024root.h").is_file():
            selected_variant = variant
            obj_dir = candidate
            break
    root_header = obj_dir / "Vsim___024root.h"
    root_header_path = repo_root / root_header
    text = _read_text(root_header_path)
    marker_groups = {
        "control_scalars": [
            "tb_top__DOT__core_clk",
            "tb_top__DOT__rst_l",
            "tb_top__DOT__porst_l",
        ],
        "pc_candidates": pc_candidates + ["dec_i0_pc_d", "dec_tlu_i0_pc_e4", "ifu_i0_pcdata"],
        "cycle_counters": [
            "mcyclel",
            "minstretl",
            "tb_top__DOT__mcycle",
            "tb_top__DOT__minstret",
        ],
        "mailbox_observables": ["mailbox_write", "WriteData"],
        "gpr_observables": ["__DOT__gpr", "gpr_banks", "arf"],
    }
    offset_probe = _probe_root_offsets(root_header_path, marker_groups)
    marker_hits: dict[str, dict[str, Any]] = {}
    for group, markers in marker_groups.items():
        group_hits = {marker: len(re.findall(re.escape(marker), text)) for marker in markers}
        marker_hits[group] = {
            "markers": group_hits,
            "observed": any(count > 0 for count in group_hits.values()),
        }
    missing_marker_groups = [
        group for group, hit in marker_hits.items() if hit.get("observed") is not True
    ]
    observed_marker_group_count = sum(1 for hit in marker_hits.values() if hit.get("observed") is True)
    return {
        "root_obj_dir_variant": selected_variant,
        "root_obj_dir_candidates": [
            {"variant": variant, "path": path.as_posix()}
            for variant, path in root_obj_dir_candidates
        ],
        "root_obj_dir": obj_dir.as_posix(),
        "root_header": root_header.as_posix(),
        "root_header_observed": root_header_path.is_file(),
        "root_layout_probe_performed": root_header_path.is_file(),
        "root_layout_probe_kind": "generated_verilator_root_header_marker_scan" if root_header_path.is_file() else None,
        "root_marker_hits": marker_hits if root_header_path.is_file() else {},
        "observed_marker_group_count": observed_marker_group_count if root_header_path.is_file() else 0,
        "missing_marker_groups": missing_marker_groups if root_header_path.is_file() else list(marker_groups),
        **offset_probe,
        "root_field_offsets_reviewed": False,
        "state_layout_ready": False,
    }


def _design_row(repo_root: Path, target: Mapping[str, Any]) -> dict[str, Any]:
    design = str(target["design"])
    configuration = str(target["configuration"])
    test = str(target["test"])
    design_root = repo_root / "third_party" / "rtlmeter" / "designs" / design
    descriptor_path = design_root / "descriptor.yaml"
    descriptor = _load_yaml(descriptor_path)
    descriptor_info = _descriptor_paths(descriptor, configuration=configuration, test=test)
    source_paths = [design_root / item for item in descriptor_info["verilog_sources"]]
    include_paths = [
        design_root / item
        for item in descriptor_info["base_includes"] + descriptor_info["configuration_includes"]
    ]
    program_paths = [design_root / item for item in descriptor_info["program_files"]]
    tb_top = design_root / "src" / "tb_top.sv"
    tb_text = _read_text(tb_top)
    source_prefix = str(target["expected_source_prefix"])
    prefixed_sources = [
        path.name
        for path in source_paths
        if source_prefix and path.name.startswith(source_prefix)
    ]
    unprefixed_core_sources = [
        path.name
        for path in source_paths
        if not source_prefix
        and path.name
        in {
            "veer.sv",
            "veer_wrapper.sv",
            "dec.sv",
            "ifu.sv",
            "lsu.sv",
            "exu.sv",
            "mem.sv",
        }
    ]
    program_sha = _sha256(program_paths[0]) if program_paths else None
    evidence_ready = {
        "descriptor": descriptor_path.is_file(),
        "all_sources_exist": all(path.is_file() for path in source_paths),
        "all_includes_exist": all(path.is_file() for path in include_paths),
        "program_hex_exists": bool(program_paths) and all(path.is_file() for path in program_paths),
        "tb_top_exists": tb_top.is_file(),
        "clock_matches_el2_surface": descriptor_info["main_clock"] == "tb_top.core_clk",
        "top_module_matches_el2_surface": descriptor_info["top_module"] == "tb_top",
        "readmemh_program_hex": '$readmemh("program.hex"' in tb_text,
        "mailbox_write_present": "mailbox_write" in tb_text,
        "test_passed_mailbox_present": "TEST PASSED" in tb_text or "8'h1" in tb_text,
    }
    direct_reuse_blockers: list[str] = []
    if not target["el2_direct_reuse"]:
        direct_reuse_blockers.extend(
            [
                "el2_authority_target_name_is_fixed",
                "el2_state_layout_and_root_symbol_paths_are_fixed",
                "el2_sidecar_executable_program_sha256_is_fixed",
            ]
        )
    if program_sha != EL2_PROGRAM_SHA256:
        direct_reuse_blockers.append("hello_program_sha256_differs_from_el2")
    if str(target["expected_wrapper_instance"]) != "rvtop_wrapper":
        direct_reuse_blockers.append("wrapper_instance_differs_from_el2_rvtop_wrapper")
    if not all(evidence_ready.values()):
        direct_reuse_blockers.append("descriptor_or_testbench_evidence_incomplete")
    missing_surface: list[str] = []
    if design == "VeeR-EL2":
        reports = {
            "authority": EL2_AUTHORITY,
            "state_layout_report": EL2_STATE_LAYOUT_REPORT,
            "state_image_report": EL2_STATE_IMAGE_REPORT,
            "sidecar_bridge_report": EL2_BRIDGE_REPORT,
            "timing_report": EL2_TIMING_REPORT,
        }
    else:
        stem = design.lower().replace("-", "_")
        reports = {
            "authority": _authority_path_for(design, configuration, test),
            "state_layout_report": _state_layout_report_path_for(design),
            "root_offset_review_report": _root_offset_review_report_path_for(design),
            "state_image_report": _state_image_report_path_for(design),
            "sidecar_executable_review_report": _sidecar_executable_review_report_path_for(design),
            "sidecar_bridge_report": _sidecar_bridge_report_path_for(design),
            "timing_report": Path(f"reports/rtlmeter_{stem}_timing_pair_cycle_fused_nstates16.json"),
        }
    for key, path in reports.items():
        if not (repo_root / path).is_file():
            missing_surface.append(key)
    sidecar_executable_review = _load_json(
        repo_root / _sidecar_executable_review_report_path_for(design)
    ) if design != "VeeR-EL2" else None
    sidecar_executable_reviewed_for_target = (
        _mapping(sidecar_executable_review).get("sidecar_executable_reviewed_for_target") is True
    )
    ready_to_port = (
        all(evidence_ready.values())
        and descriptor_info["top_module"] == "tb_top"
        and descriptor_info["main_clock"] == "tb_top.core_clk"
    )
    measured = design == "VeeR-EL2" and not missing_surface and _load_json(repo_root / EL2_TIMING_REPORT) is not None
    if measured:
        status = "measured_el2_reference_surface"
        next_action = "keep_as_reference_and_do_not_reuse_for_eh_without_new_authority"
    elif (
        ready_to_port
        and "authority" not in missing_surface
        and "state_layout_report" not in missing_surface
        and "state_image_report" not in missing_surface
        and "sidecar_bridge_report" not in missing_surface
    ):
        status = "sidecar_bridge_preflight_surface_missing"
        if sidecar_executable_review is not None and not sidecar_executable_reviewed_for_target:
            next_action = "implement_design_specific_sidecar_executable_review_offsets_execute_bridge_and_timing"
        else:
            next_action = "execute_bridge_comparison_and_timing"
    elif (
        ready_to_port
        and "authority" not in missing_surface
        and "state_layout_report" not in missing_surface
        and "state_image_report" not in missing_surface
    ):
        status = "state_image_materialized_surface_missing"
        next_action = "create_sidecar_bridge_and_timing"
    elif ready_to_port and "authority" not in missing_surface and "state_layout_report" not in missing_surface:
        status = "state_layout_preflight_ready_surface_missing"
        next_action = "create_state_image_materializer_sidecar_bridge_and_timing"
    elif ready_to_port and "authority" not in missing_surface:
        status = "authority_ready_surface_missing"
        next_action = "create_state_layout_report_state_image_materializer_sidecar_bridge_and_timing"
    elif ready_to_port:
        status = "portable_descriptor_ready_surface_missing"
        next_action = "create_design_specific_authority_state_layout_state_image_bridge_and_timing"
    else:
        status = "descriptor_or_testbench_incomplete"
        next_action = "fix_descriptor_or_testbench_evidence_before_hybrid_surface"
    return {
        "case": target["case"],
        "design": design,
        "configuration": configuration,
        "test": test,
        "status": status,
        "descriptor": {
            "path": _display_path(descriptor_path, repo_root=repo_root),
            "exists": descriptor_path.is_file(),
            "top_module": descriptor_info["top_module"],
            "main_clock": descriptor_info["main_clock"],
            "configuration_exists": descriptor_info["configuration_exists"],
            "test_exists": descriptor_info["test_exists"],
            "configuration_test_exists": descriptor_info["configuration_test_exists"],
            "source_count": len(source_paths),
            "include_count_total": len(include_paths),
            "program_files": [_display_path(path, repo_root=repo_root) for path in program_paths],
        },
        "testbench_surface": {
            "tb_top": _display_path(tb_top, repo_root=repo_root),
            "expected_wrapper_instance": target["expected_wrapper_instance"],
            "expected_core_symbol_fragment": target["expected_core_symbol_fragment"],
            "program_sha256": program_sha,
            "program_sha256_matches_el2": program_sha == EL2_PROGRAM_SHA256,
            "prefixed_core_source_count": len(prefixed_sources),
            "unprefixed_core_source_count": len(unprefixed_core_sources),
        },
        "evidence_ready": evidence_ready,
        "missing_surface": missing_surface,
        "direct_el2_reuse_blockers": direct_reuse_blockers,
        "ready_to_port_from_descriptor": ready_to_port,
        "hybrid_measured": measured,
        "report_paths": {key: path.as_posix() for key, path in reports.items()},
        "next_action": next_action,
    }


def build_audit(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    rows = [_design_row(root, target) for target in TARGETS]
    missing_designs = [row["design"] for row in rows if not row["hybrid_measured"]]
    portable_missing = [
        row["design"]
        for row in rows
        if row["ready_to_port_from_descriptor"] and not row["hybrid_measured"]
    ]
    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "incomplete" if missing_designs else "complete",
        "objective_scope": "VeeR EH1/EH2/EL2 hybrid measurement surface",
        "rows": rows,
        "summary": {
            "target_count": len(rows),
            "hybrid_measured_count": sum(1 for row in rows if row["hybrid_measured"]),
            "missing_hybrid_surface_designs": missing_designs,
            "portable_descriptor_ready_missing_surface_designs": portable_missing,
            "el2_reference_measured": any(
                row["design"] == "VeeR-EL2" and row["hybrid_measured"] for row in rows
            ),
            "eh1_ready_to_port_from_descriptor": any(
                row["design"] == "VeeR-EH1" and row["ready_to_port_from_descriptor"] for row in rows
            ),
            "eh2_ready_to_port_from_descriptor": any(
                row["design"] == "VeeR-EH2" and row["ready_to_port_from_descriptor"] for row in rows
            ),
            "eh1_hybrid_measured": any(row["design"] == "VeeR-EH1" and row["hybrid_measured"] for row in rows),
            "eh2_hybrid_measured": any(row["design"] == "VeeR-EH2" and row["hybrid_measured"] for row in rows),
        },
        "recommended_order": [
            "reuse_descriptor/testbench commonality only as a porting guide",
            "create EH1/EH2-specific state-image materializers and bridges before sidecar timing",
            "do not reuse the EL2 executable directly because target, hierarchy, and hello program hashes differ",
        ],
        "non_claims": [
            "not_eh1_or_eh2_hybrid_measurement",
            "not_el2_executable_port",
            "not_gpu_speedup_claim",
        ],
    }


def write_authorities(repo_root: Path) -> list[str]:
    written: list[str] = []
    for target in TARGETS:
        if target.get("el2_direct_reuse") is True:
            continue
        path = repo_root / _authority_path_for(
            str(target["design"]),
            str(target["configuration"]),
            str(target["test"]),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(build_authority_payload(repo_root, target), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(_display_path(path, repo_root=repo_root))
    return written


def write_state_layout_preflights(repo_root: Path) -> list[str]:
    written: list[str] = []
    for target in TARGETS:
        if target.get("el2_direct_reuse") is True:
            continue
        path = repo_root / _state_layout_report_path_for(str(target["design"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(build_state_layout_preflight(repo_root, target), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(_display_path(path, repo_root=repo_root))
    return written


def write_state_images(repo_root: Path) -> list[str]:
    written: list[str] = []
    for target in TARGETS:
        if target.get("el2_direct_reuse") is True:
            continue
        report, state_image = build_state_image_payload(repo_root, target)
        report_path = repo_root / _state_image_report_path_for(str(target["design"]))
        artifact_path = repo_root / _state_image_artifact_path_for(str(target["design"]))
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(state_image, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(_display_path(report_path, repo_root=repo_root))
    return written


def write_root_offset_reviews(repo_root: Path) -> list[str]:
    written: list[str] = []
    for target in TARGETS:
        if target.get("el2_direct_reuse") is True:
            continue
        path = repo_root / _root_offset_review_report_path_for(str(target["design"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(build_root_offset_review_payload(repo_root, target), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(_display_path(path, repo_root=repo_root))
    return written


def write_sidecar_executable_reviews(repo_root: Path) -> list[str]:
    written: list[str] = []
    for target in TARGETS:
        if target.get("el2_direct_reuse") is True:
            continue
        path = repo_root / _sidecar_executable_review_report_path_for(str(target["design"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(build_sidecar_executable_review_payload(repo_root, target), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(_display_path(path, repo_root=repo_root))
    return written


def write_sidecar_bridge_preflights(repo_root: Path) -> list[str]:
    written: list[str] = []
    for target in TARGETS:
        if target.get("el2_direct_reuse") is True:
            continue
        path = repo_root / _sidecar_bridge_report_path_for(str(target["design"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(build_sidecar_bridge_payload(repo_root, target), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(_display_path(path, repo_root=repo_root))
    return written


def _markdown_table(report: Mapping[str, Any]) -> str:
    headers = ["Design", "Status", "Portable descriptor", "Missing surface", "Direct EL2 reuse blockers", "Next action"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in report.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("design")),
                    str(row.get("status")),
                    str(row.get("ready_to_port_from_descriptor")),
                    ", ".join(str(item) for item in row.get("missing_surface", [])),
                    ", ".join(str(item) for item in row.get("direct_el2_reuse_blockers", [])[:3]) or "none",
                    str(row.get("next_action")),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-out", default=DEFAULT_REPORT)
    parser.add_argument(
        "--write-authorities",
        action="store_true",
        help="Write EH1/EH2 fail-closed authority registry entries derived from descriptors",
    )
    parser.add_argument(
        "--write-state-layout-preflight",
        action="store_true",
        help="Write EH1/EH2 fail-closed state-layout preflight reports",
    )
    parser.add_argument(
        "--write-state-images",
        action="store_true",
        help="Write EH1/EH2 fail-closed state-image materializer reports and artifacts",
    )
    parser.add_argument(
        "--write-root-offset-review",
        action="store_true",
        help="Write EH1/EH2 fail-closed root offset candidate review reports",
    )
    parser.add_argument(
        "--write-sidecar-executable-review",
        action="store_true",
        help="Write EH1/EH2 fail-closed sidecar executable reuse review reports",
    )
    parser.add_argument(
        "--write-sidecar-bridge-preflight",
        action="store_true",
        help="Write EH1/EH2 fail-closed sidecar bridge preflight reports",
    )
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.repo_root)
    written_authorities: list[str] = []
    if args.write_authorities:
        written_authorities = write_authorities(root)
    written_state_layout_preflights: list[str] = []
    if args.write_state_layout_preflight:
        written_state_layout_preflights = write_state_layout_preflights(root)
    written_state_images: list[str] = []
    if args.write_state_images:
        written_state_images = write_state_images(root)
    written_root_offset_reviews: list[str] = []
    if args.write_root_offset_review:
        written_root_offset_reviews = write_root_offset_reviews(root)
    written_sidecar_executable_reviews: list[str] = []
    if args.write_sidecar_executable_review:
        written_sidecar_executable_reviews = write_sidecar_executable_reviews(root)
    written_sidecar_bridge_preflights: list[str] = []
    if args.write_sidecar_bridge_preflight:
        written_sidecar_bridge_preflights = write_sidecar_bridge_preflights(root)
    report = build_audit(root)
    if written_authorities:
        report["written_authorities"] = written_authorities
    if written_state_layout_preflights:
        report["written_state_layout_preflights"] = written_state_layout_preflights
    if written_state_images:
        report["written_state_images"] = written_state_images
    if written_root_offset_reviews:
        report["written_root_offset_reviews"] = written_root_offset_reviews
    if written_sidecar_executable_reviews:
        report["written_sidecar_executable_reviews"] = written_sidecar_executable_reviews
    if written_sidecar_bridge_preflights:
        report["written_sidecar_bridge_preflights"] = written_sidecar_bridge_preflights
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
