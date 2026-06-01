"""RTLMeter first-seed candidate metadata."""

from __future__ import annotations


SURFACE = "rtlmeter_first_seed_selection"
SELECTED_SEED = "Example:kind:hello"


def rtlmeter_first_seed_selection() -> dict[str, object]:
    """Return the first RTLMeter seed candidate without changing config state."""

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "candidate_selected_not_configured",
        "selected_seed": SELECTED_SEED,
        "selection_scope": "rtlmeter_user_path_plumbing_candidate",
        "config_selection_json_updated": False,
        "config_targets_json_updated": False,
        "active_project_priority_changed": False,
        "canonical_project_state_changed": False,
        "source_of_truth_note": (
            "config/selection.json, docs/status.md, and docs/roadmap.md remain the active "
            "project-state source of truth; this helper is non-canonical planning metadata"
        ),
        "why_this_seed": [
            "uses RTLMeter's own descriptor and case naming",
            "requires no repo-specific launch template for command capture",
            "requires no RTLMeter source patch",
            "has the smallest blast radius for PATH wrapper and compileArgs pass-through",
        ],
        "candidate_summary": {
            "Example:kind:hello": {
                "decision": "selected",
                "strength": "best first seed for preserving RTLMeter UX with no custom overlay",
                "weakness": "not a meaningful performance or GPU-speedup seed",
            },
            "OpenTitan primitive overlay": {
                "decision": "defer",
                "strength": "closer to existing GPU-toggle coverage harnesses",
                "weakness": "currently routes through repo-owned overlays/templates instead of normal RTLMeter UX",
            },
            "TL-UL target": {
                "decision": "defer",
                "strength": "has stronger existing CPU/GPU compare history in this repo",
                "weakness": "would risk conflating repo-specific template evidence with RTLMeter workflow acceleration",
            },
            "NVDLA CMAC": {
                "decision": "defer",
                "strength": "more performance-relevant design class",
                "weakness": "larger dependency and overlay blast radius for a first user-path seed",
            },
        },
        "next_gate_before_config_update": (
            "prove CPU/GPU compare integration for the selected RTLMeter-preserving path "
            "without requiring manual config/slice_launch_templates selection"
        ),
        "non_goals": [
            "no broad RTLMeter acceleration claim",
            "no arbitrary RTLMeter descriptor support claim",
            "no automatic GPU allocation claim",
            "no performance or speedup claim from the seed decision",
            "no source-of-truth change from this helper",
            "no update to config/selection.json without a reviewed priority change",
        ],
    }
