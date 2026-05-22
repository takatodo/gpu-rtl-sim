"""Coverage-output comparison helpers for compare_vl_hybrid_modes."""

from __future__ import annotations

from compare_vl_hybrid_coverage_blocks import (
    coverage_layout_by_name_or_block,
    coverage_state_pair_plan_or_block,
)
from compare_vl_hybrid_coverage_config import (
    derive_strict_output_field_names,
    select_coverage_output_target,
    validate_coverage_output_gate,
    validate_coverage_output_manifest,
)
from compare_vl_hybrid_coverage_summary import (
    initial_coverage_output_summary,
    validate_coverage_manifest_for_summary,
)
from compare_vl_hybrid_coverage_strict import compare_strict_output_words


def compare_coverage_output_words(
    *,
    reference: bytes,
    candidate: bytes,
    storage_size: int,
    strict_words: list[str],
    layout_by_name: dict[str, dict[str, int | str]],
    pairs: list[tuple[int, int]],
    limit: int,
) -> dict[str, object]:
    comparison = compare_strict_output_words(
        reference=reference,
        candidate=candidate,
        storage_size=storage_size,
        strict_words=strict_words,
        layout_by_name=layout_by_name,
        pairs=pairs,
        limit=limit,
    )
    return {
        "compared_state_pair_count": len(pairs),
        **comparison,
    }


def _update_coverage_output_comparison_if_ready(
    *,
    summary: dict[str, object],
    reference: bytes,
    candidate: bytes,
    storage_size: int,
    layout: list[dict[str, int | str]],
    strict_words: list[str],
    limit: int,
) -> None:
    layout_by_name = coverage_layout_by_name_or_block(
        summary=summary,
        layout=layout,
        strict_words=strict_words,
    )
    if layout_by_name is None:
        return

    plan = coverage_state_pair_plan_or_block(
        summary=summary,
        reference=reference,
        candidate=candidate,
        storage_size=storage_size,
    )
    if plan is None:
        return

    summary.update(
        compare_coverage_output_words(
            reference=reference,
            candidate=candidate,
            storage_size=storage_size,
            strict_words=strict_words,
            layout_by_name=layout_by_name,
            pairs=list(plan["pairs"]),
            limit=limit,
        )
    )


def build_coverage_output_policy_summary(
    reference: bytes,
    candidate: bytes,
    *,
    storage_size: int,
    layout: list[dict[str, int | str]],
    gate: dict,
    target_entry: dict,
    manifest: dict | None,
    manifest_path: str | None = None,
    limit: int = 16,
) -> dict[str, object]:
    contract = gate.get("coverage_output_contract") or {}
    strict_words = derive_strict_output_field_names(gate)
    summary = initial_coverage_output_summary(
        gate=gate,
        target_entry=target_entry,
        contract=contract,
        strict_words=strict_words,
        manifest_path=manifest_path,
    )

    if not validate_coverage_manifest_for_summary(
        summary=summary,
        manifest=manifest,
        contract=contract,
    ):
        return summary
    _update_coverage_output_comparison_if_ready(
        summary=summary,
        reference=reference,
        candidate=candidate,
        storage_size=storage_size,
        layout=layout,
        strict_words=strict_words,
        limit=limit,
    )
    return summary
