#!/usr/bin/env python3
"""Reject oversized files before they enter normal commits."""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Callable, Sequence

try:
    from .check_staged_large_files_inputs import staged_guard_input_from_parts
    from . import check_staged_large_files_filesystem as _filesystem_input
    from . import check_staged_large_files_git_input as _git_input
    from .check_staged_large_files_public import *  # noqa: F403
except ImportError:  # pragma: no cover - exercised when run as a script.
    from check_staged_large_files_inputs import staged_guard_input_from_parts
    import check_staged_large_files_filesystem as _filesystem_input
    import check_staged_large_files_git_input as _git_input
    from check_staged_large_files_public import *  # noqa: F403


def _sync_git_input_subprocess() -> None:
    _git_input.subprocess = subprocess


def stderr_text(stderr: bytes | str) -> str:
    return _git_input.stderr_text(stderr)


def staged_blobs() -> list[StagedBlob]:
    _sync_git_input_subprocess()
    return _git_input.staged_blobs()


def staged_line_deltas(*, diff_filter: str) -> list[LineDelta]:
    _sync_git_input_subprocess()
    return _git_input.staged_line_deltas(diff_filter=diff_filter)


def staged_script_growth() -> list[ScriptGrowth]:
    _sync_git_input_subprocess()
    return _git_input.staged_script_growth()


def staged_new_script_count() -> int:
    _sync_git_input_subprocess()
    return _git_input.staged_new_script_count()


def staged_line_sizes(blobs: Sequence[StagedBlob], path_predicate: Callable[[str], bool]) -> list[ScriptSize]:
    _sync_git_input_subprocess()
    return _git_input.staged_line_sizes(blobs, path_predicate)


def staged_script_sizes(blobs: Sequence[StagedBlob]) -> list[ScriptSize]:
    return staged_line_sizes(blobs, is_guarded_script_path)


def staged_contract_test_changes(blobs: Sequence[StagedBlob]) -> list[ContractTestChange]:
    _sync_git_input_subprocess()
    return _git_input.staged_contract_test_changes(blobs)


def batch_object_sizes(object_ids: Sequence[str]) -> list[int]:
    _sync_git_input_subprocess()
    return _git_input.batch_object_sizes(object_ids)


def batch_object_size_map(object_ids: Sequence[str]) -> dict[str, int]:
    unique_ids = unique_in_order(object_ids)
    sizes = batch_object_sizes(unique_ids)
    return dict(zip(unique_ids, sizes))


def filesystem_file_sizes(paths: Sequence[str]) -> list[FileSize]:
    return _filesystem_input.filesystem_file_sizes(paths)


def contract_test_changes_from_files(files: Sequence[FileSize]) -> list[ContractTestChange]:
    return _filesystem_input.contract_test_changes_from_files(files)


def staged_files_for_guard(*, max_files: int) -> GuardInput:
    blobs = staged_blobs()
    forbidden_paths = forbidden_source_paths(blob.path for blob in blobs)
    script_growth = staged_script_growth()
    new_script_count = staged_new_script_count()
    script_sizes = staged_script_sizes(blobs)
    contract_test_changes = staged_contract_test_changes(blobs)
    if len(blobs) > max_files or forbidden_paths:
        size_by_object = {}
    else:
        sizable_blobs = [blob for blob in blobs if blob.object_id is not None]
        size_by_object = batch_object_size_map([blob.object_id for blob in sizable_blobs])
    return staged_guard_input_from_parts(
        blobs=blobs,
        max_files=max_files,
        forbidden_paths=forbidden_paths,
        script_growth=script_growth,
        new_script_count=new_script_count,
        script_sizes=script_sizes,
        contract_test_changes=contract_test_changes,
        size_by_object=size_by_object,
    )


def filesystem_input_for_guard(paths: Sequence[str]) -> GuardInput:
    files = filesystem_file_sizes(paths)
    return filesystem_input_from_files(files)


def filesystem_input_from_files(files: Sequence[FileSize]) -> GuardInput:
    return _filesystem_input.filesystem_guard_input_from_parts(
        files=files,
        forbidden_paths=forbidden_source_paths(entry.path for entry in files),
        contract_test_changes=contract_test_changes_from_files(files),
    )


def load_guard_input(args: argparse.Namespace, thresholds: GuardThresholds) -> GuardInput:
    if args.paths is not None:
        return filesystem_input_for_guard(args.paths)
    return staged_files_for_guard(max_files=thresholds.max_files)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        thresholds = resolve_thresholds(args)
    except GitSizeCheckError as exc:
        print(f"pre-commit: invalid commit guard threshold: {exc}", file=sys.stderr)
        return 2
    validate_thresholds(parser, thresholds)

    try:
        guard_input = load_guard_input(args, thresholds)
    except GitSizeCheckError as exc:
        print(f"pre-commit: unable to verify staged file sizes: {exc}", file=sys.stderr)
        return 2

    failures = collect_failures(guard_input, thresholds)
    if not failures.any():
        return 0
    print_failure_report(failures, guard_input, thresholds)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
