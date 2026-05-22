import importlib
import unittest
from pathlib import Path

from tests.contract.full_ita_mha_larger_paged_kv_next_constants import *  # noqa: F403
from tests.contract.full_ita_mha_larger_paged_kv_next_constants import (
    CURRENT_PRIORITY,
    CURRENT_PRIORITY_SOURCE_ARTIFACT,
)


def load_tests(
    loader: unittest.TestLoader,
    tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    if pattern is not None:
        return tests

    suite = unittest.TestSuite()
    package = __package__ or "tests.contract"
    for shard in sorted(Path(__file__).parent.glob("test_full_ita_mha_larger_paged_kv_next_*.py")):
        if shard.stem == "test_full_ita_mha_larger_paged_kv_next":
            continue
        module = importlib.import_module(f"{package}.{shard.stem}")
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


class FullItaMhaAndLargerPagedKvNextGateTestBase(unittest.TestCase):
    def assert_no_runtime_or_new_workload_claims(self, policy: dict[str, object]) -> None:
        self.assertFalse(policy["runtime_or_abi_change_allowed_by_this_gate"])
        self.assertFalse(policy["new_workload_allowed_by_this_gate"])

    def assert_no_measurement_runtime_or_workload_claims(self, policy: dict[str, object]) -> None:
        self.assertFalse(policy["new_measurement_allowed_by_this_gate"])
        self.assert_no_runtime_or_new_workload_claims(policy)

    def assert_current_priority_selection(self, selection: dict[str, object]) -> None:
        self.assertEqual(selection["current_priority"], CURRENT_PRIORITY)
        self.assertEqual(selection["current_priority_source_artifact"], CURRENT_PRIORITY_SOURCE_ARTIFACT)

    def assert_tokens_present(self, text: str, tokens: tuple[str, ...]) -> None:
        for token in tokens:
            self.assertIn(token, text)


__all__ = [
    name
    for name in globals()
    if not name.startswith("_") and name != "load_tests"
]
