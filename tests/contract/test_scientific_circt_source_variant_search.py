import dataclasses
import sys
import unittest
from pathlib import Path

from tests.contract.hybrid_cli_helpers import REPO_ROOT, TOOLS_DIR

sys.path.insert(0, TOOLS_DIR.as_posix())

import scientific_circt_source_variant_search as search  # noqa: E402
import scientific_circt_source_variant_search_codegen as codegen  # noqa: E402


GOLDEN_DIR = REPO_ROOT / "artifacts/scientific_circt/hls_attention_head4"
GOLDEN_MLP4_DIR = REPO_ROOT / "artifacts/scientific_circt/hls_mlp_block_variants/mlp4_hls_friendly"


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

    def test_mlp_replicate4_firrtl_is_byte_identical_to_golden_hand_tuned_variant(self) -> None:
        # The mlp descriptor is extracted from mlp_blocks.VARIANTS["mlp4_hls_friendly"], so
        # Replicate(4) at fixed density should reproduce its FIRRTL exactly (same module name,
        # same node graph). CUDA/bridge intentionally differ: they embed the search's own
        # variant/symbol name (mlp4_source_variant_search) rather than the golden's, so those
        # are not byte-identical even though the descriptor extraction is faithful.
        descriptor = codegen.descriptor_for_candidate("microgpt_mlp_slice")
        plan = search.VariantPlan((search.Replicate(4),))
        sources = codegen.render_sources(descriptor, plan)
        self.assertEqual(sources.firrtl, (GOLDEN_MLP4_DIR / "mlp4_hls_friendly.fir").read_text(encoding="utf-8"))

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

    REFERENCE_PLAN = search.VariantPlan((search.Replicate(4),))

    def test_gates_fail_closed_on_mismatch_and_below_band(self) -> None:
        mismatch = {
            "variant": "bad",
            "plan": str(self.REFERENCE_PLAN),
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
            "plan": str(search.VariantPlan((search.Replicate(6),))),
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
        self.assertEqual(search.decide_falsification_gate(self.REFERENCE_PLAN, 20.0, [below]), (False, "speedup_out_of_band"))

    def test_gates_fail_closed_with_distinct_reason_on_unmeasured_plan(self) -> None:
        unmeasured = {
            "variant": "broken_build",
            "plan": str(self.REFERENCE_PLAN),
            "samples": [{"status": "failed_cxx_direct_callsite_build"}],
        }
        self.assertEqual(search.decide_intermediate_gate(10.0, [unmeasured]), (False, "unmeasured_plan_in_search"))
        self.assertEqual(search.decide_falsification_gate(self.REFERENCE_PLAN, 10.0, [unmeasured]), (False, "unmeasured_plan_in_search"))

    def test_falsification_gate_passes_on_structure_identity_regardless_of_measured_value(self) -> None:
        # Same structure as the reference, but a wildly different measured value: this must still
        # pass, because value equality is implied by byte-identical codegen, not re-checked here.
        same_structure_different_value = {
            "variant": "attention_head4_hls_friendly",
            "plan": str(self.REFERENCE_PLAN),
            "samples": [
                {
                    "status": "runtime_handoff_boundary_measured",
                    "cpu_vs_gpu_output_equal": True,
                    "cpu_vs_gpu_control_checksum_equal": True,
                    "cpu_to_bridge_hybrid_wall_speedup": 999.0,
                }
            ],
        }
        self.assertEqual(
            search.decide_falsification_gate(self.REFERENCE_PLAN, 6.0, [same_structure_different_value]), (True, "passed")
        )

    def test_falsification_gate_flags_structure_mismatch_with_higher_value_as_a_finding(self) -> None:
        superior = {
            "variant": "beats_reference",
            "plan": str(search.VariantPlan((search.Replicate(8),))),
            "samples": [
                {
                    "status": "runtime_handoff_boundary_measured",
                    "cpu_vs_gpu_output_equal": True,
                    "cpu_vs_gpu_control_checksum_equal": True,
                    "cpu_to_bridge_hybrid_wall_speedup": 50.0,
                }
            ],
        }
        self.assertEqual(search.decide_falsification_gate(self.REFERENCE_PLAN, 10.0, [superior]), (False, "superior_variant_found"))

    def test_enumerate_plans_is_structural_only_at_fixed_density(self) -> None:
        first = search.enumerate_plans("intermediate")
        second = search.enumerate_plans("intermediate")
        self.assertEqual(first, second)
        self.assertEqual(first[0], search.VariantPlan())
        self.assertEqual(
            first,
            [search.VariantPlan()] + [search.VariantPlan((search.Replicate(n),)) for n in (2, 3, 4, 6, 8)],
        )
        shapes = [search.plan_shape(plan) for plan in first]
        self.assertTrue(all(shape.inner_repeat == 1000 and shape.packing == "uint8" for shape in shapes))

    def test_enumerate_density_probes_covers_unroll_density_at_winning_replicate(self) -> None:
        probes = search.enumerate_density_probes()
        shapes = [search.plan_shape(plan) for plan in probes]
        self.assertEqual(shapes, [search.PlanShape(4, m, "uint8") for m in (250, 500, 2000)])
        self.assertTrue(all(search.PackInputs("uint32") not in plan.transforms for plan in probes))
        self.assertTrue(all(search.PackInputs("uint32") not in plan.transforms for plan in search.enumerate_plans("falsification")))


if __name__ == "__main__":
    unittest.main()
