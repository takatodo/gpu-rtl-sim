"""Parser-payload validation for the non-executing direct command fixture."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import NoReturn

try:
    from .verilator_native_option_parser_stub_fixture import (
        CORRECTNESS_POLICY,
        HANDOFF_FIELDS,
        SOURCE_BOUNDARY_STATUS,
        SURFACE,
    )
except ImportError:  # pragma: no cover - exercised when imported via sys.path.
    from verilator_native_option_parser_stub_fixture import (
        CORRECTNESS_POLICY,
        HANDOFF_FIELDS,
        SOURCE_BOUNDARY_STATUS,
        SURFACE,
    )


ACCELERATOR_MODE = "sidecar-gpu"
ERROR_CODE = "invalid_parser_payload"
LIST_STRING_FIELDS = (
    "ordinary_verilator_args",
    "source_files",
    "filelists",
    "defines",
    "include_dirs",
    "warning_flags",
)
NON_EMPTY_STRING_FIELDS = ("mdir", "top_module", "state_and_report_naming_rules")


ErrorFactory = Callable[[str, str], Exception]


def _reject(error_factory: ErrorFactory, message: str) -> NoReturn:
    raise error_factory(ERROR_CODE, message)


def _require_exact_keyset(parser_payload: Mapping[str, object], error_factory: ErrorFactory) -> None:
    required = set(HANDOFF_FIELDS)
    missing = [field for field in HANDOFF_FIELDS if field not in parser_payload]
    unknown = [key for key in parser_payload if key not in required]
    if missing or unknown:
        _reject(
            error_factory,
            "parser payload fields must match parser-stub handoff keyset; "
            f"missing={missing!r} unknown={[repr(key) for key in unknown]!r}",
        )
    for field in HANDOFF_FIELDS:
        if parser_payload.get(field) is None:
            _reject(error_factory, f"parser payload field {field!r} is required")


def _require_value(
    parser_payload: Mapping[str, object],
    field: str,
    expected: object,
    error_factory: ErrorFactory,
) -> None:
    value = parser_payload.get(field)
    if value != expected:
        _reject(error_factory, f"parser payload field {field!r} must be {expected!r}")


def _require_non_empty_string(
    parser_payload: Mapping[str, object], field: str, error_factory: ErrorFactory
) -> str:
    value = parser_payload.get(field)
    if type(value) is not str or not value.strip():
        _reject(error_factory, f"parser payload field {field!r} must be a non-empty string")
    return value


def _require_positive_int(
    parser_payload: Mapping[str, object], field: str, error_factory: ErrorFactory
) -> int:
    value = parser_payload.get(field)
    if type(value) is not int or value <= 0:
        _reject(error_factory, f"parser payload field {field!r} must be a positive integer")
    return value


def _require_list_of_strings(
    parser_payload: Mapping[str, object], field: str, error_factory: ErrorFactory
) -> list[str]:
    value = parser_payload.get(field)
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        _reject(error_factory, f"parser payload field {field!r} must be a list of strings")
    return list(value)


def _require_non_empty_string_list(
    parser_payload: Mapping[str, object], field: str, error_factory: ErrorFactory
) -> list[str]:
    values = _require_list_of_strings(parser_payload, field, error_factory)
    if not values:
        _reject(error_factory, f"parser payload field {field!r} must be a non-empty list of strings")
    return values


def _validate_identity(parser_payload: Mapping[str, object], error_factory: ErrorFactory) -> None:
    _require_value(parser_payload, "schema_version", 1, error_factory)
    _require_value(parser_payload, "surface", SURFACE, error_factory)
    _require_value(parser_payload, "accelerator_mode", ACCELERATOR_MODE, error_factory)
    _require_value(parser_payload, "correctness_policy", CORRECTNESS_POLICY, error_factory)
    _require_value(parser_payload, "source_boundary_status", SOURCE_BOUNDARY_STATUS, error_factory)


def validate_direct_command_parser_payload(
    parser_payload: Mapping[str, object], *, error_factory: ErrorFactory
) -> tuple[int, int, str, dict[str, object]]:
    """Validate parser-stub handoff payload and return normalized fixture inputs."""

    _require_exact_keyset(parser_payload, error_factory)
    _validate_identity(parser_payload, error_factory)
    state_count = _require_positive_int(parser_payload, "state_count", error_factory)
    step_count = _require_positive_int(parser_payload, "step_count", error_factory)
    expected_shape = f"{state_count}x{step_count}"
    if parser_payload.get("shape") != expected_shape:
        _reject(error_factory, f"parser payload shape must be {expected_shape!r}")

    preserved: dict[str, object] = {}
    for field in NON_EMPTY_STRING_FIELDS:
        preserved[field] = _require_non_empty_string(parser_payload, field, error_factory)
    for field in LIST_STRING_FIELDS:
        preserved[field] = _require_list_of_strings(parser_payload, field, error_factory)
    _require_non_empty_string_list(parser_payload, "non_claims", error_factory)
    return state_count, step_count, expected_shape, preserved
