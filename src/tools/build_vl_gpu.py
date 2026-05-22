#!/usr/bin/env python3
"""
build_vl_gpu.py
Verilator --cc 出力ディレクトリから GPU cubin を自動生成する。

Usage:
  python3 build_vl_gpu.py <mdir> [--sm sm_89] [--out out.cubin] [--force]
  python3 build_vl_gpu.py <mdir> [--ptxas-opt-level 0]
  python3 build_vl_gpu.py <mdir> [--emit-ptx-module]
  python3 build_vl_gpu.py <mdir> [--reuse-gpu-patched-ll] [--gpu-opt-level O0]
  python3 build_vl_gpu.py <mdir> [--reuse-ptx] [--ptxas-opt-level 0]
  python3 build_vl_gpu.py <mdir> --kernel-split-phases --kernel-probe-act-sequent-chunk-size N
  python3 build_vl_gpu.py <mdir> --syms-state-image --syms-storage-size N --state-root-offset N

Steps:
  1. {mdir}/*_classes.mk から VM_CLASSES_FAST + VM_CLASSES_SLOW を読み込む
  2. 各 .cpp を clang++-18 -std=c++20 -S -emit-llvm (-O1 既定、--clang-O で変更) → .ll
  3. llvm-link-18 → merged.ll
  4. C++ probe で storage_size (sizeof root struct) を自動検出
  5. vlgpugen merged.ll --storage-size=N → vl_batch_gpu.ll
     (or Syms image mode: --storage-size=<sizeof __Syms> --state-root-offset=<root offset>)
  6. opt (lowerinvoke,simplifycfg,vl-strip-x86-attrs,vl-stub-host-io-calls,vl-stub-timing-scheduler-context,vl-patch-convergence,cleanup) → patched
  7. host cleanup → optional opt → vl-sanitize-host-io-null-writes → vl_batch_gpu_opt.ll → optional VlWide lifetime retiming → llc-18 → vl_batch_gpu.ptx → ptxas → vl_batch_gpu.cubin
     (or skip ptxas and use vl_batch_gpu.ptx directly when --emit-ptx-module is set)
  8. vl_classifier_report.json (reachable GPU/runtime placement report)
  9. vl_batch_gpu.meta.json (schema_version, cubin/module path, storage_size, sm, kernel, classifier_report)
"""

import argparse
from pathlib import Path

from build_vl_gpu_cli import build_arg_parser
from build_vl_gpu_hierarchy import detect_hierarchy_state_metadata
from build_vl_gpu_inputs import (
    CLANG,
    CXX_STANDARD,
    find_prefix,
    verilator_include_dir,
)
from build_vl_gpu_orchestration import run_build_request
from build_vl_gpu_types import BuildRequest


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_vl_gpu(
    mdir: Path,
    sm: str = 'sm_89',
    out_cubin: Path = None,
    force: bool = False,
    clang_opt: str = 'O1',
    gpu_opt_level: str = 'O3',
    ptxas_opt_level: int | None = None,
    emit_ptx_module: bool = False,
    analyze_phases: bool = False,
    kernel_split_phases: bool = False,
    kernel_probe_act_sequent_chunk_size: int = 0,
    reuse_gpu_patched_ll: bool = False,
    reuse_ptx: bool = False,
    syms_state_image: bool = False,
    syms_storage_size: int | None = None,
    state_root_offset: int | None = None,
    jobs: int = 1,
) -> tuple[Path, int]:

    request = BuildRequest(
        sm=sm,
        out_cubin=out_cubin,
        force=force,
        clang_opt=clang_opt,
        gpu_opt_level=gpu_opt_level,
        ptxas_opt_level=ptxas_opt_level,
        emit_ptx_module=emit_ptx_module,
        analyze_phases=analyze_phases,
        kernel_split_phases=kernel_split_phases,
        kernel_probe_act_sequent_chunk_size=kernel_probe_act_sequent_chunk_size,
        reuse_gpu_patched_ll=reuse_gpu_patched_ll,
        reuse_ptx=reuse_ptx,
        syms_state_image=syms_state_image,
        syms_storage_size=syms_storage_size,
        state_root_offset=state_root_offset,
        jobs=jobs,
    )

    return run_build_request(mdir, request)


def build_request_from_args(args: argparse.Namespace) -> BuildRequest:
    return BuildRequest(
        sm=args.sm,
        out_cubin=Path(args.out) if args.out else None,
        force=args.force,
        clang_opt=args.clang_opt,
        gpu_opt_level=args.gpu_opt_level,
        ptxas_opt_level=args.ptxas_opt_level,
        emit_ptx_module=args.emit_ptx_module,
        analyze_phases=args.analyze_phases,
        kernel_split_phases=args.kernel_split_phases,
        kernel_probe_act_sequent_chunk_size=args.kernel_probe_act_sequent_chunk_size,
        reuse_gpu_patched_ll=args.reuse_gpu_patched_ll,
        reuse_ptx=args.reuse_ptx,
        syms_state_image=args.syms_state_image,
        syms_storage_size=args.syms_storage_size,
        state_root_offset=args.state_root_offset,
        jobs=args.jobs,
    )


def main():
    args = build_arg_parser().parse_args()
    request = build_request_from_args(args)
    cubin, sz = run_build_request(Path(args.mdir), request)
    print(f'\nstorage_size={sz}')
    print(f'cubin={cubin}')


if __name__ == '__main__':
    main()
