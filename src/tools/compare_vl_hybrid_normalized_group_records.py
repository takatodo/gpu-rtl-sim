"""Record helpers for normalized field mismatch groups."""

from __future__ import annotations


def field_mismatch_offsets(reference_slice: bytes, candidate_slice: bytes) -> list[int]:
    return [
        idx
        for idx, (reference_byte, candidate_byte) in enumerate(zip(reference_slice, candidate_slice))
        if reference_byte != candidate_byte
    ]


def new_normalized_field_group(
    *,
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
    first_field_byte_offset = mismatch_byte_offsets[0] if mismatch_byte_offsets else 0
    return {
        "field_name": str(field["name"]),
        "field_role": role,
        "field_offset": field_offset,
        "field_size": field_size,
        "decl_type": str(field.get("decl_type", "")),
        "mismatch_bytes": 0,
        "first_reference_state_index": reference_state_index,
        "first_candidate_state_index": candidate_state_index,
        "first_field_byte_offset": first_field_byte_offset,
        "reference_first_byte": (
            reference_slice[first_field_byte_offset]
            if first_field_byte_offset < len(reference_slice)
            else None
        ),
        "candidate_first_byte": (
            candidate_slice[first_field_byte_offset]
            if first_field_byte_offset < len(candidate_slice)
            else None
        ),
        "field_byte_offsets": [],
        "reference_state_indices": [],
        "candidate_state_indices": [],
    }


def record_normalized_field_group(
    *,
    group: dict[str, object],
    reference_state_index: int,
    candidate_state_index: int,
    mismatch_bytes: int,
    mismatch_byte_offsets: list[int],
) -> None:
    group["mismatch_bytes"] = int(group["mismatch_bytes"]) + mismatch_bytes
    field_byte_offsets = group["field_byte_offsets"]
    reference_state_indices = group["reference_state_indices"]
    candidate_state_indices = group["candidate_state_indices"]
    for field_byte_offset in mismatch_byte_offsets[:8]:
        if field_byte_offset not in field_byte_offsets:
            field_byte_offsets.append(field_byte_offset)
    if reference_state_index not in reference_state_indices:
        reference_state_indices.append(reference_state_index)
    if candidate_state_index not in candidate_state_indices:
        candidate_state_indices.append(candidate_state_index)
