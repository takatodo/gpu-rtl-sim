#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from results_reproduction import (
    parse_shape,
    parse_resident_batch_states,
    run_median_measurements,
    run_mobile_vit_imagenet_128_reproduction,
    run_paged_attention_kv_cache_repeat_median,
    run_public_pack_archive_plan,
    run_persistent_resident_state_abi_probe,
    run_persistent_resident_state_abi_repeat_median,
    run_reproduction_plan,
    run_resident_batch_sweep,
    run_resident_state_reuse_experiment,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the representative modern-LLM-serving-like RTL hybrid "
            "result set documented in docs/results.md."
        )
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
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
        "--mobile-vit-imagenet-128",
        action="store_true",
        help="Run the MobileViT ImageNet local-cache limit-128 CPU-kick plus hybrid proxy reproduction.",
    )
    parser.add_argument(
        "--public-pack-archive",
        action="store_true",
        help="Print the public benchmark pack archive include/exclude plan. Dry-run only; does not create an archive.",
    )
    args = parser.parse_args(argv)

    try:
        if args.public_pack_archive:
            run_public_pack_archive_plan(dry_run=args.dry_run)
        elif args.mobile_vit_imagenet_128:
            run_mobile_vit_imagenet_128_reproduction(dry_run=args.dry_run)
        elif args.persistent_resident_state_abi_repeat_median is not None:
            if args.persistent_resident_state_abi is None:
                raise ValueError("--persistent-resident-state-abi-repeat-median requires --persistent-resident-state-abi SHAPE")
            nstates, steps = parse_shape(args.persistent_resident_state_abi)
            run_persistent_resident_state_abi_repeat_median(
                nstates=nstates,
                steps=steps,
                phases=args.persistent_resident_state_abi_phases,
                repeat_count=args.persistent_resident_state_abi_repeat_median,
                dry_run=args.dry_run,
            )
        elif args.persistent_resident_state_abi is not None:
            nstates, steps = parse_shape(args.persistent_resident_state_abi)
            run_persistent_resident_state_abi_probe(
                nstates=nstates,
                steps=steps,
                phases=args.persistent_resident_state_abi_phases,
                dry_run=args.dry_run,
            )
        elif args.resident_state_reuse is not None:
            nstates, steps = parse_shape(args.resident_state_reuse)
            run_resident_state_reuse_experiment(
                nstates=nstates,
                steps=steps,
                phases=args.resident_state_reuse_phases,
                dry_run=args.dry_run,
            )
        elif args.resident_batch_sweep is not None:
            states = parse_resident_batch_states(args.resident_batch_sweep)
            run_resident_batch_sweep(
                repeat_count=args.resident_batch_sweep_repeat,
                batch_states=states,
                dry_run=args.dry_run,
            )
        elif args.paged_kv_repeat_median is not None:
            run_paged_attention_kv_cache_repeat_median(
                repeat_count=args.paged_kv_repeat_median,
                dry_run=args.dry_run,
            )
        elif args.repeat_median is not None:
            run_median_measurements(repeat_count=args.repeat_median, dry_run=args.dry_run)
        else:
            run_reproduction_plan(dry_run=args.dry_run)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
