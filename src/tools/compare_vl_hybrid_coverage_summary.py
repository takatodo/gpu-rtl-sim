"""Summary and validation helpers for coverage-output comparison."""

from __future__ import annotations

from compare_vl_hybrid_policies import (
    ACCEPTANCE_POLICY_COVERAGE_OUTPUT,
    COVERAGE_OUTPUT_POLICY_NAME,
    COVERAGE_OUTPUT_REQUIRED_COUNT,
    COVERAGE_OUTPUT_REQUIRED_PREFIX,
)
from compare_vl_hybrid_coverage_config import validate_coverage_output_manifest


def initial_coverage_output_summary(
    *,
    gate: dict,
    target_entry: dict,
    contract: dict,
    strict_words: list[str],
    manifest_path: str | None,
) -> dict[str, object]:
    return {
        "name": COVERAGE_OUTPUT_POLICY_NAME,
        "acceptance_policy": ACCEPTANCE_POLICY_COVERAGE_OUTPUT,
        "gate": gate.get("gate"),
        "coverage_domain": gate.get("coverage_domain"),
        "target": target_entry.get("target"),
        "manifest_path": manifest_path,
        "strict_output_word_prefixes": [
            {"prefix": str(entry["prefix"]), "count": int(entry["count"])}
            for entry in (contract.get("strict_output_words") or [])
        ],
        "expected_total_words_per_state": contract.get("total_words_per_state"),
        "expected_total_bytes_per_state": contract.get("total_bytes_per_state"),
        "strict_output_word_count": len(strict_words),
        "missing_fields": [],
        "compared_state_pair_count": 0,
        "compared_word_count": 0,
        "compared_byte_count": 0,
        "mismatches": [],
        "mismatch_count": 0,
    }


def validate_coverage_manifest_for_summary(
    *,
    summary: dict[str, object],
    manifest: dict | None,
    contract: dict,
) -> bool:
    if manifest is None:
        summary["manifest_validation"] = None
        summary["passed"] = False
        summary["blocked_reason"] = "coverage_manifest_not_loaded"
        return False

    manifest_region_words = contract.get("manifest_region_words") or {}
    manifest_validation = validate_coverage_output_manifest(
        manifest,
        expected_prefix=str(
            manifest_region_words.get("prefix", COVERAGE_OUTPUT_REQUIRED_PREFIX)
        ),
        expected_count=int(
            manifest_region_words.get("count", COVERAGE_OUTPUT_REQUIRED_COUNT)
        ),
    )
    summary["manifest_validation"] = manifest_validation
    if manifest_validation["valid"]:
        return True
    summary["passed"] = False
    summary["blocked_reason"] = "coverage_manifest_real_toggle_word_coverage_invalid"
    return False
