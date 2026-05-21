from __future__ import annotations

from dataclasses import dataclass


class GitSizeCheckError(RuntimeError):
    """Raised when staged blob sizes or thresholds cannot be read reliably."""


@dataclass(frozen=True)
class FileSize:
    path: str
    size_bytes: int


@dataclass(frozen=True)
class StagedBlob:
    path: str
    object_id: str | None


@dataclass(frozen=True)
class RawDiffEntry:
    old_mode: str
    new_mode: str
    old_object_id: str
    new_object_id: str
    status: str
    old_path: str | None
    path: str


@dataclass(frozen=True)
class ScriptGrowth:
    path: str
    added_lines: int


@dataclass(frozen=True)
class ScriptSize:
    path: str
    total_lines: int


@dataclass(frozen=True)
class LineDelta:
    path: str
    added_lines: int
    deleted_lines: int


@dataclass(frozen=True)
class ContractTestChange:
    path: str
    added_lines: int
    deleted_lines: int
    total_lines: int


@dataclass(frozen=True)
class GuardInput:
    files: list[FileSize]
    staged_count: int
    forbidden_paths: list[str]
    script_growth: list[ScriptGrowth]
    new_script_count: int
    script_sizes: list[ScriptSize]
    contract_test_changes: list[ContractTestChange]


@dataclass(frozen=True)
class GuardThresholds:
    max_bytes: int
    max_files: int
    max_script_added_lines: int
    max_new_script_files: int
    max_script_total_lines: int
    max_contract_test_added_lines: int
    max_contract_test_total_lines: int


@dataclass(frozen=True)
class GuardFailures:
    files: list[FileSize]
    forbidden_paths: list[str]
    script_growth: list[ScriptGrowth]
    script_sizes: list[ScriptSize]
    contract_tests: list[ContractTestChange]
    staged_count_exceeded: bool
    new_script_count_exceeded: bool

    def any(self) -> bool:
        return any(
            (
                self.files,
                self.forbidden_paths,
                self.script_growth,
                self.script_sizes,
                self.contract_tests,
                self.staged_count_exceeded,
                self.new_script_count_exceeded,
            )
        )
