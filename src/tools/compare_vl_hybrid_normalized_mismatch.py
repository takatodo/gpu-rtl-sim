"""Mismatch aggregation for normalized final-state comparison."""

from __future__ import annotations

from compare_vl_hybrid_normalized_field_groups import (
    normalized_field_result,
    ordered_normalized_groups,
    record_normalized_field_mismatch,
)


def _record_normalized_pair_mismatches(
    *,
    reference: bytes,
    candidate: bytes,
    storage_size: int,
    fields: list[dict[str, int | str]],
    reference_state_index: int,
    candidate_state_index: int,
    groups: dict[tuple[str, int], dict[str, object]],
    role_summary: dict[str, dict[str, int]],
    functional_fields: set[tuple[str, int]],
    per_candidate_functional_bytes: dict[int, int],
    mismatching_candidate_states: set[int],
) -> int:
    reference_base = int(reference_state_index) * storage_size
    candidate_base = int(candidate_state_index) * storage_size
    functional_bytes = 0
    for field in fields:
        field_offset = int(field["offset"])
        field_size = int(field["size"])
        reference_slice = reference[reference_base + field_offset : reference_base + field_offset + field_size]
        candidate_slice = candidate[candidate_base + field_offset : candidate_base + field_offset + field_size]
        if reference_slice == candidate_slice:
            continue
        functional_bytes += record_normalized_field_mismatch(
            groups=groups,
            role_summary=role_summary,
            functional_fields=functional_fields,
            per_candidate_functional_bytes=per_candidate_functional_bytes,
            mismatching_candidate_states=mismatching_candidate_states,
            field=field,
            field_offset=field_offset,
            field_size=field_size,
            reference_state_index=reference_state_index,
            candidate_state_index=candidate_state_index,
            reference_slice=reference_slice,
            candidate_slice=candidate_slice,
        )
    return functional_bytes


def compare_normalized_final_state_fields(
    *,
    reference: bytes,
    candidate: bytes,
    storage_size: int,
    fields: list[dict[str, int | str]],
    pairs: list[tuple[int, int]],
    limit: int,
) -> dict[str, object]:
    groups: dict[tuple[str, int], dict[str, object]] = {}
    role_summary: dict[str, dict[str, int]] = {}
    functional_fields: set[tuple[str, int]] = set()
    functional_bytes = 0
    per_candidate_functional_bytes: dict[int, int] = {}
    mismatching_candidate_states: set[int] = set()
    for reference_state_index, candidate_state_index in pairs:
        functional_bytes += _record_normalized_pair_mismatches(
            reference=reference,
            candidate=candidate,
            storage_size=storage_size,
            fields=fields,
            reference_state_index=reference_state_index,
            candidate_state_index=candidate_state_index,
            groups=groups,
            role_summary=role_summary,
            functional_fields=functional_fields,
            per_candidate_functional_bytes=per_candidate_functional_bytes,
            mismatching_candidate_states=mismatching_candidate_states,
        )

    for group in groups.values():
        role = str(group["field_role"])
        role_summary.setdefault(role, {"field_count": 0, "mismatch_bytes": 0})
        role_summary[role]["field_count"] += 1

    return normalized_field_result(
        ordered=ordered_normalized_groups(groups),
        role_summary=role_summary,
        functional_fields=functional_fields,
        functional_bytes=functional_bytes,
        per_candidate_functional_bytes=per_candidate_functional_bytes,
        mismatching_candidate_states=mismatching_candidate_states,
        limit=limit,
    )
