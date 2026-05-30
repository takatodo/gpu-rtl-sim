"""Non-executing native-parser adapter handoff fixture."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

try:
    from .verilator_native_option_parser_stub_fixture import (
        CORRECTNESS_POLICY,
        SOURCE_BOUNDARY_STATUS,
        parse_verilator_native_option_stub,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from verilator_native_option_parser_stub_fixture import (
        CORRECTNESS_POLICY,
        SOURCE_BOUNDARY_STATUS,
        parse_verilator_native_option_stub,
    )


ADAPTER_SURFACE = "native_verilator_parser_sidecar_handoff_fixture"
CORRECTNESS_POLICY_REFERENCE_STATUS = "adapter_default_reference_only_not_parser_populated_compare_evidence"
SIDECAR_OWNED_RESOLUTION_STATUS = "unresolved_by_native_parser_adapter_fixture"

ADAPTER_PAYLOAD_FIELDS = tuple(
    "schema_version surface adapter_source_surface accelerator_mode state_count step_count shape "
    "ordinary_verilator_args mdir top_module source_files filelists defines include_dirs warning_flags "
    "source_boundary_status state_and_report_naming_rules correctness_policy_ref "
    "correctness_policy_reference_status sidecar_owned_resolution_status unresolved_sidecar_responsibilities "
    "non_claims".split()
)

FORBIDDEN_RESOLVED_SIDECAR_FIELDS = frozenset(
    {
        "state_authority",
        "state_files",
        "generated_reports",
        "compare",
        "acceptance_policy",
        "compare_labels",
        "coverage_output_target",
        "coverage_output_gate_or_manifest_ref",
        "host_probe_build_metadata_ref",
        "init_state_path",
        "init_state_path_or_rule",
        "reference_dump_path",
        "reference_dump_path_or_rule",
        "candidate_dump_path",
        "candidate_dump_path_or_rule",
        "compare_report_path",
        "compare_report_path_or_rule",
        "verilator_command",
        "verilator_command_argv",
    }
)

UNRESOLVED_SIDECAR_RESPONSIBILITIES = (
    "source closure",
    "coverage output target",
    "coverage manifest or gate reference",
    "host-probe metadata",
    "state file paths",
    "report paths",
    "compare labels",
    "runtime handoff",
    "timing evidence",
    "automatic GPU allocation",
)


class NativeParserSidecarHandoffError(ValueError):
    """Raised when parser-stub output cannot become an adapter payload."""


def _require(parser_handoff: Mapping[str, object], field: str) -> object:
    if field not in parser_handoff:
        raise NativeParserSidecarHandoffError(f"parser handoff is missing required field {field!r}")
    return parser_handoff[field]


def _copy_list(parser_handoff: Mapping[str, object], field: str) -> list[object]:
    value = _require(parser_handoff, field)
    if not isinstance(value, list):
        raise NativeParserSidecarHandoffError(f"parser handoff field {field!r} must be a list")
    return list(value)


def build_native_parser_sidecar_handoff(parser_handoff: Mapping[str, object]) -> dict[str, object]:
    """Build the reviewed non-executing adapter payload from parser-stub output."""

    if FORBIDDEN_RESOLVED_SIDECAR_FIELDS.intersection(parser_handoff):
        forbidden = sorted(FORBIDDEN_RESOLVED_SIDECAR_FIELDS.intersection(parser_handoff))
        raise NativeParserSidecarHandoffError(f"parser handoff already contains sidecar-owned fields: {forbidden}")

    payload = {
        "schema_version": 1,
        "surface": ADAPTER_SURFACE,
        "adapter_source_surface": _require(parser_handoff, "surface"),
        "accelerator_mode": _require(parser_handoff, "accelerator_mode"),
        "state_count": _require(parser_handoff, "state_count"),
        "step_count": _require(parser_handoff, "step_count"),
        "shape": _require(parser_handoff, "shape"),
        "ordinary_verilator_args": _copy_list(parser_handoff, "ordinary_verilator_args"),
        "mdir": parser_handoff.get("mdir"),
        "top_module": parser_handoff.get("top_module"),
        "source_files": _copy_list(parser_handoff, "source_files"),
        "filelists": _copy_list(parser_handoff, "filelists"),
        "defines": _copy_list(parser_handoff, "defines"),
        "include_dirs": _copy_list(parser_handoff, "include_dirs"),
        "warning_flags": _copy_list(parser_handoff, "warning_flags"),
        "source_boundary_status": parser_handoff.get("source_boundary_status", SOURCE_BOUNDARY_STATUS),
        "state_and_report_naming_rules": _require(parser_handoff, "state_and_report_naming_rules"),
        "correctness_policy_ref": parser_handoff.get("correctness_policy", CORRECTNESS_POLICY),
        "correctness_policy_reference_status": CORRECTNESS_POLICY_REFERENCE_STATUS,
        "sidecar_owned_resolution_status": SIDECAR_OWNED_RESOLUTION_STATUS,
        "unresolved_sidecar_responsibilities": list(UNRESOLVED_SIDECAR_RESPONSIBILITIES),
        "non_claims": list(parser_handoff.get("non_claims", ()))
        + [
            "adapter fixture does not populate sidecar-owned state files, reports, compare labels, coverage targets, manifest refs, or host-probe metadata",
            "adapter fixture keeps coverage_output_equivalence as a later sidecar policy reference only",
            "adapter fixture does not execute RTL simulation, compare outputs, measure timing, or change runtime ABI",
        ],
    }
    assert tuple(payload.keys()) == ADAPTER_PAYLOAD_FIELDS
    return payload


def native_parser_values_to_sidecar_adapter_payload(parser_values: Mapping[str, object]) -> dict[str, object]:
    """Name the parser-values to adapter-payload boundary explicitly."""

    return build_native_parser_sidecar_handoff(parser_values)


def parse_verilator_native_option_sidecar_handoff(argv: Sequence[str]) -> dict[str, object]:
    """Parse future Verilator-style args and return the reviewed adapter payload."""

    return native_parser_values_to_sidecar_adapter_payload(parse_verilator_native_option_stub(argv))
