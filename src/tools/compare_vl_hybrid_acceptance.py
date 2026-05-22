"""Acceptance-policy summaries for VL/hybrid comparisons."""

from __future__ import annotations

from compare_vl_hybrid_policies import (
    ACCEPTANCE_POLICY_COVERAGE_OUTPUT,
    ACCEPTANCE_POLICY_IGNORE_INTERNAL,
    ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE,
    ACCEPTANCE_POLICY_PHASE_B_ENDPOINT,
    ACCEPTANCE_POLICY_STRICT,
    COVERAGE_OUTPUT_POLICY_NAME,
    NORMALIZED_FINAL_STATE_EXCLUSIONS,
    NORMALIZED_FINAL_STATE_POLICY_NAME,
    PHASE_B_ALLOWED_INTERNAL_FIELDS,
)


def has_only_phase_b_residual_fields(summary: dict[str, object]) -> bool:
    mismatch_fields = list(summary.get("mismatch_fields") or [])
    if not mismatch_fields:
        return True
    allowed = PHASE_B_ALLOWED_INTERNAL_FIELDS
    for entry in mismatch_fields:
        if str(entry.get("field_role")) != "verilator_internal":
            return False
        if str(entry.get("field_name")) not in allowed:
            return False
    return True


def normalized_acceptance_policy(normalized_summary: dict[str, object], *, passed: bool) -> dict[str, object]:
    return {
        "passed": passed,
        "description": (
            "Final comparable primitive DESIGN SPECIFIC STATE fields must match for "
            "design_state/top_level_io/other roles. CELLS pointers, parameters, "
            "Verilator internal variables, and Verilator-internal primitive "
            "temporaries/trigger history are excluded from the claim."
        ),
        "diagnostic_only_prefixes": True,
        "comparison_policy": {
            "name": normalized_summary.get("name", NORMALIZED_FINAL_STATE_POLICY_NAME),
            "included_member_count": normalized_summary.get("included_member_count"),
            "included_byte_count": normalized_summary.get("included_byte_count"),
            "exclusions": normalized_summary.get("exclusions", list(NORMALIZED_FINAL_STATE_EXCLUSIONS)),
        },
    }


def coverage_output_acceptance_policy(coverage_output_summary: dict[str, object], *, passed: bool) -> dict[str, object]:
    return {
        "passed": passed,
        "description": (
            "Coverage-output words derived from a coverage-output gate must match "
            "byte-for-byte for compatible CPU/GPU state pairs. This policy is separate "
            "from normalized_final_state_equivalence and only inspects the strict "
            "output fields named by the gate."
        ),
        "diagnostic_only_prefixes": True,
        "comparison_policy": {
            "name": coverage_output_summary.get("name", COVERAGE_OUTPUT_POLICY_NAME),
            "gate": coverage_output_summary.get("gate"),
            "target": coverage_output_summary.get("target"),
            "coverage_domain": coverage_output_summary.get("coverage_domain"),
            "strict_output_word_count": coverage_output_summary.get("strict_output_word_count"),
            "compared_word_count": coverage_output_summary.get("compared_word_count"),
            "compared_byte_count": coverage_output_summary.get("compared_byte_count"),
            "missing_fields": coverage_output_summary.get("missing_fields") or [],
            "blocked_reason": coverage_output_summary.get("blocked_reason"),
        },
    }


def build_acceptance_policies(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    candidates = dict(summary.get("acceptance_candidates") or {})
    strict_passed = bool(candidates.get("strict_match", summary.get("match", False)))
    ignore_internal_passed = bool(candidates.get("match_excluding_verilator_internal", False))
    phase_b_endpoint_passed = ignore_internal_passed and has_only_phase_b_residual_fields(summary)
    normalized_summary = dict(summary.get("normalized_final_state_policy") or {})
    normalized_passed = bool(normalized_summary.get("passed", False))
    coverage_output_summary = dict(summary.get("coverage_output_policy") or {})
    coverage_output_passed = bool(coverage_output_summary.get("passed", False))
    return {
        ACCEPTANCE_POLICY_STRICT: {
            "passed": strict_passed,
            "description": "Final raw state bytes must match exactly.",
            "diagnostic_only_prefixes": True,
        },
        ACCEPTANCE_POLICY_IGNORE_INTERNAL: {
            "passed": ignore_internal_passed,
            "description": (
                "Final design_state/top_level_io/other bytes must match; "
                "verilator_internal bytes may differ."
            ),
            "diagnostic_only_prefixes": True,
        },
        ACCEPTANCE_POLICY_PHASE_B_ENDPOINT: {
            "passed": phase_b_endpoint_passed,
            "description": (
                "Final design_state/top_level_io/other bytes must match, and any residual "
                "verilator_internal mismatch must be limited to the known convergence "
                "bookkeeping fields (__VicoPhaseResult, __VactIterCount, "
                "__VinactIterCount, __VicoTriggered)."
            ),
            "diagnostic_only_prefixes": True,
        },
        ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE: {
            **normalized_acceptance_policy(normalized_summary, passed=normalized_passed),
        },
        ACCEPTANCE_POLICY_COVERAGE_OUTPUT: coverage_output_acceptance_policy(
            coverage_output_summary,
            passed=coverage_output_passed,
        ),
    }


def select_acceptance_policy(
    summary: dict[str, object], policy_name: str
) -> dict[str, object]:
    policies = dict(summary.get("acceptance_policies") or {})
    selected = dict(policies[policy_name])
    selected["name"] = policy_name
    return selected
