import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = (
    REPO_ROOT
    / "config"
    / "scaling_gates"
    / "define_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate.json"
)


class VerilatorNativeOptionParserIntegerHardeningGateTest(unittest.TestCase):
    def read_gate(self) -> dict[str, object]:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def test_definition_selects_strict_integer_hardening_boundary(self) -> None:
        gate = self.read_gate()

        self.assertEqual(
            gate["source_review_gate"],
            "config/scaling_gates/review_verilator_native_option_parser_overlay_patch_parser_behavior_run_gate.json",
        )
        self.assertEqual(
            gate["current_priority"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )
        decision = gate["definition_decision"]
        self.assertEqual(decision["selected_strategy"], "define_hardening_cases_before_patch_change")
        self.assertIn("std::atoi", decision["weakest_point"])

        boundary = gate["hardening_boundary"]
        self.assertEqual(boundary["validation_kind"], "built_verilator_binary_parser_integer_hardening_smoke")
        self.assertFalse(boundary["requires_verilator_source_in_repository"])
        self.assertFalse(boundary["uses_generated_artifacts_as_source_of_truth"])

    def test_definition_pins_negative_and_suffix_cases_without_claiming_success(self) -> None:
        gate = self.read_gate()
        cases = {case["name"]: case for case in gate["required_hardening_cases"]}

        self.assertEqual(
            cases["reject_negative_states_separate_token"]["argv_suffix"],
            ["--sim-accel", "sidecar-gpu", "--sim-accel-states", "-1", "--sim-accel-steps", "1"],
        )
        self.assertIn("tokenizer behavior", cases["reject_negative_steps_separate_token"]["reason"])
        self.assertIn("64abc", cases["reject_non_numeric_states_suffix"]["argv_suffix"])
        self.assertIn("std::atoi", cases["reject_non_numeric_steps_suffix"]["reason"])

        deferred = gate["explicitly_deferred_behavior"]
        self.assertEqual(deferred["equals_form_negative_values"]["status"], "optional_tokenization_control_case")
        self.assertEqual(deferred["compact_shape_spelling"]["status"], "outside_native_minimum")

        policy = gate["acceptance_policy"]
        self.assertTrue(policy["definition_only"])
        self.assertTrue(policy["parser_integer_hardening_boundary_defined"])
        self.assertFalse(policy["hardening_smoke_executed_by_this_gate"])
        self.assertFalse(policy["strict_integer_parsing_claim_allowed_by_gate_alone"])
        self.assertFalse(policy["sidecar_handoff_claim_allowed_by_gate_alone"])

    def test_next_gate_reviews_before_patch_or_execution_claims(self) -> None:
        gate = self.read_gate()
        next_gate = gate["required_next_gate"]

        self.assertEqual(
            next_gate["name"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )
        self.assertIn("strict integer parsing is implemented", next_gate["must_not_claim"])
        self.assertEqual(
            gate["next_task"],
            "review_verilator_native_option_parser_overlay_patch_parser_integer_hardening_gate",
        )


if __name__ == "__main__":
    unittest.main()
