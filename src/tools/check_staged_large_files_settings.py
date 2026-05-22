from __future__ import annotations

import os
from argparse import Namespace, ArgumentParser

try:
    from .check_staged_large_files_types import GitSizeCheckError, GuardThresholds
except ImportError:  # pragma: no cover - exercised when run as a script dependency.
    from check_staged_large_files_types import GitSizeCheckError, GuardThresholds


DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_STAGED_FILES = 100
DEFAULT_MAX_SCRIPT_ADDED_LINES = 250
DEFAULT_MAX_NEW_SCRIPT_FILES = 3
DEFAULT_MAX_SCRIPT_TOTAL_LINES = 300
DEFAULT_MAX_CONTRACT_TEST_ADDED_LINES = 250
DEFAULT_MAX_CONTRACT_TEST_TOTAL_LINES = 1200
MAX_BYTES_ENV = "GPU_TOGGLE_MAX_COMMIT_FILE_BYTES"
MAX_STAGED_FILES_ENV = "GPU_TOGGLE_MAX_COMMIT_FILE_COUNT"
MAX_SCRIPT_ADDED_LINES_ENV = "GPU_TOGGLE_MAX_SCRIPT_ADDED_LINES"
MAX_NEW_SCRIPT_FILES_ENV = "GPU_TOGGLE_MAX_NEW_SCRIPT_FILES"
MAX_SCRIPT_TOTAL_LINES_ENV = "GPU_TOGGLE_MAX_SCRIPT_TOTAL_LINES"
MAX_CONTRACT_TEST_ADDED_LINES_ENV = "GPU_TOGGLE_MAX_CONTRACT_TEST_ADDED_LINES"
MAX_CONTRACT_TEST_TOTAL_LINES_ENV = "GPU_TOGGLE_MAX_CONTRACT_TEST_TOTAL_LINES"


def positive_int_from_env(env_name: str, default: int) -> int:
    value = os.environ.get(env_name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise GitSizeCheckError(f"{env_name} must be an integer, got {value!r}") from exc
    if parsed <= 0:
        raise GitSizeCheckError(f"{env_name} must be positive, got {value!r}")
    return parsed


def default_max_bytes_from_env() -> int:
    return positive_int_from_env(MAX_BYTES_ENV, DEFAULT_MAX_BYTES)


def default_max_files_from_env() -> int:
    return positive_int_from_env(MAX_STAGED_FILES_ENV, DEFAULT_MAX_STAGED_FILES)


def resolve_thresholds(args: Namespace) -> GuardThresholds:
    return GuardThresholds(
        max_bytes=args.max_bytes if args.max_bytes is not None else default_max_bytes_from_env(),
        max_files=args.max_files if args.max_files is not None else default_max_files_from_env(),
        max_script_added_lines=(
            args.max_script_added_lines
            if args.max_script_added_lines is not None
            else positive_int_from_env(MAX_SCRIPT_ADDED_LINES_ENV, DEFAULT_MAX_SCRIPT_ADDED_LINES)
        ),
        max_new_script_files=(
            args.max_new_script_files
            if args.max_new_script_files is not None
            else positive_int_from_env(MAX_NEW_SCRIPT_FILES_ENV, DEFAULT_MAX_NEW_SCRIPT_FILES)
        ),
        max_script_total_lines=(
            args.max_script_total_lines
            if args.max_script_total_lines is not None
            else positive_int_from_env(MAX_SCRIPT_TOTAL_LINES_ENV, DEFAULT_MAX_SCRIPT_TOTAL_LINES)
        ),
        max_contract_test_added_lines=(
            args.max_contract_test_added_lines
            if args.max_contract_test_added_lines is not None
            else positive_int_from_env(MAX_CONTRACT_TEST_ADDED_LINES_ENV, DEFAULT_MAX_CONTRACT_TEST_ADDED_LINES)
        ),
        max_contract_test_total_lines=(
            args.max_contract_test_total_lines
            if args.max_contract_test_total_lines is not None
            else positive_int_from_env(MAX_CONTRACT_TEST_TOTAL_LINES_ENV, DEFAULT_MAX_CONTRACT_TEST_TOTAL_LINES)
        ),
    )


def validate_thresholds(parser: ArgumentParser, thresholds: GuardThresholds) -> None:
    if thresholds.max_bytes <= 0:
        parser.error("--max-bytes must be positive")
    if thresholds.max_files <= 0:
        parser.error("--max-files must be positive")
    if thresholds.max_script_added_lines <= 0:
        parser.error("--max-script-added-lines must be positive")
    if thresholds.max_new_script_files <= 0:
        parser.error("--max-new-script-files must be positive")
    if thresholds.max_script_total_lines <= 0:
        parser.error("--max-script-total-lines must be positive")
    if thresholds.max_contract_test_added_lines <= 0:
        parser.error("--max-contract-test-added-lines must be positive")
    if thresholds.max_contract_test_total_lines <= 0:
        parser.error("--max-contract-test-total-lines must be positive")
