"""GuardInput assembly helpers for large-file commit checks."""

from __future__ import annotations

from collections.abc import Sequence

try:
    from .check_staged_large_files_types import (
        ContractTestChange,
        FileSize,
        GuardInput,
        ScriptGrowth,
        ScriptSize,
        StagedBlob,
    )
except ImportError:  # pragma: no cover - exercised when run as a script dependency.
    from check_staged_large_files_types import (
        ContractTestChange,
        FileSize,
        GuardInput,
        ScriptGrowth,
        ScriptSize,
        StagedBlob,
    )


def staged_guard_input_from_parts(
    *,
    blobs: Sequence[StagedBlob],
    max_files: int,
    forbidden_paths: list[str],
    script_growth: list[ScriptGrowth],
    new_script_count: int,
    script_sizes: list[ScriptSize],
    contract_test_changes: list[ContractTestChange],
    size_by_object: dict[str, int],
) -> GuardInput:
    staged_count = len(blobs)
    if staged_count > max_files or forbidden_paths:
        return GuardInput(
            files=[],
            staged_count=staged_count,
            forbidden_paths=forbidden_paths,
            script_growth=script_growth,
            new_script_count=new_script_count,
            script_sizes=script_sizes,
            contract_test_changes=contract_test_changes,
        )

    sizable_blobs = [blob for blob in blobs if blob.object_id is not None]
    return GuardInput(
        files=[FileSize(path=blob.path, size_bytes=size_by_object[blob.object_id]) for blob in sizable_blobs],
        staged_count=staged_count,
        forbidden_paths=[],
        script_growth=script_growth,
        new_script_count=new_script_count,
        script_sizes=script_sizes,
        contract_test_changes=contract_test_changes,
    )


def filesystem_guard_input_from_parts(
    *,
    files: Sequence[FileSize],
    forbidden_paths: list[str],
    contract_test_changes: list[ContractTestChange],
) -> GuardInput:
    return GuardInput(
        files=list(files),
        staged_count=len(files),
        forbidden_paths=forbidden_paths,
        script_growth=[],
        new_script_count=0,
        script_sizes=[],
        contract_test_changes=contract_test_changes,
    )
