from __future__ import annotations

from pathlib import Path
from typing import Sequence

try:
    from .check_staged_large_files_paths import count_lines, forbidden_source_paths, is_guarded_contract_test_path
    from .check_staged_large_files_types import ContractTestChange, FileSize, GuardInput
    from .check_staged_large_files_inputs import filesystem_guard_input_from_parts
except ImportError:  # pragma: no cover - exercised when run as a script.
    from check_staged_large_files_paths import count_lines, forbidden_source_paths, is_guarded_contract_test_path
    from check_staged_large_files_types import ContractTestChange, FileSize, GuardInput
    from check_staged_large_files_inputs import filesystem_guard_input_from_parts


def filesystem_file_sizes(paths: Sequence[str]) -> list[FileSize]:
    entries: list[FileSize] = []
    for path_text in paths:
        path = Path(path_text)
        if path.is_file():
            entries.append(FileSize(path=path_text, size_bytes=path.stat().st_size))
    return entries


def contract_test_changes_from_files(files: Sequence[FileSize]) -> list[ContractTestChange]:
    return [
        ContractTestChange(
            path=entry.path,
            added_lines=0,
            deleted_lines=0,
            total_lines=count_lines(Path(entry.path).read_bytes()),
        )
        for entry in files
        if is_guarded_contract_test_path(entry.path) and Path(entry.path).is_file()
    ]


def filesystem_input_for_guard(paths: Sequence[str]) -> GuardInput:
    files = filesystem_file_sizes(paths)
    return filesystem_guard_input_from_parts(
        files=files,
        forbidden_paths=forbidden_source_paths(entry.path for entry in files),
        contract_test_changes=contract_test_changes_from_files(files),
    )
