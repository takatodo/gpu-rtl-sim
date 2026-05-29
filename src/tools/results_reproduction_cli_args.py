"""Argument parser construction for the results reproduction CLI."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the representative modern-LLM-serving-like RTL hybrid "
            "result set documented in docs/results.md."
        )
    )
    add_general_options(parser)
    add_repeat_median_options(parser)
    add_resident_options(parser)
    add_persistent_resident_options(parser)
    add_public_pack_options(parser)
    return parser


def add_general_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")


def add_repeat_median_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repeat-median",
        type=int,
        metavar="N",
        help="Repeat the representative timing workloads N times and write reports/*median*.json.",
    )
    parser.add_argument(
        "--paged-kv-repeat-median",
        type=int,
        metavar="N",
        help=(
            "Repeat the reviewed paged-attention/KV-cache four-shape workload set N times "
            "and write reports/paged_attention_kv_cache_repeat_median_summary.json."
        ),
    )
    parser.add_argument(
        "--paged-kv-continuation-repeat-median",
        type=int,
        metavar="N",
        help=(
            "Repeat the paged-attention/KV-cache scale-up continuation four-shape workload set N times "
            "and write reports/paged_attention_kv_cache_scale_up_continuation_repeat_median_summary.json."
        ),
    )
    parser.add_argument(
        "--paged-kv-next-shapes-repeat-median",
        type=int,
        metavar="N",
        help=(
            "Repeat the paged-attention/KV-cache scale-up next-shapes four-shape workload set N times "
            "and write reports/paged_attention_kv_cache_scale_up_next_shapes_repeat_median_summary.json."
        ),
    )
    parser.add_argument(
        "--filelist-shape-breadth-repeat-median",
        type=int,
        metavar="N",
        help=(
            "Repeat the filelist-derived shape-breadth four-shape workload set N times "
            "and write reports/filelist_shape_breadth_repeat_median_summary.json."
        ),
    )
    parser.add_argument(
        "--filelist-broader-shape-repeat-median",
        type=int,
        metavar="N",
        help=(
            "Repeat the filelist-derived broader-shape four-shape workload set N times "
            "and write reports/filelist_broader_shape_repeat_median_summary.json."
        ),
    )
    parser.add_argument(
        "--filelist-broader-policy-repeat-median",
        type=int,
        metavar="N",
        help=(
            "Repeat exactly the two broader-policy-selected 64x1 filelist workloads N times "
            "and write reports/filelist_broader_policy_repeat_median_summary.json."
        ),
    )
    parser.add_argument(
        "--filelist-shape-breadth-gpu-allocation-policy",
        action="store_true",
        help=(
            "Print the scoped filelist shape-breadth GPU allocation policy. "
            "Dry-run only; writes no reports or artifacts."
        ),
    )
    parser.add_argument(
        "--filelist-broader-shape-gpu-allocation-policy",
        action="store_true",
        help=(
            "Print the scoped broader filelist GPU allocation policy. "
            "Dry-run only; writes no reports or artifacts."
        ),
    )


def add_resident_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--resident-batch-sweep",
        metavar="STATES",
        help=(
            "Run resident MHA decode-like batch sweep for comma-separated state counts "
            "at 64 steps, e.g. 1,8,16,32."
        ),
    )
    parser.add_argument(
        "--resident-batch-sweep-repeat",
        type=int,
        default=3,
        metavar="N",
        help="Repeat each --resident-batch-sweep shape N times.",
    )
    parser.add_argument(
        "--resident-state-reuse",
        metavar="SHAPE",
        help="Run the resident state reuse experiment for SHAPE, e.g. 16x64.",
    )
    parser.add_argument(
        "--resident-state-reuse-phases",
        type=int,
        default=4,
        metavar="N",
        help="Number of resident state reuse phases to plan or run.",
    )


def add_persistent_resident_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--persistent-resident-state-abi",
        metavar="SHAPE",
        help=(
            "Plan the persistent resident state ABI probe for SHAPE, e.g. 16x64. "
            "Only --dry-run is supported before the runtime ABI implementation gate."
        ),
    )
    parser.add_argument(
        "--persistent-resident-state-abi-phases",
        type=int,
        default=4,
        metavar="N",
        help="Number of persistent resident state ABI phases to plan.",
    )
    parser.add_argument(
        "--persistent-resident-state-abi-repeat-median",
        type=int,
        metavar="N",
        help=(
            "Repeat the existing persistent resident state ABI measurement N times "
            "and write reports/persistent_resident_state_abi_repeat_median_summary.json."
        ),
    )
    parser.add_argument(
        "--persistent-resident-state-abi-shape-phase-sweep",
        action="store_true",
        help=(
            "Run the four-case persistent resident state ABI shape/phase sweep "
            "and write reports/persistent_resident_state_abi_shape_phase_sweep_summary.json."
        ),
    )


def add_public_pack_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mobile-vit-imagenet-128",
        action="store_true",
        help="Run the MobileViT ImageNet local-cache limit-128 CPU-kick plus hybrid proxy reproduction.",
    )
    parser.add_argument(
        "--public-pack-archive",
        action="store_true",
        help="Print the public benchmark pack archive include/exclude plan. Dry-run only; does not create an archive.",
    )
