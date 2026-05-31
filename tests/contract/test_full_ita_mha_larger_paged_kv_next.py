import unittest

from tests.contract.full_ita_mha_larger_paged_kv_next_shared import *  # noqa: F403
from tests.contract import full_ita_mha_larger_paged_kv_next_shared as _shared


class FullItaMhaLargerPagedKvNextShimTest(unittest.TestCase):
    def test_shim_points_at_tracked_shared_contract(self) -> None:
        self.assertEqual(
            _shared.CURRENT_PRIORITY,
            "review_verilator_native_option_parser_direct_command_path_sidecar_stage_plan_execution_boundary_gate",
        )


def load_tests(loader, tests, pattern):
    return _shared.load_tests(loader, tests, pattern)


__all__ = [
    name
    for name in globals()
    if not name.startswith("_") and name != "load_tests"
]
