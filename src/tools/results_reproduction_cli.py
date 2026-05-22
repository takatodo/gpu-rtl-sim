"""CLI parser and workflow dispatch for results reproduction."""

from __future__ import annotations

import argparse

from results_reproduction import (
    parse_resident_batch_states,
    parse_shape,
    run_median_measurements,
    run_mobile_vit_imagenet_128_reproduction,
    run_paged_attention_kv_cache_continuation_repeat_median,
    run_paged_attention_kv_cache_next_shapes_repeat_median,
    run_paged_attention_kv_cache_repeat_median,
    run_persistent_resident_state_abi_probe,
    run_persistent_resident_state_abi_repeat_median,
    run_persistent_resident_state_abi_shape_phase_sweep,
    run_public_pack_archive_plan,
    run_reproduction_plan,
    run_resident_batch_sweep,
    run_resident_state_reuse_experiment,
)
from results_reproduction_cli_args import build_parser


def dispatch(args: argparse.Namespace) -> None:
    if args.public_pack_archive:
        run_public_pack_archive_plan(dry_run=args.dry_run)
    elif args.mobile_vit_imagenet_128:
        run_mobile_vit_imagenet_128_reproduction(dry_run=args.dry_run)
    elif args.persistent_resident_state_abi_shape_phase_sweep:
        run_persistent_resident_state_abi_shape_phase_sweep(dry_run=args.dry_run)
    elif args.persistent_resident_state_abi_repeat_median is not None:
        run_persistent_resident_repeat_median(args)
    elif args.persistent_resident_state_abi is not None:
        run_persistent_resident_probe(args)
    elif args.resident_state_reuse is not None:
        run_resident_state_reuse(args)
    elif args.resident_batch_sweep is not None:
        run_resident_batch_sweep_cli(args)
    elif args.paged_kv_repeat_median is not None:
        run_paged_kv_repeat_median(args)
    elif args.paged_kv_continuation_repeat_median is not None:
        run_paged_kv_continuation_repeat_median(args)
    elif args.paged_kv_next_shapes_repeat_median is not None:
        run_paged_kv_next_shapes_repeat_median(args)
    elif args.repeat_median is not None:
        run_median_measurements(repeat_count=args.repeat_median, dry_run=args.dry_run)
    else:
        run_reproduction_plan(dry_run=args.dry_run)


def run_persistent_resident_repeat_median(args: argparse.Namespace) -> None:
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


def run_persistent_resident_probe(args: argparse.Namespace) -> None:
    nstates, steps = parse_shape(args.persistent_resident_state_abi)
    run_persistent_resident_state_abi_probe(
        nstates=nstates,
        steps=steps,
        phases=args.persistent_resident_state_abi_phases,
        dry_run=args.dry_run,
    )


def run_resident_batch_sweep_cli(args: argparse.Namespace) -> None:
    states = parse_resident_batch_states(args.resident_batch_sweep)
    run_resident_batch_sweep(
        repeat_count=args.resident_batch_sweep_repeat,
        batch_states=states,
        dry_run=args.dry_run,
    )


def run_paged_kv_repeat_median(args: argparse.Namespace) -> None:
    run_paged_attention_kv_cache_repeat_median(
        repeat_count=args.paged_kv_repeat_median,
        dry_run=args.dry_run,
    )


def run_paged_kv_continuation_repeat_median(args: argparse.Namespace) -> None:
    run_paged_attention_kv_cache_continuation_repeat_median(
        repeat_count=args.paged_kv_continuation_repeat_median,
        dry_run=args.dry_run,
    )


def run_paged_kv_next_shapes_repeat_median(args: argparse.Namespace) -> None:
    run_paged_attention_kv_cache_next_shapes_repeat_median(
        repeat_count=args.paged_kv_next_shapes_repeat_median,
        dry_run=args.dry_run,
    )


def run_resident_state_reuse(args: argparse.Namespace) -> None:
    nstates, steps = parse_shape(args.resident_state_reuse)
    run_resident_state_reuse_experiment(
        nstates=nstates,
        steps=steps,
        phases=args.resident_state_reuse_phases,
        dry_run=args.dry_run,
    )
