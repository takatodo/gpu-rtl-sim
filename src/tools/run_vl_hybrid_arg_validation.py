from __future__ import annotations

import argparse


def persistent_phase_dump_parts(args: argparse.Namespace) -> list[str] | None:
    raw = args.persistent_resident_state_abi_phase_dumps
    if raw is None:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.resident_steps and args.patch:
        parser.error("--resident-steps rejects --patch; use --patch-script for a resident schedule")
    if (args.persistent_resident_state_abi_handle is None) != (
        args.persistent_resident_state_abi_phase is None
    ):
        parser.error(
            "--persistent-resident-state-abi-handle and "
            "--persistent-resident-state-abi-phase must be provided together"
        )
    if args.persistent_resident_state_abi_phase is not None and args.persistent_resident_state_abi_phase < 1:
        parser.error("--persistent-resident-state-abi-phase must be >= 1")
    if args.persistent_resident_state_abi_phase is not None and not args.resident_steps:
        parser.error("--persistent-resident-state-abi-* requires --resident-steps")
    if args.persistent_resident_state_abi_phase is not None and args.persistent_resident_state_abi_phase > 1 and args.init_state:
        parser.error("persistent resident state ABI phases after 1 must not use --init-state")
    if args.persistent_resident_state_abi_phases is not None:
        if args.persistent_resident_state_abi_phase is None:
            parser.error("--persistent-resident-state-abi-phases requires persistent ABI handle and phase")
        if args.persistent_resident_state_abi_phases < 1:
            parser.error("--persistent-resident-state-abi-phases must be >= 1")
        if args.persistent_resident_state_abi_phase != 1:
            parser.error("multi-phase persistent resident ABI mode must start at phase 1")
        phase_dumps = persistent_phase_dump_parts(args)
        if phase_dumps is not None:
            if len(phase_dumps) != args.persistent_resident_state_abi_phases:
                parser.error("--persistent-resident-state-abi-phase-dumps count must match --persistent-resident-state-abi-phases")
    if args.timing_repeats < 1:
        parser.error("--timing-repeats must be >= 1")
