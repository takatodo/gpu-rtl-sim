from __future__ import annotations

import subprocess

try:
    from .check_staged_large_files_paths import (
        is_guarded_script_path,
        parse_numstat_records,
        parse_raw_diff_entries,
    )
    from .check_staged_large_files_types import GitSizeCheckError, LineDelta, ScriptGrowth, StagedBlob
except ImportError:  # pragma: no cover - exercised when run as a script.
    from check_staged_large_files_paths import (
        is_guarded_script_path,
        parse_numstat_records,
        parse_raw_diff_entries,
    )
    from check_staged_large_files_types import GitSizeCheckError, LineDelta, ScriptGrowth, StagedBlob


GITLINK_MODE = "160000"


def stderr_text(stderr: bytes | str) -> str:
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace").strip()
    return stderr.strip()


def staged_blobs() -> list[StagedBlob]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--raw", "-z", "--diff-filter=ACMRDT"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = stderr_text(result.stderr) or "git diff --cached --raw failed"
        raise GitSizeCheckError(detail)

    blobs: list[StagedBlob] = []
    for entry in parse_raw_diff_entries(result.stdout):
        if entry.old_mode != GITLINK_MODE and entry.new_mode != GITLINK_MODE:
            object_id = None if entry.status.startswith("D") else entry.new_object_id
            blobs.append(StagedBlob(path=entry.path, object_id=object_id))
    return blobs


def staged_line_deltas(*, diff_filter: str) -> list[LineDelta]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--numstat", "-z", f"--diff-filter={diff_filter}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = stderr_text(result.stderr) or "git diff --cached --numstat failed"
        raise GitSizeCheckError(detail)
    return parse_numstat_records(result.stdout)


def staged_script_growth() -> list[ScriptGrowth]:
    growth: list[ScriptGrowth] = []
    for delta in staged_line_deltas(diff_filter="ACMRT"):
        if is_guarded_script_path(delta.path):
            growth.append(ScriptGrowth(path=delta.path, added_lines=delta.added_lines))
    return growth


def staged_new_script_count() -> int:
    result = subprocess.run(
        ["git", "diff", "--cached", "--raw", "-z", "--diff-filter=ACMR"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = stderr_text(result.stderr) or "git diff --cached --raw failed"
        raise GitSizeCheckError(detail)

    count = 0
    for entry in parse_raw_diff_entries(result.stdout):
        if entry.status.startswith("A") and is_guarded_script_path(entry.path):
            count += 1
        elif entry.status.startswith("C") and is_guarded_script_path(entry.path):
            count += 1
        elif (
            entry.status.startswith("R")
            and entry.old_path is not None
            and is_guarded_script_path(entry.path)
            and not is_guarded_script_path(entry.old_path)
        ):
            count += 1
    return count
