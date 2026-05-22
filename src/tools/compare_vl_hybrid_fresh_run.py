"""Fresh single-vs-split comparison orchestration."""

from __future__ import annotations

import argparse
import tempfile
from contextlib import nullcontext
from pathlib import Path

from compare_vl_hybrid_fresh import build_fresh_run_artifacts
from compare_vl_hybrid_phase_debug import add_phase_debug_if_available
from compare_vl_hybrid_state_compare import compare_state_dumps
from compare_vl_hybrid_summary import (
    emit_comparison_summary,
    finalize_fresh_run_summary,
)


def run_fresh_comparison_in_tmpdir(
    args: argparse.Namespace,
    *,
    mdir: Path,
    tmpdir: Path,
) -> int:
    artifacts = build_fresh_run_artifacts(args, mdir=mdir, tmpdir=tmpdir)
    summary = compare_state_dumps(
        artifacts.single_dump,
        artifacts.split_dump,
        artifacts.storage_size,
        layout=artifacts.layout,
    )
    launch_sequence = add_phase_debug_if_available(
        summary=summary,
        tmpdir=tmpdir,
        mdir=mdir,
        single_dump=artifacts.single_dump,
        split_path=artifacts.split_path,
        storage_size=artifacts.storage_size,
        layout=artifacts.layout,
        args=args,
    )
    finalize_fresh_run_summary(
        summary=summary,
        mdir=mdir,
        single_path=artifacts.single_path,
        split_path=artifacts.split_path,
        launch_sequence=launch_sequence,
        layout=artifacts.layout,
        single_dump=artifacts.single_dump,
        split_dump=artifacts.split_dump,
        args=args,
    )
    return emit_comparison_summary(summary, json_out=args.json_out)


def run_fresh_comparison(args: argparse.Namespace, *, mdir: Path) -> int:
    dump_ctx = (
        nullcontext(args.dump_dir.resolve())
        if args.dump_dir is not None
        else tempfile.TemporaryDirectory(prefix="vl_hybrid_compare_")
    )
    with dump_ctx as tmp:
        return run_fresh_comparison_in_tmpdir(args, mdir=mdir, tmpdir=Path(tmp))
