"""Map RTLMeter Verilator metadata into non-executing sidecar contract metadata."""

from __future__ import annotations

from collections.abc import Mapping

try:
    from .rtlmeter_verilator_command_capture import SURFACE as COMMAND_CAPTURE_SURFACE
    from .rtlmeter_verilator_command_capture import capture_rtlmeter_verilator_command
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from rtlmeter_verilator_command_capture import SURFACE as COMMAND_CAPTURE_SURFACE
    from rtlmeter_verilator_command_capture import capture_rtlmeter_verilator_command


SURFACE = "rtlmeter_sidecar_contract_mapping"
JSON_FLOW_ROLE = "debug_inspection"
STATUS_FRONTEND_METADATA_MAPPED = "frontend_metadata_mapped_sidecar_unresolved"

FRONTEND_OWNED_FIELDS = (
    "top_module",
    "main_clock",
    "prefix",
    "verilator_command_argv",
    "filelist_entries",
    "verilog_source_files",
    "verilog_include_files",
    "verilog_defines",
    "cpp_source_files",
    "cpp_include_files",
    "cpp_defines",
    "verilator_args",
    "extra_args",
)
SIDECAR_OWNED_RESPONSIBILITIES = (
    "source closure status",
    "GPU build artifacts",
    "coverage-output selection",
    "state file paths",
    "compare labels",
    "generated compare reports",
    "CPU reference execution",
    "hybrid sidecar execution",
    "timing and speedup evidence",
    "automatic GPU allocation",
)
FORBIDDEN_PREPOPULATED_SIDECAR_FIELDS = frozenset(
    {
        "source_closure_status",
        "gpu_artifacts",
        "coverage_output_target",
        "state_paths",
        "compare_labels",
        "generated_reports",
        "cpu_reference_execution",
        "hybrid_sidecar_execution",
        "timing",
        "speedup",
        "automatic_gpu_allocation",
        "handoff_contract",
        "operator_plan",
    }
)


class RtlmeterSidecarContractMappingError(ValueError):
    """Raised when RTLMeter metadata cannot be mapped to sidecar contract metadata."""


def _require(capture: Mapping[str, object], field: str) -> object:
    if field not in capture:
        raise RtlmeterSidecarContractMappingError(f"RTLMeter capture is missing required field {field!r}")
    return capture[field]


def _copy_list(capture: Mapping[str, object], field: str) -> list[object]:
    value = _require(capture, field)
    if not isinstance(value, list):
        raise RtlmeterSidecarContractMappingError(f"RTLMeter capture field {field!r} must be a list")
    return list(value)


def _copy_dict(capture: Mapping[str, object], field: str) -> dict[str, object]:
    value = _require(capture, field)
    if not isinstance(value, Mapping):
        raise RtlmeterSidecarContractMappingError(f"RTLMeter capture field {field!r} must be a mapping")
    return {str(key): item for key, item in value.items()}


def map_rtlmeter_capture_to_sidecar_contract(capture: Mapping[str, object]) -> dict[str, object]:
    """Return sidecar contract metadata for an RTLMeter command capture."""

    if capture.get("surface") != COMMAND_CAPTURE_SURFACE:
        raise RtlmeterSidecarContractMappingError("RTLMeter capture surface is not command capture")
    forbidden = sorted(FORBIDDEN_PREPOPULATED_SIDECAR_FIELDS.intersection(capture))
    if forbidden:
        raise RtlmeterSidecarContractMappingError(
            f"RTLMeter capture already contains sidecar-owned fields: {forbidden}"
        )

    frontend_metadata = {
        "top_module": _require(capture, "top_module"),
        "main_clock": _require(capture, "main_clock"),
        "prefix": _require(capture, "prefix"),
        "verilator_command_argv": _copy_list(capture, "verilator_command_argv"),
        "filelist_entries": _copy_list(capture, "filelist_entries"),
        "verilog_source_files": _copy_list(capture, "verilog_source_files"),
        "verilog_include_files": _copy_list(capture, "verilog_include_files"),
        "verilog_defines": _copy_dict(capture, "verilog_defines"),
        "cpp_source_files": _copy_list(capture, "cpp_source_files"),
        "cpp_include_files": _copy_list(capture, "cpp_include_files"),
        "cpp_defines": _copy_dict(capture, "cpp_defines"),
        "verilator_args": _copy_list(capture, "verilator_args"),
        "extra_args": _copy_list(capture, "extra_args"),
    }

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "json_flow_role": JSON_FLOW_ROLE,
        "runtime_abi": False,
        "execution_authority": False,
        "status": STATUS_FRONTEND_METADATA_MAPPED,
        "source_surface": capture.get("surface"),
        "case": capture.get("case"),
        "compile_case": capture.get("compile_case"),
        "frontend": "rtlmeter/verilator",
        "requires_rtlmeter_launch_template": False,
        "frontend_owned_fields": list(FRONTEND_OWNED_FIELDS),
        "frontend_owned_build_metadata": frontend_metadata,
        "sidecar_owned_resolution_status": "unresolved_by_rtlmeter_contract_mapping",
        "sidecar_owned_responsibilities": list(SIDECAR_OWNED_RESPONSIBILITIES),
        "correctness_policy_ref": "coverage_output_equivalence",
        "correctness_policy_ref_status": "reference_only_not_compare_evidence",
        "non_claims": [
            "RTLMeter sidecar contract mapping is structured metadata, not the runtime ABI",
            "RTLMeter sidecar contract mapping does not infer source closure",
            "RTLMeter sidecar contract mapping does not build GPU artifacts, execute sidecar stages, compare outputs, or measure timing",
            "RTLMeter sidecar contract mapping does not require users to select repo-specific launch templates",
        ],
    }


def map_rtlmeter_case_to_sidecar_contract(
    case: str,
    *,
    compile_args: tuple[str, ...] = (),
    rtlmeter_root: str | None = None,
) -> dict[str, object]:
    """Capture a RTLMeter case and map it to non-executing sidecar contract metadata."""

    return map_rtlmeter_capture_to_sidecar_contract(
        capture_rtlmeter_verilator_command(case, rtlmeter_root=rtlmeter_root, extra_args=compile_args)
    )
