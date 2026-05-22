from __future__ import annotations


def ordered_normalized_groups(groups: dict[tuple[str, int], dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        groups.values(),
        key=lambda entry: (
            int(entry["first_candidate_state_index"]),
            int(entry["field_offset"]),
            str(entry["field_name"]),
        ),
    )


def normalized_field_result(
    *,
    ordered: list[dict[str, object]],
    role_summary: dict[str, dict[str, int]],
    functional_fields: set[tuple[str, int]],
    functional_bytes: int,
    per_candidate_functional_bytes: dict[int, int],
    mismatching_candidate_states: set[int],
    limit: int,
) -> dict[str, object]:
    return {
        "passed": functional_bytes == 0,
        "blocked_reason": None,
        "mismatching_candidate_state_count": len(mismatching_candidate_states),
        "mismatch_field_count": len(ordered),
        "mismatch_byte_count": sum(int(entry["mismatch_bytes"]) for entry in ordered),
        "functional_non_internal_mismatch_field_count": len(functional_fields),
        "functional_non_internal_mismatch_byte_count": functional_bytes,
        "max_functional_non_internal_mismatch_byte_count": max(per_candidate_functional_bytes.values(), default=0),
        "mismatch_role_summary": role_summary,
        "mismatch_fields": ordered[:limit],
    }
