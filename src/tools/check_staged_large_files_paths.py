"""Pure path and git-output parsing helpers for the large-file guard."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

try:
    from .check_staged_large_files_types import GitSizeCheckError, LineDelta, RawDiffEntry
except ImportError:  # pragma: no cover - exercised when run as a script.
    from check_staged_large_files_types import GitSizeCheckError, LineDelta, RawDiffEntry


FORBIDDEN_SOURCE_PREFIXES = ("artifacts/",)
TOOL_SCRIPT_PREFIX = "src/tools/"
HOOK_SCRIPT_PREFIX = ".githooks/"
CONTRACT_TEST_PREFIX = "tests/contract/"


def repo_relative_path(path_text: str, *, cwd: Path | None = None) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        return path.as_posix().removeprefix("./")

    root = (cwd or Path.cwd()).resolve()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def forbidden_source_paths(paths: Iterable[str]) -> list[str]:
    return sorted(
        path
        for path in paths
        if repo_relative_path(path).startswith(FORBIDDEN_SOURCE_PREFIXES)
    )


def is_guarded_script_path(path_text: str) -> bool:
    path = repo_relative_path(path_text)
    return (path.startswith(TOOL_SCRIPT_PREFIX) and path.endswith(".py")) or (
        path.startswith(HOOK_SCRIPT_PREFIX) and (path.endswith(".sh") or Path(path).name == "pre-commit")
    )


def is_guarded_contract_test_path(path_text: str) -> bool:
    path = repo_relative_path(path_text)
    name = Path(path).name
    return path.startswith(CONTRACT_TEST_PREFIX) and name.startswith("test_") and name.endswith(".py")


def parse_raw_diff_entries(raw_output: bytes) -> list[RawDiffEntry]:
    entries: list[RawDiffEntry] = []
    records = [record for record in raw_output.split(b"\0") if record]
    index = 0
    while index < len(records):
        header = records[index].decode("utf-8", errors="replace")
        fields = header.split()
        if len(fields) < 5:
            raise GitSizeCheckError(f"could not parse git diff raw header: {header!r}")
        status = fields[4]
        path_record_count = 2 if status.startswith(("R", "C")) else 1
        if index + path_record_count >= len(records):
            raise GitSizeCheckError(f"missing path record for git diff raw header: {header!r}")

        old_path: str | None = None
        path_record = records[index + 1]
        if path_record_count == 2:
            old_path = path_record.decode("utf-8", errors="replace")
            path_record = records[index + 2]
        entries.append(
            RawDiffEntry(
                old_mode=fields[0].lstrip(":"),
                new_mode=fields[1],
                old_object_id=fields[2],
                new_object_id=fields[3],
                status=status,
                old_path=old_path,
                path=path_record.decode("utf-8", errors="replace"),
            )
        )
        index += 1 + path_record_count
    return entries


def parse_numstat_records(raw_output: bytes) -> list[LineDelta]:
    deltas: list[LineDelta] = []
    records = [record for record in raw_output.split(b"\0") if record]
    index = 0
    while index < len(records):
        fields = records[index].decode("utf-8", errors="replace").split("\t")
        index += 1
        if len(fields) < 3:
            raise GitSizeCheckError(f"could not parse git diff numstat record: {fields!r}")
        added_text, _deleted_text, path = fields[:3]
        if len(fields) == 3 and path == "":
            if index + 1 >= len(records):
                raise GitSizeCheckError(f"missing path record for git diff numstat record: {fields!r}")
            path = records[index + 1].decode("utf-8", errors="replace")
            index += 2
        try:
            added_lines = int(added_text)
        except ValueError:
            added_lines = 0
        try:
            deleted_lines = int(_deleted_text)
        except ValueError:
            deleted_lines = 0
        deltas.append(LineDelta(path=path, added_lines=added_lines, deleted_lines=deleted_lines))
    return deltas


def count_lines(content: bytes) -> int:
    if not content:
        return 0
    newline_count = content.count(b"\n")
    return newline_count if content.endswith(b"\n") else newline_count + 1


def unique_in_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
