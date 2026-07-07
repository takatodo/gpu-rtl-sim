#!/usr/bin/env python3
"""
run_vl_hybrid.py — launch vl_eval_batch_gpu via artifacts/tool_bins/hybrid/run_vl_hybrid.

Requires: build_vl_gpu.py output (cubin + vl_batch_gpu.meta.json).
The runtime binary is built on demand when missing after a clean.

Usage:
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> [--nstates N] [--steps S] [--patch O:V ...]
  python3 run_vl_hybrid.py --cubin path.cubin --storage-size BYTES --nstates N [--steps S] ...
  python3 run_vl_hybrid.py --cubins a.cubin,b.cubin --storage-size BYTES --kernels k0,k1
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --dump-state out.bin
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --init-state init.bin
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --patch-script steps.txt
  python3 run_vl_hybrid.py --cubin path.cubin --storage-size BYTES --kernels k0,k1,k2
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --trace-stages
  python3 run_vl_hybrid.py --mdir <verilator-cc-dir> --resident-steps --schedule-lowering-plan plan.json --allow-ordering-aware-token-loop-probe-plan
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from results_reproduction_io import sanitize_local_absolute_paths
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


def _write_sanitized(text: str | None, stream) -> None:
    if not text:
        return
    stream.write(sanitize_local_absolute_paths(text))
    stream.flush()


def _gpu_runtime_failure_note(*parts: str | None) -> str:
    text = sanitize_local_absolute_paths("\n".join(part for part in parts if part))
    for line in text.splitlines():
        if any(key in line for key in ("gpu_runtime_unavailable", "CUDA error", "cuInit")):
            return "; classified_failure: gpu_runtime_unavailable: " + line.strip()
    return ""


def _run_hybrid_runtime(cmd: list[str], env: dict[str, str]) -> int:
    timeout_text = os.environ.get("RUN_VL_HYBRID_RUNTIME_TIMEOUT_SECONDS")
    timeout_seconds = float(timeout_text) if timeout_text else None
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        _write_sanitized(stdout, sys.stdout)
        _write_sanitized(stderr, sys.stderr)
        print(
            f"error: hybrid runtime timed out after {timeout_seconds:g}s",
            file=sys.stderr,
        )
        return 124
    _write_sanitized(completed.stdout, sys.stdout)
    _write_sanitized(completed.stderr, sys.stderr)
    if completed.returncode != 0:
        note = _gpu_runtime_failure_note(completed.stderr, completed.stdout)
        print(f"error: hybrid runtime failed with exit code {completed.returncode}{note}", file=sys.stderr)
    return completed.returncode


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)
    resolution = resolve_launch_inputs(parser, args)
    require_launch_files(resolution)
    cmd = build_runner_command(args, resolution)
    print(sanitize_local_absolute_paths(" ".join(cmd)))
    env = configure_launch_env(args, resolution)
    sanitized_init_tmp = prepare_init_state_env(parser, args, resolution, env)
    try:
        returncode = _run_hybrid_runtime(cmd, env)
    except FileNotFoundError:
        print(f"error: hybrid runtime command not found: {cmd[0]}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        note = _gpu_runtime_failure_note(exc.stderr, exc.output)
        print(f"error: hybrid runtime failed with exit code {exc.returncode}{note}", file=sys.stderr)
        sys.exit(exc.returncode)
    finally:
        if sanitized_init_tmp is not None:
            sanitized_init_tmp.unlink(missing_ok=True)
    if returncode != 0:
        sys.exit(returncode)


if __name__ == "__main__":
    main()
