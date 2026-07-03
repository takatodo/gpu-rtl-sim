import dataclasses
import sys
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_search as search  # noqa: E402
import scientific_circt_source_variant_search_codegen as codegen  # noqa: E402


GOLDEN_DIR = REPO_ROOT / "artifacts/scientific_circt/hls_attention_head4"


def attention_py(x: list[int]) -> list[int]:
    score0 = sum(int(x[j]) * int(x[4 + j]) for j in range(4))
    score1 = sum(int(x[j]) * int(x[8 + j]) for j in range(4))
    w0 = (score0 + 1) * (score0 + 1)
    w1 = (score1 + 1) * (score1 + 1)
    return [w0 * x[12 + j] + w1 * x[16 + j] for j in range(4)]


class ScientificCirctSourceVariantSearchTest(unittest.TestCase):
    def test_attention_replicate4_codegen_is_byte_identical_to_golden_sources(self) -> None:
        plan = search.VariantPlan((search.Replicate(4),))
        sources = codegen.render_sources(search.ATTENTION_DESCRIPTOR, plan)
        self.assertEqual(sources.cuda, (GOLDEN_DIR / "attention_head4_hls_friendly_gpu.cu").read_text(encoding="utf-8"))
        self.assertEqual(sources.bridge, (GOLDEN_DIR / "attention_head4_hls_friendly_bridge.cpp").read_text(encoding="utf-8"))

    def test_codegen_source_has_no_literal_replication_count_branches(self) -> None:
        source = Path(codegen.__file__).read_text(encoding="utf-8")
        self.assertNotIn("h3_", source)
        self.assertNotIn("attention_head4_hls_friendly", source)
        self.assertNotIn("if shape.units == 4", source)

    def test_transform_obligations_pass_and_corruptions_fail(self) -> None:
        plan = search.VariantPlan((search.Replicate(2), search.UnrollDensity(250), search.PackInputs("uint32")))
        self.assertTrue(search.transform_obligation_holds(search.ATTENTION_DESCRIPTOR, plan, attention_py))
        shared = dataclasses.replace(search.ATTENTION_DESCRIPTOR, shared_accumulator=True)
        permuted = dataclasses.replace(search.ATTENTION_DESCRIPTOR, input_permutation=tuple(reversed(range(20))))
        self.assertFalse(search.transform_obligation_holds(shared, plan, attention_py))
        self.assertFalse(search.transform_obligation_holds(permuted, plan, attention_py))

    def test_gates_fail_closed_on_mismatch_and_below_band(self) -> None:
        mismatch = {
            "variant": "bad",
            "samples": [
                {
                    "status": "runtime_handoff_boundary_measured",
                    "cpu_vs_gpu_output_equal": False,
                    "cpu_vs_gpu_control_checksum_equal": True,
                    "cpu_to_bridge_hybrid_wall_speedup": 99.0,
                }
            ],
        }
        self.assertEqual(search.decide_intermediate_gate(10.0, [mismatch]), (False, "oracle_mismatch_in_search"))
        below = {
            "variant": "slow",
            "samples": [
                {
                    "status": "runtime_handoff_boundary_measured",
                    "cpu_vs_gpu_output_equal": True,
                    "cpu_vs_gpu_control_checksum_equal": True,
                    "cpu_to_bridge_hybrid_wall_speedup": 10.1,
                }
            ],
        }
        self.assertEqual(search.decide_intermediate_gate(10.0, [below]), (False, "below_intermediate_delta"))
        self.assertEqual(search.decide_falsification_gate(20.0, [below]), (False, "speedup_out_of_band"))

    def test_enumerate_plans_is_deterministic_and_budgeted(self) -> None:
        first = search.enumerate_plans("intermediate")
        second = search.enumerate_plans("intermediate")
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 12)
        self.assertEqual(first[0], search.VariantPlan())
        shapes = [search.plan_shape(plan) for plan in first]
        self.assertIn(search.PlanShape(4, 250, "uint8"), shapes)
        self.assertIn(search.PlanShape(4, 1000, "uint32"), shapes)


if __name__ == "__main__":
    unittest.main()
