from __future__ import annotations

import subprocess
from typing import Callable, Sequence

try:
    from .check_staged_large_files_paths import (
        count_lines,
        is_guarded_contract_test_path,
        is_guarded_script_path,
    )
    from . import check_staged_large_files_git_diff as _git_diff
    from . import check_staged_large_files_git_objects as _git_objects
    from .check_staged_large_files_types import (
        ContractTestChange,
        GitSizeCheckError,
        LineDelta,
        ScriptGrowth,
        ScriptSize,
        StagedBlob,
    )
except ImportError:  # pragma: no cover - exercised when run as a script.
    from check_staged_large_files_paths import (
        count_lines,
        is_guarded_contract_test_path,
        is_guarded_script_path,
    )
    import check_staged_large_files_git_diff as _git_diff
    import check_staged_large_files_git_objects as _git_objects
    from check_staged_large_files_types import (
        ContractTestChange,
        GitSizeCheckError,
        LineDelta,
        ScriptGrowth,
        ScriptSize,
        StagedBlob,
    )


def stderr_text(stderr: bytes | str) -> str:
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace").strip()
    return stderr.strip()


def staged_blobs() -> list[StagedBlob]:
    _git_diff.subprocess = subprocess
    return _git_diff.staged_blobs()


def staged_line_deltas(*, diff_filter: str) -> list[LineDelta]:
    _git_diff.subprocess = subprocess
    return _git_diff.staged_line_deltas(diff_filter=diff_filter)


def staged_script_growth() -> list[ScriptGrowth]:
    _git_diff.subprocess = subprocess
    return _git_diff.staged_script_growth()


def staged_new_script_count() -> int:
    _git_diff.subprocess = subprocess
    return _git_diff.staged_new_script_count()


def staged_line_sizes(blobs: Sequence[StagedBlob], path_predicate: Callable[[str], bool]) -> list[ScriptSize]:
    sizes: list[ScriptSize] = []
    for blob in blobs:
        if blob.object_id is None or not path_predicate(blob.path):
            continue
        result = subprocess.run(
            ["git", "cat-file", "-p", blob.object_id],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            detail = stderr_text(result.stderr) or f"git cat-file failed for {blob.path}"
            raise GitSizeCheckError(detail)
        sizes.append(ScriptSize(path=blob.path, total_lines=count_lines(result.stdout)))
    return sizes


def staged_script_sizes(blobs: Sequence[StagedBlob]) -> list[ScriptSize]:
    return staged_line_sizes(blobs, is_guarded_script_path)


def staged_contract_test_changes(blobs: Sequence[StagedBlob]) -> list[ContractTestChange]:
    total_lines_by_path = {
        entry.path: entry.total_lines
        for entry in staged_line_sizes(blobs, is_guarded_contract_test_path)
    }
    deltas_by_path = {
        entry.path: entry
        for entry in staged_line_deltas(diff_filter="ACMRT")
        if is_guarded_contract_test_path(entry.path)
    }

    changes: list[ContractTestChange] = []
    for path in sorted(total_lines_by_path):
        delta = deltas_by_path.get(path, LineDelta(path=path, added_lines=0, deleted_lines=0))
        changes.append(
            ContractTestChange(
                path=path,
                added_lines=delta.added_lines,
                deleted_lines=delta.deleted_lines,
                total_lines=total_lines_by_path[path],
            )
        )
    return changes


def batch_object_sizes(object_ids: Sequence[str]) -> list[int]:
    _git_objects.subprocess = subprocess
    return _git_objects.batch_object_sizes(object_ids)


def batch_object_size_map(object_ids: Sequence[str]) -> dict[str, int]:
    _git_objects.subprocess = subprocess
    return _git_objects.batch_object_size_map(object_ids)
