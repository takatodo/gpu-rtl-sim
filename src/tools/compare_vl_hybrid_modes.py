#!/usr/bin/env python3
"""
Compare stock-Verilator hybrid outputs between:
  1) single-kernel vl_eval_batch_gpu
  2) phase-split launch_sequence (ico/nba)

This is a regression harness for Phase B fidelity work. It rebuilds the cubin in both modes,
runs src/tools/run_vl_hybrid.py twice with identical launch settings, dumps the final device
storage, and reports whether the bytewise state images match.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from compare_vl_hybrid_cli import build_compare_parser
from compare_vl_hybrid_coverage import (
    derive_strict_output_field_names,
    validate_coverage_output_manifest,
)
from compare_vl_hybrid_existing_dumps import (
    compare_dump_files,
    read_storage_size_from_meta,
)
from compare_vl_hybrid_fresh_run import run_fresh_comparison
from compare_vl_hybrid_layout import (
    probe_root_layout,
)
from compare_vl_hybrid_policies import (
    ACCEPTANCE_POLICY_COVERAGE_OUTPUT,
    ACCEPTANCE_POLICY_IGNORE_INTERNAL,
    ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE,
    ACCEPTANCE_POLICY_PHASE_B_ENDPOINT,
    ACCEPTANCE_POLICY_STRICT,
)
from compare_vl_hybrid_summary import emit_comparison_summary


def build_parser() -> argparse.ArgumentParser:
    # Coverage-output options such as --coverage-output-gate and
    # --coverage-output-target are provided by the shared compare parser.
    return build_compare_parser(
        default_policy=ACCEPTANCE_POLICY_STRICT,
        policy_choices=[
            ACCEPTANCE_POLICY_STRICT,
            ACCEPTANCE_POLICY_IGNORE_INTERNAL,
            ACCEPTANCE_POLICY_PHASE_B_ENDPOINT,
            ACCEPTANCE_POLICY_NORMALIZED_FINAL_STATE,
            ACCEPTANCE_POLICY_COVERAGE_OUTPUT,
        ],
    )


def compare_existing_dumps(args: argparse.Namespace, *, mdir: Path) -> int:
    reference_dump, candidate_dump = args.compare_dumps
    if args.acceptance_policy == ACCEPTANCE_POLICY_COVERAGE_OUTPUT and args.coverage_output_gate is None:
        raise SystemExit(
            "--acceptance-policy coverage_output_equivalence requires "
            "--coverage-output-gate PATH"
        )
    summary = compare_dump_files(
        mdir=mdir,
        display_mdir=args.mdir,
        reference_dump=reference_dump,
        candidate_dump=candidate_dump,
        storage_size=args.storage_size,
        acceptance_policy=args.acceptance_policy,
        reference_label=args.reference_label,
        candidate_label=args.candidate_label,
        coverage_output_gate_path=args.coverage_output_gate,
        coverage_output_target=args.coverage_output_target,
    )
    return emit_comparison_summary(summary, json_out=args.json_out)


def main() -> int:
    p = build_parser()
    args = p.parse_args()

    mdir = args.mdir.resolve()

    if args.compare_dumps is not None:
        return compare_existing_dumps(args, mdir=mdir)

    return run_fresh_comparison(args, mdir=mdir)


if __name__ == "__main__":
    raise SystemExit(main())
