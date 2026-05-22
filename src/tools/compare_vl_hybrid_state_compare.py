"""State-dump byte and layout comparison helpers."""

from __future__ import annotations

from pathlib import Path

from compare_vl_hybrid_layout import (
    annotate_state_offset,
    first_field_with_role,
    sha256_file,
    summarize_mismatch_fields,
)
from compare_vl_hybrid_normalized import build_normalized_final_state_policy_summary
from compare_vl_hybrid_policies import build_acceptance_candidates


def byte_mismatch_summary(single: bytes, split: bytes) -> tuple[int, int | None]:
    first_mismatch = None
    mismatch_count = 0
    for idx in range(min(len(single), len(split))):
        if single[idx] != split[idx]:
            mismatch_count += 1
            if first_mismatch is None:
                first_mismatch = idx
    mismatch_count += abs(len(single) - len(split))
    return mismatch_count, first_mismatch


def first_mismatch_payload(
    *,
    single: bytes,
    split: bytes,
    first_mismatch: int,
    storage_size: int,
    layout: list[dict[str, int | str]] | None,
) -> dict[str, object]:
    payload = {
        "global_offset": first_mismatch,
        "state_index": first_mismatch // storage_size if storage_size > 0 else None,
        "state_offset": first_mismatch % storage_size if storage_size > 0 else None,
        "single_byte": single[first_mismatch],
        "split_byte": split[first_mismatch],
    }
    if layout:
        annotation = annotate_state_offset(layout, payload["state_offset"])
        if annotation is not None:
            payload.update(annotation)
    return payload


def add_layout_mismatch_summary(
    *,
    payload: dict[str, object],
    single: bytes,
    split: bytes,
    storage_size: int,
    layout: list[dict[str, int | str]],
    mismatch_count: int,
) -> None:
    field_count, mismatch_fields, all_mismatch_fields, role_summary = summarize_mismatch_fields(
        single,
        split,
        storage_size=storage_size,
        layout=layout,
    )
    payload["mismatch_field_count"] = field_count
    payload["mismatch_fields"] = mismatch_fields
    payload["mismatch_role_summary"] = role_summary
    payload["acceptance_candidates"] = build_acceptance_candidates(
        match=payload["match"],
        mismatch_count=mismatch_count,
        role_summary=role_summary,
    )
    payload["normalized_final_state_policy"] = build_normalized_final_state_policy_summary(
        single,
        split,
        storage_size=storage_size,
        layout=layout,
    )
    payload["acceptance_candidates"]["normalized_final_state_equivalence"] = bool(
        payload["normalized_final_state_policy"]["passed"]
    )
    first_non_internal = first_field_with_role(
        all_mismatch_fields, "design_state", "top_level_io", "other"
    )
    if first_non_internal is not None:
        payload["first_non_internal_mismatch"] = first_non_internal
    first_design_state = first_field_with_role(all_mismatch_fields, "design_state")
    if first_design_state is not None:
        payload["first_design_state_mismatch"] = first_design_state


def compare_state_dumps(
    single_dump: Path,
    split_dump: Path,
    storage_size: int,
    *,
    layout: list[dict[str, int | str]] | None = None,
) -> dict:
    single = single_dump.read_bytes()
    split = split_dump.read_bytes()
    mismatch_count, first_mismatch = byte_mismatch_summary(single, split)

    payload = {
        "match": mismatch_count == 0 and len(single) == len(split),
        "single_bytes": len(single),
        "split_bytes": len(split),
        "mismatch_count": mismatch_count,
        "storage_size": storage_size,
        "single_sha256": sha256_file(single_dump),
        "split_sha256": sha256_file(split_dump),
    }
    if first_mismatch is not None:
        payload["first_mismatch"] = first_mismatch_payload(
            single=single,
            split=split,
            first_mismatch=first_mismatch,
            storage_size=storage_size,
            layout=layout,
        )
    if layout:
        add_layout_mismatch_summary(
            payload=payload,
            single=single,
            split=split,
            storage_size=storage_size,
            layout=layout,
            mismatch_count=mismatch_count,
        )
    return payload
