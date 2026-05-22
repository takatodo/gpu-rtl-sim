from __future__ import annotations

from compare_vl_hybrid_state_pairs import state_pair_plan


def coverage_layout_by_name_or_block(
    *,
    summary: dict[str, object],
    layout: list[dict[str, int | str]],
    strict_words: list[str],
) -> dict[str, dict[str, int | str]] | None:
    layout_by_name = {str(entry["name"]): entry for entry in layout}
    missing_fields = [name for name in strict_words if name not in layout_by_name]
    if not missing_fields:
        return layout_by_name
    summary["missing_fields"] = missing_fields
    summary["passed"] = False
    summary["blocked_reason"] = "missing_coverage_output_fields"
    return None


def coverage_state_pair_plan_or_block(
    *,
    summary: dict[str, object],
    reference: bytes,
    candidate: bytes,
    storage_size: int,
) -> dict[str, object] | None:
    plan = state_pair_plan(len(reference), len(candidate), storage_size)
    summary["comparison_mode"] = plan["comparison_mode"]
    summary["compatible"] = bool(plan["compatible"])
    summary["reference_state_count"] = plan["reference_state_count"]
    summary["candidate_state_count"] = plan["candidate_state_count"]
    if plan["compatible"]:
        return plan
    summary["passed"] = False
    summary["blocked_reason"] = plan["reason"]
    return None
