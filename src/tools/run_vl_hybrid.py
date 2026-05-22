#!/usr/bin/env python3
"""
run_vl_hybrid.py — launch vl_eval_batch_gpu via src/hybrid/run_vl_hybrid (Phase D).

Requires: build_vl_gpu.py output (cubin + vl_batch_gpu.meta.json) and `make -C src/hybrid`.

Usage:
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> [--nstates N] [--steps S] [--patch O:V ...]
  python3 run_vl_hybrid.py --cubin path.cubin --storage-size BYTES --nstates N [--steps S] ...
  python3 run_vl_hybrid.py --cubins a.cubin,b.cubin --storage-size BYTES --kernels k0,k1
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --dump-state out.bin
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --init-state init.bin
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --patch-script steps.txt
  python3 run_vl_hybrid.py --cubin path.cubin --storage-size BYTES --kernels k0,k1,k2
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --trace-stages
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from run_vl_hybrid_state_sanitize import (
    _detect_unsupported_nonflat_syms_state,
    _sanitize_host_only_internals_at_root_offset,
)
from run_vl_hybrid_args import (
    build_parser,
    validate_args,
)
from run_vl_hybrid_launch import (
    HYBRID_BIN,
    LaunchResolution,
    build_runner_command,
    configure_kernel_env,
    configure_launch_env,
    configure_persistent_resident_env,
    configure_runtime_mode_env,
    configure_state_io_env,
    prepare_init_state_env,
    require_launch_files,
    resolve_launch_inputs,
)

# WSL2: prefer host libcuda so Driver API sees the GPU (nvidia-smi can work without this).
_WSL_LIBCUDA = Path("/usr/lib/wsl/lib/libcuda.so.1")
if _WSL_LIBCUDA.is_file():
    prefix = "/usr/lib/wsl/lib"
    rest = os.environ.get("LD_LIBRARY_PATH", "")
    if rest and rest != prefix and not rest.startswith(prefix + ":"):
        os.environ["LD_LIBRARY_PATH"] = f"{prefix}:{rest}"
    elif not rest:
        os.environ["LD_LIBRARY_PATH"] = prefix

_PERSISTENT_RESIDENT_PUBLIC_SURFACE = (
    "--persistent-resident-state-abi-handle",
    "--persistent-resident-state-abi-phase",
    "RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_HANDLE",
    "RUN_VL_HYBRID_PERSISTENT_RESIDENT_STATE_PHASE",
    "persistent resident state ABI phases after 1 must not use --init-state",
    "requires --resident-steps",
)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)
    resolution = resolve_launch_inputs(parser, args)
    require_launch_files(resolution)
    cmd = build_runner_command(args, resolution)
    print(" ".join(cmd))
    env = configure_launch_env(args, resolution)
    sanitized_init_tmp = prepare_init_state_env(parser, args, resolution, env)
    try:
        subprocess.run(cmd, check=True, env=env)
    finally:
        if sanitized_init_tmp is not None:
            sanitized_init_tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
