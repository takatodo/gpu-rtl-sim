"""Argument parser helpers for compare_vl_hybrid_modes."""

from __future__ import annotations

import argparse
from pathlib import Path


def add_run_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("mdir", type=Path, help="Verilator --cc output directory (contains *_classes.mk)")
    p.add_argument("--sm", default="sm_89", help="GPU arch (default: sm_89)")
    p.add_argument("--clang-O", dest="clang_opt", default="O1", help="clang optimization for .ll")
    p.add_argument("--force-build", action="store_true", help="Force both cubin rebuilds")
    p.add_argument("--nstates", type=int, default=64, help="Parallel states for each run")
    p.add_argument("--steps", type=int, default=1, help="Launch steps for each run")
    p.add_argument("--block-size", type=int, default=256, help="CUDA block size")
    p.add_argument(
        "--patch",
        action="append",
        default=[],
        metavar="GLOBAL_OFF:BYTE",
        help="Per-step HtoD patch forwarded to run_vl_hybrid.py",
    )
    p.add_argument("--json-out", type=Path, default=None, help="Optional JSON summary path")


def add_existing_dump_options(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--compare-dumps",
        nargs=2,
        type=Path,
        metavar=("REFERENCE_DUMP", "CANDIDATE_DUMP"),
        help=(
            "Compare two existing state dumps using this mdir layout instead of rebuilding "
            "and running single/split GPU modes"
        ),
    )
    p.add_argument(
        "--storage-size",
        type=int,
        default=None,
        help="Storage bytes per state for --compare-dumps; defaults to mdir/vl_batch_gpu.meta.json",
    )
    p.add_argument("--reference-label", default="reference", help="Label recorded for the first --compare-dumps input")
    p.add_argument("--candidate-label", default="candidate", help="Label recorded for the second --compare-dumps input")
    p.add_argument(
        "--dump-dir",
        type=Path,
        default=None,
        help="Optional directory to keep single/split raw state dumps for mismatch debugging",
    )


def add_acceptance_policy_options(
    p: argparse.ArgumentParser,
    *,
    default_policy: str,
    policy_choices: list[str],
) -> None:
    p.add_argument(
        "--acceptance-policy",
        default=default_policy,
        choices=policy_choices,
        help="Pass/fail policy for the tool exit code (default: strict_final_state)",
    )
    p.add_argument(
        "--coverage-output-gate",
        type=Path,
        default=None,
        help=(
            "Path to a coverage-output equivalence gate JSON; required for "
            "--acceptance-policy coverage_output_equivalence. The gate is validated "
            "and its strict_output_words are compared field-by-field between the two "
            "--compare-dumps inputs using the probed root layout."
        ),
    )
    p.add_argument(
        "--coverage-output-target",
        default=None,
        help=(
            "Name of the target_scope entry in the coverage-output gate to use; "
            "required when the gate exposes more than one target."
        ),
    )


def build_compare_parser(*, default_policy: str, policy_choices: list[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare single-kernel vs phase-split stock-Verilator hybrid outputs"
    )
    add_run_options(parser)
    add_existing_dump_options(parser)
    add_acceptance_policy_options(
        parser,
        default_policy=default_policy,
        policy_choices=policy_choices,
    )
    return parser
