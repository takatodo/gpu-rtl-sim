"""Field-level mismatch grouping for normalized final-state comparison."""

from __future__ import annotations

from compare_vl_hybrid_layout import classify_field_role
from compare_vl_hybrid_normalized_group_records import (
    field_mismatch_offsets,
    new_normalized_field_group,
    record_normalized_field_group,
)
from compare_vl_hybrid_normalized_field_result import (
    normalized_field_result,
    ordered_normalized_groups,
)


def record_normalized_role_summary(
    *,
    role_summary: dict[str, dict[str, int]],
    functional_fields: set[tuple[str, int]],
    per_candidate_functional_bytes: dict[int, int],
    mismatching_candidate_states: set[int],
    role: str,
    key: tuple[str, int],
    candidate_state_index: int,
    mismatch_bytes: int,
) -> int:
    role_bucket = role_summary.setdefault(role, {"field_count": 0, "mismatch_bytes": 0})
    role_bucket["mismatch_bytes"] += mismatch_bytes
    mismatching_candidate_states.add(int(candidate_state_index))
    if role == "verilator_internal":
        return 0
    functional_fields.add(key)
    per_candidate_functional_bytes[int(candidate_state_index)] = (
        per_candidate_functional_bytes.get(int(candidate_state_index), 0) + mismatch_bytes
    )
    return mismatch_bytes


def normalized_field_group_for_mismatch(
    *,
    groups: dict[tuple[str, int], dict[str, object]],
    key: tuple[str, int],
    field: dict[str, int | str],
    field_offset: int,
    field_size: int,
    role: str,
    reference_state_index: int,
    candidate_state_index: int,
    reference_slice: bytes,
    candidate_slice: bytes,
    mismatch_byte_offsets: list[int],
) -> dict[str, object]:
    group = groups.get(key)
    if group is not None:
        return group
    group = new_normalized_field_group(
        field=field,
        field_offset=field_offset,
        field_size=field_size,
        role=role,
        reference_state_index=reference_state_index,
        candidate_state_index=candidate_state_index,
        reference_slice=reference_slice,
        candidate_slice=candidate_slice,
        mismatch_byte_offsets=mismatch_byte_offsets,
    )
    groups[key] = group
    return group


def record_normalized_field_mismatch(
    *,
    groups: dict[tuple[str, int], dict[str, object]],
    role_summary: dict[str, dict[str, int]],
    functional_fields: set[tuple[str, int]],
    per_candidate_functional_bytes: dict[int, int],
    mismatching_candidate_states: set[int],
    field: dict[str, int | str],
    field_offset: int,
    field_size: int,
    reference_state_index: int,
    candidate_state_index: int,
    reference_slice: bytes,
    candidate_slice: bytes,
) -> int:
    role = classify_field_role(str(field["name"]))
    mismatch_byte_offsets = field_mismatch_offsets(reference_slice, candidate_slice)
    mismatch_bytes = len(mismatch_byte_offsets) + abs(len(reference_slice) - len(candidate_slice))
    if mismatch_bytes == 0:
        return 0
    key = (str(field["name"]), field_offset)
    group = normalized_field_group_for_mismatch(
        groups=groups,
        key=key,
        field=field,
        field_offset=field_offset,
        field_size=field_size,
        role=role,
        reference_state_index=reference_state_index,
        candidate_state_index=candidate_state_index,
        reference_slice=reference_slice,
        candidate_slice=candidate_slice,
        mismatch_byte_offsets=mismatch_byte_offsets,
    )
    record_normalized_field_group(
        group=group,
        reference_state_index=reference_state_index,
        candidate_state_index=candidate_state_index,
        mismatch_bytes=mismatch_bytes,
        mismatch_byte_offsets=mismatch_byte_offsets,
    )
    return record_normalized_role_summary(
        role_summary=role_summary,
        functional_fields=functional_fields,
        per_candidate_functional_bytes=per_candidate_functional_bytes,
        mismatching_candidate_states=mismatching_candidate_states,
        role=role,
        key=key,
        candidate_state_index=candidate_state_index,
        mismatch_bytes=mismatch_bytes,
    )
