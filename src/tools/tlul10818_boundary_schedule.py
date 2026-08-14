"""Canonical TL-UL #10818 boundary sweep and patch lowering."""

from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Mapping, Sequence
from typing import Any


REQUEST_INTEGRITY_VALUES = ("valid", "malformed")
RUNNER_CONTROL_AXES = (
    {
        "name": "request_integrity",
        "kind": "categorical",
        "values": REQUEST_INTEGRITY_VALUES,
    },
    {
        "name": "backpressure_cycles",
        "kind": "ordered",
        "value_type": "nonnegative_integer",
        "values_owner": "external_experiment_contract",
    },
    {
        "name": "response_delay_cycles",
        "kind": "ordered",
        "value_type": "nonnegative_integer",
        "values_owner": "external_experiment_contract",
    },
)


def _nonnegative_cycle_count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _ordered_cycle_values(values: Sequence[int], name: str) -> list[int]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name} values must be a sequence of nonnegative integers")
    normalized = [_nonnegative_cycle_count(value, name) for value in values]
    if not normalized:
        raise ValueError(f"{name} values must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} values must be unique")
    if normalized != sorted(normalized):
        raise ValueError(f"{name} values must be strictly increasing")
    return normalized


def boundary_sweep_space(
    *,
    backpressure_cycles: Sequence[int],
    response_delay_cycles: Sequence[int],
) -> dict[str, Any]:
    backpressure_values = _ordered_cycle_values(backpressure_cycles, "backpressure_cycles")
    response_delay_values = _ordered_cycle_values(response_delay_cycles, "response_delay_cycles")
    return {
        "schema_version": 1,
        "surface": "rtl_boundary_sweep_space",
        "axes": [
            {
                "name": "request_integrity",
                "kind": "categorical",
                "values": list(REQUEST_INTEGRITY_VALUES),
                "adjacent_value_pairs": [["valid", "malformed"]],
            },
            {"name": "backpressure_cycles", "kind": "ordered", "values": backpressure_values},
            {"name": "response_delay_cycles", "kind": "ordered", "values": response_delay_values},
        ],
    }


def boundary_parameters(parameters: Mapping[str, Any]) -> tuple[str, int, int]:
    expected = {"request_integrity", "backpressure_cycles", "response_delay_cycles"}
    if set(parameters) != expected:
        raise ValueError(
            "boundary parameters must contain exactly request_integrity, "
            "backpressure_cycles, and response_delay_cycles"
        )
    request_integrity = parameters.get("request_integrity")
    if request_integrity not in REQUEST_INTEGRITY_VALUES:
        raise ValueError("request_integrity must be 'valid' or 'malformed'")
    return (
        str(request_integrity),
        _nonnegative_cycle_count(parameters.get("backpressure_cycles"), "backpressure_cycles"),
        _nonnegative_cycle_count(parameters.get("response_delay_cycles"), "response_delay_cycles"),
    )


def boundary_action_name(parameters: Mapping[str, Any]) -> str:
    request_integrity, backpressure_cycles, response_delay_cycles = boundary_parameters(parameters)
    return f"{request_integrity}_bp{backpressure_cycles}_rd{response_delay_cycles}"


def boundary_action_mapping(
    *,
    backpressure_cycles: Sequence[int],
    response_delay_cycles: Sequence[int],
) -> list[dict[str, Any]]:
    sweep_space = boundary_sweep_space(
        backpressure_cycles=backpressure_cycles,
        response_delay_cycles=response_delay_cycles,
    )
    axes = sweep_space["axes"]
    rows: list[dict[str, Any]] = []
    for combination in itertools.product(*(axis["values"] for axis in axes)):
        parameters = dict(zip((axis["name"] for axis in axes), combination))
        rows.append({"action": boundary_action_name(parameters), "parameters": parameters})
    return rows


def boundary_contract_projection(
    *,
    backpressure_cycles: Sequence[int],
    response_delay_cycles: Sequence[int],
    sweep_enumerator: Any,
) -> dict[str, Any]:
    sweep_space = boundary_sweep_space(
        backpressure_cycles=backpressure_cycles,
        response_delay_cycles=response_delay_cycles,
    )
    enumeration = sweep_enumerator(sweep_space)
    if not isinstance(enumeration, Mapping):
        raise ValueError("sweep enumerator must return an object")
    digest = enumeration.get("sweep_space_sha256")
    points = enumeration.get("points")
    point_count = enumeration.get("point_count")
    if (
        enumeration.get("schema_version") != 1
        or enumeration.get("surface") != "rtl_boundary_sweep_enumeration"
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or isinstance(point_count, bool)
        or not isinstance(point_count, int)
        or not isinstance(points, list)
        or point_count != len(points)
    ):
        raise ValueError("sweep enumerator returned an invalid canonical enumeration")
    expected = {
        tuple(sorted(row["parameters"].items()))
        for row in boundary_action_mapping(
            backpressure_cycles=backpressure_cycles,
            response_delay_cycles=response_delay_cycles,
        )
    }
    rows: list[dict[str, Any]] = []
    seen_parameters: set[tuple[tuple[str, Any], ...]] = set()
    seen_actions: set[str] = set()
    for point in points:
        if not isinstance(point, Mapping) or set(point) != {"point_id", "parameters"}:
            raise ValueError("sweep enumeration point has an invalid shape")
        point_id = point.get("point_id")
        if not isinstance(point_id, str) or not point_id.startswith("point:v1:"):
            raise ValueError("sweep enumeration point ID is invalid")
        normalized = dict(zip(
            ("request_integrity", "backpressure_cycles", "response_delay_cycles"),
            boundary_parameters(point.get("parameters")),
        ))
        parameter_key = tuple(sorted(normalized.items()))
        action = boundary_action_name(normalized)
        if parameter_key in seen_parameters or action in seen_actions:
            raise ValueError("sweep enumeration contains a duplicate runner action")
        seen_parameters.add(parameter_key)
        seen_actions.add(action)
        rows.append({"point_id": point_id, "action": action, "parameters": normalized})
    if seen_parameters != expected:
        raise ValueError("sweep enumeration does not cover the runner finite grid")
    encoded = json.dumps(
        rows, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return {
        "sweep_space": sweep_space,
        "sweep_space_sha256": digest,
        "action_domain": rows,
        "action_domain_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _patch_line(offsets: dict[str, int], **values: int) -> str:
    return " ".join(f"{offsets[name]}:{value}" for name, value in values.items())


def boundary_patch_script(
    offsets: dict[str, int],
    *,
    request_integrity: str,
    backpressure_cycles: int,
    response_delay_cycles: int,
) -> str:
    if request_integrity not in {"valid", "malformed"}:
        raise ValueError("request_integrity must be 'valid' or 'malformed'")
    backpressure_cycles = _nonnegative_cycle_count(backpressure_cycles, "backpressure_cycles")
    response_delay_cycles = _nonnegative_cycle_count(response_delay_cycles, "response_delay_cycles")
    malformed = request_integrity == "malformed"
    active_response_delay = 0 if malformed else response_delay_cycles
    wait_cycles_before_completion = max(backpressure_cycles, active_response_delay)
    lines = [
        _patch_line(
            offsets,
            clk_i=0,
            rst_ni=0,
            start_i=0,
            malformed_i=int(malformed),
            d_backpressure_i=0,
            response_valid_i=0,
        ),
        _patch_line(offsets, clk_i=1),
        _patch_line(offsets, clk_i=0),
        _patch_line(offsets, rst_ni=1, start_i=1),
        _patch_line(offsets, clk_i=1),
        _patch_line(offsets, clk_i=0, start_i=0),
        _patch_line(offsets, clk_i=1),
    ]
    for wait_cycle in range(wait_cycles_before_completion + 1):
        lines.append(
            _patch_line(
                offsets,
                clk_i=0,
                d_backpressure_i=int(wait_cycle < backpressure_cycles),
                response_valid_i=int(wait_cycle >= active_response_delay),
            )
        )
        lines.append(_patch_line(offsets, clk_i=1))
    return "\n".join(lines) + "\n"


def boundary_patch_script_for_parameters(offsets: dict[str, int], parameters: Mapping[str, Any]) -> str:
    request_integrity, backpressure_cycles, response_delay_cycles = boundary_parameters(parameters)
    return boundary_patch_script(
        offsets,
        request_integrity=request_integrity,
        backpressure_cycles=backpressure_cycles,
        response_delay_cycles=response_delay_cycles,
    )
