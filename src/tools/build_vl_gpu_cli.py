"""Argument parser helpers for build_vl_gpu."""

from __future__ import annotations

import argparse
import os


def add_basic_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('mdir', help='Verilator --cc output directory (contains *_classes.mk)')
    parser.add_argument('--sm', default='sm_89', help='GPU arch (default: sm_89)')
    parser.add_argument('--out', default=None, help='Output cubin path (default: mdir/vl_batch_gpu.cubin)')
    parser.add_argument('--force', action='store_true', help='Re-run all steps even if outputs exist')


def add_optimization_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--clang-O',
        dest='clang_opt',
        default='O1',
        choices=('O0', 'O1', 'O2', 'O3', 'Os', 'Oz'),
        help='clang optimization when emitting .ll (default O1). O2/O3 often shortens GPU _eval.',
    )
    parser.add_argument(
        '--gpu-opt-level',
        default='O3',
        choices=('O0', 'O1', 'O2', 'O3'),
        help=(
            'Optimization after vl_batch_gpu_patched.ll. O0 copies patched.ll directly to '
            'vl_batch_gpu_opt.ll; useful for low-cost validation rebuilds.'
        ),
    )
    parser.add_argument(
        '--ptxas-opt-level',
        type=int,
        choices=(0, 1, 2, 3),
        default=None,
        help='Optional ptxas optimization level override. Use 0 for faster validation builds.',
    )
    parser.add_argument(
        '--emit-ptx-module',
        action='store_true',
        help='Skip ptxas and write meta that points directly at vl_batch_gpu.ptx.',
    )


def add_phase_split_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--analyze-phases',
        action='store_true',
        help='After merged.ll, run vlgpugen --analyze-phases and write mdir/vl_phase_analysis.json; then continue cubin build.',
    )
    parser.add_argument(
        '--kernel-split-phases',
        action='store_true',
        help='Pass --kernel-split=phases to vlgpugen (ico/nba batch kernels + vl_eval_batch_gpu); meta gets launch_sequence.',
    )
    parser.add_argument(
        '--kernel-probe-act-sequent-chunk-size',
        type=int,
        default=0,
        help=(
            'With --kernel-split-phases, emit non-launch act_sequent chunk probe kernels '
            'of this size into vl_kernel_manifest.json.'
        ),
    )
    parser.add_argument(
        '--disable-cfg-clone-diagnostics',
        action='store_true',
        help=(
            'Pass --disable-cfg-clone-diagnostics to vlgpugen so ordering-aware '
            'baseline builds omit CFG-clone counter/shadow diagnostic IR.'
        ),
    )


def add_reuse_and_state_image_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--reuse-gpu-patched-ll',
        action='store_true',
        help='Skip vlgpugen and pass lowering; rebuild from an existing vl_batch_gpu_patched.ll.',
    )
    parser.add_argument(
        '--reuse-ptx',
        action='store_true',
        help='Skip llc/vlgpugen and rebuild only from an existing vl_batch_gpu.ptx.',
    )
    parser.add_argument(
        '--syms-state-image',
        action='store_true',
        help=(
            'Generate a non-flattened Verilator __Syms state-image kernel. '
            'Requires --syms-storage-size and --state-root-offset.'
        ),
    )
    parser.add_argument('--syms-storage-size', type=int, default=None)
    parser.add_argument('--state-root-offset', type=int, default=None)


def add_parallelism_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--jobs',
        type=int,
        default=int(os.environ.get('BUILD_VL_GPU_JOBS', '1')),
        help='Parallel clang emission jobs for .cpp -> .ll (default: $BUILD_VL_GPU_JOBS or 1).',
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Verilator --cc output dir → GPU cubin')
    add_basic_options(parser)
    add_optimization_options(parser)
    add_phase_split_options(parser)
    add_reuse_and_state_image_options(parser)
    add_parallelism_options(parser)
    return parser
