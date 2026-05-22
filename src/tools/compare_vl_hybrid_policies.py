"""Policy constants shared by compare_vl_hybrid_modes."""

ACCEPTANCE_POLICY_STRICT = "strict_final_state"
ACCEPTANCE_POLICY_IGNORE_INTERNAL = "ignore_verilator_internal_final_state"
ACCEPTANCE_POLICY_PHASE_B_ENDPOINT = "phase_b_endpoint"
ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE = "normalized_final_state_equivalence"
ACCEPTANCE_POLICY_COVERAGE_OUTPUT = "coverage_output_equivalence"

NORMALIZED_FINAL_STATE_POLICY_NAME = "primitive_design_state_fields_only"
NORMALIZED_FINAL_STATE_EXCLUSIONS = [
    "CELLS pointer fields",
    "std::string",
    "VlQueue",
    "VlClassRef",
    "scheduler objects",
    "internal variables section",
    "parameters",
]

COVERAGE_OUTPUT_POLICY_NAME = "tlul_coverage_output_strict_equality"
COVERAGE_OUTPUT_REQUIRED_DOMAIN = "toggle_real_subset_bitmap"
COVERAGE_OUTPUT_REQUIRED_PREFIX = "real_toggle_subset_word"
COVERAGE_OUTPUT_REQUIRED_COUNT = 18

PHASE_B_ALLOWED_INTERNAL_FIELDS = {
    "__VicoPhaseResult",
    "__VactIterCount",
    "__VinactIterCount",
    "__VicoTriggered",
}


def build_acceptance_candidates(
    *,
    match: bool,
    mismatch_count: int,
    role_summary: dict[str, dict[str, int]],
) -> dict[str, int | bool]:
    internal_bytes = int(role_summary.get("verilator_internal", {}).get("mismatch_bytes", 0))
    design_state_bytes = int(role_summary.get("design_state", {}).get("mismatch_bytes", 0))
    top_level_io_bytes = int(role_summary.get("top_level_io", {}).get("mismatch_bytes", 0))
    other_bytes = mismatch_count - internal_bytes - design_state_bytes - top_level_io_bytes
    return {
        "strict_match": match,
        "match_excluding_verilator_internal": mismatch_count == internal_bytes,
        "verilator_internal_mismatch_bytes": internal_bytes,
        "design_state_mismatch_bytes": design_state_bytes,
        "top_level_io_mismatch_bytes": top_level_io_bytes,
        "other_mismatch_bytes": other_bytes,
    }
