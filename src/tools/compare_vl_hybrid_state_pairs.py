"""State-dump pairing policy for hybrid comparison reports."""

from __future__ import annotations


def state_pair_plan(
    reference_len: int, candidate_len: int, storage_size: int
) -> dict[str, object]:
    if storage_size <= 0:
        return {
            "compatible": False,
            "reason": "storage_size_must_be_positive",
            "pairs": [],
            "comparison_mode": "invalid_storage_size",
            "reference_state_count": None,
            "candidate_state_count": None,
        }
    if reference_len % storage_size != 0 or candidate_len % storage_size != 0:
        return {
            "compatible": False,
            "reason": "state_dump_size_is_not_a_multiple_of_storage_size",
            "pairs": [],
            "comparison_mode": "incompatible_state_dump_sizes",
            "reference_state_count": None,
            "candidate_state_count": None,
        }

    reference_state_count = reference_len // storage_size
    candidate_state_count = candidate_len // storage_size
    if reference_state_count == candidate_state_count:
        pairs = [(idx, idx) for idx in range(reference_state_count)]
        comparison_mode = "corresponding_state_chunks"
    elif reference_state_count == 1:
        pairs = [(0, idx) for idx in range(candidate_state_count)]
        comparison_mode = "single_reference_state_against_candidate_chunks"
    elif candidate_state_count == 1:
        pairs = [(idx, 0) for idx in range(reference_state_count)]
        comparison_mode = "reference_chunks_against_single_candidate_state"
    else:
        return {
            "compatible": False,
            "reason": "reference_and_candidate_state_counts_are_incompatible",
            "pairs": [],
            "comparison_mode": "incompatible_state_counts",
            "reference_state_count": reference_state_count,
            "candidate_state_count": candidate_state_count,
        }

    return {
        "compatible": True,
        "reason": None,
        "pairs": pairs,
        "comparison_mode": comparison_mode,
        "reference_state_count": reference_state_count,
        "candidate_state_count": candidate_state_count,
    }
