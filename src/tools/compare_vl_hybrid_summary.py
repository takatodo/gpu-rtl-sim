"""Summary formatting helpers for compare_vl_hybrid_modes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from compare_vl_hybrid_acceptance import (
    build_acceptance_policies,
    select_acceptance_policy,
)


def write_json_summary(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {path}")


def finalize_fresh_run_summary(
    *,
    summary: dict[str, object],
    mdir: Path,
    single_path: Path,
    split_path: Path,
    launch_sequence: list[str],
    layout: list[dict[str, object]],
    single_dump: Path,
    split_dump: Path,
    args: argparse.Namespace,
) -> None:
    summary["phase_localization_note"] = (
        "Prefix comparisons are diagnostic against single final state, "
        "not phase-aligned acceptance gates; use delta_from_previous_prefix "
        "and first_*_delta_* keys to isolate what each added kernel changed."
    )
    summary["acceptance_policies"] = build_acceptance_policies(summary)
    summary["selected_acceptance_policy"] = select_acceptance_policy(
        summary, args.acceptance_policy
    )
    summary.update(
        {
            "schema_version": 2,
            "mdir": str(mdir),
            "single_cubin": str(single_path),
            "split_cubin": str(split_path),
            "launch_sequence": launch_sequence,
            "root_layout_member_count": len(layout),
            "nstates": args.nstates,
            "steps": args.steps,
            "block_size": args.block_size,
            "patches": list(args.patch),
            "single_dump": str(single_dump),
            "split_dump": str(split_dump),
        }
    )


def emit_comparison_summary(summary: dict[str, object], *, json_out: Path | None) -> int:
    if json_out is not None:
        write_json_summary(json_out, summary)

    print(json.dumps(summary, indent=2))
    return 0 if summary["selected_acceptance_policy"]["passed"] else 2
