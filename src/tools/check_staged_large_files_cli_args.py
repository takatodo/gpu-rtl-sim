from __future__ import annotations

import argparse

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
except ImportError:  # pragma: no cover - exercised when run as a script.
    from check_staged_large_files_settings import (
        MAX_BYTES_ENV,
        MAX_CONTRACT_TEST_ADDED_LINES_ENV,
        MAX_CONTRACT_TEST_TOTAL_LINES_ENV,
        MAX_NEW_SCRIPT_FILES_ENV,
        MAX_SCRIPT_ADDED_LINES_ENV,
        MAX_SCRIPT_TOTAL_LINES_ENV,
        MAX_STAGED_FILES_ENV,
    )


def add_file_limit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help=f"Maximum allowed staged file size in bytes. Overrides {MAX_BYTES_ENV}.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help=f"Maximum allowed staged source file count. Overrides {MAX_STAGED_FILES_ENV}.",
    )


def add_script_limit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-script-added-lines",
        type=int,
        default=None,
        help=f"Maximum allowed added lines per guarded script. Overrides {MAX_SCRIPT_ADDED_LINES_ENV}.",
    )
    parser.add_argument(
        "--max-new-script-files",
        type=int,
        default=None,
        help=f"Maximum allowed new guarded script files per commit. Overrides {MAX_NEW_SCRIPT_FILES_ENV}.",
    )
    parser.add_argument(
        "--max-script-total-lines",
        type=int,
        default=None,
        help=f"Maximum allowed total lines in one staged guarded script. Overrides {MAX_SCRIPT_TOTAL_LINES_ENV}.",
    )


def add_contract_test_limit_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-contract-test-added-lines",
        type=int,
        default=None,
        help=(
            "Maximum allowed added lines per guarded contract test. "
            f"Overrides {MAX_CONTRACT_TEST_ADDED_LINES_ENV}."
        ),
    )
    parser.add_argument(
        "--max-contract-test-total-lines",
        type=int,
        default=None,
        help=(
            "Maximum allowed total lines in one growing guarded contract test. "
            f"Overrides {MAX_CONTRACT_TEST_TOTAL_LINES_ENV}."
        ),
    )


def add_path_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Check these filesystem paths instead of staged git blobs. Intended for tests and local audits.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reject files larger than the configured commit threshold.")
    add_file_limit_args(parser)
    add_script_limit_args(parser)
    add_contract_test_limit_args(parser)
    add_path_args(parser)
    return parser
