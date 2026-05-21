from __future__ import annotations

import sys

try:
    from .check_staged_large_files_settings import (
        MAX_BYTES_ENV,
        MAX_CONTRACT_TEST_ADDED_LINES_ENV,
        MAX_CONTRACT_TEST_TOTAL_LINES_ENV,
        MAX_NEW_SCRIPT_FILES_ENV,
        MAX_SCRIPT_ADDED_LINES_ENV,
        MAX_SCRIPT_TOTAL_LINES_ENV,
        MAX_STAGED_FILES_ENV,
    )
    from .check_staged_large_files_types import GuardFailures, GuardInput, GuardThresholds
except ImportError:  # pragma: no cover - exercised when run as a script dependency.
    from check_staged_large_files_settings import (
        MAX_BYTES_ENV,
        MAX_CONTRACT_TEST_ADDED_LINES_ENV,
        MAX_CONTRACT_TEST_TOTAL_LINES_ENV,
        MAX_NEW_SCRIPT_FILES_ENV,
        MAX_SCRIPT_ADDED_LINES_ENV,
        MAX_SCRIPT_TOTAL_LINES_ENV,
        MAX_STAGED_FILES_ENV,
    )
    from check_staged_large_files_types import GuardFailures, GuardInput, GuardThresholds


def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MiB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KiB"
    return f"{size_bytes} B"


def print_oversized_file_failures(failures: GuardFailures, thresholds: GuardThresholds) -> None:
    if failures.files:
        print(
            f"pre-commit: files larger than {format_size(thresholds.max_bytes)} are not allowed in normal commits.",
            file=sys.stderr,
        )
        for entry in failures.files:
            print(f"  {entry.path}: {format_size(entry.size_bytes)}", file=sys.stderr)


def print_forbidden_path_failures(failures: GuardFailures) -> None:
    if failures.forbidden_paths:
        print("pre-commit: artifacts/ is generated output and is not allowed in normal source commits.", file=sys.stderr)
        for path in failures.forbidden_paths:
            print(f"  {path}", file=sys.stderr)


def print_count_failures(
    failures: GuardFailures,
    guard_input: GuardInput,
    thresholds: GuardThresholds,
) -> None:
    if failures.staged_count_exceeded:
        print(
            "pre-commit: "
            f"{guard_input.staged_count} staged files exceeds the review-sized commit limit of {thresholds.max_files}.",
            file=sys.stderr,
        )
    if failures.new_script_count_exceeded:
        print(
            "pre-commit: "
            f"{guard_input.new_script_count} new guarded scripts exceeds the limit of "
            f"{thresholds.max_new_script_files}.",
            file=sys.stderr,
        )


def print_script_failures(failures: GuardFailures, thresholds: GuardThresholds) -> None:
    if failures.script_growth:
        print(
            "pre-commit: guarded scripts are growing too much in one commit "
            f"(limit {thresholds.max_script_added_lines} added lines per script).",
            file=sys.stderr,
        )
        for entry in failures.script_growth:
            print(f"  {entry.path}: +{entry.added_lines} lines", file=sys.stderr)
    if failures.script_sizes:
        print(
            "pre-commit: guarded scripts exceed the total line budget "
            f"(limit {thresholds.max_script_total_lines} lines per script).",
            file=sys.stderr,
        )
        for entry in failures.script_sizes:
            print(f"  {entry.path}: {entry.total_lines} lines", file=sys.stderr)


def print_contract_test_failures(failures: GuardFailures, thresholds: GuardThresholds) -> None:
    if failures.contract_tests:
        print(
            "pre-commit: guarded contract tests are too large or growing too much "
            f"(limits {thresholds.max_contract_test_total_lines} total lines and "
            f"{thresholds.max_contract_test_added_lines} added lines while not shrinking).",
            file=sys.stderr,
        )
        for entry in failures.contract_tests:
            print(
                f"  {entry.path}: {entry.total_lines} lines, "
                f"+{entry.added_lines}/-{entry.deleted_lines}",
                file=sys.stderr,
            )


def print_failure_guidance() -> None:
    print(
        "Keep generated or bulky data out of normal source commits; "
        "leave local artifacts uncommitted, use reviewed reports/ snapshots or external storage when needed, "
        "keep scripts and contract tests small by moving reusable logic into shared modules, "
        "and commit source changes in smaller batches. "
        f"Reviewed local overrides: {MAX_BYTES_ENV}=<bytes>, {MAX_STAGED_FILES_ENV}=<count>, "
        f"{MAX_SCRIPT_ADDED_LINES_ENV}=<lines>, {MAX_SCRIPT_TOTAL_LINES_ENV}=<lines>, "
        f"{MAX_NEW_SCRIPT_FILES_ENV}=<count>, {MAX_CONTRACT_TEST_ADDED_LINES_ENV}=<lines>, "
        f"or {MAX_CONTRACT_TEST_TOTAL_LINES_ENV}=<lines>.",
        file=sys.stderr,
    )


def print_failure_report(
    failures: GuardFailures,
    guard_input: GuardInput,
    thresholds: GuardThresholds,
) -> None:
    print_oversized_file_failures(failures, thresholds)
    print_forbidden_path_failures(failures)
    print_count_failures(failures, guard_input, thresholds)
    print_script_failures(failures, thresholds)
    print_contract_test_failures(failures, thresholds)
    print_failure_guidance()
