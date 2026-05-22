"""Hybrid launch helpers used by phase-debug comparison."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RUN_VL_HYBRID = SCRIPT_DIR / "run_vl_hybrid.py"


def run_hybrid(
    *,
    mdir: Path | None,
    cubin: Path | None,
    storage_size: int,
    nstates: int,
    steps: int,
    block_size: int,
    dump_state: Path,
    patches: list[str],
    kernels: list[str] | None = None,
) -> None:
    cmd = [sys.executable, str(RUN_VL_HYBRID)]
    if mdir is not None:
        cmd.extend(["--mdir", str(mdir)])
    else:
        assert cubin is not None
        cmd.extend(["--cubin", str(cubin), "--storage-size", str(storage_size)])
    cmd.extend(
        [
            "--nstates",
            str(nstates),
            "--steps",
            str(steps),
            "--block-size",
            str(block_size),
            "--dump-state",
            str(dump_state),
        ]
    )
    if kernels is not None:
        cmd.extend(["--kernels", ",".join(kernels)])
    for patch in patches:
        cmd.extend(["--patch", patch])
    subprocess.run(cmd, check=True)


def run_phase_prefix(
    *,
    tmpdir: Path,
    split_path: Path,
    storage_size: int,
    prefix_index: int,
    kernels: list[str],
    args: argparse.Namespace,
) -> Path:
    prefix_dump = tmpdir / f"split_prefix_{prefix_index}.bin"
    run_hybrid(
        mdir=None,
        cubin=split_path,
        storage_size=storage_size,
        nstates=args.nstates,
        steps=args.steps,
        block_size=args.block_size,
        dump_state=prefix_dump,
        patches=args.patch,
        kernels=kernels,
    )
    return prefix_dump
