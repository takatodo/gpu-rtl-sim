"""Coverage-output gate and manifest validation helpers."""

from __future__ import annotations

from compare_vl_hybrid_policies import (
    COVERAGE_OUTPUT_REQUIRED_COUNT,
    COVERAGE_OUTPUT_REQUIRED_DOMAIN,
    COVERAGE_OUTPUT_REQUIRED_PREFIX,
)


def derive_strict_output_field_names(gate: dict) -> list[str]:
    contract = gate.get("coverage_output_contract") or {}
    entries = contract.get("strict_output_words") or []
    words: list[str] = []
    for entry in entries:
        prefix = str(entry["prefix"])
        count = int(entry["count"])
        for idx in range(count):
            words.append(f"{prefix}{idx}_o")
    return words


def validate_coverage_output_manifest(
    manifest: dict,
    *,
    expected_prefix: str = COVERAGE_OUTPUT_REQUIRED_PREFIX,
    expected_count: int = COVERAGE_OUTPUT_REQUIRED_COUNT,
) -> dict:
    coverage_domain = manifest.get("coverage_domain")
    domain_ok = coverage_domain == COVERAGE_OUTPUT_REQUIRED_DOMAIN
    regions = manifest.get("regions") or []
    words: list[str] = []
    for region in regions:
        for word in region.get("words") or []:
            words.append(str(word))
    expected = {
        f"{expected_prefix}{idx}_o"
        for idx in range(expected_count)
    }
    actual = set(words)
    duplicates = sorted({word for word in words if words.count(word) > 1})
    missing_required = sorted(expected - actual)
    extra_unexpected = sorted(actual - expected)
    return {
        "coverage_domain": coverage_domain,
        "coverage_domain_ok": domain_ok,
        "region_count": len(regions),
        "covered_word_count": len(words),
        "covered_unique_word_count": len(actual),
        "missing_required_words": missing_required,
        "extra_unexpected_words": extra_unexpected,
        "duplicate_words": duplicates,
        "valid": (
            domain_ok
            and len(words) == expected_count
            and not missing_required
            and not extra_unexpected
            and not duplicates
        ),
    }


def select_coverage_output_target(gate: dict, target_name: str) -> dict:
    target_scope = gate.get("target_scope") or []
    matches = [entry for entry in target_scope if entry.get("target") == target_name]
    if not matches:
        names = [str(entry.get("target")) for entry in target_scope]
        raise ValueError(
            f"target {target_name!r} not in coverage gate target_scope; available: {names}"
        )
    return dict(matches[0])


def validate_coverage_output_gate(gate: dict) -> None:
    if gate.get("coverage_domain") != COVERAGE_OUTPUT_REQUIRED_DOMAIN:
        raise ValueError(
            f"coverage gate coverage_domain must be {COVERAGE_OUTPUT_REQUIRED_DOMAIN!r}, "
            f"got {gate.get('coverage_domain')!r}"
        )
    if not (gate.get("target_scope") or []):
        raise ValueError("coverage gate target_scope must be non-empty")
    contract = gate.get("coverage_output_contract") or {}
    entries = contract.get("strict_output_words") or []
    if not entries:
        raise ValueError(
            "coverage gate coverage_output_contract.strict_output_words must be non-empty"
        )
