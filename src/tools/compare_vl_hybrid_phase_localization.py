from __future__ import annotations


def initial_phase_localization() -> dict[str, object]:
    return {
        "first_divergent_prefix_index": None,
        "first_divergent_kernels": None,
        "first_non_internal_prefix_index": None,
        "first_non_internal_kernels": None,
        "first_non_internal_mismatch": None,
        "first_design_state_prefix_index": None,
        "first_design_state_kernels": None,
        "first_design_state_mismatch": None,
        "first_delta_prefix_index": None,
        "first_delta_kernels": None,
        "first_delta_fields": None,
        "first_non_internal_delta_prefix_index": None,
        "first_non_internal_delta_kernels": None,
        "first_non_internal_delta_mismatch": None,
        "first_design_state_delta_prefix_index": None,
        "first_design_state_delta_kernels": None,
        "first_design_state_delta_mismatch": None,
        "per_prefix_mismatch_counts": [],
        "per_prefix_delta_counts": [],
    }


def build_phase_delta_summary(summary: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
        "mismatch_count": int(summary.get("mismatch_count", 0)),
        "mismatch_field_count": int(summary.get("mismatch_field_count", 0)),
        "mismatch_role_summary": dict(summary.get("mismatch_role_summary") or {}),
        "acceptance_candidates": dict(summary.get("acceptance_candidates") or {}),
        "mismatch_fields": [dict(entry) for entry in summary.get("mismatch_fields", [])],
    }
    for key in ("first_mismatch", "first_non_internal_mismatch", "first_design_state_mismatch"):
        value = summary.get(key)
        if value is not None:
            payload[key] = dict(value)
    return payload


def record_prefix_vs_single_localization(
    *,
    phase_localization: dict[str, object],
    prefix_index: int,
    kernels: list[str],
    prefix_summary: dict[str, object],
) -> None:
    phase_localization["per_prefix_mismatch_counts"].append(prefix_summary["mismatch_count"])
    if phase_localization["first_divergent_prefix_index"] is None and prefix_summary["mismatch_count"] > 0:
        phase_localization["first_divergent_prefix_index"] = prefix_index
        phase_localization["first_divergent_kernels"] = list(kernels)
        phase_localization["first_divergent_fields"] = list(prefix_summary.get("mismatch_fields", []))
    if (
        phase_localization["first_non_internal_prefix_index"] is None
        and prefix_summary.get("first_non_internal_mismatch") is not None
    ):
        phase_localization["first_non_internal_prefix_index"] = prefix_index
        phase_localization["first_non_internal_kernels"] = list(kernels)
        phase_localization["first_non_internal_mismatch"] = dict(prefix_summary["first_non_internal_mismatch"])
    if (
        phase_localization["first_design_state_prefix_index"] is None
        and prefix_summary.get("first_design_state_mismatch") is not None
    ):
        phase_localization["first_design_state_prefix_index"] = prefix_index
        phase_localization["first_design_state_kernels"] = list(kernels)
        phase_localization["first_design_state_mismatch"] = dict(prefix_summary["first_design_state_mismatch"])


def record_prefix_delta_localization(
    *,
    phase_localization: dict[str, object],
    prefix_index: int,
    kernels: list[str],
    prev_summary: dict[str, object],
) -> None:
    phase_localization["per_prefix_delta_counts"].append(prev_summary["mismatch_count"])
    if phase_localization["first_delta_prefix_index"] is None and prev_summary["mismatch_count"] > 0:
        phase_localization["first_delta_prefix_index"] = prefix_index
        phase_localization["first_delta_kernels"] = list(kernels)
        phase_localization["first_delta_fields"] = list(prev_summary.get("mismatch_fields", []))
    if (
        phase_localization["first_non_internal_delta_prefix_index"] is None
        and prev_summary.get("first_non_internal_mismatch") is not None
    ):
        phase_localization["first_non_internal_delta_prefix_index"] = prefix_index
        phase_localization["first_non_internal_delta_kernels"] = list(kernels)
        phase_localization["first_non_internal_delta_mismatch"] = dict(
            prev_summary["first_non_internal_mismatch"]
        )
    if (
        phase_localization["first_design_state_delta_prefix_index"] is None
        and prev_summary.get("first_design_state_mismatch") is not None
    ):
        phase_localization["first_design_state_delta_prefix_index"] = prefix_index
        phase_localization["first_design_state_delta_kernels"] = list(kernels)
        phase_localization["first_design_state_delta_mismatch"] = dict(
            prev_summary["first_design_state_mismatch"]
        )
