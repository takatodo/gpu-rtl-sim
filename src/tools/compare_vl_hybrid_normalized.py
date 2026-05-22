"""Normalized final-state comparison helpers for compare_vl_hybrid_modes."""

from __future__ import annotations

import re

from compare_vl_hybrid_layout import VERILATOR_INTERNAL_FIELDS
from compare_vl_hybrid_normalized_mismatch import compare_normalized_final_state_fields
from compare_vl_hybrid_policies import (
    ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE,
    NORMALIZED_FINAL_STATE_EXCLUSIONS,
    NORMALIZED_FINAL_STATE_POLICY_NAME,
)
from compare_vl_hybrid_state_pairs import state_pair_plan


def is_normalized_final_state_field(entry: dict[str, int | str]) -> bool:
    section = str(entry.get("section", ""))
    if section and section != "DESIGN SPECIFIC STATE":
        return False
    decl_type = str(entry.get("decl_type", ""))
    decl_type_without_comments = re.sub(r"/\*.*?\*/", "", decl_type)
    if "*" in decl_type_without_comments:
        return False
    excluded_type_markers = (
        "std::string",
        "VlQueue",
        "VlClassRef",
        "VlDelayScheduler",
        "VlTriggerVec",
    )
    if any(marker in decl_type for marker in excluded_type_markers):
        return False
    name = str(entry.get("name", ""))
    if name in VERILATOR_INTERNAL_FIELDS:
        return False
    return True

def normalized_final_state_fields(
    layout: list[dict[str, int | str]]
) -> list[dict[str, int | str]]:
    return [entry for entry in layout if is_normalized_final_state_field(entry)]

def initial_normalized_final_state_summary(
    fields: list[dict[str, int | str]]
) -> dict[str, object]:
    return {
        "name": NORMALIZED_FINAL_STATE_POLICY_NAME,
        "acceptance_policy": ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE,
        "exclusions": list(NORMALIZED_FINAL_STATE_EXCLUSIONS),
        "included_member_count": len(fields),
        "included_byte_count": sum(int(entry["size"]) for entry in fields),
    }

def normalized_state_pair_plan_or_block(
    *,
    summary: dict[str, object],
    reference: bytes,
    candidate: bytes,
    storage_size: int,
) -> dict[str, object] | None:
    plan = state_pair_plan(len(reference), len(candidate), storage_size)
    summary.update(
        {
            "comparison_mode": plan["comparison_mode"],
            "compatible": bool(plan["compatible"]),
            "reference_state_count": plan["reference_state_count"],
            "candidate_state_count": plan["candidate_state_count"],
        }
    )
    if plan["compatible"]:
        return plan
    summary.update(
        empty_normalized_final_state_result(
            blocked_reason=plan["reason"],
            count_value=None,
        )
    )
    return None

def empty_normalized_final_state_result(
    *,
    blocked_reason: object,
    count_value: int | None,
) -> dict[str, object]:
    return {
        "passed": False,
        "blocked_reason": blocked_reason,
        "mismatch_field_count": count_value,
        "mismatch_byte_count": count_value,
        "functional_non_internal_mismatch_field_count": count_value,
        "functional_non_internal_mismatch_byte_count": count_value,
        "max_functional_non_internal_mismatch_byte_count": count_value,
        "mismatch_role_summary": {},
        "mismatch_fields": [],
    }

def build_normalized_final_state_policy_summary(
    reference: bytes,
    candidate: bytes,
    *,
    storage_size: int,
    layout: list[dict[str, int | str]],
    limit: int = 16,
) -> dict[str, object]:
    fields = normalized_final_state_fields(layout)
    summary = initial_normalized_final_state_summary(fields)
    plan = normalized_state_pair_plan_or_block(
        summary=summary,
        reference=reference,
        candidate=candidate,
        storage_size=storage_size,
    )
    if plan is None:
        return summary
    if not fields:
        summary.update(
            empty_normalized_final_state_result(
                blocked_reason="no_comparable_normalized_fields",
                count_value=0,
            )
        )
        return summary

    pairs = list(plan["pairs"])
    summary.update(
        compare_normalized_final_state_fields(
            reference=reference,
            candidate=candidate,
            storage_size=storage_size,
            fields=fields,
            pairs=pairs,
            limit=limit,
        )
    )
    return summary
