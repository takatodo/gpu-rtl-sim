from __future__ import annotations

import argparse
from pathlib import Path

from run_vl_hybrid_arg_validation import persistent_phase_dump_parts, validate_args


def add_basic_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mdir",
        type=Path,
        help="Verilator --cc directory containing vl_batch_gpu.meta.json",
    )
    parser.add_argument("--cubin", type=Path, help="Path to vl_batch_gpu.cubin")
    parser.add_argument("--storage-size", type=int, help="Bytes per state (AoS stride)")
    parser.add_argument("--nstates", type=int, default=4096, help="Parallel states (default 4096)")
    parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Repeat patch+launch cycle (default 1)",
    )
    parser.add_argument("--block-size", type=int, default=256, help="CUDA block size (default 256)")
    parser.add_argument(
        "--patch",
        action="append",
        default=[],
        metavar="GLOBAL_OFF:BYTE",
        help="Per-step HtoD patch (repeatable); byte decimal or 0xNN; @STATE:LOCAL_OFF:BYTE is also accepted",
    )


def add_state_io_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--patch-script",
        type=Path,
        help=(
            "Optional text file with one patch step per non-comment line. "
            "Each token uses GLOBAL_OFF:BYTE or @STATE:LOCAL_OFF:BYTE syntax."
        ),
    )
    parser.add_argument(
        "--dump-state",
        type=Path,
        help="Optional raw binary dump of final device storage after all launches",
    )
    parser.add_argument(
        "--init-state",
        type=Path,
        help="Optional raw binary state image uploaded before any patches/launches",
    )
    parser.add_argument(
        "--sanitize-host-only-internals",
        action="store_true",
        help=(
            "Rewrite host-only internal fields in --init-state before upload. "
            "Currently sanitizes __VdlySched tail bytes plus transient "
            "Verilator trigger/phase bookkeeping, and zeros vlNamep / "
            "__VdlyCommitQueue* / probable *_path fields when present."
        ),
    )
    parser.add_argument(
        "--schedule-lowering-plan",
        type=Path,
        help=(
            "Optional validated schedule-lowering JSON artifact. The launcher "
            "applies its runtime env overrides before invoking the hybrid runtime."
        ),
    )
    parser.add_argument(
        "--allow-ordering-aware-token-loop-probe-plan",
        action="store_true",
        help=(
            "Permit an ordering-aware token-loop lowering plan only as a "
            "probe-only ABI env source. This does not enable schedule-integrated "
            "runtime execution or correctness claims."
        ),
    )


def add_kernel_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cubins",
        help=(
            "Optional comma-separated cubin paths. The first path is passed as "
            "the legacy runner argv[1]; the full list is forwarded through "
            "RUN_VL_HYBRID_CUBINS."
        ),
    )
    parser.add_argument(
        "--kernels",
        help="Optional comma-separated kernel override; bypasses meta launch_sequence when set",
    )
    parser.add_argument(
        "--trace-stages",
        action="store_true",
        help="Emit stage trace lines from the CUDA runner to help localize module-load vs launch failures.",
    )
    parser.add_argument(
        "--module-load-symbol-check",
        help=(
            "Load the CUDA module chain and require this function symbol, then "
            "exit before allocation or kernel launch."
        ),
    )


def add_resident_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--resident-steps",
        action="store_true",
        help=(
            "Keep batched state resident on device across repeated eval steps. "
            "Rejects argv --patch; --patch-script is uploaded once as a device-resident schedule."
        ),
    )
    parser.add_argument(
        "--gpu-replicate-init-state",
        action="store_true",
        help=(
            "When --init-state is one storage image and nstates > 1, upload it once "
            "and replicate it across device state storage with vl_replicate_init_state_gpu."
        ),
    )
    parser.add_argument(
        "--feedback-edges",
        help=(
            "Optional resident feedback edge table as SRC_LOCAL:DST_LOCAL pairs "
            "separated by commas. Requires --resident-steps and a generated "
            "vl_apply_feedback_edges_gpu kernel."
        ),
    )
    parser.add_argument(
        "--feedback-increments",
        help=(
            "Optional resident feedback increment table as OFFSET_LOCAL:DELTA_BYTE "
            "pairs separated by commas. Requires --resident-steps and a generated "
            "vl_apply_feedback_increments_gpu kernel."
        ),
    )
    parser.add_argument(
        "--feedback-phase-sets",
        help=(
            "Optional persistent resident phase set table as PHASE:OFFSET_LOCAL:BYTE "
            "or @STATE:PHASE:OFFSET_LOCAL:BYTE records separated by commas. "
            "Requires --resident-steps, multi-phase persistent resident ABI mode, "
            "and a generated vl_apply_feedback_sets_gpu kernel."
        ),
    )
    parser.add_argument(
        "--feedback-edge-mode",
        choices=("phase", "step"),
        default=None,
        help=(
            "Launch feedback edges after each persistent resident phase or after "
            "each logical step. Defaults to phase for multi-phase persistent ABI, "
            "otherwise step."
        ),
    )


def add_persistent_resident_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--persistent-resident-state-abi-handle",
        help=(
            "Logical persistent resident state handle for ABI probing. "
            "Phase 1 may use --init-state; later phases must not reload a previous GPU dump."
        ),
    )
    parser.add_argument(
        "--persistent-resident-state-abi-phase",
        type=int,
        help="1-based persistent resident state ABI probe phase.",
    )
    parser.add_argument(
        "--persistent-resident-state-abi-phases",
        type=int,
        help="Run multiple persistent resident ABI phases inside one process.",
    )
    parser.add_argument(
        "--persistent-resident-state-abi-phase-dumps",
        help="Comma-separated per-phase state dump paths for multi-phase persistent ABI mode.",
    )


def add_timing_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--timing-repeats",
        type=int,
        default=1,
        help=(
            "Repeat GPU-event timing samples inside one process. Values above 1 are "
            "limited by the C runner to zero-init, no-patch, non-resident captures."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run hybrid GPU launch (vl_eval_batch_gpu)")
    add_basic_args(parser)
    add_state_io_args(parser)
    add_kernel_args(parser)
    add_resident_args(parser)
    add_persistent_resident_args(parser)
    add_timing_args(parser)
    return parser
