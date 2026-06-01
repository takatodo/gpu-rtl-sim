"""Audit RTLMeter overlays against the RTLMeter-preserving user path."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from rtlmeter_seed_selection import SELECTED_SEED


SURFACE = "rtlmeter_overlays_audit"
EXAMPLE_LIMIT = 5
DE_EMPHASIZE_PATTERNS = (
    "config/slice_launch_templates/prim_*.json",
    "config/slice_launch_templates/tlul_*.json",
    "config/slice_launch_templates/nvdla_*.json",
    "overlays/rtlmeter/designs/OpenTitan/**",
    "overlays/rtlmeter/designs/NVDLA/**",
)
POTENTIALLY_USEFUL_LATER_EXAMPLES = (
    "overlays/rtlmeter/designs/OpenTitan/src/prim_and2_gpu_cov_tb.sv",
    "overlays/rtlmeter/designs/OpenTitan/src/tlul_fifo_sync_gpu_cov_tb.sv",
    "overlays/rtlmeter/designs/NVDLA/src/nvdla_cmac_core_mac_gpu_cov_tb.sv",
    "overlays/rtlmeter/designs/NVDLA/src/nvdla_cmac_a2cacc_gpu_cov_tb.sv",
)


def _tracked_paths(repo_root: Path | None = None) -> list[str]:
    root = repo_root or Path(__file__).resolve().parents[2]
    return subprocess.check_output(
        ["git", "ls-files"],
        cwd=root,
        text=True,
    ).splitlines()


def _paths_with_prefix(paths: Sequence[str], prefix: str) -> list[str]:
    return sorted(path for path in paths if path.startswith(prefix))


def _legacy_template_paths(paths: Sequence[str]) -> list[str]:
    prefixes = (
        "config/slice_launch_templates/prim_",
        "config/slice_launch_templates/tlul_",
        "config/slice_launch_templates/nvdla_",
    )
    return sorted(path for path in paths if path.endswith(".json") and path.startswith(prefixes))


def _bounded_examples(paths: Sequence[str]) -> list[str]:
    return sorted(paths)[:EXAMPLE_LIMIT]


def _potential_later_examples(paths: Sequence[str]) -> list[str]:
    path_set = set(paths)
    return [path for path in POTENTIALLY_USEFUL_LATER_EXAMPLES if path in path_set]


def rtlmeter_overlays_audit(tracked_paths: Sequence[str] | None = None) -> dict[str, object]:
    """Return file-scoped overlay guidance without deleting or moving files."""

    paths = list(tracked_paths) if tracked_paths is not None else _tracked_paths()
    rtlmeter_overlays = _paths_with_prefix(paths, "overlays/rtlmeter/")
    generated_overlays = _paths_with_prefix(paths, "overlays/generated/")
    legacy_templates = _legacy_template_paths(paths)

    return {
        "schema_version": 1,
        "surface": SURFACE,
        "status": "audit_recorded_no_cleanup_performed",
        "first_seed": SELECTED_SEED,
        "minimal_overlay_set_for_first_seed": [],
        "first_seed_requires_repo_specific_launch_template": False,
        "canonical_project_state_changed": False,
        "audit_is_source_of_truth": False,
        "audit_source": "provided_tracked_paths" if tracked_paths is not None else "git_ls_files",
        "tracked_counts": {
            "rtlmeter_overlays": len(rtlmeter_overlays),
            "generated_overlays": len(generated_overlays),
            "legacy_launch_templates": len(legacy_templates),
        },
        "classifications": {
            "first_seed_required": [],
            "potentially_useful_later_examples": _potential_later_examples(rtlmeter_overlays),
            "rtlmeter_overlay_inventory_examples": _bounded_examples(rtlmeter_overlays),
            "tracked_generated_output_warning_examples": _bounded_examples(generated_overlays),
            "legacy_launch_template_examples": _bounded_examples(legacy_templates),
            "de_emphasize_from_public_rtlmeter_path": list(DE_EMPHASIZE_PATTERNS),
            "delete_or_archive_candidate": [],
        },
        "warnings": [
            "tracked overlays/generated paths should not become canonical source of truth",
            "broad overlay inventory is not current public RTLMeter acceleration support",
        ],
        "cleanup_recommendations": [
            "Do not delete RTLMeter overlays without a cleanup branch and recovery path.",
            "Do not present the broad overlay inventory as current RTLMeter acceleration support.",
            "Keep first RTLMeter user-path work independent of manual config/slice_launch_templates selection.",
            "Rename or regenerate tracked overlays/generated files in a separate cleanup if they are truly generated.",
        ],
        "non_claims": [
            "overlay audit does not prove RTLMeter acceleration",
            "overlay audit does not make broad OpenTitan or NVDLA support public",
            "overlay audit performs no file deletion",
        ],
    }
