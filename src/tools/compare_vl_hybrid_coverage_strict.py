from __future__ import annotations


def field_mismatch_offsets(reference_slice: bytes, candidate_slice: bytes) -> list[int]:
    return [
        idx
        for idx, (reference_byte, candidate_byte) in enumerate(zip(reference_slice, candidate_slice))
        if reference_byte != candidate_byte
    ]


def strict_word_mismatch(
    *,
    word_name: str,
    offset: int,
    size: int,
    reference_state_index: int,
    candidate_state_index: int,
    reference_slice: bytes,
    candidate_slice: bytes,
) -> dict[str, object] | None:
    if reference_slice == candidate_slice:
        return None
    mismatch_byte_offsets = field_mismatch_offsets(reference_slice, candidate_slice)
    first_field_byte_offset = mismatch_byte_offsets[0] if mismatch_byte_offsets else 0
    return {
        "field_name": word_name,
        "field_offset": offset,
        "field_size": size,
        "reference_state_index": reference_state_index,
        "candidate_state_index": candidate_state_index,
        "mismatch_bytes": len(mismatch_byte_offsets) + abs(len(reference_slice) - len(candidate_slice)),
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
    }


def compare_strict_output_words(
    *,
    reference: bytes,
    candidate: bytes,
    storage_size: int,
    strict_words: list[str],
    layout_by_name: dict[str, dict[str, int | str]],
    pairs: list[tuple[int, int]],
    limit: int,
) -> dict[str, object]:
    mismatches: list[dict[str, object]] = []
    compared_byte_count = 0
    compared_word_count = 0
    for reference_state_index, candidate_state_index in pairs:
        reference_state_index = int(reference_state_index)
        candidate_state_index = int(candidate_state_index)
        reference_base = reference_state_index * storage_size
        candidate_base = candidate_state_index * storage_size
        for word_name in strict_words:
            entry = layout_by_name[word_name]
            offset = int(entry["offset"])
            size = int(entry["size"])
            reference_slice = reference[reference_base + offset : reference_base + offset + size]
            candidate_slice = candidate[candidate_base + offset : candidate_base + offset + size]
            compared_byte_count += size
            compared_word_count += 1
            mismatch = strict_word_mismatch(
                word_name=word_name,
                offset=offset,
                size=size,
                reference_state_index=reference_state_index,
                candidate_state_index=candidate_state_index,
                reference_slice=reference_slice,
                candidate_slice=candidate_slice,
            )
            if mismatch is not None:
                mismatches.append(mismatch)
    return {
        "compared_word_count": compared_word_count,
        "compared_byte_count": compared_byte_count,
        "mismatches": mismatches[:limit],
        "mismatch_count": len(mismatches),
        "passed": not mismatches,
        "blocked_reason": None,
    }
