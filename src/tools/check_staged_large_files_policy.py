from __future__ import annotations

from collections.abc import Iterable

try:
    from .check_staged_large_files_types import (
        ContractTestChange,
        FileSize,
        GuardFailures,
        GuardInput,
        GuardThresholds,
        ScriptGrowth,
        ScriptSize,
    )
except ImportError:  # pragma: no cover - exercised when run as a script dependency.
    from check_staged_large_files_types import (
        ContractTestChange,
        FileSize,
        GuardFailures,
        GuardInput,
        GuardThresholds,
        ScriptGrowth,
        ScriptSize,
    )


def oversized_files(files: Iterable[FileSize], max_bytes: int) -> list[FileSize]:
    return sorted(
        (entry for entry in files if entry.size_bytes > max_bytes),
        key=lambda entry: (-entry.size_bytes, entry.path),
    )


def oversized_script_growth(growth: Iterable[ScriptGrowth], max_added_lines: int) -> list[ScriptGrowth]:
    return sorted(
        (entry for entry in growth if entry.added_lines > max_added_lines),
        key=lambda entry: (-entry.added_lines, entry.path),
    )


def oversized_script_sizes(sizes: Iterable[ScriptSize], max_total_lines: int) -> list[ScriptSize]:
    return sorted(
        (entry for entry in sizes if entry.total_lines > max_total_lines),
        key=lambda entry: (-entry.total_lines, entry.path),
    )


def oversized_contract_test_changes(
    changes: Iterable[ContractTestChange],
    *,
    max_added_lines: int,
    max_total_lines: int,
) -> list[ContractTestChange]:
    return sorted(
        (
            entry
            for entry in changes
            if entry.added_lines >= entry.deleted_lines
            and (entry.added_lines > max_added_lines or entry.total_lines > max_total_lines)
        ),
        key=lambda entry: (-entry.total_lines, -entry.added_lines, entry.path),
    )


def collect_failures(guard_input: GuardInput, thresholds: GuardThresholds) -> GuardFailures:
    return GuardFailures(
        files=oversized_files(guard_input.files, thresholds.max_bytes),
        forbidden_paths=guard_input.forbidden_paths,
        script_growth=oversized_script_growth(
            guard_input.script_growth,
            thresholds.max_script_added_lines,
        ),
        script_sizes=oversized_script_sizes(
            guard_input.script_sizes,
            thresholds.max_script_total_lines,
        ),
        contract_tests=oversized_contract_test_changes(
            guard_input.contract_test_changes,
            max_added_lines=thresholds.max_contract_test_added_lines,
            max_total_lines=thresholds.max_contract_test_total_lines,
        ),
        staged_count_exceeded=guard_input.staged_count > thresholds.max_files,
        new_script_count_exceeded=guard_input.new_script_count > thresholds.max_new_script_files,
    )
