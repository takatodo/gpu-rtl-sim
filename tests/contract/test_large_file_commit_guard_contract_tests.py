import unittest
from pathlib import Path

from src.tools import check_staged_large_files


REPO_ROOT = Path(__file__).resolve().parents[2]


class LargeFileCommitGuardContractTestBudgetTest(unittest.TestCase):
    def test_contract_test_guard_rejects_new_large_contract_test(self) -> None:
        changes = [
            check_staged_large_files.ContractTestChange(
                "tests/contract/test_generated_large_gate.py",
                added_lines=2100,
                deleted_lines=0,
                total_lines=2100,
            )
        ]

        failures = check_staged_large_files.oversized_contract_test_changes(
            changes,
            max_added_lines=250,
            max_total_lines=1200,
        )

        self.assertEqual(failures, changes)

    def test_contract_test_guard_allows_oversized_contract_test_to_shrink(self) -> None:
        changes = [
            check_staged_large_files.ContractTestChange(
                "tests/contract/test_full_ita_mha_larger_paged_kv_next.py",
                added_lines=50,
                deleted_lines=300,
                total_lines=14800,
            )
        ]

        failures = check_staged_large_files.oversized_contract_test_changes(
            changes,
            max_added_lines=250,
            max_total_lines=1200,
        )

        self.assertEqual(failures, [])

    def test_contract_test_guard_rejects_non_shrinking_large_contract_test(self) -> None:
        changes = [
            check_staged_large_files.ContractTestChange(
                "tests/contract/test_full_ita_mha_larger_paged_kv_next.py",
                added_lines=20,
                deleted_lines=20,
                total_lines=14987,
            )
        ]

        failures = check_staged_large_files.oversized_contract_test_changes(
            changes,
            max_added_lines=250,
            max_total_lines=1200,
        )

        self.assertEqual(failures, changes)

    def test_contract_test_guard_rejects_large_added_delta_even_under_total_budget(self) -> None:
        changes = [
            check_staged_large_files.ContractTestChange(
                "tests/contract/test_bloated_but_small_total.py",
                added_lines=300,
                deleted_lines=0,
                total_lines=900,
            )
        ]

        failures = check_staged_large_files.oversized_contract_test_changes(
            changes,
            max_added_lines=250,
            max_total_lines=1200,
        )

        self.assertEqual(failures, changes)

    def test_full_ita_mha_larger_paged_kv_shards_stay_below_contract_test_budget(self) -> None:
        shard_paths = sorted(REPO_ROOT.glob("tests/contract/test_full_ita_mha_larger_paged_kv_next*.py"))

        oversized = []
        for path in shard_paths:
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > check_staged_large_files.DEFAULT_MAX_CONTRACT_TEST_TOTAL_LINES:
                oversized.append(f"{relative_path}: {line_count} lines")

        self.assertEqual(oversized, [])


if __name__ == "__main__":
    unittest.main()
