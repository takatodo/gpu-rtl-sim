"""Public imports re-exported by the large-file commit guard facade."""

from __future__ import annotations

try:
    from .check_staged_large_files_paths import (
        count_lines,
        forbidden_source_paths,
        is_guarded_contract_test_path,
        is_guarded_script_path,
        parse_numstat_records,
        parse_raw_diff_entries,
        repo_relative_path,
        unique_in_order,
    )
    from .check_staged_large_files_cli_args import build_parser
    from .check_staged_large_files_policy import (
        collect_failures,
        oversized_contract_test_changes,
        oversized_files,
        oversized_script_growth,
        oversized_script_sizes,
    )
    from .check_staged_large_files_report import format_size, print_failure_report
    from .check_staged_large_files_settings import (
        DEFAULT_MAX_BYTES,
        DEFAULT_MAX_CONTRACT_TEST_ADDED_LINES,
        DEFAULT_MAX_CONTRACT_TEST_TOTAL_LINES,
        DEFAULT_MAX_NEW_SCRIPT_FILES,
        DEFAULT_MAX_SCRIPT_ADDED_LINES,
        DEFAULT_MAX_SCRIPT_TOTAL_LINES,
        DEFAULT_MAX_STAGED_FILES,
        MAX_BYTES_ENV,
        MAX_STAGED_FILES_ENV,
        default_max_bytes_from_env,
        default_max_files_from_env,
        positive_int_from_env,
        resolve_thresholds,
        validate_thresholds,
    )
    from .check_staged_large_files_types import (
        ContractTestChange,
        FileSize,
        GitSizeCheckError,
        GuardFailures,
        GuardInput,
        GuardThresholds,
        LineDelta,
        RawDiffEntry,
        ScriptGrowth,
        ScriptSize,
        StagedBlob,
    )
except ImportError:  # pragma: no cover - exercised when run as a script dependency.
    from check_staged_large_files_paths import (
        count_lines,
        forbidden_source_paths,
        is_guarded_contract_test_path,
        is_guarded_script_path,
        parse_numstat_records,
        parse_raw_diff_entries,
        repo_relative_path,
        unique_in_order,
    )
    from check_staged_large_files_cli_args import build_parser
    from check_staged_large_files_policy import (
        collect_failures,
        oversized_contract_test_changes,
        oversized_files,
        oversized_script_growth,
        oversized_script_sizes,
    )
    from check_staged_large_files_report import format_size, print_failure_report
    from check_staged_large_files_settings import (
        DEFAULT_MAX_BYTES,
        DEFAULT_MAX_CONTRACT_TEST_ADDED_LINES,
        DEFAULT_MAX_CONTRACT_TEST_TOTAL_LINES,
        DEFAULT_MAX_NEW_SCRIPT_FILES,
        DEFAULT_MAX_SCRIPT_ADDED_LINES,
        DEFAULT_MAX_SCRIPT_TOTAL_LINES,
        DEFAULT_MAX_STAGED_FILES,
        MAX_BYTES_ENV,
        MAX_STAGED_FILES_ENV,
        default_max_bytes_from_env,
        default_max_files_from_env,
        positive_int_from_env,
        resolve_thresholds,
        validate_thresholds,
    )
    from check_staged_large_files_types import (
        ContractTestChange,
        FileSize,
        GitSizeCheckError,
        GuardFailures,
        GuardInput,
        GuardThresholds,
        LineDelta,
        RawDiffEntry,
        ScriptGrowth,
        ScriptSize,
        StagedBlob,
    )
